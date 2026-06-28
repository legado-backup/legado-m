# Spec: Skill HTML 获取能力增强

---

## 1. Intent（意图）

### 为什么做这件事？

优化"优质资源(1080zyk)"订阅源时暴露了 skill 工具链的系统性缺陷：

1. **HTML 获取能力缺失**：Cloudflare/JS Challenge 拦截了 curl 请求，无法获取实际 HTML 结构。当前工具链仅有静态 HTTP 请求（requests/urllib），不执行 JS，遇到 CF 保护网站只能拿到"Just a moment..."空壳。

2. **选择器只能猜测**：没有 HTML 输入，JVM MVP2 的 jsoup CSS 选择器验证能力无法使用。5/9 个规则字段标记为"低可信需真机验证"，用户拿到源后仍需大量调试。

3. **CF 绕过方案不够优**：当前设计用 `loginUrl + startBrowserAwait()` 让用户手动通过 CF 验证。但源码验证发现 `java.webView()` 可以**自动通过 CF JS Challenge**（WebView 加载页面后 `onPageFinished` 自动将 Cookie 同步到 CookieStore），无需用户手动操作。仅 Turnstile 验证（managed challenge）才需要 `startBrowserAwait()`。

4. **无 CMS 样本库**：苹果CMS V10 是最常见的视频站 CMS（占视频站 60%+），但 skill 中没有标准 HTML 样本和选择器映射。苹果CMS 是开源的（GitHub: magicblack/maccms10），默认模板 HTML 可直接获取。

5. **Playwright 仅文档提及**：4 个文件 14 处提到 Playwright，但全部是文档引用，没有可执行脚本。

6. **Wayback Machine 未集成**：`html-fetch-traps.md` 提到 Wayback Machine 可获取历史快照分析结构，但没有自动化脚本。

### 解决什么问题？

- CF JS Challenge 保护网站可通过 `java.webView()` 自动绕过 → 无需用户手动操作
- CF 保护网站能获取到实际 HTML（Wayback/Playwright）→ 选择器可验证 → 低可信项大幅减少
- 苹果CMS等常见 CMS 有标准样本库 → 选择器可直接复用 → 无需每次猜测
- Playwright 集成 → SPA/PJAX 网站也能获取渲染后 HTML
- HTML 获取回退链 → 系统化处理各种获取失败场景

---

## 2. Scope（范围）

### 做什么

| 范围 | 说明 | 优先级 |
|------|------|--------|
| **L0: CF JS Challenge 自动绕过** | loginCheckJs 中用 `java.webView()` 自动通过 CF JS Challenge，Cookie 自动同步到 CookieStore，仅 Turnstile 需 `startBrowserAwait()` | P0 |
| **L1: HTML 获取回退链** | Phase 2 增加 curl → Wayback Machine → CMS 样本库 → Google Cache 的回退链流程 | P0 |
| **L2: CMS 样本库** | 为 Top 5 CMS 建立标准 HTML 样本 + 选择器映射，样本来源于 GitHub 开源模板 | P0 |
| **L3: Playwright 集成** | 添加 `tools/fetch_html.py` 脚本，自动处理 CF 验证、获取渲染后 HTML | P1 |
| **L4: JVM Cookie 注入** | RuleEngineServer 支持 Cookie 注入，CF Cookie 可传入 JVM 仿真器 | P2 |
| **SKILL.md 流程更新** | Phase 1-5 每阶段精确修改 + 6大参考目录修改 + 验证脚本修改 | P0 |

### 不做什么

| 不做 | 原因 |
|------|------|
| 不修改 Legado 源码 | 只增强 skill 工具链，不修改 Legado 项目本身 |
| 不替代 JVM 仿真器 | JVM MVP2 的 jsoup 验证是可靠的，缺的是 HTML 输入，不是验证能力 |
| 不构建完整浏览器环境 | Playwright 仅用于 HTML 获取，不做端到端浏览器测试 |
| 不迁移所有 CMS 样本 | 先做 Top 5 CMS（覆盖 80%+ 场景），后续按需扩展 |
| 不破解 CF Turnstile 验证 | Turnstile 需要真实浏览器交互，无法自动破解，只能用 startBrowserAwait() 让用户手动通过 |
| 不修改现有验证脚本接口 | 固化脚本（verify-*.py）接口不变，仅增强 HTML 获取能力 |

