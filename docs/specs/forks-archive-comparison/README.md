# 阅读 Archive 私仓深度对比与借鉴分析

> **状态**：🔄 待验收（检查点2：实施完成 2026-07-18，等待用户审核）
> **创建时间**：2026-07-18
> **任务来源**：用户要求下载阅读 Archive 私仓（`Rimchars/legado-private-armv8-release`），与当前版本深度对比，提炼可借鉴点
> **类型**：延伸版本对比（参考 `docs/project-rules/forks-reference.md`）

---

## 功能概述

阅读 Archive（站点A）是 fork 自 Lyc 维护的 Legado 分支的主流延伸版本，对比优先级 ⭐⭐⭐。本任务对齐 `forks-reference.md` 中"阅读Archive > 蛋蛋Max > 阅读NG"的 WebView 优化优先级矩阵，深度分析私仓版本与本项目（阅读 Sigma fork）的差异。

### 核心能力
1. **文件结构对比**：顶层目录、Java 源码包、res 资源、构建配置全维度扫描
2. **关键模块对比**：主题管理 / EPUB 阅读 / AI 助手 / 发现页与订阅源 / 视频播放 / 构建配置 / 依赖库 七大维度
3. **差异识别与价值评估**：每项差异附收益/风险评分
4. **借鉴决策表**：明确"借鉴/不借鉴/待评估"三态决策与理由

### 关键约束
- **只分析不修改**：本任务不修改本项目源码，借鉴应用是后续独立任务
- **浅克隆**：私仓为 `--depth 1` 浅克隆，无法看历史变更轨迹
- **armv8 优化在 CI 层**：源码不可见 ARM 优化细节（在 `private-armv8-release.yml` 工作流中）

### 已知关键发现（基于 README/build.gradle 初扫）
- 阅读 Archive 已引入 **Jetpack Compose**（compose.bom/ui/material3）
- 引入 **liquidglass**（iOS 玻璃效果）、**miuix**（小米 UI 风格）
- 引入 **sora-editor** 代码编辑器、**danmakuFlameMaster** 弹幕
- 引入 **libarchive** 压缩解压、**LyricViewx** 椒盐歌词
- `minSdk 21`（本项目 23）、`targetSdk 36`（本项目待确认）
- `applicationIdSuffix '.Archive'`（release 后缀方案）
- 主题管理"重做"，支持日间/夜间/背景图/界面颜色/导入导出/云端同步
- AI 助手支持工具调用、书源搜索、章节读取、阅读记录查询、联网搜索
- EPUB 原生阅读深化：图片、注解、分页缓存、复杂样式、大文件导入
- 视频改进：直达播放页、详情/目录信息展示

---

## 文档索引

| 文档 | 内容 |
|------|------|
| [spec.md](./spec.md) | Intent / Scope / Approach（含 Alternatives Considered + Drawbacks）/ Requirements / Scenarios |
| [design.md](./design.md) | Technical Approach / Architecture Decisions（ADR Y-Statement）/ Data Flow / File Changes |
| [tasks.md](./tasks.md) | `- [ ] X.Y` 格式任务清单 + AOAdapt 日志 |
| analysis-report.md | 差异分析报告（实施阶段产出） |
| borrow-decisions.md | 借鉴决策表（实施阶段产出） |

---

## 状态追踪

- [x] 2026-07-18：克隆私仓到 `temp/forks-comparison/legado-archive/`（2418 文件，最新 tag `private-armv8-3.26.07071245`）
- [x] 2026-07-18：完成 README/build.gradle/CI workflow 初扫
- [ ] 生成四文档
- [ ] 用户审查设计方案
- [ ] 执行差异分析
- [ ] 输出借鉴决策表
- [ ] 用户最终验收
