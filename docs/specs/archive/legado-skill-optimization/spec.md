# Spec: Legado Skill 整体优化方案

> **统一 OpenSpec**：合并 simulation-fidelity-95（JAR 仿真服务端）+ python-client-optimization（Python 客户端）+ Skill 工作流优化
> **源码核实修正**：3 组子代理（27 个源文件）逐行核实，修正 18 个设计文档错误

---

## Intent

让 AI/Agent 使用 legado-source-creator Skill 快速为用户开发/优化书源和订阅源，**减少对开源阅读源码的依赖**，通过 JAR 仿真服务端 + Python 客户端协作完成测试校验。

**核心目标**：
1. **100% 测试校验准确性**：JAR 测试通过则真机也能通过；JAR 失败时能准确区分源规则问题还是仿真端问题
2. **减少源码依赖**：AI 使用 Skill 生成源后，无需查阅 Legado 源码即可完成测试校验
3. **自动化率 > 70%**：70% 的网站生成可用源无需手动操作；30% 需用户协助时提供 AI 指引
4. **快速反馈**：预校验 < 3 秒，JAR 调试 < 30 秒，全流程 < 2 分钟

**与旧目标的区别**：
- 旧目标"100% 兼容运行"：要求所有方法行为与真机完全一致，包括持久化/安全沙箱/性能等 → 185 个 GAP 中 40% 是过度修复
- 新目标"100% 测试校验准确性"：只要求影响测试校验结果的行为与真机一致 → 52 个必需修复 + 28 个可选修复 + 10 个重新设计 + 75 个过度修复（不实施）

---

## Scope

### 核心定义：什么算"100% 测试校验准确性"

| 场景 | 判定 | 责任方 |
|------|------|--------|
| JAR 测试通过，真机也能通过 | ✅ 准确 | - |
| JAR 测试通过，但真机失败（假阳性） | ❌ 必须修复 | 仿真端 |
| JAR 测试失败，但真机能运行（假阴性） | ❌ 必须修复 | 仿真端 |
| JAR 测试失败，真机也失败（源规则问题） | ✅ 准确（正确识别源规则问题） | 源规则 |
| 真机也运行失败（网站改版/反爬/域名失效/SSL 过期） | ➖ 不计入 | 网站 |
| Android 平台特有方法（WebView/UI/硬件） | 🔄 委托路径 | 平台限制 |
| 持久化/安全沙箱/性能差异（不影响校验结果） | ➖ 不计入 | 过度修复 |

### 涵盖范围

#### 1. JAR 仿真服务端修复（52 个必需 + 28 个可选 + 10 个重新设计）

**A. 低难度修复（12 个，P0）**：
- 6 个属性 var→val 签名修正（concurrentRate/loginUrl/loginUi/header/enabledCookieJar/jsLib）
- timeFormat 格式对齐（**源码核实修正：dateFormat 在 AppConst 不在 BaseSource**）
- connect 错误时 url 修正
- getTxtInFolder 删除 folder
- importScript 异常类型替换
- aesEncodeToString 对齐真机 bug（**源码核实修正：aesEncodeToString 在 JsEncodeUtils 不在 JsExtensions；疑似源码 Bug，加密方法调用解密**）

**B. 中难度修复（18 个，P0）**：
- 6 个 base64/AES flags 映射完善（**源码核实修正：mapBase64Flags 方法不存在，需新建映射逻辑**）
- 3 个 get/head/post 改用 Jsoup.connect 对齐真机
- 2 个 ajaxAll/ajaxTestAll 并发实现
- 2 个 downloadFile 流式下载 + 路径修正
- toNumChapter 章节号转换
- log 接入 Debug 回调
- putConcurrent 实现（**源码核实修正：ConcurrentRecord 定义在 AnalyzeUrl 中，非 ConcurrentRateLimiter**）
- executeSortUrlJs 注入 source 变量
- evalJS 实现 sharedScope

**C. 高难度修复（8 个，P0）**：
- refreshJSLib 实现 SharedJsScope
- getLoginInfoMap 实现 RowUi 解析（**源码核实修正：getLoginInfoMap 在 BaseSource 不在 JsExtensions**）
- getHeaderMap 对齐 AppConfig.userAgent
- debugExplore infoMap 实现
- ~~压缩文件解压（4 个）~~ ❌ 延后
- ~~Rar/7z 内容读取（4 个）~~ ❌ 延后
- ~~配置读取（4 个）~~ 🔄 重新设计：只补充 userAgent/customHosts
- ~~refreshExplore~~ ❌ 过度修复

