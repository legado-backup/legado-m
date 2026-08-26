# 遗留列表 Compose 化收尾（CacheActivity + ExploreFragment 瀑布列表）

## 功能概述

archive 迁移后 Compose UI 收尾专项。还剩两处**列表**仍在使用传统 RecyclerView + Adapter，与本项目「Compose 优先」的 UI 现行基线不一致，需 Compose 化并补齐设计文档：

- **遗留项 7.11ai**：`CacheActivity`（缓存列表页）主列表仍用 `binding.recyclerView` + `CacheAdapter`。
- **遗留项 7.11aj**：`ExploreFragment`（探索）瀑布主列表仍用 `rvDiscoverBooks` + `ExploreShowWaterfallAdapter`（StaggeredGridLayoutManager）。

本次目标是参考已验证的「纯 Compose 壳层」范式（`UrlRecordScreen` / `PreciseManageScreen`），将上述两处列表整页/整段迁移为 Compose，消除残余 View 列表，统一数据流为 `mutableStateListOf` + Diff 重组。

## 核心能力

1. **CacheActivity 列表 Compose 化**：`RecyclerView`+`CacheAdapter` → `LazyColumn` + @Composable item（7 字段），点击回调 `onDownloadToggle(book)` / `onExport(book)`，局部刷新改按 `bookUrl` Diff 重组。
2. **Explore 瀑布列表 Compose 化**：`rvDiscoverBooks` + `ExploreShowWaterfallAdapter` → `LazyVerticalStaggeredGrid` 封面瀑布 item，滚动到底加载更多由 Compose 滚动状态接管。
3. **数据流统一**：`adapter.setItems()` / `notifyItemChanged()` → `mutableStateListOf<Book>` + 签名 Diff 局部重组。
4. **顶栏/间距状态收敛**：`updateModernTopBarOverlay` / `applyDiscoverBookContainerMargins` 的 View 级 padding 迁移到 `composeDiscoverTopPadding` 等 Compose 状态统一接管。
5. **适配器类退役**：`CacheAdapter.kt` / `ExploreShowWaterfallAdapter.kt` 删除或转为 Compose item 文件。

## 文档索引

| 文档 | 说明 |
|------|------|
| [spec.md](./spec.md) | 规格说明（Intent / Scope / Approach / Requirements / Scenarios） |
| [design.md](./design.md) | 技术方案（Technical Approach / ADR / Data Flow / File Changes） |
| [tasks.md](./tasks.md) | 任务清单（`- [ ] X.Y` 格式 + AOAdapt 日志） |

## 状态标记

✅ 设计完成（检查点1 通过 2026-08-25，待实施）