### 影响哪些模块

| 模块 | 影响类型 | 说明 |
|------|---------|------|
| `SKILL.md` | 修改 | Phase 1-5 每阶段精确修改 + 陷阱速查表新增CF条目 + 参考文档索引更新 + 测试脚本表格更新 |
| `references/cms-samples/` | 新增 | CMS 标准HTML样本 + 选择器映射（来源于 GitHub 开源模板） |
| `references/js-extensions/webview.md` | 修改 | 补充 webView() 用于 CF 绕过的用法说明 |
| `references/js-extensions/cookie-cache.md` | 修改 | 补充 Cookie 双向共享机制说明 |
| `references/js-patterns/url-js-patterns.md` | 修改 | 补充 loginUrl CF 绕过模式 |
| `references/js-patterns/rule-js-patterns.md` | 修改 | 补充 loginCheckJs CF 检测模式 |
| `references/troubleshooting/html-fetch-traps.md` | 修改 | 补充 CF 保护网站获取方案 |
| `references/troubleshooting/source-type-traps.md` | 修改 | 补充 loginCheckJs 返回值陷阱 |
| `references/source-analysis/` | 新增 | CF 绕过源码分析文档 |
| `references/_INDEX.md` | 修改 | 新增 cms-samples/ 目录索引 + 自进化指引更新 |
| `tools/html_fetcher.py` | 新增 | HTML 获取回退链模块 |
| `tools/fetch_html.py` | 新增 | Playwright HTML 获取脚本 |
| `tools/rule_engine_client.py` | 修改 | 支持 Cookie 注入 |
| `tools/jvm_helpers.py` | 修改 | 新增 HTML 获取辅助函数 + 可信度评估增加 HTML 来源维度 |
| `scripts/verify-selector.py` | 修改 | 支持 `--sample` 参数指定 CMS 样本 |
| `scripts/analyze-site.py` | 修改 | 集成 html_fetcher.py 回退链 |
| `scripts/quick-verify.py` | 修改 | 增加 CF 检测 |
| `scripts/deep-verify.py` | 修改 | 增加 HTML 来源维度 + CMS 样本验证 |
| `scripts/classify-and-fix.py` | 修改 | 增加 CMS 样本匹配分类 |
| `scripts/verify-source.py` | 修改 | 增加 CF 绕过配置验证 |
| `AGENTS.md` | 修改 | 更新 skill 描述 |

---

## 3. Approach（方法）

### 技术方向

采用**CF自动绕过 + 5层回退链 + CMS样本库 + Playwright集成**四位一体的方法：

#### 3.0 CF JS Challenge 自动绕过（L0，新增关键方案）

**源码验证结论**：

| 组件 | 行为 | 源码依据 |
|------|------|---------|
| `java.webView(null, url, null, false)` | 在后台WebView中加载URL，自动执行JS，返回渲染后HTML | JsExtensions.kt L203-229 |
| `BackstageWebView.onPageFinished` | 自动从WebView CookieManager读取Cookie，写入CookieStore | BackstageWebView.kt L183-189 |
| `CookieStore` | OkHttp的Cookie存储，后续请求自动携带 | CookieStore.kt |
| `loginCheckJs` | 必须返回StrResponse，可在其中调用webView()后重新ajax() | Rss.kt L53-77 |

**CF绕过三级策略**：

**推荐方案（方案A）**：在 `loginUrl` 中调用 `webView()` 通过 CF，`loginCheckJs` 仅检测是否通过。

```json
{
    "loginUrl": "@js:java.webView(null, source.sourceUrl, null, false);",
    "loginCheckJs": "var s=result.body();if(s.indexOf('Just a moment')!=-1){java.startBrowserAwait(source.sourceUrl,'通过Cloudflare验证');}result;"
}
```

