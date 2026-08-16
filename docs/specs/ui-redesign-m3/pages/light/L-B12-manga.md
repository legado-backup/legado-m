# L-B12 漫画阅读（ReadMangaActivity）· 轻量设计文档

> **适用**：B12 漫画为枝叶页，继承族文档 `pages/P2-reader.md`（S5 全屏沉浸范式）。

## 0. 页面身份
- **页面名 / 文件锚点**：`ui/book/manga/ReadMangaActivity.kt`（862 行）
- **所属族文档**：`pages/P2-reader.md`（继承 S5 全屏沉浸范式）
- **骨架归类**：S5 全屏沉浸页
- **对应 task**：tasks.md `12.43`；pages-inventory B12（task 待接线）

## 1. 继承声明
- 复用骨架：S5 全屏沉浸（正文垫底 + 菜单层浮出 + 弹层单态）
- 复用组件（§3.4）：`AppModalBottomSheet`（菜单/信息栏配置）、`AppNumberPickerDialog`（自动翻页速度）、`AppDropdownMenu`（漫画菜单）
- 复用状态范式：沉浸式状态 + 菜单显隐（S5 范式）

## 2. 差异点（与族文档唯一不同处）
| 维度 | 族文档 | 本页差异 | 说明 |
|------|--------|---------|------|
| 正文层 | ReadView 排版 | MangaLayoutManager + PagerSnapHelper 横/竖翻页 | 差异核心 |
| 自动 | — | 自动翻页 / 自动滚动（速度 NumberPicker）；Glide 预加载（mangaPreDownloadNum） | |
| 信息栏 | — | MangaFooterConfig（章节/页码/进度% 可配置）；LoadMoreView footer | |
| 手势 | — | onTouchMiddle 开菜单/翻页、双指缩放、音量键、滚动驱动进度跨章 | |
| 菜单 | — | 亮度/页码/自定义按钮；换源/目录/刷新/预下载数量/禁用缩放/禁用点击滚动/横屏切换/颜色滤镜/电子纸/灰度/隐藏标题/底部信息栏配置/禁用页吸附/禁用页动画/自动翻页速度 | |

## 3. 组件选型（仅列差异组件）
| 组件 | §3.4 规格摘要 | 本页使用点 |
|------|-------------|-----------|
| `AppNumberPickerDialog`（L2 族） | L2 语义 Dialog | 自动翻页速度/预下载数量 |
| `AppDropdownMenu` | M3 DropdownMenu | 漫画菜单 |
| `AppModalBottomSheet` | L1 浮层面板 | 底部信息栏配置 |

## 4. 三态
| 状态 | 组件 | 说明 |
|------|------|------|
| 加载 | `ShelfGridSkeleton` | 图片分页加载骨架 |
| 空态 | — | 不适用 |
| 错误 | `EmptyStatePlaceholder` | 加载失败分支 + 重试 |

## 5. i18n 与无障碍
- 新文案 strings.xml 双语；漫画菜单项无硬编码中文

## 6. 验收标准（轻量）
- [ ] 横/竖翻页（MangaLayoutManager+PagerSnapHelper）+ 自动翻页/自动滚动 + Glide 预加载
- [ ] MangaFooterConfig 信息栏（章节/页码/进度% 可配置）+ LoadMoreView
- [ ] 漫画菜单全功能（亮度/页码/换源/目录/刷新/预下载/禁用缩放/颜色滤镜/电子纸/灰度/隐藏标题/信息栏配置/禁吸附/自动翻页速度）
- [ ] 手势保留；三态/i18n 补齐；§3.3 实施回执已填

## 7. 变更记录
- 2026-08-13：初始建立，task 12.43
