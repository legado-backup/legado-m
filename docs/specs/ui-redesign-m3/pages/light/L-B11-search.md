# L-B11 搜索（SearchActivity + SearchContentActivity）· 轻量设计文档

> **适用**：B11 搜索为枝叶页，继承族文档 `pages/P6-explore.md`（S2 列表）+ `pages/P7-rss.md`（S2 搜索范式）。task 12.16p，S2 列表管理页。

## 0. 页面身份
- **页面名 / 文件锚点**：`ui/book/search/SearchActivity.kt` + `ui/book/searchContent/SearchContentActivity.kt`
- **所属族文档**：`pages/P6-explore.md` + `pages/P7-rss.md`（继承 S2 搜索列表范式）
- **骨架归类**：S2 列表管理页
- **对应 task**：tasks.md `12.16p`；pages-inventory B11

## 1. 继承声明
- 复用骨架：S2 列表管理（搜索结果滚动自动加载 + DiffUtil payload 规避 §4.3）
- 复用组件（§3.4）：`GlassTopAppBar`、`SettingsSearchBar`（搜索）、`AppDropdownMenu`（菜单）、`EmptyStatePlaceholder`（空态）、`BadgeDot`（缓存标记）
- 复用状态范式：`ViewModel + StateFlow`（V2 接线后）

## 2. 差异点（与族文档唯一不同处）
| 维度 | 族文档 | 本页差异 | 说明 |
|------|--------|---------|------|
| 搜索页 | — | SearchView→viewModel.search；结果滚动自动加载；书架模糊搜索；历史 Flexbox+清空+删除+回填；精准搜索；搜索范围 Dialog；书源管理；动态分组；空结果 alert | 差异核心 |
| 全文搜索 | — | 逐章搜本地/已缓存（IO 协程+ensureActive+进度）；结果列表（章节名/行号/命中/缓存标记）；点击 postEvent(SEARCH_RESULT)+IntentData 回传阅读器定位；启用替换/正则 | |
| 数据源 | — | `flowByBook` 逐章 / 搜索流聚合 | |
| 搜索词 | — | SettingsSearchBar 接线 + 搜索词升 StateFlow + AppDropdownMenu 菜单族 + 三态 | V2 差异化治理 |

## 3. 组件选型（仅列差异组件）
| 组件 | §3.4 规格摘要 | 本页使用点 |
|------|-------------|-----------|
| `SettingsSearchBar` | 搜索栏（孤儿） | 顶栏搜索（V2 待接线，接线前清"搜索设置"硬编码） |
| `EmptyStatePlaceholder` | Icon 48dp + 标题 + 副标 | 空结果/空态（V7 待接线） |
| `BadgeDot` | error 底、10sp、99+ | 缓存标记/搜索命中 |
| `AppDropdownMenu` | M3 DropdownMenu | 动态分组菜单（V9 待接线） |
| `AppSelectDialog`（L2 族） | L2 语义 Dialog | 搜索范围 Dialog 收敛去向（V8 待接线） |

## 4. 三态
| 状态 | 组件 | 说明 |
|------|------|------|
| 加载 | `ShelfGridSkeleton` | 搜索中加载骨架屏 |
| 空态 | `EmptyStatePlaceholder` | 空结果占位（现状 alert 弹窗非占位，V7 改） |
| 错误 | `EmptyStatePlaceholder` | 错误分支 + 重试 |

## 5. i18n 与无障碍
- i18n 硬编码 7 处（V10）+ 日志 6 处（V11）+ view_search.xml defaultQueryHint（V12）+ SettingsSearchBar（V13）+ 英文值（V14）+ 占位符（V15）全待清；chip 27dp<48dp（V17）

## 6. 验收标准（轻量）
- [ ] 搜索页 SearchView→search / 滚动自动加载 / 书架模糊搜索 / 历史 Flexbox / 精准搜索 / 搜索范围 Dialog / 书源管理 / 动态分组全实现
- [ ] 全文搜索逐章搜本地已缓存 + 结果列表 + 点击 postEvent(SEARCH_RESULT) 回传定位 + 启用替换/正则
- [ ] SettingsSearchBar 接线 + 搜索词 StateFlow + AppDropdownMenu 菜单族 + 三态补齐
- [ ] i18n/无障碍清零（M1/M4）；§3.3 实施回执已填

## 7. 变更记录
- 2026-08-13：初始建立（关联 task 12.16p）
