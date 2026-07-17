# design.md — legado-skill-optimization-v2

> **文档类型**: ADR Y-Statement 决策文档
> **关联**: [README.md](./README.md) | [spec.md](./spec.md) | [tasks.md](./tasks.md)

---

## ADR-1: 采纳分层渐进方案（A+B 立即 + C+D 分阶段）

### Context（上下文）

用户反馈"非常不满意 skill 干活"。诊断发现 3 个 P0 + 3 个 P1 问题。历次 7+ OpenSpec 完成度普遍 5.6%-20%，最大陷阱是"大而全方案+实施率低"。

可选方案：
- A: 仅修错误知识（Layer A）
- B: 全面重构（A+B+C+D）
- C: 废弃重建
- D: 分层渐进（A+B 立即 + C+D 分阶段）

### Decision（决策）

采纳 D：分层渐进。

### Consequences（后果）

**正向**:
- 立即止血（A）+ 防止再发（B）解决用户最痛点
- C+D 分阶段独立验收，避免重蹈"声称完成≠实际生效"
- 改动可控，风险低

**负向**:
- C+D 推进期间仍存在架构臃肿
- 需要更多次检查点
- 用户需多次确认

**风险**: 用户可能因 C+D 拖延而不满 → 缓解：每层带量化验收

---

## ADR-2: 用"源码锚定"作为 references/ 写入门禁

### Context

cf-bypass.md 的错误建议存在已久，未被任何机制拦截。根因是 references/ 写入无源码验证要求。

可选方案：
- A: 新增自动化脚本批量校验所有现有 references
- B: 写入时强制要求 `source_ref: app/src/.../Xxx.kt#L行号` 字段
- C: 人工审查每次写入

### Decision

采纳 B + A 增量。

**B**: 写入门禁——新增 references 内容必须带 `source_ref:` 字段
**A 增量**: 现有 references 按引用频率排序，高优先补全 source_ref

### Consequences

**正向**:
- 错误建议写入前必须找到源码依据
- 错误经验可追溯到具体源码位置
- AI 检索时能验证建议可信度

**负向**:
- 增加写入成本
- 旧 references 需要批量补全
- 部分建议（如最佳实践）可能难以锚定具体源码行

**风险**: 写入成本上升导致经验反哺减少 → 缓解：只对涉及 loginUrl/loginCheckJs/WebView/cookie 等关键字段的建议强制要求 source_ref

---

## ADR-3: 合并 60+ 脚本为 5-6 个核心脚本

### Context

scripts/ 下 60+ 独立 .py 脚本，4 个 cleanup_*.py + 6 个 fix_*.py 功能重叠。完整 legado_client 包（FastAPI+Vue3+SQLAlchemy+Alembic）偏离"创建源"核心任务。

可选方案：
- A: 全部废弃，从零写 5-6 个
- B: 按功能分类合并为 5-6 个
- C: 保留现状，仅文档化
- D: 拆 legado_client 出去，scripts/ 下脚本合并

### Decision

采纳 D + B。

**D**: legado_client/ 拆为独立项目（迁移到 `tools/legado-source-manager/` 或归档到 `.archive/`）
**B**: scripts/ 下 60+ 脚本按功能合并为：
1. `create_source.py` — 创建：分析网站+生成JSON+JVM校验（吸收 generate-js-doc / deep-analyze-js / analyze_site）
2. `fix_source.py` — 修复：诊断+修复+验证（吸收 auto_fix_sources / deep_fix_search / fix_rule_articles / fix_search_failed / smart_fix / dom_fix）
3. `cleanup_sources.py` — 清理：死源/空壳/假成功（吸收 cleanup_dead_empty / cleanup_false_success / cleanup_unusable / batch_clean_dead_sources）
4. `debug_source.py` — 端到端调试（保留，已有）
5. `validate_source.py` — 验证（吸收 verify-decrypt / verify-image / verify-selector / verify-source / quick-verify / deep_verify）
6. `manage_sources.py` — 批量管理（吸收 batch_optimize / batch_device_debug / smart_dedup_v3 / smart_merge_v4 / deep_analysis）

### Consequences

**正向**:
- 文件数从 60+ 降至 6
- 功能边界清晰
- AI 检索效率提升

**负向**:
- 单文件可能较大（需用模块化设计）
- 现有调用方需更新引用
- 部分边缘场景功能可能丢失

**风险**: 合并引入 bug → 缓解：先备份原文件到 .archive/v2-pre-bak/scripts/，合并后用 test-data/ 跑回归

---

