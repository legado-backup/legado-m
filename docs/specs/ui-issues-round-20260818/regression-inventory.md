# 功能裁剪回溯清单（regression-inventory）

> spec：`ui-issues-round-20260818`（UI 问题综合整改）
> 基线：`897b42f95`（2026-08-02，8 月 4 号前最新）→ 对比 HEAD `aa1170a08`
> 审计方式：只读 `git diff/log/show` + 当前源码核实，证据链见 `docs/temp-analysis/regression-diff.md`
> 判定三态：✅ 存在 / ⚠️ 降级（DEGRADED）/ ❌ 不存在（CUT）
> 红线（AD-06）：只恢复不新增；恢复项逐条真机回归并登记回执

---

## 一、❌ 明确裁剪（CUT，5 项）

| # | 功能 | 基线（8/2） | 现状 | 证据 | 优先级 | 恢复方案 | 恢复回执 |
|---|------|------------|------|------|-------|---------|---------|
| C1 | **主题模式四态选择器**（跟随系统/日间/夜间/**墨水屏**） | `pref_main.xml` themeMode NameListPreference 4 选项（arrays theme_mode 0-3） | `PreferKey.themeMode`/`AppConfig.themeMode`/`AppContextWrapper` 读取逻辑仍在，但全工程无 UI 入口；`ThemeConfigFragment` 仅日/夜二态 toggle；**墨水屏入口丢失**、"跟随系统"不可选 | `ThemeConfigFragment.kt:186-194`；`AppConfig.kt:46,56`；`AppContextWrapper.kt:33-42` | 🔴 高 | `ThemeConfigFragment` 日/夜二态 → 四态 NameListPreference，复用现有逻辑 | ⬜ |
| C2 | **欢迎页文字/图标显隐 4 开关** | `pref_config_welcome.xml`：日 `welcomeShowText`/`welcomeShowIcon` + 夜 `welcomeShowTextDark`/`welcomeShowIconDark`（显示时长/自定义欢迎/日/夜背景图已保留） | `WelcomeConfigScreen` 仅 显示时长 Slider/自定义欢迎/日/夜背景图 4 项，4 个显隐开关 UI 被注释裁剪；`WelcomeActivity` 仍读 key（默认 true）→ 用户无法再控制 | `WelcomeConfigScreen.kt:40-55,64-143`；`WelcomeActivity.kt:92-105`；`AppConfig.kt:1099-1126` | 🟠 中 | `WelcomeConfigScreen` 补日/夜 4 个 `SettingsToggleRow`（P3-1.2） | ⬜ |
| C3 | **书源排序「最近更新/自动/响应时间」** | `book_source.xml` 排序子菜单 7 项（倒序/手动/自动/名称/地址/最近更新/响应时间/启用） | `BookSourceScreen.kt:161-168` 仅 6 项 `ListSortOption("0".."5")`；`sortSources` 中 `bookSourceSort==6 -> lastUpdateTime` 逻辑仍在但 UI 无入口；自动/响应时间仅留旧回退分支 | `BookSourceScreen.kt:161-168`；`BookSourceActivity.kt:567-607` | 🟠 中 | `ListSortOption` 补 `"6"`（最近更新）（P3-1.3） | ⬜ |
| C4 | **切换桌面图标（launcherIcon）** | `pref_config_theme.xml` launcherIcon IconListPreference + `LauncherIconHelp.changeIcon()` | 字符串/数组资源仍在，无任何 UI/代码引用，`LauncherIconHelp` 无调用方 | `ThemeConfigScreen.kt` 无该行；Grep `launcherIcon` 仅命中资源 | 🟡 低 | `ThemeConfigScreen` 补 `SettingsClickRow`（P3-1.4） | ⬜ |
| C5 | **捐赠入口（DonateActivity）** | `activity_donate.xml` + DonateActivity + DonateFragment | 布局与类全删，Grep `Donate` 0 命中 | `git show 897b42f95:res/layout/activity_donate.xml` | 🟡 低 | 视用户意愿决定是否恢复 | ⬜ |

## 二、⚠️ 降级（DEGRADED，5 项）

| # | 功能 | 基线 | 现状 | 证据 | 决策 |
|---|------|------|------|------|------|
| D1 | 书源管理文件夹视图 | 可切换文件夹视图 | `isFolderViewMode` 硬编码 `false`（注释指向 spec AD-03 决策），`folderItems` 恒空，配置弹窗 `showGroupStyle=false` | `BookSourceActivity.kt:133-134,166,195,463-471,640,944-951` | 与问题4 批量分组设计冲突 → P1 一并决策（批量分组基于「分组」维度，不依赖文件夹视图开关） |
| D2 | 书源管理拖拽滑选 | 长按进入滑选拖动区间 | `DragSelectTouchHelper/ItemTouchHelper` 移除（注释"纯死接线"），现为点击/长按单点多选 | `BookSourceActivity.kt:387,296-305` | 暂不处理（低优先级） |
| D3 | 书架 style2 快速索引条 FastScroller | `setFastScrollEnabled(showBookshelfFastScroller)` | style1 `BooksFragment.kt:189-192` 保留 ✅；style2 Compose `BookshelfScreen` 无 FastScroller 覆盖层 | `style2/BookshelfFragment2.kt:67,103`；`BookshelfScreen.kt:141,314,525` | 列为 Compose 增强项，非本批次回归重点 |
| D4 | 文件管理入口 | `pref_main.xml` 一级入口 | `ProfileScreen3Level`「其他」组无文件管理行；改为 我的→精准管理→文件管理（深一层） | `ProfileScreen3Level.kt:211-247`；`PreciseManageScreen.kt:76-77` | 暂不处理（可达性 OK） |
| D5 | 书源筛选（启用/禁用探索） | `book_source.xml` 分组子菜单 | `BookSourceMoreMenu` 无此项，降为搜索框快捷词 `enabled_explore`/`disabled_explore` | `BookSourceScreen.kt:416,428`；`BookSourceViewModel.kt:205` | 暂不处理（低优先级） |

## 三、✅ 已核实无裁剪（PRESERVED，15 项）

| 功能域 | 结论 | 证据 |
|--------|------|------|
| 底部导航 4 Tab（书架/发现/订阅/我的） | ✅ 完整 | `MainActivity.kt:85,94,385-438`（RSS 仍受 `showRSS` 控制） |
| 书架页 12 项菜单 | ✅ 完整 | `BaseBookshelfFragment.kt:156-198` |
| 发现页（文件夹配置/分组筛选） | ✅ 完整 | `ExploreFragment.kt:258-268` |
| 订阅页（文件夹配置/历史/收藏/分组/设置） | ✅ 完整 | `RssFragment.kt:274-311` |
| 书源管理主菜单 | ✅ 完整 | `BookSourceActivity.kt:238-250` |
| 书源批量操作 | ✅ 完整 | `BookSourceActivity.kt:320-338` |
| 书源编辑页 15 项菜单 | ✅ 完整 | `BookSourceEditActivity.kt:245-341` |
| 订阅源编辑页 | ✅ 完整 | `RssSourceEditActivity.kt:194` |
| 订阅源管理页（排序/筛选/设置） | ✅ 完整 | `RssSourceActivity.kt:188-279` |
| 视频播放页 | ✅ 完整 | `VideoPlayerActivity.kt:564-697` |
| 音频播放页 | ✅ 完整 | `AudioPlayActivity.kt:147-255` |
| 关于页 | ✅ 完整 | `AboutScreen.kt:49-80` |
| 主题设置页 | ✅ 完整 | `ThemeConfigScreen.kt` |
| 备份恢复/其他设置入口 | ✅ 完整 | `ProfileScreen3Level.kt:119-150` |
| 高亮样式/背景图模糊 | ✅ 完整 | `HighlightStyleSheet.kt`；`ThemeConfigScreen.kt:414-470` |

---

## 四、实施状态汇总

| 状态 | 计数 | 说明 |
|------|------|------|
| ❌ CUT 待恢复 | 5 | C1（高）→ C2/C3（中）→ C4/C5（低），P3-1 逐项恢复 |
| ⚠️ DEGRADED | 5 | D1 需 P1 决策；D2/D4/D5 暂不处理；D3 增强项 |
| ✅ PRESERVED | 15 | 已核实，无需动作 |
