# CF 盾检测与降级模式

> 影响范围：1/7 真实源（1080zyk 优质资源）

## 模式特征

Cloudflare 返回 JS challenge 页面，JVM 仿真端无法执行 JS，导致请求被拦截。

## 检测特征

- HTTP 响应状态码 403/503
- 响应体包含 `challenge`、`cf-`、`__cf_bm`、`_cf_chl` 等关键词
- 响应头 `Server: cloudflare`

## 处理流程

```
检测到CF盾 → 标记unverifiable → 输出用户操作建议 → 降级到真机验证
```

## 用户操作建议

当检测到 CF 盾时，输出以下建议：
```
[需用户介入] CF 盾检测到，JVM 无法模拟 JS challenge
建议操作：
1. 在手机端 Legado App 中导入该源
2. 使用 webView 模式访问目标网站
3. 手动完成 CF 验证后，导出 Cookie
4. 将 Cookie 导入源配置（enabledCookieJar: true）
```

## 仿真端局限性

JVM 仿真端使用 jsoup 发送 HTTP 请求，无法执行 JavaScript：
- ❌ 无法执行 CF 的 JS challenge
- ❌ 无法模拟浏览器指纹
- ✅ 可以检测 CF 盾并输出降级建议

## 验证结果

| 源 | 结果 | 说明 |
|----|------|------|
| 1080zyk | 失败（符合预期）| CF 盾拦截，标记为需用户介入 |
| 611371056 | 通过 | CF 检测代码存在但未触发（网站未启用 CF）|
