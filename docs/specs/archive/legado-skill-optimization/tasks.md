# Tasks: Legado Skill 整体优化方案

> **格式说明**：`- [ ] X.Y` 未完成 / `- [x] X.Y ✅ YYYY-MM-DD` 已完成
> **强制规则**：每个任务有源码行号引用 + 验证方法
> **统一 OpenSpec**：合并 JAR 仿真服务端 + Python 客户端 + Skill 工作流

---

## 方向 0：已完成修复（历史记录）

- [x] 0.1 icu4j 编码检测移植 ✅ 2026-06-21
- [x] 0.2 SSL/cookieJar/限流补全 ✅ 2026-06-21
- [x] 0.3 htmlFormat 实现 ✅ 2026-06-21
- [x] 0.4 繁简转换实现 ✅ 2026-06-21
- [x] 0.5 BaseSource.evalJS 补全 ✅ 2026-06-21
- [x] 0.6 getHeaderMap @js: 支持 ✅ 2026-06-21
- [x] 0.7 login 方法实现 ✅ 2026-06-21
- [x] 0.8 登录信息管理方法 ✅ 2026-06-21
- [x] 0.9 发现页调试实现 ✅ 2026-06-21
- [x] 0.10 setVariable/getVariable 签名修正 ✅ 2026-06-21
- [x] 0.11 OkHttpUtils.text() 编码检测 ✅ 2026-06-21
- [x] 0.12 nextChapterUrl/tocUrl/isWebFile/isVolume 修复 ✅ 2026-06-21

---

## 第一部分：JAR 仿真服务端修复

### 方向 1：低难度方法修复（12 个，P0）

> **源码依据**：`BaseSource.kt`（**源码核实修正：BaseSource 是 interface**）/ `JsExtensions.kt` / `JsEncodeUtils.kt`（**源码核实修正：aesEncodeToString 在此文件**）

#### 1.1 属性 val→var 签名修正（6 个）

> **源码核实修正**：真机 BaseSource.kt 中 6 个属性均为 `var`，仿真端 BaseSourceInterface.kt 当前为 `val`，需改为 `var` 并添加 setter

- [ ] 1.1.1 阅读 `BaseSource.kt` 确认 concurrentRate/loginUrl/loginUi/header/enabledCookieJar/jsLib 均为 var
- [ ] 1.1.2 修改 `BaseSourceInterface.kt`：6 个属性 val→var（**源码核实修正：真机是 var，仿真端 interface 需改为 var**）
- [ ] 1.1.3 验证：编译通过 + 签名与真机一致

#### 1.2 其他低难度修复（6 个）

- [ ] 1.2.1 dateFormat：读取 `LEGADO_DATE_FORMAT` 环境变量，默认 `"yyyy/MM/dd HH:mm"`（**源码核实修正：dateFormat 在 AppConst 不在 BaseSource**）
- [ ] 1.2.2 connect：catch 块中 url 改用 `analyzeUrl.url`
- [ ] 1.2.3 getTxtInFolder：添加 `folder.delete()`
- [ ] 1.2.4 importScript：`IllegalStateException` → `NoStackTraceException`
- [ ] 1.2.5 aesEncodeToString：反向引入真机 bug（**源码核实修正：在 JsEncodeUtils 不在 JsExtensions；疑似源码 Bug**）
- [ ] 1.2.6 验证：编译通过 + 行为与真机一致

### 方向 2：中难度方法修复（18 个，P0）

#### 2.1 base64/AES flags 映射完善（6 个）

- [ ] 2.1.1 阅读 `JsEncodeUtils.kt` 确认 android.util.Base64 flags 值
- [ ] 2.1.2 新建 `mapBase64Flags(flags)` 映射函数（**源码核实修正：mapBase64Flags 方法不存在，需新建**）
- [ ] 2.1.3 修改 base64Decode/base64DecodeToByteArray/base64Encode
- [ ] 2.1.4 修改 aesDecodeArgsBase64Str/tripleDESEncodeArgsBase64Str/tripleDESDecodeArgsBase64Str
- [ ] 2.1.5 修改 digestBase64Str/HMacBase64
- [ ] 2.1.6 验证：编解码结果与 android.util.Base64 一致

#### 2.2 其他中难度修复（7 个）

