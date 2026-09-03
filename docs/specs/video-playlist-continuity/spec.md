# spec.md — video-playlist-continuity

## Intent

统一视频播放的滑动行为（用户裁决："行为一致性！统一！"）：
- **多集**（订阅源 ruleRoutes/ruleEpisodes 多线路多集 / 书源 episodes 卷章）：下滑 = 下一集，上滑 = 上一集
- **单集，或多集最后一集**：下滑 = 播放列表中的下一个视频（影片），上滑 = 上一集
- **组件化**：抽取统一播放队列组件（订阅源/书源共用），为后续统一升级优化打好基础

**现状缺陷实锤（2026-09-02 源码核实）**：VideoPagerAdapter/onPageSelected 分页优先级 `rssArticles > episodes`——订阅源多线路多集播放时下滑切的是"下一个影片"而非"下一集"（集间只能靠集数选择器），不满足统一行为；本期修复。

## Scope

### In Scope
- **视频列表呈现入口全面盘点与补齐**（代码事实核查 2026-09-02）：

| 入口 | 类型 | 列表注入现状 | 本期动作 |
|------|------|------------|---------|
| 书源-发现分类列表（**ExploreShowActivity L205 为真实主体**；ExploreFragment 为聚合入口） | BookSource(video) | ❌ 单 book | **注入列表** |
| 书源-搜索/全局搜索（SearchActivity L618-626） | BookSource(video) | ❌ 单 book | **注入列表** |
| 书源-书架/播放历史重进（ContextExtensions 等） | BookSource(video) | 无列表上下文 | 保持单集（合理） |
| 订阅源-分类列表（RssArticlesFragment L345 已传列表+分页上下文） | RssSource(video) | ✅ 已有 | 队列迁移 |
| 订阅源-统一搜索（RssSearchActivity→RssArticleInfoActivity→ReadRss） | RssSource(video) | ✅ 已有 | 队列迁移 |
| 订阅源-收藏/历史单篇直达（单参 readRss） | RssSource(video) | 无列表上下文 | 保持单集（合理，Out of Scope） |

- **统一播放队列组件**（VideoPlaybackQueue，组件化核心）：承载"影片单元列表+扁平集位映射+懒追加"，订阅源与书源双实现接入
- **订阅源多集分页改造**：多线路多集模式（ruleRoutes/ruleEpisodes 非空）分页数据源从 rssArticles（文章/影片）改为 rssEpisodes（当前线路集）；末集下滑 → 接 rssArticles 下一影片（新影片默认线路第一集）；上滑回上一集（跨单元上滑回前一影片，订阅源文章列表在内存天然可回退）
- **书源跨视频续播**：最后一集下滑 → 加载列表下一个视频（换源式，见 design AD-02）→ 播第一集
- **占位页**：集尽且有下一个影片时 ViewPager 尾部占位，滑到触发加载

### Out of Scope
- 订阅源收藏/历史单篇直达的列表连续性（无列表来源，保持单集）
- 漫画/图片源（ImagePlay 独立机制）
- 换线路/选集交互重构（沿用现有 switchToRoute/playRssEpisode/详情抽屉，仅对齐队列位置）

## Approach

### Selected Approach

**统一播放队列组件（VideoPlaybackQueue）+ 影片单元抽象（组件化核心，用户裁决升级）**：

1. **组件抽象**：`VideoPlaybackQueue`（model 层组件）承载"影片单元（Unit）列表 + 扁平集位映射 + 懒追加"：
   - `QueueUnit`：一个影片单元 = {标题, 集列表(List<RssEpisode> 统一模型), 单元元数据(订阅源: rssArticle+当前线路 / 书源: book+当前线路索引)}
   - 扁平位映射：`position ↔ (unitIdx, epIdx)`；ViewPager itemCount = Σ units 集数 +（可追加 ? 1 占位）
   - 追加分派由**源侧 Provider 实现**（组件不感知源类型）：订阅源=rssArticles 下一文章+采其默认线路集数（多线路模式复用 Rss.getEpisodesAwait）；书源=playlist 下一 SearchBook+getChapterListAwait
2. **分页数据源改造（订阅源多集现状缺陷修复）**：
   - 订阅源多线路多集（ruleRoutes/ruleEpisodes 非空）：分页数据源 rssArticles → **rssEpisodes**（集间滑动，现状缺陷修复：现状下滑=切影片）；末集下滑 → 队列追加下一影片（其默认/当前线路集数）；上滑回上一集（跨单元上滑回前一影片，文章列表在内存可回退）
   - 书源：episodes 分页（已有）→ 末集下滑 → 队列追加下一 SearchBook 目录（即时加载）
   - 订阅源单集/文章模式（非多线路多集）：保持 rssArticles 分页（既有行为已统一）
3. **列表注入**：`VideoPlaylistHolder`（object 单例，仿 RssSearchSourceHolder 先例）——书源入口（SearchActivity/ExploreFragment 点击）注入 SearchBook 列表+索引；订阅源列表已有（rssArticles+分页上下文）
4. **行为矩阵（统一后）**：

