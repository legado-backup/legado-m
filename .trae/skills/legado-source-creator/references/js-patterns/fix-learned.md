# 实战修复中学到的JS技巧 + 深度修复中新发现的JS技巧

> 基于14+22个源实际修复过程中深度分析JS代码的经验

---

## 十七、实战修复中学到的JS技巧

> 基于14个源实际修复过程中深度分析JS代码的经验

### API签名三步流程（阅友小说）

```javascript
// 第1步：获取时间戳
time = Math.round(new Date()/1000);
// 第2步：计算uth (HmacMD5)
uth = java.HMacHex("b313789b-2d2a-41ce-8982-26af5271fe7c&" + time, "HmacMD5", "snY%169j");
// 第3步：计算sign (HmacSHA256)
sign = java.HMacHex("/path+params+uth", "HmacSHA256", "snY%169j");
// 第4步：DES加密参数
_p = java.desEncodeToBase64String("params+uth+sign", "snY%169j", "DES/ECB/PKCS5Padding", "");
// 第5步：拼接URL
url = "/api/path?...&_p=" + java.encodeURI(_p);
```

### 参数排序+MD5签名（陶越文华）

```javascript
// jsLib中的签名函数
function o2p(json) {
    return Object.keys(json).sort()
        .map(function(key) { return encodeURIComponent(key) + "=" + json[key]; })
        .join("&");
}
function creatRequest(path, params) {
    var pm = Object.assign({}, params, default_pm);
    var spm = o2p(pm);  // 参数按key排序拼接
    pm.sign = java.md5Encode(spm + "&key=qcbook_123456");  // MD5签名
    return path + "?" + o2p(pm);
}
```

### 凯撒密码内容解密（阿巴小说/UC系）

```javascript
// 服务端返回加密内容 → 凯撒密码偏移解密 → Base64解码 → 明文
function caesar(e) {
    return e.split("").map(function(c) {
        return c.match(/[A-Za-z]/) ?
            String.fromCharCode((c.toLowerCase().charCodeAt(0) - 83) % 26 + 97) : c;
    }).join("");
}
java.base64Decode(caesar(result));
```

### AES/CBC + GZIP组合解密（酷匠网吧）

```javascript
// 服务端返回 iv@a2o@密文
var jm = String(jms.body.content).split("a2o@");
var key = "S3VqaWFuZ0FwcDc0NzYwNQ==";  // Base64编码的AES key
var iv = jm[0];   // 初始向量
var data = jm[1]; // 密文
// AES/CBC/PKCS5Padding解密 → GZIP解压 → 正文
decode(java.aesBase64DecodeToString(data, java.base64Decode(key),
    "AES/CBC/PKCS5Padding", java.base64Decode(iv)));
```

### Cloudflare绕过（太极小说等）

```javascript
// loginCheckJs自动检测CF验证页面
if (/_cf_|ge_ua|verify.php/ig.test(result.body()) && result.code() >= 403) {
    cookie.removeCookie(baseUrl);
    result = java.startBrowserAwait(result.url(), "验证", false);
}
```

### loginUrl自动注册设备（阅友小说）

```javascript
// 首次使用时自动注册设备获取token
var uuid = java.randomUUID();
var body = JSON.stringify({
    device_id: uuid,
    device_name: "Pixel 6",
    app_version: "3.5.0"
});
var res = java.ajax("https://xxx/api/register," + JSON.stringify({
    method: "POST",
    body: body,
    headers: {"Content-Type": "application/json"}
}));
var token = JSON.parse(res).token;
source.putVariable("token", token);
```

### JSON API bookList相对路径原则

```
bookList定位到数组元素后，字段规则只需相对key名：

❌ 错误：bookList=$.body.list, name=$.body.list[*].bookName
✅ 正确：bookList=$.body.list, name=bookName

❌ 错误：bookList=$.data.list, bookUrl=$.data.list[*].id
✅ 正确：bookList=$.data.list, bookUrl=https://xxx/book/{{$.id}}
```

---

## 十六、深度修复中新发现的JS技巧

> 基于22个源（9个JS搜索源+7个JS重度源+6个CSS源）的修复经验

### eval(String(source.loginUrl)) 代码复用模式

```javascript
// loginUrl中定义公共函数和初始化代码
// loginUrl: "https://xxx/login,...<js>function creatRequest(path,params){...}java.put('key','val')</js>"

// 在其他规则中复用loginUrl的代码
eval(String(source.loginUrl));
var url = creatRequest("/api/search", {keyword: key});
```

### JavaImporter调用Java加密库（移动阅读）

```javascript
// Rhino引擎中直接导入Java加密类
var javaImport = new JavaImporter();
javaImport.importPackage(Packages.javax.crypto.spec, Packages.javax.crypto, Packages.android.util);
with(javaImport) {
    function encryptByDES(massage, keydata) {
        var key = new DESKeySpec(keydata.getBytes());
        var cipher = Cipher.getInstance("DES/ECB/PKCS5Padding");
        cipher.init(Cipher.ENCRYPT_MODE, key);
        return Base64.encodeToString(cipher.doFinal(massage.getBytes()), 2);
    }
}
```

### payAction字段实现借阅逻辑（ARCHIVE配置）

