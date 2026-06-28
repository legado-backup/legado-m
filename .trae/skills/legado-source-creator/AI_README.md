# Legado Source Creator - AI 使用指南

> 本skill用于帮助AI快速创建、优化、测试、修复Legado书源和订阅源。

## 金字塔架构

```
L1: SKILL.md (488行)        ← 决策入口：触发条件+陷阱速查+5阶段工作流+L3操作规范+JVM测试基础设施+代码进化
L2: references/ (6大目录)    ← 完整知识库：代码示例+详细解释+修复方案
L3: basic-memory (project=legado) ← 经验索引：陷阱/模式/经验摘要+指针
L4: Legado源码               ← 绝对真相：不可变
```

**权威源规则**：Skill文档 > references/ > basic-memory。两处不一致时以Skill文档为准。

## 快速开始

### 你是AI助手，用户要求你创建/优化/修复书源或订阅源时：

1. **先读 SKILL.md** → 获取决策框架、陷阱速查、L3操作规范
2. **搜索 basic-memory** → 查找同类网站经验（见下方"L3操作指南"）
3. **按任务类型选择参考文档**：
   - 书源创建 -> references/rule-syntax.md + references/special-scenarios/_index.md
   - 订阅源创建 -> references/examples.md 中订阅源部分 + references/special-scenarios/rss-basic.md
   - JS规则编写 -> references/js-patterns/_index.md（先读索引，按需查子文档）
   - 遇到问题 -> references/troubleshooting/_index.md（先读索引，按关键词定位子文档）
4. **使用脚本验证**：
   - 端到端调试(首选): `python scripts/debug-source.py --source PATH --key KEY --stage all`
   - 快速检查: `python scripts/quick-verify.py`
   - 解密验证: `python scripts/verify-decrypt.py --algo AES --key K --iv V --data D [--jvm]`
   - 选择器验证: `python scripts/verify-selector.py --url URL --selector CSS [--jvm]`
   - 图片验证: `python scripts/verify-image.py --url URL --key K --iv V [--jvm]`
   - 网站分析: `python scripts/analyze-site.py --url URL [--jvm]`
   - 源完整性: `python scripts/verify-source.py --source-json PATH [--jvm]`
   - 问题分类: `python scripts/debug-source.py`

### JVM 测试基础设施

> 纯Python模拟覆盖率仅35-40%，JVM仿真器提升到85-90%。环境要求：JDK 17+。

| JAR 文件 | 覆盖率 | 能力 |
|----------|--------|------|
| `legado-jvm/build/libs/legado-jvm.jar` | 85-90% | 从 Legado 源码抽取的完整规则引擎（最高覆盖率） |

**Python客户端**：`tools/rule_engine_client.py`（JDK自动检测+JAR多路径回退）
**共享模块**：`tools/jvm_helpers.py`（add_jvm_args/init_jvm_client/assess_confidence）

**RuleEngineClient API**（AI agent 可直接在 Python 中调用）：
- `ping()` — 检查JVM进程是否存活
- `eval_js(code, context="")` — 执行 JS 代码
- `eval_css(html, selector)` — CSS 选择器查询
- `analyze_rule(content, rule, base_url="")` — 完整规则解析（legado-jvm，支持自定义索引+组合逻辑）
- `analyze_elements(content, rule, base_url="")` — 获取元素列表（legado-jvm）
- `decrypt(algo, key, data, iv, key_encoding="utf-8", iv_encoding="utf-8", data_encoding="base64")` — hutool 解密
- `encrypt(algo, key, data, iv, key_encoding="utf-8", iv_encoding="utf-8", data_encoding="utf-8")` — hutool 加密
- `analyze_url(url, key=None, page=None, source_json=None, base_url="")` — URL 解析（AnalyzeUrl 移植版）
- `debug_book_source(source_json, key, on_log=None, on_error=None, on_result=None)` — 书源端到端调试（流式，search→detail→toc→content）
- `debug_rss_source(source_json, key, on_log=None, on_error=None, on_result=None)` — 订阅源端到端调试（流式，sort→content）
- `shutdown()` — 关闭JVM进程

