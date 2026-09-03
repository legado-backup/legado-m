# 书源视频对标订阅源——需求规格

> 功能名：`video-booksource-align-rss`
> 前置 spec：`video-playlist-continuity`（书源视频跨影片续播：书源视频多集多页 ViewPager+占位页+VideoPlaybackQueue 队列）
> 关联 spec：`video-booksource-multiroute`（书源多线路/多集解析模型，资产保留）
> 用户裁决日期：2026-09-03

## Intent

书源视频的播放行为与订阅源（rssArticles 模式）**完全对齐**：

- **单页播放**：1 页 = 当前影片，ViewPager 恒为单页、禁滑动翻页；
- **列表驱动上滑**：上滑 = 同列表下一个影片（复用 VideoPlaylistHolder 注入列表），不再是"下一集"；
- **集数切换走选择器/详情抽屉**：playBookEpisode 链路已验证可用，仅经选择器与详情抽屉触发。

背景：`video-playlist-continuity` 实施后反复出问题，根因归结为 4 个架构病根：

1. **双采集链漂移**：书源链（startPlayBookChapter→WebBook.getContent→VideoUrlExtractor 三层嗅探）与订阅源链（playRssEpisode）并行各自演进，直链快速路径/header/嗅探逻辑漂移。实锤：直链 m3u8 地址经 ruleContent 请求后产出整段清单文本被当作 URL 播放失败；书源缺 directRouteIdx 优选需补。
2. **双索引失步**：书源模式映射订阅源模型产生 chapterInVolumeIndex（权威）+ rssEpisodeIndex（镜像），syncBookEpisodeMirror 同步点分散；标题三处数据源（composeTitle / VIDEO_SUB_TITLE 事件 / UP_VIDEO_INFO 事件）反复错乱。
3. **书源自建队列脆弱**：占位页 + generation 守卫（loadNextPlaylistVideo 回调 gen 校验恒不匹配被静默丢弃，上滑卡死实锤）。
4. **列表注入入口分散**：搜索 SearchActivity / 发现 classic+modern+suite / 书架 style1+style2 / 分类页 ExploreShowActivity，共 7 处（以 tasks 5.1 清单为准）；另有 `startActivityForBook` 视频分流兜底路径（阅读器/详情链路进入播放器，无上滑=降级，本 spec 显式记录，红队 R1-2）。

**用户裁决原文要点（2026-09-03）**：书源视频不做多集 ViewPager 多页，直接对标订阅源已验证稳定的模型——书源视频=单页播放（1页=当前影片），集数切换只走选择器/详情抽屉，上滑=同列表下一个影片（列表驱动，复用 VideoPlaylistHolder 注入列表），抽公共采集链组件 VideoPlaybackPipeline（书源订阅源共用）；VideoPlaybackQueue 组件保留但书源侧不接入（订阅源多集分页改造后续用）。

目标：**采集链唯一化**根治"直链地址不正确 / 播放信息不匹配 / 上滑卡死"三类反复出现的问题。

## Scope

### In Scope

- 书源视频 ViewPager 单页化（删除多集多页 / 占位页 / generation 队列接入 / 双索引镜像 rssEpisodeIndex）。
- 上滑手势 = 同列表下一影片（单页模式下 Activity 手势拦截驱动，复用 VideoPlaylistHolder 注入列表）。
- 公共采集链组件 VideoPlaybackPipeline：书源 / 订阅源播放采集唯一实现。
- 标题单一权威：displayEpisodeTitle 收敛为唯一标题源。
- 列表注入入口收敛核查（搜索 / 发现 classic+modern+suite / 书架 style1+style2 / 分类页，共 7 处，以 tasks 5.1 清单为准；`startActivityForBook` 视频分流兜底路径为降级入口）。

### Out of Scope

- 订阅源多集分页改造（tasks 2.1–2.6，属 `video-playlist-continuity`，继续有效）。
- VideoPlaybackQueue 组件删除（保留供订阅源后续接入）。
- 书源多线路/多集解析模型（`video-booksource-multiroute` 的映射保留，仅不再驱动 ViewPager 多页）。
- 订阅源行为的任何变化（**零回归红线**）。

## Approach

### Selected Approach

书源视频**单页化 + 列表驱动 + 公共采集链组件**三件套：

1. **单页化**：书源视频进入播放器后 ViewPager 恒为单页，删除占位页与 generation 守卫逻辑；影片切换走换源式全链重建（initSource），无队列回调、无 gen 校验。
2. **列表驱动**：上滑手势由 Activity 层拦截（ViewPager 禁滑时 gesture 处理），驱动 VideoPlaylistHolder neighborOf(+1) 切换到同列表下一影片，复用 `video-playlist-continuity` 已建的列表注入机制（7 入口，`startActivityForBook` 兜底路径除外）。
3. **采集链唯一化**：抽取 VideoPlaybackPipeline 公共组件，承载"直链判定→正文/规则解析→MPD 落盘→三层嗅探→header 合并→AnalyzeUrl→setUp"完整链，书源 `startPlay` 书源分支 / `startPlayBookChapter` 与订阅源 `playRssEpisode` 三入口均委托之，三处不再各自实现。

**理由**：订阅源 rssArticles 模式的"单页 + 列表滑动 + 选择器"已在真机验证稳定，书源对齐即复用已验证路径；组件抽取让直链 / 嗅探 / header 逻辑单处实现，从结构上消除双链漂移的可能性。

