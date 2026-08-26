# 主Tab头部搜索入口统一 — 实施任务（tasks.md）

## 1. 准备工作
- [x] 1.1 确认需求范围与用户偏好（订阅页为标准；书架去无效搜索框；我的页新建全屏搜索页；主题零破坏）
- [x] 1.2 阅读 MainTopBarView.setSearchEntryVisible / 书架基类 initComposeTopBar / MyFragment 全量 / MySettingsScreen / RssSearchActivity 范式（已完成，见 design.md）

## 2. 共享数据提取（MySettingsData.kt）
- [x] 2.1 新建 `MySettingsData.kt`（包 `io.legado.app.ui.main.my`），平迁以下逻辑为共享顶层函数（签名仅增加 Context/Activity 接收者，逻辑逐行保留）：
  - `buildSettingsSections(context)`（原 buildSections + actionRow）
  - `buildSettingsSubSearchItems(context)`（原 buildSubSearchItems + buildPreferenceXmlSearchItems + collectPreferenceAttr）
  - `buildSettingsThemeOptions(context)`（原 buildThemeOptions）
  - `Activity.handleSettingsRowClick(key, searchTarget)`（原 handleRowClick 全部分支）
  - 主题模式弹框/设置与 Web 服务启停/弹框（原 showThemeModeActions/setThemeMode/currentThemeModeLabel/setWebServiceEnabled/handleWebServiceClick/showWebServiceActions）提取为 Activity 扩展
- [x] 2.2 Grep 确认原 MyFragment 私有方法已被共享函数替代，无复制残留

## 3. 新增全屏设置搜索页（SettingsSearchActivity）
- [x] 3.1 新增 `activity_settings_search.xml`：单个全屏 ComposeView
- [x] 3.2 新增 `SettingsSearchActivity.kt`（BaseActivity）：
  - `LegadoTheme { Column { GlassTopAppBar(返回箭头+标题) ; SettingsSearchBar(searchQuery, 自动聚焦) ; MySettingsScreen(sections/subSearchItems/searchQuery/回调) } }`
  - 回调接共享路由（handleSettingsRowClick / 主题模式弹框 / Web 服务）
  - companion `start(context)`
- [x] 3.3 AndroidManifest.xml 注册 SettingsSearchActivity（`windowSoftInputMode="adjustResize|stateHidden"`）
- [x] 3.4 strings.xml 补充搜索页标题/占位符资源（若缺），无硬编码中文
- [x] 3.5 SettingsSearchActivity 状态刷新（AD-05）：`registerOnSharedPreferenceChangeListener`（PreferKey.themeMode→刷新 themeModeState；PreferKey.webService→启停+刷新）+ `observeLiveBus(EventBus.WEB_SERVICE)`；onDestroy 注销
- [x] 3.6 grep `my_search_hint` 引用范围，确认 MyFragment 移除 `setSearchHint` 后无残留引用；清理死代码清单记入 4.2（无残留引用，已删除 values/values-zh 两处资源定义）

## 4. 我的页面收敛（MyFragment + 布局）
- [x] 4.1 `MyFragment.initTopBar()`：追加 `topBar.setSearchEntryVisible(false)`；searchButton → `SettingsSearchActivity.start(requireContext())`；移除 searchEntry 就地展开绑定
- [x] 4.2 删除就地搜索代码：settingsSearchView / showSettingsSearch / initSearchView / applySearchBarStyle / applySearchQuery / searchQueryState（Grep 确认无残留）
- [x] 4.3 `installComposeContent()`：searchQuery 传空串、回调改指共享函数；sections/subSearchItems/themeOptions 改用共享构建函数
- [x] 4.4 `fragment_my_config.xml` 删除 `view_search` include 与无用 import（SearchView/TopBarSearchStyle/uiTypeface 等）

## 5. 书架页收敛
- [x] 5.1 `BaseBookshelfFragment.initComposeTopBar()` 追加 `topBar.setSearchEntryVisible(false)`，注释说明仅保留 searchButton 入口

## 6. 编译与静态验证
- [x] 6.1 启动前 Get-Process 校验无构建进程占用（仅 IDE JDT/redhat 语言服务器，白名单不处理）
- [x] 6.2 增量编译 `compileAppDebugKotlin`（或 `assembleAppDebug`），无编译错误（2 轮修复：XML 闭合标签 + internal 可见性/接收者）
- [x] 6.3 Grep `setSearchEntryVisible(false)` 确认书架/我的两处变更存在；Grep 确认 MyFragment 无残留 settingsSearchView/showSettingsSearch 引用
- [x] 6.4 Grep `android.util.Log.d|android.util.Log.e` 确认无新增调试日志
- [x] 6.5 逻辑走查：regular 风格书架/我的头部无胶囊；订阅页未调用 setSearchEntryVisible(false) 不受影响（RssFragment 566 行为 hasSearch 动态控制）

## 7. 真机/模拟器验证（Level 2）
- [ ] 7.1 书架页：头部仅搜索按钮→点击打开搜索页；style1/style2 均验证
- [ ] 7.2 我的页面：头部仅搜索按钮→点击打开全屏设置搜索页，搜索框自动聚焦，输入实时过滤
- [ ] 7.3 搜索页点击结果行跳转目标正确；主题切换后搜索页样式随动（主题零破坏验证）
- [ ] 7.4 订阅页回归：searchEntry/searchButton 打开 RssSearchActivity 行为不变
- [ ] 7.5 经典（default）顶栏风格下书架/我的头部无搜索框残留、按钮正常

## 8. 收尾与文档同步
- [ ] 8.1 基于 git diff 更新 `app/src/main/assets/updateLog.md`
- [ ] 8.2 更新 docs/INDEX.md 活跃 Specs 描述（header-search-unify 状态）
- [ ] 8.3 编译后执行 `stop-daemons.bat` 清理构建 daemon
- [ ] 8.4 核对 docs/project-flow/ 相关文档一致性（本次不涉及 WebBook/数据库/RuleEngine，无强制同步项）

### AOAdapt 日志（实施过程遇到问题时追加）
- [ ] （待填写）