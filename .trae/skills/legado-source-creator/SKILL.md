# Legado Source Creator Skill v4

> 帮助 AI 为 Legado 阅读器生成"**优秀好用**"的书源/订阅源 JSON。
> **v4 核心目标**：必填字段强制校验 + 真机测试集成 + 自动修复循环。

## 核心原则（v4）

1. **源码验证优先**：写规则前先去 Legado 源码核实，不凭经验臆测
2. **必填字段强制**：所有源必须通过 `MandatoryFieldValidator` 校验
3. **JSON 输出合规**：所有 None 字段必须经 `sanitize_source_json` 过滤为空字符串
4. **真机验证为最终标准**：JVM 仿真仅覆盖规则引擎层，真机测试集成是验收门禁
5. **自动修复闭环**：生成 → 测试 → 失败 → 自动诊断 → 修复 → 重测

## 4 阶段闭环工作流（v4）

### Phase 1: 分析（v4 强化 - 必经 Playwright）

**目标**：用 Playwright MCP 真实分析网站结构 + 找同类经验。

> **🔴 铁律**（v4 强化，2026-07-18 反哺）：禁止仅凭 CMS 主题名或经验猜测字段值，**必须用 Playwright MCP 真实访问目标站点**提取4字段（sourceIcon/searchUrl/sortUrl/ruleNextPage）。
> 完整指南：[references/source-analysis/playwright-site-analysis.md](./references/source-analysis/playwright-site-analysis.md)

1. **必经 Playwright 访问**：用 `playwright_navigate` 真实访问目标站点首页（headless=True, waitUntil=domcontentloaded）
2. **必经 JavaScript 提取**：用 `playwright_evaluate` 执行 IIFE 提取4字段技术结构（favicon/searchForm/categoryLinks/pagination）
3. 搜索 `basic-memory`（project=legado）找同类经验
4. 识别触发字段：CF/登录/验证码 → 必须先源码验证再写规则
5. 把提取结果记录到 `source_ref` metadata（`verified_against_source=true`）

```python
# Playwright 提取结果 → 源 JSON 字段映射（v4 反哺辅助函数）
def build_search_url(form_info):
    """从表单信息构建 searchUrl"""
    if not form_info:
        return None
    action = form_info['action'].rstrip('?')
    text_input = next((i for i in form_info['inputs'] if i['type'] in ('text', 'search')), None)
    if text_input:
        sep = '&' if '?' in action else '?'
        return f"{action}{sep}{text_input['name']}={{{{key}}}}"
    return None

def build_sort_url(category_links, hot_links, base_url):
    """从分类链接+排序参数构建 sortUrl"""
    items = []
    if hot_links:
        items.append(f"热门::{hot_links[0]}")
    if category_links:
        all_cat = next((l for l in category_links if '/categories/' in l['href']), None)
        if all_cat:
            items.append(f"全部分类::{all_cat['href']}")
    items.append(f"最新::{base_url}")
    return '\n'.join(items)

def extract_next_page_selector(pagination_html):
    """从分页HTML提取下一页CSS选择器"""
    if not pagination_html:
        return None
    if 'next page-link' in pagination_html:
        return '@CSS:a.next.page-link@href'
    if 'class="next"' in pagination_html:
        return '@CSS:a.next@href'
    if 'rel="next"' in pagination_html:
        return '@CSS:a[rel="next"]@href'
    return None
```

### Phase 2: 生成 + 必填校验（v4 强化）

**目标**：编写源 JSON + sanitize + 必填字段强制校验。

1. 按 [references/](./references/) 写源 JSON
2. **必经 sanitize**：所有 None 值会触发 Legado Rss.kt:64 ReferenceError
3. **必经 MandatoryFieldValidator 校验**（v4 新增）：

```python
from legado_client.utils.file_utils import sanitize_source_json
from legado_client.validator import validate_source, format_validation_report

# 1. sanitize 清理 None
sanitized = sanitize_source_json(source_dict)

# 2. 必填字段强制校验（strict_recommended=True 用户"优秀好用"标准）
result = validate_source(sanitized, source_type='rss', strict_recommended=True)
if not result['passed']:
    print(format_validation_report(result))
    # CRITICAL 缺失（sourceUrl）→ 必须补全才能继续
    # MANDATORY 缺失（ruleArticles 等）→ 必须补全
    # RECOMMENDED 缺失（sourceIcon/searchUrl/sortUrl）→ 用户要求必填，必须补全
    raise ValueError("必填字段校验未通过")
```

