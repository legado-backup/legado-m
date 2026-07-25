# 加密相关陷阱

> 加密/解密/编码在Legado JS环境中的常见陷阱。

## 2.1 CryptoJS 在 Rhino 中不可用

**现象**：书源 JS 规则中调用 `CryptoJS.AES.encrypt()` 报错。

**原因**：Rhino 是纯 Java JS 引擎，没有浏览器环境，CryptoJS 是浏览器/Node.js 库。

**解决方案**：使用 Java Crypto API 互操作：

**⚠️ 禁止手动 javax.crypto！** 以下代码仅为说明原理，**实际写规则时必须用 `java.createSymmetricCrypto()`**：

```javascript
var aesKey = new javax.crypto.spec.SecretKeySpec(keyBytes, 'AES');
var cipher = javax.crypto.Cipher.getInstance('AES/CBC/PKCS5Padding');
cipher.init(javax.crypto.Cipher.ENCRYPT_MODE, aesKey, ivSpec);
var encrypted = cipher.doFinal(plainBytes);
```

**✅ 正确做法**：
```javascript
var crypto = java.createSymmetricCrypto('AES/CBC/PKCS5Padding', key, iv);
var encrypted = crypto.encryptBase64(data);
var decrypted = crypto.decryptStr(encryptedData);
```

## 2.2 ZeroPadding 在 Java Crypto 中不支持（唯一例外）

**现象**：网站使用 ZeroPadding，但 Java Crypto 只有 `PKCS5Padding` 和 `NoPadding`。

**解决方案**：用 `NoPadding` + 手动填充零字节：

**⚠️ 这是唯一允许手动 javax.crypto 的例外！** 因为 `java.createSymmetricCrypto` 不支持 ZeroPadding，只能用 NoPadding + 手动填充零字节。其他所有加密场景仍必须用 `java.createSymmetricCrypto`。

```javascript
var padLen = (16 - inputBytes.length % 16) % 16;
var paddedInput = new byte[inputBytes.length + padLen];
for (var i = 0; i < inputBytes.length; i++) {
    paddedInput[i] = inputBytes[i];
}
// paddedInput 剩余位置自动为 0（ZeroPadding）
var cipher = javax.crypto.Cipher.getInstance('AES/CBC/NoPadding');
```

## 2.3 Base64 兼容性问题

**现象**：`java.util.Base64` 在 Android 低版本上不可用（API 26+ 才有）。

**解决方案**：使用 `android.util.Base64`：
```javascript
var base64 = android.util.Base64.encodeToString(bytes, android.util.Base64.NO_WRAP);
var decoded = android.util.Base64.decode(str, android.util.Base64.DEFAULT);
```

## 2.4 JS 混淆代码分析

**现象**：网站加密函数经过混淆（变量名如 `_0x582c`、`_0x5cc227`），难以直接阅读。

**分析技巧**：
1. 搜索关键字符串常量：`'AES'`、`'CBC'`、`'encrypt'`、`'CryptoJS'`
2. 找到密钥/IV 的硬编码字符串（通常是16位十六进制字符串）
3. 识别加密模式：`CryptoJS.mode.CBC`、`CryptoJS.pad.ZeroPadding`
4. 用已知明文-密文对验证加密逻辑

## 2.5 Vue.js SPA 多层加密站（XOR + deflate + AES + DES）

**现象**：网站首页返回空壳HTML，所有内容通过JS加密渲染。页面内联加密数据，API请求参数加密，视频详情URL使用DES加密ID。

**典型架构**（小黄书视频站实测）：
```
首页HTML → XOR(0x60)解密 → Vue.js SPA
  └─ 内联数据: APP.Index('token') → base64url解码 → XOR(密钥) → deflate解压 → JSON
  └─ API请求: 参数 → AES/CBC加密 → 服务端
  └─ 详情URL: vod_id → DES/ECB/PKCS7加密 → Hex编码 → /vod/details/{hex}
  └─ 视频播放: DPlayer + HLS.js 播放m3u8
```

**关键发现**：
1. **CSS选择器不可用**：Vue组件使用 `generateUniqueID()` 生成随机class名，每次部署都不同
2. **视频链接不在 `<a>` 标签中**：使用Vue的 `@click="toLink"` 事件处理，渲染后没有href
3. **必须解密内联数据**：视频列表数据嵌入在加密的内联脚本中，需要JS解密后用JSONPath提取

