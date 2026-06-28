# Tasks: Skill HTML 获取能力增强

---

## 0. L0: CF JS Challenge 自动绕过（P0）

- [x] 0.1 编写 `references/special-scenarios/cf-bypass.md`：CF 绕过三级策略文档（JS Challenge/Turnstile/Interactive + 源码验证结论） ✅ 2026-06-14
- [x] 0.2 更新 `SKILL.md`：新增 CF 绕过三级策略章节（loginUrl 推荐写法 + loginCheckJs 推荐写法 + 执行流程图） ✅ 2026-06-14
- [x] 0.3 更新 `SKILL.md`：loginUrl 推荐写法 `@js:java.webView(null, source.sourceUrl, null, false);` ✅ 2026-06-14
- [x] 0.4 更新 `SKILL.md`：loginCheckJs 推荐写法（先检测 CF → Turnstile 则 startBrowserAwait()） ✅ 2026-06-14
- [x] 0.5 basic-memory 写入 CF 绕过经验（含源码验证结论：webView()自动通过JS Challenge + Cookie双向共享机制） ✅ 2026-06-14
- [x] 0.6 更新"优质资源(1080zyk)"订阅源：loginUrl 改为 webView() 自动绕过 CF ✅ 2026-06-14
- [x] 0.7 更新 `references/special-scenarios/anti-crawl.md`：新增 CF 绕过三级策略（webView()自动通过 + startBrowserAwait()降级） ✅ 2026-06-14
- [x] 0.8 更新 `SKILL.md` 陷阱速查表：新增 CF 绕过相关陷阱（webView()自动通过JS Challenge / loginCheckJs必须返回result） ✅ 2026-06-14
- [x] 0.9 更新 `SKILL.md` Phase 1 完成检查清单：新增搜索CF绕过经验 + 搜索CMS类型经验 + 查cms-samples/目录 ✅ 2026-06-14
- [x] 0.10 更新 `SKILL.md` Phase 4 源码深挖表格：新增CF绕过相关源码位置（JsExtensions/BackstageWebView/CookieStore/Rss.kt） ✅ 2026-06-14
- [x] 0.11 更新 `SKILL.md` Phase 5 反哺写入目标：新增anti-crawl.md + cms-samples/ + html-fetch-traps.md ✅ 2026-06-14

## 1. L1: HTML 获取回退链（P0）

- [x] 1.1 创建 `tools/html_fetcher.py` 模块框架（FetchResult 数据类 + HtmlFetcher 类 + CLI 接口 + 缓存机制） ✅ 2026-06-14
- [x] 1.2 实现 Step 1: curl/requests 直接获取（支持自定义 UA/Header/超时 + CF 检测） ✅ 2026-06-14
- [x] 1.3 实现 Step 2: Wayback Machine CDX API 查询 + 快照获取 + 工具栏清理（正则清理注入代码） ✅ 2026-06-14
- [x] 1.4 实现 Step 3: CMS 样本库匹配（复用 analyze-site.py 的 CMS 检测逻辑 + 读取本地样本 HTML） ✅ 2026-06-14
- [x] 1.5 实现 Step 4: Google Cache 缓存页面获取 ✅ 2026-06-14
- [x] 1.6 实现 Step 5: Playwright 回退（检测可用性 + 调用 fetch_html.py） ✅ 2026-06-14
- [x] 1.7 实现回退链日志记录（每步尝试结果 + 最终获取方式 + JSON 输出） ✅ 2026-06-14
- [x] 1.8 实现 CF 检测函数 `_is_cf_challenge()`（5 种 CF 特征检测） ✅ 2026-06-14
- [x] 1.9 实现缓存机制：内存缓存 + 有效期（direct 5分钟/wayback 24小时/cms_sample永久） ✅ 2026-06-14
- [x] 1.10 实现错误处理边界：Wayback API超时/CMS样本损坏/Playwright崩溃/Google Cache 403 ✅ 2026-06-14
- [x] 1.11 编写单元测试（mock 各步骤的成功/失败场景） ✅ 2026-06-14
- [x] 1.12 更新 `tools/jvm_helpers.py`：新增 `fetch_html()` 辅助函数 + `assess_confidence()` 增加 HTML 来源维度 ✅ 2026-06-14
- [x] 1.13 更新 `SKILL.md` Phase 2 步骤1"分析网站"：curl失败后调用html_fetcher.py回退链 ✅ 2026-06-14

## 2. L2: CMS 样本库（P0）

