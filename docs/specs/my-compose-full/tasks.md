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
- [ ] 2.5 W2 波提交 + MC 门禁核对留痕

## 3. W3 并存页统一收尾
- [ ] 3.1 TopBarManageActivity：RecyclerView 与 ComposeView 并存收编（AppPackageManageScreen 样板，功能等价）
- [ ] 3.2 NavigationBarManageActivity：同模式 + **alert{}×2（L337/L464）→showCompose 系（MC-7）**
- [ ] 3.3 ShareNoteTemplateManageActivity：同模式（样板页核对基准）
- [ ] 3.4 **AdvancedTitleManageActivity 纳入**（红队 R1：入口阅读页 TipConfigDialog，顶栏统一+组件收编）
- [ ] 3.5 孤儿治理：ThemeEditorDialogFragment/DiscoveryConfigFragment/SubscriptionConfigFragment 死代码删除（**同步删 ConfigActivity.kt:126-127 分发分支+ConfigTag 常量；删前运行时入口审计：searchTarget 深链核查**）；fileManage 死分支路由删除
  - 验证标准（3.1-3.5）：管理功能等价 + 顶栏统一 + 死代码清零 (L2)
- [ ] 3.6 W3 波提交

## 4. W4 纯 View 重写（大）
- [ ] 4.1 CacheManageActivity：composeHost + AppManagementScaffold 重写（**ViewModel 复用；ItemTouchHelper→LazyColumn 拖拽重实现**；多选/排序/清理确认全保留）
  - 验证标准：缓存数据零丢失，操作等价 (L3)
- [ ] 4.2 CoverCollectionDetailActivity：同模板重写（浏览/收藏管理）
  - 验证标准：收藏浏览功能等价 (L3)
- [ ] 4.3 W4 波提交

## 5. W5 管理列表/编辑型穷举（红队 R1-P0 缺口补入）
- [ ] 5.1 BookSourceActivity/RssSourceActivity/TxtTocRuleActivity/ReplaceRuleActivity/DictRuleActivity/HighlightRuleActivity：管理列表型统一（含 ReplaceRule View 手术残留收尾：titleBar GONE+removeView 清理）
- [ ] 5.2 AutoTaskActivity(+Edit)/AiProviderManageActivity(+Edit)/AiImageProviderManageActivity(+Edit)/AiWorldBookManageActivity：编辑型+管理型统一
- [ ] 5.3 S3ContainerManage/LibraryContainerManage/RelaySettingsActivity/AllBookmarkActivity/CoverCollectionManage/BookInfoManage/BubbleManage：管理列表型统一（含 BubbleManage 对话框族×8 核对）
  - 验证标准（5.1-5.3）：各页功能等价 + 顶栏统一 + MC 门禁留痕 (L2/L3)
- [ ] 5.4 W5 波提交

## 6. W6 浏览型+对话框清扫（红队 R1-P0 补登记）
- [ ] 6.1 LogActivity/SettingsSearchActivity/UrlRecord/StorageManage/DownloadManage/FileManage/RssArticleInfo：轻改收尾
- [ ] 6.2 **AiImageGalleryActivity/DebugToolsActivity 明确迁移**；QrCodeActivity/WebViewActivity/VerificationCodeActivity/OpenUrlConfirmActivity 补登记后定迁移或豁免（红队 R1-P2 补树）
- [ ] 6.3 对话框 40 类按形态分组（全屏/输入/多选/排序/预览）→ComposeDialogFragment 基线清扫（红队 R2：分组验收矩阵）
- [ ] 6.4 W6 波提交

## 7. 收尾
- [ ] 7.1 全域回归：我的 Tab 全入口 L3 点击 + 深浅主题 + 全局壁纸开关 + 顶栏包切换 + manageBgAlpha 两态
- [ ] 7.2 MainTopBarView Mode.SUB 引用全域清零确认（Grep）+ **Mode.SUB 枚举删除（Delta 2026-09-07 终态：子页面唯一顶栏 GlassTopAppBar，3→1 达成）**；MainTopBarView 仅剩主 Tab 消费；AppManagementTopBar 定义删除确认
- [ ] 7.3 updateLog + INDEX.md + ui-standards/migration-registry 登记（MC-13）+ 提交推送
- [ ] 7.4 SubBarDebug 清理确认（W0 未清部分兜底）