**为什么不用方案B（在loginCheckJs中调用webView()）**：
- `loginCheckJs` 每次请求都执行，`webView()` 是同步阻塞操作（5-10秒），影响性能
- `loginCheckJs` 必须返回 `StrResponse` 对象，`webView()` 返回 `String`，无法直接替换
- `loginUrl` 只在用户点击"登录"时执行一次，性能影响可控

**执行流程**：
1. 用户首次打开源 → 请求被CF拦截 → loginCheckJs检测到CF → 弹出SourceLoginDialog
2. 用户点击"登录" → 触发 `loginUrl` → `webView()` 加载页面 → CF JS Challenge 自动通过 → Cookie 保存
2. `loginCheckJs` 检测页面 → 如果仍有"Just a moment"（Turnstile）→ 弹浏览器让用户手动通过
3. 后续请求自动携带 CF Cookie → 无需再次验证

**CF 验证类型与绕过策略**：

| CF 验证类型 | 特征 | 自动绕过 | 降级方案 |
|------------|------|---------|---------|
| JS Challenge | "Just a moment..." + 自动执行JS | ✅ `webView()` 自动通过 | - |
| Managed Challenge (Turnstile) | 需要用户交互（点击/滑块） | ❌ 无法自动通过 | `startBrowserAwait()` 手动通过 |
| Interactive Challenge | 需要输入验证码 | ❌ 无法自动通过 | `startBrowserAwait()` 手动通过 |

#### 3.1 HTML 获取回退链（L1）

```
Step 1: curl/requests 直接获取
  ↓ 失败（CF/5秒盾/JS渲染）
Step 2: Wayback Machine 历史快照
  ↓ 失败（无快照/快照过旧）
Step 3: CMS 样本库匹配
  ↓ CMS 类型未知
Step 4: Google Cache 缓存页面
  ↓ 失败（无缓存/Google已缩减Cache服务）
Step 5: Playwright 获取（如果已安装）
  ↓ 未安装
标记为"需真机验证"
```

**注意**：Google Cache 优先级降低到 Step 4，因为 Google 2024年后已大幅缩减 Cache 服务，可靠性下降。

**html_fetcher.py 调用方式**：
- AI 在 Phase 2 中用 RunCommand 调用：`python tools/html_fetcher.py --url URL --output output.html`
- 脚本输出 FetchResult JSON 到 stdout
- AI 解析 JSON 获取 HTML 和来源信息

**Wayback Machine 工具栏清理**：
- Wayback 返回的 HTML 包含 `<!-- BEGIN WAYBACK TOOLBAR INSERT -->` 到 `<!-- END WAYBACK TOOLBAR INSERT -->` 之间的注入代码
- 需要用正则清理：`re.sub(r'<!-- BEGIN WAYBACK TOOLBAR INSERT -->.*?<!-- END WAYBACK TOOLBAR INSERT -->', '', html, flags=re.DOTALL)`
- 同时清理 Wayback 注入的 JS/CSS：`/web/_static/` 路径下的资源引用

#### 3.2 CMS 样本库（L2）

**样本来源**：GitHub 开源 CMS 仓库的默认模板 HTML

| CMS | GitHub 仓库 | 模板路径 |
|-----|-----------|---------|
| 苹果CMS V10 | magicblack/maccms10 | template/default/html/ |
| 苹果CMS X10 | magetop/maccms-x10 | resources/template/ |
| WordPress | WordPress/WordPress | wp-content/themes/twentytwentyfour/ |
| Discuz | Discuz/DiscuzX | template/default/ |
| DedeCMS | dedecms/dedecms | templets/default/ |

**样本 HTML 脱敏规范**：
1. 去除所有用户数据（用户名、头像、评论内容）→ 替换为占位符
2. 去除广告和追踪代码（第三方统计/广告 `<script>`）
3. 去除敏感 URL 参数（token/session）
4. 保留完整的 HTML 结构（标签、class、id、data-* 属性）
5. 保留足够的列表项（至少 5 个）以验证选择器
6. 文件头 HTML 注释标注来源和脱敏日期

