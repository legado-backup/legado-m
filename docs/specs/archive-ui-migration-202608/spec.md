# Archive 前端 UI 迁移整合 — 需求规格（spec.md）

> 修订 v2（2026-08-19）：基于最新 tag `archive-v3-3.26.08172114` 深度分析（5 份 rev2 报告）与用户 4 项调整意见（阶段划分 / 特色功能范围 / 迁移基座方向 / 差异分析质疑）重写。

## Intent

本项目将 `app/src/main/java/io/legado/app/ui/` 前端 UI 层从"本项目自研增量 Compose 化"改为"整体迁移阅读Archive（[Rimchars/legado]）的 UI 层"。

- **为什么**：本项目耗时约半个月的自研 Compose 迁移进度慢、遗留大量未改项与回归 bug，而 Archive 的 UI（Compose 化管理页、重做主题系统、阅读器、漫画、订阅源页）已成熟精美。
- **前提**：两端同源 fork 自 Luoyacheng/legado-E，后端 `model/webBook` 公开 API 11/12 完全一致、基类/ViewModel 基类链逐字节一致；ARCHIVE UI 的 ViewModel 后端依赖在 OURS 几乎全部存在——已由基于最新 tag 的深度预研证实（见 design.md + rev2 报告）。
- **必须**：完整保留本项目特色能力（视频/图片播放器 + 嗅探 + 上下滑动、RSS 全局搜索、分组编辑、高亮），保留个人项目标识。
- **边界**：以独立项目思路实施，本次不向 Archive 上游提交合并申请（用户备用方案，仅当独立方案受阻时考虑）。

## Scope

### 在范围内（In Scope）

1. **Cronet 升级** `150.0.7871.128` → `500.0.1`，去除 `app/cronetlib/` 本地内部打包，改用 Maven 构件（**方案 1 `cronet-bundled`，用户已确认**），减小 APK 体积。
2. **Archive 前端 UI 整体搬迁**：按模块替换本项目 UI（主界面 / 书架 / 发现 / 我的 / 订阅 / 书源管理 / 搜索 / 详情 / 目录 / 阅读页 / 配置页）。**完整搬入**（用户已确认），不裁剪核心页面。
3. **地基补齐（Phase 0）**：搬入 Archive UI 编译硬约束所需的 4 个 Compose 生态依赖（miuix / reorderable / lazyColumnScrollbar / liquidglass）+ 2 个缺失工具类（`SearchBookMergeUtils` / `VideoBookPreloader`）+ 后端接口扩展（`WebViewPool.Scope` 枚举）。
4. **后端支撑增量搬入**：Archive UI 依赖而本项目缺失的后端（`AppCloudStorage` + `lib/cloud`、EPub Core 新引擎、主题引擎配套、新增 Room 实体 + DAO、`ReadBook` 新方法、`BookDao.flowShelf*` 系列）。
5. **主题系统整合**：采用 Archive 主题系统（32 字段 ThemeConfig + ~68 PreferKey + `ThemeRuntimeKeys` + `ThemeUiPalette` / `UiCorner` / `ComposeUiCorner` / `UiTypography` + `ThemePackageManager` / `AppearanceKitManager`），兼容本项目存量主题数据；**`themeMode` 默认值跟随 Archive 语义（"0"跟随系统，用户已确认）**。
6. **数据库迁移链合并**：以本项目 v104 为基座，增量并入 Archive 独有 25 实体（5 批迁移 → v108），保留本项目 9 特色实体，保证覆盖安装升级路径。
7. **本项目特色功能整合**：视频播放器（抖音风格 + 前置嗅探 + 预加载）、图片播放器、RSS 订阅源全局搜索、发现/订阅分组编辑、高亮体系等在新 UI 上完整可用。按 **P0/P1/P2 分级**（用户调整后范围：P0 视频/图片/全局搜索为核心必保，P1 分组编辑/高亮，P2 漫画/规则订阅/分组封面复用等价）。
8. **前端 UI 标准建设**：迁移过程中沉淀 `docs/project-flow/ui-standards/`（组件目录 / 取色规范 / 间距圆角规范 / 页面骨架规范 / 迁移登记表）。
9. **项目标识还原**：应用名称、logo、仓库地址、开发者信息改回本项目。
10. **Archive 重 AI 功能完整搬入（用户已确认，替代原"仅建表保编译"默认）**：AI 助手 / AI 记忆 / AI Agent / AI 绘图 / 角色 / 朗读 BGM / 段落规则 等的 **25 实体 + 14 DAO + 业务逻辑 + UI 入口全部搬入**，不做裁剪；`help/ai/*` 全量业务与 `ui/book/character/*`、`AiChatActivity` 等对应页面一并搬入。
11. **搬迁后单元测试门禁（用户附加要求）**：每个关键模块搬迁完成后，必须针对其核心功能编写并运行单元测试（`./gradlew test`），迁移后行为与预期一致、不依赖真机即可发现回归；单元测试通过为该模块"完成"的前置条件。