- [ ] 2.2.1 downloadFile：改用 OkHttp 流式下载 + 修正路径计算
- [ ] 2.2.2 toNumChapter：移植 AppPattern + StringUtils
- [ ] 2.2.3 log：接入 Debug 回调，写入日志文件
- [ ] 2.2.4 putConcurrent：实现 updateConcurrentRate（**源码核实修正：ConcurrentRecord 在 AnalyzeUrl 中**）
- [ ] 2.2.5 executeSortUrlJs：注入 source 变量
- [ ] 2.2.6 evalJS：实现 sharedScope（SharedJsScope）
- [ ] 2.2.7 验证：所有方法行为与真机一致

### 方向 3：高难度方法修复（8 个）

- [ ] 3.1 refreshJSLib：实现 SharedJsScope.remove
- [ ] 3.2 getLoginInfoMap：移植 RowUi 解析逻辑（**源码核实修正：在 BaseSource 不在 JsExtensions**）
- [ ] 3.3 getHeaderMap：读取 `LEGADO_USER_AGENT` 环境变量
- [ ] 3.4 debugExplore：实现 exploreInfoMapList 解析
- [ ] 3.5 验证：所有保留的方法行为与真机一致

### 方向 4：委托路径实现（21 个，P1）

#### 4.1 WebView 渲染委托（9 个）

- [ ] 4.1.1 WebViewRequiredException 携带完整请求信息
- [ ] 4.1.2 Python 端实现 `webview_delegate.py`（Selenium 执行 JS 渲染）
- [ ] 4.1.3 实现结果回传机制（HTTP API）
- [ ] 4.1.4 验证：需 WebView 渲染的源可调试

#### 4.2 UI 交互委托（5 个）

- [ ] 4.2.1 startBrowser → Selenium 浏览器自动化
- [ ] 4.2.2 startBrowserAwait → Selenium + 等待
- [ ] 4.2.3 getVerificationCode → OCR + 用户介入
- [ ] 4.2.4 openVideoPlayer/openUrl → 标记不影响验证
- [ ] 4.2.5 验证：需要登录的源可调试

#### 4.3 硬件信息环境变量配置（4 个）

- [ ] 4.3.1 LEGADO_ANDROID_ID 环境变量注入
- [ ] 4.3.2 LEGADO_WEBVIEW_UA 环境变量注入
- [ ] 4.3.3 getLoginInfo/putLoginInfo 依赖 androidId 修复
- [ ] 4.3.4 验证：AES 加密解密与真机一致

#### 4.4 Toast 日志文件替代（2 个）

- [ ] 4.4.1 toast/longToast → 写入日志文件
- [ ] 4.4.2 验证：日志文件正确记录

### 方向 5：仿真端已知问题修复（2 个，P0）

- [ ] 5.1 BT之家 PKIX 证书链修复（SSLHelper 信任所有证书）
- [~] 5.2 阳光电影 DNS 修复（OkHttp 公共 DNS 回退）（**部分实现：仅有 IPv4 优先，无公共 DNS 回退**）
- [ ] 5.3 验证：BT之家和阳光电影可访问

### 方向 6：失败源优化（58 个源，P0）

#### 6.1 RSS sortUrl 生成器 bug 修复（31 个源）

- [ ] 6.1.1 分析 31 个 RSS 源的 sortUrl 字段错误填充原因
- [ ] 6.1.2 修正生成器字段映射逻辑
- [ ] 6.1.3 重新生成 31 个 RSS 源
- [ ] 6.1.4 验证：31 个 RSS 源至少进入 articleList 阶段

#### 6.2 搜索规则重写（23 个源）

- [ ] 6.2.1 用浏览器 F12 检查 23 个 book 源搜索结果页 HTML
- [ ] 6.2.2 重写搜索规则选择器
- [ ] 6.2.3 验证：23 个 book 源搜索阶段通过

#### 6.3 bookList 类型错误修复（2 个源）

- [ ] 6.3.1 修复哔哩哔哩漫画 bookList 选择器
- [ ] 6.3.2 修复腾讯视频 bookList 选择器
- [ ] 6.3.3 验证：bookList 返回 List 类型

#### 6.4 URL 模板错误修复（2 个源）

- [ ] 6.4.1 修复番茄小说搜索 URL 变量语法
- [ ] 6.4.2 修复荔枝 FM 搜索 URL
- [ ] 6.4.3 验证：搜索 URL 变量正确替换

### 方向 8：OkHttpUtils 方法补全（3 个，P1）

- [ ] 8.1 补充 newCallResponseBody 扩展函数
- [ ] 8.2 补充 decompressed 扩展函数
- [ ] 8.3 补充 await 方法的 invokeOnCancellation 协程取消
- [ ] 8.4 验证：下载文件/zip 解压/协程取消正常

