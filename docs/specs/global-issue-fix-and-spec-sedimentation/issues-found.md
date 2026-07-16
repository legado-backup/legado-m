# 测试发现的问题清单：global-issue-fix-and-spec-sedimentation

> **创建时间**：2026-07-16
> **用途**：记录真机测试中发现的所有问题，防止压缩上下文后丢失
> **权威源性质**：补充权威源（主权威源是 tasks.md）

## 问题状态统计

- 总计：19
- 待修复：0（Issue-18 用户决定搁置，不计入待修复）
- 修复中：0
- 已修复：18（Issue-1 到 Issue-17B 全部已修复）
- 搁置：1（Issue-18 订阅源登录后列表为空 articles=0，用户决定搁置）

## 问题列表

（测试执行中追加，每发现一个问题立即记录）

---

## 已知问题（测试前分析阶段发现）

### Issue-1: 数据库升级覆盖安装失败（P0 阻塞）

- **发现时间**：2026-07-16（用户反馈 #6）
- **问题描述**：升级数据库打的最新包，覆盖安装后直接闪退，只能全新安装
- **根因分析**（2026-07-16 重新核实修正）：
  - **之前诊断错误**：误认为当前 migration_95_96 代码没有 DROP+CREATE VIEW
  - **实际代码状态**：migration_95_96（DatabaseMigrations.kt L524-545）**已包含** DROP+CREATE VIEW 重建，SQL 与 @DatabaseView（BookSourcePart.kt L12-18）完全一致
  - **真实根因**：之前发布的某个中间版本 96（migration_95_96 未包含 DROP+CREATE 时的版本）已存在于用户设备。重新安装修复后的 96 版本时，version 相同 Room 不执行 migration，但设备上的 view 结构是旧的（没有 lastHost 列），Room schema 校验发现不匹配抛 IllegalStateException
  - **全新安装正常的原因**：全新安装直接创建 version=96 的数据库，view 结构正确，不需要 migration
- **修复方案**：version 96→97，新增 migration_96_97 强制重建 view。这样覆盖安装时会执行 96→97 的 migration，无论之前 96 是 bug 版还是修复版，都会 DROP+CREATE 重建 view
- **状态**：已修复（Phase 2 完成，真机验证通过）
- **经验教训**：(1) DatabaseView 修改必须在 migration 中 DROP+CREATE 重建 (2) 已发布有 bug 的 version 不能通过重装同 version 修复，必须 version+1 新增 migration
- **日志证据**：logs_v1（3.26.071518debug 版本）App 能正常启动，4 次 FATAL 全是 MaterialButton 崩溃，无数据库迁移异常；logs_v6（3.26.071419debug 版本）App 也能正常启动。覆盖安装失败时的日志未被记录（App 在数据库初始化阶段崩溃，来不及写 appLog）

### Issue-2: 高亮规则点+号崩溃（P0 崩溃）

- **发现时间**：2026-07-16（用户反馈 #3）
- **问题描述**：书架打开小说，高亮规则管理点右上角+号直接报错退出
- **日志证据**：
  ```
  FATAL EXCEPTION: main
  android.view.InflateException: Binary XML file line #89
  Caused by: java.lang.IllegalArgumentException:
    The style on this component requires your app theme to be
    Theme.MaterialComponents (or a descendant).
  at MaterialButton.<init>
  ```
- **根因分析**：
  - dialog_highlight_rule_edit.xml 用 MaterialButton + Widget.Material3.Button.TextButton 样式
  - 项目主题是 Theme.AppCompat.DayNight.NoActionBar（非 Material 主题）
  - MaterialButton 构造时 ThemeEnforcement 校验失败
- **修复方案**：4 个布局的 MaterialButton 改为 Button/AppCompatButton
- **涉及文件**：
  - dialog_highlight_rule_edit.xml
  - dialog_highlight_rule_group_manage.xml
  - dialog_highlight_note.xml
  - item_highlight_rule_group.xml
- **状态**：已修复（Phase 3 完成，真机验证通过）

### Issue-3: 订阅源播放器菜单丢失（P1 UI）

- **发现时间**：2026-07-16（用户反馈 #1）
- **问题描述**：订阅源内置播放器详情页右上角没有刷新和三个点了，浏览器打开功能丢失
- **具体根因**（子代理深度分析确认）：
  - `app/src/main/res/menu/video_play.xml` 缺少 `menu_rss_refresh` 和 `menu_browser_open` 两个菜单项（对比 `rss_read.xml` L5-8, L34-36 有这两项）
  - `app/src/main/java/io/legado/app/ui/video/VideoPlayerActivity.kt` L964-1100 的 `onCompatOptionsItemSelected` 缺少对应 when 分支
  - 迁移抖音风格重构时 menu 文件被精简但遗漏了订阅源场景的菜单项
