# Spec: Skill Trio 优化 — AI 友好度提升

---

## 1. Intent（意图）

### 为什么做这件事？

`skill-architecture-optimization`（v2）完成了三个 Skill 的基础架构搭建（金字塔知识体系、JVM 仿真器、basic-memory 经验引擎、审计闭环），但**从 AI 使用者视角看**，存在大量阻碍 AI 高效准确执行的障碍：

**source-creator（20 个痛点）**：
- MockJsExtensions 函数签名与 Legado 源码不一致（ajax 参数类型 Any vs String），导致 JVM 测试误判
- 缺失约 80+ 个 JsExtensions 函数，AI 频繁遇到 `TypeError: java.xxx is not a function`
- 陷阱数量三处不一致（56 vs 79 vs AGENTS.md 56），AI 无法确定完整列表
- Phase 3 测试失败标准未定义，AI 不知何时进入 Phase 4
- MVP 选择无决策树，AI 要么始终用最慢的 MVP4，要么随机选择
- basic-memory 双写 7 步流程过于复杂，写入合规率仅 ~50%

**skill-auditor（16 个痛点）**：
- 42 个检查点远超 AI 单次上下文处理能力（违反 AGENTS.md "单子代理 ≤12 源文件"约束）
- 维度 H8/H9/H10 与 B1/D1/E1 重叠，AI 重复检查同一问题
- 审查框架自身存在 A3 类问题（子文档数量标注与实际不符）
- 无分层审查机制，无法快速健康检查 vs 全面深度审查
- 缺少自动化检测脚本，全部手动操作

**workflow-auditor（12 个痛点）**：
- **P0 级逻辑断裂**：8 个检查项中有 3 个检查的字段在 source-creator 执行证据模板中不存在
- 触发衔接断裂：source-creator 任务结束后无上下文传递机制给 workflow-auditor
- 全文仅 95 行，缺少判定逻辑细节（字段来源、失败处理）
- 降级路径过于简陋（3 行 vs skill-auditor 的 5 种场景表格）

### 解决什么问题？

1. **消除 AI 执行阻塞**：修复 P0 级逻辑断裂、字段缺失、签名不一致等直接导致错误输出的问题
2. **降低 AI 认知负荷**：精简流程步骤、合并重叠检查项、提供决策树替代自由判断
3. **提升 AI 执行一致性**：统一数据模型、统一降级模式、统一触发词表
4. **提高自动化程度**：提供检测脚本、检查清单模板、示例输出，减少 AI 手动操作

---

## 2. Scope（范围）

### 做什么

| 范围 | 说明 | 优先级 |
|------|------|--------|
| **P0 逻辑修复** | 修复 workflow-auditor 字段缺失、MockJsExtensions 签名不一致、陷阱数量统一 | P0 |
| **SKILL.md 精简与重构** | source-creator SKILL.md 从 669 行精简到 <500 行；skill-auditor 引入分层审查 | P0 |
| **统一数据模型** | 统一执行证据 metadata 字段集、统一 basic-memory note_type 语义 | P0 |
| **MVP 选择决策树** | 为 source-creator 增加 MVP1-4 选择指引 | P1 |
| **Phase 失败标准定义** | 明确 Phase 3 何种结果需要进入 Phase 4 | P1 |
| **basic-memory 双写简化** | 从 7 步简化为 3 步，提供一键模板 | P1 |
| **skill-auditor 分层审查** | L1 快速(10项) / L2 核心(15项) / L3 深度(17项) | P1 |
| **自动化检测脚本** | 死链检测、版本锁检测、文件债务扫描等 | P1 |
| **全局触发词表与调用链路图** | 去重触发词、明确调用顺序、上下文传递规范 | P2 |
| **MockJsExtensions 未实现函数速查表** | 明确列出 80+ 未实现函数，避免 AI 陷入不必要的 Phase 4 | P2 |
| **统一降级路径模式** | 三套降级逻辑归一为"检测→替代→标记"三步 | P2 |

### 不做什么