### 方向 9：RssSourceDebugger 逻辑修正（5 个，P0-P2）

- [x] 9.1 GAP-22 ruleDescription 逻辑修正（P0）：ruleDescription 有值时跳过内容页 ✅ 2026-06-21（RssSourceDebugger.kt 第82/310行已实现）
- [x] 9.2 GAP-23 key::url 调试入口 ✅ 2026-06-21（RssSourceDebugger.kt 第171-180行已实现 `::` 格式解析）
- [ ] 9.3 GAP-24 取消机制
- [ ] 9.4 GAP-25 校验模式
- [ ] 9.5 GAP-26 无参 key 入口
- [ ] 9.6 验证：RSS 源调试结果与真机一致

### 方向 10：持久化实现（2 个保留，改为内存存储）

- [ ] 10.1 GAP-32 CookieManager 补充 saveResponse/loadRequest（内存 Map 实现）
- [ ] 10.2 GAP-34 getFile 描述修正（误报，行为等价）
- [ ] 10.3 验证：HTTP 响应的 Set-Cookie 自动保存到内存 Map

### 方向 11：新发现遗漏修复（4 个，P2-P4）

- [ ] 11.1 Debug.kt 补充状态管理
- [ ] 11.2 await 回调顺序对齐
- [ ] 11.3 AnalyzeUrl 标记 getGlideUrl/getMediaItem 为不实现
- [ ] 11.4 补充 CheckSource 校验功能
- [ ] 11.5 验证：Debug 状态依赖代码行为正常 + 批量校验可用

### 方向 12：第四轮 P0 级修复（6 个，P0）

- [ ] 12.1 GAP-36 JsExtensions 委托模式改为实例化模式
- [ ] 12.2 GAP-37 移植 ConcurrentRateLimiter 完整限流实现（**源码核实修正：ConcurrentRecord 在 AnalyzeUrl 中**）
- [ ] 12.3 GAP-38 getSubDomain 对齐 PublicSuffixDatabase
- [ ] 12.4 GAP-39 搜索阶段创建独立 RuleData() 注入
- [ ] 12.5 GAP-40 详情阶段添加 removeAllBookType+addType 类型重置
- [ ] 12.6 GAP-41 RSS 调试创建独立 RuleData() 注入
- [ ] 12.7 验证：并发调试 source/book 变量正确 + 限流生效

### 方向 13：第四轮 P1 级修复（14 个，P1）

- [ ] 13.1 GAP-42 移植 SymmetricCryptoAndroid 对齐 encryptBase64
- [ ] 13.2 GAP-43 移植 toStringArray() 处理多字节字符
- [ ] 13.3 GAP-44/45/46 移除 AnalyzeUrl 仿真端多余功能（**源码核实修正：AnalyzeUrl 无 followRedirects 字段**）
- [ ] 13.4 GAP-47/52 补充 loginCheckJs 检测
- [ ] 13.5 GAP-48/49 详情阶段修复
- [ ] 13.6 GAP-50/51/53 分页处理对齐
- [ ] 13.7 GAP-54 Book 数据模型对齐（**源码核实修正：BookType.text=0b1000(8)**）
- [ ] 13.8 GAP-55 新增 SearchBook 数据模型
- [ ] 13.9 验证：加密结果一致 + 多字节字符正确

### 方向 14：第四轮 P2 级修复（11 个，P2）

- [ ] 14.1 GAP-56 evalJS 注入持久化对象
- [ ] 14.2 GAP-57 反向引入真机 getZipByteArrayContent 循环 bug
- [ ] 14.3 GAP-58 补充 BookChapter 业务方法（**源码核实修正：无 chapterUrl/level，实际为 url**）
- [ ] 14.4 GAP-59 BookSource/RssSource 改为继承 BaseSourceInterface（**源码核实修正：BaseSource 是 interface**）
- [ ] 14.5 GAP-60/61/62/63 移除 RSS 调试仿真端多余功能
- [ ] 14.6 GAP-64/65/66 网络层标记不实现
- [ ] 14.7 验证：边缘场景行为一致

### 方向 15：第五轮 WebBook/Rss 模块修复（5 个 P0 必需 + 16 个 P1 可选）

#### 15.1 P0 级修复（5 个，必须修复）

