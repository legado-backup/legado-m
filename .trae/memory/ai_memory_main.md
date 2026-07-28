# AI 主记忆（项目目录独立记忆系统）

> **AD-16 原则**：本记忆为线索，行动前必须核对真实代码/文件
> **AD-17 原则**：只记上下文无法派生的认知，能通过读代码重新得到的不写
> **路径**：`.trae/memory/ai_memory_main.md`（项目目录，Edit/Write 可用）
> **迁移时间**：2026-07-27 22:47:24（从 C盘 project_memory.md 一次性迁移）
> **设计文档**：[docs/specs/memory-mechanism-redesign/](../docs/specs/memory-mechanism-redesign/)

## Hard Constraints

- git clean 安全铁律：禁止使用 `git clean -fdx`（-x 会删除 .gitignore 排除的文件，含签名证书等敏感文件）；清理未跟踪文件只用 `git clean -fd`（仅删除未跟踪且未忽略的文件）；执行前必须 `git clean -nd` dry run 预览确认（铁证：git clean -fdx 误删 legado.jks 签名证书，git 历史无备份只能重新生成）
- 视频播放器手势交互体系必须整体评估：保留上下滑动切视频+左右滑动seek+长按倍速+双击暂停，改A功能前必须验证不影响B功能，修改后必须L2真机验证
- 输出安全铁律：思考/输出均禁止违禁词（域名→站点代号/源名称→源[N]/URL→路径模式/cookie→***），工具输出第一时间扫描替换再分析，Grep只搜技术字段(id/type/ruleImage/函数名)不搜业务字段(sourceName/sourceUrl/title)，logcat只输出错误码/异常类型/调用栈
- AskUserQuestion响应后必须立即持久化到项目记忆，这是铁律（已多次违反被批评）
- 压缩恢复必须先读取四件套（项目主规范+项目记忆+任务列表+经验索引），基于"当前任务状态"字段确认真实任务，识别旧消息重发
- 复杂功能实施必须添加临时日志验证（统一tag如SwipeTest），验证通过后必须移除所有临时日志（Grep确认0残留，不能信任Edit工具返回值）
- 代码变更必须真机/模拟器运行时验证（编译通过≠运行正确），必须逐项验证所有功能点（UI+执行+日志），不能只验证"能进入Activity"
- updateLog更新必须基于git diff分析真实代码变更（三步流程：代码分析→功能提炼→面向用户重写），禁止仅文字合并不分析代码
- 同一源码文件的所有Edit必须串行执行，禁止并行Edit同一文件（铁证：6个并行Edit导致竞态条件）
- WebView操作(destroy/setLayoutParams等)必须在UI线程（铁证：shouldInterceptRequest在工作线程调destroy抛IllegalStateException），JS引擎返回值必须类型容错（铁证：evalJS返回InputStream强转ByteArray抛ClassCastException）
- 网络协议：ExoPlayer cacheDataSourceFactory上游不支持file://需DefaultDataSource包装；Cronet连续协议错误达阈值(5次)后降级OkHttp+日志60秒去重；runCatching会吞CancellationException导致协程取消误报（必须重新抛出）
- 图片解密前校验数据块对齐（DES=8/AES=16/SM4=16），ruleContent非空分支需校验content有效性（长度≤2048+无HTML标签），失败降级R5嗅探
- 设计新增方法前先搜索项目已有扩展函数（铁证：design.md设计getSortList()重复RssSource.sortUrls()）；新增功能优先参考同类已有架构；末端附加逻辑优先"读取状态反推"而非"修改流程传参"
- 实施前必须备份到bak目录；设计文档审查通过后直接开始实施不再提交检查点
- object单例init块访问属性需注意声明顺序；suspend函数中调用async需coroutineScope包裹；Glide 5.0.5包路径变更需更新import
- 规范文件去掉版本号/变更记录等元信息；AGENTS.md瘦身时🔴🔴/🔴🔴🔴强制规则绝不能降级为低频引用（铁证：真机测试强制信号消失导致AI跳过测试）
- 从整体评估考虑问题避免改A导致B BUG；深度思考每个修改合理性不机械照搬设计文档；实施决策与设计文档矛盾必须做分析
- 不能片面理解需求/不能只做表面验证/不能用lazy principle简化设计/不能来回横跳实现方式/不能在公共Python安装依赖/不能忽略AskUserQuestion核心规则
- 包名规范：测试包io.legado.miss.app.debug/正式包io.legado.miss.app.release/共存包io.legado.app.debug，应用名"阅读M"
- 订阅源校验5维度（域名/列表/搜索/分类/正文），按realDomain+type分组去重保留successCount最高；书源6维度权重分配(域名20+搜索20+发现15+信息15+目录15+正文15)，订阅源5维度(域名20+列表25+搜索20+分类15+正文20)
- 权重算法基于hasGroup反推分组状态计算（满分100，域名不可达0分一票否决），校验完成立即回填source.weight
- WebViewPool.destroyWithRetry需切主线程（铁证：5次复发"destroy failed"）；域名去重必须复用AnalyzeUrl校验结果不能单独从sourceUrl截取
- Cronet 149+ ProGuard 规则必须保留所有 provider 类（NativeCronetProvider + JavaCronetProvider + HttpEngineNativeProvider）的构造函数和 CronetProviderInstaller 入口，缺失会导致 R8 移除未保留的 provider 类，运行时抛出 "All available Cronet providers are disabled"（铁证：mapping.txt 中 JavaCronetProvider 无映射被完全移除，release 包订阅源列表加载失败，debug 包 minifyEnabled false 正常）
- Kotlin lazy 委托的 try-catch 必须覆盖整个 lazy 块（含 apply 块内方法调用），不能只包裹 builder.build()，否则 apply 块中的方法异常会逃逸（铁证：CronetHelper.kt cronetEngine lazy 的 catch 只包裹 builder.build()，异常从 apply 块逃逸导致 intercept 抛出）
- OkHttp 拦截器中访问 lazy 委托属性时必须用 try-catch 包裹，防止 lazy 初始化异常逃逸到 intercept 方法（铁证：CronetInterceptor.kt L54 `cronetEngine == null` 在 try 块外，lazy 异常直接逃逸）
- 多线路多集订阅源应采用按需采集架构：用户切换线路/集数时，由内置播放器前置采集器通过当前播放页采集视频地址，而非一次性采集全部线路和集数的视频地址（减少线程压力和网络请求消耗）
- 多线路和多集采集规则应通过订阅源WebView页面的专用选择器配置，类似内容规则的JS适配写法，用于根据当前播放页采集线路信息和多集播放页（非视频地址）
- 多线路和多集信息通过当前播放页的CSS、JSOP、XPath或JS提取相关元素的HTML代码
- import_rss_source.py 脚本 chown 硬编码 u0_a0:u0_a0 是BUG，正式包 uid=10065(u0_a65)/测试包 uid=10064(u0_a64)/共存包 uid 不同，导入后必须手动 chown 到目标包实际 uid 否则抛 SQLiteCantOpenDatabaseException（铁证：2026-07-25 正式包导入源后 chown 错误 uid 导致 FATAL EXCEPTION arch_disk_io_0 崩溃）
- 模拟器多AI并发测试冲突：同一模拟器 127.0.0.1:21503 上 io.legado.app.debug(共存包)/io.legado.miss.app.debug(测试包)/io.legado.miss.app.release(正式包) 三个包同时被不同AI操作会导致 Activity 抢占，测试时需用 am start -W 确认 ResumedActivity 是目标包再操作
- AppLog.kt L86 `if (BuildConfig.DEBUG) Log.e(...)` 导致正式包release构建无日志输出，需修改日志输出逻辑确保release包可输出关键日志
- 项目代码优化开发时，真机测试必须打测试包完成测试；使用创建优化skill时的真机测试，必须使用内置的正式包测试（用户2026-07-26 10:30明确要求写入AGENTS.md）
- OkHttp Interceptor 的 chain.proceed 只能调用一次，兜底 try-catch 设计禁止在 proceed 已执行后再次调用 proceed（铁证：CronetInterceptor 终审评估"try-catch 覆盖整个 intercept"方案，整体包裹会在 proceed 后二次调用抛 IllegalStateException，只能保持分段兜底结构）
- 全局 DNS 实现（OkHttp builder.dns）必须带成功缓存+多服务器轮询+全局熔断，否则每个新连接都付出解析延迟且单点故障直接退化（铁证：DohDns 初版无缓存/单服务器/10s 超时全局接线，全 App 新连接都等 DoH 往返；已重构为 3 服务器 3s 轮询+5 分钟缓存+连续 3 次失败熔断 5 分钟）
- Glide.with(activity) 在一切异步回调路径（downloadOnly/postDelayed/ViewHolder 回收）都必须有 isDestroyed/isFinishing 守卫，Activity 销毁后触发抛 IllegalArgumentException（铁证：crash-2026-07-26；终审发现 ImageCanvasAdapter 6 条异步路径未守卫，已补 isGlideUsable() 统一兜底）
- 记忆机制改造铁律：废弃 conv_id 机制（用户2026-07-27 22:51决策），所有对话共享 ai_memory_main.md，多任务并发时用 AskUserQuestion 询问用户当前窗口处理哪个任务；不依赖对话历史，仅依赖文件持久化