| 不做 | 原因 |
|------|------|
| 不新增 Skill 功能 | 本次是优化现有 Skill 的 AI 友好度，非功能扩展 |
| 不补充所有 80+ 缺失函数 | 只补充高频函数（~15个），其余标注"未实现" |
| 不重写整个 skill-auditor 框架 | 在现有 42 项基础上合并精简，非推倒重来 |
| 不修改 Legado 项目源码 | 只修改 Skill 文件和工具代码 |
| 不开发新的 MCP 服务器 | 复用现有 basic-memory MCP |
| 不改变金字塔架构（L1-L4） | 架构本身合理，问题是内容呈现方式 |

### 影响哪些模块

| 模块 | 影响类型 | 说明 |
|------|---------|------|
| `.trae/skills/legado-source-creator/SKILL.md` | 修改 | 精简+重构+增加决策树+统一陷阱编号 |
| `.trae/skills/legado-source-creator/references/troubleshooting/_index.md` | 修改 | 统一陷阱编号为连续 79 条 |
| `.trae/skills/legado-skill-auditor/SKILL.md` | 修改 | 引入分层审查+合并重叠项+减少至 ~30 项 |
| `.trae/skills/legado-workflow-auditor/SKILL.md` | 修改 | 修复字段缺失+补充判定逻辑+增加关系说明 |
| `tools/mvp1-build/src/main/kotlin/.../MinimalMockJsExtensions.kt` | 修改 | 修复 ajax/createSymmetricCrypto 签名+补充高频函数 |
| `tools/rule_engine_client.py` | 修改 | 同步新函数 API |
| `tools/jvm_helpers.py` | 修改 | 更新可信度评估规则 |
| `AGENTS.md` | 修改 | 统一陷阱数量描述+更新 Skill 协作说明 |
| `docs/specs/skill-architecture-optimization/tasks.md` | 修改 | 标记关联任务状态 |

---

## 3. Approach（方法）

### 技术方向

采用 **"先修断路，再铺快车道，最后装红绿灯"** 三阶段方法：

#### 阶段一：修断路（P0 修复）

优先修复直接导致 AI 输出错误或无法执行的问题：

```
1. workflow-auditor 字段对齐（sync_status/trap_check/dual_write → 执行证据模板）
2. MockJsExtensions 签名修复（ajax: String→Any, createSymmetricCrypto 补 ByteArray 重载）
3. 陷阱数量统一（SKILL.md 标题/L113/AGENTS.md → 统一为 79 条）
4. @. 前缀验证与清理（rule-syntax.md 中可能错误的 JSONPath 描述）
```

#### 阶段二：铺快车道（P1 优化）

降低 AI 认知负荷，让常用路径更顺畅：

```
5. SKILL.md 精简（移除冗余描述，拆分为 L1 必读 + L2 按需查阅）
6. MVP 选择决策树嵌入 SKILL.md
7. Phase 3 失败标准明确定义
8. basic-memory 双写 7 步 → 3 步
9. skill-auditor 分层审查（L1/L2/L3）
10. 自动化检测脚本（死链/版本锁/文件债务）
```

#### 阶段三：装红绿灯（P2 完善）

建立规范和护栏，确保长期一致性：

```
11. 全局触发词表（去重+优先级排序）
12. 调用链路图（skill-auditor → source-creator → workflow-auditor）
13. MockJsExtensions 未实现函数速查表
14. 统一降级路径模式（三步式）
15. 审计报告格式简化
```

#### 阶段四：自进化闭环（P1 核心 — 用户核心诉求）

让 skill 每次使用后自动进化，越来越精准：

```
16. 进化触发器（测试失败→自动分析根因→分类进化需求）
17. 服务端自动进化（Mock函数缺失/行为不一致→更新Kotlin→重建JAR→重新验证）
18. 客户端自动进化（测试能力不足→增强Python脚本）
19. 进化成果沉淀（写入basic-memory+更新文档+标记进化版本）
20. 精准度度量与追踪（定义精准度指标，每次进化后重新计算）
```

#### 阶段五：零人工干预测试（P1 核心 — 用户核心诉求）

让内置测试模拟真实 Legado 全流程，用户不需要手机调试：

