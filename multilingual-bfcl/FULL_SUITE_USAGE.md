# 中文 BFCL v4：全类别测试集使用说明

这是用户提供的 BFCL v4 快照的非官方中文派生数据。覆盖19个主数据文件、4696条源样本，以及格式敏感性选择表和全部配套参考资源。记忆与网页搜索展开为不同运行条件后有5106个计分实例；这些条件不是额外独立题目。具体类别数量见 [BFCL_CATEGORIES.md](BFCL_CATEGORIES.md)。

发布完整性以 `data/benchmarks/bfcl_full/validation.json` 的 `publishable` 为准。只有该值为 `true` 且安装包核验通过，才能宣称该制品具备全量数据发布条件。

## 安装并定位数据

需要 Python 3.10 或以上版本，基础包无第三方运行依赖。源码目录中运行：

```bash
python -m pip install --no-deps .
python -m multilingual_bfcl full-data-path
python -m multilingual_bfcl full-validate
```

也可以安装发布附件中的 wheel，再运行上述两个命令。`full-validate` 只检查数据覆盖、样本数量及内容哈希，不调用任何模型，也不产生模型能力分数。

```python
import json
from multilingual_bfcl.datasets import full_suite_path, full_category_path, load_jsonl

root = full_suite_path()
rows = load_jsonl(full_category_path("multi_turn_base"))
print(len(rows))  # 200
for turn in rows[0]["question"]:
    for message in turn:
        if message["role"] == "user":
            print(message["content"])

# 此文件是普通 JSON 选择表；其他主数据文件是每行一个对象的 JSONL，
# 为兼容原 BFCL 命名，其扩展名仍为 .json。
selector = json.loads((root / "BFCL_v4_format_sensitivity.json").read_text(encoding="utf-8"))
```

## 目录和字段

`bfcl_full/zh-CN/` 保持 BFCL 原生文件名与数据布局。`BFCL_v4_<category>.json` 保存问题；`possible_answer/` 保存参考答案；`multi_turn_func_doc/` 保存多轮工具文档；`memory_prereq_conversation/` 保存记忆前置对话。格式敏感性文件仅选择已有样本，不应再计为200道独立问题。

每个样本保留源 `id`。`question` 为“轮次 → 消息”的嵌套列表，消息可能包含 system 等角色，不能假设第一条消息必然是用户问题。根据 `role == "user"` 读取中文问题。工具定义、状态、依赖关系和其他字段保留原值。

向模型构造请求时只传入当前可见的对话、工具和环境信息。不要把 `possible_answer`、预期终态或评分答案放入模型输入。多轮、记忆和搜索必须使用其相应执行环境；将每条记录简单地当作独立单轮请求会改变任务定义。

## 中文化范围

全量版本是 **中文用户问题 + 原始工具与环境** 的条件：由 Codex 直接翻译用户自然语言，不使用翻译 API。保留数值、日期、函数名、参数键、枚举、路径、ID、代码、精确搜索词及要求写入的正文等必要字面量，以维持原答案和环境的可比较性。原文中的缺失参数、矛盾约束和无效日期也保留，不擅自修题。

少量输入原本就是中文，或者是纯代码、控制字符、无意义片段；它们原样保留，逐项理由见 `invariant_queries.json`。这不属于漏译。记忆内容、文件正文、工具描述和非用户消息仍可能为英文，因此不要将本条件描述为“整个执行环境均已中文化”。

原有132条 `multiple` 五条件实验继续存放于 `bfcl_multiple/`，用于分别研究问题、描述及自由文本参数本地化；它不是全量测试集，也不与全量样本数相加。

## 重建和检查

在完整源码包的 `multilingual-bfcl` 目录运行：

```bash
python scripts/build_full_suite.py
python scripts/validate_full_suite.py --require-complete
python scripts/run_release_tests.py
```

重建需要源码包中随附的原始 BFCL 快照。翻译资产是冻结的 source/中文批次与补充 TSV，按源文本 SHA-256 合并，缺失译文会使类别保持未完成。完整性检查验证 ID/顺序、样本和轮次数量、角色、原工具/状态/参考资源及技术字面量。`inventory.json` 记录源文件摘要，`build_status.json` 记录输出摘要。

本发布不包含真实模型评测结果或排行榜，也不声称已验证所有上游模型执行后端。包内现有 `score` 命令仅适用于132条单轮实验子集；全量各类别的模型运行与计分应接入相应 BFCL v4 运行器。数据集完整性不等于某模型得分有效。

## 来源、许可和引用

数据源自 [Gorilla/BFCL](https://github.com/ShishirPatil/gorilla/tree/main/berkeley-function-call-leaderboard)，锁定于用户所提供 ZIP 的本地内容哈希，不能视为当前上游最新版。上游许可证为 Apache-2.0，随包提供 LICENSE、NOTICE；详细来源和修改说明见 [SOURCES.md](SOURCES.md)。请同时引用上游 BFCL 和所使用的中文发布版本。

中文翻译与复核由 Codex 完成，未声称独立人类审校。发现译文问题时，请报告类别、源 ID、用户消息轮次、原文/译文及建议；保留固定技术标识符，不直接修改参考答案来掩盖翻译问题。
