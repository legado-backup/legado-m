# P1 实施级设计 — AI 地基迁移（供应商抽象 + 上下文压缩 + DB v109）

> 依据 [design.md](../design.md) AD-04；证据源 [evidence-pack.md](../evidence-pack.md) A/C/E 节。
> NG 根：`F:\myself\github\WeAgentChat\temp\legado_NG_src\legado_NG-main`；本项目 DB 基线 v108。

## 1 目标与非目标

**目标**
1. 供应商抽象层落地：`AiProvider` 接口 + 3 协议实现（OpenAI 兼容/Gemini/Claude）+ `AiManager` 路由 + 模型能力富化（Registry）+ 12 家预设，按本项目架构重组为 `help/ai/provider/` 子包。
2. 上下文压缩核心：六桶 token 估算 + usage 实测校准 + 触发策略 + 兜底裁剪，从 NG 697 行单文件拆为 4 个 ≤300 行类，沉入 `help/ai/compress/`。
3. DB v108→v109：新增 AI 会话/消息/压缩记录最小表集（全列显式 defaultValue，手动 Migration）。
4. 配置 UI 最小增量：现有供应商管理页叠加协议类型/测试连接/预设导入，**不新建页面**。

**非目标**（P1 明确不做）：完整聊天 UI 与流式聊天迁移（现有 `AiChatService.chatStream` 通道保持不动）；MCP 服务（P2）；Agent/Skill/ModeEntryContext 同步逻辑（P4）；余额查询 AiBalanceProvider（裁剪）；替换既有 `AiContextManager`（P1 并存观察）；密钥 Keystore 加密改造（记债）。

## 2 NG 源码证据（文件:行，均相对 `help/ai/`，另注者除外）

| 证据 | 位置 |
|------|------|
| `AiProvider` 接口（listModels/generateText）+`AiTextParams`（temperature/maxTokens/thinking/effort/jsonResponse）+`AiTextResult`（content/reasoning/finishReason/usage 三元/rawPreview） | AiProvider.kt:3-33 |
| `AiProviderSetting` 26 字段全 `alternate` 短 key 持久化；超参：chatCompletionsPath/modelsUrl/supportsThinking/effortParam/reasoningOutputField/balanceUrl 等 | AiProviderSetting.kt:8-61 |
| `AiProviderType` 三协议枚举（openai/google/claude，from() 兜底 OPENAI） | AiProviderSetting.kt:63-78 |
| 12 家预设（OpenAI/Claude/Gemini/DeepSeek/硅基流动/OpenRouter/小米 MiMo/商汤/百炼/火山/月之暗面/智谱；商汤含 effortParam+reasoningOutputField 踩坑参数） | AiDefaultProviders.kt:5-129 |
| `AiManager` 路由：providerFor() 三分支；generateText 校验 enabled/model 非空；testConnection 用 system"Reply OK"探针（区分 reasoning-only 与空 content） | AiManager.kt:9-20,50-77,84-90 |
| 存储层：PreferKey JSON 持久化（aiProvidersJson/aiActiveProviderId）；mergeWithDefaults 按缺省补齐；migrateLegacyConfig 旧单供应商配置迁移；normalize/sanitize 容错 | AiProviderStore.kt:16-28,71-76,114-199,227-258 |
| 模型能力富化：token 匹配 DSL（~989 行数据表）+capabilities()/enrich()（推断能力与声明能力并集合并） | AiModelRegistry.kt:773-809；AiModelDsl.kt(205 行) |
| OpenAI 兼容实现：listModels 端点候选重试（EndpointResolver）；generateText 组包 stream=false（**非流式**），reasoningOutputField 可配 | OpenAiCompatibleProvider.kt:13-37,40-106（stream=false 见 :64） |
| Gemini：`x-goog-api-key` 头 + `{base}/models/{model}:generateContent`；models 解析按 supportedGenerationMethods 含 generateContent 过滤 | GoogleAiProvider.kt:17-26,77-79 |
| Claude：`x-api-key` + `anthropic-version: 2023-06-01` + `{base}/messages`；listModels 双头回退（x-api-key 失败转 Bearer） | ClaudeAiProvider.kt:13-22,66-69 |
| token 估算：逐字符加权（CJK 1.0 / 空白 0.15 / 其他 0.25，向上取整，最少 1）+每消息 12 token 开销 | AiChatContextManager.kt:389-405,608 |
| 六桶 breakdown：systemPrompt/tool/skill/appContext/conversation/protocol 分桶累计 | AiChatContextManager.kt:315-387,654-665 |
| 实测校准：calibrationFromHistory 以 provider usage.promptTokens 为锚，锚定已发 payload，仅估算增量（AiChatTokenCalibration.estimate） | AiChatContextManager.kt:226-254,680-715 |
| 触发策略：shouldCompact=thresholdPercent>0 且 estimated≥threshold；compactIfNeeded 三条件（官方 usage 达阈值/预测达硬窗口 90% 守卫/force） | AiChatContextManager.kt:407-414；AiChatClient.kt:845-865 |
| 压缩重建：buildCompactedHistory = 全部 system + summary(revision 递增) + 预算内 recent users（20k token 或窗口 20%）+ pinned artifacts | AiChatContextManager.kt:22,459-495 |
| 兜底裁剪：trimOldestCompactionHistoryUnit（按 user 消息单元成组删）/shrinkLargestCompactionMessage（最长消息对半截断+省略标记），用于压缩摘要请求自身超窗时循环收敛 | AiChatContextManager.kt:256-313；AiChatClient.kt:972-974 |
| 压缩摘要生成：独立 system prompt（assets/ai/context_compaction.md 12 行）+temperature 0+禁 thinking+非流式；超窗循环裁剪直至成功或抛"窗口不足" | AiChatClient.kt:915-987,989-995 |
| 配置项：上下文窗口 7 档（32k~2M，默认 1M）、阈值 50~95% 步进 5（0=关，默认 90）；压缩模型可独立指定（缺省跟随助手模型，仅支持 OpenAI 兼容） | AiConfig.kt:32-43,153-190,372-380；AiChatClient.kt:923 |
| 数据类：AiModel(id/type/modalities/abilities) / AiMessage(SYSTEM/USER/ASSISTANT) | AiModel.kt:5-70；AiMessage.kt:3-12 |