```
21. 全流程模拟器（deep-verify.py 升级：模拟搜索→详情→目录→正文全链路）
22. 网络请求模拟（ajax/get/post 的真实HTTP请求+Cookie管理）
23. WebView 部分模拟（CF盾检测+Cookie传递，非完全WebView渲染）
24. "已验证可用"标记机制（全流程通过后输出标记，用户直接导入手机）
25. 进化反馈循环（手机端反馈→进化skill→下次更精准）
```

### 设计约束

| 约束 | 值 | 说明 |
|------|-----|------|
| SKILL.md 目标行数 | source-creator <500, skill-auditor <800 | 减少 AI 读取压力 |
| 检查点目标数 | skill-auditor 从 42 降至 ~30 | 合并重叠项后 |
| basic-memory 写入步骤 | 从 7 步降至 3 步 | 降低 AI 操作成本 |
| Mock 新增函数数 | ~15 个高频函数 | 不追求全覆盖 |
| 全流程模拟覆盖率 | >85% | 模拟搜索→详情→目录→正文→review全链路 |
| 零人工干预率 | >80% | 内置测试通过即可直接导入手机 |
| 自进化触发率 | >90% | 测试失败自动触发进化闭环 |
| 进化响应时间 | <5分钟 | 从测试失败到进化完成 |
| AI 执行效率 | <10分钟 | 从用户给URL到输出_verified:true |
| 首次通过率 | >60% | 无需进化直接通过 |
| 进化收敛率 | >95% | 精准度达标后停止自动进化 |
| 进化次数上限 | 3次 | 同一问题最多进化3次 |
| 向后兼容 | 所有修改不破坏现有工作流 | 已有的书源创建流程不受影响 |

---

## 4. Requirements（需求）

### FR-1: P0 逻辑修复

| ID | 需求 | 验收标准 |
|----|------|---------|
| FR-1.1 | workflow-auditor 检查项字段与 source-creator 执行证据模板完全匹配 | 8 个检查项中每个字段的来源（metadata.key 或标志解析）都有明确定义 |
| FR-1.2 | MockJsExtensions.ajax() 参数类型改为 `Any`，内部 `toString()` 转换 | JVM 测试中 `java.ajax(123)` 和 `java.ajax(response)` 均正常工作 |
| FR-1.3 | MockJsExtensions.createSymmetricCrypto() 补充 ByteArray 重载，iv 类型改为 `String?` | 使用 ByteArray 密钥的加密规则可通过 JVM 验证 |
| FR-1.4 | 陷阱数量在 SKILL.md 标题、L113、AGENTS.md 三处统一为 "79 条" | Grep "56条" 返回 0 结果（排除引用旧版本的注释） |
| FR-1.5 | rule-syntax.md 中 `@.` 前缀描述经源码验证，如不支持则删除或标注废弃 | AnalyzeRule.kt SourceRule.init 中无 `@.` 处理逻辑时，文档中不再推荐使用 |

### FR-2: SKILL.md 精简与决策辅助

| ID | 需求 | 验收标准 |
|----|------|---------|
| FR-2.1 | source-creator SKILL.md 总行数 <500 行（当前 669 行） | `wc -l SKILL.md` < 500 |
| FR-2.2 | MVP 选择决策树嵌入 SKILL.md JVM 测试章节 | AI 可根据规则类型（纯 CSS / 含加密 / 含 JS / 不确定）选择合适 MVP |
| FR-2.3 | Phase 3 失败标准明确定义（至少 4 种失败条件） | AI 遇到 ES6 语法/JVM TypeError/可信度低>50%/CSS 匹配 0 时，均知道需进入 Phase 4 |
| FR-2.4 | 测试脚本选择决策树嵌入 SKILL.md | AI 知道何时用 verify-source.py vs deep-verify.py vs verify-decrypt.py |
| FR-2.5 | 陷阱速查表编号连续化或明确标注"精选 N 条（完整 79 条详见 xxx）" | AI 不会因为编号跳过（1,2,5,6,9...）而困惑 |

### FR-3: basic-memory 简化

