# Spec: 上下文压缩用户反馈保全 + 主线任务完成质量审查（含 openspec 设计偏差审查）+ 打包功能差距修复

> 本 spec 由用户两次"需调整"反馈驱动扩展。
> 第一次："我说了，你仅仅要反思，你还要深度分析我给你的任务历史里面的主线任务呀，完成的是什么玩意，现在最新打包的功能千差万里！！！"
> 第二次："我说的主线任务是我给你发的历史文档里面有好多我已经明确要让你改的地方，但是你压根就没改，并且每次压缩上下文，你就丢失了这个我回复的信息，尤其是你在提问当中我给你的回复信息呀……你再看看你生成的这两个openspec，导致我现在看到你打的最新包里面整改的功能完全跟我设想的不一样的"

## Intent

本 spec 解决三个相互关联的核心问题：

### 问题 A：上下文压缩后 AI 无视用户反馈（原 Intent）

用户明确控诉："每次上下文超掉之后，你只要一压缩，就跟一个二比一样！直接无视我的反馈，尤其是你提问后我给你的响应信息！"

**根因**：用户反馈只存在于对话上下文，未持久化；压缩 summary 偏重任务进度轻视用户反馈；恢复时不读取反馈记录。

**子代理深度分析 364KB 历史文档发现的 4 个压缩后丢失反馈实例**：

| 丢失项 | 描述 | 后果 |
|--------|------|------|
| L1 | 第六次检查点用户选"需调整"但没给意见，AI 自行脑补为"用户授权自主推进" | 严重误判，AI 按自己想法推进 |
| L2 | P0 修复中用户发"?"催促，AI 无视继续执行 | 用户意图丢失 |
| L3 | 多次压缩导致环境信息反复遗忘（venv/ADB/updateLog 时机） | 反复犯同类错误 |
| L4 | 用户对"首页参考书架"核心诉求的持续弱化 | 从审查阶段正确纳入 → P0 阶段被降级为 Out of Scope |

### 问题 B：主线任务完成质量极差 + openspec 设计偏差（"完成的是什么玩意" + "你再看看你生成的这两个openspec"）

用户批评主线任务（P0 修复）完成质量低劣，且两个 openspec（yesterday-changes-deep-audit + p0-bugfix-round1）未能捕获用户核心反馈，导致"最新包功能跟设想不一样"。

#### B0：openspec 设计偏差审查（核心，第二次"需调整"反馈驱动）

子代理从历史文档提取了 **10 项用户提问反馈**，对照两个 openspec 后发现：

**7 项用户要求改但 openspec 没包含的地方**：

| 序号 | 用户要求 | yesterday-changes-deep-audit | p0-bugfix-round1 | 状态 |
|------|---------|------------------------------|-------------------|------|
| G1 | RssSourceActivity 移除文件夹视图保持列表 | 未明确 | **未包含** | 缺失 |
| G2 | 文件夹卡片样式参考书架 grid_group2 | 未明确 | **未包含** | 缺失 |
| G3 | **首页 style1/style2 设计**（核心诉求） | R5 正确捕获 | **明确排除（Out of Scope F-08）** | 🔴 最严重 |
| G4 | 双维度下拉菜单（归类维度+样式维度） | R5.6 捕获 | **未包含** | 缺失 |
| G5 | 编译前更新 updateLog.md | 未明确 | **未包含** | 缺失 |
| G6 | venv 强制使用（禁止公共 Python） | 未明确 | **未包含** | 缺失 |
| G7 | L2 真机功能验证（非仅编译通过） | 未明确 | **未包含** | 缺失 |

**5 项 openspec 与用户设想的偏差**：

| 序号 | 偏差 | 严重度 | 说明 |
|------|------|--------|------|
| D1 | 🔴 **核心诉求被降级推迟** | 致命 | F-08 首页 style1/style2 从用户核心诉求（第二次检查点反馈就明确）变为 p0-bugfix-round1 的 Out of Scope，是"千差万里"的根因 |
| D2 | RssSourceActivity 处理方向相反 | 严重 | 用户要"移除文件夹视图"，spec 在给管理页"添加选择模式"，方向相反 |
| D3 | 验证标准过低 | 严重 | 编译通过 ≠ 功能正确；E2E 无崩溃 ≠ 功能可用；未要求 L2 真机功能验证 |
| D4 | 双维度下拉菜单完全缺失 | 中 | R5.6 已设计，但 p0-bugfix-round1 完全没提 |
| D5 | 环境规范缺失 | 中 | venv 强制、updateLog 编译前更新、L2 验证均未写入 spec |

