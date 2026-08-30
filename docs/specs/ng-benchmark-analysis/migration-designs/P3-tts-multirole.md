# P3 实施级设计 — 多角色听书一期（非 AI 最小闭环）

> 状态：Proposed（待检查点裁决，未审查不实施）｜上游：[design.md](../design.md) AD-06 / 决策表 #9｜证据源：[evidence-pack.md](../evidence-pack.md) F/C 节
> NG 源：`F:\...\legado_NG-main`（快照 3.26.082815）｜本项目 DB v108（`AppDatabase.kt:126`）

## 1 目标与非目标

**目标（一期交付）**
1. TTS 引擎层：SCRIPT 引擎 V2（TtsEngineStore/Setting/ScriptEngineClient/HttpForwarderClient/SpeedPolicy/WavValidation/CacheManager 裁剪迁移），支持引擎导入/启停/音色目录获取/并发限流
2. 五级路由 ReadAloudTtsRouter：character → castRole → dialogue_male/female → dialogue 默认 → narrator → 引擎默认（代码级完整迁移，castRole 一期无生产者）
3. 数据实体最小集：workKey 域键 4+2 表 + DAO；DB 版本衔接 P1 的 v109 规划
4. 手动绑定 UI 最小集：角色管理+音色绑定（嵌入本项目朗读面板/弹框体系）+ 全局旁白/男/女兜底绑定 + 最小引擎管理页
5. HttpReadAloudService 改造：按 segment 路由合成，缓存名含 scenarioMode+voiceId；单音色路径完整回退

**非目标（明确不做）**
- AI 分镜（AiTtsStoryboardHelper ~2800 行）、AI 选角（BookTtsCastingCoordinator 1747 行，仅提取 1 个纯函数）
- Compose 全屏播放器 + 6 动效（NG ReadAloudPlayerActivity 体系）、跨章无缝 NextChapterPlaybackPlan
- 流式合成播放族（TtsStreamingAudio/TtsSoundTouchAudioProcessor/TtsPlayerFactory/ReadAloudAudioPreparation/ReadAloudProgress，合计 ~713 行）与 WebSocket 引擎客户端（TtsWebSocketEngineClient 359 行）
- 场景级音色覆盖（voiceAssignments，依赖分镜数据）与 AI 自动化开关族（BookTtsAutomationConfig/BindingPolicy）

**一期关键新增（NG 无对应物，须评审确认）**：`LocalDialogueSegmenter`（~150 行）——无 AI 分镜时按中文引号对白规则（`“…”`/`"…"` + 前缀说话人提示 `XX道|说|喊`）将段落切分为 DIALOGUE/NARRATION segment；失败兜底=整段 NARRATION（与 NG `segmentsForParagraph` 无分镜路径语义一致，NG `AiTtsStoryboardHelper.kt:620-645`）。不做此物则五级路由中 character/dialogue 各级恒空，多角色退化为"仅旁白换音色"。

## 2 NG 源码证据（文件:行）

