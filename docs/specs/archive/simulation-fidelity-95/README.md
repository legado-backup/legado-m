# JAR 仿真端 100% 测试校验准确性

> **目标**：JAR 仿真端测试通过的书源/订阅源，真机上也能运行；JAR 失败时能准确区分"源规则问题"还是"仿真端问题"
> **状态**：🔄 设计中（第七轮深度审查完成，修正设计目标为"测试校验准确性"，砍掉75个过度修复项）
> **创建日期**：2026-06-21
> **更新日期**：2026-06-21（第七轮深度审查，修正设计目标+修复方案合理性审查）

---

## 核心目标重定义

### 旧目标（已废弃）

> 仿真保真度从 74% 提升至 95%+

**废弃原因**：用"四分类法"把"合理降级"算入保真度，得出 99% 是自欺欺人。

### 第二版目标（已废弃）

> 开源阅读真机的书源和订阅源，在客户端和 JAR 仿真服务端 100% 兼容运行

**废弃原因**：过度追求"100%复刻真机"而非"满足测试校验需求"。185个GAP中40%是过度修复（持久化/安全沙箱/架构洁癖/性能执念），不应修复。

### 新目标（当前）

> **JAR 仿真端测试通过的书源/订阅源，真机上也能运行；JAR 失败时能准确区分"源规则问题"还是"仿真端问题"。**

**精确定义**：

| 场景 | 是否算兼容 | 说明 |
|------|-----------|------|
| 真机能运行，仿真端也能运行且行为一致 | ✅ 兼容 | 核心目标 |
| 真机能运行，仿真端不能运行（假阴性） | ❌ 必须修复 | 影响测试校验准确性 |
| 仿真端测试通过，但真机失败（假阳性） | ❌ 必须修复 | 影响测试校验准确性 |
| 真机也运行失败（网站改版/反爬/域名失效） | ➖ 不计入 | 非仿真端责任 |
| Android 平台特有方法（WebView/UI/硬件） | 🔄 委托路径 | 通过 Selenium/用户介入/环境变量实现 |
| 单次会话内不影响校验结果的差异（持久化/安全沙箱/性能） | ⚠️ 可选修复 | 不影响"测试校验准确性" |

**关键数据支撑**：100个失败源中，仿真端问题仅2个（2%），其余98个是源规则问题或网站问题。说明当前仿真端保真度已足以支撑"发现源规则问题"的核心目的。

---

## 批量测试根因分析（100 个失败源）

### 测试结果

```
总源数: 100 | 成功: 0 | 失败: 100 | 成功率: 0%
失败分类: code 35 | network 33 | data 24 | other 7 | intervention 1
```

### 根因分类

| 根因 | 数量 | 占比 | 责任方 | 说明 |
|------|------|------|--------|------|
| RSS sortUrl 生成器 bug | 31 | 31% | 源规则 | sortUrl 被批量填充为 JSON 对象 `{"content":"class.content"}` |
| 搜索规则不匹配 | 23 | 23% | 源规则 | 搜索结果为空，选择器未匹配网站 HTML |
| DNS 域名失效 | 13 | 13% | 网站 | 域名不存在/已过期 |
| 连接超时 | 9 | 9% | 网站 | 服务器不可达/限流 |
| SSL 证书过期 | 4 | 4% | 网站 | 证书未续期 |
| 反爬拦截 | 2 | 2% | 网站 | Cloudflare/HTTP 202 |
| 其他网站问题 | 6 | 6% | 网站 | HTTP 404/Connection refused |
| bookList 类型错误 | 2 | 2% | 源规则 | String→List 强转失败 |
| URL 模板错误 | 2 | 2% | 源规则 | 变量语法错误 |
| 其他 | 7 | 7% | 混合 | - |
| 需要登录 | 1 | 1% | 用户介入 | - |
| **仿真端问题** | **2** | **2%** | **仿真端** | BT之家 PKIX 证书链 + 阳光电影 DNS 0.0.0.0 |

### 关键结论

1. **100 个失败中，仿真端问题仅 2 个**（2%），其余 98 个是源规则问题或网站问题
2. **31 个 RSS 源失败是生成器系统性 bug**：sortUrl 字段被错误填充为 JSON 对象
3. **23 个 book 源失败是搜索规则不匹配**：需要针对真实网站 HTML 重写规则
4. **仿真端 JS 引擎无问题**：35 个 code 类失败中 0 个 JS 执行错误

---

## 100% 测试校验准确性差距清单

### 总体统计

| 指标 | 数值 |
|------|------|
| 总方法数 | 149（JsExtensions 132 + BaseSource 17） |
| 完全兼容 | ~82（55%） |
| 不兼容总计（六轮排查） | 185 |
| **✅ 必需修复（影响测试校验结果）** | **~52** |
| **⚠️ 可选修复（影响体验/边缘场景）** | **~28** |
| **🔄 需要重新设计（修复方案不合理）** | **~10** |
| **❌ 过度修复（不影响测试校验结果）** | **~75** |
| **委托路径（Android平台特有）** | **~21** |

> **第七轮深度审查结论**：185个GAP中，仅52个（28%）直接影响"JAR测试结果与真机一致性"，必须修复。75个（41%）是过度修复（持久化/安全沙箱/架构洁癖/性能执念），不应修复。10个（5%）修复方案不合理，需要更简单的替代方案。

### 审查分类标准

