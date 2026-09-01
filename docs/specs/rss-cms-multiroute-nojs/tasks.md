# tasks.md — rss-cms-multiroute-nojs

> 功能：视频订阅源多线路多集零JS解析增强 + CMS采集书源转化（MacCMS 免JS多线路多集）
> 测试包：`io.legado.miss.app.debug`（代码开发阶段用测试包，禁止混用正式包，铁证规范 package-naming.md）
> 验证要求：必须用 `ai_tests\venv\Scripts\python.exe`；测试前必读 `ai_tests/docs/fixed_test_workflow.md`
> 关联文档：[spec.md](./spec.md) ｜ [design.md](./design.md) ｜ [rss-subsystem.md](../../project-flow/modules/rss-subsystem.md)
> 说明：任务完成即勾选 `- [x]`；实施中遇到问题在文末 `## AOAdapt 日志` 按 Action/Observation/Adapt 补记（24H 制）。

## 1. 准备工作

- [x] 1.1 ✅ 重新核实 `Rss.kt` / `AnalyzeRule.kt` 现状（实测行号与文档一致后按当次读取修改）
- [x] 1.2 ✅ 目标站 API 验证：`class` 数组存在（基础接口）、`vod_play_from`/`vod_play_url` 格式与设计一致、m3u8 直链可达；发现 lziapi 站对应用请求返回拦截页（2530B），切换非凡站
- [x] 1.3 ✅ 真实分类：ffzy class 数组 32 项（含父级），父分类无数据（81B 空响应），sortUrl 采用 26 个子分类枚举
- [x] 1.4 ✅ 确认 venv 解释器与固化脚本（import_rss_source.py），真机流程按 SOP 驱动

## 2. 解析层增强（Rss.kt）

- [x] 2.1 ✅ v3 全量落地：①`normalizeMacCmsBody`（增量注入顶层 routes、零侵入判定、routes 已存在跳过）接入 2 处 setContent；②ruleRoutes getStringList 优先+flatMap 展开+回落（L179-184）；③parseEpisodesResult 加 routeIndex 参数+隐式分组兜底（越界回落首组记 WARN）；④parseEpisodesByLines CMS 段解析（# 分集/$ limit=2 拆名址/缺名"第N集"/旧格式兼容）
- [x] 2.2 ✅ 边界自查（静态推演+真机实证）：routeIndex 边界、单线路、CMS 段特殊字符（limit=2 保留地址内 $）、旧格式回归、routes 已存在跳过、`$.routes[*].name` 列表规则、`$.routes[0].episodes`、回落写法兼容；发现并修复 ruleRoutes 列表结果需 flatMap 按 \n 展开兼容旧 replaceRegex 转行产物
- [x] 2.3 ✅ updateLog.md 基于 git diff 更新（新增 3 条+修复 3 条，编译前完成）

## 3. 订阅源转化

- [x] 3.1 ✅ 订阅源 JSON 生成（docs/specs/rss-cms-multiroute-nojs/source-liangzi.json）：非凡站、type=2、全部列表范式规则、ruleContent 留空、sortUrl 26 子分类静态枚举（`{{page}}` 双括号）
- [x] 3.2 ✅ 导入验证：DB 直写链路（run-as 管道+md5 双向校验闭环）落库成功；字段完整性核实（NOT NULL 列补全 singleUrl/articleStyle 等）

## 4. 编译验证

- [x] 4.1 ✅ Get-Process 校验（识别 IDE 语言服务器 java 进程 vs 构建进程，保留前者）
- [x] 4.2 ✅ build-legado.bat 构建成功（legado_miss_app_3.26.090111.apk，libcronet.so 打包校验 OK，daemon 自动清场）；期间处理并行会话编译冲突（transforms 缓存损坏×3 清理、App.kt 缺 import 最小补齐）
- [x] 4.3 ✅ adb install 成功，L1 启动正常（pm clear 后重走隐私协议/引导）

## 5. 真机 L2 验证

- [x] 5.1 ✅ 分类 Tab 干净无 `&` 残留（split 修复生效）、列表条目正常（毒战行动/狂暴对峙等）、标题/封面解析正常
- [x] 5.2 ✅ 点开影片：多线路下拉显示 feifan/ffm3u8 两条（ruleRoutes 列表范式 `$.routes[*].name` 生效）+ 第一线路集数列表（`$.routes[0].episodes` 生效，logcat "多线路采集完成 routeCount=2 firstRouteEpisodes=14/1"）
- [x] 5.3 ✅ 切换线路：播放器线路下拉切换后集数刷新正常（getEpisodesAwait 链路+routeIndex 占位符），超界兜底（解析层 getOrNull 回落首组）
- [x] 5.4 ✅ 播放验证实锤：切 ffm3u8 线路点第 1 集 → logcat `ExoPlayer play success (STATE_READY): urlPath=/20260826/57486_9a7c0ca4/index.m3u8, fallbackIndex=0/2` + startRenderers 持续渲染（诊断过程发现并修复 Map.toString URL 污染，见 AOAdapt 11:50）
- [x] 5.5 ✅ 搜索接口验证（wd 参数 200/178KB）；RssSearchActivity 复用同一规则引擎
- [x] 5.6 ⚠️ 回归：旧格式分支（多行URL/JSON数组）代码未动+解析层单函数增强，静态保证；预置 4 源为网页型（type=0）无旧格式视频源可实机回归——遗留至后续真实旧格式源复测
- [x] 5.7 ✅ `{{$.vod_id}}` 大括号模板生效实锤：logcat sourceDebug 显示列表解析 link=`...ids=98758/98850/99013/99151` 各不相同（修复前恒为空 ids）

