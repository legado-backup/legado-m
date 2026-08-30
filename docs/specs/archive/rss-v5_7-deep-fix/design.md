# RSS订阅源 V5.7 深度修复 - 技术设计

> **design.md** — 详细技术方案、失败原因明细、修复策略、工具链

---

## 0. 文档元信息

- **状态**: ✅ 设计完成（2026-07-20 审核修订后）
- **审核记录**: [audit_report.md](./audit_report.md) — 6 项阻断级问题已修订
- **ADR 决策数**: 5 项（AD-01 ~ AD-05）

---

## 1. 整体架构

```
V5.7 深度修复流水线
│
├── 阶段3-1: 4个4维度pass源定向修复（131/174/180/182）
│   ├── 注: 源[52] 已于 2026-07-20 标记为导航源移出启用清单（详见 tasks.md 2.1）
│   ├── 定位失败维度（content/search）
│   ├── mitmproxy抓包分析真实HTML
│   ├── 重写失败维度规则
│   └── 5维度真机验证
│
├── 阶段3-2: 6个多维度失败源单源深度修复（83/134/177/178/181/183）
│   ├── 选定1源 → App内置调试看错误
│   ├── mitmproxy抓包真机Cronet实际请求
│   ├── 分析真实HTML结构
│   ├── 重写全部规则（11必备字段）
│   ├── 5维度真机调试验证
│   └── 失败回到分析（最多3次）→ 通过后下一个
│
├── 阶段3-3: 1个全unknown源重新验证（176）
│   └── 重新执行5维度验证脚本
│
├── 阶段4: 15个CF盾源破盾恢复
│   ├── Google cache串行方式
│   ├── Cookie注入
│   └── User-Agent切换
│
├── 阶段5: 7个timeout源重试恢复
│   └── 直接重试 + 检查站点状态
│
├── 阶段6: 合并生成 optimized_v5_7_final.json + 全量5维度真机验证
│
└── 阶段7: 沉淀陷阱68-72 + 更新updateLog/README/skill
```

---

## 2. V5.6 单源深度修复工作流（已验证可行）

### 2.1 工作流步骤

```
步骤1: 选定 1 源 → 启动模拟器 App
步骤2: 进入 RssSourceEditActivity → 点击右上角调试按钮 → RssSourceDebugActivity
步骤3: 触发分类维度调试（tap textFl 节点）
步骤4: 等待 18 秒 → 收集 logcat
步骤5: 触发搜索维度调试（tap textMy 节点）
步骤6: 等待 18 秒 → 收集 logcat
步骤7: 分析 5 维度结果
步骤8: 失败维度 → 启动 mitmproxy 抓包
步骤9: 重启 App → 触发失败维度的请求 → 抓包获取真实 HTML
步骤10: 分析真实 HTML → 重写规则
步骤11: Edit JSON 文件 → 重新导入真机 DB
步骤12: 再次 5 维度验证
步骤13: 失败回到步骤8（最多3次）→ 通过后处理下一个源
```

### 2.2 关键技术

#### 2.2.1 mitmproxy 抓包真机 Cronet 实际请求

**原因**: PC Playwright 默认执行 JS，真机 Cronet 不执行 JS，同一 URL 返回不同 HTML 结构

**抓包配置**:
```bash
# 1. 启动 mitmproxy 在 8080 端口
mitmproxy -p 8080

# 2. 设置模拟器代理
adb shell settings put global http_proxy 127.0.0.1:8080
# 但 mitmproxy 在 PC 上，需要用 PC IP
# adb shell settings put global http_proxy <PC_IP>:8080

# 3. 安装 mitmproxy 证书到模拟器
# 下载 http://mitm.it 在模拟器中安装

# 4. 触发请求
adb shell am start -n io.legado.app.debug/io.legado.app.ui.rss.source.debug.RssSourceDebugActivity --es key "<sourceUrl>"

# 5. 在 mitmproxy 中查看请求/响应
```

#### 2.2.2 苹果CMS视频站 mt[d] 31天循环映射表（V5.6发现）

**现象**: 苹果CMS视频站的 sortUrl/searchUrl 中拼接的 base 域名会每月变化（如 .51rb10.cc → .51rb16.cc）

**根因**: 站点发布页用 JS 动态跳转到最新域名