### 不在范围内（Out of Scope）

- ❌ 不迁移 Archive 的 `modules/web` 前端（本项目 Web 前端保留现状，仅做接口对齐）。
- ❌ 不向 Archive 上游提交合并申请（独立项目实施；备选方案触发条件另行评估）。
- ❌ 不删改本项目 `modules/book`、`modules/rhino`（两端一致，直接沿用）。

## Approach

### Selected Approach：以本项目为 git 基座 + Archive UI 分层搬入 + 独立项目实施

**基线选择（用户调整意见：迁移基座方向）**：git 历史、远程仓库、数据库迁移链均以本项目为基座（本项目为存量事实标准，覆盖安装升级路径清晰）。本次**独立项目实施**，不混入 Archive 的 git 历史；以 Archive 最新 tag `archive-v3-3.26.08172114` 源码作为 UI 蓝本（解决差异分析质疑——v1 分析基于旧 master 快照，已重做为最新 tag）。

**迁移粒度（用户调整意见：阶段划分调整）**：不一次性整目录替换（diff 失控、无法编译验证），调整为 **10 阶段流水线**——Phase 0 地基（编译硬约束先行，保证后续可编译）→ Phase 1 后端支撑 → Phase 2 主题系统 → Phase 3 数据库 → Phase 4 UI 基建 → Phase 5 核心页面 → Phase 6 特色整合 → Phase 7 UI 标准 → Phase 8 项目标识 → Phase 9 验证交付。每层编译门禁 + 验证。

**特色保留（用户调整意见：特色功能范围调整）**：本项目特色后端与特色 UI 文件保留，按 P0/P1/P2 分级整合（P0 视频/图片/全局搜索必保；P1 分组编辑/高亮；P2 漫画/规则订阅/分组封面复用 Archive 等价能力），特色 UI 外观统一接入 Archive 的 Compose 组件库。

**可行性依据（rev2 预研结论摘要）**：
- 后端 `model/webBook`（WebBook 公开 API）12 个公开方法 **11 个签名完全一致**，仅 `exploreBook/exploreBookAwait` 多 2 个参数（`webViewPoolScope`/`shouldBreak`）
- 基类 `base/` 9 文件同名同构，`BaseViewModel`/`VMBaseActivity`/`VMBaseFragment` 逐字节一致
- 抽查 7 个 ARCHIVE 核心 ViewModel，其搜索/书源/阅读后端依赖（SearchModel/WebBook/ReadBook/LocalBook/BookHelp/AnalyzeUrl 等）**OURS 几乎全部存在**
- **编译硬约束仅 3 个点**（`SearchBookMergeUtils` / `VideoBookPreloader` / `WebViewPool.Scope`）+ 4 个 Compose 生态依赖；另 `ReadBook` 新方法、缺失 DAO/实体、主题系统为"随功能搬入"的中等工作量
- 导航无 Router，两端同为 `startActivity<T>()` 扩展 + putExtra + ActivityResult + LiveEventBus

**主要缺口**（= 搬入工作量，详见 design.md + rev2 报告）：
1. 编译硬约束：2 工具类 + 1 接口枚举 + 4 Compose 依赖（小，Phase 0）
2. 后端：`ReadBook` 新方法（reloadCurrentContent 等 10 个）、`BookDao.flowShelf*` 系列、`AppCloudStorage` + `lib/cloud`、epubcore、config 新类（中）
3. 主题：32 字段 ThemeConfig + ~68 PreferKey + `lib/theme` 六件套 + 主题包/外观套件（中）
4. 数据库：Archive 独有 25 实体 + DAO + 5 批迁移（中）
5. UI 基建：`ui/widget/compose/*` 全量组件库（与 OURS `widget/components` 两套并存隔离）（中）

