# Spec: RSS 订阅源年龄验证自动绕过

## Intent

优化含服务端年龄验证（18+弹框）的 RSS 订阅源 JSON 配置，使 Legado App 用户无需手动点击确认按钮即可直接访问内容。当前该类源首次加载时，服务端返回全页验证页而非真实内容，用户必须手动点击"同意"按钮才能继续，体验差且不符合 Legado"一键订阅"的理念。

## Scope

### In Scope

- 分析目标站点（源[N]）的服务端年龄验证机制
- 通过修改订阅源 JSON 配置实现自动绕过
- 覆盖 OkHttp 层（文章列表/内容获取）和 WebView 层（文章阅读）
- 输出优化后的完整订阅源 JSON

### Out of Scope

- 修改 Legado App 源码（本次仅优化 JSON 配置）
- 处理 Cloudflare 等其他类型的反爬机制
- 处理前端 JS 弹框（本次目标站点为服务端验证）
- 处理需要账号登录的验证场景

## Approach

### Selected Approach: 三层防护 Cookie 预置 + 自动验证

**核心原理**：目标站点的年龄验证是服务端 Cookie 校验，未携带 `YES_Eighteen` Cookie 时返回验证页，携带后直接返回真实内容。

**方案设计**：

1. **Layer 1 - Header Cookie 预置**（覆盖 OkHttp 请求）：
   - 在 `header` 字段中添加 `"Cookie":"YES_Eighteen=IamOverEighteenYearsOld"`
   - 所有 OkHttp 请求（文章列表、内容获取、搜索）自动携带此 Cookie
   - 服务端检测到 Cookie 直接返回真实内容

2. **Layer 2 - loginCheckJs 自动验证**（OkHttp 层兜底）：
   - 在 `loginCheckJs` 中检测响应是否为验证页
   - 若检测到验证页，通过 `java.ajax()` 请求验证确认URL
   - 服务端 Set-Cookie 后，`enabledCookieJar` 自动保存 Cookie 到 CookieStore
   - 后续 WebView 请求通过 `CookieManager.applyToWebView()` 自动应用

3. **Layer 3 - injectJs 自动点击**（WebView 层兜底）：
   - 在 `injectJs` 中检测验证页面的确认按钮
   - 若检测到，自动执行点击操作
   - 此层仅在 WebView 加载且前两层未生效时触发

**选择理由**：
- Cookie 预置是最直接可靠的方式，服务端直接识别无需交互
- 三层防护确保在不同加载路径下均能生效
- 不修改 App 源码，仅通过 JSON 配置实现

### Alternatives Considered

| 方案 | 描述 | 否决理由 |
|------|------|----------|
| 仅用 loginCheckJs 打开浏览器 | 类似 CF 标准配置，用 `java.startBrowserAwait()` 打开浏览器让用户手动确认 | 需要用户交互，不符合"自动破除"需求 |
| 仅用 injectJs 自动点击 | 在 WebView 中注入 JS 自动点击确认按钮 | 仅覆盖 WebView 层，OkHttp 层（文章列表）仍返回验证页 |
| 使用 WebView 加载验证URL | 在 `loginUrl` 中配置验证URL，App启动时自动加载 | 增加启动时间，且 `loginUrl` 在订阅源中的执行时机不可控 |
| 使用 shouldOverrideUrlLoading 拦截 | 在 URL 跳转时拦截验证页面 | 验证页是服务端返回的完整页面，非 URL 跳转，无法通过此方式拦截 |

### Drawbacks

| 缺点 | 接受理由 |
|------|----------|
| Cookie 值硬编码在 header 中，站点更新 Cookie 机制后可能失效 | 该 Cookie 值已稳定使用3年+（2023年图片命名可见），180天有效期，短期内不会变化 |
| loginCheckJs 中 `java.ajax()` 产生额外网络请求 | 仅在首次访问或 Cookie 失效时触发，后续请求走 Layer 1 直接命中 |
| injectJs 可能在 WebView 未完全加载时执行失败 | Layer 1+2 已覆盖绝大多数场景，Layer 3 仅作为最终兜底 |
| 优化方案仅针对该站点，无法通用化到其他站点 | 每个站点验证机制不同，通用化需修改 App 源码（超出范围） |

### Prior Art

- Legado CF 标准配置：使用 `loginCheckJs` + `java.startBrowserAwait()` 处理 Cloudflare 验证，但需要用户交互
- 社区源中常见的 `header` Cookie 预置模式：在 header 中直接添加 Cookie 字段绕过简单验证

## Requirements

### R1: OkHttp 层自动绕过
- 修改 `header` 字段，添加验证 Cookie
- 所有 OkHttp 请求（文章列表、内容、搜索）无需用户交互即可获取真实内容

### R2: OkHttp 层自动检测兜底
- 添加 `loginCheckJs` 字段，检测响应是否为验证页
- 若为验证页，自动请求验证确认URL获取 Set-Cookie
- 确保后续请求携带正确 Cookie

### R3: WebView 层自动点击兜底
- 添加 `injectJs` 字段，检测验证页面确认按钮
- 自动点击确认按钮，触发 Cookie 设置
- WebView 加载后无需用户交互即可显示真实内容

### R4: 兼容性
- 优化后的 JSON 可直接导入 Legado App 使用
- 不影响现有功能（搜索、分类、文章列表、内容阅读）
- `enabledCookieJar` 保持 `true` 确保 Cookie 持久化

## Scenarios

### S1: 首次打开订阅源
1. 用户导入优化后的订阅源
2. 点击订阅源进入文章列表
3. OkHttp 请求携带预置 Cookie → 服务端直接返回真实内容
4. 文章列表正常显示，无需任何用户交互

### S2: Cookie 过期后重新访问
1. 用户访问订阅源
2. OkHttp 请求携带过期 Cookie → 服务端返回验证页
3. `loginCheckJs` 检测到验证页 → 自动请求验证确认URL
4. 服务端 Set-Cookie → CookieStore 更新 → 后续请求正常

### S3: WebView 阅读文章
1. 用户点击文章进入 WebView 阅读
2. `CookieManager.applyToWebView()` 应用 CookieStore 中的 Cookie
3. 若 Cookie 缺失/过期，WebView 加载验证页
4. `injectJs` 检测到验证页确认按钮 → 自动点击
5. Cookie 设置 → 页面刷新显示真实内容