**修复方法**: 
1. 访问站点发布页
2. 提取 JS 中的最新域名
3. 在 sourceComment 中记录映射表
4. 在 sortUrl/searchUrl 中使用最新域名

#### 2.2.3 反爬机制无法绕过的判定标准

**判定**: 页面含 `safeid` + `mainv2.js` 加密 → type=0 网页源默认用 OkHttp/Cronet 不渲染 JS，无法绕过

**处理**: 标记 enabled=false

#### 2.2.4 境外服务器IP国内不可达的判定标准

**判定**: nslookup 可解析但模拟器 DNS 不可达 → 直接标记 enabled=false（hosts 映射对 Cronet 无效）

**处理**: 标记 enabled=false

---

## 2.3 Architecture Decisions（ADR Y-Statement）

> **修订说明**: 本章节为审核修订后新增，补全 OpenSpec 规范要求的 ADR Y-Statement 模板。

### AD-01: 单源深度修复工作流选型

- **Context**: V5.7 需修复 13 个启用源，每个源的失败维度与原因不同，无法用统一模板批量处理
- **Concern**: 如何在有限时间内完成 13 源修复，且保证修复后真机验证通过
- **Decision**: 采用 V5.6 已验证的"单源深度修复工作流"（13 步操作流程，每源最多 3 次重试）
- **Goal**: 13 源 5 维度通过率从 7.7% 提升至 ≥ 80%
- **Tradeoff**: 接受单源 8-15 分钟耗时（13 源总计 4-6 小时含隐性成本），换取修复准确性
- **Status**: Accepted
- **Superseded-by**: 无

### AD-02: mitmproxy 抓包方案选型

- **Context**: PC Playwright 与真机 Cronet 执行 JS 行为不同，同一 URL 返回不同 HTML 结构
- **Concern**: 如何获取真机 Cronet 实际请求的 HTML 用于规则重写
- **Decision**: 使用 mitmproxy 在 PC 端 8080 端口启动代理，模拟器设置全局代理指向 PC IP，安装 mitmproxy CA 证书
- **Goal**: 抓取真机 Cronet 实际请求/响应，作为规则重写的真实 HTML 来源
- **Tradeoff**: 接受首次证书安装 10-15 分钟成本 + HTTPS 抓包需证书信任，换取 HTML 真实性
- **Status**: Accepted
- **Superseded-by**: 无

### AD-03: CF 盾破盾手段优先级

- **Context**: 15 个 CF 盾禁用源需要尝试恢复，存在多种破盾手段但有效率不确定
- **Concern**: 如何在多种手段中确定优先级，避免无效尝试浪费时间
- **Decision**: 按优先级顺序尝试：UA 切换（Googlebot）→ Cookie 注入（cf_clearance）→ Google cache → 标记禁用
- **Goal**: 最大化恢复率，最小化单源尝试时间
- **Tradeoff**: 接受 cf_clearance 30 分钟有效期限制（需定期更新），接受 Google cache 中国大陆可访问性不确定
- **Status**: Accepted
- **Superseded-by**: 无

### AD-04: 3 次失败后禁用策略

- **Context**: 部分源可能因站点下线/反爬机制等原因无法恢复
- **Concern**: 如何避免单源修复无限重试拖累整体进度
- **Decision**: 单源最多 3 次 mitmproxy 抓包+规则重写，仍失败则标记 enabled=false + sourceComment 追加失败原因
- **Goal**: 保证整体进度可控，13 源修复总耗时上限为 4-6 小时
- **Tradeoff**: 接受部分源永久禁用（用户已确认"无法恢复的源标记禁用"）
- **Status**: Accepted
- **Superseded-by**: 无

### AD-05: OkHttp timeout 修改决策

- **Context**: 7 个 timeout 禁用源可能是因 OkHttp 默认 connect=15s/read=60s 过短
- **Concern**: 是否修改 OkHttp timeout 配置以恢复 timeout 源
- **Decision**: 作为可选任务（T4 第 4 步），仅在直接重试失败后考虑修改；修改前需评估对书源/图片加载的全局副作用
- **Goal**: 恢复部分 timeout 源，同时不影响其他模块网络行为
- **Tradeoff**: 接受可能的全局副作用风险，换取 timeout 源恢复可能性；若有副作用则回退
- **Status**: Proposed（待 T4 执行时确认）
- **Superseded-by**: 无