**10 项用户提问反馈清单（从历史文档提取）**：

| 序号 | 反馈类型 | 摘要 |
|------|---------|------|
| F1 | 最初指令 | /openspec 深度审查昨日改动 |
| F2 | 检查点1 第1次"需调整" | 只学到书架表象，未深度设计 |
| F3 | 检查点1 第2次"需调整" | 🔴 核心：要首页参考书架布局深度设计 |
| F4 | 检查点1 第3次"需调整" | 双维度下拉菜单 |
| F5 | 检查点1 第4次"需调整" | 搜索框不回填归类信息 |
| F6 | 检查点1 第5次 | 元审查要求 |
| F7 | 检查点1 第6次"需调整"但没给意见 | AI 自行脑补为"授权自主推进"（L1 丢失） |
| F8 | P0 修复中用户发"?" | 催促意图被无视（L2 丢失） |
| F9 | 愤怒爆发 | 10 个批评点（打包/环境/日志/Python 污染/任务完成度） |
| F10 | P0 修复中设计批评 | 文件夹卡片样式 + RssSourceActivity 移除文件夹视图（不在 p0-bugfix-round1 范围内） |

#### B1：代码实施审查（对照 p0-bugfix-round1/design.md）

| 主线任务 | TaskList 标记 | 实际状态 | 差距 |
|---------|--------------|---------|------|
| P0 修复 Phase 2 代码 | #5 in_progress | 代码完成但**未 git commit** | 18 文件修改游离在工作区 |
| F-P0-6 测试用例修复 | #11 completed | E2E 实测 `pass_rate=10%`（9/10 manual） | 标记完成但实测全失败 |
| 编译验证 + updateLog | #13 in_progress | clean build 完成，APK 已安装 | **updateLog.md 未更新**，功能未验证 |
| pref_main.xml 根因 | #14 in_progress | clean build 解决 | **未验证"书源管理"是否出现** |
| Phase 4 用户确认 | 未做 | — | 跳过检查点2 |
| Phase 5 交付 | 未做 | — | updateLog/INDEX/tasks 同步全缺 |

**铁证**：job-89502a6e3d044da7a20adac9e1023946 E2E 测试结果——`total=10 pass=1 manual=9 pass_rate=10.0%`，所有用例 `scroll_find: 未找到元素 "书源管理"`。

#### B2：交付质量审查

- P0 修复代码未提交（18 文件游离）
- E2E 测试 pass_rate=10%（远低于通过线）
- updateLog.md 未更新
- 未做真机 L2 功能验证（只做 L1 编译验证）

### 问题 C：当前打包功能与设计千差万里（"千差万里"）

最新 APK（legado_app_3.26.070914.apk）虽然 clean build 成功安装，但：

1. **F-08 首页 style1/style2 未实现**（用户核心诉求被 Out of Scope）—— 首页依然是旧的简单文件夹/列表切换
2. **双维度下拉菜单未实现** —— R5.6 设计的被完全遗漏
3. **RssSourceActivity 文件夹视图未移除**（方向相反，spec 在加选择模式）
4. **文件夹卡片样式未参考书架**（用户 F10 批评）
5. **F-P0-6 书源管理测试 9/10 失败** —— 用例假设的 UI 入口在首页找不到
6. **P0 修复代码未提交** —— 18 文件游离
7. **功能未真机 L2 验证** —— 只验证"App 不崩溃"
8. **updateLog.md 未更新** —— 用户不知道改了什么
9. **pref_main.xml 前 5 项缺失**（增量打包缓存 bug，已 clean build 但未验证）
10. **公共 Python 环境被污染**（违反 venv 强制规范）

## Scope

### In Scope（本次实现）

#### Part A: 反馈保全机制（预防未来）

