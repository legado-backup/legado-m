# legadoc-benchmark-analysis — 阅读C（legadoC）深度对标调研

> 状态：✅ 设计完成（tasks 全勾+七轮交叉验证闭环；AD-03~06 与分期顺序裁决经三轨总线编排检查点 1 一并裁决通过，2026-08-31；分期实施按 migration-designs 另立实施 spec 推进，编排见 master-track-orchestration）
> 生成日期：2026-08-30

## 功能概述

对 **CCSSNE/legadoC（阅读C，own 分支 v3.26.082723c）** 做源码级深度对标。legadoC 与本项目**血统不同**（阅读R/Archive 系 vs 本项目 Sigma 系）、**纯 View 体系 0 Compose**，是 fork 生态中"阅读页体验深度"路线的代表（朗读架构原语化/正文多媒体/番茄化 UI）。本 spec 独立于 ng-benchmark-analysis，但两者叠加性已验证（朗读原语化与 NG 多角色 TTS 正交）。

## 核心结论速览

| 域 | legadoC 优势 | 迁移分期 |
|----|-------------|---------|
| 朗读架构 | **原语化重构**（发布层 generation 防乱序/纯函数跟随/绘制期投影/EMA 预测换页）——本项目引擎直写显示+页级存储态高亮+死事件 | C1 |
| 多媒体插入 | 正文级插图/音频块/视频块全链（锚点+排版列+内嵌播放+EPUB sidecar）——本项目空白 | C2 |
| 合集书架 | BookCollection/Shortcut 双外键+虚拟 Book 模式+马赛克拼图+RowUi 发现页规则渲染 | C3 |
| AI 体系 | AI 净化规则沉淀（SHA-256 指纹幂等进替换体系）+创作工作台（生图模板协议）——本项目已有 AiImageService 执行层超集，legadoC 仅贡献编排层 | C4 |
| 工程纪律 | 用户日志模块勾选（classify 自动归属）/防泄露发布/产物验证门禁 | C5 |
| 即时修复 | **本项目 AnalyzeRule 缓存污染 bug**（legadoC ResolvedSourceRule 为解法）+并发去重+BookScriptObject+exploreKinds 缓存键+WebViewHtmlStore | C0 |

**本项目优势（保留不迁）**：网络层超集/视频套件/ai_tests/OpenSpec 治理/订阅搜索/高亮规则/自动任务/Compose 路线。
**legadoC 弱点**：0 Compose/无 CI 无 E2E 无沙箱/docs 漂移/DB schema 缺 3 快照。

## 文档索引

| 文档 | 内容 |
|------|------|
| [spec.md](./spec.md) | Intent/Scope/Approach（Alternatives+Drawbacks）/Requirements/Scenarios |
| [design.md](./design.md) | **总体设计**：8 维全景矩阵+双向优缺点+决策表 18 项+分期路线 C0-C5+AD-01~06 |
| [evidence-pack.md](./evidence-pack.md) | 8 轮分析统一事实源 |
| [tasks.md](./tasks.md) | 任务清单+AOAdapt 日志（含交叉验证轮记录） |

### 实施级迁移设计（migration-designs/，设计前置）

| 分期 | 文档 | 覆盖 |
|------|------|------|
| C0 | [C0-quick-fixes.md](./migration-designs/C0-quick-fixes.md) | 缓存污染 bug+并发去重+BookScriptObject+缓存键+HtmlStore |
| C1 | [C1-aloud-primitives.md](./migration-designs/C1-aloud-primitives.md) | 朗读架构原语化三步 |
| C2 | [C2-multimedia-illustration.md](./migration-designs/C2-multimedia-illustration.md) | 多媒体插入全链 |
| C3 | [C3-collection-shelf.md](./migration-designs/C3-collection-shelf.md) | 合集书架+RowUi |
| C4 | [C4-ai-purify-creation.md](./migration-designs/C4-ai-purify-creation.md) | AI 净化+创作图片链 |
| C5 | [C5-logging-engineering.md](./migration-designs/C5-logging-engineering.md) | 用户日志+工程纪律 |
