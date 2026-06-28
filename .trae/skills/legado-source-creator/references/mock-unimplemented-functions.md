# JsExtensionsStub 未实现函数速查表

> **用途**：当 JVM 仿真器测试报错 `TypeError: java.xxx is not a function` 时，AI 可查阅本表判断该函数的影响级别和建议处理方式。
>
> **数据来源**：对比 `app/src/main/java/io/legado/app/help/JsExtensions.kt` + `JsEncodeUtils.kt`（共 ~130 个函数签名）与 `tools/legado-jvm/src/main/kotlin/io/legado/app/help/JsExtensionsStub.kt`（已实现 132 个函数签名：86 完整 + 38 Stub 降级 + 8 不可用）。
>
> **统计**：未实现函数 96 个（含已废弃但 web 仍调用的旧函数）。
>
> **影响级别判断标准**：
> - **高**：书源/订阅源中常用，缺失会导致规则执行失败
> - **中**：特定场景使用，有替代方案
> - **低**：极少使用或已废弃
>
> **建议处理方式**：
> - **标记需真机**：依赖 Android 原生 API 或 WebView，无法在 JVM 仿真器中实现，必须在 Legado 真机测试
> - **降级 Python 仿真**：可用 Python 标准库实现的函数
> - **可补全实现**：可在 JsExtensionsStub.kt 中补全实现并重建 JAR

---

## 1. 网络类（20 个）

| # | 函数签名 | 影响级别 | 建议处理方式 | 说明 |
|---|----------|---------|-------------|------|
| 1 | `fun ajaxAll(urlList: Array<String>, skipRateLimit: Boolean): Array<StrResponse>` | 中 | 可补全实现 | skipRateLimit 参数未实现，串行执行已有 |
| 2 | `fun ajaxTestAll(urlList: Array<String>, timeout: Int): Array<StrResponse>` | 低 | 可补全实现 | 并发测试网络，极少使用 |
| 3 | `fun ajaxTestAll(urlList: Array<String>, timeout: Int, skipRateLimit: Boolean): Array<StrResponse>` | 低 | 可补全实现 | 同上重载 |
| 4 | `fun webView(html: String?, url: String?, js: String?, cacheFirst: Boolean): String?` | 高 | 标记需真机 | WebView 渲染，CF 盾/PJAX 站必需 |
| 5 | `fun webViewGetSource(html: String?, url: String?, js: String?, sourceRegex: String): String?` | 高 | 标记需真机 | WebView 获取资源 URL |
| 6 | `fun webViewGetSource(html: String?, url: String?, js: String?, sourceRegex: String, cacheFirst: Boolean): String?` | 高 | 标记需真机 | 同上重载 |
| 7 | `fun webViewGetSource(html: String?, url: String?, js: String?, sourceRegex: String, cacheFirst: Boolean, delayTime: Long): String?` | 高 | 标记需真机 | 同上重载 |
| 8 | `fun webViewGetOverrideUrl(html: String?, url: String?, js: String?, overrideUrlRegex: String): String?` | 高 | 标记需真机 | WebView 获取跳转 URL |
| 9 | `fun webViewGetOverrideUrl(html: String?, url: String?, js: String?, overrideUrlRegex: String, cacheFirst: Boolean): String?` | 高 | 标记需真机 | 同上重载 |
| 10 | `fun webViewGetOverrideUrl(html: String?, url: String?, js: String?, overrideUrlRegex: String, cacheFirst: Boolean, delayTime: Long): String?` | 高 | 标记需真机 | 同上重载 |
| 11 | `fun openVideoPlayer(url: String, title: String)` | 中 | 标记需真机 | 打开内置视频播放器，依赖 Android UI |
| 12 | `fun openVideoPlayer(url: String, title: String, isFloat: Boolean)` | 中 | 标记需真机 | 同上重载 |
| 13 | `fun startBrowser(url: String, title: String)` | 中 | 标记需真机 | 内置浏览器打开链接，依赖 Android UI |
| 14 | `fun startBrowser(url: String, title: String, html: String?)` | 中 | 标记需真机 | 同上重载 |
| 15 | `fun startBrowserAwait(url: String, title: String, refetchAfterSuccess: Boolean): StrResponse` | 高 | 标记需真机 | CF Turnstile/交互式验证码必需 |
| 16 | `fun startBrowserAwait(url: String, title: String, refetchAfterSuccess: Boolean, html: String?): StrResponse` | 高 | 标记需真机 | 同上重载 |
| 17 | `fun getVerificationCode(imageUrl: String): String` | 高 | 标记需真机 | 图片验证码输入，依赖 Android UI |
| 18 | `fun get(urlStr: String, headers: Map<String, String>, timeout: Int?): Connection.Response` | 中 | 可补全实现 | get 的 timeout 重载，jsoup 已支持 |
| 19 | `fun head(urlStr: String, headers: Map<String, String>, timeout: Int?): Connection.Response` | 中 | 可补全实现 | head 的 timeout 重载 |
| 20 | `fun post(urlStr: String, body: String, headers: Map<String, String>, timeout: Int?): Connection.Response` | 中 | 可补全实现 | post 的 timeout 重载 |

