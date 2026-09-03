# 红队审查报告——video-booksource-align-rss（五轮递进对抗审查）

> 审查日期：2026-09-03 ｜ 审查对象：README.md / spec.md / design.md / tasks.md
> 方法：每个问题均对照源码实测行号核验（Read 实读，非推理）。行号以当前工作区为准。
> 级别：P0=阻塞实施必须改设计 ｜ P1=实施前必须澄清 ｜ P2=可实施后优化

## 结论总览

| 轮次 | P0 | P1 | P2 | 小计 |
|---|---|---|---|---|
| R1 需求完备性 | 0 | 2 | 3 | 5 |
| R2 可行性 | 2 | 4 | 1 | 7 |
| R3 可靠性/稳定性 | 0 | 2 | 3 | 5 |
| R4 通用性 | 0 | 1 | 3 | 4 |
| R5 回归与迁移 | 0 | 2 | 3 | 5 |
| **合计** | **2** | **11** | **13** | **26** |

---

## R1 需求完备性攻击（场景遗漏）

### R1-1 [P1] 单集播完的自动连播行为未定义，与"上滑=下一影片"模型割裂
- **证据**：`app/src/main/java/io/legado/app/help/gsyVideo/VideoPlayer.kt` L379-382 `onAutoCompletion()` → `VideoPlay.upDurIndex(1, this)`；`model/VideoPlay.kt` L1306-1320 `upDurIndex`：`chapterInVolumeIndex+1` → `saveRead(0)` → `startPlay(player)`，末集时 L1313-1315 仅 toast「已播放完」并 return，**不查 VideoPlaylistHolder.neighborOf(+1)**。
- **影响**：单页化后自动连播仍在"集"维度自动推进（选择器语义之外的隐性切集），而末集播完即使列表有下一影片也不接续；用户对"上滑=下一影片"与"连播=下一集"两套语义混用的感知未在 spec 中裁决。
- **修复建议**：spec 增加明确裁决条目——①保留集内自动连播（现状）+末集提示；或②末集播完自动接 `switchToBookFromList(+1)`。任选其一写入 REQ-2/S2。

### R1-2 [P1] 入口注入清单数量自相矛盾（5/6/7 三个口径），且不含阅读器-详情路径
- **证据**：spec.md L35「共 5 处」；tasks.md 5.1「六入口」；实际口径（搜索1+发现classic/modern/suite 3+书架style1/2 2+分类页1）= 7 处。另 `utils/ContextExtensions.kt` L66-80 `startActivityForBook`：`book.isVideo -> VideoPlayerActivity`，其调用方含 ReadBookActivity.kt L197 附近等书籍链路入口，不在注入清单内。
- **影响**：REQ-6「全仓审计漏注入=降级」的审计基线口径不一致，实施者按 5 或 6 处核对都会漏点；阅读器/详情入口进入播放器永远无上滑（降级可接受但 spec 未写明该入口的存在）。
- **修复建议**：统一入口清单（含 startActivityForBook 视频分流路径），逐处标注"注入/降级"预期。

### R1-3 [P2] 下载与画中画/悬浮窗对 Pipeline 的时序契约未列明
- **证据**：`ui/video/VideoFragment.kt` L746/L762-767 下载按钮读 `VideoPlay.videoUrl` + `VideoPlay.currentPlayHeaders`（L697 file:// 判定隐藏下载）；`model/VideoPlay.kt` L1091-1094 FloatingPlayer/VideoPlayer `cloneState` 克隆播放态。书源链现状 videoUrl 在 IO 协程中途赋值（L1679、L1690 两次）。
- **影响**：Pipeline 收编后若改变 videoUrl/currentPlayHeaders 赋值时点，下载按钮可能拿到嗅探中间态地址、悬浮窗克隆到旧地址。
- **修复建议**：design PipelineContext 契约中补"videoUrl/currentPlayHeaders 必须 setUp 前单点终态赋值"约束。

