# 真机测试问题修复 - 功能规格

> **创建时间**：2026-07-27 10:00
> **日志证据**：`temp/logs/Downloadslogs(3).(1)..zip`（2026-07-27 真机实测，分析详见 `temp/logs/review2_report.md`）
> **问题清单**：`issues/user/temp/20260727/001/`（高亮×2）+ `002/bug.md`（视频+图片）
> **状态**：设计阶段

---

## §1 核心问题详述

### 1.1 V-P0-1：播放器实例池并发崩溃（5 次 FATAL，100% 可复现）

**现象**：用户感知"两次半框崩溃直接退出播放器"。日志实为 5 次 FATAL（09:15/09:30/09:31/09:38/09:39），pid 全不同=进程死亡，连发崩溃（间隔 65~96s）被用户记为 2 次。

**根因（源码交叉验证确认）**：
- `PlayerInstancePool.kt:54-56` `sharedTrackSelector` 为 app 级 lazy 单例，`:104` `.setTrackSelector(sharedTrackSelector)` 共享给所有池实例
- `TrackSelector.init()` 有 checkState 校验：**一个 TrackSelector 同一时刻只能属于一个存活 Player**
- 崩溃序列 5/5 一致：R5 抓包双命中 → 两个 manager 并发 prepareAsyncInternal → 第一个 acquire hit 取走池实例、第二个 acquire miss 新建 → build 时二次 init → `IllegalStateException`
- 代码注释"ExoPlayer 官方 demo 即 app 级共享"是错误类推（demo 为单实例播放器场景）

**验收标准**：并发 prepare 场景 0 崩溃；池实例各自持有独立 TrackSelector；recycle 时 override 清理逻辑保持有效。

---

### 1.2 I-P0-1：图片详情全量 403（核心功能回归）

**现象**：用户"所有详情图片都无法查看"。日志 09:41:01~09:41:10 站点E 550x550 大图连续 86+ 次 `HttpException 403`（防盗链拒绝；数据层 12/12 成功非空，URL 解析正常）。

**根因方向（源码核验）**：
- V4 加载链的防盗链头注入依赖 `ImagePlay.rssSource?.sourceUrl`（sourceOriginOption）+ `ImagePlay.rssArticles?.getOrNull(item.articleIndex)?.link`（refererOption），见 ImageCanvasAdapter.kt:199-209/403-415
- 任一值为 null → 请求无任何防盗链头 → 图床 403
- 旧路径（ImagePageAdapter.kt:97-100）由 Activity 构造参数传入 origin/referer，不依赖 ImagePlay 全局状态
- **待实施时核实**：V4 流程 `ImagePlay.rssSource/rssArticles` 的填充时机是否晚于首次 bind（竞态），或 articleIndex 映射错位导致 articleLink 取空

**验收标准**：站点E 场景图片加载成功率 ≥95%；headers 缺失时有 WARN 日志可定位；不再出现全量 403。

---

### 1.3 I-P0-2：图片降级链断裂

**现象**：86 张 403 失败仅 1 张走入降级链；且唯一一次 fallback-3（WebView 即时预热）在 **Glide 工作线程**调用 WebView 方法，异常被吞，预热失效。

**根因**：
- `onWebViewFallback` 回调（ImageGalleryActivity.kt:182-205）从 Glide RequestListener（工作线程）直接触发，内部 `webviewPreheat.loadUrl()` 必须在 UI 线程（项目铁律：WebView 操作必须在 UI 线程）
- 降级触发计数缺失：每张图独立的降级阶段状态未维护，导致大部分失败未触发降级
- 终审 7.1 修复了 Adapter 内 6 条 Glide 路径的销毁守卫，但**漏了回调线程切换**

**验收标准**：加载失败 → 降级1（skipMemory 重试）→ 降级2 → 降级3（WebView 预热，UI 线程）→ 降级4（网页模式）全链逐级触发有日志；每张图独立计数；无异常被吞。

---

### 1.4 V-P1-1：直链后缀未识别 + UNKNOWN 降级链起步错误