**降级路径**：JVM可用→RuleEngineServer → JDK不可用→Python仿真 → JS规则标记"未验证"

### L3 操作指南（basic-memory MCP）

**所有操作必须指定 `project="legado"`！**

| 操作 | MCP 工具 | 关键参数 |
|------|---------|---------|
| 搜索经验 | `mcp_basic-memory_search_notes` | `query="{关键词}", search_type="hybrid", project="legado"` |
| 读取笔记 | `mcp_basic-memory_read_note` | `identifier="{标题}", project="legado"` |
| 写入笔记 | `mcp_basic-memory_write_note` | `title, content, directory, project="legado", note_type, tags` |
| 编辑笔记 | `mcp_basic-memory_edit_note` | `identifier, operation, content, project="legado"` |
| 列出目录 | `mcp_basic-memory_list_directory` | `dir_name, project="legado"` |

**L3 目录结构**：traps/ | patterns/ | experiences/ | verifications/ | execution-logs/ | test-reports/ | cases/

**搜索策略**：最小必执行1次 search_notes → 推荐增强(tags过滤) → 降级(Grep references/)

### 脚本使用指南

| 脚本 | 用途 | --jvm | --jar-path |
|------|------|-------|------------|
| debug-source.py | **端到端真机级调试（首选）**：书源/订阅源完整链路 | ✅ | ✅ |
| quick-verify.py | 浅层可用性验证(网站存活+HTTP) | ❌ | ❌ |
| verify-decrypt.py | 解密验证(AES/DES/CBC/ECB) | ✅ | ✅ |
| verify-selector.py | 选择器验证(jsoup CSS) | ✅ | ✅ |
| verify-image.py | 图片加密解密验证 | ✅ | ✅ |
| analyze-site.py | 网站结构分析(JS引擎检测/加密特征) | ✅ | ✅ |
| verify-source.py | 源完整性验证(ES6检测/字段校验) | ✅ | ✅ |
| generate-js-doc.py | 提取JS模式生成文档 | ❌ | ❌ |
| deep-analyze-js.py | 深度JS分析(变量传递链/加密模式) | ❌ | ❌ |
| check_health.py | 三合一健康检查（死链+版本锁+文件债务） | ❌ | ❌ |

### 辅助工具（阶段七/八：减少用户手工操作 + 查漏补缺）

> 可选辅助模块，提升"检测到→尝试辅助→辅助失败再标记"的积极模式。未安装不影响 debug-source.py 基础功能。

| 工具 | 用途 |
|------|------|
| `tools/obstacle_resolver.py` | 障碍统一解析器（登录/CF/验证码表单分析+Cookie导入+持久化） |
| `tools/crypto_analyzer.py` | 加密自动分析（JS扫描+密钥提取+模式判断+解密代码生成） |
| `tools/auto_fixer.py` | 错误自动修复（CSS/URL/字段/语法修复+历史学习+循环验证） |
| `tools/interactive_guide.py` | 用户交互引导（登录/CF/验证码引导+规则确认+进度反馈） |
| `tools/cookie_manager.py` | Cookie/Session管理（文件持久化+跨网站复用+过期管理+导入导出） |
| `tools/smart_http_client.py` | 智能HTTP客户端（自适应重试+代理池+频率自适应+UA池+Referer） |
| `tools/knowledge_matcher.py` | 知识库匹配（网站特征提取+相似度计算+案例匹配+自动更新） |
| `tools/degradation_chain.py` | 统一降级链（自动求解→Cookie导入→手动引导→标记unverifiable） |
| `tools/workflow_timer.py` | 工作流耗时统计（5阶段耗时+瓶颈分析+优化建议） |
| `tools/error_translator.py` | 错误信息翻译（技术错误→用户友好描述+修复建议+分级） |
| `tools/user_action_minimizer.py` | 用户操作最小化（自动化尝试→手动降级） |

### 工作流程（5阶段闭环 + L3经验引擎）