**D. 委托路径实现（21 个不可实现方法）**：
- WebView 渲染委托（9 个）→ Python Selenium
- Android UI 交互委托（5 个）→ Selenium + OCR
- Android 硬件信息配置（4 个）→ 环境变量
- Toast 输出替代（2 个）→ 日志文件
- Debugger WebView 委托（1 个）→ Selenium

**E. 第四轮深度排查修复（31 个）**：
- P0（6 个）：GAP-36 委托模式并发覆盖、GAP-37 限流器空实现、GAP-38 域名提取、GAP-39/40/41 ruleData 注入
- P1（14 个）：GAP-42 加密差异、GAP-43 多字节字符、GAP-44/45/46 多余功能移除（**源码核实修正：AnalyzeUrl 无 followRedirects 字段，GAP-44 描述需修正**）、GAP-47/52 loginCheckJs、GAP-48/49 详情修复、GAP-50/51/53 分页对齐、GAP-54/55 数据模型
- P2（11 个）：边缘场景修复

**F. 第五轮深度排查修复（41 个）**：
- P0（5 个必需）：GAP-67a loginCheckJs 全阶段、GAP-67b PAGE 分页（**源码核实修正：ruleNextPage=="PAGE" 在 RssParserByRule.kt 非 WebBook.kt**）、GAP-67c init 规则（**源码核实修正：init 规则在 BookInfo.kt 非 WebBook.kt**）、GAP-67d 正文格式化链（**源码核实修正：HtmlFormatter 方法名是 format 非 formatHtml**）、GAP-67e checkRedirect
- P1（16 个可选）：preUpdateJs、并发分页、章节字段（**源码核实修正：BookChapter 无 chapterUrl/level 字段，实际为 url**）等
- P2（9 个不修复）：模块移植过度修复

**G. 第六轮深度排查修复（29 个）**：
- P0（2 个重新设计）：GAP-67 Room 数据库→内存存储、GAP-80 HTTP 拦截器→只添加 UA 注入+CookieJar
- P1（8 个）：4 个过度修复 + 1 个重新设计 + 3 个保留
- P2/P3（19 个）：12 个过度修复 + 2 个保留 + 2 个重新设计 + 3 个保持原状

#### 2. Python 客户端优化（6 个方向）

**A. source_validator 预校验模块（新建）**：
- BookSource 必填字段校验（**源码核实修正：searchUrl/ruleSearch 实际可空，不应标记为必填**）
- RssSource 必填字段校验（**源码核实修正：字段名是 type 非 sourceType；ruleArticles 实际可空**）
- 字段冲突检测
- URL 格式校验

**B. rule_precheck 规则语法预检查（新建）**：
- CSS 选择器语法校验（@CSS: 前缀）
- XPath 语法校验（@XPath: 前缀）
- JSONPath 语法校验（**源码核实修正：源码书写为 `@Json:`（大写 J），但 `startsWith` 第二参数为 `true`（忽略大小写），`@json:` 也能匹配。建议书源规则统一用大写 `@Json:`**）
- JS 语法检查（**源码核实修正：在 `AnalyzeRule.kt` 规则解析中，`@js:` 和 `<js></js>` 均通过 `JS_PATTERN` 正则匹配（非前缀判断）；`<regex>` 前缀不存在。但 `@js:` 在 `BaseSource.kt` 等其他文件中是作为前缀使用**）
- 正则语法校验

**C. debug_runner 流程调整（修改）**：
- 集成预校验
- 降级路径优化（JAR 不可用时降级到 Python 模式）
- 错误诊断闭环

**D. error_diagnoser 错误类型扩充（修改）**：
- 新增预校验错误类型
- 新增 JAR 通信错误类型
- 新增仿真端差异错误类型
- 新增网站结构变化错误类型

**E. experience_manager 半自动经验写入（修改）**：
- 经验要素自动提取
- 经验草稿生成
- 半自动写入流程

**F. 双客户端职责边界明确**：
- legado_client/ 是核心包，包含调试流程必需的模块
- tools/ 是辅助包，包含可选的增强模块

#### 3. Skill 工作流优化（5 阶段闭环）