## ADR-4: legado_client 包拆为独立项目

### Context

legado_client/ 是完整的 FastAPI+Vue3+SQLAlchemy+Alembic 项目，约 3000+ 行代码。其功能（Web 管理界面、数据库迁移、设备管理）与 skill 核心任务"创建源"无关，导致：
- skill 体积膨胀
- 维护负担重
- AI 检索 references/ 时被 legado_client/ 干扰

可选方案：
- A: 拆为独立项目 `tools/legado-source-manager/`
- B: 归档到 `.archive/legado-client-snapshot/`
- C: 删除
- D: 保留在 skill 内但移到 skill 外的 `legado_client/`

### Decision

采纳 B（短期）+ A（长期）。

**B 短期**: v2 阶段先归档到 `.archive/legado-client-snapshot-20260717/`，skill 不再引用
**A 长期**: 后续单独建立 `tools/legado-source-manager/` 独立项目（不在本次 v2 范围内）

### Consequences

**正向**:
- skill 体积立即减少 3000+ 行
- AI 检索 references/ 不再被干扰
- 用户仍可从归档恢复使用

**负向**:
- Web 管理界面短期内不可用
- 已依赖 legado_client 的脚本（如 batch_device_debug）需更新
- 用户可能需要单独 clone 独立项目

**风险**: 用户当前依赖 Web 界面 → 缓解：归档前先用 AskUserQuestion 确认

---

## ADR-5: JVM 仿真器能力声明降级

### Context

AI_README.md 声称"JVM 覆盖率 85-90%"，但实际无法覆盖 WebView 系统组件、Activity 生命周期、Cookie 自动同步等真机行为。cf-bypass.md 错误未被 JVM 测试拦截即证明。

可选方案：
- A: 提升 JVM 能力，模拟 WebView（工作量大）
- B: 降级声明，明确边界
- C: 保持现状

### Decision

采纳 B。

**B**: 降级声明为：
- ✅ 覆盖：Rhino JS 引擎 / jsoup CSS / hutool 加密 / AnalyzeRule 规则解析
- ❌ 不覆盖：Android WebView 系统组件 / Activity 生命周期 / Cookie 自动同步 / 真机网络栈

### Consequences

**正向**:
- AI 不再误信"85-90% 覆盖"而忽略源码验证
- 边界清晰，可问责
- 引导 AI 在涉及 WebView 时强制走 Phase 0 源码验证

**负向**:
- JVM 仿真器可信度感知降低
- 涉及 WebView 的场景必须真机验证（成本高）

**风险**: AI 过度依赖真机测试 → 缓解：在 SKILL.md 中明确"涉及 WebView 字段才需真机，其他场景 JVM 仍可用"

---

## ADR-6: basic-memory 写入前源码验证

### Context

basic-memory 是经验索引层，写入的错误经验（如 cf-bypass.md 错误建议的索引）会反复强化错误。当前写入流程无源码验证要求。

可选方案：
- A: 所有写入前必须 Grep 验证源码
- B: 仅涉及关键字段（loginUrl/loginCheckJs/WebView/cookie）的写入需源码验证
- C: 写入后定期审查

### Decision

采纳 B。

**B**: 涉及 loginUrl / loginCheckJs / webView / cookie / header 等关键字段的经验笔记，写入前必须 Grep 验证源码一致性，并在 metadata 中带 `verified_against_source: app/src/.../Xxx.kt#L行号`

### Consequences

**正向**:
- 关键字段错误经验写入前被拦截
- 不增加非关键字段经验写入成本
- 可增量推进

**负向**:
- 关键字段写入成本上升
- 旧笔记需增量补全
- 非关键字段仍可能写入错误经验

**风险**: 旧错误经验未清理 → 缓解：本次 v2 Layer A 阶段先清理已知的 cf-bypass.md 错误经验对应笔记

---

## 决策矩阵汇总

| ADR | 决策 | 主要权衡 |
|-----|------|---------|
| ADR-1 | 分层渐进（A+B立即+C+D分阶段） | 立即止血 vs 一次性彻底 |
| ADR-2 | 源码锚定门禁 | 准确性 vs 写入成本 |
| ADR-3 | 合并 60+ 脚本为 6 个 | 可维护性 vs 合并风险 |
| ADR-4 | legado_client 归档 | 瘦身 vs Web 界面不可用 |
| ADR-5 | JVM 定位降级 | 边界清晰 vs 可信度感知降低 |
| ADR-6 | basic-memory 关键字段源码验证 | 错误拦截 vs 写入成本 |
