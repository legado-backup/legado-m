# Rhino 环境安全限制

> 验证日期：2026-06-03（第三次深度验证，修正原因归因）
> 源码文件：`modules/rhino/src/main/java/com/script/rhino/RhinoClassShutter.kt`、`RhinoScriptEngine.kt`、`RhinoTopLevel.kt`、`RhinoWrapFactory.kt`、`ClassNameMatcher.kt`
> 应用源码：`app/src/main/java/io/legado/app/model/analyzeRule/AnalyzeRule.kt` L828-858

## 1. RhinoClassShutter 禁止的类

> 源码：RhinoClassShutter.kt L48-119
> 匹配逻辑：ClassNameMatcher 使用二分搜索，精确匹配类名或包前缀匹配（className 以 prefix + "." 开头）

### 1.1 精确禁止的类名（32 个 Java/Android 核心类）

```
java.lang.Class
java.lang.ClassLoader
java.net.URLClassLoader
java.lang.Runtime
java.lang.ProcessBuilder
java.lang.ProcessImpl
java.lang.UNIXProcess
java.io.File
java.io.FileDescriptor
java.io.FileInputStream
java.io.FileOutputStream
java.io.PrintStream
java.io.FileReader
java.io.FileWriter
java.io.PrintWriter
java.io.UnixFileSystem
java.io.RandomAccessFile
java.io.ObjectInputStream
java.io.ObjectOutputStream
java.security.AccessController
java.nio.file.Paths
java.nio.file.Files
java.nio.file.FileSystems
java.util.Formatter
sun.misc.Unsafe
android.content.Intent
android.provider.Settings
android.app.ActivityThread
android.app.AppGlobals
android.os.Looper
android.os.Process
android.os.FileUtils
```

### 1.2 精确禁止的类名（8 个 Hutool/Rhino 类）

```
cn.hutool.core.lang.JarClassLoader
cn.hutool.core.lang.Singleton
cn.hutool.core.util.RuntimeUtil
cn.hutool.core.util.ClassLoaderUtil
cn.hutool.core.util.ReflectUtil
cn.hutool.core.util.SerializeUtil
cn.hutool.core.util.ClassUtil
org.mozilla.javascript.DefiningClassLoader
```

### 1.3 精确禁止的类名（11 个 Legado/AndroidX/Okio 类）

```
io.legado.app.data.AppDatabase
io.legado.app.data.AppDatabase_Impl
io.legado.app.data.AppDatabaseKt
io.legado.app.utils.ContextExtensionsKt
androidx.core.content.FileProvider
splitties.init.AppCtxKt
okio.JvmSystemFileSystem
okio.JvmFileHandle
okio.NioSystemFileSystem
okio.NioFileSystemFileHandle
okio.Path
```

### 1.4 包前缀禁止（16 个包，该包下所有类均不可访问）

```
android.system
android.database
androidx.sqlite.db
androidx.room
cn.hutool.core.io
cn.hutool.core.bean
cn.hutool.core.lang.reflect
dalvik.system
java.nio.file
java.lang.reflect     ← ⚠️ java.lang.reflect.Array.newInstance() 被禁止！
java.lang.invoke
io.legado.app.data.dao
com.script
org.mozilla
sun
libcore
```

### 1.5 继承检查禁止（protectedClasses，10 个基类 + 2 个条件类）

> 源码：RhinoClassShutter.kt L126-143
> 逻辑：如果目标类是以下类的子类（isAssignableFrom），则禁止访问

```
ClassLoader
Class
Member
Context (org.mozilla.javascript.Context)
ObjectInputStream
ObjectOutputStream
okio.FileSystem
okio.FileHandle
okio.Path
android.content.Context
--- API 26+ 额外禁止 ---
java.nio.file.FileSystem
java.nio.file.Path
```

### 1.6 System 类方法保护

> 源码：RhinoClassShutter.kt L122-124, L176-184
> 逻辑：System 类本身未被禁止，但通过 ProtectedNativeJavaClass 屏蔽了以下方法