- **修复方案**：
  1. 在 `video_play.xml` 添加 `<item android:id="@+id/menu_rss_refresh" ... />` 和 `<item android:id="@+id/menu_browser_open" ... />`（参考 rss_read.xml 结构）
  2. 在 `VideoPlayerActivity.onCompatOptionsItemSelected` 添加对应 when 分支：刷新调用 `refreshRssArticles()`，浏览器打开调用 `openInBrowser(currentUrl)`
  3. 菜单可见性根据 `isRssSource` 条件显示（非 RSS 源不显示刷新项）
- **涉及文件**：`res/menu/video_play.xml`、`VideoPlayerActivity.kt`
- **如何避免**：沉淀到 `global-thinking-checklist.md`——"迁移/重构功能时必须盘点该功能所有使用场景的菜单项，避免遗漏场景"
- **状态**：已修复（前序阶段完成）

### Issue-4: 订阅源播放器返回按钮不生效（P1 UI）

- **发现时间**：2026-07-16（用户反馈 #2）
- **问题描述**：订阅源内置播放器页面顶部左侧返回按钮不生效（改了好几版仍不生效）
- **具体根因**（子代理深度分析确认）：
  - `app/src/main/res/layout/activity_video_player.xml` L16-19, L36-39 存在**两个 TitleBar 并存**（旧版+新版）
  - `app/src/main/java/io/legado/app/ui/widget/TitleBar.kt` L198-201, L271-278 的 `onAttachedToWindow` 自动调用 `setSupportActionBar`，导致 ActionBar 状态混乱
  - `app/src/main/java/io/legado/app/base/BaseActivity.kt` L127-133 的 `onOptionsItemSelected` 是 `final` 方法，拦截了 `android.R.id.home` 走 `supportFinishAfterTransition()`
  - `VideoPlayerActivity.kt` L248-251 的 `onSupportNavigateUp` 重写是**死代码**（永远不会被调用）
  - `VideoPlayerActivity.kt` L215-227 的 `switchToViewPagerMode` 在协程内异步执行，存在时序窗口：用户点击返回时该方法可能尚未完成，导致 `supportFinishAfterTransition()` 不调用 `finish()`
- **修复方案**：
  1. 移除 `activity_video_player.xml` 中重复的 TitleBar（只保留一个）
  2. 在保留的 TitleBar 上调用 `setNavigationOnClickListener { finish() }`（直接走 Activity.finish，绕过 final 方法的时序问题）
  3. 删除 `VideoPlayerActivity.onSupportNavigateUp` 死代码
  4. `switchToViewPagerMode` 改为同步执行或确保在 `onCreate` 完成前执行完毕
- **涉及文件**：`res/layout/activity_video_player.xml`、`VideoPlayerActivity.kt`
- **如何避免**：沉淀到 `spec-sedimentation-mechanism.md`——"Activity 布局中禁止出现两个 TitleBar 并存，会导致 ActionBar 状态混乱；BaseActivity final 方法拦截导航事件时，子类重写无效需通过 setNavigationOnClickListener 绕过"
- **状态**：已修复（前序阶段完成）

### Issue-5: 订阅源编辑页单源线程数配置缺失（P1 UI）

- **发现时间**：2026-07-16（用户反馈 #4）
- **问题描述**：说过可以在订阅源编辑页配置解析线程数，但功能按钮找不到
- **具体根因**（子代理深度分析确认）：
  - `app/src/main/java/io/legado/app/data/entities/RssSource.kt` 已有 `parseConcurrency: Int?` 字段（数据库层支持）
  - `app/src/main/res/layout/activity_rss_source_edit.xml` **未添加配置控件**（UI 层缺失入口）
  - `RssSourceEditActivity.kt` 未绑定 parseConcurrency 字段（逻辑层未对接）
  - 即数据模型有字段但 UI 和 Activity 没有对接，导致用户找不到配置入口
- **修复方案**：
  1. 在 `activity_rss_source_edit.xml` 适当位置（建议在"高级设置"折叠区）添加 `EditText` 或 `SeekBar` 控件，inputType="number"，范围 1-32
  2. `RssSourceEditActivity.kt` 在 `initView()` 绑定控件，在 `saveSource()` 保存到 `rssSource.parseConcurrency`
  3. 加载时读取 `parseConcurrency ?: AppConfig.rssParseConcurrency` 显示（单源配置优先于全局配置）
