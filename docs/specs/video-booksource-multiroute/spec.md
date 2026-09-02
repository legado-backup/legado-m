# spec.md — video-booksource-multiroute

## Intent

视频订阅源的多线路多集字段（ruleRoutes/ruleEpisodes）本质是从书源"目录/正文"字段简化扩展而来。本功能在**不修改书源现有字段解析逻辑**的前提下，让内置视频播放器兼容"视频书源"：建立 ruleRoutes/ruleEpisodes 到书源字段体系的映射，使视频书源获得与视频订阅源一致的播放体验（多线路切换/集数选择/直链优先/嗅探兜底），并覆盖"正文打开视频播放器先嗅探"的场景。

## Scope

### In Scope
- `bookSourceType=video`（常量值 **4**，[BookSourceType.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/constant/BookSourceType.kt)——禁止硬编码数字，2 是 image）书源的字段映射与解析分支（增量，不影响文本书源）
- 目录（ruleToc）到"卷=线路、章=集数"结构的自动规范化（App 侧 routes 管线复用）
- 播放管线（VideoPlay）对书源多线路多集的支持（多线路切换/集数选择/换源记忆）
- 视频书源正文（ruleContent）视频地址解析：直链优先 → 三层嗅探兜底（复用既有链）
- 阅读器正文页（type=video 书源）视频播放入口
- 搜索/发现结果的视频书源识别（既有 isVideoResult 机制对接）

### Out of Scope
- 修改 ruleToc/ruleContent 等**现有字段**的解析逻辑或语义（文本书源零影响）
- 视频订阅源（RssSource）管线的任何行为变更
- 音频书源（bookSourceType=1）的播放适配
- 漫画/图片类书源
- Web 端（Vue）播放器改动

## Approach

### Selected Approach

**字段映射核心答案**（对应用户问题"映射到书源的哪两个字段"）：

| 订阅源字段 | 书源承载字段 | 映射说明 |
|-----------|-------------|---------|
| ruleEpisodes（集数） | **ruleToc**（目录规则） | 目录 = 集数列表；type=video 时 MacCMS 响应经数据规范化层注入卷章结构（chapters 扁平卷行+章行），作者可零规则（L0）或四条 JSONPath 显式表达（L1） |
| 每集视频地址 | **ruleContent**（正文规则） | 正文 = 视频地址（m3u8 直出）；为空或为播放页 URL 时走三层嗅探链（既有能力）；五类解析任选 |
| ruleRoutes（多线路） | **目录卷结构（isVolume/卷=线路）** | 不新增书源字段（用户裁决 2026-09-02：ruleRoutes/ruleEpisodes 不进 BookSource）；线路由目录卷行表达 |

**解析手段分级标准（用户裁决 2026-09-02，JS 为最后手段）**：

| 级别 | 写法 | 适用场景 |
|------|------|---------|
| L0 零规则 | 源侧什么都不写，App 侧检测规范化结构直接产卷章 | MacCMS JSON 资源站 |
| L1 纯 JSONPath（推荐标准） | `chapterList=$.chapters[*]` / `chapterName=$.title` / `chapterUrl=$.url` / `isVolume=$.isVolume` | MacCMS JSON，显式可控 |
| L2 CSS/XPath/正则 | 目录选择器 + isVolume 判线路行；正文选择器取 iframe/source/a | HTML 视频站 |
| L3 JS（仅兼容） | archive 同款 @js 写法 | 兼容存量（底线非推荐） |

**播放链路**（type=video 书源）：
搜索/发现 → isVideoResult 识别 → VideoPlayerActivity → 目录解析（routes 规范化：卷=线路、章=集数）→ 选集 → WebBook.getContent（正文=视频地址）→ 直链优先 → 空/播放页 URL 走三层嗅探 → 播放。