- [ ] 15.1.1 GAP-67a 所有阶段添加 loginCheckJs 检测逻辑
- [ ] 15.1.2 GAP-67b 目录/正文分页添加 ruleNextPage=="PAGE" 特殊处理（**源码核实修正：在 `model/rss/RssParserByRule.kt`（非 `rss/RssParserByRule.kt`）；使用 `uppercase()` 转大写比较，`"page"`/`"Page"`/`"PAGE"` 均可匹配**）
- [ ] 15.1.3 GAP-67c init 规则执行方式改为 getElement（**源码核实修正：init 规则在 BookInfo.kt**）
- [ ] 15.1.4 GAP-67d 移植完整正文格式化链（**源码核实修正：HtmlFormatter 方法名是 format 非 formatHtml；文件路径是 `utils/HtmlFormatter.kt` 非 `help/book/HtmlFormatter.kt`**）
- [ ] 15.1.5 GAP-67e 搜索/详情阶段添加 checkRedirect 重定向检测
- [ ] 15.1.6 验证：所有 P0 级修复后调试结果与真机一致

#### 15.2 P1 级修复（16 个，可选修复）

- [ ] 15.2.1~15.2.16 GAP-68a~p 可选修复（遇到实际失败源时实施）
- [ ] 15.2.17 验证：可选修复实施后调试结果与真机一致

### 方向 16：第五轮 Rhino/并发基础架构修复（2 个 P0 重新设计）

- [ ] 16.1.1 GAP-70a（重新设计-AD-11）：移植 WrapFactory + instructionObserverThreshold（**源码核实修正：instructionObserverThreshold=10000；WrapFactory 依赖 ClassShutter 需移除调用**）
- [ ] 16.1.2 GAP-70b（重新设计-AD-12）：只添加 withTimeout 超时控制
- [ ] 16.1.3 验证：JS 执行行为与真机一致 + 超时控制正常

### 方向 17：第六轮 P0 级修复（2 个重新设计）

- [x] 17.1 GAP-67 内存存储（不引入数据库）✅ 2026-06-21（AppConfig.kt + AnalyzeUrl.kt 第752-779行内存 Map 实现）
- [~] 17.2 GAP-80 只添加 UA 注入 + CookieJar（不添加 5 个拦截器）（**部分实现：UA 注入已完成，CookieJar 拦截器未完成**）
- [ ] 17.3 验证：内存存储在会话内正常工作 + UA 注入行为与真机一致

### 方向 18：第六轮 P1 级修复（1 个重新设计 + 3 个保留）

- [ ] 18.1 GAP-72 只补充 userAgent + customHosts 到 AppConfig
- [ ] 18.2 GAP-82 CookieJar 拦截器（保留）
- [ ] 18.3 GAP-83 UA 自动注入拦截器（保留）
- [ ] 18.4 验证：UA 注入行为与真机一致 + CookieJar 自动管理 Cookie

### 方向 19：第六轮 P2/P3 级修复

- [ ] 19.1 GAP-73 userAgent 默认值改为与真机一致（保留）
- [ ] 19.2 GAP-75 只补充 MAX_THREAD + charsets（重新设计）
- [ ] 19.3 GAP-76 customHosts/DNS 自定义解析（保留）
- [ ] 19.4 GAP-88 ReplaceAnalyzer（可选修复）
- [ ] 19.5 验证：保留项行为一致

---

## 第二部分：Python 客户端优化

### 方向 20：source_validator 预校验模块（新建）

> **源码依据**：`BookSource.kt` / `RssSource.kt` 字段定义

#### 20.1 BookSource 字段校验

- [ ] 20.1.1 阅读 `BookSource.kt` 确认必填字段列表（**源码核实修正：searchUrl/ruleSearch 实际可空**）
- [ ] 20.1.2 实现 BookSource 必填字段校验（bookSourceName/bookSourceUrl/bookSourceType）
- [ ] 20.1.3 实现 BookSource 推荐字段校验（searchUrl/ruleSearch 降级为 WARN）
- [ ] 20.1.4 实现 BookSource 字段冲突检测
- [ ] 20.1.5 验证：用真实 BookSource 测试校验结果

#### 20.2 RssSource 字段校验

- [ ] 20.2.1 阅读 `RssSource.kt` 确认必填字段列表（**源码核实修正：字段名是 type 非 sourceType；ruleArticles 实际可空**）
- [ ] 20.2.2 实现 RssSource 必填字段校验（sourceName/sourceUrl/type）
- [ ] 20.2.3 实现 RssSource 字段冲突检测
- [ ] 20.2.4 验证：用真实 RssSource 测试校验结果

#### 20.3 URL 格式校验

- [ ] 20.3.1 实现 URL 格式校验（协议+域名合法性）
- [ ] 20.3.2 实现 URL 模板变量校验（{{key}}/{{page}} 等变量合法性）
- [ ] 20.3.3 验证：URL 格式校验准确

