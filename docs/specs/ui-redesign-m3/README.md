# UI 重构设计（对标开源 fork 生态 · M3 设计语言 · 全量页面 Compose 化）

## 状态

🔄 **开发中**（设计 v2 已完成全面修订 · ADR 01-22 · 实施 Phase0-3 已落地，Phase4-5 待执行）

> **本 spec 的最终目标：前端全部 Compose**（工程级标准规范，能指导后续任意页面改造）。边界：阅读器正文引擎/漫画/音频/WebView 池/代码编辑器（sora）/相机扫码等**内核与第三方控件保留原生 View，用 Compose 做页面壳与浮层**（AD-02）。现有实施进度：Phase0 组件库（19 文件）、Phase1 主题 34 槽位、Phase2 我的页、Phase3 书架 Compose 化已真机验证；Phase4 阅读器浮层 Sheet 化、Phase5 全 App 一致性巡检待执行。
>
> **v2 完善内容（2026-08-11）**：新增 [`pages-inventory.md`](./pages-inventory.md)（全量 84 页面类功能点核对表，保证"核心功能一个不漏"）与 [`ui-standards.md`](./ui-standards.md)（前端 UI 工程规范：6 类页面骨架 / 组件六族接线计划 / 状态管理范式 / 三态规范 / 页面改造检查清单 / 验收 KPI），并将四文档范围从"8 类核心页"扩至全量页面。真机功能点覆盖测试随每页 Compose 化强制执行。

## 功能概述

以 `# DESIGN-MD` 设计规范为纲，深度对标 33 个已下载 Legado fork 的 UI 设计资产（HapeLee MD3、legadoT 种青色引擎、legados/Suml-1 换肤体系、Jingshiro 低风险 MD3 token、MoRealm 墨境纯 Compose 工程标杆等），重构 Legado 的视觉与交互体系。**100% 保留业务功能**（书源引擎/JS 编辑器/净化规则/RSS/WebDAV/本地书/备份恢复），只动布局、控件样式、交互路径。

- **全量页面清单**：`pages-inventory.md` 登记全部 84 个页面类的功能点，逐页 Compose 化时逐项核对，**核心功能一个不漏**。
- **统一工程规范**：`ui-standards.md` 定义 6 类页面骨架（主框架Tab/列表管理/表单编辑/详情阅读/全屏沉浸/弹窗透明窗），所有页面复用统一骨架与组件，**杜绝每页独立风格**。
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
| 全量 Compose 迁移路径 | 页面壳/浮层/列表/弹窗全 Compose；正文引擎/第三方控件保留原生 View（AD-02/AD-20） |
| 页面工程规范 | `ui-standards.md`：6 类骨架模板 + 组件六族复用规则 + 状态范式 + 三态 + 改造检查清单 |
| 全量页面清单 | `pages-inventory.md`：84 页面类功能点核对表 + 迁移路线图 + 真机覆盖状态 |
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
| [design.md](./design.md) | Technical Approach / 用户旅程状态机 / ADR 01-22（Y-Statement）/ Data Flow / File Changes |
| [frontend-synthesis.md](./frontend-synthesis.md) | **整体前端思想综合** ⭐权威：五支柱收敛、五仓贡献矩阵、整体架构图、功能不裁剪红线清单、实施 Phase 0~5 |
| [implementation-spec.md](./implementation-spec.md) | **实现细化规格** ⭐开发支撑：17 组件签名、主题 toM3Scheme 代码映射、真实文件锚点、PR 粒度任务+KPI、themeConfig 格式封口 |
| [pages-inventory.md](./pages-inventory.md) | **全量页面清单** ⭐v2新增：84 页面类功能点核对表 + 技术栈/骨架/优先级 + 迁移路线图 + 真机覆盖状态 |
| [ui-standards.md](./ui-standards.md) | **前端 UI 工程规范** ⭐v2新增：6 类页面骨架模板 / 组件六族接线计划 / **§3.4 组件规格真值表（唯一真值）** / 状态管理范式 / 三态规范 / 页面改造检查清单 / 验收 KPI |
| [pages/](./pages/) | **分页面详细设计文档**（每页一册，见下方"分页面设计文档"） |
| [background/](./background/) | **学习笔记（背景参考，非开发依据）**：forks-deep-dive（33 forks 清单）、morealm-deep-dive（墨境）、four-fork-deep-dive（四 Fork）——开发时以 ui-standards §3.4 规格书 + pages/ 页面文档为准，本目录仅供溯源借鉴来源 |
| [audit-wired-components.md](./audit-wired-components.md) | **已接线组件规格审计**（2026-08-13 已定案收敛）：5 项已接线（S1/S2/S4/Phase4/S6）对照 §3.4 规格书逐项对账，违例清单含明确修复决策 |
| [audit-lightweight-docs.md](./audit-lightweight-docs.md) | **轻量文档质量审计**（2026-08-13）：43 份轻量文档逐份审计，task 占位符已全部回填精确 task 号 |
| [app-icon-design.md](./app-icon-design.md) | **App 图标改版设计依据**（D-4，2026-08-16）：adaptive icon 现代化 / M3 对齐 / monochrome 主题图标 / 资源清单 / D-14③ launcherIcon 残留收尾 |

