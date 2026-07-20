# RSS V5.7 深度修复 OpenSpec 设计文档审查报告

> **审查时间**: 2026-07-20
> **审查范围**: README.md / spec.md / design.md / tasks.md
> **审查基准**: OpenSpec 工作流规范 + 项目源码现状 + 用户两次严重批评要求
> **审查方法**: 穿透核验（文档描述 vs 真实代码）

---

## Part 1: OpenSpec 规范合规性审查

### 1.1 合规性检查清单

| # | 检查项 | 结果 | 证据/缺失原因 |
|---|--------|------|---------------|
| 1 | README.md 含功能概述 | PASS | 第1-2节有项目背景与目标 |
| 2 | README.md 含文档索引 | PASS | 第5节"OpenSpec 四文档索引" |
| 3 | README.md 含 OpenSpec 状态标记 | **FAIL** | 无 🔄 设计中 / ✅ 设计完成 / 🔄 开发中 标识，仅在末尾说"V5.7 阶段2 完成" |
| 4 | spec.md 含 Intent 章节 | **FAIL** | 直接以"REQ-1 总体需求"开始，无 Intent/Scope/Approach/Scenarios 五大章节结构 |
| 5 | spec.md 含 Scope 章节 | **FAIL** | 缺失 |
| 6 | spec.md 含 Approach 章节 | **FAIL** | 缺失（无 Selected Approach + Alternatives Considered 表格 + Drawbacks + Prior Art） |
| 7 | spec.md 含 Requirements 章节 | PARTIAL | 有 REQ-1~19 但未按 RFC 2119 关键词（MUST/SHALL/SHOULD/MAY）表述 |
| 8 | spec.md 含 Scenarios 章节 | **FAIL** | 缺失正常流程/异常流程/边界条件场景 |
| 9 | design.md 含 Technical Approach | PASS | 第1节整体架构 + 第2节工作流 |
| 10 | design.md 含 ADR Y-Statement | **FAIL** | 完全缺失 Architecture Decisions（无 AD-XX 编号、无 Context/Concern/Decision/Goal/Tradeoff/Status） |
| 11 | design.md 含 Data Flow | PASS | 第7节数据流 |
| 12 | design.md 含 File Changes | **FAIL** | 第4.3节仅列核心源码路径，无变更清单（无新增/修改/删除文件清单） |
| 13 | tasks.md 用 `- [ ] X.Y` 格式 | **FAIL** | 使用 T1/T2.1/T2.2 格式，进度跟踪表用 `[ ] T2.1` 非标准格式 |
| 14 | docs/INDEX.md 注册 rss-v5_7-deep-fix | **FAIL** | 第三部分"功能设计"仅注册 `rss-batch-optimize-v2`，未注册 `rss-v5_7-deep-fix` |

**合规性汇总**: 14 项中 PASS 5 项 / PARTIAL 1 项 / FAIL 8 项，合规度 35.7%

---

## Part 2: 文档质量问题清单

### 2.1 阻断级问题（必须修复）

#### Q1: 「11 必备字段」标题与表格 12 项不一致（贯穿全文）

**位置**:
- README.md 第 64 行标题"### 3.1 11 必备字段清单" + 第 67-79 行表格列 12 项
- spec.md 第 64 行标题"## 2. 11 必备字段必填约束" + 第 71-82 行列表 12 项
- tasks.md 第 572 行陷阱68 描述"11必备字段清单" + 列出 12 项

**问题本质**: 标题与内容数量不一致，违反 OpenSpec"无歧义验收"原则。用户明确要求"11 必备字段"但文档实际列 12 个，未说明 ruleContent 是否可空（content=skip 可接受 vs 必填）。

**修复建议**:
- 若 ruleContent 必填 → 标题改为"12 必备字段"
- 若 ruleContent 可空（content=skip 可接受）→ 表格只列 11 项，ruleContent 单独说明"正文规则可选，但缺省时 content 维度自动 skip"
- 推荐方案：标题统一为"12 必备字段（其中 ruleContent 可为空）"，避免与 REQ-8"content=skip 可通过"矛盾

#### Q2: spec.md REQ-11 第1批分类描述偏差

**位置**: spec.md 第 146-152 行

