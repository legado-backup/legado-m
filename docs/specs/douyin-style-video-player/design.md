# Design: 抖音风格沉浸式竖屏视频播放器重设计

> **状态**：✅ 设计通过（OpenSpec 检查点1 第5次通过）
> **创建日期**：2026-07-10
> **架构方案**：ViewPager2 + Fragment 垂直滑动切换

## 1. Technical Approach（技术方案）

### 1.1 架构总览

**当前架构**（传统竖屏 LinearLayout）：
```
VideoPlayerActivity（单 Activity，持有所有逻辑）
├── TitleBar（标题栏）
├── VideoPlayer / GSY（播放器，半屏高度）
├── rss_video_panel（订阅源功能区：播放地址/快进快退/倍速/调试/多集/简介）
├── data（书籍信息区：封面/书名/作者/简介）
├── chapters_container（章节区：卷列表/章节列表）
└── debug_panel（调试面板）
```

**目标架构**（抖音风格沉浸式）：
```
VideoPlayerActivity（容器，持有 ViewPager2 + 状态管理）
├── ViewPager2（ORIENTATION_VERTICAL，垂直滑动切换）
│   └── VideoFragment × N（每个视频一个 Fragment）
│       ├── PlayerView（ExoPlayer/GSY，铺满屏幕，match_parent）
│       ├── 悬浮控件层（ConstraintLayout 叠加在 PlayerView 上）
│       │   ├── 左下角：tv_video_title（视频标题）
│       │   ├── 右侧竖直：btn_mute / btn_favorite / btn_speed / btn_settings
│       │   └── 下方居中：btn_fullscreen（仅横屏比例视频显示）
│       └── 设置面板入口（btn_settings → VideoSettingsDialog）
└── 状态管理器（STATE_PURE / STATE_NORMAL / STATE_FULLSCREEN）
```

### 1.2 ViewPager2 + Fragment 设计

**核心组件**：

| 组件 | 职责 | 生命周期 |
|------|------|---------|
| `VideoPlayerActivity` | 容器，持有 ViewPager2，管理视频列表数据，处理全局事件 | Activity 生命周期 |
| `VideoPagerAdapter` | FragmentStateAdapter，创建/复用 VideoFragment | 跟随 ViewPager2 |
| `VideoFragment` | 单个视频播放单元，持有播放器 + 悬浮控件 + 手势处理 | Fragment 生命周期 |

**ViewPager2 配置**：
```kotlin
binding.viewPager.apply {
    orientation = ViewPager2.ORIENTATION_VERTICAL
    offscreenPageLimit = 1  // 只保留相邻1页，节省内存
    registerOnPageChangeCallback(object : ViewPager2.OnPageChangeCallback() {
        override fun onPageSelected(position: Int) {
            // 新页面选中：自动播放 + 进入纯净态
            // 旧页面：释放播放器
        }
    })
    adapter = videoPagerAdapter
}
```

**数据传递机制**：
- `VideoPlayerActivity` 持有视频列表数据（`rssEpisodes` 或 `bookChapters`）
- 通过 `VideoPagerAdapter.createFragment(position)` 创建 VideoFragment
- VideoFragment 通过 `arguments` Bundle 接收：`videoUrl` / `videoTitle` / `position` / `sourceType`
- 复杂数据（Book/RssSource）通过 `VideoPlay` 单例传递（保持现有机制）

**播放器实例管理策略**：
- 当前页 VideoFragment：持有活跃播放器实例，正在播放
- 相邻页（offscreenPageLimit=1）：Fragment 存在但暂停播放器（释放解码器，保留视图）
- 远离页：Fragment 被 ViewPager2 销毁，播放器完全释放
- 切换时序：旧页 `pausePlayer()` → 新页 `resumePlayer()` + `play()`

### 1.3 三种状态设计

**状态枚举**：
```kotlin
enum class VideoPlayState {
    STATE_PURE,       // 纯净播放态：所有控件隐藏，仅视频画面
    STATE_NORMAL,     // 竖屏常态：显示标题+功能按钮+全屏按钮
    STATE_FULLSCREEN  // 横屏全屏态：Activity横屏，视频铺满，功能按钮适配
}
```

**状态转换图**：
```
                    ┌─────────────────────────────┐
                    │                             │
                    ▼                             │
            ┌──────────────┐              ┌──────────────┐
            │  STATE_PURE  │──单击──▶     │ STATE_NORMAL │
            │  (纯净播放)  │◀──单击──     │  (竖屏常态)  │
            └──────────────┘              └──────┬───────┘
                    │                            │
                    │ 双指缩放                    │ 点击全屏按钮
                    │                            ▼
                    │                    ┌───────────────┐
                    └──────────────────▶│ STATE_FULLSCREEN│
                                         │ (横屏全屏态)   │
                                         └───────┬───────┘
                                                 │ 返回键/全屏按钮
                                                 ▼
                                         返回 STATE_NORMAL
```

**各状态控件可见性**：

| 控件 | STATE_PURE | STATE_NORMAL | STATE_FULLSCREEN |
|------|-----------|--------------|------------------|
| 视频画面 | ✅ 铺满 | ✅ 铺满 | ✅ 横屏铺满 |
| 左下角标题 | ❌ 隐藏 | ✅ 显示 | ✅ 显示（适配横屏） |
| 右侧功能按钮 | ❌ 隐藏 | ✅ 显示 | ✅ 显示（适配横屏） |
| 下方全屏按钮 | ❌ 隐藏 | ✅ 显示（仅横屏比例视频） | ❌ 隐藏（已是全屏） |
| 设置面板 | ❌ | ❌（点击设置按钮弹出） | ❌（点击设置按钮弹出） |

### 1.4 悬浮控件布局设计

