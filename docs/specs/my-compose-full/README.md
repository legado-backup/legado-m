# "我的"全域 Compose 化（my-compose-full）

## 状态
**设计中**（2026-09-07）

## 功能概述
"我的"入口全量页面树（穷尽枚举修订版，见 page-tree.md 附录）：一级 16 + 二级 32 + 三级叶子 + 对话框约 40 类；档位 C-full 13 / C-mixed 30 / C-none 7；孤儿/死代码 7 项同步治理。目标：全域 100% Compose + 归一化设计系统（四型模板 T1-T4 + MC-1..13 门禁 + 主题验证矩阵），与顶栏组件归一（subpage-topbar-unify 二期）协同。

## 文档索引
| 文档 | 说明 |
|------|------|
| [spec.md](./spec.md) | 需求规范（Intent/归一化设计系统/门禁 MC-1..13/组件统一表/主题验证矩阵） |
| [tasks.md](./tasks.md) | W0 前置 + W1-W6 分波任务清单 |
| [page-tree.md](./page-tree.md) | 页面树穷尽清单（层级+档位+入口）+ 孤儿清单 |

## 迁移波次（红队五轮修订版）
- **W0 前置**：SubBarDebug 定稿（shadow/Log）+ manageBgAlpha 收窄裁决落盘 + Tier×波次映射
- **W1**：AppearanceKit/Edit + ThemeManage 顶栏布局统一（自造清零拆 W5）
- **W2**：RssSearch 列表/About 去壳/ReadRecord 清残留/MyFragment 本体（验收含 SettingsSearch 回归）
- **W3**：TopBar/NavigationBar/ShareNoteTemplate 收尾 + AdvancedTitleManage 纳入 + 孤儿治理
- **W4**：CacheManage/CoverCollectionDetail 重写（ViewModel 复用+拖拽重实现）
- **W5**：管理列表/编辑型穷举（16 缺口页补入：三大源/规则族/Ai 族/S3/库容器/Relay/AllBookmark 等）
- **W6**：浏览型轻改 + 对话框 40 类基线清扫（补登记 QrCode/WebView/Verification/OpenUrlConfirm）

## 可复用资产（已固化）
- `AppManagementScaffold` / `GlassTopAppBar` / `ComposeSettingFragment` 体系 / composeHost 模式 / `AppPackageManageScreen` 共享壳（TopBarManage/ShareNote 样板）

## 变更日志
| 日期 | 变更 |
|------|------|
| 2026-09-07 | v2：红队五轮（3P0+13P1+13P2）修复落盘——波次穷举补 16 缺口页、W0 前置、门禁编号 MC 化、ThemeManage 拆波、SettingsSearch 回归纳入、Tier 映射落盘 |
| 2026-09-07 | v1 初版（45 页盘点 + 四波计划） |