---

## 2. 文件操作类（9 个）

| # | 函数签名 | 影响级别 | 建议处理方式 | 说明 |
|---|----------|---------|-------------|------|
| 21 | `fun getFile(path: String): File` | 中 | 降级 Python 仿真 | 返回 java.io.File，可用临时目录模拟 |
| 22 | `fun readFile(path: String): ByteArray?` | 中 | 降级 Python 仿真 | 读取文件为 ByteArray |
| 23 | `fun readTxtFile(path: String): String` | 高 | 降级 Python 仿真 | 读取文本文件，importScript 依赖此函数 |
| 24 | `fun readTxtFile(path: String, charsetName: String): String` | 中 | 降级 Python 仿真 | 同上重载，指定编码 |
| 25 | `fun deleteFile(path: String): Boolean` | 低 | 降级 Python 仿真 | 删除文件 |
| 26 | `fun getTxtInFolder(path: String): String` | 低 | 降级 Python 仿真 | 读取文件夹内所有文本文件 |
| 27 | `fun importScript(path: String): String` | 高 | 降级 Python 仿真 | 导入 JS 脚本，依赖 cacheFile/readTxtFile |
| 28 | `fun downloadFile(url: String): String` | 中 | 降级 Python 仿真 | 下载文件到缓存目录 |
| 29 | `fun downloadFile(content: String, url: String): String` | 低 | 降级 Python 仿真 | 已废弃，16进制转文件 |

---

## 3. 编码/解码类（5 个）

| # | 函数签名 | 影响级别 | 建议处理方式 | 说明 |
|---|----------|---------|-------------|------|
| 30 | `fun strToBytes(str: String): ByteArray` | 中 | 可补全实现 | 无 charset 重载，默认 UTF-8 |
| 31 | `fun bytesToStr(bytes: ByteArray): String` | 中 | 可补全实现 | 无 charset 重载，默认 UTF-8 |
| 32 | `fun base64Decode(str: String, flags: Int): String` | 中 | 可补全实现 | flags 参数（Android Base64 标志位） |
| 33 | `fun base64DecodeToByteArray(str: String?, flags: Int): ByteArray?` | 中 | 可补全实现 | flags 参数重载 |
| 34 | `fun encodeURI(str: String, enc: String): String` | 低 | 可补全实现 | 指定编码的 encodeURI |

---

## 4. 压缩类（13 个）

| # | 函数签名 | 影响级别 | 建议处理方式 | 说明 |
|---|----------|---------|-------------|------|
| 35 | `fun unzipFile(zipPath: String): String` | 中 | 降级 Python 仿真 | Zip 解压，Python zipfile 可实现 |
| 36 | `fun un7zFile(zipPath: String): String` | 低 | 降级 Python 仿真 | 7z 解压，py7zr 可实现 |
| 37 | `fun unrarFile(zipPath: String): String` | 低 | 降级 Python 仿真 | Rar 解压，rarfile 可实现 |
| 38 | `fun unArchiveFile(zipPath: String): String` | 中 | 降级 Python 仿真 | 通用解压（自动判断格式） |
| 39 | `fun getZipStringContent(url: String, path: String): String` | 中 | 降级 Python 仿真 | 从 Zip 中读取指定文件内容 |
| 40 | `fun getZipStringContent(url: String, path: String, charsetName: String): String` | 中 | 降级 Python 仿真 | 同上重载 |
| 41 | `fun getRarStringContent(url: String, path: String): String` | 低 | 降级 Python 仿真 | 从 Rar 中读取指定文件内容 |
| 42 | `fun getRarStringContent(url: String, path: String, charsetName: String): String` | 低 | 降级 Python 仿真 | 同上重载 |
| 43 | `fun get7zStringContent(url: String, path: String): String` | 低 | 降级 Python 仿真 | 从 7z 中读取指定文件内容 |
| 44 | `fun get7zStringContent(url: String, path: String, charsetName: String): String` | 低 | 降级 Python 仿真 | 同上重载 |
| 45 | `fun getZipByteArrayContent(url: String, path: String): ByteArray?` | 中 | 降级 Python 仿真 | 从 Zip 中读取 ByteArray |
| 46 | `fun getRarByteArrayContent(url: String, path: String): ByteArray?` | 低 | 降级 Python 仿真 | 从 Rar 中读取 ByteArray |
| 47 | `fun get7zByteArrayContent(url: String, path: String): ByteArray?` | 低 | 降级 Python 仿真 | 从 7z 中读取 ByteArray |

