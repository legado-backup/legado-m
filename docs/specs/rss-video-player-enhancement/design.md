# design.md — 订阅源视频播放器增强

## Technical Approach

### R1 多集选择播放

#### 1.1 数据模型

新增 `RssEpisode` data class（放于 `data/entities/` 或 `model/` 包）：

```kotlin
@Parcelize
data class RssEpisode(
    var title: String = "",
    var url: String = "",
    var duration: Long = 0,      // 预留：时长（毫秒）
    var cover: String = ""        // 预留：封面 URL
) : Parcelable
```

`VideoPlay` 单例新增字段：
```kotlin
var rssEpisodes: List<RssEpisode>? = null   // 订阅源多集列表
var rssEpisodeIndex: Int = 0                  // 当前集索引
```

#### 1.2 内容规则解析（VideoPlay.kt RssSource 分支）

修改 `VideoPlay.startPlay()` 的 RssSource 分支（line 217-248），在 `Rss.getContent().onSuccess` 中增加多集解析：

```kotlin
Rss.getContent(loadScope, rssArticle, ruleContent, s)
    .onSuccess(IO) { content ->
        val content = content.trim()
        // ① 尝试 JSON 数组多集
        val episodes = parseRssEpisodes(content, rssArticle.link)
        if (episodes != null && episodes.size > 1) {
            rssEpisodes = episodes
            rssEpisodeIndex = 0
            // 播放第一集
            playRssEpisode(player, episodes[0])
            return@onSuccess
        }
        // ② 单 URL（现有逻辑）
        val mUrl = if (content.isEmpty()) {
            throw ContentEmptyException("正文为空")
        } else if (content.startsWith("<")) {
            // mpd 文本（现有逻辑）
            ...
        } else {
            NetworkUtils.getAbsoluteURL(rssArticle.link, content)
        }
        videoUrl = mUrl
        ... // 现有 setUp 逻辑
    }
```

`parseRssEpisodes` 解析函数：
```kotlin
private fun parseRssEpisodes(content: String, baseUrl: String): List<RssEpisode>? {
    val trimmed = content.trim()
    // 模式1：JSON 数组
    if (trimmed.startsWith("[")) {
        return try {
            val arr = JSONArray(trimmed)
            (0 until arr.length()).map { i ->
                val obj = arr.getJSONObject(i)
                RssEpisode(
                    title = obj.optString("title", "第${i+1}集"),
                    url = NetworkUtils.getAbsoluteURL(baseUrl, obj.getString("url"))
                )
            }.filter { it.url.isNotBlank() }
        } catch (e: Exception) { null }
    }
    // 模式2：多行 URL（每行必须是合法 URL）
    val lines = trimmed.split("\n").map { it.trim() }.filter { it.isNotBlank() }
    if (lines.size > 1 && lines.all { isLikelyUrl(it) }) {
        return lines.mapIndexed { i, url ->
            RssEpisode(title = "第${i+1}集", url = NetworkUtils.getAbsoluteURL(baseUrl, url))
        }
    }
    return null  // 单 URL，交由现有逻辑处理
}

private fun isLikelyUrl(s: String): Boolean {
    return s.startsWith("http://") || s.startsWith("https://") || s.startsWith("/")
}
```

#### 1.3 多集切换播放

`VideoPlay` 新增方法：
```kotlin
fun playRssEpisode(player: StandardGSYVideoPlayer, episode: RssEpisode) {
    videoUrl = episode.url
    Coroutine.async(loadScope, IO) {
        val analyzeUrl = AnalyzeUrl(episode.url, source = source, ruleData = rssStar?.toRssArticle() ?: rssRecord?.toRssArticle())
        withContext(Main) {
            player.mapHeadData = analyzeUrl.headerMap
            player.setUp(analyzeUrl.url, cachePlay, File(appCtx.externalCache, "exoplayer"), episode.title)
            if (autoPlay) { player.startPlayLogic() }
        }
    }.onError { AppLog.put("加载订阅源视频集失败: ${episode.title}", it, true) }
}
```

VideoPlayerActivity 集数点击回调调用：
```kotlin
fun onRssEpisodeClick(index: Int) {
    VideoPlay.rssEpisodeIndex = index
    val episode = VideoPlay.rssEpisodes?.getOrNull(index) ?: return
    VideoPlay.playRssEpisode(binding.videoPlayer, episode)
}
```

#### 1.4 VideoPlayerActivity UI 修改

修改 `initView()`（line 222-244）：
```kotlin
private fun initView() {
    val book = VideoPlay.book
    if (book == null) {
        binding.data.invisible()
        binding.chaptersContainer.invisible()
        // 新增：订阅源多集支持
        val rssEpisodes = VideoPlay.rssEpisodes
        if (!rssEpisodes.isNullOrEmpty()) {
            binding.chaptersContainer.visible()
            binding.chapters.visible()
            showRssEpisodes(rssEpisodes)
        }
        return
    }
    ... // 现有书源逻辑
}
```

新增 `showRssEpisodes()` 方法，复用 `showToc()` 的 ChapterAdapter 或新建 RssEpisodeAdapter。

#### 1.5 内容规则编写指南（面向源作者，用户核心诉求 F1-F6）

**ruleContent 三种模式与 parseRssEpisodes 解析逻辑对应关系**：

| 模式 | ruleContent 返回值 | parseRssEpisodes 判定条件 | 输出 |
|------|-------------------|--------------------------|------|
| ① 单 URL（现有兼容） | 单个 URL 字符串 | 不匹配模式②③ | null（交由现有逻辑） |
| ② 多行 URL（简写多集） | 多行 URL（每行 http/https/相对路径） | `lines.size > 1 && lines.all { isLikelyUrl(it) }` | List<RssEpisode>（标题"第N集"） |
| ③ JSON 数组（完整多集） | `[{"url":"...","title":"..."}]` | `trimmed.startsWith("[")` 且 JSONArray 解析成功 | List<RssEpisode>（带标题） |

**JSON 数组对象结构定义**（源作者编写 JS 规则时需返回此结构）：

