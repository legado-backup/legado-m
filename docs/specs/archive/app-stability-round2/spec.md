# Spec: App Stability Round 2 修复

## Intent

10026 版本（07-13 编译）日志反馈"还有好多问题"。该版本已实现零崩溃（R4/R5 修复生效），但残留 3 个 P1 功能异常 + 2 个 P2 体验问题，影响三类核心场景。检查点1 用户反馈再追加 1 个 P1（视频链接自动抓取流程），合计 4 个 P1 + 2 个 P2：

1. **订阅文章列表加载**：部分订阅源文章因 description 字段过大触发 SQLiteBlobTooBigException，列表无法加载（22 次 Row too big 错误）
2. **图片显示**：未加密图片被强制解密触发 IllegalBlockSizeException，图片加载失败（32 次 DATA_NOT_MULTIPLE_OF_BLOCK_LENGTH）
3. **视频播放**：m3u8 等流媒体类型识别失败触发 3003 错误，视频无法播放
4. **视频链接自动抓取**：用户不填内容规则全交给 App 抓取时，正则兜底误匹配非视频页面链接（带 `?url=`/`&playurl=` 参数的分享页/跳转页/广告页），导致不触发更准确的 WebView 嗅探，播放器拿到伪视频链接播放失败

本轮目标：消除上述残留问题，将"还有好多问题"收敛为"零残留"，提升订阅文章/图片/视频三类核心体验。

## Scope

### 纳入范围

| 编号 | 问题 | 修复方向 |
|------|------|---------|
| P1-1 Bug#5 | Room SQLiteBlobTooBigException | flowByOriginSort 查询去掉 description 字段 |
| P1-2 Bug#3 | 图片解密 IllegalBlockSizeException | 图片文件头检测，已知格式跳过解密 |
| P1-3 Bug#4 | ExoPlayer 3003 | createMediaItem 不拼 SPLIT_TAG，改用 setMimeType |
| P1-4 | 视频链接自动抓取正则兜底误匹配阻塞嗅探 | 收紧 isVideoUrl + 拆分 extractPrecise + 流程调整"精确→嗅探→正则兜底" |
| P2-1 | Cronet/DNS 高频失败（3287 次） | 排查 Cronet 初始化，必要时禁用改用 OkHttp |
| P2-2 | 协程取消异常（60 次） | onDestroy 主动 cancel Job，嗅探超时缩短 |

### 不做范围（已修复不动）

- WebView shouldInterceptRequest 线程（R5 修复，78 次抓包命中证据，0 崩溃）
- VideoPlayService 前台服务超时（未复发）
- MaterialCardView 主题崩溃（未复发）
- 视频手势交互（正常）
- ExoPlayer file:// 协议（DefaultDataSource 包装修复）

### 不做范围（源站问题不处理）

- 源站 403/404/520 等网络错误
- 源站内容失效

## Approach

### Selected Approach

#### P1-1 Bug#5 Room SQLiteBlobTooBigException

**选定方案**：flowByOriginSort 查询去掉 description 字段。

**核实依据**：读取 `RssArticlesAdapter.kt`（L54-97）确认，列表界面 convert 方法仅使用 title/pubDate/image/read/origin 字段，**完全不使用 description 字段**。原 DAO 注释"列表使用 description"为错误信息。

**理由**：
- 根因：description 字段含大段 HTML/base64，单行超 CursorWindow 2MB 限制
- 列表界面已确认不使用 description，去掉该字段零功能损失
- 详情页通过 `get(origin, link, sort)` 查询获取完整字段，不受影响
- 相比 substr 截断，去掉字段更彻底，无残留风险

#### P1-2 Bug#3 图片解密 IllegalBlockSizeException

**选定方案**：加图片文件头检测，已知格式跳过解密。

**理由**：
- 根因：decode(ByteArray) 块校验有漏洞（块对齐≠已加密），decode(InputStream) 完全无校验
- 文件头检测准确率高：PNG/JPG/GIF/WebP 标准头前 4 字节固定，加密密文不匹配标准头
- 两个 decode 方法都加，覆盖全面