### R1-4 [P2] 播放历史键在"入口播放"与"选集播放"两条书源路径不一致
- **证据**：`model/VideoPlay.kt` L318-321 `historyKeyUrl = originalPlayUrl ?: videoUrl`；选集链 `startPlayBookChapter` L1615 同步设 `originalPlayUrl = chapter.url`；而入口链 `startPlay` 书源分支 L879 在 getContent 之后才设 `originalPlayUrl = mUrl`（正文产出链接，≠chapter.url）。
- **影响**：同一影片两条路径产生两个历史键，进度记忆可能失效；列表切换后恢复行为依赖哪条链发起而不一致。设计 AD-04 只管标题，未管该键。
- **修复建议**：Pipeline 统一在采集发起前以"原始链接"（chapter.url/episode.url）单点写 originalPlayUrl。

### R1-5 [P2] switchBookRoute 单页语义兼容但"直链外露收敛进 Pipeline"表述职责错位
- **证据**：`model/VideoPlay.kt` L1544-1565 `switchBookRoute` 重置 `chapterInVolumeIndex=0` 播新线路首集（单页兼容✓）；映射段 L1185-1191 `preferIdx` 直链线路优选属于**路由选择**逻辑，位于 `initSource` L1168-1209 映射段内。
- **影响**：design File Changes 写「删书源映射段 VideoPlaybackQueue.reset 与直链外露逻辑（收敛进 Pipeline）」——线路优选若被搬进"采集链组件"，违反 AD-03 自己定的"组件仅承载采集→起播，不承担换源/选集入口职责"边界。
- **修复建议**：明确 preferIdx 优选留在 initSource 映射段（仅删该段内 Queue.reset/canAppendNext），Pipeline 不含路由优选。

---

## R2 可行性攻击（源码现实 vs 设计假设）

### R2-1 [P0] 恒单页 + 稳定 ID → notifyDataSetChanged 不会重建 Fragment，切影片后旧片继续播
- **证据**：`ui/video/VideoPagerAdapter.kt` L47-52 `getItemId = position.toLong()`（恒定 ID），L55-58 `containsItem` 按 itemCount 校验；单页化后 itemCount 恒 1，切影片前后 ID=0 不变 → `FragmentStateAdapter` 语义下 notifyDataSetChanged **保留原 Fragment 实例**。`ui/video/VideoFragment.kt` L231 `activatePlayer` 首行 `if (isActivated) return` 早退；旧片 Fragment isActivated=true，无任何调用方触发 deactivatePlayer（handlePageSelected 不触发，因 setCurrentItem(0) 时 currentItem 已是 0，onPageSelected 不回调）。`ui/video/VideoPlayerActivity.kt` L686-693 onFragmentViewReady 的"当前页 Fragment 重建兜底"仅在 Fragment 真正重建时触发，而稳定 ID 下不重建。
- **影响**：REQ-3/AD-02 设计的完成链「notifyDataSetChanged + setCurrentItem(0)」在恒单页下是**空操作**：全局状态（book/toc/episodes）已换、画面还是旧片，或黑屏。现占位页流程能工作恰因页数变化+落点页变更触发了 onPageSelected。
- **修复建议**：二选一写入 AD-02/任务 4.1：①switchToBookFromList 完成后显式 `currentFragment?.deactivatePlayer()` + 重新 `activatePlayer()`（startPlay 读新 chapterInVolumeIndex）；②getItemId 绑定影片标识（bookUrl.hashCode）强制重建 + 完成链直呼 `playBookEpisode(player, 0, 首集)`。

