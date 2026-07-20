# RSS订阅源 V5.7 深度修复 - 功能需求规格

> **spec.md** — 定义 V5.7 深度修复必须达成的功能需求与验收标准

---

## 0. 文档元信息

- **状态**: ✅ 设计完成（2026-07-20 审核修订后）
- **审核记录**: [audit_report.md](./audit_report.md) — 6 项阻断级问题已修订
- **RFC 2119 关键词**: 本文档使用 MUST / SHALL / SHOULD / MAY 表达需求强制等级

---

## 1. Intent（意图）

V5.6 交付后真机验证仅 1/13 启用源通过（通过率 7.7%），用户于 2026-07-20 两次严重批评：

1. "184个订阅源，为什么那么多被禁用的？"
2. "每一个订阅源的名称、源URL、图标、搜索地址、分类URL、列表规则、列表下一页规则、标题规则、时间规则、图片URL规则、链接规则、WEB_VIEW 中的内容规则，这些都是必不可少的，为什么你搞的很多订阅源，丢三落四！你确定你认认真真的优化测试了么？"

**核心意图**:
- 修复 13 个启用源的字段规则，使其 5 维度真机验证全部通过
- 尝试恢复 22 个禁用源（15 CF 盾源 + 7 timeout 源）
- 沉淀 V5.7 阶段发现的新经验到 skill 文档（陷阱 68-72）
- 验证"字段填充 100% ≠ 真机可用 100%"的关键认知

## 2. Scope（范围）

### 2.1 In Scope（本次必须做）

| 项 | 说明 |
|----|------|
| 13 个启用源深度修复 | 源[52, 81, 83, 131, 134, 174, 176, 177, 178, 180, 181, 182, 183] |
| 15 个 CF 盾禁用源恢复 | 尝试 Googlebot UA / cf_clearance Cookie / Google cache 三种手段 |
| 7 个 timeout 禁用源恢复 | 直接重试 + 站点状态检查 |
| 全量 184 源 5 维度真机验证 | 生成最终验证报告 |
| 陷阱 68-72 沉淀 | 写入 skill batch-optimization-patterns.md |
| 文档同步 | updateLog.md / ai_tests/README.md / 最终成果报告 |

### 2.2 Out of Scope（本次不做）

| 项 | 说明 |
|----|------|
| 新增订阅源 | 仅修复现有 184 源，不新增 |
| 重写 CheckRssSourceService.kt | 5 维度校验逻辑保持现状 |
| 修改 RssSource 数据模型 | 不变更实体字段定义 |
| 优化 Cronet 库下载机制 | T5 仅作为可选任务检查库状态 |
| 开发 AI 自动源生成器 | 长期建议，不在本次范围 |

## 3. Approach（方案）

### 3.1 Selected Approach（选定方案）

**单源深度修复工作流**（V5.6 已验证可行）：

```
1. 选定 1 源 → 模拟器 App 内置调试看错误
2. mitmproxy 抓包真机 App Cronet 实际请求
3. 分析真实 HTML 结构（不是 PC Playwright 的 HTML）
4. 重写规则（12 必备字段全部填充，ruleContent 可为空）
5. 5 维度真机调试验证（domain/list/search/category/content）
6. 失败回到分析（最多 3 次）→ 通过后下一个
```

**选定理由**:
- V5.6 已通过单源修复验证可行性
- mitmproxy 抓包获取真实 HTML，规避 PC Playwright 与真机 Cronet 的 JS 执行差异
- 13 步工作流已细化至可操作级别
- 失败 3 次禁用机制保证整体进度不被单源拖累

### 3.2 Alternatives Considered（否决的替代方案）

| # | 替代方案 | 否决理由 |
|---|----------|----------|
| A1 | 批量套用通用模板补齐字段 | V5.1 已证伪：通用模板无法覆盖站点 DOM 差异，导致 search_result_empty 高发（10/13 失败源） |
| A2 | PC Playwright 验证替代真机验证 | V5.4 已证伪：PC Playwright 默认执行 JS，真机 Cronet 不执行 JS，同一 URL 返回不同 HTML 结构 |
| A3 | 直接 curl 测试站点可达性 | 只能验证 domain 维度，无法验证 list/search/category/content 解析逻辑 |
| A4 | 修改 RssSource 数据模型放宽字段约束 | 治标不治本，用户明确要求 12 必备字段全部填充 |
| A5 | 开发 AI 自动源生成器自动重写规则 | 长期方案，开发周期长，无法解决 V5.7 紧急修复需求 |
| A6 | 放弃不可达源（直接禁用） | 违反用户"恢复禁用源"要求，需先尝试恢复手段 |

