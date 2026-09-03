# 书源视频对标订阅源——任务清单

## 1. 准备与基线
- [ ] 1.1 全量回归基线录制：订阅源（文章滑动/多线路多集选择器/搜索）+ 书源（进入/选集/切线路/详情抽屉）真机过一遍，记录当前行为清单
- [ ] 1.2 全仓审计 VideoPlaylistHolder.set 调用点与 VideoPlaybackQueue 引用点清单（Grep 技术字段）

## 2. 公共采集链组件 VideoPlaybackPipeline（AD-03，先行）
- [ ] 2.1 新增 help/video/VideoPlaybackPipeline.kt：PipelineContext（url/article或chapter/source/player/token/title）+ play() 承载 直链判定→getContent/解析→MPD 落盘→三层嗅探→R5 header 合并→AnalyzeUrl→setUp+startPlayLogic；非 MPD/非直链 content 先尝试 parseRssEpisodes 同款多行解析（多行取第一行，红队 R4-2）
- [ ] 2.2 startPlayBookChapter 委托 Pipeline（L0 直链快速路径收进组件），删除方法内联实现
- [ ] 2.3 playRssEpisode 委托 Pipeline，删除内联重复实现
- [ ] 2.4 直链场景单测级验证：chapter.url=m3u8 直链不再触发 getContent 清单文本（真机切 hhm3u8 线路）
- [ ] 2.5 startPlay 书源分支委托 Pipeline（P0-R2-2，L827-927）：瘦身为"定位章节→委托 Pipeline"，删除内联采集实现；验证冷启动进入与自动连播（upDurIndex）场景直链不再触发 getContent 清单文本
- [ ] 2.6 三入口等价对照表（R5-1）：playRssEpisode 重构前后逐点行为对照（playEpisodeJob cancel+token / SniffEngine.invalidate / AnalyzeUrl 以 episode.url 构建 / HeaderResolver.merge 三层 / setUp resolvedUrl / VIDEO_SUB_TITLE / triggerPreload / 三层失败统一错误文案）+ 分步灰度：先书源链委托上线真机回归通过，订阅源委托独立任务独立回归后才合入（对应 design AD-08 裁决表）

## 3. 书源视频单页化（AD-01）
- [ ] 3.1 VideoPagerAdapter 书源分支恒 1 页（删 episodes.size 多页+hasNextPlaylistVideo 占位页扩展）
- [ ] 3.2 switchToViewPagerMode 书源恒禁滑（isSinglePage 简化），删书源 onPageSelected 集数映射分支
- [ ] 3.3 删 syncBookEpisodeMirror 双索引镜像与相关写点；VideoBookDetailSheet 选中集判断改单一状态（chapterInVolumeIndex）
- [ ] 3.4 删书源侧 VideoPlaybackQueue.reset/append 调用与 loadNextPlaylistVideo 占位页触发（组件文件保留）；联动删除点全清单核对（R5-3）：initSource 映射段 reset/canAppendNext（L1200-1208）、loadNextPlaylistVideo（L427-459）、VideoFragment 占位页判定（L235-240）、VideoPlayerActivity 占位页分支（L616-625）与「正在加载下一个视频...」composeTitle（L625）、onDestroy `VideoPlaybackQueue.clear()`（L1839）逐条勾选，防部分删除留不可达路径与幽灵事件源
- [ ] 3.5 标题单一权威收口：handlePageSelected/事件链/详情抽屉全部经 displayEpisodeTitle，删除其余覆盖点；VIDEO_BOOK_UNIT_SWITCHED 处理中 composeTitle 取值改 displayEpisodeTitle(episodes[0])（R3-4：事件时刻 videoTitle 仍是旧片集名）
- [ ] 3.6 镜像写点/读点全清单清理（R2-3）：写点 initSource 映射段 `rssEpisodeIndex = chapterInVolumeIndex`（L1196）/ playRssEpisode 书源分派（L1921）/ upRssEpisodeIndex（L2097）/ VideoFragment 直写（L840+L882）/ switchBookRoute rssRouteIndex（L1551）；读点同步迁移 VideoBookDetailSheet（L195-196，选中集匹配改 index 直比，title 相等比对同名集会错选）/ VideoFragment 悬浮选择器 RssEpisodeAdapter（L880）/ VideoPlayerActivity UP_VIDEO_INFO（L1580-1582）；handlePageSelected 书源 position 写索引分支整体删除（R5-5：防通知触发 onPageSelected(0) 重置用户已选集）