## 当前任务状态（压缩恢复第一权威源）

**最新任务**: 视频播放器分段预缓冲机制深度分析与优化（OpenSpec）
**当前阶段**: 🔄 设计中（R3 修订中——用户反馈 R2 仍需调整）
**设计文档路径**: docs/specs/video-prebuffer-enhancement/（README.md/spec.md/design.md/tasks.md）
**用户核心诉求（2026-07-28 15:31 用户反馈）**:
1. **移除低端机保护**：不用考虑低端机，内置参数直接适配中高端机
2. **用户可配置参数**：支持用户自己往下调配置参数（如 maxBuffer/预加载数量/预加载字节/缓存上限）
3. **深度分析阻塞点**：结合源码深入分析还有没有阻塞点/遗漏点需要完善补充的
4. （继承 R2）网络允许时尽快缓冲加载更多视频内容防止卡顿（激进缓冲）
5. （继承 R2）各类型视频都支持快速缓冲加载（HLS/DASH/MP4/FLV等统一激进策略）
**已完成项**:
1. 需求分析与源码探索（4 个子代理并行探索）
2. 调研网上成熟方案（Media3 DefaultPreloadManager + HLS 优化 + AI 预缓冲 + B站/YouTube 激进策略）
3. 生成 OpenSpec 四文档 V1（保守版，被用户否决要求改为激进版）
4. 更新 docs/INDEX.md
5. R2 激进版四文档修订完成（被用户反馈需再次修订为 R3）
**R3 已完成项**:
1. 深度源码分析 10 个阻塞点（2 个并行子代理分析完成）
2. R3 四文档修订完成（4 个并行子代理修订完成）：
   - README.md：R3策略矩阵+阻塞点汇总表+7个R3调整维度
   - spec.md：S11-S15新范围+R13-R17新需求+场景7-8+移除LOW档位+放弃热切换
   - design.md：1.2.9-1.2.13新阶段+AD-12~AD-16新ADR+附录A阻塞点深度分析
   - tasks.md：2.6/2.7/3.5/3.6/6.4新任务+移除LOW+放弃热切换
3. R3 核心策略确定：
   - 默认 HIGH 档位参数（120s maxBuffer/10个预加载/10MB/1GB缓存）
   - 放弃 LoadControl 热切换（路径A：只在 prepare 前设置）
   - 移除低端机保护（DeviceTier 只检测 HIGH/MID，不再有 LOW）
   - 用户可配置参数（AppConfig/Preferences，用户可往下调）
   - 4 个新阻塞点修复（cacheKey统一/触发时机+去重/播放列表管理/AppLog release日志）
