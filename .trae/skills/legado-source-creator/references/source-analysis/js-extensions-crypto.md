# JS 加密 API 与 CryptoJS 差异

> 验证日期：2026-06-02
> 源码文件：`JsExtensions.kt`、`JsEncodeUtils.kt`、`SymmetricCryptoAndroid.kt`

## 1. Legado 推荐加密 API

### 对称加密（推荐方式）

```javascript
// 创建加密器
var crypto = java.createSymmetricCrypto(transformation, key, iv);

// 加密
crypto.encrypt(data)           // 返回 ByteArray
crypto.encryptBase64(data)     // 返回 Base64 String
crypto.encryptHex(data)        // 返回 Hex String

// 解密
crypto.decrypt(data)           // 返回 ByteArray
crypto.decryptStr(data)        // 返回 String
```

**transformation 格式**：`算法/模式/填充`，如 `AES/CBC/PKCS5Padding`、`DES/ECB/PKCS5Padding`

**key 参数类型**：
- `String` → `key.encodeToByteArray()` 转为字节数组（UTF-8编码）
- `ByteArray` → 直接使用
- ⚠️ DES密钥必须8字节，AES密钥必须16/24/32字节

### 旧版 API（@Deprecated 但仍可用）

```javascript
// DES
java.desDecodeToString(data, key, "DES/ECB/PKCS5Padding", "")
java.desEncodeToBase64String(data, key, "DES/ECB/PKCS5Padding", "")

// AES
java.aesDecodeToString(str, key, "AES/CBC/PKCS5Padding", iv)
java.aesEncodeToBase64String(data, key, "AES/CBC/PKCS5Padding", iv)
```

### 摘要/HMAC

```javascript
java.md5Encode(str)                    // MD5 32位hex
java.md5Encode16(str)                  // MD5 16位hex
java.digestHex(data, "SHA-256")        // 通用摘要
java.HMacHex(data, "HmacSHA256", key)  // HMAC
```

### 编码

```javascript
java.base64Encode(str)                 // Base64编码
java.base64Decode(str)                 // Base64解码
java.hexEncodeToString(utf8)           // Hex编码
java.hexDecodeToByteArray(hex)         // Hex解码为ByteArray
java.hexDecodeToString(hex)            // Hex解码为String
```

## 2. ⚠️ CryptoJS 与 Legado API 的关键差异

### 2.1 DES 密钥派生差异

**CryptoJS 字符串密钥模式**：
```javascript
// CryptoJS 使用 EVP_BytesToKey 从 passphrase 派生密钥
CryptoJS.DES.encrypt(plaintext, passphrase, {mode: ECB, padding: Pkcs7})
// 实际密钥 = MD5(passphrase) 的前8字节
```

**Legado createSymmetricCrypto**：
```javascript
// 直接用字符串的 UTF-8 字节作为密钥
java.createSymmetricCrypto("DES/ECB/PKCS5Padding", "passphrase")
// 实际密钥 = passphrase.encodeToByteArray() 的 UTF-8 字节
// ⚠️ 如果passphrase超过8字节，DES会报错（密钥必须8字节）！
```

**正确做法**：区分两种CryptoJS密钥模式

**模式A：`CryptoJS.enc.Utf8.parse("key")` — WordArray密钥，直接用UTF-8字节**
```javascript
// CryptoJS.enc.Utf8.parse("UC2FmMyG928hRZY4") = 16字节WordArray
// DES只需要8字节，CryptoJS自动截取前8字节
// 实际DES密钥 = "UC2FmMyG" 的UTF-8字节

// Legado Rhino 中等效写法：
var crypto = java.createSymmetricCrypto("DES/ECB/PKCS5Padding", "UC2FmMyG", null);
var encrypted = crypto.encryptHex(vodId);
```

**模式B：字符串密钥 — EVP_BytesToKey(MD5)派生**
```javascript
// CryptoJS.DES.encrypt(plaintext, "passphrase", {mode:ECB})
// 使用EVP_BytesToKey: MD5(passphrase)前8字节作为DES密钥

// Legado Rhino 中等效写法：
var md5Hex = java.md5Encode("passphrase");
var desKeyHex = md5Hex.substring(0, 16);
var desKeyBytes = java.hexDecodeToByteArray(desKeyHex);
var crypto = java.createSymmetricCrypto("DES/ECB/PKCS5Padding", desKeyBytes, null);
var encrypted = crypto.encryptHex(vodId);
```

