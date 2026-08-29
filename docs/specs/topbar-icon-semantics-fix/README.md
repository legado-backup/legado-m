# topbar-icon-semantics-fix（顶栏图标语义与功能修复）

> 状态：🔄 开发中

## 功能概述

Archive UI 迁移链路（T1 菜单下沉范式 → T2 搬壳不搬语义 → T3 H6 双向降维）导致顶栏一级功能图标语义静默蒸发：ConfigTopBar 仅渲染「返回键 + 单一 MoreVert + AppDropdownMenu」，MenuAction 数据模型无 showAsAction 承接字段。二次全面审查（原版 59 menu 文件/87 个 always 项对照普查）实锤 **B 类收拢回归 18 页/25 项**（备份恢复页问号、我的 tab 帮助、编辑页代码/保存/调试、主题设置、订阅 tab、管理页等）+ C 类疑似彻底丢失 3 项（封面启停/正文全屏编辑/主题剪贴板导入）。修复目标：按「对齐 Archive 原版 showAsAction 语义」原则四组件系分层恢复、死按钮防线加固、ui-standards 四层面规范补齐（门禁/严禁/迁移登记列/审计维度）防 AI 重犯、真机无响应专项排查。

## 核心能力

1. **四组件系分层恢复**：ConfigTopBar 系（MenuAction+alwaysShow 分级渲染）/ GlassTopAppBar 系（actions 槽一级 IconButton）/ MainTopBarView 系（我的 tab/订阅 tab 布局加图标位）/ View TitleBar 系（书源编辑）。
2. **18 页 B 类回归分批修复**：P0 批（备份问号/编辑页 3+2+3 图标/主题设置）→ 批C 管理页 → 批D MainTopBarView 系 → 批E 判定型逐项裁决。
3. **C 类 3 项真机复核闭环**：实锤修复 / 证伪关闭，结论登记。
4. **死按钮防线加固**：AppManagementAction.onClick 必填确认、GlassTopAppBar 漏传 onNavClick KDoc 警示、Fragment 切换 menuActions 残留真机验证。
5. **ui-standards 四层面补齐**：门禁双条款（图标功能有效性+语义保留）/ 严禁 3 条 / migration-registry 增"原 showAsAction 处置"必填列 / 审计增加"图标行为走查"维度 + 防重犯机制（checklist 置顶）。

## 文档索引

| 文档 | 说明 |
|------|------|
| [spec.md](./spec.md) | 需求规格：问题现象、根因分析、验收标准 |
| [design.md](./design.md) | 技术设计：MenuAction 扩展、ConfigTopBar 分级渲染方案 |
| [tasks.md](./tasks.md) | 任务拆解：开发步骤与真机验证清单 |

## 与现有工作的关系

本功能属于 ui-style-unify-deep-fix 顶栏体系（H6/H13/H15-H17）的延伸修复：统一顶栏改造解决了样式与交互一致性问题，但引入图标语义丢失与部分入口失效的回归。因问题独立、范围可控，单独立项跟踪，不回写原任务范围。

## 状态流转

🔄 设计中 → ✅ 设计完成 → 🔄 开发中 → ✅ 已完成