| 字段 | 类型 | 必须 | 缺省值 | 说明 |
|------|------|------|--------|------|
| `url` | String | ✅ 必须 | 无（缺失则该集被过滤） | 播放地址，相对路径自动拼接 baseUrl |
| `title` | String | ❌ 可选 | "第N集" | 集数标题 |
| `duration` | Long | ❌ 可选 | 0（预留） | 时长（毫秒，未来扩充） |
| `cover` | String | ❌ 可选 | ""（预留） | 封面 URL（未来扩充） |

**RssEpisode 数据类扩充**（支持未来扩展字段，对应 1.1 节）：

```kotlin
@Parcelize
data class RssEpisode(
    var title: String = "",
    var url: String = "",
    var duration: Long = 0,      // 预留：时长（毫秒）
    var cover: String = ""        // 预留：封面 URL
) : Parcelable
```

**兼容性保证**（parseRssEpisodes 实现细节，用户核心诉求 F3）：
1. 模式③优先判定：`trimmed.startsWith("[")` 才尝试 JSON 解析，普通 URL 不会误判
2. 模式②次之：仅当 `lines.size > 1 && lines.all { isLikelyUrl(it) }` 才判定多集，HTML 含换行不会误判（HTML 标签不以 http/https 开头）
3. 模式③ JSON 解析失败（非合法 JSON）返回 null，回退到模式①单 URL
4. 模式③数组中 `url` 为空的对象被过滤（`filter { it.url.isNotBlank() }`）
5. 现有单 URL 订阅源无需修改，自动走模式①（100% 向后兼容）

**源作者编写示例**（详见 spec.md R1 Approach "内容规则编写指南"小节）：
- CSS 简写（模式②）：`video source@src`（返回多行 URL）
- XPath 简写（模式②）：`//source/@src`
- JS 完整（模式③）：`<js>JSON.stringify([{url:...,title:...}])</js>`

#### 1.5.1 R3 多线路格式（嵌套 JSON）

ruleContent 返回嵌套 JSON 数组时，解析为多线路列表：

```json
[{"name":"线路1","episodes":[{"title":"第1集","url":"..."}]}]
```

| 字段 | 类型 | 必须 | 缺省值 | 说明 |
|------|------|------|--------|------|
| `name` | String | ❌ 可选 | "线路N" | 线路名称 |
| `episodes` | Array | ✅ 必须 | 无 | 集数列表，元素结构同 1.5 节格式③ |

**判定条件**：JSON 数组第一个元素包含 `episodes` 字段 → 多线路格式；否则 → 扁平 JSON（单线路）。

**兼容性**：扁平 JSON/多行 URL/单 URL 自动包装为单线路 `List<RssRoute>`，现有订阅源无需修改。

#### 1.5.2 R5 自动抓取（ruleContent 为空时）

当 `ruleContent` 为空且 `type=2` 时，系统自动从文章页面 HTML 抓取视频链接（`VideoUrlExtractor.extract()`）：

1. 请求文章页面 URL（`rssArticle.link`）
2. 五种方法按精确度优先提取：① video/source 标签 → ② OG/Meta → ③ script JSON → ④ JS 变量 → ⑤ 正则兜底
3. 播放器页面 URL 自动解析（`/player/?url=...m3u8` → 实际视频流 URL）
4. 多个 URL → 自动构建多集列表

**限制**：无法提取需 JS 运行时动态生成的 URL（需用 type=0 WebView 模式）。

> **完整编写指南**：[.trae/skills/legado-source-creator/references/special-scenarios/video-audio.md](../../../../.trae/skills/legado-source-creator/references/special-scenarios/video-audio.md) 5.6 节

### R2 m3u8 播放失败分析+调试日志

#### 2.1 错误回调链

采用 **EventBus 通知机制**（不破坏 GSY 现有回调链）：

```
ExoPlayer 错误
  → Exo2MediaPlayer.onPlayerErrorChanged(error)  [新增]
  → AppLog.put("视频播放错误", error)             [记录日志]
  → postEvent(EventBus.VIDEO_PLAY_ERROR, errorInfo)  [通知 UI]
  → VideoPlayerActivity.onVideoPlayError(event)  [接收]
  → 调试日志面板显示                              [UI]
```

#### 2.2 Exo2MediaPlayer 错误回调

`Exo2MediaPlayer` 实现 `Player.Listener` 的 `onPlayerErrorChanged`（media3 新 API，替代旧 onPlayerError）：

```kotlin
@OptIn(UnstableApi::class)
override fun onPlayerErrorChanged(error: PlaybackException?) {
    super.onPlayerErrorChanged(error)
    if (error != null) {
        val errorInfo = VideoErrorInfo(
            errorCode = error.errorCode,
            errorName = error.errorCodeName,
            message = error.message ?: "",
            cause = error.cause?.message ?: "",
            url = mCurrentUrl ?: ""
        )
        AppLog.put("视频播放错误: ${error.errorCodeName}", error)
        postEvent(EventBus.VIDEO_PLAY_ERROR, errorInfo)
    }
}
```

需保存当前 URL（`mCurrentUrl`），在 `setDataSource` 时记录。

#### 2.3 VideoErrorInfo 数据类

```kotlin
@Parcelize
data class VideoErrorInfo(
    val errorCode: Int = 0,
    val errorName: String = "",
    val message: String = "",
    val cause: String = "",
    val url: String = ""
) : Parcelable
```

#### 2.4 调试日志面板 UI

调试日志面板已统一到 R3.3 布局中（`rss_video_panel` 内的 `debug_panel`），详见 R3.3 节。R2 只负责错误事件的接收和日志追加逻辑，不单独定义布局。

#### 2.5 VideoPlayerActivity 调试逻辑

```kotlin
// EventBus 接收
@Subscribe(threadMode = ThreadMode.MAIN)
fun onVideoPlayError(event: Event<VideoErrorInfo>) {
    val info = event.data ?: return
    appendDebugLog("❌ 播放失败")
    appendDebugLog("错误类型: ${info.errorName}(${info.errorCode})")
    appendDebugLog("错误消息: ${info.message}")
    appendDebugLog("原因: ${info.cause}")
    appendDebugLog("URL: ${info.url}")
    // 非全屏时自动显示
    if (!VideoPlay.backFromWindowFull(this)) {
        binding.debugPanel.visible()
    }
}

// 切换调试面板显示
fun toggleDebugPanel() {
    binding.debugPanel.toggleVisibility()
}

// 追加调试日志
private fun appendDebugLog(text: String) {
    val ts = SimpleDateFormat("HH:mm:ss", Locale.getDefault()).format(Date())
    val line = "[$ts] $text\n"
    debugLogBuilder.append(line)
    binding.tvDebugLog.text = debugLogBuilder.toString()
}
```

