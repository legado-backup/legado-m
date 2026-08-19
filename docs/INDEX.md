# 文档索引

> 项目所有文档的统一入口，覆盖项目规范、项目流程、功能设计、核�?Skill 四类文档�?

---

## 一、项目规范（docs/project-rules/�?

> AI Agent 编码时必须遵循的项目特有规则，按需加载�?

| 规范 | 文件 | 核心内容 |
|------|------|----------|
| 命名规范 | [project-rules/naming_rules.md](./project-rules/naming_rules.md) | 类后缀约定+up/dur/Await缩写+常量混合风格+扩展函数组织+包结�?|
| 代码风格 | [project-rules/checkstyle_rules.md](./project-rules/checkstyle_rules.md) | Coroutine链式封装+双版本模�?kotlin.runCatching+object单例+@IntDef+顶层lazy |
| 异常处理 | [project-rules/exception_rules.md](./project-rules/exception_rules.md) | NoStackTraceException体系+四种捕获模式+网络错误�?协程异常 |
| 日志规范 | [project-rules/logging_rules.md](./project-rules/logging_rules.md) | AppLog+LogUtils+DebugLog三层体系+标签约定+使用规则 |
| 架构模式 | [project-rules/architecture_rules.md](./project-rules/architecture_rules.md) | 手动DI+ViewModel模式+Room配置+Web服务�?事件系统+模块依赖+构建配置 |
| 测试规范 | [project-rules/testing_rules.md](./project-rules/testing_rules.md) | JUnit4+书源自测三阶�?测试运行命令 |
| 工作流程 | [project-rules/openspec-workflow.md](./project-rules/openspec-workflow.md) | OpenSpec四文�?强制检查点+文档同步映射�?子代理使用指�?上下文预算检�?|
| 延伸版本对比方法�?| [project-rules/forks_comparison_methodology.md](./project-rules/forks_comparison_methodology.md) | 27+延伸版本清单+五阶段对比流�?优先级矩�?踩坑案例 |
| E2E测试流程 | [project-rules/ai_e2e_testing_workflow.md](./project-rules/ai_e2e_testing_workflow.md) | 5.5.1-5.5.8八步强制流程+固化层保�?V3.1快速验证脚�?|
| 测试用例设计 | [project-rules/test-case-design-guide.md](./project-rules/test-case-design-guide.md) | 双轨�?源码溯源字段+步骤语义�?|
| 改造过程日�?| [project-rules/logging-during-refactoring.md](./project-rules/logging-during-refactoring.md) | 10类必加日志场�?永久/临时双轨+Tag规范+验证检查清�?|
| 版本交付同步 | [project-rules/version-delivery-sync.md](./project-rules/version-delivery-sync.md) | 同步清单+updateLog.md格式+编译前更新时�?|
| 复杂任务流水�?| [project-rules/complex-task-pipeline.md](./project-rules/complex-task-pipeline.md) | 五阶段流水线+硬性约束（单子代理�?2文件�?反模�?|
| 子代理质量管�?| [project-rules/sub-agent-quality-management.md](./project-rules/sub-agent-quality-management.md) | 分级子代理策略（低风险强�?高风险禁止）+prompt四要�?主代理监�?二次验证+兜底机制 |
| 全局思考检查清�?| [project-rules/global-thinking-checklist.md](./project-rules/global-thinking-checklist.md) | 改动功能前强制门禁：前端入口+后端接口+数据�?覆盖安装+使用场景+回填�?维度盘点 |
| 错误沉淀机制 | [project-rules/spec-sedimentation-mechanism.md](./project-rules/spec-sedimentation-mechanism.md) | 错误→沉淀→子规范→主规范引用闭环+5条沉淀规则+3次验证流�?|
| 数据库升级安全规�?| [project-rules/database-migration-safety.md](./project-rules/database-migration-safety.md) | DatabaseView修改DROP+CREATE+migration runCatching+version递增+覆盖安装兼容�?|
| 真机测试流程复用 | [project-rules/real-device-test-reuse.md](./project-rules/real-device-test-reuse.md) | 可用脚本清单+测试流程模板+问题闭环+数据库验证（WAL�?校验必须触发真实路径 |
| 包名规范 | [project-rules/package-naming.md](./project-rules/package-naming.md) | 构建APK包名配置+与原版共�?|
| 延伸版本参�?| [project-rules/forks-reference.md](./project-rules/forks-reference.md) | 网络�?前端/协程/WebView/数据管理组件优化或功能借鉴任务的方法论 |

---

## 二、项目流程（docs/project-flow/�?

> 项目架构和模块的详细技术文档，按需加载�?

### 快速入�?

| 文档 | 核心内容 |
|------|----------|
| [project-flow/quick-reference.md](./project-flow/quick-reference.md) | 命令/文件/版本锁定速查 |
| [project-flow/task-navigation.md](./project-flow/task-navigation.md) | 14个任务导航表（按任务类型索引代码锚点�?|
| [project-flow/build-apk-guide.md](./project-flow/build-apk-guide.md) | APK打包全流程：环境搭建+签名+构建+包名修改 |
| [project-flow/INDEX.md](./project-flow/INDEX.md) | 关键词索引（A-Z�?|

### 架构文档

