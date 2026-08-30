# Archive 前端 UI 迁移整合（archive-ui-migration-202608）

> ⚠️ 归档待定（2026-08-30 文档规整）：设计停滞超 7 天，如需恢复实施请移回 docs/specs/ 并更新状态

> 状态：🔄 设计中（2026-08-19，基于最新 tag `archive-v3-3.26.08172114` 修订 v2）

## 功能概述

放弃"自行 Compose 化改造 UI"的低效增量路线，改为**整体迁移 [Rimchars/legado]（阅读Archive）的前端 UI 层**替换本项目的 UI，同时：

- **完整保留并强化本项目特色能力**：内置图片/视频播放器 + 前置嗅探 + 上下滑动自动切换下一内容、订阅源全局搜索、发现/订阅分组编辑、高亮体系等
- **Archive 全量搬入（用户已确认"全搬"）**：AI 助手 / 记忆 / Agent / 绘图 / 角色 / 朗读 BGM / 段落规则 的实体+业务+UI 一并完整搬入，不做裁剪；EPub Core 引擎搬入 Archive 版
- **快速缝合不报错（用户要求）**：以本项目为 git 基座 + Archive UI 分层搬入，每阶段编译门禁（`assembleAppDebug`）+ 每模块核心功能单元测试（`./gradlew test`）双门禁，杜绝"改完一堆 bug"
- **保留个人项目标识**：仓库地址、开发者、项目名称、logo
- **建设前端 UI 标准**：迁移过程中实时沉淀 Compose 组件规范，支撑后续功能扩展
- **以独立项目思路实施**：本次不向 Archive 上游提交合并申请（备用方案）

本方案同时覆盖 4 项子任务：

| # | 子任务 | 交付物 |
|---|--------|--------|
| 1 | Cronet `150.0.7871.128` → `500.0.1` 升级，去除本地内部打包（`app/cronetlib/`），减小 APK 体积 | 依赖替换 + 打包配置改造（方案 1 `cronet-bundled`，用户已确认） |
| 2 | 当前 Compose 迁移 WIP 快照分支 + 推送远端 | `test_compose_self_20260818` ✅ 已完成（commit 86ac9a802） |
| 3 | 深度分析两端底层核心层与前端 UI 层接口协议差异 | design.md 差异分析章节 + 5 份 rev2 预研报告 |
| 4 | 迁移全过程实时建设前端 UI 标准 | `docs/project-flow/ui-standards/` |

## 核心能力（迁移后形态）

- UI 层以 Archive 为蓝本（Compose 化管理页 / 重做主题系统 / 阅读器 / 漫画 / 订阅源页）
- 视频播放：保留本项目抖音风格（ViewPager2 竖向 + 上下滑动切文章/切集 + 前置嗅探 + M3U8/HLS 加固 + 预加载）
- 图片播放：保留本项目内置图片播放器（画廊/详情/画布/金字塔加载）
- 搜索：书源全局搜索（随 Archive UI）+ RSS 订阅源全局搜索（本项目特色）+ 内容全文搜索
- 分组编辑：发现页 / 订阅 tab / 管理页分组（含本项目分组封面 + 批量分组）
- 主题：直接采用 Archive 重做后的主题系统（32 字段 ThemeConfig / ~68 PreferKey / 日/夜运行时键 / 背景图 / 主题包 / 外观套件），`themeMode` 默认值跟随 Archive 语义（"0"跟随系统）
- 数据库：以本项目 v104 为基座，增量并入 Archive 独有 25 实体（5 批迁移 → v108），保留本项目 9 特色实体，覆盖安装升级无痛

## 文档索引

- [spec.md](./spec.md) — 需求规格（Intent / Scope / Approach / Requirements / Scenarios）
- [design.md](./design.md) — 技术设计（深度差异分析 / ADR / 数据流 / 文件变更）
- [tasks.md](./tasks.md) — 任务清单（`- [ ] X.Y` 格式）

### 深度预研报告（`docs/temp-analysis/`，gitignored 不入库）

| 报告 | 内容 |
|------|------|
| [rev2-sa1-backend-diff.md](../../temp-analysis/rev2-sa1-backend-diff.md) | 后端核心层（model/data/help）差异（基于最新 tag） |
| [rev2-sa2-db-diff.md](../../temp-analysis/rev2-sa2-db-diff.md) | 数据库实体与迁移链差异（基于最新 tag） |
| [rev2-sa3-theme-diff.md](../../temp-analysis/rev2-sa3-theme-diff.md) | 主题系统差异（基于最新 tag） |
| [rev2-sa4-ui-interface-diff.md](../../temp-analysis/rev2-sa4-ui-interface-diff.md) | UI-ViewModel 接口契约差异（基于最新 tag） |
| [rev2-sa5-features-wiring.md](../../temp-analysis/rev2-sa5-features-wiring.md) | 本项目特色功能迁移接线（基于最新 tag） |

> v1 版报告（`sa1~sa4`，基于旧 master 快照）已废弃，以 rev2 为准。

## 状态标记

- [x] 需求分析
- [x] 深度差异分析（基于最新 tag archive-v3-3.26.08172114，5 份 rev2 报告）
- [x] 分支快照推送远端
- [x] 四文档修订 v2（基于 rev2 分析 + 用户调整意见）
- [ ] 设计审查（🛑 检查点 1）
- [ ] 实施（🔄 开发中）
- [ ] 验收（✅ 已完成）
