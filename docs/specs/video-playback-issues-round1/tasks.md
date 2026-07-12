# tasks.md — 视频播放问题修复第1轮

## P0: ExoPlayer 失败降级机制（使用 skill V2 模板）

- [ ] 1.1 Exo2MediaPlayer.onPlayerError 补充 ERROR_CODE_IO_UNSPECIFIED (2000) 友好提示
  - 修改文件: `app/src/main/java/io/legado/app/help/gsyVideo/Exo2MediaPlayer.kt`
  - 修改位置: L218-240 的 when 表达式
  - 添加: `PlaybackException.ERROR_CODE_IO_UNSPECIFIED -> "视频格式不兼容，可尝试使用 WebView 播放"`

- [ ] 1.2 将 skill V2 模板复制到 App assets 目录
  - 源文件: `.trae/skills/legado-source-creator/templates/hls-video-player.html`（774行）
  - 目标文件: `app/src/main/assets/hls_video_player_template.html`
  - 修改: 添加 Headers 注入支持（HLS.js xhrSetup，支持 Referer 等自定义 Header）

- [ ] 1.3 创建错误对话框布局 dialog_video_play_error.xml
  - 新增文件: `app/src/main/res/layout/dialog_video_play_error.xml`
  - 内容: 错误信息 + "重试"/"使用WebView播放"/"取消" 三按钮

- [ ] 1.4 VideoPlayerActivity 修改 VIDEO_PLAY_ERROR 事件处理
  - 修改文件: `app/src/main/java/io/legado/app/ui/video/VideoPlayerActivity.kt`
  - 当前: 仅显示错误信息
  - 修改后: 显示错误对话框，含"使用 WebView 播放"按钮
  - 点击"使用 WebView 播放" → 调用 WebViewVideoPlayer.play(url, title, headers)

- [ ] 1.5 创建 WebViewVideoPlayer.kt 封装 WebView 视频播放（使用 V2 模板）
  - 新增文件: `app/src/main/java/io/legado/app/ui/video/WebViewVideoPlayer.kt`
  - 功能:
    - 读取 assets/hls_video_player_template.html 模板内容
    - 替换 {{result}} 为视频 URL, {{videoTitle}} 为标题, {{referer}} 为 Referer
    - webView.loadDataWithBaseURL 加载替换后的 HTML
    - 复用 V2 模板完整功能（进度条/倍速/全屏/横竖屏/上下集/错误重试）
    - 处理多视频地址（逗号分隔）
  - 接口: `fun play(url: String, title: String, headers: Map<String, String>)`

- [ ] 1.6 VideoFragment 添加 WebView 播放模式支持
  - 修改文件: `app/src/main/java/io/legado/app/ui/video/VideoFragment.kt`
  - 添加: WebViewVideoPlayer 实例 + 切换逻辑
  - 显示"切换回内置播放器"按钮
  - WebView 播放时隐藏 ExoPlayer 控件，显示"切换回内置播放器"按钮

- [ ] 1.7 VideoPlay 新增 playerType 配置
  - 修改文件: `app/src/main/java/io/legado/app/model/VideoPlay.kt`
  - 新增: `var playerType: Int`（0=AUTO, 1=EXO_PLAYER, 2=WEB_VIEW）
  - 修改: startPlay() 根据 playerType 选择播放方式
    - AUTO/EXO_PLAYER → 使用 ExoPlayer（当前逻辑）
    - WEB_VIEW → 使用 WebViewVideoPlayer.play()

- [ ] 1.8 VideoSettingsPanel 添加"播放器类型"设置项
  - 修改文件: `app/src/main/java/io/legado/app/ui/video/VideoSettingsPanel.kt`
  - 新增: 播放器类型选择（自动/内置播放器/WebView）
  - 持久化到 SharedPreferences

- [ ] 1.9 strings.xml 添加错误提示文案
  - 修改文件: `app/src/main/res/values/strings.xml`
  - 新增: 视频格式不兼容/使用WebView播放/切换回内置播放器/播放器类型 等文案

## P1: 加密解密失败 + ClassCastException 容错

- [ ] 2.1 加密解密失败容错（IllegalBlockSizeException）
  - 修改文件: `app/src/main/java/io/legado/app/model/rss/Rss.kt`（或 JS 执行入口）
  - 捕获 IllegalBlockSizeException → 显示源名称 + 友好提示
  - 不崩溃，允许用户继续使用其他源

- [ ] 2.2 ClassCastException 类型容错（String→List）
  - 修改文件: `app/src/main/java/io/legado/app/model/analyzeRule/AnalyzeRule.kt`
  - 检测 String 类型时自动包装为单元素 List
  - 避免直接 `as List<*>` 强制转换

## P2: 网络连接问题 + 源格式容错

- [ ] 3.1 网络重试机制（Connection reset/Timeout）
  - 修改文件: `app/src/main/java/io/legado/app/model/analyzeRule/AnalyzeUrl.kt`
  - 检测 Connection reset/SocketTimeoutException → 自动重试（最多 2 次，间隔 1 秒）

- [ ] 3.2 链接参数 JSON 格式容错
  - 修改文件: 待确认（搜索"链接参数 JSON 格式不规范"定位）
  - 尝试宽松解析非标准 JSON
  - 解析失败时记录警告，不阻塞播放

## 验证与文档

- [ ] 4.1 编译验证（`.radlew.bat assembleDebug`）
- [ ] 4.2 L2 真机验证：ExoPlayer 失败 → 点击 WebView 降级 → V2 模板播放（进度条/倍速/全屏功能正常）
- [ ] 4.3 L2 真机验证：设置播放器类型为 WebView → 直接 V2 模板播放
- [ ] 4.4 L2 真机验证：加密解密失败源 → 显示友好提示不崩溃
- [ ] 4.5 L2 真机验证：ClassCastException 源 → 类型容错正常显示
- [ ] 4.6 更新 updateLog.md
- [ ] 4.7 更新 docs/INDEX.md
- [ ] 4.8 更新 project_memory.md 活跃 Spec 清单

## AOAdapt 日志

（遇问题时记录）