### 3.3 Drawbacks（选定方案的已知缺点）

| # | 缺点 | 接受理由 |
|---|------|----------|
| D1 | 单源 8-15 分钟，13 源总计 4-6 小时（含隐性成本） | 不可并行化，但可在多窗口间切换执行 |
| D2 | mitmproxy 证书首次安装需 10-15 分钟 | 仅首次成本，后续源复用配置 |
| D3 | 3 次失败后禁用可能导致部分源永久禁用 | 用户接受"无法恢复的源标记禁用"，符合 REQ-12 |
| D4 | CF 盾破盾手段有效率不确定（cf_clearance 30 分钟有效期） | 用户接受"能恢复几个算几个"，无固定数量目标 |
| D5 | 修改 OkHttp timeout 影响全局网络（书源/订阅源/图片加载） | T4 中明确为可选任务，需评估副作用 |
| D6 | 单源修复期间站点 HTML 结构可能变化 | 每次修复后立即真机验证，失败后重新抓包 |

### 3.4 Prior Art（参考的类似工作）

| 来源 | 关键经验 |
|------|----------|
| V5.6 单源深度修复 | 13 步工作流已验证可行，源[1]修复成功 |
| skill 陷阱 1-67 | 已沉淀历史经验（详见 batch-optimization-patterns.md） |
| Legado 原 BookSource 修复流程 | mitmproxy + CSS 选择器重写模式 |
| OpenSpec 工作流规范 | 强制检查点 + AOAdapt 日志 + 三级完成标准 |

## 4. Scenarios（场景）

### 4.1 正常流程

**场景 N1**: 单源修复成功
- 前置: 源[idx] 在 V5.7 阶段2 验证失败（某维度 fail）
- 步骤: 启动调试 → mitmproxy 抓包 → 分析 HTML → 重写规则 → 导入 DB → 5 维度验证
- 后置: 5 维度全部 pass（或 content=skip）→ 标记 ✅ 进入下一源

**场景 N2**: CF 盾源恢复成功
- 前置: 源[idx] 因 CF 盾被禁用
- 步骤: 添加 Googlebot UA header → 启用 → 5 维度验证
- 后置: 验证通过 → 保持启用，记录恢复手段

### 4.2 异常流程

**场景 E1**: 单源 3 次修复仍失败
- 前置: 源[idx] 经 3 次 mitmproxy 抓包+规则重写仍失败
- 步骤: 标记 enabled=false → sourceComment 追加 `[AI_V5_7:final_disabled|reason=<原因>|retry_count=3]`
- 后置: 跳过该源，进入下一源

**场景 E2**: 站点已下线（domain 维度持续 fail）
- 前置: 源[idx] domain 维度 fail，PC curl 测试也不可达
- 步骤: 标记 enabled=false → sourceComment 追加 `reason=site_offline`
- 后置: 跳过该源，不进入 list/search 修复

**场景 E3**: 验证脚本异常（全维度 unknown）
- 前置: 源[idx] 5 维度验证结果全 unknown（如源[176]）
- 步骤: 重新执行验证脚本 → 检查 RssSourceDebugActivity 是否正确启动
- 后置: 若仍异常，标记 enabled=false 并记录 `reason=verify_script_error`

### 4.3 边界条件

**场景 B1**: ruleContent 为空
- 处理: content 维度自动 skip，符合 REQ-8 通过标准，不需强制填充
- 注意: 若用户后续要求"内容必读"，则需补齐 ruleContent

**场景 B2**: 站点返回 status_500
- 处理: 等待 10 分钟后重试，若仍 500 → 标记 enabled=false + `reason=server_error`

