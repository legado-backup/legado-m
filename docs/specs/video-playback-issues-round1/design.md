# design.md — 视频播放问题修复第1轮

## Technical Approach（技术方案）

### P0: ExoPlayer 失败降级机制（使用 skill V2 模板）

#### 架构设计

```
VideoPlayerActivity
├── VideoFragment (内置播放器模式)
│   ├── Exo2MediaPlayer → ExoPlayer
│   └── onPlayerError → VIDEO_PLAY_ERROR 事件
│       └── VideoPlayerActivity 接收 → 显示错误对话框
│           ├── "重试" 按钮 → 重新播放
│           ├── "使用 WebView 播放" 按钮 → 切换 WebView 模式 (S0-1)
│           └── "取消" 按钮 → 关闭
└── WebView 视频播放模式 (新增，使用 skill V2 模板)
    ├── 读取 assets/hls_video_player_template.html (V2 模板)
    ├── 替换 {{result}} 为视频 URL
    ├── 替换 {{videoTitle}} 为视频标题
    ├── 通过 HLS.js xhrSetup 注入 Referer/Header
    ├── WebView loadDataWithBaseURL 加载 HTML
    └── "切换回内置播放器" 按钮
```

#### 播放器类型配置

```
AppConfig / VideoPlay
└── playerType: Int (新增配置项)
    ├── 0 = AUTO (默认，内置播放器 + 失败提示降级)
    ├── 1 = EXO_PLAYER (强制内置播放器)
    └── 2 = WEB_VIEW (强制 WebView，使用 V2 模板)
```

#### V2 模板集成方案

**模板来源**: `.trae/skills/legado-source-creator/templates/hls-video-player.html`（774行，V2.20260606.1）

**集成步骤**:
1. 将 V2 模板复制到 App assets 目录: `app/src/main/assets/hls_video_player_template.html`
2. 修改模板，添加 Headers 注入支持（HLS.js xhrSetup）
3. WebViewVideoPlayer.kt 读取模板内容，替换变量，加载到 WebView

**模板变量替换**:
| 变量 | 替换为 | 说明 |
|------|--------|------|
| `{{result}}` | 视频 URL（m3u8/mp4） | 支持多地址（逗号分隔） |
| `{{videoTitle}}` | 视频标题 | 从 rssArticle.title 获取 |

**Headers 注入方案**:
V2 模板使用 HLS.js，通过 `xhrSetup` 回调设置请求头：
```javascript
// 在模板中添加（或通过 JS 注入）
hls.config.xhrSetup = function(xhr, url) {
    xhr.setRequestHeader('Referer', '{{referer}}');
    // 其他 Headers...
};
```

#### 实现要点

**S0-1: 错误提示添加 WebView 降级按钮（使用 V2 模板）**

修改 `VideoPlayerActivity` 接收 `VIDEO_PLAY_ERROR` 事件的处理逻辑：
- 当前: 仅显示错误信息
- 修改后: 显示错误对话框，包含"使用 WebView 播放"按钮
- 点击按钮后: 
  1. 获取当前视频 URL + Headers + 标题
  2. 读取 V2 模板内容
  3. 替换 `{{result}}` / `{{videoTitle}}` / `{{referer}}`
  4. WebView `loadDataWithBaseURL` 加载 HTML

**S0-2: 播放器类型配置**

在视频播放设置中添加"播放器类型"选项：
- 存储位置: `VideoPlay.playerType`（SharedPreferences）
- UI 入口: VideoSettingsPanel 设置面板
- 读取位置: `VideoPlay.startPlay()` 根据 playerType 选择播放方式
- playerType == WEB_VIEW 时，直接用 V2 模板播放

**S0-3: 补充 ERROR_CODE_IO_UNSPECIFIED 友好提示**

修改 `Exo2MediaPlayer.onPlayerError`：
- 当前: `else -> null`（2000 错误码无友好提示）
- 修改后: `ERROR_CODE_IO_UNSPECIFIED -> "视频格式不兼容，可尝试使用 WebView 播放"`