- **涉及文件**：`res/layout/activity_rss_source_edit.xml`、`RssSourceEditActivity.kt`
- **如何避免**：沉淀到 `global-thinking-checklist.md`——"新增数据字段时必须同步完成『模型定义+UI 控件+Activity 绑定+加载/保存逻辑』全链路，不可只改模型不改 UI"
- **状态**：已修复（前序阶段完成）

### Issue-6: 视频浏览器弹框样式不搭（P2 UI）

- **发现时间**：2026-07-16（用户反馈 #5）
- **问题描述**：内置视频浏览器下方功能区弹框样式跟软件整体风格不搭
- **具体根因**（子代理深度分析确认）：
  - `app/src/main/java/io/legado/app/ui/video/VideoSettingsPanel.kt` L48 继承 `BottomSheetDialogFragment`
  - `app/src/main/res/drawable/bg_settings_panel.xml` 硬编码 `#E6121212`（暗色背景）
  - `app/src/main/res/drawable/bg_panel_button.xml` 硬编码 `#1AFFFFFF`（半透明白）
  - `app/src/main/res/values/styles.xml` L148 `VideoPanelButton` 样式 textColor=`#E6FFFFFF`（硬编码白色文字）
  - `app/src/main/res/layout/layout_video_settings_panel.xml` 中 `#E6FFFFFF` / `#99FFFFFF` 等硬编码颜色遍布9处
  - **整套样式固定暗色**，不跟随 DayNight 主题，在亮色主题下与整体风格冲突
  - 对比：`AppLogDialog.kt` 用 `primaryColor` 跟随主题，`BottomWebViewDialog.kt` 用动态 `backgroundTintList`
- **修复方案**：
  1. `bg_settings_panel.xml` 改为 `?attr/colorBackground` 或 `?android:colorBackground`
  2. `bg_panel_button.xml` 改为 `?attr/colorControlHighlight`
  3. `styles.xml` 的 `VideoPanelButton` textColor 改为 `?attr/textColorPrimary`
  4. `layout_video_settings_panel.xml` 中9处硬编码颜色全部替换为 `?attr/*` 或 `@color/*` 引用
  5. 真机验证在亮色/暗色主题下都正确显示
- **涉及文件**：`VideoSettingsPanel.kt`、`bg_settings_panel.xml`、`bg_panel_button.xml`、`styles.xml`、`layout_video_settings_panel.xml`
- **如何避免**：沉淀到 `global-thinking-checklist.md`——"新建 UI 组件时禁止硬编码颜色，必须使用 `?attr/*` 或 `@color/*` 引用主题色，保证跟随 DayNight 主题切换"
- **状态**：已修复（前序阶段完成）

### Issue-7: 校验逻辑和原来没区别（P1 功能）

- **发现时间**：2026-07-16（用户反馈 #7）
- **问题描述**：校验逻辑应该像调试模式一样多线程调度，判断关键元素，加权计算 weight，但现在和原来没区别
- **具体根因**（子代理深度分析确认）：
  - `CheckSourceService.kt` L199-272 `doCheckSource` 方法**各维度串行执行**（域名→搜索→发现→详情→目录→正文），未做维度并发
  - `SourceWeightCalculator.kt` L48-74 `calculateBookWeightFromGroups` 基于 `source.hasGroup("XXX失效")` **二元判断**（有失效分组=0分，无失效=满分），不反映关键元素获取程度
  - 对比 `Debug.kt` L22-385：调试模型用 `tasks.add()` 注册任务并管理并发，分步骤收集结果——校验没有复用这套机制
  - 即校验只是简单跑各维度然后看是否有"失效分组"，**没有收集"搜索结果数/详情字段完整度/目录章节数/正文字数"等关键元素**，权重计算粒度太粗
