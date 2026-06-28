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

## 1.3 详情页初始化 JS（`init`）

在 `BookInfoRule.init` 中编写 JS，在获取详情页前执行：

```json
{
  "ruleBookInfo": {
    "init": "java.cookieStore.setCookie(source.getKey(), 'session=' + sessionId)"
  }
}
```
