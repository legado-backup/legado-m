# 红队对抗审查报告 — video-playlist-continuity

> 审查日期：2026-09-02 ｜ 审查方式：五轮攻击视角 × 全源码渗透验证（非纸面审查）
> 被审文档：spec.md / design.md / tasks.md（本目录）
> 结论先行：**需修订后实施**（P0 阻塞 5 项，见汇总清单；含"书源全回退扁平队列"裁决：应升级）

---

## 轮1【状态机与竞态】攻击结果

### R1-1（P0 阻塞）多集模式下 loadMoreArticles 误触发实锤
- **定位**：[VideoPlayerActivity.kt#L586-L589](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/video/VideoPlayerActivity.kt#L586-L589)
- **事实**：`onPageSelected` 中触发条件为 `!articles.isNullOrEmpty() && position == articles.size - 1`。设计 AD-02 将多集模式分页数据源改为 rssEpisodes（扁平位），但 rssArticles 仍非空（列表上下文保留）。设列表 10 部影片 × 20 集 → flatSize=200，`position == 9`（影片0 集9）即误触发 loadMoreArticles，网络请求与队列 appendNext 双触发，且拉入的下一页文章不进入队列 → itemCount 与 rssArticles.size 失配 → containsItem 防崩溃但位置语义全乱。
- **修正**：队列接管后 loadMoreArticles 触发必须限定"非多集模式（普通文章分支）"；多集模式的列表续拉改由订阅源 Provider 的 appendNext 内部承担（末 Unit 且 rssArticles 用尽时再 loadMoreArticles，取回的新文章进队列而非直接改 itemCount）。

### R1-2（P0 阻塞）换线路后队列 position 校正算法缺失
- **定位**：[VideoPlayerActivity.kt#L644-L647](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/video/VideoPlayerActivity.kt#L644-L647)、[VideoPlay.kt#L1402-L1437](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/model/VideoPlay.kt#L1402-L1437)
- **事实**：现状换线路 = `notifyDataSetChanged() + setCurrentItem(0, false)`（单影片场景安全）。队列化后当前 Unit 集列表整体替换 → flatSize 变化 → 后续所有 Unit 的 unitStart 平移；多单元场景 `setCurrentItem(0)` 会把用户跳回第一个影片首集，属于功能性回退。switchToRoute 异步采集完成后也无任何 ViewPager 位置校正。
- **修正**：design AD-02 必须补充：换线路成功后 `setCurrentItem(unitStart(currentUnitIdx) + newEpIdx, false)`；异步回调持"队列 generation"校验（见 R1-4），过期则不做任何 UI 定位。

### R1-3（P1）初始 Unit 集列表异步就绪竞态
- **定位**：[VideoPlay.kt#L640-L664](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/model/VideoPlay.kt#L640-L664)
- **事实**：rssRoutes/rssEpisodes 在 startPlay 的 Rss.getContent onSuccess 异步回调中才初始化。用户在采集完成前快速滑到末集占位 → flatSize 未含集列表 → 末集判断/占位判定失真；appendNext 完成回调与 startPlay 采集回调写同一批字段（rssEpisodes/rssRoutes）无互斥。
- **修正**：QueueUnit 引入状态机 LOADING/READY/FAILED；flatSize 仅统计 READY 集；队列结构变更统一 Main 线程串行 + generation 计数器；startPlay 采集成功回调改为"写入队列当前 Unit"再由队列广播。

### R1-4（P1）三套异步令牌未统一
- **定位**：[VideoPlay.kt#L302-L308](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/model/VideoPlay.kt#L302-L308)（switchTokenCounter）、[VideoPlay.kt#L389](file:///f:/myself/github/WeAgentChat/temp/legado/app/model/VideoPlay.kt#L389)（switchToRouteToken）
- **事实**：播放切换与线路切换各持独立 token 池；AD-01 让 appendNext 复用 switchToRouteToken，语义不明：appendNext 期间用户切集/切线路时现有 token 均不覆盖 appendNext 的"成功后 setCurrentItem 定位"回调 → 迟到定位绑架导航。
- **修正**：VideoPlaybackQueue 内置 generation: Long，任何结构变更（append/替换 Unit 集列表/重置）递增；appendNext 回调与换线路回调统一校验 generation。

### R1-5（P2）Fragment 复用锚定 itemId=position
- **定位**：[VideoPagerAdapter.kt#L45-L56](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/video/VideoPagerAdapter.kt#L45-L56)
- **事实**：getItemId=position、containsItem 防越界已存在（历史崩溃 3.26.081817 的修复）。队列追加发生在尾部、占位页转正为集，既有 position 语义保持不变——该机制与队列兼容良好；但队列 Unit 集列表**替换**（换线路）时同 position 内容变化，FragmentStateAdapter 不会自动重建（itemId 未变），依赖 notifyDataSetChanged 的 REPOSITION 策略，需真机验证滑动手感与画面正确性。

---

## 轮2【数据一致性与双源真相】攻击结果

### R2-1（P0 阻塞）QueueUnit.episodes 与 VideoPlay.rssEpisodes/episodes 双份状态，权威契约未定义
- **定位**：[VideoPlay.kt#L381-L383](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/model/VideoPlay.kt#L381-L383)、[VideoPlay.kt#L1879](file:///f:/myself/github/WeAgentChat/temp/legado/app/model/VideoPlay.kt#L1879)、[VideoPlay.kt#L1939-L1954](file:///f:/myself/github/WeAgentChat/temp/legado/app/model/VideoPlay.kt#L1939-L1954)
- **事实**：triggerPreload/upRssEpisodeIndex/集选择器 UI/换线路采集全部直读写 VideoPlay.rssEpisodes；设计让队列另持 QueueUnit.episodes 却未声明同步契约。两份状态漂移 → 选集错位、预加载错集、换线路后队列与选择器不一致。
- **修正**：design 必须写死单一权威：**队列是集列表唯一写者；VideoPlay.rssEpisodes = 队列当前 Unit.episodes 的只读投影**（切换 Unit/换线路/appendNext 时由队列统一投影写入），选择器/预加载/索引字段全部保持现读法不变（零改动面最小）。书源同理：VideoPlay.episodes/volumes/toc 为投影，权威在 Unit.meta（书源重构见 R2-2）。

### R2-2（P0 阻塞）跨影片切换"整体替换清单"不完整，且手写清单方案脆弱
- **定位**：[VideoPlay.kt#L930-L977](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/model/VideoPlay.kt#L930-L977)（resetForNewIntent 全量清单）、[VideoPlay.kt#L1036-L1114](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/model/VideoPlay.kt#L1036-L1114)（initSource 完整写入面）
- **事实**：tasks 3.5 列的替换字段（book/toc/volumes/episodes/rssRoutes/rssEpisodes/进度）遗漏：chapter、durVolume、durChapterPos、**rssStar/rssRecord（进度写回目标，R2-3）**、rssEpisodeIndex/rssRouteIndex、videoUrl/originalPlayUrl（播放历史键，4.8b Z9 体系）、hasPlayedSuccessfully（BUFFERING 超时 25s/12s 判定）、currentPlayHeaders、source（书源跨影片 origin 可能不同）、danmakuStr/danmakuFile、lastPlayedArticleLink。
- **修正**：放弃手写清单，抽取 `VideoPlay.switchToUnitState(...)` 复用 initSource 的书源写入链（bookUrl 入库查 toc→卷切片→rssRoutes 映射→durChapterPos 恢复，L1047-1114 已是完整实现）；订阅源复用 switchToArticle 的 source 同步+rssStar/rssRecord 重查逻辑。禁止实现者凭 tasks 3.5 手抄字段——那是串台 bug 温床。

### R2-3（P1）saveRead 跨影片写回错乱窗口
- **定位**：[VideoPlay.kt#L1956-L2016](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/model/VideoPlay.kt#L1956-L2016)、[VideoPlayerActivity.kt#L501-L511](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/video/VideoPlayerActivity.kt#L501-L511)
- **事实**：saveRead 直接读单例 book/rssStar/rssRecord；10s 定时 historySaveJob 随时触发。若队列 UI 先切、状态后切，定时器落在窗口内 → 旧影片进度写错或新影片进度用旧 durChapterPos 覆盖。播放历史键 originalPlayUrl 同理。
- **修正**：switchToUnitState 状态切换先于队列/UI 变更且在 Main 线程同步完成（状态写入本身无挂起点，书源 toc 查 DB 放前置协程、切换动作在回调内原子执行）；切换期间置 `isSwitchingUnit=true`，saveRead 入口短路。

### R2-4（P1）rssArticle 三级取值链与队列 meta 的权威错位
- **定位**：[VideoPlay.kt#L478](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/model/VideoPlay.kt#L478)、[VideoPlay.kt#L1411-L1412](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/model/VideoPlay.kt#L1411-L1412)
- **事实**：`rssStar?.toRssArticle() ?: rssRecord?.toRssArticle() ?: rssArticles?.getOrNull(rssArticleIndex)` ——rssStar/Record 的转换体与列表对象字段可能不一致。队列 Unit.meta 持 RssArticle 后，分派若走 rssStar 转换体、appendNext 若走列表对象，末集判断与集采集用的文章可能非同一对象。
- **修正**：明确 Unit.meta.rssArticle = rssArticles[index] 原对象（列表权威）；switchToUnit 时同步重查 rssStar/rssRecord（复用 switchToArticle L1629-1632），仅作为进度/收藏载体，不再参与"取文章"。

---

## 轮3【回归面与行为矩阵】攻击结果

### R3-1（P0 阻塞）书源分页数据源迁移在 tasks/File Changes 中缺失（与 R5 组件化承诺矛盾）
- **定位**：[VideoPagerAdapter.kt#L23-L29](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/video/VideoPagerAdapter.kt#L23-L29)
- **事实**：现状书源 itemCount = VideoPlay.episodes.size（BookChapter 卷切片）。设计 File Changes 对 VideoPagerAdapter 只写"订阅源多集=rssEpisodes"；行为矩阵又写"书源多集 下一集（已有）"暗示不动。若书源不迁队列，adapter 双真相（书源走 episodes、订阅源走队列）→ R5 组件化承诺落空且 AD-03 的占位页/appendNext 无处生效。
- **修正**：明确书源**也迁队列**（行为不变、数据源换为队列投影）：新增 tasks"书源 episodes 分页迁队列（行为零变化回归）"，VideoPagerAdapter.getItemCount 统一 = 队列 flatSize + 占位。

### R3-2（P0 阻塞）R6 列表注入入口盘点不全（3 处遗漏实锤）
- **定位**：Grep `SearchBookOpenHelper.open` 全仓 5 个调用点：
  - [SearchActivity.kt#L618-L626](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/book/search/SearchActivity.kt#L618-L626)（单源+全局，设计已列）
  - [ExploreFragment.kt#L3689-L3693](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/main/explore/ExploreFragment.kt#L3689-L3693)（设计已列）
  - [ExploreShowActivity.kt#L200-L207](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/book/explore/ExploreShowActivity.kt#L200-L207) —— **发现分类展开列表的真实点击主体，设计 In-Scope 表把它误记为 ExploreFragment**
  - [AiToolPreviewDialog.kt#L143](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/main/ai/compose/AiToolPreviewDialog.kt#L143)、[AiMarkdownComponents.kt#L739](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/main/ai/compose/AiMarkdownComponents.kt#L739)（AI 场景直达播放）
- **修正**：spec In-Scope 表与 tasks 3.3/3.4 补齐 ExploreShowActivity（P0，R6 承诺主体）；AI 两处标注 P2（单影片直达语义可接受，注明 Out of Scope 或后续补）。

### R3-3（P1）"普通文章模式零改动"承诺需落地为明确的分支保留声明
- **定位**：[VideoPlayerActivity.kt#L562-L589](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/video/VideoPlayerActivity.kt#L562-L589)、[VideoFragment.kt#L291-L310](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/video/VideoFragment.kt#L291-L310)
- **事实**：onPageSelected 的 when 分支与 VideoFragment.activatePlayer 的 rssArticles 分支（switchToArticle(episodeIndex)）是普通文章模式唯一链路。设计没写"这条链路保留原样"；且 activatePlayer 的分派参数是 Fragment 参数 position（newInstance L1388-1392）——多集模式下 position 变扁平位，switchToArticle(扁平位) 语义错误（把集位当文章位）。File Changes 里 VideoFragment 只写"占位页加载态渲染"，遗漏分派改造。
- **修正**：design 增补"分支矩阵"：普通文章模式 = onPageSelected rssArticles 分支 + activatePlayer rssArticles 分支原样保留；多集/书源 = 队列 locate 分派。File Changes 补 VideoFragment：activatePlayer 分派改造 + 占位页渲染。

### R3-4（P1）appendNext 的"默认线路"采集断言与代码能力不匹配
- **定位**：[Rss.kt#L353-L376](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/model/rss/Rss.kt#L353-L376)、[VideoPlay.kt#L648-L664](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/model/VideoPlay.kt#L648-L664)
- **事实**：getEpisodesAwait 按 routeIndex 采**单线路**；而"默认线路"= directRouteIdx 直链优选，需先全线路解析（startPlay 走 Rss.getContent→parseRssRoutes→直链优选）。设计 Provider 写"复用 Rss.getEpisodesAwait 采集默认线路"——实现者会发现拿不到 directRouteIdx。
- **修正**：订阅源 Provider appendNext 复用 Rss.getContent 同款全线路采集+直链优选，新 Unit 缓存全 routes（附赠：该影片换线路零网络）。

### R3-5（P1）全局搜索混源列表的 source 同步未纳入 Provider
- **定位**：[RssArticleInfoActivity.kt#L270-L279](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/rss/search/RssArticleInfoActivity.kt#L270-L279)、[VideoPlay.kt#L1614-L1627](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/model/VideoPlay.kt#L1614-L1627)
- **事实**：RssSearchSourceHolder.rssArticles 是多源混合列表（各文章 origin 不同）；switchToArticle 的 B2 修复做 source 同步+失败中止。队列订阅源 Provider"取下一文章"跨源时必须复用同一逻辑，否则 ruleContent 解析用错源 → 播放失败。设计 Data Flow 与 Provider 定义均未提。
- **修正**：Provider 前置步骤 = switchToArticle 的 source 同步块（抽公共函数），失败则 appendNext 返回 null 走统一错误。

### R3-6（P2）换源对话框入口的形态漂移缺回归用例
- **定位**：[ChangeRssArticleSourceDialog.kt#L124-L133](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/rss/search/ChangeRssArticleSourceDialog.kt#L124-L133)
- **事实**：混源列表中点击多集源文章 → 形态从文章模式切多集模式，行为矩阵在该入口发生漂移。回归用例应覆盖。

---

## 轮4【性能与内存】攻击结果

### R4-1（P2）队列内存与 Fragment 数量可控，回滑重采集是真实体验点
- **事实**：FragmentStateAdapter+offscreenPageLimit=1 → 活跃 Fragment≈3 个，无增长问题。QueueUnit 集列表为轻对象（几百集≈几十 KB）。但 activatePlayer 每次激活都走完整网络采集链（switchToArticle/playRssEpisode 无结果缓存，[VideoFragment.kt#L297-L309](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/video/VideoFragment.kt#L297-L309)）——现状即如此（非回归），但"全回退"升级（见裁决）会放大回滑频率。
- **修正**：P2——Unit 缓存已采集 routes；二期考虑 finalUrl 结果缓存（SniffEngine 现为进行中去重非结果缓存，[VideoPlay.kt#L1869-L1871](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/model/VideoPlay.kt#L1869-L1871)）。

### R4-2（P1）appendNext 等待期导航绑架风险
- **事实**：占位页触发 appendNext（书源=getChapterListAwait 两级网络）。用户等待中上滑返回 → appendNext 完成后 setCurrentItem(新首集) 会把用户拉回新影片。AD-05 未定义取消语义。
- **修正**：appendNext 完成回调校验"用户仍停留在占位页（viewPager.currentItem==占位位）"，否则只入队不定位；上滑离开占位页即取消 pending 定位（generation 校验天然覆盖）。

### R4-3（INFO）预加载现状与队列兼容
- **事实**：triggerPreload 仅预嗅探当前线路下一集（[VideoPlay.kt#L1875-L1921](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/model/VideoPlay.kt#L1875-L1921)），跨影片无预加载；VideoBookPreloader 预载发现页前 12 项目录 + initSource 即时加载兜底（[VideoPlay.kt#L1065-L1092](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/model/VideoPlay.kt#L1065-L1092)）已实证存在。设计依赖成立。

---

## 轮5【边界与崩溃】攻击结果

### R5-1（P0 阻塞）VideoPlaylistHolder 生命周期与 consume 校验未定义
- **事实**：先例 RssSearchSourceHolder 由阅读页/播放页 onDestroy 清理（[RssArticleInfoActivity.kt#L278-L279](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/rss/search/RssArticleInfoActivity.kt#L278-L279)）。若 VideoPlaylistHolder 不清理：上次搜索残留 books 列表 → 用户下次从书架/历史进入另一影片（无列表上下文）→ initSource consume 残留列表 → 错误续播陌生影片列表（数据串台级 bug）。
- **修正**：AD-04 补三条铁律：a) VideoPlayerActivity onDestroy 清空 Holder；b) consume 一次性取走（取后置空）；c) 校验 Intent bookUrl == books[index].bookUrl，不匹配整表丢弃。

### R5-2（P1）队列不持久化，force-stop 重进退化路径未声明
- **事实**：队列在 VideoPlay 单例进程内存。force-stop 重进 → Intent 仅单影片参数 → 队列仅初始 Unit → Scenario 5 兜底成立但设计未明说；Activity 旋转重建（进程未死）→ 队列存活、FragmentStateAdapter 自动恢复（itemId=position 稳定）成立。
- **修正**：design 显式声明："队列不持久化，进程死亡退化为单影片模式（Scenario 5）；会话内旋转/重入恢复依赖队列存活 + position 稳定 ID"。Scenario 5 补充该前提。

### R5-3（P1）失败重试与防重守卫的复位语义
- **定位**：[VideoPlay.kt#L1075-L1092](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/model/VideoPlay.kt#L1075-L1092)（initSource 目录失败仅 AppLog，现状 startPlay toast"未找到章节"）
- **事实**：AD-01"一次触发防重"未定义失败复位：若失败后 canAppend 永久 false → 用户无法重试；若失败不回退占位页 → 用户卡死在无播放页。另外书源目录失败现状静默日志（VbsDiag），队列化后必须走统一错误事件。
- **修正**：AD-05 补：失败 → postEvent VIDEO_PLAY_ERROR + setCurrentItem 回退占位前一页 + 复位 append 标志（可重试）；防重 = 进行中互斥而非一次性。

### R5-4（P2）书源跨影片后的标题/详情刷新事件缺口
- **定位**：[VideoPlay.kt#L1502-L1505](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/model/VideoPlay.kt#L1502-L1505)
- **事实**：startPlayBookChapter 不发 VIDEO_SUB_TITLE（订阅源 playRssEpisode L1839 发）；书源标题靠 onPageSelected composeTitle。跨影片 setCurrentItem 会触发 onPageSelected 刷新标题，但**详情抽屉/线路选择器依赖 UP_VIDEO_INFO 事件**，switchToUnit 后必须补发，否则抽屉显示旧影片数据。
- **修正**：switchToUnitState 末尾统一 postEvent(UP_VIDEO_INFO)（换线路已有同款，[VideoPlay.kt#L1429](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/model/VideoPlay.kt#L1429)）。

### R5-5（P2）悬浮窗/T1.13 快照与队列的边界声明
- **定位**：[VideoPlayerActivity.kt#L289-L300](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/video/VideoPlayerActivity.kt#L289-L300)
- **事实**：快照仅 4 字段（videoUrl/videoTitle/singleUrl/inBookshelf），队列不在快照范围；悬浮窗返回走 clonePlayState 不重建队列（安全），但 8 实例快速切换时队列作为新增共享可变状态，串扰面与 VideoPlay 单例同源——属 T1.13 已知遗留，非本期劣化。
- **修正**：design 风险评估声明一句即可（不新增劣化，快照范围不变）。

### R5-6（INFO）占位页 Fragment 生命周期安全已验证
- **定位**：[VideoFragment.kt#L230-L233](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/video/VideoFragment.kt#L230-L233)
- **事实**：activatePlayer 首行 `_playerView ?: return`，占位页（无播放器视图）被 onPageSelected/onFragmentViewReady 激活时安全返回。该前提成立，设计无需修改。

---

## 汇总①：五轮问题清单（P0/P1/P2）

| 编号 | 级别 | 问题 | 定位 |
|------|------|------|------|
| R1-1 | P0 | 多集模式 loadMoreArticles 误触发（双追加冲突） | VideoPlayerActivity L586-589 |
| R1-2 | P0 | 换线路后队列 position 校正算法缺失（setCurrentItem(0) 回跳首影片） | VideoPlayerActivity L644-647 |
| R2-1 | P0 | 队列/VideoPlay 双份集状态权威契约未定义 | VideoPlay L381-383/L1879 |
| R2-2 | P0 | 跨影片状态替换清单不完整（漏 12+ 字段），须复用 initSource 链 | VideoPlay L930-977/L1036-1114 |
| R3-1 | P0 | 书源分页迁队列任务缺失，与 R5 组件化承诺矛盾 | VideoPagerAdapter L23-29 |
| R3-2 | P0 | R6 注入入口漏 3 处（ExploreShowActivity 为主） | ExploreShowActivity L205 等 |
| R5-1 | P0 | VideoPlaylistHolder 生命周期/consume 校验未定义（串台风险） | RssSearchSourceHolder 先例 |
| R1-3 | P1 | 初始 Unit 集列表异步就绪竞态 | VideoPlay L640-664 |
| R1-4 | P1 | 三套异步令牌未统一，appendNext 回调无守卫 | VideoPlay L302-308/L389 |
| R2-3 | P1 | saveRead 跨影片写回窗口 | VideoPlay L1956-2016 |
| R2-4 | P1 | rssStar 三级取值链与队列 meta 权威错位 | VideoPlay L478 |
| R3-3 | P1 | 普通文章模式分支保留声明缺失；VideoFragment 分派改造遗漏 | VideoFragment L291-310 |
| R3-4 | P1 | "默认线路"采集断言错误（getEpisodesAwait 无直链优选） | Rss L353-376 |
| R3-5 | P1 | 混源列表 source 同步未纳入 Provider | VideoPlay L1614-1627 |
| R4-2 | P1 | appendNext 等待期导航绑架（取消语义缺失） | AD-05 |
| R5-2 | P1 | 队列不持久化退化路径未声明 | — |
| R5-3 | P1 | 失败重试与防重复位语义未定义 | AD-01/AD-05 |
| R1-5 | P2 | 换线路同 position 内容变化的 Fragment 复用验证 | VideoPagerAdapter L45-56 |
| R3-6 | P2 | 换源对话框入口形态漂移回归用例 | ChangeRssArticleSourceDialog L124-133 |
| R4-1 | P2 | 回滑重采集（Unit 缓存 routes 缓解） | VideoFragment L297-309 |
| R5-4 | P2 | 书源跨影片 UP_VIDEO_INFO/标题事件补发 | VideoPlay L1502-1505 |
| R5-5 | P2 | 悬浮窗/T1.13 边界声明 | VideoPlayerActivity L289-300 |

## 汇总②："书源全回退扁平队列"裁决

**裁决：应升级。AD-03 由"换源式+不回退"改为"全回退扁平队列，向后回退零网络"。** 三维度论证：

1. **内存代价（低）**：书源回退无需网络——BookChapter 已入库（initSource 即查 `appDb.bookChapterDao.getChapterList(bookUrl)`，[VideoPlay.kt#L1048](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/model/VideoPlay.kt#L1048)）。Unit.meta 只需持 {Book 引用, durVolumeIndex}（<1KB 级）；已访问 Unit 可选缓存 toc 列表（几百章约 100-300KB/部，可 LRU 或仅持 bookUrl+卷索引按需重查 DB）。订阅源侧本就全内存。**内存不构成否决理由**。
2. **实现复杂度（低增量）**：向前 appendNext 本就必须实现"switchToUnitState 整体状态切换"（tasks 3.5 + R2-2 整改）；向后回退 = 同一函数 + toc 从 DB 重查代替网络采集。二者是**同一份代码的两次调用**，增量仅为"向 VideoPlaylistHolder 取前一个 SearchBook 并重查目录"。设计原本的"不回退"反而要额外实现"跨 Unit 边界上滑禁用"分支。
3. **状态一致性（升级后更优）**：统一 switchToUnitState 使 saveRead 写回（R2-3）、rssRoutes 映射、UP_VIDEO_INFO 刷新天然一致；"不回退"方案则留下不对称行为（订阅源可回退、书源不可），与本次重构"行为一致性！"的初心直接冲突。

**边界修正**：初始 Unit 之前的影片（用户从列表中间进入）同样懒加载构造（Holder 有完整 books+index，向前 append 与向后 append 对称）；若实施中发现对称懒加载复杂度超预期，允许一期先做"已访问/已 append 单元间回退 + Unit 内全回退"，前向懒加载列二期——但必须在 design 显式标注，不允许沉默降级。

## 汇总③：设计文档需修订的具体条目清单

| 文档 | 条目 | 修订内容 |
|------|------|---------|
| spec.md | In-Scope 表 | 书源发现列表入口更正为 ExploreShowActivity（L205），ExploreFragment 为聚合入口；补 AI 两入口为 Out of Scope（P2） |
| spec.md | Approach-2 订阅源采集 | "复用 Rss.getEpisodesAwait"改为"复用 Rss.getContent 全线路采集+直链线路优选（directRouteIdx）" |
| spec.md | Approach-2 上滑 | 书源上滑由"—"改为"上一集/上一影片（升级为全回退队列）" |
| spec.md | Scenarios | 补 S7 换线路后滑动校正、S8 force-stop 重进退化、S9 混源列表点击多集文章、S10 悬浮窗返回 |
| design.md | AD-01 | 补 generation 计数器统一守卫（替代多 token 池叠加）；补 Unit 状态机 LOADING/READY/FAILED |
| design.md | AD-02 | 补换线路后 setCurrentItem(unitStart+idx) 校正；补 loadMoreArticles 限定普通文章分支 |
| design.md | AD-03 | **重写为全回退扁平队列**（见裁决），书源回退 = DB 重查目录 |
| design.md | AD-04 | 补 Holder 生命周期三铁律（onDestroy 清理/consume 一次性/bookUrl 校验） |
| design.md | AD-05 | 补取消语义（离开占位页不定位）、失败复位可重试 |
| design.md | 新增章节 | "状态权威契约"（R2-1：队列唯一写者，VideoPlay 字段为投影）+"switchToUnitState 原子切换"（R2-2/R2-3：复用 initSource/switchToArticle 链，Main 线程原子执行，saveRead 短路） |
| design.md | File Changes | 补 VideoFragment（activatePlayer 分派改造）、ExploreShowActivity、RssArticlesFragment 无需改的声明 |
| tasks.md | 任务新增 | 2.5 订阅源 Provider source 同步块抽取；3.6 书源 episodes 分页迁队列零变化回归；3.7 向前回退懒加载（Unit=前一个 SearchBook）；4.5 loadMoreArticles 分支限定；4.6 换线路 position 校正；5.7 补 S7-S10 真机用例 |
| tasks.md | 0.x 准备 | 固化本报告已核实结论（分派链=getPageSelected+activatePlayer 双入口、holder 先例清理时机、getEpisodesAwait 单线路限制），避免实施期重复考证 |

## 汇总④：结论

**需修订后实施（⚠️ 整改后落地）**。

- 核心架构方向（统一队列+扁平映射+Provider 分派+占位页）与源码现状兼容性良好：itemId=position 稳定 ID 机制（[VideoPagerAdapter.kt#L45-L56](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/video/VideoPagerAdapter.kt#L45-L56)）、占位页激活安全（[VideoFragment.kt#L230-L233](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/video/VideoFragment.kt#L230-L233)）、initSource 即时加载链均可直接复用。
- 但按现稿直接开工必然产出串台级缺陷（R2-2 状态清单、R5-1 Holder 残留、R1-1 双追加、R1-2 位置回跳）。
- 完成上表 13 条修订（P0 7 条为开工前置，P1 可与实施并行修订）后，文档可达到"拿到即可开工"标准。

**量化评分（修订前，0-100 参考）**：代码匹配度 72 ｜ 技术成熟度 68 ｜ 落地清晰度 58
**量化评分（按清单修订后预估）**：代码匹配度 90+ ｜ 技术成熟度 85+ ｜ 落地清晰度 90+
