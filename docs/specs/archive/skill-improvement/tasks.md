# tasks.md — legado-source-creator Skill 改进

> **状态**：🔄 开发中（二次源码核实已完成） | **创建日期**：2026-06-03 | **核实日期**：2026-06-03

---

## 1. Phase 1：源码确认 + 测试验证（必须先完成）

> **验证铁律**：每项经验必须经过"源码确认 → 编写测试 → 测试通过"三步，只有测试通过才能写入正式文档。我们的项目是 lyc 魔改版（`gitee.com/lyc486/legado`），所有验证以该版本源码为准。

### 1.1 Default 语法解析逻辑验证 ✅ 已完成（二次核实通过）
- [x] 1.1.1 读取 AnalyzeByJSoup.kt，确认 `class.名称` → `.名称` 简写解析逻辑（V12）— 源码确认 L310-321
- [x] 1.1.2 读取 AnalyzeByJSoup.kt，确认 `tag.名称.位置` 语法解析（V13）— 源码确认 L314-316
- [x] 1.1.3 读取 AnalyzeByJSoup.kt，确认 `id.名称` → `#名称` 简写解析（V14）— 源码确认 L317-319
- [x] 1.1.4 读取 AnalyzeByJSoup.kt，确认 `text.文本` 格式解析（V3）— 源码确认 L320
- [x] 1.1.5 读取 AnalyzeByJSoup.kt，确认数字索引 `.0/.1/.-1` 解析（V4）— 源码确认 L482-506
- [x] 1.1.6 读取 AnalyzeByJSoup.kt，确认 `[!0:-1]` 排除数组语法（V15）— 源码确认 L418-481，**修正：!0在旧式索引中也可用**
- [x] 1.1.7 读取 AnalyzeByJSoup.kt，确认 `[-1:0]` 倒序语法（V16）— 源码确认 L418-481
- [x] 1.1.8 编写 Python 测试脚本，模拟 Default 语法解析并验证结果 — temp/verify_skill_docs.py 26 PASS
- [x] 1.1.9 将源码确认+测试结果写入 references/source-analysis/default-syntax.md — 已完成并修正

### 1.2 选择器兼容性验证 ✅ 已完成（二次核实通过）
- [x] 1.2.1 读取 AnalyzeByJSoup.kt，确认 `@css:` 前缀下 `:first-child/:last-child` 是否可用（V1）— 确认可用
- [x] 1.2.2 读取 AnalyzeByJSoup.kt，确认 `:contains()` 在不同模式下的可用性（V2）— 确认可用
- [x] 1.2.3 编写 Python + jsoup 测试脚本，验证选择器兼容性 — temp/verify_skill_docs.py 覆盖
- [x] 1.2.4 将源码确认+测试结果写入 references/source-analysis/default-syntax.md — 已合并到 1.1

### 1.3 变量系统验证 ✅ 已完成（二次核实通过）
- [x] 1.3.1 读取 AnalyzeRule.kt，确认 `@put/@get` 与 `java.put/java.get` 的区别（V8）— 源码确认 L946-948, L454-477, L656-658
- [x] 1.3.2 读取 AnalyzeRule.kt，确认 JS 中无法使用 `@get` 的限制（V9）— 确认
- [x] 1.3.3 编写测试脚本验证变量系统 — temp/verify_skill_docs.py 覆盖
- [x] 1.3.4 将源码确认+测试结果写入 references/rule-syntax.md — 已完成

### 1.4 正则模式验证 ✅ 已完成（二次核实通过）
- [x] 1.4.1 读取 AnalyzeRule.kt，确认 `###` 结尾的 OnlyOne 模式（V6）— 源码确认 L487-496
- [x] 1.4.2 读取 AnalyzeRule.kt，确认 `:` 开头的 AllInOne 模式（V7）— 源码确认 L531-543（splitSourceRule方法）
- [x] 1.4.3 编写 Python 测试脚本，模拟正则三种模式的解析行为 — temp/verify_skill_docs.py 覆盖
- [x] 1.4.4 将源码确认+测试结果写入 references/rule-syntax.md — 已完成

### 1.5 WebView/webJs 验证 ✅ 已完成（二次核实通过）
- [x] 1.5.1 读取 BackstageWebView.kt，确认 webJs 必须有返回值的限制（V10）— 源码确认 L236+L249-278，重试30次约29秒
- [x] 1.5.2 编写测试脚本验证 webJs 返回值为空时的行为 — temp/verify_skill_docs.py 覆盖
- [x] 1.5.3 将源码确认+测试结果写入 references/js-extensions/webview.md — 已完成

