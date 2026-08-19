# spec.md — UI 问题综合整改（2026-08-18）

## Intent

本 spec 针对 2026-08-18 用户验收反馈的 **9 大 UI 问题**（承接 [`ui-redesign-m3`](../ui-redesign-m3/spec.md) UI Compose 化改造遗留问题）进行系统性整改，目标：

1. **修复 4 个功能性 Bug**：书架分组样式切换后头部不按原标签展示（问题1）、沉浸式操作栏只沉浸底部不沉浸头部（问题2）、长按书架书进详情报 book is null（问题8）、书源编辑页头部被改丑（问题7）。
2. **恢复被私自裁剪的功能**：功能裁剪回溯自查（重点：启动界面 / 发现订阅布局选项 / 书源订阅源布局设置，对比 2026-08-04 前版本），凡被裁剪的既有功能一律回补（问题3/9）。
3. **统一弹框体系与组件风格**：三种弹框样式（右上角下拉 AppDropdownMenu / 底部上滑 AppModalBottomSheet / 悬浮居中 Dialog 族 AppEditDialog/AppSelectDialog/ConfirmDialog）+ Switch 滑动 SettingsToggleRow 等组件全站统一，杜绝页面私有弹框与组件（问题9）。
4. **发现/订阅行为对齐书架**：默认「标签」展示样式与书架一致、分组/文件夹模式下搜索框显隐规则、批量分组设置、去掉三点菜单冗余分组列表（问题4/5/6）。
5. **推进全页面 Compose 化收尾**：除阅读详情页外，所有页面组件 Compose 化（问题3/9）。**设计阶段已完成页面现状调研**（见 [design.md「调研结论」](./design.md#调研结论)，详证 `docs/temp-analysis/compose-status-inventory.md`）：84 页面类三分类（纯 Compose 7 / View+Compose 壳 62 其中"只改头部"42 / 纯 View 15），并产出**功能裁剪/降级证据清单 C1-C5（裁剪 5 项，含墨水屏模式入口丢失）+ D1-D5（降级 5 项）+ ✅ 无裁剪 15 项**（详证 `docs/temp-analysis/regression-diff.md`）与**用户点名 5 疑点根因核实**（详证 `docs/temp-analysis/user-suspicion-check.md`），实施不偷懒、不漏页、不臆测。

**红线（禁止触碰）**：
- **阅读详情页禁止改动**：阅读器正文引擎（PageView/TextChapterLayout/翻页委托）、漫画/音频/WebView 池等内核与第三方控件保留原生 View（对齐 ui-redesign-m3 AD-02）。
- **禁止再次裁剪功能**：本批次为"整改回归"性质，任何整改不得再缩减既有功能，只允许恢复与统一。
- **禁止臆测**：各问题根因以需求分析确认结论为准，实施前先到源码核实再动手。

## Scope

### In Scope

| 范围 | 说明 |
|------|------|
| P0 Bug 修复 | 问题1（书架分组样式切换重建 + style1 头部固定 Tab 对齐原版）、问题8（长按进详情补传 bookUrl）、问题2（沉浸式操作栏头部联动） |
| P1 发现/订阅整改 | 问题5（默认标签展示 + 分组/文件夹模式搜索框显隐规则）、问题6（三点菜单去掉分组列表）、问题4（批量分组设置） |
| P2 弹框与样式统一 | 问题7（书源编辑页头部样式还原）、问题9 弹框三样式统一与组件风格统一（SettingsToggleRow 等） |
| P3 功能裁剪回溯与 Compose 化补全 | 问题3（启动界面/我的页/子页面样式统一）、问题9 功能裁剪回溯清单（基线 897b42f95）+ Compose 化收尾（按调研结论 A ③ 纯 View 清单：BackupConfig/OtherConfig + P3 长尾页） |
| 验收与交付 | 逐问题验收、编译门禁、updateLog 同步、真机验证、文档同步（对齐 README/tasks 阶段划分） |

### Out of Scope

| 排除项 | 原因 |
|--------|------|
| 阅读详情页（reader 正文引擎/翻页/漫画/音频/WebView 池/代码编辑器） | 内核与第三方控件保留原生 View，Compose 仅做页面壳（ui-redesign-m3 AD-02），本批次不改 |
| 网络层 / 播放器 / 数据层 / 规则引擎 | 业务逻辑零改动，仅 UI 层整改 |
| 数据库 schema 变更 | 无 |
| 新增功能 | 本批次为整改回归性质，不引入不需要的新功能 |

## Approach

### Selected Approach

采用 **"P0 修 Bug → P1 发现订阅整改 → P2 弹框样式统一 → P3 回溯补全"四阶段渐进整改**路线，每阶段独立验证、回归后再进入下一阶段：

**P0 — Bug 修复（问题 1 / 8 / 2，最高优先级）**
- **问题1**：`BaseBookshelfFragment.configBookshelf()` 切换 `AppConfig.bookGroupStyle` 时，在 `notifyMain=true` 之外**追加触发 fragment RECREATE**，让 `MainActivity.getFragmentId`（按 `bookGroupStyle == 1` 分发 style2/style1）重新生效；同时修正 style1 头部结构——固定 Tab（全部/本地）且位置对齐原版 Toolbar+TabLayout（当前为 Compose BookGroupTabs 的 ScrollableTabRow 结构）。
- **问题8**：`BookshelfFragment1/2.onBookLongClick` 目前只 `putExtra("name"/"author")` 不传 `bookUrl`，导致 `BookInfoActivity.initData` 经 `viewModel.getBook()` 加载为 null。改为补传 `bookUrl`（或直接复用点击路径的 `startActivityForBook(book)` 传完整对象）。
- **问题2**：`PreferKey.immNavigationBar` 目前仅作用底部导航栏（`BaseActivity.setNavigationBarColorAuto`），头部（状态栏/顶栏）未联动。开启后复用 `transparentStatusBar` 方案联动头部沉浸，与底部导航栏行为一致。

**P1 — 发现/订阅整改（问题 4 / 5 / 6）**
- **问题5**：发现/订阅默认展示样式对齐书架「标签」——复用 `BookGroupTabs` 占领头部展示标签；分组/文件夹模式下隐藏搜索框（当前 `ExploreFragment` 为 View TabLayout + `SettingsSearchBar` 固定显示在标签上方），进入文件夹后才显示搜索框且搜索范围仅限当前文件夹。
- **问题6**：移除 `ExploreFragment.buildMenuActions` 中的 Groups header 与动态分组列表，三点菜单只保留有实际意义的操作项。
- **问题4**：为发现/订阅增加批量分组设置，复用书架 `GroupManageDialog` + `BookshelfManageActivity` 的多选 → 分组交互模式。

**P2 — 弹框与样式统一（问题 7 / 9）**
- **问题7**：`BookSourceEditActivity` 头部 `initComposeQuickToolbar` 的 FlowRow+Checkbox+DropdownMenu 紧凑风格还原贴近原版简洁样式；参考 `RssSourceEditActivity` 只改顶栏、保留原 XML 表单的正面做法（该页被用户认可），订阅源编辑页保持现状不退化。
- **问题9**：弹框统一为三种样式（`AppDropdownMenu` 右上角下拉 / `AppModalBottomSheet` 底部上滑 / Dialog 族 `AppEditDialog`/`AppSelectDialog`/`ConfirmDialog` 悬浮居中），开关组件统一走 `SettingsToggleRow`（M3 Switch，颜色动画随主题），替换散落页面的私有弹框与 Toggle/Checkbox 混用。

**P3 — 功能裁剪回溯 + Compose 化补全（问题 3 / 9）**
- **问题3**：`WelcomeScreen`（当前仅 showTitle/showSubtitle/showIcon/showSlogan 四要素）还原完整启动样式功能——`WelcomeConfigScreen` 补回日/夜 4 个文字/图标显隐开关（C2，`WelcomeActivity` 消费逻辑已在）；修复「我的」页开关不生效（疑点1：`SettingsToggleRow` 整行无 clickable）；修复书源管理页网格列数与设置不符（疑点2：`BookSourceScreen` 列数硬编码）；「我的」页子页面（`OtherConfigFragment`/`BackupConfigFragment`）Compose 化补全。
- **问题9**：以 git `897b42f95`（2026-08-02，8 月 4 号前最新）为基线对比，**设计阶段已产出功能裁剪清单**（见 design.md 调研结论 B：C1 墨水屏模式四态选择器、C2 欢迎页 4 开关、C3 书源排序"最近更新"、C4 桌面图标、C5 捐赠 + D1-D5 降级 + ✅ 无裁剪 15 项），P3 按优先级恢复核心功能（C1→C2/C3→C4）；除阅读详情页外，剩余 View 页面按调研矩阵（design.md A ②b 表）完成 Compose 化收尾，并同步 ui-standards 组件目录与实施回执。

### Alternatives Considered

| 替代方案 | 否决理由 |
|----------|----------|
| 问题1：切换分组样式时**只改 Compose 状态、不重建 fragment** | `MainActivity.getFragmentId` 按 `bookGroupStyle` 在 style1（Tab）/style2（Folder）两个不同 Fragment 类间分发，仅改 Compose 状态无法完成 Fragment 类型切换；且 style1 头部结构本身与需求不符，必须重建并修正头部。故采用"notifyMain + RECREATE"。 |
| 问题5：发现/订阅**保留 View TabLayout** 与当前搜索框布局 | 与书架 `BookGroupTabs`（Compose）行为/样式不一致，标签无法复用、无法满足"默认标签展示与书架一致"的验收，且持续维护两套标签实现。故复用 `BookGroupTabs` 统一标签体系。 |
| 问题7：为书源编辑页**重新设计一套 Compose 头部** | 引入新设计回归风险高；用户已明确认可订阅源编辑页"保留顶栏 + 原 XML 表单"的观感。故直接还原贴近原版的简洁样式，不做新设计。 |
| 问题9：各页面**保留私有弹框/开关组件** | 风格分裂、维护成本高，直接违反 ui-redesign-m3 组件复用门禁（页面禁止私有复制组件）。故统一为三样式弹框族 + `SettingsToggleRow`。 |
| 问题8：仅在 `BookInfoActivity` **增加无 bookUrl 兜底容错** | 治标不治本：错误入口仍在，且点击路径（`startActivityForBook`）本就正常，说明应修复长按路径传参而非在详情页兜底。故从源头补传 bookUrl。 |

### Drawbacks

| 已知缺点 | 接受理由 |
|----------|----------|
| P2/P3 Compose 化与回溯工作量大，回归风险高 | 本批次为整改回归性质，P0/P1 优先闭环后再推进 P2/P3，每阶段独立验证；功能裁剪回溯为红线要求，必须执行 |
| 问题1 强制重建 fragment 可能带来短暂重建开销/状态闪烁 | 分组样式属低频切换操作，重建代价可接受；换取"切换后行为与选中样式一致"的正确性 |
| 弹框统一为三样式可能影响现有用户的交互习惯 | 统一性收益大于短期习惯差异；现有高频入口与操作路径不变，仅视觉/弹出方式收敛 |
| 问题2 头部沉浸可能改变部分页面顶栏显示观感 | 沉浸式操作栏为可开关选项，用户主动开启才生效，默认行为不变 |
| 功能裁剪回溯清单可能较大，核对耗时 | 以 git 基线与逐项三态核对保证完整性，优先恢复核心功能，非核心项记录在案不强制 |

### Prior Art（已有可复用资产）

- **弹框三样式组件**：`AppDropdownMenu`（右上角下拉）/ `AppModalBottomSheet`（底部上滑）/ Dialog 族 `AppEditDialog`/`AppSelectDialog`/`ConfirmDialog`（悬浮居中），位于 `app/src/main/java/io/legado/app/ui/widget/components/`。
- **组件风格**：`SettingsToggleRow`（Switch 滑动，颜色动画随主题）、`SettingsCard`，同目录。
- **标签组件复用**：`BookGroupTabs` 位于 `app/src/main/java/io/legado/app/ui/main/bookshelf/BookshelfScreen.kt`，可复用于发现/订阅默认标签展示。
- **批量分组交互模式**：书架 `GroupManageDialog`（`app/src/main/java/io/legado/app/ui/book/group/GroupManageDialog.kt`）+ `BookshelfManageActivity`（`app/src/main/java/io/legado/app/ui/book/manage/BookshelfManageActivity.kt`）。
- **正面样例**：`RssSourceEditActivity`（`app/src/main/java/io/legado/app/ui/rss/source/edit/RssSourceEditActivity.kt`）"只改顶栏、保留原 XML 表单"被用户认可，作为书源编辑页还原参照。
- **沉浸式基础**：`transparentStatusBar` 已有实现（`BaseActivity`/`ComposeActivitySupport` 体系），供 `immNavigationBar` 头部联动复用。
- **工程规范**：ui-redesign-m3 的 `ui-standards.md`（组件六族/页面骨架/验收 KPI）与 `pages-inventory.md`（84 页清单/迁移路线图）。

## Requirements

### 功能需求（FR，R1-R9 对应 9 大问题）

| ID | 需求 | 优先级 | 验收标准 |
|----|------|--------|----------|
| R1 | 书架布局管理切分组样式为「标签」后，头部按原标签展示 | P0 | 切「标签」→ style1 立即重建，头部固定 Tab（全部/本地）且位置对齐原版 Toolbar+TabLayout；切「文件夹」→ style2 文件夹样式正常；无需手动重启 |
| R2 | 沉浸式操作栏（`immNavigationBar`）开启后头部联动沉浸 | P0 | 开启后状态栏/顶栏与底部导航栏**一起沉浸**（内容顶到边缘）；关闭后恢复原状；默认行为不变 |
| R3 | 启动界面/「我的」页/子页面样式还原统一 | P1 | 启动界面完整样式功能（背景/文字/图标/标语）齐全；「我的」页单选/滑动开关全部生效；主/子页面样式统一；子页面 Compose 化完成 |
| R4 | 发现/订阅支持批量分组设置 | P1 | 条目可多选并批量归入目标分组，交互与书架 `GroupManageDialog`+`BookshelfManageActivity` 一致 |
| R5 | 发现/订阅默认「标签」展示 + 搜索框显隐规则 | P1 | 默认标签样式与书架一致（占领头部）；分组/文件夹模式隐藏搜索框；进入文件夹才显示搜索框且搜索仅限当前文件夹；标签模式搜索框回到标签上方全局搜索 |
| R6 | 去掉发现/订阅三点菜单的分组弹框 | P1 | 三点菜单不再出现 Groups header 与动态分组列表，仅保留有实际意义的操作项 |
| R7 | 书源编辑页头部样式还原 | P2 | 头部观感贴近原版/与订阅源编辑页一致，不再为紧凑 FlowRow 风格 |
| R8 | 长按书架书进详情不再报 book is null | P0 | 长按任意书进详情页正常加载该书，不再出现 book is null 异常 |
| R9 | 弹框体系统一 + 组件风格统一 + 功能裁剪回溯 + Compose 化收尾 | P2/P3 | 全应用弹框仅三种样式（无页面私有弹框）；开关组件统一 `SettingsToggleRow` 且跟随主题；**功能裁剪清单（基线 897b42f95，设计阶段已核实 C1-C5 裁剪 5 项 + D1-D5 降级 5 项 + ✅ 无裁剪 15 项）核心功能已回补**（墨水屏模式/欢迎页 4 开关/书源排序"最近更新"/桌面图标）；除阅读详情页外所有页面为 Compose（按调研结论 A 清单：纯 Compose 7 + View+Compose 壳 62 其中"只改头部"42 待补 + 纯 View 15 待补） |

### NFR

- **回归红线**：整改不引入新回归、不再次裁剪既有功能；阅读详情页零改动。
- **兼容**：minSdk 23，AndroidX 版本不动，不引新增依赖。
- **组件复用门禁**：页面禁止私有复制公共组件（对齐 ui-redesign-m3 FR-10）。
- **编译/交付门禁**：`./gradlew assembleAppDebug` BUILD SUCCESSFUL；updateLog 编译前基于 git diff 同步；真机 L2 用例通过。

## Scenarios

### S1 用户在书架布局管理切换分组样式
1. 书架 → 布局管理 → 分组样式选「标签」。
2. `configBookshelf()` 保存 `AppConfig.bookGroupStyle` 并触发 fragment 重建。
3. 书架头部立即按 style1 展示固定 Tab（全部/本地），位置对齐原版 Toolbar+TabLayout，无需重启应用。
4. 再切回「文件夹」→ 头部切换为文件夹样式，行为一致。

### S2 用户长按书架书进详情
1. 书架任意样式下长按某本书。
2. `onBookLongClick` 携带完整 `book` 信息（含 `bookUrl`）跳转 `BookInfoActivity`。
3. `initData` 经 `viewModel.getBook()` 正常加载该书并展示详情，不再出现 book is null。

### S3 用户将发现页切换为分组/文件夹模式
1. 发现页默认展示「标签」样式，头部标签与书架一致。
2. 切换为分组/文件夹模式 → 搜索框隐藏。
3. 点进某个文件夹 → 搜索框出现，输入关键词仅搜索当前文件夹内容。
4. 切回标签模式 → 搜索框回到标签上方，恢复全局搜索。

### S4 用户开启沉浸式操作栏
1. 我的 → 设置 → 主题/界面 → 打开「沉浸式操作栏」。
2. 底部导航栏与头部（状态栏/顶栏）同时沉浸，内容顶到屏幕边缘，行为一致。
3. 关闭开关 → 恢复原有非沉浸显示。

### S5 用户使用发现/订阅三点菜单与批量分组
1. 发现/订阅右上角三点菜单 → 只看到有实际意义的操作项，不再弹出大片分组列表。
2. 通过「分组设置」入口进入批量分组 → 多选条目 → 归入目标分组，交互与书架一致。
3. 分组后的条目在对应文件夹中可被搜索（限当前文件夹）。
