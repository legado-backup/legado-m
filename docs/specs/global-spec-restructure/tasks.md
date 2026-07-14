# tasks.md - 全局规范重组

## 1. 准备工作
- [x] 1.1 确认系统注入机制（注入顺序=修改时间从旧到新，大小限制约12KB）
- [x] 1.2 子代理验证规则加载（子代理与主代理规则加载相同）
- [x] 1.3 更新设计文档（spec.md/design.md/tasks.md）
- [x] 1.4 备份 core-spec.md 到 .zip

## 2. 全局规范拆分（从 core-spec.md 拆分）
- [x] 2.1 备份 core-spec.md → core-spec-backup-20260713.zip
- [x] 2.2 创建 context-recovery.md（3,726 bytes）
- [x] 2.3 创建 output-safety.md（精简到1,940 bytes，强化违禁词规范）
- [x] 2.4 创建 coding-philosophy.md（2,825 bytes）
- [x] 2.5 删除旧 core-spec.md（27.9KB）
- [x] 2.6 重建 core-spec.md（精简到993 bytes，仅索引）
- [x] 2.7 子代理验证注入状态（旧状态2/5注入，系统注入在对话开始时固定，需新对话验证）

## 3. AGENTS.md 通用内容迁移
- [x] 3.1 创建 openspec-workflow.md（2,591 bytes）
- [x] 3.2 创建 complex-task.md（2,018 bytes）
- [x] 3.3 创建 concurrent-editing.md（2,057 bytes）
- [x] 3.4 创建 budget-management.md（1,822 bytes）
- [x] 3.5 子代理验证注入状态（第二批，旧状态确认，新状态需新对话验证）

## 4. AGENTS.md 瘦身
- [x] 4.1 删除 V2.1 硬约束段（保留项目子规范表）
- [x] 4.2 删除复杂任务五阶段段（迁移到 complex-task.md）
- [x] 4.3 删除输出预算管理段（迁移到 budget-management.md）
- [x] 4.4 删除 OpenSpec 工作流段（迁移到 openspec-workflow.md）
- [x] 4.5 删除并发文件修改段（迁移到 concurrent-editing.md）
- [x] 4.6 添加全局规范引用索引（11个文件清单）
- [x] 4.7 验证 AGENTS.md 只含项目特定内容（533行→354行，-33.6%）

## 5. 最终验证
- [x] 5.1 子代理验证注入状态（旧状态确认，新状态需新对话验证）
- [x] 5.2 验证 AGENTS.md 只含项目特定内容（git diff: 32insertions/140deletions）
- [x] 5.3 验证全局规范文件总大小（核心5文件9.42KB < 10.5KB目标）
- [x] 5.4 更新 docs/INDEX.md（spec 状态，添加global-spec-restructure条目）
- [ ] 5.5 更新 updateLog.md（不适用：全局规范重组非代码变更）

## 6. 检查点
- [x] 6.1 检查点1：用户审查设计（通过）
- [ ] 6.2 检查点2：用户审核实施（当前）
- [ ] 6.3 检查点3：用户最终验收

## 7. 新对话验证（用户要求）
- [x] 7.1 生成测试提示词文档（test-prompt.md）
- [ ] 7.2 用户开新对话验证注入状态
- [ ] 7.3 对比验证结果报告

## AOAdapt 日志

### 2026-07-13 检查点1"需调整"
- Action: 提出"双轨保障方案"
- Observation: 用户反馈"得先弄清楚trae cn的工作原理"
- Adapt: 研究系统注入机制，调整为多文件拆分策略

### 2026-07-13 用户反馈"拆分而非整合"
- Action: 提出"精简 core-spec.md 到 ≤200行"
- Observation: 用户反馈"为什么不想着是拆分多个文件呢"
- Adapt: 颠覆整合策略，改为多文件拆分

### 2026-07-13 用户反馈"去掉元信息"
- Action: 设计文件内容时包含版本号
- Observation: 用户反馈"规范文件里面不要有额外的信息"
- Adapt: 所有规范文件去掉元信息

### 2026-07-13 子代理验证发现注入限制
- Action: 创建4个新文件，总大小25KB
- Observation: 子代理验证发现新文件全部被省略（超系统注入上限）
- Adapt: 精简大文件（rule 9.2KB→3.1KB, output-safety 4KB→1.9KB, core-spec 1.7KB→0.9KB），核心5文件合计9.42KB

### 2026-07-13 系统注入时机发现
- Action: 子代理验证注入状态
- Observation: 子代理看到旧版rule（含成本对比表），证明系统注入在对话开始时固定
- Adapt: 生成test-prompt.md，用户需开新对话验证新状态