**selectors.json 格式**：使用 `primary` + `fallbacks` 数组结构，与 Legado 的 `||` 操作符语义对应。

#### 3.3 Playwright 集成（L3）

**CF 检测增强**：
- 不仅检测 "Just a moment..." 标题
- 还检测 CF 特征：`cf_chl_opt` 变量、`_cf_chl_rt_tk` 参数、`challenge-platform` 脚本
- Turnstile 验证检测：`iframe[src*="challenges.cloudflare.com"]`

**Playwright 安装检测增强**：
- 检测 `playwright` Python 包是否安装
- 检测 Chromium 浏览器是否安装（`playwright install chromium`）
- 两者都可用才启用 Playwright 路径

#### 3.4 JVM Cookie 注入（L4）

**Cookie 格式转换**：
- Playwright 导出格式：`[{name, value, domain, path, expires, httpOnly, secure, sameSite}]`
- OkHttp CookieStore 需要：`Cookie(name, value, domain, path, expires, secure, httpOnly, hostOnly)`
- 需要格式转换函数（在 `rule_engine_client.py` 中实现）

---

## 4. Requirements（需求）

### R0: CF JS Challenge 自动绕过（L0，新增）

| ID | 需求 | 优先级 | 验收标准 |
|----|------|--------|---------|
| R0.1 | SKILL.md 新增 CF 绕过三级策略文档 | P0 | 包含 JS Challenge/Turnstile/Interactive 三种场景的解决方案 |
| R0.2 | SKILL.md 更新 loginUrl 推荐写法：`@js:java.webView(null, source.sourceUrl, null, false);` | P0 | CF JS Challenge 网站可自动通过 |
| R0.3 | SKILL.md 更新 loginCheckJs 推荐写法：先检测 CF → Turnstile 则 startBrowserAwait() | P0 | Turnstile 网站弹浏览器让用户手动通过 |
| R0.4 | basic-memory 写入 CF 绕过经验（含源码验证结论） | P0 | 经验可被后续任务搜索到 |
| R0.5 | 更新"优质资源(1080zyk)"订阅源：使用 webView() 自动绕过 CF | P0 | 源配置使用新的 CF 绕过方案 |
| R0.6 | SKILL.md 陷阱速查表新增 CF 绕过相关陷阱（webView()自动通过JS Challenge / loginCheckJs必须返回result） | P0 | 陷阱速查表包含CF绕过相关条目 |
| R0.7 | SKILL.md Phase 1 增加 CF 绕过经验搜索步骤 | P0 | Phase 1 完成检查清单包含CF经验搜索 |
| R0.8 | SKILL.md Phase 4 增加 CF 绕过源码验证步骤（JsExtensions.webView + BackstageWebView + CookieStore） | P0 | Phase 4 源码深挖表格包含CF绕过相关源码位置 |
| R0.9 | SKILL.md Phase 5 增加 CF 绕过经验反哺步骤 | P0 | Phase 5 反哺写入目标包含anti-crawl.md和cf-bypass经验 |

### R1: HTML 获取回退链（L1）