```
System.load()        ← 禁止
System.loadLibrary() ← 禁止
System.exit()        ← 禁止
```

## 2. ⚠️⚠️⚠️ 陷阱#3 根因修正：`java` 变量遮蔽，而非 ClassShutter 禁止整个包

> **关键修正**：之前文档将 `java.lang.String`/`java.util.ArrayList`/`java.net.URL` 等无法通过 `java.xxx` 访问的原因归咎于 ClassShutter 禁止了整个 `java.lang`/`java.util`/`java.io`/`java.net` 包，这是**错误的**。

### 真实原因

RhinoClassShutter **只禁止了特定类和特定子包**（见上方 1.1-1.4），**并未禁止** `java.lang`、`java.util`、`java.io`、`java.net` 整个包。以下类在 ClassShutter 层面是**允许访问**的：

| 类 | ClassShutter 是否允许 | `java.xxx` 能否访问 | 原因 |
|-----|------|------|------|
| `java.lang.String` | ✅ 允许 | ❌ 不能 | `java` 变量被绑定为 JsExtensions 实例 |
| `java.util.ArrayList` | ✅ 允许 | ❌ 不能 | 同上 |
| `java.util.zip.Inflater` | ✅ 允许 | ❌ 不能 | 同上 |
| `java.io.ByteArrayOutputStream` | ✅ 允许 | ❌ 不能 | 同上 |
| `java.net.URL` | ✅ 允许 | ❌ 不能 | 同上 |
| `java.lang.Runtime` | ❌ 禁止 | ❌ 不能 | ClassShutter 禁止 + java 变量遮蔽 |

**根本原因**：在 Legado 的 Rhino JS 环境中，`java` 被绑定为 JsExtensions 实例（`bindings["java"] = this`），**遮蔽了 Rhino 原生的 Java 包命名空间**。因此 `java.lang` 实际上是访问 JsExtensions 实例的 `lang` 属性（undefined），而非 Java 的 `java.lang` 包。

**解决方案**：使用 `Packages.java.xxx` 前缀访问 Java 类（`Packages` 是 Rhino 标准作用域中的内置对象，不受 `java` 变量遮蔽影响）。

## 3. ✅ 可以使用的 Java 类（不在禁止列表中）

> ⚠️ 重要：必须通过 `Packages` 前缀访问，不能通过 `java` 前缀！详见第2节。

| 类 | 用途 | 正确访问方式 |
|-----|------|------|
| `java.util.zip.Inflater` | deflate 解压 | `new Packages.java.util.zip.Inflater(true)` |
| `java.util.zip.InflaterInputStream` | deflate 流式解压 | `new Packages.java.util.zip.InflaterInputStream(...)` |
| `java.io.ByteArrayOutputStream` | 字节数组输出流 | `new Packages.java.io.ByteArrayOutputStream()` |
| `java.io.ByteArrayInputStream` | 字节数组输入流 | `new Packages.java.io.ByteArrayInputStream(...)` |
| `java.lang.String` | 字符串/编码转换 | `new Packages.java.lang.String(bytes, 'UTF-8')` |
| `java.util.Arrays` | 数组操作 | `Packages.java.util.Arrays.copyOfRange(...)` |
| `javax.crypto.Cipher` | 加密（但推荐用 createSymmetricCrypto） | `Packages.javax.crypto.Cipher.getInstance(...)` |
| `android.util.Base64` | Base64 编解码 | `Packages.android.util.Base64.encodeToString(...)` |

## 4. Rhino 中创建字节数组的正确方式

> ⚠️ `java.lang.reflect.Array.newInstance()` 被禁止！
> ⚠️ `new byte[n]` 不是有效 Rhino/JS 语法！

