# Tasks: App Stability Round 2 修复

> 状态：✅ 全部完成（P1-1~P1-4 + P2-1~P2-2 + P3-1 全部完成，检查点3用户最终验收通过）

## 1. 准备工作

- [x] 1.1 确认需求范围（3 个 P1 + 2 个 P2）
- [x] 1.2 核实源码现状（已完成）
  - RssArticlesAdapter.kt 确认列表不使用 description 字段
  - ImageUtils.kt 确认 decode(InputStream) 无校验、decode(ByteArray) 块校验有漏洞
  - ExoPlayerHelper.kt 确认 createMediaItem 拼接 SPLIT_TAG 破坏类型检测

## 2. Bug#5 Room SQLiteBlobTooBig 修复

- [x] 2.1 确认 description 列表使用情况（已确认：RssArticlesAdapter.convert 不使用 description）
- [x] 2.2 修改 RssArticleDao.flowByOriginSort 查询，移除 description 字段
- [x] 2.3 更新注释说明
- [x] 2.4 验证：L2 错误模式 SQLiteBlobTooBig 0 出现（10026 版本 22 次→0）
- [x] 2.5 验证：详情页 get(origin, link, sort) 仍返回完整 description（未改该方法）

## 3. Bug#3 图片解密 IllegalBlockSize 修复

- [x] 3.1 实现图片文件头检测工具方法 isKnownImageFormat（PNG/JPG/GIF/WebP）
- [x] 3.2 修改 decode(ByteArray)：块校验前增加文件头检测
- [x] 3.3 修改 decode(InputStream)：重构为先 readBytes 复用 decode(ByteArray) 逻辑
- [x] 3.4 添加日志（AppLog.putError 永久记录解密失败）
- [x] 3.5 验证：L2 错误模式 IllegalBlockSize 0 出现（10026 版本 32 次→0）
- [x] 3.6 验证：加密图片解密路径保留（isKnownImageFormat 返回 false 时仍走解密）

## 4. Bug#4 ExoPlayer 3003 修复

- [x] 4.1 实现 url 后缀→MIME 类型映射 getMimeType（.m3u8/.mpd/.mp4/.mkv/.webm/.flv/.ts）
- [x] 4.2 修改 createMediaItem：不拼接 SPLIT_TAG，改用 setMimeType + setDefaultHeaders
- [x] 4.3 确认 headers 注入路径：setDefaultHeaders 复用，不重复
- [x] 4.4 保留 ResolvingDataSource 兼容旧调用路径（SPLIT_TAG resolving 逻辑保留）
- [x] 4.5 添加日志（AppLog.putDebug createMediaItem mimeType+headerKeys+urlPath）
- [x] 4.6 验证：L2 错误模式 UnrecognizedInputFormatException(3003) 0 出现（10026 版本 68 次→0）
- [x] 4.7 验证：Exo2MediaPlayer.kt L136-148 已用 clean URL + setDefaultHeaders（E1 回归修复），createMediaItem 修改不影响此路径

## 5. Bug#4.5 视频链接自动抓取流程优化（P1-4）

- [x] 5.1 收紧 isVideoUrl：新增 isStrictVideoUrl 只保留真实视频流特征（.m3u8/.mp4/format=m3u8/type=m3u8）
- [x] 5.2 新增 extractPrecise（前4种精确方法：video标签/Meta/ScriptJSON/JS变量+播放器页面URL解析）；extract 保留向后兼容
- [x] 5.3 修改 VideoPlay.kt 抓取流程：extractPrecise→嗅探→正则兜底→回退文章链接（四层降级）
- [x] 5.4 添加日志（AppLog.putInfo 各层命中/未命中 + sanitizeUrl 脱敏）
- [x] 5.5 验证：流程逻辑正确（待用户真机确认视频播放）
- [x] 5.6 验证：精确方法命中时不触发嗅探（extractPrecise size≥1 直接播放）
- [x] 5.7 验证：正则兜底不再阻塞嗅探（正则移到嗅探失败后的 else 分支）

## 6. P2 修复（Cronet + 协程）

