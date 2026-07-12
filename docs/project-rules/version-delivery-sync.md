# 版本交付同步规范（version-delivery-sync）

> **任何涉及代码变更的任务完成后，必须同步更新 `assets/updateLog.md`。禁止只改代码不写更新日志！**
>
> **触发场景**：任何代码变更任务（新功能/Bug修复/优化/重构）完成后
> **来源**：从 AGENTS.md 提取为独立子规范

## 同步清单

| 变更类型 | 必须同步的文件 | 说明 |
|----------|--------------|------|
| **任何代码变更** | `app/src/main/assets/updateLog.md` | 顶部追加日期条目，写明用户可感知的变更内容 |
| **文档变更** | `docs/INDEX.md` | 更新 spec 状态标记 |
| **架构变更** | `docs/project-flow/` 相关文档 | 同步架构说明 |
| **Skill 变更** | `.trae/skills/` 相关 SKILL.md | 同步能力说明 |

## updateLog.md 格式

```markdown
**YYYY/MM/DD**
- 变更说明1（面向用户，非技术细节）
- 变更说明2
```

**条目位置**：追加在 `## cronet版本:` 行之后、已有条目之前。

**内容原则**：
- 面向用户，用通俗语言描述可感知的变化
- 而非内部技术术语
- 一个变更点一条，不合并

## 更新时机

> **编译前更新**，不是交付阶段！

- 在代码变更完成、准备编译前，先更新 updateLog.md
- 然后再执行编译命令
- 禁止在交付阶段才补写 updateLog.md

## 反模式

❌ 改代码不写 updateLog.md
❌ updateLog.md 只写"优化代码，修复问题"无具体内容
❌ 新功能上线但用户不知道
❌ tasks.md 全部完成但 updateLog.md 未更新
❌ 在交付阶段才补写 updateLog.md（应在编译前）