#### P1-3 Bug#4 ExoPlayer 3003

**选定方案**：createMediaItem 不拼 SPLIT_TAG 到 uri，改用 setMimeType 显式声明类型 + setDefaultHeaders 注入 headers。

**理由**：
- 根因：SPLIT_TAG 拼接到 MediaItem.uri 破坏 DefaultMediaSourceFactory 后缀类型检测
- setMimeType 显式声明优先级高于后缀检测，彻底规避问题
- setDefaultHeaders（R5 已实现 L150-152）负责 headers 注入，无需 SPLIT_TAG 中转
- 保留 ResolvingDataSource 兼容旧调用，主路径走新方案

#### P1-4 视频链接自动抓取流程优化（正则优先级后移）

**选定方案**：收紧 `isVideoUrl` 过滤条件 + 拆分 `extractPrecise` + 调整 VideoPlay 流程为"精确→嗅探→正则兜底"。

**核实依据**：读取 `VideoUrlExtractor.kt`（L291-313）和 `VideoPlay.kt`（L265-337）确认：
- `isVideoUrl`（L307-313）过滤太宽松，包含 `?url=`/`&url=`/`?playurl=`/`&playurl=` 条件，把任意带 url 参数的非视频页面链接（分享页/跳转页/广告）当视频链接
- `extractByRegex`（L291-300）通过 `isVideoUrl` 过滤，抓到这些伪视频链接后 `extract` 返回非空
- VideoPlay `extract` 命中（size≥1）→ 直接播放，不再触发更准确的 `extractWithWebView` 嗅探 → 播放器拿到非视频链接播放失败

**理由**：
- 用户反馈"用户不填写内容规则全部交给你去抓取时，正则抓出来的都是非视频链接，正则可以往后放一放"
- 收紧 `isVideoUrl`：去掉 `?url=`/`&url=`/`?playurl=`/`&playurl=` 过宽条件，只保留真实视频流特征（`.m3u8`/`.mp4`/`format=m3u8`/`type=m3u8`）。播放器页面 URL 由 `extractPlayerPageUrl` 在精确方法结果中解析（已有逻辑）
- `extract` 拆分：新增 `extractPrecise`（标签/Meta/JSON/JS变量，高可信度），`extractByRegex` 正则兜底独立
- 流程调整后正则兜底不再阻塞嗅探：精确未命中→嗅探→嗅探失败→正则兜底（兜底的兜底）

### Alternatives Considered

#### P1-1 Bug#5 备选方案

| 方案 | 描述 | 否决理由 |
|------|------|---------|
| A. substr 截断 description | SQL `substr(description,1,N)` 限制返回长度 | 治标不治本，N 难定；且列表不用 description，截断仍浪费 IO |
| B. 入库时截断 description | 写入数据库时截断 description | 破坏数据完整性，详情页无法获取完整内容 |
| C. 加大 CursorWindow | 设置 cursorWindow 字节数 | Room 不可配置 CursorWindow 大小，需改框架层，风险高 |

#### P1-2 Bug#3 备选方案

| 方案 | 描述 | 否决理由 |
|------|------|---------|
| A. 仅补 decode(InputStream) 块校验 | 只加 bytes.size % 8 校验 | 块校验有漏洞，未加密图片碰巧块对齐仍失败 |
| B. try-catch 吞异常 | 解密失败返回原 bytes | 已有 runCatching，但日志污染严重（32 次错误），需从源头规避 |
| C. 移除 RssSource 图片解密配置 | 不对 RssSource 图片解密 | 破坏正常加密图片源功能 |

#### P1-3 Bug#4 备选方案

| 方案 | 描述 | 否决理由 |
|------|------|---------|
| A. 保留 SPLIT_TAG，ResolvingDataSource 提前 resolve | 在 ResolvingDataSource resolve 时改写 uri | 类型检测在 ResolvingDataSource 之前的 DefaultMediaSourceFactory 层，太晚 |
| B. 完全移除 SPLIT_TAG 机制和 ResolvingDataSource | createMediaItem 只设 uri，headers 全走 setDefaultHeaders | 旧调用方兼容性风险，需保留 ResolvingDataSource 兜底 |
| C. 自定义 MediaSourceFactory | 绕过 DefaultMediaSourceFactory 自己判断类型 | 改动大，维护成本高 |