| 数据形态 | 下滑 | 上滑 | 实现载体 |
|-------|---------|---------|---------|
| 订阅源多线路多集 | **下一集（改造）** | **上一集（改造）** | 队列 rssEpisodes 分页 |
| 订阅源多集末集 | 下一个影片（队列追加下一文章） | — | 队列 appendNext |
| 订阅源单集/文章模式 | 下一文章（已有） | 上一文章（已有） | rssArticles 分页 |
| 书源多集 | 下一集（已有） | 上一集（已有） | episodes 分页 |
| 书源多集末集/单集 | 下一个视频（新增） | **上一集/上一影片（全回退队列，DB 重查零网络）** | 队列 appendNext/appendPrev |
| 任意源无列表 | 单页禁滑动（合理） | — | isSinglePage 判定 |

### Alternatives Considered

| 替代方案 | 否决理由 |
|---------|---------|
| 订阅源/书源各自实现续播（不抽组件） | **用户否决**：要求"抽取出来考虑组件化复用性，为后续统一升级优化做好准备"——两套滑动/追加/占位逻辑必然漂移 |
| 订阅源维持文章分页不动 | 违背统一裁决：多集订阅源下滑≠下一集，用户明确要求修复 |
| 书源跨视频扁平队列（episodes 追加他 book 章节） | BookChapter.bookUrl 语义污染（DB 写回/弹幕/进度映射全链适配），队列用统一 RssEpisode 模型承接更干净 |
| 仅靠扩大 VideoBookPreloader 预加载覆盖 | 治标——与"未找到章节"修复（initSource 即时加载）重复建设，无法覆盖任意点击 |
| 订阅源历史/收藏单篇做列表连续性 | 无列表来源（单篇直达），硬造列表违背语义 |

### Drawbacks

- 订阅源多集分页改造触及 VideoPagerAdapter/onPageSelected/标题映射核心链路——回归面大（订阅源三种形态全要真机回归）
- 书源队列追加为换源式（新影片目录网络加载）——上滑不回退前一视频（订阅源队列可回退），不对称 Tradeoff 接受
- 占位页/追加为异步网络操作——需加载态、失败统一提示（VIDEO_PLAY_ERROR）、竞态守卫

## Requirements

- **R1**: 行为统一矩阵（见 Approach 表）全源类型生效
- **R2**: 订阅源多线路多集下滑=下一集/上滑=上一集（现状=切影片，需改造）
- **R3**: 末集/单集下滑接列表下一个影片：异步、可取消（竞态守卫）、失败统一提示、成功播第一集并同步标题/详情/选集
- **R4**: 跨影片进度记忆各影片独立
- **R5**: 组件化：VideoPlaybackQueue 独立于具体源类型，源侧 Provider 分派（后续新源类型可插拔）
- **R6**: 书源列表注入覆盖发现分类列表 + 搜索（含全局搜索）
- **R7**: 订阅源非多线路多集形态（普通文章模式）回归零变化

## Scenarios

### Scenario 1: 订阅源多集——集间滑动（现状缺陷修复）
给定多线路多集订阅源影片A（2线路×N集），
当播放页下滑/上滑，
则切换A的下一集/上一集（**现状是切影片，本期修复**）；A末集下滑则接列表下一影片B的第一集。

### Scenario 2: 书源多集末尾接播下一个视频
给定从发现列表点入影片A（3集，列表中A后还有影片B/C），
当用户下滑到A第3集再继续下滑，
则出现加载占位 → 自动加载B的目录 → 播放B第1集；标题/详情/选集数据同步切换为B。

### Scenario 3: 书源单集接播
给定单集影片A（列表中A后有B），
当下滑，
则直接加载播放B第一集。

### Scenario 4: 订阅源文章模式回归
给定非多线路多集订阅源（普通文章），
当下滑到最后一个文章再下滑，
则 loadMoreArticles 追加下一页（既有行为零变化）。

### Scenario 5: 无列表兜底
给定从书架/历史重进（无列表注入），
当多集下滑到最后一集或单集下滑，
则无下一个动作（单页禁滑动或停留末集），不报错。

### Scenario 6: 加载失败
给定列表有下一个影片但目录/集数加载失败（网络/源异常），
当下滑触发加载，
则统一错误提示（VIDEO_PLAY_ERROR），可回退重试（FAILED 单元重新进入触发重试）。

### Scenario 7: 换线路后滑动校正（红队 R1-2）
给定多线路多集影片播放中（队列扁平位在影片中段），
当用户切换线路（新线路集数不同），
则 ViewPager 定位校正到"当前影片起始位+当前集索引（clamp）"，不回跳首影片。

### Scenario 8: force-stop 重进退化（红队 R5-2）
给定播放队列在内存（force-stop 后丢失），
当用户重进播放器，
则从该影片单单元起步重建队列，进度按 book 恢复，续播列表按需重新注入（无列表则单集）。

### Scenario 9: 混源列表点击（红队 R3-5）
给定全局搜索混源结果（多源影片混合列表），
当点入某影片后下滑触发追加，
则 Provider 按 origin 解析对应源（B2 source 同步），追加影片集数来源正确。

### Scenario 10: 悬浮窗返回（红队 R5-5）
给定悬浮窗播放后返回播放器（T1.13 快照机制），
当恢复播放，
则队列状态与快照一致（不重建队列、不重复追加），续播行为保持。