1. 用户反馈即时持久化机制（写入 project_memory.md 的"用户反馈与决策记录"小节）
2. 压缩恢复流程从三件套扩展为四件套（+用户反馈记录）
3. AskUserQuestion 响应处理规范（复述确认 + 持久化）
4. 用户批评/纠正/决策即时持久化规范
5. AGENTS.md 上下文压缩恢复流程章节更新
6. 反馈记录定期归档机制（保留最近 7 天）

#### Part B: 主线任务完成质量深度审查（三层，解决当前问题）

**B0: openspec 设计偏差审查（新增，核心）**

7. 从历史文档提取用户提问反馈（10 项 F1-F10）
8. 对照 yesterday-changes-deep-audit spec.md，确认 R5 首页布局架构审查是否捕获用户核心诉求
9. 对照 p0-bugfix-round1 spec.md，找出"用户要求但 openspec 没包含"的地方（7 项 G1-G7）
10. 找出"openspec 与用户设想不一样"的地方（5 项偏差 D1-D5），特别是 D1 F-08 被降级为 Out of Scope
11. 输出《openspec 设计偏差审查报告》，明确每个缺失项/偏差的处理建议

**B1: 代码实施审查（原有）**

12. 对照 p0-bugfix-round1/design.md 逐项审查 P0 修复实际实施情况（C-01/V-01/F-01/M-01/M-02）
13. 审查 P0 修复代码是否真正提交（git status 确认 18 文件状态）

**B2: 交付质量审查（原有）**

14. 审查 F-P0-6 测试用例 UI 入口路径（为什么 scroll_find 找不到"书源管理"）
15. 审查 updateLog.md 是否已更新
16. 审查是否做了真机 L2 验证
17. 输出《主线任务完成质量审查报告》，列出所有"标记完成但实测失败"项

#### Part C: 打包功能与设计差距修复（解决当前问题）

**C1: openspec 偏差修复（新增）**

18. 修订 p0-bugfix-round1 spec 或新建 spec，明确 7 项缺失（G1-G7）的处理计划
19. 特别明确 F-08 首页 style1/style2 的归属 spec 和实施时机（不能继续 Out of Scope 悬空）
20. 明确双维度下拉菜单、RssSourceActivity 移除文件夹视图的归属

**C2: 代码/测试修复（原有）**

21. 修复 F-P0-6 测试用例 UI 入口路径（通过 UI dump 确认真实入口）
22. 提交 P0 修复代码（git commit 18 文件）
23. 更新 updateLog.md（面向用户描述 P0 修复内容）

**C3: E2E 重跑 + 真机 L2 验证（原有）**

24. 重新运行 E2E 测试（用 venv Python），确认 pass_rate 提升
25. 真机 L2 验证 P0 修复功能生效（UI dump + Python 解析 XML 确认交互元素状态）

### Out of Scope（不在本次实现）

- 不修改 AI 模型本身的上下文压缩算法（无法控制）
- 不解决所有上下文压缩问题（只聚焦用户反馈丢失）
- 不开发自动化工具检测反馈丢失（靠规范约束）
- 不修改 basic-memory 的存储结构（仅规范使用方式）
- 不在本 spec 直接实现 F-08 首页 style1/style2（属 P2 架构重构，本 spec 只明确其归属和计划，实际实现由专门 spec 承接）
- 不在本 spec 直接实现双维度下拉菜单（同上，明确归属后由专门 spec 承接）
- 不重构测试框架（只修复用例路径）

## Approach

### Selected Approach

**三部分并行推进：A 预防 + B 三层审查 + C 三层修复**

#### Part A: 用户反馈强制持久化 + 压缩恢复扩展四件套

核心思路：用户反馈不能只存在于对话上下文（会被压缩丢失），必须立即写入持久化存储（project_memory.md）；压缩恢复时必须读取用户反馈记录，而非只看任务进度。

具体措施：
1. project_memory.md 新增"用户反馈与决策记录"小节，实时追加用户反馈
2. 压缩恢复从三件套扩展为四件套：AGENTS.md + project_memory.md（含反馈记录）+ TaskList + 反馈清单输出
3. AskUserQuestion 响应必须复述 + 持久化
4. 用户批评/纠正/决策必须即时写入 project_memory.md + basic-memory

#### Part B: 主线任务完成质量三层深度审查

核心思路：不能信任 TaskList 的 completed 标记，也不能信任 openspec 已捕获用户所有反馈。必须从历史文档提取用户提问反馈，对照 openspec 找偏差，再审查代码实施，再审查交付质量。

