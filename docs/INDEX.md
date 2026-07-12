# 文档索引

> 项目所有文档的统一入口，覆盖项目规范、项目流程、功能设计、核心 Skill 四类文档。

---

## 一、项目规范（docs/project-rules/）

> AI Agent 编码时必须遵循的项目特有规则，按需加载。

| 规范 | 文件 | 核心内容 |
|------|------|----------|
| 命名规范 | [project-rules/naming_rules.md](./project-rules/naming_rules.md) | 类后缀约定+up/dur/Await缩写+常量混合风格+扩展函数组织+包结构 |
| 代码风格 | [project-rules/checkstyle_rules.md](./project-rules/checkstyle_rules.md) | Coroutine链式封装+双版本模式+kotlin.runCatching+object单例+@IntDef+顶层lazy |
| 异常处理 | [project-rules/exception_rules.md](./project-rules/exception_rules.md) | NoStackTraceException体系+四种捕获模式+网络错误链+协程异常 |
| 日志规范 | [project-rules/logging_rules.md](./project-rules/logging_rules.md) | AppLog+LogUtils+DebugLog三层体系+标签约定+使用规则 |
| 架构模式 | [project-rules/architecture_rules.md](./project-rules/architecture_rules.md) | 手动DI+ViewModel模式+Room配置+Web服务器+事件系统+模块依赖+构建配置 |
| 测试规范 | [project-rules/testing_rules.md](./project-rules/testing_rules.md) | JUnit4+书源自测三阶段+测试运行命令 |
| 工作流程 | [project-rules/openspec-workflow.md](./project-rules/openspec-workflow.md) | OpenSpec四文档+强制检查点+文档同步映射表 |
| 延伸版本对比方法论 | [project-rules/forks_comparison_methodology.md](./project-rules/forks_comparison_methodology.md) | 27+延伸版本清单+五阶段对比流程+优先级矩阵+踩坑案例 |
| E2E测试流程 | [project-rules/ai_e2e_testing_workflow.md](./project-rules/ai_e2e_testing_workflow.md) | 5.5.1-5.5.8八步强制流程+固化层保护+V3.1快速验证脚本 |
| 测试用例设计 | [project-rules/test-case-design-guide.md](./project-rules/test-case-design-guide.md) | 双轨制+源码溯源字段+步骤语义化 |
| 改造过程日志 | [project-rules/logging-during-refactoring.md](./project-rules/logging-during-refactoring.md) | 10类必加日志场景+永久/临时双轨+Tag规范+验证检查清单 |
| 版本交付同步 | [project-rules/version-delivery-sync.md](./project-rules/version-delivery-sync.md) | 同步清单+updateLog.md格式+编译前更新时机 |
| 复杂任务流水线 | [project-rules/complex-task-pipeline.md](./project-rules/complex-task-pipeline.md) | 五阶段流水线+硬性约束（单子代理≤12文件）+反模式 |

---

## 二、项目流程（docs/project-flow/）

> 项目架构和模块的详细技术文档，按需加载。

### 快速入口

| 文档 | 核心内容 |
|------|----------|
| [project-flow/quick-reference.md](./project-flow/quick-reference.md) | 命令/文件/版本锁定速查 |
| [project-flow/task-navigation.md](./project-flow/task-navigation.md) | 14个任务导航表（按任务类型索引代码锚点） |
| [project-flow/build-apk-guide.md](./project-flow/build-apk-guide.md) | APK打包全流程：环境搭建+签名+构建+包名修改 |
| [project-flow/INDEX.md](./project-flow/INDEX.md) | 关键词索引（A-Z） |

### 架构文档