播放开始时也记录调试信息：
```kotlin
// 在 startPlay 后追加
appendDebugLog("▶ 开始播放")
appendDebugLog("URL: $videoUrl")
appendDebugLog("Header: ${analyzeUrl.headerMap}")
```

#### 2.6 调试面板触发入口

调试面板触发入口已统一到 R3.3 布局的功能区中（`btn_toggle_debug` 按钮），点击切换 `debug_panel` 显示/隐藏。播放失败时（R2.5）非全屏自动弹出。

### R3 学习旧订阅源布局样式（基于 auto-video-player.html 模板）

#### 3.1 HTML 模板布局分析

用户提供的旧 WebView 方案模板 `auto-video-player.html` 布局结构（从上到下）：

| 区块 | HTML 元素 | 功能 |
|------|----------|------|
| ① 标题区 | `<h3 id="title">` | 视频标题 |
| ② 播放器区 | `<div id="video-wrapper">` + `<video>` + 进度条 | 视频播放 |
| ③ 播放地址展示 | `<div id="video-url">` | 显示当前播放地址 |
| ④ 功能区 | `<div id="video-controls-bar">` | ←3m/←1m/←30s/30s→/1m→/3m→ + 倍速选择(1x/3x/5x/10x/15x) + 全屏 + 反转 |
| ⑤ 视频源切换 | `<div id="video-source-container">` | 上一集 + 视频源下拉选择 + 下一集（多集选择） |
| ⑥ 分页控制 | `<div id="page-controls">` | 上一页/页码/下一页/自动加载 |
| ⑦ 切换按钮 | `<div id="toggle-buttons">` | 显/隐信息 + 调试信息 |
| ⑧ 消息区 | `<div id="messages">` | 状态消息（成功/警告/错误） |
| ⑨ 调试信息区 | `<div id="debug-info">` | 调试日志 |
| ⑩ 描述区 | `<div id="description">` | 视频简介 |

#### 3.2 内置播放器现有布局对比

`activity_video_player.xml` 现有布局：
- TitleBar（标题栏）✅ 对应 ①
- VideoPlayer（播放器）✅ 对应 ②
- data 区（封面+书名+作者+简介）⚠️ 只对书源生效，订阅源 book==null 时隐藏
- chapters_container（卷+集数）⚠️ 只对书源生效，订阅源 book==null 时隐藏

**缺失**：③播放地址展示、④功能区(快进快退/倍速/全屏)、⑤多集选择(订阅源)、⑦调试按钮、⑧⑨消息/调试面板、⑩视频简介(订阅源)

#### 3.3 内置播放器布局增强设计（R1+R2+R3 统一）

在 `activity_video_player.xml` 的 VideoPlayer 下方、chapters_container 之前，新增**订阅源功能区**（订阅源 book==null 时显示，书源保持原样）：

```xml
<!-- 订阅源功能区（book==null 时可见） -->
<LinearLayout
    android:id="@+id/rss_video_panel"
    android:layout_width="match_parent"
    android:layout_height="wrap_content"
    android:orientation="vertical"
    android:visibility="gone">

    <!-- ③ 播放地址展示 + 复制按钮（REQ-3.11 多行换行 / REQ-3.12 复制按钮） -->
    <LinearLayout
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:orientation="horizontal"
        android:background="#1A2B4A"
        android:padding="4dp">
        <TextView
            android:id="@+id/tv_video_url"
            android:layout_width="0dp"
            android:layout_height="wrap_content"
            android:layout_weight="1"
            android:textColor="#8AB4F8"
            android:textSize="11sp"
            android:maxLines="3"
            android:ellipsize="end"
            tools:text="播放地址：https://..." />
        <Button
            android:id="@+id/btn_copy_url"
            style="@style/VideoCtrlButton"
            android:layout_width="wrap_content"
            android:layout_height="wrap_content"
            android:layout_gravity="center_vertical"
            android:text="复制" />
    </LinearLayout>

    <!-- ④ 功能区：快进快退 + 倍速 + 调试按钮 -->
    <LinearLayout
        android:id="@+id/video_controls_bar"
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:gravity="center"
        android:orientation="horizontal"
        android:padding="6dp">

        <Button android:id="@+id/btn_skip_back_30s" android:text="←30s" style="@style/VideoCtrlButton" />
        <Button android:id="@+id/btn_skip_back_10s" android:text="←10s" style="@style/VideoCtrlButton" />
        <Button android:id="@+id/btn_skip_fwd_10s" android:text="10s→" style="@style/VideoCtrlButton" />
        <Button android:id="@+id/btn_skip_fwd_30s" android:text="30s→" style="@style/VideoCtrlButton" />
        <Spinner android:id="@+id/spinner_playback_rate"
            android:layout_width="wrap_content"
            android:layout_height="wrap_content"
            android:minWidth="48dp"
            android:minHeight="36dp"
            android:padding="3dp" />
        <Button android:id="@+id/btn_toggle_debug" android:text="调试" style="@style/VideoCtrlButton" />
    </LinearLayout>

    <!-- ⑤ 多集选择（R1，rssEpisodes 不为空时显示） -->
    <LinearLayout
        android:id="@+id/rss_episodes_container"
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:orientation="horizontal"
        android:gravity="center"
        android:visibility="gone">
        <Button android:id="@+id/btn_prev_episode" android:text="上一集" />
        <Spinner android:id="@+id/spinner_episode" />
        <Button android:id="@+id/btn_next_episode" android:text="下一集" />
    </LinearLayout>

    <!-- ⑩ 视频简介（订阅源） -->
    <TextView
        android:id="@+id/tv_rss_description"
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:padding="8dp"
        android:textSize="13sp"
        android:visibility="gone" />

    <!-- ⑧⑨ 调试信息面板（R2，默认隐藏） -->
    <ScrollView
        android:id="@+id/debug_panel"
        android:layout_width="match_parent"
        android:layout_height="200dp"
        android:background="#CC000000"
        android:visibility="gone">
        <TextView
            android:id="@+id/tv_debug_log"
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:padding="8dp"
            android:textColor="#00FF00"
            android:textSize="11sp"
            android:fontFamily="monospace"
            android:textIsSelectable="true" />
    </ScrollView>
</LinearLayout>
```