| 主题 | 证据 |
|---|---|
| 五级路由主决策 | `help/tts/ReadAloudTtsRouter.kt:36-93`（route()：characterBinding→castRoleBinding→dialogueFallbackBinding→defaultDialogueBinding→narratorBinding，仅 SCRIPT+enabled 引擎可被路由 `:53`）；RouteKind 枚举 `:168-174` |
| 兜底链 | `ReadAloudTtsRouter.kt:95-140` fallbackRoutes：场景覆盖回退→性别兜底→narrator→引擎默认，去重 distinctBy(engine,voice,style) |
| 绑定解析与不可用判定 | `ReadAloudTtsRouter.kt:249-362`（create()：workKey 查库、别名归一索引 `:304-324`、INHERIT 跳过 `:471`、AUTO 无有效音色不可用 `:476-478`）；isBindingUnavailable `:455-466` |
| 全局兜底绑定（AppConfig 键） | `ReadAloudTtsRouter.kt:364-383` resolveGlobalBindings；`help/config/AppConfig.kt:677-810`（readAloudMultiRole/multiRoleTtsEngineId/defaultNarratorTts{Engine,Voice}Id/defaultDialogueMale|FemaleTtsVoiceId） |
| 引擎模型与能力声明 | `help/tts/TtsEngineModels.kt:176-260` TtsEngineSetting（30+ 字段含 voicesUrl/synthesisPath/参数映射）；TtsVoice `:19-36`；能力常量 `:87-95`；`TtsCapabilityRegistry.kt`（57 行）能力注册表 |
| 引擎库（存储/合并/导入/音色目录） | `help/tts/TtsEngineStore.kt:243-301` engines()（内置+saved 合并+默认脚本升级）；saveEngine `:331-360`；ensureVoiceCatalog 并发合并锁 `:501-524`；导入冲突三动作 `:45-130`；脚本元数据解析 `:1286-1303`；系统 TTS 引擎枚举 `:1317-1350`（默认禁用 `:1184-1201`） |
| SCRIPT 引擎客户端 | `help/tts/TtsScriptEngineClient.kt:24-138`（options 缓存 Lru16/fetchVoices/getSynthesisResponse）；audioCacheKey 十元组 `:375-397`（engineId+scriptMD5+optionValues+voice/style/speed/volume/pitch+context+text） |
| 音色转发器 | `help/tts/TtsHttpForwarderClient.kt`（178 行，MultiTTS 本地转发协议 voices 解析） |
| 速度策略 | `help/tts/TtsSpeedPolicy.kt:8-18`（服务端合成速度与本地播放倍速分离：playbackRate=(progress+5)/10） |
| 多角色分段合成 | `service/HttpReadAloudService.kt:973-1010`（prepareSpeakFilesConcurrently：逐 item routeFor→缓存名→并发任务）；:1012-1077（prepareSpeakFileWithFallback：候选路由逐个尝试+roleRouteFailure 告警）；:1404-1473（buildSpeakItemsForContent：无分镜→NARRATION 兜底 `:1459-1467`）；:1535-1560（md5SpeakFileName：scenarioMode=multi|single+audioCacheKey） |
| 段落模型 | `ui/book/character/ChapterStoryboardParser.kt:49-151` StoryboardSegment（speakerName/speakerId/speakerGender/start/end/type）、StoryboardScene `:28-47`、StoryboardSegmentType `:154` |
| 无分镜兜底 | `help/ai/AiTtsStoryboardHelper.kt:620-645` segmentsForParagraph：segments 为空→单条 NARRATION |
| 缓存管理 | `help/tts/ReadAloudCacheManager.kt:47-54`（cacheDir/httpTTS/{md5(workKey)}/）；clearTtsAudioCache 保留 .part `:56-78` |
| 域键模式 | `data/entities/BookCharacterProfile.kt:26-39` workKey=normalize(书名)\nnormalize(作者)（剥"作者:"前缀）；抗 bookUrl 变化 |
| 实体五表 | `BookCharacter.kt:9-54`（workKey 索引+唯一(workKey,name)+FK CASCADE）；`BookTtsCastRole.kt:10-25`（identityState/isRoutableRole `:112-114`）；`BookCharacterTtsBinding.kt:9-24`（复合 PK workKey+targetType+targetId+engineId；TargetType 5 类 `:59-65`；BindingMode AUTO/MANUAL/INHERIT `:67-71`） |
| NG 破坏性先例 | v113 DROP httpTTS（evidence-pack C 节；本项目**不照搬**） |

## 3 本项目对接点现状