**现象**：`.mp4` 直链播放被迫经历 HLS(1/3)→DASH(2/3)→Progressive(3/3) 全链试错，前两次必然失败（日志实证：`unrecoverable error: code=3002(PARSING_MANIFEST_MALFORMED)` → `trying next MediaSource (2/3)/(3/3)`，urlPath=//mp43/{seg}.mp4），用户白白多等 2 次解析失败才进入正确 MediaSource。

**根因（源码+日志交叉验证，推翻初审"R5旁路嗅探"误判）**：
- 前置嗅探链工作正常：09-10 会话 `sniffVideoType: success, contentType=2, mimeType=application/x-mpegURL` 多次实证（初审报告以旧 tag `SniffingMime` 检索得出"0 行=整体旁路"，该 tag 属已被 R4-T8 替换的 `sniffMimeType`，结论不成立）
- 真相①：`ExoPlayerHelper.inferContentTypeByExtension`（:430-438）只识别 `.m3u8/.mpd/.ism` 清单后缀，**不识别 .mp4/.mkv/.webm/.flv 等直链后缀** → Range 请求失败时后缀兜底 miss → UNKNOWN
- 真相②：`Exo2MediaPlayer.buildFallbackTypes`（:193）UNKNOWN 分支固定 `[HLS, DASH, OTHER]`——HLS 优先对直链场景起步即错，两次清单解析失败是必然损耗

**修复方向**：① 后缀表补齐直链后缀 → `C.TYPE_OTHER`；② UNKNOWN 降级链按 URL 后缀特征启发式排序（直链后缀 → Progressive 优先；否则维持 HLS 优先）；③ `createMediaItem` 的 `getMimeType(url)` 结果作为补充提示传入 buildFallbackTypes。

**验收标准**：.mp4 直链首选 ProgressiveMediaSource（日志 `ExoFallback: try contentType=$C.TYPE_OTHER (#1/N)`）；直链场景 MANIFEST_MALFORMED 试错次数归零；m3u8 场景首选 HLS 不回退。

---

### 1.5 V-P1-2：3003 逃逸白名单 → WebView 兜底双触发路径全死

**现象**：09-16 会话 3003 错误弹框 ×3、09-32 会话 ×6（`错误码: 3003 (ERROR_CODE_PARSING_CONTAINER_UNSUPPORTED)` + `UnrecognizedInputFormatException: None of the available extractors ... could read the stream`）；`VIDEO_FALLBACK_WEBVIEW` 自动切换全天 0 次，弹框建议"可尝试 WebView 播放"但机制从未运转。

**根因（源码交叉验证，三层叠加）**：
1. **白名单漏 3003**：`Exo2MediaPlayer.onPlayerError`（:709-712）`isUnrecoverableError` 仅含 3002/3004/decoder 两类，`ERROR_CODE_PARSING_CONTAINER_UNSUPPORTED(3003)` 被注释"3003 未使用，已移除"错误排除——而 `UnrecognizedInputFormatException` 正好映射 3003，是降级链末端最常见的失败码
2. **isParsingError 成死代码**：解析错误判定（:728-730，含 `UnrecognizedInputFormatException` 分支）嵌套在 `if (isUnrecoverableError)` 块内——3003 到达时整块跳过，不计数、不降级、不触发任何兜底，直接落通用错误弹框
3. **耗尽分支不可达**：即使 3002/3004 进入解析错误分支，末端 MediaSource 失败时 `currentFallbackIndex < fallbackTypes.size - 1` 为 false → 不调 `tryNextFallback()` → 其内部"全部耗尽→发 VIDEO_FALLBACK_WEBVIEW"分支（:304-313）永不执行；阈值路径（`unrecoverableFailCount >= 3`）因解析错误优先 return 走降级链，同次播放内计数永远停在 1/3

**修复方向**：① 白名单补 3003；② 末端降级失败（`isParsingError && currentFallbackIndex == size-1`）直接触发 VIDEO_FALLBACK_WEBVIEW，不再依赖计数阈值；③ UI 错误弹框增加"用 WebView 打开"手动入口（自动兜底失效时的用户自救通道）。

**验收标准**：降级链全部失败场景 WebView 兜底自动触发率 100%（日志 `all fallback exhausted` 可统计）；3003 正确计入不可恢复错误并有 `unrecoverable error` 日志；弹框提供手动 WebView 入口。