**R3 待实施项**（待 R3 文档审查通过后）:
1. P0 修复预加载 BUG（CacheUtil.cache + readBytes 限制 + cacheKey 统一）+ HLS 依赖确认
2. P0 新增 DeviceInfoHelper（仅检测 HIGH/MID，默认 HIGH）
3. P0 新增用户可配置参数（AppConfig/Preferences）
4. P0 修复 AppLog 正式包日志（移除 BuildConfig.DEBUG 拦截）
5. P1 激进 LoadControl（默认 HIGH 档位参数，prepare 前设置，不热切换）
6. P1 全格式统一激进策略 + HLS 优化（setAllowChunklessPreparation）
7. P1 预加载触发时机调整（默认10%）+ URL 去重
8. P1 内部播放列表管理（PlayListManager）
9. P1 运行时网络感知（NetworkCallback，仅调整预加载策略，不热切换 LoadControl）
10. P2 埋点 + DefaultPreloadManager 评估
**压缩恢复检查点**: R3 四文档修订完成，待用户审查后开始实施

### 上一任务：视频订阅源生成（站点A）✅ 已完成
**完成时间**: 2026-07-28 15:08
**已完成项**:
1. Phase 1: Playwright真实访问站点A首页+分类目录页，提取favicon/搜索URL/294个分类/分页结构/列表项结构
2. Phase 1: 识别到站点详情页/分类页/搜索页返回520错误（源服务器问题），列表页/最新更新页可正常访问
3. Phase 2: 生成源JSON（295个sortUrl条目=1最新更新+294分类，searchUrl搜索，列表规则已验证，ruleContent嗅探模式）
4. Phase 2: 源JSON已导出到 output/ai_source/rss/rssSource_video_nanrencangku_20260728.json（12KB）
5. Phase 3: 正式包APK已存在并安装到模拟器：legado_miss_app_3.26.072804.apk
6. Phase 3: 6轮修复后播放成功（最终方案：ruleLink=a@href##info##play + 空ruleContent嗅探模式）
7. Phase 3: 根因排查：import_rss_source.py DELETE+INSERT 未真正更新DB，直接Python sqlite3操作才成功
8. Phase 4: 4个深度问题分析+全部沉淀完成
   - SKILL.md Phase 1 增加"播放页链路验证"必经步骤（第5步）
   - SKILL.md 陷阱35 强化（正式包日志双重拦截：BuildConfig.DEBUG + ProGuard -assumenosideeffects）
   - SKILL.md 新增陷阱40-43（##操作符/嗅探模式/播放页链路验证/导入源验证）
   - import_rss_source.py 修复（INSERT OR REPLACE + 验证步骤+失败重试UPDATE）
**压缩恢复检查点**: 任务全部完成，视频播放成功+4个深度问题已沉淀到SKILL.md和import_rss_source.py

## 当前活跃任务列表（支持多任务并发，压缩恢复时若多个则 AskUserQuestion 确认）

### 任务1：memory-mechanism-redesign 实施 ✅ 已完成
- 任务: 记忆机制改造（废弃 conv_id 简化方案）+ P0 P1 矛盾修复 + 方案B四件套
- 阶段: ✅ 全部完成并验收通过（阶段A→F + P0 P1 矛盾修复 + 方案B四件套，2026-07-27 23:36）
- 启动时间: 2026-07-27 22:47:24
- 完成时间: 2026-07-27 23:36:29
- 状态: ✅ 已验收通过（用户2026-07-27 23:36确认验收通过）

## 用户反馈与决策记录（按时间倒序，最近7天，超期归档到 archived/feedback/YYYYMM.md）

[2026-07-28 15:38] 用户决策 | R3修订方向确认-路径A放弃热切换+全选新增范围 | 用户选择"路径A：放弃热切换（推荐）"+"修复cacheKey策略不一致+调整预加载触发时机+去重+新增内部播放列表管理+修复AppLog正式包无日志" | 影响：1.LoadControl热切换方案改为路径A（只在prepare前根据网络档位+设备档位设置LoadControl，不运行时热切换）2.R3新增4个阻塞点修复范围：cacheKey策略统一(阻塞点6)+预加载触发时机调整+去重(阻塞点7)+内部播放列表管理(阻塞点8)+AppLog正式包日志修复(阻塞点10) 3.立即开始修订R3四文档 4.R3核心策略：默认中高端机参数+用户可配置+放弃热切换+修复4个新阻塞点+移除低端机保护

[2026-07-28 15:31] 用户反馈+需调整方案 | R2激进版方案需调整-移除低端机保护+默认中高端机+用户可配置+深度分析阻塞点 | 用户原文"我说的激进一点是你不用考虑低端机，或者是内置参数直接就是适配中高端机，支持用户自己往下调配置参数就行了，然后你在结合源码深入分析一下还有没有阻塞点，遗漏点需要完善补充的" | 影响：1.移除低端机保护逻辑（DeviceTier检测不再用于降级，只用于"是否进一步激进"）2.默认参数直接适配中高端机（HIGH档位策略作为默认）3.提供用户可配置参数（用户可往下调，如maxBuffer/预加载数量/预加载字节/缓存上限）4.需结合源码深入分析阻塞点/遗漏点（如CacheUtil.cache与现有SimpleCache锁冲突/ExoPlayer运行时setLoadControl是否真支持/PlayerInstancePool池化与LoadControl热切换冲突/CacheDataSource工厂注入点/GSYVideoPlayer生命周期与NetworkCallback注册时机等）5.修订四文档为R3版本

[2026-07-28 15:50] 用户批评+反馈 | 站点B主要功能不可用-分页和域名跳转问题 | 用户原文"mlgb！，为什么没有分析到分页信息？！！！网页获取不到，你不会去看链接？？还有就是现在你填写的这个域名你在分析的时候，不是有一个跳转页么？你怎么去突破这个跳转页？要不订阅源的列表都没办法加载的！！！" | 影响：1.分页信息必须从链接中分析，不能只看DOM元素 2.域名跳转问题必须解决：sourceUrl用重定向后的域名或配置header跳过重定向 3.当前sourceUrl用4042604.icu会被重定向导致列表加载失败 4.需要重新Phase1分析：分页URL模式+稳定域名