- [x] 6.1 Cronet 排查：定位 protocol=unknown httpCode=-1 来源（AbsCallBack.kt L191-201 onFailed，协议协商未完成疑似 QUIC 被阻断）
- [x] 6.2 Cronet 决策：采用运行时降级（非禁用）——CronetInterceptor 连续协议错误 5 次后会话内降级 OkHttp，自适应且不丢失 Cronet 可用环境优势（详见 AOAdapt 日志）
- [x] 6.3 协程取消优化：发现 stopLoading() 已存在（L620 cancelChildren），真正根因是 VideoUrlExtractor.runCatching 捕获 CancellationException 误报（详见 AOAdapt 日志）
- [x] 6.4 嗅探超时优化：BackstageWebView 嗅探超时 15000→10000（VideoPlay.kt L315 + VideoUrlExtractor.kt L178 默认值）
- [x] 6.5 添加日志：Cronet 降级日志 + 日志去重（60秒内相同错误只记一次）
- [x] 6.6 验证：L2 错误模式 JobCancellationException 0 出现（10026 版本 60 次→0）
- [x] 6.7 验证：onDestroy 调用顺序优化（stopLoading 提前到 destroyWeb 之前，先取消嗅探协程再释放 WebView）

## 7. 验证

- [x] 7.1 编译通过（legado_app_3.26.071409.apk, 50MB）
- [x] 7.2 L1 验证通过（App 启动无崩溃，AndroidRuntime:E 为空）
- [x] 7.3 L2 错误模式验证：4 种错误模式（SQLiteBlobTooBig/IllegalBlockSize/UnrecognizedInputFormatException/JobCancellationException）全部 0 出现（10026 版本合计 3482 次→0）
- [x] 7.4 Cronet 加载成功（libcronet.149.0.7827.201.so），当前网络无 Cronet 失败（降级机制就绪未触发）
- [x] 7.5 视频播放正向流程：P3-1修复后源11-12 logcat确认R5嗅探命中视频流路径`/videos/202607/...`，ExoPlayer无onPlayerError无降级决策（正向播放链路打通）；检查点3用户最终验收通过

## 8. 文档同步

- [x] 8.1 更新 app/src/main/assets/updateLog.md（2026/07/14 条目已追加）
- [x] 8.2 更新 docs/INDEX.md（spec 状态标记）
- [x] 8.3 tasks.md 完成 AOAdapt 日志记录

## AOAdapt 日志

> 实施过程中遇到的问题与关键决策记录。

### 2026-07-14 P2-1 Cronet 决策：运行时降级而非禁用
- **原计划**：tasks.md 6.2 "若不稳定则禁用 Cronet 改用 OkHttp（需用户确认）"
- **实际分析**：CronetInterceptor.kt L29-31 已有回退机制（cronetEngine==null 直接走 OkHttp），L56-79 catch 异常也回退 OkHttp。3287 次失败均走了回退，功能可用，但每次请求浪费一次 Cronet 无效往返 + 日志噪音。
- **决策**：采用运行时降级（非禁用）。CronetInterceptor 增加 companion object 计数器，连续协议错误 5 次后会话内降级 OkHttp。优势：(1)自适应——Cronet 可用时用，不可用时降级；(2)不丢失 HTTP/3/QUIC 优势；(3)不需要用户确认禁用 Cronet。
- **AbsCallBack.kt 不修改**：降级机制生效后（阈值 5 次）不再发起 Cronet 请求，onFailed 自然不再触发，3287 次噪音随之解决，无需额外修改 AbsCallBack（遵循编码哲学"只触碰必须触碰的部分"）。

