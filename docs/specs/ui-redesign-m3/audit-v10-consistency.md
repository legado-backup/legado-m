# V-10 一致性巡检报告（组件验收矩阵 · 全 App 扫码）

> 审计类型：只读静态扫描（未修改任何源码）
> 审计时间：2026-08-16
> 审计范围：`app/src/main/java/io/legado/app/ui/` 下全部 Compose 页面（31 个 `*Screen.kt` + 含 Compose 的 Activity/Dialog）+ `ui/widget/components/` 公共组件目录（55 文件，2026-08-16 孤儿清理后）
> 审计依据：`ui-standards.md` §1 设计基石 / §3 组件目录 / §3.2 防重复 / §3.4 组件规格真值表 + `AppShapes.kt`（2026-08-16 收敛的圆角 token）
> 审计方法：Glob/Grep 全仓扫 `RoundedCornerShape(X.dp)`（87 处）、`Color(0x...)`（35 处）、私有组件定义（120 处），逐页核读确认

---

## 1. 关键背景（影响结论的前提）

- **`AppShapes.kt` 为 2026-08-16（本次巡检当日）新建**，收敛圆角 token：`Card=18` / `Button=12` / `SheetTop=16(顶)` / `IconContainer=10` / `Chip=8` / `Tiny=4`。使用约定为「新代码一律引用 token，存量硬编码点逐步迁移（P2 token 回迁）」（注：原稿误标「tasks 12.1A」，tasks.md 无此编号，P2 回迁任务见 §7 进度跟踪）。
- **§3.4 真值表为 2026-08-13 建立**（早于 AppShapes 3 天）。真值表写死具体 dp 值，与 token 体系存在「数值一致但未符号化」的断层——组件按真值表实现了 18/12/8dp 等值，但未统一改引 `AppShapes`。
- 因此本报告将「硬编码圆角值」判为 **WARN**（数值多已对齐基线，缺的是 token 引用），将「页面私有重复组件」「跨页面逐字重复」判为 **ERROR**（违反 §3.2 防复制铁律）。

---

## 2. 公共组件目录清单（`ui/widget/components/` 共 55 文件）

> 注：本清单为审计当日（2026-08-16）快照，原列 57 文件；审计后 P1/P2 修复沉淀 `SettingsSelectableRow.kt`/`TagChip.kt` 等公共组件，随后 2026-08-16 孤儿清理删除 SummaryCard/ThemedSnackbarHost/SplicedColumnGroup/ManageScreenSheet 4 个无消费组件，目录现为 55 文件，以 `ui-standards.md` §3 组件目录表（55 文件）为准。

**主题/基石（4）**：`ThemeSpec.kt`（5色→34槽位）、`LegadoTheme.kt`（在 ui/theme/）、`ComposeActivitySupport.kt`（在 ui/theme/）、`AppShapes.kt`（圆角 token，**本次新增**）

**导航/顶栏（2）**：`PillNavigationBar.kt`、`GlassTopAppBar.kt`

**设置族（7）**：`SettingsSection.kt`、`SettingsCard.kt`、`SettingsClickRow.kt`、`SettingsToggleRow.kt`、`SettingsSearchBar.kt`、`RowIcon.kt`、`MetricGrid.kt`

**列表/展示（9）**：`ListCard.kt`(含 BookListCardMetrics)、`ListScaffold.kt`、`ListLayoutMenu.kt`、`GroupHeader.kt`、`ShelfGridSkeleton.kt`、`VerticalScrollbar.kt`(已接线→DownloadManage)、`LazyListFastScroller.kt`、`EmptyStatePlaceholder.kt`、`HeatmapCalendar.kt`

**反馈/弹层（4）**：`AppModalBottomSheet.kt`、`BadgeDot.kt`、`MenuLayer.kt`、`HighlightStyleSheet.kt`

**Dialog 族（11）**：`BaseComposeDialogFragment.kt`(基类)、`AppAlertDialog.kt`、`AppConfirmDialog.kt`、`ConfirmDialog.kt`、`AppEditDialog.kt`、`AppTextDialog.kt`、`AppWaitDialog.kt`、`AppNumberPickerDialog.kt`、`AppSelectDialog.kt`、`TextInputDialog.kt`、`SingleChoiceDialog.kt`、`MultiSelectDialog.kt`、`ActionListDialog.kt`、`AlertBuilder.kt`(DSL)、`AppEditDialog.kt`