**B0: openspec 设计偏差审查（三层中的第一层，最核心）**

具体措施：
1. 重新分析历史文档，提取用户提问反馈清单（F1-F10）
2. 对照 yesterday-changes-deep-audit/spec.md，确认 R5 是否捕获用户核心诉求（首页参考书架 style1/style2）
3. 对照 p0-bugfix-round1/spec.md 的 Out of Scope，逐项确认是否与用户诉求冲突（特别是 F-08）
4. 列出 7 项缺失（G1-G7）+ 5 项偏差（D1-D5），明确每项的处理建议
5. 输出《openspec 设计偏差审查报告》

**B1: 代码实施审查（三层中的第二层）**

具体措施：
1. 读取 p0-bugfix-round1/design.md，列出所有 P0 修复项
2. 逐项 Grep/Read 源码，确认每项修复是否真正实施
3. `git status` 确认 18 文件是否已提交

**B2: 交付质量审查（三层中的第三层）**

具体措施：
1. 对照 E2E 测试结果（job-89502a6e3d044da7a20adac9e1023946），确认测试是否真正通过
2. Read updateLog.md 确认是否更新
3. 确认是否做了真机 L2 验证
4. 输出《主线任务完成质量审查报告》

#### Part C: 打包功能与设计差距三层修复

核心思路：基于 Part B 三层审查报告，分层修复所有"千差万里"的差距。

**C1: openspec 偏差修复（三层中的第一层）**

具体措施：
1. 基于 B0 报告，修订 p0-bugfix-round1 spec 或新建 spec，明确 7 项缺失（G1-G7）的归属
2. 特别明确 F-08 首页 style1/style2 不能继续 Out of Scope 悬空，必须有明确实施计划
3. 明确双维度下拉菜单、RssSourceActivity 移除文件夹视图的归属 spec
4. 将 openspec 偏差审查发现沉淀为 project_memory.md 新规范（"openspec 生成前必须对照用户提问反馈清单"）

**C2: 代码/测试修复（三层中的第二层）**

具体措施：
1. UI dump 确认"书源管理"真实入口路径，修复 F-P0-6 用例
2. git commit P0 修复 18 文件
3. 更新 updateLog.md（面向用户描述 P0 修复内容）

**C3: E2E 重跑 + 真机 L2 验证（三层中的第三层）**

具体措施：
1. 用 venv Python 重跑 E2E 测试
2. 真机 L2 验证 P0 修复功能生效

### Alternatives Considered

#### Part A 否决方案

| 方案 | 描述 | 否决理由 |
|------|------|---------|
| A1. 独立反馈日志文件 | 新建 `用户反馈日志.md` 独立文件 | 增加文件管理复杂度；压缩恢复时需多读一个文件；与 project_memory.md 信息重叠 |
| A2. basic-memory 作为唯一存储 | 所有用户反馈只写入 basic-memory | basic-memory 是索引层非全文存储；搜索可能遗漏；project_memory.md 更直接可控 |
| A3. TaskList 扩展反馈字段 | 在 TaskList 任务描述中追加用户反馈 | TaskList 是任务状态源，非反馈存储；反馈不一定关联特定任务；结构不适合存长文本反馈 |
| A4. 对话摘要强制包含反馈 | 要求压缩 summary 必须包含用户反馈 | 无法控制 AI 模型的压缩行为；summary 仍可能遗漏；治标不治本 |

#### Part B 否决方案

| 方案 | 描述 | 否决理由 |
|------|------|---------|
| B1. 只信任 TaskList 标记 | 不审查，直接按 TaskList completed 项继续 | 正是当前问题的根因——TaskList 标记 completed 但实测失败 |
| B2. 只做代码审查不做 E2E | 只 Grep 源码确认修改，不跑 E2E | 代码存在不等于功能生效；F-P0-6 就是代码"存在"但 UI 入口找不到 |
| B3. 只做 E2E 不做代码审查 | 只跑 E2E，不对照 design.md | 无法发现"未提交的代码"和"updateLog 未更新"等问题 |
| B4. 不审查 openspec 设计偏差 | 只审查代码实施，不审查 openspec 是否捕获用户反馈 | 正是第二次"需调整"反馈的核心诉求；不审查就无法发现 F-08 被降级 |
| B5. 只审查 p0-bugfix-round1 不对照 yesterday-changes-deep-audit | 只看 P0 修复 spec | 无法发现 R5 正确捕获但 P0 spec 排除的偏差 |