| 文档 | 核心内容 |
|------|----------|
| [project-flow/architecture/rule-engine.md](./project-flow/architecture/rule-engine.md) | SourceRule状态机+五种解析+JS环境+WebJs模式+变量系统+ruleType常量 |
| [project-flow/architecture/rule-engine-algorithms.md](./project-flow/architecture/rule-engine-algorithms.md) | SourceRule完整规范+RuleAnalyzer完整算法+五种解析器算法细节+Mode枚举 |
| [project-flow/architecture/rule-engine-js-env.md](./project-flow/architecture/rule-engine-js-env.md) | AnalyzeRule/AnalyzeUrl环境绑定+ajax跨域请求+Rhino编译缓存+共享作用域+@put/@get变量机制 |
| [project-flow/architecture/skill-architecture.md](./project-flow/architecture/skill-architecture.md) | Skill架构：金字塔架构+5阶段工作流+JVM仿真器+basic-memory经验引擎+固化脚本+审计者 |
| [project-flow/architecture/multi-agent-analysis-spec.md](./project-flow/architecture/multi-agent-analysis-spec.md) | 五阶段流水线+单代理≤12文件+并行+交叉验证+导航同步 |
| [project-flow/architecture/overview.md](./project-flow/architecture/overview.md) | 项目架构总览 |
| [project-flow/architecture/android-ui.md](./project-flow/architecture/android-ui.md) | MainActivity导航+ReadBookActivity三层继承+RSS UI+Activity体系+Fragment+Widget+Theme |
| [project-flow/architecture/api-dataflow.md](./project-flow/architecture/api-dataflow.md) | HTTP/WebSocket/Beacon完整链路+API对照表 |
| [project-flow/architecture/app-init.md](./project-flow/architecture/app-init.md) | 50步启动流程+常量系统+EventBus+异常体系+监控 |
| [project-flow/architecture/base-layer.md](./project-flow/architecture/base-layer.md) | BaseActivity/VMBaseActivity/BaseViewModel/BaseService/RecyclerAdapter/Diff+动画 |
| [project-flow/architecture/frontend.md](./project-flow/architecture/frontend.md) | Vue3 MPA架构+config/types等9模块+路由+组件树+技术栈 |
| [project-flow/architecture/frontend-components.md](./project-flow/architecture/frontend-components.md) | Vue3 Web重构方案—组件与页面：路由设计+页面组件+通用组件 |
| [project-flow/architecture/frontend-stores.md](./project-flow/architecture/frontend-stores.md) | Vue3 Web重构方案—Store与API层：TypeScript类型定义+Pinia Store+API调用层 |
| [project-flow/architecture/network-layer.md](./project-flow/architecture/network-layer.md) | OkHttp拦截器链+SSL全信任+Cookie双层+Cronet加速+代理 |

### 模块文档

| 文档 | 核心内容 |
|------|----------|
| [project-flow/modules/webbook-search.md](./project-flow/modules/webbook-search.md) | WebBook双版本+并发搜索调度+四分类聚合去重+发现/详情/目录/正文全链路 |
| [project-flow/modules/content-pipeline.md](./project-flow/modules/content-pipeline.md) | ContentProcessor七步管线+替换规则引擎+分段/简繁/样式适配 |
| [project-flow/modules/reading-engine.md](./project-flow/modules/reading-engine.md) | ReadBook状态机+三章缓存+预下载+翻页跳章+漫画+音频 |
| [project-flow/modules/reading-engine-pagination.md](./project-flow/modules/reading-engine-pagination.md) | durChapterPos字符偏移分页机制+TextChapter数据结构+页面计算算法+6种翻页动画 |
| [project-flow/modules/reading-engine-media.md](./project-flow/modules/reading-engine-media.md) | ReadManga漫画阅读+AudioPlay音频播放+BookType位标志 |
| [project-flow/modules/data-layer.md](./project-flow/modules/data-layer.md) | 21实体+21DAO+1视图+BookChapter复合主键+AutoMigration+位标志+TypeConverter |
| [project-flow/modules/web-service.md](./project-flow/modules/web-service.md) | NanoHTTPD路由+14POST+12GET+4控制器+WebSocket+静态服务 |
| [project-flow/modules/local-book.md](./project-flow/modules/local-book.md) | TXT编码检测+目录规则自动选+EPUB懒加载+PDF/MOBI |
| [project-flow/modules/service-layer.md](./project-flow/modules/service-layer.md) | WebDAV同步+下载缓存+TTS朗读+RSS子系统+JS扩展函数 |
| [project-flow/modules/config-system.md](./project-flow/modules/config-system.md) | AppConfig/ReadBookConfig/ThemeConfig/SourceConfig/LocalConfig |
| [project-flow/modules/android-services.md](./project-flow/modules/android-services.md) | 11个Service+WebSocketServer+ExoPlayer+朗读状态机+音频焦点+WakeLock+通知 |
| [project-flow/modules/backup-restore.md](./project-flow/modules/backup-restore.md) | 21数据源JSON导出+AES加密+WebDAV同步+Mutex并发 |
| [project-flow/modules/remote-third-party.md](./project-flow/modules/remote-third-party.md) | RemoteBook/WebDAV浏览+Glide/GSYVideo/ExoPlayer+更新系统 |
| [project-flow/modules/js-extensions.md](./project-flow/modules/js-extensions.md) | 30+ JS可调用方法：ajax/connect/webView/cache/file/encode/python |
| [project-flow/modules/source-management.md](./project-flow/modules/source-management.md) | 导入/导出/校验/调试/登录/18+过滤/排序全链路 |
| [project-flow/modules/model-layer.md](./project-flow/modules/model-layer.md) | ReadAloud/VideoPlay/BookCover/CheckSource/Debug/RuleUpdate/SharedJsScope |
| [project-flow/modules/rss-subsystem.md](./project-flow/modules/rss-subsystem.md) | Rss调度+RssParserByRule规则解析+RssParserDefault标准解析+文章流UI |
| [project-flow/modules/tools-infrastructure.md](./project-flow/modules/tools-infrastructure.md) | utils工具类+协程封装+加密+广播接收器 |
| [project-flow/modules/custom-libraries.md](./project-flow/modules/custom-libraries.md) | MOBI解析引擎+WebDAV客户端+主题引擎+阿里云TTS |

