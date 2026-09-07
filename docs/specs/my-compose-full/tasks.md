# tasks.md — "我的"全域 Compose 化

> 门禁：每波开工前备份涉及文件到 bak；每波结束 git 提交隔离。
> 每波强制自查：MC-1..13 门禁逐条核对（弹框/菜单/卡片/开关/取色）+ 主题配置验证矩阵（深浅×颜色×顶栏包×壁纸×透明度×沉浸×fontScale）+ 核对留痕写入本文件对应任务下。
> **Delta 2026-09-07（用户裁决）**：顶栏 3→1 组件归一收编本任务表——22 页 Mode.SUB 随各波逐页消亡（既有任务内含），GlassTopAppBar 插槽扩展+AppManagementTopBar 委托收官列 6.5/6.6，终态验收点=7.2。

## 0. W0 前置（红队 R5-P0/R2-P1）
- [x] 0.1 SubBarDebug 定稿：GlassTopAppBar shadow(0.dp) 实验回滚或定稿（恢复 barElevation 消费）；TopBarConfig.kt Log.d 热路径日志清除
  - 验证标准：Grep SubBarDebug/android.util.Log 清零；L1 门禁可满足
  - 留痕：commit 22ac62dd4，shadow 定稿仅实色生效（barColor.alpha>=0.99），Log 清零 Grep 确认
- [x] 0.2 manageBgAlpha 语义收窄裁决落盘：MC-12"顶栏族全局"回写 architecture.md；manageBgAlpha 标签语义倒挂（独立 Bug）立遗留项
  - 验证标准：architecture.md 与本 spec G12/MC-12 表述一致
  - 留痕：architecture.md:54 已回写，遗留项已立
- [x] 0.3 Tier×波次映射表落盘（subpage-topbar-unify 二期三期衔接）：22 页分档逐页标注所属波次；非我的域 10 页归属声明
  - 验证标准：22 页每页有唯一波次归属
  - Tier×波次映射表（红队 R4 落盘）：
    - **W1**：AppearanceKit、AppearanceKitEdit、ThemeManage（3 页，本波顶栏+布局统一）
    - **W2**：About（去壳）
    - **W3**：TopBarManage、NavigationBarManage、ShareNoteTemplateManage、AdvancedTitleManage（4 页）
    - **W5**：BookInfoManage、BubbleManage（2 页，随管理列表批）
    - **W6**：AiReadAloudUsageRecord、AiImageGallery、ExploreShow（3 页，浏览型；ExploreShow 同时是 master-track B4-c 登记页——以本表为准）
    - **master-track B2**：BookSourceEdit（1 页）；**B3**：BookSourceDebug（1 页）；**B4-c**：ParagraphRuleManage、ParagraphRuleEdit、ReadAloudBgmManage、ReadMenuButtonManage、ReadMenuCustomButtonEdit（5 页，阅读域随波次）
    - 非我的域 10 页归属声明：ReadMenuButtonManage/ReadMenuCustomButtonEdit/ParagraphRule×2/ReadAloudBgm/AiReadAloudUsageRecord（阅读域 5 页）+ ExploreShow/DiscoverySuiteManage（发现域 2 页）+ BookSourceEdit/Debug（书源域 2 页）+ CacheManage（ui/book/cache，精准管理域已入 W4）——各域归属如上，不重复排期
    - 合计 3+1+4+2+3+1+1+5+2=22 ✓

## 1. W1 先行（ThemeManage 自造组件清零拆至 W5，红队 R5 拆波）
- [ ] 1.1 AppearanceKitActivity：去 View 顶栏（MainTopBarView Mode.SUB）→ 统一顶栏组件；自造 AppearanceKitCard→AppManagementCard（MC-8）
  - 验证标准：编译通过；顶栏统一组件+透壁纸语义；主题 Kit 功能等价 (L2)
- [ ] 1.2 AppearanceKitEditActivity：同 1.1 模式；自造 SettingPanel/自绘按钮/M3 OutlinedTextField→统一组件（MC-3/8/11）
  - 验证标准：同上 (L2)
