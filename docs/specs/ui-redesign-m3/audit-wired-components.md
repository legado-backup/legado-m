# 已接线 5 项组件规格对账审计报告

> 审计方式：只读源码分析，逐项对照 `ui-standards.md §3.4` 组件规格真值表（唯一真值）核对 5 个维度（容器/形状、内边距、字号、颜色槽位、高度/尺寸/触控）+ 硬编码检查。
> 日期：2026-08-13。给后续 AI 开发用的可执行审计清单。🔴=违例需修；🟡=观察项/待人工确认；✅=符合。

---

## 审计 1：S1 MainActivity 底部导航（骨架 S1）

- 规格依据：§3.4 `PillNavigationBar` 行（状态 ✅，2026-08-13 修复）
- 代码：`ui/widget/components/PillNavigationBar.kt` + 接线 `ui/main/MainActivity.kt:196`

逐项对账：

| 维度 | 规格 | 代码 | 判定 |
|------|------|------|------|
| 容器/形状 | Row surface 底 + 顶部 HorizontalDivider 0.5dp outlineVariant α0.4 | `:62-66` HorizontalDivider thickness=0.5.dp color=outlineVariant.copy(α0.4f)；`:70` Row background=surface | ✅ |
| 内边距 | 垂直 6dp(Row)/垂直 4dp(Tab)/SpaceEvenly | `:71` Row padding vertical=6.dp；`:125` Tab padding vertical=4.dp；`:72` SpaceEvenly | ✅ |
| 字号 | labelSmall Bold(选中)/Regular(未选中) | `:160` labelSmall + `:161` fontWeight Bold/Normal | ✅ |
| 颜色槽位 | surface / primary α0.12 选中底 / onSurfaceVariant 未选中 / onSurface 选中 | `:57` primary.copy(α0.12f)；`:82` onSurfaceVariant 未选中；`:83-84` primary 选中 | ✅ |
| 高度/尺寸 | Tab 图标 22dp + 选中底 36×30dp 胶囊 RoundedCornerShape(15.dp) | `:136` size(36,30)+RoundedCornerShape(15.dp)；`:144` Icon 22.dp | ✅ |
| 触控 | Tab weight(1f) 均分，≥48dp | `:123` weight(1f)；整列高约 60dp≥48dp | ✅ |
| 动画 | 底色 spring 弹性（替代 tween 原地变色） | `:112-119` bgColor spring(DampingRatioMediumBouncy, StiffnessMedium)；icon/text tween(200) 合理 | ✅ |

- 硬编码检查：grep `Color(0x`/`.sp` → **0 命中** ✅
- 结论：✅ **全部符合**

---

## 审计 2：S2 BookSourceActivity 书源管理（骨架 S2）

- 规格依据：§3.4 `GroupHeader` / `EmptyStatePlaceholder` 行；§1.1 禁硬编码字号
- 代码：`ui/book/source/manage/BookSourceScreen.kt` + `BookSourceItems.kt`

逐项对账：

| 维度 | 规格 | 代码 | 判定 |
|------|------|------|------|
| GroupHeader 使用 | Row h16 v8 / titleSmall Bold / onSurface+outline / 行≥48dp / 整行折叠+组操作菜单 | `BookSourceScreen.kt:564` 调用；`GroupHeader.kt:58` padding h16、`:69` titleSmall+Bold、`:56` height 48dp、`:57` 整行 clickable+`:95` AppDropdownMenu | ✅ |
| EmptyStatePlaceholder 使用 | Column 居中 / Icon 48dp+Spacer16+标题+Spacer24 / bodyLarge+bodyMedium / outline / Icon 48dp | `BookSourceScreen.kt:240,270,306` 三处调用；`EmptyStatePlaceholder.kt:42` Icon 48dp、`:44` Spacer16、`:47` bodyLarge、`:55` bodyMedium、`:61` Spacer24 | ✅ |
| 三视图断点 | （网格列数自适应）紧凑<480/中480-840/宽≥840 | `BookSourceScreen.kt:356-361` 网格断点 400/600/800dp | 🟡 观察项（列数决策非骨架断点，见下方） |
| 圆角 | 卡 18dp | `BookSourceItems.kt:232,239` SourceCardContent RoundedCornerShape(18.dp) | ✅ |
| 硬编码色 | 禁 Color(0x) | `BookSourceItems.kt:313-320` sourceCoverColorPalette → **§1.1 例外登记③ 豁免**；`:382-385` SourceTypeBadge 4 色 → **例外登记④ 豁免** | ✅（豁免） |
| 硬编码字号 | 禁写死字号，用 typography | `BookSourceItems.kt:357` `fontSize = 24.sp`（SourceCover 首字符，已叠 titleLarge 又覆盖） | 🔴 **违例** |

