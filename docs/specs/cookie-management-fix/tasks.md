# Cookie 管理链路修复 — 任务清单

## 1. 准备工作
- [ ] 1.1 阅读当前 CookieManager.kt / CookieStore.kt / ReadRssActivity.kt / BackstageWebView.kt 源码确认行号
- [ ] 1.2 阅读原版 Legado 仓库对应文件，确认是否已有修复

## 2. P0 修复：ReadRssActivity WebView Cookie 回写 CookieStore
- [ ] 2.1 在 ReadRssActivity.onPageFinished 中添加 WebView CookieManager → CookieStore 同步代码
- [ ] 2.2 验证：导入含年龄验证的订阅源，在 ReadRssActivity 中通过验证后返回列表页刷新，确认不再弹出验证

## 3. P1 修复：CookieStore 过期 Cookie 自动清理
- [ ] 3.1 在 CookieStore.getCookie() 中添加 max-age=0 过期过滤
- [ ] 3.2 （可选）添加 Cookie 写入时间戳记录，实现完整过期检查
- [ ] 3.3 验证：设置 max-age=0 的 Cookie 后，getCookie() 不再返回该 Cookie

## 4. P2 修复：applyToWebView() 移除全局清空
- [ ] 4.1 移除 CookieManager.applyToWebView() 中的 removeSessionCookies(null) 调用
- [ ] 4.2 验证：先访问源A登录成功，再访问源B，回到源A时仍保持登录状态

## 5. P3 修复：AnalyzeUrl.saveCookie() 死代码处理
- [ ] 5.1 移除 AnalyzeUrl.saveCookie() 方法
- [ ] 5.2 Grep 确认无其他调用点

## 6. P4 修复：BackstageWebView Cookie 域名匹配
- [ ] 6.1 修改 BackstageWebView.onPageFinished 中 Cookie 存储使用请求 URL 域名
- [ ] 6.2 验证：使用含重定向的源，确认 Cookie 域名与 OkHttp 请求域名一致

## 7. 综合验证
- [ ] 7.1 编译 Debug APK
- [ ] 7.2 安装到模拟器
- [ ] 7.3 导入含年龄验证的订阅源，端到端测试（登录 → 列表 → 详情 → 返回列表刷新）
- [ ] 7.4 多源切换测试（源A登录 → 源B浏览 → 源A仍保持登录）
- [ ] 7.5 更新 updateLog.md

## 8. 文档同步
- [ ] 8.1 更新 docs/project-flow/architecture/ 中 Cookie 相关文档
- [ ] 8.2 更新 skill 参考文档中的 Cookie 同步说明
- [ ] 8.3 更新 docs/INDEX.md