| ID | 需求 | 优先级 | 验收标准 |
|----|------|--------|---------|
| R1.1 | 创建 `tools/html_fetcher.py` 模块，封装 HTML 获取回退链 | P0 | 传入 URL 返回 HTML 或明确失败原因 |
| R1.2 | Step 1: curl/requests 直接获取，支持自定义 UA/Header | P0 | 返回 HTML 或 HTTP 错误码 |
| R1.3 | Step 2: Wayback Machine CDX API 查询 + 快照获取 + 工具栏清理 | P0 | 自动查询 CDX API，获取最近快照，清理 Wayback 注入代码 |
| R1.4 | Step 3: CMS 样本库匹配（基于 CMS 检测逻辑） | P0 | 检测到 CMS 类型后返回对应样本 HTML |
| R1.5 | Step 4: Google Cache 缓存页面获取 | P1 | 自动查询 Google Cache |
| R1.6 | Step 5: Playwright 获取（检测可用性 + 调用 fetch_html.py） | P1 | Playwright 可用时自动使用 |
| R1.7 | 回退链结果记录：每步尝试结果写入日志 | P0 | 日志包含 URL、每步结果、最终获取方式 |
| R1.8 | html_fetcher.py 缓存机制：同一 URL 短时间内不重复请求 | P1 | 缓存有效期：direct 5分钟 / wayback 24小时 / cms_sample 永久 |
| R1.9 | html_fetcher.py 错误处理边界：Wayback API 超时/CMS 样本损坏/Playwright 崩溃 | P0 | 每步失败都有明确错误信息，不影响后续步骤 |
| R1.10 | SKILL.md Phase 2 增加 HTML 获取步骤 | P0 | Phase 2 流程包含"获取 HTML → 分析结构 → 构建规则" |
| R1.11 | Phase 3 可信度分级优化：增加 HTML 来源维度 | P0 | 可信度标注反映 HTML 来源（直接/Wayback/CMS样本/无） |
| R1.12 | SKILL.md Phase 2 步骤1"分析网站"更新：curl失败后自动调用html_fetcher.py回退链 | P0 | Phase 2 步骤1包含HTML获取回退链调用说明 |

### R2: CMS 样本库（L2）

| ID | 需求 | 优先级 | 验收标准 |
|----|------|--------|---------|
| R2.1 | 创建 `references/cms-samples/` 目录结构 | P0 | 目录存在，含 _INDEX.md |
| R2.2 | 苹果CMS V10 样本（从 GitHub magicblack/maccms10 获取默认模板 HTML） | P0 | list/detail/search/play 4 个页面样本 |
| R2.3 | 苹果CMS V10 selectors.json 选择器映射 | P0 | 选择器基于真机验证或 51rb5 实战案例 |
| R2.4 | 苹果CMS X10 样本 | P1 | 从 GitHub magetop/maccms-x10 获取 |
| R2.5 | WordPress 样本 | P1 | 含默认主题（Twenty Twenty-Four） |
| R2.6 | Discuz 样本 | P2 | 含论坛列表/帖子列表/帖子详情 |
| R2.7 | DedeCMS 样本 | P2 | 含文章列表/文章详情 |
| R2.8 | `references/cms-samples/_INDEX.md` 索引文件 | P0 | 列出所有 CMS 类型、样本页面、选择器映射 |
| R2.9 | verify-selector.py 支持 `--sample` 参数指定 CMS 样本 | P0 | `--sample maccms-v10:list` 使用样本 HTML 验证 |

### R3: Playwright 集成（L3）

| ID | 需求 | 优先级 | 验收标准 |
|----|------|--------|---------|
| R3.1 | 创建 `tools/fetch_html.py` 脚本 | P1 | 脚本存在且可执行 |
| R3.2 | CF Challenge 多特征检测（标题/cf_chl_opt/Turnstile iframe） | P1 | 三种 CF 验证类型都能检测 |
| R3.3 | CF JS Challenge 自动等待（最长 30s） | P1 | 自动等待 CF 验证通过 |
| R3.4 | 支持有头模式（手动通过 Turnstile） | P1 | `--headed` 参数启动有头浏览器 |
| R3.5 | 等待指定选择器出现 | P1 | `--wait-selector SELECTOR` 参数 |
| R3.6 | Cookie 导出（JSON 格式，兼容 JVM Cookie 注入） | P1 | `--export-cookies FILE` 参数 |
| R3.7 | Playwright 完整安装检测（Python 包 + Chromium 浏览器） | P1 | 未安装时输出明确安装指引 |
| R3.8 | html_fetcher.py 集成 Playwright | P1 | 回退链 Step 5 调用 fetch_html.py |

### R4: JVM Cookie 注入（L4）

