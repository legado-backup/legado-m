# Spec：多线路多集按需采集架构优化

## Intent（意图）

**问题陈述**：当前 RSS 视频源（type=2）的多线路多集采集存在架构性问题——ruleContent JS 一次性采集所有线路所有集的 URL（部分 JS 还在脚本内逐集请求播放页 HTML 提取 m3u8），导致：

1. **性能损耗**：N 集 × M 线路次网络请求在 JS 执行阶段完成，列表加载耗时长
2. **开发者负担**：JS 规则需处理镜像站、player_aaaa 变量、转义斜杠、MacCMS 模板差异等底层细节
3. **职责混乱**：ruleContent 既是"结构采集器"又是"视频流地址采集器"，与内置播放器前置采集器（VideoUrlExtractor）能力重叠
4. **AI 不友好**：大 JS 脚本难以被 AI 理解、生成、验证，AI 处理多线路多集视频订阅源困难
5. **失败降级链路长**：JS 提取 m3u8 失败 → ExoPlayer 收到 HTML 报 3003 错误 → switchToWebViewMode 隐藏 UI → 用户无法切换线路/集数

**用户期望**：
1. 用户切到哪个线路哪一集，再由内置播放器前置采集器采集对应视频地址
2. 新增"多线路选择器"和"多集选择器"规则字段（类似 ruleContent 的 JS 框），勾选后多出 CSS/JSONPath/XPath/JS 写法框
3. 这两个框写根据当前播放页采集线路信息和多集播放页（不是视频地址）
4. 不仅开发者要好使用，**让 AI 也能更方便处理**这种多线路多集视频订阅源
5. 内置播放器前置多种抓取视频播放地址的能力是核心，看改动代码会不会影响

**核心目标**：将多线路多集采集重构为"结构化字段+两阶段按需采集"架构，新增 ruleRoutes 和 ruleEpisodes 字段分离线路采集和集数采集，让开发者/AI 更容易编写，让 VideoUrlExtractor 承担视频流地址解析职责。

## Scope（范围）

### In Scope（本次实现）

- **RssSource 新增 ruleRoutes 和 ruleEpisodes 字段**：支持 CSS/JSONPath/XPath/JS 四种写法
- **数据库迁移**：新增字段的 migration 脚本（覆盖安装兼容）
- **订阅源编辑页 UI 改造**：**仅 type=2（视频源）时显示**"多线路规则"和"多集规则"输入框，其他 type 隐藏
- **Rss.getContent 新增分支**：**仅 type=2 且 ruleRoutes/ruleEpisodes 非空时**使用新字段采集
- **废弃 ruleContent 多线路多集模式**：ruleContent 不再支持返回多线路多集嵌套 JSON，仅支持单集视频 URL（用户明确要求不兼容老版本，老版本主要是单集视频采集）
- **VideoPlay 新增 switchToRoute 方法**：切换线路时重新执行 ruleEpisodes 采集新线路集数（按需采集，替代当前 switchRssRoute 内存缓存模式）
- **VideoUrlExtractor 新增统一按需采集入口** `extractVideoUrlForEpisode`：整合 MacCMS 解析 + DOM 解析 + 网络抓包三层降级
- **VideoPlay.playRssEpisode 调用统一入口**：替代当前 MacCMS 单层解析
- **legado-source-creator SKILL.md 新增多线路多集按需采集标准写法**：明确 ruleRoutes/ruleEpisodes 的使用规范，提供 MacCMS 模板"软通用采集器"示例
- **审查已修改的 4 处源码**：评估配合架构优化后是否可简化
- **MacCMS 模板站点真机回测**：奈飞中文网订阅源用新字段重写后真机验证

### Out of Scope（不在本次实现）

- ❌ **不引入硬编码"通用采集器"**：不在 VideoUrlExtractor 内置 MacCMS 通用 CSS 规则，用 Skill 文档"软通用采集器"替代（维护成本高+AI 不友好+违背声明式规则风格）
- ❌ **不重构 VideoPlay 全局状态管理**：rssStar/rssRecord/rssArticle/rssEpisodes 等保持现状
- ❌ **不修改 VideoFragment UI 交互逻辑**：线路选择器/集数列表 UI 保持现状（仅数据源改变）
- ❌ **不引入新的视频播放引擎**（如 MPV）：本任务不涉及播放器引擎层
- ❌ **不修改 ruleContent JS 执行引擎**（Rhino）：保持现有 JS 执行环境
- ❌ **不修改 BackstageWebView 实现**：复用已有的 extractWithWebView 能力
- ❌ **不引入影视仓字符串编码协议**（`$$$#/`）：Legado 用结构化字段更合适
- ❌ **不扩展 VideoUrlExtractor 用于采集 ruleRoutes/ruleEpisodes**：ruleRoutes/ruleEpisodes 由 Rss.getContent 用 AnalyzeRule 解析（已支持 CSS/JSONPath/XPath/JS），VideoUrlExtractor 专注于视频地址采集

