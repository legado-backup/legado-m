---
name: legado-workflow-auditor
description: Legado 书源/订阅源工作流审计器。在 legado-source-creator 任务完成后审计 Phase 执行证据的完整性，检查 basic-memory 中的执行记录，输出审计报告。
---

# Legado 工作流审计器

> 在 `legado-source-creator` Skill 任务完成后，审计 Phase 1/3/5 执行证据的完整性。

## 触发条件

- `legado-source-creator` Skill 的书源/订阅源创建/修复/优化任务完成后
- 用户明确要求审计时

## 审计流程

### 步骤1：确认任务信息

优先从调用方传入参数获取 source_name，降级为向用户确认：
- 源名称（source_name）— 获取顺序：调用方传入参数 > 上下文提取 > 向用户确认
- 任务类型（创建/修复/优化）

### 步骤2：搜索 basic-memory 执行证据

```
mcp_basic-memory_search_notes(
    query="执行证据: {源名称}",
    search_type="hybrid",
    project="legado",
    tags=["execution-log"],
    page_size=20
)
```

### 步骤3：逐项检查

| 检查项 | 字段来源 | 检查方法 | 通过条件 | 失败处理 |
|--------|---------|---------|---------|---------|
| Phase 1 执行证据存在 | metadata.basic_memory_search | search_notes 找到 Phase 1 记录 | 找到且 basic_memory_search ∈ {"命中","降级"} | 标记 WARN，建议补写 |
| Phase 3 执行证据存在 | metadata.test_coverage | search_notes 找到 Phase 3 记录 | 找到且 test_coverage > 0 | 标记 WARN，建议补写 |
| Phase 5 执行证据存在 | metadata.dual_write | search_notes 找到 Phase 5 记录 | 找到且 dual_write ∈ {"完成","部分完成"} | 标记 WARN，建议补写 |
| 陷阱检查已执行 | metadata.trap_check | Phase 1 记录中读取 | 值为"已检查" | 标记 WARN |
| 测试覆盖率 > 0 | metadata.test_coverage | Phase 3 记录中读取 | 数值 > 0 | 标记 ERROR |
| 经验反哺完成 | metadata.dual_write | Phase 5 记录中读取 | dual_write ∈ {"完成","部分完成"} | 标记 WARN |
| 代码进化已执行 | metadata.jvm_evolution_needed → metadata.code_evolution_executed | Phase 3 识别需求 → Phase 5 执行 | 如 needed=true 则必须 executed=true | 标记 ERROR |
| Phase 完成标志输出 | 上下文搜索 [PHASEX_COMPLETE] | 搜索上下文 | 3个标志都存在 | 标记 WARN |

**代码进化检查路径**（检查项"代码进化已执行"的详细步骤）：
1. 从 Phase 3 执行证据中读取 `metadata.jvm_evolution_needed`，若为 `false` 则该项标记 N/A
2. 若 `jvm_evolution_needed=true`，搜索 basic-memory 查找进化记录：
   ```
   mcp_basic-memory_search_notes(
       query="代码进化: {源名称}",
       search_type="hybrid",
       project="legado",
       tags=["jvm-evolution"],
       page_size=5
   )
   ```
3. 验证 Phase 5 执行证据中 `metadata.code_evolution_executed=true`
4. 若 `jvm_evolution_needed=true` 但未找到进化记录或 `code_evolution_executed≠true`，标记 ERROR

### 步骤4：输出审计报告