**fragment_video.xml 布局结构**：
```xml
<ConstraintLayout match_parent × match_parent>
    <!-- 播放器视图（铺满屏幕） -->
    <PlayerView 0dp × 0dp, constraints=all/>

    <!-- 悬浮控件层（叠加在播放器上） -->
    <ConstraintLayout match_parent × match_parent>
        <!-- 左下角：视频标题 -->
        <TextView id=tv_video_title
            constraints={bottom_toBottom=parent, start_toStart=parent}
            maxLines=2, ellipsize=end, textColor=white, bgColor=semi-transparent/>

        <!-- 右侧竖直功能按钮容器 -->
        <LinearLayout id=right_buttons_container
            orientation=vertical, gravity=center
            constraints={top_toTop=parent, bottom_toBottom=parent, end_toEnd=parent}>
            <ImageButton id=btn_mute .../>
            <ImageButton id=btn_favorite .../>
            <ImageButton id=btn_speed .../>
            <ImageButton id=btn_settings .../>
        </LinearLayout>

        <!-- 下方居中：全屏按钮（仅横屏比例视频显示） -->
        <ImageButton id=btn_fullscreen
            constraints={bottom_toBottom=parent, start_toStart=parent, end_toEnd=parent}
            visibility=gone（默认隐藏，横屏比例视频时显示）/>
    </ConstraintLayout>
</ConstraintLayout>
```

**控件样式规范**（抖音风格）：
- 图标尺寸：48dp × 48dp
- 图标颜色：白色（#FFFFFF）
- 背景：半透明圆形（#80000000，12dp 圆角）
- 间距：功能按钮间距 16dp
- 标题：14sp，白色，半透明背景（#80000000），padding 12dp

### 1.5 横屏适配设计

**横屏比例视频检测**：
```kotlin
// 在 onPrepared / onVideoSizeChanged 中检测
val aspectRatio = videoWidth.toFloat() / videoHeight.toFloat()
val isLandscapeVideo = aspectRatio > 1.2  // 宽高比>1.2 判定为横屏视频
```

**等比缩放居中展示**（竖屏容器内显示横屏视频）：
- 使用 `ResizeMode.RESIZE_MODE_ZOOM` 或自定义 `TextureView` 变换
- 保持原始宽高比，居中展示，上下留黑边（letterbox）
- 不拉伸、不裁剪

**全屏切换逻辑**：
```kotlin
fun toggleFullScreen() {
    state = if (state == STATE_NORMAL) {
        requestedOrientation = ActivityInfo.SCREEN_ORIENTATION_SENSOR_LANDSCAPE
        STATE_FULLSCREEN
    } else {
        requestedOrientation = ActivityInfo.SCREEN_ORIENTATION_SENSOR_PORTRAIT
        STATE_NORMAL
    }
    updateControlsVisibility()
}
```

**双指缩放手势**：
```kotlin
val scaleDetector = ScaleGestureDetector(requireContext(), object : SimpleOnScaleGestureListener() {
    override fun onScaleEnd(detector: ScaleGestureDetector) {
        if (detector.scaleFactor > 1.2f && state != STATE_FULLSCREEN) {
            toggleFullScreen()  // 双指向外拉伸 > 1.2 触发全屏
        }
    }
})
```

### 1.6 设置面板设计（100%功能保留）

**VideoSettingsDialog（BottomSheetDialogFragment）**：

将当前 VideoPlayerActivity 的所有功能重新组织到设置面板：

```
VideoSettingsDialog
├── 播放控制区
│   ├── 快进快退：←30s / ←10s / 10s→ / 30s→
│   └── 倍速选择：Spinner（0.5x/0.75x/1.0x/1.25x/1.5x/2.0x/3.0x）
├── 播放地址区
│   ├── 当前地址展示（tv_video_url，可展开/折叠）
│   └── 复制地址按钮（btn_copy_url）
├── 多集选择区
│   ├── 上一集 / 下一集按钮
│   └── 集数列表（RecyclerView，rssEpisodes 或 bookChapters）
├── 视频简介区
│   └── tv_rss_description（订阅源模式）
├── 书籍信息区（书籍源模式）
│   ├── 封面（iv_cover）
│   ├── 书名（tv_name）/ 作者（tv_author）
│   └── 简介（tv_intro_container）
├── 章节/卷选择区（书籍源模式）
│   ├── 卷列表（volumes）
│   └── 章节列表（chapters）+ 章节按钮（iv_chapter）
├── 调试面板区
│   ├── 调试开关（btn_toggle_debug）
│   └── 调试日志（tv_debug_log）
└── 菜单功能区
    ├── 自定义按钮（menu_custom_btn）
    ├── 收藏（menu_rss_star）
    ├── 悬浮窗（menu_float_window）
    ├── 配置设置（menu_config_settings）
    ├── 登录（menu_login）
    ├── 复制URL（menu_copy_video_url）
    ├── 其他播放器（menu_open_other_video_player）
    ├── 编辑源（menu_edit_source）
    └── 日志（menu_log）
```

### 1.7 3003 Bug 修复设计

**问题根因**：R5 VideoUrlExtractor 从文章页面抓取到的 URL 是播放器页面 URL（如 `danmutv.cc/player/?url=...`），而非直接视频流 URL。实际视频流 URL 嵌在 `?url=` 参数中。

**修复方案**：在 VideoUrlExtractor 的提取流程末尾增加"播放器页面 URL 识别与解析"步骤：

```kotlin
/**
 * 识别播放器页面 URL 并提取实际视频流 URL
 * 场景：danmutv.cc/player/?url=https%3A%2F%2Fv.baofeng11.com%2Fvideo%2F...%2Findex.m3u8
 */
private fun extractPlayerPageUrl(url: String): String? {
    // 1. 检测是否是播放器页面 URL（包含 ?url= 或 &url= 参数）
    val urlPattern = Regex("""[?&]url=([^&]+)""")
    val match = urlPattern.find(url) ?: return null

    // 2. 提取 url 参数值
    val encodedUrl = match.groupValues[1]

    // 3. URL 解码
    val actualVideoUrl = URLDecoder.decode(encodedUrl, "UTF-8")

    // 4. 验证解码后的 URL 是否是合法的视频流 URL
    return if (isValidVideoUrl(actualVideoUrl)) actualVideoUrl else null
}
```

**集成位置**：在 R5 现有五种提取方法之后，作为第六种提取方法。

## 2. Architecture Decisions（架构决策）

### ADR-1: ViewPager2 + Fragment vs RecyclerView vs 单Activity

**Context**：需要实现抖音风格的垂直滑动切换视频功能。

**Decision**：选择 ViewPager2 + Fragment 方案。