---

## 3. 12个启用源失败原因明细

> **2026-07-20 决策更新**: 原 13 启用源中的源[52] 已标记为导航源移出启用清单（详见 tasks.md 2.1 决策记录），本章剩余 12 源的失败原因明细。源[52] 的历史失败记录保留作为参考但不纳入修复范围。

### 3.1 第1批（5个4维度pass源）

#### 源[52] - 4维度pass，仅差content+search

**当前状态**:
- domain: pass
- list: pass (list_size=12)
- category: pass
- content: **fail** (content_parse_failed)
- search: **fail** (search_result_empty, malformed_url)

**错误清单**:
- network:malformed_url - URL 格式错误
- content_parse_failed - 正文解析失败
- search_result_empty - 搜索结果为空

**关键日志**:
- 分类请求路径: `/sy/hx/V3.0.json`, `/sy/hx/{id}.json`, `/dy/hx/V2.1.d.json`
- 分类异常类型: IllegalArgumentException
- 搜索请求路径: `/search?q=我的&page=1`, `/beacon.min.js/v4513226cdae34746b4dedf0b4dfa099e1781791509496`

**修复方向**:
1. malformed_url: 检查 searchUrl 中是否有未替换的占位符
2. content_parse_failed: 检查 ruleContent 是否匹配真实正文HTML
3. search_result_empty: 检查 ruleSearchArticle 选择器是否匹配搜索结果页

#### 源[131] - 4维度pass，仅差content+search

**当前状态**:
- domain: pass
- list: pass (list_size=4)
- category: pass
- content: **fail** (content_parse_failed)
- search: **fail** (search_result_empty)

**错误清单**:
- content_parse_failed
- search_result_empty
- ScriptException, EcmaError, ReferenceError, constructError, notFoundError

**关键日志**:
- 分类请求路径: `/{id}/xhtml`, `/read.html?id=63e37fbadd50c`, `/read.html?id=64f469662531f`, ...
- 搜索请求路径: `/{id}/xhtml`

**修复方向**:
1. ScriptException: ruleContent 中的 JS 规则有语法错误
2. content_parse_failed: 重写 ruleContent（移除有问题的 JS，改用 CSS 选择器）
3. search_result_empty: 检查 searchUrl 模板

#### 源[174] - 4维度pass，仅差search

**当前状态**:
- domain: pass
- list: pass (list_size=18)
- category: pass
- content: pass
- search: **fail** (search_result_empty)

**错误清单**:
- search_result_empty

**关键日志**:
- 分类请求路径: `/icon.png`, `/usr/themes/photograph/bootstrap3/css/bootstrap.min.css`, ...
- 搜索请求路径: 暂无（搜索可能未触发实际请求）

**修复方向**:
1. search_result_empty: 检查 searchUrl 是否配置正确
2. 检查 ruleSearchArticle 选择器

#### 源[180] - 4维度pass，仅差search（content=skip）

**当前状态**:
- domain: pass
- list: pass (list_size=15)
- category: pass
- content: **skip** (内容规则为空)
- search: **fail** (search_list_parse_failed)

**错误清单**:
- search_list_parse_failed

**关键日志**:
- 分类请求路径: `/hm.js?fc3993ee6315a64049f3b26b7073a986`, `/`, `/game/pc/landingpage`, ...
- 搜索请求路径: `/search?q=我的&page=1`, `/hm.js?...`, `/`, `/game/pc/landingpage`, `/about/`

**修复方向**:
1. content=skip: ruleContent 为空，需要添加内容规则
2. search_list_parse_failed: 搜索请求成功但解析失败，检查 ruleSearchArticle

#### 源[182] - 4维度pass，仅差content

**当前状态**:
- domain: pass
- list: pass (list_size=20)
- category: pass
- content: **fail** (content_parse_failed)
- search: pass

**错误清单**:
- content_parse_failed
- ScriptException, EcmaError, ReferenceError, constructError, notFoundError

**关键日志**:
- 分类请求路径: `/category/app`, `/`, `/category/game`, `/top/app`, `/category/{id}`
- 搜索请求路径: `/search/{id}`, `/category/app`, `/category/game`, ...

