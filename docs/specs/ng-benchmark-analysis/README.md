# ng-benchmark-analysis — 阅读NG（legado_NG）深度对标调研

> 状态：✅ 设计完成（2026-08-30 检查点 1 经五轮审查验收通过；用户裁决**P0 安全加固先行**，各分期实施按 migration-designs 另立实施 spec 推进）
> 生成日期：2026-08-30

## 功能概述

对最新开源阅读延伸版本 **阅读NG（Next Generation Legado，`joestar817/legado_NG`）** 进行源码级深度对标分析。NG 与本项目同源（均 fork 自 Luoyacheng/legado-E 阅读Sigma），是其 fork 网络中演进最活跃、功能差异最大的兄弟分支（65 stars，最新版 `3.26.082815`，2026-08-28 发布，领先上游 224+ 提交）。

调研回答三个问题：
1. NG 比本项目强在哪？
2. 哪些功能值得参考学习？
3. 值得迁移的功能清单及优先级。

## 核心结论（速览）

| 能力域 | NG 优势 | 迁移价值 |
|--------|---------|----------|
| AI 体系 | 供应商抽象层（3 协议×12 家预设）、MCP 服务端（书架/书源开放给外部 AI 客户端）、上下文压缩、AI 净化/扫书、内置技能包体系 | ⭐⭐⭐⭐⭐ 高价值差异化能力 |
| 听书体系 | AI 分镜角色路由多语音 TTS（五级路由+情绪表演指导）、Compose 播放器+6 套动效、跨章无缝播放 | ⭐⭐⭐⭐ 高（可先迁非 AI 部分） |
| 视觉体系 | 液态玻璃设计系统（AGSL 折射+色散，改造自 AndroidLiquidGlass）、材质语义角色参数化、主题 Resolver 隔离层 | ⭐⭐⭐⭐ 高（正中本项目 M3 统一改造痛点） |
| 工程与安全 | 书源安全沙箱 8 项修补（文件命名空间/Cookie 隔离/类白名单/状态写保护）、CI/CD 全自动发版 | ⭐⭐⭐⭐ 安全项低成本高收益 |

## 文档索引

| 文档 | 内容 |
|------|------|
| [spec.md](./spec.md) | 调研 Intent/Scope/Approach（含 Alternatives+Drawbacks）/Requirements/Scenarios |
| [design.md](./design.md) | **总体设计（设计前置版）**：8 维全景对比矩阵 + 双向优缺点客观对比（§2）+ 借鉴决策表 v2（15 项）+ 分期路线 + AD-01~06 |
| [evidence-pack.md](./evidence-pack.md) | 8 轮子代理分析统一事实源（网络/规则引擎/数据层/UI/AI/听书/视觉/工程安全，全带文件:行证据） |
| [tasks.md](./tasks.md) | 调研与设计任务清单 + AOAdapt 日志 |

### 实施级迁移设计（migration-designs/，函数/代码级深化版，未审查不实施）

| 分期 | 文档 | 深度 | 覆盖 |
|------|------|------|------|
| P0 | [P0-source-security-hardening.md](./migration-designs/P0-source-security-hardening.md) | 629 行 | 书源安全加固 5 项：逐函数解读+6 新类 kotlin 骨架+16 边界+21 单测方法+D1-D16 |
| P1 | [P1-ai-foundation.md](./migration-designs/P1-ai-foundation.md) | 632 行 | AI 供应商融合（AiProviderConfig v2 30 字段草案+J1-J9 注入点）+压缩 4 类+DB v109 DDL |
| P2 | [P2-mcp-service.md](./migration-designs/P2-mcp-service.md) | 418 行 | MCP 四模块拆分（NG 行号→模块映射表）+69 工具规格表+四层安全代码级 |
| P3 | [P3-tts-multirole.md](./migration-designs/P3-tts-multirole.md) | 461 行 | 多角色听书一期：五级路由 kotlin 草案+LocalDialogueSegmenter+7 段 diff 改造+6 新表 DDL+前端对齐 ui-standards |
| P5 | [P4-visual-patterns.md](./migration-designs/P4-visual-patterns.md) | 566 行 | 视觉三模式：快照四 data class+MaterialSurface 三分支+18 处直读清单+与 ui-style-unify-deep-fix 衔接 |

注：P5 期载体文件名为 P4-visual-patterns.md（延续创建序命名），期号以本表分期列为准

## 状态标记

- ✅ 设计完成：调研+设计前置验收通过（五轮审查：①通过 ②补双向对比 ③设计前置重构 ④函数级深化 ⑤B 类疑惑关闭 11 条+自评验收+P0 先行裁决）
- 实施阶段：P0 → P1 → P2 → P3 → P5 分期推进，每期另立实施 spec（引用本目录设计文档为权威依据）；实施中偏离设计须先回写本文档再改代码（AD-02 门禁）
