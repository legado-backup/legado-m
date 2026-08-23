# 20260822 真机反馈 Bug 修复 — 任务清单（tasks.md）

> 修订 v1（2026-08-22）：基于用户六条反馈 + `Downloadslogs(1).zip` 全量深度分析生成。
> 状态标记：`- [ ]` 待办 / `- [x]` 完成（⚠️ 代码完成 / ✅ 功能验证）。编译门禁 = `./gradlew assembleAppDebug`（测试包 `io.legado.miss.app.debug`）。
> 注：崩溃类 3 项 + 备份页 Compose 化 + 统计框隐藏为文档生成前先行修复，本次文档审查通过后确认保留。

## 1. 日志深度分析（已完成）
- [x] 1.1 解析 bug.md 六条用户反馈，映射修复方向 — 完成
- [x] 1.2 logcat.txt 全量扫描 12 处 FATAL（StackOverflow×2 / IndexOutOfBounds×1 / ActivityNotFound×9）— 完成
- [x] 1.3 appLog 100+ 文件技术扫描（约 9400 行异常分类：网络层/协程取消/ClassCast/NPE/JS规则/视频/SSL）— 完成
- [x] 1.4 识别应用代码缺陷 2 类（ClassCastException ×39 / NPE ×12）— 完成
- [x] 1.5 对比 Archive 定位订阅切换无反应根因（modernRssPage 无消费方）— 完成

## 2. 崩溃类修复（先行，✅ 代码完成）
- [x] 2.1 BookSourceActivity 递归环断环（删 initComposeHost/onBackPressed 覆写）— ⚠️ 已实施
- [x] 2.2 VideoPagerAdapter 稳定 ID（getItemId/containsItem）— ⚠️ 已实施
- [x] 2.3 Manifest 注册 BookInfoComposeActivity + ThemeManageActivity — ⚠️ 已实施

## 3. 备份恢复页对齐 Archive（先行，⚠️ 代码完成待审）
- [x] 3.1 BackupConfigFragment → ComposeSettingFragment（buildPageSpec 云存储/主题同步）— ⚠️ 已实施
- [x] 3.2 PreferKey 补 s3FullWebDavFallbackNeverRemind — ⚠️ 已实施
- [x] 3.3 arrays.xml 补 cloud_storage_types/values — ⚠️ 已实施
- [x] 3.4 ConfigViewModel 补 upCloudStorageConfig + Backup 接 AppCloudStorage — ⚠️ 已实施
- [ ] 3.5 备份页功能真机验证（用户后续验证）

## 4. 我的页统计框隐藏（先行，✅ 代码完成）
- [x] 4.1 MySettingsScreen MetricGrid 渲染 if(false) 包裹（代码保留）— 已实施
- [x] 4.2 MyFragment loadMetrics() 注释 — 已实施

## 5. 应用代码缺陷修复
- [x] 5.1 SourceNetworkClient.analyzeLoginResult 类型容错（ClassCast 修复）— ✅ 已实施
- [x] 5.2 AnalyzeByJSonPath.getStringList NPE 判空 — ✅ 已实施（F-5.2 列表项/顶层判空）

## 6. 订阅页管理设置 + 新版/经典切换（核心项，对齐 Archive）
- [x] 6.1 AppConfig 补 modernRssPage 读写属性（读 PreferKey.modernRssPage）— ✅ 已实施
- [x] 6.2 fragment_rss.xml 补双形态布局：titleBar（经典）+ topBar（现代）+ rss_fragment_container/rss_web_container（现代容器）— ✅ 已实施
- [x] 6.3 RssFragment 补 usingModernRss + applyRssMode() 双形态渲染（对齐 Archive L179-197）— ✅ 已实施
- [x] 6.4 onResume 检测 modernRssPage 变化重建视图（切换即时生效，对齐 Archive L122-134）— ✅ 已实施（L252-255 检测差异重分派）
- [x] 6.5 现代形态：initModernRssView/observeRssSources/RssArticlesFragment/WebView 单源渲染（对齐 Archive）— ✅ 已实施
- [x] 6.6 经典形态：applyClassicRssMode（initRecyclerView/initGroupData 等经典列表/文件夹/排序形态）— ✅ 已实施
- [x] 6.7 菜单管理入口对齐 Archive：menu_rss_config → RssSourceActivity + menu_rss_star → RssFavoritesActivity（经典形态显示）— ✅ 已实施（L384/814/873 已接入）
- [x] 6.8 管理设置生效验证（发现 vs 订阅行为一致）— ✅ 真机验证通过（2026-08-23：新版/经典双向切换生效，prefs modernRssPage true/false 正确落盘，订阅页形态即时响应；发现-订阅配置页完整显示）
- [x] 6.9 切换逻辑修复：经典形态 initRecyclerView 重复 addHeaderView（"规则订阅"header 反复堆积）→ classicHeaderReady 一次性守卫 — ✅ 已实施
- [x] 6.10 切换逻辑修复：经典形态 initTabLayout 重复注册 tab 监听（upTabLayout 只 remove 单实例→累积）→ classicTabListenerReady 一次性守卫 — ✅ 已实施
- [x] 6.11 切换逻辑修复：现代源切换竞态（selectSource 启动 presentSource 无版本防护，sortUrls 可达 30s JS 执行，旧源晚返回会用旧 currentSorts 覆盖当前源→切源显示错乱）→ rssSourceVersion 版本号 + presentSource 校验丢弃过期结果 — ✅ 已实施
- [x] 6.12 切换逻辑修复真机验证（新版/经典反复切换无重复条目 + 快速切源显示正确）— ✅ 真机验证通过（BUG-A header 恒为1 / BUG-B tab 恒为4不累积 / BUG-C 快速切源顶栏随选择更新无崩溃）

