# 测试基础设施升级 - 端到端真机级调试能力

> 状态：⚠️ 代码实现完成，测试验证缺失（2026-06-18）
> 创建日期：2026-06-18
> 优先级：P0
> 详见：[design.md 第 7 章 实施差异与后续优化](./design.md#7-实施差异与后续优化2026-06-18-实施后补充)

## 功能概述

升级 `legado-source-creator` Skill 的测试基础设施（客户端 + 服务端），让 AI 在使用 Skill 开发新书源/订阅源时，能够**完整跑通**生成的源配置，达到"导入手机开源阅读 App 即可直接使用"的交付标准，彻底解决"AI 说测试通过但用户导入手机报错"的系统性问题。

核心手段：将开源阅读（Legado）真机的 `Debug.kt` 调试流程、`AnalyzeUrl` URL 解析、`AnalyzeRule` 完整规则引擎、`JsExtensions` 完整 API、`CookieStore` Cookie 管理等关键能力，**从源码提取并移植**到 JVM 仿真器服务端，新增端到端 `debugBookSource` / `debugRssSource` 命令，输出与真机一致的 `[mm:ss.SSS] ︾︽⇒┌└≡◇` 调试日志。

## 核心问题诊断

### 当前架构的 8 大根因（"测试通过但手机报错"的真相）

| # | 根因 | 影响 | 严重度 |
|---|------|------|--------|
| 1 | `deep-verify.py` 用 Python 仿真（BS4/jsonpath_ng/lxml）而非 JVM | 仿真行为与 jsoup/jayway/JsoupXpath 不一致，"通过"的规则在真机可能匹配失败 | 🔴 致命 |
| 2 | JVM 服务端**无 AnalyzeUrl** | searchUrl 的 `<js>`/`{{key}}`/`{{page}}`/POST body/header/charset 全部无法解析 | 🔴 致命 |
| 3 | AnalyzeRule **无 Book/BookSource 上下文** | `{{book.author}}`、source.header、isFromBookInfo 等变量无法解析 | 🔴 致命 |
| 4 | **无 init 变量链传递** | 每次命令新建 AnalyzeRule 实例，`@put` 变量不跨命令持久化 | 🟠 严重 |
| 5 | **Cookie 不持久化** | MockCookie 是空 stub，需要登录态的源 ajax 请求返回 403 | 🟠 严重 |
| 6 | **无端到端链路命令** | 无法跑通 search→detail→toc→content 全链路 | 🔴 致命 |
| 7 | **MockJsExtensions 覆盖率仅 20%** | 关键网络/cookie/cache 函数缺失（80/100 函数未实现） | 🟠 严重 |
| 8 | **无增量日志输出** | 批量 JSON 响应，无法定位失败阶段（搜索/详情/目录/正文） | 🟡 中等 |

### 当前能力 vs 真机能力差距矩阵

| 维度 | 真机 Debug | 当前测试脚本 | 差距 |
|------|-----------|-------------|------|
| URL 解析 | AnalyzeUrl（完整模板+JS+charset） | Python 字符串替换 | 严重 |
| HTTP 请求 | OkHttp + CookieJar + source.header | Python urllib / Mock ajax | Cookie/Header 不持久 |
| 规则解析器 | AnalyzeRule(book, source, ...) | AnalyzeRule(mockJs) 无上下文 | 缺 book/source 上下文 |
| JsExtensions | 完整实现（90+ 函数） | MinimalMock（20 函数+3 异常+1 空） | 缺失 70+ 函数 |
| CookieStore | 持久化 CookieStore | MockCookie 空 stub | 无法维持登录态 |
| 日志输出 | 增量 callback（state=10/20/30/40） | 批量 JSON 响应 | 无法定位失败阶段 |
| 变量链 | init→后续规则变量传递 | 单命令无持久化 | 变量链断裂 |
| 分页 | nextTocUrl/nextContentUrl 循环 | 不验证 | 章节不完整 |

## 核心能力（升级后）

| 能力 | 说明 | 覆盖率提升 |
|------|------|-----------|
| **L0: AnalyzeUrl 完整移植** | 从真机源码提取 AnalyzeUrl，支持 `<js>`/`@js:`/`{{key}}`/`{{page}}`/`<page>`/POST body/header/charset/JS 求值 | 0% → 90% |
| **L1: 端到端 debugBookSource 命令** | 接收完整 BookSource JSON + 搜索关键词，按 search→detail→toc→content 顺序执行，变量跨步骤持久化 | 30% → 85% |
| **L2: 端到端 debugRssSource 命令** | 接收完整 RssSource JSON，按 sort→content 顺序执行，支持分页 | 30% → 85% |
| **L3: 增量日志输出（与真机一致）** | 流式输出 `[mm:ss.SSS] ︾︽⇒┌└≡◇` 日志 + state=10/20/30/40 状态码，每阶段输出 HTML 源码 | 0% → 100% |
| **L4: CookieStore 内存实现** | 二级域名 Cookie 存储 + ajax/connect 自动携带 + enabledCookieJar 支持 | 0% → 80% |
| **L5: MockJsExtensions 扩展** | 补齐 ajax(带cookie/header)、connect、getCookie/setCookie、md5Encode16、sha1/sha256、HMac 等关键函数 | 20% → 70% |
| **L6: Book/BookSource 上下文注入** | AnalyzeRule 接收 BookSource JSON，应用 header/cookie/loginUrl 配置；evalJS 注入 13 个变量 | 0% → 90% |
| **L7: deep-verify.py 改用 JVM** | 废弃 Python 仿真（BS4/jsonpath_ng/lxml），全链路调用 JVM debugBookSource 命令 | 35% → 85% |

## 文档索引

| 文档 | 说明 |
|------|------|
| [spec.md](./spec.md) | 需求规范（含 L0-L7 完整需求 + 8 个场景 + 验收标准） |
| [design.md](./design.md) | 技术设计（含架构图 + 数据流 + 12 个架构决策 + 文件变更清单） |
| [tasks.md](./tasks.md) | 任务清单（8 个分组 50+ 个任务项） |

## 预期效果

| 指标 | 优化前 | 优化后 |
|------|--------|--------|
| 端到端测试覆盖率 | 30%（Python 仿真） | 85%+（JVM 真机级） |
| "测试通过但手机报错"概率 | 高（70%+） | 低（≤10%） |
| 调试日志与真机一致性 | 0%（无日志） | 100%（格式完全一致） |
| Cookie/Header 持久化 | 不支持 | 支持（内存版） |
| AnalyzeUrl 覆盖率 | 0% | 90% |
| JsExtensions API 覆盖率 | 20% | 70%+ |
| 失败阶段定位能力 | 无（批量响应） | 有（state=10/20/30/40 增量日志） |
| 用户需手动反馈调试信息 | 经常 | 极少（AI 自主定位） |

## 设计原则

1. **源码优先**：所有能力从 Legado 真机源码提取，剥离 Android 依赖，保留核心逻辑
2. **行为一致**：日志格式、URL 解析、规则识别、变量注入、错误码与真机完全一致
3. **增量演进**：改造现有 MVP4 而非新建 MVP5，按 P0→P1→P2 优先级增量补充
4. **不可仿真标记**：BackstageWebView / startBrowserAwait / getVerificationCode 等 Android 原生能力保持抛异常 + confidence=unverifiable，不强行仿真
5. **懒原则**：最少代码完成目标，复用现有 AnalyzeRule/AnalyzeByJSoup/AnalyzeByXPath/RuleAnalyzer（已与真机高度一致）

## 不可达能力（明确边界）

以下能力依赖 Android 原生运行时，JVM 仿真器**无法实现**，保持抛异常 + confidence=unverifiable：

| 能力 | 原因 | 处理方式 |
|------|------|---------|
| `webView()` / `webViewGetSource()` / `webViewGetOverrideUrl()` | 依赖 Android WebView | 抛异常 + unverifiable |
| `startBrowser()` / `startBrowserAwait()` | 依赖 UI 交互 | 抛异常 + unverifiable |
| `getVerificationCode()` | 依赖图片识别 + UI 对话框 | 抛异常 + unverifiable |
| WebJs 模式（`<webJs></webJs>`） | 依赖 BackstageWebView | 抛异常 + unverifiable |
| `toast()` / `openUrl()` / `openVideoPlayer()` | 依赖 Android UI | stub 空实现 |
| `androidId()` / `getWebViewUA()`（动态） | 依赖 Android 系统 | 返回固定值 |

涉及以上能力的源规则，测试报告将明确标记"需真机验证"，AI 不得声称"测试通过"。

## 回测验证闭环

> 不经过实际验证的优化=虚假优化。用一个已知能正常工作的书源 + 一个已知有问题的书源回测验证。

| 验证步骤 | 命令 | 预期结果 |
|---------|------|---------|
| AnalyzeUrl 单元测试 | `verify-url --url "search.php,{method:POST,body:...}"` | URL/method/body/header 解析正确 |
| 端到端书源调试 | `debug-source --source book.json --key "斗破"` | 输出 4 阶段日志 + 至少跑通搜索阶段 |
| 端到端订阅源调试 | `debug-source --source rss.json` | 输出 2 阶段日志 + 跑通列表阶段 |
| Cookie 持久化验证 | 调试需登录的源 | ajax 请求携带 Cookie，返回 200 |
| 日志格式对比 | 与真机 Debug 日志对比 | 时间戳/符号/state 完全一致 |
| 失败阶段定位 | 故意写错 ruleToc | 日志明确显示"目录页解析失败" |
| 真机导入验证 | 用户导入手机测试 | 无报错，可直接使用 |

## 与既有 Skill 工作流的关系

本升级**不改变** Skill 的 5 阶段闭环工作流（Phase 1-5），仅升级 Phase 3（测试驱动）的执行能力：

```
Phase 1: 经验优先（不变）
Phase 2: 构建规则（不变）
Phase 3: 测试驱动（升级）
  ├─ 旧：deep-verify.py Python 仿真（35% 覆盖率）
  └─ 新：debug-source.py JVM 端到端（85%+ 覆盖率，真机级日志）
Phase 4: 源码深挖（不变，但触发频率降低）
Phase 5: 经验反哺（不变）
```

升级后 Phase 3 完成检查清单新增：
- [ ] 执行 `debug-source.py --source {json} --key {keyword}` 端到端调试
- [ ] 4 阶段日志全部输出（state=10/20/30/40）
- [ ] 失败阶段已定位并修复
- [ ] 不可仿真项（webView 等）已标记"需真机验证"