| 对接点 | 现状（已核实） | 结论 |
|---|---|---|
| `service/HttpReadAloudService.kt`（633 行） | 单音色：`getSpeakStream` 用 `AnalyzeUrl(httpTts.url, speakText, speakSpeed)`（`:354-361`）+loginCheckJs；缓存名 `MD5(chapterTitle)+MD5(url-\|-\|speechRate-\|-\|content)`（`:445-448`）；错误重试 downloadErrorNo≤5（`:407-440`） | 改造为主战场：多角色分支并存，单音色路径不动 |
| `model/ReadAloud.kt` | 仅 `var httpTTS: HttpTTS?`（`:27`）+upReadAloudClass；**无** engineV2/refreshTtsRoute/updatePreparedTtsEngine | 需增补 engineV2 持有与刷新钩子（参照 NG `TtsEngineStore.kt:332-359` 调用形态） |
| `help/tts/` 包 | **不存在**（Glob 零命中） | 全新目录，无迁移冲突 |
| `data/entities/BookCharacter.kt`（本项目版） | 表 `book_characters`，bookUrl 维度，speechRouteJson/roleLevel/skills 字段（`:11-57`），供 AI 聊天角色卡 | **同名不同构冲突**，裁决见 §10-DD1 |
| 自研 TTS 绑定字段 | `AnalyzeUrl.kt:90-94,402-406`（currentToneID/currentSpeakerName/currentEmotionName/currentEmotionTag/currentSpeechRouteJson 作为 JS bindings）；唯一消费方 `ui/main/ai/AiChatSpeechPlayer.kt:228-232`（AI 聊天语音播报） | **与听书多角色无交集**（不同调用链/不同数据），映射策略=并存不合并，见下表 |
| `AppDatabase.kt:126` | v108，69 实体 44 DAO；本项目 v108 已与 NG 分叉 | 版本链自起重编（§6） |
| 朗读 UI | `ReadAloudDialog.kt`（ComposeDialogFragment，435 行）、`ReadAloudPlayerPanel.kt`（5328 行）、悬浮窗族 | 嵌面板入口+新弹框，不建 NG 式全屏 Activity |
| httpTTS 表 | 本项目有扩展字段在用（evidence-pack C 节） | 保留，不 DROP |

**自研绑定字段 → 新体系映射表**

| 自研字段（AnalyzeUrl bindings，AI 聊天播报链） | 语义 | NG/新体系对应物 | P3 处置 |
|---|---|---|---|
| currentToneID | 音色 ID | Route.voiceId | 不迁移不互通：AiChatSpeechPlayer 继续原样传入 bindings |
| currentSpeakerName | 说话人名 | StoryboardSegment.speakerName | 同上；语义独立（聊天角色名 vs 章节分段说话人） |
| currentEmotionName / currentEmotionTag | 情绪 | TtsSynthesisContext（SCRIPT 引擎 ctx 参数） | 一期听书路由不注入情绪；二期 AI 分镜再对齐 |
| currentSpeechRouteJson | 路由快照 JSON | ReadAloudTtsRouter.Route | 不互通；避免字段名混用（文档级隔离） |
| legacy HttpTTS.url 模板（`{{speakText}}` 等） | 单音色书源 TTS | SCRIPT 引擎 synth 文本参数 | 完整保留为 single 模式路径；多角色开关关闭时零行为变化 |

## 4 文件变更映射表（逐文件+行数）

**A. help/tts/ 新建（自 NG 裁剪迁移，包名不变）**