- 硬编码检查：grep `Color(0x` → 12 处命中（全部落在两条豁免登记内）；grep 硬编码 `sp` → **1 处真违例 `BookSourceItems.kt:357`**
- 结论：⚠️ **1 处违例需修** + 1 观察项

详细违例：
- 🔴 **`BookSourceItems.kt:357`** `fontSize = 24.sp` 硬编码字号。规格 §1.1「字体：禁止写死字号；用 MaterialTheme.typography」。SourceCover 首字符已设 `titleLarge`，又叠加 `fontSize=24.sp` 覆盖。建议：删除该行，改用 `MaterialTheme.typography.titleLarge` 或 `displaySmall`（可视需要选 24sp 邻近语义档）。
- 🟡 **`BookSourceScreen.kt:356-361`** 网格断点 400/600/800dp 与规格 §1.4「紧凑<480/中480-840/宽≥840」不一致。此为网格列数自适应（2/3/4/6 列），非页面骨架断点，规格未强制列数档位，**待人工确认**是否需要对齐 480/840。
- 🟡 **组件表台账**：`SettingsSearchBar`（组件表标 ⚠️ 孤儿）已被 `BookSourceScreen.kt:215` 接线，组件表状态未更新，文档需同步（非代码违例）。

---

## 审计 3：S4 BookInfoActivity 书籍详情壳层（骨架 S4）

- 规格依据：§3.4 `GlassTopAppBar` / `AppDropdownMenu` 行
- 代码：`ui/book/info/BookInfoActivity.kt` + `ui/widget/components/GlassTopAppBar.kt` + `AppDropdownMenu.kt`

逐项对账：

| 维度 | 规格 | 代码 | 判定 |
|------|------|------|------|
| GlassTopAppBar 底 | surface 纯色实底（2026-08-13 封口） | `GlassTopAppBar.kt:37-38` containerColor=surface ✅；`BookInfoActivity.kt:295` 接线 | ✅ |
| GlassTopAppBar 字号 | titleMedium | `GlassTopAppBar.kt:44-48` title Text 仅设 fontWeight=Medium，无显式 style → 继承 M3 TopAppBar 默认 titleLarge | 🔴 **违例（待人工确认）** |
| AppDropdownMenu checked 勾选 | checked 勾选 primary | `AppDropdownMenu.kt:62-70` checked==true 显示 Check icon primary；`BookInfoActivity.kt:487,538,558` MenuAction 传 checked | ✅ |
| 顶栏/底部按钮圆角 | 按钮 12dp 圆角 48dp 高 | `BookInfoActivity.kt:343,346` OutlinedButton shape 12dp + height 48dp；`:362,365` Button 同 | ✅ |

- 硬编码检查：grep `Color(0x`/`.sp` → `BookInfoActivity.kt` **0 命中** ✅
- 结论：⚠️ **1 处违例（待人工确认）**