#### Part C 否决方案

| 方案 | 描述 | 否决理由 |
|------|------|---------|
| C1. 不修复测试用例，直接跳过 F-P0-6 | F-P0-6 失败就失败，继续做 P1 | 违反"自测不通过=未完成"强制规则；用户已确认"全部修复" |
| C2. 不提交代码，只修复测试 | 代码留在工作区 | 18 文件游离有丢失风险；违反版本管理规范 |
| C3. 用公共 Python 跑 E2E | 不用 venv | 违反"禁止用公共 Python"强制规则（project_memory P0-17） |
| C4. 不修复 openspec 偏差，只修代码 | 只提交代码和测试，不明确 F-08 等归属 | 用户核心诉求继续悬空，"千差万里"未解决 |
| C5. 在本 spec 直接实现 F-08 | 把首页 style1/style2 实现塞进本 spec | 本 spec 是审查+修复+反馈保全，不是架构重构；F-08 应由专门 spec 承接 |

### Drawbacks

#### Part A 缺点

1. **project_memory.md 膨胀风险**：频繁追加用户反馈会导致文件变大，影响压缩恢复时的读取速度
   - 接受理由：通过定期归档（保留 7 天）缓解；反馈记录相比规范条文体积小
   - 升级路径：若膨胀严重，改为独立文件 + project_memory.md 仅保留指针

2. **AI 遵守规范的可靠性**：规范写在 AGENTS.md，但 AI 可能仍然不遵守
   - 接受理由：规范 + 检查点双重约束；用户可监督 AI 是否执行"复述+持久化"
   - 升级路径：若 AI 仍不遵守，考虑在 hooks 层强制拦截

3. **反馈记录的准确性依赖 AI 判断**：AI 需判断哪些用户输入属于"关键反馈"需要持久化
   - 接受理由：通过明确分类（AskUserQuestion 响应/批评/纠正/决策）降低判断难度
   - 升级路径：若判断不准，改为"所有用户消息都持久化"（但体积更大）

#### Part B 缺点

4. **审查耗时**：三层审查（openspec 偏差 + 代码实施 + 交付质量）消耗大量 token 和时间
   - 接受理由：不审查就无法发现"千差万里"；用户已明确要求深度分析
   - 升级路径：审查完成后，将模式沉淀为规范，减少未来审查需求

5. **openspec 偏差审查的主观性**：判断"用户设想"与"openspec 设计"的偏差需要解读用户意图
   - 接受理由：以历史文档中用户原话为依据，非 AI 臆测
   - 升级路径：偏差报告交用户确认后再修复

#### Part C 缺点

6. **修复可能引入新问题**：修复 F-P0-6 用例路径、提交代码、重跑 E2E 可能发现新 bug
   - 接受理由：发现问题正是审查的价值；隐藏的问题更危险
   - 升级路径：新 bug 按 P1/P2 流程处理，不阻塞本 spec 交付

7. **openspec 偏差修复可能需要新建多个 spec**：F-08/双维度下拉菜单/RssSourceActivity 等可能各需一个 spec
   - 接受理由：本 spec 只明确归属和计划，不直接实现，控制范围
   - 升级路径：新建 spec 由用户确认后启动

### Prior Art

- 当前 AGENTS.md 已有"上下文压缩恢复流程"章节（三件套并行读取），本方案是其扩展
- 当前 project_memory.md 已有"强制规范"和"关键踩坑案例"小节，本方案新增"用户反馈与决策记录"小节
- 当前 p0-bugfix-round1 spec 已有 design.md 和 tasks.md，本方案审查其实施情况
- 当前 yesterday-changes-deep-audit spec 已有 R5 首页布局架构审查，本方案对照其是否被 P0 spec 继承
- project_memory.md 已有 P0 规范 16/17（测试用例必须实测验证 UI 路径可达性 / E2E 测试必须用 venv Python），本方案是这些规范的具体执行

## Requirements

### REQ-01: 用户反馈即时持久化（Part A）