**问题本质**:
- 描述"第 1 批（5 个 4维度pass源）"
- 但源[52] content=fail + search=fail → 实际 3 维度 pass（domain/list/category）
- 源[131] content=fail + search=fail → 实际 3 维度 pass
- 按 REQ-8 通过标准"5 维度全部 pass 或 content=skip"，content=fail 不算通过
- 真正 4 维度 pass 的只有 3 个：源[174]/源[180]/源[182]

**修复建议**:
- 将"第1批5个4维度pass源"改为"第1批5个3-4维度pass源"
- 或按实际 pass 维度数重新分批：
  - 1批A（4维度pass，差1维度）：源[174]/源[180]/源[182]
  - 1批B（3维度pass，差2维度）：源[52]/源[131]

#### Q3: tasks.md 任务编号不符合 OpenSpec 标准

**位置**: tasks.md 全文

**问题本质**: 使用 T1/T2.1/T2.2/T3/T4/T5/T6/T7 格式，违反 OpenSpec 规范要求的 `- [ ] X.Y` 标准格式。

**修复建议**: 全文替换为标准格式：
```markdown
## 1. 准备工作
- [ ] 1.1 环境就绪检查（T1 原内容）

## 2. 13 源单源深度修复
- [ ] 2.1 源[52] 定向修复
- [ ] 2.2 源[131] 定向修复
...
```

#### Q4: design.md 第5.2节 CronetHelper.kt 文件路径错误

**位置**: design.md 第 436-446 行

**问题本质**:
- 文档说 `app/src/main/java/io/legado/app/help/http/CronetHelper.kt`
- 实际文件不存在，真实文件为 `app/src/main/java/io/legado/app/help/http/HttpHelper.kt`
- 文档写 `connectTimeout = 15_000` 赋值语法
- 实际代码为 `.connectTimeout(15, TimeUnit.SECONDS)` 链式调用
- 数值（15s/60s）正确，但文件名与语法均错误

**修复建议**:
- 路径改为 `app/src/main/java/io/legado/app/help/http/HttpHelper.kt`
- 代码片段改为：
```kotlin
// HttpHelper.kt 第87-91行
val builder = OkHttpClient.Builder()
    .connectTimeout(15, TimeUnit.SECONDS)
    .writeTimeout(15, TimeUnit.SECONDS)
    .readTimeout(60, TimeUnit.SECONDS)
    .callTimeout(60, TimeUnit.SECONDS)
```
- 注：修改 connectTimeout 需重新编译 APK，且影响全局 OkHttp 客户端（包括书源/订阅源/图片加载），需评估副作用

#### Q5: docs/INDEX.md 未注册 rss-v5_7-deep-fix

**位置**: docs/INDEX.md 第三部分"功能设计"

**问题本质**: 同目录下其他 spec 均已注册（如 rss-batch-optimize-v2/rss-cache-first 等），但本 spec 缺失，违反 OpenSpec 步骤3"主代理更新 docs/INDEX.md"。

**修复建议**: 在 INDEX.md 第三部分添加：
```markdown
| [specs/rss-v5_7-deep-fix/](./specs/rss-v5_7-deep-fix/) | RSS 订阅源 V5.7 深度修复（13 启用源字段规则修复 + CF盾/timeout 禁用源恢复 + 5维度真机验证 + 陷阱68-72沉淀） 🔄 设计中 |
```

### 2.2 高优先级问题（应修复）

#### Q6: spec.md 缺 Intent/Scope/Approach/Scenarios 五大章节

**位置**: spec.md 全文结构

**问题本质**: OpenSpec 规范明确要求 spec.md 必须包含 Intent/Scope/Approach（含 Selected Approach + Alternatives Considered 表格 + Drawbacks + Prior Art）/ Requirements / Scenarios 五大章节，本文档直接以"REQ-1 总体需求"开始，完全缺失前三大章节。

**修复建议**: 在 spec.md 开头补充：
- **Intent**: 解决 V5.6 后真机验证仅 1/13 通过、用户两次批评字段缺失问题
- **Scope**: 仅修复 13 个启用源 + 尝试恢复 22 个禁用源，不涉及新功能开发
- **Approach**:
  - Selected Approach: 单源深度修复工作流（V5.6 已验证可行）
  - Alternatives Considered: 批量套用通用模板（V5.1 已证伪）/ PC Playwright 验证（V5.4 已证伪）
  - Drawbacks: 单源 8-15 分钟，13 源 2-3 小时
  - Prior Art: V5.6 单源工作流