**菜单（3）**：`AppMenuSheet.kt`、`AppDropdownMenu.kt`、`ModernActionPopup.kt`

**导入（1）**：`ImportSourceSheet.kt`

**交互（2）**：`SwipeActionContainer.kt`（✅ 已接线→BookSourceItems）、`SourceFilterRule.kt`(数据模型)、`LoginAssistChip.kt`

**阅读器族（6）**：`ReadMenuGlassButtonSurface.kt`、`ReadMenuSlider.kt`、`ReaderBookSheet.kt`、`ReaderMoreActionsSheet.kt`、`ReaderViewport.kt`、`TextActionSelectionMenu.kt`、`ReaderMenuSheet.kt`、`BookTocBookmarkSheet.kt`

> 注：`ui/widget/components/` 实际已远超规范 §3 表的「32 文件」登记数，**有 20+ 文件未登记进 §3 组件目录表**（如 AppConfirmDialog 已登记、但 `ListScaffold/ReaderMenuSheet/HighlightStyleSheet/MenuLayer` 等部分存在登记缺失）。建议 §3 表按实际文件全量回填。

---

## 3. 违规项清单

### 3.1 ERROR 级：页面私有重复组件 / 严重偏离（违反 §3.2 防复制铁律）

| # | 文件:行 | 私有组件 | 重复的公共能力 | 具体问题 | 建议修复 |
|---|---------|----------|---------------|---------|---------|
| E1 | `ui/main/bookshelf/BookshelfScreen.kt:333-351` | `ShelfUnreadBadge` | `BadgeDot`（§3.1 已声明「书架替换私有 UnreadBadge → BadgeDot ✅ 已接线」） | 私有角标仍残留：`RoundedCornerShape(8.dp)` 硬编码 + primary 底 + 自实现 `badgeTextBright` 黑白字判断。**规范声称已替换，代码实际未替换**，文档与代码不一致 | 改引 `BadgeDot`（count 模式）；若坚持 8dp 圆角矩形语义，收敛为 BadgeDot 的 shape 参数或登记豁免 |
| E2 | `ui/book/explore/ExploreShowScreen.kt:300-315` + `ui/book/import/ImportBookScreen.kt:191-198` | `TagChip`（同名 ×2） | 无公共 chip（应沉淀为公共组件） | **同名私有组件跨页面两处定义**，且规格不一致：Explore 版 `RoundedCornerShape(4.dp)`（AppShapes.Tiny 值）、Import 版 `MaterialTheme.shapes.extraSmall`；同文本标签视觉不同 | 提取公共 `TagChip`（建议 AppShapes.Chip 8dp）至 components 目录，两页改引 |
| E3 | `ui/book/storage/StorageManageScreen.kt:209-257` | `StorageManageItemRow` | `SettingsClickRow` | 注释自述「**SettingsClickRow 样式** + 尾部清除按钮，对齐原 item_cache_item」——即明知是公共组件等价实现仍私有复制（h16 v12 手写） | SettingsClickRow 增加尾部 action slot 或直接用公共组件 + trailing 插槽 |
| E4 | `ui/dict/rule/DictRuleScreen.kt:329-399`、`ui/autoTask/AutoTaskScreen.kt:345-420`、`ui/book/toc/rule/TxtTocRuleScreen.kt:337-411` | `DictRuleItemRow` / `AutoTaskItemRow` / `TxtTocRuleItemRow` | 三者互备（多选+开关+拖拽行），且应复用 `ListCard`/`SwipeActionContainer` | **三个页面逐字重复同一「72dp 高 + Checkbox + Switch + 拖拽手柄 + Edit/Delete/More」行实现**（surface 底 + combinedClickable + secondaryContainer α0.4 选中态），拖拽部分 3 份拷贝 | 沉淀公共 `SettingsSelectableRow`（受控 Checkbox/Switch/拖拽回调）或统一复用 `ListCard` + 拖拽排序模式（§3 已列为 🆕 规范），三页收敛 |
| E5 | `ui/about/AboutScreen.kt:216-229` | `AboutSectionHeader` | `SettingsSection` | 私有分组标题复制公共组件，且**规格偏离真值表**：公共版 = labelLarge Bold **primary** + top12/h16v6；私有版 = titleSmall Bold **onSurfaceVariant** + start16/top16/bottom8 | 改引 `SettingsSection` |
| E6 | `ui/about/AboutScreen.kt:167-210` | `AboutSummaryCard` | ~~`SummaryCard`~~（已删除） | 摘要卡私有实现已注释登记（公共 `SummaryCard` 2026-08-16 孤儿清理删除，API 无法承载公众号高亮+点击复制，保留私有实现） | 豁免登记（已注释） |
| E7 | `ui/about/ReadRecordScreen.kt:293-299` + `ui/main/my/ProfileScreen3Level.kt:260-274` | `formatDuring`（×2 私有工具） | 应提取公共工具 | 同名私有工具函数两处重复，且硬编码中文「天/小时/分钟/秒/0秒」（**P4 规范 V2 已登记**，仍未修） | 提取公共 `FormatUtil.formatDuring`，文案迁 strings.xml 双语（en+zh） |
| E8 | `ui/debug/` 全目录 7 页 | 私有卡片组件 10 个：`RegexTestScreen.kt:640/702/750/792`(StatusCard/MatchInfoCard/HighlightCard/ReplacePreviewCard)、`PingTestScreen.kt:578/614/645`(PingResultItem/StatChip/StatItem)、`CurlTestScreen.kt:459/473`(ParsedItem/ResponseStatItem)、`DebugToolsScreen.kt:135`(DebugToolItem) | 未引用任何公共组件 | **debug 族 7 页公共组件引用数 = 0**，全部私有实现，且 `RegexTestScreen.kt:647-651` 硬编码成功/失败色 | 至少对齐卡 18dp / 间距 16dp / colorScheme 基线；后续按需接 `ListCard`/`EmptyStatePlaceholder` |