```
## 审计报告：{源名称}

**审计版本**：v1.0 | **审计者**：legado-workflow-auditor | **审计日期**：{YYYY-MM-DD}

| 检查项 | 状态 | 详情 |
|--------|------|------|
| Phase 1 执行证据 | ✅/❌ | {详情} |
| Phase 3 执行证据 | ✅/❌ | {详情} |
| Phase 5 执行证据 | ✅/❌ | {详情} |
| 陷阱检查 | ✅/❌ | {详情} |
| 测试覆盖率 | ✅/❌ | {详情}% |
| 经验反哺 | ✅/❌ | {详情} |
| 代码进化 | ✅/❌/N/A | {详情} |
| Phase 完成标志 | ✅/❌ | {详情} |

### 总评
- 有效项数 = 8 - N/A 项数（如 7/8 通过且 1 项 N/A 时显示 7/7 全通过）
- 通过项: N/{有效项数}
- 状态: ✅ 审计通过（全部通过）/ ⚠️ 部分通过（有 WARN）/ ❌ 审计失败（有 ERROR）

### 建议（按未通过项结构化输出，无未通过项则省略本节）

对每个未通过项，按以下模板输出：

- **[检查项名称]** ❌ERROR/⚠️WARN
  - 问题描述：{具体缺失或不符合的内容}
  - 修复动作：{建议的补写/修复操作}
  - 优先级：ERROR（必须修复，阻断交付）/ WARN（建议修复，不阻断）
```

### 步骤5：写入审计报告到 basic-memory

```
mcp_basic-memory_write_note(
    title="审计报告: {源名称}",
    content="{审计报告内容}",
    directory="audit-reports/",
    project="legado",
    note_type="audit-report",
    tags=["audit", "{源名称}"],
    metadata={
        "source_name": "{源名称}",
        "audit_result": "通过/部分通过/失败",
        "audit_date": "{YYYY-MM-DD}"
    }
)
```

## 降级路径（basic-memory 不可用时，三步统一）

1. **检测不可用**：调用 `mcp_basic-memory_search_notes`，若抛出异常或超时，判定为不可用
2. **替代查询**：检查上下文中的 [PHASEX_COMPLETE] 标志 + 用 Glob 验证 `output/book/` 或 `output/rss/` 下是否存在输出文件（`*.json`）
3. **标记待验证**：输出简化版审计报告，每项标注数据来源（✅(上下文) / ✅(output目录) / ❌(缺失)），并标记"需 basic-memory 验证"

**简化版审计报告格式**（降级时使用）：

```
## 审计报告（降级模式）：{源名称}

**审计版本**：v1.0 | **审计者**：legado-workflow-auditor | **审计日期**：{YYYY-MM-DD}
⚠️ basic-memory 不可用，以下结果基于上下文和 output 目录，需后续 basic-memory 验证。

| 检查项 | 状态 | 数据来源 | 详情 |
|--------|------|---------|------|
| Phase 1 执行证据 | ✅/❌ | 上下文/output目录 | {详情} |
| Phase 3 执行证据 | ✅/❌ | 上下文/output目录 | {详情} |
| Phase 5 执行证据 | ✅/❌ | 上下文 | {详情} |
| 陷阱检查 | ✅/❌ | 上下文 | {详情} |
| 测试覆盖率 | ✅/❌ | output目录 | {详情} |
| 经验反哺 | ✅/❌ | 上下文 | {详情} |
| 代码进化 | ✅/❌/N/A | 上下文 | {详情} |
| Phase 完成标志 | ✅/❌ | 上下文 | {详情} |

### 总评
- 有效项数 = 8 - N/A 项数
- 通过项: N/{有效项数}
- 状态: ✅ 审计通过 / ⚠️ 部分通过 / ❌ 审计失败 / ⚠️ 需 basic-memory 验证
```

## 与 legado-skill-auditor 的关系

| 维度 | workflow-auditor | skill-auditor |
|------|-----------------|---------------|
| 审计对象 | 单次任务执行证据 | Skill 本身质量 |
| 触发时机 | 任务完成后自动/手动 | 用户要求时 |
| 检查项数 | 8 项 | ~30 项（分层） |
| 输出 | 审计报告（通过/失败） | 审查报告（问题清单+修复建议） |
| 调用顺序 | source-creator 之后 | 独立调用 |
