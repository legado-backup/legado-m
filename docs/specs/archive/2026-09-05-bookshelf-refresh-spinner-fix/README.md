# bookshelf-refresh-spinner-fix（书架刷新转圈卡死修复）

## 状态
设计中 → 设计完成 → **开发中（Delta 轮代码完成 L1，待用户真机验收 L2）** → 已完成

## 变更日志
- 2026-09-05：Delta 轮——双转圈根因（外层 XML SwipeRefreshLayout 零引用无复位）删除单层化；书源/订阅源合集导入并行化+进度反馈； ImportSourceSheet 保持零改动
- 2026-09-04：创建，根因定位（archive 对比），方案对齐 archive 语义

## 功能概述
修复书架（style1/style2 文件夹模式）下拉刷新后转圈不消失的问题。切换订阅/我的 tab 再返回书架，转圈依然残留。

## 根因
Compose 迁移时将下拉转圈语义从 archive 的"触发即收圈"改为"跟随数据完成收圈"（refreshing=true → upTocIdle 信号/5s 兜底 → 跨 View/Compose 重组链写回 view.isRefreshing=false）。重组链在嵌套 ComposeView 场景真实断裂，转圈永久残留。

Archive 参考：`docs/analysis/archive-src/.../BooksFragment.kt` L168-171——listener 第一行立即 `isRefreshing = false`，数据更新后台静默完成，转圈与数据层解耦。

## 修复方案（对齐 archive 语义）
1. SwipeRefreshContainer 的 onRefreshListener 触发瞬间直接 `swipeRefresh.isRefreshing = false`
2. 删除"等数据收圈"全链：Fragment1/2 的 refreshing state、refreshResetJob 复位协程、isRefreshing 参数链
3. upToc 数据更新逻辑保留（列表由 DB flow 自动静默刷新）

## 变更点
| 文件 | 变更 |
|------|------|
| BookshelfScreen.kt | onRefreshListener 触发即收圈；移除 isRefreshing/trackedIsRefreshing 参数链 |
| BookshelfFragment1.kt | 删 refreshing/refreshResetJob/复位协程 |
| BookshelfFragment2.kt | 同上 |

## 文档索引
- [spec.md](./spec.md) 需求与场景
- [tasks.md](./tasks.md) 任务清单

## 变更日志
- 2026-09-04：创建，根因定位（archive 对比），方案对齐 archive 语义
