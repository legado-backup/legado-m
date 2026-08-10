# UI 重构设计（对标开源 fork 生态 · M3 设计语言）

## 状态

✅ 设计完成（19 文件 · ADR 01-18 · 经三轮评审确认）→ 实施待另立项

> 本次交付范围 = **完整 UI 重构设计文档**（含每页四要素设计、与业务隔离边界、整体前端思想综合、实现细化规格），**不含代码实现**。设计阶段已通过三次强制评审，实施 Phase 0~4 规格见 [`implementation-spec.md`](./implementation-spec.md)。

## 功能概述

以 `# DESIGN-MD` 设计规范为纲，深度对标 33 个已下载 Legado fork 的 UI 设计资产（HapeLee MD3、legadoT 种青色引擎、legados/Suml-1 换肤体系、Jingshiro 低风险 MD3 token 等），重构 Legado 的视觉与交互体系。**100% 保留业务功能**（书源引擎/JS 编辑器/净化规则/RSS/WebDAV/本地书/备份恢复），只动布局、控件样式、交互路径。

- **阅读优先**：阅读器正文文字区域最大化，操作 UI 仅在需要时浮出。
- **交互升级**：高频操作 ≤2 步到达；弹窗改 BottomSheet；长按唤起快捷菜单。
- **视觉改版**：Material 3 柔和护眼 / 磨砂顶栏 / 卡片 18dp 圆角 / 按钮 12dp / 大量留白。
- **三套主题 + 暗紫保留**：浅色米白、暖黄护眼、纯黑深色三套收敛配色；**保留现状"暗夜紫"默认暗色主题**（目标仓库 `themeConfig.json` 第 12 条已内置 `#7B1FA2 / #CE93D8 / #1E1E32`）。
- **栅格体系**：基准 360dp / 安全边距 16dp / 间距档位 4/8/16/24/32 / 触控 ≥48dp。

## 核心能力

| 能力 | 说明 |
|------|------|
| 设计 Token 体系 | 一套 color/spacing/radius/typography token，同时服务 View 与 Compose |
| ThemeStore→M3 桥接层 | 复用现有 `ui/theme/LegadoTheme.kt`（与 legados 系 fork 同构），单一主题权威源 |
| Compose 渐进迁移路径 | 新 UI 层 Compose，正文引擎保持原生 View（AndroidView 包嵌） |
| 页面设计文档 | 每页四要素：骨架层平台(文字框图) / 交互流程 / Compose 组件思路 / 绘图 Prompt |
| 三套主题+暗夜紫 | 米白/暖黄/纯黑 + 保留现状暗紫 |

## 对齐参考（fork 生态）

| Fork | 借鉴点 |
|------|--------|
| HapeLee legado-with-MD3 | Monet 动态取色 + 12 预设色板双引擎、339 个 Compose 文件、Sealed 37 阅读浮层单渲染、SharedTransition+圆角过渡 |
| 325506_legado-with-MD3-DIY | OldThemeConfig 旧 JSON 兼容层、BookCoverSharedElement key="book-cover:$url" |
| legadoT | Hct 种子→M3 30+ token 引擎、背景色「锚定中性面」5 级 surfaceContainer、15 套中式主题预设、藕荷雅紫 seed |
| legados / legado-archive / Rimchars | `ThemeStore` 喂 `M3 ColorScheme` 的桥接法（与目标实现同构）、liquid glass 液态玻璃 |
| Suml-1_Legado_Max / youfengnoGht | 主题 zip 一键换肤（ApplicationThemeManager）、高亮 Canvas 五线下划线 + HighlightPresetRule 预置规则 |
| Jingshiro | 不引 Compose、XML 13 个 md3_* token、语义色改别名达成"骨架级 MD3 皮肤" |
| **MoRealm（墨境）** ⭐现代工程标杆 | 纯 Compose+M3+Navigation+Hilt；主题实体 5色→34槽位推导（平滑换肤动画不学）；PillNavigationBar 悬浮胶囊底栏；SettingsSection/SettingsCard/SettingRow 三套设置模板；shimmer 骨架屏/SwipeBackEdge/ThemeSnackbarHost；阅读器 9宫格手势+目录书签双Tab底部面板 |

## 文档索引

| 文档 | 内容 |
|------|------|
| [spec.md](./spec.md) | Intent / Scope / Approach（含 Alternatives + Drawbacks）/ Requirements / Scenarios |
| [design.md](./design.md) | Technical Approach / 用户旅程状态机 / ADR 01-14（Y-Statement）/ Data Flow / File Changes、每页四要素设计正文 |
| [forks-deep-dive.md](./forks-deep-dive.md) | **33 forks 深度学习清单**：学了什么、源码佐证（真实路径）、迁移评级 ★1-5 |
| [four-fork-deep-dive.md](./four-fork-deep-dive.md) | **四 Fork 前端对标**（HapeLee/legados/Rimchars/legado_NG）+ 鸿蒙版三级布局方案 + 组件化清单 + 原版痛点对照 |
| [morealm-deep-dive.md](./morealm-deep-dive.md) | **Morealm 墨境深度学习**（纯 Compose 现代架构标杆）：导航/主题 5色→34槽位/设置双范式/PillNavigationBar/阅读器/组件 Top10 |
| [frontend-synthesis.md](./frontend-synthesis.md) | **整体前端思想综合** ⭐权威：五支柱收敛、五仓贡献矩阵、整体架构图、功能不裁剪红线清单、实施 Phase 0~4 |
| [implementation-spec.md](./implementation-spec.md) | **实现细化规格** ⭐开发支撑：17 组件签名、主题 toM3Scheme 代码映射、真实文件锚点、PR 粒度任务+KPI、themeConfig 格式封口 |
| [tasks.md](./tasks.md) | 设计文档产出的任务清单 + AOAdapt 日志 |
| [pages/](./pages/) | 分页面四要素设计文档（每个核心页面一册） |

## 状态标记说明

- 🔄 设计中：本文档为设计交付，实施代码不在本次范围内
- 设计审查通过后：更新为 "✅ 设计完成"，实施另行立项

## 交付要求落实

对每一个页面文档输出：① 布局结构（文字框图，说明每块组件）② 交互流程（点击/长按/手势触发）③ Compose 组件实现思路（复用公共组件优先）④ 绘图 Prompt（供生成页面效果图）。