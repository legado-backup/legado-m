# Design: 书源/订阅源布局参考书架重构（Issue-6 方案D）

## Technical Approach

### 整体策略

保留现有 Activity 的 layout 分支结构（layout=0/1/2+），仅重构布局XML文件本身。通过 Adapter 代码适配新增控件ID。

**核心模式**：左侧首字图标 + 右侧多字段信息 + 右侧操作按钮区

### 布局参数精确对照表

#### 列表模式（参考 item_bookshelf_list.xml）

| 维度 | 书架列表 | 书源列表（重构后） | 订阅源列表（重构后） |
|------|---------|------------------|---------------------|
| 根布局 | ConstraintLayout | ConstraintLayout | ConstraintLayout |
| 左侧图标 | CoverImageView 66x90dp | FrameLayout 66x90dp | FrameLayout 66x90dp |
| 图标内容 | 封面图 | 首字TextView 28sp白色加粗 + 启用状态点8dp | 首字TextView 28sp白色加粗 + 启用状态点8dp |
| 图标背景 | - | bg_source_folder_cover | bg_source_folder_cover |
| 名称字段 | tv_name 16sp | cb_book_source 16sp（CheckBox） | cb_source 16sp（CheckBox） |
| 副字段1 | tv_author 13sp | tv_book_source_url 13sp（drawableStart=ic_author） | tv_rss_source_url 13sp（drawableStart=ic_author） |
| 副字段2 | tv_last_update_time 13sp | tv_debug_text 13sp（drawableStart=ic_history） | tv_last_update 13sp（drawableStart=ic_history） |
| 副字段3 | tv_read 13sp | - | - |
| 副字段4 | tv_last 13sp | - | - |
| 右侧操作 | fl_has_new + BadgeView + RotateLoading | swt_enabled + iv_edit(48dp) + iv_menu_more(48dp) + iv_explore + iv_progressBar | swt_enabled + iv_edit(48dp) + iv_menu_more(48dp) |
| 顶部 | - | tv_host_text（域名分组标题，可选） | tv_host_text（域名分组标题，可选） |

#### 紧凑列表模式（参考 item_bookshelf_list2.xml）

| 维度 | 书架紧凑列表 | 书源紧凑列表（重构后） | 订阅源紧凑列表（重构后） |
|------|------------|---------------------|---------------------|
| 根布局 | ConstraintLayout | ConstraintLayout | ConstraintLayout |
| 左侧图标 | CoverImageView 48x64dp | FrameLayout 48x64dp | FrameLayout 48x64dp |
| 图标内容 | 封面图 | 首字TextView 20sp白色加粗 + 启用状态点8dp | 首字TextView 20sp白色加粗 + 启用状态点8dp |
| 名称字段 | tv_name 16sp | cb_book_source 16sp | cb_source 16sp |
| 合并行 | tv_author + isolate + tv_read 13sp | tv_book_source_url 13sp | tv_rss_source_url 13sp |
| 右侧操作 | fl_has_new | swt_enabled | swt_enabled |

#### 网格模式（参考 item_bookshelf_grid.xml）

| 维度 | 书架网格 | 书源网格（已对齐） | 订阅源网格（待优化） |
|------|---------|-----------------|---------------------|
| 根布局 | ConstraintLayout | ConstraintLayout | ConstraintLayout |
| 卡片 | CoverImageView match_parent 4dp margin | CardView + ConstraintLayout | CardView + ConstraintLayout |
| 封面 | CoverImageView 3:4比例 | ImageView 3:4比例 + bg_source_folder_cover | ImageView 3:4比例 + bg_source_folder_cover |
| 首字 | - | tv_source_initial 36sp白色加粗 | tv_source_initial 36sp白色加粗 |
| 启用点 | - | v_enabled_dot 8dp | v_enabled_dot 8dp |
| 名称 | tv_name 12sp 2行居中 | tv_source_name 12sp 2行居中 | tv_source_name 12sp 2行居中（待对齐） |

## Architecture Decisions

### ADR-1: 使用 FrameLayout 包装首字图标（不直接用 ImageView）

**决策**：左侧图标用 FrameLayout 容器内嵌 TextView（首字）+ View（启用状态点）

**理由**：
- 书源/订阅源没有真实封面图（不像书架有 cover字段）
- 用首字+主题色背景替代封面，符合书架网格已实现的模式
- FrameLayout 容器方便后续扩展（如加载网络图标）

**影响**：
- 复用已有 drawable `bg_source_folder_cover`（在网格布局中已使用）
- 复用已有 drawable `bg_source_enabled_dot`（在网格布局中已使用）