- Phase 2 添加预校验步骤
- Phase 3 优化降级路径
- Phase 4 添加工具辅助
- Phase 5 添加半自动经验写入

#### 4. 失败源优化（58 个源，用真实源测试验证）

- 31 个 RSS 源 sortUrl bug 修复
- 23 个 book 源搜索规则重写
- 2 个 bookList 类型错误修复
- 2 个 URL 模板错误修复

### 不涵盖范围

- 真机也失败的源（网站改版/反爬/域名失效/SSL 过期）——非仿真端责任
- 源规则本身写错（真机也失败）——非仿真端责任
- 需要 Android 硬件的方法（无替代方案时）——平台限制
- JAR 仿真服务端的修复（由本统一 OpenSpec 负责）
- Legado 源码修改（客户端只调用 JAR，不直接修改源码）
- 新增 Python 依赖（复用现有依赖，不引入新框架）

---

## Approach

### 核心策略：三层协作 + 真机源码逐行对齐 + 真实源测试验证

#### 策略 1：源码移植优先（修正过度修复项）

所有方法修复均基于真机源码逐行分析，优先**直接移植真机源码**：

| 修复类别 | 策略 | 理由 |
|---------|------|------|
| ~~压缩文件解压~~ | ~~移植 ArchiveUtils~~ | ~~延后~~ |
| ~~配置读取~~ | ~~移植 ReadBookConfig/ThemeConfig~~ | ~~重新设计：只补充 userAgent/customHosts~~ |
| base64/AES flags | 完善 flags 映射表（**源码核实修正：mapBase64Flags 方法不存在，需新建**） | 真机使用 android.util.Base64 |
| 并发请求 | 使用 CompletableFuture/线程池 | 真机使用 runBlocking + flow.mapAsync |
| SharedJsScope | 移植 SharedJsScope（Rhino Scope 管理） | 真机使用 getShareScope |
| WrapFactory | 移植 WrapFactory（移除对 ClassShutter 的调用） | 真机使用 RhinoWrapFactory |

#### 策略 2：委托路径实现

不可实现方法通过委托路径实现"行为等价"：

| 不可实现方法 | 委托路径 | 实现方式 |
|------------|---------|---------|
| WebView 渲染 | Python Selenium | WebViewRequiredException 携带请求信息 → Python 执行 → 回传结果 |
| UI 交互 | Selenium + OCR | UserInterventionException 携带上下文 → Selenium/OCR 处理 |
| 硬件信息 | 环境变量 | LEGADO_ANDROID_ID/LEGADO_WEBVIEW_UA 环境变量注入 |
| Toast | 日志文件 | 写入 debug.log 文件 |

#### 策略 3：预校验前置（减少无效 JAR 调用）

在 debug_runner 入口添加 source_validator + rule_precheck，拦截字段缺失和语法错误的源，避免无效 JAR 调用。

**收益**：预计减少 20-30% 的无效 JAR 调用

#### 策略 4：错误诊断闭环（减少源码查阅）

扩充 error_diagnoser 错误类型，对接 auto_fixer 自动修复，AI 无需查阅 Legado 源码即可修复常见错误。

**收益**：预计 50% 的错误可自动修复，30% 有明确修复建议，20% 需用户介入

#### 策略 5：经验半自动写入（减少手动记录）

experience_manager 自动提取经验要素，生成草稿，AI 审核后写入 basic-memory。

**收益**：经验写入从全手动改为半自动，预计节省 80% 的经验记录时间

#### 策略 6：真实源测试验证

用真实书源和订阅源测试，验证修复效果：

1. **修复 31 个 RSS 源 sortUrl bug** → 重新测试
2. **重写 23 个 book 源搜索规则** → 用真实网站 HTML 验证
3. **修复 2 个仿真端问题**（PKIX + DNS）→ 重新测试
4. **全量回归测试** → 目标：真机能运行的源，仿真端也能运行

### 架构原则

1. **不引入新重型依赖**：icu4j 用项目内源码，chinese-transfer 仅几百 KB
2. **保持 object 单例**：SSLHelper/HtmlFormatter/ChineseUtils 均为 object
3. **Android 依赖隔离**：Android 专有 API 用 JDK 替代或委托
4. **与真机逐行对齐**：每个方法实现后必须有源码行号引用
5. **委托路径必须有回传机制**：异常携带上下文 → 委托处理 → 回传结果
6. **预校验用 Python 而非 JAR**：Python 启动快（< 1 秒），JAR 启动慢（3-5 秒）
7. **规则语法校验不执行 JS**：只做语法检查（括号匹配 + 关键字检查）
8. **降级模式只支持搜索和详情**：目录和正文涉及分页/JS 执行，Python 端无法完整实现