**Y-Statement**：
- **Why**：ViewPager2 原生支持垂直方向滑动，Fragment 生命周期管理清晰，可复用现有 Fragment 基础设施。RecyclerView 播放器实例管理复杂，单 Activity 无滑动动画体验差。
- **Consequences**：架构改动较大，需处理 Fragment 间播放器实例管理；但获得原生抖音体验，滑动流畅。

### ADR-2: Fragment 播放器实例管理策略

**Context**：多个 VideoFragment 需要管理播放器实例的创建/释放/复用。

**Decision**：使用 `setOffscreenPageLimit(1)` + Fragment 生命周期管理。

**Y-Statement**：
- **Why**：只保留相邻1页 Fragment，平衡内存占用和滑动流畅度。当前页播放，相邻页暂停（释放解码器保留视图），远离页销毁。
- **Consequences**：滑动时可能有轻微加载延迟；但内存占用可控（不超过当前+30%）。

### ADR-3: 控件显隐动画方案

**Context**：需要在纯净态和常态之间平滑切换控件显隐。

**Decision**：使用 alpha + translationY 动画（300ms）。

**Y-Statement**：
- **Why**：alpha 动画平滑过渡，translationY 增加上升/下降效果，符合抖音视觉风格。300ms 是 Material Design 标准动画时长。
- **Consequences**：动画期间控件不可点击（动画结束后才可交互）；但用户体验更好。

### ADR-4: 设置面板实现方案

**Context**：需要将当前所有功能（45+方法、9个菜单项、多个功能区）重新组织到设置面板。

**Decision**：使用 BottomSheetDialogFragment。

**Y-Statement**：
- **Why**：BottomSheetDialogFragment 是 Material Design 标准组件，从底部滑出符合抖音交互习惯，支持滚动内容，不干扰视频播放。可复用现有 Fragment 基础设施。
- **Consequences**：设置面板内容较多时需滚动；但功能完整保留，用户可随时访问。

### ADR-5: 3003 Bug 修复方案

**Context**：R5 抓取返回播放器页面 URL 而非视频流 URL。

**Decision**：在 VideoUrlExtractor 末尾增加播放器页面 URL 识别方法。

**Y-Statement**：
- **Why**：最小化改动，不重构现有五种提取方法，只在末尾增加第六种识别方法。符合 O3（不重构 R5 核心提取逻辑）的 Out of Scope 约束。
- **Consequences**：只能处理 `?url=` 参数模式的播放器页面 URL；但覆盖 R2 日志发现的 3003 Bug 场景。

### ADR-6: 书籍源模式兼容方案

**Context**：书籍源有章节/卷结构，非视频列表，不适合 ViewPager2 垂直滑动。

**Decision**：书籍源模式（book != null）禁用 ViewPager2 滑动，只显示单个 VideoFragment。

**Y-Statement**：
- **Why**：书籍源的视频章节是线性结构，用户通过章节列表切换而非滑动。保持现有章节选择逻辑可确保向后兼容（NFR-4）。
- **Consequences**：书籍源模式无滑动切换功能；但保持现有交互逻辑不变，降低回归风险。

### ADR-7: 多线路数据结构方案

**Context**：视频详情页有多个播放线路（如奈飞中文网9个线路×14子线路×N集），当前 RssEpisode 扁平结构无法表达"多线路×多集"二维结构。

**Decision**：新增 RssRoute 二级嵌套数据类，与书源 volumes/episodes 范式对称。

**Y-Statement**：
- **Why**：
  - 书源场景已有 `volumes`（卷=线路）+ `episodes`（集）+ `durVolumeIndex` + `chapterInVolumeIndex` 的成熟范式，订阅源场景应与之对称
  - 二级嵌套结构清晰，UI 可复用 SwitchVideoAdapter 做线路切换
  - `rssEpisodes` 保持为"当前线路的集数列表"（= rssRoutes[rssRouteIndex].episodes），100%兼容现有 playRssEpisode 逻辑
- **Consequences**：
  - 需新增 RssRoute 类 + parseRssRoutes 解析逻辑
  - 需在 releaseAllVideos() 等重置点同步重置 rssRoutes/rssRouteIndex
  - 但获得清晰的多线路多集表达能力，且单线路场景自动退化兼容

**数据结构设计**：
```kotlin
// 新增数据类
@Parcelize
data class RssRoute(
    var name: String = "",                    // 线路名称，如"线路1"/"高清"/"LZ线路"
    var episodes: List<RssEpisode> = emptyList()  // 该线路的集数列表
) : Parcelable

// VideoPlay 新增字段（model/VideoPlay.kt L150 附近）
var rssRoutes: List<RssRoute>? = null    // 多线路列表（null=单URL场景）
var rssRouteIndex: Int = 0               // 当前线路索引
// rssEpisodes 保持不变，始终 = rssRoutes?.get(rssRouteIndex)?.episodes（兼容现有逻辑）
```

### ADR-8: 多线路 UI 布局方案

**Context**：用户要求"左下方名称下方选择播放线路+选择播放哪一集"，需在悬浮控件层增加线路选择器和集数选择器。

**Decision**：左下角标题下方垂直排列线路选择器 + 集数选择器，根据数据自动显隐。

**Y-Statement**：
- **Why**：
  - 左下角垂直排列符合抖音风格（标题在下方便于阅读）
  - 线路选择器在上、集数在下，符合"先选线路再选集"的操作逻辑
  - 自动显隐（单URL全隐藏/多集无线路隐藏线路/多线路全显示）确保通用性
- **Consequences**：
  - 多线路时左下角控件较多，需控制高度（线路选择器单行 + 集数横向滚动）
  - 但用户体验完整，且兼容所有场景

**UI 布局设计**：
```
┌─────────────────────────────────────┐
│                              [静音] │
│                              [收藏] │
│         视频画面             [倍速] │
│                              [设置] │
│                                     │
│ 视频标题（左下角）                   │
│ [线路1 ▼]（线路选择器，多线路时显示）│
│ [第1集][第2集][第3集]...（横向滚动） │
│              [全屏]                 │
└─────────────────────────────────────┘
```

### ADR-9: R5 多线路通用抓取策略