**实现要点**：
- `VideoPlay` 现有 `source as? RssSource` 强转点抽象为多线路能力接口（如 `SourceMultiRoute`），`RssSource` 与 `BookSource(type=video)` 双实现，管线逻辑复用
- 目录解析：type=video 书源的 `getChapterList` 分支调用订阅源同款 `normalizeMacCmsBody` + routes 展开（卷章结构），ruleToc.chapterList 仅作为非 MacCMS 视频源的通用兜底
- 正文入口：type=video 书源的正文页菜单新增"播放"动作（正文为 URL 时自动嗅探直达）

**解析手段兼容硬要求（用户裁决 2026-09-02）**：
- **五类解析全支持**（CSS/JSONPath/XPath/正则/JS），禁止仅 JS 路线——见上方解析分级标准 L0-L3；规范化层注入双结构（routes + chapters）是 L1 纯 JSONPath 写法的数据基础，解析逻辑零修改
- **archive 视频书源回归**：用户提供的 archive 视频书源（@js ruleToc 展开卷章 + @js ruleContent 提直链）导入本项目必须可用（同源 JS 引擎 + 既有解析路径透明），列入真机验证硬用例：导入 → 目录卷章 → 切线路/选集 → 播放
- **不新增书源字段**：ruleRoutes/ruleEpisodes 不进入 BookSource（用户裁决），映射完全落在 ruleToc/ruleContent 两个既有字段上

### Alternatives Considered

| 替代方案 | 否决理由 |
|---------|---------|
| 直接对 MacCMS 原始数据用 TocRule 扁平语法展开（chapterList/isVolume 直接消费 vod_play_url） | 原始扁平串 `线路$$$集1#集2` 无卷章结构，纯 JSONPath 无法切分分组（archive 用 JS 的根因）；已由 AD-05 规范化层解决——注入 chapters 扁平卷章结构后 TocRule 扁平语法即可表达 |
| JS 目录（`<js>` 返回卷章 JSON） | 违背"尽可能不使用 JS"的硬目标；Rhino 性能与兼容负担 |
| 两级跳交互（目录=线路列表、正文=集数列表页、再播放） | 无需扩展即可实现，但交互多一层（线路→集数→播放三级），体验显著差于订阅源（线路+集数同屏）；且正文语义被挪用为"集数列表页"，嗅探兜底语义被破坏 |
| 修改 TocRule 增加嵌套字段（如 tocGroup） | 直接违反约束"不修改书源现有解析字段规则"——字段结构变更影响 Parcelable/Gson/编辑器/导出兼容面 |
| 把订阅源 ruleRoutes/ruleEpisodes 增量字段搬进 BookSource | **用户否决（2026-09-02）**：不想要订阅源新增字段进视频书源，映射必须落在 ruleToc/ruleContent 两个既有字段；且违背"更高标准复用既有字段体系"的目标 |
| 播放管线不复用，为书源另写播放逻辑 | 大量重复代码（direct-route-first/按需采集/嗅探链/错误处理），且行为漂移风险高 |

### Drawbacks

- 规范化层注入 chapters 为 App 约定键名（非字段协议变更）：需文档化承诺并防与源数据原生键冲突（注入前检测）——接受：与订阅源 routes 注入同构，已真机验证
- type=video 分支在目录解析处产生条件分叉：文本书源路径需回归保证——接受：以 bookSourceType==video 严格隔离分支 + 文本书源回归用例
- 正文页新增播放入口对正文页 UI 有轻微侵入——接受：仅 type=video 书源显示

### Prior Art

- 订阅源多线路多集：`docs/specs/rss-cms-multiroute-nojs/`（normalizeMacCmsBody + routes 规范化 + {routeIndex} 占位符 + direct-route-first，已真机验证）
- 书源播放管线现状：`VideoPlay.startPlay` book 分支（WebBook.getContent → MPD/URL → extractVideoUrlForEpisode 三层嗅探，卷=线路模型已有注释说明）
- 视频搜索识别：`SearchBookOpenHelper.isVideoResult/openVideo`（bookSourceType==video → 直进播放器）

## Requirements