| 文档 | 核心内容 |
|------|----------|
| [project-flow/architecture/rule-engine.md](./project-flow/architecture/rule-engine.md) | SourceRule状态机+五种解析+JS环境+WebJs模式+变量系统+ruleType常量 |
| [project-flow/architecture/rule-engine-algorithms.md](./project-flow/architecture/rule-engine-algorithms.md) | SourceRule完整规范+RuleAnalyzer完整算法+五种解析器算法细�?Mode枚举 |
| [project-flow/architecture/rule-engine-js-env.md](./project-flow/architecture/rule-engine-js-env.md) | AnalyzeRule/AnalyzeUrl环境绑定+ajax跨域请求+Rhino编译缓存+共享作用�?@put/@get变量机制 |
| [project-flow/architecture/skill-architecture.md](./project-flow/architecture/skill-architecture.md) | Skill架构：金字塔架构+5阶段工作�?JVM仿真�?basic-memory经验引擎+固化脚本+审计�?|
| [project-flow/architecture/multi-agent-analysis-spec.md](./project-flow/architecture/multi-agent-analysis-spec.md) | 五阶段流水线+单代理≤12文件+并行+交叉验证+导航同步 |
| [project-flow/architecture/overview.md](./project-flow/architecture/overview.md) | 项目架构总览 |
| [project-flow/architecture/android-ui.md](./project-flow/architecture/android-ui.md) | MainActivity导航+ReadBookActivity三层继承+RSS UI+Activity体系+Fragment+Widget+Theme |
| [project-flow/architecture/api-dataflow.md](./project-flow/architecture/api-dataflow.md) | HTTP/WebSocket/Beacon完整链路+API对照�?|
| [project-flow/architecture/app-init.md](./project-flow/architecture/app-init.md) | 50步启动流�?常量系统+EventBus+异常体系+监控 |
| [project-flow/architecture/base-layer.md](./project-flow/architecture/base-layer.md) | BaseActivity/VMBaseActivity/BaseViewModel/BaseService/RecyclerAdapter/Diff+动画 |
| [project-flow/architecture/frontend.md](./project-flow/architecture/frontend.md) | Vue3 MPA架构+config/types�?模块+路由+组件�?技术栈 |
| [project-flow/architecture/frontend-components.md](./project-flow/architecture/frontend-components.md) | Vue3 Web重构方案—组件与页面：路由设�?页面组件+通用组件 |
| [project-flow/architecture/frontend-stores.md](./project-flow/architecture/frontend-stores.md) | Vue3 Web重构方案—Store与API层：TypeScript类型定义+Pinia Store+API调用�?|
| [project-flow/architecture/network-layer.md](./project-flow/architecture/network-layer.md) | OkHttp拦截器链+SSL全信�?Cookie双层+Cronet加�?代理 |

### 模块文档

| 文档 | 核心内容 |
|------|----------|
| [project-flow/modules/webbook-search.md](./project-flow/modules/webbook-search.md) | WebBook双版�?并发搜索调度+四分类聚合去�?发现/详情/目录/正文全链�?|
| [project-flow/modules/content-pipeline.md](./project-flow/modules/content-pipeline.md) | ContentProcessor七步管线+替换规则引擎+分段/简�?样式适配 |
| [project-flow/modules/reading-engine.md](./project-flow/modules/reading-engine.md) | ReadBook状态机+三章缓存+预下�?翻页跳章+漫画+音频 |
| [project-flow/modules/reading-engine-pagination.md](./project-flow/modules/reading-engine-pagination.md) | durChapterPos字符偏移分页机制+TextChapter数据结构+页面计算算法+6种翻页动�?|
| [project-flow/modules/reading-engine-media.md](./project-flow/modules/reading-engine-media.md) | ReadManga漫画阅读+AudioPlay音频播放+BookType位标�?|
| [project-flow/modules/data-layer.md](./project-flow/modules/data-layer.md) | 21实体+21DAO+1视图+BookChapter复合主键+AutoMigration+位标�?TypeConverter |
| [project-flow/modules/web-service.md](./project-flow/modules/web-service.md) | NanoHTTPD路由+14POST+12GET+4控制�?WebSocket+静态服�?|
| [project-flow/modules/local-book.md](./project-flow/modules/local-book.md) | TXT编码检�?目录规则自动�?EPUB懒加�?PDF/MOBI |
| [project-flow/modules/service-layer.md](./project-flow/modules/service-layer.md) | WebDAV同步+下载缓存+TTS朗读+RSS子系�?JS扩展函数 |
| [project-flow/modules/config-system.md](./project-flow/modules/config-system.md) | AppConfig/ReadBookConfig/ThemeConfig/SourceConfig/LocalConfig |
| [project-flow/modules/android-services.md](./project-flow/modules/android-services.md) | 11个Service+WebSocketServer+ExoPlayer+朗读状态机+音频焦点+WakeLock+通知 |
| [project-flow/modules/backup-restore.md](./project-flow/modules/backup-restore.md) | 21数据源JSON导出+AES加密+WebDAV同步+Mutex并发 |
| [project-flow/modules/remote-third-party.md](./project-flow/modules/remote-third-party.md) | RemoteBook/WebDAV浏览+Glide/GSYVideo/ExoPlayer+更新系统 |
| [project-flow/modules/js-extensions.md](./project-flow/modules/js-extensions.md) | 30+ JS可调用方法：ajax/connect/webView/cache/file/encode/python |
| [project-flow/modules/source-management.md](./project-flow/modules/source-management.md) | 导入/导出/校验/调试/登录/18+过滤/排序全链�?|
| [project-flow/modules/model-layer.md](./project-flow/modules/model-layer.md) | ReadAloud/VideoPlay/BookCover/CheckSource/Debug/RuleUpdate/SharedJsScope |
| [project-flow/modules/rss-subsystem.md](./project-flow/modules/rss-subsystem.md) | Rss调度+RssParserByRule规则解析+RssParserDefault标准解析+文章流UI |
| [project-flow/modules/rss-image-type-analysis.md](./project-flow/modules/rss-image-type-analysis.md) | 图片类型订阅源（type=1）内容规则加载图片完整链�?ruleContent适配方式+coverDecodeJs解密+与BookSource差距分析 |
| [project-flow/modules/tools-infrastructure.md](./project-flow/modules/tools-infrastructure.md) | utils工具�?协程封装+加密+广播接收�?|
| [project-flow/modules/custom-libraries.md](./project-flow/modules/custom-libraries.md) | MOBI解析引擎+WebDAV客户�?主题引擎+阿里云TTS |

### 数据库文�?

| 文档 | 核心内容 |
|------|----------|
| [project-flow/database/overview.md](./project-flow/database/overview.md) | 数据库架构总览 |
| [project-flow/database/entities.md](./project-flow/database/entities.md) | 实体详细定义 |
| [project-flow/database/tables.md](./project-flow/database/tables.md) | 数据库v89全部21张表完整DDL+索引定义+约束说明 |

---

## 三、功能设计（docs/specs/�?

> 功能设计文档，按 OpenSpec 工作流程管理�?

### 活跃 Specs

