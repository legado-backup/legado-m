# 加密认证

> MD5/SHA 密码加密、动态签名/Token 生成、AES/DES 对称加密、搜索参数加密实战案例。

## 3.1 MD5/SHA 密码加密

```javascript
// loginCheckJs 中
var password = java.get('password');  // 用户输入的密码
var encrypted = java.md5Encode(password + 'salt123');
// 提交加密后的密码
```

可用的加密函数（JsEncodeUtils）：

| 函数 | 说明 |
|------|------|
| `java.md5Encode(str)` | MD5 32位小写 |
| `java.md5Encode16(str)` | MD5 16位小写 |
| `java.base64Encode(str)` | Base64 编码 |
| `java.base64Decode(str)` | Base64 解码 |
| `java.hexEncode(str)` | Hex 编码 |

## 3.2 动态签名/Token 生成

```javascript
// 在 searchUrl 中用 JS 计算签名
// 搜索URL: @js:'/api/search?q='+key+'&sign='+java.md5Encode(key+'secret')
```

## 3.3 AES/DES 对称加密

使用 `java.createSymmetricCrypto()` 内置方法（基于 hutool SymmetricCrypto）：

```javascript
// searchUrl 的 JS 计算
var sign = java.createSymmetricCrypto('AES/ECB/PKCS5Padding', 'your-key-12345678', null).encryptBase64(keyword);
'/api/search?q=' + encodeURI(keyword) + '&sign=' + encodeURIComponent(sign);
```

> ⚠️ `java.aesEncrypt` / `java.aesDecrypt` 不存在，请使用 `java.createSymmetricCrypto().encryptBase64()` / `java.createSymmetricCrypto().decryptStr()` 替代。详见下方 3.4 节。

## 3.4 搜索参数加密（实战案例）

> **核心场景**：网站搜索 URL 中的关键词经过 AES 加密，如 `/search-0-1-{encrypted}.html`

### 步骤一：分析加密逻辑

1. 获取页面 JS 源码（curl 获取原始 HTML，找到 `<script>` 标签中的加密函数）
2. 识别加密方式：本例为 `CryptoJS.AES.encrypt()` + `ZeroPadding` + `CBC` 模式
3. 提取密钥和 IV：从 JS 源码中找到硬编码的 Key 和 IV（可能经过混淆，需耐心反混淆）
4. 验证加密结果：用已知明文-密文对验证加密逻辑是否正确

### 步骤二：使用 Legado 内置加密方法

> ⚠️ **核心原则：永远优先使用 `java.createSymmetricCrypto()`**
> Legado 原生内置了完整的对称加密工具链（基于 hutool SymmetricCrypto），**禁止手动调用 `javax.crypto.*`**。手动调用的代码不仅冗长（500+字符），还会踩 Rhino 的 `java.lang.String` 未定义陷阱。

```javascript
// ✅ 正确：Legado 内置方法，一行搞定
var base64 = java.createSymmetricCrypto('AES/CBC/NoPadding', '2d4ebb7cb767dab1', '7563ca4af41bd0fb').encryptBase64(key);
var encoded = encodeURIComponent(base64);
var url = '/search-0-1-' + encoded + '.html';
if (page > 1) {
    url = '/search-0-1-' + encoded + '-' + page + '.html';
}
url;
```

对比：

| 方式 | 代码量 | 可靠性 | 是否踩 Rhino 陷阱 |
|------|--------|--------|-------------------|
| ❌ 手动 `javax.crypto.*` | 500+ 字符 | 低（踩 String/byte 陷阱） | 是 |
| ✅ `java.createSymmetricCrypto()` | **1 行核心调用** | 高（官方封装） | 否 |

### `java.createSymmetricCrypto()` API 速查

> 来自 [JsEncodeUtils.kt](../app/src/main/java/io/legado/app/help/JsEncodeUtils.kt)，通过 `java` 变量在 JS 中直接调用。

**创建实例**：
```javascript
// 参数：transformation, key, iv（ECB模式可省略iv）
var crypto = java.createSymmetricCrypto('AES/CBC/PKCS5Padding', 'your-key-16ch!', 'your-iv-16ch!!');
```

**常用 transformation 格式**：

| 算法 | 模式 | 填充 | 完整字符串 |
|------|------|------|-----------|
| AES | CBC | PKCS5Padding | `AES/CBC/PKCS5Padding` |
| AES | CBC | NoPadding（=ZeroPadding） | `AES/CBC/NoPadding` |
| AES | ECB | PKCS5Padding | `AES/ECB/PKCS5Padding` |
| DES | ECB | PKCS5Padding | `DES/ECB/PKCS5Padding` |
| DESede (3DES) | CBC | PKCS5Padding | `DESede/CBC/PKCS5Padding` |

**可用方法**：

| 方法 | 返回值 | 说明 |
|------|--------|------|
| `.encryptBase64(data)` | String | 加密 → Base64 字符串 ✅最常用 |
| `.encryptHex(data)` | String | 加密 → Hex 字符串 |
| `.encrypt(data)` | byte[] | 加密 → 字节数组 |
| `.decryptStr(data)` | String | 解密 Base64/Hex → 字符串（⚠️仅文本内容） |
| `.decrypt(data)` | byte[] | 解密 Base64/Hex → 字节数组（⚠️图片/视频必须用此方法） |

**其他内置加密方法**（同样通过 `java` 对象调用）：

| 方法 | 说明 | 示例 |
|------|------|------|
| `java.md5Encode(str)` | MD5 32位小写 | `java.md5Encode('password')` |
| `java.md5Encode16(str)` | MD5 16位小写 | `java.md5Encode16('password')` |
| `java.base64Encode(str)` | Base64 编码 | `java.base64Encode('hello')` |
| `java.base64Decode(str)` | Base64 解码 | `java.base64Decode('aGVsbG8=')` |
| `java.hexEncode(str)` | Hex 编码 | `java.hexEncode('hello')` |
| `java.digestHex(data, algo)` | 摘要算法 | `java.digestHex(data, 'SHA-256')` |
| `java.HMacHex(data, algo, key)` | HMAC 签名 | `java.HMacHex(data, 'HmacSHA256', 'secret')` |

### 关键注意事项

| 陷阱 | 说明 | 解决方案 |
|------|------|----------|
| CryptoJS 不可用 | Rhino 环境无浏览器库 | 使用 `java.createSymmetricCrypto()` |
| ZeroPadding 不支持 | hutool 无 ZeroPadding | 用 `NoPadding` 替代（效果相同） |
| javax.crypto 陷阱 | `java.lang.String` 在 Rhino 中未定义 | **不要手动调 javax.crypto，用 java 内置方法** |
| 密钥长度 | AES 要求 16/24/32 字节 | Key 必须是 16/24/32 个字符（对应 128/192/256 位） |
| IV 长度 | AES CBC 要求 16 字节 | IV 必须是 16 个字符 |
| JS 混淆 | 网站加密函数可能经过混淆 | 耐心反混淆，关注 CryptoJS 调用和字符串常量 |
