# ui-standards — UI 标准建设文档索引

> 目录：`docs/project-flow/ui-standards/`
> 关联任务：`docs/specs/archive-ui-migration-202608/tasks.md` 全仓 UI 对齐 Archive 工程（§7.11 E 类等）。
> 本文档组对项目当前 UI 的实现资产与规范做「源码核验型」整理，供组件建设 / 迁移登记 / 取色与间距规范落地参考。

## 子文档列表

| 文件 | 对应任务 | 用途 |
|------|---------|------|
| [components.md](components.md) | §9.1 | 组件目录：Compose 组件库与运行期骨架/对话框组件的完整清单 + 一句话用途 |
| [color.md](color.md) | §9.2 | 取色规范：Compose 主题调色板 key 表 + `.xml` 兜底色及 R.color 兜底清单 |
| [spacing-corner-typography.md](spacing-corner-typography.md) | §9.3 | 间距 / 圆角 / 字体规范：Token 与运行时实现映射 |
| [page-skeleton.md](page-skeleton.md) | §9.4 | 页面骨架：通用管理壳 / 设置组件 / Compose 对话框用法说明 |
| [dialog-shell.md](dialog-shell.md) | §9.5 | 对话框壳：Compose 对话框族 / 统一设置壳 / 旧 `base/BaseDialogFragment` 淘汰边界 |
| [migration-registry.md](migration-registry.md) | §9.6 | 迁移登记表：跟踪 Archive 对齐迁移（§7.11 E 类等）的完成状态 |

## 维护约定

- 本目录文档一律以**当前源码**为准，组件名 / 函数签名 / 色值 key 均来自实际文件，禁止杜撰。
- 源码变更后应同步 / 复核本目录对应条目（尤其 components.md 与 migration-registry.md）。