- **R1**: `bookSourceType==video`（常量值 4，禁止硬编码数字）书源的目录解析输出"卷=线路、章=集数"结构；MacCMS 源由 App 侧 routes 规范化自动完成，源侧零规则成本
- **R2**: 播放管线对视频书源支持多线路切换与集数选择；能力与视频订阅源一致，**载体经 AD-06 详情抽屉实现**（REQ-17/18 悬浮选择器数据硬绑 rssRoutes/rssEpisodes，书源模式天然隐藏，不强行复用载体）
- **R3**: 正文（ruleContent）解析结果为直链（.m3u8/.mp4 等）时直接播放；为播放页 URL 或空时走三层嗅探链（既有）。**L0/L1 直链通路约定：L1 四条 JSONPath 源的 ruleContent 必须留空**——既有机制（[WebBook.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/model/webBook/WebBook.kt) 正文规则空→返回 chapter.url，即集数直链）天然完成"正文=视频地址"映射，直链直出；播放页 URL 场景由嗅探兜底
- **R4**: 兜底兼容入口：阅读器正文页对 type=video 书源提供"播放"动作（注：书源视频经搜索/书架/目录均直达播放器，阅读器几乎不可达——本入口为兜底兼容，非主路径）
- **R5**: 现有文本书源（type=0/1）的目录/正文解析行为零变化（回归保证）
- **R6**: 五类解析全支持（CSS/JSONPath/XPath/正则/JS），JS 为最后手段；解析分级 L0 零规则 / L1 四条 JSONPath（`$.chapters[*]`）/ L2 CSS·XPath·正则 / L3 JS 兼容存量
- **R7**: 多线路映射遵循既有卷章模型（卷=线路），播放进度/换线路记忆复用 Book 的卷章索引
- **R8**: 不新增书源字段（ruleRoutes/ruleEpisodes 不进 BookSource），映射完全落在 ruleToc/ruleContent 既有字段（用户裁决 2026-09-02）
- **R9**: 抖音模式详情面板：书源模式提供详情底部抽屉（封面/书名/作者/简介 + 线路 Tab + 集数列表）；订阅源模式**不注入**该入口（无详情数据，UI 零退化），线路/集数悬浮选择器（REQ-17/18）零改动
- **R10**: archive 视频书源（@js）真机回归硬用例：导入→卷章→切线路/选集→播放（与零 JS L1 改造版双源对照）

## Scenarios

### Scenario 1: MacCMS 视频书源完整播放
给定 type=video（=4）书源（bookSourceUrl 指向 `/api.php/provide/vod`，无 JS），
当用户搜索影片 → 视频识别 → 进播放器，
则目录自动呈现"卷=线路（ffm3u8/liangzi）、章=集数"，选集后直链起播（direct-route-first），share 分享页线路可切换。

### Scenario 2: 正文嗅探兜底
给定书源正文（ruleContent）解析结果为播放页 URL（非直链）或空，
当该集进入播放，
则走三层嗅探链（MacCMS 播放页→DOM→网络抓包），成功后播放；失败给统一错误提示。

### Scenario 3: 正文页播放入口
给定 type=video 书源打开正文（阅读器），
当用户点击正文菜单"播放"（或正文为视频 URL 时自动提示），
则唤起内置播放器并先嗅探再播放。

### Scenario 4: 文本书源回归
给定既有 type=0 文本书源，
当正常阅读（目录/正文/换源），
则行为与改造前完全一致（零变化）。

### Scenario 5: 书源详情抽屉（AD-06）
给定 type=video 书源进入播放器（书名/作者/简介/封面数据齐备），
当用户点击左下角"详情"入口，
则弹出底部抽屉展示详情 + 线路 Tab + 集数列表，抽屉内选集/切线路与悬浮选择器动作一致。

### Scenario 6: 订阅源 UI 零退化
给定视频订阅源（无简介/信息字段）进入播放器，
当播放/切线路/选集，
则不出现详情入口，悬浮线路/集数选择器行为与改造前完全一致。