### 3.2 WARN 级：硬编码圆角未引用 AppShapes token（共 81 处使用点，抽样全部文件）

> 数值多已对齐 §1 基线（按钮 12 / 卡 18 / Sheet 16），**核心问题是未符号化为 `AppShapes.*`**。按文件列出（`=` 后为硬编码 dp 值）：

| 文件 | 行号 | 值 | 应替换为 |
|------|------|-----|---------|
| `ui/debug/CurlTestScreen.kt` | 217, 332, 385 | 12 | `AppShapes.Button` |
| `ui/debug/DebugToolsScreen.kt` | 148 | 12 | `AppShapes.Button` |
| `ui/debug/DebugToolsScreen.kt` | 158 | 10 | `AppShapes.IconContainer` |
| `ui/debug/EncodeToolsScreen.kt` | 97, 154, 269 | 12 | `AppShapes.Button` |
| `ui/debug/HttpDebugScreen.kt` | 307, 367, 425, 455, 554, 593 | 12 | `AppShapes.Button` |
| `ui/debug/PingTestScreen.kt` | 129, 342, 386, 460, 540 | 12 | `AppShapes.Button` |
| `ui/debug/PingTestScreen.kt` | 319 | 4 | `AppShapes.Tiny` |
| `ui/debug/PingTestScreen.kt` | 581 | 8 | `AppShapes.Chip` |
| `ui/debug/PingTestScreen.kt` | 622 | 16 | `AppShapes.SheetTop` 或容器 |
| `ui/debug/RegexTestScreen.kt` | 330, 446, 474, 656, 711, 758, 801 | 12 | `AppShapes.Button` |
| `ui/debug/TimestampConvertScreen.kt` | 131, 197, 250, 333 | 12 | `AppShapes.Button` |
| `ui/highlight/HighlightRuleScreen.kt` | 219 | 8 | `AppShapes.Chip` |
| `ui/book/bookmark/AllBookmarkScreen.kt` | 147 | 8 | `AppShapes.Chip` |
| `ui/main/bookshelf/BookshelfScreen.kt` | 255 | **6（非 token 值）** | `AppShapes.Chip` 或 Tiny |
| `ui/main/bookshelf/BookshelfScreen.kt` | 339 | 8 | `AppShapes.Chip` |
| `ui/book/explore/ExploreShowScreen.kt` | 304 | 4 | `AppShapes.Tiny` |
| `ui/video/VideoSettingsPanelContent.kt` | 101 | **2（非 token 值）** | 收敛至 Tiny 或登记 |
| `ui/video/VideoSettingsPanelContent.kt` | 194, 412 | 8 | `AppShapes.Chip` |
| `ui/book/source/manage/BookSourceItems.kt` | 196 | 12 | `AppShapes.Button` |
| `ui/book/source/manage/BookSourceItems.kt` | 235, 242 | 18 | `AppShapes.Card` |
| `ui/book/source/manage/BookSourceItems.kt` | 326 | 8 | `AppShapes.Chip` |
| `ui/book/source/manage/BookSourceItems.kt` | 374 | 4 | `AppShapes.Tiny` |
| `ui/book/source/edit/BookSourceEditActivity.kt` | 438 | **6（非 token 值）** | `AppShapes.Chip` |
| `ui/book/source/edit/BookSourceEditActivity.kt` | 541, 553 | 12 | `AppShapes.Button` |
| `ui/book/info/BookInfoActivity.kt` | 343, 362 | 12 | `AppShapes.Button` |
| `ui/replace/edit/ReplaceEditActivity.kt` | 162, 169 | 12 | `AppShapes.Button` |