### R2-2 [P0] startPlay 书源分支未纳入 Pipeline 委托 → 入口直链 bug 原样残留
- **证据**：`model/VideoPlay.kt` L827-927 `startPlay` 书源分支：L832-846 章节定位后 **L854 直接 `WebBook.getContent`，无 `isDirectVideoStreamUrl` L0 快速路径**；而 `startPlayBookChapter` L1621-1652 有 L0。两者是近乎重复的采集链实现。入口播放（activatePlayer L302 `book != null -> VideoPlay.startPlay`）与自动连播（upDurIndex L1318 → startPlay）都走 startPlay 分支。
- **影响**：spec 实锤问题「直链 m3u8 被 ruleContent 请求产出清单文本」在**冷启动进入与自动连播场景依旧复现**（S4 只修复了选集/切线路链路），"采集链唯一化"目标未达成。
- **修复建议**：startPlay 书源分支同样委托 Pipeline（即书源采集链三处入口：startPlay 书源分支、startPlayBookChapter、playRssEpisode 书源分派，全部单点）；tasks 2.2 增加对应条目。

### R2-3 [P1] "镜像写点全部清理"与保留 rssEpisodeIndex 读点的组件自相矛盾，且清理点清单不全
- **证据**：写点：initSource 映射段 L1196 `rssEpisodeIndex = chapterInVolumeIndex`、`switchBookRoute` L1551（rssRouteIndex）、`playRssEpisode` 书源分派 L1921、`upRssEpisodeIndex` L2097、`VideoFragment.kt` L840/L882 直写。读点：`VideoBookDetailSheet.kt` L195-196（选中集按 rssEpisodes[rssEpisodeIndex]）、`VideoFragment` 悬浮选择器 L880 `RssEpisodeAdapter(episodes, VideoPlay.rssEpisodeIndex)`、`VideoPlayerActivity` UP_VIDEO_INFO L1580-1582。tasks 3.3 仅列 VideoBookDetailSheet 与 syncBookEpisodeMirror。
- **影响**：若只删 syncBookEpisodeMirror 而映射段/其余写点保留，镜像以另一种形式存活，AD-01 目标落空；若全部清理但读点未迁移，详情抽屉/悬浮选择器高亮错位——正是本 spec 要根治的"双索引失步"换壳回归。
- **修复建议**：tasks 3.3 扩为"镜像写点/读点全清单"逐项迁移（上述 5 写点+3 读点），并把 VideoBookDetailSheet 选中判断改按索引比对（现状 L195 按 title 相等比对，同名集会错选）。

### R2-4 [P1] AD-05 手势归属自相矛盾（Fragment 回调 vs Activity GestureDetector），未定义消费协议
- **证据**：design.md AD-05 Decision 同时写「`VideoFragment` 手势检测逻辑保持不变，仅对外暴露垂直 fling 回调」与「由 Activity 层 GestureDetector 的 onFling 判定」；tasks 4.2 写「VideoFragment 手势层垂直 fling 回调，Activity 接线」。源码现实：`VideoFragment.kt` L1360-1376 surface_container 的 OnTouchListener 对非控件区**恒返回 true 消费**，GestureDetector 在 L1048/L1123 喂事件；Activity 只能通过 dispatchTouchEvent 侧录。
- **影响**：两处表述指向不同实现位置，实施时可能出现双检测（Fragment 回调+Activity GestureDetector 各一套）→ 连滑双触发；且未定义"手势落在控件区返回 false 给 GSY"时 fling 是否生效。
- **修复建议**：二选一定稿（推荐：Fragment 内既有 GestureDetector 增加 onFling 判定并回调 Activity，因事件已被 Fragment 层消费，Activity 独立 GestureDetector 收不到 UP 后的完整序列），并写明控件区手势不触发切换。

### R2-5 [P1] switchToBookFromList 防重入/取消语义未设计
- **证据**：现有跨影片链 `loadNextPlaylistVideo`（`model/VideoPlay.kt` L427-459）有 switchBookAppending 防重入 L429-431，复位点在 withContext(Main) L436 与 onError L454；但 `stopLoading` L1103-1105 `loadScope.cancelChildren()`、onNewIntent teardown L375-379 取消任务时，**复位代码不保证执行**（协程取消不触发 onError，CancellationException 不走 kotlin.runCatching 的正常恢复路径——initSource L1146 的 runCatching 会吞取消异常继续走 upEpisodes/映射）。onPause L491-494 只取消 Activity 自己的 initSourceJob，不覆盖 loadScope 子协程。
- **影响**：切换中退出/快速连滑后 switchBookAppending（或新设计的等价守卫）可能永久 true → 上滑永久失效；或取消后的 initSource 半途写状态（book/toc/映射已换、episodes 未就绪）。
- **修复建议**：AD-02 明确：①守卫复位改 finally/try-finally 语义；②switchToBookFromList 持独立 Job 引用 + switchTokenCounter 令牌（对齐 switchToArticle L1749-1753 的 cancel+token 双保险）；③initSource 内 runCatching 需先 rethrow CancellationException。

