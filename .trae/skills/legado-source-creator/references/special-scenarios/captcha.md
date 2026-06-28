# 验证码处理

> 图片验证码、滑块验证码、验证码后 Token 传递的完整处理方案。

## 2.1 图片验证码（手动输入）

使用 `getVerificationCode()` JS 函数弹出验证码对话框：

```javascript
// 在 loginCheckJs 或其他 JS 规则中调用
var code = getVerificationCode('https://example.com/captcha.jpg');
// code 为用户输入的验证码
```

## 2.2 滑块/行为验证码

使用 `startBrowserAwait()` 打开内置浏览器让用户手动完成：

```javascript
var response = startBrowserAwait('https://example.com/verify', '验证页面');
// 用户在浏览器中完成滑块验证后，返回验证后的页面内容
// response.url — 最终页面URL
// response.body — 最终页面HTML
```

## 2.3 验证码后的Token传递

```javascript
// loginCheckJs
var code = getVerificationCode(captchaUrl);
// 用验证码请求登录
var loginResult = ajax({
    url: loginUrl,
    method: 'POST',
    body: 'username=' + username + '&password=' + password + '&captcha=' + code
});
// 解析登录结果中的token
var token = JSON.parse(loginResult).token;
java.cookieManager.put('auth_token', token);
result.includes('success') ? 'ok' : 'no';
```
