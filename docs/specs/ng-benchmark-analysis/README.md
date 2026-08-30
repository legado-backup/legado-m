# ng-benchmark-analysis — 阅读NG（legado_NG）深度对标调研

> 状态：🔄 设计中（调研报告已生成，待用户审查）
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

### 实施级迁移设计（migration-designs/，设计前置，未审查不实施）

| 分期 | 文档 | 覆盖 |
|------|------|------|
| P0 | [P0-source-security-hardening.md](./migration-designs/P0-source-security-hardening.md) | 书源安全加固 5 项（文件沙箱/缓存命名空间/弹窗拦截/类策略灰度/状态写保护） |
| P1 | [P1-ai-foundation.md](./migration-designs/P1-ai-foundation.md) | AI 供应商抽象（配置融合路线）+ 上下文压缩 + DB v109 |
| P2 | [P2-mcp-service.md](./migration-designs/P2-mcp-service.md) | 外部 MCP 服务端（四模块拆分+工具目录适配+四层安全） |
| P3 | [P3-tts-multirole.md](./migration-designs/P3-tts-multirole.md) | 多角色听书一期（TTS 引擎 V2+五级路由+手动绑定+DB v110） |
| P5 | [P4-visual-patterns.md](./migration-designs/P4-visual-patterns.md) | 视觉三模式融入 ui-standards（材质角色/调度点/快照取色） |

## 状态标记

- 🔄 设计中：调研报告已生成，等待用户审查（检查点 1）
- 后续：用户裁决迁移范围 → 按裁决结果生成各迁移项的独立实施 spec