### 方向 21：rule_precheck 规则语法预检查（新建）

> **源码依据**：`AnalyzeRule.kt` 规则类型识别逻辑

#### 21.1 规则类型识别

- [ ] 21.1.1 阅读 `AnalyzeRule.kt` 确认规则类型前缀（**源码核实修正：@Json: 大写 J；@js: 和 `<regex>` 前缀不存在**）
- [ ] 21.1.2 实现规则类型识别函数
- [ ] 21.1.3 验证：规则类型正确识别

#### 21.2 CSS 选择器语法校验

- [ ] 21.2.1 用 soupsieve 校验 `@CSS:` 前缀规则语法
- [ ] 21.2.2 处理 jsoup 扩展语法（降级为 WARN）
- [ ] 21.2.3 验证：CSS 选择器语法错误能被捕获

#### 21.3 XPath 语法校验

- [ ] 21.3.1 用 lxml 校验 `@XPath:` 前缀规则语法
- [ ] 21.3.2 验证：XPath 语法错误能被捕获

#### 21.4 JSONPath 语法校验

- [ ] 21.4.1 检查 jsonpath-ng 是否已安装，未安装则降级为括号匹配检查
- [ ] 21.4.2 用 jsonpath-ng 校验 `@Json:` 前缀规则语法（**源码核实修正：大写 J**）
- [ ] 21.4.3 验证：JSONPath 语法错误能被捕获

#### 21.5 JS 规则语法检查

- [ ] 21.5.1 实现 JS 规则括号匹配检查（**源码核实修正：`<js>` 是正则匹配非前缀**）
- [ ] 21.5.2 实现 JS 关键字检查
- [ ] 21.5.3 验证：JS 语法错误能被捕获（不执行 JS）

#### 21.6 规则提取

- [ ] 21.6.1 实现 BookSource 规则字段提取
- [ ] 21.6.2 实现 RssSource 规则字段提取
- [ ] 21.6.3 验证：所有规则字段被正确提取

### 方向 22：debug_runner 流程调整（修改）

#### 22.1 集成预校验

- [ ] 22.1.1 在 run() 入口添加 source_validator 调用
- [ ] 22.1.2 在 run() 入口添加 rule_precheck 调用
- [ ] 22.1.3 预校验失败时返回 DebugResult(success=False, stage="prevalidate"/"precheck")
- [ ] 22.1.4 验证：预校验失败时不调用 JAR

#### 22.2 降级路径优化

- [ ] 22.2.1 实现 JAR 不可用时降级到 Python 模式
- [ ] 22.2.2 降级模式只支持搜索和详情阶段
- [ ] 22.2.3 降级模式结果标注"Python 降级模式，建议用 JAR 复验"
- [ ] 22.2.4 验证：降级路径正常工作

#### 22.3 错误诊断闭环

- [ ] 22.3.1 JAR 失败时调用 error_diagnoser 诊断
- [ ] 22.3.2 可自动修复时调用 auto_fixer 修复后重试（最多 3 次）
- [ ] 22.3.3 需用户介入时调用 user_interaction 生成交互请求
- [ ] 22.3.4 验证：错误诊断闭环正常工作

### 方向 23：error_diagnoser 错误类型扩充（修改）

#### 23.1 新增错误类型

- [ ] 23.1.1 新增预校验错误类型（字段缺失/规则语法错误）
- [ ] 23.1.2 新增 JAR 通信错误类型（进程崩溃/超时/端口占用）
- [ ] 23.1.3 新增仿真端差异错误类型（行为不一致）
- [ ] 23.1.4 新增网站结构变化错误类型
- [ ] 23.1.5 验证：新增错误类型能被正确识别

#### 23.2 修复建议模板

- [ ] 23.2.1 为每种错误类型编写修复建议模板
- [ ] 23.2.2 修复建议包含：错误描述/可能原因/修复方法/参考文档链接
- [ ] 23.2.3 验证：修复建议清晰可操作

#### 23.3 对接 auto_fixer

- [ ] 23.3.1 标记每种错误类型是否可自动修复
- [ ] 23.3.2 可自动修复的错误类型对接 auto_fixer 修复方法
- [ ] 23.3.3 验证：auto_fixer 能根据错误类型选择修复方法

### 方向 24：experience_manager 半自动经验写入（修改）

#### 24.1 经验要素自动提取