---

## Requirements

### JAR 仿真服务端需求

### REQ-01: 低难度方法修复（12 个）

- 6 个属性 var→val 签名修正
- timeFormat 对齐 AppConst.dateFormat（**源码核实修正：dateFormat 在 AppConst 不在 BaseSource**）
- connect 错误时 url 修正为 analyzeUrl.url
- getTxtInFolder 添加 folder 删除
- importScript 改用 NoStackTraceException
- aesEncodeToString 对齐真机 bug（**源码核实修正：aesEncodeToString 在 JsEncodeUtils 不在 JsExtensions；疑似源码 Bug**）
- **验证**：编译通过 + 签名与真机一致

### REQ-02: 中难度方法修复（18 个）

- 6 个 base64/AES flags 映射完善（**源码核实修正：mapBase64Flags 方法不存在，需新建映射逻辑**）
- 3 个 get/head/post 改用 Jsoup.connect 或对齐 AnalyzeUrl 行为
- 2 个 ajaxAll/ajaxTestAll 并发实现（CompletableFuture）
- 2 个 downloadFile 流式下载 + 路径修正
- toNumChapter 章节号转换
- log 接入 Debug 回调机制
- putConcurrent 实现 updateConcurrentRate（**源码核实修正：ConcurrentRecord 定义在 AnalyzeUrl 中**）
- executeSortUrlJs 注入 source 变量
- evalJS 实现 sharedScope
- **验证**：base64 编解码与真机一致 + 并发请求正确

### REQ-03: 高难度方法修复（8 个）

- refreshJSLib 实现 SharedJsScope
- getLoginInfoMap 实现 RowUi 解析（**源码核实修正：getLoginInfoMap 在 BaseSource 不在 JsExtensions**）
- getHeaderMap 对齐 AppConfig.userAgent
- debugExplore infoMap 实现
- **验证**：SharedJsScope 正确管理 Scope + loginUi 正确解析 + UA 正确注入 + exploreInfoMap 正确构建

### REQ-04: WebView 委托路径实现（9 个）

- WebViewRequiredException 携带完整请求信息
- Python Selenium 端实现 webView 渲染委托
- 结果回传机制（HTTP API 或文件交换）
- **验证**：需要 WebView 渲染的源可调试

### REQ-05: UI 交互委托路径实现（5 个）

- startBrowser → Selenium 浏览器自动化
- getVerificationCode → OCR 自动识别 + 用户介入
- openVideoPlayer/openUrl → 标记为不影响验证
- **验证**：需要登录的源可调试

### REQ-06: 硬件信息环境变量配置（4 个）

- LEGADO_ANDROID_ID 环境变量注入
- LEGADO_WEBVIEW_UA 环境变量注入
- getLoginInfo/putLoginInfo 依赖 androidId 修复
- **验证**：AES 加密解密与真机一致

### REQ-07: 仿真端已知问题修复（2 个）

- BT之家 PKIX → 配置 SSLHelper 信任所有证书
- 阳光电影 DNS → 配置 OkHttp 公共 DNS 回退（223.5.5.5）
- **验证**：BT之家和阳光电影可访问

### REQ-08: 失败源优化（58 个源）

- 31 个 RSS 源 sortUrl bug 修复
- 23 个 book 源搜索规则重写
- 2 个 bookList 类型错误修复
- 2 个 URL 模板错误修复
- **验证**：修复后重新批量测试，真机能运行的源仿真端也能运行

### REQ-09: 全量回归测试

- 用 100 个真实源全量测试
- 对比真机结果（如有真机测试数据）
- 目标：真机能运行的源，仿真端也能运行
- **验证**：成功率显著提升（排除网站问题后）

### REQ-10: OkHttpUtils 方法补全（3 个，P1）

- 补充 newCallResponseBody 扩展函数
- 补充 decompressed 扩展函数
- 补充 await 方法的 invokeOnCancellation 协程取消
- **验证**：下载文件/获取图片/zip 响应解压正常 + 协程取消时底层请求也取消

### REQ-11: RssSourceDebugger 逻辑修正（5 个，P0-P2）