**场景 B3**: cf_clearance cookie 过期（30 分钟后）
- 处理: 重新用 PC 浏览器访问站点获取新 cf_clearance → 更新 header → 重新验证

**场景 B4**: 修改 OkHttp timeout 后影响其他模块
- 处理: 修改前评估对书源/图片加载的影响 → 修改后全量回归测试 → 若有副作用则回退

---

## 5. 总体需求

### REQ-1: 12 个启用源深度修复

> **2026-07-20 决策更新**: 原 13 启用源中的源[52] 经分析确认为导航源（提供 `legado://import/rssSource?src=...` JSON 导入链接而非内容源），V5.7 阶段1 错误为其添加了通用默认字段。已标记 `enabled=false` 并从启用源清单移除，剩余 12 启用源继续修复。详见 tasks.md 2.1 决策记录。

**输入**: 12 个 enabled=true 的源（在 V5.7 阶段1 已补齐字段填充率到 100%；原 13 源中源[52] 已移出）

**输出**: 12 个源全部通过 App 内置 5 维度真机调试

**12 个源编号清单**:
```
源[81], 源[83], 源[131], 源[134],
源[174], 源[176], 源[177], 源[178], 源[180],
源[181], 源[182], 源[183]
```

**当前状态**（V5.7 阶段2 验证结果，源[52] 已移出）:
- 完全通过（5维度全pass）: 1 个 → 源[81]
- 4维度pass，仅差1维度: 4 个 → 源[131, 174, 180, 182]
- 多维度失败: 6 个 → 源[83, 134, 177, 178, 181, 183]
- 全unknown（验证异常）: 1 个 → 源[176]

### REQ-2: 尝试恢复 CF 盾禁用源

**输入**: 15 个因 CF 盾拦截被禁用的源

**输出**: 尽可能恢复可用源（无固定数量目标，能恢复几个算几个）

**恢复手段**:
- Google cache 串行方式破盾
- Cookie/Referer 规则模拟浏览器
- User-Agent 切换

### REQ-3: 尝试恢复 timeout 禁用源

**输入**: 7 个因超时被禁用的源

**输出**: 重试并尽可能恢复可用源

**恢复手段**:
- 直接重试（可能是临时网络波动）
- 调整 timeout 配置
- 检查站点是否已下线

### REQ-4: 全量 5 维度真机验证

**输入**: 184 源（修复后的最终 JSON）

**输出**: 全量 5 维度验证报告（含每个源的 domain/list/search/category/content 状态）

### REQ-5: 经验沉淀到 skill

**输入**: V5.7 阶段发现的新问题和新经验

**输出**: 陷阱 68-72 沉淀到 `.trae/skills/legado-source-creator/references/source-analysis/batch-optimization-patterns.md`

---

## 6. 12 必备字段必填约束

### REQ-6: 字段填充率 100%（MUST）

**约束**: 每个源 MUST 12 必备字段全部填充，其中 ruleContent SHOULD 填充但可为空（缺省时 content=skip 可通过）

**字段清单**（与 README 第 3.1 节一致）:
1. sourceName（源名称）— MUST
2. sourceUrl（源URL）— MUST
3. sourceIcon（图标）— MUST
4. searchUrl（搜索地址）— MUST
5. sortUrl（分类URL）— MUST
6. ruleArticles（列表规则）— MUST
7. ruleNextPage（列表下一页规则）— MUST
8. ruleTitle（标题规则）— MUST
9. rulePubDate（时间规则）— MUST
10. ruleImage（图片URL规则）— MUST
11. ruleLink（链接规则）— MUST
12. ruleContent（WEB_VIEW内容规则）— SHOULD（可为空）

**当前状态**（V5.7 阶段1 完成）:
- 全量 184 源字段填充率：100%
- 13 启用源字段填充率：100%
- 总补丁数：34 个（18 提取值 + 16 通用默认值）

**补丁来源标记**（在 sourceComment 中）:
- `[AI_V5_7:field_fixed|<field>=extracted|...]` - Playwright 提取
- `[AI_V5_7:field_fixed|<field>=default_template|...]` - 通用默认值
- `[AI_V5_7:field_fixed|<field>=default_favicon|...]` - 站点/favicon.ico