### ADR-2: drawableStart 替代独立 ImageView

**决策**：tv_book_source_url 用 `drawableStart="@drawable/ic_author"` + `drawableTint` 而非独立 ImageView

**理由**：
- 原计划使用 `@drawable/ic_link` 但该 drawable 不存在
- 用已有 `@drawable/ic_author` + drawableTint 设置颜色
- 减少控件数量，简化布局

**影响**：
- 需要在 TextView 上添加 `tools:ignore="UseCompatTextViewDrawableXml"` 忽略 lint 警告
- drawableTint 在 API 21+ 可用，本项目 minSdk=23 满足

### ADR-3: 保留原有控件ID

**决策**：所有原有控件ID（cb_book_source / swt_enabled / iv_edit / iv_menu_more / iv_explore / iv_progressBar / tv_debug_text / tv_host_text）保留不变

**理由**：
- 避免修改 Adapter 代码中的 findViewById 调用
- 减少回归风险

**影响**：
- 新增控件ID（iv_source_cover / tv_source_initial / v_enabled_dot / tv_book_source_url）需要在 Adapter 中绑定
- 修改 Adapter 的 bindViewHolder 方法

### ADR-4: 首字提取逻辑（复用 Grid Adapter 已有实现）

**决策**：复用 BookSourceAdapterGrid L79 / RssSourceAdapterGrid L79 已有的简单实现
- 实现代码：`item.bookSourceName.firstOrNull()?.toString() ?: ""`（书源）/ `item.sourceName.firstOrNull()?.toString() ?: ""`（订阅源）
- 空名称：firstOrNull 返回 null，?: "" 返回空字符串（显示空，不显示"?"，与Grid保持一致）

**实现位置**：在 SourceExt 或 SourceHelp 中新增扩展函数 `sourceInitial(): String`，内部调用 `name.firstOrNull()?.toString() ?: ""`

**优点**：与 Grid 模式行为完全一致，避免中英文/emoji/符号等边界情况的处理复杂度

### ADR-5: 订阅源列表模式已存在（无需新增adapter）

**决策**：已验证 RssSourceActivity.applyListView 的 layout=0 分支使用 adapter（列表模式已存在）
- 订阅源已有3种模式：layout=0用adapter（列表）/layout=1用adapterCompact/layout=2+用adapterGrid
- **无需新增adapter，仅重构布局文件 item_rss_source.xml**
- 已确认 RssSourceAdapter / RssSourceAdapterCompact / RssSourceAdapterGrid 三个adapter都存在

### ADR-6: 必须保留 ivTypeBadge 类型徽章（重要遗漏补全）

**决策**：BookSourceAdapterCompact 和 RssSourceAdapterCompact 的 convert 方法都绑定了 ivTypeBadge 控件显示类型徽章，重构紧凑列表布局时**必须保留 ivTypeBadge 控件**

**BookSourceAdapterCompact 的 ivTypeBadge**（L78-86）：
- 类型徽章显示规则：0=文本(默认隐藏), 1=音频, 2=图片, 3=文件, 4=视频
- 使用字段：`item.bookSourceType`
- 资源：R.string.type_text/type_audio/type_image/type_file/type_video
- ivTypeBadge.isVisible = item.bookSourceType != 0

**RssSourceAdapterCompact 的 ivTypeBadge**（L78-85，类型映射不同！）：
- 类型徽章显示规则：0=网页(默认隐藏), 1=图片, 2=视频
- 使用字段：`item.type`（注意：不是 bookSourceType！）
- 资源：R.string.type_web/type_image/type_video
- ivTypeBadge.isVisible = item.type != 0

**位置建议**：在紧凑列表布局中，ivTypeBadge 放在 cbBookSource 和 swtEnabled 之间，或合并到 tv_book_source_url 行末尾

**XML ID 命名**：XML 用下划线 `iv_type_badge`，ViewBinding 自动转驼峰 `ivTypeBadge`，重构时保持 ID 一致

### ADR-7: payloads 增量更新必须同步新控件状态（仅列表Adapter，Compact无getChangePayload）

**决策**：原 convert 方法的 payloads 分支需要补全新控件的增量更新

**关键约束（子代理审计A5修正）**：
- **BookSourceAdapter / RssSourceAdapter（列表模式）有 getChangePayload**，需要补全 payload 同步
- **BookSourceAdapterCompact / RssSourceAdapterCompact（紧凑模式）无 getChangePayload**，payloads 只可能为空（全量刷新）或来自主动 notifyItemChanged 的 "selected"
- Compact 模式新增控件只需在 payloads.isEmpty 全量分支绑定即可，无需写 payload 增量代码

