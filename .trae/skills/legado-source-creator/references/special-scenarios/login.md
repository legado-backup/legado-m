# 登录处理

> 标准登录、Cookie 登录、详情页初始化 JS（init 字段）的完整处理方案。

## 1.1 标准登录流程

```json
{
  "loginUrl": "https://www.example.com/login",
  "loginUi": "[{\"name\":\"username\",\"type\":\"text\"},{\"name\":\"password\",\"type\":\"password\"}]",
  "loginCheckJs": "result.includes('退出登录') ? $.ok : $.no"
}
```

**loginUi** JSON 数组，每项定义登录表单字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `name` | String | 字段名称（提交时的 key） |
| `type` | String | text/number/password/email/select |
| `value` | String? | 默认值 |

**loginCheckJs** — 登录成功后执行的 JS，判断是否登录成功：
- 返回/包含 `ok` 或 `true` → 登录成功
- 返回/包含 `no` 或 `false` → 登录失败

## 1.2 带 Cookie 的登录后请求

```json
{
  "enabledCookieJar": true,
  "loginUrl": "https://www.example.com/login",
  "loginCheckJs": "java.cookieManager.put('token', result.match(/token=([^;]+)/)[1]); result.includes('success')"
}
```

设置 `enabledCookieJar: true` 后，登录获取的 Cookie 会自动持久化，后续请求自动携带。

## 1.3 服务端 Cookie 年龄验证（无需登录框）

> 验证日期：2026-07-20
> 源码依据：CookieManager.kt L57-77 mergeCookies()、Rss.kt L40-84 loginCheckJs 执行链

**场景**：站点使用服务端 Set-Cookie 校验用户年龄，而非前端弹框。用户首次访问时，服务端返回年龄确认页面，用户点击确认后服务端 Set-Cookie（如 `YES_Eighteen=IamOverEighteenYearsOld`），后续请求携带此 Cookie 即可跳过验证。

**三层自动破除方案**（无需用户手动操作）：

| 层级 | 字段 | 作用 | 优先级 |
|------|------|------|--------|
| Layer 1 | `header` Cookie | 预置 Cookie，首次请求即携带，直接跳过验证 | 最高（静态） |
| Layer 2 | `loginCheckJs` | 检测验证页 + 清除过期 Cookie + 重设，动态修复 | 中（动态） |
| Layer 3 | `injectJs` | WebView 层面自动点击确认按钮，兜底保护 | 最低（WebView） |

**配置示例**：
```json
{
  "enabledCookieJar": true,
  "header": "{\"Cookie\": \"YES_Eighteen=IamOverEighteenYearsOld\"}",
  "loginCheckJs": "var src=result.body();if(src&&src.indexOf('Eighteen_declaration')>-1){cookie.removeCookie(baseUrl);cookie.setCookie(baseUrl,'YES_Eighteen=IamOverEighteenYearsOld')}result",
  "injectJs": "(function(){var btn=document.getElementById('fwin_dialog_submit');if(btn){btn.click()}})()"
}
```

**关键技巧 — loginCheckJs 中必须先 `removeCookie` 再 `setCookie`**：

`CookieManager.loadRequest()` 中 `mergeCookies(requestCookie, cookie)` 的合并逻辑是 **CookieStore 值覆盖 header 值**（`acc.apply { putAll(cookieMap) }`）。如果 CookieStore 中存有过期/错误的 Cookie，即使 header 中预置了正确的 Cookie，合并后仍然会被 CookieStore 的过期值覆盖。

**因此 loginCheckJs 的正确写法**：
1. 先 `cookie.removeCookie(baseUrl)` — 清除 CookieStore 中的过期值
2. 再 `cookie.setCookie(baseUrl, 'CORRECT_COOKIE')` — 写入正确值
3. 最后返回 `result` — loginCheckJs 必须返回 StrResponse

**CookieStore vs header Cookie 合并顺序**（源码：CookieManager.kt L103-109）：
```kotlin
fun mergeCookiesToMap(vararg cookies: String?): MutableMap<String, String> {
    return cookies.filterNotNull().map {
        CookieStore.cookieToMap(it)
    }.reduce { acc, cookieMap ->
        acc.apply { putAll(cookieMap) }  // ← 后者覆盖前者！CookieStore > header
    }
}
```

**真机验证**：24/24项解析成功，列表正确显示，无需用户手动操作。

## 1.4 详情页初始化 JS（`init`）

在 `BookInfoRule.init` 中编写 JS，在获取详情页前执行：

```json
{
  "ruleBookInfo": {
    "init": "java.cookieStore.setCookie(source.getKey(), 'session=' + sessionId)"
  }
}
```