- [ ] 1.3 ThemeManageActivity（2495 行）：本轮限顶栏+布局统一；自造组件清零（tabs/开关行/编辑大弹框/alert{}:1201/ColorPicker×3）拆至 W5 专项
  - 验证标准：顶栏统一+透壁纸；主题切换/应用/同步功能等价 (L2)
- [x] 1.4 W1 波提交 + 三页 Mode.SUB 引用删除确认（Grep MainTopBarView 零残留于三页）+ MC 门禁核对留痕
  - 留痕：commit 97daa7a23

## 2. W2 中成本收尾
- [x] 2.1 RssSearchActivity：RssSearchAdapter/历史 Adapter → LazyColumn；补空结果空状态组件（MC-3）；顶栏已 Compose 保持
  - 验证标准：搜索/历史/清空功能等价 (L2)
  - 留痕：新建 RssSearchResultScreen（LazyColumn+BookCoverImage 复用+空状态）；输入帮助区直接复用书源 SearchInputHelpScreen（bookshelfBooks 传空）；删除 RssSearchAdapter/RssSearchHistoryAdapter/item_rss_search.xml；历史 FlowRow+清空 chip 组件内聚
- [x] 2.2 AboutActivity 壳纯化（去 llAbout 自绘卡壳，AboutFragment=ComposeSettingFragment 已有）
  - 留痕：installGlassTopBar 运行时替换（评分/分享按钮→MenuAction alwaysShow）；activity_about.xml 删 MainTopBarView 节点（专用布局）+llAbout 去 shape_card_view/UiCorner 背景
- [x] 2.3 ReadRecordActivity：GONE 顶栏与 ViewBinding 残留清理（XML+Activity）
  - 验证标准：单顶栏、Compose 正常 (L2)
  - AOAdapt（2026-09-07 实施期修正）: Action-核验 activity_read_record.xml 消费方 | Observation-该布局为双页共用：ReadRecordFragment（主框架阅读记录 Tab，活代码 MainActivity:2507）活跃消费 topBar(READ_RECORD 筛选栏)/titleBar/scrollView 面板体系；ReadRecordActivity 消费 composeHost 全屏列表模式，GONE 切换是正当双视图共存机制而非残留 | Adapt-任务判定修正：XML 节点全部有活消费者不可删，GONE 切换代码保留；本任务关闭于"共存模式正当性确认"，无需代码变更（原判定基础"布局为 Activity 专属"不成立）
- [x] 2.4 MyFragment 本体：View 壳+View 顶栏 → Compose 壳（MySettingsData 路由零改动）
  - 验证标准：我的 Tab 全入口（21+）+ **SettingsSearchActivity 全路由回归**（复用 handleSettingsRowClick 连带，红队 R2）(L3)
  - 留痕：fragment_my_config.xml 纯化为单 ComposeView（compose_host）；顶栏 GlassTopAppBar（搜索/帮助一级图标语义保留）+statusBarsPadding 外层 Box（GlassTopAppBar 无 modifier 槽）；MainTopBarView Mode.MY 引用删除；路由 onRowClick→handleSettingsRowClick 零改动
- [x] 2.5 W2 波提交 + MC 门禁核对留痕
  - 留痕：commit 406beb1c0；MC 门禁核对：MC-3（历史区复用 SearchInputHelpScreen 基线/空状态组件化）✓ MC-5（GlassTopAppBar 单源取色）✓ MC-10（About 评分/分享、我的搜索/帮助图标 onClick 真实挂载）✓ MC-12（顶栏透壁纸语义随 GlassTopAppBar）✓；调试日志 Grep 0 残留 ✓
  - **L2 验证状态（用户裁决 2026-09-07 17:4x"接受现状进W3"）**：结构级 L2 全过（我的 Tab 全设置行挂载+顶栏搜索/帮助图标[588,30]/[660,30]+书源管理路由跳转 BookSourceActivity+RssSearch 顶栏搜索栏挂载+全程无 FATAL）；视觉 L2 挂起——模拟器 GPU 合成故障（对照实验：W1 验收通过的 090716 旧包同黑屏，定性环境问题非代码缺陷），视觉验收随 W3 波/真机回归补验