```
Phase 1: 经验优先 ──────────────────────────────────────────
  过陷阱速查表 → search_notes(project="legado") → 查references/
  ↓ 找到经验→直接复用；未找到→记录"skill未覆盖"
Phase 2: 构建规则 ──────────────────────────────────────────
  curl获取HTML → 判断类型 → 构建规则 → 处理特殊场景
Phase 3: 测试驱动 ──────────────────────────────────────────
  陷阱扫描 → debug-source.py → 可信度分层 → 输出JSON
  ↓ 失败 → Phase 4；成功 → Phase 5
Phase 4: 源码深挖 ──────────────────────────────────────────
  读Legado源码定位根因 → 写入source-analysis/ → 回Phase 3
Phase 5: 经验反哺+代码进化 ────────────────────────────────
  先更新references/(权威源) → 再write_note(project="legado", sync_status="synced")
  如有JVM/Python功能缺失 → 更新Kotlin源码→重建JAR→更新Python客户端
```

**Phase完成标志**（必须输出）：
- `[PHASE1_COMPLETE] basic-memory搜索:命中/未命中/降级, 陷阱检查:已检查/未检查`
- `[PHASE3_COMPLETE] 测试覆盖率:X%, 高可信:N, 中可信:N, 需真机:N`
- `[PHASE5_COMPLETE] 双写:完成/部分完成/失败, Schema验证:通过/未通过`

### 书源 vs 订阅源 区分

| 维度 | 书源(BookSource) | 订阅源(RSSSource) |
|------|------------------|-------------------|
| 文件位置 | output/book/ | output/rss/ |
| 核心字段 | searchUrl/ruleSearch/ruleBookInfo/ruleToc/ruleContent | sourceUrl/ruleArticles/ruleTitle/ruleLink/ruleImage/ruleDescription/rulePubDate/ruleContent |
| 验证重点 | 搜索->详情->目录->正文 全链路 | 文章列表->文章内容 |
| 常见问题 | CSS选择器过时、JS签名、403反爬 | RSS格式变化、articleList规则、图片规则 |
| 参考文档 | rule-syntax.md + special-scenarios/ | examples.md中订阅源章节 + special-scenarios/rss-basic.md |

### 经验反哺规范（双写：Skill文档 + basic-memory）

> ⚠️ 大文件已拆分为子目录，追加新经验时先读对应子目录的 `_index.md` 确认写入目标。

**双写流程**：
1. **先更新 Skill 文档**（权威源，references/ 下的文件）
2. **再写 basic-memory**（索引层），必须包含 `source_doc` + `source_sync_date` + `sync_status`
3. Skill文档更新失败 → **不写basic-memory**（避免索引层比权威源更新）

**写入 basic-memory 示例**：
```
mcp_basic-memory_write_note(
    title="经验: {简短描述}",
    content="## 网站特征\n{描述}\n\n## 解决方案\n{方案}\n\n## 参考文档\n- references/{路径}",
    directory="experiences/",
    project="legado",
    note_type="experience",
    tags=["{技术栈}", "{网站类型}"],
    metadata={"source_doc": "references/{路径}", "source_sync_date": "{YYYY-MM-DD}", "sync_status": "synced"}
)
```

**L2 写入目标**：
- 新问题类型 → troubleshooting/_index.md 定位子文档
- 新JS技巧 → js-patterns/_index.md 定位子文档
- 新修复模式 → troubleshooting/community-fix-experience.md
- 新验证发现 → source-analysis/ 对应子文档
- ⚠️ 创建新子文档前 → 检查 _index.md 的边界规则，优先追加到已有子文档

### 数据文件说明

> ⚠️ 以下为历史产出文件示例，当前仓库可能为空。AI agent 创建新源时应将 JSON 保存到对应目录。

output/book/:
- *.json -- 书源 JSON 文件（`[...]` 数组格式）

output/rss/:
- *.json -- 订阅源 JSON 文件（`[...]` 数组格式）

temp/ (临时文件目录，AI agent 按需创建):
- *.html -- 调试用抓取的HTML页面
- *-fix.json / *-analysis.json -- 分析报告中间产物