### Phase 3: 真机验证（v4 集成）

**目标**：编译+安装+导入+真机测试+日志分析。

```python
from legado_client.runtime import validate_source_on_device

# 端到端真机验证（自动调用 ai_tests 脚本）
result = validate_source_on_device(
    source_obj=sanitized,
    source_type='rss',
    skip_build=False,  # True=跳过编译（APK 已装）
)
if not result['success']:
    for err in result['errors']:
        print(f"[{err['stage']}] {err['message']}")
```

或手动跑固定脚本（SOP: [fixed_test_workflow.md](../../ai_tests/docs/fixed_test_workflow.md)）：

```bash
ai_tests/venv/Scripts/python.exe ai_tests/scripts/quick_build_install.py
ai_tests/venv/Scripts/python.exe ai_tests/scripts/import_rss_source.py <json>
ai_tests/venv/Scripts/python.exe ai_tests/scripts/l2_verify_video_player.py --scenario error_patterns
```

### Phase 4: 自动修复循环（v4 新增）

**目标**：失败 → 自动诊断 → 修复 → 重测。

```python
from legado_client.runtime import auto_fixer_loop

# 一键自动修复循环
result = auto_fixer_loop(
    source_obj=source_dict,
    source_type='rss',
    max_attempts=3,
    skip_build=False,
    strict_recommended=True,
)
if result['success']:
    print(f"修复成功，最终源: {result['final_source']}")
else:
    print(f"修复失败，剩余错误: {result['remaining_errors']}")
    print(f"修复轨迹: {result['fix_history']}")
```

## v4 必填字段清单（基于源码深度分析）

> 完整分析：[docs/temp-analysis/legado_mandatory_fields.md](../../docs/temp-analysis/legado_mandatory_fields.md)

### RssSource 字段级别

| 级别 | 字段 | 不填后果 |
|------|------|----------|
| **CRITICAL** | `sourceUrl` | 导入时抛 NoStackTraceException("不是订阅源") |
| **MANDATORY** | `sourceName`/`ruleArticles`/`ruleTitle`/`ruleLink`/`ruleContent` | 核心功能失效（无名称/无列表/无标题/无链接/无正文） |
| **RECOMMENDED** | `sourceIcon`/`searchUrl`/`sortUrl`/`sourceGroup`/`sourceComment` | 用户要求必填（优秀好用标准） |

### BookSource 字段级别

| 级别 | 字段 | 不填后果 |
|------|------|----------|
| **CRITICAL** | `bookSourceUrl` | 导入时抛 NoStackTraceException("不是书源") |
| **MANDATORY** | `bookSourceName`/`searchUrl`/`ruleSearch.bookList`/`ruleBookInfo.name`/`ruleToc.chapterList`/`ruleContent.content` | 核心功能失效 |
| **RECOMMENDED** | `bookSourceGroup`/`bookSourceComment` | 优秀好用标准 |

### 设计哲学

Legado 源码采用"**最小必填 + 渐进增强**"模式：
- 导入层面只校验 @PrimaryKey 非空（CRITICAL）
- 功能层面通过 `isNullOrBlank` 判断动态降级（MANDATORY 缺失时功能降级而非崩溃）
- v4 校验器在"功能必填"基础上加上用户要求的"优秀好用"标准（RECOMMENDED 强制）

## 核心陷阱速查（Top 20）

> 完整陷阱库见 [references/troubleshooting/](./references/troubleshooting/)

### JSON 输出陷阱

1. **None 序列化 bug**（v3 修复）：Python None → 字符串 "None" → Rss.kt:64 当 JS 执行 → ReferenceError。**修复**：用 `sanitize_source_json` 过滤
2. **loginUrl 禁用 `@js:java.webView()`**：WebViewLoginFragment.loadUrl() 不识别 @js: 形式
3. **loginCheckJs 陷阱**：每次请求执行，调 `java.startBrowserAwait()` 导致无限循环
4. **header 字段格式**：必须是 JSON 字符串（`json.dumps`），不是 dict

### 规则引擎陷阱

5. **@CSS vs class.**：`@CSS:.item` 与 `class.item` 等价但混用出错
6. **@XPath 转义**：属性值含 `"` 必须用 `'` 包裹
7. **@js 内联 vs `<js>` 标签**：前者追加在规则后，后者独立块
8. **put/get 变量**：跨规则传值必须用 `@put:{key:rule}` + `@get:{key}`
9. **列表规则返回 string**：必须用 `||` 分隔多结果
10. **正则 `{{}}` 陷阱**：`{{regex}}` 用于匹配，`{{regex|replace}}` 用于替换