## Approach（方案）

### Selected Approach：结构化字段+两阶段按需采集架构（B 方案修订版）

**核心思路**：新增 ruleRoutes 和 ruleEpisodes 两个结构化字段，分离线路采集和集数采集；ruleContent 回归"旧源兼容"角色，新源优先使用新字段。

**字段设计**：

| 字段 | 类型 | 用途 | 支持写法 |
|------|------|------|---------|
| `ruleRoutes` | String? | 多线路规则：从详情页采集线路列表（线路名） | CSS/JSONPath/XPath/JS |
| `ruleEpisodes` | String? | 多集规则：从详情页采集集数列表（集数标题+播放页 URL） | CSS/JSONPath/XPath/JS |

**执行流程**：

1. **进入播放器**（第一线路第一集）：
   - Rss.getContent 检查 type=2 且 ruleRoutes/ruleEpisodes 是否非空
   - **type=2 且非空**：执行 ruleRoutes 采集线路列表，执行 ruleEpisodes 采集第一线路集数列表
   - **type=2 且为空**：单集模式，执行 ruleContent 采集单个视频 URL（**不再支持多线路多集嵌套 JSON**）
   - **其他 type**：现有逻辑
   - 新模式返回嵌套 JSON：`[{"name":"线路1","episodes":[{"title":"第1集","url":"播放页URL"}]}]`
2. **切换线路**（真正按需采集）：
   - VideoPlay.switchToRoute(routeIndex, player) 被调用
   - **重新执行 ruleEpisodes 采集新线路集数列表**（不是从内存缓存取，替代当前 switchRssRoute 内存模式）
   - CSS 选择器带线路索引，或 JS 接收 routeIndex 参数
   - 更新 VideoFragment 集数列表 UI
3. **切换集数**：
   - VideoPlay.playRssEpisode(player, episode) 被调用
   - 调用 VideoUrlExtractor.extractVideoUrlForEpisode(episode.url, source, rssArticle)
   - 三层降级：MacCMS 解析 → DOM 解析 → 网络抓包拦截
   - 返回真实视频流 URL（m3u8/mp4 等）交给 ExoPlayer

**架构对照（影视仓两阶段架构）**：

| 影视仓阶段 | 职责 | Legado 对应 | 实现方式 |
|-----------|------|------------|---------|
| detailContent | 返回所有线路所有集数 URL 结构 | ruleRoutes + ruleEpisodes | 结构化字段采集（新源）/ ruleContent JS（旧源） |
| playerContent | 按需采集真实视频流 URL | VideoUrlExtractor + playRssEpisode | 统一入口三层降级 |

**与影视仓的区别**：
- 影视仓用字符串编码（`$$$#/`）+ 统一 Spider 接口，适合命令式 Spider
- Legado 用结构化字段（ruleRoutes + ruleEpisodes），适合声明式规则
- 两者本质都是"detailContent 返回结构 + playerContent 按需采集"

**AI 友好性**：
- 结构化字段（CSS/JSONPath/XPath）比大 JS 脚本更容易 AI 生成验证
- AI 可分别生成和验证线路规则和集数规则
- 与现有 ruleArticles/ruleTitle/ruleLink 等字段风格一致
- 95% 视频源可用结构化字段，JS 仅作兜底（参考影视仓研究结论）

### Alternatives Considered（考虑过的替代方案）