| 方式 | 代码 | 说明 |
|------|------|------|
| `java.hexDecodeToByteArray()` | `var arr = java.hexDecodeToByteArray('00'.repeat(4096))` | ✅ 创建4096字节零数组 |
| `java.base64DecodeToByteArray()` | `var arr = java.base64DecodeToByteArray('AAAA')` | ✅ 从base64创建字节数组 |
| In-place 修改 | `decoded[i] = (decoded[i] ^ key) & 0xFF` | ❌ **值>127时Rhino装箱为java.lang.Byte报错！** |
| Hex中转修改 | 见第12节模板 | ✅ 用hex字符串中转，避免byte[]原地赋值 |
| `new byte[n]` | `var buffer = new byte[4096]` | ❌ 不是有效JS语法！ |
| `java.lang.reflect.Array.newInstance()` | | ❌ 被RhinoClassShutter禁止 |

## 5. JS 规则执行环境绑定

> 源码：AnalyzeRule.kt L828-858

| 绑定名 | 类型 | 说明 |
|--------|------|------|
| `java` | JsExtensions (AnalyzeRule) | 所有 java.xxx 调用（**不是Java包！**） |
| `cookie` | CookieStore | Cookie 存储 |
| `cache` | CacheManager | 缓存管理 |
| `source` | BookSource/RssSource | 当前源 |
| `book` | Book | 当前书籍（书源时） |
| `result` | Any | 上一步结果/当前content |
| `baseUrl` | String | 基础URL |
| `chapter` | BookChapter | 当前章节（书源时） |
| `title` | String | 章节标题 |
| `src` | String | 原始内容 |
| `nextChapterUrl` | String | 下一章URL |
| `rssArticle` | RssArticle | RSS文章（订阅源时） |
| `fromBookInfo` | Boolean | 是否来自书籍信息 |

## 6. `java` 变量绑定的 5 种上下文

> ⚠️ 不同上下文中 `java` 绑定的 JsExtensions 实例不同，可用的方法可能略有差异

| 上下文 | 源码位置 | 绑定代码 | JsExtensions 实例 |
|--------|----------|----------|-------------------|
| AnalyzeRule（规则执行） | AnalyzeRule.kt L830 | `bindings["java"] = this` | AnalyzeRule 自身（实现 JsExtensions） |
| AnalyzeUrl（URL模板） | AnalyzeUrl.kt L366 | `bindings["java"] = this` | AnalyzeUrl 自身（继承 JsExtensions） |
| BaseSource（源JS执行） | BaseSource.kt L327 | `bindings["java"] = this` | BaseSource 自身（实现 JsExtensions） |
| RegexJsExtensions（正则JS替换） | RegexExtensions.kt L55 | `bindings["java"] = reJsExtensions` | RegexJsExtensions 实例 |
| TextFile（本地书目录JS） | TextFile.kt L587 | `bindings["java"] = JsExtensions(lastVolumeTitle, toc)` | 匿名 JsExtensions 实现 |

## 7. Rhino ES 限制

> 源码：RhinoScriptEngine.kt L318-343

- 语言版本：ES6（`Context.VERSION_ES6`）
- 解释模式：`setInterpretedMode(true)`（支持continuation）
- 指令计数阈值：10000（防死循环）
- 最大栈深度：1000
- 支持 Java Map 属性访问：`map.key` 等同于 `map.get("key")`
- ❌ **不支持** `new byte[n]` Java数组创建语法（这不是有效JS语法）

## 8. ⚠️⚠️⚠️ Rhino 中 `java` 变量是 JsExtensions 实例，不是 Java 包！

> 源码依据：AnalyzeRule.kt L830 `bindings["java"] = this`
> 根因：`java` 变量遮蔽了 Rhino 的 Java 包命名空间，而非 ClassShutter 禁止了整个包

在 Legado 的 Rhino JS 环境中，`java` 被绑定为 JsExtensions 实例（`bindings["java"] = this`），**不是** Java 的 `java` 包命名空间！