**Context**：不同视频网站的多线路 DOM 结构差异很大（Tab式/分组式/多级嵌套），R5 自动抓取不能硬编码特定网站逻辑，需设计通用策略。

**Decision**：三层通用性设计——ruleContent 用户自定义优先 + R5 智能模式识别回退 + skill 编写指南辅助。

**Y-Statement**：
- **Why**：
  - Legado 核心哲学是用户编写规则（CSS/JSONPath/XPath/Regex/JS），AI 不硬编码特定网站
  - ruleContent 用户自定义规则通用性最高，适用于任何网站
  - R5 智能回退只识别通用 DOM 模式，不针对特定网站
  - skill 编写指南降低用户编写难度，提供模板和示例
- **Consequences**：
  - ruleContent 为空时 R5 智能回退覆盖率有限（约60-70%常见模式）
  - 但通过 skill 指南，用户可快速编写 ruleContent 覆盖任何网站
  - 符合 Legado 哲学，通用性由用户规则保证

**三层设计详解**：

#### 第一层：ruleContent 用户自定义规则（通用性最高，推荐）

用户通过 ruleContent 编写 JS，返回 `List<RssRoute>` 嵌套结构：

```javascript
// ruleContent JS 示例（通用模板）
// 用户根据目标网站 DOM 编写，返回多线路多集数据
<js>
(() => {
    const routes = [];
    // 1. 选择所有线路分组
    const routeGroups = document.querySelectorAll('.playlist-group');
    routeGroups.forEach((group, routeIndex) => {
        const routeName = group.querySelector('.route-title')?.textContent || `线路${routeIndex + 1}`;
        const episodes = [];
        // 2. 选择该线路下的所有集数
        group.querySelectorAll('.episode-link').forEach((link, epIndex) => {
            episodes.push({
                title: link.textContent.trim() || `第${epIndex + 1}集`,
                url: link.href
            });
        });
        if (episodes.length > 0) {
            routes.push({ name: routeName, episodes: episodes });
        }
    });
    return JSON.stringify(routes);
})()
</js>
```

**ruleContent 返回格式规范**：
- 嵌套 JSON：`[{"name":"线路1","episodes":[{"title":"第1集","url":"..."}]}]`
- 扁平 JSON（兼容旧版）：`[{"title":"第1集","url":"..."}]` → 自动包装为单线路
- 多行 URL（兼容旧版）：`url1\nurl2\nurl3` → 自动包装为单线路

#### 第二层：R5 智能模式识别（ruleContent 为空时回退）

当 ruleContent 为空时，R5 尝试识别常见的多线路 DOM 模式：

**模式A：Tab 式线路**（最常见，约40%网站）
```html
<!-- DOM 特征：data-tab 属性 + 对应的 data-tab-content -->
<div class="tab" data-tab="1">线路1</div>
<div class="tab" data-tab="2">线路2</div>
<div class="episodes" data-tab-content="1">
  <a href="play/1-1">第1集</a>
</div>
```
- 识别规则：查找含 `data-tab`/`data-route`/`data-line` 属性的元素 + 对应内容容器

**模式B：分组式线路**（约30%网站）
```html
<!-- DOM 特征：标题元素 + 相邻的集数列表，重复多次 -->
<div class="route-title">线路1</div>
<div class="episode-list">
  <a href="play/1-1">第1集</a>
</div>
<div class="route-title">线路2</div>
<div class="episode-list">
  <a href="play/2-1">第1集</a>
</div>
```
- 识别规则：查找 `.route-title`/`.module-player-title`/`.playlist-title` 等常见类名 + 相邻的链接列表

**模式C：多级嵌套式**（如奈飞中文网，约10%网站）
```html
<!-- 详情页只有线路链接，需二次请求获取集数 -->
<a href="/voddetail/132245.html/?url=...">线路1</a>
```
- 识别规则：检测页面是否只有线路链接无集数列表
- 处理策略：标注"需二次请求"，R5 可选抓取第一个线路的集数（避免耗时过长）

**模式D：单线路多集**（约20%网站，现有逻辑兼容）
- 无线路分组结构，直接是集数列表
- R5 返回 `List<String>`，包装为单元素 `List<RssRoute>`

**R5 智能识别算法**：
```kotlin
fun extractRoutesWithPattern(doc: Document): List<RssRoute>? {
    // 1. 尝试模式A：Tab式（data-tab/data-route/data-line 属性）
    val tabRoutes = extractTabPattern(doc)
    if (tabRoutes != null && tabRoutes.size > 1) return tabRoutes

    // 2. 尝试模式B：分组式（常见类名 + 相邻链接列表）
    val groupRoutes = extractGroupPattern(doc)
    if (groupRoutes != null && groupRoutes.size > 1) return groupRoutes

    // 3. 尝试模式C：多级嵌套（检测是否只有线路链接）
    val nestedRoutes = extractNestedPattern(doc)
    if (nestedRoutes != null) return nestedRoutes

    // 4. 回退模式D：单线路多集（现有逻辑）
    return null  // 返回 null，调用方走现有 extract() 逻辑
}
```

#### ADR-9-Appendix：5 站点多线路 DOM 结构实证分析

> 对5个典型视频站点进行深度 DOM 分析，验证 ADR-9 四种模式的覆盖率和识别策略。

**站点 A**（MacCMS v10 + mxtheme 主题）：
- 线路模式：**Tab式（HTML全量渲染变体）**
- 线路数：2（固定，WJ线路/OK线路）
- 线路识别锚点：`[data-dropdown-value]` + `.module-tab-item.tab-item`
- 集数识别锚点：`.module-play-list-link`
- 播放页路径：`/vodplay/{vodId}-{sid}-{nid}.html`（简化式）
- 播放页特征：`var player_aaaa={...}` JS变量，encrypt=0明文
- 特殊：HTML全量渲染所有线路所有集数（非JS动态加载），R5可直接解析无需模拟点击

**站点 B**（MacCMS + stui 主题）：
- 线路模式：**Tab式（Bootstrap nav-tabs）**
- 线路数：1（当前数据，但DOM结构支持多线路扩展）
- 线路识别锚点：`ul.nav-tabs.dpplay > li > a[href^="#playlist"][data-toggle="tab"]`
- 集数识别锚点：`ul.stui-content__playlist > li > a`
- 播放页路径：`/vodplay/{vodId}-{routeIndex}-{episodeIndex}.html`（三段式）
- 播放页特征：`var player_aaaa={...}` JS变量，encrypt=0明文
- 特殊：单线路是Tab式退化特例（li只有1个），R5应归入Tab式处理

