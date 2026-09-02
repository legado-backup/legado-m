# review-report.md — video-booksource-multiroute 渗透审查（2026-09-02）

审查方式：四文档逐条断言对照真实源码穿透核验（非纸面评审）。
核验基线：BookSourceType.kt / BookExtensions.kt / SearchBookOpenHelper.kt / BookChapterList.kt / VideoPlay.kt / Rss.kt / WebBook.kt / BookContent.kt / VideoFragment.kt / VideoPlayerActivity.kt / TocActivity.kt / AnalyzeRule.kt / BookSource.kt / RssSource.kt / BookInfoActivity.kt / modules/web。

## 一、问题清单（按级别）

### P0-1 [P0 阻塞] bookSourceType=2 值错误（video 实为 4，2 是 image）
- 锚点：spec.md L10/L83/L97、design.md L14（`bookSourceType=2` 共 4 处）
- 根因：[BookSourceType.kt#L8-L12](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/constant/BookSourceType.kt#L8-L12) 定义 `video = 4`、`image = 2`；文档把订阅源的 `RssSource.type == 2`（视频订阅源约定，Rss.kt L97）与 BookSourceType 命名空间混淆。照文档实施会命中**图片书源**分支。
- 修复：全部替换为 `bookSourceType=4`（`BookSourceType.video`），design 流程图 `bookSourceType=2 → bookSourceType==video`；tasks 0.3 增加"以 BookSourceType.video 常量为准，禁止硬编码数字"。

### P1-1 [P1] 强转点数量与分类错误（6 处 → 实为 8+1 处，且仅 3~4 处需抽象）
- 锚点：design.md AD-03、tasks.md 0.2/1.3
- 根因：Grep `as? RssSource` 实际 8 处（L476 startPlay 分派 / L1114 prewarm / L1332 isNewRoutesMode / L1346 switchToRoute / L1411 switchToArticle / L1468 loadMoreArticles / L1526 preloadNextArticleHtml / L1759 历史保存）；另有 startPlay 书源分支 [VideoPlay.kt#L780](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/model/VideoPlay.kt#L780) `source as BookSource` 硬强转未列入。其中 L1114/L1411/L1468/L1526 为文章模式专属，无书源对应物，强行接口化会扩大重构面、抬高订阅源回归风险。
- 修复：tasks 0.2/1.3 清单改为"多线路相关 4 处：L476/L1332/L1346/L1759（L1759 历史键按模式分派即可，可保留 cast）"；L780 硬强转列入盘点并在接口分派后收敛。

### P1-2 [P1] SourceMultiRoute 接口签名不完整，返回类型双实现不兼容
- 锚点：tasks.md 1.1（getRouteNames/getEpisodesByRoute/normalizedBody 等）、design AD-03
- 根因：RssEpisode（title/url/duration/cover）与 BookChapter 是不同模型；`getEpisodesByRoute` 返回类型不定义则双实现无法共享管线。且缺播放分派方法：`playRssEpisode`（VideoPlay L1565）硬依赖 rssArticle 非空（L1566-1572 直接 return），书源模式换线路必须走 `durVolumeIndex → upEpisodes()（L1141-1157）→ startPlay 章节链`，现有方法清单未覆盖该分派。
- 修复：接口至少定义：`isMultiRouteSupported(): Boolean`、`getRouteNames(): List<String>`、`getEpisodesByRoute(index): List<统一集数模型>`（建议复用 RssEpisode 或新增轻量 `RouteEpisode{title,url}`，BookSource 实现内由 BookChapter 映射）、`playRouteEpisode(player, routeIndex, episodeIndex, token)`（接口内分派：Rss→playRssEpisode / Book→durVolumeIndex+upEpisodes+startPlay）；tasks 1.1 按此落签名。

### P1-3 [P1] L0/L1 直链集的正文通路约定未写入设计（正文采集上下文）
- 锚点：spec.md R3/Approach、design AD-05、tasks 2.5
- 根因：正文阶段 ruleContent 的执行上下文 = **章节 URL 抓回的 body**（[BookContent.kt#L63](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/model/webBook/BookContent.kt#L63) `setContent(body)`）。对 L0/L1 源，chapter.url 即 m3u8 直链，App 会下载 m3u8 文本再跑 ruleContent → 必然失败/空正文（BookContent L204 抛 ContentEmptyException）。真实通路是既有机制 [WebBook.kt#L419-L422](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/model/webBook/WebBook.kt#L419-L422)：**正文规则为空 → 直接返回 chapter.url**。设计未声明"L1 四条 JSONPath 源的 ruleContent 必须留空"这一约定，书源作者若写了 ruleContent 即断链。
- 修复：spec R3 与 design AD-05 补充："L0/L1 直链集约定 ruleContent 留空（App 既有机制：contentRule.content 空 → getContent 返回章节链接，WebBook L419-422）；ruleContent 仅在章节 URL 为播放页时编写（L2 场景）"；skill 模板同步；tasks 2.5 增加"L1 源 ruleContent 留空用例"。

### P1-4 [P1] AD-04 正文页入口可达性不成立
- 锚点：spec Scenario 3/R4、design AD-04、tasks 3.1/3.2
- 根因：视频书所有主入口均重定向播放器：书架 [ContextExtensions.kt#L71](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/utils/ContextExtensions.kt#L71)/[FragmentExtensions.kt#L99](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/utils/FragmentExtensions.kt#L99)、详情页 [BookInfoActivity.kt#L1253](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/book/info/BookInfoActivity.kt#L1253)（isVideo → VideoPlayerActivity）、目录页 TocActivity L123、搜索 SearchBookOpenHelper L53。阅读器（ui/book/read 目录 grep isVideo 零命中，AD-04 现状描述准确）对 type=video 几乎不可达，Scenario 3 前提缺失。
- 修复：AD-04 降级表述为"兜底兼容入口"（源类型误标/历史遗留会话可达时生效），或在 design 补一条可达路径论证；tasks 3.1/3.2 保留但验收改为"构造可达场景验证"（如临时以文本书源属性打开视频书内容）。

### P1-5 [P1] R2 与 R9/AD-06 交互载体矛盾
- 根因：REQ-17/18 悬浮选择器数据源硬绑 `VideoPlay.rssRoutes/rssEpisodes`（[VideoFragment.kt#L755](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/video/VideoFragment.kt#L755)、L819），书源模式下天然隐藏（rssRoutes=null）；书源模式切线路/选集唯一 UI 载体是 AD-06 详情抽屉。R2"交互与视频订阅源一致"若按字面实施会去改 REQ-17/18 数据源，违反 R9 零改动。
- 修复：R2 限定为"能力一致：书源模式经详情抽屉提供线路 Tab+集数列表（AD-06），悬浮选择器仅订阅源"；AD-06 补一句"书源模式悬浮选择器维持隐藏属预期行为"。

### P2-1 [P2] normalizeMacCmsBody 是 Rss.kt private 且仅注入 routes，chapters 双结构为新工作
- 根因：[Rss.kt#L382](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/model/rss/Rss.kt#L382) private、注入顶层 `routes`（L409-410）；冲突检测 `item.has("routes")`（L386）与顶层注入不对称（源顶层若已有 routes 会被覆盖）。spec/design 将其列为"已真机验证能力"仅对 routes 成立；chapters 注入属新增。
- 修复：tasks 2.2 明确"抽取共享 Normalizer（建议 `help/video/MacCmsNormalizer`，routes+chapters 双结构、顶层 `json.has()` 冲突检测、空 url 段跳过语义沿用 L403），Rss.kt 委托调用保持订阅源行为等价"；tasks 4.3 回归锚定。

### P2-2 [P2] L0"零规则"范围未限定
- 修复：spec Scenario 1/AD-05 注明"L0 仅指目录/正文零规则；ruleSearch/ruleExplore/ruleBookInfo 仍需编写（MacCMS 标准模板）"。

### P2-3 [P2] AD-06 复用 showBookIntro 需适配说明
- 根因：[VideoPlayerActivity.kt#L936](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/video/VideoPlayerActivity.kt#L936) 渲染绑定 legacyContainer 隐藏视图（tvIntroContainer/introTextView，P0-1 后 gone），三分支 `<useweb>/<usehtml>/<md>`。
- 修复：AD-06 注明"复用需抽出渲染逻辑（传入目标容器）或抽屉内重建三分支渲染"，防实施时直接把隐藏视图塞进抽屉。

### P2-4 [P2] Web 端/导入导出零影响未显式声明
- 修复：spec Out of Scope 补"modules/web 书源编辑器零改动（bookSourceType/ruleToc/ruleContent 编辑能力既有，bookSourceEditConfig.ts L7/L336-399）；书源 JSON 导入导出对 bookSourceType=4 天然支持，零改动"。

## 二、遗漏排查逐项结论（2a-2j）

| 项 | 结论 | 证据锚点 |
|---|---|---|
| a 无新增字段→零影响 | 成立。ruleRoutes/ruleEpisodes 仅在 RssSource（L74/L76），BookSource 无新增 → schema/Parcelable/Gson 零影响 | BookSource.kt L42 |
| b Web 编辑器 | 无需同步（编辑能力既有）；建议文档显式声明（P2-4） | bookSourceEditConfig.ts |
| c 导入/导出/编辑器 | 字段既有，JSON 导入天然支持；零改动成立 | BookSource.kt |
| d TocActivity 卷章兼容 | 兼容。openChapter isVideo 分支 durVolumeIndex/chapterInVolumeIndex 换算与 upEpisodes `subList(startInt+1)` 语义一致 | TocActivity.kt L123-152 |
| e 正文采集卡点 | ruleContent 上下文=章节 URL body；直链集依赖"ruleContent 留空→返回 chapter.url"既有机制——设计必须写明（P1-3） | WebBook L419-422 / BookContent L63 |
| f JSONPath 元素级 getString | 支持。getElements Mode.Json getList（AnalyzeRule L415-433）+ 元素 setContent(Any)→isJSON 判定（L99-111）→ `$.title` 可取；订阅源 `$.routes[*].name` 列表范式同类已真机验证 | AnalyzeRule.kt |
| g 阅读器行为/AD-04 挂点 | 全入口重定向播放器，阅读器对视频书几乎不可达（P1-4）；ReadBookActivity 无任何 isVideo 代码（现状描述准确，播放动作为纯新增） | ContextExt L71 等 |
| h SourceMultiRoute 匹配度 | 接口不存在（待新增）✓；设计缺口见 P1-2（返回类型+播放分派） | — |
| i 电影类 L1 | 成立。规范化对每线路恒产 ≥1 章行（空 url 段跳过，L403 语义），卷+单章形态可播；纯"无剧集"仅 L3 存量，VideoPlay L760-767 既有语义覆盖 | Rss.kt L396-406 / VideoPlay L760-767 |
| j 换线路更新路径 | 现状书源模式无换线路 UI（playRssEpisode 依赖 rssArticle，null 静默返回）；目标=接口分派：durVolumeIndex→upEpisodes→startPlay 章节链（tasks 2.4 覆盖，需按 P1-2 落签名） | VideoPlay L1344-1374/L1565 |

## 三、一致性检查

- AD-01~06 ↔ R1-R10 ↔ tasks 映射完整：R1→2.2/2.3、R2→2.4/3.3、R3→2.5、R4→3.1/3.2、R5→4.2、R6→4.8、R7→2.4、R8→2.1/2.2、R9→3.3/3.4/4.9、R10→4.6/4.7，全部 AD 有任务覆盖。
- 口径矛盾 3 处：bookSourceType=2（P0-1）、6 处强转（P1-1）、R2/R9 载体（P1-5）。
- 文档行号引用核验：BookChapterList getElements L206 / isVolume L234-247 / 卷 url 替代 L261-263、VideoPlay 电影类注释 L761、volumes 模型 L1141-1157、ContextExt L71 / FragmentExt L99 —— 均准确；tasks 0.1"禁止凭文档行号改"门禁保留。
- 已核实为真的关键断言：normalizeMacCmsBody 注入机制存在（routes）、`$$$` 检测（L389）、P0-1 统一 ViewPager2 + legacyContainer gone（L166/L453/L533）、REQ-17/18 左下角容器（VideoFragment L665/L698/L701）、BookInfo PREPARE_BOOK_INFO、三层嗅探链 extractVideoUrlForEpisode L629、isDirectVideoStreamUrl L551、source: BaseSource L352。

## 四、审查结论

**需修正后实施**。修正 P0-1（bookSourceType=4）+ P1-1/1-2（强转清单与接口签名收窄）+ P1-3（L0/L1 ruleContent 留空约定落文档）+ P1-4（AD-04 可达性降级表述）+ P1-5（R2 载体限定）后即可开工；P2 各项随 tasks 修订一并落实。整体架构方向（字段映射/规范化层/管线复用/AD-06 抽屉）与源码现状吻合，核心复用点（normalize 机制、upEpisodes 卷模型、三层嗅探、直链短路既有机制）全部真实存在，无架构脱节。