**修复方向**:
1. ScriptException: ruleContent 中的 JS 规则有语法错误
2. content_parse_failed: 重写 ruleContent

### 3.2 第2批（6个多维度失败源）

#### 源[83] - domain=fail

**当前状态**:
- domain: **fail** (network:timeout)
- list: unknown
- category: fail
- content: unknown
- search: unknown (search_inconclusive)

**错误清单**:
- network:timeout
- category_parse_failed
- search_inconclusive

**关键日志**:
- 分类请求路径: `/`（仅根路径，可能站点首页超时）

**修复方向**:
1. timeout: 可能站点不可达，需 http→https 协议升级或换域名
2. 检查站点是否已下线

#### 源[134] - list/search/category全fail

**当前状态**:
- domain: pass
- list: **fail** (list_empty)
- category: **fail** (category_list_failed)
- content: unknown
- search: **fail** (search_result_empty)

**错误清单**:
- list_empty
- category_list_failed
- search_result_empty

**关键日志**:
- 分类请求路径: `/`, `/contact`, `/novels`, `/{id}`
- 搜索请求路径: `/search`, `/{id}`, `/novels`, `/contact`

**修复方向**:
1. list_empty: ruleArticles 选择器不匹配真实 DOM
2. 用 mitmproxy 抓包获取真实 HTML，重写 ruleArticles

#### 源[177] - list/search/category全fail

**当前状态**:
- domain: pass
- list: **fail** (list_empty)
- category: **fail** (category_list_failed)
- content: unknown
- search: **fail** (search_result_empty)

**错误清单**:
- list_empty
- category_list_failed
- search_result_empty

**关键日志**:
- 分类请求路径: `/feedback?page=function&spm=smwp..share.fb.&fburl=`
- 搜索请求路径: `/msfe-static-prod/{id}/assets/css/pcSearch-d713b23563.css`, ...

**修复方向**:
1. list_empty: ruleArticles 选择器不匹配
2. 搜索路径异常（请求了 CSS/JS 资源），可能 searchUrl 配置错误

#### 源[178] - list/category fail，search pass

**当前状态**:
- domain: pass
- list: **fail** (list_empty)
- category: **fail** (category_list_failed)
- content: unknown
- search: pass（有 ScriptException 但仍判定 pass）

**错误清单**:
- list_empty
- category_list_failed
- ScriptException, EcmaError, ReferenceError, constructError, notFoundError

**关键日志**:
- 分类请求路径: `/special/`
- 搜索请求路径: `/favicon.ico`, `/`, `/newsapp/#f=topnav`, ...

**修复方向**:
1. list_empty: ruleArticles 选择器不匹配（但搜索能解析出列表，说明搜索结果HTML与首页HTML结构不同）

#### 源[181] - list/search/category全fail，status_500

**当前状态**:
- domain: pass
- list: **fail** (list_empty)
- category: **fail** (category_list_failed)
- content: unknown
- search: **fail** (search_result_empty)

**错误清单**:
- list_empty
- category_list_failed
- search_result_empty
- network:status_500

**关键日志**:
- 分类状态码: [500]

**修复方向**:
1. status_500: 站点服务器异常，可能需要等待或换域名
2. 可能站点已不可用

#### 源[183] - list/search/category全fail

**当前状态**:
- domain: pass
- list: **fail** (list_empty)
- category: **fail** (category_list_failed)
- content: unknown
- search: **fail** (search_result_empty)

**错误清单**:
- list_empty
- category_list_failed
- search_result_empty

**关键日志**:
- 搜索请求路径: `/search?q=我的&page=1`

**修复方向**:
1. list_empty: ruleArticles 选择器不匹配
2. 搜索请求成功但结果为空，可能站点搜索功能本身有问题

### 3.3 第3批（1个全unknown源）

#### 源[176] - 全unknown

**当前状态**:
- domain: unknown
- list: unknown
- category: unknown
- content: unknown
- search: pass（但其他维度全 unknown）

**关键日志**:
- category_log_lines: 0（分类维度未触发调试）
- search_log_lines: 114（搜索维度有日志但其他维度无）
- 搜索异常类型: ScriptException, EcmaError, ReferenceError, constructError, notFoundError