| ID | 需求 | 优先级 | 验收标准 |
|----|------|--------|---------|
| R4.1 | RuleEngineServer 新增 `set_cookies` 命令 | P2 | 传入 Cookie JSON，存入 CookieStore |
| R4.2 | RuleEngineClient 新增 `set_cookies(cookies)` 方法 + Cookie 格式转换 | P2 | Playwright 导出的 Cookie 可直接注入 |
| R4.3 | MockJsExtensions.ajax() 从 CookieStore 读取 Cookie | P2 | ajax() 请求自动携带注入的 Cookie |
| R4.4 | 可信度评估更新：Cookie 注入后 ajax() 规则可信度提升 | P2 | 含 Cookie 的 ajax() 规则从"低"提升到"中" |
| R4.5 | SKILL.md MockJsExtensions ajax()差异表格更新：标注L4 Cookie注入后的变化 | P2 | 差异表格包含Cookie注入前后的对比 |

### R5: 6大参考目录修改（P0-P1）

| ID | 需求 | 优先级 | 验收标准 |
|----|------|--------|---------|
| R5.1 | js-extensions/webview.md 补充 webView() 用于 CF 绕过的用法说明 | P0 | 包含loginUrl中webView()的推荐写法和注意事项 |
| R5.2 | js-extensions/cookie-cache.md 补充 Cookie 双向共享机制说明（WebView→CookieStore自动 / OkHttp→WebView需applyToWebView） | P0 | 包含Cookie同步机制的完整说明 |
| R5.3 | js-patterns/url-js-patterns.md 补充 loginUrl 的 CF 绕过模式（webView()自动通过 + startBrowserAwait()降级） | P1 | 包含CF绕过loginUrl的代码模式 |
| R5.4 | js-patterns/rule-js-patterns.md 补充 loginCheckJs 的 CF 检测模式（检测"Just a moment" → 降级处理） | P1 | 包含CF检测loginCheckJs的代码模式 |
| R5.5 | troubleshooting/html-fetch-traps.md 补充 CF 保护网站的获取方案（Wayback/CMS样本/Playwright回退链） | P0 | 包含CF保护网站的完整获取方案 |
| R5.6 | troubleshooting/source-type-traps.md 补充 loginCheckJs 必须返回 StrResponse 的陷阱说明 | P0 | 包含loginCheckJs返回值陷阱 |
| R5.7 | source-analysis/ 新增 CF 绕过源码分析文档（JsExtensions.webView + BackstageWebView + CookieStore） | P1 | 包含CF绕过相关源码的完整分析 |
| R5.8 | references/_INDEX.md 更新：新增 cms-samples/ 目录索引 + 自进化指引新增CMS样本条目 | P0 | 索引包含cms-samples/条目 |

### R6: 验证脚本修改（P0-P1）

| ID | 需求 | 优先级 | 验收标准 |
|----|------|--------|---------|
| R6.1 | quick-verify.py 增加 CF 检测：检测 HTTP 响应是否为 CF Challenge 页面 | P1 | CF保护网站输出"CF Challenge detected" |
| R6.2 | deep-verify.py 增加 HTML 来源维度：可信度标注包含 HTML 来源信息 | P0 | 验证报告包含html_source字段 |
| R6.3 | deep-verify.py 增加 CMS 样本验证：支持使用 CMS 样本 HTML 验证选择器 | P1 | 支持--sample参数 |
| R6.4 | classify-and-fix.py 增加 CMS 样本匹配分类：问题分类包含"可使用CMS样本修复" | P1 | 分类结果包含cms_sample_available字段 |
| R6.5 | verify-source.py 增加 CF 绕过配置验证：检查 loginUrl/loginCheckJs 格式 | P0 | CF保护网站缺少loginUrl时报错 |

### R7: SKILL.md 5阶段工作流精确修改（P0）

