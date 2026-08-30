# tasks.md

## 第一批：格式压缩 + AI主动使用强化 + openspec简化

- [ ] 1.1 user_rules.md 压缩（297→200）+ 增加AI主动使用强化首行（对话开始→Read core-spec.md→检查触发条件→加载子规范→开始工作）+ 增加执行锚点（AskUserQuestion响应后第一动作：写入项目记忆，非可选，未写入禁止继续工作）
- [ ] 1.2 core-spec.md 压缩（1041→900）+ AskUserQuestion规则集中描述（强化执行顺序：写入项目记忆是第一优先级非可选步骤）+ 合并表格 + 增加触发条件自查清单 + 子规范表改强制措辞
- [ ] 1.3 output-safety.md 压缩（976→750）+ 去emoji/表格/代码块 + 保留思考铁律3条+黑名单+处理流程+违禁词+预防性搜索+中断恢复
- [ ] 1.4 context-recovery.md 压缩（928→850）+ 压缩恢复闭环（7个关键环节全包含：四件套+主动读取文件+双重验证清单+AskUserQuestion响应+反馈持久化+任务权威源+经验持久化）+ 增加执行检查点（执行前自检：是否已写入项目记忆？未写入则禁止继续工作）
- [ ] 1.5 openspec-workflow.md 大幅简化（784→150）+ 改为引用提示（用户用/openspec指令，文字提到时Read commands/openspec.md）
- [ ] 1.6 complex-task.md 压缩（679→450）+ 去表格/代码块/emoji
- [ ] 1.7 budget-management.md 压缩（597→400）+ 去表格
- [ ] 1.8 coding-philosophy.md 压缩（576→400）+ 去表格/代码块
- [ ] 1.9 concurrent-editing.md 压缩（443→300）+ 去表格
- [ ] 1.10 danger-ops.md 压缩（433→300）+ 去表格

## 第二批：验证

- [ ] 2.1 字符数验证（总字符≤5000）
- [ ] 2.2 格式验证（无emoji/表格标记/代码块标记）
- [ ] 2.3 内容完整性验证（逐文件Read确认核心规则保留）
- [ ] 2.4 压缩恢复闭环验证（对照7个关键环节逐项确认）
- [ ] 2.5 AI主动使用验证（新对话测试确认AI主动Read core-spec.md）