- P0：修正 ruleDescription 逻辑（GAP-22）
- 补充 key::url 格式和搜索关键字调试入口（GAP-23）
- 添加取消机制（GAP-24）
- 补充校验模式（GAP-25）
- 添加无参 key 调试入口（GAP-26）
- **验证**：RSS 源调试结果与真机一致

### REQ-12: 持久化实现（2 个保留，改为内存存储）

- CookieManager 补充 saveResponse/loadRequest 方法（GAP-32，内存 Map 实现）
- getFile 根目录修正（GAP-34，误报修正）
- **验证**：HTTP 响应的 Set-Cookie 自动保存到内存 Map + 后续请求自动携带 Cookie

### REQ-13: 新发现遗漏修复（4 个，P2-P4）

- Debug.kt 补充状态管理
- await 回调顺序对齐
- AnalyzeUrl 标记 getGlideUrl/getMediaItem 为不实现
- 补充 CheckSource 校验功能
- **验证**：Debug 状态依赖代码行为正常 + 批量校验可用

### REQ-14: 第四轮 P0 级修复（6 个，P0）

- GAP-36: JsExtensions 委托模式改为实例化模式
- GAP-37: 移植 ConcurrentRateLimiter 完整限流实现（**源码核实修正：ConcurrentRecord 在 AnalyzeUrl 中**）
- GAP-38: getSubDomain 对齐 PublicSuffixDatabase
- GAP-39: 搜索阶段创建独立 RuleData() 注入
- GAP-40: 详情阶段添加 removeAllBookType+addType 类型重置
- GAP-41: RSS 调试创建独立 RuleData() 注入
- **验证**：并发调试 source/book 变量正确 + 限流生效 + Cookie 域名匹配

### REQ-15: 第四轮 P1 级修复（14 个，P1）

- GAP-42: 移植 SymmetricCryptoAndroid 对齐 encryptBase64
- GAP-43: 移植 toStringArray() 处理多字节字符
- GAP-44/45/46: 移除 AnalyzeUrl 仿真端多余功能（**源码核实修正：AnalyzeUrl 无 followRedirects 字段，GAP-44 描述需修正为"仿真端新增的字段需移除"**）
- GAP-47/52: 补充 loginCheckJs 检测
- GAP-48: 使用扩展属性 book.isWebFile 替代魔法数判断
- GAP-49: 目录阶段添加 preUpdateJs 执行
- GAP-50/51/53: 对齐真机分页处理逻辑
- GAP-54: Book 数据模型对齐（**源码核实修正：BookType.text=0b1000(8) 非 0b1**）
- GAP-55: 新增 SearchBook 数据模型
- **验证**：加密结果一致 + 多字节字符正确 + 多余功能移除后不影响现有源

### REQ-16: 第四轮 P2 级修复（11 个，P2）

- GAP-56: evalJS 注入持久化 CookieStore/CacheManager
- GAP-57: 反向引入真机 getZipByteArrayContent 循环 bug
- GAP-58: 补充 BookChapter 业务方法（**源码核实修正：BookChapter 无 chapterUrl/level 字段，实际为 url**）
- GAP-59: BookSource/RssSource 改为继承 BaseSourceInterface（**源码核实修正：BaseSource 是 interface 不是 class**）
- GAP-60/61/62/63: 移除 RSS 调试仿真端多余功能
- GAP-64: 移植 SSLHelper 双向认证方法
- GAP-65/66: 标记 getMediaItem/Cronet 为不实现
- **验证**：边缘场景行为一致 + 继承体系修改后 JS 执行正常

### REQ-17: 第五轮 WebBook/Rss 模块修复（5 个 P0 必需 + 16 个 P1 可选）

- P0（5 个必需）：loginCheckJs 全阶段、PAGE 分页（**源码核实修正：ruleNextPage=="PAGE" 在 RssParserByRule.kt**）、init 规则（**源码核实修正：init 规则在 BookInfo.kt**）、正文格式化链（**源码核实修正：HtmlFormatter 方法名是 format 非 formatHtml**）、checkRedirect
- P1（16 个可选）：遇到实际失败源时再实施
- **验证**：P0 级 5 个差异修复后，所有阶段调试结果与真机一致

### REQ-18: 第五轮 Rhino/并发基础架构修复（2 个 P0 重新设计）