---

## 5. 字体类（5 个）

| # | 函数签名 | 影响级别 | 建议处理方式 | 说明 |
|---|----------|---------|-------------|------|
| 48 | `fun queryBase64TTF(data: String?): QueryTTF?` | 低 | 标记需真机 | 已废弃，用 queryTTF 替代 |
| 49 | `fun queryTTF(data: Any?, useCache: Boolean): QueryTTF?` | 中 | 标记需真机 | 字体解析，依赖 QueryTTF 类（Android 字体渲染） |
| 50 | `fun queryTTF(data: Any?): QueryTTF?` | 中 | 标记需真机 | 同上重载 |
| 51 | `fun replaceFont(text: String, errorQueryTTF: QueryTTF?, correctQueryTTF: QueryTTF?, filter: Boolean): String` | 中 | 标记需真机 | 字体替换，依赖 QueryTTF |
| 52 | `fun replaceFont(text: String, errorQueryTTF: QueryTTF?, correctQueryTTF: QueryTTF?): String` | 中 | 标记需真机 | 同上重载 |

---

## 6. 加密类 — JsEncodeUtils（21 个）

### 6.1 非对称加密与签名（2 个）

| # | 函数签名 | 影响级别 | 建议处理方式 | 说明 |
|---|----------|---------|-------------|------|
| 53 | `fun createAsymmetricCrypto(transformation: String): AsymmetricCrypto` | 中 | 可补全实现 | RSA 等非对称加密，Java Cipher 可实现 |
| 54 | `fun createSign(algorithm: String): Sign` | 低 | 可补全实现 | 签名，Java Signature 可实现 |

### 6.2 HMac 散列消息鉴别码（2 个）

| # | 函数签名 | 影响级别 | 建议处理方式 | 说明 |
|---|----------|---------|-------------|------|
| 55 | `fun HMacHex(data: String, algorithm: String, key: String): String` | 中 | 可补全实现 | HMac 转 16 进制，Java Mac 可实现 |
| 56 | `fun HMacBase64(data: String, algorithm: String, key: String): String` | 中 | 可补全实现 | HMac 转 Base64 |

### 6.3 AES 旧函数（已废弃但 web 仍调用）（9 个）

> **注意**：这些函数已标注 `@Deprecated`，但注释为"web 需要调用"，部分旧书源仍使用。

| # | 函数签名 | 影响级别 | 建议处理方式 | 说明 |
|---|----------|---------|-------------|------|
| 57 | `fun aesDecodeToByteArray(str: String, key: String, transformation: String, iv: String): ByteArray?` | 低 | 可补全实现 | 已废弃，内部调用 createSymmetricCrypto |
| 58 | `fun aesDecodeToString(str: String, key: String, transformation: String, iv: String): String?` | 中 | 可补全实现 | 已废弃但 web 调用 |
| 59 | `fun aesDecodeArgsBase64Str(data: String, key: String, mode: String, padding: String, iv: String): String?` | 中 | 可补全实现 | 已废弃但 web 调用，参数 Base64 编码 |
| 60 | `fun aesBase64DecodeToByteArray(str: String, key: String, transformation: String, iv: String): ByteArray?` | 低 | 可补全实现 | 已废弃 |
| 61 | `fun aesBase64DecodeToString(str: String, key: String, transformation: String, iv: String): String?` | 中 | 可补全实现 | 已废弃但 web 调用 |
| 62 | `fun aesEncodeToByteArray(data: String, key: String, transformation: String, iv: String): ByteArray?` | 低 | 可补全实现 | 已废弃 |
| 63 | `fun aesEncodeToString(data: String, key: String, transformation: String, iv: String): String?` | 中 | 可补全实现 | 已废弃但 web 调用 |
| 64 | `fun aesEncodeToBase64ByteArray(data: String, key: String, transformation: String, iv: String): ByteArray?` | 低 | 可补全实现 | 已废弃 |
| 65 | `fun aesEncodeToBase64String(data: String, key: String, transformation: String, iv: String): String?` | 中 | 可补全实现 | 已废弃但 web 调用 |