**这意味着**：
- ❌ `java.lang.String` → `java.lang` 是 `undefined`，访问 `.String` 报 TypeError
- ❌ `java.util.zip.Inflater` → `java.util` 是 `undefined`，访问 `.zip` 报 TypeError
- ❌ `java.io.ByteArrayOutputStream` → `java.io` 是 `undefined`，报 TypeError
- ❌ `java.net.URLDecoder.decode(str, 'UTF-8')` → 同上
- ✅ `java.base64Encode(str)` → 调用 JsExtensions 的方法
- ✅ `java.hexDecodeToByteArray(hex)` → 调用 JsExtensions 的方法
- ✅ `java.createSymmetricCrypto(...)` → 调用 JsExtensions 的方法

## 9. ✅✅✅ 访问 Java 类的正确方式：`Packages` 前缀

> 源码依据：
> - RhinoScriptEngine.kt L261-269: `bindings.prototype = cx.initStandardObjects()` → `Packages` 在标准作用域中可用
> - RhinoClassShutter.kt: `visibleToScripts(fullClassName)` → 未禁止的类可通过 Packages 访问
> - RhinoWrapFactory.kt L63-75: `wrapJavaClass()` → 对可见类返回 `ProtectedNativeJavaClass`，支持 `new` 构造

### 核心规则

`Packages` 是 Rhino 标准作用域中的内置对象，提供对 Java 包的访问。由于 `java` 被 JsExtensions 覆盖，**必须使用 `Packages.java.xxx` 来访问 Java 类**。

### 正确用法对照表

| 需求 | ❌ 错误写法（会报TypeError） | ✅ 正确写法 |
|------|-----------|-----------|
| 创建 Inflater | `new java.util.zip.Inflater(true)` | `new Packages.java.util.zip.Inflater(true)` |
| 创建 ByteArrayOutputStream | `new java.io.ByteArrayOutputStream()` | `new Packages.java.io.ByteArrayOutputStream()` |
| 创建 ByteArrayInputStream | `new java.io.ByteArrayInputStream(bytes, off, len)` | `new Packages.java.io.ByteArrayInputStream(bytes, off, len)` |
| 字节数组→UTF-8字符串 | `new java.lang.String(bytes, 'UTF-8')` | `String(new Packages.java.lang.String(bytes, 'UTF-8'))` |
| 字节数组切片 | 手动循环复制 | `Packages.java.util.Arrays.copyOfRange(bytes, from, to)` |
| URL解码 | `java.net.URLDecoder.decode(str, 'UTF-8')` | `decodeURIComponent(str)`（Rhino内置JS函数） |
| 当前时间戳 | `new java.util.Date().getTime()` | `Date.now()`（JS内置） |
| 字符串→字节数组 | `new java.lang.String(key).getBytes('UTF-8')` | `java.hexDecodeToByteArray(java.hexEncodeToString(key))` |
| 字节→hex | `java.lang.Integer.toHexString(b)` | hex查找表：`var hc='0123456789abcdef'; hc.charAt(b>>4)+hc.charAt(b&0x0F)` |
| 创建字节数组缓冲区 | `new byte[4096]` | `java.hexDecodeToByteArray('00'.repeat(4096))` |

### ⚠️ JavaImporter / importPackage 不可用！

> 源码依据：
> - RhinoTopLevel.kt L47-48: 继承 `ImporterTopLevel`，提供 `importPackage`/`importClass`
> - RhinoScriptEngine.kt L261-269: `getRuntimeScope(bindings)` 使用 `cx.initStandardObjects()`，**不是** RhinoTopLevel
> - AnalyzeRule.kt L844-855: evalJS 使用 `getRuntimeScope(bindings)`，原型链中**没有** ImporterTopLevel

**结论**：`JavaImporter`、`importPackage`、`importClass` 在 evalJS 作用域中**不可用**！只能使用 `Packages.java.xxx` 完整路径。

### 完整的 Inflater 解压模板

```javascript
var inflater = new Packages.java.util.zip.Inflater(true);
inflater.setInput(decoded, 1, bodyLen);
var output = new Packages.java.io.ByteArrayOutputStream();
var buf = java.hexDecodeToByteArray('00'.repeat(4096));
while (!inflater.finished()) {
    var count = inflater.inflate(buf);
    if (count <= 0) break;
    output.write(buf, 0, count);
}
inflater.end();
var jsonStr = String(new Packages.java.lang.String(output.toByteArray(), 'UTF-8'));
```