### P1-1: 加密解密失败容错

#### 实现要点

修改 JS 脚本执行的错误处理逻辑：
- 捕获 `IllegalBlockSizeException` 时，记录源名称到错误信息
- 显示友好提示："订阅源 XXX 解密失败，请联系源作者修复"
- 不崩溃，允许用户继续使用其他源

### P1-2: ClassCastException 类型容错

#### 实现要点

修改 `Rss.getContent` 或 `parseRssRoutes` 的类型处理：
- 检测 `ruleContent` 返回类型为 String 时，自动包装为单元素 List
- 避免直接 `as List<*>` 强制转换

### P2-1: 网络连接问题优化

#### 实现要点

修改 `AnalyzeUrl` 的网络请求逻辑：
- 检测 `Connection reset` / `SocketTimeoutException` 时自动重试（最多 2 次）
- 重试间隔 1 秒

### P2-2: 源格式容错

#### 实现要点

修改链接参数 JSON 解析逻辑：
- 检测 JSON 格式不规范时，尝试宽松解析（如允许尾随逗号、单引号）
- 解析失败时记录警告日志，不阻塞播放

## Architecture Decisions（架构决策）

### ADR-1: 降级策略选择

**Context**: ExoPlayer 对 HLS TS 分片解析过严导致播放失败，需要降级机制

**Decision**: 采用手动降级（V2 模板）+ 配置选项（播放器类型）组合方案

**Y-Statement**:
- **In the context of** ExoPlayer HLS 播放失败（H264 SPS 解析异常）
- **facing** 自动降级实现复杂/修复 TsExtractor 工作量大/仅用 WebView 功能降级/简单 video 标签功能太少
- **we decided for** 手动降级（使用 skill V2 模板）+ 配置选项
- **and accepted** 用户需手动点击降级/WebView 模式需加载 HLS.js/配置可能被忽略
- **to achieve** 快速解决用户问题 + 用户可控 + 复用 skill 成熟模板 + 保留 ExoPlayer 优势
- **neglecting** 自动降级的无缝体验

### ADR-2: 使用 skill V2 模板而非简单 video 标签

**Context**: 降级到 WebView 播放时，需要选择播放器实现

**Decision**: 复用 skill 中的 V2 hls-video-player.html 模板（774行）

**Y-Statement**:
- **In the context of** 需要 WebView 视频播放降级
- **facing** 简单 video 标签/skill V2 模板/自建播放器
- **we decided for** 复用 skill V2 模板
- **and accepted** 需要将模板复制到 App assets/需修改模板支持 Headers 注入
- **to achieve** 代码复用 + 功能丰富（进度条/倍速/全屏/横竖屏/上下集/错误重试）+ 经实战验证
- **neglecting** 自建播放器的定制化能力

### ADR-3: V2 模板而非 V1/V3

**Context**: skill 有三版本视频播放器模板（V1/V2/V3）

**Decision**: 降级场景使用 V2 模板

**Y-Statement**:
- **In the context of** ExoPlayer 失败降级到 WebView
- **facing** V1 自动抓取/V2 手动输入/V3 注入式
- **we decided for** V2 手动输入
- **and accepted** V2 模板需要手动传入视频 URL
- **to achieve** 降级场景已有视频 URL，V2 直接加载最合适
- **neglecting** V1 的自动提取能力（降级场景不需要）

## Data Flow（数据流）

### ExoPlayer 失败降级流程（使用 V2 模板）