### 1.6 Rhino 陷阱验证 ✅ 已完成（二次核实通过）
- [x] 1.6.1 读取 RhinoScriptEngine.kt，确认 `const` 块级作用域问题（V11）— 源码确认 L323, VERSION_ES6
- [x] 1.6.2 编写测试脚本验证 — temp/verify_skill_docs.py 覆盖
- [x] 1.6.3 将源码确认+测试结果写入 AGENTS.md 陷阱清单 — 已完成（#21-#25）

### 1.7 全局对象方法验证 ✅ 已完成（二次核实通过）
- [x] 1.7.1 读取 BaseBook.kt，确认 `book.putVariable/getVariable` 存在性（V31）— 源码确认 L19-24, RuleDataInterface.kt L32-34
- [x] 1.7.2 读取 BookChapter.kt，确认 `chapter.putVariable/getVariable/putLyric/putImgUrl/update()` 存在性（V32）— 源码确认 L69-101
- [x] 1.7.3 读取 BaseSource.kt，确认 `source.put/get` 和登录头管理方法存在性（V33/V34）— 源码确认 L275-312
- [x] 1.7.4 读取 CookieStore.kt，确认 `cookie.getKey/replaceCookie/setWebCookie` 存在性（V35）— 源码确认 L37-92，**修正：方法在CookieStore.kt非CookieManager.kt**
- [x] 1.7.5 读取 CacheManager.kt，确认 `cache.putFile/getFile/putMemory/getFromMemory` 存在性（V36）— 源码确认，**修正：cache对象类型是CacheManager非WebCacheManager**
- [x] 1.7.6 编写测试脚本验证全局对象方法 — temp/verify_skill_docs.py 覆盖
- [x] 1.7.7 将源码确认+测试结果写入 references/js-extensions/global-objects.md — 已完成并修正

### 1.8 编码/网络方法验证 ✅ 已完成（二次核实通过）
- [x] 1.8.1 读取 AnalyzeUrl.kt，确认 charset 参数处理流程（V18/V20）— 源码确认 L233-255, L783, L837-842
- [x] 1.8.2 读取 JsExtensions.kt，确认 `java.s2t()/java.t2s()` 存在性（V21）— 源码确认 L680/L685
- [x] 1.8.3 读取 JsExtensions.kt，确认 `java.encodeURI(str, enc)` 签名（V22）— 源码确认 L657/L666，**修正：第二参数名是enc非charset**
- [x] 1.8.4 读取 JsExtensions.kt，确认 `java.utf8ToGbk(str)` 存在性（V23）— **不存在**，已从文档移除
- [x] 1.8.5 读取 JsExtensions.kt，确认 `java.ajaxAll(urlList, skipRateLimit)` 签名（V24）— 源码确认 L124-138
- [x] 1.8.6 编写测试脚本验证编码/网络方法 — temp/verify_skill_docs.py 覆盖
- [x] 1.8.7 将源码确认+测试结果写入 references/js-extensions/network.md — 已完成

### 1.9 登录/加密/字体方法验证 ✅ 已完成（二次核实通过）
- [x] 1.9.1 读取 JsEncodeUtils.kt，确认 `java.createAsymmetricCrypto()` 存在性（V25）— 源码确认 L80-84，**修正：定义在JsEncodeUtils.kt非JsExtensions.kt**
- [x] 1.9.2 读取 JsExtensions.kt，确认 `java.queryTTF()/java.replaceFont()` 存在性（V26/V27）— 源码确认 L962-1053，**修正：replaceFont第四参数名是filter非isSave**
- [x] 1.9.3 读取 JsExtensions.kt，确认 `java.getVerificationCode()` 存在性（V28）— 源码确认 L354
- [x] 1.9.4 读取 AnalyzeUrl.kt，确认 `initUrl()/getStrResponse()` 存在性（V29/V30）— 确认
- [x] 1.9.5 编写测试脚本验证登录/加密/字体方法 — temp/verify_skill_docs.py 覆盖
- [x] 1.9.6 将源码确认+测试结果写入 references/js-extensions/crypto-encoding.md — 已完成并修正

---

## 2. Phase 2：文档改进（基于验证结果）

