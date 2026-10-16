# 完整 BFCL 范围与翻译原则

以用户 ZIP 中 `category_mapping.py` 注册的 BFCL v4 为准，不冒充今日上游最新版本。共23个逻辑类别，22个注册为计分类别，另有格式敏感性实验。19个主 JSONL 数据文件加1个格式选择 JSON；记忆和网页搜索各从一份题目展开不同运行条件。

| 组 | 类别 | 本快照样本规模 |
|---|---|---|
| 非Live单轮 | `simple_python`、`simple_java`、`simple_javascript` | 400、100、50 |
| 非Live工具选择与并行 | `multiple`、`parallel`、`parallel_multiple` | 各200 |
| 非Live不调用 | `irrelevance` | 240 |
| Live | `live_simple`、`live_multiple`、`live_parallel`、`live_parallel_multiple` | 258、1053、16、24 |
| Live相关性 | `live_irrelevance`、`live_relevance` | 884、16 |
| 多轮 | `multi_turn_base`、`multi_turn_miss_func`、`multi_turn_miss_param`、`multi_turn_long_context` | 各200 |
| 记忆 | `memory_kv`、`memory_vector`、`memory_rec_sum` | 同一155条分别在3个记忆后端运行，共465个条件实例 |
| 搜索 | `web_search_base`、`web_search_no_snippet` | 同一100条分别在有/无摘要条件运行，共200个条件实例 |
| 格式敏感性 | `format_sensitivity` | 200个已存在题目的ID选择及提示格式变体，不是额外200个独立问题 |

物理题目4696条；展开记忆/搜索条件后有5106个计分条件实例，不能与唯一问题数混淆。历史 `unused_datasets` 中的 REST、SQL、可执行调用等不在本快照当前注册的23类内。

`multiple` 是从多个候选函数中选择一个正确函数，不是“顺序调用多个函数”；`parallel` 才要求多个调用，`parallel_multiple` 将候选函数选择与多个调用结合。包内旧 TEST_CATEGORIES.md 对multiple的顺序调用描述不准确，应以数据及评分实现为准。

## 为什么原脚本标记有些“不可翻译”

原 `classify_benchmark.py` 的 `translatable_params` 只检查 **ground truth 参数值**，不检查整条用户问题能否翻译。数字、布尔值、日期、代码、路径和标识符通常没有语言变化，因此可以标记false；这不意味着中文测试必须删掉它们。

例如“Calculate the area of a triangle with sides 3, 4 and 5”可翻译为“计算边长为3、4、5的三角形面积”，参数仍保持3、4、5。若只研究“中文参数值与英文参数值的差别”，这条没有答案翻译对照；若研究中文理解与工具调用，它应保留。

原132条是ZIP中已有冻结子集，筛选分类CSV未随目录提供，不能据此宣称其余68条全部不可翻译。当前子集还包含一些只涉及数值的样本，进一步说明它不应被当成完整、可靠的可翻译性边界。

## 可翻译的层次

1. **用户问题**：几乎全部类别都可以做中文问题版；代码片段、引号内用于精确匹配的内容、路径、ID等应保留。
2. **工具/参数描述**：自然语言可以翻译，函数名、参数键、类型和枚举token应保持。Java和JavaScript中的字符串化程序表达式仍是代码，不是自然语言。
3. **自由文本答案**：可翻译，但必须与问题和允许答案同步；枚举或协议选择值不应翻译。
4. **多轮状态/记忆内容**：如果翻译文件正文、搜索词或预置记忆，必须同步所有引用、预期状态和答案。只翻译问题则保留这些原始状态，并明确是“中文问题、原始环境”条件。
5. **网页搜索与格式敏感性**：真实网页不会因题目翻译自动变中文；时间/事实锚点应保留。翻译系统提示本身是另一个实验条件，不可与仅翻译用户问题混为一谈。

## 当前全量扩展

按用户要求覆盖所有注册类别，不再按 `translatable_params` 删除样本。先构建语义较稳妥的 **全量中文问题条件**，保留原工具、答案、记忆前置对话和状态；原132条五条件继续保留为独立研究子集。不能将后者直接宣称覆盖全BFCL。

`data/benchmarks/bfcl_full/inventory.json` 是当前覆盖与缺口清单。翻译由Codex直接编写，不使用翻译API，不运行模型评测；缺失译文不会用英文占位后伪报完成。只有所有译文、ID、答案和配套资源校验通过后，才能把全量版标为完整并发布。