| 方案 | 描述 | 优势 | 否决理由 |
|------|------|------|---------|
| **A 方案：不新增字段，复用 ruleContent** | ruleContent JS 只返回播放页 URL，m3u8 由 VideoUrlExtractor 按需采集 | 无需数据库迁移+UI 改造 | 1. ruleContent JS 仍需在一个脚本内处理线路+集数+镜像站<br>2. 大 JS 脚本 AI 不友好（用户明确要求 AI 友好）<br>3. 开发者仍需编写复杂 JS，未真正降低难度 |
| **C 方案：保持现状（ruleContent JS 全量采集）** | ruleContent 继续一次性采集所有线路所有集的 URL（含 m3u8） | 无需改动代码 | 1. 性能差（多集时 N×M 次请求）<br>2. 开发者编写复杂<br>3. AI 不友好<br>4. 与内置播放器前置采集器能力重叠 |
| **D 方案：引入影视仓字符串编码协议** | 在 ruleContent 中用 `$$$#/` 分隔符编码多线路多集 | 与影视仓兼容 | 1. 字符串编码 AI 不友好（需理解分隔符语义）<br>2. 与 Legado 声明式规则风格不一致<br>3. 开发者需手动拼接字符串，易出错 |
| **E 方案：ruleContent 返回纯结构无 URL + 播放器按需采集 URL** | ruleContent 只返回线路名+集数标题，URL 完全由播放器按需采集 | JS 最简单（只采集文本） | 1. 集数 URL 必须由播放器从详情页重新采集，增加复杂度<br>2. 部分站点详情页和播放页不同域（如镜像站），播放器无法推断<br>3. 与"采集播放页 URL"相比性能提升有限 |
| **F 方案：硬编码"通用采集器"** | 在 VideoUrlExtractor 内置 MacCMS 通用 CSS 规则，开箱即用无需配置 | 用户无需配置 ruleRoutes/ruleEpisodes | 1. 维护成本高（新模板出现需更新 App）<br>2. AI 不友好（黑盒无法理解生成）<br>3. 灵活性差（非 MacCMS 模板无法使用）<br>4. 违背 Legado 声明式规则风格 |
| **B 方案修订版：新增 ruleRoutes + ruleEpisodes 字段 + Skill 文档"软通用采集器"**（= 选定方案） | 新增两个结构化字段分离线路采集和集数采集，**废弃 ruleContent 多线路多集模式**（不兼容老版本），Skill 文档提供 MacCMS 模板标准写法作为"软通用采集器" | 1. 结构化字段 AI 友好<br>2. 开发者分离关注点（线路规则/集数规则）<br>3. 与现有字段风格一致<br>4. **真正按需采集**（切换线路重新采集，不是内存缓存）<br>5. 参考影视仓两阶段架构但适配 Legado 声明式风格<br>6. "软通用采集器"比硬编码更灵活可维护 | 1. 数据库迁移成本（已有机制可控）<br>2. UI 改造成本（订阅源编辑页新增两个输入框）<br>3. ruleRoutes/ruleEpisodes 需支持线路索引切换（CSS 选择器或 JS 参数）<br>4. 老版本多线路多集订阅源需迁移到新字段 |

**选定理由**：B 方案修订版在 AI 友好性、开发者体验、职责清晰度、真正按需采集四个维度均优于其他方案。相比 F 方案（硬编码通用采集器），"软通用采集器"（Skill 文档示例）更灵活、可维护、AI 友好。用户明确要求新增字段+AI 友好+废弃老模式，B 方案修订版完全满足。

### Drawbacks（选定方案的已知缺点）

| 缺点 | 接受理由 |
|------|---------|
| 数据库迁移成本（新增 2 个字段） | 项目已有 migration 脚本机制，新增字段迁移简单（ALTER TABLE ADD COLUMN），覆盖安装兼容 |
| 订阅源编辑页 UI 改造成本 | 仅 type=2 时显示新输入框，复用现有 ruleContent 输入框样式，改造成本可控 |
| ruleEpisodes 需支持线路索引切换 | 1. CSS 选择器可用 :nth-child 或带索引的选择器<br>2. JS 写法可接收 routeIndex 参数<br>3. JSONPath/XPath 原生支持索引 |
| 旧订阅源需引导迁移到新字段 | 通过 skill 文档引导 + 真机回测验证，旧源仍能工作（ruleContent 回退） |
| 用户切换集数时按需采集等待时间 | 1. MacCMS 解析（<1s）覆盖 80%+ 场景<br>2. 网络抓包仅在 MacCMS 失败时触发（3-10s）<br>3. 可通过预缓冲下一集缓解 |
| 已修改的 4 处源码仍需保留 | 1. 这些修改解决了 WebView 降级时 UI 隐藏的紧急问题<br>2. 配合架构优化后，ExoPlayer 收到 HTML 的概率降低，但仍可能失败<br>3. 保留作为兜底降级 |

### Prior Art（类似工作参考）