#### 3.4 功能区按钮逻辑（学习 HTML 模板）

| 按钮 | HTML 模板行为 | 内置播放器实现 |
|------|-------------|--------------|
| ←30s/←10s | `video.currentTime -= 30/10` | `player.seekTo(currentPosition - 30000)` |
| 10s→/30s→ | `video.currentTime += 10/30` | `player.seekTo(currentPosition + 10000)` |
| 倍速选择 | `video.playbackRate = value` | Exo2MediaPlayer 已有 setSpeed 支持，Spinner 选项 1x/3x/5x/10x/15x |
| 调试按钮 | 切换 debug-info 显示/隐藏 | 切换 debug_panel visibility |
| 上一集/下一集 | 切换 videoSources 索引 | R1 的 onRssEpisodeClick(index±1) |
| 集数选择 | `<select>` 切换 videoSources | Spinner 切换 rssEpisodes |

#### 3.5 样式定义

新增 `style/VideoCtrlButton`（学习 HTML 模板的按钮样式，REQ-3.9/3.10 统一尺寸+圆角背景）：
```xml
<style name="VideoCtrlButton" parent="Widget.AppCompat.Button.Borderless">
    <item name="android:minWidth">48dp</item>
    <item name="android:minHeight">36dp</item>
    <item name="android:padding">3dp</item>
    <item name="android:textSize">11sp</item>
    <item name="android:background">@drawable/bg_video_ctrl_btn</item>
    <item name="android:textColor">@color/primaryText</item>
</style>
```

新增圆角背景 `drawable/bg_video_ctrl_btn.xml`（selector + 圆角，REQ-3.10，pressed 状态视觉反馈）：
```xml
<selector xmlns:android="http://schemas.android.com/apk/res/android">
    <item android:state_pressed="true">
        <shape android:shape="rectangle">
            <solid android:color="#66757575" />      <!-- 按下状态：更深背景 -->
            <corners android:radius="2dp" />
        </shape>
    </item>
    <item>
        <shape android:shape="rectangle">
            <solid android:color="#33757575" />      <!-- 默认：淡灰背景，适配暗色/亮色模式 -->
            <corners android:radius="2dp" />
        </shape>
    </item>
</selector>
```

注意：使用 `Widget.AppCompat.Button.Borderless`（非 MaterialButton），避免 AppCompat 主题不兼容崩溃（P0 教训）。Spinner 不使用 style（Spinner 不支持 Button style），但显式设置相同 minWidth/minHeight/padding 保持视觉统一（REQ-3.9）。

#### 3.6 title 来源修复设计（REQ-3.13）

**根因分析**（源码深度分析）：
- `ReadRss.kt` line 40-44 / 69-73：启动 `VideoPlayerActivity` 时只传 `sourceKey/sourceType/record`，**未传 `videoTitle`**
- `VideoPlayerActivity.kt` line 190：`intent.getStringExtra("videoTitle")` 为 null → `titleBar.title` 未设置
- `VideoPlayerActivity.kt` line 874：通过 `observeEventSticky<String>(EventBus.VIDEO_SUB_TITLE) { binding.titleBar.title = it }` 更新标题
- `VideoPlay.kt` RssSource 分支：`player.setUp(..., rssArticle.title)` 传给 GSY 播放器，但**未同步 `videoTitle = rssArticle.title` + 未 `postEvent(VIDEO_SUB_TITLE)`** → TitleBar 标题为空

**修复方案**（2 处修改）：

| 修改点 | 文件 | 说明 |
|--------|------|------|
| ReadRss 传 videoTitle | `ui/rss/read/ReadRss.kt` | 两个 `readRss` 方法启动 VideoPlayerActivity 时传 `putExtra("videoTitle", rssArticle.title)`（record 分支从 record.title 获取） |
| VideoPlay 同步 postEvent | `model/VideoPlay.kt` | RssSource 分支 `player.setUp` 后：`videoTitle = rssArticle.title` + `postEvent(EventBus.VIDEO_SUB_TITLE, rssArticle.title)`（ruleContent 为空分支 + 非空单 URL 分支） |

**title 来源规则**：
- 单 URL 模式（ruleContent 为空 / 非空返回单 URL）：TitleBar.title = `rssArticle.title`（列表标题规则内容）
- 多行 URL 模式（ruleContent 返回多行 URL）：TitleBar.title = `rssArticle.title`（整个视频标题，非单集）
- JSON 数组多集模式（ruleContent 返回 JSON 数组）：TitleBar.title = `episode.title`（当前播放集标题，保持现有 playRssEpisode 逻辑）

### R4 日志异常优化

#### 4.1 Mixed Content（HTTP m3u8）

确认 `AndroidManifest.xml` 的 `usesCleartextTraffic` 配置：
```xml
<application
    android:usesCleartextTraffic="true"
    ... >
```
ExoPlayer 非 WebView，不受 WebView Mixed Content 限制，但需 cleartext 配置。若已配置则 HTTP m3u8 应可播放，失败原因是其他（Header/SSL/Cookie）。

#### 4.2 CryptoException

检查 `Rss.getContent()` 解析 ruleContent 时的异常处理，确保解密失败有明确错误反馈，不静默吞掉。

#### 4.3 SQLiteBlobTooBigException

检查视频缓存/历史记录写入时的数据大小，对超大 blob 截断或跳过。

#### 4.4 SocketException Connection reset

ExoPlayer 已有内置重试，但可增加友好提示。在 onPlayerError 回调中识别 SocketException 并提示"网络连接中断，请重试"。

#### 4.5 ForegroundServiceDidNotStartInTimeException（P0 崩溃，新发现）

**根因**：`VideoPlayService.startForegroundNotification()` (line 279-285) 的 try-catch 吞掉异常：