#### P1-4 备选方案

| 方案 | 描述 | 否决理由 |
|------|------|---------|
| A. 仅收紧 isVideoUrl 不调流程 | 只去掉 `?url=`/`&url=`/`?playurl=`/`&playurl=` 过宽条件 | 治标，正则兜底仍可能误匹配其他模式阻塞嗅探 |
| B. 直接先嗅探再静态解析 | extractWithWebView 嗅探优先 | 嗅探 3-15s 太慢影响首屏体验 |
| C. 完全移除正则兜底 | 删除 extractByRegex | 丢失兜底能力，部分仅靠正则的页面失效 |

### Drawbacks

| 方案 | 已知缺点 | 接受理由 |
|------|---------|---------|
| P1-1 去掉 description | flowByOriginSort 返回的 RssArticle 对象 description 字段为默认值（空） | 列表不用，详情页单独查 |
| P1-2 文件头检测 | 非标准头图片格式（如 AVIF/HEIF）无法识别 | 当前书源生态以 PNG/JPG/GIF/WebP 为主，可接受；后续可扩展 |
| P1-3 setMimeType | 需维护 url 后缀→MIME 映射表 | 映射表小（m3u8/mpd/mp4），维护成本低 |
| P1-4 extractPrecise 未命中必走嗅探（3-15s） | 首屏略慢于正则直接命中 | 准确性大幅提升；嗅探失败仍有正则兜底 |
| P2-1 禁用 Cronet | 失去 Cronet 性能优势（HTTP/3/QUIC） | 稳定性优先；OkHttp 已满足需求 |
| P2-2 缩短嗅探超时 | 部分慢源站嗅探可能失败 | 8-10s 仍足够；15s 太长导致退出卡顿 |

### Prior Art

参考 `docs/specs/video-playback-issues-round1/` 的 ExoPlayer 修复经验，特别是 E1 教训（SPLIT_TAG 拼接破坏类型检测）和 R5 修复（setDefaultHeaders 注入）。

## Requirements

### 功能性需求

- **R1.1** flowByOriginSort 查询不返回 description 字段，列表加载不再触发 SQLiteBlobTooBigException
- **R1.2** RssArticlesAdapter 列表显示不受影响（title/pubDate/image 正常）
- **R1.3** 订阅文章详情页通过 get(origin, link, sort) 仍能获取完整 description 内容
- **R2.1** decode(ByteArray) 增加图片文件头检测，已知格式（PNG/JPG/GIF/WebP）跳过解密
- **R2.2** decode(InputStream) 增加图片文件头检测，已知格式跳过解密
- **R2.3** 未加密图片不再触发 IllegalBlockSizeException
- **R2.4** 正常加密图片仍能正确解密显示
- **R3.1** createMediaItem 不再将 SPLIT_TAG 拼接到 MediaItem.uri
- **R3.2** createMediaItem 根据 url 后缀显式 setMimeType（.m3u8/.mpd/.mp4 等）
- **R3.3** headers 通过 setDefaultHeaders 注入（若调用方未预设则在 createMediaItem 内预设）
- **R3.4** m3u8/mpd 流媒体视频能正常播放，不再触发 3003
- **R3.5** 保留 ResolvingDataSource 兼容旧调用路径
- **R6.1** extractPrecise 命中（标签/Meta/JSON/JS变量）时优先播放，不触发 WebView 嗅探（保证首屏快）
- **R6.2** extractPrecise 未命中时触发 extractWithWebView 嗅探（动态抓包最准确）
- **R6.3** 嗅探失败时回退 extractByRegex 正则兜底（兜底的兜底），正则兜底不再阻塞嗅探
- **R6.4** 收紧 isVideoUrl：去掉 `?url=`/`&url=`/`?playurl=`/`&playurl=` 过宽条件，只保留真实视频流特征（.m3u8/.mp4/format=m3u8/type=m3u8）
- **R6.5** 用户不填内容规则全交给 App 抓取时，自动抓取到真实视频流链接（非带 url 参数的非视频页面链接）
- **R4.1** 排查 Cronet 初始化逻辑，定位 protocol=unknown httpCode=-1 根因
- **R4.2** 若 Cronet 不稳定，禁用 Cronet 改用 OkHttp（需用户确认）
- **R5.1** VideoPlayerActivity.onDestroy 主动 cancel VideoUrlExtractor Job
- **R5.2** 嗅探超时从 15s 缩短为 8-10s