### Alternatives Considered

| 方案 | 否决理由 |
|---|---|
| 继续修补两套采集链（维持现状） | 反复出问题的根因就是双链漂移，每轮补丁只点状修复不治本（本轮 L0 快速路径 / directRouteIdx 都是漂移补丁） |
| 全面统一队列（订阅源也接入 VideoPlaybackQueue 多集分页） | 工作量最大且订阅源现状已稳定，回归风险高；队列组件保留接口后续再接入 |
| 书源视频完全下线多线路 | 多线路/多集解析模型（video-booksource-multiroute）是资产，选择器/详情抽屉已验证可用，仅需断开与 ViewPager 多页的耦合 |

### Drawbacks

- 书源视频失去"多集连滑"体验（上滑不再是下一集而是下一影片）。**接受理由**：用户明确裁决"不做多集上滑"，且多集 ViewPager 是本轮全部错乱的来源。
- 单页模式下上滑需要手势拦截层（ViewPager 禁滑时 gesture 处理），新增少量代码。**接受理由**：逻辑远简于队列守卫。

### Prior Art

- 订阅源 rssArticles 模式（单页 + 列表滑动 switchToArticle 链）已真机验证稳定。
- `video-playlist-continuity` 的 VideoPlaylistHolder 注入机制（5 入口）继续复用。

## Requirements

- **REQ-1**: 书源视频进入播放器后 ViewPager 恒为单页（禁滑动翻页），集数/线路切换仅经选择器与详情抽屉。
- **REQ-2**: 单页模式下上滑手势触发"列表下一影片"（VideoPlaylistHolder neighborOf(+1)），下滑触发上一影片（hasPrev），边界提示与订阅源一致（"已到开头"/无下一个时提示）。
- **REQ-3**: 影片切换复用换源式链路（initSource 全链重建，无 generation 校验、无占位页），完成后走**显式激活链**：VIDEO_BOOK_UNIT_SWITCHED 事件处理中 `currentFragment?.deactivatePlayer()` 复位 isActivated（新增 deactivate 重置标记）→ `activatePlayer()` 重新起播 + 定位首集 + 标题同步；CurrentItem 已在 0 时直接走该显式激活链，不依赖 notifyDataSetChanged/onPageSelected（恒单页 + 稳定 ID 下两者不触发重建/回调）。
- **REQ-4**: 新增 VideoPlaybackPipeline 公共组件承载"直链判定→正文/规则解析→MPD 落盘→三层嗅探→header 合并→AnalyzeUrl→setUp"完整链，**三入口**均委托之：书源 `startPlay` 书源分支（瘦身为"定位章节→委托 Pipeline"）、`startPlayBookChapter`、订阅源 `playRssEpisode`，三处不再各自实现（覆盖冷启动进入与自动连播场景的直链行为）。
- **REQ-5**: 标题单一权威：displayEpisodeTitle 为唯一标题计算点，头部 composeTitle / 左下角 tv_video_title / 详情抽屉全部经它。
- **REQ-6**: 列表注入入口唯一收敛：VideoPlaylistHolder.set 的调用点全仓审计（搜索 / 发现 classic+modern+suite / 书架 style1+style2 / 分类页，共 7 处，以 tasks 5.1 清单为准），漏注入 = 无上滑续播（降级为单页循环播放，不崩溃）；`startActivityForBook` 视频分流兜底路径（阅读器/详情链路）显式标记为降级入口。
- **REQ-7**: 订阅源全场景零变化（回归红线）。
- **REQ-8**: 切换窗口进度短路：switchToBookFromList 发起到新片首帧期间置 `switchingInProgress` 标记（initSource 完成后复位），`saveRead` 与 10s 定时保存（historySaveJob）入口检查该标记短路，防止旧片进度串写新影片落库（红队 R3-1）。
- **REQ-9**: 单集播完自动连播（onAutoCompletion → upDurIndex 末集）：列表存在下一影片时自动接续列表下一影片，与上滑语义一致（红队 R1-1 裁决：行为一致性）；无下一影片时保持"已播放完"提示，不崩溃。

## Scenarios

- **S1**: 书架点击单集影片（直链线路）→ 进入即直链起播，头部/左下角/详情抽屉 = 影片名。
- **S2**: 书架多集剧进入 → 单页播放当前集，选择器选集正常，上滑 = 列表下一影片（非下一集）。
- **S3**: 上滑到列表末尾 → 提示"已到结尾"类信息，界面不卡死。
- **S4**: 直链线路切换（选择器切 hhm3u8）→ L0 快速路径起播，不出现清单文本地址。
- **S5**: 订阅源全场景（文章滑动/多线路多集选择器）回归 → 行为与改造前一致。
- **S6**: 单集播完自动接列表下一影片（红队 R1-1）：末集 onAutoCompletion 后自动 switchToBookFromList(+1)，与上滑行为一致；列表无下一影片时提示"已播放完"不崩溃。
- **S7**: 切换中快速连滑 / 退后台再回前台（红队 R2-5/R3-1/R3-2）：无卡死（switchBookAppending 不卡死、switchBookJob cancel+token 丢弃过期回调）、无进度串写（switchingInProgress 短路 saveRead/定时保存）、无旧片残留播放（显式激活链复位 isActivated 后重启用播新片）。