| ID | 需求 | 验收标准 |
|----|------|---------|
| FR-3.1 | 双写流程从 7 步简化为 3 步（判断类型→写 Skill 文档→写 basic-memory） | SKILL.md Phase 5 反哺写入策略章节 < 30 行 |
| FR-3.2 | 执行证据模板 metadata 字段增加 sync_status/trap_check/dual_write/schema_validation | workflow-auditor 8 个检查项均可从 metadata 直接读取 |
| FR-3.3 | basic-memory 降级路径统一为"检测不可用→Grep references/替代→标记待验证" | 三个 Skill 的降级描述使用相同的三步模式 |
| FR-3.4 | workflow-auditor 审计报告 note_type 改为 `audit-report`，directory 改为 `audit-reports/` | 不再与 source-creator 的 test-report 混淆 |

### FR-4: skill-auditor 分层审查

| ID | 需求 | 验收标准 |
|----|------|---------|
| FR-4.1 | 定义 L1 快速检查（10 项，5 分钟内完成） | 包含死链/薄文件/版本锁/旧版源码/临时脚本/缓存/语法/JAR 存在性/模板/输出目录 |
| FR-4.2 | 定义 L2 核心检查（15 项，20 分钟内完成） | 包含跨文件一致性/代码一致性/脚本参数/源码匹配/basic-memory/新用户视角 |
| FR-4.3 | 定义 L3 深度检查（17 项，40 分钟内完成） | 包含字段定义/重复笔记/设计文档/债务清理/CMS样本/回退链 |
| FR-4.4 | 合并 H8+B1+D1 为"代码一致性统一检查"、H9+A4+D3+D4 为"文档一致性统一检查"、H10+E1+E2 为"memory 一致性检查" | 检查点总数从 42 降至 ~30 |
| FR-4.5 | 修正审查框架自身的 A3 数量标注（special-scenarios 12→13, source-analysis 5→6） | 审查框架自身通过 A3 检查 |

### FR-5: 自动化与规范化

| ID | 需求 | 验收标准 |
|----|------|---------|
| FR-5.1 | 提供 check_dead_links.py 或等效的一行命令检测 A1 死链 | 返回所有断链的文件路径和行号 |
| FR-5.2 | 提供版本锁检测命令（grep build.gradle.kts vs AGENTS.md） | 返回 jsoup/rhino/hutool 三个版本的一致性判断 |
| FR-5.3 | 全局触发词表（三个 Skill 去重后的唯一触发词集合） | 无两个 Skill 共享同一触发词（除非有意为之且有优先级说明） |
| FR-5.4 | MockJsExtensions 未实现函数速查表（按类别分组，标注影响和建议） | AI 遇到未实现函数时知道标记"需真机验证"而非进入 Phase 4 |
| FR-5.5 | workflow-auditor 增加"与 legado-skill-auditor 的关系"说明 | 包含区别表格和调用顺序建议 |

### FR-6: workflow-auditor 增强

| ID | 需求 | 验收标准 |
|----|------|---------|
| FR-6.1 | 每个检查项增加"字段来源"和"失败处理"列 | AI 执行时不需自行猜测字段从哪取 |
| FR-6.2 | 明确代码进化检查路径（search_notes jvm-evolution tag） | 检查项7 可稳定执行，不再默认 N/A |
| FR-6.3 | 降级路径扩展（增加 basic-memory 不可用检测方法、output 目录检查方法、报告输出格式） | 降级后仍能输出结构化报告 |
| FR-6.4 | 总评分分母规则明确（有效项数 = 8 - N/A 项数） | 7/8 通过且 1 项 N/A 时显示 7/7 全通过 |

### FR-7: 自进化闭环（用户核心诉求）

