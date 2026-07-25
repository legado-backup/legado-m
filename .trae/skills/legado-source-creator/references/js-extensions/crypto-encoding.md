# JS 扩展函数参考 — 加密与编码

> 拆分自 js-extensions.md §四。Legado 书源 JS 环境中可调用的加密解密和编码解码扩展函数。
> 引擎为 Rhino 1.8.1（ES5），禁止使用 ES6+ 语法。
> 在 JS 中通过 `java` 变量调用，如 `java.md5Encode(str)`。

---

## 四、加密与编码

### MD5

```javascript
var md5_32 = java.md5Encode("hello");     // 32位 MD5
var md5_16 = java.md5Encode16("hello");   // 16位 MD5
```

| 函数 | 签名 | 返回值 | 频率 |
|------|------|--------|------|
| md5Encode | `md5Encode(str: String): String` | 32位 MD5 十六进制 | 极高 |
| md5Encode16 | `md5Encode16(str: String): String` | 16位 MD5 十六进制 | 高 |

---

### 摘要算法（digestHex / digestBase64Str）

```javascript
var sha256 = java.digestHex("hello", "SHA-256");       // SHA-256 摘要，返回十六进制
var sha1 = java.digestHex("hello", "SHA-1");            // SHA-1 摘要
var sha256b64 = java.digestBase64Str("hello", "SHA-256"); // SHA-256 摘要，返回 Base64
```

| 函数 | 签名 | 返回值 | 频率 |
|------|------|--------|------|
| digestHex | `digestHex(data: String, algorithm: String): String` | 十六进制摘要 | 高 |
| digestBase64Str | `digestBase64Str(data: String, algorithm: String): String` | Base64 摘要 | 中 |

支持的 algorithm：`MD5`、`SHA-1`、`SHA-256`、`SHA-384`、`SHA-512` 等 Java 标准算法名。

> **源码位置**：定义在 `JsEncodeUtils.kt` L456-476，`JsExtensions` 通过 `interface JsExtensions : JsEncodeUtils` 继承。

---

### HMAC（HMacHex / HMacBase64）

```javascript
var hmac = java.HMacHex("hello", "HmacSHA256", "secretKey");        // HMAC-SHA256，返回十六进制
var hmacB64 = java.HMacBase64("hello", "HmacSHA256", "secretKey");  // HMAC-SHA256，返回 Base64
```

| 函数 | 签名 | 返回值 | 频率 |
|------|------|--------|------|
| HMacHex | `HMacHex(data: String, algorithm: String, key: String): String` | 十六进制 HMAC | 高 |
| HMacBase64 | `HMacBase64(data: String, algorithm: String, key: String): String` | Base64 HMAC | 中 |

支持的 algorithm：`HmacMD5`、`HmacSHA1`、`HmacSHA256`、`HmacSHA512` 等。

> **源码位置**：定义在 `JsEncodeUtils.kt` L488-515，`JsExtensions` 通过继承可用。

---

### 对称加密（推荐：createSymmetricCrypto）

```javascript
// 创建加密器（推荐方式，支持 AES/DES/3DES 等）
var crypto = java.createSymmetricCrypto("AES/CBC/PKCS5Padding", "0123456789abcdef", "abcdef0123456789");

// 加密
var encryptedBase64 = crypto.encryptBase64("明文内容");   // 加密后返回 Base64
var encryptedHex = crypto.encryptHex("明文内容");         // 加密后返回十六进制
var encryptedBytes = crypto.encrypt("明文内容");          // 加密后返回字节数组

// 解密
var decrypted = crypto.decryptStr("Base64或Hex密文");     // 解密为字符串
var decryptedBytes = crypto.decrypt("Base64或Hex密文");   // 解密为字节数组
```

| 函数 | 签名 | 说明 |
|------|------|------|
| createSymmetricCrypto | `createSymmetricCrypto(transformation: String, key: ByteArray?, iv: ByteArray?): SymmetricCrypto` | key 和 iv 为字节数组 |
| createSymmetricCrypto | `createSymmetricCrypto(transformation: String, key: ByteArray): SymmetricCrypto` | key 是字节数组，无 iv |
| createSymmetricCrypto | `createSymmetricCrypto(transformation: String, key: String): SymmetricCrypto` | 无 IV，key 为字符串 |
| createSymmetricCrypto | `createSymmetricCrypto(transformation: String, key: String, iv: String?): SymmetricCrypto` | key 和 iv 都是字符串 |

**transformation 格式**：`算法/模式/填充`，如 `AES/CBC/PKCS5Padding`、`DES/ECB/PKCS5Padding`、`DESede/CBC/PKCS5Padding`

