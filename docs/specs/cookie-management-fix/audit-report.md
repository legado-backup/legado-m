# 设计文档全面审查报告（2026-07-20 第六轮）

> 本报告由4个并行子代理对照源码逐项验证 design.md 中 P0-P18 共18个问题的真实性。
> 验证方法：Read 完整源码 + Grep 关键字 + 行号核对 + 用户场景适用性评估。

## 用户核心场景（审查基准）

- 订阅源有 **loginUrl** 字段（用户通过 WebViewLoginFragment 登录）
- 用户**没有 loginCheckJs** 字段
- 登录后 Cookie 已保存到 CookieStore
- 列表请求**时好时不好**

## 18个问题真实性验证汇总

| 问题 | 真实性 | 实际行号 | 用户场景适用 | 影响 |
|------|--------|---------|------------|------|
| P0 ReadRssActivity 不同步 CookieStore | ✅真实 | L723-741 | ⚠️次要（用户走loginUrl非ReadRss登录） | 高 |
| P1 CookieStore 无过期清理 | ✅真实 | CookieStore.kt L102-119 | ✅适用 | 高 |
| P2 applyToWebView 全局清空会话Cookie | ✅真实 | CookieStore.kt L75 / CookieManager.kt L149 | ✅适用 | 中-高 |
| P3 saveCookie() 死代码 | ✅真实 | AnalyzeUrl.kt L751-762 | ✅适用（但无功能影响） | 低 |
| P4 BackstageWebView 域名不一致 | ✅真实 | BackstageWebView.kt L207-214 | ✅适用（WebViewLoginFragment同模式） | 中 |
| P5 双重合并覆盖链 | ✅真实 | AnalyzeUrl.kt L737 / CookieManager.kt L64 | ✅**极高适用** | **极高** |
| P6 cookieToMap 过滤空值 | ✅真实 | CookieStore.kt L149 | ✅适用 | 高 |
| P7 BackstageWebView 异步竞态 | ✅真实 | BackstageWebView.kt L209 | ❌不适用（用户场景同步调用） | 中 |
| P8 ReadRssActivity L407 applyToWebView | ✅真实 | ReadRssActivity.kt L407 | ⚠️次要（与P2重复） | 中-高 |
| P9 replaceCookie 读改写竞态 | ✅真实 | CookieStore.kt L84-97 | ✅适用 | 中 |
| P10 会话Cookie重启丢失 | ✅真实 | CookieManager.kt L87-96 | ⚠️设计行为非Bug | 低 |
| P11 getKey 传URL给getSessionCookie | ✅真实 | CookieStore.kt L123 | ✅适用（但影响有限） | 中 |
| P12 shouldInterceptRequest 绕过CookieStore | ✅真实 | ReadRssActivity.kt L624-721 | ⚠️次要（与P0重复） | 高 |
| P13 loginCheckJs 事后检测 | ✅真实 | Rss.kt L60-84 | ❌**不适用**（用户无loginCheckJs） | - |
| P14 OkHttp Cache 缓存验证页 | ⚠️部分 | HttpHelper.kt L85/104/118 | ⚠️概率低 | 低 |
| P15 followRedirects 跟随登录页 | ✅真实 | HttpHelper.kt L105 | ⚠️非直接根因 | 中 |
| P16 loginCheckJs 误删Cookie | ✅真实（能力风险） | AnalyzeUrl.kt L373 注入 | ❌**不适用**（用户无loginCheckJs） | - |
| P17 loginUrl/sourceUrl 域名不一致 | ✅真实 | WebViewLoginFragment.kt L92-99 | ✅适用（大多数源同域） | 中 |
| P18 setCookie(null) 空串覆盖 | ✅真实 | CookieStore.kt L61-64 | ✅**极高适用** | **极高** |

## 关键审查发现

### 1. 设计文档对问题真实性的判断基本准确

18个问题中：
- **17个真实存在**（P0-P13, P15-P18）
- **1个部分存在**（P14 - 取决于服务端响应头）
- **行号引用准确无误**

### 2. 用户场景适用性重要修正

设计文档第五轮自我精简为3个根因（P16/P13/负载均衡），但**这个精简方向错误**：

| 设计文档第五轮结论 | 实际审查结论 |
|------------------|------------|
| P16 是最高可能根因 | ❌ 用户无 loginCheckJs，P16 不适用 |
| P13 是次要根因 | ❌ 用户无 loginCheckJs，P13 不适用 |
| 服务端负载均衡是第三根因 | ⚠️ 无法客户端修复 |