**components 目录内部仍硬编码圆角（AppShapes 刚建未回迁，共 10 文件 21 处）**：

| 文件 | 行号 | 值 |
|------|------|-----|
| `components/ImportSourceSheet.kt` | 215, 231, 240 | 12 |
| `components/ImportSourceSheet.kt` | 326 | 8 |
| `components/HeatmapCalendar.kt` | 349, 356, 362, 438, 475 | 8 |
| `components/HeatmapCalendar.kt` | 416 | **3（非 token 值）** |
| `components/LazyListFastScroller.kt` | 118, 145 | **9（非 token 值）** |
| `components/HighlightStyleSheet.kt` | 159, 248 | 8 |
| `components/HighlightStyleSheet.kt` | 258 | 4 |
| `components/ListLayoutMenu.kt` | 104 | 8 |
| `components/ReaderMoreActionsSheet.kt` | 139 | 12 |
| `components/ShelfGridSkeleton.kt` | 83 | 10 |
| `components/ShelfGridSkeleton.kt` | 91, 99, 155, 162 | 4 |
| `components/ShelfGridSkeleton.kt` | 143 | 8 |
| `components/TextActionSelectionMenu.kt` | 56 | 12 |
| `components/TextActionSelectionMenu.kt` | 119 | 8 |

> 已正确引用 AppShapes 的组件（10 处）：`AppAlertDialog.kt:49`、`AlertBuilder.kt:149`、`AppModalBottomSheet.kt:39`、`HeatmapCalendar.kt:165`、`MetricGrid.kt:69/79`、`RowIcon.kt:28`、`SettingsCard.kt:34`、`SettingsSearchBar.kt:45`。

### 3.3 WARN 级：硬编码颜色 `Color(0x...)` 未走 colorScheme（约 30 处）

| 文件:行 | 颜色用途 | 问题与建议 |
|---------|---------|-----------|
| `ui/download/DownloadManageScreen.kt:323-324` | 下载状态色 0xFF43A047/0xFFE53935 | 注释自述「语义状态色…不随主题变化」——**与 §1.2 语义色规范冲突**（error 应走 M3 标准红/colorScheme），建议收敛为 colorScheme（如 `MaterialTheme.colorScheme.primary`/`error`）或 ThemeSpec 语义槽位 |
| `ui/book/explore/ExploreShowScreen.kt:251` | 书架内绿点 0xFF4CAF50 | 状态指示色，建议 colorScheme.primary/tertiary |
| `ui/urlrecord/UrlRecordScreen.kt:281-293` | HTTP 方法/状态色 7 处（1E88E5/8E24AA/F57C00/E53935/43A047/FB8C00） | 语义状态色，建议收敛至 ThemeSpec 语义槽位或登记豁免 |
| `ui/debug/CurlTestScreen.kt:361-362` | HTTP 状态码色 4CAF50/FF9800 | 同上 |
| `ui/debug/RegexTestScreen.kt:209, 647-651` | 高亮黄 0x40FFEB3B / 成功绿 4CAF50 / 失败红 F44336 | 高亮/状态色，建议走 colorScheme |
| `ui/debug/PingTestScreen.kt:432, 500-501, 580, 594` | Ping 状态色 4CAF50/FF9800 | 同上 |
| `ui/main/bookshelf/BookshelfItems.kt:68-75` | 封面定色 8 色 | ✅ 已登记豁免（§1.1 例外①） |
| `ui/book/source/manage/BookSourceItems.kt:366-369` | 类型徽章色 4CAF50/2196F3/FF9800/E53935 | ✅ 已登记豁免（§1.1 例外④） |
| `ui/widget/components/ThemeSpec.kt:68, 89` | 主题转换 error 色 | ✅ 正常（主题派生源头） |