**BookSourceAdapter payloads 同步**（需同时修改 areContentsTheSame 增加 lastHost 比较 + getChangePayload 增加 upHost payload）：
```kotlin
// areContentsTheSame 增加（子代理审计A4修正）
override fun areContentsTheSame(oldItem: BookSourcePart, newItem: BookSourcePart): Boolean {
    return oldItem.bookSourceName == newItem.bookSourceName
            && oldItem.bookSourceGroup == newItem.bookSourceGroup
            && oldItem.enabled == newItem.enabled
            && oldItem.enabledExplore == newItem.enabledExplore
            && oldItem.hasExploreUrl == newItem.hasExploreUrl
            && oldItem.lastHost == newItem.lastHost  // 新增：追踪 lastHost 变化
}

// getChangePayload 增加
if (oldItem.lastHost != newItem.lastHost) {
    payload.putBoolean("upHost", true)
}

// convert payloads 分支增加
"upHost" -> tvBookSourceUrl.text = item.sourceUrlHost()
"enabled" -> {
    swtEnabled.isChecked = bundle.getBoolean("enabled")
    vEnabledDot.visibility = if (bundle.getBoolean("enabled")) View.VISIBLE else View.GONE  // 新增
}
"upName" -> {
    cbBookSource.text = item.getDisPlayNameGroup()
    tvSourceInitial.text = item.sourceInitial()  // 新增
}
```

**BookSourceAdapterCompact（紧凑模式）无需 payload 同步**：
- Compact 模式 areContentsTheSame 需增加 lastHost 比较触发全量刷新
- 新控件在 payloads.isEmpty 全量分支绑定即可：
```kotlin
if (payloads.isEmpty()) {
    // 全量绑定（含新增控件）
    tvSourceInitial.text = item.sourceInitial()
    tvBookSourceUrl.text = item.sourceUrlHost()
    vEnabledDot.isVisible = item.enabled
}
```

**RssSourceAdapter payloads 同步**：同 BookSourceAdapter，需增加 lastHost 比较和 upHost payload

**RssSourceAdapterCompact**：同 BookSourceAdapterCompact，无 payload 增量，全量分支绑定

### ADR-8: registerListener 必须保留所有原有事件监听器

**决策**：重构布局后，所有原有事件监听器必须保留并正常工作

**BookSourceAdapter（列表）** 保留：
- swtEnabled.setOnUserCheckedChangeListener → 切换启用
- cbBookSource.setOnUserCheckedChangeListener → 多选切换
- ivEdit.setOnClickListener → 进入编辑页
- ivMenuMore.setOnClickListener → 弹出菜单

**BookSourceAdapterCompact（紧凑）** 保留：
- swtEnabled.setOnUserCheckedChangeListener → 切换启用
- cbBookSource.setOnUserCheckedChangeListener → 多选切换
- root.setOnClickListener → 进入编辑页（**注意**：不是 ivEdit，紧凑模式用 root 点击）
- root.setOnLongClickListener → 删除（**注意**：不是 ivMenuMore，紧凑模式用 root 长按）

**RssSourceAdapter（订阅源列表）** 保留：
- swtEnabled/cbSource/ivEdit/ivMenuMore 同 BookSourceAdapter

**RssSourceAdapterCompact（订阅源紧凑）** 保留：
- swtEnabled/cbSource 同 BookSourceAdapterCompact
- root.setOnClickListener → 进入编辑页
- root.setOnLongClickListener → 删除

**BookSourceAdapterGrid / RssSourceAdapterGrid（网格）** 保留：
- root.setOnClickListener → 进入编辑页
- root.setOnLongClickListener → **选择切换**（**注意**：不是删除！网格模式用 root 长按切换选中状态）
- 选中状态用 ivSourceCover.backgroundTintList = Color.argb(120,33,150,243) 半透明蓝色遮罩表示

**注意**：紧凑列表的 root 点击进入编辑、root 长按删除的交互方式，重构布局后必须保证 vw_foreground 不干扰这些点击事件。网格的 ivSourceCover 必须支持 backgroundTintList 用于选中状态显示。

### ADR-9: BookSourceAdapterCompact 不支持拖拽排序

**决策**：紧凑列表不支持拖拽排序（注释明确说明 "简化说明：不支持拖拽排序和调试信息"）
- 拖拽排序仅在 layout=0（列表模式）+ 手动排序时启用
- 紧凑列表（layout=1）和网格（layout≥2）不启用拖拽
- 这简化了紧凑列表布局的设计，不需要考虑拖拽视觉反馈