## Scenarios

### 场景1：订阅文章列表加载

**前置**：某订阅源文章 description 含大段 HTML（>2MB）

**步骤**：
1. 用户进入订阅源文章列表
2. flowByOriginSort 查询执行
3. 查询不返回 description 字段，单行数据 < 2MB
4. 列表正常加载，显示 title/pubDate/image

**预期**：不再触发 SQLiteBlobTooBigException，列表流畅加载

### 场景2：图片显示（未加密）

**前置**：RssSource 配置了图片解密规则，但 logo.png 等图片实际未加密

**步骤**：
1. Glide 加载 logo.png
2. ImageUtils.decode 被调用
3. 读取前 4 字节检测文件头，匹配 PNG（89 50 4E 47）
4. 跳过解密，返回原 bytes
5. Glide 正常显示图片

**预期**：不再触发 IllegalBlockSizeException，图片正常显示

### 场景3：图片显示（加密）

**前置**：BookSource 配置了图片解密规则，封面图实际已加密

**步骤**：
1. Glide 加载封面图
2. ImageUtils.decode 被调用
3. 读取前 4 字节检测文件头，不匹配标准图片格式
4. 进入解密路径，evalJS 执行解密规则
5. 解密成功，返回解密后 bytes
6. Glide 显示解密后图片

**预期**：加密图片正常解密显示

### 场景4：视频播放 m3u8

**前置**：视频源为 m3u8 流媒体，需带 headers 请求

**步骤**：
1. 用户点击播放视频
2. createMediaItem 被调用，url 后缀 .m3u8
3. setMimeType(APPLICATION_M3U8) 显式声明类型
4. 不拼接 SPLIT_TAG，uri 保持纯净
5. setDefaultHeaders 注入 headers
6. DefaultMediaSourceFactory 根据 MIME 类型创建 HlsMediaSource
7. 视频正常播放

**预期**：不再触发 3003 UnrecognizedInputFormatException，m3u8 正常播放

### 场景5：用户不填规则时自动抓取视频链接

**前置**：订阅源 type=2（视频），ruleContent 为空（用户全交给 App 抓取），文章页面带 `?url=`/`&playurl=` 等参数的非视频页面链接（分享页/跳转页/广告）

**步骤**：
1. 用户点击播放视频
2. VideoPlay.kt 调用 `extractPrecise`（标签/Meta/JSON/JS变量）静态解析
3. extractPrecise 未命中真实视频流
4. 调用 `extractWithWebView` 嗅探（动态抓包 3-15s）
5. 嗅探成功 → 拿到真实 m3u8/mp4 视频流链接
6. 嗅探失败 → 回退 `extractByRegex` 正则兜底（兜底的兜底）
7. 正则兜底也失败 → 回退文章链接交给 ExoPlayer

**预期**：
- 收紧后的 `isVideoUrl` 不再把带 `?url=`/`&playurl=` 的非视频页面链接当视频链接
- extractPrecise 未命中时优先触发嗅探（不再被正则兜底误匹配阻塞）
- 自动抓取到真实视频流链接，播放器正常播放，不再播放伪视频链接失败

**反例（修复前）**：
- extract 命中 `?url=xxx` 类伪视频链接（size≥1）→ 直接播放 → 不触发嗅探 → 播放器拿到非视频链接播放失败