- **影视仓 catvod Spider 接口**（已下载研究）：detailContent 返回所有线路所有集数 URL（字符串编码 `$$$#/`），playerContent 按需采集真实视频流 URL。本方案参考其两阶段架构，但用结构化字段替代字符串编码以适配 Legado 声明式规则风格。
- **研究产物**：`temp/yingshicang-source-research.md`（11节，约380行）+ `temp/yingshicang-research/`（5个源码文件）
- **Legado 现有 VideoUrlExtractor.extractWithWebView**（R5 已实施）：已实现网络抓包拦截能力，本方案复用此能力作为降级兜底
- **Legado 现有 playRssEpisode MacCMS 解析**（已修改）：已实现 MacCMS 播放页按需解析，本方案将其纳入统一入口

## Requirements（需求）

### R1：新增 ruleRoutes 和 ruleEpisodes 字段

- **R1.1** RssSource.kt 新增 `var ruleRoutes: String? = null` 和 `var ruleEpisodes: String? = null` 字段
- **R1.2** 数据库 migration 脚本（migration_99_100，version 99→100）：ALTER TABLE rssSources ADD COLUMN ruleRoutes TEXT; ALTER TABLE rssSources ADD COLUMN ruleEpisodes TEXT;
- **R1.3** 覆盖安装兼容：migration 用 runCatching 包裹，失败不阻塞（参考 database-migration-safety.md）
- **R1.4** 字段支持四种写法：CSS/JSONPath/XPath/JS（与 ruleContent 同等适配，复用 AnalyzeRule）

### R2：订阅源编辑页 UI 改造

- **R2.1** type=2（视频源）时显示"多线路规则"和"多集规则"输入框
- **R2.2** 复用 ruleContent 输入框样式（多行文本+JS高亮）
- **R2.3** 输入框旁提示："为空时回退到 ruleContent（旧源兼容）"
- **R2.4** 编辑页保存时持久化 ruleRoutes/ruleEpisodes 字段

### R3：Rss.getContent 新增分支

- **R3.1** 检查 ruleRoutes/ruleEpisodes 是否非空
- **R3.2** 非空：执行 ruleRoutes 采集线路列表，执行 ruleEpisodes 采集第一线路集数列表，返回嵌套 JSON
- **R3.3** 为空：回退到 ruleContent（旧源兼容）
- **R3.4** ruleEpisodes 执行时支持线路索引参数（CSS :nth-child / JS routeIndex 参数 / JSONPath 索引）。占位符预处理（{routeIndex+1}/{routeIndex}）在 Rss.getEpisodesAwait 完成，不在 AnalyzeRule 内部改（AD-03 决策）。JS 用 putVar 注入 routeIndex

### R4：VideoPlay 新增 switchToRoute 方法

- **R4.1** 新增 `fun switchToRoute(routeIndex: Int, player: GSYBaseVideoPlayer): Boolean`（含 switchToRouteToken 竞态守卫 + source as? RssSource 类型转换）
- **R4.2** 切换线路时重新执行 ruleEpisodes 采集新线路集数列表
- **R4.3** 更新 VideoFragment 集数列表 UI
- **R4.4** 默认播放新线路第一集

### R5：VideoUrlExtractor 新增统一按需采集入口

- **R5.1** 新增 `extractVideoUrlForEpisode(url, source, rssArticle): String` 方法
- **R5.2** 方法内部按顺序执行三层降级：
  1. MacCMS 播放页解析（isMacCmsPlayPage 判断 + extractPlayerAaaaUrl 提取）
  2. DOM 解析（extract 方法，4 种 DOM 解析 + 正则兜底）
  3. 网络抓包拦截（extractWithWebView，BackstageWebView 加载页面拦截 fetch/XHR）
- **R5.3** 每层降级记录 AppLog（命中/失败/降级原因）
- **R5.4** 协程取消异常（CancellationException）必须重新抛出，不记录为失败
- **R5.5** **不破坏现有 VideoUrlExtractor 方法**：extract/extractWithWebView/resolvePlayerPageUrl/isMacCmsPlayPage/extractPlayerAaaaUrl 保持不变，新方法仅调用它们

### R6：playRssEpisode 调用统一入口

- **R6.1** playRssEpisode 调用 `VideoUrlExtractor.extractVideoUrlForEpisode` 替代当前 MacCMS 单层解析
- **R6.2** 保留 Referer 注入逻辑（R5 Header 修复）
- **R6.3** 保留 AppLog.put 日志记录（符合项目规范，禁止 Log.e）
- **R6.4** 保留 Coroutine.async(loadScope, IO) 协程调度和 withContext(Main) 设置 player

### R7：已修改源码审查与保留