| 目标文件 | NG 来源 | 迁/裁/不迁 | 预计行数 |
|---|---|---|---|
| TtsEngineModels.kt | TtsEngineModels.kt（456） | 迁；保留 TtsSynthesisContext 字段结构（一期恒 null，避免二期改协议）；裁 streaming 专用注释 | ~430 |
| TtsEngineStore.kt | TtsEngineStore.kt（1284） | 迁；默认脚本资产清单按本项目 assets/defaultData/tts 重建；NEXT_EDGE 首用默认逻辑保留 | ~1200 |
| TtsScriptEngineClient.kt | 同名（759） | 迁 | ~750 |
| TtsHttpForwarderClient.kt | 同名（178） | 迁 | ~178 |
| TtsCapabilityRegistry.kt | 同名（57） | 迁 | ~57 |
| TtsSpeedPolicy.kt | 同名（15） | 迁 | 15 |
| ReadAloudWavValidation.kt | 同名（191） | 迁（prepareSpeakFile 的 WAV 头校验依赖） | ~191 |
| ReadAloudCacheManager.kt | 同名（71） | 裁剪迁移：删 AiTtsStoryboardHelper 依赖与分镜清理段 | ~55 |
| TtsEngineModels 内 TtsVoiceStyle/styleOptions | 同上 | 迁 | 含上 |
| **不迁** | TtsWebSocketEngineClient(359)/TtsStreamingAudio(248)/TtsSoundTouchAudioProcessor(102)/TtsPlayerFactory(38)/ReadAloudAudioPreparation(185)/ReadAloudProgress(140)/StoryboardTtsContext(66) | 一期裁剪（流式+WS 传输），二期按需补 | 0 |
| **不迁** | BookTtsCastingCoordinator(1747)/BookTtsAutomationConfig(37)/BookTtsBindingPolicy(106) | 不迁；仅从 CastingCoordinator 提取 `normalizeIdentityName` 纯函数 | ~20（新 TtsIdentityName.kt） |
| **新增（本项目）** | — | LocalDialogueSegmenter.kt：引号对白正则切分→StoryboardSegment | ~150 |
| **新增（本项目）** | ReadAloudTtsRouter.kt（470） | 迁；裁 scene voiceAssignments 覆盖段（`:55-72`，scene 恒 null）；castRole 各索引/绑定结构保留（数据恒空）；storybook 模型引用改为本项目路径 | ~430 |

**B. 数据实体/DAO（新建，包 data/entities + data/dao）**

| 目标文件 | NG 来源 | 预计行数 |
|---|---|---|
| WorkProfile.kt | BookCharacterProfile（41）整表迁，类/表改名（§10-DD1） | ~45 |
| WorkCharacter.kt | NG BookCharacter（82）迁，类/表改名；裁 imagePrompt/portraitUri（AI 绘图二期） | ~75 |
| WorkTtsCastRole.kt | NG BookTtsCastRole（115）迁，类名 WorkTtsCastRole；表名保留 bookTtsCastRoles | ~110 |
| WorkTtsBinding.kt | NG BookCharacterTtsBinding（114）迁 | ~110 |
| TtsVoiceEntity.kt / TtsEngineRuntimeEntity.kt | NG 同名（各 ~40）迁 | ~80 |
| WorkTtsDao.kt（合并 4 表查询，仿 NG bookCharacterDao）+ TtsVoiceDao/TtsEngineRuntimeDao | NG 对应 DAO | ~180 |
| **不迁** BookTtsCastRoleContribution | NG v111 表（可重建缓存，依赖 AI 分镜） | 0 |

**C. 既有文件改造**