```
1. VideoPlay.startPlay() → player.setUp(url) → player.startPlayLogic()
2. Exo2MediaPlayer.prepareAsyncInternal() → ExoPlayer.prepare()
3. ExoPlayer 加载 HLS → TsExtractor 解析 TS 分片
4. H264Reader.endNalUnit() → NalUnitUtil.parseSpsNalUnitPayload()
5. ParsableNalUnitBitArray.assertValidOffset() → IllegalStateException
6. ExoPlayer → onPlayerError(PlaybackException)
7. Exo2MediaPlayer.onPlayerError() → AppLog.put() + postEvent(VIDEO_PLAY_ERROR)
8. VideoPlayerActivity 接收 VIDEO_PLAY_ERROR → 显示错误对话框
9. 用户点击"使用 WebView 播放"
10. WebViewVideoPlayer.play(url, title, headers)
    → 读取 assets/hls_video_player_template.html
    → 替换 {{result}} = url, {{videoTitle}} = title, {{referer}} = headers['Referer']
    → webView.loadDataWithBaseURL(url, html, "text/html", "utf-8", url)
11. WebView 加载 HTML → HLS.js 初始化 → Chromium 播放视频
```

### 播放器类型选择流程

```
1. VideoPlay.startPlay() 读取 playerType 配置
2. playerType == AUTO → 使用 ExoPlayer（默认）
3. playerType == EXO_PLAYER → 使用 ExoPlayer（强制）
4. playerType == WEB_VIEW → 使用 V2 模板（强制）
5. AUTO 模式失败 → 显示降级提示（含"使用 WebView 播放"按钮）
```

## File Changes（文件变更）

### 新增文件

| 文件 | 说明 |
|------|------|
| `app/src/main/assets/hls_video_player_template.html` | skill V2 模板副本（774行，添加 Headers 注入支持） |
| `app/src/main/java/io/legado/app/ui/video/WebViewVideoPlayer.kt` | WebView 视频播放器封装（读取 V2 模板 + 变量替换 + 加载） |
| `app/src/main/res/layout/dialog_video_play_error.xml` | 错误对话框布局（含 WebView 降级按钮） |

### 修改文件

| 文件 | 修改内容 |
|------|---------|
| `app/src/main/java/io/legado/app/help/gsyVideo/Exo2MediaPlayer.kt` | onPlayerError 补充 ERROR_CODE_IO_UNSPECIFIED (2000) 友好提示 |
| `app/src/main/java/io/legado/app/ui/video/VideoPlayerActivity.kt` | VIDEO_PLAY_ERROR 事件处理改为显示错误对话框（含 WebView 降级按钮） |
| `app/src/main/java/io/legado/app/ui/video/VideoFragment.kt` | 添加 WebView 播放模式支持（WebViewVideoPlayer 实例 + 切换逻辑） |
| `app/src/main/java/io/legado/app/model/VideoPlay.kt` | startPlay 根据 playerType 选择播放方式；新增 playerType 配置 |
| `app/src/main/java/io/legado/app/ui/video/VideoSettingsPanel.kt` | 添加"播放器类型"设置项 |
| `app/src/main/res/values/strings.xml` | 新增错误提示文案 |
| `app/src/main/assets/updateLog.md` | 更新变更说明 |

### P1/P2 修改文件

| 文件 | 修改内容 |
|------|---------|
| `app/src/main/java/io/legado/app/model/analyzeRule/AnalyzeRule.kt` | ClassCastException 类型容错（String→List） |
| `app/src/main/java/io/legado/app/model/analyzeRule/AnalyzeUrl.kt` | 网络重试机制（Connection reset） |
| `app/src/main/java/io/legado/app/model/rss/Rss.kt` | 加密解密失败容错（IllegalBlockSizeException） |

## 风险评估

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| WebView 模式需加载 HLS.js | 首次加载需 200KB CDN 下载 | 后续有浏览器缓存；可考虑将 hls.js 内嵌到 assets |
| Headers 注入可能不完整 | 部分防盗链可能仍失败 | 通过 xhrSetup 尽量注入；失败时提示用户 |
| 配置项增加用户困惑 | 用户不知道选哪个 | 默认 AUTO 模式，添加说明文案 |
| 降级对话框打断体验 | 用户需手动点击 | 后续可优化为自动降级 |
| P1/P2 容错可能掩盖真实问题 | 源作者不知道源有问题 | 记录详细日志 + 错误提示含源名称 |