### 非压缩数据直接转换模板

```javascript
// 跳过首字节(flag)，直接将 decoded[1:] 转为 UTF-8 字符串
var jsonStr = String(new Packages.java.lang.String(decoded, 1, bodyLen, 'UTF-8'));
```

## 10. AES/DES 加密中 createSymmetricCrypto 的正确调用

> 源码依据：JsEncodeUtils.kt L44-76

`createSymmetricCrypto` 有4个重载：

| 签名 | 说明 |
|------|------|
| `(String, ByteArray?, ByteArray?)` | key和iv都是字节数组 |
| `(String, ByteArray)` | key是字节数组，无iv |
| `(String, String)` | key是字符串，无iv |
| `(String, String, String?)` | key和iv都是字符串 |

### 陷阱8a：key String + iv ByteArray 重载歧义

当 key 是 String 而 iv 是 ByteArray 时，Rhino 方法重载解析可能失败！

```javascript
// ❌ 错误：key是String，iv是ByteArray，重载解析歧义
var crypto = java.createSymmetricCrypto('AES/CFB/NoPadding', 'WB0nMZHXlxNndORe', ivBytes);

// ✅ 正确：先将key转为ByteArray，确保调用 (String, ByteArray?, ByteArray?) 重载
var keyBytes = java.hexDecodeToByteArray(java.hexEncodeToString('WB0nMZHXlxNndORe'));
var crypto = java.createSymmetricCrypto('AES/CFB/NoPadding', keyBytes, ivBytes);
```

### 陷阱8b：⚠️⚠️⚠️ 传 null 第三参数导致重载歧义

> 根因：Rhino 无法确定 `null` 匹配 `String?` 还是 `ByteArray?`，导致两个重载都匹配，抛 EvaluatorException。
> 实际报错：`对应于 JavaScript 参数类型 (string,[B,null) 的 Java 方法 createSymmetricCrypto 的选择不明确`

```javascript
// ❌ 错误：第三个参数 null 让 Rhino 无法决定走 (String, ByteArray?, ByteArray?) 还是 (String, String, String?)
var keyBytes = java.hexDecodeToByteArray(java.hexEncodeToString('UC2FmMyG'));
var crypto = java.createSymmetricCrypto('DES/ECB/PKCS5Padding', keyBytes, null);

// ✅ 正确：不需要 iv 时，用2参数版本，去掉 null
var keyBytes = java.hexDecodeToByteArray(java.hexEncodeToString('UC2FmMyG'));
var crypto = java.createSymmetricCrypto('DES/ECB/PKCS5Padding', keyBytes);
```

**规则**：`createSymmetricCrypto` 调用时，**永远不要传 `null` 作为第三参数**。不需要 iv 就用2参数重载。

## 11. AES 解密：避免 String.fromCharCode 损坏数据

> ⚠️ `String.fromCharCode(byteValue)` 对于 byte > 127 会产生多字节 UTF-16 字符，后续 base64 编码会损坏！

```javascript
// ❌ 错误：byte > 127 时 fromCharCode 产生多字节字符，base64Encode 结果损坏
var respEncB64 = '';
for (i = 0; i < respEncBytes.length; i++) {
    respEncB64 += String.fromCharCode(respEncBytes[i] & 0xFF);
}
var decrypted = decCrypto.decryptStr(java.base64Encode(respEncB64));

// ✅ 正确：直接用 decrypt(byte[]) 解密，再用 Packages.java.lang.String 转字符串
var decryptedBytes = decCrypto.decrypt(respEncBytes);
var decrypted = String(new Packages.java.lang.String(decryptedBytes, 'UTF-8'));
```

## 12. ⚠️⚠️⚠️ decodeURIComponent URIError 陷阱