### REQ-7: 字段值必须有效（MUST）

**约束**: 字段值不能仅是"有内容"，MUST 真正能在 Legado 规则引擎中解析出结果

**验证方式**: 真机 5 维度调试

---

## 7. 5 维度真机验证标准

### REQ-8: 5 维度全部 pass（MUST）

**5 个维度**:
1. **domain** - 域名访问成功（Cronet/OkHttp 请求 sourceUrl 返回 200）
2. **list** - 列表解析成功且 list_size > 0
3. **search** - 搜索功能可用且返回结果非空
4. **category** - 分类功能可用且列表非空
5. **content** - 正文解析成功（或 skip 表示内容规则为空）

**通过标准**: 5 维度 MUST 全部 pass 或 content=skip

### REQ-9: 验证方法唯一性（MUST）

**约束**: 只接受 Legado App 内置调试功能的验证结果，MUST NOT 接受 PC Playwright/curl 验证

**理由**: PC Playwright 默认执行 JS，真机 Cronet 不执行 JS，同一 URL 返回不同 HTML 结构

**App 内置调试入口**:
- Activity: `RssSourceEditActivity` → 右上角调试按钮 → `RssSourceDebugActivity`
- 服务: `CheckRssSourceService.kt`（5 维度校验核心）
- 触发命令: `am start -n io.legado.app.debug/io.legado.app.ui.rss.source.debug.RssSourceDebugActivity --es key "<sourceUrl>"`

### REQ-10: 单源深度修复工作流（MUST）

**约束**: 每个失败源 MUST 按 V5.6 验证可行的工作流修复

**工作流**:
```
1. 选定 1 源 → 模拟器 App 内置调试看错误
2. mitmproxy 抓包真机 App Cronet 实际请求
3. 分析真实 HTML 结构（不是 PC Playwright 获取的 HTML）
4. 重写规则（11 必备字段全部填充）
5. 5 维度真机调试验证（domain/list/search/category/content）
6. 失败回到分析（最多 3 次）→ 通过后下一个
```

---

## 8. 失败源分类与修复策略

### REQ-11: 13 个启用源按通过程度分类处理（MUST）

> **修订说明**: 原描述"5 个 4维度pass源"不准确，实际源[52]/源[131]/源[180] 有 2 个维度失败（content+search），仅 3 维度 pass。已修正分类描述。

**第 1 批（5 个 3-4 维度 pass 源）** - 定向修复 1-2 个失败维度:
- 源[52]: 3 维度 pass（domain/list/category），content=fail + search=fail → 修复 content 规则 + search 规则
- 源[131]: 3 维度 pass（domain/list/category），content=fail + search=fail → 修复 content 规则 + search 规则
- 源[174]: 4 维度 pass（domain/list/category/content），search=fail → 仅修复 search 规则
- 源[180]: 3 维度 pass + content=skip，search=fail → 添加 content 规则 + 修复 search 规则
- 源[182]: 4 维度 pass（domain/list/category/search），content=fail → 仅修复 content 规则

**第 2 批（6 个多维度失败源）** - 单源深度修复:
- 源[83]: domain=fail → 站点不可达，可能需 http→https 或换域名
- 源[134]: list=fail, search=fail, category=fail → list 选择器不匹配
- 源[177]: list=fail, search=fail, category=fail → list 选择器不匹配
- 源[178]: list=fail, category=fail → list 选择器不匹配
- 源[181]: list=fail, search=fail, category=fail, status_500 → 站点服务异常
- 源[183]: list=fail, search=fail, category=fail → list 选择器不匹配

**第 3 批（1 个全unknown源）** - 重新验证:
- 源[176]: 全维度 unknown → 验证脚本异常，需重新执行验证

### REQ-12: 失败 3 次后禁用（MUST）

**约束**: 单源深度修复最多 3 次，仍失败则 MUST 标记 enabled=false 并记录失败原因

**禁用标记**: 在 sourceComment 中追加 `[AI_V5_7:final_disabled|reason=<具体原因>]`

---

## 9. 禁用源恢复策略

### REQ-13: CF 盾源破盾（SHOULD）

**输入**: 15 个因 CF 盾拦截被禁用的源

