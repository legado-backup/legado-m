# 加密/签名模式

> 基于 yckceo.com 社区 23,881 个书源 + 2,702 个订阅源的深度分析
> 453个加密/签名示例

### AES解密

```javascript
var crypto = java.createSymmetricCrypto('AES/CBC/PKCS5Padding', key, iv);
var decrypted = crypto.decryptBase64ToString(encrypted);
```

### MD5签名

```javascript
var sign = java.md5Encode(key + body + secret);
headers['X-Sign'] = sign;
```

### X-Gorgon签名（抖音/番茄系）

```javascript
// 需要引入xGorgon函数
xGorgon("/api/category/landing?", body)
```

### Mirages主题图片AES解密（WordPress+Mirages主题）

> 适用网站：91大事件(91dasj.com)、51吃瓜(51cg1.com)等WordPress+Mirages主题网站
> 源码验证：Mirages主题的`loadBackgroundImage`函数检测CDN路径后，用`$.ajax({responseType:'arraybuffer'})`获取二进制，再调用`decryptImage()`解密

**特征识别**：
- 列表页图片通过`loadBannerDirect('URL',...)`JS调用加载
- 详情页图片真实URL在`data-xkrkllgl`属性中（`src`是loading占位图）
- CDN路径判断：URL含`/xiao/`、`/upload_01/`、`/uploads/`、`/upload/upload/`的图片需要解密
- 加密密钥通常在`/usr/plugins/tbxw/js/zzz.js`的`decryptImage`函数中（CryptoJS库）

**列表页ruleImage完整代码**：
```javascript
@js:var url='';var scripts=result.select('script');
for(var i=0;i<scripts.size();i++){
  var s=scripts.get(i).data()+'';
  var m=s.match(/loadBannerDirect\('([^']+)',/);
  if(m){url=m[1];break;}
}
if(url){
  // CDN路径判断（与Mirages主题is_cdnimg函数一致）
  if(url.indexOf('/xiao/')>-1||url.indexOf('/upload_01/')>-1||url.indexOf('/uploads/')>-1||url.indexOf('/upload/upload/')>-1){
    try{
      // 关键：java.ajax()返回String无法获取二进制，必须用OkHttp
      var client=new Packages.okhttp3.OkHttpClient();
      var req=new Packages.okhttp3.Request.Builder().url(url).build();
      var resp=client.newCall(req).execute();
      var bytes=resp.body().bytes();
      resp.close();
      // byte[]→Base64字符串→createSymmetricCrypto解密→Base64字符串→data URI
      var b64=Packages.android.util.Base64.encodeToString(bytes,2);
      var decBytes=java.createSymmetricCrypto('AES/CBC/PKCS5Padding','f5d965df75336270','97b60394abc2fbe1').decrypt(b64);
      var d=Packages.android.util.Base64.encodeToString(decBytes,2);
      var ext=url.substring(url.lastIndexOf('.')+1);
      'data:image/'+ext+';base64,'+d;
    }catch(e){'';}
  }else{url;}  // 非CDN图片直接返回URL
}else{'';}
```

**详情页ruleContent图片解密**：
```javascript
// 优先读取data-xkrkllgl属性获取真实URL
var src=img.attr('data-xkrkllgl');
if(!src){src=img.attr('src');}
// CDN路径判断+解密逻辑同上
```

**关键注意事项**：
1. ⚠️ **`java.ajax()`返回String，不能获取二进制数据！** 必须用`Packages.okhttp3.OkHttpClient()`获取byte[]
2. ⚠️ **`decrypt()`返回ByteArray（二进制），`decryptStr()`返回String（文本）**。图片解密必须用`decrypt()`
3. ⚠️ **`Packages.android.util.Base64`**优于`java.util.Base64`，Android低版本兼容性更好
4. ⚠️ Key/IV需从目标网站的JS中提取，不同网站可能不同
5. ⚠️ `resp.close()`必须调用，否则连接泄漏