### 3.4 INFO 级：轻微不一致

| 文件:行 | 问题 |
|---------|------|
| `ui/about/AboutScreen.kt:174+178` | `AboutSummaryCard` 双重 `padding(12)+padding(12)`=24dp，非 16dp 基线（随 E6 一并豁免登记（注释）） |
| `ui/main/my/ProfileScreen3Level.kt:103-109` | 加载态用居中 `CircularProgressIndicator`（P4 规范 V3 已登记，应换 LinearProgress/骨架） |
| `ui/main/my/ProfileScreen3Level.kt:79-80` | 服务开关状态不观察 EventBus（P4 规范 V4 已登记） |
| `ui/main/bookshelf/BookshelfScreen.kt:372` | 封面用 `MaterialTheme.shapes.small`（M3 默认 8dp），与 AppShapes 体系未显式对齐 |
| `ui/main/bookshelf/BookshelfScreen.kt:394` | 书名遮罩 `Color.Black α0.55` 硬编码黑——属内容遮罩，可登记豁免或走 colorScheme.scrim |

---

## 4. 公共 token 命中率统计

| 指标 | 数值 | 说明 |
|------|------|------|
| 全仓 import 公共组件文件数 | **74 文件 / 264 处引用** | 含 Activity/Fragment/Dialog/Adapter |
| Compose 页面（`*Screen.kt`，31 个）引用公共组件 | **23 个 / 31 个 = 74.2%** | 8 个零引用（见下） |
| 零引用公共组件的 Screen | **8 个** | `WelcomeScreen` + debug 族 7 个（TimestampConvert/RegexTest/PingTest/HttpDebug/EncodeTools/DebugTools/CurlTest） |
| AppShapes 圆角 token 引用 | **11 处**（9 个组件） | 刚建当日，存量未回迁 |
| 硬编码 `RoundedCornerShape(X.dp)` 使用点 | **81 处** | 其中非 token 值（2/3/6/9dp）5 类 9 处 |
| 硬编码 `Color(0x...)` | **约 30 处** | 豁免登记 10 处，违规约 20 处 |
| 已接线样板页（合规标杆） | `ProfileScreen3Level`、`BookSourceScreen`、`ReplaceRuleScreen` | 复用率高、无私有复制（E7 除外） |

**命中率评价**：设置族/顶栏/菜单/Dialog 族 token 命中率最高（样板页全复用）；**重灾区 = debug 工具族 7 页（0 命中）+ 列表管理页私有行（E3/E4）+ 圆角 token 回迁未完成**。

---

## 5. 建议修复优先级清单

**P0（文档-代码一致性）✅ 已完成（2026-08-16）**
1. E1 `BookshelfScreen.ShelfUnreadBadge` → 改引 `BadgeDot`（§3.1 声称已接线但代码残留，先对齐文档）
2. E5/E6 `AboutScreen` 私有 `AboutSectionHeader`/`AboutSummaryCard` → E5 改引 `SettingsSection`；E6 豁免登记（公共 `SummaryCard` 已删除）
3. E7 `formatDuring` 双份私有工具 → 提取公共工具 + strings.xml 双语（P4 V2 长期遗留）

**P1（跨页重复收敛）✅ 已完成（2026-08-16）**
4. E4 三个 72dp 多选+开关+拖拽行（DictRule/AutoTask/TxtTocRule）→ 沉淀公共 `SettingsSelectableRow`
5. E2 `TagChip` 同名双实现 → 收敛公共 TagChip（AppShapes.Chip）
6. E3 `StorageManageItemRow` → SettingsClickRow trailing 插槽化

**P2（token 回迁：AppShapes 圆角回迁）✅ 已完成（2026-08-16，81 处）**
7. components 目录 10 文件 21 处硬编码圆角 → AppShapes（含非 token 值 2/3/9dp 收敛）
8. debug 族 7 页 30+ 处 `RoundedCornerShape(12.dp)` → `AppShapes.Button`；顺带接入 EmptyStatePlaceholder 等
9. 页面层 50+ 处硬编码圆角 → AppShapes（逐文件替换）