**站点 C**（80s电影网模板，自研CMS）：
- 线路模式：**分组式（标题+集数列表，HTML全量渲染）**
- 线路数：1-2（实测"暴风4K"+"非凡高速"等线路名）
- 线路识别锚点：播放列表标题（如"暴风4K"、"非凡高速"纯文本节点）
- 集数识别锚点：`<a>` 标签列表，href格式 `/play/{vodId}/{routeIndex}/{epIndex}.html`
- 播放页路径：`/play/{vodId}/{routeIndex}/{epIndex}.html`
- 特殊：线路名是纯文本节点（非HTML标签），需按文本内容分割；集数分属不同routeIndex

**站点 D**（MacCMS + mxtheme 主题，站点A同系）：
- 线路模式：**Tab式（与站点A完全一致）**
- 线路识别锚点：`.module-tab-item.tab-item` + `[data-dropdown-value]`
- 集数识别锚点：`.module-play-list-link`
- 播放页路径：`/vodplay/{vodId}-{sid}-{nid}.html`
- 播放页特征：`var player_aaaa={...}` JS变量
- 特殊：与站点A同CMS同主题，选择器完全复用

**站点 E**（MacCMS + mxtheme 主题，多级嵌套变体）：
- 线路模式：**多级嵌套式（详情页→9线路链接→子线路页面→集数列表）**
- 详情页线路链接：9个不同域名的链接 + 6个备用链接
- 线路链接特征：链接指向同路径但不同域名的详情页
- 子线路页面特征：14个子线路（如LZ线路/DB线路等），每线路独立集数列表
- 播放页路径：`/vodplay/{vodId}-{routeId}-{epIndex}.html`
- 特殊：三级嵌套（详情页→线路页→集数列表），R5只能抓取第一级，需ruleContent JS处理深层

**实证分析结论**：

| 模式 | 覆盖率（5站点） | R5识别可行性 | ruleContent必要性 |
|------|----------------|-------------|------------------|
| Tab式（MacCMS） | 3/5（60%） | 高（选择器统一） | 低（R5可覆盖） |
| 分组式（80s模板） | 1/5（20%） | 中（需按文本节点分割） | 中（简单JS即可） |
| 多级嵌套式 | 1/5（20%） | 低（需二次请求） | 高（必须JS处理） |

**MacCMS 指纹识别策略**（R5 优先嗅探）：
R5 应先检测播放页是否存在 `var player_aaaa=` 变量，若存在即判定为 MacCMS 站点，可直接套用 Tab 式选择器组合：
1. 线路：`[data-dropdown-value]` 或 `a[href^="#playlist"]`
2. 集数：`.module-play-list-link` 或 `ul.stui-content__playlist > li > a`
3. 视频流：`player_aaaa.url`（按 encrypt 字段分级处理）

#### ruleContent JS 标准数据格式规范（ADR-9 核心）

> 用户最关心的核心：即使内置 R5 不能覆盖所有网站，也要出标准规范让用户通过 ruleContent JS 编写。

**标准返回格式**：

```javascript
// 多线路多集格式（完整版，List<RssRoute>）
<js>
(() => {
    const routes = [];
    // 遍历所有线路分组
    document.querySelectorAll('.你的线路选择器').forEach((group, i) => {
        const routeName = group.querySelector('.线路名称选择器')?.textContent || `线路${i+1}`;
        const episodes = [];
        group.querySelectorAll('.集数链接选择器').forEach((link, j) => {
            episodes.push({
                title: link.textContent.trim() || `第${j+1}集`,
                url: link.href      // 必须：播放页完整URL
            });
        });
        if (episodes.length > 0) {
            routes.push({ name: routeName, episodes: episodes });
        }
    });
    return JSON.stringify(routes);
})()
</js>
```

**返回 JSON 结构**：

```json
// 格式1：多线路多集（完整版）
[
  {
    "name": "线路1名称",
    "episodes": [
      { "title": "第1集", "url": "播放页URL" },
      { "title": "第2集", "url": "播放页URL" }
    ]
  },
  {
    "name": "线路2名称",
    "episodes": [
      { "title": "第1集", "url": "播放页URL" }
    ]
  }
]

// 格式2：单线路多集（简化版，自动包装为单线路）
[
  { "title": "第1集", "url": "播放页URL" },
  { "title": "第2集", "url": "播放页URL" }
]

// 格式3：多行URL（最简版，自动包装为单线路单标题）
// URL1
// URL2
// URL3
```

**字段说明**：

| 字段 | 层级 | 必须 | 说明 |
|------|------|------|------|
| name | RssRoute | 否 | 线路名称，缺省为"线路N" |
| episodes | RssRoute | 是 | 该线路的集数列表 |
| title | RssEpisode | 否 | 集数标题，缺省为"第N集" |
| url | RssEpisode | **是** | 播放页URL（可以是播放页URL或直接视频流URL） |

**兼容性保证**：
- 格式2/3 自动包装为 `[{ name: "默认线路", episodes: [...] }]`
- 现有订阅源（无 ruleContent 或 ruleContent 返回旧格式）完全兼容
- R5 VideoUrlExtractor 返回 `List<String>` 时自动包装为单线路

**MacCMS 站点 ruleContent 模板**（覆盖60%站点）：