**BookSourceActivity 拖拽条件（完整）**：
```
itemTouchCallback.isCanDrag = AppConfig.bookSourceSort == 0
    && sort == BookSourceSort.Default
    && layout == 0
    && !groupSourcesByDomain  // 按域名分组时不允许拖拽
```

**RssSourceActivity 拖拽条件（完整）**：
```
itemTouchCallback.isCanDrag = AppConfig.rssSort == 0 && layout == 0
```

**差异**：书源拖拽多了 `sort == BookSourceSort.Default` 和 `!groupSourcesByDomain` 两个条件，订阅源没有这两个条件

### ADR-10: RssSource 也有 enabled 字段

**决策**：vEnabledDot 可见性逻辑对订阅源也适用
- RssSource.enabled 字段存在（diffItemCallback 比较 enabled）
- vEnabledDot.visibility = if (item.enabled) View.VISIBLE else View.GONE 对订阅源同样适用

### ADR-11: sourceUrlHost() 必须复用 lastHost 字段（重要修正）

**决策**：sourceUrlHost() 不能直接从 sourceUrl 截取 host，必须复用 lastHost 字段

**根因**：项目记忆[2026-07-15 18:00]明确要求"源地址填写的多样性（jslib/注释/#规避等复杂情况）"，直接从 sourceUrl 截取 host 会得到错误结果

**关键约束（子代理审计A1修正）**：BookSourcePart 是独立 data class（不继承 BaseSource，无 getKey() 方法），必须分别定义两个扩展函数：

```kotlin
// 文件位置：app/src/main/java/io/legado/app/help/source/SourceExt.kt（新建）

// BookSourcePart 不继承 BaseSource，用 bookSourceUrl 字段
fun BookSourcePart.sourceUrlHost(): String {
    val origin = lastHost ?: bookSourceUrl
    return extractHost(origin)
}

// RssSource 继承 BaseSource，可用 getKey() 或 sourceUrl
fun RssSource.sourceUrlHost(): String {
    val origin = lastHost ?: sourceUrl
    return extractHost(origin)
}

// 通用 host 提取逻辑（参考 BookSourceActivity.kt L916-934 的 getSourceHost 方法）
private fun extractHost(origin: String): String {
    val trimmed = origin.trim()
    if (trimmed.isEmpty() || trimmed.equals("http", true) || trimmed.equals("https", true)
        || trimmed.startsWith("http:///", true) || trimmed.startsWith("https:///", true)
    ) return "#"
    return if (trimmed.startsWith("http", ignoreCase = true)) {
        NetworkUtils.getSubDomainOrNull(trimmed) ?: "#"
    } else {
        NetworkUtils.getSubDomainOrNull("http://$trimmed") ?: "#"
    }
}
```

**已有基础设施**：
- SourceLastHostHelper.kt：提供 lastHost 回填逻辑（AnalyzeUrl 解析后回填）
- BookSourceActivity.getSourceHost()：提供 host 提取逻辑（含异常输入处理）
- NetworkUtils.getSubDomainOrNull()：提供子域名提取

**影响**：design.md 的 `source.sourceUrlHost()` 调用会正确显示真实域名，而非 sourceUrl 中的复杂字符串

### ADR-12: sourceInitial() 复用 Grid Adapter 已有实现

**决策**：sourceInitial() 复用 BookSourceAdapterGrid L79 / RssSourceAdapterGrid L79 已有的简单实现，不搞复杂的中英文区分

**实现**：
```kotlin
fun BookSourcePart.sourceInitial(): String = bookSourceName.firstOrNull()?.toString() ?: ""
fun RssSource.sourceInitial(): String = sourceName.firstOrNull()?.toString() ?: ""
```

**优点**：与 Grid 模式行为完全一致，避免中英文/emoji/符号等边界情况的处理复杂度

### ADR-13: 订阅源列表布局字段差异（重要遗漏补全）

**决策**：订阅源列表布局与书源列表布局的字段差异必须明确

**订阅源列表相对书源列表的差异**：
- ❌ **无 iv_explore**：订阅源没有"发现URL"概念，不显示发现标识
- ❌ **无 iv_progressBar**：订阅源没有校验进度条（校验功能在 CheckRssSourceService 中，不在列表Adapter显示进度）
- ❌ **无 tv_debug_text**：订阅源没有调试信息字段（可改为显示"最后更新时间"或"文章数"，参考spec.md REQ-3）
- ✅ **有 tv_host_text**：订阅源也支持域名分组（RssSourceActivity 可选实现，需确认是否有 getSourceHost 方法）