### 数据库文档

| 文档 | 核心内容 |
|------|----------|
| [project-flow/database/overview.md](./project-flow/database/overview.md) | 数据库架构总览 |
| [project-flow/database/entities.md](./project-flow/database/entities.md) | 实体详细定义 |
| [project-flow/database/tables.md](./project-flow/database/tables.md) | 数据库v89全部21张表完整DDL+索引定义+约束说明 |

---

## 三、功能设计（docs/specs/）

> 功能设计文档，按 OpenSpec 工作流程管理。

### 活跃 Specs

| 文档 | 说明 |
|------|------|
| [specs/INDEX.md](./specs/INDEX.md) | 项目状态面板+功能状态 |
| [specs/TEMPLATE.md](./specs/TEMPLATE.md) | 功能设计文档模板 |
| [specs/android-ui-optimization/](./specs/android-ui-optimization/) | Android UI/UX 优化（P0 Bug+Design Token+暗色模式+现代化） ✅ 实施完成 |
| [specs/sigma-sync-202607/](./specs/sigma-sync-202607/) | 同步阅读Sigma 2026-07最新提交（2 bug修复+订阅源+默认值） ✅ 已完成 |
| [specs/builtin-themes/](./specs/builtin-themes/) | 新增8个内置主题（5日间+3夜间，WCAG AA） ✅ 已完成 |
| [specs/legado-skill-optimization/](./specs/legado-skill-optimization/) | Legado Skill 优化 |
| [specs/legado-skill-v2-rebuild/](./specs/legado-skill-v2-rebuild/) | Legado Skill V2 重建 |
| [specs/skill-core-capability-rebuild/](./specs/skill-core-capability-rebuild/) | Skill 核心能力重建 |
| [specs/skill-usability-optimization/](./specs/skill-usability-optimization/) | Skill 可用性优化 |
| [specs/source-repair-loop-optimization/](./specs/source-repair-loop-optimization/) | 源修复循环优化 |
| [specs/jvm-webview-and-test-fix/](./specs/jvm-webview-and-test-fix/) | JVM WebView 与测试修复 |
| [specs/legado-core-optimization/](./specs/legado-core-optimization/) | Legado 核心质量优化（内存泄漏+线程安全+ANR+错误处理+测试） ✅ Batch1+2完成 |
| [specs/dependency-upgrade-optimization/](./specs/dependency-upgrade-optimization/) | 依赖升级性能优化+minSdk迁移（Coroutines 9.8x+Lifecycle 2.11+Core 1.19+7组AndroidX升级+OkHttp 5.4+WebView修复） ✅ 实施完成 |
| [specs/legado-skill-unified-redesign/](./specs/legado-skill-unified-redesign/) | Legado Skill 统一重设计 |
| [specs/network-perf-stability/](./specs/network-perf-stability/) | 网络组件性能与稳定性深度优化（OkHttp/Cronet/协程/缓存/图片解密，P0稳定+P1性能+P2架构） ✅ 实施完成（P0+P1），待真机验证 |
| [specs/e2e-automated-testing/](./specs/e2e-automated-testing/) | APK 端到端自动化测试验证系统（MEmu+uiautomator2+AI 日志分析，一键打包→装包→跑用例→出报告） 🔄 设计中 |
| [specs/e2e-ui-executor-hardening/](./specs/e2e-ui-executor-hardening/) | E2E UI 执行器加固（scroll_find 滚动查找/自愈重构/失败跳过/dismiss_dialogs 误判修复/规则分析器 uiautomator2 崩溃排除/证据收集路径修复/测试用例对齐 Compose UI） ✅ 实施完成，单用例 pass_rate=100% |
| [specs/apk-size-optimization/](./specs/apk-size-optimization/) | APK 体积审核与精简优化（v3：debug APK解压分析+打包技术手段全量评估，已用所有稳定优化，零功能影响预估-2.5~3.5MB，附折中选项） 🔄 设计中 |
| [specs/folder-view-welcome-refactor/](./specs/folder-view-welcome-refactor/) | 书源/订阅源文件夹视图重构 + 欢迎页增强 + 前端样式审计 ✅ 实施完成，待真机验证 |
| [specs/video-m3u8-cache/](./specs/video-m3u8-cache/) | 视频播放器 m3u8 边下边播缓存（cachePlay 配置 + 设置开关，默认开启） ✅ 已实施，待真机验证 |
| [specs/rss-cache-first/](./specs/rss-cache-first/) | RSS 阅读源缓存优先加载（列表页 DiffUtil 增量更新 + WebView cacheFirst 默认 true） ✅ 已实施，待真机验证 |
| [specs/video-mute-highspeed/](./specs/video-mute-highspeed/) | 视频播放器默认静音 + 高倍速支持（3X/5X/10X/15X + 播放界面静音按钮） ✅ 已实施，待真机验证 |
| [specs/source-layout-redesign/](./specs/source-layout-redesign/) | 书源/订阅源布局设置重做（修复书源分组 bug + 视图模式扩展5种 + 订阅源排序 + 类型筛选 + 统一配置对话框） 🔄 设计中 |
| [specs/yesterday-changes-deep-audit/](./specs/yesterday-changes-deep-audit/) | 昨日改动（2026-07-08）深度自我审查（书源订阅源布局+视频播放器，6 Agent 并行审查发现 29 项 bug + 7 阻塞点 + 1 需求偏差） ✅ 审查完成 |
| [specs/context-compression-feedback-preservation/](./specs/context-compression-feedback-preservation/) | 上下文压缩用户反馈保全 + 主线任务完成质量三层审查 + 打包功能差距三层修复（Part A 反馈持久化+四件套 + Part B B0openspec偏差/B1代码/B2交付 + Part C C1偏差归属/C2 F1-F10核查/C3 E2E+L2） ✅ 已完成（D1偏差已修正，7类细节不符需新建spec） |
| [specs/source-layout-detail-refinement/](./specs/source-layout-detail-refinement/) | 书源/订阅源布局细节精修（D1标签+分组两模式 / D2按类型分组修复+返回键 / D3订阅源二级页还原列表 / D4搜索框 / D5视频缓存下拉选择 / D6倍速15x保留） ✅ 实施完成待文档同步 |
| [specs/rss-video-player-enhancement/](./specs/rss-video-player-enhancement/) | 订阅源视频播放器增强（R1多集选择播放 + R2 m3u8播放失败调试日志 + R3学习旧订阅源布局 + R4日志异常优化 + R5自动抓取视频链接+Header修复404） 🔄 实施完成待用户实测（7.1/7.2/7.5/7.6 + 3.17 Bug修复 L2通过；7.3/7.4/7.7/7.8 需真实视频站点验证） |
| [specs/douyin-style-video-player/](./specs/douyin-style-video-player/) | 抖音风格沉浸式竖屏视频播放器重设计（ViewPager2+Fragment架构 / 三种状态PURE/NORMAL/FULLSCREEN / 左下角标题+线路+集数 / 右侧快退/静音/收藏/倍速/设置/快进 / 横屏全屏+双指缩放 / 控件默认显示+双指左右滑动隐藏 / 综合设置面板BottomSheet） 🔄 实施完成待L2真机验证 |
| [specs/video-article-swipe-switch/](./specs/video-article-swipe-switch/) | 视频播放器上下滑动切换文章（ViewPager2+Fragment+文章列表模式+分页加载+预缓冲+位置记忆） ✅ 实施完成（阶段1-8全部代码完成+L2验证通过） |
| [specs/video-control-visibility-enhancement/](./specs/video-control-visibility-enhancement/) | 视频播放器控件显隐与缓冲条优化（F1缓冲进度条修复+secondaryProgress绑定 / F2控件3秒自动隐藏+单击切换+触摸事件根因修复OnTouchListener设到surface_container） ✅ 实施完成（L2真机验证通过） |
| [specs/video-ui-dedup-layout-adjust/](./specs/video-ui-dedup-layout-adjust/) | 视频播放器 UI 去重与布局调整（移除右侧静音/倍速按钮避免与GSY底部控件重叠 + 左下角标题区和全屏按钮上移32dp避免遮挡GSY底部播放条 + VideoFragment.kt死代码清理） ✅ 实施完成（Phase 1-4全部完成+L2验证通过） |
| [specs/video-playback-issues-round1/](./specs/video-playback-issues-round1/) | 视频播放问题修复第1轮（10类问题：ExoPlayer失败降级WebView用skill V2模板 + 播放器类型配置 + ViewPager2兼容性 + 加密解密容错 + ClassCastException容错 + SQLiteBlobTooBig容错 + WebView线程安全 + 网络重试 + JSON容错 + HlsPlaylistStuck + Cronet回退） ✅ 实施完成（L2真机验证通过，5.6 ViewPager2滑动切换核心修复 onInterceptTouchEvent 方案） |
| [specs/spec-system-optimization/](./specs/spec-system-optimization/) | 规范体系优化（三层规范结构：全局通用规范→项目主规范→项目子规范，AGENTS.md核心步骤+索引格式，全局规范整合去重，压缩恢复强制加载项目主规范，违禁词三道防线，子规范强制加载机制） ✅ 已完成（检查点3最终验收通过 2026-07-13） |
### 归档 Specs