⚠️ **关键区别**：`CryptoJS.enc.Utf8.parse()` 和字符串密钥的派生方式完全不同！必须看网站源码确认用的是哪种。

### 2.2 AES 密钥差异

**CryptoJS 字符串密钥**：同样使用 EVP_BytesToKey，MD5+迭代派生
**Legado**：直接用 UTF-8 字节

**CryptoJS Utf8.parse 密钥**：`CryptoJS.enc.Utf8.parse("key")` 等同于直接用 UTF-8 字节
**Legado**：`java.createSymmetricCrypto("AES/CBC/PKCS5Padding", "key", iv)` 行为相同

### 2.3 Base64 差异

**CryptoJS**：`CryptoJS.enc.Base64.stringify()` 标准Base64
**Legado**：`java.base64Encode()` 标准Base64

⚠️ `java.util.Base64` 在 Android 低版本不可用！用 `android.util.Base64` 或 `java.base64Encode()`

## 3. 实际案例：小黄书视频站

### DES 加密 vod_id

```javascript
// 网站前端代码（CryptoJS）：
// const secretKey = CryptoJS.enc.Utf8.parse("UC2FmMyG928hRZY4");  ← WordArray密钥
// CryptoJS.DES.encrypt(vod_id, secretKey, {mode:ECB, padding:Pkcs7})
// CryptoJS.enc.Utf8.parse() = 直接用UTF-8字节，16字节 > DES需要的8字节
// CryptoJS自动截取前8字节 = "UC2FmMyG" 的UTF-8字节

// Legado Rhino 中等效写法（模式A：WordArray密钥）：
var crypto = java.createSymmetricCrypto("DES/ECB/PKCS5Padding", "UC2FmMyG", null);
var encrypted = crypto.encryptHex(String(vodId));
result = baseUrl + "vod/details/" + encrypted;
```

⚠️ **之前的错误**：误用了EVP_BytesToKey(MD5)派生，实际网站用的是 `CryptoJS.enc.Utf8.parse()` 模式，直接截取前8字符作为DES密钥。

### AES-CFB 加密API请求参数

```javascript
// 网站前端代码（CryptoJS）：
// const apiKey = "WB0nMZHXlxNndORe";
// encryptData(params) = AES-CFB-128加密 + IV插入密文中间
// 格式: 密文前8字节hex + IV的hex + 密文剩余hex

// Legado Rhino 中等效写法：
var apiKey = "WB0nMZHXlxNndORe";
var ivHex = java.md5Encode(java.randomUUID()).substring(0, 32);
var ivBytes = java.hexDecodeToByteArray(ivHex);
var aesCrypto = java.createSymmetricCrypto("AES/CFB/NoPadding", apiKey, ivBytes);
var encB64 = aesCrypto.encryptBase64(params);
var encBytes = java.base64DecodeToByteArray(encB64);
var encHex = "";
for (var i = 0; i < encBytes.length; i++) {
    var b = encBytes[i] & 0xFF;
    encHex += (b < 16 ? "0" : "") + java.lang.Integer.toHexString(b);
}
var combined = encHex.substring(0, 16) + ivHex + encHex.substring(16);
```

### XOR + deflate 解密

```javascript
// XOR解密：in-place修改decoded数组
var decoded = java.base64DecodeToByteArray(b64);
var keyBytes = new java.lang.String(key).getBytes("UTF-8");
for (var i = 0; i < decoded.length; i++) {
    decoded[i] = (decoded[i] ^ keyBytes[i % keyBytes.length]) & 0xFF;
}
// deflate解压
var inflater = new java.util.zip.Inflater(true);
inflater.setInput(decoded, 1, decoded.length - 1);
var output = new java.io.ByteArrayOutputStream();
var buffer = new byte[4096];
while (!inflater.finished()) {
    var count = inflater.inflate(buffer);
    if (count > 0) output.write(buffer, 0, count);
}
inflater.end();
```