- [ ] 24.1.1 实现网站特征提取（URL/框架/反爬/编码）
- [ ] 24.1.2 实现错误模式提取（类型/阶段/选择器）
- [ ] 24.1.3 实现修复方法提取（方法/新选择器/原因）
- [ ] 24.1.4 实现规则模式提取（searchUrl/rule*字段）
- [ ] 24.1.5 验证：经验要素被正确提取

#### 24.2 经验草稿生成

- [ ] 24.2.1 实现经验草稿 JSON 格式生成
- [ ] 24.2.2 草稿写入 experience/pending/ 目录
- [ ] 24.2.3 验证：草稿格式正确

#### 24.3 半自动写入流程

- [ ] 24.3.1 实现 AI 审核接口（可选，默认跳过）
- [ ] 24.3.2 实现写入 basic-memory（通过 MCP）
- [ ] 24.3.3 实现写入 references/（降级路径，通过文件写入）
- [ ] 24.3.4 实现 conflict_resolver 冲突检测和解决
- [ ] 24.3.5 验证：半自动写入流程正常工作

---

## 第三部分：Skill 工作流优化

### 方向 25：SKILL.md 5 阶段工作流调整（修改）

#### 25.1 Phase 2 预校验

- [ ] 25.1.1 在 Phase 2 末尾添加预校验步骤描述
- [ ] 25.1.2 添加 source_validator + rule_precheck 调用说明
- [ ] 25.1.3 预校验失败时返回 Phase 2 重新构建的流程描述
- [ ] 25.1.4 验证：Phase 2 描述与实现一致

#### 25.2 Phase 3 降级路径

- [ ] 25.2.1 添加 JVM 不可用时降级到 Python 模式的描述
- [ ] 25.2.2 添加降级模式限制说明（只支持搜索和详情）
- [ ] 25.2.3 添加降级模式结果标注说明
- [ ] 25.2.4 验证：Phase 3 降级路径描述与实现一致

#### 25.3 Phase 4 工具辅助

- [ ] 25.3.1 添加 source_navigation 自动导航描述
- [ ] 25.3.2 添加 error_diagnoser 修复建议描述
- [ ] 25.3.3 添加 auto_fixer 自动修复描述
- [ ] 25.3.4 验证：Phase 4 工具辅助描述与实现一致

#### 25.4 Phase 5 半自动经验写入

- [ ] 25.4.1 添加 experience_manager 半自动写入描述
- [ ] 25.4.2 添加经验草稿生成和审核流程描述
- [ ] 25.4.3 添加 conflict_resolver 冲突解决描述
- [ ] 25.4.4 验证：Phase 5 半自动经验写入描述与实现一致

#### 25.5 Phase 3 JVM 降级路径行为修正（第九轮新增，REQ-S05）

- [ ] 25.5.1 修改 debug_runner.py 第 754-766 行：退出码 3 中断改为自动降级到 Python 模式
- [ ] 25.5.2 实现 _python_fallback_debug() 函数（requests + BeautifulSoup4 简化调试）
- [ ] 25.5.3 降级模式结果标注"Python 降级模式，建议用 JAR 复验"，可信度降为 medium
- [ ] 25.5.4 验证：JVM 不可用时工作流不中断，降级模式正常工作

#### 25.6 Phase 3 错误诊断覆盖扩充（第九轮新增，第十轮修正，REQ-S06）

- [ ] 25.6.1 扩充 auto_fixer 错误类型从 4 种（rule_parse/css/url_empty/network）到 12 种
- [ ] 25.6.2 实现 12 种错误类型的自动修复方法（见 design.md 3.6 节表格）
- [ ] 25.6.3 验证：auto_fixer 覆盖全部 12 种错误类型，自动修复成功率 > 50%

#### 25.7 Phase 5 经验写入自动化提升（第九轮新增，第十轮修正，REQ-S07）

- [ ] 25.7.1 **新增** experience_manager.extract() 方法：自动提取经验要素（现有方法为 search()/write_pending()，不存在 extract()）
- [ ] 25.7.2 **新增** experience_manager.write_to_basic_memory() 方法：返回 MCP 调用指令由 AI agent 执行
- [ ] 25.7.3 实现降级路径：MCP 不可用时写入 references/
- [ ] 25.7.4 验证：经验写入从全手动改为半自动

---

## 第五部分：Python 客户端工程化修复（第九轮新增）

### 方向 26：JVM 依赖断裂修复（REQ-P07，P0）

> **问题**：`tools/rule_engine_client.py` 已迁移到 `legado_client/client/`，但 5 个独立脚本仍引用旧路径，导致 JVM 验证功能全部失效。