**解决方案**：使用 `<js>` 规则解密内联数据，替代CSS选择器：
```javascript
// articleList规则：解密APP.Index('token')中的视频列表
var match = html.match(/APP\.Index\('([^']+)'\)/);
var token = match[1];
var key = '密钥';
var b64 = token.replace(/-/g, '+').replace(/_/g, '/');
while (b64.length % 4 !== 0) b64 += '=';
var decoded = java.base64DecodeToByteArray(b64);
// XOR解密（in-place修改decoded数组，避免创建新数组）
var keyBytes = new java.lang.String(key).getBytes('UTF-8');
for (var i = 0; i < decoded.length; i++) {
    decoded[i] = (decoded[i] ^ keyBytes[i % keyBytes.length]) & 0xFF;
}
// deflate解压（flag==1时）
var flag = decoded[0];
var bodyLen = decoded.length - 1;
var body;
if (flag == 1) {
    var inflater = new java.util.zip.Inflater(true);
    inflater.setInput(decoded, 1, bodyLen);
    var output = new java.io.ByteArrayOutputStream();
    var buffer = new byte[4096];
    while (!inflater.finished()) {
        var count = inflater.inflate(buffer);
        if (count > 0) output.write(buffer, 0, count);
    }
    inflater.end();
    body = output.toByteArray();
} else {
    // 创建空字节数组：用hexDecodeToByteArray替代java.lang.reflect.Array
    var hexStr = '';
    for (var j = 0; j < bodyLen; j++) hexStr += '00';
    body = java.hexDecodeToByteArray(hexStr);
    for (var j = 0; j < bodyLen; j++) body[j] = decoded[j + 1];
}
var data = JSON.parse(new java.lang.String(body, 'UTF-8'));
result = JSON.stringify(data.vod.list);
```

⚠️ **Rhino限制**：`java.lang.reflect.Array.newInstance()` 被RhinoClassShutter禁止！创建字节数组应使用 `java.hexDecodeToByteArray()` 或 `new byte[n]`（Rhino支持Java数组创建语法）

## 2.6 CryptoJS DES 字符串密钥的密钥派生

**现象**：网站使用 `CryptoJS.DES.encrypt(plaintext, "passphrase", {mode: ECB, padding: Pkcs7})`，但直接用passphrase作为DES密钥在Java中加密结果不一致。

**原因**：CryptoJS使用字符串密钥时，会通过OpenSSL的 `EVP_BytesToKey` 算法派生实际密钥（MD5哈希），而非直接使用原始字符串。

**解决方案**：区分CryptoJS两种密钥模式，在Legado中正确实现：

**模式A：`CryptoJS.enc.Utf8.parse("key")` — WordArray密钥（最常见）**
```javascript
// 网站前端: const secretKey = CryptoJS.enc.Utf8.parse("UC2FmMyG928hRZY4");
// CryptoJS自动截取前8字节作为DES密钥 = "UC2FmMyG"
var crypto = java.createSymmetricCrypto('DES/ECB/PKCS5Padding', 'UC2FmMyG', null);
var encrypted = crypto.encryptHex(String(vodId));
result = baseUrl + 'vod/details/' + encrypted;
```

**模式B：字符串密钥 — EVP_BytesToKey(MD5)派生**
```javascript
// 网站前端: CryptoJS.DES.encrypt(plaintext, "passphrase", {mode:ECB})
// EVP_BytesToKey: MD5(passphrase)前8字节作为DES密钥
var md5Hex = java.md5Encode(passphrase);
var desKeyHex = md5Hex.substring(0, 16);
var desKeyBytes = java.hexDecodeToByteArray(desKeyHex);
var crypto = java.createSymmetricCrypto('DES/ECB/PKCS5Padding', desKeyBytes, null);
var encrypted = crypto.encryptHex(String(vodId));
```

⚠️ **关键区别**：
- `CryptoJS.enc.Utf8.parse("key")` 和字符串密钥的派生方式完全不同！
- **必须看网站源码确认用的是哪种**：找 `CryptoJS.enc.Utf8.parse` = 模式A，找纯字符串 = 模式B
- `java.createSymmetricCrypto('DES/ECB/PKCS5Padding', '8字符密钥')` 传8字符String时，UTF-8字节正好8字节=DES密钥
- `java.lang.reflect.Array.newInstance()` 被RhinoClassShutter禁止，用 `java.hexDecodeToByteArray()` 或 `new byte[n]` 替代
