# 原版 showAsAction 对照表（showasaction-audit）

> 生成：2026-08-28（tasks 1.4）｜基线：archive-ref/legado-08172114 res/menu/*.xml（59 文件/87 个 always 项）vs 本项目现版逐页判定
> 用途：tasks 3.x 全部批次修复与 3.5 批E 裁决的唯一依据
> 修复原则（tasks 0.3）：原 always→一级图标；原 never→下拉；D 类重构页与有意进化登记"保留现状"+理由

## B 类收拢回归（18 页/25 项，逐项处置）

| # | 页面 | 原版 menu | 原动作 | 原级别 | 现版实现 | 拟恢复级别 | 组件系 | 处置批次 |
|---|------|-----------|--------|--------|----------|-----------|--------|---------|
| 1 | 备份/恢复页 | backup_restore.xml:11 | menu_help(问号) | always | ConfigTopBar MoreVert 下拉（BackupConfigFragment.kt:133-138） | P0 恢复一级 | ① ConfigTopBar 系 | 批A 3.1① |
| 2 | 主题设置页 | theme_config.xml:5-9 | menu_theme_mode(亮度) | always | ConfigTopBar MoreVert 下拉（ThemeConfigFragment.kt:32-39） | P0 恢复一级 | ① ConfigTopBar 系 | 批A 3.1② |
| 3 | 订阅源编辑 | source_edit.xml:11/17/23 | menu_fullscreen_edit/menu_save/menu_debug_source(代码/保存/调试) | always×3 | GlassTopAppBar MoreVert 下拉（RssSourceEditActivity.kt:173-188） | P0 恢复一级×3 | ② GlassTopAppBar 系 | 批B 3.2① |
| 4 | 替换编辑 | replace_edit.xml:11/17 | menu_fullscreen_edit/menu_save | always×2 | GlassTopAppBar 下沉下拉（ReplaceEditActivity.kt:121-133） | P0 恢复一级×2 | ② GlassTopAppBar 系 | 批B 3.2② |
| 5 | 书源编辑 | source_edit.xml:11/17/23 | 代码/保存/调试 | always×3 | View TitleBar moreButton 弹 ModernActionPopup(R.menu.source_edit)（BookSourceEditActivity.kt:125-144） | P0 恢复一级×3 | ④ View TitleBar 系 | 批B 3.2③ |
| 6 | "我的" tab | main_my.xml:10 | menu_help(ic_help) | always | MainTopBarView Mode.MY moreButton 点击直接 showHelp("appHelp")（MyFragment.kt:120，语义不符非死按钮） | P0 恢复一级问号 | ③ MainTopBarView 系 | 批D 3.4① |
| 7 | txt_toc 规则管理 | txt_toc_rule.xml:10 | menu_add(ic_add) | always | GlassTopAppBar MoreVert 下拉（TxtTocRuleScreen.kt:121-135 / TxtTocRuleActivity.kt:151-155） | P1 恢复一级 | ② GlassTopAppBar 系 | 批C 3.3 |
| 8 | 字典规则管理 | dict_rule.xml:11 | menu_add(ic_add) | always | GlassTopAppBar MoreVert 下拉（DictRuleScreen.kt:113-129 / DictRuleActivity.kt:145-150） | P1 恢复一级 | ② GlassTopAppBar 系 | 批C 3.3 |
| 9 | 缓存/下载页 | book_cache.xml:11/17 | menu_download(ic_play)+menu_book_group(分组) | always×2 | 下载保留一级✓；分组下沉 AppDropdownMenu（CacheActivity.kt:156-176） | P1 恢复分组一级（下载已达标） | ② GlassTopAppBar 系 | 批C 3.3 |
| 10 | WebDav 书仓 | book_remote.xml:11/16 | menu_refresh+menu_sort | always×2 | menuActions 6 项全进 ImportBookScreen MoreVert（RemoteBookActivity.kt:109-167 / ImportBookScreen.kt:89-99） | P1 恢复一级×2 | ② GlassTopAppBar 系 | 批C 3.3 |
| 11 | 本地导入 | import_book.xml:11/17 | menu_select_folder+menu_sort | always×2 | 同上 ImportBookScreen MoreVert（ImportBookScreen.kt:89-99） | P1 恢复一级×2 | ② GlassTopAppBar 系 | 批C 3.3 |
| 12 | 订阅收藏夹 | rss_favorites（原版 menu_group always） | menu_group(分组) | always | GlassTopAppBar MoreVert 下拉（RssFavoritesActivity.kt:88-108） | P1 恢复一级 | ② GlassTopAppBar 系 | 批C 3.3 |
| 13 | 订阅 tab | main_rss.xml:10/16/22/32 | 历史/星标/分组/设置 | always×4 | 星标并入一级星标按钮✓；历史/分组/设置走 moreButton 弹 ModernActionPopup（RssFragment.kt:950-962） | P1 按原版恢复历史/分组/设置（星标已达标） | ③ MainTopBarView 系 | 批D 3.4② |
| 14 | 书籍信息页 | book_info.xml:9/15/21/27/38 | 编辑/分享/刷新/自定义/云模式 | ifRoom×6 | GlassTopAppBar MoreVert 下拉（BookInfoActivity.kt:298-316） | E 判定型 | ② GlassTopAppBar 系 | 批E 3.5 |
| 15 | 视频播放页 | video_play.xml:19/26 | menu_float_window(浮窗) | 动态 | 浮窗进 MoreVert 下拉第一项；刷新/收藏/自定义动态保留一级（VideoPlayerActivity.kt:675-698,733-738） | E 判定型 | ② GlassTopAppBar 系 | 批E 3.5 |
| 16 | 发现 tab(modern) | main_explore.xml:9 | menu_group(分组) | always | modern/suite 形态 menu 不 inflate，分组走 ModernActionPopup（ExploreFragment.kt:341-350,3617-3623） | E 判定型 | ② GlassTopAppBar 系 | 批E 3.5 |
| 17 | 换源弹窗 | change_source.xml:11/18 | menu_screen(筛选)/menu_start_stop | always | 筛选并入页内 SettingsSearchBar+MoreVert；启停保留一级✓（ChangeBookSourceDialog.kt:370,405-475） | E 判定型 | ② GlassTopAppBar 系 | 批E 3.5 |
| 18 | 内容编辑弹窗 | content_edit.xml+dialog_text.xml | menu_save；全屏编辑/关闭 | always | 保存一级✓；全屏编辑/关闭无入口（ContentEditDialog.kt:123-167）→ 关联 C 类② | E 判定型（并入 C 类② 复核） | ② GlassTopAppBar 系 | 批E 3.5 |

## 批E 判定型页面裁决结果（tasks 3.5，2026-08-28 裁决登记）

| 页面 | 裁决 | 理由 |
|------|------|------|
| 书籍信息页 6 项 ifRoom | 维持现状（全下拉） | 原版 ifRoom=空间够则显示，Compose 无动态空间适配机制；360dp 窄屏返回键+6 图标挤爆顶栏，违背"一级图标 ≤3"分级标准；功能全部可达（下拉），登记为进化决策 |
| 视频播放页浮窗（动态） | 维持现状（下拉第一项） | 原版 video_play.xml 19 项为动态 visible，浮窗属低频动态项；刷新/收藏/自定义动态一级已保留 |
| 发现 tab modern 分组 | 维持现状（ModernActionPopup） | modern/suite 形态为本项目进化设计（menu 不 inflate 是有意行为），分组入口在 ModernActionPopup 可达 |
| 换源弹窗筛选 | 维持现状（页内 SettingsSearchBar） | 原版 menu_screen 为 SearchView 一级搜索框，现版页内搜索条形态进化且功能完整；启停一级已保留 |

## 排序类处置注记（WebDav/本地导入）

原版 menu_sort 为单项 always 点击弹排序子菜单；现版拆分为 2 个 checked 平铺项（按名/按更新时间或按名/按大小）。为保持 ImportBookScreen 双页（WebDav/本地）复用一致性与一级图标 ≤3 标准，排序项收敛下拉、仅刷新（WebDav）/选目录（本地）恢复一级——登记为轻量简化。

## C 类疑似彻底丢失（3 项，一律真机复核后裁决）

| # | 页面 | 原版 menu | 原动作 | 疑点 | 真机复核方向 |
|---|------|-----------|--------|------|-------------|
| C1 | 封面更换页 | change_cover.xml:10 | menu_start_stop(启停) | change_cover.xml 本项目死文件（R.menu 零引用），CoverCollectionManageActivity 顶栏未见启停一级按钮 | 真机进封面更换页确认启停入口是否存在 |
| C2 | 正文编辑弹窗 | dialog_text.xml:10/16 | menu_fullscreen_edit/menu_close | dialog_text.xml 死文件；ContentEditDialog 下拉仅 reset/copy_all，无全屏编辑入口 | 真机进正文编辑确认全屏编辑入口 |
| C3 | 主题管理页 | theme_list.xml:8 | menu_import(剪贴板导入) | "剪贴板导入"语义消失，仅剩手动配置/zip 导入（ThemeManageActivity.kt:404-421，可视为有意变更） | 真机进主题管理确认导入方式；剪贴板导入判有意进化则登记保留 |

## 保留现状登记（不修）

| 类别 | 页面 | 理由 |
|------|------|------|
| A 类正常（18 页） | 阅读页(View menu 5 always 保留)/漫画页/订阅源阅读页/听书页/代码编辑页/书源管理(topActions 排序分组新增一级)/订阅源管理/替换管理/规则订阅/书架管理/扫码/内置浏览器/分类文章/日志弹窗/换源启停/服务器配置/验证码/内容编辑保存 | 一级图标语义完好，无回归 |
| D 类重构页（5 页） | 分组管理(GroupManageComposeDialog)/WebDav 服务器(ServersDialog)/订阅阅读记录(ReadRecordDialog)/目录搜索(TocSearchField)/朗读引擎(SpeakEngineDialog) | 页面重构为 Dialog/页内形态，功能完整，非 showAsAction 语义回归 |
| 有意进化 | 订阅 tab 星标并入一级星标按钮；视频页刷新/收藏/自定义动态一级保留 | 新版交互优化且功能完整 |