### 网站类型陷阱

11. **CF 站点**：检查 `<title>Just a moment</title>` 或 `cf-challenge` cookie
12. **登录站点**：必须配置 loginUrl + 人工登录后才能爬取
13. **验证码站点**：无法自动绕过，标记 unverifiable
14. **图片加密**：先校验块对齐（DES=8, AES=16, SM4=16）
15. **JS 解密**：用 `crypto_analyzer.py` 扫描加密调用

### 真机验证陷阱

16. **Room WAL 模式**：导入前必须 `am force-stop` App，否则 WAL 覆盖
17. **Cookie 自动同步**：JVM 仿真不覆盖，必须真机验证
18. **WebView 生命周期**：destroy/setLayoutParams 必须在 UI 线程
19. **JS 引擎返回值**：类型不可信，必须类型容错（is ByteArray / is InputStream）
20. **ExoPlayer cacheDataSourceFactory**：上游 OkHttpDataSource 不支持 file://

## 工具脚本

### v4 核心模块（legado_client）

| 模块 | 用途 |
|------|------|
| `legado_client.validator.MandatoryFieldValidator` | 必填字段强制校验（CRITICAL/MANDATORY/RECOMMENDED 三级） |
| `legado_client.runtime.RuntimeValidator` | 真机测试集成验证器（编译+安装+导入+L2+logcat） |
| `legado_client.runtime.auto_fixer_loop` | 自动修复循环（生成→测试→诊断→修复→重测） |
| `legado_client.utils.sanitize_source_json` | None 序列化 bug 修复 |
| `legado_client.analyzer.auto_fix_error` | 错误自动修复（12 种自动 + 5 种需用户介入） |

### 调试脚本（scripts/）

| 脚本 | 用途 |
|------|------|
| `scripts/debug-source.py --source PATH --key KEY --stage all` | 端到端调试（首选） |
| `scripts/quick-verify.py` | 静态可用性检查 |

### 真机测试脚本（ai_tests/scripts/）

| 脚本 | 用途 |
|------|------|
| `ai_tests/scripts/quick_build_install.py` | 编译+安装+L1 验证 |
| `ai_tests/scripts/import_rss_source.py <json>` | 导入订阅源到 legado.db（含 WAL 处理） |
| `ai_tests/scripts/l2_verify_video_player.py --scenario error_patterns` | L2 视频播放器验证 |
| `ai_tests/scripts/skill_e2e_test.py` | Skill v4 E2E 测试（14 用例） |
| `ai_tests/scripts/export_rss_sources.py` | 从模拟器反向导出订阅源到 JSON（批量优化起点） |
| `ai_tests/scripts/batch_optimize_sources.py` | Playwright 批量分析站点补全4字段 |
| `ai_tests/scripts/fix_rule_next_page.py` | 修复批量脚本导致的字段错误值（'page'/'None'等） |
| `ai_tests/scripts/verify_rss_scenarios.py` | 4场景真机验证（列表/搜索/分类/下一页） |
| `ai_tests/scripts/analyze_rule_prefix.py` | 字段前缀分布分析（用于诊断） |

## JVM 仿真器能力边界

> **v3 修正声明**（2026-07-17）：JVM 仿真覆盖规则引擎层 85-90%，**不覆盖** WebView/Activity/Cookie/真机网络栈。

| 能力 | 覆盖率 | 说明 |
|------|--------|------|
| Rhino JS 执行 | ✅ 85-90% | 规则引擎层 |
| jsoup CSS 选择器 | ✅ 100% | 完整支持 |
| hutool 加密 | ✅ 100% | AES/DES/SM4 |
| AnalyzeRule | ✅ 100% | 规则解析器 |
| WebView | ❌ 0% | 必须真机 |
| Activity 生命周期 | ❌ 0% | 必须真机 |
| Cookie 自动同步 | ❌ 0% | 必须真机 |
| 真机网络栈 | ❌ 0% | 必须真机 |

**降级路径**：JVM 可用 → RuleEngineServer → JDK 不可用 → Python 仿真 → 标记"未验证"

## basic-memory 操作（project=legado）

| 操作 | MCP 工具 |
|------|---------|
| 搜索经验 | `search_notes(query="{关键词}", search_type="hybrid", project="legado")` |
| 读取笔记 | `read_note(identifier="{标题}", project="legado")` |
| 写入笔记 | `write_note(title, content, directory, project="legado")` |
| 编辑笔记 | `edit_note(identifier, operation, content, project="legado")` |