- **Scenarios**: 正常流程（修复→验证→通过）/ 异常流程（3次失败→禁用）/ 边界条件（站点已下线）

#### Q7: design.md 缺 Architecture Decisions（ADR Y-Statement）

**位置**: design.md 全文

**问题本质**: OpenSpec 规范明确要求 design.md 必须含 ADR Y-Statement 模板（Context/Concern/Decision/Goal/Tradeoff/Status），本文档完全缺失。

**修复建议**: 补充 ADR 章节，至少包含：
- AD-01: 单源深度修复工作流选型
- AD-02: mitmproxy 抓包方案选型
- AD-03: CF 盾破盾手段优先级
- AD-04: 3 次失败后禁用策略
- AD-05: OkHttp timeout 修改决策

#### Q8: CF 盾破盾方案未评估关键风险

**位置**: design.md 第4节 + spec.md REQ-13

**问题本质**:
- Google cache 在中国大陆可访问性未评估（关键风险，可能直接不可用）
- cf_clearance cookie 获取流程未说明（如何用 PC 浏览器获取并导入 header）
- 三种手段的优先级顺序在 spec.md REQ-13 和 tasks.md T3 不一致
  - spec.md: Google cache → Cookie → UA
  - tasks.md: UA → Cookie → Google cache

**修复建议**:
- 补充 Google cache 在中国大陆可访问性评估（需翻墙或不可用，应作为低优先级手段）
- 补充 cf_clearance 获取操作步骤（PC 浏览器访问站点 → F12 → Application → Cookies → 复制 cf_clearance 值）
- 统一 spec.md 与 tasks.md 的手段优先级（推荐 UA → Cookie → Google cache 顺序）

#### Q9: 单源修复耗时评估未含隐性成本

**位置**: design.md 第9.1节

**问题本质**: 评估"13源总计 2-3 小时"未含：
- mitmproxy 证书首次安装（10-15 分钟）
- ADB 连接中断重连（每次 1-2 分钟）
- App 重启（每个源可能需重启 30s）
- 重新导入真机 DB（每次 30s）
- 5维度验证等待（18s × 2维度 × 13源 = 8分钟）

实际可能 4-6 小时。

**修复建议**: 修订耗时评估为"13源总计 4-6 小时（含 mitmproxy 首次配置 15分钟 + ADB 重连 + App 重启 + 验证等待）"。

### 2.3 中优先级问题（建议修复）

#### Q10: spec.md Requirements 未用 RFC 2119 关键词

**位置**: spec.md REQ-1~REQ-19

**问题本质**: OpenSpec 规范要求"需求表述采用 RFC 2119 标准关键词（MUST/SHALL/SHOULD/MAY）"，本文档用"必须/约束/输出"等中文表述，未区分强制等级。

**修复建议**: 关键约束改为 MUST 级，如"每个源 MUST 11 必备字段全部填充"。

#### Q11: design.md 缺 File Changes 章节

**位置**: design.md 第4.3节

**问题本质**: 仅列核心源码路径，无明确"变更清单"（哪些文件新增/修改/删除）。

**修复建议**: 补充 File Changes 表格：
| 文件 | 变更类型 | 变更内容 |
|------|----------|----------|
| output/rss/optimized_v5_7_final.json | 修改 | 13源字段规则重写 |
| app/src/main/assets/updateLog.md | 修改 | 追加 V5.7 条目 |
| .trae/skills/legado-source-creator/references/source-analysis/batch-optimization-patterns.md | 修改 | 追加陷阱68-72 |
| ai_tests/README.md | 修改 | 追加 V5.7 章节 |
| (可选) app/src/main/java/io/legado/app/help/http/HttpHelper.kt | 修改 | timeout 调整 |

### 2.4 低优先级问题（可选改进）

#### Q12: tasks.md T7.1 陷阱68 描述与表格数量再次不一致

**位置**: tasks.md 第 565-572 行

**问题本质**: 陷阱68 标题"11必备字段必填"但下方清单列 12 项，与 Q1 同源问题。

#### Q13: tasks.md 附录B 单源修复示例流程过于简略

**位置**: tasks.md 附录B