## 3 本项目对接点现状（已 Read 确认）

**3.1 数据库**：`data/AppDatabase.kt:126` version=108，exportSchema=true；:195-207 注释惯例——88 之后一律手动 Migration（最近例：migration_105_106 新增 19 张 AI 表），AutoMigration 链止于 88→89。迁移规范 `docs/project-rules/database-migration-safety.md`：R1 改 @DatabaseView 必须 DROP+CREATE；R2 migration 操作必须 kotlin.runCatching 包裹+AppLog；R6 Room schema 校验是运行时的，须真机验证。

**3.2 既有 ai 包（35 文件）实体盘点**（`data/entities/`，均属本项目 v105 独有表）：
| 实体/设施 | 语义 | P1 判定 |
|---|---|---|
| AiAgentSession/AiAgentJob/AiAgentTrace | Agent 运行状态（scope/status/goal/contextJson），**非聊天会话表** | 不复用，v109 新表独立定位 |
| AiMemoryItem/AiMemoryFragment/AiMemoryFts | 长期记忆+FTS | 不动 |
| AiGeneratedImage/AiImageGroup、AiReadAloudRoleCache/AiReadAloudUsageRecord | 图像/听书 | 不动 |
| `help/ai/AiMcpClient.kt` | MCP 客户端方向 | 与供应商层无冲突 |
| `help/ai/AiContextManager.kt:7-12` | 现聊天压缩（CHARS_PER_TOKEN=3 粗估、90% 触发、最近 10 条保留） | P1 不动，语义差异记 §7 |
| `help/ai/AiChatService.kt` | OpenAI 兼容直连：chat:96/fetchModels:243/chatStream:275/aiChatHttpClient:496/requestCompletionStream:622-648，走 `okHttpClient.newCallResponse{}` | P1 不动；新调用一律走 AiManager |

**3.3 配置设施**：`ui/main/ai/AiConfigModels.kt:7-25` 现有 `AiProviderConfig`（仅 7 字段 id/name/baseUrl/apiKey/headers/apiMode/promptCache，**单协议 OpenAI 兼容**，apiMode 区分 chat_completions/responses）+`AiModelConfig`（场景模型绑定）。存储：`AppConfig.kt:541` aiProviderList → PreferKey `aiProviderList`（:1386-1454 读写+normalize+legacy 迁移）；PreferKey.kt:424-434 另有 aiCurrentProviderId/aiModelConfigList 等。**管理页已存在**：`ui/config/AiProviderManageActivity.kt:95-140`（列表/删除）、`AiProviderEditActivity.kt:239-271`（编辑）、`AiConfigFragment.kt:217-223`（入口汇总）。

