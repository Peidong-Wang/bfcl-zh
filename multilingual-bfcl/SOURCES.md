# 来源、许可和修改说明

核查日期：2026-10-16。本发布分发 BFCL v4 全部19个主数据文件的4696条中文问题样本、格式选择表、33个配套参考文件，以及原132条英文源样本和中文五条件。原压缩包的 WildToolBench、德语/希伯来语翻译、批处理任务记录和历史实验日志不进入新 wheel。德语仅在原 checkout 中用作方法和离线回归对照。

全量来源逐文件 SHA-256 记录在 `data/benchmarks/bfcl_full/inventory.json`。输出及配套参考资源摘要在 `build_status.json`，ID、轮次、状态和字面量核验在 `validation.json`。全部用户文本以源内容 SHA-256 去重组织翻译；重复样本仍保留全部原始 ID。只修改 user 消息的自然语言，其他消息、工具、答案和执行状态保持原值。原样保留项逐条记录在 `invariant_queries.json`。

## 原始输入与内容锁定

直接输入是用户提供的 `multilingual-tool-use-evaluation-main.zip`，SHA-256 为 `cac7509126cd983488461fca7b49a4ec63a372e0c24657bd76c397d03263df70`。没有上游 Git 元数据，因此不编造原压缩包的作者、仓库地址或提交号。原包声明 Apache-2.0，许可证保留在发布包 `LICENSE`。

英文输入 `en/en_translatable.jsonl` 的 SHA-256 为 `badafe2952c617167d1c71d572562a5f588475d028f15c463883b947cb44146d`。已逐条核对：132条的问题、工具定义和答案，均与压缩包内 BFCL 原始 `multiple` 数据按 ID 连接后完全一致。列选择仅将 `question` 重命名为 `messages`，并内联答案。

对应原始文件内容哈希：

| 文件 | SHA-256 |
|---|---|
| `BFCL_v4_multiple.json` | `aef168155ebd74b7ac2401198b201343bc7d16d7a3d7e0d4e6d8ee82c6969b2a` |
| `possible_answer/BFCL_v4_multiple.json` | `244e00ce9395df948bcafc7bee64e8f9c87ef70887587d83cae45b13699f3047` |

公开上游为 [Gorilla/BFCL 源码](https://github.com/ShishirPatil/gorilla/tree/main/berkeley-function-call-leaderboard) 和 [Gorilla 团队发布的数据卡](https://huggingface.co/datasets/gorilla-llm/Berkeley-Function-Calling-Leaderboard)。数据卡明确标记 `apache-2.0`，源码仓库提供 [Apache-2.0 LICENSE](https://github.com/ShishirPatil/gorilla/blob/main/LICENSE)。这些网页用于核对来源与许可声明；本次评分和数据内容锁定于用户 ZIP 的哈希，**不声称与今天的上游 main 逐字节相同**。

132条是原 ZIP 已筛选的冻结 ID 集。原始筛选脚本引用的分类和人工修订 CSV 不在该目录中，因此本发布复现的是这个固定子集，不能声称重现原作者的分类模型流程。`PROVENANCE.json` 保存每个 source_id 和输入内容摘要。

## 评分代码

`src/multilingual_bfcl/_vendor/bfcl/` 包含压缩包中 BFCL AST checker、类型转换器及枚举的五个文件。仅把导入前缀替换为本地命名空间；其余评分函数逻辑不变。`SNAPSHOT.json` 记录原文件与分发文件哈希，单元测试比较 AST，证明评分函数未被重写。

新增的轻量 `constants/model_config.py` 仅提供 `underscore_to_dot` 两个布尔配置：canonical 原名与 API 下划线名，替代原来导入所有推理提供方的全局模型注册表。适配器、资源读取、CLI、请求构造、打包和测试是本次新增代码。它们不代表上游提供或认证的实现。

## 中文修改与审校

问题、自由文本答案和描述由 Codex 生成并进行第二轮逐项审校；不是 de 原翻译服务的复跑，也没有聘请独立人类审校者。详细范围、修订和源数据歧义见 [CHINESE_REVIEW.md](CHINESE_REVIEW.md)。固定技术 token、枚举、键、数值和日期；翻译规则例外显式记录。修改后的生成文件哈希保存在 `zh-CN/build_manifest.json`。

## 不分发的数据

原 ZIP 的 WildToolBench 派生数据属于另一个来源：[官方项目](https://github.com/yupeijei1997/WildToolBench)。本次不依靠它来证明 BFCL 数据的许可，也不将它、服务元数据或旧推理日志纳入新发布包。此前本地修复的 WildToolBench JSONL 仍留在原 checkout 中供用户使用。

## 引用与范围

本项目是非官方中文派生数据，覆盖本快照全部注册类别并保留 `multiple` 配对子集，不冒用 BFCL 官方身份，不发布未经实测的排行榜。上游数据卡列出的 BFCL 作者为 Fanjia Yan、Huanzhi Mao、Charlie Cheng-Jie Ji、Tianjun Zhang、Shishir G. Patil、Ion Stoica 和 Joseph E. Gonzalez（2024），请同时引用[原始 BFCL 项目](https://gorilla.cs.berkeley.edu/blogs/8_berkeley_function_calling_leaderboard.html)。中文版本正式发布地址和版本号确定后，再追加派生版本引用。
