# L-C15 图片浏览（ImageGallery / ImageDetail）轻量设计文档

> **轻量版**：本页继承族文档 `pages/P2-reader.md`（S5 全屏沉浸）的骨架/组件/状态范式，本文只写「继承 + 差异」。开发本页只读本文档 + P2 + ui-standards §3.4 规格书。

## 0. 页面身份

- **页面名 / 文件锚点**：ImageGalleryActivity + ImageDetailActivity（`ui/image/`，View，V4 垂直画布架构）
- **所属族文档**：`pages/P2-reader.md`（继承 S5）
- **骨架归类**：S5 全屏沉浸页
- **对应 task**：tasks.md `12.49`；pages-inventory C15（优先级 P2）
- **fork 借鉴来源**：—

## 1. 继承声明（本页复用什么）

- 复用骨架：S5 全屏沉浸页（P2 §2 全屏 + 沉浸式 + 工具栏）
- 复用组件（§3.4）：`GlassTopAppBar`、`AppDropdownMenu`、`ConfirmDialog`
- 复用状态范式：`ViewModel + StateFlow` + `onSaveInstanceState`

## 2. 差异点（与族文档唯一不同处）

| 维度 | 本页差异 | 说明 |
|------|---------|------|
| 数据源 | 文章图片流（分页加载） | PAGINATION_THRESHOLD + isInitialScrollDone |
| 布局结构 | Gallery：垂直长画布扁平化所有文章图；智能预加载（速度阈值 2.0px/ms + 150ms 去抖）；快滚 Glide pause/resume；**WebView 串行预热**（Cloudflare 403→降级重载 5s 兜底）；降级链回调（onWebViewFallback/onWebModeFallback）；**横向大图模式**（ViewPager2 全屏淡入/平滑回滚）；旋转工具栏；沉浸式；页码双显（横向 n/total + 画布右下悬浮） | — |
| 交互 | 长按保存/分享/复制URL；工具栏（收藏/刷新/浏览器打开/日志）；返回键退横向；Detail：独立大图页 ViewPager2 + 共享元素过渡；onSaveInstanceState 存 index | — |
| 功能点 | 画布图片浏览 + 横向大图 + 详情大图 | 对照 pages-inventory C15 无遗漏 |

## 3. 组件选型（§3.4 规格引用，仅列差异组件）

| 组件 | §3.4 规格摘要 | 本页使用点 |
|------|-------------|-----------|
| `SwipeActionContainer` | 左滑操作 | 长按操作替代交互 |
| `ConfirmDialog` | L2 语义确认弹窗 | 删除/保存确认 |

## 4. 三态（继承族文档，仅列差异）

| 状态 | 组件 | 说明 |
|------|------|------|
| 加载 | `ShelfGridSkeleton` | 分页加载骨架屏 |
| 空态 | `EmptyStatePlaceholder` | 无图片空态 |
| 错误 | `EmptyStatePlaceholder` | 图片加载失败/降级兜底 + 重试 |

## 5. i18n 与无障碍

- 新文案 `strings.xml` 双语；无硬编码中文/色/字号（同族文档）

## 6. 验收标准（轻量）

- [ ] 复用 P2 骨架/组件，无私有复制组件
- [ ] 差异点全部实现；功能点对照 pages-inventory C15 无遗漏
- [ ] 三态齐全；i18n 通过
- [ ] 真机功能点覆盖用例通过；§3.3 实施回执已填

## 7. 变更记录

- 2026-08-13：初始建立（关联 task 12.49 / pages-inventory C15）