### 6.4 AES 参数 Base64 编码变体（1 个）

| # | 函数签名 | 影响级别 | 建议处理方式 | 说明 |
|---|----------|---------|-------------|------|
| 66 | `fun aesEncodeArgsBase64Str(data: String, key: String, mode: String, padding: String, iv: String): String?` | 中 | 可补全实现 | 已废弃但 web 调用，参数 Base64 编码 |

### 6.5 DES 旧函数（已废弃但 web 仍调用）（4 个）

| # | 函数签名 | 影响级别 | 建议处理方式 | 说明 |
|---|----------|---------|-------------|------|
| 67 | `fun desDecodeToString(data: String, key: String, transformation: String, iv: String): String?` | 中 | 可补全实现 | 已废弃但 web 调用 |
| 68 | `fun desBase64DecodeToString(data: String, key: String, transformation: String, iv: String): String?` | 中 | 可补全实现 | 已废弃但 web 调用 |
| 69 | `fun desEncodeToString(data: String, key: String, transformation: String, iv: String): String?` | 中 | 可补全实现 | 已废弃但 web 调用 |
| 70 | `fun desEncodeToBase64String(data: String, key: String, transformation: String, iv: String): String?` | 中 | 可补全实现 | 已废弃但 web 调用 |

### 6.6 3DES 旧函数（已废弃但 web 仍调用）（4 个）

| # | 函数签名 | 影响级别 | 建议处理方式 | 说明 |
|---|----------|---------|-------------|------|
| 71 | `fun tripleDESDecodeStr(data: String, key: String, mode: String, padding: String, iv: String): String?` | 中 | 可补全实现 | 已废弃但 web 调用 |
| 72 | `fun tripleDESDecodeArgsBase64Str(data: String, key: String, mode: String, padding: String, iv: String): String?` | 中 | 可补全实现 | 已废弃但 web 调用，参数 Base64 编码 |
| 73 | `fun tripleDESEncodeBase64Str(data: String, key: String, mode: String, padding: String, iv: String): String?` | 中 | 可补全实现 | 已废弃但 web 调用 |
| 74 | `fun tripleDESEncodeArgsBase64Str(data: String, key: String, mode: String, padding: String, iv: String): String?` | 中 | 可补全实现 | 已废弃但 web 调用，参数 Base64 编码 |

---

## 7. 其他类（21 个）

### 7.1 上下文获取（2 个）

| # | 函数签名 | 影响级别 | 建议处理方式 | 说明 |
|---|----------|---------|-------------|------|
| 75 | `fun getSource(): BaseSource?` | 中 | 可补全实现 | Mock 已有 source 字段，可包装为函数 |
| 76 | `fun getTag(): String?` | 低 | 可补全实现 | 返回源标签 |

### 7.2 时间格式化（2 个）

| # | 函数签名 | 影响级别 | 建议处理方式 | 说明 |
|---|----------|---------|-------------|------|
| 77 | `fun timeFormatUTC(time: Long, format: String, sh: Int): String?` | 低 | 降级 Python 仿真 | UTC 时间格式化，Python datetime 可实现 |
| 78 | `fun timeFormat(time: Long): String` | 低 | 降级 Python 仿真 | 时间格式化 |

### 7.3 文本处理（4 个）

| # | 函数签名 | 影响级别 | 建议处理方式 | 说明 |
|---|----------|---------|-------------|------|
| 79 | `fun htmlFormat(str: String): String` | 中 | 降级 Python 仿真 | HTML 格式化，保留图片 |
| 80 | `fun t2s(text: String): String` | 中 | 标记需真机 | 繁转简，依赖 ChineseUtils（本地词典） |
| 81 | `fun s2t(text: String): String` | 低 | 标记需真机 | 简转繁，依赖 ChineseUtils |
| 82 | `fun toNumChapter(s: String?): String?` | 中 | 降级 Python 仿真 | 章节数转数字，正则可实现 |

### 7.4 URL 工具（2 个）

| # | 函数签名 | 影响级别 | 建议处理方式 | 说明 |
|---|----------|---------|-------------|------|
| 83 | `fun toURL(urlStr: String): JsURL` | 中 | 可补全实现 | URL 解析，java.net.URL 可实现 |
| 84 | `fun toURL(url: String, baseUrl: String? = null): JsURL` | 中 | 可补全实现 | 同上重载 |