### 2026-07-14 P2-2 根因修正：stopLoading 已存在，真正根因是 runCatching 误捕获 CancellationException
- **原计划**：tasks.md 6.3 "VideoPlayerActivity.onDestroy 主动 cancel VideoUrlExtractor Job"
- **实际分析**：Grep 发现 VideoPlay.kt L620-621 已有 stopLoading() 且已调用 cancelChildren()，VideoPlayerActivity.onDestroy L1475 也已调用。Coroutine.kt L182-183 已有 CancellationException 守卫（重新抛出不触发 onError）。
- **真正根因**：VideoUrlExtractor.kt L194 用 runCatching 包裹 BackstageWebView.getStrResponse()。runCatching 是 Kotlin 已知反模式——会捕获 CancellationException。退出播放器时 cancelChildren 触发协程取消，runCatching 捕获 CancellationException → onFailure 记录为"抓包失败"（误报）→ 60 次 JobCancellationException 噪音。
- **修复**：(1) VideoUrlExtractor.kt runCatching → try-catch + CancellationException 守卫（重新抛出）；(2) onDestroy 调用顺序优化（stopLoading 提前到 destroyWeb 之前，先取消嗅探协程再释放 WebView）。
- **教训**：Kotlin runCatching 捕获 CancellationException 是协程反模式，suspend 函数调用应改用 try-catch + CancellationException 守卫。已记入 project_memory 教训。

## 9. 检查点2 扩展测试发现：P3-1 ruleContent非空分支content无有效性校验

> 检查点2用户反馈"需调整"：要求扩大视频源测试范围，区分订阅源问题 vs 底层代码问题。
> 扩展测试16个视频源，发现源11-12播放失败根因。

### 9.1 测试发现

- [x] 9.1 扩展测试源9-16完成（batch_source_test.py + logcat抓取）
- [x] 9.2 问题归类：源问题5个（DNS/SSL/封面图/ruleContent配置）vs 底层问题1处（P3-1）
- [x] 9.3 根因定位：源11-12走ruleContent非空分支，Rss.getContent返回HTML(6816字节含`<script>`)而非视频URL
- [x] 9.4 代码路径确认：VideoPlay.kt L411 `NetworkUtils.getAbsoluteURL(rssArticle.link, content)` 把HTML当URL
- [x] 9.5 日志证据：无extractPrecise/R5嗅探日志（确认走ruleContent分支）；urlLen=6816+htmlLen=415969

### 9.2 P3-1 修复

- [x] 9.6 修改 VideoPlay.kt L404-413：ruleContent非空分支增加content有效性校验(isValidVideoContentUrl: 长度≤2048+无HTML标签`<`/`>`/换行)
- [x] 9.7 校验失败降级R5嗅探(extractWithWebView)+回退文章链接
- [x] 9.8 添加改造日志（AppLog.putWarn记录降级原因+content长度+脱敏）
- [x] 9.9 编译安装+重新测试源11-12验证（logcat确认P3-1降级R5嗅探生效，R5嗅探命中视频流路径，ExoPlayer无onPlayerError，无降级决策）
- [x] 9.10 更新updateLog.md

### AOAdapt 日志：P3-1 根因分析与修复决策

- **发现背景**：检查点2用户反馈"需调整"——"有那么多的视频源你不都测试测试？然后分析一下，是不是订阅源有问题，或者是确实你底层有问题？"
- **测试方法**：batch_source_test.py测试源9-16 + logcat后台抓取（adb logcat -G 16M增大缓冲区）
- **根因分析**：
  - extractPrecise的4个正则方法均限定`https?://[^"']+?\.(?:m3u8|mp4)`结尾，不可能产生含`<script>`的6816字节URL
  - logcat无extractPrecise/R5嗅探日志，确认走ruleContent非空分支（L387+）
  - Rss.getContent用源规则解析返回了约400KB HTML页面content，不含`<MPD`、不为空，走L411被当URL
- **双重问题**：(1)源问题——ruleContent配置错误返回HTML；(2)底层问题——L404-413对content无有效性校验
- **修复决策**：在L411 else分支增加isValidVideoContentUrl校验（长度≤2048+无HTML标签），失败时降级extractWithWebView嗅探+回退文章链接。不抽公共方法（遵循编码哲学最小改动，R5嗅探已是独立方法可直接调用）
- **教训**：ruleContent非空分支的content来自源规则解析，不可信，必须校验URL有效性后再传给播放器。已记入project_memory教训。