> **开发依据分层**：开发某页面时，**只读 `pages/P{编号}.md`（页面设计）+ `ui-standards.md` §3.4（组件规格）**，禁止到 background/ 学习笔记里自创样式（避免"学习开源项目导致设计文档杂乱无章"）。background/ 仅当需要追溯某规格的 fork 来源时查阅。

## 分页面设计文档

> 每页（骨架级/核心页）一份完整 v2 设计文档放 `pages/`；其余子页轻量文档按 `pages/_light-template.md` 编写。详见 ui-standards §10 索引表 + pages-inventory 归属。

| 文档 | 页面 | 骨架 | 状态 |
|------|------|------|------|
| [pages/P9-main.md](./pages/P9-main.md) | 主框架 MainActivity | S1 | ✅ v2 样板 |
| [pages/P1-bookshelf.md](./pages/P1-bookshelf.md) | 书架 Bookshelf | S2 | ✅ v2 |
| [pages/P2-reader.md](./pages/P2-reader.md) | 阅读器 ReadBook | S5 | ✅ v2 |
| [pages/P3-bookinfo.md](./pages/P3-bookinfo.md) | 书籍详情 BookInfo | S4 | ✅ v2 |
| [pages/P4-my-config.md](./pages/P4-my-config.md) | 我的/设置 My+Config | S2 | ✅ v2 |
| [pages/P5-booksource.md](./pages/P5-booksource.md) | 书源管理 BookSource | S2 | ✅ v2 样板 |
| [pages/P6-explore.md](./pages/P6-explore.md) | 发现 Explore | S2 | ✅ v2 |
| [pages/P7-rss.md](./pages/P7-rss.md) | 订阅源 Rss | S2 | ✅ v2 |
| [pages/P8-overlays.md](./pages/P8-overlays.md) | 浮层/弹窗族 | S6 | ✅ v2 |
| [pages/P10-booksource-edit.md](./pages/P10-booksource-edit.md) | 书源编辑 BookSourceEdit | S3 | ✅ v2 样板 |

### 子页轻量文档（pages/light/，继承对应族文档规格）

> 轻量文档只写「继承 + 差异」，继承族文档见文件名前缀；完整清单见 ui-standards §10.3 档位矩阵。

| 功能域 | 轻量文档 |
|--------|---------|
| A 书架/主框架 | L-A5-base-bookshelf |
| B 阅读器核心 | L-B2-toc、L-B3-bookmark、L-B4-highlight、L-B5-all-bookmark、L-B7-bookinfo-edit、L-B8-bookshelf-manage、L-B9-import-book、L-B10-cache、L-B11-search、L-B12-manga、L-B13-audio、L-B14-explore-show、L-B15-storage-manage、L-B16-txt-toc-rule |
| C 书源/规则/工具 | L-C3-booksource-debug、L-C4-replace-rule、L-C5-highlight-rule、L-C6-dict-rule、L-C9-file-manage、L-C10-download-manage、L-C11-url-record、L-C12-recycle-bin、L-C13-source-login、L-C15-image-gallery、L-C16-auto-task、L-C17-welcome、L-C19-debug-tools、L-C20-about-record |
| D RSS/订阅 | L-D2-rss-source-edit、L-D3-rss-source-debug、L-D4-rss-articles、L-D5-rss-search、L-D6-read-rss、L-D7-rss-favorites、L-D8-rule-sub、L-D9-video-player |
| E 配置子页 | L-E1-backup-config、L-E2-theme-config、L-E3-cover-config、L-E4-other-config、L-E5-precise-manage、L-E6-welcome-config |

> 完整 84 页归属 + 子页轻量文档清单见 ui-standards §10 与 pages-inventory.md。

## 状态标记说明

- 🔄 开发中：设计阶段已通过三次强制评审；实施 Phase0-3 已落地并真机验证，Phase4-5 待执行
- 全部 Phase 完成后：更新为 "✅ 已完成"，并在 docs/INDEX.md 登记归档

## 交付要求落实

对每一个页面文档输出：① 布局结构（文字框图，说明每块组件）② 交互流程（点击/长按/手势触发）③ Compose 组件实现思路（复用公共组件优先）④ 绘图 Prompt（供生成页面效果图）。