| ID | 需求 | 验收标准 |
|----|------|---------|
| FR-7.1 | 进化触发器：测试失败时自动分析根因，分类进化需求（8 类：经验缺失/Mock缺失/行为不一致/脚本能力不足/规则语法错误/URL模板错误/选择器错误/字段映射错误） | AI 遇到测试失败时，能自动判断属于 8 类中的哪一类，而非直接进入 Phase 4 或标记"需真机" |
| FR-7.2 | 服务端自动进化：Mock 函数缺失时，自动读取 Legado 源码对应函数 → **依赖分析**（判断是否可独立 Mock）→ 更新 MinimalMockJsExtensions.kt → 重建 JAR → 重新验证 | AI 遇到 `TypeError: java.xxx is not a function` 时，能自动补全函数并重新测试；依赖 AppContext 等不可独立 Mock 的函数标注"需简化实现" |
| FR-7.3 | 服务端行为进化：Mock 函数行为与 Legado 不一致时，对比源码 → 修正行为 → 重建 JAR → 重新验证 | JVM 测试结果与 Legado 真机行为一致率 >90% |
| FR-7.4 | 客户端自动进化：测试脚本能力不足时，增强 Python 脚本（如增加新验证场景：登录/分页/多页目录） | deep-verify.py 能覆盖新发现的验证场景 |
| FR-7.5 | 进化成果沉淀：进化后写入 basic-memory（note_type=experience, tags=["evolution"]）+ 更新未实现函数速查表 + 标记进化版本 | 每次进化有版本号+变更记录，可追溯 |
| FR-7.6 | 精准度度量：定义精准度 = 内置测试通过率 × 真机一致率，每次进化后重新计算并记录 | 精准度指标可追踪趋势，持续提升 |
| FR-7.7 | 进化安全机制：自动进化前备份 JAR 和 Kotlin 源码，进化失败时回滚 | 进化失败不影响现有功能 |
| FR-7.8 | 规则语法错误进化：测试失败原因为规则语法错误时（如 JSONPath 语法错误、CSS 选择器无效），自动分析语法错误并修正规则 | AI 遇到规则语法错误时，能自动修正而非标记"需真机" |
| FR-7.9 | URL 模板进化：测试失败原因为 URL 模板错误时（如编码方式不对、参数缺失），自动分析并修正 URL 模板 | AI 遇到 URL 模板错误时，能自动修正 |
| FR-7.10 | 选择器进化：测试失败原因为选择器匹配 0 元素时，自动分析页面结构并修正选择器 | AI 遇到选择器匹配失败时，能自动修正 |

### FR-8: 零人工干预测试（用户核心诉求）

> **注**：FR-8.1-8.4/8.7/8.8/8.10 的基础能力由 `test-infra-upgrade` Spec 提供（端到端调试器、CookieStore、MockJsExtensions 扩展、debug-source.py），本 Spec 不重复实现，仅在此基础上增加上层能力。

| ID | 需求 | 验收标准 |
|----|------|---------|
| FR-8.5 | 验证报告增强：在 test-infra-upgrade 的 debug-source.py 验证报告基础上，增加进化记录（触发原因+进化动作+结果）和速度度量（耗时+首次通过率） | 用户可查看验证详情+进化历史+速度趋势 |
| FR-8.6 | 进化反馈循环：用户手机端反馈（可用/不可用）写入 basic-memory，下次遇到同类网站时更精准 | basic-memory 中有 `cases/` 目录记录实战案例和反馈 |
| FR-8.9 | 网络请求安全机制：在 test-infra-upgrade 的 RealHttpExecutor 基础上增加请求频率控制（间隔≥1秒）+ UA伪装（模拟浏览器）+ 超时重试（30秒超时，3次重试）+ 请求日志记录 | 网络请求不会触发网站反爬，日志可追溯 |

### FR-9: 进化收敛机制（防止无限进化）

| ID | 需求 | 验收标准 |
|----|------|---------|
| FR-9.1 | 进化次数上限：同一问题（相同错误签名）最多进化 3 次，超过则标记"需人工介入"并终止自动进化 | 同一错误不会无限触发进化，3 次后自动停止 |
| FR-9.2 | 进化收敛判断：精准度 >90% 后降低进化频率（仅记录不自动进化），>95% 后完全停止自动进化 | 精准度达标后不再过度进化 |
| FR-9.3 | 进化冲突检测：同一函数被多次进化时，保留最新版本 + 版本号追溯 + 旧版本归档 | 函数版本管理清晰，可回溯任意版本 |
| FR-9.4 | 进化死循环检测：相同错误在 24 小时内重复出现 3 次时终止进化，标记"疑似环境问题" | 避免因环境问题（如网络不通）导致无限进化 |
| FR-9.5 | 进化日志与统计：记录每次进化的触发原因、耗时、结果，输出进化趋势报告 | 进化历史可追溯，趋势可分析 |