```javascript
<js>
(() => {
    const routes = [];
    // MacCMS mxtheme 主题选择器
    document.querySelectorAll('.module-tab-item[data-dropdown-value]').forEach((tab, i) => {
        const routeName = tab.getAttribute('data-dropdown-value') || `线路${i+1}`;
        const panels = document.querySelectorAll('.module-play-list');
        const panel = panels[i];
        if (!panel) return;
        const episodes = [];
        panel.querySelectorAll('.module-play-list-link').forEach((link, j) => {
            episodes.push({
                title: link.querySelector('span')?.textContent?.trim() || `第${j+1}集`,
                url: link.href
            });
        });
        if (episodes.length > 0) {
            routes.push({ name: routeName, episodes: episodes });
        }
    });
    // MacCMS stui 主题选择器（备选）
    if (routes.length === 0) {
        document.querySelectorAll('ul.nav-tabs.dpplay > li > a[href^="#playlist"]').forEach((tab, i) => {
            const routeName = tab.textContent.trim() || `线路${i+1}`;
            const paneId = tab.getAttribute('href')?.replace('#', '');
            const pane = paneId ? document.getElementById(paneId) : null;
            if (!pane) return;
            const episodes = [];
            pane.querySelectorAll('ul.stui-content__playlist > li > a').forEach((link, j) => {
                episodes.push({
                    title: link.textContent.trim() || `第${j+1}集`,
                    url: link.href
                });
            });
            if (episodes.length > 0) {
                routes.push({ name: routeName, episodes: episodes });
            }
        });
    }
    return JSON.stringify(routes.length > 0 ? routes : []);
})()
</js>
```

**80s模板站点 ruleContent 模板**（覆盖20%站点）：

```javascript
<js>
(() => {
    const routes = [];
    const scrollBox = document.querySelector('.scroll-content');
    if (!scrollBox) return JSON.stringify([]);
    // 按线路标题文本分割
    const titles = scrollBox.querySelectorAll('h3, .module-heading, strong');
    titles.forEach((title, i) => {
        const routeName = title.textContent.trim();
        const episodes = [];
        let sibling = title.nextElementSibling;
        while (sibling && sibling.tagName !== 'H3' && !sibling.classList.contains('module-heading')) {
            sibling.querySelectorAll('a').forEach((link, j) => {
                if (link.href && link.href.includes('/play/')) {
                    episodes.push({
                        title: link.textContent.trim() || `第${j+1}集`,
                        url: link.href
                    });
                }
            });
            sibling = sibling.nextElementSibling;
        }
        if (episodes.length > 0) {
            routes.push({ name: routeName, episodes: episodes });
        }
    });
    return JSON.stringify(routes);
})()
</js>
```

**多级嵌套站点 ruleContent 模板**（覆盖20%站点，需二次请求）：

```javascript
<js>
(() => {
    const routes = [];
    // 第一级：获取线路链接
    const routeLinks = document.querySelectorAll('a[href*="voddetail"]');
    // 注意：多级嵌套需二次请求获取子线路+集数，此处仅抓取第一级
    // 完整实现需在 Legado 的 JS 环境中使用 ajax/fetch
    routeLinks.forEach((link, i) => {
        const routeName = link.textContent.trim() || `线路${i+1}`;
        // 二次请求示例（Legado JS 环境支持 java.ajax）
        // const subPage = java.ajax(link.href);
        // 解析子页面获取 episodes...
        routes.push({ name: routeName, episodes: [] }); // 占位，待二次请求填充
    });
    return JSON.stringify(routes);
})()
</js>
```

#### 第三层：skill 编写指南（辅助用户编写 ruleContent）

在 `.trae/skills/legado-source-creator/references/` 新增"多线路规则编写指南"：
- 多线路 ruleContent 编写规范（嵌套 JSON 格式）
- ruleContent JS 标准数据格式规范（上述三种格式 + 字段说明）
- 常见 CMS 主题指纹 + 对应 ruleContent 模板（MacCMS mxtheme/stui/80s模板）
- 多线路抓取 JS 模板（可复用，用户只需修改选择器）
- 调试技巧（如何验证 ruleContent 返回正确结构）

## 3. Data Flow（数据流）

### 3.1 订阅源视频播放数据流

```
用户从订阅源列表点击视频条目
→ ReadRss.kt 启动 VideoPlayerActivity
   传入: videoUrl + videoTitle + rssEpisodes（多集列表）
→ VideoPlayerActivity.onCreate()
   1. 解析 rssEpisodes 构建视频列表
   2. 创建 VideoPagerAdapter
   3. ViewPager2.adapter = videoPagerAdapter
   4. ViewPager2.setCurrentItem(0)  // 默认第一个
→ VideoFragment(0).onCreateView()
   1. 初始化 PlayerView（铺满屏幕）
   2. 初始化悬浮控件（默认隐藏）
   3. 从 arguments 获取 videoUrl/videoTitle
   4. 加载视频 URL（若 ruleContent 为空，触发 R5 VideoUrlExtractor）
   5. R5 提取视频流 URL（含 3003 Bug 修复）
   6. 设置 Header（Referer/UA/Cookie）
   7. 开始播放
→ onPrepared() 回调
   1. 检测视频宽高比
   2. 判断是否横屏比例视频
   3. 若横屏比例：显示下方全屏按钮
   4. 进入 STATE_PURE（纯净播放态）
```

### 3.2 书籍源视频播放数据流

```
用户从书籍章节列表点击视频章节
→ VideoPlayerActivity 启动
   传入: book + chapter（无 rssEpisodes）
→ VideoPlayerActivity.onCreate()
   1. 检测 book != null（书籍源模式）
   2. 禁用 ViewPager2 滑动（ setUserInputEnabled(false)）
   3. 只创建单个 VideoFragment
   4. 显示书籍信息区 + 章节/卷选择区（在设置面板中）
→ VideoFragment 加载视频
   → 从 book.chapter 获取视频 URL
   → 播放流程同订阅源
```

### 3.3 三种状态切换数据流

```
STATE_PURE → STATE_NORMAL（单击屏幕）
→ GestureDetector.onSingleTapConfirmed()
→ state = STATE_NORMAL
→ 显示控件动画（alpha 0→1, translationY offset→0, 300ms）
→ 更新控件内容（标题/收藏状态/倍速/静音状态）

STATE_NORMAL → STATE_PURE（单击屏幕）
→ GestureDetector.onSingleTapConfirmed()
→ state = STATE_PURE
→ 隐藏控件动画（alpha 1→0, translationY 0→offset, 300ms）
→ 动画结束后 visibility = GONE

STATE_NORMAL → STATE_FULLSCREEN（点击全屏按钮/双指缩放）
→ requestedOrientation = SCREEN_ORIENTATION_SENSOR_LANDSCAPE
→ state = STATE_FULLSCREEN
→ onConfigurationChanged() 触发布局重配
→ 隐藏下方全屏按钮（已是全屏）
→ 功能按钮适配横屏布局（位置调整）

STATE_FULLSCREEN → STATE_NORMAL（返回键/全屏按钮）
→ requestedOrientation = SCREEN_ORIENTATION_SENSOR_PORTRAIT
→ state = STATE_NORMAL
→ 恢复竖屏布局
→ 显示下方全屏按钮（若是横屏比例视频）
```