## 3. W3 并存页统一收尾
> 红队 R2 补充（子代理源码穿透 2026-09-07）：四页布局全部为 activity_theme_manage.xml（14 页共用容器），顶栏统一走 installGlassTopBar 运行时替换（W1 模式，XML 不动）。四页内容区均已大量 Compose 化，残留点各异，实施序=从小到大（3.4→3.3→3.1→3.2）。
- [x] 3.1 TopBarManageActivity：RecyclerView 与 ComposeView 并存收编（AppPackageManageScreen 样板，功能等价）
  - 留痕 (L1 编译过)：installGlassTopBar 顶栏（S3 容器/同步任务保留一级图标）；containerActionVisible mutableStateOf 驱动 S3 按钮显隐（替代 AppCompatImageButton.isVisible）；ModernActionPopup→showComposeActionListDialog；ColorPickerDialog 保留（W5 专项）；功能 15 项零删改
  - 改造点：①顶栏 View→installGlassTopBar（titleBar L192-205 删）②容器切换 ModernActionPopup(L251)→showComposeActionListDialog（对齐 ThemeManage W1 模式）③ColorPickerDialog(L390-395) View 弹框暂保留（W5 专项统一取色器）④私有 TopBarManageScreen(L841-882) 已用样板，抽取独立文件可选。功能 15 项全保留（新增/导入/应用/编辑全项/条目菜单7项/S3切换/同步/WebDav/zip/壁纸裁剪/默认包只读）
- [x] 3.2 NavigationBarManageActivity：同模式 + **alert{}×2（L337/L464）→showCompose 系（MC-7）**
  - 留痕 (L1 编译过，6 轮编译收敛)：①新增 NavigationBarEditDialog（ComposeDialogFragment 壳：OutlinedTextField 名称+AppManagementListRow 配置行+AndroidView 包装 ImageView 图标预览+LegadoMiuixActionButton 保存/取消，AppDialogSize.Management）②新增 NavigationBarItemsDialog（BottomNavItemsManageContent 复用壳，AppDialogSize.Form）③buildEditView/buildNavBarEditRows+iconRow 族/buildNavBarIconRows 数据化（editVersion mutableIntStateOf 驱动重组替代 View 全量重建 refreshEditDialog）④saveEditingPackage(name) 参数化（EditText findViewWithTag 废弃）⑤showAlphaPicker→showComposeNumberPickerDialog ⑥顶栏 installGlassTopBar+containerActionVisible+ModernActionPopup→showComposeActionListDialog ⑦View 系全清（editingDialog/ScrollView 壳/PackageManageUi 依赖/NumberPickerDialog/UiCorner 等 import 清零）| 实施教训：同文件并行 Edit 竞态第 3 次复发（showAlphaPicker/Alignment/drawable?/ItemsDialog palette 四处被覆盖），已全部串行重修——铁律：同文件 Edit 严禁并行
  - 改造点：①L337 alert（customView 塞 ComposeView BottomNavItemsManageContent+okButton）→ComposeDialogFragment 容器（参照 TopBarEditDialog 模式）②L464 alert（editDialogScrollContainer=buildEditView L495-619 动态 LinearLayout）→专用 ComposeDialogFragment（全部配置项 Compose 重写：布局模式/材质/搜索开关/壁纸/透明度/边框色/侧栏背景/逐项图标）③NumberPickerDialog(L679)→showComposeNumberPickerDialog ④PackageManageUi View 助手弃用评估 ⑤顶栏→installGlassTopBar