AI 在以下场景必须立即将用户反馈写入 project_memory.md 的"用户反馈与决策记录"小节：

| 场景 | 持久化内容 | 写入时机 |
|------|-----------|---------|
| AskUserQuestion 响应 | 用户选择/Other 输入原文 + 触发问题 | 用户响应后、AI 继续工作前 |
| 用户批评 | 批评原文 + AI 反思要点 | AI 回复前先写入 |
| 用户纠正 | 纠正内容 + 被纠正的错误行为 | AI 调整行为前先写入 |
| 用户明确决策 | 决策内容 + 决策上下文 | AI 执行决策前先写入 |

格式：`[YYYY-MM-DD HH:MM] 类型 | 触发上下文摘要 | 用户原文/响应 | 影响`

### REQ-02: 压缩恢复四件套（Part A）

上下文压缩恢复时，必须并行读取四件套（原三件套 + 用户反馈记录）：

1. AGENTS.md（强制规则）
2. project_memory.md（**含"用户反馈与决策记录"小节**）
3. TaskList（任务状态唯一权威源）
4. basic-memory（若有当前任务历史决策）

恢复后必须输出"已加载的用户反馈清单"，列出最近 7 天的用户反馈，确认理解。

### REQ-03: AskUserQuestion 响应复述（Part A）

用户通过 AskUserQuestion 给出响应后，AI 必须在继续工作前：
1. 复述用户的选择（"收到您选择：XXX"）
2. 若用户选"需调整"并通过 Other 输入意见，必须原文复述意见
3. 将响应写入 project_memory.md 的"用户反馈与决策记录"
4. 然后才能继续执行后续工作

### REQ-04: 反馈记录定期归档（Part A）

- project_memory.md 的"用户反馈与决策记录"小节保留最近 7 天的反馈
- 超过 7 天的反馈归档到 `c:\Users\shiyq\.trae-cn\memory\projects\-f-myself-github-WeAgentChat-temp-legado\archived_feedback\YYYYMM.md`
- 归档在每周首次压缩恢复时执行

### REQ-05: AGENTS.md 规范更新（Part A）

更新 AGENTS.md "上下文压缩恢复流程"章节：
- 三件套 → 四件套（+用户反馈记录）
- 新增"用户反馈持久化"小节
- 新增"AskUserQuestion 响应处理"规范

### REQ-06: 主线任务完成质量三层深度审查（Part B）

#### REQ-06.0: openspec 设计偏差审查（B0，核心）

| 审查项 | 审查方法 | 通过标准 |
|--------|---------|---------|
| 用户提问反馈提取 | 重新分析历史文档 | 提取 10 项反馈（F1-F10），与子代理报告交叉验证 |
| yesterday-changes-deep-audit 对照 | Read spec.md R5 章节 | 确认 R5 是否捕获用户核心诉求（首页参考书架 style1/style2） |
| p0-bugfix-round1 Out of Scope 对照 | Read spec.md Out of Scope | 逐项确认是否与用户诉求冲突，特别是 F-08 |
| 7 项缺失（G1-G7）确认 | 对照用户提问反馈 vs openspec | 列出每项缺失及处理建议 |
| 5 项偏差（D1-D5）确认 | 对照用户设想 vs openspec 设计 | 列出每项偏差及严重度，D1 F-08 降级为致命 |

输出《openspec 设计偏差审查报告》。

#### REQ-06.1: 代码实施审查（B1）

| 审查项 | 审查方法 | 通过标准 |
|--------|---------|---------|
| C-01 sourceSort 拆分 | Grep `bookSourceSort`/`rssSort` 确认 5 处修改 | PreferKey/AppConfig/BookSourceActivity/RssSourceActivity/SourceFolderAdapter 全部修改 |
| V-01 视频换集静音 | Read VideoPlayer.kt:161-163 确认 `setNeedMute(isMuted)` | 不再 `if (muteOnStart) setNeedMute(true)` |
| F-01 搜索框解耦 | Grep `currentGroup` 确认 RssFragment/ExploreFragment 修改 | onFolderClick 不回填 searchView |
| M-01/M-02 compact/grid 选择 | Grep `BookSourceSelection`/`RssSourceSelection` 接口 | 3 adapter 全部实现接口 |
| 代码提交 | `git status` 确认 18 文件 | 已 commit，工作区干净 |