### 3.4 3003 Bug 修复数据流

```
R5 VideoUrlExtractor.extract(articleUrl)
→ 执行五种提取方法（video标签/OG/Meta/script JSON/JS变量/正则）
→ 获取到候选 URL（可能是播放器页面 URL）
→ 调用 extractPlayerPageUrl(candidateUrl)
   1. 检测 ?url= 或 &url= 参数
   2. 提取参数值
   3. URL 解码
   4. 验证合法性
→ 若是播放器页面 URL：返回解码后的实际视频流 URL
→ 若不是：返回原始候选 URL
→ ExoPlayer 使用实际视频流 URL 播放
→ 成功播放（3003 Bug 修复）
```

### 3.5 多线路数据流

```
订阅源视频启动（type=2）
→ VideoPlay.startPlay()
→ 检测 ruleContent 是否为空
  分支A：ruleContent 非空
    → Rss.getContent 获取内容
    → parseRssRoutes(content, link) 解析多线路
      1. 尝试解析嵌套 JSON：[{name, episodes:[{title,url}]}]
      2. 若非嵌套格式，回退 parseRssEpisodes 解析扁平 JSON数组/多行URL
         → 包装为单元素 List<RssRoute>(name="默认线路", episodes=flatEpisodes)
    → 返回 List<RssRoute>?
  分支B：ruleContent 为空（R5 自动抓取）
    → VideoUrlExtractor.extract(articleUrl)
    → 先尝试 extractRoutesWithPattern(doc) 智能模式识别
      1. 模式A：Tab式（data-tab/data-route/data-line 属性 + 对应内容容器）
      2. 模式B：分组式（.route-title/.module-player-title 等类名 + 相邻链接列表）
      3. 模式C：多级嵌套（检测是否只有线路链接无集数，可选二次请求）
      4. 模式D：回退单线路多集（现有逻辑）
    → 若识别到多线路：返回 List<RssRoute>
    → 若未识别到多线路：走现有 extract() 返回 List<String>
      → size == 1：rssRoutes = null（单URL场景）
      → size > 1：包装为单元素 List<RssRoute>(name="默认线路", episodes=...)
    → 注：R5 智能回退覆盖率约60-70%，复杂网站需用户编写 ruleContent
→ VideoPlay.rssRoutes = routes
→ VideoPlay.rssRouteIndex = 0
→ VideoPlay.rssEpisodes = routes?.get(0)?.episodes（兼容现有逻辑）
→ UP_VIDEO_INFO post [1]（触发 UI 更新）
→ VideoFragment 显示：
  - rssRoutes == null 或 size <= 1：隐藏线路选择器
  - rssRoutes.size > 1：显示线路选择器 + 集数选择器
→ 用户切换线路
  → rssRouteIndex = newIndex
  → rssEpisodes = routes[newIndex].episodes
  → 更新集数选择器数据
  → 自动播放线路1的第1集（或保持集索引）
→ 用户切换集数
  → playRssEpisode(playerView, episode)
  → 现有逻辑不变
```

## 4. File Changes（文件变更清单）

### 4.1 新建文件

| 文件路径 | 说明 |
|----------|------|
| `app/src/main/java/io/legado/app/ui/video/VideoFragment.kt` | 单个视频播放 Fragment，持有播放器 + 悬浮控件 + 手势处理 |
| `app/src/main/java/io/legado/app/ui/video/VideoPagerAdapter.kt` | ViewPager2 的 FragmentStateAdapter |
| `app/src/main/java/io/legado/app/ui/video/VideoSettingsDialog.kt` | BottomSheetDialogFragment 设置面板 |
| `app/src/main/java/io/legado/app/data/entities/RssRoute.kt` | 多线路数据类（name + episodes），与书源 volumes 范式对称 |
| `app/src/main/res/layout/fragment_video.xml` | VideoFragment 布局：播放器 + 悬浮控件层（含线路选择器+集数选择器） |
| `app/src/main/res/layout/layout_video_settings.xml` | 设置面板布局 |
| `app/src/main/res/layout/item_route_selector.xml` | 线路选择器列表项布局 |

### 4.2 修改文件

| 文件路径 | 修改内容 |
|----------|---------|
| `app/src/main/java/io/legado/app/ui/video/VideoPlayerActivity.kt` | 重构为容器角色，持有 ViewPager2，移除直接 UI 控制逻辑（迁移到 VideoFragment/VideoSettingsDialog） |
| `app/src/main/res/layout/activity_video_player.xml` | LinearLayout → ConstraintLayout + ViewPager2 容器 |
| `app/src/main/java/io/legado/app/help/video/VideoUrlExtractor.kt` | 增加 extractPlayerPageUrl() 方法（3003 Bug 修复） |
| `app/src/main/java/io/legado/app/model/VideoPlay.kt` | 新增 rssRoutes/rssRouteIndex 字段 + parseRssRoutes() 方法 + 切换线路逻辑 + releaseAllVideos() 同步重置 |
| `app/src/main/java/io/legado/app/ui/rss.read/ReadRss.kt` | 无需修改（数据通过 VideoPlay 单例传递，多线路数据在 VideoPlay.startPlay 中解析） |

### 4.3 当前功能保留映射表

> **REQ-13 强制要求**：当前所有功能 100% 保留，重新组织到新架构中。

#### 当前布局功能 → 新架构映射

