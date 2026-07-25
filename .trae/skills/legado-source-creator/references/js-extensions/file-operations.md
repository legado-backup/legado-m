# JS 扩展函数参考 — 文件操作

> 拆分自 js-extensions.md §六。Legado 书源 JS 环境中可调用的文件读写和压缩解压扩展函数。
> 引擎为 Rhino 1.8.1（ES5），禁止使用 ES6+ 语法。
> 在 JS 中通过 `java` 变量调用，如 `java.readTxtFile(path)`。

---

## 六、文件操作

> 所有文件操作都是相对路径，只能操作阅读缓存目录（`/android/data/{package}/cache/...`）内的文件。

### 读取文件

```javascript
var content = java.readTxtFile("subdir/file.txt");           // 自动检测编码
var content = java.readTxtFile("subdir/file.txt", "GBK");    // 指定编码
var bytes = java.readFile("subdir/data.bin");                 // 读取为字节数组
```

| 函数 | 签名 | 返回值 | 频率 |
|------|------|--------|------|
| readTxtFile | `readTxtFile(path: String): String` | 自动检测编码的文本 | 高 |
| readTxtFile | `readTxtFile(path: String, charsetName: String): String` | 指定编码的文本 | 中 |
| readFile | `readFile(path: String): ByteArray?` | 原始字节数组 | 低 |

---

### 缓存与下载文件

```javascript
var content = java.cacheFile("https://example.com/script.js");          // 下载并缓存，返回内容
var content = java.cacheFile("https://example.com/script.js", 3600);    // 缓存 3600 秒
var path = java.downloadFile("https://example.com/file.zip");           // 下载文件，返回相对路径
```

| 函数 | 签名 | 返回值 | 频率 |
|------|------|--------|------|
| cacheFile | `cacheFile(urlStr: String): String` | 缓存文件内容 | 高 |
| cacheFile | `cacheFile(urlStr: String, saveTime: Int): String` | 带时效缓存 | 中 |
| downloadFile | `downloadFile(url: String): String` | 下载文件相对路径 | 高 |
| downloadFile | `downloadFile(content: String, url: String): String` | @Deprecated，十六进制内容转文件 | 低 |

---

### 导入脚本

```javascript
var scriptContent = java.importScript("https://example.com/helper.js");  // 从网络导入
var scriptContent = java.importScript("local/helper.js");                // 从本地导入
// 返回: String（脚本内容）
```

| 函数 | 签名 | 频率 |
|------|------|------|
| importScript | `importScript(path: String): String` | 中 |

> **注意**：源码中参数名为 `path`（非 `urlStr`），因为该方法既支持网络路径也支持本地路径。

---

### 删除文件

```javascript
var success = java.deleteFile("subdir/file.txt");
// 返回: Boolean
```

**使用频率**：低

---

### 压缩文件解压

```javascript
var dir = java.unzipFile("cache/archive.zip");     // 解压 ZIP
var dir = java.un7zFile("cache/archive.7z");       // 解压 7z
var dir = java.unrarFile("cache/archive.rar");     // 解压 RAR
var dir = java.unArchiveFile("cache/archive.zip"); // 自动识别格式
// 返回: String（解压后的相对路径）
```

| 函数 | 签名 | 频率 |
|------|------|------|
| unzipFile | `unzipFile(zipPath: String): String` | 中 |
| un7zFile | `un7zFile(zipPath: String): String` | 低 |
| unrarFile | `unrarFile(zipPath: String): String` | 低 |
| unArchiveFile | `unArchiveFile(zipPath: String): String` | 中 |

---

### 读取文件夹内所有文本文件

```javascript
var allText = java.getTxtInFolder("cache/extracted/");
// 返回: String（所有文件内容换行连接，读取后删除原文件夹）
```

**使用频率**：中

---

### 获取压缩包内指定文件内容

```javascript
// ZIP 文件
var content = java.getZipStringContent("https://example.com/data.zip", "chapter1.txt");
var content = java.getZipStringContent("https://example.com/data.zip", "chapter1.txt", "GBK");

// RAR 文件
var content = java.getRarStringContent("https://example.com/data.rar", "chapter1.txt");

// 7z 文件
var content = java.get7zStringContent("https://example.com/data.7z", "chapter1.txt");

// url 也可以是十六进制字符串
var content = java.getZipStringContent(hexData, "chapter1.txt");
```

| 函数 | 签名 | 频率 |
|------|------|------|
| getZipStringContent | `getZipStringContent(url: String, path: String): String` | 中 |
| getZipStringContent | `getZipStringContent(url: String, path: String, charsetName: String): String` | 低 |
| getRarStringContent | `getRarStringContent(url: String, path: String): String` | 低 |
| getRarStringContent | `getRarStringContent(url: String, path: String, charsetName: String): String` | 低 |
| get7zStringContent | `get7zStringContent(url: String, path: String): String` | 低 |
| get7zStringContent | `get7zStringContent(url: String, path: String, charsetName: String): String` | 低 |
| getZipByteArrayContent | `getZipByteArrayContent(url: String, path: String): ByteArray?` | 低 |
| getRarByteArrayContent | `getRarByteArrayContent(url: String, path: String): ByteArray?` | 低 |
| get7zByteArrayContent | `get7zByteArrayContent(url: String, path: String): ByteArray?` | 低 |