- GAP-70a: 只移植 WrapFactory + instructionObserverThreshold（**源码核实修正：instructionObserverThreshold=10000 非 1000；maximumInterpreterStackDepth=1000**）
- GAP-70b: 只添加 withTimeout 超时控制
- **验证**：JS 执行中 source/book 变量正确包装 + 死循环源规则被中断

### REQ-19: 第六轮 P0 级修复（2 个重新设计）

- GAP-67: 内存存储（不引入数据库）
- GAP-80: 只添加 UA 注入 + CookieJar（不添加 5 个拦截器）
- **验证**：内存存储在会话内正常工作 + UA 注入行为与真机一致

### REQ-20: 第六轮 P1 级修复（1 个重新设计 + 3 个保留）

- GAP-72: 只补充 userAgent + customHosts 到 AppConfig
- GAP-82: CookieJar 拦截器（保留）
- GAP-83: UA 自动注入拦截器（保留）
- **验证**：UA 注入行为与真机一致 + CookieJar 自动管理 Cookie

### Python 客户端需求

### REQ-P01: source_validator 预校验模块（新建）

- BookSource 必填字段校验（**源码核实修正：searchUrl/ruleSearch 实际可空，降级为 WARN**）
- RssSource 必填字段校验（**源码核实修正：字段名是 type 非 sourceType；ruleArticles 实际可空，降级为 WARN**）
- 字段冲突检测
- URL 格式校验
- **验证**：字段缺失/冲突能被捕获

### REQ-P02: rule_precheck 规则语法预检查（新建）

- CSS 选择器语法校验（@CSS: 前缀）
- XPath 语法校验（@XPath: 前缀）
- JSONPath 语法校验（**源码核实修正：前缀是 @Json: 大写 J**）
- JS 语法检查（**源码核实修正：@js: 前缀不存在，`<js>` 是正则匹配非前缀；无 `<regex>` 前缀**）
- 正则语法校验
- **验证**：5 种规则类型语法错误能被捕获

### REQ-P03: debug_runner 流程调整（修改）

- 集成预校验
- 降级路径优化（JAR 不可用时降级到 Python 模式）
- 错误诊断闭环
- **验证**：预校验失败时不调用 JAR

### REQ-P04: error_diagnoser 错误类型扩充（修改）

- 新增预校验错误类型
- 新增 JAR 通信错误类型
- 新增仿真端差异错误类型
- 新增网站结构变化错误类型
- **验证**：16 种错误类型覆盖

### REQ-P05: experience_manager 半自动经验写入（修改）

- 经验要素自动提取
- 经验草稿生成
- 半自动写入流程
- **验证**：草稿格式正确

### REQ-P06: 双客户端职责边界明确

- legado_client/ 是核心包
- tools/ 是辅助包
- **验证**：代码结构清晰

### REQ-P07: JVM 依赖断裂修复（第九轮审查新增）

**问题**：`tools/rule_engine_client.py` 已迁移到 `legado_client/client/rule_engine_client.py`，但 5 个独立脚本仍引用旧路径，导致 JVM 验证功能全部失效。

- 修复 verify-source.py / analyze_site.py / verify-selector.py / verify-decrypt.py / verify-image.py 的 import 路径
- 修复 tools/jvm_helpers.py 的 import 路径
- **验证**：5 个独立脚本的 JVM 验证功能恢复正常

### REQ-P08: 双客户端整合（第九轮审查新增）

**问题**：tools/（扁平结构，无 `__init__.py`）与 legado_client/（规范包）并存，debug_runner.py 混合依赖两套模块，职责边界模糊。

- 将 tools/ 中的核心模块迁移到 legado_client/ 对应子包：
  - auto_fixer.py → legado_client/analyzer/auto_fixer.py
  - obstacle_resolver.py → legado_client/client/obstacle_resolver.py
  - crypto_analyzer.py → legado_client/analyzer/crypto_analyzer.py
  - interactive_guide.py → legado_client/client/interactive_guide.py
- tools/ 仅保留无包依赖的独立工具（html_fetcher.py、fetch_html.py 等）
- debug_runner.py 统一使用包内 import，移除 try-import 降级
- **验证**：debug_runner.py 无 try-import 降级，所有核心模块在 legado_client/ 内

### Skill 工作流需求

### REQ-S01: Phase 2 预校验

- 在 Phase 2 末尾添加预校验步骤
- **验证**：Phase 2 描述与实现一致