```kotlin
override fun startForegroundNotification() {
    try {
        val notification = createNotification()
        startForeground(NotificationId.VideoPlayService, notification.build())
    } catch (e: Exception) {
        AppLog.put("创建视频播放通知出错,${e.localizedMessage}", e, true)
        //创建通知出错不结束服务就会崩溃,服务必须绑定通知
        // ⚠️ 缺少 stopSelf()，导致服务未在前台运行但未停止
    }
}
```

当 `createNotification()` 或 `startForeground()` 抛异常时，catch 块只记日志，没有调用 `stopSelf()`，5 秒后系统抛出 `ForegroundServiceDidNotStartInTimeException` 崩溃。触发路径：`VideoPlayerActivity.startFloatingWindow()` → `ContextCompat.startForegroundService()` → `VideoPlayService.onStartCommand()` → `BaseService.onStartCommand()` → `startForegroundNotification()` → 异常。

**修复方案**：catch 块中调用 `stopSelf()`：
```kotlin
} catch (e: Exception) {
    AppLog.put("创建视频播放通知出错,${e.localizedMessage}", e, true)
    stopSelf()  // 新增：异常时停止服务，避免前台服务超时崩溃
}
```

#### 4.6 NullPointerException (RssSourceAdapter，新发现)

**根因**：`RssSourceAdapter.kt` line 220 的 `dragSelectCallback$1.getItemId()` 空指针，发生在拖拽选择时。

**修复方案**：`getItemId()` 添加空判断，返回安全默认值（0L）。

#### 4.7 SyntaxError: Empty JSON string（新发现）

**根因**：JS 脚本中 `JSON.parse()` 解析空字符串导致 `org.mozilla.javascript.EcmaError: SyntaxError: Empty JSON string`。大量出现在 07-08 23:49 日志中（多行号 #26/#32/#33/#36/#43）。

**修复方案**：这属于书源/订阅源 JS 脚本问题，非 App 代码 bug。但可在 Rhino 错误提示中增加引导信息，提示用户检查源规则的 JSON.parse 调用。

### R5 自动视频链接抓取（ruleContent 为空时）

#### 5.1 现状与问题

`VideoPlay.kt` line 199-223 的 `ruleContent.isNullOrBlank()` 分支直接用 `rssArticle.link`（文章 URL）作为播放地址。文章 URL 通常不是视频 URL（如 `https://example.com/video/123.html`），直接播放必然失败。

用户旧 WebView 方案（auto-video-player.html）有四种方法自动抓取视频链接，但内置播放器（type=2）走原生 Kotlin 不经 WebView，无此能力。

#### 5.2 VideoUrlExtractor 设计

新建 `app/src/main/java/io/legado/app/help/video/VideoUrlExtractor.kt`，提供 `extract(html, baseUrl): List<String>` 方法。

```kotlin
object VideoUrlExtractor {
    // 视频URL正则（忽略大小写，匹配 m3u8/mp4）
    private val VIDEO_URL_REGEX = Regex(
        """(?i)https?://[^\s'"<>\)\\]*(?:\.m3u8|\.mp4)[^\s'"<>\)\\]*"""
    )
    // JS变量赋值正则（匹配 var/let/const xxx = "http...m3u8/mp4"）
    private val JS_VAR_REGEX = Regex(
        """(?i)(?:var|let|const)\s+\w+\s*=\s*["'](https?://[^"']*(?:\.m3u8|\.mp4)[^"']*)"""
    )

    fun extract(html: String, baseUrl: String): List<String> {
        val urls = mutableListOf<String>()
        urls.addAll(extractByRegex(html, baseUrl))       // 方法①正则
        urls.addAll(extractFromVideoTags(html, baseUrl)) // 方法②video/source标签
        urls.addAll(extractFromMeta(html, baseUrl))      // 方法③OG/Meta
        urls.addAll(extractFromJsVars(html, baseUrl))    // 方法④JS变量
        return urls.distinct()
    }

    private fun extractByRegex(html: String, baseUrl: String): List<String> {
        // Regex(VIDEO_URL_REGEX).findAll → filter isVideoUrl → getAbsoluteURL
    }

    private fun extractFromVideoTags(html: String, baseUrl: String): List<String> {
        // jsoup.parse(html, baseUrl)
        // doc.select("video[src], video[data-src], source[src], [data-src]") → attr("src"/"data-src")
    }

    private fun extractFromMeta(html: String, baseUrl: String): List<String> {
        // jsoup.parse → doc.select("meta[property=og:video], meta[property=og:video:url], ...") → attr("content")
    }

    private fun extractFromJsVars(html: String, baseUrl: String): List<String> {
        // Regex(JS_VAR_REGEX).findAll → groupValues[1] → filter isVideoUrl → getAbsoluteURL
    }

    private fun isVideoUrl(url: String): Boolean {
        val lower = url.lowercase()
        return lower.contains(".m3u8") || lower.contains(".mp4") ||
               lower.contains("format=m3u8") || lower.contains("type=m3u8")
    }
}
```

#### 5.3 VideoPlay.kt 修改

修改 `startPlay()` 的 `ruleContent.isNullOrBlank()` 分支（line 200-223）：