### FR-10: 必须人工干预边界（明确零干预的极限）

| ID | 需求 | 验收标准 |
|----|------|---------|
| FR-10.1 | 明确"可零干预"场景：普通 CSS/XPath 规则网站、含 JS 但无加密的网站、含 AES/DES 加密的网站 | 这三类网站可完全零人工干预 |
| FR-10.2 | 明确"需配置"场景：CloudFlare 保护（JS Challenge）需配置 loginUrl，网站结构变化需用户确认新结构 | 这类场景 AI 检测后提示用户配置，非自动通过 |
| FR-10.3 | 明确"必须人工"场景：需要账号密码登录、需要人工过验证码 | 这类场景 AI 检测后直接标记"需人工"，不尝试自动通过 |
| FR-10.4 | 场景检测与标记：全流程模拟器在执行前先检测网站类型，标注属于哪类场景 | 用户可在验证报告中看到网站类型标注和干预建议 |

### FR-11: 速度度量（用户核心诉求 — 越来越快）

| ID | 需求 | 验收标准 |
|----|------|---------|
| FR-11.1 | 进化响应时间度量：记录从测试失败到进化完成的时间 | 目标 <5 分钟 |
| FR-11.2 | AI 执行效率度量：记录从用户给 URL 到输出 _verified:true 的时间 | 目标 <10 分钟 |
| FR-11.3 | 首次通过率度量：统计无需进化直接通过的比例 | 目标 >60%，趋势递增 |
| FR-11.4 | 速度趋势报告：输出历史速度趋势 + 当前值 + 目标值 | 速度指标可追踪趋势，持续提升 |

---

## 5. Scenarios（场景）

### 场景 1：AI 创建一个普通小说网站的书源

**前置**：用户说"帮我把 xx 笔趣阁做成书源"

**当前体验（优化前）**：
1. AI 读取 SKILL.md（669 行）→ 上下文占用大
2. AI 过陷阱速查表 → 编号不连续，困惑是否有遗漏
3. AI 搜索 basic-memory → 7 步搜索策略复杂
4. AI 构建 CSS 规则 → 不知道用 MVP2 还是 MVP4，默认 MVP4（慢）
5. AI 运行测试 → 10 个脚本不知道选哪个
6. AI 评估可信度 → 规则分散在 3 处，可能用过时的
7. AI 写执行证据 → 模板复杂，字段多
8. AI 调用 workflow-auditor → 字段不匹配，3/8 检查项必然失败

**目标体验（优化后）**：
1. AI 读取精简版 SKILL.md（<500 行）→ 上下文节省 25%
2. AI 过陷阱速查表 → 编号清晰，79 条完整列表可选
3. AI 搜索 basic-memory → 1 次 search_notes，3 步即可
4. AI 构建 CSS 规则 → 决策树指示"纯 CSS → MVP2 即可"
5. AI 运行测试 → 脚本选择决策树指引 verify-source.py → verify-selector.py
6. AI 评估可信度 → 单一来源规则（jvm_helpers.py 为准）
7. AI 写执行证据 → 3 步简化模板
8. AI 调用 workflow-auditor → 8/8 检查项均可从 metadata 读取

### 场景 2：AI 执行 skill-auditor 全面审查

**前置**：用户说"全面审查一下 legado-source-creator skill"

**当前体验（优化前）**：
1. AI 读取 skill-auditor SKILL.md（1104 行）→ 上下文接近溢出
2. AI 启动 3 个子代理 → 子代理 A 负责 18 项过载
3. AI 执行 42 个检查项 → 多处重复（H8 vs B1 vs D1）
4. AI 发现审查框架自身 A3 问题 → 降低可信度
5. AI 输出报告 → 5 个部分格式复杂

**目标体验（优化后）**：
1. AI 选择审查模式 → 默认 L2 核心（15 项），或用户要求全量时 L3
2. AI 启动子代理 → 负载均衡（每代理 ~10 项）
3. AI 执行 ~30 个检查项 → 无重复（已合并 H8+B1+D1 等）
4. AI 使用自动化脚本 → A1 死链/B5 版本锁/H4 缓存自动检测
5. AI 输出报告 → 3 部分简化格式