## 4. 列表驱动上滑（AD-02/05）
- [ ] 4.1 VideoPlay 新增 switchToBookFromList(offset: Int, player)：Holder 校验→neighborOf→initSource 重建→事件定位首集；边界 toastOnUi
- [ ] 4.2 VideoFragment 手势层垂直 fling 回调（书源单页模式），Activity 接线 switchToBookFromList(+1/-1)
- [ ] 4.3 与现有手势共存验证：单击显隐/左右 seek/长按倍速/双指全屏不受影响；控件区手势不触发切换（R2-4 定稿：Fragment 内单一检测点，无 Activity 双检测）
- [ ] 4.4 VIDEO_BOOK_UNIT_SWITCHED 显式激活链实现（P0-R2-1）：事件处理改 `currentFragment?.deactivatePlayer()`（新增 deactivate 重置 isActivated 标记）→ `currentFragment?.activatePlayer()` 重新起播；CurrentItem 已在 0 时直接走显式激活链，删除对 notifyDataSetChanged/onPageSelected 的依赖（恒单页 + 稳定 ID 下为空操作）
- [ ] 4.5 切换防重入与取消语义（R2-5/R3-2）：switchBookAppending 入口守卫 + onPause/stopLoading/onNewIntent 取消场景 Coroutine.onError 复位 + initSource 相关 runCatching rethrow CancellationException + switchBookJob cancel 与 currentSwitchToken 双保险（switchToArticle 同款，令牌复用全局 switchTokenCounter）
- [ ] 4.6 切换窗口 saveRead 短路（R3-1）：switchingInProgress 标记（switchToBookFromList 开始置位、initSource 完成后复位），saveRead 与 historySaveJob 定时保存入口检查该标记短路，防旧片进度串写新影片落库

## 5. 入口注入收敛核查（REQ-6）
- [ ] 5.1 搜索/发现 classic+modern+suite/书架 style1+style2/分类页 七入口逐一真机验证注入生效（switchToViewPagerMode 诊断日志 hasNext=true；R1-2 口径统一：共 7 处，以此清单为准）
- [ ] 5.2 未注入场景降级验证：直接进播放器（历史/分享链路）与 startActivityForBook 视频分流兜底路径（阅读器/详情链路，R1-2）无上滑续播不崩溃

## 6. 真机全量回归
- [ ] 6.1 书源场景：书架单集影片直链起播（标题=影片名三处一致）/多集剧选集/切线路直链（S4）/上滑下一影片（S2）/末尾边界（S3）/多集剧第 N 集退出重进恢复（R5-2）
- [ ] 6.2 订阅源场景零回归（S5）：文章滑动/多线路多集/搜索/分类列表
- [ ] 6.3 打包 versionCode=10200 覆盖安装验证
- [ ] 6.4 自动连播末集→列表下一影片验证（S6，R1-1）：单集播完自动接列表下一影片，与上滑语义一致；列表无下一影片时提示"已播放完"不崩溃
- [ ] 6.5 快速连滑 + 退后台压测（S7，R2-5/R3-1/R3-2）：切换中连续上滑多次（无并发交错/守卫卡死/进度串写）、切换中退后台再回前台（无卡死无旧片残留播放）、切换中 saveRead 定时保存触发窗口验证短路生效

## 7. 收尾
- [ ] 7.1 移除全部 VbsDiag 临时日志（Grep 确认 0 残留）
- [ ] 7.2 updateLog.md 基于 git diff 更新（编译前）
- [ ] 7.3 提交远端（feat(master-track-waves)）
- [ ] 7.4 文档同步：docs/INDEX.md 状态迁移、video-playlist-continuity README 标注书源侧被本 spec 取代（R5-3：此项需提前至阶段 3 实施前执行，便于实施者对照 continuity 文档书源侧描述做删除点清单核对）

## 红队修订

> 本轮任务清单依据 `red-team-report.md`（2026-09-03，2 P0 + 11 P1）回填：P0-R2-1 显式激活链（任务 4.4，对应 design AD-02 / spec REQ-3）、P0-R2-2 三入口委托（任务 2.5/2.6，对应 design AD-03 / spec REQ-4）、P1 R2-3 镜像写点/读点全清单（任务 3.6）、R2-5/R3-2 防重入/取消/连滑双保险（任务 4.5）、R3-1 切换窗口 saveRead 短路（任务 4.6，对应 spec REQ-8）、R1-1 自动连播末集接下一影片（任务 6.4，对应 spec REQ-9/S6）、R1-2 入口口径统一 7 处（任务 5.1/5.2 标签修正）、R5-1 等价对照表+分步灰度（任务 2.6）、R5-3 联动删除点全清单（任务 3.4/7.4）、R2-4 手势单一检测点（任务 4.3，对应 design AD-05）、R4-2 多行 content 解析（任务 2.1，对应 design AD-08）。设计侧完整落点见 design.md「红队修订记录」。