### REQ-S02: Phase 3 降级路径

- 添加 JVM 不可用时降级到 Python 模式的描述
- **验证**：Phase 3 降级路径描述与实现一致

### REQ-S03: Phase 4 工具辅助

- 添加 source_navigation 自动导航描述
- 添加 error_diagnoser 修复建议描述
- 添加 auto_fixer 自动修复描述
- **验证**：Phase 4 工具辅助描述与实现一致

### REQ-S04: Phase 5 半自动经验写入

- 添加 experience_manager 半自动写入描述
- **验证**：Phase 5 半自动经验写入描述与实现一致

### REQ-S05: Phase 3 JVM 降级路径行为修正（第九轮审查新增）

**问题**：SKILL.md 第 219 行描述"JVM 不可用时自动降级到 Python 模式，工作流继续执行"，但实际实现是退出码 3 中断，不是自动继续。

- 修改 debug_runner.py 第 754-766 行：将退出码 3 中断改为自动降级到 Python 模式继续执行
- Python 降级模式：requests + BeautifulSoup4 执行简化调试（只支持搜索和详情阶段）
- 降级模式结果标注"Python 降级模式，建议用 JAR 复验"，可信度降为 medium
- **验证**：JVM 不可用时工作流不中断，降级模式正常工作

### REQ-S06: Phase 3 错误诊断覆盖扩充（第九轮审查新增，第十轮修正）

**问题**：SKILL.md 第 221 行描述"最多 3 次自动修复后重试"，但 `tools/auto_fixer.py:471-476` fix_map 实际处理 4 种错误类型（`rule_parse`/`css`/`url_empty`/`network`），`TypeError` 和 `unknown` 走默认全量修复路径无专门逻辑，覆盖不足。

- 扩充 auto_fixer 错误类型覆盖：从 4 种扩展到 12 种（对齐 error_diagnoser 的 ERROR_PATTERNS）
- 12 种错误类型：rule_empty / relative_url / css_selector_empty / js_error / http_403 / need_login / cf_challenge / field_missing / syntax_error / jar_crash / jar_timeout / behavior_mismatch
- **验证**：auto_fixer 覆盖全部 12 种错误类型，自动修复成功率 > 50%

### REQ-S07: Phase 5 经验写入自动化提升（第九轮审查新增，第十轮修正）

**问题**：SKILL.md 第 309-313 行描述"experience_manager 自动提取经验要素"，但 `legado_client/experience/experience_manager.py` 实际方法为 `search()`/`search_experience()`/`write_pending()`/`write_experience()`，**不存在** `extract()` 和 `write_to_basic_memory()` 方法。文件头注释说明"basic-memory是MCP服务器，Python脚本无法通过subprocess调用"。

- **新增** experience_manager.extract() 方法：自动从调试结果中提取经验要素（网站特征/错误类型/修复方法/规则模式/可信度）
- **新增** experience_manager.write_to_basic_memory() 方法：返回 MCP 调用指令，由 AI agent 执行写入 basic-memory
- 保留现有 search()/write_pending()/write_experience() 方法不变
- 降级路径：MCP 不可用时写入 references/（通过文件写入）
- **验证**：经验写入从全手动改为半自动，AI 仅需确认即可写入

---

## Scenarios

### Scenario 1: RSS sortUrl bug 修复验证

```
给定: 31 个 RSS 源 sortUrl 被错误填充为 JSON 对象
当: 修正生成器字段映射，sortUrl 改为 URL 模板
预期: sortUrl 解析不再报 SelectorParseException
验证: 31 个 RSS 源至少进入 articleList 阶段
```

### Scenario 2: 搜索规则重写验证

```
给定: 23 个 book 源搜索结果为空
当: 用浏览器 F12 检查搜索结果页 HTML，重写选择器
预期: 搜索结果非空
验证: 23 个 book 源搜索阶段通过
```

### Scenario 3: PKIX 证书链修复验证

```
给定: BT之家 SSL 证书链缺失
当: 配置 SSLHelper 信任所有证书
预期: SSL 连接成功
验证: BT之家可访问
```

### Scenario 4: base64 flags 对齐验证

```
给定: 书源使用 base64Decode(str, 2) (NO_WRAP)
当: 完善 flags 映射（源码核实修正：mapBase64Flags 方法不存在，需新建）
预期: 解码结果与真机一致
验证: 编解码结果与 android.util.Base64 一致
```