### R2-6 [P2] 两链 header 合并与 URL 后处理不对称，Pipeline 参数化方案缺失
- **证据**：书源链手工 merge（`model/VideoPlay.kt` L1698-1700 `sniffMergedHeaders.forEach { analyzeUrl.headerMap[k]=v }`）+ L1713 `resolvePlayerPageUrl(playUrl)`；订阅源链 HeaderResolver.merge 三层（L1968-1975，refererFallback=rssArticle.link）+ **无 resolvePlayerPageUrl**（L1984 直接 setUp candidate.url）。另有订阅源专属 `triggerPreload()` L1995、`playEpisodeJob?.cancel()` L1938、书源链 0 处 VIDEO_SUB_TITLE（全文件 grep：该事件仅 L564/599/616/658/686/732/816/1986/2161，书源采集链无）。
- **影响**：Pipeline 用哪套合并实现必须显式决策：统一 HeaderResolver → 书源链行为变化（允许，书源不在零回归红线内）；保留两套 → 组件退化为 if-else 壳。VIDEO_SUB_TITLE 触发差异决定标题刷新时机（书源链靠 saveRead L2161 10s 定时器，切换后标题更新滞后）。
- **修复建议**：design AD-03 补一张"两链逐点差异表"（header 合并/resolvePlayerPageUrl/事件/预载/错误文案），逐项裁决统一后行为。

---

## R3 可靠性/稳定性攻击

### R3-1 [P1] 切换窗口期 saveRead/savePlayHistory 把旧片进度写进新影片
- **证据**：`initSource` L1127-1130 先替换 `book` 并回填 `chapterInVolumeIndex/durVolumeIndex/durChapterPos`（此时旧片仍在播放器里）；`saveRead` L2103-2148 用 `videoManager.currentPosition`（旧片位置）计算 `book.durChapterIndex/durChapterPos` 并 `book.update()` 落库；触发源含 `help/gsyVideo/VideoPlayer.kt` L798-802 `onError -> VideoPlay.saveRead()`、10s 定时器（VideoPlayerActivity L511-516）与 onPause L497。spec 提及 saveRead 短路诉求，但 **tasks.md 无对应任务项**。
- **影响**：列表切换期间任一次定时保存/错误回调都把旧片秒数写进新影片的书进度，新影片从旧片位置起播（错乱且持久化）。
- **修复建议**：tasks 增加任务项：切换会话期（switchToBookFromList 发起到新片首帧）设 @Volatile switching 标志，saveRead/savePlayHistory 入口短路。

### R3-2 [P1] 快速连滑并发无互斥设计
- **证据**：设计 AD-02 仅描述单次 switchToBookFromList 流程；对比同构链 switchToArticle 有 `switchArticleJob?.cancel()` + token 双保险（L1749-1753），playRssEpisode 有 playEpisodeJob cancel + token（L1938-1941）。手势层 GestureDetector onFling 可在数百 ms 内连发。
- **影响**：两次 initSource 并发交错写全局状态（book/toc/映射/episodes），先发的后完成覆盖后发的（回退到上一部影片），token 缺失时无法丢弃过期回调。
- **修复建议**：switchToBookFromList 内置 job cancel + token + 防重入三件套（并入 R2-5 修复）。