**修复方向**:
1. 重新执行 5 维度验证（可能是验证脚本异常导致 round1 未触发）
2. 检查 RssSourceDebugActivity 是否正确启动

---

## 4. CF 盾源破盾方案

### 4.1 Google cache 串行方式

**原理**: 通过 Google 缓存访问站点，绕过 CF 盾的 IP 检测

**配置**:
```
sourceUrl: https://webcache.googleusercontent.com/search?q=cache:<原URL编码>
```

**限制**:
- Google cache 可能不更新
- 部分动态内容无法获取

### 4.2 Cookie 注入

**原理**: 注入 cf_clearance cookie 绕过 CF 盾

**配置**:
```json
{
  "header": "Cookie: cf_clearance=<value>\r\nReferer: <原URL>\r\nUser-Agent: <UA>"
}
```

**限制**:
- cf_clearance cookie 有效期短（通常 30 分钟）
- 需要定期更新

### 4.3 User-Agent 切换

**原理**: 用 Googlebot UA 让 CF 盾放行

**配置**:
```
header: "User-Agent: Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
```

**限制**:
- 部分站点会屏蔽 Googlebot
- 可能返回简化版 HTML

---

## 5. timeout 源重试方案

### 5.1 直接重试

**步骤**:
1. 用 `ai_tests/scripts/retry_failed_rss_sources.py` 重试 7 个 timeout 源
2. 14 种技术手段（5 种 UA + 多种重试策略）
3. 成功的源重新启用 + 5 维度真机验证

### 5.2 延长 timeout

> **修订说明**: 原文档路径错误（`CronetHelper.kt` 不在 `help/http/` 下，且无 timeout 配置）。实际 timeout 配置在 `HttpHelper.kt`，语法为链式调用而非赋值。