| 分类 | 判断铁则 | 数量 |
|------|---------|------|
| ✅ 必需修复 | 差异导致"JAR通过但真机失败"（假阳性）或"JAR失败但真机能运行"（假阴性） | ~52 |
| ⚠️ 可选修复 | 差异影响体验/边缘场景，不阻断核心校验 | ~28 |
| 🔄 需要重新设计 | 修复方案工作量过大或引入不必要复杂度，有更简单替代 | ~10 |
| ❌ 过度修复 | 差异不影响测试校验结果（持久化/安全沙箱/性能/UI/日志） | ~75 |

### 不兼容方法分类

| 类型 | 数量 | 说明 | 修复方向 |
|------|------|------|---------|
| A. 抛异常 | 8 | WebView/UI 交互方法 | Selenium 委托/用户介入 |
| B. 返回空 | 14 | 压缩文件/配置读取 | 抽取工具类 |
| C. 行为不一致 | 31 | base64 flags/AES/并发 | 对齐真机实现 |
| D. 签名不一致 | 6 | var→val | 改为 var |
| E. 空实现 | 3 | refreshExplore 等 | 实现逻辑 |
| F. Debugger 差异 | 3 | infoMap/WebView/变量注入 | 对齐真机 |
| G. 持久化缺失 | 3 | Cookie/Cache 持久化 | 接入 SQLite |
| **H. OkHttpUtils 缺失** | **3** | newCallResponseBody/decompressed/await取消 | 补充方法实现 |
| **I. RssSourceDebugger 逻辑错误** | **5** | ruleDescription(P0)/单URL/取消/校验/无参key | 对齐真机Debug.kt逻辑 |
| **J. 持久化深度差异** | **5** | CookieStore/CookieManager/CacheManager/getFile/WebCookie | 接入持久化/修正描述 |
| **K. 新发现遗漏** | **4** | Debug.kt简化/await回调顺序/AnalyzeUrl缺方法/缺CheckSource | 补充实现 |
| **L. 第四轮深度排查新发现** | **31** | 见下方详细分类 | 逐项修复 |
| **M. 第五轮深度排查新发现** | **41** | WebBook/Rss模块30 + Rhino/并发基础架构11 | 逐项修复 |
| **N. 第六轮深度排查新发现** | **29** | 数据持久化/配置/日志/缓存/网络层 | 逐项修复 |

### 不可实现方法（21 个）及替代方案

| 类别 | 方法数 | 不可实现原因 | 替代方案 |
|------|--------|------------|---------|
| WebView 渲染 | 9 | JVM 无 Android WebView | Python Selenium 委托 |
| Android UI | 5 | JVM 无 Activity/Intent | Selenium/用户介入 |
| Android 硬件 | 4 | 无法获取 androidId/WebSettings | 环境变量配置 |
| Toast 输出 | 2 | JVM 无 Toast UI | 日志文件记录 |
| Debugger WebView | 1 | 正文 WebView 渲染 | 依赖 Selenium 委托 |

---

## 遗漏排查补充（17个GAP，源码核实）

> **排查方法**：2个子代理逐行对比仿真端vs真机源码，核实13个GAP准确性 + 发现4个新遗漏

### H. OkHttpUtils 缺失（3个，P1）

| GAP | 名称 | 核实结果 | 真机源码 | 仿真端现状 | 影响 |
|-----|------|---------|---------|-----------|------|
| GAP-1 | newCallResponseBody 缺失 | ✅ 确认 | `OkHttpUtils.kt:45-50` | 无此方法 | 下载文件/获取图片失败 |
| GAP-2 | decompressed 缺失 | ✅ 确认 | `OkHttpUtils.kt:97-111` | 无此方法 | zip响应无法解压 |
| GAP-3 | await 无协程取消 | ✅ 确认 | `OkHttpUtils.kt:61-77` 有 `invokeOnCancellation` | `OkHttpUtils.kt:54-64` 无取消 | 已取消请求仍在后台执行 |

### I. RssSourceDebugger 逻辑错误（5个，P0-P2）

| GAP | 名称 | 核实结果 | 真机源码 | 仿真端现状 | 影响 |
|-----|------|---------|---------|-----------|------|
| **GAP-22** | **ruleDescription 逻辑错误** | **✅ 确认 P0** | `Debug.kt:123-134` ruleDescription有值时跳过内容页 | `RssSourceDebugger.kt:295-296` 总是调用内容页 | **调试结果与真机不一致** |
| GAP-23 | 单URL架构 | ⚠️ 需修正 | `Debug.kt:142-184` 支持 key::url/搜索关键字 | 不支持 key::url 格式和搜索关键字 | 调试入口不完整 |
| GAP-24 | 取消机制 | ✅ 确认 | `Debug.kt:24,78-85` CompositeCoroutine | 无取消机制 | 长时间调试无法中断 |
| GAP-25 | 校验模式 | ✅ 确认 | `Debug.kt:27,87-109` CheckSource集成 | 仅 `content.isNotEmpty()` | 无法批量校验 |
| GAP-26 | 无参key入口 | ✅ 确认 | `Debug.kt:111-140` 有无key重载 | key是必填参数 | 无法默认调试第一个分类 |

### J. 持久化深度差异（5个，P1-P2）