## 6. 收尾

- [x] 6.1 ✅ 真机问题记录（见 AOAdapt：lziapi 拦截页/DB 直写时序/SourceRule inner class 绑定）
- [x] 6.2 ✅ 文档同步：rss-subsystem.md / INDEX.md / design.md（§2.5+实施差异）/ updateLog
- [x] 6.3 ✅ 临时日志清理：RssLinkDebug/SwipeTest 调试日志移除，Grep 确认 0 残留；探测脚本保留于 ai_tests/scripts/（固化复用）
- [x] 6.4 ✅ 经验沉淀到 ai_memory_main.md（su -c 参数引号陷阱/DB 直写时序铁律/transform 缓存并行冲突/SourceRule inner class 绑定语义）
- [ ] 6.5 （可选，另行确认）其余 12 个资源站批量转化

## AOAdapt 日志

> 实施中遇到问题时按以下格式补记（Action=做了什么 / Observation=观察到什么 / Adapt=如何调整），时间 24H 制：

- [2026-09-01 08:10] 目标站（量子站）对应用请求返回 2530B 拦截页（本机/模拟器 curl 均 200/305KB），列表解析出 1 条无 vod_id 的异常项
  - Action: 抓 logcat 分析 bodyLen=2530 异常；本机/模拟器双环境 curl 排除 UA/网络因素
  - Observation: 应用网络栈（Cronet+DoH 选 IP）命中 CDN 拦截节点，curl 直连正常
  - Adapt: 切换非凡站（ffzyapi）重测，验证通过；量子站留待用户真机复测或配 header
- [2026-09-01 08:30] 订阅源 DB 导入"成功"但应用读不到，多次反复
  - Action: 排查 import_rss_source.py 的 su cp 链路，逐条命令加输出校验
  - Observation: ①`su -c` 多段命令在 Windows adb 参数拼接下引号丢失（`stat -c %U` 的第二个 -c 被 su 误解析为用户名）；②运行中的应用 push DB 会被 WAL 回滚覆盖；③覆盖安装后 uid 变化使硬编码 chown 破坏权限；④`adb shell` 管道拉二进制有 CRLF 污染致 malformed
  - Adapt: 新建 import_rss_runas.py——run-as 管道（debug 包免 root）+ exec-out 二进制安全拉取 + force-stop 前置 + 动态 uid + md5 双向校验闭环；沉淀为固定脚本
- [2026-09-01 10:55] `{{$.vod_id}}` 大括号模板替换为空（link=`...ids=`），所有影片打开同一详情
  - Action: 加 RssLinkDebug 临时日志实证 item 类型与子规则上下文
  - Observation: item 为 LinkedHashMap 且含 vod_id=99062，但 makeUpRule 子规则 getString 的 content 是**创建 SourceRule 的外层实例**的 content（整个列表响应，顶层无 vod_id）——SourceRule 是 inner class 绑定创建实例，ruleLink 在外层实例拆分导致子规则上下文错位
  - Adapt: makeUpRule 子规则调用改为 `getString(ruleList, result)` 显式传入当前解析上下文（列表项）；重编译后 logcat 实证 ids=98758/98850/99013/99151 各不相同，修复生效
- [2026-09-01 12:41] 用户 goal 反馈"列表只有1条数据、视频地址错误"——模拟器复现实锤：应用请求 ffzy 仅 2226B（本机/模拟器 curl 均 305KB），且 UA 限流同样影响数据量（文章数=1）
  - Action: 源 header 配浏览器 UA + Referer 重导入
  - Observation: `RSS自定义规则解析完成 文章数=20 总数=20`、bodyLen=41095，UI 列表 13+ 条可见；切 ffm3u8 → `ExoPlayer play success (STATE_READY)` 播放闭环
  - Adapt: ①header 方案写入订阅源 JSON ②陷阱 60-64（多线路多集写法/UA 限流/父分类/{{page}}/ids 参数）沉淀至 skill video-source-traps.md 并更新 _index ③"视频地址错误"的另一根因（Map.toString 污染）已于 11:45 修复
- [2026-09-01 09:00] 并行编译冲突：transforms 缓存反复损坏（3 次）+ Gradle daemon 被外部 stop
  - Action: 清理 transforms 缓存目录后重试；与并行会话错峰构建
  - Observation: build-legado.bat 的清理环节与另一会话构建进程并发时互相踩踏
  - Adapt: 用户协调后单会话构建；教训：多会话并行开发期禁止同时触发构建
- [2026-09-01 11:45] 用户真机反馈"视频无法播放且线路没用"，播放 404（ERROR_CODE_IO_BAD_HTTP_STATUS）
  - Action: 源站 URL 三级验证（master/子清单/分片均 200 排除源问题）→ R5 嗅探日志发现集数 url 值=`https:` → 加 routesJson 临时日志实证
  - Observation: 集数 url 被 `{title=第1集, url=https://...}` Map.toString 污染——`AnalyzeByJSonPath.getString` 对 JSON 数组的**对象元素**执行 `joinToString("\n")` 产生非法 Map 字符串，parseEpisodesResult 收到后无法走 JSON 分支，整行 Map 串被当相对 URL 拼上 origin
  - Adapt: AnalyzeByJSonPath getString/getStringList 修复——字符串元素保持 joinToString 旧语义，Map/对象元素序列化为合法 JSON（org.json）；重编译后切 ffm3u8 线路点播 → `ExoPlayer play success (STATE_READY)` m3u8 直链实锤；此修复对书源同类对象数组规则同样受益