| 文档 | 说明 |
|------|------|
| [specs/INDEX.md](./specs/INDEX.md) | 项目状态面�?功能状�?|
| [specs/TEMPLATE.md](./specs/TEMPLATE.md) | 功能设计文档模板 |
| [specs/archive-ui-migration-202608/](./specs/archive-ui-migration-202608/) | Archive 前端 UI 迁移整合（放弃自研增量 Compose 化，整体迁移 Rimchars/legado 最新 tag archive-v3-3.26.08172114 UI 层替换本项目 UI；Cronet 150→500.0.1 cronet-bundled 去内部打包减体积；深度差异分析=后端 WebBook 11/12 兼容+编译硬约束 3 点+主题系统 32 字段/~68 key 重做+数据库 v104 并入 25 实体 5 批迁移+特色功能 A/B 分级 P0/P1/P2 整合；10 阶段迁移流水线+UI 标准实时沉淀+项目标识还原+独立项目实施） 🔄 设计中 |
| [specs/sniff-stability-enhance-20260731/](./specs/sniff-stability-enhance-20260731/) | 嗅探稳定性增强（基于logs(8)真机日志深度分析9个优化点：P0 R5嗅探去重�?1%浪费消除/P1 DoH负缓�?0s�?0s+健康检�?视频流强制HTTP/1.1+favicon.ico缓存/P2 StreamReset重用NonCancellable+日志采样+证书错误记忆/P3 play.php预解�?window.__videoUrls__容错�?🔄 设计�?|
| [specs/bugfix-20260730-batch1/](./specs/bugfix-20260730-batch1/) | 真机测试Bug修复批次1�?个BUG：图片头部遮�?播放器UI入口缺失+CDN缓存清除+"未找到订�?提示+ExoPlayer LoadControl共享线程错误+DoH DNS冷启�?Cronet降级+InsetsSource警告�?🔄 设计�?|
| [specs/cronet-proguard-fix-20260731/](./specs/cronet-proguard-fix-20260731/) | release包Cronet ProGuard规则修复（R8混淆移除org.chromium.net.Cronet入口类导致libcronet.so JNI_OnLoad SIGABRT崩溃9次，嗅探能力减弱；精准补全keep规则保留API入口类） 🔄 设计�?|
| [specs/cronet-so-download-fix-20260731/](./specs/cronet-so-download-fix-20260731/) | Cronet SO下载修复+嗅探能力恢复（真机日志铁证：DoH 3服务器全失败+HTTP/2协议错误降级OkHttp+SO下载源Google Storage国内不稳定；修复DoH服务器配置增加阿里腾�?切换SO下载源到GitHub Releases+修复下载逻辑+优化HTTP/2降级时长+恢复嗅探超时5s�?🔄 设计�?|
| [specs/cronet-global-enable-20260731/](./specs/cronet-global-enable-20260731/) | Cronet 全局启用深度分析与优化方案（深度分析4大已用模块OkHttp/ExoPlayer/DoH/AnalyzeUrl+3大未用模块WebView/Glide/HttpURLConnection；识别isCronet开关不一致问题：ExoPlayer+DoH不受开关控制；统一开关逻辑+日志诊断增强+ProGuard规则完善�?🔄 设计�?|
| [specs/rhino-engine-upgrade/](./specs/rhino-engine-upgrade/) | Rhino 引擎升级兼容性分析（字节码实证：1.9.1 唯一 VarHandle 出处 SlotMapOwner$ThreadedAccess；运行时探针证实该项目配置下�?class 永不加载�?6/26 书源片段通过、书源型负载 +31%；唯一障碍收敛为构建期 D8 反糖化） �?已完�?�?最终决�?保持锁定 1.8.1，沉淀「待�?minSdk�?3 直跳 1.9.1」里程碑 |
| [specs/multiline-on-demand-extraction/](./specs/multiline-on-demand-extraction/) | 多线路多集按需采集架构优化（ruleContent只返回播放页URL，VideoUrlExtractor统一入口三层降级按需采集m3u8，参考影视仓两阶段架构） 🔄 开发中 |
| [specs/sniff-migration-booksource/](./specs/sniff-migration-booksource/) | 嗅探与滑动切换能力迁移至书源（图片嗅探→type2书源 ReadManga 0图兜�?reuse ImageSnifferWebView / 视频嗅探→type4书源复用统一三层入口 extractVideoUrlForEpisode 泛化 ruleData 解决播放页URL / 上下滑动切换�?下集 episodes 驱动多页；零数据库变更、RSS 不受影响�?�?已完成（代码实施+编译通过+RSS 真机回归通过；书源侧真机验证因无测试源由用户决策改源码级验证�?|
| [specs/tvbox-source-converter/](./specs/tvbox-source-converter/) | TVBox/影视仓播放源转化�?legado 订阅源（字段映射+类型适配+规则转换+批量处理�?🔄 设计�?|
| [specs/legados-forks-comparison/](./specs/legados-forks-comparison/) | legados Fork 对比与集成方案（分析GEd520/legados fork差异，P0/P1/P2三级集成候选，HelpDoc/MemoryPressure/JsCacheManager�?0项集成设计） 🔄 设计�?|
| [specs/forks-ecosystem-analysis/](./specs/forks-ecosystem-analysis/) | Legado 延伸版本生态功能深度分析（更新10+下载7=17个直系fork源码仓库�?大功能领域横向对比排除UI维度，输出汇总式analysis-report+三态borrow-decisions借鉴决策矩阵�?🔄 实施中（阶段B系列：B12/B14/B15/B16 已落地，真机验证已执行通过，详�?issues-found.md�?|
| [specs/precise-manage/](./specs/precise-manage/) | 精准管理聚合页（借鉴 Legado_Max：我的页新增入口聚合网址记录/存储管理/下载管理/文件管理，View 体系重写；网址记录=OkHttp 拦截�?Room 新表 Migration 102�?03+搜索/筛�?日期分组/批量清除；存储管�?复用 cache 统计 API 8 类缓存清理；下载管理=DownloadState 内存单例+500ms 轮询系统 DownloadManager 列表页） �?已实施（2026/08/08 编译+单测 186 通过，待真机�?|
| [specs/tvbox-optimization/](./specs/tvbox-optimization/) | 借鉴影视仓优点优�?legado（播放器双引�?网络层catvod/QuickJS+DLNA投屏+本地服务器） 🔄 设计�?|
| [specs/rss-age-verify-autobypass/](./specs/rss-age-verify-autobypass/) | RSS 订阅源年龄验证自动绕过（三层防护：Header Cookie 预置 + loginCheckJs 自动验证 + injectJs 自动点击�?🔄 设计�?|
| [specs/cookie-management-fix/](./specs/cookie-management-fix/) | Cookie 管理链路修复（WebView↔CookieStore↔OkHttp 同步断裂6问题：P0 Cookie不回�?P1过期清理+P2全局清空+P3死代�?P4域名不匹配） 🔄 设计�?|
| [specs/apk-release-publish-20260729/](./specs/apk-release-publish-20260729/) | APK 发布�?Gitee+GitHub Release（Python 脚本一键发布三包到双平�?Release，版本号从文件名提取，updateLog 自动作为 body，token 配置不入 git�?🔄 设计�?|
| [specs/image-gallery-activity/](./specs/image-gallery-activity/) | 图片浏览�?Activity 化改造（PhotoDialog 单图弹出→ImageGalleryActivity 多图浏览，参�?VideoPlayerActivity 架构，ViewPager2 双层嵌套+跨文章切�?旋转/缩放/长按保存�?🔄 实施完成待L2真机验证 |
| [specs/image-canvas-thread-fix-20260728/](./specs/image-canvas-thread-fix-20260728/) | 图片画廊图片不显示根因修复（Glide downloadOnly 回调�?glide-disk-cache-thread 触发，SSIV.recycle() 创建 GestureDetector �?Handler 异常，被 CallbackException 吞掉不触�?onLoadFailed；修复：onResourceReady/onLoadFailed �?itemView.post 切主线程�?🔄 设计�?|
| [specs/player-review-and-optimization/](./specs/player-review-and-optimization/) | 视频/图片播放器审查与优化整合（基�?份审查报�?1份多维度审查整合报告，共32 ERROR+44 WARN+32 INFO=108项，�?2个ADR决策；R2修订完成：AD-01保留L4不缓�?AD-06 centerCrop替代fitXY/AD-10补充22类硬编码颜色/AD-12 PlayerControlsHelper替代BasePlayerActivity�?🔄 设计中（R2 修订完成，待实施�?*图片部分已废弃，�?image-player-vertical-canvas-optimization 取代**�?|
| [specs/video-prebuffer-enhancement/](./specs/video-prebuffer-enhancement/) | 视频播放器分段预缓冲机制深度分析与优化（源码深度分析+对标Media3 DefaultPreloadManager；发现P0 BUG：FirstFramePreloader/VideoPreloader的readBytes无限�?未写入SimpleCache导致预加载完全无效；P0修复+P1 HLS setAllowChunklessPreparation+运行时NetworkCallback+P2埋点评估�?🔄 设计�?|
| [specs/video-buffer-speed-optimization/](./specs/video-buffer-speed-optimization/) | 当前播放视频缓冲速度优化（聚焦当前视频非预加载；7层联合优化：LoadControl深度调优 setTargetBufferBytes(-1)+setPrioritizeTimeOverSizeThresholds / HLS LL-HLS targetOffsetMs+超时配置 / OkHttp EventListener+Dispatcher / CacheDataSource FLAG_IGNORE_CACHE_ON_ERROR / 自适应码率 / 解码器异步队�?/ AnalyticsListener 性能监控埋点�?2个ADR决策�?5个需求项R1-R15�?0个验证场景） 🔄 设计�?|
| [specs/image-player-vertical-canvas-optimization/](./specs/image-player-vertical-canvas-optimization/) | 内置图片播放器垂直画布优化方案（�?RecyclerView 垂直长画�?点击进入 ViewPager2 大图+滚动到底部自动加载下一篇，取代 player-review-and-optimization 图片部分，含 13 �?ADR + 17 个验证场�?+ 48 项任务） �?V4 设计审查通过+全部任务实施完成（Phase 0-8 �?48 项），待编译验证+L2 真机测试 |
| [specs/android-ui-optimization/](./specs/android-ui-optimization/) | Android UI/UX 优化（P0 Bug+Design Token+暗色模式+现代化） �?实施完成 |
| [specs/reader-overlay-compose/](./specs/reader-overlay-compose/) | 阅读器浮层 Compose 化（S5 骨架四阶段完成：菜单层顶栏MenuTitleBar+底栏MenuBottomBar+scrim Compose化 / activeSheet单态收敛 / 阅读设置Sheet / ReaderUiState单StateFlow / BackHandler优先级链；正文 page/ 5 文件零改动红线已实测保留；P2 §8 验收 7/8 勾选，FR-11 真机交用户回归） ✅ 已实施（真机待回归） |
| [specs/ui-redesign-m3/](./specs/ui-redesign-m3/) | UI 重构设计（v2 已完善：深度对标四仓+MoRealm墨境纯Compose现代工程标杆，五色→34槽位推导/PillNavigationBar/设置三模板/shimmer骨架屏 + 鸿蒙MyCenter三级布局；整体前端思想综合收敛五支柱+功能不裁剪红线清单A-D；v2 新增 全量84页面类功能点核对表pages-inventory + 前端UI工程规范ui-standards（6类页面骨架S1-S6/组件六族目录/状态管理范式/真机功能点覆盖测试门禁）；实现细化规格17组件签名/主题toM3Scheme映射/PR+KPI/themeConfig格式封口；ADR 01-22；保留暗夜紫默认主题；目标=前端全部Compose（正文内核保留View）丨🔄 设计v2完善 + 实施Phase0-3已落地 + Phase P1 支干实施中（2026-08-12 S1 MainActivity 接线 12.20/12.21 FR-11✅ + S4 BookInfoActivity 壳层接线 12.23 + 公共组件族两期 12.22）） |
| [specs/sigma-sync-202607/](./specs/sigma-sync-202607/) | 同步阅读Sigma 2026-07最新提交（2 bug修复+订阅�?默认值） �?已完�?|
| [specs/builtin-themes/](./specs/builtin-themes/) | 新增8个内置主题（5日间+3夜间，WCAG AA�?�?已完�?|
| [specs/legado-skill-optimization/](./specs/legado-skill-optimization/) | Legado Skill 优化 |
| [specs/legado-skill-optimization-v2/](./specs/legado-skill-optimization-v2/) | Legado Skill V2 优化（聚焦修复错误知�?门禁强化+架构瘦身，避免历�?声称完成≠实际生�?陷阱�?🔄 设计�?|
| [specs/skill-optimization/](./specs/skill-optimization/) | Legado Source Creator Skill 优化（v6：删孤岛+废弃JVM仿真�?确立Playwright MCP唯一地位+新增网站分析报告中间产物+删除legado_client Python客户�?AI手动操作工作�?移除basic-memory引用+新增经验检索三�?视频源核心要求速查+快速入�?源码阅读步骤+SKILL.md�?20�?references�?5文档�?🔄 设计�?|
| [specs/rss-batch-optimize-v2/](./specs/rss-batch-optimize-v2/) | RSS 订阅源批量优�?v2�?22源，复用v1工作�?占位�?模板源处�?域名迁移+反爬配置+skill反哺�?🔄 设计�?|
| [specs/legado-skill-v2-rebuild/](./specs/legado-skill-v2-rebuild/) | Legado Skill V2 重建 |
| [specs/skill-core-capability-rebuild/](./specs/skill-core-capability-rebuild/) | Skill 核心能力重建 |
| [specs/skill-usability-optimization/](./specs/skill-usability-optimization/) | Skill 可用性优�?|
| [specs/source-repair-loop-optimization/](./specs/source-repair-loop-optimization/) | 源修复循环优�?|
| [specs/jvm-webview-and-test-fix/](./specs/jvm-webview-and-test-fix/) | JVM WebView 与测试修�?|
| [specs/legado-core-optimization/](./specs/legado-core-optimization/) | Legado 核心质量优化（内存泄�?线程安全+ANR+错误处理+测试�?�?Batch1+2完成 |
| [specs/dependency-upgrade-optimization/](./specs/dependency-upgrade-optimization/) | 依赖升级性能优化+minSdk迁移（Coroutines 9.8x+Lifecycle 2.11+Core 1.19+7组AndroidX升级+OkHttp 5.4+WebView修复�?�?实施完成 |
| [specs/legado-skill-unified-redesign/](./specs/legado-skill-unified-redesign/) | Legado Skill 统一重设�?|
| [specs/network-perf-stability/](./specs/network-perf-stability/) | 网络组件性能与稳定性深度优化（OkHttp/Cronet/协程/缓存/图片解密，P0稳定+P1性能+P2架构�?�?实施完成（P0+P1），待真机验�?|
| [specs/ssl-handshake-investigation/](./specs/ssl-handshake-investigation/) | SSL握手失败根因排查（net_error -101）：OkHttp升级路径审计+WebView链路审计，结�?非升级导�? �?调查完成 |
| [specs/e2e-automated-testing/](./specs/e2e-automated-testing/) | APK 端到端自动化测试验证系统（MEmu+uiautomator2+AI 日志分析，一键打包→装包→跑用例→出报告�?🔄 设计�?|
| [specs/ai-tests-deep-audit/](./specs/ai-tests-deep-audit/) | ai_tests 深度审计与补全完善（15优点+14缺点+12缺失项，短期6+中期8+长期5任务�?�?审计完成 |
| [specs/e2e-ui-executor-hardening/](./specs/e2e-ui-executor-hardening/) | E2E UI 执行器加固（scroll_find 滚动查找/自愈重构/失败跳过/dismiss_dialogs 误判修复/规则分析�?uiautomator2 崩溃排除/证据收集路径修复/测试用例对齐 Compose UI�?�?实施完成，单用例 pass_rate=100% |
| [specs/apk-size-optimization/](./specs/apk-size-optimization/) | APK 体积审核与精简优化（v3：debug APK解压分析+打包技术手段全量评估，已用所有稳定优化，零功能影响预�?2.5~3.5MB，附折中选项�?🔄 设计�?|
| [specs/folder-view-welcome-refactor/](./specs/folder-view-welcome-refactor/) | 书源/订阅源文件夹视图重构 + 欢迎页增�?+ 前端样式审计 �?实施完成，待真机验证 |
| [specs/source-folder-cover/](./specs/source-folder-cover/) | 发现/订阅源文件夹封面替换（学到书架精髓：长按选图换封面+恢复默认；Room v103→104 新增 source_group_covers 表，kind+groupName 双命名空间隔离；管理页固定平铺去文件夹） 🔄 设计�?|
| [specs/video-m3u8-cache/](./specs/video-m3u8-cache/) | 视频播放�?m3u8 边下边播缓存（cachePlay 配置 + 设置开关，默认开启） �?已实施，待真机验�?|
| [specs/rss-cache-first/](./specs/rss-cache-first/) | RSS 阅读源缓存优先加载（列表�?DiffUtil 增量更新 + WebView cacheFirst 默认 true�?�?已实施，待真机验�?|
| [specs/rss-image-decrypt-optimization/](./specs/rss-image-decrypt-optimization/) | 订阅源图片解密优化（调试输出截断防崩�?+ 列表并行化提速；真机发现并修�?ImageUtils 块对齐校验误拦截 base64 文本封面致图片永不显示） �?引擎修复完成（ImageUtils 移除块校�?失败兜底bytes），真机验证图片显示通过 |
| [specs/video-mute-highspeed/](./specs/video-mute-highspeed/) | 视频播放器默认静�?+ 高倍速支持（3X/5X/10X/15X + 播放界面静音按钮�?�?已实施，待真机验�?|
| [specs/source-layout-redesign/](./specs/source-layout-redesign/) | 书源/订阅源布局设置重做（修复书源分�?bug + 视图模式扩展5�?+ 订阅源排�?+ 类型筛�?+ 统一配置对话框） 🔄 设计�?|
| [specs/exoplayer-resilience/](./specs/exoplayer-resilience/) | ExoPlayer 韧性优化（预嗅�?LRU缓存+自动WebView降级，解�?002错误码和浏览器能播放但内置播放器失败痛点�?🔄 实施�?|
| [specs/video-playback-failure-fix-20260726/](./specs/video-playback-failure-fix-20260726/) | 视频播放失败修复（基�?026-07-26真机日志深度分析�?7个Bug清单+38项任务，解决视频地址获取8.5�?嗅探超时3000ms+降级链使用过期嗅探结�?onPlayerError未记录AppLog+协程生命周期错位等核心问题，预期视频地址获取时间<3�?嗅探成功率≥90%/播放失败可追溯率100%�?�?Phase 1+2 代码改造完成（27项任务全部完成）+Phase 6 真机日志分析修复2个Bug（ImageGalleryActivity Glide销毁崩�?VideoUrlExtractor .m3u8快速路径回归）+编译验证通过，待L2真机测试 |
| [specs/player-mature-solutions-alignment/](./specs/player-mature-solutions-alignment/) | 播放器成熟方案对齐（基于V2深度架构分析+49个权威来源验证：70%真实支撑+10%AI臆想+20%成熟方案遗漏�?个Phase 22项任务：Phase1可观测�?错误反馈闭环/Phase2视频核心能力补齐（BandwidthMeter+首帧预加�?下一个视频预加载�?Phase3图片核心诉求补齐（左右滚�?图片金字�?最大尺�?智能预加载）/Phase4网络层韧性（DoH+302缓存+Cronet恢复�?Phase5架构优化（实例池+修正AI臆想设计），全部P0/P1任务有成熟方案参考支撑） �?Phase 1+2+4+5 实施完成（含实例池LoadControl档位工厂化修复），编译通过待真机测试；Phase 3 图片增强项待实施 |
| [specs/memory-mechanism-redesign/](./specs/memory-mechanism-redesign/) | 项目记忆机制改造（AI 独立记忆系统 AD-11 完全分离：项目目�?.trae/memory/ 替代 C盘，废弃 conv_id 简化方案，多任务并�?AskUserQuestion 确认，解决C盘路径Edit/Write受限痛点�?🔄 实施�?|
| [specs/sub-agent-budget-optimization/](./specs/sub-agent-budget-optimization/) | 子代理编排与思考预算优化（强制子代理规避GLM-5.2思考上限，同对话内虚拟拆分任务不增加成本，监控+质量保证+规范冲突处理�?�?已完�?|
| [specs/yesterday-changes-deep-audit/](./specs/yesterday-changes-deep-audit/) | 昨日改动�?026-07-08）深度自我审查（书源订阅源布局+视频播放器，6 Agent 并行审查发现 29 �?bug + 7 阻塞�?+ 1 需求偏差） �?审查完成 |
| [specs/context-compression-feedback-preservation/](./specs/context-compression-feedback-preservation/) | 上下文压缩用户反馈保�?+ 主线任务完成质量三层审查 + 打包功能差距三层修复（Part A 反馈持久�?四件�?+ Part B B0openspec偏差/B1代码/B2交付 + Part C C1偏差归属/C2 F1-F10核查/C3 E2E+L2�?�?已完成（D1偏差已修正，7类细节不符需新建spec�?|
| [specs/source-layout-detail-refinement/](./specs/source-layout-detail-refinement/) | 书源/订阅源布局细节精修（D1标签+分组两模�?/ D2按类型分组修�?返回�?/ D3订阅源二级页还原列表 / D4搜索�?/ D5视频缓存下拉选择 / D6倍�?5x保留�?�?实施完成待文档同�?|
| [specs/rss-video-player-enhancement/](./specs/rss-video-player-enhancement/) | 订阅源视频播放器增强（R1多集选择播放 + R2 m3u8播放失败调试日志 + R3学习旧订阅源布局 + R4日志异常优化 + R5自动抓取视频链接+Header修复404�?🔄 实施完成待用户实测（7.1/7.2/7.5/7.6 + 3.17 Bug修复 L2通过�?.3/7.4/7.7/7.8 需真实视频站点验证�?|
| [specs/douyin-style-video-player/](./specs/douyin-style-video-player/) | 抖音风格沉浸式竖屏视频播放器重设计（ViewPager2+Fragment架构 / 三种状态PURE/NORMAL/FULLSCREEN / 左下角标�?线路+集数 / 右侧快退/静音/收藏/倍�?设置/快进 / 横屏全屏+双指缩放 / 控件默认显示+双指左右滑动隐藏 / 综合设置面板BottomSheet�?🔄 实施完成待L2真机验证 |
| [specs/video-article-swipe-switch/](./specs/video-article-swipe-switch/) | 视频播放器上下滑动切换文章（ViewPager2+Fragment+文章列表模式+分页加载+预缓�?位置记忆�?�?实施完成（阶�?-8全部代码完成+L2验证通过�?|
| [specs/video-control-visibility-enhancement/](./specs/video-control-visibility-enhancement/) | 视频播放器控件显隐与缓冲条优化（F1缓冲进度条修�?secondaryProgress绑定 / F2控件3秒自动隐�?单击切换+触摸事件根因修复OnTouchListener设到surface_container�?�?实施完成（L2真机验证通过�?|
| [specs/video-ui-dedup-layout-adjust/](./specs/video-ui-dedup-layout-adjust/) | 视频播放�?UI 去重与布局调整（移除右侧静�?倍速按钮避免与GSY底部控件重叠 + 左下角标题区和全屏按钮上�?2dp避免遮挡GSY底部播放�?+ VideoFragment.kt死代码清理） �?实施完成（Phase 1-4全部完成+L2验证通过�?|
| [specs/video-playback-issues-round1/](./specs/video-playback-issues-round1/) | 视频播放问题修复�?轮（10类问题：ExoPlayer失败降级WebView用skill V2模板 + 播放器类型配�?+ ViewPager2兼容�?+ 加密解密容错 + ClassCastException容错 + SQLiteBlobTooBig容错 + WebView线程安全 + 网络重试 + JSON容错 + HlsPlaylistStuck + Cronet回退�?�?实施完成（L2真机验证通过�?.6 ViewPager2滑动切换核心修复 onInterceptTouchEvent 方案�?|
| [specs/video-back-fullscreen-fix/](./specs/video-back-fullscreen-fix/) | 视频播放器返回按钮修�?全屏按钮迁移+真全屏优化（B1: setNavigationOnClickListener绕过onSupportNavigateUp时序冲突 / U1: btn_fullscreen移入right_buttons随整体显�?/ F1: TitleBar gone()替代ActionBar hide()释放布局空间�?🔄 开发中（代码完�?L1通过，待真机L2验证�?|
| [specs/video-gesture-overhaul/](./specs/video-gesture-overhaul/) | 视频播放器手势交互重构（修复长按加速丢�?去掉快退快进按钮改左右滑�?长按倍�?双击暂停/播放�?种手势统一管理不冲突） �?已完�?|
| [specs/spec-system-optimization/](./specs/spec-system-optimization/) | 规范体系优化（三层规范结构：全局通用规范→项目主规范→项目子规范，AGENTS.md核心步骤+索引格式，全局规范整合去重，压缩恢复强制加载项目主规范，违禁词三道防线，子规范强制加载机制�?�?已完成（检查点3最终验收通过 2026-07-13，整合策略已被global-spec-restructure颠覆�?|
| [specs/global-spec-restructure/](./specs/global-spec-restructure/) | 全局规范重组（多文件拆分策略�?1个全局规范文件，核�?文件9.42KB系统注入+6个按需加载，AGENTS.md瘦身533�?54行，test-prompt.md待新对话验证�?🔄 实施中（检查点2�?|
| [specs/app-stability-round2/](./specs/app-stability-round2/) | App 稳定性第二轮修复（P1-1~P1-4+P2-1~P2-2+P3-1�?项：Room去description+图片解密文件头检�?ExoPlayer setMimeType+视频抓取流程优化+Cronet运行时降�?协程取消守卫+ruleContent非空分支content校验�?�?全部完成（检查点3验收通过�?6源扩展测试通过�?|
| [specs/build-workflow-optimization/](./specs/build-workflow-optimization/) | 打包流程规整（统一包名规范：测试包/共存�?正式包三种分类，修复build-legado.bat默认包名不一致，设计面向AI执行的详细打包流程，更新build-apk-guide.md�?🔄 设计�?|
| [specs/rss-concurrency-and-checksource-optimization/](./specs/rss-concurrency-and-checksource-optimization/) | 订阅源解析并发配置化+书源/订阅源校验去重优化（需求一：Semaphore(6)配置�?图片加载并发+双参数分离；需求二：书源域名校验走AnalyzeUrl真实请求+订阅�?维度校验+域名+type多维度去重） 🔄 设计�?|
| [specs/real-device-test-plan/](./specs/real-device-test-plan/) | 真机测试计划：rss-concurrency-and-checksource-optimization �?4项变更功能真机端到端测试（分层UI+Service+数据+日志，用真实书源数据，weight回填验证，经验沉淀�?🔄 设计�?|
| [specs/global-issue-fix-and-spec-sedimentation/](./specs/global-issue-fix-and-spec-sedimentation/) | 全局问题修复与规范沉淀�?3项用户反馈：数据库升级覆盖安�?高亮规则崩溃+校验逻辑重构+lastHost三层回填+UI Bug修复+工程规范沉淀机制+全局思考检查清单） 🔄 设计�?|
| [specs/v3.26.0717-bug-fix-batch/](./specs/v3.26.0717-bug-fix-batch/) | v3.26.0717 真机测试 Bug 批量修复�?问题：订阅源并发显示+颜色选择器主�?替换规则崩溃+设置项数值显�?域名分组排序+视图布局评估�?🔄 设计�?|
| [specs/rss-parse-optimization/](./specs/rss-parse-optimization/) | 订阅源解析全流程性能优化�?维度22个优化点�?个P1+17个P2，核�?项分三批实施：Pattern缓存+RssArticle索引/scriptCache全局共享+HTTP响应缓存/解密缓存扩容+预连接） �?全部完成（检查点3验收通过�?文件+106行变更，APK legado_app_3.26.071419.apk�?|
| [specs/source-layout-bookshelf-style/](./specs/source-layout-bookshelf-style/) | Issue-6 书源/订阅源布局参考书架重构（方案D�?个XML重构+SourceExt.kt新建+4个Adapter适配+订阅源upSourceHost链路改�?RssSourceActivity异常输入修复�?1个ADR�?�?实施完成（编译通过+真机启动无崩溃，APK legado_app_3.26.071720.apk�?|
| [specs/forks-archive-comparison/](./specs/forks-archive-comparison/) | 阅读 Archive 私仓深度对比与借鉴分析（克�?Rimchars/legado-private-armv8-release �?temp/forks-comparison/legado-archive�? 大维度子代理并行对比：主�?EPUB/AI/发现�?视频/构建/依赖，输出三态借鉴决策�?12借鉴/8不借鉴/9待评估，不修改本项目源码�?🔄 待验�?|
| [specs/rss-unified-search/](./specs/rss-unified-search/) | 订阅源统一搜索（对标书架搜索：新建 RssSearchActivity+RssSearchModel 并发调度所有带 searchUrl 的订阅源，title+pubDate 去重聚合多源，支持换源，复用 SearchKeyword 表加 type 字段�?🔄 设计�?|
| [specs/rss-v5_7-deep-fix/](./specs/rss-v5_7-deep-fix/) | RSS 订阅�?V5.7 深度修复�?3 启用�?12 必备字段规则修复 + 15 CF盾源破盾恢复 + 7 timeout 源重�?+ 5维度真机验证 + 陷阱68-72沉淀 + ADR Y-Statement 5项决策） 🔄 设计�?|
| [specs/logging-audit-and-enhancement/](./specs/logging-audit-and-enhancement/) | 日志规范全面审查与补全完善（核心模块catch块日志覆盖：WebBook 90%缺失+规则引擎40%+网络�?7%，统一模块Tag规范+ai_tests通用日志获取脚本+规范文档优化�?🔄 设计�?|
| [specs/thread-pool-split-config/](./specs/thread-pool-split-config/) | 书源线程池拆分与自定义配置（共用 threadCount 拆分�?searchThreadCount + updateCacheThreadCount 两个独立配置�?0+ 业务点归类替换，UI 自定义入口，老用户自动迁移） �?实施完成（仅本地commit+验收通过�?
| [specs/thread-pool-audit/](./specs/thread-pool-audit/) | 线程池配置全面审查（13项配置点静态审查：8个FixedThreadPool+globalExecutor+DispatchersMonitor+OkHttp连接�?Dispatchers.IO+Coroutine.kt，识别泄漏风�?性能瓶颈/默认值合理性，输出P0/P1/P2优化建议�?🔄 设计�?|
| [specs/highlight-rule-fix-20260727/](./specs/highlight-rule-fix-20260727/) | 阅读高亮规则系统修复（isRegex 修正+首启播种+upsert+即时生效+fill 快绘补画�? 项根因修复） �?已实施（核心修复完成，回归由 highlight-rule-restore-default-20260729 修复�?|
| [specs/highlight-rule-restore-default-20260729/](./specs/highlight-rule-restore-default-20260729/) | 高亮规则丢失修复 + 恢复默认规则（修复愈合逻辑覆盖用户 pattern �?BUG + 新增"恢复默认规则"菜单支持合并/覆盖模式，解决用户清空后无法恢复内置常规规则痛点�?🔄 实施中（Phase A/B 完成，待编译+真机验收�?|
| [specs/video-player-m3u8-fix/](./specs/video-player-m3u8-fix/) | 内置视频播放�?m3u8 播放失败深度分析与优化（m3u8 URL 短路嗅探+HLS fallback 链去�?分片重试策略增强+Cache-Control 请求头移除） 🔄 设计�?|
| [specs/source-arch-mutual-borrow/](./specs/source-arch-mutual-borrow/) | 书源/订阅源架构差异分析与机制层互补优�?V2（按用户反馈推翻V1字段借鉴方案；抽�?个共享机制组件：M1并发控制/M2正文URL过滤/M3缓存策略/M4预连�?M5WebView控制/M6网络请求统一；零实体字段增加+零数据库迁移；WebBook.kt 4�?Rss.kt 2处重复网络请求模式统一；修复RssSource.parseConcurrency未落地BUG；分6批实施M6→M1→M4→M2→M3→M5�?🔄 设计�?V2 |
| [specs/harden-blank-highlight-rules-20260808/](./specs/harden-blank-highlight-rules-20260808/) | 高亮规则空数据自动修复（根因：用户升级后 prefs 存储 12 条规�?name/pattern 全空导致列表�?编辑�?不生效；HighlightRuleStore.load() 增加"全部规则 name+pattern 为空→自�?reset 恢复内置规则"自愈加固�?�?实施完成（编�?真机验证：全空注入自动恢复、混合数据不误伤、正常数据无自愈日志�?|
### 归档 Specs