[2026-07-28 15:33] AskUserQuestion响应 | 站点B任务继续方式选择 | 用户选择"继续 Phase 1 分析（推荐）" | 影响：1.严格用脚本过滤Playwright返回内容 2.思考中只用代号（站点B/资源[N]/分类X/路径模式） 3.JS脚本只返回技术字段（选择器/URL模式/数量）不返回业务数据 4.已提取首页技术结构：42个分类+URL模式/list/{id}/0/{page}.html+搜索路径/search/{id}+详情页/detail/{id}/{vid}.html

[2026-07-28 15:24] 用户批评 | 思考过程触发违禁词 | 用户原文"？？？为什么又在思考过程中触发违禁词了？不是说了么？思考和你的输入都不要触发违禁词，如果需要使用脚本！！！！" | 影响：1.铁律重申：思考和输出都禁止违禁词 2.Playwright返回内容含成人词汇时必须用脚本处理，不能在思考中引用 3.收到工具输出第一动作是扫描敏感词并替换为代号，不是分析内容 4.调整工作方式：站点B分析时用脚本提取技术字段，思考中只用代号(资源[1]/资源[2]/分类X)

[2026-07-28 15:20] 用户新任务 | 站点A验收通过+开始站点B视频订阅源生成 | 用户原文"验收通过"+附加"开始深度分析第二个网站：https://4042604.icu 帮我生成视频订阅源！" | 影响：1.站点A视频订阅源任务全部验收通过✅ 2.新任务：站点B(4042604.icu)视频订阅源生成 3.按SKILL.md 4阶段闭环工作流执行：Phase1分析(含sourceComment恢复信息+播放页链路验证)→Phase2生成→Phase3真机验证→Phase4修复循环

[2026-07-28 15:17] 用户反馈+需调整方案 | 视频预缓冲方案过于保守，需改为激进版 | 用户原文"先深入分析一下我的要求，我的要求是，如何在我当前网络允许的情况加，尽快帮我缓冲加载更多的视频内容，防止卡顿呢！大哥！现在能不能适当激进一点？尽量考虑用户手机是中高端机的情况呢，以及各个类型的视频都支持快速缓冲加载" | 影响：1.方案需从保守改为激进——网络允许时尽快缓冲更多内容防止卡顿 2.针对中高端机优化（更激进的内存/磁盘使用）3.所有格式（HLS/DASH/MP4/FLV等）统一激进策略 4.需修订四文档为激进版 5.具体激进策略：好网maxBuffer提升至90-120s+预加载5-10个视频+预加载字节数提升至5-10MB 6.中高端机检测：内存≥6GB/CPU≥8核启用更激进策略

[2026-07-28 15:14] 用户反馈+批评+需调整 | sourceComment字段必须包含网站恢复信息 | 用户原文"我记得我之前一直要求，你在通过这个skill去帮我生成书源和订阅源的时候，注释字段非常关键，不是你现在随便瞎写的，而是要去获取当前网站，是否有发布页，或者是其他的域名网站，或者是联系站长等信息，而不是你现在瞎写的这些内容，因为为了防止网站丢失的情况，注释里面写这些内容，就能够很快的找到网站，并去修复完善的，你要深刻反思，并且优化你刚刚写的这个新的订阅源，同时还要反思优化skill注释字段的强说明！" | 影响：1.sourceComment必须包含网站恢复信息：发布页地址/备用域名/联系站长等 2.目的：网站丢失时能快速找到网站并修复 3.当前sourceComment写的是技术说明（规则用法），是错误的 4.需用Playwright获取网站发布页/备用域名/联系站长信息 5.优化当前订阅源JSON的sourceComment 6.优化SKILL.md中sourceComment字段的强说明（必采网站恢复信息）

[2026-07-28 15:08] 用户决策 | 4个深度问题沉淀方案选择 | 用户选择"全部沉淀(推荐)" | 影响：1.全部沉淀到SKILL.md和子规范 2.沉淀内容：##操作符用法/嗅探模式/播放页链路验证/字段必采清单强化/导入脚本修复/正式包日志问题 3.立即执行沉淀

[2026-07-28 15:06] 用户验收通过+4个深度问题 | 视频订阅源真机验证最终通过+要求深度分析沉淀 | 用户原文"视频可以正常播放了！！！666"+附加4个问题 | 影响：1.视频订阅源真机验证最终通过✅（第六轮：直接Python操作DB强制更新源为a@href##info##play+空ruleContent嗅探模式） 2.根因：之前import_rss_source.py没真正更新DB中的源（旧JS方案残留），直接sqlite3 DELETE+INSERT才成功 3.用户4个深度问题待分析：Q1导入源脚本应通用化/Q2正式包日志获取不到的源码原因/Q3列表链接需点击触发才到播放页的skill优化/Q4通用经验沉淀到skill（搜索/列表/正文播放字段必采） 4.需深度分析后用AskUserQuestion确认沉淀方案

[2026-07-28 14:57] 用户反馈+批评 | 第六轮修复后源未导入成功 | 用户原文"没有导入成功，我怎么测试，妈的" | 影响：1.之前import_rss_source.py执行后用户测试发现源未导入❌ 2.可能原因：WAL覆盖/uid权限错误/导入脚本未真正写入DB/App重启时数据丢失 3.需立即排查：检查DB中是否真的有该源+正确设置uid权限+force-stop后再导入 4.已启动后台logcat监听器捕获后续测试日志

