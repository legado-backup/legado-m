# spec.md — P3-3 长尾页 Compose 化收尾（专项）

> 本文是 `ui-issues-round-20260818` 的 **P3-3 子 spec**：承接主 spec [README](../README.md) 问题 3/9「除阅读详情页外，所有页面组件 Compose 化」在**长尾低频页**上的收尾推进。依托主 spec 设计阶段已完成的**[调研结论](../design.md#调研结论)**（84 页面类三分类 + §6.4 P3 长尾清单），本子 spec 将候选长尾页从「View 主体」收敛为「Compose Lazy* 主体」。

## Intent

将 P3 剩余 **7 个长尾低频页**（搜索、全文搜索、目录页、订阅源管理、RSS 文章列表、替换规则、RSS 搜索）的内容区由 View（RecyclerView/Adapter）迁移到 Jetpack Compose `Lazy*`，迁移后实现与已交付页面（OtherConfig/BackupConfig/发现订阅等）一致的 M3 视觉体系与组件复用。

**本子 spec 目标**：
1. **内容区 Compose 化**：7 个候选页主体列表/网格从 RecyclerView+Adapter 迁移到 `LazyColumn`/`LazyVerticalGrid`，Item 统一复用公共组件（`ListCard`/`SettingsCard`/`EmptyStatePlaceholder` 等）。
2. **风格统一**：Item/空态/加载更多/滚动条全部走公共组件与 token（对齐 ui-standards v2.18），消灭页面私有样式。
3. **组件与弹框收敛**：页面私有 Adapter 视情况废弃；私有弹框按设计 AD-P33-05 三选一收敛公共弹框族。
4. **零功能回退**：严格执行主 spec 红线——业务逻辑/数据层零改动、不裁剪既有功能，仅 UI 壳层迁移。

**红线（不可触碰）**：
- **阅读详情页禁止改动**（`ui/book/read/page/` 29 文件）：AD-02 正文引擎零改动。
- **纯 View 内核页不透传**：漫画/视频播放器/WebView 池/代码编辑器/扫码/透明窗——不在本批次清单。
- **订阅源编辑页** `RssSourceEditActivity`：主体 XML 表单被用户认可，保留不迁移。
- **禁止再次裁剪功能**：本批次只做"迁移"与"收敛"，任何整改不得再缩减既有功能。
- **禁止臆测**：替换规则页 `ReplaceRuleScreen` 接入状态等存疑项，实施前先到源码核实，与设计冲突时反哺设计。

## Scope

### In Scope

| 范围 | 说明 |
|------|------|
| 搜索页 | `SearchActivity` 内容区 Compose 化：搜索结果/搜索历史/书籍分组三种列表 Lazy 化，`SearchScopeDialog` 收敛公共弹框 |
| 全文搜索 | `SearchContentActivity` 搜索结果列表 Lazy 化 |
| 目录页 | `TocActivity` 三 Fragment 列表（章节/书签/高亮）Compose 化，Activity 壳保留 ViewPager2/生命周期 |
| 订阅源管理 | `RssSourceActivity` 多视图（Grid/List/Compact）列表 Compose 化；滑选多选/拖拽排序拆独立任务（AD-P33-04） |
| RSS 文章列表 | `RssArticlesFragment` 5 样式列表 + 预加载 Compose 化 |
| 替换规则 | `ReplaceRuleActivity` 主体列表 Compose 化（`ReplaceRuleListScreen` 新增）；顶栏 `ReplaceRuleTopBar`/`ReplaceRuleScreen.kt` 经源码核实已 Compose，免动；拖拽/滑选拆独立任务（AD-P33-04） |
| RSS 搜索 | `RssSearchActivity` 列表 Lazy 化 + 私有弹框收敛 |
| 验收与交付 | 逐页回执表登记（缺失=未完成）、编译门禁、updateLog 同步、章节登记 |

### Out of Scope

| 排除项 | 原因 |
|--------|------|
| 阅读详情页 / 漫画 / 视频 / WebView 池 / 代码编辑器 | 内核与第三方控件保留原生 View（红线） |
| 网络层 / 播放器 / 数据层 / 规则引擎 | 业务逻辑零改动，仅 UI 壳层迁移 |
| 数据库 schema 变更 | 无 |
| 新增第三方依赖 | 拖拽 Reorderable 等依赖未经设计确认不引入（AD-P33-04） |
| 新增功能 | 本批次为迁移收敛性质，不引入新功能 |

## Approach

### Selected Approach

采用 **「壳保持 + composeHost.setContent」双轨迁移模板**（对齐主 spec P3-3b 已交付的 `OtherConfig`/`BackupConfig` 与 ui-redesign-m3 已验证范式）：

```
Activity/Fragment（壳）  保持继承 + 生命周期 + Intent 处理 + ViewModel 获取
                          仅将内容区替换为 binding.composeHost.setContent { LegadoTheme { XxxScreen(...) } }
                          副作用（权限/文件选择/startActivity/DialogFragment）留在壳回调上抛
ComposeScreen（新增）    内容区全 Compose：列表→Lazy*、Item→公共组件、空态→EmptyStatePlaceholder、
                          加载更多→LazyListState+derivedStateOf、State 提升到壳回调
```

关键原则（对齐 AD-P33-01~05）：
- **单模板**：7 页统一范式，Code Review 体感一致、回退最小。
- **数据层零改动**：沿用既有 `XxxViewModel`，`collectAsStateWithLifecycle` 消费，不新建 VM、不搬逻辑。
- **DiffUtil→Lazy key 差分**：用 `items(items, key={it 唯一ID})` 天然差分，不手写 Diff、不引第三方 Diff 库。
- **复杂交互**（滑选多选/拖拽排序）：首期内容区列表 Compose 化，手势作为独立验证任务；需要时 `AndroidView(RecyclerView)` 桥接保留手势层（AD-P33-04）。
- **私有弹框三选一收敛**：右上角=AppDropdownMenu / 底部=AppModalBottomSheet / 悬浮=AppEditDialog+AppSelectDialog+ConfirmDialog（AD-P33-05）。

### Alternatives Considered

| 方案 | 说明 | 未采纳原因 |
|------|------|-----------|
| A. 全量一次性迁移（含手势） | 一次到位把列表+滑选+拖拽全 Compose | 订阅源管理/替换规则手势复杂，Compose 无现成等价（Reorderable 需新依赖），一次动完回归面太大 |
| B. 保留 View RecyclerView，仅换壳 | 最小改动，只改头部 | 不解决内容区 Compose 化目标，与问题3/9「全页面 Compose 化」诉求冲突 |
| C. 逐页各自自定义栈组织 | 每页独立决定结构 | 范式漂移、回退困难、Review 体感不一致 → AD-P33-01 明确否决 |
| D. 新建 VM 或改业务逻辑 | 数据获取/规则评估一并迁移 | 触碰内核，高概率回归 → AD-P33-02 明确否决 |

### Drawbacks（所选路线风险与缓解）

| 风险 | 缓解 |
|------|------|
| 半混合态（列表 Compose + 手势 View 桥） | 明确为过渡态，AD-P33-04 登记，视觉一致但内层手势保留，手势方案成熟后统一 |
| 超大列表（万级目录）性能 | AD-P33-03 预留实施验证，必要时分页/稳定 key |
| 存疑项（替换规则接入状态）导致设计不准 | 实施前源码核实，不符时反哺设计（§5 实施反哺） |
| 迁移引入功能回归 | 逐页回执登记 + compile 门禁 + updateLog 同步，禁止混用完成级别（L1/L2/L3） |

## Requirements

### Functional Requirements（FR）

- **FR-P33-01**：7 个候选页内容区主体由 RecyclerView+Adapter 迁移为 Compose `Lazy*`，Item 复用公共组件，消灭页面私有样式。
- **FR-P33-02**：各页数据层/业务逻辑零改动（沿用 XxxViewModel + `collectAsStateWithLifecycle`），只改 UI 壳层。
- **FR-P33-03**：各页 DiffUtil/ViewHolder Adapter → `items(key=唯一ID)` 差分，不手写 Diff 逻辑。
- **FR-P33-04**：空态、加载更多（触底自动）、滚动条走公共组件（EmptyStatePlaceholder / LazyListState+derivedStateOf / VerticalScrollbar）。
- **FR-P33-05**：私有弹框按三选一收敛公共弹框族（AD-P33-05），无屏蔽/无新增私有弹框。
- **FR-P33-06**：订阅源管理滑选多选、替换规则拖拽排序作为独立验证任务，首期列表 Compose 化不阻塞验收（AD-P33-04）。
- **FR-P33-07**：替换规则页顶栏/搜索（`ReplaceRuleTopBar`/`ReplaceRuleScreen.kt`）经源码核实已 Compose 且已接入 Activity，**不重做**；本批次仅补主体列表 `LazyColumn` 化，拖拽/滑选按 AD-P33-04 拆独立任务。
- **FR-P33-08**：字符串进 `strings.xml`（禁止硬编码），圆角/间距/触控遵循 ui-standards token。

### Non-Functional Requirements（NFR）

- **NFR-P33-01（回归）**：每个迁移页面经 compile 门禁 + 运行验证，禁止只改代码不验证。
- **NFR-P33-02（红线）**：阅读详情页/内核页/订阅源编辑页零改动。
- **NFR-P33-03（一致性）**：Item/空态/加载更多/滚动条对齐 ui-standards v2.18 与主 spec P3-2b 巡检门禁。
- **NFR-P33-04（性能）**：≥200 项列表滚动流畅；万级目录预留分页/稳定 key 验证。

## Scenarios

### 搜索页（优先级最高）
用户在书搜索页输入关键词 → 防抖触发 `SearchViewModel` 搜索 → 结果按书源分组，`LazyColumn` 渲染（key=bookUrl）→ 点击进阅读详情（壳回调 `startActivityForBook`）→ 长按/滑选多选批量操作；历史词以 `LazyVerticalGrid` 展示，可删除/清空；搜索范围用 `AppSelectDialog`/`AppModalBottomSheet` 选择。

### 全文搜索
用户全文搜索 → 结果列表 `LazyColumn` 展示，命中词高亮 → 点击跳转阅读页定位（`TocActivityResult` 语义）→ 触底自动加载更多。

### 目录页
用户在阅读页打开目录 → 章节/书签/高亮三 Tab 列表 Compose 化 → 点章跳转（Activity 结果回调沿用）、当前章高亮定位、书签/高亮增删；SwipeTabRow（壳已在）+ 三 LazyColumn 独立 ScrollState 保持状态。

### 订阅源管理（风险最高）
用户订阅源管理页切换 Grid/List/Compact 视图 → `LazyVerticalGrid`/`LazyColumn` 按 `sourceLayout` 切换 → 批量启用/禁用/分组（SelectActionBar 语义）→ 拖拽滑选作为独立任务验证，不阻塞本页验收。

### RSS 文章列表
用户在订阅源进入文章列表 → 5 种展示样式切换 → `LazyColumn`/`LazyVerticalGrid` 渲染 + 预加载（触底自动加载）→ 点击读文（`RssArticleInfoActivity`）、长按收藏/删除。

### 替换规则
顶栏/搜索/菜单/分组管理经源码核实已 Compose（`ReplaceRuleScreen.kt` 实为 `ReplaceRuleTopBar`，已接入 `ReplaceRuleActivity`）——**不重做**。本批次仅新增 `ReplaceRuleListScreen` 将主体 `RecyclerView` 列表迁移为 `LazyColumn`（`ReplaceRuleViewModel` 沿用，点选/长按/过滤回调上抛到现有壳 handler）；拖拽排序与滑选多选保留 View 层作为独立任务（AD-P33-04）。验收：主体列表 Compose 化后仍支持启用/停用/无分组/分组:xx 过滤与实时搜索结果。

### RSS 搜索
用户在 RSS 搜索页输入关键词 → 结果 `LazyColumn` 渲染 → 历史词展示/删除 → 点击进 RSS 文章详情（`RssArticleInfoActivity`）；`ChangeRssArticleSourceDialog`/`SearchScopeDialog` 收敛公共弹框。