> 根因：XOR 解密后的数据中可能包含孤立的 `%` 字符（0x25），后续两个字节不是合法 hex 数字，导致 `decodeURIComponent` 抛 URIError。
> Python 的 `urllib.parse.unquote()` 对此更宽容（忽略无效序列），但 Rhino/JS 的 `decodeURIComponent` 严格报错。

```javascript
// ❌ 危险：XOR解密后直接调用 decodeURIComponent，遇到孤立%会抛 URIError
var str1 = '';
for (i = 0; i < raw.length; i++) {
    str1 += String.fromCharCode((raw[i] ^ xorKey) & 0xFF);
}
var decoded = decodeURIComponent(str1);  // 💥 URIError: URI 序列的格式不正确

// ✅ 正确：先转义孤立%，再加 try-catch 安全网
var str1 = '';
for (i = 0; i < raw.length; i++) {
    str1 += String.fromCharCode((raw[i] ^ xorKey) & 0xFF);
}
str1 = str1.replace(/%(?![0-9A-Fa-f]{2})/g, '%25');  // 转义孤立%
var layer1Str;
try { layer1Str = decodeURIComponent(str1); } catch(e) { layer1Str = str1; }  // 安全网
```

**适用场景**：任何对 XOR/加密解密后的字节数据使用 `String.fromCharCode` 转字符串后需要 `decodeURIComponent` 的场景。

## 13. hex查找表模板（替代 Integer.toHexString）

```javascript
var hc = '0123456789abcdef';
var hexStr = '';
for (var i = 0; i < bytes.length; i++) {
    var b = bytes[i] & 0xFF;
    hexStr += hc.charAt(b >> 4) + hc.charAt(b & 0x0F);
}
```

## 14. ⚠️⚠️⚠️ byte[] 原地赋值陷阱（EvaluatorException: 无法将 N 转换为 java.lang.Byte）

> 根因：Rhino 对 Java `byte[]` 元素赋值时，内部尝试装箱为 `java.lang.Byte` 对象。
> `java.lang.Byte` 的范围是 -128~127，当 JS 表达式 `& 0xFF` 产生 128~255 的无符号值时，`Byte.valueOf(237)` 超出范围直接抛 EvaluatorException。

```javascript
// ❌ 错误：XOR 结果 & 0xFF 产生 0~255 的值，赋给 byte[] 时值>127 报错
for (i = 0; i < decoded.length; i++) {
    decoded[i] = (decoded[i] ^ keyBytes[i % keyBytes.length]) & 0xFF;  // 💥 237 > 127，无法转为Byte
}

// ✅ 正确：用 hex 字符串中转，避免 byte[] 原地赋值
var hc = '0123456789abcdef';
var hexStr = '';
for (i = 0; i < decoded.length; i++) {
    var val = (decoded[i] ^ keyBytes[i % keyBytes.length]) & 0xFF;
    hexStr += hc.charAt(val >> 4) + hc.charAt(val & 0x0F);
}
decoded = java.hexDecodeToByteArray(hexStr);  // Java 内部正确处理 signed byte
```

**适用场景**：任何需要对 Java `byte[]` 进行 XOR/加密运算后回写的场景。

## 15. ⚠️⚠️⚠️ 网站JSON结构动态变化陷阱

> 根因：网站API返回的JSON结构可能随时变化（如字段嵌套层级调整），导致硬编码的JSON路径失效，列表为空但不报错。
> 实际案例：`data.vod.list` → `data.list`（去掉了`vod`嵌套层），JS中 `data.vod ? data.vod.list : []` 因 `data.vod` 为 undefined 返回空数组。

```javascript
// ❌ 脆弱：只兼容一种JSON结构，网站变更后列表静默为空
var vodList = data.vod ? data.vod.list : [];

// ✅ 健壮：兼容新旧两种JSON结构
var vodList = data.vod ? (data.vod.list || []) : (data.list || []);
```