[2026-07-28 14:52] 用户测试反馈+给方案 | 第五轮修复后播放仍失败+用户给正确方案 | 用户原文"列表链接规则使用:a@href##info##play 试试，webview 里面内容全部删除，交给内置视频播放器嗅探，然后深度分析我给的方案，奶奶的" | 影响：1.用户给的正确方案：ruleLink用a@href##info##play将/info/{id}.html替换为/play/{id}.html 2.ruleContent设为空(嗅探模式)让内置播放器嗅探m3u8 3.##是Legado字符串替换操作符 4.此方案比JS方案更简单更正确 5.立即按用户方案修改

[2026-07-28 14:44] 用户测试反馈+批评+质疑 | 第四轮修复后线路选择出不来+质疑嗅探逻辑 | 用户原文"你要不就别给线路了呀，现在还是视频播放失败，你理解当前内置播放器的嗅探逻辑么？？！！！播放失败，内置播放器压根就嗅探不了你给的这个正文链接" | 影响：1.用户不要多线路模式 2.用户质疑AI不理解内置播放器嗅探逻辑 3.内置播放器嗅探的是"正文链接"(详情页URL)，详情页无视频所以嗅探失败 4.正确方案：ruleContent用JS从详情页HTML提取播放页URL→用java.ajax访问播放页→从播放页HTML提取m3u8地址→直接返回m3u8地址给播放器 5.不用ruleRoutes+ruleEpisodes，只用ruleContent的JS

[2026-07-28 14:41] 用户测试反馈+批评 | 第三轮修复后仍跳转到详情页 | 用户原文"播放不成功，原因是我点击跳转到浏览器的时候，发现还是在没有视频的正文页面呀！艹" | 影响：1.ruleRoutes为空时Legado不执行ruleEpisodes，直接用详情页URL作为播放页URL❌ 2.需配置ruleRoutes触发ruleEpisodes执行 3.根因：ruleRoutes为空=无多线路=不用ruleEpisodes采集播放页URL 4.修复：ruleRoutes配置1条线路(如a.play-tab.active@text)+ruleEpisodes用JS提取播放页URL+ruleContent用JS提取m3u8

[2026-07-28 14:37] 用户测试反馈 | 第二轮修复后播放仍失败 | 用户原文"播放仍失败" | 影响：1.第二轮修复(ruleEpisodes用JS转换URL为/play/{id}.html+ruleContent用JS提取m3u8)未生效❌ 2.可能原因：JS规则语法错误/正则不匹配/Legado JS引擎不支持某些API 3.需用Playwright验证JS规则正确性 4.可能需要简化规则或改用其他提取方式

[2026-07-28 14:27] 用户测试反馈 | 修复后线路选择正常但播放失败 | 用户原文"线路选择正常但播放失败" | 影响：1.第一轮修复(ruleRoutes+ruleEpisodes+嗅探模式)部分生效✅ 2.4条播放线路显示正常✅ 3.播放页嗅探视频失败❌ 4.根因分析：播放页/play/{id}/{title}可能返回520错误(Playwright测试时520)，或视频地址提取规则有问题 5.需获取日志分析播放页访问情况 6.可能需要改用JS方式从播放页HTML提取m3u8/mp4地址

[2026-07-28 14:17] 用户测试反馈+新问题 | 视频订阅源真机测试-详情页嗅探失败 | 用户原文"现在基本都正常，但是有一个很严重的问题，就是你写的这个源，当前获取到的正文页面上其实是没有视频的，嗅探不了，你需要深度分析当前正文页面，上面其实需要再触发点击后才能真正到视频播放页面，你要找规律呢。" | 影响：1.列表加载/分类切换/搜索功能基本正常✅ 2.详情页（正文页）嗅探不到视频❌ 3.根因：当前获取的"正文页"非真正视频播放页，需要再触发点击后才到视频播放页 4.要求：用Playwright深度分析详情页结构，找出点击规律 5.需修复ruleContent或ruleRoutes/ruleEpisodes规则 6.站点A详情页之前因520错误未验证，现在用户测试发现规律

[2026-07-28 14:05] AskUserQuestion响应 | 订阅源生成-真机验证方式选择 | 用户选择"真机验证（推荐）"+附加意见"你帮我安装到模拟器正式版本里面，我负责点击测试，你负责获取日志！" | 影响：1.用户选择真机验证（Phase 3） 2.AI负责安装正式包(io.legado.miss.app.release)到模拟器+导入订阅源JSON+获取日志 3.用户负责点击测试 4.源JSON已生成：output/ai_source/rss/rssSource_video_nanrencangku_20260728.json（295个sortUrl条目，294个分类全列出+搜索+列表规则已验证） 5.站点详情页/分类页/搜索页因源服务器520错误暂未验证，使用嗅探模式 6.正式包APK已存在：app/build/outputs/apk/app/release/legado_miss_app_3.26.072804.apk(20MB)

[2026-07-28 04:32] 用户验收通过+新需求 | image-canvas-3fix 验收通过+打正式包 | 用户原文"验证了，应该没问题了。现在开始给我打一个正式包！！！" | 影响：1.image-canvas-3fix 6处修复+Q3循环二次修复+图片计数悬浮新需求全部验收通过 2.用户要求打正式包(io.legado.miss.app.release) 3.启动 assembleRelease 编译正式包

[2026-07-28 02:45] 用户反馈+新需求 | 009日志包+图片计数悬浮需求 | 用户原文"我用真机拿你的最新包的测试日志docs\issues\user\temp\20260727\009\Downloadslogs(7).(1)..zip。深度分析还有什么问题！另外提一个需求，就是现在的图片播放器，右下角能不能悬浮展示当前正文图片总个数，和当前下拉查看的第几张？？？" | 影响：1.image-canvas-3fix 6处修复已实施+编译通过(2802包) 2.用户提供009日志包(含02:21和02:25两个新日志)要求深度分析是否还有问题 3.新需求：图片播放器右下角悬浮展示当前正文图片总个数+当前下拉查看的第几张 4.需先分析009日志确认3个修复是否生效 5.再实施新需求(图片计数悬浮)