#### REQ-06.2: 交付质量审查（B2）

| 审查项 | 审查方法 | 通过标准 |
|--------|---------|---------|
| E2E 测试 | 读取 job-89502a6e3d044da7a20adac9e1023946 结果 | pass_rate > 50%（当前 10%） |
| updateLog.md | Read updateLog.md 顶部 | 有 2026/07/09 条目 |
| 真机 L2 验证 | 确认是否有 L2 验证记录 | UI dump + Python 解析 XML 确认功能生效 |

输出《主线任务完成质量审查报告》，列出所有"标记完成但实测失败"项。

### REQ-07: 打包功能与设计差距三层修复（Part C）

#### REQ-07.1: openspec 偏差修复（C1）

1. 基于 B0 报告，修订 p0-bugfix-round1 spec 或新建 spec，明确 7 项缺失（G1-G7）归属
2. 特别明确 F-08 首页 style1/style2 的实施计划（不能继续 Out of Scope 悬空）
3. 明确双维度下拉菜单、RssSourceActivity 移除文件夹视图的归属 spec
4. 将 openspec 偏差审查发现沉淀为 project_memory.md 新规范

#### REQ-07.2: 代码/测试修复（C2）

1. **F-P0-6 用例 UI 入口修复**：UI dump 确认"书源管理"真实入口路径，更新测试用例
2. **P0 代码提交**：`git add` + `git commit` 18 文件（Conventional Commits 格式）
3. **updateLog.md 更新**：在顶部追加 2026/07/09 条目，面向用户描述 P0 修复内容

#### REQ-07.3: E2E 重跑 + 真机 L2 验证（C3）

1. **E2E 重跑**：用 `ai_tests\venv\Scripts\python.exe` 重跑 F-P0-6，确认 pass_rate 提升
2. **真机 L2 验证**：UI dump + Python 解析 XML 确认 P0 修复功能生效

### REQ-08: 审查报告输出（Part B + C）

输出三份报告：

1. **《openspec 设计偏差审查报告》**（B0）：10 项用户反馈 + 7 项缺失 + 5 项偏差 + 处理建议
2. **《主线任务完成质量审查报告》**（B1+B2）：对照 design.md 逐项审查结果 + 交付质量，列出"标记完成但实测失败"项
3. **《打包功能与设计差距修复报告》**（C1+C2+C3）：openspec 偏差修复 + 代码测试修复 + E2E/L2 验证结果

## Scenarios

### Scenario 1: AskUserQuestion 响应丢失（Part A，当前痛点）

**当前行为（错误）**：
1. AI 用 AskUserQuestion 询问修复范围
2. 用户选"全部修复"
3. 对话继续，AI 开始修复
4. 上下文压缩触发，summary 只保留"修复任务进行中"
5. 压缩恢复后，AI 不知道用户选了"全部修复"，可能只修了部分
6. 用户愤怒："我说的全部修复你听不见吗？"

**修复后行为（正确）**：
1. AI 用 AskUserQuestion 询问修复范围
2. 用户选"全部修复"
3. AI 复述："收到您选择：全部修复"
4. AI 立即写入 project_memory.md：`[2026-07-09 21:00] 决策 | 修复范围询问 | 用户选"全部修复" | P0-P3 全部修复`
5. 对话继续，AI 开始修复
6. 上下文压缩触发
7. 压缩恢复时读取四件套，包括"用户反馈与决策记录"
8. AI 输出："已加载用户反馈：2026-07-09 用户选'全部修复'"
9. AI 继续按"全部修复"执行，不遗漏

### Scenario 2: openspec 设计偏差审查（Part B0，当前痛点）

**当前行为（错误）**：
1. 用户在检查点1第二次反馈"要首页参考书架布局深度设计"
2. yesterday-changes-deep-audit spec 正确捕获为 R5
3. 生成 p0-bugfix-round1 spec 时，AI 把 F-08 首页 style1/style2 列为 Out of Scope
4. AI 没有对照用户提问反馈检查 openspec 是否捕获所有诉求
5. P0 修复完成，用户发现首页没变化
6. 用户愤怒："你再看看你生成的这两个openspec，导致我现在看到你打的最新包里面整改的功能完全跟我设想的不一样的"

