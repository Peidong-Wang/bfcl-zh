# 中文 BFCL v4 benchmark

全类别版本覆盖用户提供的 BFCL v4 快照：19个主数据文件、4696条源样本、23个逻辑类别（含格式敏感性），保留原 ID、工具、答案及执行环境。采用“中文用户问题 + 原始环境”条件，另保留与 de 对齐的132条五条件实验。翻译由 Codex 直接完成，不使用翻译 API、不运行模型评测。

**全量使用方式见 [FULL_SUITE_USAGE.md](FULL_SUITE_USAGE.md)**；类别与保留规则见 [BFCL_CATEGORIES.md](BFCL_CATEGORIES.md)。完整性以 `data/benchmarks/bfcl_full/validation.json` 为准，实际发布状态见 [RELEASE_READINESS.md](RELEASE_READINESS.md)。

```bash
python -m pip install --no-deps .
python -m multilingual_bfcl full-data-path
python -m multilingual_bfcl full-validate
```

下文的五条件和 `score` 命令专门用于132条配对实验子集，不代表全量各类别的执行器。

## 安装与数据

基础包无第三方运行依赖，Python 3.10+ 即可使用。wheel 包含英文源、中文五条件、翻译资产、许可证、来源说明和固定 BFCL 评分器；无需另装 BFCL 或下载数据。原 ZIP 的德语/希伯来语、WildToolBench 和历史日志不进入发布包。

从 `multilingual-bfcl` 目录安装源码：

```bash
python -m pip install --no-deps .
```

如果拿到已构建 wheel：

```bash
python -m pip install --no-deps multilingual_bfcl-0.2.0rc1-py3-none-any.whl
python -m multilingual_bfcl validate
python -m multilingual_bfcl data-path
```

安装后可在任意工作目录使用 `mbfcl` 或 `python -m multilingual_bfcl`。源 checkout 中未安装时，设置 `PYTHONPATH=src` 后也可运行。读取示例：

```python
from multilingual_bfcl.datasets import benchmark_path, load_jsonl

path = benchmark_path("bfcl_multiple", "zh-CN", "zh-CN_translatable_full")
rows = load_jsonl(path)
print(len(rows))  # 132
print(rows[0]["messages"][0][0]["content"])
```

## 五个实验条件

每个条件132条，以 `source_id` 对齐，总共660行配对输入；不能当作660个独立问题。

| benchmark 名称，不带扩展名 | 问题 | 工具描述 | 答案参数 |
|---|---|---|---|
| `zh-CN_translatable_query` | 中文 | 英文 | 原始值 |
| `zh-CN_translatable_full` | 中文 | 英文 | 本地化自由文本值 |
| `zh-CN_translatable_func_desc` | 原始英文 | 中文 | 原始值 |
| `zh-CN_translatable_full_func_desc` | 中文 | 中文 | 本地化自由文本值 |
| `zh-CN_translatable_full_lang_desc` | 中文 | 英文，增加语言提示 | 本地化自由文本值 |

英文基线使用 `--locale en --benchmark en_translatable`。两个重复问题文本组109/196、110/197仍然保留，完整工具输入不同。原 ZIP 德语文件只在源码 checkout 中用于对齐和回归对照。

每行字段：`id`（如 `multiple_2_zh-CN`）、`source_id`、`locale`、`localization_level`、嵌套轮次 `messages`、工具 `function` 和内联 `ground_truth`。`ground_truth` 是评分答案，不可作为模型输入。

`ground_truth=[{"country_info.capital":{"country":["巴西"]}}]` 中的列表表示可接受候选。模型实际调用应为 `{"country_info.capital":{"country":"巴西"}}`，不要把候选列表当成实际参数数组。数组和字典类型参数另有嵌套候选结构。

## 离线评分：已实现

预测文件为 JSONL，每条包含同一 benchmark 的精确 `id`，以及已解码的 `calls`：

```json
{"id":"multiple_2_zh-CN","calls":[{"country_info.capital":{"country":"巴西"}}]}
```

也支持 OpenAI `tool_calls` 格式：

```json
{"id":"multiple_2_zh-CN","tool_calls":[{"function":{"name":"country_info_capital","arguments":"{\"country\":\"巴西\"}"}}]}
```

评分：

```bash
mbfcl score --benchmark zh-CN_translatable_full --predictions predictions.jsonl --output-dir scores --name-style canonical --model MY_MODEL
```

OpenAI 工具名将点替换为下划线时使用 `--name-style api`。评分器直接读取所选文件的中文答案；不按模型名称切换答案，不调用旧的 BFCL 全局 runner，也不会执行模型生成的 Python 表达式。