**L3 目录结构**：traps/ | patterns/ | experiences/ | verifications/ | cases/

## v4 重构变更（2026-07-18）

### 新增（v4）

- `legado_client/validator/`：必填字段校验器包
  - `mandatory_fields.py`：三级字段清单（CRITICAL/MANDATORY/RECOMMENDED）
  - `MandatoryFieldValidator` 类 + `validate_source()` 便捷函数
- `legado_client/runtime/`：真机测试集成包
  - `runtime_validator.py`：复用 ai_tests 10 lib 模块 + 7 固定脚本
  - `auto_fixer_loop.py`：生成→测试→诊断→修复→重测闭环
- `auto_fix_error()` 入口集成 `MandatoryFieldValidator`：
  - CRITICAL 缺失 → 直接返回失败，不进入修复流程
  - MANDATORY/RECOMMENDED 缺失 → 加入 `missing_fields` 清单

### v3 保留

- `sanitize_source_json()` 函数：None 序列化 bug 修复
- `ai_tests/scripts/skill_e2e_test.py`：端到端测试（v4 升级到 14 用例）
- 6 大核心脚本（debug/quick-verify/verify-selector/verify-decrypt/verify-image/analyze-site）
- `legado_client/` 包内核心模块（analyzer/client/delegate/experience/utils）
- `references/` 知识库（85 文档，T6 待合并到 ≤25）

### v3 归档模块（不可用）

以下模块已归档到 `.trae/skills/legado-source-creator-archive/`：
- `legado_client/web/`（Vue3 前端）
- `legado_client/storage/`（MySQL ORM）
- `legado_client/server/`（FastAPI）
- `legado_client/device/`（设备管理）
- `legado_client/fetcher/`（source_parser）
- `scripts/alembic/`（DB 迁移）
- 45 个一次性脚本

## 完整参考

- [references/](./references/) - 规则语法、JS 模式、特殊场景、故障排除完整知识库
- [docs/specs/legado-skill-v4-rebuild/](../../docs/specs/legado-skill-v4-rebuild/) - v4 重构设计文档
- [docs/temp-analysis/legado_mandatory_fields.md](../../docs/temp-analysis/legado_mandatory_fields.md) - 必填字段源码分析
- [docs/temp-analysis/ai_test_reuse_for_skill.md](../../docs/temp-analysis/ai_test_reuse_for_skill.md) - ai_test 复用分析
- [ai_tests/docs/fixed_test_workflow.md](../../ai_tests/docs/fixed_test_workflow.md) - 真机测试 SOP
- [references/source-analysis/playwright-site-analysis.md](./references/source-analysis/playwright-site-analysis.md) - Playwright 网站真实分析指南
- [references/source-analysis/batch-optimization-patterns.md](./references/source-analysis/batch-optimization-patterns.md) - 批量优化模式与陷阱

## 批量优化工作流（v4 反哺 2026-07-18）

> 65 个订阅源批量优化的实战经验反哺。

### 5 步闭环

```
1. export_rss_sources.py      从模拟器导出 N 个源
2. batch_optimize_sources.py  Playwright 逐个分析补全4字段
3. fix_rule_next_page.py      修复批量脚本导致的字段错误值
4. import_rss_source.py       导入回模拟器（含 WAL 处理）
5. verify_rss_scenarios.py    4 场景真机验证
```

### 24 大陷阱（详见 batch-optimization-patterns.md）

> v5反哺新增陷阱16-24（2026-07-18 222源批量优化实战）

**陷阱1-15（v4反哺，65源优化）**：
1. **批量脚本字段填充错误值**（最高风险）：50/65 个 ruleNextPage 被错填为 "page"。**必修**：写入前合法性校验
2. **成功率陷阱**：脚本判定"成功"未校验提取值合法性。**必修**：后置校验+自动清空
3. **Playwright 站点可达性差异**：41/65 失败（模板 URL/IP失效/CF防护）。**应对**：失败不中断+保持原值
4. **校验器字段级别动态调整**：ruleContent/ruleDescription 对视频源是 OPTIONAL。**已落实**：mandatory_fields.py
5. **4 场景真机验证误判**：`.stui-page@li@href` 被判无效。**修复**：识别无前缀 CSS 选择器
6. **Python None 序列化污染**：str(None)="None" 污染字段。**必修**：sanitize_source_json 过滤
7-15. 详见 batch-optimization-patterns.md（诊断脚本脱敏/批量脚本修复/域名迁移/导入残留/subprocess传参/Playwright异常脱敏/失败源7种重试/反爬loginUrl/模拟器DNS/JSON boolean类型）