### Scenario 5: WebView 委托验证

```
给定: 书源需要 webView() 渲染 JS
当: 抛出 WebViewRequiredException 携带请求信息
预期: Python Selenium 执行 JS 渲染并回传结果
验证: 需 WebView 的源可调试
```

### Scenario 6: 硬件信息环境变量验证

```
给定: 书源使用 androidId 作为 AES key
当: 设置 LEGADO_ANDROID_ID 环境变量为真机 androidId
预期: AES 加密解密与真机一致
验证: getLoginInfo/putLoginInfo 结果与真机一致
```

### Scenario 7: 全量回归测试

```
给定: 100 个真实源（修复后）
当: 执行批量测试
预期: 排除网站问题后，真机能运行的源仿真端也能运行
验证: 成功率显著提升（目标：排除网站问题后 100%）
```

### Scenario 8: ruleDescription 逻辑修正验证（P0）

```
给定: RSS 源 ruleDescription 有值，ruleContent 为空
当: 执行 RSS 源调试
预期: 跳过内容页解析，输出"存在描述规则，不解析内容页"
验证: 调试结果与真机 Debug.kt:123-134 行为一致
```

### Scenario 9: CookieManager saveResponse 验证

```
给定: 网站返回 Set-Cookie 响应头
当: 仿真端发送 HTTP 请求获取响应
预期: CookieManager.saveResponse 自动解析并保存 Cookie 到内存 Map
验证: 后续请求自动携带保存的 Cookie，登录态不丢失
```

### Scenario 10: JsExtensions 委托模式并发覆盖验证（P0）

```
给定: 并发调试 2 个不同书源（书源 A 和书源 B）
当: 书源 A 的 JS 规则调用 java.getSource()
预期: 返回书源 A（不是书源 B）
验证: 委托模式改为实例化后，并发调试 source 变量正确指向对应书源
```

### Scenario 11: 预校验拦截无效源

```
给定: AI 生成的 BookSource 缺少 bookSourceUrl 字段
当: debug_runner.run() 被调用
预期: source_validator 校验字段完整性 → 发现 bookSourceUrl 为空
验证: 预校验 < 1 秒，不调用 JAR，错误信息清晰可操作
```

### Scenario 12: 规则语法错误预检查

```
给定: AI 生成的 ruleSearch.name 规则为 @CSS:div.class@tag.name，CSS 语法错误
当: debug_runner.run() 被调用
预期: rule_precheck 校验规则语法 → 发现 CSS 选择器语法错误
验证: 预校验 < 2 秒，错误定位到具体规则字段
```

### Scenario 13: JAR 调试失败 + 自动修复

```
给定: 预校验通过，JAR 调试失败（CSS 选择器未匹配）
当: error_diagnoser 诊断错误 → auto_fixer 自动修复
预期: 重新调用 JAR → 成功
验证: 自动修复成功率 > 50%
```

### Scenario 14: JAR 不可用 + 降级到 Python 模式

```
给定: JAR 进程崩溃或端口占用
当: RuleEngineClient 调用 JAR → 连接失败
预期: 降级到 Python 模式（requests + BeautifulSoup4 执行简化调试）
验证: 降级路径正常工作，结果标注"Python 降级模式，建议用 JAR 复验"
```

### Scenario 15: 需要用户介入（登录场景）

```
给定: 网站需要登录，AI 无法自动完成
当: error_diagnoser 诊断 → 需要登录
预期: obstacle_resolver 尝试自动辅助 → 失败 → user_interaction 生成标准化交互请求
验证: 交互请求包含登录 URL、所需信息、操作指引
```

### Scenario 16: 经验半自动写入

```
给定: 调试成功，发现新的网站特征模式
当: experience_manager 自动提取经验要素
预期: 生成经验 JSON 草稿到 experience/pending/
验证: 经验草稿格式正确，basic-memory 写入成功
```

### Scenario 17: 100% 测试校验准确性评估

```
给定: 所有必需修复完成（52 个 P0+P1+基础对齐）
当: 用 100 个真实源全量测试
预期: 排除网站问题后，JAR 测试通过的源真机也能通过，JAR 测试失败的源能准确区分源规则问题还是仿真端问题
验证: 对于不依赖 WebView/UI/Android 原生的源，达到 100% 测试校验准确性
```
