# JS 扩展函数参考 — 速查索引

> 本目录是 js-extensions.md 的拆分版。按函数名或功能类别定位子文档。

## ⚠️ 创建新子文档前必须检查

1. 新内容是否可以归入已有子文档？→ 优先追加到已有子文档
2. 新内容与已有子文档的边界是否清晰？→ 如果重叠，应该扩展已有子文档的覆盖范围
3. 新子文档的预估内容是否 > 100行？→ 太小的内容不值得独立成文档
4. 创建后是否需要更新本索引的边界规则？→ 是则必须同步更新

## 速查表

### network.md
> **一句话描述**：HTTP网络请求相关函数（ajax/connect/get/post等）

- ✅ 包含：ajax, ajaxAll, ajaxTestAll, connect, get, head, post — 所有发起HTTP请求的函数
- ❌ 不包含：WebView加载页面（→ webview.md）、Cookie操作（→ cookie-cache.md）
- **触发关键词**：ajax, HTTP, GET, POST, 请求, 网络请求, connect, fetch, 并发请求
- **自进化写入规则**：当发现新的网络请求函数或现有函数的新用法时追加

### webview.md
> **一句话描述**：WebView浏览器操作函数（加载页面/获取源码/浏览器交互）

- ✅ 包含：webView, webViewGetSource, webViewGetOverrideUrl, startBrowser, startBrowserAwait, getVerificationCode
- ❌ 不包含：普通HTTP请求（→ network.md）、UI跳转（→ ui-interaction.md）
- **触发关键词**：webView, 浏览器, 渲染, JS执行, 验证码, sourceRegex, 跳转拦截
- **自进化写入规则**：当发现WebView函数的新用法或新的浏览器交互模式时追加

### rule-parsing.md
> **一句话描述**：AnalyzeRule规则解析函数（用规则提取文本/元素）

- ✅ 包含：setContent, getString, getStringList, getElement, getElements, setBaseUrl, setRedirectUrl
- ❌ 不包含：规则语法说明（→ ../rule-syntax.md）、JS模式技巧（→ ../js-patterns/）
- **触发关键词**：AnalyzeRule, getString, getElement, 规则解析, 内容提取, 选择器执行
- **自进化写入规则**：当发现规则解析函数的新用法或参数组合时追加

### crypto-encoding.md
> **一句话描述**：加密解密和编码解码函数（AES/MD5/Base64/HMAC等）

- ✅ 包含：MD5, 摘要算法, HMAC, createSymmetricCrypto, createAsymmetricCrypto, createSign, 旧版AES/DES, Base64, Hex, 字符串字节互转, URI编码
- ❌ 不包含：加密陷阱和错误用法（→ ../troubleshooting/crypto-traps.md）、加密场景方案（→ ../special-scenarios/encryption.md）
- **触发关键词**：加密, 解密, AES, DES, MD5, HMAC, Base64, Hex, 签名, 对称, 非对称, 编码, 解码, createSymmetricCrypto
- **自进化写入规则**：当发现加密/编码函数的新用法或新参数时追加

### cookie-cache.md
> **一句话描述**：Cookie和缓存操作函数（Cookie管理/CacheManager/变量存取）

- ✅ 包含：Cookie操作（getCookie/setCookie/removeCookie）, CacheManager（getCache/putCache）, 变量存取（put/get）
- ❌ 不包含：HTTP请求中的Cookie传递（→ network.md）、文件缓存（→ file-operations.md）
- **触发关键词**：Cookie, 缓存, Cache, put, get, 变量, 登录状态, 会话
- **自进化写入规则**：当发现Cookie/缓存函数的新用法或新的状态管理模式时追加

### file-operations.md
> **一句话描述**：文件读写和压缩解压函数

- ✅ 包含：读取文件, 缓存与下载, 导入脚本, 删除文件, 压缩解压, 读取文件夹, 获取压缩包内容
- ❌ 不包含：缓存管理（→ cookie-cache.md）、网络下载（→ network.md）
- **触发关键词**：文件, 读取, 写入, 下载, 压缩, 解压, zip, 脚本导入, deleteFile
- **自进化写入规则**：当发现文件操作函数的新用法或新的文件处理模式时追加

### font-anti-crawl.md
> **一句话描述**：字体反反爬解析函数（queryTTF/replaceFont）

- ✅ 包含：queryTTF, replaceFont, queryBase64TTF — 字体映射解析和替换
- ❌ 不包含：其他反爬方法（→ ../troubleshooting/html-fetch-traps.md）
- **触发关键词**：字体, TTF, 反反爬, 字体映射, replaceFont, queryTTF, 自定义字体
- **自进化写入规则**：当发现字体解析函数的新用法或新的字体反爬模式时追加

### ui-interaction.md
> **一句话描述**：UI交互函数（打开播放器/跳转/弹窗/搜索/添加书架）

- ✅ 包含：openVideoPlayer, openUrl, toast, longToast, searchBook, addBook, showPhoto, open
- ❌ 不包含：WebView交互（→ webview.md）、文件操作（→ file-operations.md）
- **触发关键词**：播放器, 跳转, 弹窗, toast, 搜索, 书架, 图片显示, UI, 界面
- **自进化写入规则**：当发现UI交互函数的新用法或新的交互模式时追加

### utils.md
> **一句话描述**：工具方法函数（日志/时间/UUID/UA/繁简转换等）

- ✅ 包含：log, timeFormat, timeFormatUTC, randomUUID, androidId, getWebViewUA, htmlFormat, t2s, s2t, toNumChapter, toURL, encodeURI, getReadBookConfig, getThemeMode, getThemeConfig
- ❌ 不包含：网络请求（→ network.md）、加密编码（→ crypto-encoding.md）
- **触发关键词**：日志, 时间, UUID, UA, 繁简, 转换, URL构造, 编码, 配置获取
- **自进化写入规则**：当发现工具函数的新用法或新参数时追加

### global-objects.md
> **一句话描述**：JS 全局对象 API 参考（book/chapter/source/cookie/cache 对象及全局变量）

- ✅ 包含：book, chapter, source, cookie, cache 对象的方法和属性，全局变量（result/src/baseUrl/key/page/title/nextChapterUrl）
- ❌ 不包含：JsExtensions 方法（→ 各专题子文档）、规则语法（→ ../rule-syntax.md）
- **触发关键词**：全局对象, book, chapter, source, cookie, cache, 全局变量, result, baseUrl, JS绑定对象
- **自进化写入规则**：当发现全局对象的新方法/属性或新的全局变量时追加

### advanced.md
> **一句话描述**：高级扩展（替换净化JS/WebJs注入/全局变量/约束/不存在函数）

- ✅ 包含：RegexJsExtensions（替换净化规则中的JS扩展）, WebJsExtensions（WebView注入环境）, 全局上下文变量, 重要约束, 不存在的函数
- ❌ 不包含：基础JS函数（各专题子文档）
- **触发关键词**：替换净化, WebJs, 注入, 全局变量, 约束, 不存在, 已删除, deprecated
- **自进化写入规则**：当发现高级扩展的新用法或新的约束条件时追加