### 场景 3：AI 处理含加密的视频订阅源

**前置**：用户说"这个视频站有 AES 加密，帮我做个订阅源"

**当前体验（优化前）**：
1. AI 构建 ruleContent 含 `<js>` 加密代码 → 选择 MVP4（最慢但最全）
2. AI 用 JVM 测试加密 → `createSymmetricCrypto(key, iv)` 因签名不匹配报错
3. AI 误判为规则错误 → 进入 Phase 4 读源码 → 发现是 Mock 签名问题而非规则问题
4. 浪费大量时间在 Phase 4 源码深挖上

**目标体验（优化后）**：
1. AI 构建 ruleContent 含 `<js>` 加密代码 → 决策树指示"含加密 → MVP3 或 MVP4"
2. AI 用 JVM 测试加密 → `createSymmetricCrypto` 签名正确，测试通过
3. 如遇未实现函数（如 `strToBytes`）→ 查未实现函数速查表 → 标记"需真机验证"
4. 不进入不必要的 Phase 4

### 场景 4：workflow-auditor 审计一次已完成的书源创建任务

**前置**：source-creator 刚完成任务，AI 自动调用 workflow-auditor

**当前体验（优化前）**：
1. workflow-auditor 步骤1 → "向用户确认源名称" → 但对话上下文已滚动，源名称丢失
2. workflow-auditor 步骤2 → search_notes 找到执行证据
3. workflow-auditor 步骤3 → 检查 sync_status → metadata 中无此字段 → 检查失败
4. workflow-auditor 步骤3 → 检查 trap_check → metadata 中无此字段 → 检查失败
5. workflow-auditor 步骤3 → 检查 dual_write → metadata 中无此字段 → 检查失败
6. 输出 5/8 通过 → 但实际 source-creator 正确执行了所有步骤

**目标体验（优化后）**：
1. source-creator 任务完成时 → 自动传递 source_name 给 workflow-auditor
2. workflow-auditor 步骤1 → 从调用参数获取源名称（无需向用户确认）
3. workflow-auditor 步骤3 → sync_status 从 metadata.sync_status 读取 → ✅
4. workflow-auditor 步骤3 → trap_check from metadata.trap_check → ✅
5. workflow-auditor 步骤3 → dual_write from metadata.dual_write → ✅
6. 输出 8/8 通过 → 真实反映执行情况

### 场景 5：零人工干预创建书源（终极目标）

**前置**：用户说"帮我把 xx 笔趣阁做成书源"

**当前体验（优化前）**：
1. AI 生成书源 JSON → verify-source.py 仅检查字段完整性
2. AI 说"自测通过" → 用户导入手机 → 搜索无结果
3. 用户反馈"搜索不了" → AI 需要重新分析 → 可能是 searchUrl 参数错误
4. 用户再次导入 → 搜索有了但目录页空白 → AI 再修复 ruleToc
5. 来回 3-5 轮调试，用户体验极差

**目标体验（优化后）**：
1. AI 生成书源 JSON → 全流程模拟器自动执行：
   - 模拟搜索：构造搜索 URL → 真实 HTTP 请求 → 解析搜索结果列表
   - 模拟详情：取搜索结果第一本书 → 请求详情页 → 解析书名/作者/封面
   - 模拟目录：请求目录页 → 解析章节列表
   - 模拟正文：取第一章 → 请求正文页 → 解析正文内容
2. 全流程通过 → 输出 `"_verified": true` 标记 + 验证报告
3. 用户导入手机 → 直接可用，无需调试
4. 如果模拟器发现 searchUrl 返回空 → AI 自动修复（调整参数/编码）→ 重新模拟 → 通过
5. 如果遇到新网站特征（如新加密方式）→ 触发自进化 → 补充 Mock 函数 → 重新验证 → 通过

### 场景 6：Skill 自进化（持续提升精准度）

**前置**：AI 遇到一个使用新 JS 函数的网站

**当前体验（优化前）**：
1. AI 构建规则含 `java.importScript(url)` → JVM 测试报 `TypeError: java.importScript is not a function`
2. AI 标记"需真机验证" → 用户手机测试 → 确实可用
3. 下次遇到同类网站 → 同样报错 → 同样标记"需真机" → 无进化