**SymmetricCrypto 可用方法**：
- `encrypt(data)` → ByteArray
- `encryptBase64(data)` → String
- `encryptHex(data)` → String
- `decrypt(data)` → ByteArray（自动识别 Hex 或 Base64 输入）
- `decryptStr(data)` → String

**使用频率**：极高

---

### 非对称加密（createAsymmetricCrypto）

```javascript
var crypto = java.createAsymmetricCrypto("RSA");
crypto.setPublicKey("Base64公钥");
crypto.setPrivateKey("Base64私钥");
var encrypted = crypto.encryptBase64("明文");
var decrypted = crypto.decryptStr("密文", true);  // true=用公钥解密
```

| 函数 | 签名 | 说明 |
|------|------|------|
| createAsymmetricCrypto | `createAsymmetricCrypto(transformation: String): AsymmetricCrypto` | 创建非对称加密器 |

> **源码位置**：定义在 `JsEncodeUtils.kt` L80-84，`JsExtensions` 通过继承可用。

**AsymmetricCrypto 可用方法**：
- `setPublicKey(key: String)` / `setPrivateKey(key: String)` — 设置密钥
- `encrypt(data)` / `encryptBase64(data)` — 加密
- `decrypt(data, usePublicKey?)` / `decryptStr(data, usePublicKey?)` — 解密

**使用频率**：中

---

### 签名（createSign）

```javascript
var sign = java.createSign("SHA256withRSA");
sign.setPrivateKey("Base64私钥");
sign.setPublicKey("Base64公钥");
var signatureHex = sign.signHex("待签名数据");
var verified = sign.verify("待验证数据", signatureHex.getBytes());
```

| 函数 | 签名 | 说明 |
|------|------|------|
| createSign | `createSign(algorithm: String): Sign` | 创建签名器 |

> **源码位置**：定义在 `JsEncodeUtils.kt` L87-91，`JsExtensions` 通过继承可用。

**Sign 可用方法**：
- `setPrivateKey(key: String)` / `setPublicKey(key: String)` — 设置密钥
- `sign(data)` / `signHex(data)` — 签名
- `verify(data, signBytes)` — 验签

**使用频率**：中

---

### 旧版 AES 方法（@Deprecated，仍可调用）

> 以下方法已标记 @Deprecated，推荐使用 `createSymmetricCrypto` 替代。但因 Web 端仍需调用，暂时保留。

| 函数 | 签名 | 替代方案 |
|------|------|----------|
| aesDecodeToString | `aesDecodeToString(str, key, transformation, iv): String?` | `createSymmetricCrypto(transformation, key, iv).decryptStr(str)` |
| aesDecodeArgsBase64Str | `aesDecodeArgsBase64Str(data, key, mode, padding, iv): String?` | `createSymmetricCrypto("AES/mode/padding", Base64.decode(key), Base64.decode(iv)).decryptStr(data)` |
| aesBase64DecodeToString | `aesBase64DecodeToString(str, key, transformation, iv): String?` | `createSymmetricCrypto(transformation, key, iv).decryptStr(str)` |
| aesEncodeToString | `aesEncodeToString(data, key, transformation, iv): String?` | `createSymmetricCrypto(transformation, key, iv).encryptBase64(data)` |
| aesEncodeToBase64String | `aesEncodeToBase64String(data, key, transformation, iv): String?` | `createSymmetricCrypto(transformation, key, iv).encryptBase64(data)` |
| aesEncodeArgsBase64Str | `aesEncodeArgsBase64Str(data, key, mode, padding, iv): String?` | `createSymmetricCrypto("AES/mode/padding", key, iv).encryptBase64(data)` |

> ⚠️ **源码 Bug**：`aesEncodeToString` 函数名暗示"加密并返回字符串"，但源码实现（JsEncodeUtils.kt L226）实际调用的是 `decryptStr(data)`（解密），而非 `encryptBase64(data)`（加密）。这是一个命名与实现不一致的 bug。如果需要加密功能，请使用 `createSymmetricCrypto(...).encryptBase64(data)` 替代。

---

### 旧版 DES/3DES 方法（@Deprecated，仍可调用）