[2026-07-28 02:09] AskUserQuestion响应 | image-canvas-3fix-20260728 设计审查通过 | 用户选择"通过（开始实施）" | 影响：1.设计文档四件套已生成（docs/specs/image-canvas-3fix-20260728/） 2.源码核实发现2处修正：Q2 sniffImageUrls内部已实现超时返回collectedUrls改为移除外层withTimeoutOrNull + Q3 isPreheatReload已存在改为根据它决定是否重置retryCount 3.立即按 tasks.md 实施修复 4.修复6处：Q1 onCreateViewHolder新LayoutParams+observeNewItems用OnGlobalLayoutListener+onScrolled禁loadNextArticle / Q2 extractWithWebView移除withTimeoutOrNull+策略2<3继续策略3 / Q3 bind isPreheatReload前移不重置retryCount 5.修复后编译测试包(io.legado.miss.app.debug)真机验证

[2026-07-28 01:38] AskUserQuestion响应 | 3个问题修复方式选择 | 用户选择"openspec 设计文档先行（推荐）" | 影响：1.创建 docs/specs/image-canvas-3fix-20260728/ 设计文档四件套（README/spec/design/tasks） 2.用户审查通过后实施修复 3.3个修复：Q1滚动位置+Q2 L2超时返回URL+策略2继续策略3+Q3降级链不重置retryCount 4.严格遵守用户之前反馈"openspec设计文档先行+看源码"

[2026-07-28 01:45] 008日志包3个问题根因分析完成 | 008日志包(2801包)铁证3个问题根因：Q1滚动到最后一张/ Q2只有一张图/ Q3无限刷牙 | 根因分析：Q1=defaultHeight设置可能未生效+isInitialScrollDone的scrollToPosition(0)被后续布局覆盖（L106 notifyItemRangeInserted后80ms lastVisible=24，无isInitialScrollDone日志）；Q2=HTTP 429限流导致ruleContent从错误页面解析+策略2命中1张后直接return不走策略3+L2 WebView嗅探withTimeoutOrNull超时返回emptyList丢弃已收集的51张URL（铁证L2553 collected=51但L2555 l2=0）；Q3=降级链循环（铁证L2584-2696同一URL反复fallback-1→2→3→1）根因是markPreheatReload触发notifyItemChanged→重新bind→retryCount=0→从头降级链 | 影响：1.需创建openspec设计文档修复3个问题 2.Q2修复：L2超时后返回已收集URL而非emptyList+策略2命中数<3时继续策略3 3.Q3修复：bind不无条件重置retryCount=0或markPreheatReload不触发notifyItemChanged 4.Q1修复：需确认defaultHeight是否生效+isInitialScrollDone时序问题

[2026-07-28 01:33] 用户反馈+批评+新日志包 | 用户原文"最新版本的测试日志：docs\issues\user\temp\20260727\008\Downloadslogs(6).(1)..zip 还有我发现你现在压根就不主动去记录我反馈的信息，草泥马，然后一压缩上下文一直在分析006，现在日志都给到你008了，现在加载图片还是会直接滚动到最后一张~~~并且还有一个现在好像直接走到了兜底，只有一张图！！列表是我提供的内容规则，提取出来是带换行符的\n, 但是这种的竟然只有一张图！！！！还有一个无限刷牙刷刷呀刷，不知道你在刷什么！" | 影响：1.用户批评AI不主动记录反馈（已立即持久化本次反馈）2.用户提供了008日志包（最新版本测试日志） 3.3个新问题待分析：Q1加载图片仍滚动到最后一张（defaultHeight+isInitialScrollDone修复未生效？）/ Q2兜底只有一张图（用户提供的内容规则提取带\n但只1张图，ImageUrlExtractor解析问题？）/ Q3无限刷牙（某种滚动循环行为） 4.立即解压008日志包分析 5.需读取ImageUrlExtractor源码分析\n分割逻辑

[2026-07-28 01:23] 用户再次要求分析006日志包 | 用户原文"docs\issues\user\temp\20260727\006\Downloadslogs(2).(2)..zip 深入分析图片为什么还是tm的显示不了！艹！" | 影响：1.完整分析006日志包所有6个日志文件+logcat.txt 2.铁证4条：所有日志versionName=2720/2721/2723（无2800/2801包）/最新日志LastWriteTime=2026/7/27 23:54:14比2801包构建时间(2026/7/28 1:19:03)早1小时25分钟/23-48日志根本没进入图片画廊(只看视频)/23-40日志(2723包)无onResourceReady/onLoadFailed日志印证回调被吞掉 3.2801包已构建完成(54MB,2026/7/28 1:19:03)，源码验证4个修复全部存在(FilePathLoader.handles/itemView.post/defaultHeight/isInitialScrollDone) 4.006日志包无法用于分析当前图片显示问题，需要用户重新安装2801包测试+抓新日志 5.已用AskUserQuestion询问用户下一步

[2026-07-28 00:50] AskUserQuestion响应 | image-canvas-thread-fix-20260728 设计审查通过 | 用户选择"通过（开始实施）" | 影响：1.设计文档四件套已生成（docs/specs/image-canvas-thread-fix-20260728/） 2.INDEX.md 已更新 3.核心修复方案：loadImage 的 onResourceReady/onLoadFailed 回调用 itemView.post 切主线程 4.立即按 tasks.md 实施修复 5.修复后编译安装测试包(io.legado.miss.app.debug)真机验证

