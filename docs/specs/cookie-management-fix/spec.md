# Cookie 管理链路修复 — 需求文档

## Intent

用户在 Legado 中登录订阅源/书源后，服务端通过 Set-Cookie 返回的登录凭证（如 session、年龄验证 Cookie）在后续 OkHttp 请求中"时好时不好"——有时能正常携带，有时完全丢失，导致用户体验极差。本需求从源码层面修复 Cookie 在 WebView ↔ CookieStore ↔ OkHttp 三方间的同步断裂问题。

## Scope

### In Scope

1. 修复 ReadRssActivity WebView Cookie 不回写 CookieStore 的问题（P0）
2. 添加 CookieStore 过期 Cookie 自动清理机制（P1）
3. 修复 applyToWebView() 全局清空会话 Cookie 导致多源冲突的问题（P2）
4. 激活或移除 AnalyzeUrl.saveCookie() 死代码（P3）
5. 修复 BackstageWebView Cookie 域名不匹配问题（P4）

### Out of Scope

- 不修改 CookieStore 的持久化存储方式（仍使用 SharedPreferences）
- 不重构 CookieManager 的 API 接口
- 不修改 loginCheckJs / injectJs 等订阅源 JSON 配置字段的解析逻辑
- 不涉及 BookSource 登录流程的 UI 改造

## Approach

### Selected Approach: 最小侵入式修复（逐问题精准修复）

逐个修复6个已定位的问题，每个修复限于最小文件范围，不引入新的抽象层。优先修复 P0 和 P1，它们是"时好时不好"的最直接原因。

**理由**：
- Cookie 管理是 Legado 的核心基础设施，影响所有网络请求
- 大规模重构风险高，可能引入新的回归 Bug
- 6个问题已经精确定位到源码行号，精准修复成本最低

### Alternatives Considered

| 方案 | 描述 | 否决理由 |
|------|------|---------|
| A. 统一 Cookie 同步框架 | 新建 CookieSyncManager 统一管理 WebView/CookieStore/OkHttp 三方同步 | 过度设计，引入新抽象层增加复杂度；6个问题都是具体实现 Bug，不需要架构调整 |
| B. 替换 CookieStore 为 OkHttp 原生 CookieJar | 使用 OkHttp 的 CookieJar 接口替代自定义 CookieStore | 风险极高，CookieStore 被 20+ 文件引用；且原版作者设计 CookieStore 有其考虑（跨源共享/JS 可操作） |
| C. 仅靠 loginCheckJs 绕过 | 不修源码，靠订阅源 JSON 的 loginCheckJs 补偿 | 已在上次任务中采用，但这是"治标不治本"——每个源都要手动配置，且依赖源作者了解 CookieStore 覆盖机制 |

### Drawbacks

1. **逐问题修复可能遗漏关联问题**：6个问题之间可能有隐含依赖，逐个修复可能无法一次性解决所有场景
   - 接受理由：每个修复都有明确的源码行号和验证标准，修复后逐个真机验证
2. **CookieStore 过期清理可能导致短期行为变化**：用户习惯了过期 Cookie 仍被携带的行为，清理后可能影响某些源
   - 接受理由：过期 Cookie 本就不应被使用，这是正确的修复方向；如果某些源依赖过期行为，说明源配置有问题

## Prior Art

- OkHttp 官方 CookieJar：使用内存缓存 + 可选持久化，每次请求前加载、响应后保存
- Android WebView CookieManager：系统级 Cookie 管理，自动处理过期
- 原版 Legado 的 BackstageWebView：已经正确实现了 WebView → CookieStore 同步
- **本项目已完成**：[rss-age-verify-autobypass](../rss-age-verify-autobypass/README.md) — 通过三层防护（header Cookie + loginCheckJs + injectJs）绕过年龄验证，其中 loginCheckJs 的 `cookie.removeCookie + cookie.setCookie` 正是为了绕过本任务 P1 问题（CookieStore 过期值覆盖 header Cookie）。本任务完成后，该 loginCheckJs 将不再必需（但仍可保留作为兜底）

## Requirements

### REQ-1: ReadRssActivity WebView Cookie 回写 CookieStore（P0）

**当** ReadRssActivity 的 WebView 在 onPageFinished 后获取到服务端 Cookie，
**那么** 这些 Cookie 必须被同步写入 CookieStore，
**以便** 后续 OkHttp 请求能自动携带这些 Cookie。

**验证标准**：用户在 ReadRssActivity 中通过年龄验证后，返回列表页刷新时不再出现验证弹框。

### REQ-2: CookieStore 过期 Cookie 自动清理（P1）

**当** CookieStore 中的 Cookie 已超过其 max-age 或已过期，
**那么** 这些 Cookie 应在 getCookie() 时被自动过滤，
**以便** 过期值不会覆盖 header 中预置的正确值。

**验证标准**：设置一个已过期的 Cookie 后，getCookie() 不再返回该 Cookie。

### REQ-3: applyToWebView() 不全局清空会话 Cookie（P2）

**当** 切换源或重新加载 WebView 时，
**那么** applyToWebView() 不应清空所有源的会话 Cookie，
**以便** 用户在源A的登录状态不会被源B的加载清除。

**验证标准**：先访问源A登录成功，再访问源B，回到源A时仍保持登录状态。

### REQ-4: AnalyzeUrl.saveCookie() 死代码处理（P3）

**当** AnalyzeUrl.saveCookie() 从未被调用时，
**那么** 要么激活该功能（在合适的时机调用），要么移除该死代码，
**以便** 代码库保持清晰。

### REQ-5: BackstageWebView Cookie 域名匹配修复（P4）

**当** BackstageWebView 使用 source.getKey()（源 URL）而非请求 URL 的域名存储 Cookie 时，
**那么** 应使用请求 URL 的实际域名，
**以便** Cookie 域名与 OkHttp 请求域名一致。

## Scenarios

### Scenario 1: 订阅源年龄验证（核心场景）

1. 用户打开订阅源，首次访问触发年龄验证弹框
2. 用户点击确认，WebView 获取 Set-Cookie: `YES_Eighteen=IamOverEighteenYearsOld`
3. **当前行为**：Cookie 仅写入 WebView CookieManager，不回写 CookieStore
4. **期望行为**：Cookie 同步写入 CookieStore，后续 OkHttp 请求自动携带
5. 用户返回列表页刷新 → 期望不再出现验证弹框

### Scenario 2: 书源登录后搜索

1. 用户通过 loginUrl 打开 WebView 登录页
2. 用户输入账号密码登录成功，服务端 Set-Cookie: `session=xxx`
3. BackstageWebView 的 onPageFinished 将 Cookie 同步到 CookieStore ✅
4. 用户搜索时 OkHttp 请求自动携带 session Cookie ✅
5. 但如果用户在 ReadRssActivity 中登录（而非 BackstageWebView），Cookie 丢失 ❌

### Scenario 3: 多源切换

1. 用户先访问源A，登录成功（Cookie 存入 CookieStore）
2. 用户切换到源B，ReadRssActivity 加载源B
3. **当前行为**：applyToWebView() 全局清空会话 Cookie，源A 的 WebView Cookie 被清除
4. **期望行为**：仅替换源B相关的 Cookie，不清空源A的
5. 用户切回源A → 期望 WebView 仍保持登录状态