- [x] 2.1 创建 `references/cms-samples/` 目录结构 ✅ 2026-06-14
- [x] 2.2 编写 `references/cms-samples/_INDEX.md` 索引文件 ✅ 2026-06-14
- [x] 2.3 从 GitHub magicblack/maccms10 获取苹果CMS V10 默认模板 HTML（WebFetch GitHub Raw） ✅ 2026-06-14
- [x] 2.4 脱敏处理苹果CMS V10 样本（list/detail/search/play 4 个页面） ✅ 2026-06-14
- [x] 2.5 编写苹果CMS V10 `selectors.json`（基于 1080zyk 实战案例 + primary+fallbacks 结构） ✅ 2026-06-14
- [x] 2.6 更新 `references/_INDEX.md`：新增 cms-samples/ 目录索引 + 自进化指引新增CMS样本条目 ✅ 2026-06-14
- [x] 2.7 更新 `scripts/verify-selector.py`：新增 `--sample` 参数支持 CMS 样本 HTML 输入 ✅ 2026-06-14
- [x] 2.8 集成测试：用苹果CMS V10 样本验证 verify-selector.py 的 `--sample` 功能 ✅ 2026-06-14
- [x] 2.9 集成 html_fetcher.py：Step 3 读取 CMS 样本并返回 ✅ 2026-06-14
- [x] 2.10 更新 `SKILL.md` Phase 2 步骤3：CMS类型网站优先使用selectors.json ✅ 2026-06-14

### 2.x CMS 样本库扩展（P1-P2）

- [ ] 2.11 从 GitHub magetop/maccms-x10 获取并脱敏苹果CMS X10 样本（list/detail）+ selectors.json
- [ ] 2.12 从 GitHub WordPress/WordPress 获取并脱敏 WordPress 样本（list/detail）+ selectors.json
- [ ] 2.13 从 GitHub Discuz/DiscuzX 获取并脱敏 Discuz 样本（list/detail）+ selectors.json
- [ ] 2.14 从 GitHub dedecms/dedecms 获取并脱敏 DedeCMS 样本（list/detail）+ selectors.json

## 3. L3: Playwright 集成（P1）

- [x] 3.1 创建 `tools/fetch_html.py` 脚本框架（argparse + check_playwright + detect_cf_challenge） ✅ 2026-06-14
- [x] 3.2 实现 CF Challenge 多特征检测（标题/cf_chl_opt/challenge-platform/Turnstile iframe） ✅ 2026-06-14
- [x] 3.3 实现 CF JS Challenge 自动等待（最长 30s，检测标题变化） ✅ 2026-06-14
- [x] 3.4 实现有头模式支持（`--headed` 参数，用于 Turnstile 手动通过） ✅ 2026-06-14
- [x] 3.5 实现等待指定选择器（`--wait-selector` 参数） ✅ 2026-06-14
- [x] 3.6 实现 HTML 输出（`--output` 参数） ✅ 2026-06-14
- [x] 3.7 实现 Cookie 导出（`--export-cookies` 参数，JSON 格式，兼容 JVM Cookie 注入） ✅ 2026-06-14
- [x] 3.8 实现 Playwright 完整安装检测（Python 包 + Chromium 浏览器） ✅ 2026-06-14
- [x] 3.9 集成 html_fetcher.py：Step 5 调用 fetch_html.py ✅ 2026-06-14
- [x] 3.10 集成测试：用 CF 保护网站测试完整流程 ✅ 2026-06-14

## 4. L4: JVM Cookie 注入（P2）

- [ ] 4.1 修改 `RuleEngineServer.kt`：新增 `set_cookies` 命令
- [ ] 4.2 修改 `MinimalMockJsExtensions.kt`：ajax() 从 CookieStore 读取 Cookie
- [ ] 4.3 修改 `tools/rule_engine_client.py`：新增 `set_cookies(cookies)` 方法 + `convert_playwright_cookies_to_okhttp()` 格式转换
- [ ] 4.4 重建 JAR：`cd tools/mvp1-build && gradlew.bat fatJar`
- [ ] 4.5 集成测试：注入 CF Cookie 后 ajax() 请求成功
- [ ] 4.6 更新 `tools/jvm_helpers.py`：`assess_confidence()` Cookie 注入后可信度提升
- [ ] 4.7 更新 `SKILL.md` MockJsExtensions ajax()差异表格：标注L4 Cookie注入后的变化

## 5. SKILL.md 流程更新（P0）

- [x] 5.1 Phase 1 完成检查清单新增：搜索CF绕过经验 + 搜索CMS类型经验 + 查cms-samples/目录 ✅ 2026-06-14
- [x] 5.2 Phase 2 步骤1"分析网站"更新：curl失败后调用html_fetcher.py回退链获取HTML ✅ 2026-06-14
- [x] 5.3 Phase 2 步骤3"构建详情+目录+正文规则"更新：CMS类型网站优先使用selectors.json ✅ 2026-06-14
- [x] 5.4 Phase 2 步骤4"处理特殊场景"更新：CF反爬使用三级策略（webView()/startBrowserAwait()） ✅ 2026-06-14
- [x] 5.5 Phase 3 可信度分层表格更新：增加HTML来源维度（直接/Wayback/CMS样本/Google Cache/无） ✅ 2026-06-14
- [x] 5.6 Phase 3 测试脚本执行优先级更新：新增html_fetcher.py到执行优先级 ✅ 2026-06-14
- [x] 5.7 Phase 4 源码深挖表格更新：新增CF绕过相关源码位置 ✅ 2026-06-14
- [x] 5.8 Phase 5 反哺写入目标更新：新增anti-crawl.md + cms-samples/ + html-fetch-traps.md ✅ 2026-06-14
- [x] 5.9 陷阱速查表新增CF绕过相关条目 ✅ 2026-06-14
- [x] 5.10 参考文档索引表格更新：新增 cms-samples/ + html_fetcher.py + fetch_html.py 条目 ✅ 2026-06-14
- [x] 5.11 测试脚本表格更新：新增 html_fetcher.py 条目 + verify-selector.py --sample 参数说明 ✅ 2026-06-14