- **修复方案**：
  1. `CheckSourceService.doCheckSource` 改为 `coroutineScope { async {} }` 维度并发（域名+搜索+发现+详情+目录+正文同时跑，受 concurrentRate 约束）
  2. 每个维度参考 `Debug.kt` 的 `searchDebug/infoDebug/tocDebug/contentDebug` 收集关键元素：
     - 搜索：结果数（0/有结果），返回书籍数
     - 发现：是否能获取书单
     - 详情：标题/作者/简介/封面字段完整度（4字段各有=满分，缺1字段扣1/4）
     - 目录：章节数（0/>0/>10）
     - 正文：正文字符数（0/>0/>1000）
  3. `SourceWeightCalculator` 改为接收"维度结果集"对象（含各维度关键元素获取情况），按维度加权计算：
     - 域名 20分（不通=0分直接返回，通=20分）
     - 搜索 20分（结果数>0=20分，结果数=0=0分）
     - 发现 15分（有书单=15分，无=0分）
     - 详情 15分（按字段完整度比例）
     - 目录 15分（>10章=15分，1-10章=10分，0章=0分）
     - 正文 15分（>1000字=15分，1-1000字=10分，0字=0分）
  4. 每个维度请求完成后从 `AnalyzeUrl.url`（L102）提取 host 回填 lastHost
- **涉及文件**：`CheckSourceService.kt`、`CheckRssSourceService.kt`、`SourceWeightCalculator.kt`
- **如何避免**：沉淀到 `spec-sedimentation-mechanism.md`——"校验类功能必须参考 Debug 模型的分步骤收集结果机制，权重计算基于关键元素获取程度而非二元判断"
- **状态**：已修复（前序阶段完成）

### Issue-8: lastHost 字段设计理解偏差（P1 功能）

- **发现时间**：2026-07-16（用户反馈 #13）
- **问题描述**：lastHost 应在真实使用/调试/校验三层回填，域名分组按"真实地址+源类型"合并
- **具体根因**（子代理深度分析确认）：
  - 当前回填点**仅3处**：
    - `CheckSourceService.kt:221` 校验层
    - `CheckRssSourceService.kt:223,239` 校验层
  - **缺失真实使用层**：`WebBook.kt` 的 searchBookAwait/getBookInfoAwait/getChapterListAwait/getContentAwait 不回填
  - **缺失真实使用层**：`Rss.kt` 的 getArticlesAwait/getContentAwait 不回填
  - **缺失调试层**：`BookSourceDebugActivity.kt` / `Debug.kt` 不回填
  - `BookSourceActivity.kt` L514-518 分组**只按 host 不按 type**，不满足用户要求"一个域名可有多个类型源"
  - `RssSourceActivity.kt` **完全缺失域名分组功能**
  - AnalyzeUrl 解析后的真实 URL 存放在 `AnalyzeUrl.kt` L102 `var url: String`，可直接 `URI(url).host` 提取
- **修复方案**：
  1. **真实使用层回填**：WebBook/Rss 中所有调用 AnalyzeUrl 的方法（searchBookAwait/getBookInfoAwait/getChapterListAwait/getContentAwait、Rss.getArticlesAwait/getContentAwait），请求完成后提取 host 回填
  2. **调试层回填**：BookSourceDebugActivity/Debug.kt 的 searchDebug/exploreDebug/infoDebug/tocDebug/contentDebug 回填
  3. **校验层保持**：CheckSourceService/CheckRssSourceService 已有
  4. **持久化策略**：用 `sourceLastHostCache: MutableMap<String, String>` 内存缓存，变化才写 DB（避免每次请求都写库）
  5. **BookSourceActivity 分组键**：`compareBy { getSourceHost(it.lastHost ?: it.bookSourceUrl) }.thenBy { it.bookSourceType }`
  6. **RssSourceActivity 补齐**：添加 groupSourcesByDomain 开关 + getSourceHost 方法
- **涉及文件**：`WebBook.kt`、`BookContent.kt`、`BookChapterList.kt`、`Rss.kt`、`BookSourceDebugActivity.kt`、`Debug.kt`、`BookSourceActivity.kt`、`RssSourceActivity.kt`
- **如何避免**：沉淀到 `spec-sedimentation-mechanism.md`——"新增字段时必须盘点所有使用场景的回填点（真实使用/调试/校验三层），不可只在单点回填"
- **状态**：已修复（前序阶段完成）

### Issue-9: 真机测试流程复用未沉淀（P2 规范）

- **发现时间**：2026-07-16（用户反馈 #9）
- **问题描述**：真机测试流程没有沉淀复用机制，每次都重新设计
- **具体根因**：
  - `ai_tests/scripts/` 下已有 quick_build_install.py、import_rss_source.py、l2_verify_video_player.py、swipe_test_log.py 等固化脚本，但未沉淀为"真机测试流程复用规范"
  - `ai_tests/docs/fixed_test_workflow.md` 有 SOP 但未在主规范 AGENTS.md 引用
  - 每次 spec 任务都重新设计测试流程，未复用已有脚本
  - 测试发现问题没有强制闭环（记录→修复→验证→回填状态）