**修复后行为（正确）**：
1. 用户在检查点1第二次反馈"要首页参考书架布局深度设计"
2. AI 写入 project_memory.md 反馈记录
3. 生成 p0-bugfix-round1 spec 时，AI 执行 REQ-06.0 openspec 偏差审查
4. AI 对照用户提问反馈清单，发现 F-08 是用户核心诉求
5. AI 不把 F-08 列为 Out of Scope，而是明确归属 spec 和实施时机
6. AI 输出《openspec 设计偏差审查报告》交用户确认
7. 用户确认后，F-08 在专门 spec 中实施

### Scenario 3: 主线任务完成质量审查（Part B1+B2，当前痛点）

**当前行为（错误）**：
1. P0 修复代码实施完成
2. TaskList #5 标记 in_progress，#11 标记 completed
3. E2E 测试 pass_rate=10%（9/10 manual）
4. AI 未审查 E2E 结果，继续下一步
5. 用户问"完成了吗"，AI 说"完成了"
6. 用户实测发现"书源管理"入口找不到，愤怒："完成的是什么玩意！"

**修复后行为（正确）**：
1. P0 修复代码实施完成
2. AI 执行 REQ-06.1 + REQ-06.2 审查：对照 design.md 逐项 Grep/Read 源码 + E2E 结果 + git 状态
3. AI 发现 E2E pass_rate=10%，标记为"未通过"
4. AI 输出《主线任务完成质量审查报告》：列出审查结果，标注失败项
5. AI 执行 REQ-07.2 + REQ-07.3 修复：修复用例、提交代码、更新 updateLog、重跑 E2E、L2 验证
6. AI 才向用户报告"P0 修复完成，E2E pass_rate=X%"

### Scenario 4: 打包功能与设计差距修复（Part C，当前痛点）

**当前行为（错误）**：
1. clean build 成功，APK 安装到 MEmu
2. AI 说"编译验证通过"
3. 用户安装 APK 后发现功能没变化（F-08 未实现、双维度下拉菜单缺失）
4. 用户愤怒："现在最新打包的功能千差万里！"

**修复后行为（正确）**：
1. clean build 成功，APK 安装到 MEmu
2. AI 执行 REQ-07.1 openspec 偏差修复：明确 F-08 等归属 spec
3. AI 执行 L2 验证：UI dump + Python 解析 XML 确认 P0 修复功能生效
4. AI 发现"书源管理"入口找不到（F-P0-6 失败）
5. AI 修复测试用例 UI 入口路径
6. AI 更新 updateLog.md："2026/07/09 - 修复书源/订阅源排序串扰、视频换集静音、搜索框回填等 P0 bug"
7. AI 用 venv Python 重跑 E2E，确认 pass_rate 提升
8. AI 才向用户报告"打包验证通过，updateLog 已更新，功能已 L2 验证；F-08 首页 style1/style2 已明确归属 XXX spec"

### Scenario 5: 反馈记录归档（Part A）

**触发条件**：每周首次压缩恢复时
1. AI 读取 project_memory.md 的"用户反馈与决策记录"小节
2. 筛选超过 7 天的反馈
3. 移动到 `archived_feedback/202607.md`
4. project_memory.md 只保留最近 7 天
5. 继续恢复流程

### Scenario 6: 用户批评丢失（Part A，当前痛点）

**当前行为（错误）**：
1. 用户批评："文件夹卡片丑爆了，学习书架布局"
2. AI 反思并修改
3. 上下文压缩触发，summary 只保留"修改文件夹卡片样式"
4. 压缩恢复后，AI 不知道用户批评过"丑爆了"，可能又做成简陋样式
5. 用户更愤怒："我说的话是放屁吗？"

**修复后行为（正确）**：
1. 用户批评："文件夹卡片丑爆了，学习书架布局"
2. AI 写入 project_memory.md：`[2026-07-09 21:05] 批评 | 文件夹卡片样式 | "丑爆了，学习书架布局" | 必须复用书架封面卡片视觉`
3. AI 反思并修改
4. 上下文压缩触发
5. 压缩恢复时读取四件套，包括用户批评记录
6. AI 输出："已加载用户反馈：2026-07-09 用户批评文件夹卡片丑爆了，要求学习书架布局"
7. AI 继续按用户要求执行