**3.4 结论**：供应商配置"UI+存储"已在、但"协议抽象/超参/能力富化/预设"全缺；P1=补地基并增量融合，非平地起楼。

## 4 文件变更映射表

**新增 `help/ai/provider/`**（NG 平铺 → 本项目子包；风格改造：AppLog/kotlin.runCatching/Coroutine 链式）：
| 文件 | 来源 | 目标行数 | 说明 |
|---|---|---|---|
| AiProvider.kt | NG AiProvider.kt:3-33 | ~60 | 接口+AiTextParams/AiTextResult 原样 |
| AiProviderSetting.kt | NG 同名 | ~110 | 26 字段+AiProviderType |
| AiProviderStore.kt | NG AiProviderStore.kt | ~260 | **融合改造**：底层读写改走 `AppConfig.aiProviderList` 同一 PreferKey；mergeWithDefaults/sanitize/normalize 照搬 |
| AiDefaultProviders.kt | NG 同名:5-129 | ~140 | 12 家预设，定位为"导入模板" |
| AiManager.kt | NG 同名:3-91 | ~150 | generateText/listModels/fetchAndSaveModels/testConnection |
| OpenAiCompatibleProvider.kt | NG 同名 | ~180 | 含 EndpointResolver 候选重试 |
| GoogleAiProvider.kt / ClaudeAiProvider.kt | NG 同名 | ~160/~180 | 协议差异见 §2 |
| AiProviderUtils.kt | NG 同名(104 行) | ~110 | trimEndSlash/ensureStartSlash/executeJson 扩展；HTTP 通道改本项目 `okHttpClient.newCallResponse` |
| AiModel.kt / AiModelDsl.kt / AiModelEndpointResolver.kt | NG 同名 | ~70/~205/~60 | 原样 |
| AiModelRegistry.kt | NG 同名(~989 行) | 拆 2 文件 ~1100 | Registry 定义 + RegistryEnrich(enrich/capabilities 合并逻辑) |

**新增 `help/ai/compress/`**（拆 NG 697 行单文件+AiChatClient 调度）：
| 文件 | 来源 | 目标行数 | 说明 |
|---|---|---|---|
| AiCompactionModels.kt | AiChatContextManager.kt:654-753 | ~150 | Breakdown/Usage/Calibration/Event/Record；Snapshot 类裁掉 Skill 字段 |
| AiTokenEstimator.kt | 同上:389-405,315-387 | ~200 | 加权估算+六桶 breakdown+MESSAGE_OVERHEAD |
| AiContextCompactor.kt | 同上:200-254,407-414,459-533 | ~280 | usage/shouldCompact/calibrationFromHistory/buildCompactedHistory/revision |
| AiCompactionScheduler.kt | AiChatClient.kt:845-995 | ~230 | compactIfNeeded/createCompactionSummary/isContextWindowExceeded/兜底裁剪循环；摘要生成统一走 AiManager（NG 限 OpenAI 兼容的 :923 约束保留） |

**新增 assets/ai/context_compaction.md**：NG 12 行原样拷贝。**修改 ui/main/ai/AiConfigModels.kt**：AiProviderConfig 增量扩展 protocol/超参/模型缓存字段（全默认值，旧 JSON 兼容）。**修改 ui/config/AiProviderManageActivity.kt + AiProviderEditActivity.kt**：协议下拉/测试连接/预设导入按钮（最小增量，风格随现管理页）。**修改 PreferKey.kt**：仅当需要时增 key（预计 0-2 个）。

## 5 数据流（mermaid）

```mermaid
sequenceDiagram
    participant C as 调用方(场景服务/L3测试)
    participant M as AiManager(路由)
    participant S as AiCompactionScheduler
    participant P as AiProvider(3协议实现)
    participant H as okHttpClient(HTTP)
    C->>S: submitTurn(messages, toolDefs, calibration?)
    S->>S: Estimator.breakdown 六桶 + usage(校准)
    alt estimated ≥ threshold(默认90%) 或 ≥ 硬窗口90%
        S->>M: generateText(压缩prompt+历史, temp=0)
        M->>P: providerFor(setting).generateText()
        P->>H: POST {base}{path} + 鉴权头(stream=false)
        H-->>P: JSON 一次性返回(非流式)
        P-->>M: AiTextResult(含 usage)
        S->>S: 超窗→兜底裁剪循环; 成功→buildCompactedHistory
    end
    C->>M: generateText(业务messages, params, providerId, modelId)
    M->>P: 校验 enabled/model → providerFor()
    P->>H: POST(OpenAI:Bearer / Gemini:x-goog-api-key / Claude:x-api-key)
    H-->>P: JSON(choices/usage)
    P-->>M: AiTextResult → calibrationFromHistory 更新校准锚
    M-->>C: AiTextResult
```
注：NG 供应商层为**一次性 JSON 返回**（OpenAiCompatibleProvider.kt:64 stream=false）；本项目流式能力在 AiChatService.chatStream 保留，二者 P1 并行不打通（P2+ 议题）。