### R3-3 [P2] T1.13 快照机制与全局事件的跨实例串扰在列表切换后放大
- **证据**：快照仅 initFromIntent 采集（`VideoPlayerActivity.kt` L445-448/L473-476）；`VIDEO_BOOK_UNIT_SWITCHED` 为全局 observeEvent（L1626-1631，notifyDataSetChanged+setCurrentItem(0)），EventBus 无实例过滤；Activity 为 singleTask（AndroidManifest），但 PiP/悬浮恢复场景存在第二播放会话。
- **影响**：列表切换后其他存活实例的快照字段过期；若存在第二实例同时观察该事件，会对自己的会话误刷新。
- **修复建议**：switchToBookFromList 完成链同步刷新本 Activity 快照字段；事件消费端校验事件归属（或事件载荷带会话标识）。

### R3-4 [P2] VIDEO_BOOK_UNIT_SWITCHED 完成链标题取旧片 videoTitle
- **证据**：`VideoPlayerActivity.kt` L1629 `composeTitle = VideoPlay.videoTitle ?: ""` 在事件处理时执行，而新片 videoTitle 要到新链 startPlayBookChapter L1616（或 saveRead L2146）才更新。
- **影响**：切换完成瞬间头部标题闪现上一影片的集名。
- **修复建议**：task 3.5 标题收口时把该行改为 displayEpisodeTitle(episodes[0]) 或在 initSource 完成前置更新 videoTitle。

### R3-5 [P2] Pipeline 自持 token 与 VideoPlay 全局令牌池的双体系风险
- **证据**：现全局唯一令牌池 `switchTokenCounter/currentSwitchToken`（`model/VideoPlay.kt` L303-306），startPlay 内层 async 注释（L299-302）明确"loadScope 顶层并列子协程需统一 token 校验"。
- **影响**：若 Pipeline 内部另建 token/缓存体系，与全局令牌双轨，迟到回调丢弃判定分裂。
- **修复建议**：PipelineContext 直接复用 VideoPlay.switchTokenCounter 发令牌，Pipeline 不自持计数器。

---

## R4 通用性攻击

### R4-1 [P2] isDirectVideoStreamUrl 存在自相矛盾的死分支与覆盖缺口
- **证据**：`help/video/VideoUrlExtractor.kt` L551-561：先 `substringBefore("?").substringBefore("#")` 剥离 query，再 `contains("format=m3u8")/contains("type=m3u8")`——**这两个标记只可能出现在 query 里，剥离后恒不命中（死代码）**。后缀清单不含 .m4v/.mov/.avi/.3gp/.m3u；无后缀直链、301→m3u8 跳转不命中。兜底末态：书源链 L891 `?: mUrl` 回退把垃圾文本当 URL 交给 ExoPlayer 报错（有错误对话框承接，但非干净提示）。
- **影响**：L0 快速路径对部分真实直链形态漏判，退化走完整嗅探（12s 最坏）；Pipeline 收编后同缺口被"单点固化"。
- **修复建议**：修正判定顺序（先按后缀+query 标记联合判定再剥 query 或两段都查）；嗅探失败且原内容非流时发 VIDEO_PLAY_ERROR 而非回退播放垃圾文本。

### R4-2 [P1] ruleContent 多行 URL（多清晰度/多线路数组）在书源链无解析
- **证据**：`model/VideoPlay.kt` L870-893（startPlay 书源分支）与 L1659-1689（startPlayBookChapter）均把**整段 content** 当 mUrl；多行解析 `parseRssEpisodes`（L1319 起，模式②多行 URL/模式③JSON）只用于订阅源链。design/spec 对书源返回多清晰度场景零提及。
- **影响**：正文返回多行清晰度地址的书源整段文本直接进嗅探/播放，必然失败——与直链清单文本是同一类症状的另一个根因，Pipeline 化也不解决。
- **修复建议**：Pipeline 内对非 MPD/非直链 content 先尝试 parseRssEpisodes 同款解析（复用现有函数），多行时取第一行（或弹清晰度选择），写入 design。