- [ ] 26.1 修复 verify-source.py 的 import 路径（`from rule_engine_client` → `from legado_client.client.rule_engine_client`）
- [ ] 26.2 修复 analyze_site.py 的 import 路径
- [ ] 26.3 修复 verify-selector.py 的 import 路径
- [ ] 26.4 修复 verify-decrypt.py 的 import 路径
- [ ] 26.5 修复 verify-image.py 的 import 路径
- [ ] 26.6 修复 tools/jvm_helpers.py 的 import 路径
- [ ] 26.7 验证：5 个独立脚本的 JVM 验证功能恢复正常

### 方向 27：双客户端整合（REQ-P08，P1）

> **问题**：tools/（扁平结构）与 legado_client/（规范包）并存，debug_runner.py 混合依赖两套模块，职责边界模糊。

#### 27.1 核心模块迁移

- [ ] 27.1.1 迁移 auto_fixer.py → legado_client/analyzer/auto_fixer.py
- [ ] 27.1.2 迁移 obstacle_resolver.py → legado_client/client/obstacle_resolver.py
- [ ] 27.1.3 迁移 crypto_analyzer.py → legado_client/analyzer/crypto_analyzer.py
- [ ] 27.1.4 迁移 interactive_guide.py → legado_client/client/interactive_guide.py
- [ ] 27.1.5 迁移 jvm_helpers.py → legado_client/utils/jvm_helpers.py

#### 27.2 debug_runner.py 依赖统一

- [ ] 27.2.1 移除 debug_runner.py 中的 try-import 降级（obstacle_resolver/crypto_analyzer/auto_fixer/interactive_guide）
- [ ] 27.2.2 改为包内直接 import
- [ ] 27.2.3 验证：debug_runner.py 无 try-import 降级，所有核心模块在 legado_client/ 内

#### 27.3 tools/ 目录清理

- [ ] 27.3.1 确认 tools/ 仅保留无包依赖的独立工具（html_fetcher.py、fetch_html.py 等）
- [ ] 27.3.2 删除已迁移的旧文件（auto_fixer.py、obstacle_resolver.py 等）
- [ ] 27.3.3 验证：tools/ 仅保留独立工具，无核心模块

---

## 第四部分：全量回归测试

### 方向 7：全量回归测试（P0）

> **验证标准**：JAR 测试通过则真机也能通过；JAR 测试失败时，能准确区分是源规则问题还是仿真端问题

#### 7.1 重新构建 JAR

- [ ] 7.1.1 重新构建 fatJar
- [ ] 7.1.2 验证：JAR 启动正常

#### 7.2 全量批量测试

- [ ] 7.2.1 用 100 个真实源全量测试
- [ ] 7.2.2 统计成功率
- [ ] 7.2.3 分析失败源根因（区分仿真端/源规则/网站）
- [ ] 7.2.4 验证：JAR 测试通过则真机也能通过；JAR 失败时能准确区分源规则问题还是仿真端问题

#### 7.3 经验反哺

- [ ] 7.3.1 将修复经验写入 basic-memory
- [ ] 7.3.2 更新 simulation-gap-report.md
- [ ] 7.3.3 更新 tasks.md 完成状态

---

## 任务依赖关系

```
第一部分：JAR 仿真服务端修复
方向 1（低难度）──┐
方向 2（中难度）──┤
方向 3（高难度）──┤
方向 4（委托路径）─┤
方向 5（仿真端问题）┤
方向 6（失败源优化）┤
方向 8（OkHttpUtils）─┤
方向 9（RssDebugger）─┤
方向 10（持久化）──┤
方向 11（新发现遗漏）─┤
方向 12（第四轮P0）─┤
方向 13（第四轮P1）─┤
方向 14（第四轮P2）─┤
方向 15（第五轮WebBook/Rss）─┤
方向 16（第五轮Rhino/并发）─┤
方向 17（第六轮P0）─┤
方向 18（第六轮P1）─┤
方向 19（第六轮P2/P3）─┤
                  │
第二部分：Python 客户端优化
方向 20（source_validator）─┤
方向 21（rule_precheck）────┤
                  │         │
方向 22（debug_runner 集成）─┤
方向 23（error_diagnoser）───┤
方向 24（experience_manager）─┤
                  │         │
第三部分：Skill 工作流优化
方向 25（SKILL.md 更新）────┤
                  │         │
第五部分：Python 客户端工程化修复（第九轮新增）
方向 26（JVM 依赖断裂修复）─┤
方向 27（双客户端整合）─────┤
                  │         │
                  ├──→ 方向 7（全量回归测试）
```