- [x] 3.3 ShareNoteTemplateManageActivity：同模式（样板页核对基准）
  - 留痕 (L1 编译过)：installGlassTopBar 顶栏（标题字符串资源化）；GONE→removeView 四节点；硬编码中文 9 处→stringResource（新增 share_note_ 族 10 条，对齐该族中文默认资源现状）；ComposeActionListDialog/ComposeConfirmDialog 已合规保留
  - 改造点：①顶栏→installGlassTopBar ②硬编码中文（L109 标题+L231-246/L254-259/L341 菜单标签）→stringResource（§6.1）③tabBar/tvSummary/btnAdd GONE→removeView 对齐 ④ComposeActionListDialog.create 可选统一为 showComposeActionListDialog
- [x] 3.4 **AdvancedTitleManageActivity 纳入**（红队 R1：入口阅读页 TipConfigDialog，顶栏统一+组件收编）
  - 留痕 (L1 编译过)：实施评估=AppManagementScaffold 为管理族三基线之一已合规（Screen 内自供顶栏+返回键），无需 installGlassTopBar；改造收敛为 GONE 残留清理——hideTopBar/initComposeContent 统一 removeView 五节点（titleBar/recyclerView/tabBar/tvSummary/btnAdd），删 View import。**未换样板**（Lottie 预览列表为功能特性，与红队 R1 结论一致）
- [x] 3.5 孤儿治理：ThemeEditorDialogFragment/DiscoveryConfigFragment/SubscriptionConfigFragment 死代码删除（**同步删 ConfigActivity.kt:126-127 分发分支+ConfigTag 常量；删前运行时入口审计：searchTarget 深链核查**）；fileManage 死分支路由删除
  - 留痕 (L1 编译过)：深链审计确认——DISCOVERY_CONFIG/SUBSCRIPTION_CONFIG 常量零 putExtra 来源（活链路为 DISCOVERY_SUBSCRIPTION_CONFIG）；ThemeEditor 三件套（DialogFragment/Screen/ViewModel）互引闭环零外部入口；fileManage 路由分支无入口行（FileManageActivity 活入口在精准管理/AiConfigFragment，页面保留 W6.1）| 删除 5 文件+ConfigActivity 分支 2 行+ConfigTag 常量 2 条+MySettingsData 死分支+import | rg 复核清零 |
  - 验证标准（3.1-3.5）：管理功能等价 + 顶栏统一 + 死代码清零 (L2)
- [x] 3.6 W3 波提交
  - 留痕：3.1/3.3/3.4=624e773c2、3.2=002236a3f、3.5+收尾=本波尾提交；L2 结构验证（模拟器 GPU 故障期）：安装 0907 新包→底栏管理页 dump 全挂载（GlassTopAppBar 标题+同步任务图标+日夜 Tab+列表项）→NavigationBarItemsDialog 打开验证（栏项列表+确认按钮渲染，零 FATAL）；视觉验收继续挂起待模拟器环境修复

## 4. W4 纯 View 重写（大）
- [x] 4.1 CacheManageActivity：composeHost + AppManagementScaffold 重写（**ViewModel 复用；ItemTouchHelper→LazyColumn 拖拽重实现**；多选/排序/清理确认全保留）
  - 留痕 (L1 编译过，7 轮收敛)：**AOAdapt 前提修正**——子代理源码穿透实测本页无 ItemTouchHelper/无多选/无拖拽（排序为对话框比较器），"拖拽重实现"描述不成立，按保真原则未新增拖拽；交付=新建 CacheManageScreen（Scaffold+3 topAction+日夜 Tab 行+LazyColumn item 卡片[封面 BookCoverImage/源 chip/计数/状态/任务消息/动作 chip 行]+空态+常驻批量按钮行）+Activity 重写（composeHost 桥接/mutableStateMapOf 任务态定向 diff 写等效 PAYLOAD 局部刷新/8 动作枚举分发/确认弹框与锁定门禁全保留/VM 零改动）+删 CacheManageAdapter/item_cache_manage_book.xml+XML 纯化单 ComposeView | 踩坑记录：LegadoTheme 包路径 ui.theme、AppManagementPalette.settings.row/rowPressed 为 Int 需 Color() 包装、LegadoMiuixActionButton 需 LegadoMiuixPalette（管理页色板无转换改用 Chip）、MaterialTheme.typography.bodySecondary 需扩展 import、onBack lambda 内禁读 Composable 状态、FrameLayout 无 setViewCompositionStrategy
  - 验证标准：缓存数据零丢失，操作等价 (L3)
