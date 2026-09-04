# spec.md — 管理页样式统一与交互回归修复

> 状态：🔄 设计中

## Intent

修复 090318 真机走查暴露的 5 类问题：F1 视频上滑误报、F2 书架手势三症状、F3 发现页标签闪烁、F4 管理页透明度全域生效（去灰蒙蒙）、F5 子页面顶栏/列表统一（含 TxtTocRule 白色遮罩）。F4 为 ui-theme-governance-polish P6 消费模型的修正（Delta：BaseActivity decorView tint 路线废弃，统一内容层 alpha）。

## Scope

### In Scope

- F1：恢复 5 处 `VideoPlaylistHolder.set` 注入（ExploreShowActivity/ExploreFragment/SearchActivity/BookshelfFragment1/BookshelfFragment2，按 05e4dde3c 最小 diff 重放）
- F2：书架刷新条件化（仅列表回顶放行）+ LazyGrid State Saveable + loading 分支常驻化 + LockableViewPager 轴向锁定强化
- F3：MainTopBarView LayoutTransition 禁 APPEARING/DISAPPEARING + updateFilterBarsVisibility 幂等化 + RoundedTagBarView 局部刷新
- F4：透明度消费模型统一为内容层 alpha（AppManagementScaffold 模式为准）；AppSettingComponents `page` 色与三个全屏不透明根层（ThemePackageManageScreen/AppPackageManageScreen/BookInfoManageScreen）透明化；BaseActivity 钩子语义修正（decorView 恒不透明底，tint 不再带 alpha）
- F5：管理族子页面统一化第一期——A 类 9 页（全 Compose 列表）平移 AppManagementScaffold；B 类共享组件 AppPackageManageComponents 改造（3 页近乎免费）+ View TitleBar 摘除；C 类 4 页（View RecyclerView）顶栏样式对齐；GlassTopAppBar 族透明度接入

### Out of Scope

- F2 书架"下滑翻页"产品形态（流式列表保持上滑浏览，刷新条件化即可）
- C 类 4 页全量 Compose 化（仅顶栏样式对齐，整体迁移另行任务）
- 视频播放队列自愈兜底（方案 C，网络重建快照错位风险，不做）
- 发现页标签 DiffUtil 全量化（仅消 notifyDataSetChanged 闪动，选中态已精确重绑）

## Approach

### Selected Approach

1. **F1 注入恢复**：从 05e4dde3c 重放 5 处最小 diff（每处 3-8 行：isVideo 分支内 `VideoPlaylistHolder.set(列表, idx)`），与现存消费链/清理链（VideoPlayerActivity.onDestroy clear）完全对齐，无新架构。
2. **F2 手势三修**：①PullToRefreshBox 触发条件化——Compose 侧 custom `nestedScroll` 连接：仅 `listState.canScrollBackward == false` 放行刷新（参照发现页 setOnChildScrollUpCallback 桥接模式）；②`rememberLazyGridState()`→`rememberSaveable(saver=LazyGridState.Saver)`，loading 骨架改为 Box 叠加（LazyGrid 常驻组合）；③LockableViewPager 拦截条件补轴向优势确认（斜滑抗扰）。
3. **F3 闪烁三修**：`createTopBarLayoutTransition` 补禁 APPEARING/DISAPPEARING；`updateFilterBarsVisibility` 四个 isVisible 幂等化+`animateFilterToggle` 目标一致不重启；RoundedTagBarView `submitItems` 相同 items 早退（消 notifyDataSetChanged 全量重绘）。
4. **F4 消费模型 v2 预混不透明色（红队 R5-1 整改，superseding polish P6 的 alpha/tint 双路线）**：alpha 叠加模型废弃（decorView 同色底叠 alpha 数学性归零；非同色底则灰蒙蒙）——改**预混减淡色**：`final = lerp(backgroundColor, fadeTarget, 1-fraction)`，fadeTarget=浅色主题白/深色主题黑，不透明、无叠加、无泄漏、E-Ink 自动；消费点=AppManagementScaffold 根背景层+AppSettingComponents.page+BaseActivity tint（三处统一走 AppConfig 预混 helper）；滑条语义登记为"背景减淡"（100=原色，0=完全减淡）。
5. **F5 统一化第一期**：A 类 9 页（TxtTocRule/DictRule/HighlightRule/FileManage/StorageManage/LibraryContainer/BookCharacter/Download/AiProvider）平移 AppManagementScaffold（写一次 `MenuAction→AppManagementAction` 适配器，删页内自绘 SelectionActionBar）；B 类先改 AppPackageManageComponents 共享组件（TopBarManage/NavigationBarManage/ShareNoteTemplate 三页随之统一）+ BookInfo/Bubble/AdvancedTitle/CoverCollection/DiscoverySuite 摘 View TitleBar；C 类 4 页（CacheManage/ParagraphRule/ReadMenuButton/ReadAloudBgm）View TitleBar 样式对齐（消费 backgroundColor 基色消白带断层）；GlassTopAppBar 族页面顶栏基色接入 backgroundColor 语义（消 primaryColor 断层）。

### Alternatives Considered