**目标体验（优化后）**：
1. AI 构建规则含 `java.importScript(url)` → JVM 测试报 `TypeError`
2. 进化触发器自动分析 → 分类为"Mock 函数缺失"
3. 自动读取 Legado 源码 `JsExtensions.kt` 中 `importScript` 函数签名和实现
4. **依赖分析**：判断 `importScript` 是否依赖 AppContext 等不可独立 Mock 的类 → 可独立 Mock
5. 自动更新 `MinimalMockJsExtensions.kt` → 重建 JAR → 重新验证 → 通过
6. 进化成果写入 basic-memory（tags=["evolution"]）+ 更新未实现函数速查表
7. 下次遇到同类网站 → 直接通过，无需进化
8. 精准度指标自动更新：从 60% → 62%（+2% 因新增函数）

### 场景 7：进化收敛（防止无限进化）

**前置**：AI 遇到一个使用复杂 JS 函数的网站，该函数依赖 AppContext

**当前体验（优化前）**：
1. AI 构建规则含 `java.startBrowser(url)` → JVM 测试报 `TypeError`
2. AI 尝试自动进化 → 读取源码 → 发现依赖 AppContext → 无法独立 Mock
3. AI 反复尝试不同实现 → 每次都失败 → 浪费大量时间
4. 最终标记"需真机验证"

**目标体验（优化后）**：
1. AI 构建规则含 `java.startBrowser(url)` → JVM 测试报 `TypeError`
2. 进化触发器自动分析 → 分类为"Mock 函数缺失"
3. 自动读取源码 → **依赖分析**：发现 `startBrowser` 依赖 AppContext → 标注"需简化实现"
4. 进化触发器判断：该函数不可独立 Mock → 标记"需真机验证" + 写入未实现函数速查表
5. **进化收敛机制**：记录该错误签名，24 小时内再次遇到时不再尝试进化
6. 下次遇到同类网站 → 查速查表 → 直接标记"需真机验证"，不浪费时间
7. 精准度指标记录：该函数为"不可进化项"，不影响整体精准度趋势

### 场景 8：必须人工干预边界（明确零干预的极限）

**前置**：用户说"帮我把 xx 网站做成书源"，该网站需要登录

**当前体验（优化前）**：
1. AI 生成书源 JSON → 全流程模拟器执行搜索 → 返回登录页
2. AI 误判为规则错误 → 尝试修正选择器 → 仍然返回登录页
3. AI 触发进化 → 尝试增强选择器 → 仍然失败
4. 来回 3 次进化后 → 标记"需真机验证"
5. 用户手机测试 → 发现需要登录 → 反馈给 AI
6. AI 才知道该网站需要登录

**目标体验（优化后）**：
1. AI 生成书源 JSON → 全流程模拟器执行前先检测网站类型
2. **登录检测**：请求首页 → 检测到登录表单/重定向到登录页 → 标记"需配置 loginUrl"
3. 全流程模拟器跳过搜索/详情/目录/正文模拟 → 直接输出验证报告
4. 验证报告标注：网站类型="需登录"，干预建议="请提供账号密码或配置 loginUrl"
5. AI 不尝试自动进化（因为属于"必须人工"场景）
6. 用户看到报告 → 提供账号密码 → AI 配置 loginUrl → 重新验证 → 通过

### 场景 9：速度度量与持续优化

**前置**：AI 已完成 10 次书源创建任务

**当前体验（优化前）**：
1. 每次创建耗时 30 分钟（含手动调试往返）
2. 无速度度量，不知道是否在变快
3. 无首次通过率统计，不知道进化是否有效

**目标体验（优化后）**：
1. 每次创建自动记录耗时：第 1 次 25 分钟，第 5 次 15 分钟，第 10 次 8 分钟
2. 首次通过率统计：第 1-3 次 20%，第 4-7 次 45%，第 8-10 次 65%
3. 进化响应时间统计：平均 3.5 分钟（目标 <5 分钟）
4. 速度趋势报告输出：AI 执行效率持续提升，首次通过率递增
5. 精准度趋势：从 60% → 75% → 88%，趋近收敛目标 90%
