# Tasks：子代理编排与思考预算优化

## 1. 准备工作

- [x] 1.1 确认需求范围（已完成：强制子代理+监控+质量保证+规范冲突处理）
- [x] 1.2 阅读相关源码与规范（AGENTS.md "复杂任务处理流程"、"并发文件修改规范"、OpenSpec 工作流程）
- [x] 1.3 确认功能命名与目录（`docs/specs/sub-agent-budget-optimization/`）

## 2. 核心实现

### 2.1 新增子规范文件

- [x] 2.1.1 创建 `docs/project-rules/sub-agent-quality-management.md`
  - 内容：子代理监控机制+质量保证体系+prompt 标准化+失败重试
  - 验证：Read 确认文件存在 + 关键章节存在

### 2.2 修改 AGENTS.md

- [x] 2.2.1 新增"输出与工具预算管理"章节
  - 内容：单次回复输出预算+工具调用预算+思考预算+禁止建议新对话
  - 验证：Grep 确认章节存在
- [x] 2.2.2 修改"复杂任务处理流程"触发阈值
  - 内容：50+文件 → 5+文件或10+工具调用
  - 验证：Grep 确认新阈值
- [x] 2.2.3 OpenSpec 章节引入子代理说明
  - 内容：步骤2和步骤5的子代理使用说明
  - 验证：Grep 确认子代理说明存在
- [x] 2.2.4 添加子规范引用
  - 内容：在 AGENTS.md 中引用 `sub-agent-quality-management.md`
  - 验证：Grep 确认引用存在

### 2.3 修改 OpenSpec 子规范

- [x] 2.3.1 修改 `docs/project-rules/openspec-workflow.md`
  - 内容：步骤2（生成四文档）改为子代理并行生成；步骤5（实施）引入子代理分析
  - 验证：Grep 确认子代理步骤存在
- [x] 2.3.2 新增"上下文预算检查"步骤
  - 内容：步骤2开始前+步骤5每任务后+检查点前，检查上下文占用
  - 验证：Grep 确认预算检查步骤存在

### 2.4 修改 OpenSpec 命令文件

- [x] 2.4.1 修改 `.trae/commands/openspec.md`
  - 内容：步骤2和步骤5的子代理使用指导
  - 验证：Grep 确认子代理指导存在

### 2.5 更新索引

- [x] 2.5.1 更新 `docs/INDEX.md`
  - 内容：添加本 spec 条目 + 添加新子规范条目
  - 验证：Read 确认条目存在

## 3. 验证

### 3.1 文件层验证

- [x] 3.1.1 四文档完整性检查（必须章节齐全）
  - 验证：Read 每个文档 + Grep 确认必须章节
- [x] 3.1.2 AGENTS.md 修改后语法正确
  - 验证：Read 修改部分 + 确认 markdown 格式正确
- [x] 3.1.3 子规范文件创建成功
  - 验证：Read 确认文件存在 + 关键章节存在
- [x] 3.1.4 索引更新成功
  - 验证：Read docs/INDEX.md 确认条目存在

### 3.2 一致性验证

- [x] 3.2.1 AGENTS.md 与子规范内容一致
  - 验证：Grep 关键规则在两处一致
- [x] 3.2.2 OpenSpec 命令与子规范一致
  - 验证：Grep 步骤描述一致
- [x] 3.2.3 无规范冲突
  - 验证：检查"并发文件修改规范"等现有规范与新规则无矛盾

## 4. 文档同步

- [x] 4.1 更新 `docs/INDEX.md` 状态标记（🔄 设计中 → ✅ 设计完成 → 🔄 开发中 → ✅ 已完成）
- [x] 4.2 更新 `docs/project-flow/` 相关文档（如涉及模块结构变更）
- [x] 4.3 更新 `assets/updateLog.md`（本次为规范优化，非用户可感知变更，可不更新）

## 5. AOAdapt 日志

> 遇到问题时记录在此章节

### 2026-07-12 设计阶段

- **Action**：用户用 `/openspec` 命令提出"分析模型思考次数上限"需求
- **Observation**：初次分析跑偏，扯到 Claude/Trae 通用机制，用户纠正"这是你自己当前遇到的问题"
- **Adapt**：重新聚焦 GLM-5.2 在 Trae 平台自身的触发机制

- **Action**：提出 V1 方案（长输出写文件+强制子代理+分阶段 /compact+OpenSpec 分文档生成）
- **Observation**：用户质疑"你确定你说的优化真的能够缓解问题吗？深度分析并反省"
- **Adapt**：深度反省发现 V1 方案高估了"长输出写文件"和"分文档生成"的效果，没抓住"子代理是唯一真正有效手段"

- **Action**：提出 V2 方案（强制子代理+任务拆分到多次对话）
- **Observation**：用户纠正"你提到的开启新的对话，新对话就收费了呀，一次新对话一次钱"
- **Adapt**：V2 方案的"多次对话"会直接增加成本，完全背离"省钱"诉求。调整为 V3 方案

- **Action**：提出 V3 方案（强制子代理+禁止建议新对话）
- **Observation**：用户追问"如何让主代理监控子代理？如何保证子代理质量？与现有规范冲突吗？"
- **Adapt**：补充监控机制+质量保证+规范冲突处理，形成完整方案

- **Action**：用户确认 V3 方案符合预期，要求走 OpenSpec 流程落地
- **Observation**：网络问题导致用户消息延迟，但最终确认
- **Adapt**：开始走 OpenSpec 流程，生成四文档

### 2026-07-12 实施阶段

- **Action**：检查点1通过后，按 tasks.md 顺序执行实施
- **Observation**：上下文压缩恢复后，按 core-spec V2.1 要求主动读取 core-spec.md + 加载子规范（openspec-workflow.md + sub-agent-quality-management.md）
- **Adapt**：压缩恢复后严格遵循 V2.1 规范，输出双重验证清单 + 用户反馈清单

- **Action**：发现 OpenSpec 命令文件不在项目 `.trae/commands/` 目录，而在用户级别 `c:\Users\shiyq\.trae-cn\commands\openspec.md`
- **Observation**：项目 `.trae` 目录只有 documents/skills/specs 三个子目录，无 commands
- **Adapt**：修改用户级别命令文件，保持内容通用性（不引用项目特定规范路径）

- **Action**：tasks.md 中 "- [ ]" 替换为 "- [x]" 时丢失空格（"- [x]1.1" 而非 "- [x] 1.1"）
- **Observation**：replace_all 把 "- [ ] " (带空格) 替换为 "- [x]" (不带空格)
- **Adapt**：二次 replace_all 把 "- [x]" 替换为 "- [x] " (带空格) 修复格式

- **Action**：完成所有实施任务，验证全部通过
- **Observation**：文件层6项+一致性3项+无规范冲突，检查点2用户审核通过
- **Adapt**：进入检查点3最终验收