## 6. 6大参考目录修改（P0-P1）

- [x] 6.1 更新 `references/js-extensions/webview.md`：补充 webView() 用于 CF 绕过的用法说明 ✅ 2026-06-14
- [x] 6.2 更新 `references/js-extensions/cookie-cache.md`：补充 Cookie 双向共享机制说明 ✅ 2026-06-14
- [x] 6.3 更新 `references/js-patterns/url-js-patterns.md`：补充 loginUrl CF 绕过模式 ✅ 2026-06-14
- [x] 6.4 更新 `references/js-patterns/rule-js-patterns.md`：补充 loginCheckJs CF 检测模式 ✅ 2026-06-14
- [x] 6.5 更新 `references/troubleshooting/html-fetch-traps.md`：补充 CF 保护网站获取方案 ✅ 2026-06-14
- [x] 6.6 更新 `references/troubleshooting/source-type-traps.md`：补充 loginCheckJs 返回值陷阱 ✅ 2026-06-14
- [x] 6.7 新增 `references/source-analysis/cf-bypass-source.md`：CF 绕过源码分析文档 ✅ 2026-06-14
- [x] 6.8 更新 `references/_INDEX.md`：新增 cms-samples/ 目录索引 + 自进化指引新增CMS样本条目 ✅ 2026-06-14

## 7. 验证脚本修改（P0-P1）

- [x] 7.1 更新 `scripts/quick-verify.py`：增加 CF 检测（检测HTTP响应是否为CF Challenge页面） ✅ 2026-06-14
- [x] 7.2 更新 `scripts/deep-verify.py`：增加 HTML 来源维度（可信度标注包含html_source字段） ✅ 2026-06-14
- [x] 7.3 更新 `scripts/deep-verify.py`：增加 CMS 样本验证（支持--sample参数） ✅ 2026-06-14
- [x] 7.4 更新 `scripts/classify-and-fix.py`：增加 CMS 样本匹配分类 ✅ 2026-06-14
- [x] 7.5 更新 `scripts/verify-source.py`：增加 CF 绕过配置验证 ✅ 2026-06-14

## 8. AGENTS.md 更新（P0）

- [x] 8.1 更新 skill 描述：新增 HTML 获取能力 + CF 自动绕过 + CMS 样本库 ✅ 2026-06-14
- [x] 8.2 更新参考文档索引：新增 cms-samples/ 条目 + cf-bypass.md 条目 ✅ 2026-06-14

## 9. 回测验证闭环——用"优质资源(1080zyk)"验证优化效果（P0，强制）

> **不经过实际验证的优化=虚假优化。本节是本次优化的起点和终点，必须通过实际验证确认优化效果。**

- [x] 9.1 更新"优质资源-优化.json"：loginUrl 从 `startBrowserAwait()` 改为 `@js:java.webView(null, source.sourceUrl, null, false);` ✅ 2026-06-14
- [x] 9.2 HTML获取验证：`python tools/html_fetcher.py --url https://1080zyk.com/ --json`，记录获取方式和HTML来源 ✅ 2026-06-14
- [x] 9.3 CMS样本验证：`python scripts/verify-selector.py --sample references/cms-samples/maccms-v10/list.html --selector ".stui-vodlist li"` 等6个选择器逐一验证 ✅ 2026-06-14
- [x] 9.4 JVM MVP2深度验证：`python scripts/deep-verify.py --source output/rss/优质资源-优化.json`，记录每个字段可信度 ✅ 2026-06-14
- [x] 9.5 CF绕过配置验证：检查loginUrl/loginCheckJs格式是否正确 ✅ 2026-06-14
- [x] 9.6 输出验证报告：对比优化前后可信度（5个低可信 → 预期≤2个低可信） ✅ 2026-06-14
- [x] 9.7 未达标处理：如果低可信项>2个，分析原因→修复→重新验证 ✅ 2026-06-14
- [x] 9.8 记录经验：将验证结论写入basic-memory（project=legado） ✅ 2026-06-14

## 10. 集成验证（P0）

- [ ] 10.1 用非 CF 网站验证：直接获取成功，不触发回退链
- [ ] 10.2 用 SPA 网站验证（如 Playwright 已安装）：渲染后 HTML 获取成功
- [ ] 10.3 用 Wayback Machine 验证：历史快照获取成功，工具栏清理正确

## 11. 文档同步（P0）

- [ ] 11.1 更新 `docs/INDEX.md`：移动功能状态
- [ ] 11.2 更新 `docs/specs/INDEX.md`：添加到"已完成"列表
- [ ] 11.3 更新 `references/_INDEX.md`：新增 cms-samples/ 索引
- [ ] 11.4 basic-memory 经验反哺：写入 HTML 获取回退链经验 + CF 绕过经验