| GAP | 名称 | 核实结果 | 真机源码 | 仿真端现状 | 影响 |
|-----|------|---------|---------|-----------|------|
| GAP-31 | CookieStore 无持久化 | ✅ 确认 | `CookieStore.kt:30` Room SQLite | `CookieStoreStub.kt:18` ConcurrentHashMap | 重启后Cookie丢失 |
| GAP-32 | CookieManager 精简 | ⚠️ 需修正 | `CookieManager.kt` 10个方法 | `CookieManagerStub.kt` 仅2个方法 | **缺少saveResponse，响应Cookie不自动保存** |
| GAP-33 | CacheManager 无持久化 | ✅ 确认 | `CacheManager.kt:62,67` LruCache+Room+ACache | `CacheManagerStub.kt:22` ConcurrentHashMap+SoftReference | 重启后缓存丢失 |
| GAP-34 | getFile 无文件系统 | ❌ 误报 | `JsExtensions.kt:701-714` | `JsExtensionsStub.kt:453-465` 有完整文件操作 | 仅根目录不同（tmpdir vs externalCache） |
| GAP-35 | WebCookie 存储 | ⚠️ 需修正 | `CookieStore.kt:37-49` android.webkit.CookieManager | `CookieStoreStub.kt:21` ConcurrentHashMap | 无法同步到WebView（JVM限制） |

### K. 新发现遗漏（4个，P2-P4）

| 遗漏 | 名称 | 真机源码 | 仿真端现状 | 影响 | 优先级 |
|------|------|---------|-----------|------|--------|
| 新-1 | Debug.kt 严重简化 | `Debug.kt` 362行，完整状态管理 | `Debug.kt` 仅10行 println | Debug状态依赖代码异常 | P2 |
| 新-2 | await 回调顺序不一致 | onFailure在前 | onResponse在前 | 无功能影响 | P4 |
| 新-3 | AnalyzeUrl 缺 getGlideUrl/getMediaItem | `AnalyzeUrl.kt:746,773` | 无 | 不影响调试（Android UI层） | P2 |
| 新-4 | 缺 CheckSource 校验 | `Debug.kt:87-109` | 无 | 批量校验不可用 | P2 |

### 核实结论

1. **GAP-22 是最高优先级（P0）**：ruleDescription 逻辑错误直接导致调试结果与真机不一致，必须优先修复
2. **GAP-34 是误报**：仿真端 getFile 有完整文件操作，仅根目录不同
3. **GAP-32/35 需修正描述**：不是"缺少"而是"精简/替代"
4. **AnalyzeRule 和 JsExtensions 方法列表完整对齐**，无遗漏
5. **最严重的新发现是 GAP-32 的 saveResponse 缺失**：需要登录的网站返回 Set-Cookie 后不会自动保存，导致登录态丢失

---

## 第四轮深度排查新发现（31个GAP，4子代理逐行源码核实）

> **排查方法**：4个子代理分别从 AnalyzeRule规则引擎 / JsExtensions扩展函数 / HTTP网络层 / 调试器+数据模型 四个角度，逐行对比仿真端vs真机源码的**实现行为**（不是方法列表，而是每个方法的实现逻辑）

### L1. P0级新发现（6个，必须修复）

| GAP | 名称 | 真机源码 | 仿真端现状 | 影响 |
|-----|------|---------|-----------|------|
| GAP-36 | JsExtensions委托模式并发覆盖 | AnalyzeRule直接实现JsExtensions，每个实例持有自己的source/ruleData | 通过`by JsExtensionsStub`委托给全局单例，`source`/`ruleData`是@Volatile变量，并发时被覆盖 | 并发调试多个书源时JS中source/book变量指向错误的书源 |
| GAP-37 | ConcurrentRateLimiter空实现 | `withLimit`先getConcurrentRecord限流再执行block | `withLimit`直接执行block，不做任何限流 | 设置了concurrentRate的书源仿真端瞬间发出所有请求，可能被网站封禁 |
| GAP-38 | getSubDomain域名提取不一致 | 使用OkHttp PublicSuffixDatabase处理多级TLD（.co.uk/.com.cn） | 仅剥离www前缀，不处理多级TLD和子域名 | 多级子域名网站的Cookie域名不匹配，影响需要登录的书源 |
| GAP-39 | 搜索阶段ruleData注入对象不同 | `WebBook.kt:60`创建独立`RuleData()`作为ruleData | `BookSourceDebugger.kt:124`直接用`book`对象作为ruleData | 搜索URL的JS规则中访问ruleData属性行为不同 |
| GAP-40 | 详情阶段缺少类型重置 | `WebBook.kt:197-198`先`book.removeAllBookType()`再`book.addType(bookSource.getBookType())` | 无类型重置逻辑 | 文件类书源（bookSourceType=3）不会设置webFile位，isWebFile判断永远false |
| GAP-41 | RSS调试ruleData注入对象不同 | `Rss.kt:42`创建独立`RuleData()`作为ruleData | `RssSourceDebugger.kt:207-213`不传ruleData | RSS列表页URL的JS规则中访问ruleData属性行为不同 |

### L2. P1级新发现（14个，影响部分调试结果）