- [x] 4.2 CoverCollectionDetailActivity：同模板重写（浏览/收藏管理）
  - 留痕 (L1 编译过)：新建 CoverCollectionDetailScreen（Scaffold+导入 topAction+LazyVerticalGrid 3 列图片墙[AndroidView 包装 Glide ImageView]+长按删除 combinedClickable+空态）+Activity 重写（composeHost 桥接/collectionName+images 快照状态/删除确认链原样）+XML 纯化单 ComposeView+删 item_cover_collection_image.xml | 新增 cover_collection_empty 空态字符串 | ⚠️ 第 4 次并行 Edit 竞态（空态 Box 修正被覆盖），串行重修——铁律再次验证
  - 验证标准：收藏浏览功能等价 (L3)
- [x] 4.3 W4 波提交
  - 留痕：4.1=aa840faad、4.2+4.3=本波尾提交；L2 结构验证随模拟器环境恢复统一补验（GPU 故障期视觉挂起）

## 5. W5 管理列表/编辑型穷举（红队 R1-P0 缺口补入）
> 三子代理并行源码穿透（2026-09-07）：17 页实际残留远小于预期——10 页零残留、3 页小残留、4 页中残留。
- [x] 5.1 BookSourceActivity/RssSourceActivity/TxtTocRuleActivity/ReplaceRuleActivity/DictRuleActivity/HighlightRuleActivity：管理列表型统一（含 ReplaceRule View 手术残留收尾：titleBar GONE+removeView 清理）
  - 批A 登记完成：TxtTocRuleActivity/DictRuleActivity（全 Compose 壳层+零残留，布局已纯 ComposeView）
  - Highlight 完成 (L1)：3×AlertDialog.Builder→showComposeChoiceListDialog（恢复默认三态：合并直执行+覆盖经二次确认）/showComposeConfirmDialog（覆盖确认/删除确认，dangerPositive）
  - ReplaceRule 完成 (L1)：GONE→removeView（titleBar/selectActionBar）+upCountView 死写链删除（定义+5 调用点）| SelectActionBar.CallBack 接口暂留（override 方法被 Scaffold 回调复用，接口清理留批D）
  - Book/Rss 清理留批D（Snackbar 替换/PopupMenu 接口链删除涉及调用链，单独小批实施）
- [x] 5.2 AutoTaskActivity(+Edit)/AiProviderManageActivity(+Edit)/AiImageProviderManageActivity(+Edit)/AiWorldBookManageActivity：编辑型+管理型统一
  - 批A 登记完成：AutoTaskActivity/AutoTaskEditActivity/AiWorldBookManageActivity/AiProviderManageActivity/AiImageProviderManageActivity（5 页零 View 残留）| 可选清理项：AiImageProviderManage 死函数 showActions(L190-236)、AiProviderManage Screen 拆独立文件
  - AiImageProviderEditActivity 完成 (L1)：删死布局 activity_ai_image_provider_edit.xml（-191 行，运行时 removeAllViews 全丢弃）+binding 改合成 ViewBinding 空壳（getRoot() 方法覆写，对齐 RelaySettings 模式）
- [ ] 5.3 S3ContainerManage/LibraryContainerManage/RelaySettingsActivity/AllBookmarkActivity/CoverCollectionManage/BookInfoManage/BubbleManage：管理列表型统一（含 BubbleManage 对话框族×8 核对）
  - 批A 登记完成：AllBookmarkActivity/RelaySettingsActivity/S3ContainerManageActivity/LibraryContainerManageActivity（4 页零运行时残留；S3/Library XML 死节点+共享 WaitDialog 留遗留项）| BubbleManage 对话框族×8 核对确认 100% Compose 化达成（唯一 View 弹框=第三方 ColorPickerDialog，与 ThemeManage/TopBarManage/NavBar 一致留统一取色器专项）| BookInfoManageActivity：复用 14 页共用容器，GONE 为正当共存模式（对齐 ReadRecord 2.3 判定），不动 XML 仅登记
  - CoverCollectionManageActivity 完成 (L1)：installGlassTopBar 顶栏+containerActionVisible 状态桥接（原 B 类风险登记解除）+View 节点 removeView
  - BubbleManageActivity 完成 (L1)：installGlassTopBar 顶栏（S3 容器+帮助双按钮状态桥接）+GONE→removeView 四节点
  - 验证标准（5.1-5.3）：各页功能等价 + 顶栏统一 + MC 门禁留痕 (L2/L3)
