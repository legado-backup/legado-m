# tasks.md — video-playlist-continuity

> 五轮红队审查后修订版（red-team-report.md）：P0×7 已全部转化为任务/设计条目。

## 0. 准备（红队已核实结论固化，实施期免重复考证）
- [ ] 0.1 分派链实锤：onPageSelected + activatePlayer 双入口（VideoPlayerActivity L556-605 / VideoFragment L617-632）；itemId=position 稳定 ID + containsItem 校验（VideoPagerAdapter L45-56）兼容队列
- [ ] 0.2 注入入口 5 处实锤：SearchActivity L618-626（单源+全局）/ **ExploreShowActivity L205（发现分类真实主体）** / ExploreFragment 聚合 / AI 两处（P2 登记）
- [ ] 0.3 采集断言修正：Rss.getEpisodesAwait 仅单线路无直链优选 → 追加采集复用 Rss.getContent（directRouteIdx 优选）；Holder 先例（RssSearchSourceHolder）清理时机已核实

## 1. 统一队列组件（AD-01/AD-06）
- [x] 1.1 新增 `VideoPlaybackQueue`：QueueUnit{title, episodes(RssEpisode 统一模型), state: LOADING/READY/FAILED, meta}、扁平位映射（flatSize/locate/unitStart）、**generation 计数器统一守卫**（替代三套 token 叠加）
- [x] 1.2 `UnitProvider` 接口：hasNext/hasPrev/appendNext/appendPrev（源侧实现，组件零感知）
- [ ] 1.3 `switchToUnitState(unit)` 原子切换：**复用 initSource 写入链重构**（禁手抄字段清单）+ saveRead 短路（切换窗口跳过旧影片写回）

## 2. 订阅源接入（多集分页改造 AD-02）
- [ ] 2.1 订阅源 Provider：邻近文章 + **Rss.getContent 全线路采集（directRouteIdx 优选）** → 新 Unit；末尾接 loadMoreArticles 分页续拉影片
- [ ] 2.2 多线路多集模式分页数据源 rssArticles→rssEpisodes（VideoPagerAdapter + onPageSelected + 标题映射 + isSinglePage 判定）
- [ ] 2.3 **loadMoreArticles 分支限定**（红队 R1-1）：仅普通文章分支保留"末位触发"；多线路多集分支移除，消除扁平位中段误触发双追加
- [ ] 2.4 **换线路 position 校正**（红队 R1-2）：setCurrentItem(unitStart + clamp(idx))，禁裸 setCurrentItem(0)
- [ ] 2.5 Provider source 同步块（B2 修复复用，混源列表 origin→source 解析）
- [ ] 2.6 非多线路多集形态（普通文章模式）零改动回归

## 3. 书源接入（AD-03 全回退扁平队列）
- [ ] 3.1 新增 `VideoPlaylistHolder`（books/index/consume 一次性/bookUrl 校验/onDestroy 清理——三铁律）
- [ ] 3.2 书源 Provider：appendNext=下一 SearchBook+getChapterListAwait；**appendPrev=前一 SearchBook+DB 重查目录（零网络）**；初始单元前的影片懒加载对称构造（超预期则显式标注一期降级范围）
- [ ] 3.3 SearchActivity/ExploreShowActivity/ExploreFragment 点击注入
- [ ] 3.4 跨影片切换走 switchToUnitState（VideoPlay 投影整体重建：book/toc/volumes/episodes/rssRoutes/rssEpisodes/rssStar/rssRecord/originalPlayUrl 等全量）
- [ ] 3.5 书源 episodes 分页迁队列后行为零变化回归（红队 R3-1）

## 4. 占位页与 UI（AD-05）
- [ ] 4.1 VideoPagerAdapter itemCount=队列扁平大小+占位（可追加时）
- [ ] 4.2 onPageSelected(占位) 触发 appendNext（Unit=LOADING 防重）；**滑离占位页=取消**（generation 丢弃回调）；成功 notifyDataSetChanged+定位新首集+刷新标题/详情（含 UP_VIDEO_INFO/标题事件补发）；FAILED→VIDEO_PLAY_ERROR+回退+可重试
- [ ] 4.3 VideoFragment 占位页加载态渲染 + activatePlayer 分派对齐队列
- [ ] 4.4 isSinglePage 判定修正（单集但有队列下一个 → 允许滑动）

## 5. 验证
- [ ] 5.1 真机：订阅源多集下滑=下一集/上滑=上一集（Scenario 1，现状缺陷修复确认）
- [ ] 5.2 真机：订阅源多集末集下滑=下一影片第一集（Scenario 1 续）
- [ ] 5.3 真机：书源发现列表（ExploreShowActivity 入口）多集末尾接播/单集接播（Scenario 2/3）
- [ ] 5.4 真机：订阅源普通文章模式回归零变化（Scenario 4）
- [ ] 5.5 真机：无列表兜底（Scenario 5）+ 加载失败重试（Scenario 6）
- [ ] 5.6 真机：换线路 position 校正（S7）/ force-stop 重进退化（S8）/ 混源列表（S9）/ 悬浮窗返回（S10）
- [ ] 5.7 "未找到章节"修复回归（initSource 即时加载仍生效）
- [ ] 5.8 双追加消除专项：多集模式中段滑动不再触发 loadMoreArticles

## 6. 收尾
- [ ] 6.1 移除 VbsDiag 临时日志（Grep 确认 0 残留）
- [ ] 6.2 updateLog 更新（编译前）
- [ ] 6.3 文档同步（task-navigation/player 相关）+ 提交远端

## AOAdapt 日志
（实施中记录）