| 文档 | 说明 |
|------|------|
| [specs/archive/skill-improvement/](./specs/archive/skill-improvement/) | Skill 改进设计文档 |
| [specs/archive/skill-architecture-optimization/](./specs/archive/skill-architecture-optimization/) | Skill 架构优化设计 �?已完�?|
| [specs/archive/skill-html-fetch-enhancement/](./specs/archive/skill-html-fetch-enhancement/) | Skill HTML 获取能力增强 �?已完�?|
| [specs/archive/test-infra-upgrade/](./specs/archive/test-infra-upgrade/) | 测试基础设施升级 ⚠️ 代码实现完成，测试验证缺�?|
| [specs/archive/skill-trio-optimization/](./specs/archive/skill-trio-optimization/) | Skill 三件套优�?🔄 进行�?|
| [specs/archive/skill-deep-optimization-v2/](./specs/archive/skill-deep-optimization-v2/) | Skill 深度优化 V2 �?已完�?|

---

## 四、核�?Skill�?trae/skills/legado-source-creator/�?

> 项目核心工具：Legado 书源/订阅源智能创建器�?9 条陷阱检查�? 阶段闭环工作流�?0 大参考目录�?6 个验证脚本�?

### 核心文档

| 文档 | 核心内容 |
|------|----------|
| [SKILL.md](../.trae/skills/legado-source-creator/SKILL.md) | 主文档：规则引擎完整知识+79条陷阱检查清�?5阶段闭环工作�?|
| [AI_README.md](../.trae/skills/legado-source-creator/AI_README.md) | AI使用指南：快速开�?脚本使用+工作流程+经验反哺规范 |