**订阅源列表布局控件清单（相对item_book_source.xml的差异）**：
- 保留：iv_source_cover / tv_source_initial / v_enabled_dot / cb_source / tv_rss_source_url / swt_enabled / iv_edit / iv_menu_more / tv_host_text / vw_foreground
- 移除：iv_explore / iv_progressBar / tv_debug_text
- 替代：tv_debug_text → tv_last_update（显示最后更新时间，参考item_bookshelf_list.xml的tv_last_update_time字段）

**RssSource 数据字段支持**：
- ✅ **RssSource有 lastUpdateTime: Long 字段**（已验证，RssSource.kt L102）
- tv_last_update 显示 lastUpdateTime 转换后的时间字符串（参考item_bookshelf_list.xml的tv_last_update_time字段）

### ADR-14: 当前布局文件根布局差异（重要遗漏补全）

**决策**：当前 item_rss_source.xml 用 LinearLayout 根布局，重构时需改为 ConstraintLayout

**当前布局文件状态**：
- item_book_source.xml：✅ ConstraintLayout（已重构，参考item_bookshelf_list.xml）
- item_book_source_compact.xml：✅ ConstraintLayout（当前简单布局，待重构为参考item_bookshelf_list2.xml）
- item_book_source_grid.xml：✅ ConstraintLayout（已对齐书架，无需修改）
- item_rss_source.xml：⚠️ **LinearLayout**（待重构为ConstraintLayout）
- item_rss_source_compact.xml：✅ ConstraintLayout（当前简单布局，待重构）
- item_rss_source_grid.xml：✅ ConstraintLayout（已对齐书架，无需修改）

**影响**：item_rss_source.xml 从 LinearLayout 改为 ConstraintLayout 后，所有子控件的 layout参数需要重新设计（layout_weight → constraint约束）

### ADR-15: RssSourceActivity.getSourceHost 已有但异常输入处理不完整（子代理审计A3修正）

**决策**：RssSourceActivity.getSourceHost 需对齐 BookSourceActivity.getSourceHost 的异常输入处理

**BookSourceActivity.getSourceHost**（L916-934）：
- 异常输入（空/"http"/"https"/"http:///"/"https:///"）返回 "#"
- 正常输入走 NetworkUtils.getSubDomainOrNull

**RssSourceActivity.getSourceHost**（L597-609）：
- **无异常输入处理**（空字符串会走 else 分支 `getSubDomainOrNull("http://") ?: origin` 返回空串）
- else 分支 fallback 是 `?: origin`（返回原值），与BookSourceActivity的 `?: "#"` 不一致

**风险**：订阅源 lastHost 为空或异常时，分组标题显示空字符串而非 #，isItemHeader 判断（连续空 host 误判为同组）失效

**修复方案**：RssSourceActivity.getSourceHost 对齐 BookSourceActivity 的异常输入处理（空/http/https/http:/// 返回 #）

**影响**：
- ✅ 订阅源列表布局的 tv_host_text 可直接使用 RssSourceActivity.getSourceHost
- ✅ RssSourceAdapter 需新增 upSourceHost 方法（参考BookSourceAdapter的upSourceHost）
- ✅ RssSourceAdapter 的 onCurrentListChanged 需触发 upSourceHost 更新
- ✅ RssSourceActivity.getSourceHost 需修复异常输入处理（对齐 BookSourceActivity）

**新增任务（子代理审计A2/B1）**：tasks.md 需拆解订阅源 upSourceHost 改造任务：
1. RssSourceAdapter.CallBack 接口新增 `fun getSourceHost(origin: String): String`
2. RssSourceActivity.getSourceHost 从 private 改为 override，并修复异常输入处理
3. RssSourceAdapter 新增 showSourceHost 字段 + upSourceHost + isItemHeader + getHeaderText
4. RssSourceAdapter.onCurrentListChanged 触发 upSourceHost 更新
5. RssSourceActivity 设置 adapter.showSourceHost = groupSourcesByDomain

### ADR-16: 订阅源列表布局重构后的控件ID命名规范

**决策**：订阅源列表布局的控件ID命名与书源列表保持一致风格

**控件ID命名对照**：
| 控件 | 书源列表ID | 订阅源列表ID | 说明 |
|------|----------|------------|------|
| CheckBox | cb_book_source | cb_source | 已有命名保持 |
| URL显示 | tv_book_source_url | tv_rss_source_url | 命名风格一致 |
| 首字 | tv_source_initial | tv_source_initial | 完全一致 |
| 启用点 | v_enabled_dot | v_enabled_dot | 完全一致 |
| 封面容器 | iv_source_cover | iv_source_cover | 完全一致 |
| 开关 | swt_enabled | swt_enabled | 完全一致 |
| 编辑 | iv_edit | iv_edit | 完全一致 |
| 更多 | iv_menu_more | iv_menu_more | 完全一致 |
| 分组标题 | tv_host_text | tv_host_text | 完全一致 |
| 最后更新 | - | tv_last_update | 订阅源独有 |