| 文件 | 变更 | 预计 Δ |
|---|---|---|
| service/HttpReadAloudService.kt（633） | 多角色分支：构建 segment 列表（分镜缺省→LocalDialogueSegmenter）、routeFor/fallbackChain（仿 NG `:973-1077`）、md5SpeakFileName 路由版（scenarioMode+voiceId）、路由失败告警 AppLog；单音色路径原样保留 | +250 |
| model/ReadAloud.kt | 增 engineV2 持有/刷新钩子（saveEngine/selectVoice 回调点） | +60 |
| help/config/AppConfig.kt + constant/PreferKey.kt | 6 个多角色偏好键（NG AppConfig.kt:677-810 同名同义） | +45 |
| data/AppDatabase.kt | +6 实体/+3 DAO/version+1/Migration（§6） | +70 |
| ui/book/read/config/ReadAloudDialog.kt（435） | 面板"多角色"入口行+开关（关闭时入口隐藏） | +35 |
| **新增** ui/book/read/config/ReadAloudRoleBindDialog.kt | 角色列表+增删改+每角色绑定（引擎→音色两级选择， genders/别名编辑），嵌 ComposeDialogFragment 体系；参照 NG BookCharacterTtsScreen（1177）交互裁剪为列表型 | ~450 |
| **新增** ui/settings 或 ui/book/read/config/ 下 TtsEngineManageActivity | 引擎列表/导入(文本冲突三动作)/启停/音色目录刷新；参照 NG 引擎管理裁剪 | ~500 |
| assets/defaultData/tts/*.js | 随引擎库引入 2 个内置脚本起步（multitts_forwarder.js/next_edge_proxy.js，自 NG assets 裁剪） | ~2 资产 |

**D. 明确不动的文件**：AnalyzeUrl.kt（bindings 不改）、AiChatSpeechPlayer.kt、HttpTTS 实体/TTSReadAloudService（系统 TTS 路径）、ReadAloudPlayerPanel.kt（5328 行，一期只在 Dialog 加入口，不动 Panel）、paragraph_rules 全族。

## 5 数据流

```mermaid
flowchart TD
    A[章节文本 paragraphs] --> B[getReadAloudText 净化<br/>现有逻辑]
    B --> C{多角色开关<br/>readAloudMultiRole?}
    C -- off --> Z[现有单音色路径<br/>AnalyzeUrl(httpTTS.url) 逐段合成<br/>缓存键不含 voiceId]
    C -- on --> D[LocalDialogueSegmenter<br/>引号对白切分<br/>失败→整段 NARRATION]
    D --> E[List&lt;StoryboardSegment&gt;<br/>type: DIALOGUE/NARRATION<br/>speakerName/start/end]
    E --> F[WorkTtsDao 查询<br/>workKey=norm(书名)\nnorm(作者)]
    F --> G[ReadAloudTtsRouter.route]
    G --> H1[① character 绑定<br/>speakerName→别名索引]
    G --> H2[② castRole 绑定<br/>一期数据恒空]
    G --> H3[③ dialogue_male/female<br/>性别兜底]
    G --> H4[④ dialogue 默认<br/>仅说话段]
    G --> H5[⑤ narrator 绑定<br/>非说话段]
    G --> H6[⑥ 引擎默认音色<br/>activeVoice]
    H1 & H2 & H3 & H4 & H5 & H6 --> I[Route(engine,voiceId,kind)]
    I --> J[primaryRoute 失败→fallbackRoutes<br/>性别兜底→narrator→引擎默认]
    J --> K[TtsScriptEngineClient<br/>synthesize(text,voice,params,ctx)<br/>SCRIPT 引擎 JS 沙箱]
    K --> L[缓存文件<br/>MD5(chapterTitle)+MD5(scenarioMode-\|-\|audioCacheKey)<br/>audioCacheKey 含 engineId+scriptMD5+voiceId+speed...]
    L --> M[播放列表 SpeakItem<br/>逐段 ExoPlayer 顺序播放]
```

## 6 DB 变更设计

- **版本衔接**：P1 已规划 v109（AI 地基）。P3 目标版本 **v110**；实施门禁=以实施时 `AppDatabase.kt` 当前 `version` 为准取 +1（若 P3 先于 P1 落地则顺延为 v109，禁止与 P1 抢占固定号）。禁止复用 NG 108→114 迁移链（两侧 v108 已分叉，evidence-pack C 节）。
- **新增 6 表**（全列显式 `@ColumnInfo(defaultValue)`，NG 模式吸收）：
  1. `workProfiles`：PK workKey；bookName/bookAuthor/latestBookUrl/characterCount/enabled/createdAt/updatedAt
  2. `workCharacters`：autoGenerate id；workKey 索引+唯一(workKey,name)；FK→workProfiles.CASCADE；gender/roleTag/identity/aliasesJson/enabled/sortOrder/source/confidence
  3. `bookTtsCastRoles`：同 NG 结构（identityState/nameType/evidence 族）；一期无生产者，仅结构就位
  4. `characterTtsBindings`：复合 PK (workKey,targetType,targetId,engineId)+唯一索引；voiceId/bindingMode/emotionStyleMapJson/autoConfidence
  5. `ttsVoices`：复合 PK (engineId,id)；name/language/gender/style/tagsJson/sampleText/extraJson/updatedAt
  6. `ttsEngineRuntime`：PK engineId；speed/volume/pitch/updatedAt
- **Migration 要点**：纯 CREATE TABLE/INDEX，无回填无数据迁移（手动绑定从零开始）；FK CASCADE 需迁移内开启 foreign_keys 语义（Room 迁移 SQL 手写建表顺序：父表先于子表）；引擎配置主体存 SharedPreferences（ttsEngineV2SettingsJson，NG 同款），DB 仅音色目录与运行态参数——故引擎层可独立回退，删表无损。
- **httpTTS 表**：保留不动（本项目扩展在用），**明确不执行 NG v113 的 DROP**（破坏性先例，evidence-pack C 节/design.md §2.2-7）。
- **缓存目录**：单音色沿用 `cacheDir/httpTTS/` 平铺；多角色模式新走 `cacheDir/httpTTS/{md5(workKey)}/`（NG ReadAloudCacheManager.kt:47-51），旧键兼容：single 模式缓存名公式不变，避免升级后缓存全失效。

## 7 风险清单

| # | 风险 | 缓解 |
|---|---|---|
| R1 | 与现有单音色朗读兼容回退：开关/引擎异常导致老用户听书不可用 | 开关默认关闭→全部走原路径（§5 C-off 分支）；SCRIPT 路由失败逐级 fallback 至引擎默认音色（Router `:95-140`）再失败才报错；单音色缓存键公式不变 |
| R2 | 系统 TTS（TTSReadAloudService）不参与多角色的降级 | 路由仅接受 SCRIPT 引擎（Router `:53`）；开启多角色但活跃引擎为系统 TTS 时自动降级单音色并在 AppLog 记录降级原因；UI 开关旁提示"多角色仅支持脚本引擎" |
| R3 | 缓存体积膨胀：同段落×多音色×多 scenarioMode 多份缓存 | 键含 voiceId 使命中按角色隔离（NG audioCacheKey 十元组）；接 workKey 子目录按书清理（CacheManager 裁剪版）+复用本项目 JsExtensions clearTtsCache 入口；文档标注"多角色模式缓存≈单音色×绑定音色数" |
| R4 | 与面板 UI 交互冲突：ReadAloudDialog/悬浮窗状态与多角色切换竞态 | 开关切换走 ReadAloud.upReadAloudClass 现有重建路径；绑定弹框仅在服务空闲（BaseReadAloudService.isRun=false）时允许改绑定；Panel 一期零改动 |
| R5 | LocalDialogueSegmenter 切分质量：误判 speakerName→错音色 | 仅引号内文本标记 DIALOGUE，说话人名匹配失败→按性别兜底→dialogue 默认（五级链天然兜底）；归一化匹配复用 normalizeIdentityName；一期不做置信度 |
| R6 | 引擎脚本沙箱面：SCRIPT 引擎 evalJS 与书源同权限 | TtsEngineSetting 实现 BaseSource（NG 同款，TtsEngineModels.kt:198-212）→ 自动继承本项目 P0 落地的文件沙箱/类导入灰度/弹窗拦截（design.md 决策表 #1/#2/#4），P3 前置依赖=P0 已合入 |
| R7 | BookCharacter 同名冲突漏改引用 | 新实体 Work* 前缀+新表名（§10-DD1），本项目 book_characters 零改动；编译期无同名类 |

## 8 验证方案（ai_tests 体系，`ai_tests\venv\Scripts\python.exe`）

- **L1（编译+静态）**：`quick_build_install.py` 编译测试包 `io.legado.miss.app.debug`；Grep 确认无 `android.util.Log.d/e` 残留、updateLog 已按 version-delivery-sync 更新。
- **L2（真机核心路径，脚本思路）**：
  1. 导入 2 个内置 SCRIPT 引擎（multitts 转发器+自定义 http 引擎）→ 引擎列表出现且音色目录拉取成功（ttsVoices 行数>0）
  2. 建角色（男/女各 1，含别名）→ 绑定不同音色 → 开启多角色 → 播放含对白章节
  3. 断言缓存目录出现 `httpTTS/{md5(workKey)}/` 且文件名互异（不同角色同段落多缓存=路由生效）；logcat 过滤 AppLog 关键词断言 RouteKind 分布（旁白/对白兜底计数）
  4. 关闭开关回归：播放同章节 → 缓存命中旧键公式、无 workKey 子目录（回退无副作用）
  5. 删除绑定中音色 → 播放不中断（fallbackRoutes 链路）+ AppLog 有"改用…继续朗读"降级记录
- **L3（场景脚本，`run_e2e.py --tc` 扩展用例）**：多音色长章连续听书 30 分钟无崩溃/无连续 5 次下载错误暂停；切书后 workKey 隔离生效（不同书不互读绑定）；覆盖安装升级路径 v10x→v110 数据无损（老表行数不变）。

## 9 工作量估算

| 阶段 | 内容 | 人日 |
|---|---|---|
| D1 引擎层 | help/tts 8 文件迁移裁剪+内置资产+BaseSource 适配 | 3 |
| D2 数据层 | 6 实体+3 DAO+Migration+AppDatabase 接线 | 1 |
| D3 路由 | ReadAloudTtsRouter+TtsIdentityName+StoryboardSegment 模型 | 1.5 |
| D4 分段器 | LocalDialogueSegmenter+单测（JVM 仿真正则用例） | 1 |
| D5 服务改造 | HttpReadAloudService 多角色分支+ReadAloud/AppConfig 钩子 | 2 |
| D6 UI | RoleBindDialog+EngineManageActivity+入口接线 | 3 |
| D7 测试 | L1/L2 脚本+真机回归+updateLog/文档同步 | 2.5 |
| **合计** | | **14** |

## 10 设计决策记录

- **DD1 BookCharacter 同名冲突裁决**：本项目 `BookCharacter`（book_characters，AI 聊天角色卡）**保留不动**；NG 角色体系迁入时类名/表名改 `Work*` 前缀（WorkProfile/WorkCharacter/WorkTtsCastRole/WorkTtsBinding），workKey 域键语义原样保留。理由：两侧维度不同（bookUrl vs workKey）、生命周期不同（聊天卡 vs 听书演播），合并会互相污染字段；Work* 前缀契合域键模式且规避 Ng* 前缀的 fork 定位问题（AD-06 留白在此落定）。
- **DD2 castRole 表"结构就位、无生产者"**：五级路由代码完整迁移，但 castRole 数据一期恒空（生产者是 AI 分镜，二期引入）。一期不删路由级，避免二期改 Router 结构。
- **DD3 无 AI 分解器的本地兜底为新增组件**：NG 多角色在无分镜时退化为纯旁白（AiTtsStoryboardHelper.kt:633-645），手动绑定将无实际意义；P3 新增 LocalDialogueSegmenter（§1），作为二期 AI 分镜的可替换前置层（接口与 StoryboardSegment 对齐，AI 数据到达时直接覆盖）。
- **DD4 流式与 WS 引擎一期裁剪**：路由正确性不依赖流式（文件缓存+播放列表模式足够）；TtsStreamingAudio 族 713 行+WS 359 行延后，降低一期回归面。
- **DD5 httpTTS 表不照搬 NG v113 DROP**：本项目 HttpTTS 有扩展字段在用且单音色路径长期共存；多角色开关是增量而非替换。
- **DD6 自研绑定字段两体系并存**：AiChatSpeechPlayer 的 current* bindings 与听书路由无调用链交集（§3 映射表），一期不合并不互通；二期如需统一，以 TtsSynthesisContext 为对齐点。
- **DD7 引擎配置存 SharedPreferences**：沿 NG（ttsEngineV2SettingsJson），DB 只存音色目录/运行态；好处=迁移脚本零数据搬迁+引擎层可独立回退。代价=导入/导出书架备份需注意偏好键纳入（复用现有 backup 键清单机制）。
- **DD8 默认引擎资产最小起步**：仅随包内置 multitts_forwarder 与 next_edge_proxy 两脚本（NG 有 7 个），其余走导入；避免一次引入大量第三方 endpoint 默认值（隐私与维护面）。