| 当前位置 | 当前功能 | 新位置 | 迁移方式 |
|---------|---------|--------|---------|
| TitleBar | 标题显示 | VideoFragment 左下角 tv_video_title | 标题改为悬浮显示 |
| playerView | 视频播放 | VideoFragment PlayerView | 铺满屏幕 |
| tv_video_url | 播放地址展示 | VideoSettingsDialog 播放地址区 | 迁移到设置面板 |
| btn_copy_url | 复制地址 | VideoSettingsDialog 播放地址区 | 迁移到设置面板 |
| btn_skip_back_30s | 快退30秒 | VideoSettingsDialog 播放控制区 | 迁移到设置面板 |
| btn_skip_back_10s | 快退10秒 | VideoSettingsDialog 播放控制区 | 迁移到设置面板 |
| btn_skip_fwd_10s | 快进10秒 | VideoSettingsDialog 播放控制区 | 迁移到设置面板 |
| btn_skip_fwd_30s | 快进30秒 | VideoSettingsDialog 播放控制区 | 迁移到设置面板 |
| spinner_playback_rate | 倍速选择 | VideoFragment btn_speed + VideoSettingsDialog | 右侧倍速按钮（快捷）+ 设置面板（完整） |
| btn_toggle_debug | 调试开关 | VideoSettingsDialog 调试面板区 | 迁移到设置面板 |
| btn_prev_episode | 上一集 | VideoSettingsDialog 多集选择区 | 迁移到设置面板 |
| btn_next_episode | 下一集 | VideoSettingsDialog 多集选择区 | 迁移到设置面板 |
| tv_rss_description | 视频简介 | VideoSettingsDialog 视频简介区 | 迁移到设置面板 |
| iv_cover | 书籍封面 | VideoSettingsDialog 书籍信息区 | 迁移到设置面板 |
| tv_name | 书名 | VideoSettingsDialog 书籍信息区 | 迁移到设置面板 |
| tv_author | 作者 | VideoSettingsDialog 书籍信息区 | 迁移到设置面板 |
| tv_intro_container | 书籍简介 | VideoSettingsDialog 书籍信息区 | 迁移到设置面板 |
| volumes | 卷列表 | VideoSettingsDialog 章节/卷选择区 | 迁移到设置面板 |
| chapters | 章节列表 | VideoSettingsDialog 章节/卷选择区 | 迁移到设置面板 |
| iv_chapter | 章节按钮 | VideoSettingsDialog 章节/卷选择区 | 迁移到设置面板 |
| tv_debug_log | 调试日志 | VideoSettingsDialog 调试面板区 | 迁移到设置面板 |

#### 当前菜单功能 → 新架构映射

| 菜单项 | 当前功能 | 新位置 | 迁移方式 |
|--------|---------|--------|---------|
| menu_custom_btn | 自定义按钮 | VideoSettingsDialog 菜单功能区 | 迁移到设置面板 |
| menu_rss_star | 收藏 | VideoFragment btn_favorite + VideoSettingsDialog | 右侧收藏按钮（快捷）+ 设置面板（完整） |
| menu_float_window | 悬浮窗 | VideoSettingsDialog 菜单功能区 | 迁移到设置面板 |
| menu_config_settings | 配置设置 | VideoSettingsDialog 菜单功能区 | 迁移到设置面板 |
| menu_login | 登录 | VideoSettingsDialog 菜单功能区 | 迁移到设置面板 |
| menu_copy_video_url | 复制URL | VideoSettingsDialog 播放地址区 | 迁移到设置面板 |
| menu_open_other_video_player | 其他播放器 | VideoSettingsDialog 菜单功能区 | 迁移到设置面板 |
| menu_edit_source | 编辑源 | VideoSettingsDialog 菜单功能区 | 迁移到设置面板 |
| menu_log | 日志 | VideoSettingsDialog 菜单功能区 | 迁移到设置面板 |

#### 当前 LiveEventBus 事件 → 新架构映射

| 事件 Key | 当前处理 | 新处理 | 说明 |
|---------|---------|--------|------|
| VIDEO_SUB_TITLE (sticky) | 更新 titleBar.title + updateVideoUrlDisplay | VideoFragment 更新 tv_video_title + VideoSettingsDialog 更新播放地址 | 标题改为悬浮显示 |
| UP_VIDEO_INFO | 处理多集选择（rssEpisodes/chapters） | VideoPlayerActivity 转发给当前 VideoFragment + VideoSettingsDialog | 保持多集选择功能 |
| VIDEO_PLAY_ERROR | appendDebugLog + 显示 debugPanel | VideoFragment appendDebugLog + VideoSettingsDialog 显示调试面板 | 调试功能保留 |

#### 当前播放器核心功能 → 新架构映射

| 功能 | 当前实现 | 新实现 | 说明 |
|------|---------|--------|------|
| ExoPlayer/GSY 初始化 | setupPlayerView() | VideoFragment.setupPlayer() | 迁移到 Fragment |
| Header 注入 | ExoPlayerHelper + ExoPlayerManager | 保持不变 | R5 已完成 |
| 倍速控制 | spinner_playback_rate + skipVideo() | btn_speed 弹出选择 + VideoSettingsDialog Spinner | 双入口 |
| 快进/快退 | skipVideo() | VideoSettingsDialog 按钮调用 skipVideo() | 逻辑不变 |
| 全屏切换 | toggleFullScreen() | VideoFragment.toggleFullScreen() | 迁移到 Fragment |
| 画中画 | onUserLeaveHint() + startFloatingWindow() | VideoPlayerActivity 保留 | Activity 级功能 |
| 视频比例检测 | onPrepared() 中检测 | VideoFragment onPrepared() | 迁移到 Fragment |
| 错误处理 | VIDEO_PLAY_ERROR 事件 | 保持不变 | 事件机制不变 |
| R5 视频提取 | VideoUrlExtractor | VideoUrlExtractor + extractPlayerPageUrl() | 增加 3003 修复 |

## 5. 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| 架构重构导致回归 | 现有功能可能失效 | 100%功能保留映射表逐项核对（REQ-13） |
| Fragment 生命周期管理复杂 | 播放器实例泄漏 | setOffscreenPageLimit(1) + onDestroyView 释放 |
| ViewPager2 与播放器手势冲突 | 滑动切换可能误触播放器 | GestureDetector 优先处理单击，ViewPager2 处理滑动 |
| BottomSheetDialog 内容过多 | 设置面板体验差 | 分区折叠 + 滚动优化 |
| 3003 Bug 修复覆盖面有限 | 其他播放器页面 URL 格式未覆盖 | 先处理 `?url=` 模式，其他格式后续扩展 |