| ID | 需求 | 优先级 | 验收标准 |
|----|------|--------|---------|
| R7.1 | Phase 1 完成检查清单新增：搜索CF绕过经验 + 搜索CMS类型经验 + 查cms-samples/目录 | P0 | Phase 1 检查清单包含3项新增 |
| R7.2 | Phase 2 步骤1"分析网站"更新：curl失败后调用html_fetcher.py回退链获取HTML | P0 | Phase 2 步骤1包含回退链调用说明 |
| R7.3 | Phase 2 步骤3"构建详情+目录+正文规则"更新：CMS类型网站优先使用selectors.json | P0 | Phase 2 步骤3包含CMS样本选择器复用说明 |
| R7.4 | Phase 2 步骤4"处理特殊场景"更新：CF反爬使用三级策略（webView()/startBrowserAwait()） | P0 | Phase 2 步骤4包含CF绕过三级策略 |
| R7.5 | Phase 3 可信度分层表格更新：增加HTML来源维度（直接/Wayback/CMS样本/Google Cache/无） | P0 | 可信度表格包含HTML来源维度 |
| R7.6 | Phase 3 测试脚本执行优先级更新：新增html_fetcher.py（HTML获取）到执行优先级 | P0 | 执行优先级包含html_fetcher.py |
| R7.7 | Phase 4 源码深挖表格更新：新增CF绕过相关源码位置（JsExtensions/BackstageWebView/CookieStore） | P0 | 源码深挖表格包含3个新增源码位置 |
| R7.8 | Phase 5 反哺写入目标更新：新增anti-crawl.md（CF绕过方案）+ cms-samples/（CMS样本）+ html-fetch-traps.md（获取方案） | P0 | Phase 5 反哺目标包含3个新增 |
| R7.9 | SKILL.md 参考文档索引表格更新：新增 cms-samples/ 条目 + html_fetcher.py 条目 + fetch_html.py 条目 | P0 | 索引表格包含3个新增条目 |
| R7.10 | SKILL.md 测试脚本表格更新：新增 html_fetcher.py 条目 + verify-selector.py --sample 参数说明 | P0 | 测试脚本表格包含新增条目 |

---

## 5. Scenarios（场景）

### S1: CF JS Challenge 自动绕过（新增关键场景）

**前置条件**：用户请求将 CF JS Challenge 保护的网站创建为订阅源

1. AI 构建源配置，loginUrl 使用 `@js:java.webView(null, source.sourceUrl, null, false);`
2. 用户首次打开源 → 请求被CF拦截 → loginCheckJs检测到CF → 弹出SourceLoginDialog
3. 用户点击"登录"按钮 → Legado 执行 loginUrl → webView() 加载页面
4. WebView 自动执行 CF JS Challenge → CF 验证通过 → cf_clearance Cookie 保存到 CookieStore
5. loginCheckJs 再次检测页面 → 不含"Just a moment" → 返回 result
6. 后续请求自动携带 cf_clearance Cookie → 无需再次验证
7. **仅需用户点击一次"登录"按钮，CF JS Challenge 即可自动通过**

### S2: CF Turnstile 验证降级

**前置条件**：CF 使用 Turnstile 验证（需要用户交互）

1. AI 构建源配置，loginUrl 使用 webView()，loginCheckJs 检测 CF
2. 用户首次打开源 → webView() 加载页面 → Turnstile 验证无法自动通过
3. loginCheckJs 检测到"Just a moment" → 调用 startBrowserAwait() 弹浏览器
4. 用户在浏览器中手动通过 Turnstile 验证 → Cookie 保存
5. 后续请求自动携带 Cookie

### S3: Wayback Machine 获取历史 HTML

**前置条件**：CF 保护网站，需要获取 HTML 验证选择器

1. Phase 2 开始，AI 调用 `html_fetcher.py --url URL`
2. Step 1: curl 获取 → 返回 403
3. Step 2: Wayback Machine CDX API → 找到 2024-08 快照
4. 获取快照 HTML → 清理 Wayback 工具栏 → 返回 HTML
5. AI 分析 HTML 结构，构建 CSS 选择器
6. Phase 3: JVM MVP2 用获取到的 HTML 验证选择器 → 高可信

### S4: CMS 样本库匹配

**前置条件**：新上线的苹果CMS网站，Wayback Machine 无快照

1. Phase 2 开始，AI 调用 `html_fetcher.py --url URL`
2. Step 1-2: curl 和 Wayback Machine 都失败
3. Step 3: analyze-site.py 检测到苹果CMS V10 → 返回样本 HTML
4. AI 基于样本 HTML + selectors.json 构建选择器
5. Phase 3: JVM MVP2 用样本 HTML 验证 → 中可信