```kotlin
val ruleContent = s.ruleContent
if (ruleContent.isNullOrBlank()) {
    // R5: 自动视频链接抓取
    // R3 title 修复：立即设置标题（避免抓取期间 TitleBar 为空）
    videoTitle = rssArticle.title
    postEvent(EventBus.VIDEO_SUB_TITLE, "正在抓取视频链接...")
    Coroutine.async(loadScope, IO) {
        // 1. 获取文章页面 HTML
        val analyzeUrl = AnalyzeUrl(
            rssArticle.link,
            source = source,
            ruleData = rssArticle
        )
        val res = analyzeUrl.getStrResponseAwait()
        val html = res.body ?: ""

        // 2. VideoUrlExtractor 综合提取视频 URL（五种方法去重）
        val videoUrls = VideoUrlExtractor.extract(html, rssArticle.link)

        when {
            videoUrls.size == 1 -> {
                // 单 URL：直接播放
                val mUrl = videoUrls[0]
                videoUrl = mUrl
                val playAnalyzeUrl = AnalyzeUrl(mUrl, source = source, ruleData = rssArticle)
                // R5 Header 修复：注入 Referer（模拟 WebView 行为，解决 CDN 防盗链 404）
                if (!playAnalyzeUrl.headerMap.any { it.key.equals("Referer", ignoreCase = true) }) {
                    playAnalyzeUrl.headerMap["Referer"] = rssArticle.link
                }
                withContext(Main) {
                    player.mapHeadData = playAnalyzeUrl.headerMap
                    player.setUp(playAnalyzeUrl.url, cachePlay, File(appCtx.externalCache, "exoplayer"), rssArticle.title)
                    postEvent(EventBus.VIDEO_SUB_TITLE, rssArticle.title)  // R3 title 修复
                    if (autoPlay) player.startPlayLogic()
                }
            }
            videoUrls.size > 1 -> {
                // 多 URL：直接构建 List<RssEpisode>（不走 parseRssEpisodes，避免 JSON 序列化/反序列化冗余）
                val episodes = videoUrls.mapIndexed { i, url ->
                    RssEpisode(title = "第${i + 1}集", url = NetworkUtils.getAbsoluteURL(rssArticle.link, url))
                }
                rssEpisodes = episodes
                rssEpisodeIndex = 0
                postEvent(EventBus.VIDEO_SUB_TITLE, rssArticle.title)  // R3 title 修复
                playRssEpisode(player, episodes[0])
                postEvent(EventBus.UP_VIDEO_INFO, arrayListOf(1))
            }
            else -> {
                // 未找到：回退当前逻辑 + AppLog 提示
                AppLog.put("R5自动抓取：未从文章页面找到视频URL，回退使用文章链接")
                val mUrl = rssArticle.link
                videoUrl = mUrl
                val fallbackUrl = AnalyzeUrl(mUrl, source = source, ruleData = rssArticle)
                // R5 Header 修复：注入 Referer
                if (!fallbackUrl.headerMap.any { it.key.equals("Referer", ignoreCase = true) }) {
                    fallbackUrl.headerMap["Referer"] = rssArticle.link
                }
                withContext(Main) {
                    player.mapHeadData = fallbackUrl.headerMap
                    player.setUp(fallbackUrl.url, cachePlay, File(appCtx.externalCache, "exoplayer"), rssArticle.title)
                    postEvent(EventBus.VIDEO_SUB_TITLE, rssArticle.title)  // R3 title 修复
                    if (autoPlay) player.startPlayLogic()
                }
            }
        }
    }.onError {
        AppLog.put("R5自动抓取视频链接失败", it, true)
    }
}
```

#### 5.4 复用现有架构

| 复用组件 | 用途 | 来源 |
|---------|------|------|
| `AnalyzeUrl` | 获取文章页面 HTML（getStrResponseAwait） | Rss.getContentAwait 模式 |
| `NetworkUtils.getAbsoluteURL` | 相对路径转绝对路径 | 项目工具类 |
| `Jsoup.parse` | 解析 HTML DOM | jsoup 1.16.2（项目已依赖） |
| `RssEpisode` | 多集数据结构（直接构建，不走 parseRssEpisodes） | R1 已实现 |
| `playRssEpisode` | 多集播放 | R1 已实现 |

#### 5.5 Header 修复（解决 404 Bug，检查点3用户反馈核心问题）

**根因分析**：

`Exo2MediaPlayer.prepareAsyncInternal()` (line 96-101) 使用 no-op resolver：
```kotlin
// 当前代码（有问题）：{ it } 不做任何处理
ResolvingDataSource.Factory(ExoPlayerHelper.cacheDataSourceFactory){ it }
```

而 `ExoPlayerHelper.resolvingDataSource` (line 72-90) 才负责解码 SPLIT_TAG 并设置 Header：
```kotlin
// 正确的 resolver：解码 SPLIT_TAG + 设置 Header
ResolvingDataSource.Factory(cacheDataSourceFactory) {
    if (it.uri.toString().contains(SPLIT_TAG)) {
        val urls = it.uri.toString().split(SPLIT_TAG)
        val headers = GSON.fromJson(urls[1], mapType)
        okhttpDataFactory.setDefaultRequestProperties(headers)  // ← 设置 Header
    }
    ...
}
```

GSY 父类 `IjkExo2MediaPlayer.setDataSource(context, uri, headers)` 接收了 `mapHeadData`，但 `prepareAsyncInternal` 的 no-op resolver 不处理 → **Header 丢失** → CDN 防盗链验证失败 → 404。

**修复方案**（三处修改）：

**修改1：ExoPlayerHelper.kt 暴露 Header 设置方法**
```kotlin
// help/exoplayer/ExoPlayerHelper.kt 新增
fun setDefaultHeaders(headers: Map<String, String>) {
    okhttpDataFactory.setDefaultRequestProperties(headers)
}
```

**修改2：ExoPlayerManager.kt 在 setDataSource 前设置 Header**（避免 override GSY 父类 setDataSource 的签名风险）
```kotlin
// help/gsyVideo/ExoPlayerManager.kt initVideoPlayer 方法中
// 在 mediaPlayer!!.setDataSource(context, model.getUrl().toUri(), model.getMapHeadData()) 之前添加：
model.getMapHeadData()?.let { ExoPlayerHelper.setDefaultHeaders(it) }
```

**优化说明**：原方案 override Exo2MediaPlayer.setDataSource 捕获 headers，但 IjkExo2MediaPlayer（GSY 依赖库）的 setDataSource 签名无法确认（源码不在项目中），override 有编译失败风险。改为在 ExoPlayerManager.initVideoPlayer（已知 override 方法，无签名风险）中直接调用 `setDefaultHeaders`，时序正确：`setDefaultHeaders` 在 `prepareAsyncInternal` 之前同步执行，`okhttpDataFactory` 的默认 Header 在 ExoPlayer 构建时已生效。

**修改3：VideoPlay.kt 自动注入 Referer**
```kotlin
// model/VideoPlay.kt RssSource 分支所有 AnalyzeUrl 创建处
// 在 player.mapHeadData = analyzeUrl.headerMap 之前添加：
if (!analyzeUrl.headerMap.any { it.key.equals("Referer", ignoreCase = true) }) {
    analyzeUrl.headerMap["Referer"] = rssArticle.link  // 模拟 WebView 行为
}
```

