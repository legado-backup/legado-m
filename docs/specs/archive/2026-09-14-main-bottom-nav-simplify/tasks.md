# 主界面底栏精简 任务清单（tasks.md）

> 完成级别标记：[x] (L1) 代码完成+编译通过 / [x] (L2) 功能验证 / [x] (L3) 场景回测。所有"已删除/已清零"勾选须附 Grep 证据（模式 + 命中数）。

## 0. 准备

- [x] 0.1 备份：`git status` 确认工作区整洁；核心改动文件（MainActivity / MainBottomNavConfig / NavigationBarIconConfig / MySettingsData）均先 Read 确认再 Edit（并发安全铁律）
- [x] 0.2 全量引用盘点复核：Grep 确认引用清单（menu/ids/strings/layout/代码）与 design.md File Changes 一致
- [x] 0.3 `Get-Process` 校验无正在打包的构建进程（IDE JBR ×2 + 语言服务器，无 Gradle build 进程）后启动编译

## 1. 配置源头清理（统计 Tab 移除）

- [x] 1.1 `MainBottomNavConfig.kt`：删除 `KEY_READ_RECORD` 常量、`specs` 中 readRecord `ItemSpec`、`legacyInitialItems` 中 readRecord 项
  - 验证：Grep `KEY_READ_RECORD` 全库 0 命中（L2：模拟器底栏渲染 4 项通过）
- [x] 1.2 `NavigationBarIconConfig.kt`：删除 `items` 中 `NavItem("readRecord", R.string.side_nav_stats, R.id.menu_read_record, R.drawable.ic_bottom_read_record)`
  - 验证：Grep `"readRecord"` 于该文件 0 命中（遗留 BackupSelectorConfig/ReadRecord 表名/RedNavigationTarget 字符串为业务语义，非底栏项，保留）
- [x] 1.3 `MainActivity.kt` 硬编码分支清理：删 `idReadRecord`、`realPositions` 元素、`handleNavigationItemSelected` 分支、`sideNavigationButtonMap/RowMap/TextMap` 项、`sideNavigationTitle()` 特判、`getBottomNavigationItemId()` 分支、`TabFragmentPageAdapter` 分支与 import
  - 验证：Grep `menu_read_record|ReadRecordFragment` 在 MainActivity 0 命中（L2：底栏 4 项 + 侧栏无统计通过）

## 2. 统计页迁移（独立子页）

- [x] 2.1 新增 `activity_read_record_stats.xml`（FrameLayout 容器）
- [x] 2.2 新增 `ReadRecordStatsActivity.kt`：`BaseActivity` 宿主，容器承载 `ReadRecordFragment`（`standalone=true`），系统返回默认 finish；已注册 AndroidManifest
  - ⚠️ 红队 R5 注意已验证：standalone 模式 `position` 为 null，源码盘点页面内未引用 position，模拟器运行正常
  - 验证（L2）：编译通过 + 模拟器 direct launch 统计页渲染完整（2026年/月份标签/目标卡/概览）+ 返回按钮 finish 回主界面
- [x] 2.3 `ReadRecordFragment.kt` standalone 支持：`arguments?.getBoolean(ARG_STANDALONE, false)` 为 true 时 `addActionButton(R.drawable.ic_back, R.string.back) { requireActivity().finish() }`
  - 验证（L2）：模拟器 UI dump 出现 content-desc="返回" 可点击按钮，点击后 `mResumedActivity=MainActivity`
- [x] 2.4 `MySettingsData.kt`：「readRecord」路由 → `ReadRecordStatsActivity`，import 已更新

## 3. 主题/底栏设置体系联动

- [x] 3.1 `NavigationBarManageActivity.kt` 验证：`BottomNavItemsManageContent` 以 `MainBottomNavConfig.items()` 为数据源、`buildNavBarIconRows` 以 `NavigationBarIconConfig.items` 为数据源（Read 确认自动收敛）
  - 验证（L2）：模拟器底栏管理页「底栏按钮管理」弹窗仅 4 项（书架/发现/订阅/我的），无统计
- [x] 3.2 资源联动清理：`menu/main_bnv.xml` 删 `menu_read_record`；`ids.xml` 删对应 id；`activity_main.xml` 删 `sideNavReadRecord*` 三件套与 `@string/side_nav_stats` 引用
- [x] 3.3 死代码清理：`PreferKey.showReadRecord` + `AppConfig.showReadRecord` 删除；`side_nav_stats` 字符串删除（en/zh）
  - 验证：Grep `showReadRecord|side_nav_stats|menu_read_record|ic_bottom_read_record` 全库（排除 assets 构建产物）0 命中（L1 门禁）+ drawable 三文件删除