### Alternatives Considered

| 方案 | 描述 | 否决理由 |
|------|------|---------|
| **A. 以 Archive 为基座，反向注入本项目特色** | 直接以 Archive 代码库为主干，把本项目特色后端/实体/迁移链注入 | ①本项目 git 历史与远程将丢失/需重建；②数据库迁移链以 Archive v109 为准，本项目存量用户（v104）升级路径需逆向合并，风险高；③本项目特色实体注入 Archive 迁移链更复杂；④项目标识全部需重改 |
| **B. 一次性整目录替换 `ui/`** | 直接 `cp -r archive/ui` 覆盖，再修编译错误 | ①单次 diff 数千文件，编译错误成百上千，无法有序验证；②主题/后端缺失类会导致编译全面失败；③违反"每阶段构建复验"门禁 |
| **C. 继续自研 Compose 迁移（现状）** | 维持当前增量 Compose 化路线 | 用户明确否决：半月余进展缓慢、遗留大量未改项与回归 bug，页面风格仍不及 Archive |
| **D. 只搬 Archive 的 XML/View 版 UI（不搬 Compose 页）** | 只迁入 Archive 非 Compose 的经典 UI | Archive 的 UI 价值主要体现在 Compose 化页面，退而求其次无法达到用户期望 |

### Drawbacks（选定方案的已知缺点）

1. **单次变更量仍巨大**：后端支撑 + 主题引擎 + UI 基建 + 全量页面替换，涉及数百文件，需严格执行分阶段编译门禁。
2. **数据库迁移链合并复杂**：Archive v90_91→v108_109 的迁移逻辑不能直接照搬（与 OURS v89_90→v103_104 版本号冲突），需手工将 Archive 独有 25 实体并入本项目 v104 链（5 批新版本）。
3. **两套 Compose 组件库并存**：本项目 `widget/components`（自研 M3）与 Archive `widget/compose`（基于 miuix）互不兼容，需入口/命名隔离，维护面增加；最终观感以 Archive 为准。
4. **特色 UI 需要二次适配**：本项目特色 UI（视频/图片播放器等）是 View/RecyclerView 体系，接入 Archive Compose 组件库需做外观统一，避免风格割裂。
5. **回退成本高**：一旦开始整层替换，回退到旧 UI 需要完整分支恢复（已通过分支快照缓解，`test_compose_self_20260818`）。
6. **风险集中在"一次性完成"的期望**：用户要求一次性完成迁移整合，但超大 diff 天然伴随编译与回归风险，需靠分阶段验证与真机测试兜底。

### Prior Art

- Archive（[Rimchars/legado]）本身即从 Lyc 分支持续演进 UI，其 Compose 化路径可视为本方案的"已被验证的实践"。
- 本项目此前已完成的部分页面 Compose 化（Search/SearchContent/BookSource 等）可作为特色功能的 Compose 接入参考。

## Requirements

### 功能需求（FR）