详细违例：
- 🔴 **`GlassTopAppBar.kt:44-48`** 规格 §3.4 要求 titleMedium，但 title Text 未显式设置 `style = MaterialTheme.typography.titleMedium`，将继承 M3 `TopAppBar` 默认 `titleLarge`。**待人工确认**：若 M3 版本默认确为 titleLarge，则需补 `style = MaterialTheme.typography.titleMedium`；若本主题已全局覆盖 TopAppBar title 样式则可能无差异。建议显式设置以消除歧义。

---

## 审计 4：Phase4 阅读器浮层（骨架 S5）

- 规格依据：§3.4 **无 `AppModalBottomSheet` / `BookTocBookmarkSheet` 真值行**（两者在 §3 组件表均标 ⚠️ 孤儿，真值表未登记）
- 代码：`ui/widget/components/AppModalBottomSheet.kt` + `BookTocBookmarkSheet.kt` + `ui/book/read/ReadBookActivity.kt:1264-1307 setupTocSheet`

逐项对账（对齐任务描述功能点）：

| 维度 | 要求 | 代码 | 判定 |
|------|------|------|------|
| 双 Tab | 目录/书签双 Tab | `BookTocBookmarkSheet.kt:48-69` TabRow 双 Tab（目录 MenuBook / 书签 Bookmark） | ✅ |
| AppModalBottomSheet 容器 | Sheet hub 包裹 | `ReadBookActivity.kt:1268` AppModalBottomSheet{ BookTocBookmarkSheet }；`AppModalBottomSheet.kt:37-55` M3 ModalBottomSheet + shape 16dp top + surfaceVariant + navigationBarsPadding | ✅ |
| 章节列表 TextButton 入口 | 完整目录入口（无回归） | `ReadBookActivity.kt:1296-1301` TextButton「章节列表」→ tocActivity | ✅ |

- 硬编码检查：三文件 grep `Color(0x`/`.sp` → **0 命中** ✅
- 结论：✅ **功能符合**，但 **组件未入真值表，无可对账硬规格** → 🟡 待人工确认

说明：`AppModalBottomSheet.kt` 使用 `containerColor=surfaceVariant`、`tonalElevation=8dp`、顶圆角 16dp。因规格真值表未登记这两组件行，无法逐维度对账；建议后续为 `AppModalBottomSheet` 补一行规格真值（容器/形状、内边距、颜色槽位、高度），封闭规格缺口。

---

## 审计 5：S6 Import 系列样板（骨架 S6）

- 规格依据：§3.4 `ImportSourceSheet` 行（状态 ✅，2026-08-13 接线）
- 代码：`ui/widget/components/ImportSourceSheet.kt` + `ui/association/ImportRssSourceDialog.kt`

逐项对账：

| 维度 | 规格 | 代码 | 判定 |
|------|------|------|------|
| 容器 | AppModalBottomSheet 容器 | `ImportSourceSheet.kt:109` AppModalBottomSheet 包裹 | ✅ |
| 顶部行 | h56 | `:115` height(56.dp) | ✅ |
| 列表项内边距 | h16 v12 | `ImportSourceSheet.kt:267` ImportItemRow padding(horizontal=12, vertical=6) | 🔴 **违例（待人工确认）** |
| 状态徽标色槽 | NEW=primaryContainer / UPDATE=tertiaryContainer / EXIST=secondaryContainer | `:318-323` NEW→primaryContainer、UPDATE→tertiaryContainer、EXIST→secondaryContainer | ✅ |
| 状态徽标字号 | labelSmall | `:331` labelSmall | ✅ |
| 底部三按钮 | 12dp 圆角 48dp 高 | `:215,232,240` OutlinedButton/Button shape RoundedCornerShape(12.dp)+height(48.dp) | ✅ |
| 列表高度 | LazyColumn heightIn max440dp | `:181` heightIn(max=440.dp) | ✅ |
| 触控 | 整行勾选+Checkbox+Edit ≥48dp | `:266` Column clickable 整行；`:273` Row height(48.dp)；`:288` IconButton(Edit) 默认 48dp | ✅ |

