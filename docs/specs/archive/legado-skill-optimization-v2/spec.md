# spec.md — legado-skill-optimization-v2

> **关联**: [README.md](./README.md) | [design.md](./design.md) | [tasks.md](./tasks.md)

---

## 1. 需求陈述

### 1.1 用户原始诉求

> "但是我非常不满意生成书源订阅源skill干活！你需要深度分析一下为什么，如何优化他.trae\skills\legado-source-creator"

### 1.2 需求拆解

| ID | 需求 | 类型 | 优先级 |
|----|------|------|--------|
| R1 | 深度分析"为什么 skill 干活不行" | 分析 | P0 |
| R2 | 修复 cf-bypass.md 的错误 loginUrl 建议 | 修复 | P0 |
| R3 | 修复 SKILL.md 陷阱#54 的错误描述 | 修复 | P0 |
| R4 | 审查并修复其他含错误 @js:loginUrl 模式的文件（11个） | 修复 | P0 |
| R5 | 强化"写入 references/ 前必须源码验证"门禁 | 改造 | P0 |
| R6 | 修正 JVM 仿真器能力声明（不能覆盖 WebView 层） | 改造 | P0 |
| R7 | 合并 60+ 脚本为 5-6 个核心脚本 | 重构 | P1 |
| R8 | 拆分 legado_client 包为独立项目或归档 | 重构 | P1 |
| R9 | 清理 reports/ 历史包袱 | 清理 | P1 |
| R10 | 改造 basic-memory 经验引擎（写入前源码验证） | 改造 | P1 |

---

## 2. 范围（Scope）

### 2.1 In Scope

- 修复 `.trae/skills/legado-source-creator/` 下所有错误建议
- 强化 SKILL.md 的 5 阶段闭环工作流门禁
- 瘦身 scripts/ 目录
- 改造 basic-memory 写入流程

### 2.2 Out of Scope

- 修改 Legado 应用源码（`app/src/main/...`）
- 新增 JVM 仿真器能力
- 新增书源模板
- Web 管理界面增强

---

## 3. 验收标准（Acceptance Criteria）

### 3.1 功能性验收

| AC ID | 验收点 | 验证方法 | 必通过 |
|-------|--------|---------|--------|
| AC1 | cf-bypass.md 不再推荐 `loginUrl: @js:java.webView(...)` | Grep `@js:java\.webView\(null` 在 cf-bypass.md 中无命中 | ✅ |
| AC2 | SKILL.md 陷阱#54 描述正确（loginUrl 不能用 @js: 形式） | Read SKILL.md 陷阱#54 行确认描述已修正 | ✅ |
| AC3 | SKILL.md:305 源码引用改为 WebViewLoginFragment.kt | Read 确认 | ✅ |
| AC4 | 11 个含错误模式文件已审查并修正或标注过时 | Grep 命中数 ≤2 且均为"已知过时"标注 | ✅ |
| AC5 | references/ 中所有 loginUrl 建议带 `source_ref:` 字段 | Grep `source_ref:` 在 references/ 下命中数 ≥ references 中 loginUrl 出现数 | ✅ |
| AC6 | SKILL.md 中 JVM 定位降级为"规则引擎层覆盖85-90%，不覆盖 WebView/Activity/Cookie 同步" | Read 确认 | ✅ |
| AC7 | scripts/ 下 .py 文件数 ≤10 | `ls scripts/*.py | wc -l` ≤10 | ✅ |
| AC8 | reports/ 已归档或清空 | `ls scripts/reports/*.json | wc -l` ≤5 | ✅ |
| AC9 | basic-memory 写入流程文档包含"源码验证前置"步骤 | Read references/basic-memory-usage.md 确认 | ✅ |

### 3.2 非功能性验收

| AC ID | 验收点 | 验证方法 |
|-------|--------|---------|
| AC10 | 每条任务带"验证证据"字段 | tasks.md 全部任务带 `验证证据:` 字段 |
| AC11 | 改动前已备份原文件 | `.archive/v2-pre-bak/` 目录存在且包含备份 |
| AC12 | 不删除 Legado 应用源码 | git diff 显示 `app/src/` 无变更 |

---

## 4. 证据链

### 4.1 触发证据（用户反馈）

- 用户原文："但是我非常不满意生成书源订阅源skill干活！"
- 上轮任务结果：订阅源"优化"实际 0 字段有效变更（因 cf-bypass.md 建议错误被源码证伪）

### 4.2 诊断证据（深度分析）

完整诊断报告：[docs/temp-analysis/skill-deep-diagnosis.md](../../temp-analysis/skill-deep-diagnosis.md)

#### 4.2.1 P0-1 核心知识错误证据

| 证据 | 位置 | 结论 |
|------|------|------|
| 错误建议 | cf-bypass.md:37 | 推荐 `loginUrl: @js:java.webView(...)` |
| 错误扩散 | Grep `loginUrl.*@js:\|java\.webView\(null` 命中 11 个文件 | 错误已扩散 |
| 源码真相 | WebViewLoginFragment.loadUrl() | 直接把 loginUrl 当 URL 加载，不识别 @js: |