### 2.1 Default 语法体系文档（P0） ✅ 已完成
- [x] 2.1.1 在 references/rule-syntax.md 新增"Default 语法"章节
- [x] 2.1.2 记录 class/tag/id 前缀简写规则
- [x] 2.1.3 记录数组/区间/排除语法
- [x] 2.1.4 记录属性选择器高级用法
- [x] 2.1.5 记录 `@` 连接空格替代和 `text.文本` 格式
- [x] 2.1.6 记录选择器优先级

### 2.2 全局对象 API 文档（P0） ✅ 已完成
- [x] 2.2.1 新建 references/js-extensions/global-objects.md
- [x] 2.2.2 记录 book 对象完整属性 + 方法
- [x] 2.2.3 记录 chapter 对象完整属性 + 方法
- [x] 2.2.4 记录 source 对象完整方法
- [x] 2.2.5 记录 cookie 对象完整方法
- [x] 2.2.6 记录 cache 对象完整方法 — **修正：类型为CacheManager非WebCacheManager**
- [x] 2.2.7 记录全局变量列表

### 2.3 变量系统补充（P1） ✅ 已完成
- [x] 2.3.1 在 references/rule-syntax.md 补充 `@put/@get` vs `java.put/java.get` 区别
- [x] 2.3.2 补充 JS 中无法使用 `@get` 的限制
- [x] 2.3.3 补充 `{{java.get()}}` 模板调用方式
- [x] 2.3.4 补充 `@@` 前缀说明 — **修正：@@是强制Default模式前缀，非跨栏目取值**

### 2.4 搜索高级技巧文档（P1） ✅ 已完成
- [x] 2.4.1 新建 references/special-scenarios/search-advanced.md
- [x] 2.4.2 记录 Cookie 清理、重定向处理、繁简转换等 6 种模式 — **修正：java.post()返回Connection.Response非StrResponse**

### 2.5 详情/目录/正文高级技巧文档（P1） ✅ 已完成
- [x] 2.5.1 新建 references/special-scenarios/content-advanced.md — **修正：##^##/##$##是正则锚点组合非专用语法；{{$.}}不合法，应使用{{baseUrl}}**
- [x] 2.5.2 新建 references/special-scenarios/toc-advanced.md
- [x] 2.5.3 记录 URL 拼接、目录排序、正文去章节名/去重复/段落拼接等模式

### 2.6 编码处理完整指南（P1） ✅ 已完成
- [x] 2.6.1 新建 references/special-scenarios/encoding-guide.md
- [x] 2.6.2 记录编码判断三步法、charset 参数位置、GBK 兼容性

### 2.7 动态加载处理系统化（P1） ✅ 已完成
- [x] 2.7.1 在 references/js-extensions/webview.md 补充四种 webView 启用方式
- [x] 2.7.2 补充 webJs 必须有返回值的限制
- [x] 2.7.3 补充 sourceRegex 嗅探完整流程

### 2.8 登录系统 API 补充（P2） ✅ 已完成
- [x] 2.8.1 在 references/special-scenarios/login.md 补充 loginCheckJs API
- [x] 2.8.2 补充 source 对象登录头/登录信息管理
- [x] 2.8.3 补充 CloudFlare 验证处理模式

### 2.9 HTML 分析检查清单（P2）
- [ ] 2.9.1 新建 references/html-analysis-checklist.md
- [ ] 2.9.2 记录搜索页/详情页/目录页/正文页字段完整性检查清单
- [ ] 2.9.3 记录浏览器 DOM vs 原始 HTML 差异表

### 2.10 nextContentUrl 判断规则（P2） ✅ 已完成
- [x] 2.10.1 在 references/rule-syntax.md 补充三种场景判断规则
- [x] 2.10.2 补充 select 下拉菜单分页处理

### 2.11 正则表达式三种用法分类（P2） ✅ 已完成
- [x] 2.11.1 在 references/rule-syntax.md 补充删除/替换/捕获组提取三种用法
- [x] 2.11.2 补充 OnlyOne 模式 `###` 和 AllInOne 模式 `:`

### 2.12 新增 Rhino 陷阱（P0） ✅ 已完成
- [x] 2.12.1 在 AGENTS.md 陷阱清单新增 Rhino `const` 块级作用域问题
- [x] 2.12.2 新增 JSON.stringify 中变量类型问题
- [x] 2.12.3 新增 webJs 必须有返回值
- [x] 2.12.4 新增 loginCheckJs 必须返回 result