| 文档 | 说明 |
|------|------|
| [specs/archive/skill-improvement/](./specs/archive/skill-improvement/) | Skill 改进设计文档 |
| [specs/archive/skill-architecture-optimization/](./specs/archive/skill-architecture-optimization/) | Skill 架构优化设计 ✅ 已完成 |
| [specs/archive/skill-html-fetch-enhancement/](./specs/archive/skill-html-fetch-enhancement/) | Skill HTML 获取能力增强 ✅ 已完成 |
| [specs/archive/test-infra-upgrade/](./specs/archive/test-infra-upgrade/) | 测试基础设施升级 ⚠️ 代码实现完成，测试验证缺失 |
| [specs/archive/skill-trio-optimization/](./specs/archive/skill-trio-optimization/) | Skill 三件套优化 🔄 进行中 |
| [specs/archive/skill-deep-optimization-v2/](./specs/archive/skill-deep-optimization-v2/) | Skill 深度优化 V2 ✅ 已完成 |

---

## 四、核心 Skill（.trae/skills/legado-source-creator/）

> 项目核心工具：Legado 书源/订阅源智能创建器。79 条陷阱检查、5 阶段闭环工作流、10 大参考目录、16 个验证脚本。

### 核心文档

| 文档 | 核心内容 |
|------|----------|
| [SKILL.md](../.trae/skills/legado-source-creator/SKILL.md) | 主文档：规则引擎完整知识+79条陷阱检查清单+5阶段闭环工作流 |
| [AI_README.md](../.trae/skills/legado-source-creator/AI_README.md) | AI使用指南：快速开始+脚本使用+工作流程+经验反哺规范 |