#### 4.2.2 P0-2 5阶段闭环失效证据

| 阶段 | 失效原因 |
|------|---------|
| Phase 1 经验搜索 | 搜索"CF"会命中错误的 cf-bypass.md，反向强化 |
| Phase 3 JVM测试 | 无法模拟 WebView 系统组件，测不出 loginUrl 错误 |
| Phase 4 源码深挖 | 触发条件"测试失败"未达成（JVM 测不出），永不触发 |
| Phase 5 经验反哺 | 双写只保证一致性，不保证正确性 |

#### 4.2.3 P0-3 工程化过度证据

| 维度 | 数据 |
|------|------|
| 独立 .py 脚本 | 60+ 个 |
| 完整 Python 包 | legado_client/（FastAPI+Vue3+SQLAlchemy+Alembic） |
| 历史包袱 | reports/ 下 30+ JSON |
| 功能重复 | 4 个 cleanup_*.py + 6 个 fix_*.py 重叠 |

### 4.3 历次 OpenSpec 失效证据

| OpenSpec | 声称完成度 | 实际失效 |
|---------|----------|---------|
| legado-skill-optimization | 20% | 268 任务大部分未完成 |
| legado-skill-unified-redesign | 5.6% | 已归档 |
| legado-skill-v2-rebuild | 90%+ | 声称完成但 cf-bypass.md 错误仍在 |
| skill-usability-optimization | 未开始 | 8 方向均未实施 |

---

## 5. Alternatives Considered

### 5.1 替代方案 A：仅修复错误知识（Layer A）

**描述**: 只修 cf-bypass.md / 陷阱#54 / 11 个错误文件，不动架构。

**优点**:
- 工作量最小，立即可见效
- 风险低，改动可控

**缺点**:
- 治标不治本：门禁不强化，下次还会再写入错误建议
- 用户已表态"非常不满意"，仅修复可能不足

**结论**: 不采纳（但作为 Layer A 阶段实施内容）

### 5.2 替代方案 B：全面重构（Layer A+B+C+D）

**描述**: 4 层全部彻底重构，包括拆 legado_client / 合并 60+ 脚本 / 改造经验引擎。

**优点**:
- 一次彻底解决问题
- 长期可维护性最高

**缺点**:
- 工作量大，可能再次陷入"实施率低"陷阱
- 风险高，可能引入新错误
- 用户历史教训：历次大而全方案完成度普遍 5.6%-20%

**结论**: 部分采纳。Layer A+B 立即做，C+D 分阶段推进且每阶段独立验收

### 5.3 替代方案 C：废弃现有 skill 重建

**描述**: 删除现有 skill，从零重建一个极简版。

**优点**:
- 无历史包袱
- 可彻底重新设计

**缺点**:
- 浪费已有正确部分（如部分 trap 速查、references 中正确内容）
- 用户已有大量基于现有 skill 的经验沉淀（basic-memory）
- 风险最高

**结论**: 不采纳。在现有基础上修复+瘦身

### 5.4 采纳方案：分层渐进（Layer A+B 立即 + C+D 分阶段）

**理由**:
- 立即止血（A）+ 防止再发（B）→ 解决用户最痛的问题
- 架构瘦身（C）+ 经验引擎改造（D）→ 提升长期可维护性
- 每层独立验收，避免"声称完成≠实际生效"

---

## 6. Drawbacks

### 6.1 短期 Drawbacks

| D ID | 缺点 | 缓解措施 |
|------|------|---------|
| D1 | 合并脚本可能丢失某些边缘场景功能 | 先备份到 .archive/v2-pre-bak/，合并后对比功能矩阵 |
| D2 | 拆 legado_client 后 Web 界面短期内不可用 | 拆为独立项目后保留 README 指引，用户可单独 clone |
| D3 | 改造 basic-memory 写入流程后，旧经验笔记可能不带 source_ref | 增量补全，不强制一次性补全所有旧笔记 |

### 6.2 长期 Drawbacks

| D ID | 缺点 | 缓解措施 |
|------|------|---------|
| D4 | "源码锚定"要求增加写入成本 | 提供标准化模板，AI 按格式填写 |
| D5 | "强制验证"可能拖慢经验反哺速度 | 优先验证高频引用的 references，低频的延后处理 |

---

## 7. 风险与依赖

### 7.1 风险

| R ID | 风险 | 概率 | 影响 | 缓解 |
|------|------|------|------|------|
| R1 | 修复 cf-bypass.md 后引入新错误 | 中 | 高 | 改动后立即用源码验证 |
| R2 | 合并脚本破坏现有依赖 | 中 | 中 | 先用 grep 找出所有 import 关系 |
| R3 | 用户在实施过程中改变需求 | 低 | 中 | 每层结束用 AskUserQuestion 确认 |

### 7.2 依赖

- 无外部依赖（不修改 Legado 应用源码）
- 依赖现有 basic-memory MCP 可用
- 依赖现有 legado-jvm.jar 可用（仅用于对比验证，不修改）