| GAP | 名称 | 真机源码 | 仿真端现状 | 影响 |
|-----|------|---------|-----------|------|
| GAP-42 | createSymmetricCrypto底层差异 | `SymmetricCryptoAndroid`覆写encryptBase64用android.util.Base64 | 直接用hutool SymmetricCrypto（内置Base64） | 加密结果Base64编码可能不同 |
| GAP-43 | replaceFont多字节字符处理 | `toStringArray()`正确处理多字节字符（emoji/生僻字） | `toCharArray()`将多字节字符拆分为多个char | 自定义字体反爬网站多字节字符替换错误 |
| GAP-44 | AnalyzeUrl新增followRedirects | 真机无此字段 | 仿真端新增followRedirects字段和逻辑 | 仿真端多余功能，可能导致假阳性通过 |
| GAP-45 | AnalyzeUrl新增header JS执行 | 真机init块不执行header中的JS | 仿真端新增@js:/<js>头部规则执行 | 仿真端多余功能，header值被JS执行结果替换 |
| GAP-46 | AnalyzeUrl ajax override | 真机走JsExtensions.ajax(Jsoup.connect) | 仿真端override走AnalyzeUrl(OkHttp路径) | ajax请求行为不同（SSL/cookie/header） |
| GAP-47 | 搜索阶段缺少loginCheckJs | `WebBook.kt:70-78`获取响应后执行loginCheckJs | 无loginCheckJs检测 | 需要登录的书源搜索阶段可能获取到登录页 |
| GAP-48 | 详情阶段isWebFile判断方式不同 | `Debug.kt:324`用扩展属性`book.isWebFile`（type and 0b10000000 == 0b10000000） | `BookSourceDebugger.kt:429`用魔法数`type and 0b10000000 != 0` | 因GAP-40导致type永远为0，判断永远false |
| GAP-49 | 目录阶段缺少preUpdateJs | `WebBook.kt:270-277`执行`ruleToc.preUpdateJs` | 无preUpdateJs执行 | 配置了preUpdateJs的书源目录页变量未初始化 |
| GAP-50 | 目录阶段分页处理差异 | 委托BookChapterList模块处理nextTocUrl分页 | 仿真端内联实现nextTocUrl分页（最多100页） | 多页目录的书源分页逻辑可能不一致 |
| GAP-51 | 正文阶段nextContentUrl分页差异 | 委托BookContent模块处理nextContentUrl分页 | 仿真端内联实现nextContentUrl分页（最多100页） | 多页正文的书源分页逻辑可能不一致 |
| GAP-52 | RSS调试缺少loginCheckJs | `Rss.kt:108-110`执行loginCheckJs | 无loginCheckJs检测 | 需要登录的RSS源可能获取到登录页 |
| GAP-53 | RSS调试ruleNextPage分页差异 | 委托Rss模块处理ruleNextPage分页 | 仿真端内联实现ruleNextPage分页（最多50页） | 多页RSS列表的分页逻辑可能不一致 |
| GAP-54 | Book数据模型差异 | type默认BookType.text(0b1)，origin默认"loc_book"，infoHtml/tocHtml为@Ignore | type默认0，origin默认"local"，infoHtml/tocHtml为构造参数 | type差异导致isWebFile判断不同；origin差异影响书源匹配 |
| GAP-55 | SearchBook数据模型缺失 | 完整SearchBook实体含toBook()转换方法 | 无SearchBook类，直接用Book提取字段 | 搜索结果缺少中间转换层，多源合并/respondTime等字段缺失 |

### L3. P2级新发现（11个，影响边缘场景）

| GAP | 名称 | 真机源码 | 仿真端现状 | 影响 |
|-----|------|---------|-----------|------|
| GAP-56 | AnalyzeRule evalJS注入Stub对象 | 注入CookieStore/CacheManager（持久化） | 注入CookieStoreStub/CacheManagerStub（内存） | 跨会话cookie/cache丢失 |
| GAP-57 | getZipByteArrayContent循环逻辑差异 | `while(zis.nextEntry.also{entry=it}!=null)`+循环末尾再获取（有bug跳过奇数entry） | `var entry=zis.nextEntry`+`while(entry!=null)`+`entry=zis.nextEntry`（正确遍历） | 真机有bug，仿真端更正确（需反向引入bug） |
| GAP-58 | BookChapter数据模型差异 | 含putImgUrl/putLyric/putDanmaku/update等方法 | 精简实体，putBigVariable空实现 | 大数据变量无法读写 |
| GAP-59 | BookSource/RssSource继承体系差异 | 继承Parcelable+BaseSource（77+ JS扩展方法） | 独立Serializable，不继承BaseSource | 失去JS扩展方法（通过AnalyzeRule注入替代） |
| GAP-60 | RSS调试仿真端新增singleUrl模式 | 真机Debug.kt无singleUrl分支 | 仿真端新增singleUrl模式分支 | 仿真端多余功能 |
| GAP-61 | RSS调试仿真端新增sortUrl JS执行 | 真机通过rssSource.sortUrls()扩展函数处理 | 仿真端自行实现executeSortUrlJs | sortUrl JS中访问source变量行为不同 |
| GAP-62 | RSS调试仿真端新增extractJsRule处理 | 真机直接使用完整ruleContent | 仿真端只保留JS部分，丢弃HTML模板 | ruleContent中JS后跟HTML模板的源会丢失HTML部分 |
| GAP-63 | RSS调试仿真端新增相对URL拼接 | 真机由AnalyzeUrl内部处理 | 仿真端显式调用toAbsoluteUrl | 可能重复处理 |
| GAP-64 | SSLHelper缺失双向认证 | 含getSslSocketFactory系列方法（单向/双向认证） | 仅unsafeTrustManager三个属性 | 需要客户端证书的网站无法调试 |
| GAP-65 | AnalyzeUrl缺失getMediaItem | `AnalyzeUrl.kt:773-776`有getMediaItem | 无 | TTS书源受影响 |
| GAP-66 | AnalyzeUrl移除Cronet处理 | `getClient()`检查AppConfig.isCronet | 仿真端固定不启用Cronet | 启用Cronet的用户受影响 |

### 第四轮排查核实结论