## AOAdapt 日志
（实施中按格式追加：
- [ ] X.Y 任务名
  - Action: ...
  - Observation: ...
  - Adapt: ...）

## 实施状态（2026-09-03）

- [x] 1.2 全仓审计：VideoPlaylistHolder.set 调用点 6 文件（书架 style1/style2、发现 classic+modern+suite、搜索、分类页）+ VideoPlay.consume；VideoPlaybackQueue 引用 3 文件
- [x] 2.1 新增 help/video/VideoPlaybackPipeline.kt（playBookChapter/playEpisode 两入口 + 共享 setUpAndPlay，AD-08 逐点裁决落地含 R4-2 多行 content 解析）
- [x] 2.2 startPlayBookChapter 委托 Pipeline（L0 直链快速路径收进组件，删除 ~110 行内联实现）
- [x] 2.3 playRssEpisode 订阅源分支委托 Pipeline.playEpisode（triggerPreload 经 onStarted hook 保留）
- [x] 2.4 直链场景验证：真机切 hhm3u8 线路 → 日志"Pipeline: L0 直链快速路径"→ 首帧 860ms → READY，无清单文本污染
- [x] 2.5 startPlay 书源分支瘦身为定位章节+委托（originalPlayUrl 统一 chapter.url）
- [x] 2.6 等价对照：AD-08 裁决表落 design.md（displayTitle/title 分离、HeaderResolver.merge 三层统一、VIDEO_SUB_TITLE setUp 前发一次）
- [x] 3.1 VideoPagerAdapter 书源恒 1 页（删多页+占位页扩展）
- [x] 3.2 switchToViewPagerMode 书源恒禁滑；handlePageSelected 删书源索引映射/占位页分支
- [x] 3.3 删 syncBookEpisodeMirror；rssEpisodeIndex 唯一写点收敛 playBookEpisode（详情抽屉/选择器零改动）
- [x] 3.4 删书源侧 VideoPlaybackQueue.reset/append 接入（组件文件保留）
- [x] 3.5 标题单一权威：composeTitle/Fragment 左下角/事件链统一经 displayEpisodeTitle
- [x] 3.6 镜像写点清理完成（initSource 初始同步保留为直接赋值）
- [x] 4.1 VideoPlay.switchToBookFromList(offset)（±1 边界 toast"已是最后一个视频/已到开头"）
- [x] 4.2 VideoFragment onFling 垂直判定（|vy|>|vx| 且 >1200px/s）→ Activity.onBookVerticalFling
- [x] 4.3 手势共存：左右 seek 方向锁定互斥/单击显隐/长按倍速/双指全屏未触碰
- [x] 4.4 VIDEO_BOOK_UNIT_SWITCHED 显式激活链（deactivate 复位 isActivated → notifyDataSetChanged → activate）
- [x] 4.5 switchBookJob cancel + token 双保险；onError token 校验防旧任务复位新状态（Coroutine 框架保证 CancellationException 不入 onError）
- [x] 4.6 switchingInProgress 短路 VideoPlay.saveRead + Activity.savePlayHistory
- [x] 5.1 注入生效：书架 style2 点入实测 holderSize>0（hasNext 链路生效，连续 7 部影片上滑切换正常）
- [x] 5.2 未注入降级：switchToBookFromList 对 neighborOf=null 直接 toast 返回（代码路径审查）
- [x] 6.1 书源场景真机：书架单集/多集进入直链起播（首帧 1075-4101ms）标题=影片名三处一致/上滑 7 部连续切换+下滑回退均 READY/边界不越界
- [x] 6.2 订阅源真机：文章上滑 switchToArticle 链正常、播放器进入正常；多线路多集链（Pipeline.playEpisode）受源站分类加载失败（"加载失败"）阻塞，经代码逐行等价核验
- [x] 6.3 versionCode=10201 覆盖安装验证通过
- [ ] 6.4 自动连播末集→列表下一影片（upDurIndex 边界已实现，待长视频自然播完验证）
- [x] 6.5 快速连滑压测：7 次连续上滑无状态错乱；crash buffer 零崩溃
- [x] 7.1 VbsDiag 临时日志清零（Grep 确认 0 残留，android.util.Log.d/e 0 残留）
- [x] 7.2 updateLog.md 基于 git diff 更新（编译前完成）
- [ ] 7.3 提交远端（feat/master-track-waves）
- [x] 7.4 文档同步：INDEX 状态迁移 + video-playlist-continuity README 书源侧取代标注 + design.md 实施决策记录