### 参考文档索引（10 大目录）

| 目录 | 子文档数 | 核心内容 |
|------|----------|----------|
| [references/](../.trae/skills/legado-source-creator/references/_INDEX.md) | 4 核心文档 | 规则语法+URL模板+实体字段+示例�?|
| [references/troubleshooting/](../.trae/skills/legado-source-creator/references/troubleshooting/_index.md) | 6 子文�?| 常见陷阱与故障排�?|
| [references/js-extensions/](../.trae/skills/legado-source-creator/references/js-extensions/_index.md) | 11 子文�?| JS扩展函数完整参�?|
| [references/js-patterns/](../.trae/skills/legado-source-creator/references/js-patterns/_index.md) | 11 子文�?| JS模式参考手�?|
| [references/special-scenarios/](../.trae/skills/legado-source-creator/references/special-scenarios/_index.md) | 13 子文�?| 登录/验证�?加密/视频等特殊场�?|
| [references/source-analysis/](../.trae/skills/legado-source-creator/references/source-analysis/_index.md) | 6 子文�?| 源码分析验证结果 |
| [references/site-features/](../.trae/skills/legado-source-creator/references/site-features/_INDEX.md) | 5 子文�?| 站点特征与规则类型映�?|
| [references/rule-construction-guide/](../.trae/skills/legado-source-creator/references/rule-construction-guide/_index.md) | 3 子文�?| 规则构建指南 |
| [references/known-fix-patterns/](../.trae/skills/legado-source-creator/references/known-fix-patterns/_index.md) | 8 子文�?| 已知修复模式 |
| [references/cms-samples/](../.trae/skills/legado-source-creator/references/cms-samples/_INDEX.md) | 2 子文�?| CMS模板样本 |