**适用范围**：Header 修复适用于所有 type=2 视频播放场景：
- R5 自动抓取分支（ruleContent 为空）
- ruleContent 非空分支（现有逻辑，用户 404 Bug 发生处）
- singleUrl 分支

**加密串 URL 处理策略**：
- **路径加密 URL**（如 `cdnwb.streamfastpro.com/{hash}/{token}/xxx.m3u8`）：R5 提取的完整 URL 直接播放，配合 Header 修复（Referer 注入）解决 404
- **JS 解密 URL**：原生 Kotlin 无法执行页面 JS 解密逻辑 → R5 无法处理 → 回退提示用户用 type=0 WebView 模式
- **动态生成 URL**（XHR/Fetch 拦截型）：同 JS 解密，R5 无法处理

#### 5.6 适配性增强（方法⑤ script JSON 提取）

在 `VideoUrlExtractor.extract` 中新增方法⑤：

```kotlin
private fun extractFromScriptJson(html: String, baseUrl: String): List<String> {
    val urls = mutableListOf<String>()
    val doc = Jsoup.parse(html, baseUrl)
    // 解析 <script> 标签内 JSON 数据，提取含视频 URL 的字段
    doc.select("script").forEach { script ->
        val text = script.data()
        if (text.contains("m3u8") || text.contains("mp4")) {
            // 尝试从 JSON 中提取 URL（匹配 "url":"http...m3u8/mp4" 等模式）
            val jsonUrlRegex = Regex("""(?i)["'](?:url|src|video|source|file)["']\s*[:=]\s*["'](https?://[^"']*(?:\.m3u8|\.mp4)[^"']*)""")
            jsonUrlRegex.findAll(text).forEach { match ->
                val url = match.groupValues[1]
                if (isVideoUrl(url)) {
                    urls.add(NetworkUtils.getAbsoluteURL(baseUrl, url))
                }
            }
        }
    }
    return urls
}
```

更新 `extract` 方法调用：
```kotlin
fun extract(html: String, baseUrl: String): List<String> {
    val urls = mutableListOf<String>()
    urls.addAll(extractByRegex(html, baseUrl))           // 方法①正则
    urls.addAll(extractFromVideoTags(html, baseUrl))     // 方法②video/source标签
    urls.addAll(extractFromMeta(html, baseUrl))          // 方法③OG/Meta
    urls.addAll(extractFromJsVars(html, baseUrl))        // 方法④JS变量
    urls.addAll(extractFromScriptJson(html, baseUrl))    // 方法⑤script JSON（R5增强）
    return urls.distinct()
}
```

## Architecture Decisions

### ADR-1：多集解析用 EventBus 还是直接回调

**Context**：R2 错误回调需从 Exo2MediaPlayer 传到 VideoPlayerActivity，中间隔 GSY 框架多层

**Decision**：采用 EventBus 通知机制

**Consequences**：
- ✅ 不破坏 GSY 现有回调链，改动最小
- ✅ 解耦，Exo2MediaPlayer 不依赖 Activity
- ⚠️ EventBus 需注册/反注册，需注意生命周期

### ADR-2：多集数据用新字段还是复用 episodes

**Context**：R1 多集需存储集数列表，BookSource 有 episodes 字段

**Decision**：VideoPlay 新增 `rssEpisodes: List<RssEpisode>?` 字段，不复用 `episodes: List<BookChapter>?`

**Consequences**：
- ✅ 类型隔离，RssEpisode 与 BookChapter 不耦合
- ✅ 判断逻辑清晰：`book!=null` 用 episodes，`book==null` 用 rssEpisodes
- ⚠️ VideoPlay 字段增多，但符合现有单例设计

### ADR-3：调试面板用 Activity 布局还是悬浮窗

**Context**：调试日志需在播放时显示，全屏播放时 Activity 布局不可见

**Decision**：非全屏用 Activity 布局面板，全屏时记录到 AppLog 供事后查看

**Consequences**：
- ✅ 非全屏直接可见，体验好
- ✅ 全屏不打断播放
- ⚠️ 全屏播放失败时用户需退出全屏查看，但可通过 onPlayerError 自动退出全屏

### ADR-4：R5 视频URL提取用原生 Kotlin 还是复用 WebView JS

**Context**：ruleContent 为空时需自动抓取视频链接，auto-video-player.html 有四种方法但运行在 WebView JS 环境

**Decision**：采用原生 Kotlin 实现（正则+jsoup），不复用 WebView JS

**Consequences**：
- ✅ 性能好（无需启动 WebView）
- ✅ 符合 type=2 内置播放器初衷（避免 WebView）
- ✅ 复用项目已有 jsoup 依赖，无新依赖
- ⚠️ 无法处理 JS 动态渲染页面（XHR/Fetch 拦截不可实现）
- ⚠️ 未找到时需回退+提示，用户需自行填写 ruleContent 或用 type=0

## Data Flow

### 多集播放数据流

```
用户点击订阅文章
  → ReadRss.readRss(fragment, rssArticle, rssSource)
  → type==2 → VideoPlayerActivity.start(sourceKey, sourceType=rss, record=link)
  → VideoPlayerActivity.onCreate → VideoPlay.startPlay(player)
  → RssSource 分支 → Rss.getContent(rssArticle, ruleContent, source)
  → parseRssEpisodes(content)
    → JSON数组 → rssEpisodes
    → 多行URL → rssEpisodes
    → 单URL → 现有逻辑
  → 若 rssEpisodes != null → playRssEpisode(player, episodes[0])
  → VideoPlayerActivity.initView → showRssEpisodes(rssEpisodes)
  → 用户点击集数 → onRssEpisodeClick(index) → playRssEpisode(player, episode)
```

### 错误反馈数据流

```
ExoPlayer prepareAsync → 播放失败
  → Exo2MediaPlayer.onPlayerErrorChanged(error)
  → 构造 VideoErrorInfo
  → postEvent(EventBus.VIDEO_PLAY_ERROR, errorInfo)
  → VideoPlayerActivity.onVideoPlayError(event)
  → appendDebugLog(...)
  → debugPanel.visible()
  → 用户查看错误信息
```

