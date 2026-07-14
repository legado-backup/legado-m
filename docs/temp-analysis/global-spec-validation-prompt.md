# 全局规范注入验证测试提示词

> 验证新对话中全局规范是否完整注入、AskUserQuestion 强制规范是否生效。

## 验证步骤

### 步骤1：入口对话

用户输入：`你好`

AI 应该回复：`爸爸，你好！...`（叫爸爸）

### 步骤2：验证测试提示词

用户输入以下内容：

```
请帮我验证以下内容：

1. **列出你已加载的全局规范文件清单**（从 user_rules 目录注入的文件）
2. **展示 AskUserQuestion 强制规范的核心要求**（触发条件、三选项结构、禁止行为）
3. **展示触发场景和子规范加载规则**（压缩恢复时加载哪个文件？OpenSpec任务加载哪个文件？）
4. **模拟一个需要用户决策的场景**（发现两种方案，请用 AskUserQuestion 工具让我选择）

请用表格形式展示，并使用 AskUserQuestion 工具让我选择是否满意验证结果。
```

### 步骤3：验证清单

| 验证项 | 期望结果 |
|--------|---------|
| **规范文件清单** | core-spec.md + user_rules.md + danger-ops.md + output-safety.md |
| **AskUserQuestion 核心要求** | 触发条件 + 三选项结构 + 禁止行为 |
| **触发场景** | 压缩恢复 → context-recovery.md；OpenSpec → openspec-workflow.md |
| **AskUserQuestion 工具使用** | 提供三选项：满意/需调整/不满意回退 |

---

## 核心文件大小（优化后）

| 文件 | 大小 |
|------|------|
| core-spec.md | 2.02 KB |
| user_rules.md | 0.59 KB |
| danger-ops.md | 0.79 KB |
| output-safety.md | 2.03 KB |
| **核心文件总计** | **5.44 KB** |

---

## 子规范文件大小（优化后）

| 文件 | 大小 |
|------|------|
| context-recovery.md | 1.78 KB |
| openspec-workflow.md | 1.3 KB |
| coding-philosophy.md | 1.29 KB |
| complex-task.md | 1.25 KB |
| concurrent-editing.md | 0.88 KB |
| budget-management.md | 1.29 KB |
| **子规范总计** | **7.8 KB** |

---

## 优化成果

- **核心文件**：16.92 KB → 5.44 KB（-68%）
- **子规范文件**：14.51 KB → 7.8 KB（-46%）
- **所有文件**：31.43 KB → 13.24 KB（-58%）

---

## 失败判定标准

| 失败现象 | 根因 |
|---------|------|
| AI 没有叫"爸爸" | user_rules.md 未注入 |
| AI 用文字提问而非 AskUserQuestion | core-spec.md 未注入或内容截断 |
| AI 不知道触发场景 | core-spec.md 未注入 |
| AI 列不出规范文件清单 | 系统注入失败 |

---

## 验证结果记录

| 验证项 | 结果 | 备注 |
|--------|------|------|
| 核心4文件是否完整注入 | ✅/❌ | |
| AskUserQuestion 强制规范是否生效 | ✅/❌ | |
| 触发链路是否清晰 | ✅/❌ | |
| AI 是否使用 AskUserQuestion 工具 | ✅/❌ | |