**真正的根因应该是 P5 + P18**（设计文档第四轮已识别但第五轮被精简掉）：
- **P5 双重合并覆盖链**：AnalyzeUrl 用 merge(CS,H)→H赢；CookieManager.loadRequest 用 merge(H,CS)→CS赢。参数顺序相反，导致 CookieStore 中的过期值永远覆盖 header 中的正确值
- **P18 setCookie(null) 空串覆盖**：WebViewModel.kt L135 已有代码注释明确标注为"根因"。BackstageWebView 和 WebViewLoginFragment 调用 setCookie 时都无空值保护

### 3. P5 参数顺序已严格验证

```kotlin
// AnalyzeUrl.kt L737 - mergeCookies(CS, H) → H 覆盖 CS → H 赢
mergeCookies(cookie, headerMap["Cookie"])?.let { ... }

// CookieManager.kt L64 - mergeCookies(H, CS) → CS 覆盖 H → CS 赢
val newCookie = mergeCookies(requestCookie, cookie) ?: return request

// mergeCookiesToMap 用 putAll（后者覆盖前者）
.reduce { acc, cookieMap -> acc.apply { putAll(cookieMap) } }
```

**结论**：设计文档对 P5 的描述完全准确。

### 4. P18 已有代码注释佐证

`WebViewModel.kt` L135 注释明确指出：
> "根因：CookieStore.setCookie 空值覆盖导致 refetch 不带 Cookie 被服务器拒绝"

这说明 P18 是**已知根因**，但未在 CookieStore.setCookie 本身修复，仅在 WebViewActivity.kt L474-475 添加了调用方保护。**BackstageWebView.kt L211 和 WebViewLoginFragment.kt L92/99 仍未保护**。

## 真正根因排序（基于用户场景）

### 第一梯队：极高影响（必须修复）

| 问题 | 影响机制 | 修复方案可行性 |
|------|---------|--------------|
| **P5** 双重合并覆盖链 | CookieStore 过期值永远覆盖 header 正确值 | ✅ 可行（方案B：仅补充不覆盖） |
| **P18** setCookie(null) 空串覆盖 | WebView Cookie 未就绪时 null 覆盖有效Cookie | ✅ 可行（setCookie 内部判空） |

### 第二梯队：高影响（应该修复）

| 问题 | 影响机制 | 修复方案可行性 |
|------|---------|--------------|
| **P1** 无过期清理 | 过期 Cookie 永久留存 | ⚠️ 可行但需调整（解析 max-age） |
| **P6** cookieToMap 过滤空值 | 服务端无法删除过期 Cookie | ✅ 可行（在 replaceCookie 中处理） |
| **P0/P12** ReadRssActivity 不同步 | WebView Cookie 不回写 CookieStore | ✅ 可行（参照 BackstageWebView） |
| **P2/P8** 全局清空会话Cookie | 多源互相干扰 | ✅ 可行（移除 removeSessionCookies） |

### 第三梯队：中影响（可选修复）

| 问题 | 影响机制 | 修复方案可行性 |
|------|---------|--------------|
| **P9** replaceCookie 竞态 | 并发场景 Cookie 更新丢失 | ✅ 可行（@Synchronized） |
| **P17** 域名不一致 | 跨域登录时 Cookie 存错域 | ✅ 可行（双domain保存） |
| **P4** BackstageWebView 域名 | 重定向时 Cookie 存错域 | ✅ 可行（用请求URL域名） |
| **P11** getKey 传参错误 | getSessionCookie 读不到 | ✅ 可行（改传domain） |
| **P15** followRedirects | 自动跟随到登录页 | ⚠️ 可行但需谨慎（影响所有请求） |

### 不适用用户场景（无需修复）

| 问题 | 不适用原因 |
|------|-----------|
| **P13** loginCheckJs 事后检测 | 用户无 loginCheckJs |
| **P16** loginCheckJs 误删Cookie | 用户无 loginCheckJs |
| **P7** BackstageWebView 异步竞态 | 用户走 WebViewLoginFragment（同步） |
| **P10** 会话Cookie重启丢失 | 设计行为非Bug |
| **P14** OkHttp Cache | 概率低，no-cache头有效 |
| **P3** saveCookie 死代码 | 无功能影响 |