---

### 1.6 N-P1-1：Cronet 降级乒乓抖动

**现象**：2 分钟内 6 轮降级↔恢复切换（最快 0.018s 即切回），请求在 Cronet/OkHttp 间反复横跳，加重失败。

**根因**：CronetInterceptor.kt:107-111 恢复探测**一次成功即切回**，无迟滞；抖动网络下探测成功是偶发的。

**修复方向**：恢复迟滞——需连续 2~3 次探测成功才切回，或设置最短降级保持时间（如 60s）。

**验收标准**：每 App 会话降级 ≤1 次；无 1 分钟内反复切换。

---

### 1.7 N-P1-2：DohDns 对 IDN 域名 0 成功 + 串行长延迟

**现象**：DohDns 实战 0/249 成功率，avg 244s 串行延迟；熔断 24 次触发但零收益。根因：punycode IDN 域名（xn-- 前缀）公共 DoH 不收录；3 服务器串行各 3s 超时，最坏 9s/次新连接。

**修复方向**（合并审查报告 P0-1）：
1. IDN/punycode 检测：`xn--` 前缀域名直接走系统 DNS，跳过 DoH
2. 查询并行化（或首服务器 1.5s 快速失败），消除串行 9s
3. 负缓存 30s（失败域名短时间内直接走系统 DNS）
4. 成功服务器优先排序（最近一次成功服务器置顶）
5. 缓存键含记录类型

**验收标准**：IDN 域名解析 <500ms；非 IDN 域名 DoH 成功率 >0 且失败时快速兜底；无 9s 级阻塞。

---

### 1.8 I-P1-1/I-P1-2：图片播放器 UX 对齐

**用户原话**："能不能学习一下内置视频播放器，右上角有收藏、三个点，三个点里面有刷新、配置、浏览器打开（原始详情页）、日志呢？并且现在整个列表，有没有一个底图，也不知道到底现在这个详情图片播放器，几张图，具体哪些加载了，能不能用一个初始图片占位后，然后去每个加载替换占位底图呢？"

**需求拆解**：
1. 工具栏：右上角收藏按钮 + 三点菜单（刷新 / 配置 / 浏览器打开原始详情页 / 查看日志），对齐 VideoPlayerActivity 的菜单结构
2. 占位底图：每张图加载前显示统一占位底图，加载完成替换；失败显示错误占位+重试
3. 进度可见：显示"第 X/共 Y 张"及加载状态指示

**验收标准**：菜单功能全部可用；占位→替换过程无闪烁；进度指示实时准确。

---

### 1.9 R-P1：阅读高亮系统（issues 001）——已拆出独立 spec

> 按用户 [2026-07-27 10:46] 决策：高亮规则问题从主 spec 拆出，独立成 `docs/specs/highlight-rule-fix-20260727/` 四文档（并行分析先行，待视频+图片优化完成后实施）。本 spec 不再跟踪该问题，验收以独立 spec 为准。

---

### 1.10 P2 收尾项

| 编号 | 问题 | 验收标准 |
|------|------|---------|
| N-P2-1 | AnalyzeUrl.kt:448 附近完整 URL 明文日志 + VideoSubTitle 事件源标题明文（198 行） | 全部走 sanitizeUrl/脱敏，appLog 无明文域名与源标题 |
| N-P2-2 | RedirectCache 命中不更新 Referer + LRU 并发 | 跨域名命中修正 Referer；淘汰加锁 |
| I-P2-1 | 图片渐进式加载缺失 | 大图先模糊后清晰（thumbnail 0.1f） |
| T-P2 | ai_test 自动化验证脚本 | 可统计播放成功率/首帧命中/图片加载成功率 |

---

## §2 非目标（Out of Scope）

- 不重构 R5 嗅探架构本身（已验证有效）
- 不改动阅读排版引擎除高亮叠加外的其他逻辑
- 不引入新的播放内核（保持 media3 ExoPlayer + GSY 封装）
- 书源/订阅源规则侧问题（JS header 规则 EcmaError 属源侧健壮性，App 已兜底，不在本期）