- **R7.1** 保留 switchToWebViewMode 修改（leftBottomContainer 可见）：作为 WebView 降级兜底
- **R7.2** 保留 retryExoPlayback 修改（controlsLayer 可见性恢复）：与 switchToWebViewMode 配对
- **R7.3** 保留 getOverlayControls 修改（WebView 模式下不自动隐藏 leftBottomContainer）：与 switchToWebViewMode 配对
- **R7.4** playRssEpisode MacCMS 解析逻辑：被 R5/R6 替代，原代码迁移到 extractVideoUrlForEpisode 内

### R8：Skill 文档规范更新

- **R8.1** 在 SKILL.md 新增"多线路多集按需采集标准写法"章节
- **R8.2** 提供 MacCMS 模板站点标准 ruleRoutes + ruleEpisodes 写法示例（CSS/JSONPath/XPath/JS 四种）
- **R8.3** 明确"优先使用 ruleRoutes+ruleEpisodes，ruleContent 仅作旧源兼容"的规范
- **R8.4** 明确"禁止在 ruleRoutes/ruleEpisodes 内提取 m3u8"的规范
- **R8.5** 提供 AI 生成 ruleRoutes/ruleEpisodes 的指引（结构化字段比 JS 脚本更易生成验证）
- **R8.6** 提供按需采集失败时的排查指引（AppLog 模块过滤）
- **R8.7** 提供"老订阅源迁移指引"小节（判定标准+迁移步骤+回滚方案）

### AD-09 补充：老订阅源迁移指引

**迁移判定标准**：
- 老订阅源 `type==2` 且 `ruleContent` 返回嵌套 JSON（含 episodes 字段）→ 需迁移
- 老订阅源 `type==2` 且 `ruleContent` 返回单 URL/m3u8 直链 → 无需迁移（单集模式仍支持）

**迁移步骤（用户操作）**：
1. 打开订阅源编辑页，将 type 切换为 2（视频源）
2. 在"多线路规则"输入框填写 ruleRoutes（CSS/JSONPath/XPath/JS）
3. 在"多集规则"输入框填写 ruleEpisodes（CSS/JSONPath/XPath/JS）
4. 清空 ruleContent（或保留作为兜底，但新字段优先）
5. 保存并测试

**迁移失败的回滚**：
- 若新字段采集失败，清空 ruleRoutes/ruleEpisodes，恢复 ruleContent 即可回退到单集模式
- parseRssRoutes 保留但仅用于新模式（设计已明确），老模式的 ruleContent 嵌套 JSON 不再被解析

**Skill 文档配套**（R8 已覆盖）：
- SKILL.md 新增"多线路多集按需采集标准写法"章节，提供 MacCMS 模板示例
- 老用户可参照示例迁移

## Scenarios（场景）

### 场景 1：MacCMS 模板站点多线路多集播放（新字段正常流程）

**前置条件**：用户已导入奈飞中文网订阅源（type=2），ruleRoutes+ruleEpisodes 已配置（CSS 写法），ruleContent 为空

**主流程**：
1. 用户从订阅源文章列表点击一部剧，进入视频播放器
2. VideoPlay.startPlay 调用 Rss.getContentAwait
3. getContentAwait 检查 ruleRoutes/ruleEpisodes 非空，执行新分支
4. 执行 ruleRoutes（CSS）采集线路 tab 列表：["线路1","线路2"]
5. 执行 ruleEpisodes（CSS，routeIndex=0）采集第一线路集数列表：[{title:"第1集",url:"/vodplay/1-1-1.html"},...]
6. 返回嵌套 JSON，parseRssRoutes 解析为 List<RssRoute>
7. VideoFragment 显示线路选择器+集数列表
8. 默认播放第 1 线路第 1 集：playRssEpisode 调用 extractVideoUrlForEpisode
9. extractVideoUrlForEpisode 判断 URL 是 MacCMS 播放页，请求 HTML 提取 m3u8（<1s）
10. 返回 m3u8 给 ExoPlayer，开始播放

**后置条件**：用户可流畅切换线路/集数，每次切换等待时间 <2s

### 场景 2：用户切换线路（新字段流程）

**前置条件**：场景 1 后续，用户点击线路选择器切换到线路 2

**主流程**：
1. VideoFragment 调用 VideoPlay.switchToRoute(1, player)
2. switchToRoute 重新执行 ruleEpisodes（CSS，routeIndex=1）采集第二线路集数列表
3. 更新 VideoFragment 集数列表 UI
4. 默认播放第二线路第 1 集：playRssEpisode 调用 extractVideoUrlForEpisode
5. extractVideoUrlForEpisode 提取 m3u8，开始播放