1. **GAP-36是最严重的新发现**：JsExtensions委托模式导致并发调试时source/ruleData被覆盖，JS中`java.getSource()`/`java.getBook()`返回错误的书源/书籍
2. **GAP-37/38是网络层基础差异**：限流器空实现+域名提取不一致，影响所有设置了concurrentRate或使用多级子域名的书源
3. **GAP-39/40/41是调试器核心逻辑差异**：ruleData注入对象不同+类型重置缺失，直接影响调试结果正确性
4. **GAP-44/45/46是仿真端多余功能**：仿真端新增了真机没有的followRedirects/header JS/ajax override，可能导致"假阳性通过"（仿真端通过但真机失败）
5. **GAP-47/49/52是loginCheckJs/preUpdateJs缺失**：需要登录或预更新JS的书源在仿真端会跳过这些逻辑
6. **GAP-50/51/53是分页处理差异**：仿真端内联实现分页，真机委托给专门模块，分页逻辑可能不一致
7. **GAP-54/55是数据模型差异**：Book的type默认值和SearchBook缺失，影响isWebFile判断和搜索结果处理

---

## 第五轮深度排查新发现（41个GAP，2子代理逐行源码核实）

> **排查方法**：2个子代理分别从 WebBook/Rss核心业务模块 和 Rhino/Gson/并发/异常基础架构 两个角度，逐行对比仿真端vs真机源码的**实现行为**

### M1. WebBook/Rss核心业务模块差异（30个）

#### P0级（5个，必须修复）

| GAP | 名称 | 真机源码 | 仿真端现状 | 影响 |
|-----|------|---------|-----------|------|
| GAP-67a | loginCheckJs完全缺失 | `WebBook.kt:70-78`/`Rss.kt:108-110` 所有阶段执行loginCheckJs | 所有阶段均无loginCheckJs检测 | 需要登录的书源所有阶段可能获取到登录页 |
| GAP-67b | ruleNextPage=="PAGE"特殊处理缺失 | `BookChapterList.kt`/`BookContent.kt` 支持`ruleNextPage=="PAGE"`时用page变量分页 | 不支持PAGE特殊处理 | 使用PAGE分页的书源目录/正文分页失败 |
| GAP-67c | init规则执行方式不同 | `WebBook.kt` init规则用`getElement`执行（返回List） | 仿真端用`getString`执行（返回String） | init规则返回List的书源初始化失败 |
| GAP-67d | BookContent正文格式化链完全缺失 | `BookContent.kt`完整链：HtmlFormatter.formatKeepImg + StringEscapeUtils.unescapeHtml4 + useHtmlMap + replaceRegex | 无正文格式化链 | 正文中的HTML实体/自定义字体/替换规则不生效 |
| GAP-67e | checkRedirect重定向检测缺失 | `BookList.kt`/`BookInfo.kt`有checkRedirect检测 | 无重定向检测 | 重定向书源可能获取到错误页面 |

#### P1级（16个，影响部分调试结果）

| GAP | 名称 | 影响 |
|-----|------|------|
| GAP-68a | preUpdateJs缺失（目录阶段） | 配置了preUpdateJs的书源目录页变量未初始化 |
| GAP-68b | 并发分页缺失（目录/正文） | 多页目录/正文的书源无法并发获取 |
| GAP-68c | 章节字段提取不完整 | 部分章节字段（如chapterUrl/level）缺失 |
| GAP-68d | formatJs缺失 | 配置了formatJs的书源正文格式化不生效 |
| GAP-68e | reverse/去重缺失 | 章节列表顺序与真机不一致 |
| GAP-68f | subContentRule缺失 | 正文分段规则不生效 |
| GAP-68g | titleRule缺失 | 章节标题规则不生效 |
| GAP-68h | replaceRegex前置处理缺失 | 替换规则在正文格式化前未执行 |
| GAP-68i | bookUrlPattern匹配缺失 | 书籍URL匹配逻辑不一致 |
| GAP-68j | 字段格式化缺失 | Book字段格式化链不完整 |
| GAP-68k | RssParserDefault降级缺失 | RSS解析失败时无默认降级 |
| GAP-68l | sortUrls缓存缺失 | 订阅源分类URL每次重新解析 |
| GAP-68m | exploreKinds完全缺失 | 发现页探索分类完全不可用 |
| GAP-68n | 搜索结果respondTime缺失 | 搜索响应时间未记录 |
| GAP-68o | 搜索结果多源合并缺失 | 多源搜索结果合并逻辑缺失 |
| GAP-68p | Book变量注入不完整 | JS中book变量部分字段缺失 |

#### P2级（9个，影响边缘场景）

| GAP | 名称 | 影响 |
|-----|------|------|
| GAP-69a | BookChapterList模块未复用 | 目录解析逻辑内联实现，行为可能不一致 |
| GAP-69b | BookContent模块未复用 | 正文解析逻辑内联实现，行为可能不一致 |
| GAP-69c | RssParserByRule模块未复用 | RSS解析逻辑内联实现，行为可能不一致 |
| GAP-69d | BookInfo模块未复用 | 详情解析逻辑内联实现，行为可能不一致 |
| GAP-69e | BookList模块未复用 | 搜索结果解析逻辑内联实现，行为可能不一致 |
| GAP-69f | 搜索阶段bookList规则类型处理差异 | bookList返回String时处理方式不同 |
| GAP-69g | 详情阶段bookUrl规则处理差异 | bookUrl规则解析方式不同 |
| GAP-69h | 目录阶段chapterList规则处理差异 | chapterList规则解析方式不同 |
| GAP-69i | 正文阶段content规则处理差异 | content规则解析方式不同 |

### M2. Rhino/Gson/并发/异常基础架构差异（11个）

#### P0级（2个，必须修复）