| 函数 | 签名 | 替代方案 |
|------|------|----------|
| desDecodeToString | `desDecodeToString(data, key, transformation, iv): String?` | `createSymmetricCrypto(transformation, key, iv).decryptStr(data)` |
| desBase64DecodeToString | `desBase64DecodeToString(data, key, transformation, iv): String?` | `createSymmetricCrypto(transformation, key, iv).decryptStr(data)` |
| desEncodeToString | `desEncodeToString(data, key, transformation, iv): String?` | `createSymmetricCrypto(transformation, key, iv).encrypt(data)` |
| desEncodeToBase64String | `desEncodeToBase64String(data, key, transformation, iv): String?` | `createSymmetricCrypto(transformation, key, iv).encryptBase64(data)` |
| tripleDESDecodeStr | `tripleDESDecodeStr(data, key, mode, padding, iv): String?` | `createSymmetricCrypto("DESede/mode/padding", key, iv).decryptStr(data)` |
| tripleDESDecodeArgsBase64Str | `tripleDESDecodeArgsBase64Str(data, key, mode, padding, iv): String?` | 同上，key/iv 经 Base64 解码 |
| tripleDESEncodeBase64Str | `tripleDESEncodeBase64Str(data, key, mode, padding, iv): String?` | `createSymmetricCrypto("DESede/mode/padding", key, iv).encryptBase64(data)` |
| tripleDESEncodeArgsBase64Str | `tripleDESEncodeArgsBase64Str(data, key, mode, padding, iv): String?` | 同上，key 经 Base64 解码 |

---

### Base64 编解码

```javascript
var encoded = java.base64Encode("hello");             // 默认 NO_WRAP + NO_PADDING
var encoded = java.base64Encode("hello", 0);          // 指定 flags
var decoded = java.base64Decode("aGVsbG8=");          // 解码为字符串
var decoded = java.base64Decode("aGVsbG8=", "GBK");   // 指定字符集解码
var decoded = java.base64Decode("aGVsbG8=", 0);       // 指定 flags 解码
```

| 函数 | 签名 | 返回值 | 频率 |
|------|------|--------|------|
| base64Encode | `base64Encode(str: String): String?` | Base64 编码（flags=2） | 极高 |
| base64Encode | `base64Encode(str: String, flags: Int): String?` | Base64 编码（指定 flags） | 中 |
| base64Decode | `base64Decode(str: String?): String` | Base64 解码为字符串 | 极高 |
| base64Decode | `base64Decode(str: String?, charset: String): String` | 指定字符集解码 | 低 |
| base64Decode | `base64Decode(str: String, flags: Int): String` | 指定 flags 解码 | 低 |
| base64DecodeToByteArray | `base64DecodeToByteArray(str: String?): ByteArray?` | 解码为字节数组 | 中 |
| base64DecodeToByteArray | `base64DecodeToByteArray(str: String?, flags: Int): ByteArray?` | 指定 flags 解码为字节数组 | 低 |

**flags 常量**（Android Base64）：
- `0` = DEFAULT
- `1` = NO_PADDING
- `2` = NO_WRAP
- `8` = URL_SAFE

---

### Hex 编解码

```javascript
var hexStr = java.hexEncodeToString("hello");    // UTF-8 字符串转十六进制
var str = java.hexDecodeToString("68656c6c6f"); // 十六进制转 UTF-8 字符串
var bytes = java.hexDecodeToByteArray("68656c6c6f"); // 十六进制转字节数组
```

| 函数 | 签名 | 返回值 | 频率 |
|------|------|--------|------|
| hexEncodeToString | `hexEncodeToString(utf8: String): String?` | 十六进制字符串 | 高 |
| hexDecodeToString | `hexDecodeToString(hex: String): String?` | UTF-8 字符串 | 高 |
| hexDecodeToByteArray | `hexDecodeToByteArray(hex: String): ByteArray?` | 字节数组 | 中 |

---

### 字符串与字节数组互转

```javascript
var bytes = java.strToBytes("hello");              // UTF-8 编码
var bytes = java.strToBytes("hello", "GBK");       // 指定字符集编码
var str = java.bytesToStr(bytes);                   // UTF-8 解码
var str = java.bytesToStr(bytes, "GBK");            // 指定字符集解码
```

| 函数 | 签名 | 频率 |
|------|------|------|
| strToBytes | `strToBytes(str: String): ByteArray` | 中 |
| strToBytes | `strToBytes(str: String, charset: String): ByteArray` | 低 |
| bytesToStr | `bytesToStr(bytes: ByteArray): String` | 中 |
| bytesToStr | `bytesToStr(bytes: ByteArray, charset: String): String` | 低 |

---

### URI 编码

```javascript
var encoded = java.encodeURI("斗破苍穹");          // UTF-8 编码
var encoded = java.encodeURI("斗破苍穹", "GBK");   // 指定字符集编码
```

| 函数 | 签名 | 频率 |
|------|------|------|
| encodeURI | `encodeURI(str: String): String` | 高 |
| encodeURI | `encodeURI(str: String, enc: String): String` | 低 |
