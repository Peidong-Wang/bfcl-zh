# BFCL 中文测试集

非官方 BFCL v4 中文问题派生版本，锁定用户提供的源快照。完整保留19个主数据文件中的4696条源样本、所有ID与轮次，以及格式敏感性选择表和33个参考资源文件。23个逻辑类别包含格式敏感性；记忆与搜索展开后为5106个计分条件实例。

全量条件为“中文用户问题 + 原始工具与环境”。4826条去重用户消息已覆盖；代码、固定技术标识符、精确参数和原样例外有追踪记录。由 Codex 直接翻译并复核，没有使用翻译API、没有运行模型评测，也没有独立人类审校声明。

## 安装和读取

需要 Python 3.10+；基础运行无第三方依赖：

```bash
cd multilingual-bfcl
python -m pip install --no-deps .
python -m multilingual_bfcl full-data-path
python -m multilingual_bfcl full-validate
```

`full-validate` 仅核验数据，不调用模型。也可直接解压发布附件 `bfcl-v4-zh-CN-dataset.zip`，按 BFCL 原生目录读取其中的 `zh-CN/`。主文件保留上游 `.json` 文件名，内容为 JSONL；格式敏感性文件是普通 JSON 选择表。

- [详细使用说明与重建命令](multilingual-bfcl/FULL_SUITE_USAGE.md)
- [全部类别与翻译边界](multilingual-bfcl/BFCL_CATEGORIES.md)
- [来源与许可](multilingual-bfcl/SOURCES.md)
- [审校记录](multilingual-bfcl/CHINESE_REVIEW.md)
- [全量完整性报告](multilingual-bfcl/data/benchmarks/bfcl_full/validation.json)
- [安装包验证](multilingual-bfcl/PACKAGING_VALIDATION.json)

## 源码布局

`multilingual-bfcl/` 包含 Python 包、中文数据、翻译资产、文档和离线测试；`berkeley-function-call-leaderboard/bfcl_eval/` 只保留重建和校验所需的原始快照资源与五个评分源码文件。历史日志、密钥、WildToolBench 和其他语言数据不纳入此发布仓库。

源码仓库文档入口：[完整使用说明](multilingual-bfcl/FULL_SUITE_USAGE.md)、[类别说明](multilingual-bfcl/BFCL_CATEGORIES.md)、[来源](multilingual-bfcl/SOURCES.md)、[发布状态](multilingual-bfcl/RELEASE_READINESS.md)。

原132条 `multiple` 配对实验独立保留，不与全量样本相加。包内 `score` 命令仅支持该子集；全量各类别执行与计分需接入对应 BFCL v4 环境。此仓库不发布模型分数。

Apache-2.0。请同时引用 [上游 BFCL](https://github.com/ShishirPatil/gorilla/tree/main/berkeley-function-call-leaderboard) 和使用的中文发布版本。推广网页：https://bfcl-zh.peidong-wang.chatgpt.site（访问权限以实际托管设置为准）。