- [x] 5.4 W5 波提交
  - 留痕：W5 主体（批A 登记 10 页+批B/C 实施 5 页）编译过（第 18 轮）后本批提交；Book/Rss 批D 清理+资源删除留 W6 前置
  - 批D 完成 (L1 第 19 轮)：BookSourceActivity——Snackbar→CheckProgressBanner（Compose 横幅+cancelSourceCheck，CHECK_SOURCE/CHECK_SOURCE_DONE 事件状态化）+SelectActionBar.CallBack 接口摘除（selectAll/revertSelection/onClickSelectBarMainAction 去 override 留函数）+upCountView 死写链删除（定义+6 调用点）+selectActionBar GONE→removeView | RssSourceActivity——initSelectActionBar 死函数+onMenuItemClick+PopupMenu.OnMenuItemClickListener 接口+SelectActionBar.CallBack 摘除（onClickSelectBarMainAction 死函数删除）+upCountView 死写链（定义+5 调用点）+GONE→removeView | BookSourceScreen 增 checkBannerText/onCancelCheck 参数+CheckProgressBanner 组件 | 布局 XML 死节点删除留 W6 资源清扫

## 6. W6 浏览型+对话框清扫（红队 R1-P0 补登记）
- [x] 6.1 LogActivity/SettingsSearchActivity/UrlRecord/StorageManage/DownloadManage/FileManage/RssArticleInfo：轻改收尾
  - 双子代理源码穿透（2026-09-08）：SettingsSearch/StorageManage/DownloadManage 零残留（AppManagementScaffold+GlassTopAppBar 已达标）；Log/UrlRecord 仅 binding 壳/状态桥接可选优化（登记不实施，避免过度工程）；FileManage 删除无确认弹窗为交互缺口非 View 残留（登记留功能专项）
  - RssArticleInfoActivity 完成 (L1 第 20 轮)：主体全量重写 RssArticleInfoScreen（Glide sourceOrigin 封面 fitCenter+失败隐藏/信息行/简介/多源列表/底部操作栏）+合成 ViewBinding 空壳+applyThemeColors 手动取色链删除+RssArticleInfoSourceAdapter/activity_rss_article_info.xml/item_rss_article_info_source.xml 删除（-3 文件）
- [x] 6.2 **AiImageGalleryActivity/DebugToolsActivity 明确迁移**；QrCodeActivity/WebViewActivity/VerificationCodeActivity/OpenUrlConfirmActivity 补登记后定迁移或豁免（红队 R1-P2 补树）
  - AiImageGalleryActivity 完成 (L1 第 20 轮)：AppManagementScaffold 迁移（顶栏/搜索/批量底栏）+AiImageGalleryScreen（FlowRow chips+2 列网格+Glide AndroidView）+MainTopBarView Mode.SUB 消亡+RecyclerAdapter/activity_ai_image_gallery.xml 删除（item_ai_generated_image.xml 保留：BookCharacterEdit 仍在用）
  - 豁免登记（双子代理穿透裁决）：DebugTools（纯 Compose 已达标，Screen 内私有卡片组件豁免先例）；QrCode（相机预览页，顶栏已 GlassTopAppBar）；WebView（WebView 主体不可 Compose 化，顶栏/菜单/对话框已全达标，迁移高风险零收益）；VerificationCode/OpenUrlConfirm（透明壳+ComposeDialogFragment，无可迁移面）