- **修复方案**：新建 `docs/project-rules/real-device-test-reuse.md`：
  1. 列出所有可用脚本及其使用场景（quick_build_install/import_rss_source/l2_verify_video_player/swipe_test_log）
  2. 测试流程模板：编译安装→导入数据→执行功能→日志分析→问题记录
  3. 测试发现问题的闭环：记录到 issues-found.md→修复→真机验证→回填状态
  4. AGENTS.md 在"AI 自动端到端测试"章节引用
- **如何避免**：沉淀到 `real-device-test-reuse.md`——"测试脚本必须放 ai_tests/scripts/，禁止在 temp/ 创建临时脚本；测试流程必须复用已有脚本"
- **状态**：已修复（前序阶段完成）

### Issue-10: 数据库升级问题未沉淀到子规范（P2 规范）

- **发现时间**：2026-07-16（用户反馈 #10）
- **问题描述**：数据库升级覆盖安装问题之前也遇到过，但没沉淀到子规范，导致反复犯
- **具体根因**：
  - 本次 migration_95_96 修改了 BookSourcePart（@DatabaseView）的 SQL 但未在 migration 中 DROP+CREATE 重建 view
  - 之前也遇到过类似问题但未沉淀规则
  - AGENTS.md "代码约束"章节未提及 DatabaseView 修改的强制要求
  - 没有"数据库升级安全规范"子规范，每次都凭经验
- **修复方案**：新建 `docs/project-rules/database-migration-safety.md`：
  1. DatabaseView 修改必须在 migration 中 DROP+CREATE 重建
  2. migration 必须 runCatching 包裹+日志
  3. version 必须递增，不可降级
  4. migration 不可重复执行（version 已升的不会重跑）
  5. 覆盖安装兼容性测试要求：必须从旧版本覆盖升级验证
  6. Room schema 校验是运行时的（编译期不会发现 view 未重建）
  7. AGENTS.md "代码约束"章节增加引用
- **如何避免**：沉淀到 `database-migration-safety.md`——"修改 @DatabaseView 必须同步 migration DROP+CREATE；修改实体字段必须同步 ALTER TABLE + view 重建"
- **状态**：已修复（前序阶段完成）

### Issue-11: 反复犯同样错误缺乏沉淀机制（P2 规范）

- **发现时间**：2026-07-16（用户反馈 #11）
- **问题描述**：很多错误都是反复犯的，需要沉淀机制防止第二次
- **具体根因**：
  - 项目记忆 project_memory.md 记录了大量教训但未结构化为子规范
  - 没有"错误→沉淀→子规范→主规范引用"的闭环机制
  - 每次错误只在对话中反思，新对话无法自动加载教训
- **修复方案**：新建 `docs/project-rules/spec-sedimentation-mechanism.md`：
  1. **沉淀触发条件**：用户严厉批评的错误 / 浪费用户时间的错误 / 同类错误第2次出现
  2. **沉淀流程**：错误发生→分析根因→提炼规则→写入子规范→AGENTS.md 引用
  3. **沉淀格式**：[规则名] [场景描述] [强制要求] [反面案例] [正面做法]
  4. **沉淀清单**（本次需沉淀的错误）：
     - DatabaseView 修改必须 DROP+CREATE（→database-migration-safety.md）
     - MaterialButton 需要 Material 主题（→spec-sedimentation-mechanism.md）
     - 校验必须真正触发功能路径（→spec-sedimentation-mechanism.md）
     - 字段回填必须覆盖使用/调试/校验三层（→spec-sedimentation-mechanism.md）
     - Activity 布局禁止两个 TitleBar 并存（→spec-sedimentation-mechanism.md）
     - 新增字段必须完成全链路（模型+UI+Activity+加载/保存）（→global-thinking-checklist.md）
     - 新建 UI 组件禁止硬编码颜色（→global-thinking-checklist.md）
  5. AGENTS.md 引用新增子规范
- **如何避免**：本规范本身就是沉淀机制，每次犯新错误后按流程沉淀
- **状态**：已修复（前序阶段完成）

### Issue-12: 缺乏全局思考检查清单（P2 规范）

- **发现时间**：2026-07-16（用户反馈 #14）
- **问题描述**：改功能时不通篇全局思考（前端入口、后端接口、数据库、覆盖安装）
- **具体根因**：
  - OpenSpec 工作流步骤1（需求分析）没有强制"全局思考检查清单"
  - AI 改功能时只看当前文件，不盘点前端入口数量/后端接口影响/数据库改动/覆盖安装兼容性
  - 导致：改播放器菜单漏了订阅源场景；改 RssSource 加字段漏了 UI 入口；改 DatabaseView 漏了 migration 重建