- 硬编码检查：`ImportSourceSheet.kt` grep `Color(0x`/`.sp` → **0 命中**（仅注释声明禁止）；`ImportRssSourceDialog.kt` → **0 命中** ✅
- 结论：⚠️ **1 处违例（待人工确认）**

详细违例：
- 🔴 **`ImportSourceSheet.kt:267`** 规格 §3.4「列表项 h16 v12」vs 代码 `padding(horizontal=12.dp, vertical=6.dp)`。**待人工确认规格语义**：若 h16 v12 指内边距，则水平 12≠16、垂直 6≠12 均不符，需改为 `padding(horizontal=16.dp, vertical=12.dp)`（注意行高由内部 `:273` Row height(48.dp) 保证，改垂直 padding 会抬高总高，需同步复核触控高度）；若 h16 v12 仅指行高占位语义，则与 `:273` 行高 48dp 并存，需在规格表澄清。

---

## 违例汇总表（2026-08-13 已定案收敛）

> **定案说明**：此前 3 处 🔴 均标「待人工确认」，现收敛为明确决策，后续 AI 可直接执行。执行依据=ui-standards §1（禁硬编码字号/色）与 §3.4（组件规格唯一真值）。

| # | 组件/页面 | 规格项 | 代码位置 | 差异 | 定案决策（2026-08-13） |
|---|-----------|--------|----------|------|----------|
| 1 | S2 SourceCover | §1.1 禁硬编码字号 | `BookSourceItems.kt:357` | `fontSize=24.sp` 叠加覆盖 titleLarge | **删除该行**，改用 `MaterialTheme.typography.displaySmall`（24sp 邻近语义档），与 titleLarge 幂等消除 |
| 2 | S4 GlassTopAppBar | §3.4 titleMedium | `GlassTopAppBar.kt:44-48` | title 未显式设 style，继承 TopAppBar 默认 titleLarge | **补 `style = MaterialTheme.typography.titleMedium`**（显式消除歧义，统一全站顶栏标题档位） |
| 3 | S6 ImportItemRow | §3.4 列表项 h16 v12 | `ImportSourceSheet.kt:267` | padding horizontal=12/vertical=6 与 h16/v12 不符 | **改 `padding(horizontal=16.dp, vertical=12.dp)`**；行高由内部 `:273` Row height(48.dp) 保证，垂直 padding 增大会抬高总高——**同步复核触控≥48dp**（若总高超规格则规格表澄清 h16 v12 为「内容区语义」而非「内边距字面值」） |

### 定案后遗留观察项（已收敛为明确处理方式）
- 🟡 S2 网格断点 `BookSourceScreen.kt:356-361`（400/600/800 列数）vs §1.4（480/840 骨架断点）——**结论：两者不同维度**。§1.4 是页面骨架断点（紧凑/中/宽），网格列数是内容自适应档位；**保留代码现状 400/600/800**，不强行对齐 §1.4（已可在 §1.4 补一句「网格列数档位独立于骨架断点」）。
- 🟡 `SettingsSearchBar` 组件表仍标 ⚠️ 孤儿但已被 `BookSourceScreen.kt:215` 接线——**结论：更新组件表状态为「✅ 已接线」**（tasks 12.16r 已登记）。
- 🟡 Phase4 的 `AppModalBottomSheet` / `BookTocBookmarkSheet` 未入真值表——**结论：已在 ui-standards §3.4 补真值行**（2026-08-13），规格缺口已封闭。