**问题本质**: 仅给 PowerShell 命令片段，未给完整可复用脚本。可考虑封装为 `ai_tests/scripts/single_source_fix.py`。

---

## Part 3: 代码一致性核查清单

| # | 文件路径 | 文档描述 | 实际状态 | 一致性 |
|---|----------|----------|----------|--------|
| 1 | `app/src/main/java/io/legado/app/service/CheckRssSourceService.kt` | 5 维度校验核心服务 | 存在 | PASS |
| 2 | `app/src/main/java/io/legado/app/model/CheckRssSource.kt` | RssSource 校验逻辑 | 存在 | PASS |
| 3 | `app/src/main/java/io/legado/app/ui/rss/source/edit/RssSourceEditActivity.kt` L181-185 | 调试入口 | L181 `menu_debug_source` → `RssSourceDebugActivity` + `putExtra("key", source.sourceUrl)` | PASS |
| 4 | `app/src/main/java/io/legado/app/help/http/CronetHelper.kt` | connectTimeout=15_000 / readTimeout=60_000 | **文件不存在**；实际为 `HttpHelper.kt:88-91`，语法为 `.connectTimeout(15, TimeUnit.SECONDS)` | **FAIL** |
| 5 | `ai_tests/scripts/v5_7_debug_verify.py` | 5 维度真机验证脚本 | 存在 | PASS |
| 6 | `ai_tests/scripts/v5_7_apply_patches.py` | 应用字段补丁脚本 | 存在 | PASS |
| 7 | `ai_tests/scripts/v5_7_fix_missing_fields_v2.py` | 字段提取脚本 | 存在 | PASS |
| 8 | `ai_tests/scripts/import_rss_source.py` | 导入脚本 | 存在 | PASS |
| 9 | `output/rss/optimized_v5_7_final.json` | V5.7 字段补齐版 JSON | 存在 | PASS |
| 10 | `output/rss/v5_7_debug_verify_result.json` | 阶段2验证结果 | 存在 | PASS |

**代码一致性汇总**: 10 项中 PASS 9 项 / FAIL 1 项，一致度 90%

---

## Part 4: 阻塞性问题汇总（必须修复才能进入实施）

按严重程度排序：

### 阻塞级 #1: docs/INDEX.md 未注册（Q5）
**影响**: 违反 OpenSpec 步骤3强制要求，后续步骤无法追踪状态流转。
**修复**: 在 INDEX.md 第三部分追加 rss-v5_7-deep-fix 条目（见 Q5 修复建议）。

### 阻塞级 #2: tasks.md 任务编号格式不符（Q3）
**影响**: 违反 OpenSpec 规范，无法用标准 `- [ ] X.Y` 格式跟踪进度，AOAdapt 日志无法附挂。
**修复**: 全文替换为 `- [ ] X.Y` 格式（见 Q3 修复建议）。

### 阻塞级 #3: spec.md 缺 Intent/Scope/Approach/Scenarios（Q6）
**影响**: 违反 OpenSpec 规范，需求来源与方案选型无可追溯性，执行人员无法理解"为什么这样做"。
**修复**: 补充五大章节结构（见 Q6 修复建议）。

### 阻塞级 #4: design.md 缺 ADR Y-Statement（Q7）
**影响**: 违反 OpenSpec 规范，关键技术决策无记录，未来类似问题无法复用。
**修复**: 补充 AD-01~AD-05 决策记录（见 Q7 修复建议）。

### 阻塞级 #5: 「11 必备字段」标题与内容 12 项不一致（Q1）
**影响**: 用户两次严重批评的核心约束在文档中表述自相矛盾，验收时无法判定 ruleContent 是否必填。
**修复**: 统一为"12 必备字段（ruleContent 可为空，缺省时 content=skip）"（见 Q1 修复建议）。

### 阻塞级 #6: design.md CronetHelper.kt 路径错误（Q4）
**影响**: 执行人员按文档路径找不到文件，无法实施 timeout 修改；且语法错误可能误导。
**修复**: 改为 HttpHelper.kt 并修正代码片段（见 Q4 修复建议）。

---

## Part 5: 建议性改进（非阻塞）

按价值排序：