协议为严格单次调用：错误函数、参数、类型、缺少必要参数或多余调用均不通过。未知/重复 ID 拒绝评分；缺失预测和记录为 `api_error` 的请求仍计入分母并判失败，不通过丢弃失败请求提高分数。只有一个预测时，标准整文件评分分母仍是132。输出 `scores.json` 含逐样本判定、准确率和输入哈希。

固定 checker 来自用户 ZIP 的 BFCL，评分逻辑保持原样，导入路径改变和轻量名称注册表见 [SOURCES.md](SOURCES.md)。它不是新实现的“近似 BFCL 分数”。原有恢复实验框架属于可选 legacy 工具，其宽松、多轮重试分数不得与本协议混报。

## 实际模型评测：等待 API 配置验证

基础包自带无第三方依赖的单次 HTTP runner，支持参数格式 `standard`、`reasoning`、`responses` 和 `claude`；**远端路由与部署兼容性仍需真实冒烟确认**。先复制 `.env.example` 为本地 `.env`，设置 `AZURE_OPENAI_ENDPOINT` 和 `AZURE_OPENAI_API_KEY`，不要提交或分享密钥。

不发请求的预览：

```bash
mbfcl evaluate --model YOUR_DEPLOYMENT --benchmark zh-CN_translatable_full --output-dir unused-preview --dry-run
```

用户确认模型部署和费用上限后，先跑一条：

```bash
mbfcl evaluate --model YOUR_DEPLOYMENT --model-type standard --env-file .env --benchmark zh-CN_translatable_full --output-dir runs/smoke-zh-full --limit 1
```

验证通过后将 `--limit 1` 改为 `--limit 0` 运行全部132条，并使用新的输出目录。`--locale` 和 `--benchmark` 切换条件。每条只发送一个请求，不自动重试；第一条 API 错误时立即停止，避免继续付费失败。运行目录已存在时拒绝混写，不自动 resume。

所有条件使用相同英文系统指令 `Use the supplied tools to answer the user request.`，不注入“用户使用中文”的额外提示；工具 schema 中的 `dict/float/tuple` 会转换为接口支持的 `object/number/array`。不发送答案或本地化标签。standard 使用温度0；其他类型省略不支持的温度字段。

输出包括：`selected_benchmark.jsonl`、`predictions.jsonl` 和 `scores.json`。1条冒烟分母是选中的1条；完整评测分母为132。报告同时记录完整源文件哈希与选中集哈希、模型/路由、请求预算、输出上限、系统提示和 API token usage。冒烟不代表整集 baseline。

第三方 OpenAI 兼容端点的具体路径/鉴权可能不同，需先核对部署；本机没有替用户配置可用服务，也未填入虚构成本或评分。

## 构建、审校与回归测试

在源码 `multilingual-bfcl` 目录运行：

```bash
python scripts/build_chinese_benchmark.py
python scripts/validate_chinese_benchmark.py
# 安装包后，或设置 PYTHONPATH=src 后：
python -m unittest discover -s tests -v
```

构建使用冻结翻译资产，不调用翻译 API。英文源哈希变化时拒绝自动重建，避免按旧描述顺序错配。结构验证、评分回归、打包安装验证分别记录，不互相替代。构造答案通过只是评分器检查，不能冒充真实模型准确率100%。

中文自然语言译值、枚举和技术 token 的区分、语言标签等语义例外见 [CHINESE_REVIEW.md](CHINESE_REVIEW.md)。已完成 Codex 第二轮审校；没有独立人类审校。QUERY 有意要求中文问题映射回原始参数；FULL 保留枚举、日期、标识符等固定 token，并非把所有字符串翻译成中文。

## 许可、引用和使用边界

遵循随包 Apache-2.0 [LICENSE](LICENSE)，保留 [NOTICE](NOTICE) 和 [来源及修改记录](SOURCES.md)。BFCL 官方[数据卡](https://huggingface.co/datasets/gorilla-llm/Berkeley-Function-Calling-Leaderboard)明确标注 Apache-2.0。此派生版本未获官方背书。

请同时引用上游 BFCL 和将来实际发布的中文版本；当前没有虚构的 GitHub 地址、DOI 或排行榜。132条可翻译样本不代表完整中文工具调用生态，也不覆盖多轮状态评测、真实工具执行或完整 BFCL。题目中的“当前”沿用源题，本任务评测函数选择及参数，不是检索今天的事实。