**ViewBinding 自动生成**：tv_rss_source_url → tvRssSourceUrl，tv_last_update → tvLastUpdate

### ADR-17: item_rss_source_grid.xml 已对齐书架，无需修改（子代理审计B3修正）

**决策**：item_rss_source_grid.xml 当前 tv_source_name 已是 12sp lines=2 center_horizontal，与书架网格 item_bookshelf_grid.xml 完全一致，无需修改

**修正**：spec.md REQ-5 / tasks.md T2.4 标记为"已对齐，无需修改"

**影响**：tasks.md 删除 T2.4 任务项，减少工作量

### ADR-18: 紧凑列表重构字号 14sp→16sp（子代理审计B4修正）

**决策**：紧凑列表重构时 cb_book_source/cb_source 字号从 14sp 改为 16sp（对齐书架紧凑列表 item_bookshelf_list2.xml 的 tv_name 16sp）

**当前状态**：
- item_book_source_compact.xml L20：cb_book_source 14sp
- item_rss_source_compact.xml L20：cb_source 14sp

**目标状态**：
- item_book_source_compact.xml：cb_book_source 16sp
- item_rss_source_compact.xml：cb_source 16sp

**影响**：tasks.md T1.2/T2.3 显式说明字号变更

### ADR-19: 紧凑列表重构后的完整控件约束链（子代理审计B5补全）

**决策**：紧凑列表重构后的控件约束链需明确，避免 ivTypeBadge 与首字图标重叠

**item_book_source_compact.xml 重构后控件清单**：
```
ConstraintLayout (root)
├── FrameLayout iv_source_cover (48x64dp, constraintLeft_toLeftOf=parent)
│   ├── TextView tv_source_initial (20sp白色加粗, 居中)
│   └── View v_enabled_dot (8dp, 右上角)
├── ThemeCheckBox cb_book_source (16sp, constraintLeft_toRightOf=iv_source_cover, constraintRight_toLeftOf=iv_type_badge)
├── TextView tv_book_source_url (13sp, constraintLeft_toRightOf=iv_source_cover, constraintRight_toLeftOf=iv_type_badge, constraintTop_toBottomOf=cb_book_source)
├── TextView iv_type_badge (10sp, constraintRight_toLeftOf=swt_enabled)
└── ThemeSwitch swt_enabled (constraintRight_toRightOf=parent)
```

**ivTypeBadge 位置**：放在 cb_book_source 右侧、swt_enabled 左侧（保持当前位置，约束链不变）

### ADR-20: tv_last_update 字段绑定与格式化（子代理审计B2补全）

**决策**：订阅源列表的 tv_last_update 显示 lastUpdateTime 转换后的时间字符串

**实现**：
- RssSourceAdapter.convert 绑定 `tvLastUpdate.text = formatDate(item.lastUpdateTime)`
- areContentsTheSame 增加 lastUpdateTime 比较触发刷新
- 时间格式化复用项目已有的 DateUtils 或 Book 的时间格式化方法（实施时搜索确认）

**边界情况**：
- lastUpdateTime == 0L：显示空字符串或隐藏 tvLastUpdate
- lastUpdateTime 非0：格式化为"yyyy-MM-dd HH:mm"或相对时间（如"3小时前"）

### ADR-21: BookSourceAdapter.getHeaderText 用 bookSourceUrl 而非 lastHost（子代理审计B7说明）

**决策**：tv_host_text 分组标题用 bookSourceUrl（已有逻辑保持不变），tv_book_source_url 行内域名用 lastHost 优先（新增）

**差异说明**：
- BookSourceAdapter.getHeaderText（L301）：`callBack.getSourceHost(source.bookSourceUrl)` 用 bookSourceUrl
- ADR-11 sourceUrlHost()：`lastHost ?: bookSourceUrl` 用 lastHost 优先

**风险**：分组标题与行内域名 host 来源不同，可能显示不一致（如 lastHost 已回填但 bookSourceUrl 含 jslib 注释）

**处理方案**：保持现状不改 getHeaderText（避免回归风险），行内域名用 lastHost 优先正确显示真实域名。分组标题仍按 bookSourceUrl 分组（已有逻辑稳定）。

**影响**：分组标题和行内域名可能略有差异，但都不崩溃，功能正常

## Data Flow

### 列表布局渲染流程