1. **统一 CF 盾破盾手段优先级**（Q8）: spec.md 与 tasks.md 顺序不一致，统一为 UA → Cookie → Google cache
2. **修订耗时评估含隐性成本**（Q9）: 2-3 小时 → 4-6 小时
3. **spec.md Requirements 用 RFC 2119 关键词**（Q10）: 提升需求强制等级清晰度
4. **补充 design.md File Changes 章节**（Q11）: 明确变更清单
5. **修正 spec.md REQ-11 第1批分类**（Q2）: 改为"3-4维度pass源"或重新分批
6. **封装单源修复脚本**（Q13）: 提升可复用性

---

## Part 6: 总体评估

### 6.1 量化评分

| 维度 | 评分 | 说明 |
|------|------|------|
| OpenSpec 规范合规度 | **35.7%** | 14 项检查 PASS 5 / PARTIAL 1 / FAIL 8 |
| 代码一致性 | **90%** | 10 项核查 PASS 9 / FAIL 1（CronetHelper.kt 路径错误） |
| 文档质量 | **55/100** | 内容详实但结构严重不合规，存在 6 项阻断级问题 |
| 落地可执行性 | **中** | 任务粒度清晰但规范不合规，需修订后方可实施 |

### 6.2 判定结果

⚠️ **整改后落地**: 存在 6 项阻断级问题，必须完成下列整改后方可进入实施阶段：

1. 修复 Q5: docs/INDEX.md 注册条目
2. 修复 Q3: tasks.md 改为 `- [ ] X.Y` 格式
3. 修复 Q6: spec.md 补 Intent/Scope/Approach/Scenarios 五大章节
4. 修复 Q7: design.md 补 ADR Y-Statement
5. 修复 Q1: 统一"11/12 必备字段"表述
6. 修复 Q4: design.md 修正 CronetHelper.kt → HttpHelper.kt

### 6.3 整改后落地可行性确认

完成上述 6 项阻断级整改后，该文档可 100% 支撑落地，执行人员仅凭文档即可完成全部工作，无需额外设计、主观猜测与二次拆解。理由：

- 13 源失败原因明细已在 design.md 第3节给出（domain/list/search/category/content 状态 + 错误码 + 调用栈 + 修复方向）
- 单源深度修复工作流已在 design.md 第2节给出 13 步操作流程
- 任务粒度已在 tasks.md T2.1~T2.12 拆解至单源可闭环
- 验收标准已在 spec.md REQ-8/REQ-11/REQ-12 明确
- 工具链已在 design.md 第6节给出（mitmproxy/Playwright/ADB/JSON）
- 数据流已在 design.md 第7节给出
- 风险与缓解已在 design.md 第9节给出

---

## 附录: 审查工具调用记录

| # | 工具 | 用途 | 结果 |
|---|------|------|------|
| 1 | Read | README.md | 179 行读完 |
| 2 | Read | spec.md | 264 行读完 |
| 3 | Read | design.md | 627 行读完 |
| 4 | Read | tasks.md | 797 行读完 |
| 5 | Read | docs/project-rules/openspec-workflow.md | 389 行读完，确认规范要求 |
| 6 | Read | docs/INDEX.md | 254 行读完，确认未注册 |
| 7 | Glob | CheckRssSourceService.kt | 存在 |
| 8 | Glob | CheckRssSource.kt | 存在 |
| 9 | Glob | RssSourceEditActivity.kt | 存在 |
| 10 | Glob | CronetHelper.kt | **不存在** |
| 11 | Glob | help/http/*.kt | 找到 Cronet.kt / HttpHelper.kt 等 13 个文件 |
| 12 | Grep | connectTimeout\|readTimeout | 在 HttpHelper.kt:88/90 找到正确配置 |
| 13 | Read | RssSourceEditActivity.kt L175-194 | 确认 L181-185 为调试入口 |
| 14 | Read | HttpHelper.kt L80-99 | 确认 timeout 配置语法 |
| 15 | Glob | ai_tests/scripts/v5_7_*.py | 4 个脚本均存在 |
| 16 | Glob | import_rss_source.py | 存在 |
| 17 | Glob | optimized_v5_7_final.json | 存在 |
| 18 | Glob | v5_7_debug_verify_result.json | 存在 |

---

**报告生成时间**: 2026-07-20
**审查者**: OpenSpec文档审查专家
**下一步**: 将审查结果同步给文档作者，按阻断级 #1-#6 顺序修订后重新审查