## 7. 主题设置顶栏管理对齐 Archive
- [x] 7.1 对比两端 ThemeConfigFragment 顶栏菜单差异（管理入口/行为）— ✅ 已核实一致（ThemeManageActivity/导航栏主题/应用主题/分享主题完整）
- [x] 7.2 对齐 Archive 顶栏管理实现并落地 — ✅ 已实施（ThemeManageActivity Manifest 注册修复 ActivityNotFound）
- [x] 7.3 验证 ThemeManageActivity 跳转正常（回归 S-5）— ✅ 真机验证通过（2026-08-23：ThemeManageActivity/BookInfoComposeActivity 打开无崩溃；7 入口全量可达零崩溃）
- [x] 7.4 书架分组标签（BookGroupTabs）读 TopBarConfig 修复真机验证 — ✅ 真机验证通过（2026-08-23：激活自定义顶栏包 tagBarColor=红 #E53935，书架分组标签栏由基线 #EEEEEE 变 #E53935；改 tagBarColor=绿 #2E7D32 后经顶栏管理页"应用"返回书架（不重启）即时变 #2E7D32，验证 TOP_BAR_CHANGED → topBarVersion 重组链路生效；测试后已恢复默认顶栏配置）
- [x] 7.5 顶栏"整个头部"行为验证（regular 整体换肤 vs default 仅标签色）— ✅ 真机验证通过（2026-08-23：verify_topbar_header.py 采样——style=regular+蓝底红标签 → 整个头部变蓝；style=default+蓝底红标签 → 头部保持主题色仅标签变红；行为与 archive 完全一致，MainTopBarView 无需代码变更，用户确认"与 archive 完全一致"）
- [x] 7.6 帮助弹框（TextDialog）样式对齐 archive — ✅ 真机验证通过（2026-08-23 用户反馈"帮助弹框样式没学习到 archive"：根因=本项目 TextDialog 仍为旧 View 实现 BaseDialogFragment+R.layout.dialog_text_view，archive 已升级 ComposeDialogFragment+AppDialogFrame；修复=整体替换 archive Compose 版（ComposeDialogFragment/AppDialogFrame/AppDialogStyle/LegadoMiuixActionButton/toMiuixPalette/uiTypeface 依赖均已就绪），compileAppDebugKotlin BUILD SUCCESSFUL；旧 View 版备份 bak/TextDialog_20260823_old_view.kt；覆盖范围：帮助说明(MD)/更新日志(MD)/日志详情(TEXT)/书源调试 HTML 等全部 TextDialog 调用点；真机验证：verify_help_dialog.py 从"我的"页帮助按钮进入，弹框含 Compose AppDialogFrame 面板(6个View容器)+标题"帮助"+关闭+编辑内容按钮，无崩溃，与 archive 一致）
- [x] 7.7 订阅源/书源布局配置弹框样式对齐书架布局弹框 — ✅ 真机验证通过（2026-08-23 用户反馈"订阅布局为什么不去学习现在的书架布局弹框样式"：根因=订阅布局弹框 SourceFolderAdapter.showConfigDialog 仍为旧 View 实现（BaseDialog alert+DialogSourceFolderConfigBinding），书架布局弹框 BookshelfConfigDialog 已升级 ComposeDialogFragment+AppDialogStyle+LegadoMiuixCard；修复=新建 SourceFolderConfigDialog.kt（ComposeDialogFragment，完全对齐 BookshelfConfigDialog 样式：LegadoMiuixCard 面板/选项卡片网格+选择 Popup/间距滑杆/底栏取消-应用按钮），配置项全量迁移（分组样式 sourceGroupStyle / 展示模式 sourceGroupMode / 视图模式 sourceLayout / 排序 bookSourceSort|rssSort / 间距 sourceMargin）；RssFragment.showFolderConfig 改用 showDialogFragment(SourceFolderConfigDialog.create(...))；旧 showConfigDialog 从 SourceFolderAdapter 移除；dialog_source_folder_config.xml 保留未删；真机验证 verify_source_folder_config.py --full 全绿：订阅弹框 ComposeView 命中+全结构命中+排序应用 rssSort=1 写入，书架弹框对比 ComposeView 命中+全结构命中，logcat 无 FATAL；注意订阅布局弹框仅在经典订阅形态（modernRssPage=false）的更多菜单存在，现代形态顶栏无更多按钮为对齐 Archive 的设计）

## 8. 编译门禁 + 打测试包
- [x] 8.1 ./gradlew assembleAppDebug BUILD SUCCESSFUL — ✅ 2026-08-23 00:49 通过（7m31s）
- [x] 8.2 build-legado.bat 产出测试包（io.legado.miss.app.debug）— ✅ legado_miss_app_3.26.082301.apk
- [x] 8.3 updateLog 补本次修复条目（编译前）— ✅ 已补（订阅切换/崩溃3类/备份页/统计框隐藏/NPE 等 7 条）

## 9. 文档同步
- [x] 9.1 tasks.md 勾选（实施完成后基于实际落盘核查）— ✅ 已完成
- [x] 9.2 docs/INDEX.md 登记 bugfix-20260822 spec — ✅ 已登记（第 114 行，状态已更新为实施完成待真机）
- [x] 9.3 design.md 与实施结果一致性校验 — ✅ 已完成（5.2 NPE 判空已落地，design §Bug 分析结论与实施一致）