### 工具：JVM 规则引擎仿真�?

| 工具 | 用�?|
|------|------|
| `tools/legado-jvm/build/libs/legado-jvm.jar` | JVM 仿真器（统一JAR，Rhino+jsoup+hutool+AnalyzeRule�?|
| `scripts/legado_client/client/rule_engine_client.py` | Python 客户端（调用 JVM 仿真器） |
| [references/source-analysis/ajax-diff-analysis.md](../.trae/skills/legado-source-creator/references/source-analysis/ajax-diff-analysis.md) | ajax 差异分析文档 |

### 验证脚本

| 脚本 | 用�?|
|------|------|
| `scripts/quick-verify.py` | 浅层可用性验证（网站存活+HTTP�?|
| `scripts/verify-source.py` | 深度链路验证（规则引擎模拟解析） |
| `scripts/debug-source.py` | 端到端真机级调试 |
| `scripts/generate-js-doc.py` | 提取JS模式生成文档 |
| `scripts/deep-analyze-js.py` | 深度JS分析（变量传递链/加密模式�?|

### 固化脚本

| 脚本 | 用�?|
|------|------|
| `scripts/verify-decrypt.py` | AES/DES 解密验证 |
| `scripts/verify-selector.py` | CSS 选择器验�?|
| `scripts/verify-image.py` | 图片加密验证 |
| `scripts/analyze_site.py` | 网站结构分析 |
| `scripts/verify-source.py` | 源完整性验�?|
| `scripts/diagnose-failures.py` | 失败诊断 |
| `scripts/run-full-regression.py` | 全量回归 |
| `scripts/quick-test-sources.py` | 快速批量测�?|

### 辅助脚本

| 脚本 | 用�?|
|------|------|
| `scripts/html_fetcher.py` | HTML获取回退�?|
| `scripts/diagnose-failures.py` | 失败诊断 |
| `scripts/run-full-regression.py` | 全量回归 |

### 模板文件

| 文件 | 用�?|
|------|------|
| `templates/auto-video-player.html` | 自动视频播放器模�?|
| `templates/hls-video-player.html` | HLS视频播放器模�?|
| `templates/inject-video-player.js` | 注入式视频播放器JS |

---

## 五、工作流审计�?Skill�?trae/skills/legado-workflow-auditor/�?

> 书源/订阅源创建或优化任务完成后的强制审计工具，确�?Phase 完成标志、basic-memory 执行证据、自测交付流程的合规性�?

| 文档 | 核心内容 |
|------|----------|
| [SKILL.md](../.trae/skills/legado-workflow-auditor/SKILL.md) | 审计规则+检查清�?审计报告模板 |