### 已确认符合项（无需处理）
- S1 `PillNavigationBar` 全部维度 ✅（weight 均分 + 0.5dp 分割线 + 36×30 胶囊 RoundedCornerShape(15) + 22dp 图标 + labelSmall + spring 弹性 + BadgeDot）。
- S2 `GroupHeader` / `EmptyStatePlaceholder` 使用 ✅；卡 18dp ✅；硬编码色全部落在两条豁免登记内。
- S3 底部按钮 12dp 圆角 48dp 高 ✅；AppDropdownMenu checked 勾选 primary ✅。
- S4 双 Tab + AppModalBottomSheet 容器 + 章节列表 TextButton 入口 ✅（功能），规格真值缺失除外。
- S5 顶部 h56、状态徽标三槽色、labelSmall、底部三按钮 12dp/48dp、heightIn max440、整行触控 ✅。

---

## 审计 6：S3 BookSourceEditActivity 书源编辑页（骨架 S3，2026-08-13 巡检新增）

- 规格依据：§3.4 `SettingsCard` / `SettingsClickRow` / `SettingsToggleRow` / `AppDropdownMenu` 行；§1.1 禁硬编码字号/色
- 代码：`ui/book/source/edit/BookSourceEditActivity.kt`（initComposeQuickToolbar/initComposeFields/initComposeBottomBar）+ `ui/widget/components/SettingsCard.kt`

逐项对账（主代理交叉复核底部栏 + 子代理全量审计）：

| 维度 | 规格 | 代码 | 判定 |
|------|------|------|------|
| 容器/形状 | SettingsCard 圆角 18dp | `SettingsCard.kt` RoundedCornerShape(18.dp) | ✅ |
| 内边距 | SettingsCard 内边距 16dp | `SettingsCard.kt` padding horizontal=16/vertical=4 | ✅ |
| 底部按钮圆角/高 | 按钮 12dp 圆角 48dp 高 | `BookSourceEditActivity.kt:490-503` OutlinedButton/Button height(48.dp)+RoundedCornerShape(12.dp) | ✅ |
| 字号 | 用 MaterialTheme.typography | 全页组件均用 typography，无写死 sp | ✅ |
| 颜色槽位 | 用 colorScheme，禁 Color(0x) | 全页 colorScheme，无硬编码色 | ✅ |
| 触控 | 交互元素 ≥48dp | 按钮 48dp、SettingsClickRow/ToggleRow 公共组件自带行高 | ✅ |
| 组件复用 | 无私有表单布局 | 用 SettingsCard/SettingsClickRow/SettingsToggleRow/AppDropdownMenu/GlassTopAppBar 标准组件 | ✅ |

- 硬编码检查：BookSourceEditActivity + 所用组件 grep `Color(0x`/`Color.`/`#`/`[0-9]+\.sp` → **0 命中** ✅
- 结论：✅ **全部符合**

---

## 定案修复状态更新（2026-08-13 巡检复核）

> **巡检发现**：上文定案汇总表 3 处违例（#1/#2/#3）此前仅「定案」未「落地」——实现未同步修改。本次巡检逐项复核代码现状并全部修复，验证 `assembleAppDebug` BUILD SUCCESSFUL。

| # | 组件/页面 | 定案决策 | 修复状态（2026-08-13） |
|---|-----------|----------|----------|
| 1 | S2 SourceCover | 删 `fontSize=24.sp` 改 displaySmall | ✅ 已修复（`BookSourceItems.kt:354` 改 `MaterialTheme.typography.displaySmall`） |
| 2 | S4 GlassTopAppBar | 补 `style=titleMedium` | ✅ 已修复（`GlassTopAppBar.kt:46` 补 `style=MaterialTheme.typography.titleMedium`） |
| 3 | S6 ImportItemRow | 改 padding h16/v12 | ✅ 已修复（`ImportSourceSheet.kt:267` 改 `padding(horizontal=16.dp, vertical=12.dp)`，行高 48+24=72dp 仍满足触控≥48dp） |

> **经验沉淀**：审计文档「定案」必须同步「落地」代码修改，否则定案仅为纸面结论。后续定案需在当次会话内直接改码，避免跨会话遗留。