- **FR-1 Cronet 升级**：`CronetVersion` 升级至 `500.0.1`，删除 `app/cronetlib/` 本地文件树（6 个 jar + 相关打包逻辑），改用 Maven 构件 `cronet-bundled:500.0.1`（方案 1，用户已确认），APK 体积减小且网络/嗅探/播放能力不退化。
- **FR-2 Archive UI 搬迁**：主界面、书架、发现、我的、订阅、书源管理、搜索、详情、目录、阅读、配置等页面替换为 Archive 版（完整搬入）。
- **FR-3 地基补齐**：搬入 4 个 Compose 依赖（miuix/reorderable/lazyColumnScrollbar/liquidglass）+ `SearchBookMergeUtils` + `VideoBookPreloader` + `WebViewPool.Scope` 枚举，ARCHIVE 核心 UI 编译通过。
- **FR-4 后端支撑**：补齐 `ReadBook` 新方法（reloadCurrentContent 等）、`BookDao.flowShelf*` 系列、`AppCloudStorage` + `lib/cloud`、EPub Core、config 新类，编译通过。
- **FR-5 主题系统**：采用 Archive 主题系统（32 字段 + ~68 key + ThemeRuntimeKeys + 主题包/外观套件），本项目存量主题数据（5 色 + 背景图 key）可直接读取；`themeMode` 默认值跟随 Archive 语义（"0"跟随系统）；执行一次性夜间键迁移。
- **FR-6 数据库兼容**：本项目存量用户覆盖安装升级数据不丢失；Archive 依赖的 25 个新实体可用；本项目 9 个特色实体保留。
- **FR-7 视频播放特色**：抖音风格播放器（ViewPager2 竖向 + 上下滑动切换下一内容 + 自动加载下一页）在新 UI 上完整可用；前置嗅探（JS 覆写 fetch/XHR + WebView 拦截 + MIME 嗅探 + M3U8/HLS 加固）不退化（P0 必保）。
- **FR-8 图片播放特色**：图片画廊 / 详情大图 / 画布模式 / 金字塔加载在新 UI 上可用（P0 必保）。
- **FR-9 全局搜索**：书源全局搜索（随 Archive UI）+ RSS 订阅源全局搜索（本项目特色，P0 必保）+ 内容全文搜索可用。
- **FR-10 分组编辑**：发现页 / 订阅 tab / 书源管理 / 订阅源管理分组编辑、分组封面、批量分组可用（P1）。
- **FR-11 高亮体系**：正文高亮规则（本项目特色）保留可用（P1）。
- **FR-12 项目标识**：应用名、logo、仓库地址、开发者改回本项目。
- **FR-13 UI 标准**：迁移完成时产出 `docs/project-flow/ui-standards/` 标准文档。

### 非功能需求（NFR）

- **NFR-1 编译门禁**：每个迁移阶段结束必须 `./gradlew assembleAppDebug` 编译通过（使用本项目 `io.legado.miss.app.debug` 测试包）。
- **NFR-2 真机验证**：迁移完成必须按 `ai_tests` 流程真机/模拟器端到端验证（八步流程 + L1/L2）。
- **NFR-3 覆盖安装**：测试包覆盖安装（旧库→新库）不崩溃、数据不丢失。
- **NFR-4 包体积**：Cronet 去内部打包后 APK 体积下降（量化目标：较基线减少 cronet 内嵌体积）。
- **NFR-5 性能**：阅读页 / 书架 / 视频播放无新增明显卡顿。
- **NFR-6 可维护**：迁移分支独立于 master，回退只需切分支。
- **NFR-7 单元测试**：迁移完成的模块核心功能均有单元测试覆盖（`./gradlew test` 全绿为阶段完成前置条件）。

## Scenarios

### 场景 1：存量用户覆盖安装升级
用户从本项目旧版（数据库 v104，含高亮/封面图库/播放历史/RSS 路由/回收站等特色数据）覆盖安装新版（并入 Archive 25 实体，v108）→ 数据全部保留，AI/朗读等新功能表结构就位，视频/图片播放器仍可用。

### 场景 2：抖音风格视频播放
用户在订阅源打开视频文章 → 进入播放页 → 上下滑动切换下一个视频/下一篇文章 → 滑动到末尾自动加载下一页 → 播放失败时触发前置嗅探降级 → 使用 M3U8/HLS 加固通道播放。（P0）

### 场景 3：RSS 订阅源全局搜索
用户在订阅 tab 搜索关键词 → 遍历所有订阅源统一搜索 → 结果按网页/图片/视频类型筛选 → 点击进入对应文章。（P0）

### 场景 4：发现/订阅分组管理
用户在发现页 / 订阅 tab 长按分组标签 → 弹出分组管理（新建/重命名/删除/分组封面/批量分组）→ 分组变更实时刷新列表。（P1）

### 场景 5：主题切换与夜间模式
用户在主题管理页切换主题（日/夜/背景图/界面色/主题包导入导出）→ 全应用即时生效（含 Compose 页面与 View 页面），夜间键迁移后日夜间独立配色，默认跟随系统。

### 场景 6：新功能扩展（UI 标准支撑）
后续新增设置页/管理页 → 依据 `docs/project-flow/ui-standards/` 的组件库与规范直接构建，风格与现有页面一致。
