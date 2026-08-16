# reader-overlay-compose · 阅读器浮层 Compose 化（S5 骨架）

> OpenSpec 功能概述。状态：🔄 设计中。

## 功能概述
将阅读页 ReadBookActivity 的 UI 壳（菜单层 + 浮层）逐步 Compose 化，实现**壳-核分离**与**弹层单态收敛**，正文引擎（page/ 29 文件）**零改动**（红线）。属 ui-redesign-m3 的 S5 阅读器浮层骨架样板页。

## 核心能力
- 菜单层 Compose 化：顶栏 MenuTitleBar + 底栏 MenuBottomBar + scrim，AnimatedVisibility 浮现 + 3s 自动淡出
- activeSheet 单态：sealed interface 全量枚举，一次一个弹层，杜绝 3 层嵌套
- 阅读设置 Sheet：字号/亮度/夜间/行距/对齐，SettingsCard 分组，滑块拖动实时预览
- ReaderUiState：轻量单 StateFlow 下发，替换散落 mutableBoolean
- BackHandler 优先级链：弹层→搜索→自动翻页→菜单路由→退出
- 正文零改动红线 6 条全程守住

## 文档索引
| 文档 | 说明 |
|------|------|
| [spec.md](./spec.md) | Intent / Scope / Approach / Requirements / Scenarios |
| [design.md](./design.md) | Technical Approach / ADR / Data Flow / File Changes |
| [tasks.md](./tasks.md) | 分阶段任务清单 + AOAdapt 日志 |

## 规格基础（引用不重复）
- [P2-reader.md](../ui-redesign-m3/pages/P2-reader.md)（v2 权威设计）
- [ui-standards.md](../ui-redesign-m3/ui-standards.md) §3.4（组件规格唯一真值）

## 状态
- [x] 现状源码分析（ReadBookActivity UI 壳/浮层/菜单/正文边界）
- [x] OpenSpec 四文档生成
- [ ] 检查点1：用户审查设计
- [ ] 实施（阶段1-4）
- [ ] 真机验证（FR-11）
