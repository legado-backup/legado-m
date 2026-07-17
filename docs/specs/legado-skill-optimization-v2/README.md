# legado-skill-optimization-v2

> **OpenSpec ID**: legado-skill-optimization-v2
> **启动日期**: 2026-07-17
> **触发**: 用户反馈"非常不满意生成书源订阅源skill干活"，要求深度分析"为什么"和"如何优化"
> **诊断报告**: [docs/temp-analysis/skill-deep-diagnosis.md](../../temp-analysis/skill-deep-diagnosis.md)

---

## 1. 上下文（Why Now）

### 1.1 触发事件

上轮订阅源优化任务中，skill 推荐的 CF 绕过配置：
```json
{
  "loginUrl": "@js:java.webView(null, source.sourceUrl, null, false);"
}
```
被源码验证为**致命错误**——[WebViewLoginFragment.loadUrl()](../../../app/src/main/java/io/legado/app/ui/login/WebViewLoginFragment.kt) 不识别 `@js:` 形式，直接把 loginUrl 当 URL 加载。整个"优化"过程实际 0 字段有效变更。

### 1.2 历次 OpenSpec 失效证据

| OpenSpec | 声称完成度 | 实际失效证据 |
|---------|----------|------------|
| legado-skill-optimization | 20% | tasks.md 中 268 项任务大部分未完成 |
| legado-skill-unified-redesign | 5.6% | 已归档，未实际执行 |
| legado-skill-v2-rebuild | 90%+ | 声称完成但 cf-bypass.md 错误仍存在 → "声称完成≠实际生效" |
| skill-core-capability-rebuild | 多数 | JVM 保真度提升但无法覆盖 WebView 层 |
| skill-usability-optimization | 未开始 | 8 个方向均未实施 |

### 1.3 根本失效模式

1. **写文档不做**：方案详尽但实施率低
2. **声称完成≠实际生效**：未做源码验证就标记完成
3. **大而全方案**：每次都重新设计三层架构，不聚焦具体问题
4. **无验证门禁**：写入 references/ 的建议不要求源码可追溯

---

## 2. 目标（Goals）

### 2.1 核心目标

**让 skill 在下一次创建/修复源时实际可用，而非再次误导 AI。**

### 2.2 量化验收

| 维度 | 当前状态 | v2 目标 |
|------|---------|---------|
| references/ 错误建议 | ≥1 致命错误（cf-bypass.md） | 0 致命错误（每条带源码锚定） |
| 5阶段闭环实际执行率 | <30%（声称 90%） | ≥80%（每阶段带验证证据） |
| 核心脚本数 | 60+ | ≤10（核心 5-6，辅助 ≤4） |
| legado_client 包定位 | 嵌入 skill 内 | 拆为独立项目或归档 |
| reports/ 历史包袱 | 30+ JSON | 归档至 .archive/ 或删除 |

---

## 3. 范围（Scope）

### 3.1 In Scope（本次必做）

1. **Layer A 错误知识纠正**：cf-bypass.md / SKILL.md 陷阱#54 / 11 个错误模式文件
2. **Layer B 门禁强化**：新增 Phase 0 源码验证 / JVM 定位降级 / references 源码锚定字段
3. **Layer C 架构瘦身**：脚本合并 / legado_client 拆分 / reports 清理
4. **Layer D 经验引擎改造**：写入前源码验证 / 错误经验撤销机制

### 3.2 Out of Scope（本次不做）

1. 重写 Legado 源码（v2 只读源码，不改源码）
2. 新增 JVM 仿真器能力（v2 仍依赖现有 legado-jvm.jar）
3. Web 管理界面增强（legado_client 拆出后另行处理）
4. 新增书源模板（v2 聚焦修复，不新增模板）

### 3.3 与历次 OpenSpec 的关系

- **继承**：legado-skill-v2-rebuild 的 5阶段闭环工作流（已实施部分保留）
- **修正**：本次诊断发现的 P0 致命问题（cf-bypass.md 错误、JVM 定位不实、5 阶段闭环失效）
- **不重复**：不再做"三层架构重设计""95% 保真度"等大而全方向（历次已证明无效）

---

## 4. 设计原则（Principles）

1. **小而精**：本次 v2 只解决诊断报告中的 3 个 P0 + 3 个 P1，不扩散
2. **强制验证**：每条任务必须带"验证证据"字段，未通过验证不得标记完成
3. **源码锚定**：所有 references/ 中的建议必须可追溯到 `app/src/.../Xxx.kt#L行号`
4. **可回滚**：每个改动先备份原文件到 `.archive/v2-pre-bak/`
5. **不声称完成**：完成 ≠ 标记 done，必须有源码验证截图或脚本输出证据

---

## 5. 文档导航

| 文档 | 用途 |
|------|------|
| [README.md](./README.md)（本文件） | 入口+背景+目标+范围 |
| [spec.md](./spec.md) | 需求+验收标准+证据链+Alternatives+Drawbacks |
| [design.md](./design.md) | ADR Y-Statement 决策文档 |
| [tasks.md](./tasks.md) | 分阶段任务清单（每条带验证证据字段） |
| [../../temp-analysis/skill-deep-diagnosis.md](../../temp-analysis/skill-deep-diagnosis.md) | 深度诊断报告（输入） |

---

## 6. 检查点

| 检查点 | 时机 | 验收方式 |
|--------|------|---------|
| CP1 设计审查 | 设计文档完成后 | AskUserQuestion 三选项 |
| CP2 实施审核 | Layer A+B 完成后 | AskUserQuestion + 源码验证证据 |
| CP3 最终验收 | 全部完成后 | AskUserQuestion + 端到端测试 |