- [x] 6.3 对话框 40 类按形态分组（全屏/输入/多选/排序/预览）→ComposeDialogFragment 基线清扫（红队 R2：分组验收矩阵）
  - 双子代理分类穿透（2026-09-08，31 类核对）：30 类类型 A 已达 ComposeDialogFragment 基线（含 GroupManageDialog×4 薄壳共享 GroupManageComposeDialog、FontSelectDialog/TopBarEditDialog/BookmarkDialog/CacheChapterDialog/UpdateDialog/CoverRuleConfigDialog/ImportAutoTaskDialog/AutoTaskLogDialog/AiImagePreviewDialog/ChangeBookSourceDialog/ChangeRssArticleSourceDialog/CheckSourceConfig/TextDialog/AppLogDialog/VariableDialog/SourceLoginDialog/Import 系×5/DictRuleEditDialog/Highlight 系×3/TxtTocRuleEditDialog+ComposeDialog 双版均 A）| ThemeEditorDialogFragment 类型 D 已删除
  - PackageSyncTaskDialog 完成 (L1 第 21 轮)：唯一类型 C（AndroidAlertBuilder+编程式 View 列表）重写 ComposeDialogFragment+AppDialogFrame+LazyColumn+states.collectAsState 定向刷新，扩展函数签名不变 4 调用点零改动
  - 豁免登记：WaitDialog（全 App 共用 21 处加载指示器，非"我的"域专属，留全局统一专项）| AndroidView 包 TextView/PhotoView（MD 渲染/图片手势）为合理互操作非残留
- [x] 6.4 W6 波提交

## 7. 收尾
- [ ] 7.1 全域回归：我的 Tab 全入口 L3 点击 + 深浅主题 + 全局壁纸开关 + 顶栏包切换 + manageBgAlpha 两态（MEmu GPU 故障遗留，修复后与 W2/W3 视觉验收一并补验）
- [x] 7.2 MainTopBarView Mode.SUB 引用全域清零确认（Grep）+ **Mode.SUB 枚举删除（Delta 2026-09-07 终态：子页面唯一顶栏 GlassTopAppBar，3→1 达成）**；MainTopBarView 仅剩主 Tab 消费；AppManagementTopBar 定义删除确认
  - 10 页 Mode.SUB 收官迁移（L1 第 23 轮）：ParagraphRuleManage/ReadMenuButtonManage/ReadAloudBgmManage/AiReadAloudUsageRecord/ReadMenuCustomButtonEdit/DiscoverySuiteManage（共用容器 6 页走 installGlassTopBar，DiscoverySuite 动态标题/actionsBar 改 Compose 状态桥接）| ParagraphRuleEdit/BookSourceEdit（LinearLayout 自有布局走 installGlassTopBar；ParagraphRuleEdit updateActionButtonStates 改 topActionsEnabled 状态驱动；BookSourceEdit 3 一级+12 溢出菜单迁 TopBarActionRow/AppDropdownMenu，onCompatOptionsItemSelected→handleSourceEditMenuAction）| BookSourceDebug/ExploreShow（ConstraintLayout 页走布局内 compose_top_bar 直挂，约束链顺延）
  - 基础设施：MenuAction 增 iconRes 双源（MenuActionIcon 渲染器）+enabled 启用态（对齐 AppManagementAction 模型）；installGlassTopBar LayoutParams 通用化（兼容 ConstraintLayout 外的根布局）
  - 清零确认：Mode.SUB rg 全域仅注释命中；枚举已删（BOOKSHELF/DISCOVERY/RSS/READ_RECORD/MY）；arrangeTitleSelect 死函数删除；AppManagementTopBar 定义删除（Scaffold 直接委托 GlassTopAppBar，6.6 收官）
- [x] 7.3 updateLog + INDEX.md + ui-standards/migration-registry 登记（MC-13）+ 提交推送
- [x] 7.4 SubBarDebug 清理确认（W0 未清部分兜底）：rg SubBarDebug/Log.d 于 app/src/main 与 widget/components 清零（2026-09-08 复核）