**规则**：编写JSON路径提取逻辑时，**必须考虑结构兼容性**，用三元表达式或`||`短路处理多种可能的嵌套层级。同样适用于详情页等所有JSON解析场景。

```javascript
// 详情页也要兼容
var vodInfo = detailData.vod ? (detailData.vod.list ? detailData.vod.list[0] : detailData.vod) : detailData;
```

## 16. ⚠️⚠️⚠️ API请求方法必须匹配（GET vs POST）

> 根因：网站API可能只接受POST请求，用GET会返回405 Method Not Allowed。`java.ajax()` 默认发GET请求。
> 实际案例：`/v2/api/vodData` 接口，GET返回405，POST + `data=encrypted` 成功，POST + `params=encrypted` 失败。

```javascript
// ❌ 错误：java.ajax() 默认发GET请求，API只接受POST
var resp = java.ajax(apiUrl + '?params=' + java.encodeURI(combined));

// ❌ 错误：POST参数名错误（params vs data）
var postBody = 'params=' + java.encodeURI(combined);

// ✅ 正确：用 java.post() 发POST请求，参数名用 data
var postBody = 'data=' + java.encodeURI(combined);
var headers = {'Content-Type': 'application/x-www-form-urlencoded'};
var respObj = java.post(apiUrl, postBody, headers);
var resp = String(respObj.body());
```

**规则**：调用网站API时，**必须先验证请求方法**（GET/POST）和参数名（data/params等），不能假设。

## 17. ⚠️⚠️⚠️ 详情页可能不包含视频数据，需从URL反解

> 根因：网站详情页HTML解密后的JSON可能只有 `info: []`（空），不包含vod_id等视频信息。视频数据需要通过API单独获取。
> 实际案例：详情页JSON keys为 `['menu', 'site', 'adv', 'info', 'cnxh_list']`，`info` 为空数组。

```javascript
// ❌ 脆弱：假设详情页JSON中有vod_id
var vodId = detailData.vod.vod_id;  // undefined!

// ✅ 健壮：从详情页URL中DES解密获取vod_id
// URL格式: /vod/details/{DES_encrypted_hex}
var m = baseUrl.match(/\/vod\/details\/([0-9a-fA-F]+)/);
var encHex = m[1];
var keyBytes = java.hexDecodeToByteArray(java.hexEncodeToString('UC2FmMyG'));
var crypto = java.createSymmetricCrypto('DES/ECB/PKCS5Padding', keyBytes);
var decBytes = crypto.decrypt(java.hexDecodeToByteArray(encHex));
var vodId = String(new Packages.java.lang.String(decBytes, 'UTF-8')).trim();
```

**规则**：不要假设详情页HTML中一定包含视频数据。如果列表页已经将vod_id编码到URL中，ruleContent应从URL反解而非从HTML提取。

## 18. ⚠️⚠️⚠️ API返回的vod_play_url可能是数组而非字符串

> 根因：API返回的 `vod_play_url` 可能是嵌套数组 `[{key, name, list: [{name, h264}]}]`，不是简单字符串。直接赋值会导致类型错误或空结果。

```javascript
// ❌ 错误：假设vod_play_url是字符串
result = playData.vod_play_url;  // 返回数组对象，Legado无法处理

// ✅ 正确：遍历数组提取m3u8地址
if (playData.vod_play_url && Array.isArray(playData.vod_play_url)) {
  for (var p = 0; p < playData.vod_play_url.length; p++) {
    var group = playData.vod_play_url[p];
    if (group.list && Array.isArray(group.list)) {
      for (var q = 0; q < group.list.length; q++) {
        var item = group.list[q];
        if (item.h264) { playUrl = item.h264; break; }
        if (item.url) { playUrl = item.url; break; }
      }
    }
    if (playUrl) break;
  }
}
```

**规则**：API返回的播放地址字段**必须先检查类型**（字符串 vs 数组），数组需要遍历提取实际URL。

## 19. ⚠️⚠️⚠️ java.post() headers参数NativeObject→Map转换可能失败