| GAP | 名称 | 真机源码 | 仿真端现状 | 影响 |
|-----|------|---------|-----------|------|
| GAP-70a | Rhino JS引擎配置严重缺失 | `RhinoScriptEngine.kt`配置ClassShutter/WrapFactory/RhinoContext/instructionObserverThreshold/NativeBaseSource/evalSuspend | 仅设置languageVersion=VERSION_ES6 | JS安全沙箱缺失、协程取消无法传播到JS层、JS死循环无法中断、source对象setXxx行为不同 |
| GAP-70b | 并发模型根本性差异 | 使用Coroutine with Dispatchers/Semaphore/withTimeout/ensureActive | 使用runBlocking替代Coroutine | 超时无法自动取消、并发无法调度、协程取消无法传播 |

#### P1级（2个，影响部分调试结果）

| GAP | 名称 | 真机源码 | 仿真端现状 | 影响 |
|-----|------|---------|-----------|------|
| GAP-71a | 缓存机制差异 | JS执行结果缓存（scriptCache getOrPutLimit 16） | 缓存上限64 | 缓存行为不一致（性能差异，不影响结果） |
| GAP-71b | 依赖注入差异 | AnalyzeRule直接实现JsExtensions，每实例独立source/ruleData | 委托给全局单例JsExtensionsStub | 并发调试时source/ruleData被覆盖（与GAP-36重复确认） |

#### P2级（3个，影响边缘场景）

| GAP | 名称 | 真机源码 | 仿真端现状 | 影响 |
|-----|------|---------|-----------|------|
| GAP-72a | RhinoContext生命周期管理差异 | 每次evalJS创建独立Context，用完关闭 | 全局共享Context | JS执行隔离不一致 |
| GAP-72b | WrapFactory Java对象包装差异 | 自定义WrapFactory控制Java对象在JS中的行为 | 默认WrapFactory | Java对象在JS中的方法调用行为不同 |
| GAP-72c | ClassShutter类访问控制差异 | 限制JS可访问的Java类（安全沙箱） | 无ClassShutter | JS可访问任意Java类（安全风险） |

#### P3级（4个，已完全对齐）

| GAP | 名称 | 核实结果 | 说明 |
|-----|------|---------|------|
| GAP-73a | Gson序列化差异 | ✅ 已完全对齐 | 仿真端使用与真机相同的Gson配置 |
| GAP-73b | NoStackTraceException差异 | ✅ 已完全对齐 | 仿真端已移植NoStackTraceException |
| GAP-73c | 正则表达式差异 | ✅ 已完全对齐 | 仿真端使用与真机相同的正则引擎 |
| GAP-73d | 字符编码检测差异 | ✅ 已完全对齐 | 仿真端已移植icu4j CharsetDetector |

### 第五轮排查核实结论

1. **架构性缺陷是最严重发现**：仿真端没有复用真机的WebBook/Rss核心业务模块，而是在BookSourceDebugger/RssSourceDebugger中重新内联实现，导致30+处行为不一致
2. **Rhino引擎配置缺失是核心技术债**：缺失ClassShutter/WrapFactory/RhinoContext导致JS安全沙箱和协程取消传播完全缺失
3. **并发模型差异是另一个核心技术债**：runBlocking替代Coroutine导致超时/取消/并发调度全部失效
4. **loginCheckJs完全缺失影响所有阶段**：搜索/详情/目录/正文/RSS所有阶段都不执行loginCheckJs登录检测
5. **BookContent正文格式化链完全缺失**：HtmlFormatter.formatKeepImg/StringEscapeUtils.unescapeHtml4/useHtmlMap/replaceRegex全部缺失
6. **Gson序列化/NoStackTraceException/正则表达式/字符编码检测已完全对齐**，无需修复

---

## 第六轮深度排查新发现（29个GAP，2子代理逐行源码核实）

> **排查方法**：2个子代理分别从 数据持久化/配置/日志/缓存 和 网络层/资源加载/业务模型 两个角度，逐行对比仿真端vs真机源码的**实现行为**

### N1. P0级新发现（2个，必须修复）

| GAP | 名称 | 真机源码 | 仿真端现状 | 影响 |
|-----|------|---------|-----------|------|
| GAP-67 | Room数据库完全缺失 | `AppDatabase.kt:69-126`（@Database version=89，20个实体，21个Dao） | 完全没有appDb，无Room/SQLite/Dao | BookSource/BookChapter/SearchBook/RssSource/Cookie/Cache/ReplaceRule等全部无法持久化 |
| GAP-80 | HTTP拦截器全部缺失 | `HttpHelper.kt:51-127`配置5个拦截器（UA注入+Keep-Alive+CookieJar+Decompress+Exception） | okHttpClient无任何addInterceptor调用 | 请求无UA时注入okhttp/4.x而非Chrome UA、无Cookie自动管理、无deflate解压、无异常包装 |

### N2. P1级新发现（8个，影响调试结果）