| 替代方案 | 否决理由 |
|---------|---------|
| F1 方案 B（注入下沉 SearchBookOpenHelper 收口） | 改公共 API 波及非视频调用方；列表上下文仍需入口配合，本质未省事 |
| F1 方案 C（播放器侧按 origin 重建队列） | 网络重建与用户所见列表排序可能不一致，引入真实快照错位 |
| F4 保持 decorView tint + windowBackground 改透明 | window 级 translucent+wallpaper 成本高、与全 App 主题体系冲突；且 decorView 之下无内容可透出，模型性不可行 |
| F4 page 带 alpha 叠加模型 | 同色底叠 alpha 数学性归零（红队 R5-1 P0）；非同色底灰蒙蒙+15 处消费点双重叠透泄漏——预混不透明色根治 |
| F5 一步到位 24 页全量 AppManagementScaffold 化 | C 类 4 页 View RecyclerView 全迁移 1.5-2d/页，超出本期边界；样式对齐先行 |

### Drawbacks

- F1 注入代码来自被 revert 的"半成品"批次，需真机重跑三入口矩阵（发现/搜索/书架）确认
- F4 滑条语义重定义为"背景减淡"：0% 视觉=完全减淡至白/黑（非透出下层内容，用户若要壁纸透出另行立项）；15 处 settings.page 消费点随预混自动生效，TagManage 在 Scaffold 内叠 page 的双重叠透随预混消解
- F5 C 类 4 页仅顶栏对齐，列表仍是 View RecyclerView（分批策略，样式断层部分保留）
- F2 刷新条件化后"列表在顶部下拉刷新"仍可用，仅非顶部下拉不再误触发（符合预期）

### Prior Art

- 发现页 `setOnChildScrollUpCallback`+Compose 桥接（ExploreFragment.kt:220/255-263）：F2 刷新条件化参照
- `topbar-filter-flash-fix`（MainTopBarView setFilterBarVisible 无动画直切）：F3 同款思路
- AppManagementScaffold 根背景层（ui-theme-governance-polish 已实施）：F4 统一模型基准
- BookshelfTagManageActivity：F5 唯一已接入范例

## Requirements

### R1 视频播放队列（F1）
1. 发现页/搜索/书架三入口打开视频时注入所在列表队列（VideoPlaylistHolder.set）
2. 非末部影片上滑切换下一个；真末部/单列表项才提示"已是最后一个视频"

### R2 书架手势（F2）
1. 列表非顶部时下拉不触发刷新；顶部下拉正常刷新
2. 滚动位置在刷新/loading/切分组期间保持（Saveable+常驻组合）
3. 斜滑手势不误触刷新或切 Tab

### R3 发现页头部（F3）
1. 点击标签无整条闪烁、向下按钮无 alpha 透明闪烁（浅色主题验证）
2. 切源/筛选时标签条无全量重绘闪动

### R4 管理页透明度（F4）
1. 全部管理族宿主（33 页）背景减淡可见生效，模型=预混不透明减淡色（lerp backgroundColor→fadeTarget），禁止任何 alpha 叠加路线
2. 无"灰蒙蒙"效果；decorView 恒不透明
3. E-Ink 强制 1f 语义保持

### R5 子页面统一（F5）
1. A 类 9 页 + B 类共享组件页顶栏/底栏/列表接入 AppManagementScaffold 族（白带断层消除）
2. C 类 4 页顶栏基色对齐（消白色遮罩感）
3. GlassTopAppBar 族不再出现 primaryColor 与状态栏白带断层

## Scenarios

### S-F1: 发现页视频上滑
**Given** 发现页列表有 N>1 个视频，播放第 i 个（i<N）
**When** 上滑
**Then** 切换到列表第 i+1 个视频；第 N 个上滑才提示"已是最后一个视频"

### S-F2: 书架手势
**Given** 书架列表已滚动到中间
**When** 下拉
**Then** 不触发刷新；回顶部后下拉正常刷新；刷新期间滚动位置不跳变；斜滑不误触

### S-F3: 标签无闪烁
**Given** 发现页头部为标签形式，浅色主题
**When** 点击任一标签
**Then** 仅选中态切换（无整条 alpha 闪烁，向下按钮无透明一下）

### S-F4: 管理页透明度全域
**Given** 透明度设为 50%
**When** 进入主题管理/TopBar 管理/书籍信息管理/书架管理等任意管理族页面
**Then** 页面背景呈对应减淡效果（50% 可辨、0% 完全减淡非灰蒙蒙、非无变化）；设 100% 恢复原色；书源管理页现有效果不得归零

### S-F5: TxtTocRule 无白带断层
**Given** 浅色主题
**When** 打开 txt 目录规则页
**Then** 顶栏与状态栏条带无白色断层，列表样式与书源管理同族

## 验证标准

- L1 编译 + L2 真机：S-F1 三入口矩阵（发现/搜索/书架）、S-F2 三手势、S-F3 浅色主题标签、S-F4 四页透明度、S-F5 TxtTocRule 浅色顶栏
- 回归：S-F1 修复不破坏 VideoPlay 既有切换链；F4 不破坏 E-Ink/壁纸背景图路径
