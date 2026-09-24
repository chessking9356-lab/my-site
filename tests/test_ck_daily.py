import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('daily', ROOT / 'research_daily/daily.py')
d = importlib.util.module_from_spec(spec)
spec.loader.exec_module(d)
PROFILE = json.loads((ROOT / 'research_daily/profile.json').read_text('utf-8'))


def paper(i, group):
    titles = {'A': 'Physics-informed neural inverse constitutive mechanics',
              'B': 'Bioinspired nacre composite fracture toughness',
              'C': 'Ice adhesion loading rate interfacial fracture'}
    p = {'id': f'10.1234/example{i}', 'doi': f'10.1234/example{i}', 'title': titles[group],
         'date': '2026-09-23', 'url': f'https://doi.org/10.1234/example{i}',
         'journal': 'Synthetic fixture only', 'abstract': '', 'supplement': False}
    return d.score(p, PROFILE, [])


class DailyTests(unittest.TestCase):
    def test_timezone_previous_natural_day(self):
        now = d.dt.datetime(2026, 9, 24, 23, 17, tzinfo=d.dt.timezone.utc)
        self.assertEqual(str(now.astimezone(d.TZ).date()), '2026-09-25')

    def test_publication_date_and_future_issue(self):
        self.assertEqual(d.publication({'published-online': {'date-parts': [[2026, 9, 22]]},
                                       'published-print': {'date-parts': [[2027, 1, 1]]}}), '2026-09-22')
        self.assertIsNone(d.publication({'issued': {'date-parts': [[2026]]}}))

    def test_topic_gates_no_generic_ai_or_office_ice(self):
        p = paper(1, 'A')
        for title in ['Machine learning for clinical diagnosis', 'Office management and service design']:
                self.assertIsNone(d.score(dict(p, title=title), PROFILE, []))

    def test_reject_false_positive_live_examples(self):
        p = paper(1, 'A')
        for title in [
            'Physics-Informed Machine Learning with Monotonic Constraints for Daily Fuel Consumption of Ships',
            'Bioinspired Nanocomposite with Enhanced Pesticidal Activity for Sustainable Agrochemical Delivery',
            'Factors Influencing Poor Ice Nucleation by Model Fatty Acid Monolayers',
        ]:
            self.assertIsNone(d.score(dict(p, title=title, abstract='Material interface mechanical stress.'), PROFILE, []))

    @patch.dict(d.os.environ, {'OPENAI_API_KEY': 'fixture-only'}, clear=True)
    def test_model_failure_does_not_invent_reviews(self):
        p = dict(paper(1, 'A'), abstract='Independent measurements constrain the constitutive parameters in the inverse problem.')
        with patch.object(d, 'request', side_effect=d.SafeError('HTTP_429')):
            reviews, mode = d.analyze([p], PROFILE, [])
            self.assertEqual(reviews, {})
            self.assertIn('降级', mode)

    @patch.dict(d.os.environ, {'OPENAI_API_KEY': 'fixture-only'}, clear=True)
    def test_model_evidence_must_match(self):
        p = dict(paper(1, 'A'), abstract='Independent measurements constrain the constitutive parameters in the inverse problem.')
        review = {'id': p['id'], 'summary': '摘要', 'why': '关联', 'next': '核查',
                  'quote': 'This invented sentence is not supported'}
        result = {'status': 'completed', 'output': [{'content': [{'type': 'output_text', 'text': json.dumps({'papers': [review]})}]}]}
        with patch.object(d, 'request', return_value=result):
            self.assertEqual(d.analyze([p], PROFILE, [])[0], {})
        review['quote'] = 'Independent measurements constrain the constitutive parameters'
        result['output'][0]['content'][0]['text'] = json.dumps({'papers': [review]})
        with patch.object(d, 'request', return_value=result):
            self.assertIn(p['id'], d.analyze([p], PROFILE, [])[0])

    @patch.dict(d.os.environ, {}, clear=True)
    def test_insufficient_content_not_labelled_ready(self):
        pool = [paper(1, 'A')]
        r = d.make_report(d.dt.date(2026, 9, 24), PROFILE, pool, [], set(), [])
        self.assertEqual(r['status'], 'insufficient')
        self.assertEqual(r['counts']['recommended'], 1)

    def test_normalize_doi_and_ignore_imprecise_dates(self):
        record = {'DOI': '10.1234/AbC', 'title': ['A valid title'],
                  'published': {'date-parts': [[2026, 9, 23]]}}
        self.assertEqual(d.normalize(record)['id'], '10.1234/abc')
        record['published']['date-parts'] = [[2026, 9]]
        self.assertIsNone(d.normalize(record))

    def test_balanced_selection_and_history(self):
        pool = [paper(i, g) for i, g in enumerate('AAABBBCCC')]
        eligible, selected = d.choose(pool, {pool[0]['id']})
        self.assertEqual(len(selected), 6)
        self.assertNotIn(pool[0]['id'], [p['id'] for p in selected])
        self.assertEqual({g: sum(p['group'] == g for p in selected) for g in 'ABC'}, {'A': 2, 'B': 2, 'C': 2})

    @patch.dict(d.os.environ, {}, clear=True)
    def test_no_model_honest_counts_and_card(self):
        pool = [paper(i, g) for i, g in enumerate('AABBCC')]
        r = d.make_report(d.dt.date(2026, 9, 24), PROFILE, pool, [], set(), [])
        self.assertEqual(r['counts']['deep_review'], 0)
        self.assertEqual(r['status'], 'ready')
        payload = d.card(r, True)
        self.assertLess(len(json.dumps(payload, ensure_ascii=False).encode()), 19000)
        self.assertIn('CK科研日报', payload['card']['header']['title']['content'])

    @patch.dict(d.os.environ, {'FEISHU_WEBHOOK': 'https://open.feishu.cn/open-apis/bot/v2/hook/test-only', 'FEISHU_SECRET': 'test-only'}, clear=True)
    def test_signature_and_business_error(self):
        with patch.object(d.time, 'time', return_value=1700000000), patch.object(d, 'request', return_value={'code': 0}) as req:
            d.send({'msg_type': 'interactive'})
            sent = req.call_args.args[1]
            import base64, hashlib, hmac
            self.assertEqual(sent['sign'], base64.b64encode(hmac.new(b'1700000000\ntest-only', b'', hashlib.sha256).digest()).decode())
            self.assertEqual(req.call_args.kwargs['attempts'], 1)
        with patch.object(d, 'request', return_value={'code': 19024, 'msg': 'sensitive response'}):
            with self.assertRaisesRegex(d.SafeError, '^FEISHU_REJECTED_19024$'):
                d.send({})

    def test_reject_hook_on_other_host(self):
        with patch.dict(d.os.environ, {'FEISHU_WEBHOOK': 'https://example.com/hook', 'FEISHU_SECRET': 'x'}, clear=True):
            with self.assertRaises(d.SafeError):
                d.credentials()

    def test_local_state_roundtrip(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(d.os.environ, {'CK_STATE_DIR': temp}, clear=True):
            s = d.State()
            self.assertIsNone(s.read('activation.json'))
            s.write('deliveries/2026-09-24.json', {'status': 'pending'})
            self.assertEqual(s.read('deliveries/2026-09-24.json')['status'], 'pending')


if __name__ == '__main__':
    unittest.main()