```javascript
// payAction不限于VIP判断，可实现借阅/归还
"payAction": "https://archive.org/services/loans/loan/?identifier={{$.identifier}}&format=lcp"," +
    "{\"method\":\"POST\",\"body\":\"\"}"
// 借阅后通过source.getVariable()记录状态
```

### source.getLoginInfoMap()获取用户输入

```javascript
// 从登录界面获取用户输入的参数
var info = source.getLoginInfoMap();
var username = info.get("username");
var password = info.get("password");
```

### try{run}catch{} API版本回退（米读小说）

```javascript
// 故意触发异常实现API版本回退
try {
    run;  // 故意触发ReferenceError
} catch(e) {
    // 回退到v2 API
    var url = "https://api.midureader.com/fiction/search/searchV2";
}
```

### org.jsoup.Jsoup.parse()在JS中调用Java类

```javascript
// 比正则更可靠的HTML解析方式
var doc = org.jsoup.Jsoup.parse(html);
var token = doc.select("input[name=_token]").first().attr("value");
```

### 两步异步搜索API（鸠摩搜书）

```javascript
// 第1步：POST初始化搜索
var initUrl = "https://www.jiumodiary.com/init_hubs.php";
var initRes = java.ajax(initUrl + "," + JSON.stringify({method: "POST", body: "..."}));
var searchId = JSON.parse(initRes).id;

// 第2步：用id获取结果
var fetchUrl = "https://www.jiumodiary.com/ajax_fetch_hubs.php";
var result = java.ajax(fetchUrl + "," + JSON.stringify({method: "POST", body: "id=" + searchId}));
```

### @tag语法过时替换规则

```
❌ 过时：.u-list@tag.li → ✅ 标准：.u-list li
❌ 过时：a.2@text → ✅ 标准：.bauthor a@text（用class替代索引）
❌ 过时：td.-1:-2@text → ✅ 标准：td.5@text（避免负索引）
❌ 过时：img@src → ✅ 标准：img@data-original（懒加载图片）
```

### XOR + deflate 解密内联页面数据（小黄书视频站）

```javascript
// Vue.js SPA网站将所有数据加密嵌入HTML内联脚本
// 解密流程: APP.Index('token') → base64url → XOR(密钥) → deflate → JSON
var match = result.match(/APP\.Index\('([^']+)'\)/);
if (match) {
    var token = match[1];
    var key = 'UC2FmMyG928hRZY4';
    var b64 = token.replace(/-/g, '+').replace(/_/g, '/');
    while (b64.length % 4 !== 0) b64 += '=';
    var decoded = java.base64DecodeToByteArray(b64);
    var keyBytes = new java.lang.String(key).getBytes('UTF-8');
    // XOR in-place，避免创建新数组
    for (var i = 0; i < decoded.length; i++) {
        decoded[i] = (decoded[i] ^ keyBytes[i % keyBytes.length]) & 0xFF;
    }
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
        var hexStr = '';
        for (var j = 0; j < bodyLen; j++) hexStr += '00';
        body = java.hexDecodeToByteArray(hexStr);
        for (var j = 0; j < bodyLen; j++) body[j] = decoded[j + 1];
    }
    var data = JSON.parse(new java.lang.String(body, 'UTF-8'));
    result = JSON.stringify(data.vod.list);
}
```

⚠️ **Rhino限制**：`java.lang.reflect.Array.newInstance()` 被RhinoClassShutter禁止！用 `java.hexDecodeToByteArray()` 或 `new byte[n]` 替代

### DES/ECB加密vod_id构造详情URL（小黄书视频站）

```javascript
// 网站前端: const secretKey = CryptoJS.enc.Utf8.parse("UC2FmMyG928hRZY4");
// CryptoJS.DES.encrypt(vod_id, secretKey, {mode:ECB, padding:Pkcs7})
// CryptoJS.enc.Utf8.parse() = WordArray密钥，直接用UTF-8字节
// DES只需8字节，CryptoJS自动截取前8字节 = "UC2FmMyG"
var vodId = String(result.get('vod_id'));
var crypto = java.createSymmetricCrypto('DES/ECB/PKCS5Padding', 'UC2FmMyG', null);
var encrypted = crypto.encryptHex(vodId);
result = baseUrl + 'vod/details/' + encrypted;
```

⚠️ **关键**：必须区分CryptoJS的两种密钥模式！
- `CryptoJS.enc.Utf8.parse("key")` = WordArray密钥，直接用UTF-8字节，DES截取前8字节 → Legado中直接传前8字符的String
- 字符串密钥 = EVP_BytesToKey(MD5)派生 → Legado中需手动MD5派生后传ByteArray
- **必须看网站源码确认用的是哪种！**

### Vue.js SPA随机class名站点的articleList写法

```json
{
  "ruleArticles": "<js>解密逻辑返回JSON数组</js>",
  "ruleTitle": "$.vod_name",
  "ruleLink": "<js>DES加密vod_id拼接URL</js>",
  "ruleImage": "<js>补全图片URL前缀</js>",
  "ruleDescription": "$.vod_duration"
}
```

⚠️ **RssSource字段是扁平的**：`ruleArticles`/`ruleTitle`/`ruleLink`/`ruleImage`/`ruleDescription`/`rulePubDate`/`ruleContent` 都是RssSource实体的独立String?字段，不是嵌套在ruleArticles对象中！