- **修复方案**：新建 `docs/project-rules/global-thinking-checklist.md`：
  1. **前端入口盘点**：功能有几个入口？入口在哪？入口改动影响哪些？
  2. **后端接口影响**：动了哪些接口？接口被哪些功能调用？
  3. **数据库改动评估**：是否改 schema？是否改 @DatabaseView？migration 是否需要重建 view？覆盖安装是否兼容？
  4. **覆盖安装兼容性**：migration 是否可回退？version 是否递增？旧版本覆盖升级是否成功？
  5. **使用场景盘点**：功能在哪些场景使用？（如菜单在书源/订阅源/RSS 三个场景）
  6. **回填点盘点**：新增字段在哪些点回填？（真实使用/调试/校验三层）
  7. **强制门禁**：OpenSpec 步骤1必须填写此清单，未填写不得进入步骤2
- **如何避免**：本规范本身就是检查清单，作为开发前置门禁
- **状态**：已修复（前序阶段完成）

### Issue-13: 日志文件分析结果（2026-07-16 补充）

- **发现时间**：2026-07-16（用户反馈 #8 提供 temp\tmp\Downloadslogs(1).(1)..zip）
- **问题描述**：用户测试最新版本时导出的日志，需分析是否含新问题
- **分析结果**：
  - **FATAL EXCEPTION 4 次**：全部是 MaterialButton 主题兼容崩溃（dialog_highlight_rule_edit 第89行），已在 Issue-2 覆盖
  - **非致命异常**：
    - StreamResetException（OkHttp 图片下载流被 CANCEL，已被协程捕获）
    - UnknownHostException（DNS 负缓存命中，已被协程捕获）
    - GlideException（model 为 null，非致命警告）
    - 网络层异常 172 次（Cronet 协议错误/DNS 失败，大部分已被降级机制处理）
  - **未发现的新问题**：无数据库迁移异常、无 OOM、无 ANR、无空指针、无 VideoPlayerActivity/CheckSourceService 崩溃
- **结论**：日志确认 Issue-2（MaterialButton 崩溃）是确定性复现的致命问题，4 次崩溃堆栈完全一致。其他异常均已被现有异常处理机制捕获，非新问题
- **状态**：已分析完成（无新问题，根因已在 Issue-2 覆盖）

### Issue-14: 复杂需求反复验证可行性未沉淀（P2 规范，2026-07-16 补充）

- **发现时间**：2026-07-16（用户反馈 #12）
- **问题描述**：用户建议"在处理我的复杂需求时候，一定要认真思考反复验证可行性"
- **具体根因**：
  - 当前 OpenSpec 工作流没有"复杂需求反复验证可行性"的强制环节
  - AI 在设计阶段往往只做一次方案就提交，未反复验证可行性
  - 导致：校验逻辑设计偏差（Issue-7）、lastHost 设计偏差（Issue-8）、单源线程数配置遗漏 UI 入口（Issue-5）
- **修复方案**：在 `spec-sedimentation-mechanism.md` 增加规则：
  1. **复杂需求判定标准**：涉及3+文件改动 / 涉及数据库 / 涉及多场景交互 / 涉及回填点
  2. **反复验证流程**：
     - 第一次验证：方案设计完成后自问"每个修复方案是否可执行？是否有遗漏？"
     - 第二次验证：对照用户原始反馈逐条核对覆盖情况
     - 第三次验证：用子代理交叉审查设计文档
  3. **强制门禁**：复杂需求设计方案必须经过3次验证才能提交检查点1
- **如何避免**：沉淀到 `spec-sedimentation-mechanism.md`——"复杂需求设计方案必须经过3次验证（自检+对照原始反馈+子代理交叉审查）才能提交"
- **状态**：已修复（前序阶段完成）

### Issue-15: BookSourceAdapter 拖拽选择 NPE 崩溃（P0 崩溃，2026-07-16 日志分析新增）