```
BookSourceActivity.onCreate
  → setupRecyclerView()
    → applyListView()
      → when(layout):
        0 -> adapter (item_book_source.xml)
        1 -> adapterCompact (item_book_source_compact.xml)
        2+ -> adapterGrid (item_book_source_grid.xml)
  → upSourceFlow() -> adapter.setData(sources)

BookSourceAdapter.bindViewHolder
  → binding.cb_book_source.text = source.name  (原有)
  → binding.cb_book_source.isChecked = source.selected  (原有)
  → binding.swt_enabled.isChecked = source.enabled  (原有)
  → binding.iv_edit.setOnClickListener { edit }  (原有)
  → binding.iv_menu_more.setOnClickListener { showMenu }  (原有)
  → binding.tv_source_initial.text = source.sourceInitial()  (新增)
  → binding.tv_book_source_url.text = source.sourceUrlHost()  (新增, 脱敏显示域名)
  → binding.v_enabled_dot.visibility = if(source.enabled) VISIBLE else GONE  (新增)
```

## File Changes

### 已完成

| 文件 | 变更类型 | 说明 |
|------|---------|------|
| `app/src/main/res/layout/item_book_source.xml` | 完全重写 | 参考 item_bookshelf_list.xml 重构为「左侧66x90dp首字图标 + 右侧多字段 + 右侧操作按钮」结构 |

### 待实施

#### 布局XML（5个）

| 文件 | 变更类型 | 说明 |
|------|---------|------|
| `app/src/main/res/layout/item_book_source_compact.xml` | 完全重写 | 参考 item_bookshelf_list2.xml 重构为「左侧48x64dp首字图标 + 合并行」 |
| `app/src/main/res/layout/item_rss_source.xml` | 完全重写 | 参考 item_book_source.xml 结构 |
| `app/src/main/res/layout/item_rss_source_compact.xml` | 完全重写 | 参考 item_book_source_compact.xml 结构 |
| `app/src/main/res/layout/item_book_source_grid.xml` | 优化字号 | tv_source_name 12sp 2行居中（已对齐，仅确认） |
| `app/src/main/res/layout/item_rss_source_grid.xml` | 优化字号 | tv_source_name 12sp 2行居中 |

#### Adapter代码适配（4个 - 重要遗漏补全）

**子代理调查误报已绑定新控件，实际验证 BookSourceAdapter.kt convert方法（L95-126）只绑定 cbBookSource/swtEnabled/ivExplore/ivDebugText/tvHostText，未绑定 tvSourceInitial/tvBookSourceUrl/vEnabledDot/ivSourceCover！必须新增绑定代码。**

| 文件 | 当前绑定 | 待新增绑定 |
|------|---------|-----------|
| `BookSourceAdapter.kt` (列表) | cbBookSource, swtEnabled, ivExplore, ivDebugText(通过upCheckSourceMessage), tvHostText(通过upSourceHost), ivProgressBar, ivEdit, ivMenuMore | **tvSourceInitial.text=首字**, **tvBookSourceUrl.text=域名**, **vEnabledDot.visibility=enabled?VISIBLE:GONE** |
| `BookSourceAdapterCompact.kt` (紧凑) | cbBookSource, swtEnabled, ivTypeBadge | 重构布局后需新增 tvSourceInitial/tvBookSourceUrl/vEnabledDot 绑定 |
| `RssSourceAdapter.kt` (订阅源列表) | cbSource, swtEnabled, ivEdit, ivMenuMore | 重构布局后需新增 tvSourceInitial/tvBookSourceUrl/vEnabledDot 绑定 |
| `RssSourceAdapterCompact.kt` (订阅源紧凑) | cbSource, swtEnabled, ivTypeBadge | 重构布局后需新增 tvSourceInitial/tvBookSourceUrl/vEnabledDot 绑定 |
| `BookSourceAdapterGrid.kt` (书源网格) | tvSourceInitial, vEnabledDot, ivSourceCover | 已绑定（无需修改） |
| `RssSourceAdapterGrid.kt` (订阅源网格) | tvSourceInitial, vEnabledDot, ivSourceCover | 已绑定（无需修改） |

**新增绑定代码示例**（在 convert 方法的 `if (payloads.isEmpty())` 块内）：

```kotlin
// 新增：首字图标
tvSourceInitial.text = item.sourceInitial()
// 新增：域名（脱敏显示，仅显示host）
tvBookSourceUrl.text = item.sourceUrlHost()
// 新增：启用状态点
vEnabledDot.visibility = if (item.enabled) View.VISIBLE else View.GONE
```

**payloads 增量更新需补全**：

