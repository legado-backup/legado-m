# L-C10 下载管理（DownloadManage）轻量设计文档

> **轻量版**：本页继承族文档 `pages/P4-my-config.md`（S2 设置族）的骨架/组件/状态范式，本文只写「继承 + 差异」。开发本页只读本文档 + P4 + ui-standards §3.4 规格书。

## 0. 页面身份

- **页面名 / 文件锚点**：DownloadManageActivity（`ui/download/`，View）
- **所属族文档**：`pages/P4-my-config.md`（继承 S2）
- **骨架归类**：S2 列表管理页（5 Tab 下载列表）
- **对应 task**：tasks.md `12.57`；pages-inventory C10（优先级 P3）
- **fork 借鉴来源**：—

## 1. 继承声明（本页复用什么）

- 复用骨架：S2 列表管理页（P4 §2）+ TabRow（P10 §2 Tab 范式）
- 复用组件（§3.4）：`GlassTopAppBar`、`EmptyStatePlaceholder`、`ConfirmDialog`、`AppDropdownMenu`
- 复用状态范式：`ViewModel + StateFlow`（轮询 + 过滤派生）

## 2. 差异点（与族文档唯一不同处）

| 维度 | 本页差异 | 说明 |
|------|---------|------|
| 数据源 | DownloadState 轮询（非 Room Flow） | 500ms 轮询 `DownloadState.queryAllTaskStatus` |
| 布局结构 | **5 Tab**（全部/运行中/暂停/完成/失败）；过滤 + startTime 倒序 | — |
| 交互 | 任务点击状态菜单（删除/重试/打开+复制路径+删除）；清除完成失败任务 | — |
| 功能点 | 下载任务管理 + 状态分类 | 对照 pages-inventory C10 无遗漏 |

## 3. 组件选型（§3.4 规格引用，仅列差异组件）

| 组件 | §3.4 规格摘要 | 本页使用点 |
|------|-------------|-----------|
| `ConfirmDialog` | L2 语义确认弹窗 | 删除/清除任务确认 |

## 4. 三态（继承族文档，仅列差异）

| 状态 | 组件 | 说明 |
|------|------|------|
| 加载 | `ShelfGridSkeleton` | 首次查询骨架屏 |
| 空态 | `EmptyStatePlaceholder` | 无下载任务 |
| 错误 | `EmptyStatePlaceholder` | 轮询失败 + 重试 |

## 5. i18n 与无障碍

- 新文案 `strings.xml` 双语；无硬编码中文/色/字号（同族文档）

## 6. 验收标准（轻量）

- [ ] 复用 P4 骨架/组件，无私有复制组件
- [ ] 差异点全部实现；功能点对照 pages-inventory C10 无遗漏
- [ ] 三态齐全；i18n 通过
- [ ] 真机功能点覆盖用例通过；§3.3 实施回执已填

## 7. 变更记录

- 2026-08-13：初始建立（关联 task 12.57 / pages-inventory C10）