- **发现时间**：2026-07-16（日志分析 logs_v6/logcat.txt L53309-53313）
- **问题描述**：书源校验所选时拖拽选择触发 NullPointerException 导致 App 崩溃闪退
- **日志证据**：
  ```
  07-15 15:54:13.156 FATAL EXCEPTION: main
  java.lang.NullPointerException
    at BookSourceAdapter$dragSelectCallback$1.getItemId(BookSourceAdapter.kt:352)
    at BookSourceAdapter$dragSelectCallback$1.getItemId(BookSourceAdapter.kt:346)
    at DragSelectTouchHelper$AdvanceCallback.onSelectStart(DragSelectTouchHelper.kt:855)
  ```
- **根因分析**：
  - `BookSourceAdapter.kt:352` 的 `dragSelectCallback` 中 `getItemId` 方法返回 null
  - 触发场景：用户在书源列表长按拖拽选择多个书源时（`onSelectStart` 回调）
  - 对应 project_memory [2026-07-15 16:10] 用户反馈"书源的校验所选，运行一会直接报了一个空指针异常，软件崩溃闪退了"
- **修复方案**：
  1. 读取 `BookSourceAdapter.kt:346-352` 确认 `getItemId` 实现
  2. 如果是 `getItem(position)` 返回 null，需增加 null 安全处理（返回 `0L` 或 `INVALID_ID`）
  3. 或检查 adapter 数据源是否有 null 元素
- **涉及文件**：`app/src/main/java/io/legado/app/ui/book/source/manage/BookSourceAdapter.kt`
- **如何避免**：沉淀到 `spec-sedimentation-mechanism.md`——"RecyclerView Adapter 的 getItemId 必须做 null 安全处理，不能返回 null Long 值"
- **状态**：已修复（前序阶段完成）

### Issue-16: item_source_folder_grid MaterialCardView 崩溃（P0 崩溃，2026-07-16 日志分析新增）

- **发现时间**：2026-07-16（日志分析 logs_v6/logcat.txt L2-4）
- **问题描述**：源分组文件夹网格列表打开时 MaterialCardView 崩溃
- **日志证据**：
  ```
  07-08 11:44:43.766 FATAL EXCEPTION: main
  android.view.InflateException: Binary XML file line #29 in dialog_highlight_rule_edit:layout/item_source_folder_grid
  Error inflating class com.google.android.material.card.MaterialCardView
  Caused by: IllegalArgumentException: The style on this component requires your app theme to be Theme.MaterialComponents
  ```
- **根因分析**：
  - `item_source_folder_grid.xml` 第29行用 `MaterialCardView`，与 Issue-2 同根因
  - 项目主题是 `Theme.AppCompat.DayNight.NoActionBar`（非 Material 主题）
  - MaterialCardView 构造时 ThemeEnforcement 校验失败
- **修复方案**：
  - `item_source_folder_grid.xml` 的 `MaterialCardView` 改为 `androidx.cardview.widget.CardView`
  - 需要确认 CardView 的属性兼容性（cardCornerRadius/cardElevation 等）
- **涉及文件**：`app/src/main/res/layout/item_source_folder_grid.xml`
- **如何避免**：同 Issue-2，沉淀到 `spec-sedimentation-mechanism.md`——"不仅 MaterialButton，所有 Material* 组件（MaterialCardView/MaterialTextView 等）都需要 Material 主题，非 Material 主题项目应改用 AppCompat 对应组件"
- **状态**：已修复（前序阶段已重构布局，当前文件无 MaterialCardView，根布局为 ConstraintLayout）

### Issue-17: 高亮规则编辑弹窗背景色不跟随应用主题（P2 UI，2026-07-16 新增）

- **发现时间**：2026-07-16（用户反馈"设置了软件默认是暗色主题，为什么高亮规则设置弹窗页面不追随系统主题"）
- **问题描述**：用户设置应用为暗色主题，但高亮规则编辑弹窗背景仍显示浅色
- **根因分析**：
  - `HighlightRuleEditDialog` 构造参数 `adaptationSoftKeyboard=true`
  - `BaseDialogFragment.onViewCreated`（[BaseDialogFragment.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/base/BaseDialogFragment.kt) L79-89）中 `adaptationSoftKeyboard=true` 走透明背景分支，**不设置 ThemeStore.backgroundColor()**
  - 应用通过 `setTheme(R.style.AppTheme_Dark)` 设置暗色主题，**不激活 values-night 资源限定符**
  - `dialog_highlight_rule_edit.xml` 的 `vw_bg` 使用 `@drawable/shape_card_view`（含 `@color/background_card`），在应用级暗色主题下仍返回浅色值
- **修复方案**：
  - `HighlightRuleEditDialog.onFragmentCreated` 中动态设置背景色：
    - `binding.vwBg.setBackgroundColor(ThemeStore.backgroundColor())`
    - `binding.toolBar.setBackgroundColor(ThemeStore.primaryColor())`