**陷阱16-24（v5反哺，222源优化）**：
16. **占位符源多字段交叉恢复**：sourceUrl长度<20的占位符源，通过 sourceIcon/injectJs/header 等多字段交叉提取 host，恢复率85.7%
17. **Wayback Machine 是最有效的失败恢复手段**：56个失败源深度重试，Wayback 直接访问恢复24个（66.7%），远超其他策略。**必修**：Wayback 优先策略
18. **Cloudflare 防护普遍存在**：26/33 源命中 CF 防护（79%命中率）。**应对**：反爬 jsRule 配置（页面就绪检测+弹框关闭）+ loginUrl + CookieJar
19. **searchUrl 和 jsRule 是最大字段缺口**：searchUrl 仅30.6%覆盖率，jsRule 0%覆盖率。**必修**：双策略自动补全（GET/POST表单探测+弹框关闭JS）
20. **图片源 ruleContent 4 模板选择**：已有参考源原样保留（模板C，47.4%），新设计用模板A（详情页主图，52.6%）。ruleContent 必须适配 PhotoDialog 调用链
21. **视频源 ruleContent 优先嗅探器策略**：V1优先（script正则提取m3u8/mp4，66.7%）→ V3次选（iframe src）→ V2备用（sniffer留空）
22. **子代理模式比批量脚本模式效果更好**：8个子代理并行处理222源，字段补全率70-90%（vs 批量脚本30-50%）。**必修**：子代理模式批量优化工作流
23. **真机测试脚本校验过严误报**：verify_rss_scenarios.py scenario_4 仅校验3种前缀导致0%通过率。**已修复**：支持7种 legado 原生语法（class./text./page./标签./CSS选择器/属性提取/IIFE/正则兜底），通过率从0%→62.5%
24. **Cronet 库缺失导致 HTTPS 源加载失败**：libcronet.so FileNotFoundException。**必修**：真机测试前启动App等待60秒自动下载 Cronet 库

**陷阱25-28（v6反哺，订阅源年龄验证自动破除实战）**：
25. **Accept-Encoding 头导致 OkHttp 响应乱码**：手动设置 `Accept-Encoding: gzip, deflate, br` 后 OkHttp 无法解码 brotli。**必修**：永远不在 header 中设置 Accept-Encoding/Connection/Upgrade-Insecure-Requests
26. **CookieStore 过期值覆盖 header Cookie**：mergeCookies() 中 CookieStore > header，导致"时好时不好"。**必修**：loginCheckJs 中先 `cookie.removeCookie(baseUrl)` 再 `cookie.setCookie()`
27. **shouldOverrideUrlLoading 仅绑定 java 和 url**：没有 cookie/baseUrl/source/result，`{{}}` 模板也不处理。**必修**：仅使用 java 和 url 变量
28. **服务端 Cookie 年龄验证三层自动破除**：Layer1 header预置Cookie + Layer2 loginCheckJs检测+清除+重设 + Layer3 injectJs WebView自动点击。**必修**：三层防护配置

### 实战数据（65 源）

| 指标 | 数据 |
|------|------|
| Playwright 分析成功 | 24/65（37%） |
| ruleNextPage 修复后合法值 | 14/65（22%，51 个无效值已清空） |
| strict 校验通过 | 30/65（46%） |
| 列表加载通过（抽样） | 6/8（75%） |

## 任务完成标准

任务完成前必须逐项核对：

- [ ] 已用 Playwright MCP 真实访问目标站点首页（非 WebFetch/猜测）
- [ ] 4个 RECOMMENDED 字段值来自真实 DOM 提取（sourceIcon/searchUrl/sortUrl/ruleNextPage）
- [ ] 源 JSON 经 `sanitize_source_json` 过滤
- [ ] `MandatoryFieldValidator` 校验通过（strict_recommended=True）
- [ ] `skill_e2e_test.py` 14/14 通过
- [ ] 真机导入后源可正常加载（通过 `RuntimeValidator`）
- [ ] 无 ImportError / NameError 残留
- [ ] 批量优化任务：字段值经 `is_valid_*` 校验（非 INVALID_VALUES）
- [ ] 用 AskUserQuestion 向用户确认