## 6 DB v109 变更设计

**新增 3 表**（NG AiChatConversation/AiChatMessageNode 语义吸收 + 压缩审计；全部 @ColumnInfo(defaultValue) 显式全覆盖，吸收 NG 数据层亮点）：
1. `ai_chat_sessions`：sessionId(PK TEXT)/title/providerId/modelId/contextWindowTokens(int 0)/compactionEnabled(int 0)/status/createdAt/updatedAt(int 0)；索引 (updatedAt)。
2. `ai_chat_messages`：id(PK TEXT)/sessionId/parentId(TEXT ""，预留消息树分支)/role/content/reasoning/toolCallsJson/promptTokens/completionTokens/totalTokens(int 0)/compactionRevision(int 0)/createdAt/updatedAt；索引 (sessionId,createdAt)、(parentId)。
3. `ai_compaction_records`：id(PK TEXT)/sessionId/stage(TEXT "PRE_TURN")/beforeTokens/afterTokens/revision/summaryPromptTokens/summaryCompletionTokens(int 0)/createdAt；索引 (sessionId,createdAt)。

**Migration 要点**（`DatabaseMigrations.migration_108_109`，仿 migration_105_106 惯例）：a) 每条 `CREATE TABLE IF NOT EXISTS`/`CREATE INDEX IF NOT EXISTS` 用 kotlin.runCatching 包裹 + AppLog 记录（R2）；b) 纯新增表无 @DatabaseView 改动，不触发 R1；c) DDL 与实体注解逐列一致（defaultValue 写入 CREATE TABLE 语句，Room 运行时校验才比对，R6）；d) AppDatabase version 108→109 + 注册 AiChatDao + Migration 清单追加。
**schema 快照导出**：exportSchema=true 自动在 `app/schemas/{version}.json` 产出 109.json；流程=改实体→编译→核对 `app/schemas/109.json` 新增 3 表与 DDL 一致→入库 git（迁移审计物）。
**DAO**：新增 `data/dao/AiChatDao.kt`（insert/upsert/findBySession/deleteBySession，仿既有 DAO 风格）。

## 7 风险清单

| # | 风险 | 缓解 |
|---|---|---|
| 1 | **弱供应商无 usage 返回**→校准锚为 null，压缩退化为纯本地估算：CJK 低估/英文高估，可能误触发或漏触发 | 继承 NG 双保险：阈值判定同时看官方 usage（calibration.contextTokens）与硬窗口 90% 守卫（AiChatClient.kt:861-865）；估算公式保 NG 原参数不调；记录 estimated 与实测 promptTokens 的偏差日志（AppLog）供后续校准阈值 |
| 2 | **密钥存储安全**：P1 沿用 PreferKey 明文（与 NG 及本项目现状一致）；备份导出会带出密钥 | P1 不引入 Keystore（避免扩面）；文档记债；备份导出流程在 P0/P5 期统一处理脱敏；日志侧沿用本项目 NetworkLog 脱敏规范，任何日志禁止输出 apiKey |
| 3 | **DB 迁移失败回滚**：Room migration 异常=启动崩溃且不可自动回滚 | runCatching 包裹+AppLog（R2）；DDL 全 IF NOT EXISTS 幂等可重试；上线前真机 v108 库覆盖安装验证（L3）；发布说明提示升级前备份 |
| 4 | 旧 AiProviderConfig JSON 兼容：扩展字段反序列化失败导致配置丢失 | 新字段全默认值+AiProviderStore sanitize 逐字段 runCatching（NG AiProviderStore.kt:227-258 模式）；normalize 时 apiMode→protocol 映射（chat_completions/responses→OPENAI） |
| 5 | 双调用通道并存（新 AiManager 非流式 vs 现有 AiChatService 流式）行为不一致 | P1 边界成文：新场景必须走 AiManager；AiChatService 冻结不改；P2 起规划收敛 |
| 6 | AiModelRegistry ~1100 行数据表维护成本：NG 日更模型清单跟不动 | 迁移时冻结 NG 快照；未识别模型走 enrich 兜底（type=CHAT 无能力标注），功能不劣化；后续按需增量补 |
| 7 | 新旧压缩语义差异（AiContextManager 3 字符/token 粗估 vs 六桶加权）造成行为漂移 | P1 不切旧路径；两套并存各自文档化；替换评估放 P4 |