- **涉及文件**：[HighlightRuleEditDialog.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/highlight/edit/HighlightRuleEditDialog.kt)
- **状态**：已修复（本次会话修复，编译安装完成，待用户真机验证）

### Issue-17B: HighlightStyleDialog 样式选择弹窗主题不跟随（P2 UI，2026-07-17 新增）

- **发现时间**：2026-07-17（用户反馈"样式按钮点开后还是没有跟随系统主题，白乎乎一片，下面按钮看不到"）
- **问题描述**：高亮规则编辑弹窗的"样式"按钮点开后，弹出的底部样式选择面板（HighlightStyleDialog）背景为浅色，文字不可见
- **根因分析**：
  - `HighlightStyleDialog` 是 `BottomSheetDialogFragment`（非 BaseDialogFragment 子类）
  - 原版用 `applyAppSheetBackground()` 扩展函数设置背景，当前项目简化适配时改为 `ViewCompat.setBackgroundTintList(sheet, null)` 让背景为 null
  - BottomSheet 默认背景在应用级暗色主题下返回浅色值
  - 布局中 `@color/primaryText`/`@color/secondaryText` 在应用级暗色主题下返回浅色值（暗色文字），导致"下面按钮看不到"
- **修复方案**：
  - [HighlightStyleDialog.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/book/read/HighlightStyleDialog.kt) onStart：使用 `ThemeStore.backgroundColor()` + `GradientDrawable` 圆角背景（模仿原版 applyAppSheetBackground 逻辑）
  - onViewCreated：在动态 view 添加完成后，调用 `applyThemeColors(view)` 递归遍历 view 树，给所有 TextView/CheckBox 设置 `ThemeStore.textColorPrimary()` 颜色（tv_extra 保留 accent 色作为点击提示色）
- **涉及文件**：[HighlightStyleDialog.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/book/read/HighlightStyleDialog.kt)
- **状态**：已修复（本次会话修复，编译安装完成，用户验证通过）

### Issue-18: 订阅源登录后列表为空 articles=0（P1 功能，2026-07-16 新增，用户决定搁置）

- **发现时间**：2026-07-16（用户反馈"我点击去登录了，点完对号，然后刷新列表，还是什么也没有"）
- **问题描述**：订阅源登录成功返回后，调用刷新但列表仍为空
- **调试日志根因定位**（已通过 LoginRefresh tag 日志确认）：
  1. loginResult 回调正常触发（resultCode=RESULT_CANCELED 但回调仍触发）
  2. currentArticlesFragment 正常找到
  3. refreshAfterLogin 正常调用
  4. ViewModel.loadArticles 正常执行
  5. **核心根因**：`ViewModel.loadArticles success: articles=0`，请求成功（bodyLen=8228）但 `RssParserByRule.parseXML` 解析后返回 0 条文章
  6. cookie 保存正常（len=87，getCookie 正常返回）
- **可能原因**（未深入验证）：
  - 服务器返回了非文章列表页面（如登录页/重定向页），bodyLen=8228 可能是登录页HTML
  - 解析规则不匹配响应内容（响应内容结构变化）
  - sourceUrl 含 `#new` 锚点可能影响请求 URL 拼接
- **已完成的修复**（部分修复，但根因 articles=0 未解决）：
  - `RssSortActivity.menu_login` 从 `startActivity` 改为 `loginResult.launch`（带回调刷新）
  - `WebViewLoginFragment.menu_ok` 添加 `CookieManager.getInstance().flush()`（强制持久化cookie）
  - `RssArticlesViewModel.loadArticles` 添加请求/响应日志
  - `Rss.getArticlesAwait` 添加 bodyLen 和 parsed articles 日志
- **用户决策**：搁置（"如果解决不了，就先不解决这个了"）
- **后续清理**：搁置后需移除 LoginRefresh tag 调试日志
- **涉及文件**：
  - [RssSortActivity.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/rss/article/RssSortActivity.kt)
  - [RssArticlesFragment.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/rss/article/RssArticlesFragment.kt)
  - [RssArticlesViewModel.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/rss/article/RssArticlesViewModel.kt)
  - [Rss.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/model/rss/Rss.kt)
  - [CookieStore.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/help/http/CookieStore.kt)
  - [WebViewLoginFragment.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/login/WebViewLoginFragment.kt)
- **状态**：搁置（articles=0 根因未解决，登录刷新机制已修复）
