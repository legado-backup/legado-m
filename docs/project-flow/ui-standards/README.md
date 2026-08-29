# ui-standards — UI 标准建设文档索引

> 目录：`docs/project-flow/ui-standards/`
> 关联任务：`docs/specs/archive-ui-migration-202608/tasks.md` 全仓 UI 对齐 Archive 工程（§7.11 E 类等）+ `docs/specs/ui-style-unify-deep-fix/` 组件体系单一来源治理（AD-07/AD-08）。
> **本目录是 AI 前端 UI 开发必读规范（`architecture.md` 为总纲）**：做任何 UI 改动前先读，禁止私自拉新组件 / 私有样式 / 硬编码色号 / 脱离主题设置体系。

## 子文档列表（按阅读顺序）

| 文件 | 对应任务 | 用途 |
|------|---------|------|
| [architecture.md](architecture.md) | ui-style-unify-deep-fix AD-07/08 | **UI 设计架构体系总纲（必读）**：铁律 / 主题全景 / 取色唯一基线 / 四大组件族（顶栏·菜单·弹框·卡片列表根背景）/ 新组件开发门禁 |
| [how-to.md](how-to.md) | ui-style-unify-deep-fix AD-08 | **实操指南（写码即查）**：场景决策树 + 源码核验的真签名 + 可运行骨架（弹框/菜单/页面/管理壳/取色）+ 严禁清单 + 样板页索引 |
| [components.md](components.md) | §9.1 | 组件目录：Compose 组件库与运行期骨架/对话框组件的完整清单 + 一句用途 + 状态标注（基线/待对齐/弃用） |
| [color.md](color.md) | §9.2 | 取色规范：ThemeUiPalette/R.color 兜底 + 设置类主取色链（AppSettingPalette/AppDialogStyle/UiCorner）+ M3 派生色禁令 |
| [theme-architecture.md](theme-architecture.md) | §9.7 | **主题体系架构总纲（改主题/模式/换肤代码前必读）**：Archive 三大体系（主题模式/应用主题/主题设置）全景 + 设计精髓十条 + 红线禁令 + 已知偏差指针（T 批次） |
| [spacing-corner-typography.md](spacing-corner-typography.md) | §9.3 | 间距 / 圆角 / 字体规范：Token 与运行时实现映射 |
| [page-skeleton.md](page-skeleton.md) | §9.4 | 页面骨架：通用管理壳 / 设置组件 / 对话框用法 + 根背景规则（palette.settings.page 直色） |
| [dialog-shell.md](dialog-shell.md) | §9.5 | 对话框壳：Compose 对话框族（基线）/ 5 家族分类 / 旧 `BaseDialogFragment` 36+pref2 迁移队列 |
| [migration-registry.md](migration-registry.md) | §9.6 | 迁移登记表：Archive 对齐（§7.11 E 类）+ ui-theme-gap-audit（G 系列）+ ui-style-unify-deep-fix（H/D/S 批次） |

## 维护约定

- 本目录文档一律以**当前源码**为准，组件名 / 函数签名 / 色值 key 均来自实际文件，禁止杜撰。
- 源码变更后应同步 / 复核本目录对应条目（尤其 components.md 与 migration-registry.md）。