### R4-3 [P2] MPD/加密流（widevine）能力边界未声明
- **证据**：MPD 文本落盘仅书源链实现（L870-875/L1671-1675，MD5 命名 + videoTempFile）；全仓无 DRM/widevine 会话逻辑。
- **影响**：Pipeline 统一时若遗漏 MPD 落盘分支，订阅源 ruleContent 返回 MPD 文本的场景退化；DRM 源预期失败但应给出明确错误而非崩溃。
- **修复建议**：Pipeline 明确保留 MPD 落盘分支；design 声明 DRM 超出范围（错误提示承接）。

### R4-4 [P2] 音频书源（bookSourceType=audio）误伤防护未写
- **证据**：`constant/BookSourceType.kt` audio=1/video=4 分立；书源分派以 `bookSourceType == BookSourceType.video` 判定（`model/VideoPlay.kt` L1918、L1486）；入口 `startActivityForBook` isVideo→VideoPlayerActivity、isAudio→AudioPlayActivity（utils/ContextExtensions.kt L69-71）。
- **影响**：Pipeline 是源类型无关 object，若未来被 audio 链复用会走视频采集；本期内风险低但边界应写明。
- **修复建议**：design 注明 Pipeline 仅由 video 分派点调用，play() 内首行断言 source 类型。

---

## R5 回归与迁移攻击

### R5-1 [P1] "订阅源零回归红线"与 playRssEpisode 委托重构的差异清单/灰度顺序缺失
- **证据**：`model/VideoPlay.kt` L1915-2000 playRssEpisode 可观察行为点：playEpisodeJob cancel+token（L1938-1941）、SniffEngine.invalidate（L1942）、AnalyzeUrl 以 **episode.url**（非 resolvedUrl）构建（L1962-1966）、HeaderResolver.merge 三层（L1968-1975）、setUp resolvedUrl（L1984）、VIDEO_SUB_TITLE（L1986）、triggerPreload（L1995）、三层失败统一错误文案（L1951-1958）。design/tasks 均未列"重构前后逐点等价对照"，也无"先书源侧灰度、订阅源侧后切换"的分步交付顺序。
- **影响**：委托实现时任一点遗漏（尤其 triggerPreload 与错误文案）即违反零回归红线，且无法用任务清单逐点验收。
- **修复建议**：tasks 2.3 拆为逐点对照验收表；交付顺序改为 Pipeline 先只接书源链（tasks 2.2），订阅源委托独立任务+独立真机回归（tasks 6.2）后才合入。

### R5-2 [P2] 存量用户第 N 集进度在单页模式下的恢复路径需显式回归
- **证据**：恢复链 initSource L1128 回填 chapterInVolumeIndex → startPlay L832-846 章节定位，不依赖多页；但 `switchToViewPagerMode` L594-600 的 `setCurrentItem(chapterInVolumeIndex)` 定位块在单页下必须删除（tasks 3.2 未显式列该块）；durChapterIndex 数据结构无变化。
- **影响**：漏删则单页 adapter 上 setCurrentItem(N>0) 行为未定义；删对则无回归。PreferKey/数据库无变化（tasks 6.3 覆盖安装验证兜底）。
- **修复建议**：tasks 3.2 明确删除 L594-600 书源定位块；tasks 6.1 增补"多集剧第 N 集退出重进恢复"用例。

### R5-3 [P1] video-playlist-continuity 订阅源任务依赖的组件契约核验与残留引用清理
- **证据**：`model/VideoPlaybackQueue.kt` UnitProvider L39-44/append L119-128/markReady L132-137 均为订阅源后续接入保留，本 spec 不动组件本体（tasks 3.4 ✓）；但书源侧退出后 initSource 映射段 reset/canAppendNext（L1200-1208）、loadNextPlaylistVideo L427-459、VideoFragment 占位页判定 L235-240、VideoPlayerActivity 占位页分支 L616-625、L625 composeTitle「正在加载下一个视频...」、onDestroy `VideoPlaybackQueue.clear()`（L1839）构成一组联动删除点，tasks 3.1-3.4 未做清单级逐一核对；且 continuity spec 的书源侧描述依赖 tasks 7.4 的标注同步。
- **影响**：部分删除（如删占位页但留 loadNextPlaylistVideo）会留下不可达代码路径与幽灵事件源；文档不同步则后续订阅源接入时按旧描述实施。
- **修复建议**：tasks 增加一项"删除点全清单核对"（按上述文件行号逐条勾选）；7.4 提前到 Phase 3 之前执行以便实施者对照。