**P3（颜色/间距收敛）✅ 已完成（2026-08-16，并行子代理执行 + 主代理复核）**
10. 状态语义色硬编码（Download/UrlRecord/RegexTest/PingTest/CurlTest 约 20 处）→ colorScheme 或 ThemeSpec 语义槽位 —— **已全量收敛**（主代理复核确认）：Download 状态色 → primary/error；UrlRecord 方法/状态色 → primary/tertiary/error；CurlTest 状态码色 → primary/tertiary/error；RegexTest 成功/失败 → primary/error（高亮黄 0x40FFEB3B 已登记豁免 §3.3）；PingTest 丢包/状态色 → primary/tertiary/error；ExploreShow 书架绿点 → primary；BookshelfScreen 书名遮罩 Color.Black α0.55 → colorScheme.scrim。全仓 Compose `Color(0x...)` 现仅剩：豁免登记（BookshelfItems 封面定色/BookSourceItems 类型徽章/RegexTest 高亮）+ 主题派生源头（ThemeSpec）+ 合理内容色（白色遮罩文字/BadgeDot 黑白自适应字）
11. §3 组件目录表按实际 55 文件全量回填登记（含孤儿状态；2026-08-16 孤儿清理后）—— ✅ 已完成（ui-standards.md v2.19 回填 59 文件 + v2.20 孤儿清理后对齐）
12. debug 族私有卡片组件登记豁免或接入公共组件 —— ✅ 已完成（debug 7 页 P2 已接入 EmptyStatePlaceholder/AppShapes，私有卡片按 §3.3/§4 登记）

---

## 6. 附：审计方法与限制

- 纯静态扫描，未运行/未改代码；行号为扫描当日 commit 状态。
- `Color(0x...)` 覆盖 8 位 ARGB 与 6 位 RGB；`RoundedCornerShape` 覆盖 0-18dp 全部硬编码；padding 档位以 4dp grid（4/8/12/16/24/32）人工核对。
- 阅读器内核（ReadBookConfig 独立配色）不在本巡检范围（§1.2 红线）。

---

## 7. 修复进度跟踪（2026-08-16 更新）

> 本节登记审计后的修复进度（深化迭代 12.19 收尾，2026-08-16 更新）。

| 优先级 | 修复内容 | 状态 |
|--------|---------|------|
| **P0** | E1 BadgeDot（ShelfUnreadBadge 保留但 badgeTextBright 黑白字自适应收敛，文档对齐）/ E5 SettingsSection（AboutScreen 改引公共组件）/ E6 SummaryCard（AboutSummaryCard 加「简化说明」注释登记不改引）/ E7 FormatUtils（提取公共 `utils/FormatUtils.kt::formatDuring`） / **孤儿组件清理（2026-08-16）**：删除 SummaryCard/ThemedSnackbarHost/SplicedColumnGroup/ManageScreenSheet；VerticalScrollbar 接线 DownloadManageScreen；ListScaffold 保留模板待用 | ✅ 已完成（2026-08-16） |
| **P1** | E4 SettingsSelectableRow（沉淀公共组件，DictRule/AutoTask/TxtTocRule 三页接线）/ E2 TagChip（沉淀公共组件，ExploreShow/ImportBook 两页接线）/ E3 SettingsClickRow trailing 插槽化 | ✅ 已完成（2026-08-16） |
| **P2** | components 目录 10 文件 21 处 + debug 族 7 页 + 页面层硬编码圆角全部回迁 `AppShapes`（共 81 处） | ✅ 已完成（2026-08-16） |
| **P3** | 颜色/间距收敛（Download/UrlRecord/RegexTest/PingTest/CurlTest 等约 20 处语义色 → colorScheme/ThemeSpec 语义槽位；§3 组件目录回填；debug 私有卡片登记） | ✅ 已完成（2026-08-16，并行子代理执行 + 主代理复核：语义色全量收敛至 colorScheme，剩余均为豁免/主题源头/合理内容色） |
| **孤儿清理** | 删除 SummaryCard/ThemedSnackbarHost/SplicedColumnGroup/ManageScreenSheet 4 个无消费场景孤儿组件；VerticalScrollbar 接线 DownloadManageScreen（下载管理页长列表滚动指示条）；ListScaffold 保留模板待用（task 12.30） | ✅ 已完成（2026-08-16） |

> 备注：P0/P1/P2 源码改动由并行实施子代理完成；P3 完成后在 tasks.md V-10 条目统一勾选（tasks.md 无 12.1A 编号，原稿误标已修正，见 §1）。