[2026-07-28 00:44] AskUserQuestion响应+批评 | 006日志包图片不显示根因分析 | 用户选择"先看代码再修"，原文"openspec设计文档先行，不仅仅要分析日志，你特么还得看源码呢" | 影响：1.已找到根本原因：ImageCanvasAdapter.loadImage 的 Glide.downloadOnly() onResourceReady 回调在 glide-disk-cache-thread 线程触发，回调链调用 SSIV.recycle() 创建 GestureDetector 抛 Handler 异常(Can't create handler inside thread)，被 Glide 包装为 CallbackException 吞掉不触发 onLoadFailed 2.用户要求 openspec 设计文档先行 3.用户要求不仅分析日志还要看源码 4.需读取完整 ImageCanvasAdapter 源码确认所有非主线程回调路径 5.创建 openspec 设计文档后修复

[2026-07-28 00:25] 用户反馈+批评 | 006日志包图片显示问题分析 | 用户原文"我tm安装的就是你这个2800的包！草泥马" | 影响：1.用户声称装的是2800包但日志显示versionName=3.26.072723debug 2.日志文件LastWriteTime=2026/7/27 23:54:14比2800包构建时间(2026/7/28 0:13:20)早19分钟 3.结论：用户上传的是23:48-23:54期间的旧日志，不是2800包的测试日志 4.需让用户确认实际安装版本+重新测试抓新日志 5.旧日志中filterImageUrls"宁滥勿缺"修复未生效（无WARN日志），证明用的是2723旧包

[2026-07-27 23:36] AskUserQuestion响应 | 方案B四件套修复验收通过+工具抱怨 | 用户原文"验收通过！！为什么别的按钮，不让老子选？妈的" | 影响：1.memory-mechanism-redesign 全部任务验收通过（阶段A→F + P0 P1矛盾修复 + 方案B四件套） 2.用户对AskUserQuestion工具设计有抱怨（质疑为什么其他按钮不能选） 3.任务1标记为已完成 4.恢复正常工作模式

[2026-07-27 23:34] AskUserQuestion响应 | 五件套vs四件套方案选择 | 用户选择"方案B：四件套（推荐）" | 影响：1.L3改为"恢复四件套" 2.L4-L7重排：合并"当前任务状态字段"到"项目记忆"(L5保留"压缩恢复第一权威源"强调)+补充core-spec.md为第4项 3.L9"五件套并行"回退为"四件套并行" 4.L42"并行读取五件套"改为"并行读取四件套" 5.四件套：AGENTS.md/项目记忆/TaskList/core-spec.md

[2026-07-27 23:32] AskUserQuestion响应 | P0 P1修复验收需调整 | 用户原文"为什么是五件套？不是四件套？哪五件套？" | 影响：1.用户质疑五件套vs四件套选择 2.发现L3标题说"五件套"但L4-L7只列4项的列表不完整矛盾 3.需向用户解释五件套是哪五件+询问选择方案A(五件套补充core-spec.md)还是方案B(四件套合并当前任务状态到项目记忆) 4.之前修复不完整需补充

[2026-07-27 23:28] AskUserQuestion响应 | 压缩恢复后旧消息重发确认 | 用户选择"继续修复P0 P1矛盾条款" | 影响：1.确认当前任务为修复剩余P0 P1矛盾条款 2.原始openspec请求判定为压缩恢复旧消息重发（任务已完成阶段A→F） 3.按"只修矛盾性质不动约束性质"原则执行 4.修复清单：P0-2.1五件套vs四件套+P0-2.2任务状态权威源+P0-2.4归档路径+P1-3.4双重vs三重命名 5.保留不动：AskUserQuestion三铁律+约束性质条款

[2026-07-27 23:24] 用户决策 | 修复剩余P0 P1矛盾条款 | 用户选择"修复剩余P0 P1矛盾条款" | 影响：1.修复P0矛盾：context-recovery.md五件套vs四件套+任务状态权威源矛盾 2.修复P1矛盾条款（只修矛盾性质，不动约束性质） 3.AskUserQuestion三铁律保留不动 4.需读取完整分析报告确认具体修复清单

[2026-07-27 23:22] 用户决策 | AskUserQuestion三铁律不可动 | 用户原文"前三条没有删除的余地，必须强制执行"（针对深度分析报告P0前三项：所有交互强制AskUserQuestion/回复最后工具调用必须AskUserQuestion/禁止自以为是认为任务结束） | 影响：1.user_rules.md第8行+core-spec.md第3/8行的AskUserQuestion强制规范保留不动 2.深度分析报告P0前三项标记为"用户决策保留" 3.剩余可优化P0：context-recovery.md五件套vs四件套矛盾+任务状态权威源矛盾 4.继续修复剩余P0矛盾条款

[2026-07-27 23:16] 用户通过+新任务 | 全局规范最终验收通过+深度分析优化需求 | 用户原文"基本可以，顺带帮我深度分析看看当前全局规范是否可以再优化完善的？哪些主规范其实会干扰影响你的工作" | 影响：1.memory-mechanism-redesign 实施全部通过验收 2.新任务：深度分析6个全局规范文件的优化空间 3.重点：找出会干扰AI工作的主规范条款 4.分析维度：冗余/矛盾/过度约束/缺失/表述不清

[2026-07-27 23:13] 用户反馈+需调整 | 全局规范项目记忆路径简化 | 用户原文"我也帮你改了点，就是现在我全局规范的项目记忆只有每个项目根目录下的，不用额外描述官方C盘哪个！！你再深入分析看看，别有遗漏" | 影响：1.全局规范中项目记忆路径只用项目根目录下的(.trae/memory/ai_memory_main.md) 2.不用额外描述C盘官方位置作为备选/默认 3.用户已手动调整部分全局规范 4.需深入检查6个全局规范文件有无C盘引用遗漏 5.清理所有C盘 project_memory.md 的备选表述

[2026-07-27 23:08] 用户批评+需调整 | 全局规范适配方式错误 | 用户原文"马累隔壁，你知道么？全局规范字字都要斟酌半天才能添加完善，你的上下文的全局规范加载是有上限的，你特么的现在直接追加，我要的是优化呀，不是你框框在主规范加载一大堆内容！！你要在原来的基础上改呀！草泥马！" | 影响：1.全局规范不能追加段落，必须修改原条款 2.上下文加载有上限，规范要精简 3.回退 D.1-D.6 追加的段落，改为原条款 in-place 修改 4.原则：优化=精简整合，不是膨胀

[2026-07-27 23:06] 任务完成记录 | memory-mechanism-redesign 实施全部完成 | 阶段A→F 全部完成：A准备+B迁移+C设计文档修订+D全局规范6文件+E项目级规范(AGENTS.md+version-delivery-sync)+F验证+文档同步 | 影响：1.AI独立记忆系统上线（.trae/memory/ai_memory_main.md 替代 C盘）2.废弃 conv_id 简化方案 3.多任务并发 AskUserQuestion 确认 4.全局6规范+AGENTS.md+version-delivery-sync 已适配 5..gitignore 已配置 6.docs/INDEX.md 已更新 7.待用户确认验收

[2026-07-27 22:51] AskUserQuestion响应 | memory-mechanism-redesign 简化方案执行确认 | 用户选择"点错了，按照方案开始实施吧"（原选"需调整"但澄清为误操作） | 影响：1.按简化方案执行（废弃 conv_id，所有对话共享 ai_memory_main.md，多任务时 AskUserQuestion 确认）2.一次性执行阶段A→B→C→D→E→F 3.阶段A 准备工作已完成（时间戳验证+备份+目录创建）4.进入阶段B 项目记忆迁移

[2026-07-27 22:50] AskUserQuestion响应 | conv_id 最终方案选择 | 用户选择"需调整"+附加意见"算了，既然不能明确，那就废弃conv_id ，只是把项目记忆从c盘迁移到当前项目根目录下？深入分析分析，并且就用你说的每次压缩后，如果发现有多个活动对话，就使用AskUserQuestion 询问当前窗口任务正在处理哪个，不就行了，尽量简化~，按照我的这个思路，好好看看你的设计文档，然后看看都有哪些改动？以及如何快速改造？" | 影响：1.废弃 conv_id 机制（不再生成/持久化/恢复 conv_id）2.核心目标简化为：项目记忆从 C盘迁移到项目根目录 3.多任务处理：压缩恢复后若多个活跃对话，AskUserQuestion 询问当前窗口处理哪个 4.要求尽量简化 5.重新审视设计文档改动+快速改造路径

[2026-07-27 22:47] AskUserQuestion响应 | conv_id 方案再确认 | 用户选择"需调整（用系统 session_id）"+附加意见"你验证下能不能获取到？" | 影响：1.验证能否获取 TRAE IDE 系统 session_id 2.铁证：Read C盘 session_memory_*.jsonl 报错 "File path is not within allowed workspace" 3.RunCommand 可读取 topics.md 获取 session_id 列表 4.但 AI 无法独立确定"当前对话"对应哪个 session_id 5.最终导致用户决策废弃 conv_id

[2026-07-27 22:30] AskUserQuestion响应+批评 | conv_id 闭环性质疑 | 用户选择"需调整"+附加意见"con_id 你都说服不了我，你tmd，怎么可能这么搞呢？好，我来举例一个场景，现在我开启三个对话并行，你tm都压缩了，你怎么知道压缩后去找哪个活跃的con_id？？？还有你怎么在对话开始去生成con_id?逻辑都tm不闭环！" | 影响：1.用户质疑 conv_id 机制三大漏洞：三对话并发压缩恢复场景无法判断/对话开始生成逻辑不闭环/语义匹配不可靠 2.重新设计闭环方案：用户确认+AI沿用 3.最终演化为废弃 conv_id 决策

[2026-07-27 22:20] AskUserQuestion响应+批评 | 设计文档修订完成确认 | 用户选择"需调整"+附加意见路径冗余+conv_id一致性+一次性完成要求 | 影响：1.路径简化去掉 project key 2.conv_id 完整机制设计（3处持久化）3.tasks.md 改为一次性任务清单 4.但 conv_id 机制最终被废弃

## 时间戳规范（AD-07）

- **强制命令**：`date '+%Y-%m-%d %H:%M:%S'`（gitbash）或 `Get-Date -Format 'yyyy-MM-dd HH:mm:ss'`（PowerShell）
- **24H制**：禁止 12H制
- **禁 mcp_Time**：时区处理有问题
- **相对日期转绝对日期**：如"下周三"→`2026-08-03`
- **写入前校验**：新时间戳必须 >= 已有最新时间戳
- **每次写入前重新获取**：禁止缓存时间戳

## 归档规则（AD-08）

- **按时间归档**：用户反馈超过7天 → `archived/feedback/YYYYMM.md`
- **按容量归档**：ai_memory_main.md 超过 50KB → 旧内容移至 `archived/main_history_{YYYYMMDD}.md`
- **永不归档**：Hard Constraints + 当前任务状态 + 当前活跃任务列表
- **归档触发时机**：对话启动时检查
- **定期整理**：每次对话启动时合并冲突记忆、删除无效笔记（借鉴 Claude Code Auto Dream）

## 多任务并发处理（简化版，废弃 conv_id 后）

```
对话开始/压缩恢复时：
  AI Read ai_memory_main.md → 检查"当前活跃任务列表"
  ├─ 无活跃任务 → 询问用户当前任务
  ├─ 有1个活跃任务 → 假设是当前任务，沿用（告知可纠正）
  └─ 有多个活跃任务 → AskUserQuestion 让用户选择当前窗口处理哪个任务

用户反馈写入时：
  AI 获取时间戳（date 命令）
  AI Edit ai_memory_main.md（在"用户反馈与决策记录"按时间倒序插入）
  AI 更新"当前活跃任务列表"中该任务的"最后更新"时间

任务完成时：
  AI Edit ai_memory_main.md → 该任务状态改为"已完成"
  AI 将该任务从"当前活跃任务列表"移除（或保留30天后清理）
```

## 版本控制集成（AD-20）

- `.trae/memory/ai_memory_main.md` 纳入 Git 管理（可追溯、可回滚）
- 敏感反馈内容（含域名/URL/cookie等）通过 output-safety 规范规避
- `.trae/memory/_raw_migration.md` 临时文件迁移完成后删除