## Python 客户端 3.0 新功能

### Web 管理界面

FastAPI + Vue3 全栈管理界面，提供源浏览/调试/设备管理/导入导出等可视化操作。

**启动方式**：
```bash
# 方式一：CLI 命令
legado-client serve --host 127.0.0.1 --port 8080

# 方式二：直接启动
cd scripts && python -m legado_client.cli serve

# 方式三：uvicorn 直接启动
cd scripts && uvicorn legado_client.server.app:app --host 127.0.0.1 --port 8080
```

**API 路由一览**：

| 前缀 | 模块 | 功能 |
|------|------|------|
| `/api/sources` | sources.py | 源 CRUD、批量操作、分组、导出、验证 |
| `/api/stats` | stats.py | 概览统计、测试结果分布、内容类型分布、分组分布 |
| `/api/devices` | device.py | 设备 CRUD、连接测试、推送/拉取源 |
| `/api/collections` | collections.py | 合集列表、远程爬取、下载、增量更新 |
| `/api/import` | import_export.py | URL/文件/GitHub/真机导入 |
| `/legado/{path}` | legado_proxy.py | Legado HTTP+WebSocket 代理 |
| `/api/debug` | debug.py | 对比测试、JAR 优化 |
| `/api/health` | app.py | 健康检查 |

**前端页面**（`legado_client/web/admin/`）：

| 页面 | 文件 | 功能 |
|------|------|------|
| 源列表 | SourceListPage.vue | 分页/筛选/搜索/排序 |
| 源详情 | SourceDetailPage.vue | JSON 编辑/调试/导出 |
| 调试 | DebugPage.vue | 真机 vs JAR 对比测试 |
| 设备 | DevicePage.vue | 设备管理/连接测试 |
| 导入 | ImportPage.vue | URL/文件/GitHub/真机导入 |
| 合集 | CollectionPage.vue | 合集浏览/下载 |
| 统计 | StatsPage.vue | 概览/分布图表 |
| Legado 原生 | LegadoNativePage.vue | Legado 代理操作 |

### CLI 新命令

```bash
# 数据库管理
legado-client db init                # 建表 + 扫描 output/ 导入
legado-client db migrate             # Alembic 迁移
legado-client db reset               # 删除所有表并重建
legado-client db import-dir --dir PATH  # 导入目录下 JSON
legado-client db stats               # 源数量统计
legado-client db backup --output PATH   # 备份数据库到 JSON
legado-client db restore --input PATH   # 从 JSON 恢复

# 导出源
legado-client export --type book --output book_sources.json
legado-client export --type rss --output rss_sources.json --ids 1,2,3

# 启动 Web 服务
legado-client serve --host 127.0.0.1 --port 8080

# 调试增强
legado-client debug --source test.json --skip-db-lookup  # 跳过数据库查询
legado-client debug --source test.json --db-only          # 仅查数据库不测试
```

---

## 目录结构

