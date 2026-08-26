# 弹框遗留项 Compose 化：autoTask / urlrecord 旧 View 弹框迁移

## 功能概述

项目在 Archive 迁移后的 Compose UI 收尾阶段，仍有三个残留 View 实现弹框未纳入 Compose 体系：

- **AutoTaskLogDialog**（自动任务执行日志）：`BaseDialogFragment(R.layout.dialog_recycler_view)`，展示单条任务最近运行时间 / 日志 / 错误 / 结果，提供清空菜单。
- **ImportAutoTaskDialog**（自动任务导入）：`BaseDialogFragment(R.layout.dialog_recycler_view)`，解析 JSON/JOSON 数组/URL/本地文件得到待导入任务列表，支持勾选、全选、逐条预览编辑、批量 upsert 导入。
- **urlrecord 页面内部弹框**：整页已 Compose，但 `showDetailDialog()`（历史记录详情）与 `showFilterDialog()`（四维过滤）仍走 `lib.dialogs.alert` / `lib.dialogs.selector` 旧弹框。

本 spec 将三者统一迁移到 `ComposeDialogFragment` + Compose UI（复用 `AppDialogFrame` / `AppEditDialog` / `ComposeChoiceListDialog` 等已验证组件），彻底移除这些旧 View 弹框残留，完成 7.11an / 7.11an2 遗留项收尾。

## 核心能力

- **日志查看**：自动任务最近一次运行的时间、日志 / 错误 / 结果文本，支持一键清空。
- **批量导入**：多来源（剪贴板 JSON、URL 抓取、本地文件）解析自动任务规则，勾选 / 全选后按 id upsert，可逐条代码预览编辑。
- **历史记录详情**：展示某条访问记录的请求方法 / 状态 / 耗时 / 时间 / 域名 / 完整 URL / 来源标识，一键复制 URL。
- **四维过滤收敛**：由 6 个嵌套 selector 收敛为单套 Compose 底部选择弹框，类别 / 值两级合一。
- **统一外观**：所有迁移后弹框接入 `ComposeDialogFragment` 基类，自动获得主题 / 墨水屏 / 尺寸规范支持。

## 文档索引

| 文档 | 说明 |
|------|------|
| [spec.md](./spec.md) | 规格说明（Intent / Scope / Approach / Requirements / Scenarios） |
| [design.md](./design.md) | 技术方案（Technical Approach / ADR / Data Flow / File Changes） |
| [tasks.md](./tasks.md) | 任务清单（`- [ ] X.Y` 格式 + AOAdapt 日志） |

## 状态标记

✅ 实施完成（核对 2026-08-25：autoTask 两弹框 + urlrecord 详情/过滤弹框均 ComposeDialogFragment，6.x 收尾登记同步，待全量编译门禁）