## 8 验证方案

- **L1（编译/单测）**：`./gradlew assembleAppDebug` 通过；单测：AiTokenEstimator 已知文本 token 断言（CJK/英文混合样本）、六桶 breakdown 分桶正确性、AiDefaultProviders 12 家 id/baseUrl 非空完整性、AiProviderStore 旧 JSON 反序列化兼容用例；`app/schemas/109.json` 与实体逐列 diff 审查。
- **L2（mock 集成）**：OkHttp MockWebServer 供应商替身——3 协议 generateText 请求组包断言（URL/鉴权头/超参注入）+ 响应解析断言（content/reasoning/usage 提取；404/405 端点候选重试）；压缩调度：构造超阈值历史验证 PRE_TURN 触发→摘要生成→重建历史结构（system+summary+recent+pinned）；模拟压缩请求超窗验证兜底裁剪循环收敛；无 usage 场景验证纯本地估算退化路径。
- **L3（真机）**：a) v108 旧库覆盖安装→v109 迁移成功（Room schema 校验通过，启动无异常）；b) 最小配置：供应商管理页导入 1 家预设→填 key→测试连接返回 OK→真实生成一次（testConnection 路径）拿到非空 content；c) 手动触发一次上下文压缩（长历史对话）观察 AppLog 中 before/after token 记录。用测试包 `io.legado.miss.app.debug`。

## 9 工作量估算

| 块 | 内容 | 估算 |
|---|---|---|
| 供应商层 | provider/ 子包 ~2700 行（含 Registry 数据表） | 2.0 人日 |
| 压缩核心 | compress/ ~860 行+assets | 1.5 人日 |
| DB v109 | 3 实体+DAO+Migration+schema 审查 | 1.0 人日 |
| 配置 UI | 管理页/编辑页最小增量 | 1.0 人日 |
| 测试 | 单测+MockWebServer+真机三轮 | 1.5 人日 |
| 合计 | | **~7 人日** |

## 10 设计决策记录

| # | 决策 | 理由 |
|---|---|---|
| D1 | 配置融合而非双轨：扩展现有 `AiProviderConfig` 承载 NG 26 字段语义，`AiProviderStore` 底层复用 PreferKey `aiProviderList`/`aiCurrentProviderId` | 本项目已有管理页+存量用户配置；双配置源必然漂移。NG mergeWithDefaults/sanitize 模式保证演进 |
| D2 | UI 不新建页面：现有 AiProviderManageActivity/AiProviderEditActivity 增量叠加协议/测试连接/预设导入 | 满足"最小配置 UI"；完整聊天 UI 不在 P1 |
| D3 | 12 家预设定位为"导入模板"（一键建供应商），不强制内置启用 | 尊重现有用户自建习惯；预设参数是 NG 踩坑结晶须保留 |
| D4 | 压缩核心拆 4 类而非整文件平移；Snapshot 的 Skill/ModeEntry 字段裁剪 | NG 697 行单文件是已知技术债（design.md §2.2-1）；Agent 依赖 P4 才迁 |
| D5 | 供应商层保留非流式 generateText（忠实 NG），流式仍走 AiChatService 通道 | NG 证据 stream=false（OpenAiCompatibleProvider.kt:64）；避免 P1 兼做流式抽象引入不可控面 |
| D6 | AiBalanceProvider 裁剪出 P1 | 余额查询依赖各家私有 API 形态，非地基必需；接口留扩展位 |
| D7 | DB 不复用 ai_agent_sessions；v109 新增 3 张最小表 | 现表是 Agent 运行状态机（scope/status/contextJson），语义与聊天会话不同构；全列显式 defaultValue 吸收 NG 亮点 |
| D8 | v108→v109 手动 Migration（非 AutoMigration） | 本项目 88 之后惯例；手动便于 runCatching+AppLog+幂等 DDL（R2/回滚演练） |
| D9 | AiModelRegistry 拆定义/enrich 两文件、冻结快照 | 数据表过重（~989 行）；未识别模型 enrich 兜底保证不劣化 |