### 参考文档索引（10 大目录）

| 目录 | 子文档数 | 核心内容 |
|------|----------|----------|
| [references/](../.trae/skills/legado-source-creator/references/_INDEX.md) | 4 核心文档 | 规则语法+URL模板+实体字段+示例源 |
| [references/troubleshooting/](../.trae/skills/legado-source-creator/references/troubleshooting/_index.md) | 6 子文档 | 常见陷阱与故障排除 |
| [references/js-extensions/](../.trae/skills/legado-source-creator/references/js-extensions/_index.md) | 11 子文档 | JS扩展函数完整参考 |
| [references/js-patterns/](../.trae/skills/legado-source-creator/references/js-patterns/_index.md) | 11 子文档 | JS模式参考手册 |
| [references/special-scenarios/](../.trae/skills/legado-source-creator/references/special-scenarios/_index.md) | 13 子文档 | 登录/验证码/加密/视频等特殊场景 |
| [references/source-analysis/](../.trae/skills/legado-source-creator/references/source-analysis/_index.md) | 6 子文档 | 源码分析验证结果 |
| [references/site-features/](../.trae/skills/legado-source-creator/references/site-features/_INDEX.md) | 5 子文档 | 站点特征与规则类型映射 |
| [references/rule-construction-guide/](../.trae/skills/legado-source-creator/references/rule-construction-guide/_index.md) | 3 子文档 | 规则构建指南 |
| [references/known-fix-patterns/](../.trae/skills/legado-source-creator/references/known-fix-patterns/_index.md) | 8 子文档 | 已知修复模式 |
| [references/cms-samples/](../.trae/skills/legado-source-creator/references/cms-samples/_INDEX.md) | 2 子文档 | CMS模板样本 |