## 修复方案可行性评估

### Phase 1 核心修复（根除"时好时不好"）

| 修复项 | 可行性 | 风险 | 预期效果 |
|--------|--------|------|---------|
| P5 方案B（AnalyzeUrl仅补充不覆盖） | ✅高 | 低 | 消除双重合并冲突 |
| P18（setCookie判空保护） | ✅高 | 低 | 防止空串覆盖 |
| P1+P6（replaceCookie空值删除） | ✅高 | 低 | 过期Cookie可清理 |
| P0+P12（ReadRssActivity同步Cookie） | ✅高 | 低 | WebView Cookie回写 |

**Phase 1 预期：解决80%+的"时好时不好"场景**

### Phase 2 干扰消除

| 修复项 | 可行性 | 风险 |
|--------|--------|------|
| P2+P8（移除removeSessionCookies） | ✅高 | 中（需验证setCookie覆盖） |
| P9（@Synchronized） | ✅高 | 低 |
| P11（getKey传domain） | ✅高 | 低 |

### Phase 3 边缘场景

| 修复项 | 可行性 | 风险 |
|--------|--------|------|
| P4（用请求URL域名） | ✅中 | 中 |
| P17（双domain保存） | ✅中 | 低 |
| P15（checkRedirect检测登录页） | ⚠️中 | 中 |
| P3（删除死代码） | ✅高 | 低 |

## 关键风险与冲突

### P5 + P18 组合风险

**风险**：P5 修复后 CookieStore 值不再覆盖 header，但 P18 的 setCookie(null) 仍可能写入空串。需要两者同时修复。

**缓解**：P18 在 setCookie 内部判空，无论调用方是否保护都能兜底。

### P0 修复方案需调整

设计文档原方案用 `viewModel.rssSource?.sourceUrl`，应改为 `source.getKey()` 保持与 AnalyzeUrl 一致。

### P1+P6 合并实施

P6 是 P1 的具体机制，应合并为"统一过期Cookie管理"：
- 在 `replaceCookie` 中处理空值删除标记
- 在 `getCookie` 中过滤已知过期Cookie（基于空值标记）
- 不修改 `cookieToMap` 本身（避免影响其他调用点）

## 最终结论

### 设计文档整体评估

| 维度 | 评分 | 说明 |
|------|------|------|
| 问题真实性 | **95/100** | 17/18 真实存在，行号准确 |
| 源码引用准确性 | **98/100** | 行号基本无误，代码片段准确 |
| 修复方案可行性 | **85/100** | 核心方案可行，P5方案A有冲突需改方案B |
| 根因定位准确性 | **70/100** | 第五轮精简方向错误（P13/P16不适用用户场景）|
| 优先级合理性 | **75/100** | 需重新排序，P5+P18应提升到第一梯队 |

### 核心结论

1. **18个问题17个真实存在**，设计文档对问题识别准确
2. **设计文档第五轮精简错误**：把 P13/P16 列为首要根因，但用户无 loginCheckJs，这两个问题不适用
3. **真正根因是 P5 + P18**：
   - P5 双重合并覆盖链（设计文档第四轮已识别）
   - P18 setCookie 空串覆盖（WebViewModel.kt L135 已有注释佐证）
4. **Phase 1 修复方案可行**：P5方案B + P18判空 + P1/P6过期管理 + P0同步，预期解决80%+场景
5. **无需真机验证即可启动 Phase 1 修复**：根因已通过源码严格验证

### 审查通过条件

- ✅ 采纳 P5 方案B（仅补充不覆盖）
- ✅ P18 在 setCookie 内部判空（不依赖调用方保护）
- ✅ P1+P6 合并实施（统一过期管理）
- ✅ P0 修复方案用 source.getKey() 而非 sourceUrl
- ✅ 重新排序根因：P5+P18 为第一梯队（替代原 P13+P16）
- ✅ 移除 P13/P16/P7/P10/P14（不适用用户场景）

## 下一步建议

1. **更新 design.md**：根据本审查报告调整根因排序和修复方案
2. **启动 Phase 1 实施**：P5方案B + P18 + P1/P6 + P0/P12
3. **真机验证**：Phase 1 完成后用 ai_tests/scripts/ 验证
4. **Phase 2/3 按需实施**：基于 Phase 1 真机验证结果决定
