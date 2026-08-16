# L-B2 目录（TocActivity）· 轻量设计文档

> **适用**：B2 目录为枝叶页，继承族文档 `pages/P2-reader.md`（S2 列表管理页 + 蓝图 S5 浮层）。目录改造 ReaderBookSheet 三 Tab（AD-06）属 R2 中期，短期按 S2 治理。

## 0. 页面身份
- **页面名 / 文件锚点**：`ui/book/toc/TocActivity.kt` + ChapterListFragment
- **所属族文档**：`pages/P2-reader.md`（S4/S5 复合，本页取其 S2 列表范式 + S5 浮层蓝图）
- **骨架归类**：S2 列表管理页（现状）→ S5 浮层（蓝图，R2）
- **对应 task**：tasks.md `12.16p`；pages-inventory B2

## 1. 继承声明
- 复用骨架：S2 列表管理（Room Flow 实时订阅 + DiffUtil 逐字段规避 §4.3 + 长列表 DiffRecyclerAdapter）
- 复用组件（§3.4）：`GroupHeader`（分组）、`SettingsSearchBar`（V2 接线后）、`AppDropdownMenu`（V10 接线后）
- 复用状态范式：`ViewModel + LiveData/Flow` 订阅；菜单全 @string（C9 ✅）

## 2. 差异点（与族文档唯一不同处）
| 维度 | 族文档 | 本页差异 | 说明 |
|------|--------|---------|------|
| 数据源 | ReadBook 单例 | `flowByBook/flowSearch` + 目录/书签双 Tab | 目录专用 |
| 搜索 | — | SearchView 搜索章节/书签；搜索由 TocActivity 驱动 BookmarkFragment | V2 待升 StateFlow |
| 菜单 | — | menu_book_toc：txt 目录正则/拆分长章/反转目录/目录UI替换/加载字数/导出书签/MD/Obsidian/日志 | C 项 ✅ |
| 条目 | — | ChapterListFragment：定位当前章/置顶/置底/点击回传 index/chapterChanged/长按 toast 替换后标题/云朵✓缓存态/卷名/字数/VIP锁 | 功能超越 fork |
| Tab | — | TabLayout+ViewPager+FragmentPagerAdapter（V3）与 BookTocBookmarkSheet 零接线 | 随 R2 收敛 |

## 3. 组件选型（仅列差异组件）
| 组件 | §3.4 规格摘要 | 本页使用点 |
|------|-------------|-----------|
| `GroupHeader` | titleSmall Bold、行≥48dp | 目录分组 |
| `SettingsSearchBar` | 搜索栏（孤儿） | 章节/书签搜索（V2 待接线） |
| `AppDropdownMenu` | M3 DropdownMenu、checked 勾选 | menu_book_toc（V10 待接线） |
| `ReaderBookSheet`（🆕 待建） | 三 Tab HorizontalPager 72% 高 | R2 目录收敛去向 |

## 4. 三态
| 状态 | 组件 | 说明 |
|------|------|------|
| 加载 | `ShelfGridSkeleton` | 目录加载骨架屏 |
| 空态 | `EmptyStatePlaceholder` | 空目录占位（现状裸空白，V11 改） |
| 错误 | `EmptyStatePlaceholder` | 错误分支 + 重试 |

## 5. i18n 与无障碍
- i18n 硬编码 9 处待清（V6）；ChapterListFragment 拼接非 %1$s 占位符待规范（V7）；当前章信息栏/置顶/置底按钮 36dp<48dp 待修（V12）

## 6. 验收标准（轻量）
- [ ] V14 高亮 Tab 接线（止血 updateLog 与现状不符，P1 优先）
- [ ] 功能点对照 pages-inventory B2 无遗漏（目录搜索/反转/替换标题/字数/拆分/正则/导出书签/MD/Obsidian/日志）
- [ ] V1/V2 随 S2 样板冻结（GlassTopAppBar + SettingsSearchBar + StateFlow）
- [ ] 三态/i18n/无障碍补齐；§3.3 实施回执已填

## 7. 变更记录
- 2026-08-13：初始建立（关联 task 12.16p）