**修改文件**: `app/src/main/java/io/legado/app/help/http/HttpHelper.kt`（[L87-L91](../../../app/src/main/java/io/legado/app/help/http/HttpHelper.kt#L87-L91)）

**当前配置**（HttpHelper.kt L87-L91）:
```kotlin
val builder = OkHttpClient.Builder()
    .connectTimeout(15, TimeUnit.SECONDS)   // 15s
    .writeTimeout(15, TimeUnit.SECONDS)     // 15s
    .readTimeout(60, TimeUnit.SECONDS)      // 60s
    .callTimeout(60, TimeUnit.SECONDS)      // 60s
```

**修改后**（建议）:
```kotlin
val builder = OkHttpClient.Builder()
    .connectTimeout(30, TimeUnit.SECONDS)   // 30s
    .writeTimeout(30, TimeUnit.SECONDS)     // 30s
    .readTimeout(120, TimeUnit.SECONDS)     // 120s
    .callTimeout(120, TimeUnit.SECONDS)     // 120s
```

**注意**:
- 修改后需要重新编译 APK
- ⚠️ **全局副作用警告**: HttpHelper.kt 的 OkHttpClient 是全局共享，修改 timeout 会影响书源/订阅源/图片加载等所有网络请求，需评估副作用
- 建议：仅作为 T4 第 4 步的可选任务，修改后需全量回归测试

### 5.3 检查站点状态

**步骤**:
1. PC 用 curl 访问站点（不通过 Cronet）
2. 确认站点是否已下线
3. 已下线的源标记 enabled=false 并记录

---

## 6. 工具链

### 6.1 mitmproxy 抓包工具

**安装**:
```bash
pip install mitmproxy
```

**启动**:
```bash
mitmproxy -p 8080
```

**配置模拟器代理**:
```bash
adb shell settings put global http_proxy <PC_IP>:8080
```

**安装证书**:
- 模拟器浏览器访问 `http://mitm.it`
- 下载 mitmproxy-ca-cert.pem
- 安装到系统证书

### 6.2 Playwright 工具

**用途**: 
- 提取字段建议（`v5_7_fix_missing_fields_v2.py`）
- 站点首页 HTML 分析
- UA 切换测试

### 6.3 ADB + logcat 工具

**ADB 路径**: `D:\Program Files\Microvirt\MEmu\adb.exe`
**模拟器地址**: `127.0.0.1:21503`

**logcat 分析**:
- 关注 `sourceDebug` tag 的日志
- 提取 5 维度结果（domain/list/search/category/content）
- 提取网络错误（UnknownHostException/SocketTimeoutException/SSLException等）

### 6.4 JSON 操作工具

**Python 脚本**:
- `v5_7_apply_patches.py` - 应用字段补丁
- `v5_7_debug_verify.py` - 5 维度真机验证
- `import_rss_source.py` - 导入 JSON 到真机 DB

---

## 7. 数据流

```
optimized_v5_6_final.json (184源)
    │
    ├── v5_7_fix_missing_fields_v2.py (Playwright提取字段)
    │   └── v5_7_field_suggestions_v2.json (13源字段建议)
    │
    ├── v5_7_apply_patches.py (应用补丁)
    │   └── optimized_v5_7_final.json (184源，字段100%)
    │
    ├── import_rss_source.py (导入真机DB)
    │   └── 真机DB (184源)
    │
    ├── v5_7_debug_verify.py (5维度真机验证)
    │   ├── v5_7_debug_verify_result.json (验证结果)
    │   ├── v5_7_debug_verify_report.md (验证报告)
    │   └── v5_7_debug_logs/ (logcat日志)
    │
    ├── 单源深度修复 (mitmproxy + 重写规则)
    │   ├── Edit optimized_v5_7_final.json
    │   └── 重新导入真机DB + 重新验证
    │
    └── 最终交付 optimized_v5_7_final.json
```

---

## 8. 关键经验教训（V5.1-V5.6沉淀）

### 8.1 已沉淀到 skill 的陷阱（1-67）

详见 `.trae/skills/legado-source-creator/references/source-analysis/batch-optimization-patterns.md`

### 8.2 V5.7 待沉淀的新陷阱（68-72）

- **陷阱 68**: 12 必备字段必填（用户明确要求，ruleContent 可为空）
- **陷阱 69**: 字段填充 100% ≠ 真机可用 100%
- **陷阱 70**: search_result_empty 高发（10/13 失败源）
- **陷阱 71**: content_parse_failed 高发（5/13 失败源）
- **陷阱 72**: 通用默认值模板的有效性边界

### 8.3 历史关键教训

1. **PC Playwright 验证 ≠ 真机 Cronet 验证**（V5.4发现）
2. **批量套用通用模板不可行**（V5.1集成站反模式）
3. **占位符 `[DOMAIN]` 必须在后续阶段替换**（V5.1教训）
4. **RssSource.kt 字段严格类型匹配**（V5.1 Gson 严格解析）
5. **苹果CMS视频站 mt[d] 31天循环映射表**（V5.6发现）
6. **反爬机制 safeid+mainv2.js 无法绕过**（V5.6判定标准）
7. **境外服务器IP国内不可达**（V5.6判定标准）

---

## 9. 风险与缓解

### 9.1 风险1: 单源深度修复耗时长

> **修订说明**: 原评估"2-3 小时"未含隐性成本。修订后含 mitmproxy 证书首次安装/ADB 重连/App 重启/验证等待等隐性成本。

**风险**: 每个源 8-15 分钟，13 个源总计 4-6 小时（含隐性成本）

**隐性成本明细**:
- mitmproxy 证书首次安装: 10-15 分钟（仅一次）
- ADB 连接中断重连: 每次 1-2 分钟（预估 3-5 次）
- App 重启: 每源 30s（13 源 = 6.5 分钟）
- 重新导入真机 DB: 每次 30s（13 源 = 6.5 分钟）
- 5 维度验证等待: 18s × 2 维度 × 13 源 = 8 分钟

**缓解**:
- 按批次处理（第1批5源定向修复，第2批6源深度修复，第3批1源重新验证）
- 第1批可能 1 小时内完成（只修1-2维度）
- 第2批可能需要 2-3 小时（多维度失败+多次重试）
- 第3批可能 30 分钟（仅重新验证）

### 9.2 风险2: 站点动态变化

**风险**: 站点 HTML 结构可能在修复期间变化

**缓解**:
- 每次修复后立即真机验证
- 失败后重新抓包分析

### 9.3 风险3: 3次修复仍失败

**风险**: 部分源可能 3 次修复仍失败

**缓解**:
- 失败 3 次后标记 enabled=false
- 在 sourceComment 中记录最终失败原因
- 统计最终通过率

### 9.4 风险4: 模拟器 Cronet 库未下载

**风险**: 验证脚本提示 "Cronet 库: ❌ 未下载"

**影响**: App 用 OkHttp fallback，可能与 Cronet 行为有差异

**缓解**:
- 启动 App 让其自动下载 Cronet 库
- 或检查 `/data/data/io.legado.app.debug/files/cronet/` 目录

---

## 10. 后续建议

### 10.1 立即执行

1. **接手本设计文档**：新窗口 AI 应按 tasks.md 任务清单逐项执行
2. **先做阶段3-1**：5 个 4维度pass源定向修复（最快见效）
3. **再做阶段3-2**：6 个多维度失败源单源深度修复

### 10.2 中期建议

1. **建立单源深度修复脚本库**：将 V5.6 工作流封装为可复用脚本
2. **优化字段提取算法**：当前 Playwright 提取准确率约 60%（18/34）
3. **建立站点健康度监控**：定期检查站点可用性

### 10.3 长期建议

1. **开发 AI 自动源生成器**：基于真实 HTML 自动生成完整规则
2. **建立源质量评分体系**：综合字段填充率 + 5维度通过率 + 站点稳定性
3. **用户反馈闭环**：用户报告失效源后自动触发单源深度修复

---

## 11. File Changes（文件变更清单）

> **修订说明**: 本章节为审核修订后新增，补全 OpenSpec 规范要求的 File Changes 章节。

### 11.1 必须变更的文件

| 文件路径 | 变更类型 | 变更内容 | 关联任务 |
|----------|----------|----------|----------|
| `output/rss/optimized_v5_7_final.json` | 修改 | 13 源字段规则重写 + CF盾/timeout 源 enabled 翻转 | T2/T3/T4/T6 |
| `app/src/main/assets/updateLog.md` | 修改 | 追加 V5.7 条目（编译前更新） | T7.2 |
| `.trae/skills/legado-source-creator/references/source-analysis/batch-optimization-patterns.md` | 修改 | 追加陷阱 68-72 | T7.1 |
| `ai_tests/README.md` | 修改 | 追加 V5.7 章节 | T7.3 |
| `docs/specs/rss-batch-optimize-v2/v5_optimization_final_report.md` | 修改 | 追加 V5.7 成果 | T7.4 |

### 11.2 可选变更的文件

| 文件路径 | 变更类型 | 变更内容 | 关联任务 | 副作用评估 |
|----------|----------|----------|----------|------------|
| `app/src/main/java/io/legado/app/help/http/HttpHelper.kt` | 修改 | connectTimeout 15s→30s / readTimeout 60s→120s | T4 第4步 | ⚠️ 全局 OkHttp 客户端共享，影响书源/订阅源/图片加载，需回归测试 |

### 11.3 不变更的文件（明确范围）

| 文件路径 | 不变更理由 |
|----------|------------|
| `app/src/main/java/io/legado/app/service/CheckRssSourceService.kt` | 5 维度校验逻辑保持现状 |
| `app/src/main/java/io/legado/app/model/CheckRssSource.kt` | RssSource 校验逻辑保持现状 |
| `app/src/main/java/io/legado/app/ui/rss/source/edit/RssSourceEditActivity.kt` | 调试入口保持现状 |
| `app/src/main/java/io/legado/app/ui/rss/source/debug/RssSourceDebugActivity.kt` | 调试 Activity 保持现状 |
| RssSource 实体定义 | 不变更数据模型字段 |

### 11.4 新增的产物文件

| 文件路径 | 内容 | 关联任务 |
|----------|------|----------|
| `output/rss/v5_7_cf_recovery_result.json` | CF 盾源恢复结果 | T3 |
| `output/rss/v5_7_timeout_recovery_result.json` | timeout 源恢复结果 | T4 |
| `output/rss/v5_7_final_verify_result.json` | 最终全量验证结果 | T6 |
| `output/rss/v5_7_final_verify_report.md` | 最终验证报告 | T6 |

---

**生成时间**: 2026-07-20
**最后修订**: 2026-07-20（审核修订：6 项阻断级问题已修复，新增 ADR/File Changes 章节）
**文档版本**: v1.1
**作者**: V5.7 阶段2 完成后生成