```kotlin
"enabled" -> {
    swtEnabled.isChecked = bundle.getBoolean("enabled")
    vEnabledDot.visibility = if (bundle.getBoolean("enabled")) View.VISIBLE else View.GONE  // 新增
}
"upName" -> {
    cbBookSource.text = item.getDisPlayNameGroup()
    tvSourceInitial.text = item.sourceInitial()  // 新增
}
```

#### Activity 代码（2个）

| 文件 | 变更类型 | 说明 |
|------|---------|------|
| `BookSourceActivity.kt` | 检查 | 确认 layout=0/1/2+ 分支与adapter对应（applyListView 已存在） |
| `RssSourceActivity.kt` | 检查 | 确认 layout=0/1/2+ 分支与adapter对应（applyListView 已存在，订阅源已有列表模式layout=0用adapter） |

#### 扩展函数（1个）

| 文件 | 变更类型 | 说明 |
|------|---------|------|
| `SourceExt.kt` 或新建扩展函数文件 | 新增扩展函数 | `sourceInitial()` 取首字（中英文兼容+空值处理）+ `sourceUrlHost()` 提取域名（脱敏） |

### 验证结论：资源全部就绪

- ✅ `bg_source_folder_cover.xml`：主题色渐变（colorPrimary + 135度黑色叠加），暗色主题下自动适配
- ✅ `bg_source_enabled_dot.xml`：绿色圆点（md_green_600, 8dp）
- ✅ `ic_history.xml` / `ic_author.xml` / `ic_edit.xml` / `ic_more_vert.xml`
- ✅ 所有6个Adapter使用 ViewBinding，新增控件ID会自动生成 binding.tvSourceInitial 等
- ✅ 订阅源已有列表模式（RssSourceActivity.applyListView layout=0 用 adapter，无需新增adapter）
- ✅ 拖拽排序在 `rssSort == 0 && layout == 0` 时启用，不依赖特定控件ID，布局重构不影响
- ✅ 多选用 DragSelectTouchHelper.Callback，通过 selected 集合维护，不依赖特定控件ID

## Implementation Order

1. **设计文档审查**（当前）→ AskUserQuestion 确认
2. 重构 item_book_source_compact.xml（参考 item_bookshelf_list2.xml）
3. 重构 item_rss_source.xml（参考 item_book_source.xml）
4. 重构 item_rss_source_compact.xml（参考 item_book_source_compact.xml）
5. 优化 item_rss_source_grid.xml 字号
6. 新增 sourceInitial() + sourceUrlHost() 扩展函数
7. 修改 Adapter bindViewHolder 绑定新控件
8. 调查订阅源 layout=0 分支是否需要新增列表模式
9. 编译验证
10. 真机测试（3种模式切换 + 多选/编辑/更多按钮）

## Risks & Mitigations

### Risk 1: Adapter 代码修改引入回归

**风险**：修改 bindViewHolder 可能影响原有功能

**缓解**：
- 保留原有控件ID不变，仅新增控件绑定
- 修改前后用 Grep 确认原有绑定代码完整
- 真机测试每个原有功能（多选/启用/编辑/更多）

### Risk 2: drawableTint 在低版本失效

**风险**：drawableTint 在 API 21 以下可能失效

**缓解**：
- 本项目 minSdk=23，满足要求
- 添加 `tools:ignore="UseCompatTextViewDrawableXml"` 忽略 lint 警告

### Risk 3: 首字提取边界情况

**风险**：源名称为空、纯符号、emoji等情况下首字提取异常

**缓解**：
- 扩展函数 sourceInitial() 增加空值/边界情况处理
- 空名称显示"?"

### Risk 4: 订阅源列表模式新增可能影响现有adapter

**风险**：RssSourceActivity 当前可能没有列表模式adapter

**缓解**：
- 先调查 RssSourceActivity.applyListView 现状
- 根据现状决定是新增adapter还是复用现有adapter

## Verification

### 单元测试

- sourceInitial() / sourceUrlHost() 扩展函数的边界情况（空/emoji/纯英文/纯中文）

### 真机测试

- 编译安装后真机验证：
  - 书源列表模式（layout=0）视觉与书架列表一致
  - 书源紧凑列表模式（layout=1）视觉与书架紧凑列表一致
  - 书源网格模式（layout=2+）视觉与书架网格一致
  - 订阅源3种模式同上
  - 多选/启用开关/编辑/更多按钮全部可用
  - 切换3种模式不崩溃

### 回归测试

- 验证书源分组功能正常（分组菜单显示+分组列表）
- 验证订阅源排序功能正常
- 验证类型筛选功能正常
