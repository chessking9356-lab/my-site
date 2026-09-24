# CK 科研日报 MVP

这是现有 `my-site` 仓库内的日报模块，不新建网站或仓库。原首页保持现状。

## 首次上线：用户只在 GitHub 页面填写密钥

1. 打开 https://github.com/chessking9356-lab/my-site/settings/secrets/actions ，点击 **New repository secret**：
   - `FEISHU_WEBHOOK`：现有「CK 科研日报」群自定义机器人的完整 Webhook。
   - `FEISHU_SECRET`：该机器人启用「签名校验」时的 Secret。
   - 可选 `OPENAI_API_KEY`：启用中文摘要深析。未配置或调用失败时，自动降级为明确标注的基础筛选；`deep_review=0`。API 使用单独计费，不是 ChatGPT 订阅额度。
   - 可选 `RESEARCH_CONTEXT`：最近 1–3 天科研问题的简短描述。只通过运行环境传入分析模型，不写入代码或日报存档。建议描述研究问题，不放未公开数据。
2. 机器人关键词需包含 `CK科研日报`（无空格）。代码标题固定包含该字符串。签名校验保持开启。
3. 模块合入默认分支后，首次代码推送会先运行测试卡片流程。若先合入、后填密钥，打开 **Actions → CK Research Daily → Run workflow → mode=test**。
4. 测试卡片真实发送成功且有 5–8 篇、A/B/C 均覆盖后，程序才写入激活记录。每天定时流程在激活记录不存在时拒绝发送。
5. 锁屏确认 iPhone 收到飞书通知。程序只能确认飞书服务端返回成功，不能检测你的手机通知。群内有卡片、锁屏无通知时，检查 iOS 的飞书通知权限、群免打扰和专注模式。

**不要把密钥粘到聊天、代码、Actions 输入栏、Issue、README 或命令行参数里。** 本模块不会输出请求 URL、签名或第三方原始错误响应。

## 时间与运行模式

- 每天北京时间 07:17 开始准备，在 08:00 发送（UTC cron 为前一天 23:17）。首次目标为 2026-09-25 08:00 Asia/Shanghai。
- GitHub 定时任务可能延迟或丢失，不能保证严格准点；晚启动则生成后立即补发。
- `dry-run`：真实检索、生成本地日报和卡片，不发送、不激活。
- `test`：真实检索并发送带【测试】标记的卡片；成功后激活定时流程，不消耗正式推荐历史。
- `daily`：检查激活、当日发送记录和推荐历史后发送。当日已发送则跳过。
- 手动运行 `daily` 会立即发送，不等待 08:00。定时运行才带 `--at-eight`。

不要同时建立另一套 Codex 定时推送或第二个仓库，以免重复消息。

## 内容与覆盖边界

目前仅使用 Crossref 的公开期刊元数据接口，以 A/B/C 每方向两个检索式、每式最多 40 条建立候选池。先查前一自然日，再按方向缺口扩展到 30 天、180 天。所有更早条目单独标记；不会冒充昨日新论文。

Crossref 出版日期通常没有时区，因此日期过滤按其原始出版日期执行；不能据此宣称获得了精确北京时间窗口内的全部新文献。未知完整日期、未来发表日期、勘误/撤稿标题过滤掉。

- A：AI × 材料力学；物理约束学习、参数反演、断裂/本构。
- B：仿生材料；珍珠母、透明玻璃、界面增韧、抗冲击。
- C：防冰/冰界面；速率、柔度、脱粘、失效稳定性。
- 目标每方向 2 篇，共 6 篇。不足则诚实报告，不用无关论文凑数。
- 默认长期重点与当前研究主线一致；**GitHub Actions 无法自行读取 ChatGPT 对话**。最近讨论自动同步尚未接入，`RESEARCH_CONTEXT` 需要更新。初版不能声称每天已自动回顾最新聊天。
- AI 仅分析来源提供的摘要，不下载/声称读过全文。每条 AI 分析需返回可在原摘要找到的证据片段；未知 ID、无效输出、证据不匹配会拒收或降级。此校验不代替学术核查。
- 无模型密钥时保留英文原题、中文研究匹配理由和阅读全文核查问题；不会编造中文研究结论。

## coverage-first 数据接口

`report.json` 保存 `scanned / candidate / deep_review / recommended`：

- `scanned`：本次实际获得并通过基本元数据有效性检查、去重后的记录数；不是数据库总量。
- `candidate`：通过方向门槛且未在历史正式推荐的记录数。
- `deep_review`：通过证据校验的 AI 摘要分析数量；无模型则 0。
- `recommended`：真正写入卡片的文献数。

`coverage_status=search_only`；每个数据源请求记录检索词、日期窗口、返回数、成功/失败、是否扩展窗口。`source_total` 是源返回匹配总量，绝不充当扫描数。

`candidate-pool.json → 规则粗筛 → 最多18篇摘要分析 → 5–8篇精选 → report.json / feishu-card.json / daily.html`。

后续把收集器替换为 arXiv 分类枚举、Crossref/OpenAlex 游标采集等，保持下游结构即可。当前未接 arXiv、ChemRxiv、RSS，也不是全量监测。候选池导入入口：

```sh
python research_daily/daily.py --mode dry-run --input path/to/candidate-pool.json
```

输入采用本模块导出的规范化结构，先用于复用同一次采集与调试；接入 Hub 时需显式映射既有字段。

## 归档与重复保护

每次运行归档为 Actions Artifact（90天）：`daily.html`、`report.json`、`candidate-pool.json`、未加签的 `feishu-card.json`。这不是新的公开站点。现有 Research Hub 后续可读取 JSON；当前尚未改造 Hub 展示层。

仓库 `ck-daily-state` 分支保存激活、日期与 DOI 历史，不含 Webhook、Secret 或研究聊天。该仓库为公开仓库，因此这些日期/DOI 记录可公开访问。

发送前先写 `pending`，服务端确认后写 `sent`。Webhook 不支持幂等键；网络超时等不确定结果不会自动重试以免重复推送。遇到 `DELIVERY_UNCERTAIN_CHECK_GROUP_BEFORE_RETRY`，先在飞书群确认是否收到，再处理当日 `deliveries/YYYY-MM-DD.json`。已收到则设为 `sent`；确定未收到才删除当日记录后重跑。不要盲目重跑。

GitHub token 使用本仓库 `contents:write` 写状态分支；无额外 PAT。若仓库规则阻止创建/写入状态分支，先允许 Actions 在该状态分支写入，否则流程会在发送前失败。

## 本地验证

仅需 Python 3.12 标准库，无依赖安装：

```sh
python -m unittest discover -s tests -p 'test_ck_daily.py' -v
python research_daily/daily.py --mode dry-run
```

本地真实发送也只能通过环境变量提供密钥，不能写进源码。默认不发送。

## 官方接口说明

- 飞书：https://open.feishu.cn/document/client-docs/bot-v3/add-custom-bot
- Crossref：https://www.crossref.org/documentation/retrieve-metadata/rest-api/rest-api-filters/
- GitHub 定时限制：https://docs.github.com/en/actions/how-tos/troubleshoot-workflows
- 可选 AI 接口：https://developers.openai.com/api/docs/guides/structured-outputs