### 2.13 JS 扩展方法补充（P2） ✅ 已完成
- [x] 2.13.1 在 references/js-extensions/crypto-encoding.md 补充非对称加密/签名/strToBytes/bytesToStr — **修正：方法定义在JsEncodeUtils.kt**
- [x] 2.13.2 在 references/js-extensions/network.md 补充 ajaxAll/ajaxTestAll/head/webViewGetOverrideUrl
- [x] 2.13.3 在 references/js-extensions/font-anti-crawl.md 补充 queryTTF/replaceFont — **修正：replaceFont第四参数名是filter**
- [x] 2.13.4 在 references/js-extensions/utils.md 补充 s2t/t2s/encodeURI/timeFormat 等

### 2.14 高级功能模式库（P2）
- [ ] 2.14.1 新建 references/special-scenarios/advanced-patterns.md
- [ ] 2.14.2 记录 jsLib/多接口切换/LZString/源变量控制/图片解密模式

---

## 3. Phase 3：SKILL.md 流程优化

### 3.1 流程改进 ✅ 已完成
- [x] 3.1.1 在 SKILL.md 步骤1"分析目标网站"前增加"必读参考文档"子步骤
- [x] 3.1.2 在步骤1中增加"编码检测"子步骤（强制）
- [x] 3.1.3 在步骤1中增加"获取原始 HTML"子步骤（强制，不信任浏览器 DOM）

### 3.2 导航更新 ✅ 已完成
- [x] 3.2.1 更新 AI_README.md 导航索引，添加新增文档
- [x] 3.2.2 更新 references/_INDEX.md（如存在）

---

## 4. 验证与归档

### 4.1 最终验证 ✅ 已完成（二次源码核实）
- [x] 4.1.1 检查所有新增文档的内容与 Legado 源码一致性 — 4个子代理并行核实，发现12处错误已修正
- [x] 4.1.2 检查 SKILL.md 流程是否完整覆盖新增步骤 — 已覆盖
- [x] 4.1.3 检查 AGENTS.md 陷阱清单是否包含所有新陷阱 — 已包含（#21-#25）

### 4.2 文档同步
- [ ] 4.2.1 更新 docs/specs/INDEX.md 状态
- [ ] 4.2.2 清理临时分析文档 temp/skill-comparison-design-doc.md

---

## 二次源码核实修正记录（2026-06-03）

> 4个子代理并行对照 Legado 源码逐条核实，发现并修正以下 12 处错误：

| # | 文档 | 错误内容 | 修正后 |
|---|------|----------|--------|
| 1 | rule-syntax.md | `@@` 是"跨栏目取值语法" | `@@` 是强制 Default 模式前缀（AnalyzeRule.kt L608-611） |
| 2 | content-advanced.md | `{{$.}}` 代表当前详情页 URL | `{{$.}}` 不合法，JS 中 `$` 未定义，应使用 `{{baseUrl}}` |
| 3 | content-advanced.md | `##^##` / `##$##` 是专用语法 | 是 `##` 分隔符 + 正则 `^`/`$` 锚点的组合效果 |
| 4 | rule-syntax.md | `+` 前缀实现升序排序 | `+` 仅剥离前缀，无排序逻辑（BookChapterList.kt L58-59） |
| 5 | rule-syntax.md | `-` 前缀是"取反" | `-` 是"阻止默认反转"标记（BookChapterList.kt L54-56） |
| 6 | default-syntax.md | `!0` 排除语法仅在新式索引中可用 | 旧式索引中也可用（AnalyzeByJSoup.kt L491） |
| 7 | global-objects.md | cache 对象类型是 WebCacheManager | 类型是 CacheManager（BaseSource.kt L331 等） |
| 8 | search-advanced.md | java.post() 返回 StrResponse | 返回 Connection.Response（Jsoup）（JsExtensions.kt L535） |
| 9 | file-operations.md | importScript 参数名 urlStr | 参数名是 path（JsExtensions.kt L363） |
| 10 | default-syntax.md | @js:/<js> 前缀在 SourceRule.init 中识别 | 在 splitSourceRule() 方法中识别（AnalyzeRule.kt L545-555） |
| 11 | rule-syntax.md | allInOne 实现在 AnalyzeByJSoup | 实现在 AnalyzeRule.splitSourceRule()（L531-543） |
| 12 | crypto-encoding.md | 加密方法定义在 JsExtensions.kt | 定义在 JsEncodeUtils.kt，JsExtensions 通过继承可用 |

> 测试脚本：`temp/verify_skill_docs.py`，结果：26 PASS, 0 FAIL, 13 WARN