**关键依赖**：
- 方向 22 依赖方向 20 + 21（预校验模块必须先实现）
- 方向 22 依赖方向 23（错误诊断闭环需要 error_diagnoser 扩充）
- 方向 22 依赖方向 24（经验写入需要 experience_manager 优化）
- 方向 25 依赖方向 20-24 全部完成（SKILL.md 描述需要与实现一致）
- 方向 25.5-25.7 依赖方向 22（debug_runner 修改需要先集成预校验）
- 方向 27 依赖方向 26（先修复依赖断裂，再整合双客户端）
- 方向 7 依赖方向 1-6 + 8-27 全部完成

---

## 验收标准

| 标准 | 验证方法 | 目标 |
|------|---------|------|
| 46 个可修复方法 | 逐方法对比真机 | ✅ 行为一致 |
| 21 个委托路径 | Selenium/环境变量/日志 | ✅ 委托成功 |
| 2 个仿真端问题 | BT之家/阳光电影 | ✅ 可访问 |
| 58 个失败源优化 | 重新批量测试 | ✅ 修复后通过 |
| 3 个 OkHttpUtils 方法 | 下载文件/zip 解压/协程取消 | ✅ 行为一致 |
| 5 个 RssSourceDebugger 逻辑 | RSS 源调试对比真机 | ✅ 调试结果一致 |
| 2 个持久化保留 | CookieManager 内存 Map 实现 | ✅ 单次校验期间有效 |
| 4 个新发现遗漏 | Debug 状态/校验功能 | ✅ 补充完成 |
| 6 个第四轮 P0 新发现 | 并发调试/限流/域名/ruleData/类型重置 | ✅ 行为一致 |
| 14 个第四轮 P1 新发现 | 加密/字体/多余功能移除/loginCheckJs/分页/数据模型 | ✅ 行为一致 |
| 11 个第四轮 P2 新发现 | 边缘场景验证 | ✅ 补充完成 |
| 5 个第五轮 WebBook/Rss P0 | loginCheckJs/PAGE/init/正文格式化链/checkRedirect | ✅ 所有阶段调试一致 |
| 2 个第五轮 Rhino/并发 P0 | WrapFactory+instructionObserverThreshold/withTimeout | ✅ JS 执行一致 |
| 2 个第六轮 P0 重新设计 | 内存存储/UA 注入+CookieJar | ✅ 基础设施就绪 |
| **source_validator 预校验** | **用真实源测试字段校验** | **✅ 字段缺失/冲突能被捕获** |
| **rule_precheck 规则语法校验** | **用真实源测试规则语法校验** | **✅ 规则类型语法错误能被捕获** |
| **debug_runner 预校验集成** | **预校验失败时不调用 JAR** | **✅ 预校验 < 3 秒** |
| **debug_runner 降级路径** | **JAR 不可用时降级到 Python 模式** | **✅ 搜索和详情可执行** |
| **error_diagnoser 错误类型扩充** | **新增错误类型能被识别** | **✅ 16 种错误类型覆盖** |
| **experience_manager 半自动写入** | **测试后自动生成经验草稿** | **✅ 草稿格式正确** |
| **SKILL.md 5 阶段工作流** | **Phase 2-5 描述与实现一致** | **✅ 文档与代码一致** |
| **JVM 降级路径行为修正** | **JVM 不可用时自动降级到 Python 模式** | **✅ 工作流不中断** |
| **错误诊断覆盖扩充** | **auto_fixer 覆盖 12 种错误类型** | **✅ 自动修复成功率 > 50%** |
| **经验写入自动化提升** | **experience_manager 自动提取经验要素** | **✅ 半自动写入 basic-memory** |
| **JVM 依赖断裂修复** | **5 个独立脚本 JVM 验证功能恢复** | **✅ verify-source.py 等可调用 JAR** |
| **双客户端整合** | **debug_runner.py 无 try-import 降级** | **✅ 核心模块统一在 legado_client/** |
| **全量回归测试** | **100 个真实源** | **JAR 通过则真机通过；JAR 失败能准确区分原因** |
| **100% 测试校验准确性** | **真机能运行的源** | **JAR 测试结果与真机一致** |
| **自动化率** | **100 个真实源测试** | **> 70% 无需手动操作** |
| **预校验拦截率** | **预校验失败的源占比** | **> 20% 无效 JAR 调用被拦截** |
| **自动修复成功率** | **auto_fixer 修复后通过率** | **> 50%** |