## 4. 搜索框默认隐藏（默认值链翻转）

- [x] 4.1 `AppConfig.kt`：`floatingBottomBarHideSearch` 默认 → `true`
- [x] 4.2 `MainLayoutPresetConfig.kt`：`floatingBottomBarHideSearch()` 默认 → `true`；`apply()` 写回 → `true`
- [x] 4.3 `NavigationBarIconConfig.kt`：`Config.hideSearchInFloatingStyle` 默认 → `true`（`defaultEntry` 自动跟随）
- [x] 4.4 `OtherConfigFragment.kt`：`floatingBottomBarHideSearch` switch `defaultValue` → `true`
- [x] 4.5 `AppearanceKitManager.kt`：`builtinKits()` KIT_FLOATING binding → `true`；KIT_FLOATING_NO_SEARCH 保留；L294/L657/L783/L1007-1019 核对：均为运行时动态读写 pref/绑定，无需改默认
- [x] 4.6 `NavigationBarManageActivity.kt` 验证：「搜索」编辑行读写 `config.hideSearchInFloatingStyle`（默认隐藏），能力保留（Read 确认）
- [x] 验证（L2）：模拟器默认（default 包+floating）主界面 dump 无 `search_button` 节点（0 命中）
  - 预期边界（红队 R2）：老用户**显式保存过** `floatingBottomBarHideSearch=false` 不受翻转影响——属"默认变更"预期语义，非缺陷

## 5. 我的页订阅源全局搜索入口移除

- [x] 5.1 `MySettingsData.kt`：删 `actionRow("rssSearch", ...)` 行（工具分组）
- [x] 5.2 `MySettingsData.kt`：删 `"rssSearch"` 路由与 import
  - 验证：Grep `"rssSearch"` / `RssSearchActivity` 于 MySettingsData 0 命中（L1）
- [x] 5.3 `RssFragment` 顶栏搜索按钮（`RssSearchActivity.start(requireContext(), null, buildSearchScope())`）未改动（Read 确认，能力保留）

## 6. 收尾

- [x] 6.1 updateLog.md 更新（"2026/09/14（主界面底栏精简）"，追加于 cronet版本 之后、已有条目之前，基于 git diff 真实变更）
- [x] 6.2 临时日志检查：本次变更零新增日志（无 Log/DebugLog 添加），无需清理
- [x] 6.3 文档同步：`docs/INDEX.md` 已登记（开发中）；四文档核对一致
- [x] 6.4 打包测试包：`gradlew assembleAppDebug` BUILD SUCCESSFUL（2 轮修错：R import / ARG_STANDALONE 顶层常量引用），测试包 `output/apk/test/legado_miss_app_3.26.091410.apk` 交付，MEmu 装机运行正常
- [x] 6.5 L2 模拟器验证：①底栏 4 项 ✓（menu_bookshelf/discovery/rss/my_config，无 menu_read_record）；②ReadRecordStatsActivity 统计页打开完整 + 返回按钮生效 ✓；③底栏管理页「底栏按钮管理」弹窗 4 项无统计 ✓；④默认底栏无 search_button 节点 ✓；⑤自定义套装「搜索」编辑行保留（静态，默认包只读未弹编辑）；⑥订阅源全局搜索静态移除（Grep 0 命中）；⑦订阅 Tab 顶栏搜索代码未动（静态）；⑧桌面小组件入口未动（静态）；⑨老配置兼容 `normalize()` 白名单过滤（静态，代码审查确认）
- [x] 6.6 Grep 证据汇总：`menu_read_record|side_nav_stats|ic_bottom_read_record|showReadRecord|KEY_READ_RECORD` 全库（排除 assets 构建产物）0 命中；`readRecord` 业务语义保留项（BackupSelectorConfig 表名备份 item / ReadRecord.kt 表名 "readRecord" / NavigationBarIconConfig RedNavigationTarget 字符串 / MySettingsData 行 key）不受影响
- [x] 6.7 检查点 2 最终验收（2026-09-14 用户"通过，验收并归档"）→ 已归档 `docs/specs/archive/2026-09-14-main-bottom-nav-simplify/`