**后置条件**：线路切换零延迟（本地数据）+ 集数按需采集

### 场景 3：MacCMS 解析失败降级到网络抓包（兜底流程）

**前置条件**：用户切换到某集，播放页 player_aaaa 变量缺失

**主流程**：
1. playRssEpisode 调用 extractVideoUrlForEpisode
2. MacCMS 解析失败（extractPlayerAaaaUrl 返回 null）
3. 降级到 DOM 解析（extract），仍未命中
4. 降级到网络抓包（extractWithWebView）：BackstageWebView 加载播放页，拦截 fetch/XHR
5. 网络抓包命中 m3u8（3-10s），返回给 ExoPlayer 播放
6. AppLog 记录降级链路

**后置条件**：用户感知等待时间稍长，但能正常播放

### 场景 4：旧订阅源兼容（ruleContent 返回 m3u8 直链）

**前置条件**：用户导入的旧订阅源 ruleRoutes/ruleEpisodes 为空，ruleContent JS 直接返回 m3u8 URL

**主流程**：
1. Rss.getContentAwait 检查 ruleRoutes/ruleEpisodes 为空，回退到 ruleContent
2. ruleContent JS 执行，返回嵌套 JSON，URL 字段是 m3u8 直链
3. playRssEpisode 调用 extractVideoUrlForEpisode
4. isMacCmsPlayPage 判断为 false（URL 是 m3u8，非 .html）
5. DOM 解析跳过，网络抓包跳过
6. 直接返回原 URL 给 ExoPlayer 播放

**后置条件**：旧源正常工作，无回归

### 场景 5：所有采集层失败（极端场景）

**前置条件**：MacCMS 解析、DOM 解析、网络抓包均失败

**主流程**：
1. extractVideoUrlForEpisode 三层降级全部失败，返回原 URL
2. playRssEpisode 将原 URL 交给 ExoPlayer
3. ExoPlayer 收到 HTML 报 3003 错误
4. 触发 switchToWebViewMode 降级到 WebView 播放
5. leftBottomContainer 保持可见（已修改），用户可切换其他集数

**后置条件**：用户可通过 WebView 播放或切换其他集数

### 场景 6：AI 生成订阅源（AI 友好性验证）

**前置条件**：AI 需要为一个 MacCMS 模板站点生成订阅源

**主流程**：
1. AI 分析站点详情页 HTML 结构
2. AI 生成 ruleRoutes（CSS）：`.module-tab-item[data-dropdown-value]@text`（线路名）
3. AI 生成 ruleEpisodes（CSS）：`.sort-list.tab-list:nth-child({routeIndex+1}) .module-play-list-link`（集数链接）
4. AI 生成 ruleLink（CSS）：`.module-item-title@href`（文章链接）
5. AI 无需编写复杂 JS 处理镜像站/player_aaaa/转义斜杠
6. AI 可分别验证 ruleRoutes 和 ruleEpisodes 是否正确（用 AnalyzeRule 单独测试）

**后置条件**：AI 生成订阅源更简单可靠，无需理解大 JS 脚本

### 场景 7：用户取消播放（协程取消）

**前置条件**：用户在 extractVideoUrlForEpisode 执行过程中退出播放器

**主流程**：
1. VideoPlay.stopLoading() 被调用（内部执行 loadScope.coroutineContext.cancelChildren()，见 VideoPlay.kt#L644-L646）
2. extractWithWebView 抛出 CancellationException
3. extractVideoUrlForEpisode 捕获并重新抛出
4. playRssEpisode 的 onError 不触发

**后置条件**：无错误日志误报

### 场景 8：用户快速切换线路（竞态守卫）

**前置条件**：用户在 switchToRoute 采集期间连续切换线路

**主流程**：
1. 用户点击线路1，switchToRoute(0, player) 发起采集（token=1）
2. 采集未完成时用户点击线路2，switchToRoute(1, player) 发起采集（token=2）
3. 采集未完成时用户点击线路3，switchToRoute(2, player) 发起采集（token=3）
4. 线路1采集完成回调，校验 token=1 != current=3，丢弃结果
5. 线路3采集完成回调，校验 token=3 == current=3，更新 UI 并播放
6. 线路2采集完成回调，校验 token=2 != current=3，丢弃结果

**后置条件**：最终显示线路3 集数列表，无错乱