### R5 自动抓取数据流

```
用户点击订阅文章（ruleContent 为空，type=2）
  → ReadRss.readRss(fragment, rssArticle, rssSource)
  → type==2 → VideoPlayerActivity.start(sourceKey, sourceType=rss, record=link)
  → VideoPlayerActivity.onCreate → VideoPlay.startPlay(player)
  → RssSource 分支 → ruleContent.isNullOrBlank() == true
  → R5 触发：
    ① AnalyzeUrl(rssArticle.link, source, ruleData=rssArticle).getStrResponseAwait() → 文章页面 HTML
    ② VideoUrlExtractor.extract(html, rssArticle.link)
       → 方法①正则 extractByRegex
       → 方法②video/source 标签 extractFromVideoTags（jsoup）
       → 方法③OG/Meta extractFromMeta（jsoup）
       → 方法④JS 变量 extractFromJsVars
       → 四种方法结果合并 distinct 去重
    ③ 按结果数量分支：
       → size==1 → 单 URL 直接播放（AnalyzeUrl + setUp + startPlayLogic）
       → size>1  → 直接构建 List<RssEpisode> → rssEpisodes → playRssEpisode
       → size==0 → 回退当前逻辑（用 rssArticle.link）+ AppLog 提示"未从文章页面找到视频URL"
  → 异常 → onError → AppLog.put("R5自动抓取视频链接失败", it, true)
```

## File Changes

| 文件 | 变更类型 | 说明 |
|------|---------|------|
| `model/VideoPlay.kt` | 修改 | 新增 rssEpisodes/rssEpisodeIndex 字段；RssSource 分支增加多集解析；新增 playRssEpisode 方法；**R5**: ruleContent.isNullOrBlank() 分支集成自动抓取（AnalyzeUrl 获取 HTML → VideoUrlExtractor.extract → 三分支处理）；**R3 title 修复**: RssSource 分支 player.setUp 后同步 `videoTitle = rssArticle.title` + `postEvent(VIDEO_SUB_TITLE)` |
| `data/entities/RssEpisode.kt` | 新增 | RssEpisode data class |
| `help/gsyVideo/Exo2MediaPlayer.kt` | 修改 | 实现 onPlayerError 回调；记录 currentUrl |
| `help/gsyVideo/ExoPlayerManager.kt` | **修改（R5 Header 修复）** | initVideoPlayer 中 setDataSource 前调用 `ExoPlayerHelper.setDefaultHeaders(model.getMapHeadData())`，避免 override GSY 父类 setDataSource 签名风险 |
| `help/gsyVideo/VideoErrorInfo.kt` | 新增 | 错误信息数据类 |
| `help/exoplayer/ExoPlayerHelper.kt` | **修改（R5 Header 修复）** | 新增 `setDefaultHeaders(headers)` 方法，暴露 okhttpDataFactory.setDefaultRequestProperties，解决 ExoPlayer Header 丢失导致 404 |
| `constant/EventBus.kt` | 修改 | 新增 VIDEO_PLAY_ERROR 常量 |
| `ui/video/VideoPlayerActivity.kt` | 修改 | initView 增加 rssEpisodes 显示；新增功能区按钮逻辑(快进快退/倍速/调试/复制URL)；EventBus 注册/接收；播放地址展示；**R3 布局优化**: btn_copy_url 复制按钮逻辑 |
| `res/layout/activity_video_player.xml` | 修改 | 新增 rss_video_panel 订阅源功能区；**R3 布局优化**: 播放地址 maxLines=3 换行+复制按钮、Spinner 统一尺寸(48dp/36dp) |
| `res/values/styles.xml` | 修改 | 新增 VideoCtrlButton 样式；**R3 优化**: 增加 minHeight=36dp + 圆角背景 bg_video_ctrl_btn |
| `res/drawable/bg_video_ctrl_btn.xml` | **新增（R3）** | 圆角背景 drawable（淡灰背景+2dp 圆角），VideoCtrlButton 引用 |
| `ui/rss/read/ReadRss.kt` | **修改（R3 title 修复）** | 两个 readRss 方法启动 VideoPlayerActivity 时传 `putExtra("videoTitle", rssArticle.title)` |
| `app/src/main/AndroidManifest.xml` | 检查 | 确认 usesCleartextTraffic 配置 |
| `service/VideoPlayService.kt` | 修改 | R4.5 startForegroundNotification catch 块添加 stopSelf()，避免前台服务超时崩溃 |
| `ui/rss/source/manage/RssSourceAdapter.kt` | 修改 | R4.6 dragSelectCallback.getItemId 空指针修复 |
| `help/video/VideoUrlExtractor.kt` | **新增（R5）** | 视频URL提取器：extract(html, baseUrl) 综合五种方法（正则+video标签+Meta+JS变量+script JSON）去重返回；私有 isVideoUrl 过滤 |

## 风险与缓解

| 风险 | 概率 | 影响 | 缓解 |
|------|------|------|------|
| 多行 URL 误判（HTML 含换行） | 中 | 多集解析错误 | 仅当每行都是合法 URL（http/https 开头）才判定多集 |
| GSY 框架版本不兼容 onPlayerErrorChanged | 低 | 编译失败 | media3 1.x 已支持 onPlayerErrorChanged，项目已用 media3 |
| EventBus 内存泄漏 | 低 | Activity 泄漏 | onDestroy 反注册 |
| 调试面板影响播放性能 | 低 | 卡顿 | 默认隐藏，仅显示时渲染 |
| **R5: JS 动态渲染页面无法提取** | 高 | 部分站点视频URL提取失败 | 原生 HTTP 获取的 HTML 可能不含视频URL（需JS执行后渲染）；未找到时回退当前逻辑+AppLog提示；用户需自行填写 ruleContent 或用 type=0 WebView 模式 |
| **R5: 正则误匹配非视频URL** | 中 | 提取到含 m3u8/mp4 字样的文本链接 | isVideoUrl 二次过滤 + distinct 去重；video/source/Meta 标签提取优先于正则（更精确）；多方法综合后去重降低误匹配影响 |
