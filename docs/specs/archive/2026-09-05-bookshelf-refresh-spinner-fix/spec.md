# spec：书架刷新转圈卡死修复

## Delta（2026-09-05 第二轮用户反馈）

## ADDED Requirements
### Requirement: 书架刷新组件单层化
书架 style2 布局不得存在双层下拉刷新组件嵌套，下拉手势只允许产生一个刷新指示器。

#### Scenario: 文件夹布局根页面下拉刷新
- **WHEN** 用户在 style2 文件夹布局根页面下拉刷新
- **THEN** 仅出现一个转圈且松手即收（外层 XML SwipeRefreshLayout 已删除）

#### Scenario: 文件夹内下拉刷新
- **WHEN** 用户进入文件夹内书列表下拉刷新
- **THEN** 仅出现一个转圈且松手即收

### Requirement: 书源合集导入进度反馈
通过 URL 导入 `{"sourceUrls":[...]}` 格式书源合集时，子链接下载应并行执行并向 UI 报告实时进度，不得长时间无响应。

#### Scenario: yckceo 合集链接导入
- **WHEN** 用户通过书源导入对话框粘贴合集链接（sourceUrls 格式）
- **THEN** 子链接并行下载，UI 显示"获取中 x/y"进度；完成后展示书源列表；单个子链接失败不影响其余（聚合报告）

## Intent
书架下拉刷新转圈必须在松手瞬间消失（对齐 archive 语义），数据更新后台静默完成，任何场景下转圈不残留。

## Scope
- 包含：BookshelfScreen SwipeRefreshContainer 收圈逻辑；BookshelfFragment1/2 刷新复位链删除
- 不包含：upToc 数据更新逻辑；顶栏刷新按钮；订阅页/发现页下拉刷新

## Approach（精简）
对齐 archive BooksFragment L168-171：onRefreshListener 回调内第一行 `swipeRefresh.isRefreshing = false`，随后触发数据更新回调。删除 fork 自创的"等数据收圈"机制（refreshing state + upTocIdle 等待 + 5s 兜底 + 跨 View/Compose 重组同步），该机制是卡死根因（重组链在嵌套 ComposeView 场景断裂，铁证：090418 包含修复③仍复现）。

## Requirements
### Requirement: 下拉刷新触发即收圈
下拉刷新手势触发后，刷新指示器立即停止（SwipeRefreshLayout 自身手势动画自然结束），不再等待数据更新完成。

#### Scenario: 文件夹内下拉刷新
- **WHEN** 用户在书架文件夹（style2, groupId != IdRoot）顶部下拉触发刷新
- **THEN** 转圈松手即收；后台 upToc 静默更新目录；列表由 DB flow 自动刷新

#### Scenario: 切 tab 返回书架
- **WHEN** 用户下拉刷新后切换到订阅/我的，再返回书架
- **THEN** 不存在任何残留转圈（无跨重组链状态残留）

#### Scenario: style1 列表下拉刷新
- **WHEN** 用户在 style1 书架顶部下拉刷新
- **THEN** 行为同上，触发即收圈

## Scenarios 边界
- 非顶部下拉：setOnChildScrollUpCallback 已禁止触发，无转圈出现（保留现有逻辑）
- 刷新期间书籍列表更新：列表静默刷新，无转圈依赖