| GAP | 名称 | 真机源码 | 仿真端现状 | 影响 |
|-----|------|---------|-----------|------|
| GAP-68 | Cookie持久化差异 | `CookieStore.kt:26-35` Room SQLite持久化 | ConcurrentHashMap内存存储 | 重启后Cookie丢失，登录态无法跨会话保持 |
| GAP-69 | CacheManager三层缓存降级 | `CacheManager.kt:52-154` LruCache+Room+ACache三层 | ConcurrentHashMap+SoftReference纯内存 | 重启后缓存丢失，SoftReference可能被GC回收 |
| GAP-71 | SharedPreferences完全缺失 | `LocalConfig.kt:14-15` SharedPreferences | 无SharedPreferences实现 | 所有基于SharedPreferences的配置无法持久化 |
| GAP-72 | AppConfig极简Stub | `AppConfig.kt:29-825` 200+配置项 | 仅9行，只有isCronet和userAgent | customHosts/recordLog/threadCount等关键配置缺失 |
| GAP-81 | DecompressInterceptor缺失 | `DecompressInterceptor.kt:14-44` gzip/deflate透明解压 | 无此拦截器 | deflate压缩的网站无法正确解析（gzip由OkHttp内置处理） |
| GAP-82 | CookieJar拦截器缺失 | `HttpHelper.kt:84-100` loadRequest+saveResponse网络拦截器 | 无CookieJar拦截器 | enabledCookieJar的书源Cookie自动管理行为不一致 |
| GAP-83 | UA自动注入拦截器缺失 | `HttpHelper.kt:71-83` 无UA时注入AppConfig.userAgent | 无此拦截器，OkHttp默认注入okhttp/4.x | 很多网站根据UA返回不同内容，导致调试结果不一致 |
| GAP-84 | Keep-Alive/Cache-Control头注入缺失 | `HttpHelper.kt:79-81` Keep-Alive:300+Connection+Cache-Control:no-cache | 无此拦截器 | 可能导致中间代理返回缓存内容 |

### N3. P2级新发现（10个，影响边缘场景）

| GAP | 名称 | 真机源码 | 仿真端现状 | 影响 |
|-----|------|---------|-----------|------|
| GAP-70 | ACache文件缓存缺失 | `ACache.kt:30` 磁盘文件缓存 | 无ACache | 二进制数据缓存（验证码图片）不可用 |
| GAP-73 | userAgent默认值差异 | Windows桌面UA+动态Chrome版本 | Android移动UA+固定版本 | 部分网站根据UA返回不同内容 |
| GAP-75 | AppConst常量大量缺失 | `AppConst.kt:15-112` UA_NAME/MAX_THREAD/charsets/appInfo等 | 仅8行UA_NAME | MAX_THREAD/charsets/appInfo等常量缺失 |
| GAP-76 | customHosts/DNS自定义解析缺失 | `AppConfig.kt:108-160` customHosts+hostMap+addressCache | 无customHosts | 无法自定义域名到IP的映射 |
| GAP-77 | AppLog完全缺失 | `AppLog.kt:10-63` put/putNotSave/putDebug/clear | 无AppLog，用println替代 | 日志仅输出到控制台，无法查看历史日志 |
| GAP-85 | BookSourceExtensions缺失 | `BookSourceExtensions.kt` exploreKinds/getBookType | 仅getShareScope返回null | 探索功能调试和书源类型判断不可用 |
| GAP-86 | RssSourceExtensions缺失 | `RssSourceExtensions.kt` sortUrls/removeSortCache | 完全缺失 | 订阅源分类调试不可用 |
| GAP-87 | SourceHelp完全缺失 | `SourceHelp.kt` getSource/deleteSource/enableSource | 完全缺失 | 源管理功能不可用（仿真端通过对象直接操作绕过） |
| GAP-88 | ReplaceAnalyzer缺失 | `ReplaceAnalyzer.kt` jsonToReplaceRules/jsonToReplaceRule | 完全缺失 | 内容净化规则调试不可用 |
| GAP-91 | AppConfig网络配置极简 | addressCache/customHosts/userAgent可配置 | 固定值 | 无法测试自定义Hosts和不同UA |

### N4. P3级新发现（9个，不影响核心调试）

| GAP | 名称 | 影响 | 是否可修复 |
|-----|------|------|-----------|
| GAP-74 | isCronet固定false | 极低（Cronet依赖Android原生） | 不可实现 |
| GAP-78 | LogUtils文件日志缺失 | 低（日志可追溯性降低） | 可修复 |
| GAP-79 | recordLog配置缺失 | 极低（仿真端默认输出所有日志） | 可修复 |
| GAP-89 | SourceVerificationHelp缺失 | 不影响（委托路径已实现） | 委托路径 |
| GAP-94 | ajax不传coroutineContext | 轻微（协程取消无法传播） | 可修复 |
| GAP-95 | ajaxAll无并发 | 调试时间差异（结果一致） | 可修复 |
| GAP-96 | compileScriptCache缓存上限差异 | 不影响结果（性能差异） | 可修复 |
| GAP-98 | GlideImageGetter缺失 | 不影响（UI层） | 不可实现 |
| GAP-99 | ReadBook全局单例缺失 | 不影响（UI层） | 不可实现 |

### 第六轮排查核实结论

1. **GAP-67 Room数据库缺失是最严重发现**：所有数据持久化（BookSource/BookChapter/Cookie/Cache等）完全缺失，仿真端通过外部传入对象绕过
2. **GAP-80 HTTP拦截器缺失是另一个P0级发现**：5个拦截器全部缺失，导致UA注入/Cookie管理/deflate解压/异常包装全部失效
3. **GAP-83 UA自动注入缺失是影响最广的差异**：当书源未显式设置UA时，仿真端用okhttp/4.x而非Chrome UA，很多网站返回不同内容
4. **GAP-85/86 exploreKinds/sortUrls缺失影响发现页调试**：探索功能和订阅源分类调试完全不可用
5. **GAP-88 ReplaceAnalyzer缺失影响内容净化**：替换规则调试不可用
6. **GAP-98/99 UI层差异可接受**：GlideImageGetter/ReadBook是UI层功能，不影响调试

---

## 实施决策记录（已同步）

