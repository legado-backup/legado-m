# L-B15 书库存储管理（StorageManageActivity）· 轻量设计文档

> **轻量版**：本页继承族文档 `pages/P4-my-config.md`（S2 设置族）的骨架/组件/状态范式，本文只写「继承 + 差异」。开发本页只读本文档 + `P4-my-config.md` + ui-standards §3.4 规格书。

## 0. 页面身份
- **页面名 / 文件锚点**：StorageManageActivity（`ui/book/storage/`，View）
- **所属族文档**：`pages/P4-my-config.md`（继承 S2 设置族）
- **骨架归类**：S2 列表管理页
- **对应 task**：tasks.md `12.53`；pages-inventory B15（优先级 P3）
- **fork 借鉴来源**：—

## 1. 继承声明（本页复用什么）
- 复用骨架：S2 列表管理页（P4 §2）+ 统计卡 MetricGrid
- 复用组件（§3.4）：`GlassTopAppBar`、`SettingsClickRow`（分项存储行）、`ConfirmDialog`（清除确认）、`AppDropdownMenu`（刷新/清空全部菜单）、`AppTextDialog`（详情 alert）
- 复用状态范式：`ViewModel + StateFlow`（存储统计 + 删除保护）

## 2. 差异点（与族文档唯一不同处）

| 维度 | 本页差异 | 说明 |
|------|---------|------|
| 数据源 | 分项存储统计（名称 + 大小） | Room / 文件系统遍历 |
| 布局结构 | 分项存储行 + 顶部统计卡 | — |
| 交互 | 点击 alert 详情；清除确认；菜单（刷新 / 清空全部逐项删除）；**视频播放中删除保护** | 删除保护为私有交互 |
| 功能点 | 分项统计/清除确认/刷新/清空全部/删除保护 | 对照 pages-inventory B15 无遗漏 |

## 3. 组件选型（§3.4 规格引用，仅列差异组件）

| 组件 | §3.4 规格摘要 | 本页使用点 |
|------|-------------|-----------|
| `MetricGrid` | MetricTile 12dp 圆角 | 存储总量统计卡 |
| `ConfirmDialog` | L2 语义确认弹窗 | 清除/清空全部确认 |
| `AppDropdownMenu` | M3 DropdownMenu | 刷新/清空全部菜单 |

## 4. 三态（继承族文档，仅列差异）

| 状态 | 组件 | 说明 |
|------|------|------|
| 加载 | `ShelfGridSkeleton` | 存储统计加载骨架屏 |
| 空态 | `EmptyStatePlaceholder` | 无存储项 |
| 错误 | `EmptyStatePlaceholder` | 错误分支 + 重试 |

## 5. i18n 与无障碍
- 新文案 `strings.xml` 双语；无硬编码中文/色/字号（同族文档）；触控 ≥48dp、Icon contentDescription

## 6. 验收标准（轻量）
- [ ] 复用 P4 骨架/组件，无私有复制组件
- [ ] 功能点对照 pages-inventory B15 无遗漏（分项统计/清除确认/刷新/清空全部/视频播放中删除保护）
- [ ] 三态齐全；i18n 通过
- [ ] 真机功能点覆盖用例通过；§3.3 实施回执已填

## 7. 变更记录
- 2026-08-13：初始建立（关联 pages-inventory B15），task 12.53