## 4. 二进制内容解密完整流程（图片/视频）

> 验证日期：2026-06-09
> 源码文件：`JsExtensions.kt` L100-119（ajax返回String）、`SymmetricCryptoAndroid.kt` L38-45（decrypt vs decryptStr）

### 4.1 核心问题：`java.ajax()` 返回 String，无法获取二进制数据

**源码证据**：
- `JsExtensions.kt` L100: `fun ajax(url: Any): String?` — 始终返回String
- `AnalyzeUrl.kt` L424-426: 当URL带`@type`参数时，内部调用`getByteArrayAwait()`获取byte[]，然后用`HexUtil.encodeHexStr()`转为hex字符串返回
- **结论**：`java.ajax()` 无法直接获取byte[]用于解密

### 4.2 获取byte[]的三种方式

| 方式 | 代码 | 优缺点 |
|------|------|--------|
| **OkHttp直接获取（推荐）** | `var client=new Packages.okhttp3.OkHttpClient();var req=new Packages.okhttp3.Request.Builder().url(url).build();var resp=client.newCall(req).execute();var bytes=resp.body().bytes();resp.close();` | 最直接，无需中转 |
| ajax+@type hex中转 | `var hexStr=java.ajax(url+'@type=jpg');var bytes=java.hexDecodeToByteArray(hexStr);` | 多一步hex编解码，效率低 |
| downloadFile+readFile | `var path=java.downloadFile(url);var bytes=java.readFile(path);` | 多一步文件中转，效率最低 |

### 4.3 图片解密完整流程

```
加密图片URL → OkHttp获取byte[] → Base64编码(String) → createSymmetricCrypto().decrypt() → 解密byte[] → Base64编码(String) → data:image/ext;base64,...
```

**关键代码**：
```javascript
// 1. OkHttp获取加密图片byte[]
var client=new Packages.okhttp3.OkHttpClient();
var req=new Packages.okhttp3.Request.Builder().url(url).build();
var resp=client.newCall(req).execute();
var bytes=resp.body().bytes();
resp.close();  // ⚠️ 必须关闭，否则连接泄漏

// 2. byte[] → Base64字符串（createSymmetricCrypto的decrypt参数需要String）
var b64=Packages.android.util.Base64.encodeToString(bytes,2);  // flag=2=NO_WRAP

// 3. AES解密（decrypt()返回ByteArray，不是decryptStr()返回String！）
var decBytes=java.createSymmetricCrypto('AES/CBC/PKCS5Padding','f5d965df75336270','97b60394abc2fbe1').decrypt(b64);

// 4. 解密后的ByteArray → Base64字符串 → data URI
var d=Packages.android.util.Base64.encodeToString(decBytes,2);
var ext=url.substring(url.lastIndexOf('.')+1);
'data:image/'+ext+';base64,'+d;
```

### 4.4 `decrypt()` vs `decryptStr()` 的关键区别

| 方法 | 返回类型 | 适用场景 | 错误后果 |
|------|----------|----------|----------|
| `decrypt(data)` | ByteArray | 图片/视频等二进制内容 | — |
| `decryptStr(data)` | String | JSON/HTML等文本内容 | 图片会乱码（JPEG头部FFD8被当UTF-8解析） |

**源码依据**：`SymmetricCryptoAndroid.kt` L38-45
- `decrypt()` 调用 `cipher.doFinal()` 返回原始byte[]
- `decryptStr()` 继承自hutool父类，将byte[]转为String（UTF-8编码）

### 4.5 Base64编解码选择

| API | 兼容性 | 推荐度 |
|-----|--------|--------|
| `Packages.android.util.Base64.encodeToString(bytes, 2)` | Android 1.0+ | ✅ 推荐 |
| `Packages.android.util.Base64.decode(str, 2)` | Android 1.0+ | ✅ 推荐 |
| `Packages.java.util.Base64.getEncoder().encodeToString(bytes)` | Android 8.0+ | ❌ 低版本不兼容 |
| `java.base64Encode(str)` / `java.base64Decode(str)` | Legado内置 | ⚠️ 只接受String，不接受byte[] |

> flag=2 即 `Base64.NO_WRAP`，不添加换行符，适合嵌入data URI