> **优先级统一说明**: spec.md 与 tasks.md 已统一 CF 盾破盾手段优先级为 UA → Cookie → Google cache（与 tasks.md T3 一致）

**破盾手段（按优先级）**:
1. **User-Agent 切换**（优先级 1，通用 CF 盾站点）: 用 Googlebot UA `Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)`
2. **Cookie 注入**（优先级 2，已知 cf_clearance）: 在 header 中添加 `cf_clearance=<value>` cookie + Referer + UA
3. **Google cache 串行方式**（优先级 3，临时访问，中国大陆可访问性需评估）: 用 `https://webcache.googleusercontent.com/search?q=cache:<原URL>` 作为代理
4. **标记禁用**（优先级 4，都无法绕过）: 保持 enabled=false + sourceComment 追加 `[AI_V5_7:cf_recovery_failed|tried=ua,cookie,cache]`

**验收**: 恢复后 MUST 通过 5 维度真机验证

### REQ-14: timeout 源重试（SHOULD）

**输入**: 7 个因超时被禁用的源

**重试手段**:
1. **直接重试**: 可能是临时网络波动
2. **延长 timeout**: 修改 OkHttp 配置 connect=15s → connect=30s（可选，需评估全局副作用）
3. **检查站点状态**: 确认站点是否已下线

**验收**: 恢复后 MUST 通过 5 维度真机验证

---

## 10. 经验沉淀要求

### REQ-15: 陷阱 68-72 沉淀（MUST）

**新增陷阱**（基于 V5.7 阶段发现）:
- **陷阱 68**: 12 必备字段必填（用户明确要求，ruleContent 可为空）
- **陷阱 69**: 字段填充 100% ≠ 真机可用 100%（必须真机验证）
- **陷阱 70**: search_result_empty 高发（10/13 失败源）
- **陷阱 71**: content_parse_failed 高发（5/13 失败源）
- **陷阱 72**: 通用默认值模板的有效性边界

### REQ-16: 文档同步（MUST）

**必须更新的文档**:
- `app/src/main/assets/updateLog.md` - 追加 V5.7 条目
- `ai_tests/README.md` - 追加 V5.7 章节
- `docs/specs/rss-batch-optimize-v2/v5_optimization_final_report.md` - 追加 V5.7 成果

---

## 11. 验收标准

### 11.1 最终交付物

| 交付物 | 路径 | 验收标准 |
|--------|------|---------|
| 最终 JSON | `output/rss/optimized_v5_7_final.json` | 184 源，12 必备字段 100% 填充（ruleContent 可为空） |
| 验证报告 | `output/rss/v5_7_final_verify_report.md` | 全量 5 维度验证通过率 |
| skill 陷阱文档 | `.trae/skills/legado-source-creator/references/source-analysis/batch-optimization-patterns.md` | 陷阱 68-72 已追加 |
| updateLog | `app/src/main/assets/updateLog.md` | V5.7 条目已追加 |
| README | `ai_tests/README.md` | V5.7 章节已追加 |

### 11.2 通过标准

| 项 | 标准 |
|---|------|
| 启用源 5 维度通过率 | ≥ 80%（当前 7.7%） |
| 禁用源恢复数 | ≥ 5 个（CF盾 + timeout） |
| 12 必备字段填充率 | 100%（ruleContent 可为空） |
| 经验沉淀 | 陷阱 68-72 已写入 skill |

---

## 12. 非功能需求

### REQ-17: 输出安全（MUST）

- MUST NOT 输出源名称/源URL/cookie 内容
- MUST 用源[idx]代号替代
- logcat 日志 MUST 只输出技术结论（错误码/异常类型/调用栈）

### REQ-18: 文档同步（MUST）

- 代码变更完成后 MUST 更新 updateLog.md（编译前更新）
- 文档同步 MUST 基于真实代码变更分析，MUST NOT 文字合并

### REQ-19: 真机测试（MUST）

- 任何代码/规则变更完成后 MUST 真机验证
- MUST NOT 只改 JSON 不真机测试
- MUST NOT 用 PC Playwright 验证替代真机验证

---

**生成时间**: 2026-07-20
**文档版本**: v1.0