> 根因：Rhino环境中JS对象字面量（如 `{'Content-Type': 'application/x-www-form-urlencoded'}`）是NativeObject，传给 `java.post(url, body, headers)` 时，虽然Rhino理论上可通过 `Context.jsToJava()` 将NativeObject转为 `Map<String, String>`，但实际在某些情况下转换失败，导致请求失败返回HTML错误页。
> 实际案例：`java.post(apiUrl, postBody, {'Content-Type': 'application/x-www-form-urlencoded'})` 请求API，返回HTML而非JSON，`JSON.parse` 收到HTML抛 SyntaxError。

```javascript
// ❌ 不可靠：java.post() 的 headers 参数 NativeObject→Map 转换可能失败
var headers = {'Content-Type': 'application/x-www-form-urlencoded'};
var respObj = java.post(apiUrl, postBody, headers);
var resp = String(respObj.body());
// resp 可能是 HTML 错误页而非 JSON

// ✅ 正确：用 java.ajax() 的 POST URL 格式，headers 由 AnalyzeUrl 内部 Gson 解析，更可靠
var ajaxOpt = JSON.stringify({method:'POST', body:'data='+combined, headers:{'Content-Type':'application/x-www-form-urlencoded'}});
var resp = java.ajax(apiUrl + ',' + ajaxOpt);
// resp 直接返回响应体字符串
```

**规则**：在Rhino JS中发POST请求时，**优先使用 `java.ajax()` 的POST URL格式**，而非 `java.post()`。`java.ajax()` 的选项JSON由 `AnalyzeUrl` 内部的Gson解析，比Rhino的NativeObject→Map转换更可靠。

> 注意：`java.ajax()` 返回的是响应体字符串（`String?`），不是 `Connection.Response` 对象。如果需要获取响应头或状态码，仍需使用 `java.post()`。

## 20. ⚠️⚠️⚠️ URL拼接时注意路径分隔符 `/`

> 根因：`baseUrl.replace()` 去掉路径部分后，结果可能不以 `/` 结尾，直接拼接相对路径会导致URL格式错误。
> 实际案例：
> - `baseUrl = 'https://xxx:2024/vod/details/abc'`，`baseUrl.replace(/\/vod\/details\/.*/, '')` = `'https://xxx:2024'`
> - 拼接 `'v2/api/vodData'` → `'https://xxx:2024v2/api/vodData'`（缺少 `/`，域名和路径粘在一起）
> - 正确：拼接 `'/v2/api/vodData'` → `'https://xxx:2024/v2/api/vodData'`

```javascript
// ❌ 错误：缺少前导 /
var apiUrl = baseUrl.replace(/\/vod\/details\/.*/, '') + 'v2/api/vodData';
// 结果: https://xxx:2024v2/api/vodData

// ✅ 正确：确保前导 /
var apiUrl = baseUrl.replace(/\/vod\/details\/.*/, '') + '/v2/api/vodData';
// 结果: https://xxx:2024/v2/api/vodData
```

**规则**：URL拼接时，**必须确保路径部分以 `/` 开头**，或在baseUrl末尾确认有 `/`。建议用 `baseUrl.replace(...) + '/path'` 格式。

## 21. ⚠️⚠️⚠️ 网站302重定向可能丢失路径

> 根因：网站域名动态变化时，旧域名302重定向到新域名的Location头可能只包含新域名根路径，不保留原始请求路径。
> 实际案例：`https://611371056.w3.xhs9v0w1.cc:2024/category/41/` 302重定向到 `https://2093038858.w2.xhsh7c3.cc:2024`（丢失了 `/category/41/`）。

**规则**：
1. sortUrl/searchUrl 中的域名**必须使用当前可用的域名**，不能依赖302重定向保留路径
2. 域名会动态变化，需定期更新。建议在sourceComment中记录发布页地址
3. ruleLink/ruleContent中构建URL时，从 `baseUrl` 提取域名部分（如 `baseUrl.replace(/\/category\/.*/, '')`），而非硬编码域名