### S5: Playwright 获取渲染后 HTML

**前置条件**：SPA 网站，需要 JS 渲染才能看到内容

1. Phase 2 开始，AI 调用 `html_fetcher.py --url URL`
2. Step 1: curl 获取 → 返回空壳 `<div id="app"></div>`
3. Step 5: Playwright → `fetch_html.py --url URL --wait-selector .video-list`
4. 返回渲染后 HTML → AI 分析结构 → 高可信

### S6: 所有获取方式失败

1. curl → 403 / Wayback → 无快照 / CMS → 未知类型 / Playwright → 未安装
2. 所有回退失败 → 标记为"需真机验证"
3. AI 基于经验猜测选择器，但明确标注"低可信-未验证"

### S7: 回测验证——用"优质资源(1080zyk)"验证完整流程（强制闭环）

> **本场景是本次优化的起点和终点，必须通过实际验证才能确认优化效果。不经过实际验证的优化=虚假优化。**

**优化前基线数据**（来自本次优化任务的实际验证结果）：

| 字段 | 优化前可信度 | 原因 |
|------|------------|------|
| ruleArticles | 低 | CF拦截，无法获取HTML验证 |
| ruleNextPage | 低 | CF拦截，无法获取HTML验证 |
| ruleLink | 低 | CF拦截，无法获取HTML验证 |
| ruleTitle | 低 | CF拦截，无法获取HTML验证 |
| ruleImage | 低 | CF拦截，无法获取HTML验证 |
| ruleDescription | 中 | 基于CMS经验猜测 |
| ruleContent | 中 | 依赖ajax()但无Cookie |
| header | 高 | 纯JS逻辑 |
| loginUrl/loginCheckJs | 低 | startBrowserAwait()需用户手动操作 |

**优化后预期数据**：

| 字段 | 优化后预期可信度 | 提升原因 |
|------|----------------|---------|
| ruleArticles | 高 | CMS样本库验证通过 / Wayback HTML验证通过 |
| ruleNextPage | 高 | CMS样本库验证通过 |
| ruleLink | 高 | CMS样本库验证通过 |
| ruleTitle | 高 | CMS样本库验证通过 |
| ruleImage | 高 | CMS样本库验证通过 |
| ruleDescription | 高 | CMS样本库验证通过 |
| ruleContent | 中 | 仍依赖ajax()，但Cookie可通过webView()获取 |
| header | 高 | 纯JS逻辑（不变） |
| loginUrl/loginCheckJs | 高 | webView()自动通过CF JS Challenge |

**验证步骤**（必须按顺序执行）：

1. **更新源配置**：loginUrl 从 `startBrowserAwait()` 改为 `webView()`
2. **HTML获取验证**：`python tools/html_fetcher.py --url https://1080zyk.com/ --json`
   - 预期：Step 1 CF拦截 → Step 2 Wayback成功 或 Step 3 CMS样本成功
   - 记录：获取方式、HTML来源、快照日期
3. **CMS样本验证**：`python scripts/verify-selector.py --sample references/cms-samples/maccms-v10/list.html --selector ".stui-vodlist li"`
   - 预期：primary选择器验证通过
   - 记录：每个选择器的验证结果
4. **JVM MVP2验证**：`python scripts/deep-verify.py --source output/rss/优质资源-优化.json`
   - 预期：5个低可信 → 1个低可信
   - 记录：每个字段的可信度变化
5. **CF绕过验证**：检查loginUrl/loginCheckJs配置格式
   - 预期：loginUrl使用webView()，loginCheckJs检测CF
   - 记录：配置是否正确
6. **输出验证报告**：对比优化前后，确认优化效果

**验收标准**：
- 低可信项从5个降到≤2个
- loginUrl使用webView()自动绕过CF
- html_fetcher.py至少有一种方式获取到HTML
- CMS样本库的选择器至少3个验证通过