### 7.5 UI 交互（4 个）

| # | 函数签名 | 影响级别 | 建议处理方式 | 说明 |
|---|----------|---------|-------------|------|
| 85 | `fun toast(msg: Any?)` | 低 | 标记需真机 | 弹窗提示，依赖 Android UI |
| 86 | `fun longToast(msg: Any?)` | 低 | 标记需真机 | 长弹窗提示 |
| 87 | `fun logType(any: Any?)` | 低 | 可补全实现 | 输出对象类型，可用 javaClass.name |
| 88 | `fun openUrl(url: String)` | 低 | 标记需真机 | 打开应用跳转，依赖 Android Intent |

### 7.6 系统信息（2 个）

| # | 函数签名 | 影响级别 | 建议处理方式 | 说明 |
|---|----------|---------|-------------|------|
| 89 | `fun randomUUID(): String` | 中 | 可补全实现 | 生成 UUID，java.util.UUID 可实现 |
| 90 | `fun androidId(): String` | 低 | 降级 Python 仿真 | 返回 Android ID，可返回固定值 |

### 7.7 配置获取（5 个）

| # | 函数签名 | 影响级别 | 建议处理方式 | 说明 |
|---|----------|---------|-------------|------|
| 91 | `fun openUrl(url: String, mimeType: String? = null)` | 低 | 标记需真机 | 打开 URL 重载 |
| 92 | `fun getReadBookConfig(): String` | 低 | 降级 Python 仿真 | 获取阅读配置 JSON |
| 93 | `fun getReadBookConfigMap(): Map<String, Any>` | 低 | 降级 Python 仿真 | 获取阅读配置 Map |
| 94 | `fun getThemeMode(): String` | 低 | 降级 Python 仿真 | 获取主题模式 |
| 95 | `fun getThemeConfig(): String` | 低 | 降级 Python 仿真 | 获取主题配置 JSON |
| 96 | `fun getThemeConfigMap(): Map<String, Any?>` | 低 | 降级 Python 仿真 | 获取主题配置 Map |

---

## 统计摘要

| 类别 | 未实现数 | 高 | 中 | 低 |
|------|---------|---|---|---|
| 网络类 | 20 | 10 | 8 | 2 |
| 文件操作类 | 9 | 2 | 4 | 3 |
| 编码/解码类 | 5 | 0 | 4 | 1 |
| 压缩类 | 13 | 0 | 5 | 8 |
| 字体类 | 5 | 0 | 4 | 1 |
| 加密类 | 22 | 0 | 17 | 5 |
| 其他类 | 22 | 0 | 7 | 15 |
| **合计** | **96** | **12** | **49** | **35** |

### 按建议处理方式分布

| 处理方式 | 数量 | 占比 |
|---------|------|------|
| 标记需真机 | 25 | 26% |
| 降级 Python 仿真 | 32 | 33% |
| 可补全实现 | 39 | 41% |

---

## AI 使用指南

### 遇到 `TypeError: java.xxx is not a function` 时的处理流程

```
1. 查阅本速查表，找到对应函数
2. 判断影响级别：
   - 高 → 规则执行会失败，必须处理
   - 中 → 特定场景失败，检查是否用到
   - 低 → 极少使用，可忽略
3. 按建议处理方式执行：
   - 标记需真机 → 在验证报告中标注"不可验证"，提示用户需真机测试
   - 降级 Python 仿真 → 在 Python 脚本中实现替代逻辑
   - 可补全实现 → 触发 Phase 5 代码进化，更新 JsExtensionsStub.kt
```

### 高优先级补全建议（影响级别=高，可补全实现）

以下函数缺失会导致常见书源规则执行失败，建议优先补全：

1. `strToBytes(str: String): ByteArray` — 默认 UTF-8 重载
2. `bytesToStr(bytes: ByteArray): String` — 默认 UTF-8 重载
3. `randomUUID(): String` — UUID 生成
4. `getSource(): BaseSource?` — 上下文获取
5. `get(timeout)` / `head(timeout)` / `post(timeout)` — timeout 重载

### 必须真机测试的函数（影响级别=高，标记需真机）

以下函数依赖 Android 原生能力，无法在 JVM 仿真器中实现：

1. `webView` 系列（6 个）— WebView 渲染
2. `startBrowserAwait` 重载（2 个）— 交互式验证
3. `getVerificationCode` — 图片验证码输入