### 工具：JVM 规则引擎仿真器

| 工具 | 用途 |
|------|------|
| `tools/legado-jvm/build/libs/legado-jvm.jar` | JVM 仿真器（统一JAR，Rhino+jsoup+hutool+AnalyzeRule） |
| `scripts/legado_client/client/rule_engine_client.py` | Python 客户端（调用 JVM 仿真器） |
| [references/source-analysis/ajax-diff-analysis.md](../.trae/skills/legado-source-creator/references/source-analysis/ajax-diff-analysis.md) | ajax 差异分析文档 |

### 验证脚本

| 脚本 | 用途 |
|------|------|
| `scripts/quick-verify.py` | 浅层可用性验证（网站存活+HTTP） |
| `scripts/verify-source.py` | 深度链路验证（规则引擎模拟解析） |
| `scripts/debug-source.py` | 端到端真机级调试 |
| `scripts/generate-js-doc.py` | 提取JS模式生成文档 |
| `scripts/deep-analyze-js.py` | 深度JS分析（变量传递链/加密模式） |

### 固化脚本

| 脚本 | 用途 |
|------|------|
| `scripts/verify-decrypt.py` | AES/DES 解密验证 |
| `scripts/verify-selector.py` | CSS 选择器验证 |
| `scripts/verify-image.py` | 图片加密验证 |
| `scripts/analyze_site.py` | 网站结构分析 |
| `scripts/verify-source.py` | 源完整性验证 |
| `scripts/diagnose-failures.py` | 失败诊断 |
| `scripts/run-full-regression.py` | 全量回归 |
| `scripts/quick-test-sources.py` | 快速批量测试 |

### 辅助脚本

| 脚本 | 用途 |
|------|------|
| `scripts/html_fetcher.py` | HTML获取回退链 |
| `scripts/diagnose-failures.py` | 失败诊断 |
| `scripts/run-full-regression.py` | 全量回归 |

### 模板文件

| 文件 | 用途 |
|------|------|
| `templates/auto-video-player.html` | 自动视频播放器模板 |
| `templates/hls-video-player.html` | HLS视频播放器模板 |
| `templates/inject-video-player.js` | 注入式视频播放器JS |

---

## 五、工作流审计者 Skill（.trae/skills/legado-workflow-auditor/）

> 书源/订阅源创建或优化任务完成后的强制审计工具，确保 Phase 完成标志、basic-memory 执行证据、自测交付流程的合规性。

| 文档 | 核心内容 |
|------|----------|
| [SKILL.md](../.trae/skills/legado-workflow-auditor/SKILL.md) | 审计规则+检查清单+审计报告模板 |