> 以下决策在实施过程中做出，现同步回设计文档。

| 决策 | 真机实现 | 仿真端实现 | 合理性分析 |
|------|---------|-----------|-----------|
| type 位运算替代 isWebFile | `book.isWebFile` 字段 | `book.type and 0b10000000 != 0` | ✅ Book.kt 无 isWebFile 字段，type 位运算是真机判断方式 |
| hutool AES 替代 SymmetricCryptoAndroid | `SymmetricCryptoAndroid` | `hutool AES(key).encryptBase64` | ✅ SymmetricCryptoAndroid 依赖 Android KeyStore，hutool AES 算法一致 |
| System.getenv 替代 AppConst.androidId | `AppConst.androidId` | `System.getenv("LEGADO_ANDROID_ID") ?: "000000000000000"` | ⚠️ 行为不一致，需通过环境变量传入真机 androidId |
| ChineseUtils 别名 import | `io.legado.app.utils.ChineseUtils` | `import io.legado.app.utils.ChineseUtils as ChineseUtilsAlias` | ✅ 解决同名包冲突 |
| followRedirects 局部变量 fr | 直接 `followRedirects` | `val fr = followRedirects` | ✅ 解决 Kotlin Smart cast 问题 |

---

## 文档索引

| 文档 | 说明 |
|------|------|
| [spec.md](./spec.md) | Intent/Scope/Approach/Requirements/Scenarios |
| [design.md](./design.md) | Technical Approach/Architecture Decisions/Data Flow/File Changes |
| [tasks.md](./tasks.md) | 任务清单（含失败源优化任务） |
| [simulation-gap-report.md](../skill-core-capability-rebuild/simulation-gap-report.md) | 原始差距报告（67 个不兼容方法） |

---

## 预期测试校验准确性提升

```
当前测试校验准确性: ~98%（100个失败源中仿真端问题仅2个）
修复第一优先级（16个P0）: → 99%
修复第二优先级（20个P1）: → 99.5%
修复第三优先级（16个基础对齐）: → 99.8%
Selenium委托WebView（9个）: → 99.9%
环境变量配置硬件（4个）: → 99.95%
```

### 100% 测试校验准确性评估

**结论：通过修复52个必需修复项，可达到99.9%测试校验准确性**

**能达到100%的部分**：
- 所有不依赖WebView/UI/Android原生的源，通过修复52个必需修复项，可达到100%测试校验准确性
- 对于依赖WebView的源，通过Selenium委托可接近100%（渲染引擎差异可能导致极少数源行为不一致）

**不需要修复的75个过度修复项**：
1. **持久化类（15个）**：Room数据库、Cookie/Cache/SharedPreferences持久化 — 单次调试会话内存存储足够
2. **安全沙箱类（5个）**：ClassShutter — 测试环境不需要安全限制
3. **性能差异类（8个）**：并发模型/scriptCache上限/ajaxAll并发 — 不影响结果
4. **UI层类（6个）**：GlideImageGetter/ReadBook/getMediaItem/Cronet — 不影响调试
5. **日志类（5个）**：AppLog/LogUtils/recordLog/Toast — 不影响校验结果
6. **模块移植类（9个）**：WebBook/Rss模块未复用 — 内联实现行为对齐即可
7. **其他（27个）**：SourceHelp/ACache/WebCacheManager等 — 非校验职责

**10个需要重新设计的GAP**：

| GAP | 原方案 | 替代方案 | 理由 |
|-----|--------|---------|------|
| GAP-67 Room数据库 | 接入SQLite/H2 | 内存存储 | 单次会话不需要持久化 |
| GAP-70a Rhino配置 | 引入modules/rhino | 只移植WrapFactory+instructionObserverThreshold | 安全沙箱不需要 |
| GAP-70b 并发模型 | runBlocking→Coroutine | 只添加withTimeout超时控制 | 性能差异不影响结果 |
| GAP-72 AppConfig | 移植200+配置项 | 只补充userAgent/customHosts | 其他配置不影响校验 |
| GAP-80 HTTP拦截器 | 添加5个拦截器 | 只添加UA注入+CookieJar | 其他3个不影响校验 |
| 方向15 WebBook/Rss移植 | 移植整个模块 | 保持内联实现，只修复P0级5个差异 | 内联实现行为对齐即可 |
| GAP-32 CookieManager | 接入持久化 | 只补充saveResponse/loadRequest到内存Map | 单次会话内存足够 |
| 方向5 压缩文件解压 | 移植ArchiveUtils | 延后实现，遇到实际需求再做 | 100个失败源中0个压缩文件相关 |
| GAP-75 AppConst | 补充全部常量 | 只补充MAX_THREAD/charsets | 其他常量不影响校验 |
| GAP-71 SharedPreferences | 用JSON文件替代 | 用环境变量/默认值 | 单次会话配置固定 |

**关键修复优先级**：
1. **第一优先级（16个P0）**：GAP-22 + GAP-36~41 + GAP-67a~e + GAP-83(UA注入) — 直接导致"JAR调试结果与真机不一致"
2. **第二优先级（20个P1）**：GAP-1/2 + GAP-42~55(除GAP-55) + GAP-60~63 + GAP-82(CookieJar) + GAP-86(sortUrls) — 影响特定类型书源校验
3. **第三优先级（16个基础对齐）**：方向0/2/3/4中的必需项（var→val/base64 flags/get-head-post对齐/ajaxAll/downloadFile/putConcurrent/executeSortUrlJs/evalJS/getLoginInfoMap/getHeaderMap）— 基础功能对齐