```
legado-source-creator/
  SKILL.md              -- 主文档：决策入口+陷阱速查+5阶段工作流+L3操作规范+JVM测试基础设施+代码进化
  AI_README.md          -- AI使用指南（本文件）
  scripts/              -- 验证/分析脚本
    debug-source.py     -- 端到端真机级调试（首选，书源/订阅源完整链路）
    quick-verify.py     -- 浅层可用性验证
    verify-source.py     -- 深度链路验证（规则引擎模拟解析）
    verify-decrypt.py   -- 解密验证（--jvm支持）
    verify-selector.py  -- 选择器验证（--jvm支持）
    verify-image.py     -- 图片验证（--jvm支持）
    analyze-site.py     -- 网站结构分析（--jvm支持）
    verify-source.py    -- 源完整性验证（--jvm支持）
    generate-js-doc.py  -- JS模式文档生成
    deep-analyze-js.py  -- 深度JS/HTML分析
  tools/                -- JVM仿真器+工具
    legado-jvm/build/libs/legado-jvm.jar -- legado-jvm: 从 Legado 源码抽取的完整规则引擎（最高覆盖率）
    rule_engine_client.py -- Python客户端（JDK检测+JAR多路径回退）
    jvm_helpers.py      -- 共享工具（add_jvm_args/init_jvm_client/assess_confidence）
    rhino-1.8.1.jar     -- Rhino 1.8.1 独立命令行（Legado使用的版本，快速测试JS片段）
    references/source-analysis/ajax-diff-analysis.md -- JsExtensionsStub ajax()差异分析
    html_fetcher.py      -- HTML获取回退链工具
    fetch_html.py        -- Playwright HTML获取（html_fetcher回退依赖）
    # 阶段七/八辅助工具（11个：obstacle_resolver/crypto_analyzer/auto_fixer/interactive_guide/cookie_manager/smart_http_client/knowledge_matcher/degradation_chain/workflow_timer/error_translator/user_action_minimizer，详见上方"辅助工具"表）
  legado-jvm/         -- Gradle构建项目（源码）
  templates/            -- 视频播放器模板
    auto-video-player.html  -- 自动视频播放器（V1.20260606.1）
    hls-video-player.html   -- HLS手动播放器（V2.20260606.1）
    inject-video-player.js  -- 注入式播放器
  references/           -- 参考文档（详见 _INDEX.md）
    _INDEX.md           -- 参考文档顶层索引
    rule-syntax.md      -- 规则语法核心
    url-template.md     -- URL模板语法
    booksource-schema.md -- BookSource实体字段定义
    examples.md         -- 示例源分析
    troubleshooting/    -- 常见陷阱与故障排除（6子文档）
    js-extensions/      -- JS扩展函数参考（11子文档）
    js-patterns/        -- JS模式参考手册（11子文档）
    special-scenarios/  -- 特殊场景处理（16子文档，含websocket-debug.md）
    source-analysis/    -- 源码分析验证结果（8子文档）
  output/               -- 输出数据（首次使用时可能为空，AI agent 应自动创建子目录）
  book/               -- 书源数据
  rss/                -- 订阅源数据
```

---

## 批量操作与死源清理

### 脚本工具

| 脚本 | 用途 | 命令示例 |
|------|------|---------|
| `deep_analysis.py` | 大规模闭环测试（分层采样+JAR/真机+差异分析） | `python deep_analysis.py --mode jar --sample-size 200` |
| `batch_clean_dead_sources.py` | 一键清理死源（DNS检查+真机删除+DB标记） | `python batch_clean_dead_sources.py --delete --mark-db` |
| `debug-source.py` | 端到端真机级调试（首选） | `python debug-source.py` |

### 前端一键清理

- 页面：`/admin/batch-validate` → "一键清理死源"面板
- 后端 API：`POST /api/devices/{id}/clean-dead`
- 流程：选择设备→选择源类型→点击一键清理→确认弹窗→执行

### 真机 WebSocket 调试 API

| 路径 | 功能 | 请求 |
|------|------|------|
| `/bookSourceDebug` | 书源调试 | `{"tag": "源URL", "key": "搜索关键字"}` |
| `/rssSourceDebug` | RSS源调试 | `{"tag": "源URL", "key": "首页"}` |
| `/searchBook` | 全源搜索（慢） | `{"key": "搜索关键字"}` |

> 端口：HTTP 1122 + WebSocket 1123 (HTTP+1)。日志格式为纯文本 `[MM:SS.mmm] msg`，非JSON。

---

## 能力边界

> 完整能力边界声明见 SKILL.md "能力边界（Capability Boundaries）"章节。

### 能做
- 创建/修复/优化书源和订阅源（5种解析+登录+验证码+加密+视频）
- JAR仿真测试 + 真机WebSocket调试 + 真机HTTP管理
- 批量校验 + 一键清理死源
- 前端管理界面 + Python CLI

### 不能做
- WebView渲染 → 标记 `needsWebView=true`，真机测试
- CF JS Challenge → `webView()` 或 DrissionPage
- 登录UI交互 → 标记 `needsUserIntervention=true`
- 字体反爬/动态JS加载 → 影响小，用户手动处理