### R5-4 [P2] VIDEO_BOOK_UNIT_SWITCHED 保留决策正确但设计引用行号漂移
- **证据**：事件定义 `constant/EventBus.kt` L63、post `model/VideoPlay.kt` L449、observe `VideoPlayerActivity.kt` L1626；design AD-02 写「VIDEO_BOOK_UNIT_SWITCHED 事件（L1608 链路）」行号不符。同理 design 引用 ExploreFragment L3696（实际注入点 L3708 附近）。
- **影响**：行号漂移本身无害，但设计文档行号锚点失准会误导实施与后续审计。
- **修复建议**：design 改用"函数名+当前行号"双锚点或去掉行号。

### R5-5 [P2] 单页化后 upEpisodesView/upRssEpisodesView 分支与 handlePageSelected 书源写索引分支的清理归属
- **证据**：`VideoPlayerActivity.kt` L634-639 书源分支 `chapterInVolumeIndex = position`（单页恒 0）+ `syncBookEpisodeMirror()`（待删）+ `upEpisodesView()`；L641-642 兜底分支写 rssEpisodeIndex。单页化后这些分支的裁剪与 R2-3 的读点迁移联动。
- **影响**：只删镜像不删 position 写索引分支，边界场景（通知触发的 onPageSelected(0)）会把用户刚选的第 N 集重置为 0。
- **修复建议**：handlePageSelected 书源分支单页化后整体删除（保留标题/activatePlayer 部分），tasks 3.2/3.3 合并核对。

---

## P0/P1 汇总（实施前必须处理）

| # | 级别 | 一行摘要 |
|---|---|---|
| R2-1 | P0 | 恒单页+稳定ID 下 notifyDataSetChanged 不重建 Fragment、activatePlayer 早退——设计的切影片完成链是空操作，必须改为显式 deactivate/activate 或重建型 getItemId |
| R2-2 | P0 | startPlay 书源分支无 L0 直链快速路径且未纳入 Pipeline——冷启动/自动连播仍复现"直链当清单文本"，三处采集入口必须全部委托 |
| R2-3 | P1 | 镜像清理点清单不全（5 写点+3 读点），详情抽屉按 title 比对选中会错选 |
| R2-4 | P1 | AD-05 手势归属两种表述矛盾，需定稿单一检测点与控件区消费协议 |
| R2-5 | P1 | switchToBookFromList 缺防重入/取消/finally 复位设计，runCatching 吞 CancellationException |
| R2-6 | P2→升级关注 | 两链 header 合并/resolvePlayerPageUrl/事件/预载逐点差异表缺失（列为 P1 处理：实施前必须裁决） |
| R3-1 | P1 | 切换窗口 saveRead 串写新影片进度，tasks 无对应任务项 |
| R3-2 | P1 | 快速连滑并发需 job cancel+token+防重入三件套 |
| R4-2 | P1 | ruleContent 多行/多清晰度书源正文无解析，需在 Pipeline 定义取舍 |
| R5-1 | P1 | playRssEpisode 委托缺逐点等价对照表与分步灰度顺序 |
| R5-3 | P1 | 书源侧退出联动删除点需清单级核对，continuity 文档标注提前 |
| R1-1 | P1 | 单集播完自动连播语义未裁决（末集是否接列表下一影片） |
| R1-2 | P1 | 注入入口清单 5/6/7 三口径矛盾，缺阅读器-详情路径 |
