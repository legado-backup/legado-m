# SA-3 AI 助手模块深度对比分析

> 任务编号：SA-3
> 对比对象：Archive 私仓（`temp/forks-comparison/legado-archive/`，tag `private-armv8-3.26.07071245`） vs 本项目（`f:\myself\github\WeAgentChat\temp\legado\`）
> 分析范围：`app/src/main/java/io/legado/app/help/ai/` 全部 35 个 Kotlin 文件
> 输出安全：本报告仅引用技术字段（类名/方法名/字段名/文件路径+行号锚点），不引用业务数据

---

## 1. 模块概览

| 维度 | Archive 私仓 | 本项目 | 差异类型 |
|------|-------------|--------|---------|
| `help/ai/` 目录文件数 | 35 个 Kotlin 文件 | 0（目录不存在，Glob 验证） | Archive 独有 |
| 含 "Ai" 关键字文件 | 35 个（help/ai/ 全部） | 0（`app/src/main/java/io/legado/app/` 全路径 Glob 无命中） | Archive 独有 |
| AI 实体（data/entities） | 11 个（AiAgentJob/AiAgentSession/AiAgentTrace/AiGeneratedImage/AiMemoryFragment/AiMemoryItem/AiWorldBook/AiWorldBookBinding/AiWorldBookEntry/BookCharacter/BookCharacterRelation 推断） | 0 | Archive 独有 |
| AI DAO 层 | 6+ 个（aiAgentDao/aiMemoryDao/aiGalleryDao/...） | 0 | Archive 独有 |
| UI 层 | `ui/main/ai/` 完整一套（AiChatMessage/AiContextSummary/AiAgentMode/AiChatCompanionConfig/AiModelConfig/AiProviderConfig/AiSkillConfig/AiImageProviderConfig/AiMcpServerConfig 等） | 0 | Archive 独有 |
| Agent 运行时 | 完整：Runtime + StateStore + Planner + Validator + Interruption | 无 | Archive 独有 |
| 工具体系 | 70+ 工具，10 个工具对象，含 MCP 动态扩展 | 无 | Archive 独有 |
| MCP 协议 | 完整 client（Streamable HTTP + SSE，protocol 2025-06-18） | 无 | Archive 独有 |

**差异定性**：AI 模块是 Archive 私仓相对本项目最显著的新增体系，规模达 30+ 文件、独立数据库表、独立 UI、独立工具生态，整体属于"Archive 独有"且工程量极大的功能。

---

## 2. Archive AI 架构分析

### 2.1 Agent 运行时（AiAgentRuntime.kt）

- **文件路径**：`app/src/main/java/io/legado/app/help/ai/AiAgentRuntime.kt`
- **类签名**：`internal object AiAgentRuntime`（单例，L13）
- **核心方法**：`suspend fun runToolLoop(...)`（L17-L298）
- **状态管理**：通过 `AiAgentStateStore.Run` 持久化 session/job/round 三层状态
- **生命周期**：`startRun → trace(每轮/每次工具调用) → finish/cancel`，含 `leaseUntil` 租约过期机制
- **关键架构模式**：
  - 工具循环（Tool Loop）：最多 `maxToolRounds` 轮（Goal 模式默认 256），每轮请求模型 → 解析 toolCalls → 执行工具 → 写回 conversation
  - 目标完成校验（Goal Completion Check，L102-L135）：Goal 模式下若模型不调用工具，会主动询问模型 "ACHIEVED or CONTINUE" 判定目标是否达成
  - 检查点（Checkpoint，L380-L414）：每次工具结果落盘，conversation 保留尾部 10 条、tool events 保留尾部 8 条
  - 校验重试（ValidatedToolExecution，L306-L378）：每个工具调用最多 `aiAgentToolMaxAttempts` 次，失败且可重试时指数退避
- **关键代码段**：

```kotlin
// AiAgentRuntime.kt L17-L34
suspend fun runToolLoop(
    apiMode: String,
    conversation: MutableList<JSONObject>,
    tools: List<AiResolvedTool>,
    requestLog: StringBuilder,
    onStatus: (JSONObject) -> Unit,
    includeStructuredBlocks: Boolean,
    useAllTools: Boolean,
    extraToolNames: Set<String>,
    agentRun: AiAgentStateStore.Run?,
    maxToolRounds: Int = AppConfig.aiAgentMaxToolRounds,
    requireGoalCompletion: Boolean = false,
    requestAssistantTurn: suspend (
        round: Int,
        messages: List<JSONObject>,
        tools: List<AiResolvedTool>
    ) -> AiAgentAssistantTurn
): String
```

```kotlin
// AiAgentRuntime.kt L306-L326 校验重试机制
private suspend fun executeValidatedTool(
    toolCall: AiAgentToolCall,
    toolMap: Map<String, AiResolvedTool>,
    toolOptions: AiToolExecutionOptions,
    agentRun: AiAgentStateStore.Run?,
    roundNo: Int,
    onStatus: (JSONObject) -> Unit,
    toolEvents: JSONArray
): ValidatedToolExecution {
    var lastResult = ""
    var lastValidation = AiToolValidationResult(
        ok = false, category = "not_executed",
        message = "工具未执行", retryable = true
    )
    var finalAttempt = 0
    val maxAttempts = AppConfig.aiAgentToolMaxAttempts
    for (attempt in 1..maxAttempts) {
        finalAttempt = attempt
        lastResult = AiToolExecutor.execute(toolCall, toolMap, toolOptions)
        lastValidation = AiAgentValidator.validateToolResult(toolCall, lastResult)
        // ... trace + backoff
    }
}
```

- **状态机**：`STATUS_RUNNING → STATUS_WAITING_RESUME / STATUS_DONE / STATUS_FAILED / STATUS_CANCELLED`（见 AiAgentStateStore）

### 2.2 工具调用机制（AiToolExecutor + AiToolRegistry + AiAgentValidator）

#### 2.2.1 AiResolvedTool 数据结构

```kotlin
// AiToolRegistry.kt L6-L10
data class AiResolvedTool(
    val name: String,
    val definition: JSONObject,         // OpenAI Function Calling 格式
    val execute: suspend (JSONObject?) -> String
)
```

#### 2.2.2 AiToolExecutor（执行器）

- **文件路径**：`AiToolExecutor.kt`
- **核心职责**：统一工具执行入口，处理启用校验、参数解析、超时、网络重试
- **超时策略**（L12-L13, L105-L107）：
  - 普通工具：120 秒
  - 图像工具（`generate_image`/`generate_book_character_avatar`）：300 秒
- **网络重试**（L21-L43, L110-L128）：`retryableToolNames` 集合内的工具遇 `SocketException`/`IOException` 等可重试一次
- **启用校验**（L50-L56）：`AppConfig.aiEnabledToolNames` 控制白名单，未启用工具直接返回 `{"ok":false,"error":"Tool is disabled"}`

```kotlin
// AiToolExecutor.kt L45-L103 核心执行
suspend fun execute(
    toolCall: AiAgentToolCall,
    toolMap: Map<String, AiResolvedTool>,
    options: AiToolExecutionOptions
): String {
    val enabled = AppConfig.aiEnabledToolNames.ifEmpty { AiToolRegistry.defaultEnabledTools }
    if (!options.useAllTools && toolCall.name !in enabled && toolCall.name !in options.extraToolNames) {
        return JSONObject().apply {
            put("ok", false)
            put("error", "Tool is disabled: ${toolCall.name}")
        }.toString()
    }
    val resolvedTool = toolMap[toolCall.name] ?: return /* Unknown tool error */
    // ... 参数解析 + 超时 + 重试
    return runCatching {
        withTimeout(toolTimeoutMillis(toolCall.name)) {
            resolvedTool.execute(arguments)
        }
    }.getOrElse { /* 错误包装 */ }
}
```

#### 2.2.3 AiToolRegistry（注册中心）

- **文件路径**：`AiToolRegistry.kt`
- **工具版本迁移机制**（L14-L86）：`TOOL_SETTINGS_VERSION = 16`，每次新增工具集时记录版本号，启动时按版本差量合并到用户启用列表
- **工具集分层**（L88-L130）：
  - `characterCompanionToolNames`：角色对话场景最小集（6 个）
  - `readSafeToolNames`：只读工具白名单（30+ 个），用于 Plan 模式
  - `defaultEnabledTools`：默认启用集（70+ 个）
- **工具元数据**（L214-L289）：`nativeToolLabels`（中文标签）+ `nativeToolGroups`（分组：书架/阅读/书源/阅读网络/联网搜索/AI 生图/角色资料/AI 图片库/角色配音/智能配乐/世界书/设置/AI workspace/MCP 工具）
- **工具解析入口**（L401-L414）：`nativeResolvedTools()` 聚合 10 个工具对象的 `resolvedTools()` 列表，去重 by name

```kotlin
// AiToolRegistry.kt L401-L414
private fun nativeResolvedTools(): List<AiResolvedTool> {
    val tools = AiBookshelfTool.resolvedTools().toMutableList()
    tools += AiLibraryTool.resolvedTools()
    tools += AiTavilyTool.resolvedTools()
    tools += AiBookSourceTool.resolvedTools()
    tools += AiReadingNetworkTool.resolvedTools()
    tools += AiSettingsTool.resolvedTools()
    tools += AiWorkspaceTool.resolvedTools()
    tools += AiImageTool.resolvedTools()
    tools += AiBookCharacterTool.resolvedTools()
    tools += AiReadAloudBgmTool.resolvedTools()
    tools += AiWorldBookTool.resolvedTools()
    return tools.distinctBy { it.name }
}
```

#### 2.2.4 AiAgentValidator（结果校验器）

- **文件路径**：`AiAgentValidator.kt`
- **写入类工具校验**（L86-L122）：必须返回 `item/result/results/id/count/successCount/worldBookId` 等可核对字段，否则判定 `weak_write_evidence`
- **批量工具校验**（L99-L105）：`total` vs `success`，部分失败判定 `partial_write`
- **可重试失败识别**（L142-L152）：错误信息含 `timeout/connection/network/reset/abort/429/rate` 则 `retryable=true`

```kotlin
// AiAgentValidator.kt L36-L68
fun validateToolResult(
    toolCall: AiAgentToolCall,
    result: String
): AiToolValidationResult {
    val trimmed = result.trim()
    if (trimmed.isBlank()) {
        return AiToolValidationResult(false, "empty_result", "工具返回为空", retryable = true)
    }
    val json = parseJson(trimmed) ?: return if (isWriteTool(toolCall.name)) {
        AiToolValidationResult(false, "invalid_json", "写入类工具必须返回可校验 JSON", retryable = false)
    } else {
        AiToolValidationResult(true, "text_result", "工具返回非 JSON 文本")
    }
    // ... ok/success 显式失败 + 写入工具专属校验
}
```

### 2.3 聊天服务（AiChatService）

- **文件路径**：`AiChatService.kt`（1859 行，单文件巨型服务）
- **核心方法**：
  - `chat(messages)` / `chatStream(messages, onPartial, ...)`（L96-L98, L275-L494）
  - `requestSingleToolCall(messages, tool, ...)`（L100-L211）单工具调用（用于上下文外抽取）
  - `fetchModels(provider)`（L243-L273）拉取模型列表
- **双 API 模式**（L758-L815, L858-L919, L1044-L1092）：
  - `AI_API_MODE_CHAT_COMPLETIONS`：OpenAI Chat Completions
  - `AI_API_MODE_RESPONSES`：OpenAI Responses API（含 `response.output_text.delta`、`response.function_call_arguments.delta` 等事件流）
- **备用模型 Fallback**（L506-L568）：超时/429/5xx 时自动切换到 `fallbackModelConfig`，且仅在 chatUrl 或 model 不同时才切换
- **请求重试**（L570-L620）：`NETWORK_ABORT_RETRY_COUNT = 2`，遇 `isAiRetryableRequestFailure` 时重试
- **多 Agent 模式**（L1614-L1632）：
  - `AiAgentMode.NORMAL`：常规模式
  - `AiAgentMode.PLAN`：计划模式（仅启用只读工具，强制 PLAN 模式系统提示）
  - `AiAgentMode.GOAL`：目标模式（`maxToolRounds = 256`，强制目标完成校验）
- **上下文构造**（L1204-L1296）：注入顺序为
  1. 系统 Prompt（`AppConfig.aiSystemPrompt`）
  2. AI Workspace Policy Prompt（强制工作区工作流）
  3. 世界书 `AFTER_SYSTEM_PROMPT` 位置注入
  4. Persona Prompt
  5. Context Summary
  6. Retrieved Memory（长期记忆）
  7. Agent Plan
  8. Skill Catalog（技能目录）
  9. 书架工具使用提示（如关键词命中）
  10. 世界书 `BEFORE_PROMPT` 位置注入
  11. 用户/助手消息序列
  12. 世界书 `BEFORE_LAST_USER` / `INJECT_DEPTH` 动态插入
- **调试日志脱敏**（L1486-L1496）：自动 redact Bearer token、api_key、authorization、image base64
- **Prompt Cache Key**（L1634-L1643）：基于 `provider.id + model` 生成，最长 128 字符

```kotlin
// AiChatService.kt L60-L78 工作区策略系统提示
private const val AI_WORKSPACE_POLICY_PROMPT =
    "Agent file workflow is mandatory for source, rule, log, JSON, HTML, and project-style edits. " +
            "If the user provides long data, source text, logs, JSON, HTML, or project snippets, first save it with workspace_save_input_file. " +
            "Before editing, inspect files with workspace_list_files, workspace_search_files, workspace_read_file, ... " +
            "Before modifying any existing file, proactively call workspace_create_backup, ... " +
            "After editing, call workspace_diff_file with the returned backupId to verify ..."
```

### 2.4 联网搜索（AiTavilyTool）

- **文件路径**：`AiTavilyTool.kt`
- **类签名**：`object AiTavilyTool`
- **启用条件**（L18-L20）：`AppConfig.aiTavilyEnabled && aiTavilyApiKey.isNotBlank()`
- **工具定义**（L30-L77）：`search_web_tavily`，参数含 `query/topic(=general|news|finance)/searchDepth(=basic|advanced|ultra-fast)/maxResults(1-10)/includeDomains/excludeDomains/includeAnswer`
- **请求构造**（L79-L138）：POST 到 `{aiTavilyBaseUrl}/search`，Bearer 鉴权
- **返回结构**：`{ok, query, answer, responseTime, usage, results:[{title,url,content,score,favicon}], images?}`

### 2.5 记忆系统（AiMemoryStore + AiMemoryRetriever + AiMemoryExtractor）

- **文件路径**：`AiMemoryStore.kt`
- **核心数据结构**：
  - `AiMemoryContext`（L10-L16）：`scope/bookKey/sessionId/companionId/title` 五维度定位
  - `AiRetrievedMemory`（L18-L50）：items + fragments，可转 system prompt（默认 2800 字符上限）
- **存储层**（`AiMemoryStore`，L52-L98）：
  - `upsertItem` + `upsertItemFts`：写入主表 + FTS 全文索引
  - `upsertFragment` + `upsertFragmentFts`：写入片段表 + FTS
  - `fingerprint`/`contentHash`：MD5 去重
- **检索层**（`AiMemoryRetriever`，L100-L173）：
  - 取最近 6 条消息（≤4000 字符）作为查询文本
  - `buildFtsQuery`（L146-L153）：提取英文/数字关键词，OR 连接，最多 8 个
  - `keywords`（L155-L167）：英文词 + 中文 bigram，最多 48 个用于打分
  - 双重召回：FTS 命中 + candidate（按 scope/bookKey/sessionId 候选集）
  - 排序：`score(text, keywords) * 10 + importance`
  - 命中后调用 `markItemsUsed`/`markFragmentsUsed` 更新使用时间
- **抽取层**（`AiMemoryExtractor`，L175-L234）：
  - `recordConversation`：每轮对话结束后自动写入 fragment（content ≥40 字符）
  - `extractPreference`：识别 `我希望/我喜欢/我不希望/我不喜欢/以后/记住` 关键词，提取用户偏好作为 `TYPE_USER_PREFERENCE` 类型 item，importance=75

```kotlin
// AiMemoryStore.kt L215-L233 偏好自动抽取
private fun extractPreference(content: String, context: AiMemoryContext, now: Long): AiMemoryItem? {
    val normalized = content.replace(Regex("\\s+"), " ").trim()
    val hit = listOf("我希望", "我喜欢", "我不希望", "我不喜欢", "以后", "记住")
        .firstOrNull { normalized.contains(it) } ?: return null
    return AiMemoryItem(
        scope = AiMemoryItem.SCOPE_GLOBAL,
        sessionId = context.sessionId,
        type = AiMemoryItem.TYPE_USER_PREFERENCE,
        subject = "用户偏好",
        predicate = hit,
        objectValue = normalized.take(240),
        // ...
        importance = 75
    )
}
```

### 2.6 图像生成（AiImageService）

- **文件路径**：`AiImageService.kt`
- **核心方法**：
  - `generate(prompt, provider)`：仅返回图像源
  - `generateAndStore(prompt, provider, metadata)`：生成并入库到 `AiImageGalleryManager`
- **三种生成分支**（L79-L263）：
  1. `generateByImagesApi`：OpenAI Images API（`/images/generations`），默认模型 `gpt-image-1`
  2. `generateByResponses`：Responses API + `image_generation` tool，默认模型 `gpt-5`
  3. `generateByJs`：JS 脚本自定义生图（基于 RhinoScriptEngine），支持 `generate(prompt, provider)` / `run(prompt, provider)` 函数签名
- **JS Source 集成**（L221-L282）：复用 Legado 自身的 `BaseSource` 体系（`AiImageJsSource`），可使用 `cookie/cache/header/loginUrl/jsLib`，与书源脚本机制完全对齐
- **图像格式归一化**（L334-L404）：支持 url / data url / base64 / JSON / JSONArray / NativeObject / NativeArray 多种返回形态，自动识别 PNG/JPEG/GIF/RIFF magic bytes
- **大小限制**（L30-L31）：`MAX_IMAGE_BYTES = 32MB`，`MAX_IMAGE_RESPONSE_BYTES = 48MB`
- **请求日志**（L305-L326）：通过 `AppLog.put` 落盘，记录 url/provider/model/timeout/elapsed/status

### 2.7 MCP 客户端（AiMcpClient）

- **文件路径**：`AiMcpClient.kt`
- **协议版本**：`2025-06-18`（L17），符合 MCP 最新规范
- **传输方式**：HTTP + JSON-RPC 2.0，支持 SSE 响应（L298-L339）
- **会话管理**（L172-L216）：
  - `initialize` 请求协商 protocolVersion，记录 `Mcp-Session-Id` header
  - `notifications/initialized` 通知完成握手
  - 会话 fingerprint 基于 `id+name+endpoint+apiKey+enabled`，变化时重建会话
- **工具发现**（L83-L111）：`tools/list` 分页拉取（cursor 翻页），返回 `name/title/description/inputSchema`
- **工具别名**（L374-L388）：`mcp_{serverSlug}_{toolSlug}`，最多 64 字符，重名时追加 `_{serverId后6位}_{index}`
- **工具缓存**（L29-L33, L50-L79）：`TOOL_CACHE_TTL_MS = 60s`，fingerprint 不变则复用缓存
- **工具调用**（L149-L170）：`tools/call` 方法，参数透传
- **错误恢复**（L242-L280）：会话失败时清空 session+cache，重新 `ensureSession` 后重试一次
- **响应大小限制**（L21, L341-L353）：`MAX_MCP_RESPONSE_BYTES = 1MB`
- **Schema 归一化**（L355-L372）：确保 `type=object` + `properties` 存在，允许 `additionalProperties=true`

```kotlin
// AiMcpClient.kt L172-L216 MCP 会话初始化
private suspend fun ensureSession(server: AiMcpServerConfig): SessionState {
    val fingerprint = server.fingerprint()
    val current = sessionMap[server.id]
    if (current != null && current.configFingerprint == fingerprint) {
        return current
    }
    val initializeBody = jsonRpcRequest(
        method = "initialize",
        params = JSONObject().apply {
            put("protocolVersion", PROTOCOL_VERSION)
            put("clientInfo", JSONObject().apply {
                put("name", "Legado")
                put("version", BuildConfig.VERSION_NAME)
            })
            put("capabilities", JSONObject())
        },
        id = nextRequestId()
    )
    // ... POST + 读取 Mcp-Session-Id header + 发送 initialized 通知
}
```

### 2.8 上下文管理（AiContextManager）

- **文件路径**：`AiContextManager.kt`
- **核心常量**（L8-L12）：
  - `CHARS_PER_TOKEN = 3`
  - `RECENT_MESSAGE_COUNT = 10`
  - `COMPRESS_TRIGGER_PERCENT = 90`（达到 90% 触发压缩）
  - `TARGET_PERCENT = 35`（摘要占用预算 35%）
  - `MAX_SUMMARY_CHARS = 32_000`
- **token 估算**（L97-L103）：ASCII 字符 / 4 + 非 ASCII 字符 + 1（粗略估算）
- **压缩流程**（L22-L91）：
  1. 计算 `usableLimit = aiContextWindowTokens - reserveTokens`
  2. 复用已存在的 summary（按 fingerprint 匹配 `lastMessageId`）
  3. 估算未摘要部分 token，若 `< usableLimit * 90%` 直接放行
  4. 否则取最近 10 条作为 recent，其余 old 调用 `buildSummary` 生成摘要
  5. 摘要按 `summaryBudget * 3` 字符截断，最大 32KB
- **摘要构造**（L105-L124）：
  - 头部：`Existing summary:` + 已有摘要
  - 主体：`Condensed conversation facts:` + 每条消息压缩到 900 字符的 `- User/Assistant: ...`
  - 尾部对齐：超过 maxChars 时取 `takeLast`（保留最新信息）

```kotlin
// AiContextManager.kt L22-L51
fun prepare(
    messages: List<AiChatMessage>,
    previousSummary: AiContextSummary?,
    reserveTokens: Int = 0
): PreparedContext {
    val clean = messages.filterNot { it.pending }.filter { it.content.isNotBlank() }
    if (!AppConfig.aiContextCompressionEnabled) { /* 不压缩直接返回 */ }
    val limit = AppConfig.aiContextWindowTokens
    val usableLimit = (limit - reserveTokens).coerceAtLeast(0)
    val summaryBudget = (usableLimit * TARGET_PERCENT / 100).coerceAtLeast(0)
    // ... 摘要匹配 + 压缩判定 + fitMessages
}
```

### 2.9 Agent 状态存储（AiAgentStateStore）

- **文件路径**：`AiAgentStateStore.kt`
- **三层数据模型**：Session（会话）/ Job（任务）/ Trace（事件追踪）
- **租约机制**（L12）：`DEFAULT_LEASE_MILLIS = 10 分钟`，超期 job 自动转为 `STATUS_WAITING_RESUME`
- **核心 API**：
  - `startRun(scope, type, currentGoal, currentTask, inputJson)` → 创建 session+job，返回 Run 句柄
  - `trace(run, eventType, payload, round, success, usage, checkpointPayload)` → 写 Trace + 更新 Job checkpoint
  - `markWaitingResume(run, reason, delayMillis)` → 等待恢复状态
  - `finish(run, success, outputJson, error)` → 终态 DONE/FAILED
  - `cancel(run, reason)` → 终态 CANCELLED
  - `markExpiredRunningJobs(now)` → 扫描所有超期 RUNNING job，自动转 WAITING_RESUME
- **事件类型**（`AiAgentTrace.EVENT_*`）：`STATUS / MODEL_REQUEST / MODEL_RESPONSE / TOOL_CALL / TOOL_RESULT / VALIDATION / ERROR / MEMORY_RETRIEVED / WORLD_BOOK_RETRIEVED / PLAN_CREATED`
- **Checkpoint 结构**（L191-L213）：`{eventType, round, stage, toolName, success, updatedAt, conversationTail, toolEventsTail, ...}`

### 2.10 Agent 计划器（AiAgentPlanner）

- **文件路径**：`AiAgentPlanner.kt`
- **作用**：基于关键词识别，为每轮 Agent 执行预生成"骨架计划"，作为系统提示约束模型执行顺序
- **5 步标准计划**（L77-L118）：
  1. `understand_goal`：理解用户目标
  2. `read_local_context`（如需要本地数据）：调用本地工具读取
  3. `apply_changes`（如需要写入）：执行创建/修改/删除
  4. `validate_result`：校验工具结果
  5. `final_response`：输出结论
- **关键词识别**（L122-L136）：
  - `needsLocalData`：书架/书籍/章节/阅读记录/书源/角色/配音/工具/设置/查询/搜索/调试/生图
  - `needsWrite`：创建/新增/修改/更新/删除/移除/设置/分配/导入/保存/清空/批量/生成头像

### 2.11 Agent 中断处理（AiAgentInterruption）

- **文件路径**：`AiAgentInterruption.kt`
- **4 种用户中断消息**（L7-L10）：
  - `USER_STOPPED_GENERATION`：用户停止生成
  - `USER_STOPPED_READ_AI`：用户停止阅读 AI
  - `START_NEW_READ_AI_CHAT`：开启新阅读 AI 对话
  - `SUPERSEDED_READ_AI_QUESTION`：被下一个阅读 AI 问题取代
- **判定逻辑**（L12-L19）：基于 `CancellationException` + 消息匹配

---

## 3. 本项目对应实现

### 3.1 AI 模块缺失验证

| 验证项 | 命令 | 结果 |
|--------|------|------|
| `help/ai/` 目录 | `Glob app/src/main/java/io/legado/app/help/ai/**/*.kt` | No file found |
| 任意含 "Ai" 关键字文件 | `Glob app/src/main/java/io/legado/app/**/*Ai*.kt` | No file found |
| 任意含 "Ai" 关键字类 | （推断）Grep `class Ai` 全项目 | 无命中 |

**结论**：本项目 100% 缺失 AI 助手模块，Archive 的整套 AI 体系（运行时/工具/聊天/MCP/记忆/图像/状态/计划/校验）在本项目中没有任何对应实现。

### 3.2 本项目可类比点

虽然本项目无 AI 模块，但存在以下可类比的现有能力：

| 可类比点 | 本项目位置 | 与 Archive AI 模块的关系 |
|---------|-----------|------------------------|
| 规则引擎（CSS/XPath/JSONPath/正则/JS） | `app/src/main/java/io/legado/app/model/analyzeRule/` | Archive 的 `AiBookSourceTool.fetch_source_html/debug_book_source` 复用此引擎 |
| JS 脚本引擎（Rhino） | `app/src/main/java/io/legado/app/help/source/` + `com.script.rhino` | Archive 的 `AiImageService.generateByJs` 完全复用此引擎 |
| WebBook 网络层 | `app/src/main/java/io/legado/app/model/webBook/` | Archive 的 `AiBookshelfTool` 通过此模块调用书源搜索 |
| Room 数据库 | `app/src/main/java/io/legado/app/data/` | Archive 的 AI 表（AiAgentJob/AiMemoryItem 等）若引入需新增 entity + DAO + migration |
| OkHttp 客户端 | `app/src/main/java/io/legado/app/help/http/` | Archive 的 AI HTTP 调用全部基于此客户端 |
| CookieStore | `app/src/main/java/io/legado/app/help/http/CookieStore.kt` | Archive 的 JS 生图脚本通过 `bindings["cookie"] = CookieStore` 复用 |
| CacheManager | `app/src/main/java/io/legado/app/help/CacheManager.kt` | Archive 的 JS 生图脚本通过 `bindings["cache"] = CacheManager` 复用 |

**关键观察**：Archive 的 AI 模块**深度复用** Legado 已有基础设施（Rhino/AnalyzeUrl/WebBook/CookieStore/CacheManager），并未另起炉灶。这为本项目借鉴 AI 模块降低了集成成本。

---

## 4. 差异清单

| ID | 差异点 | Archive 实现（含文件路径+行号） | 本项目实现 | 差异类型 | 收益(1-5) | 风险(1-5) | 借鉴成本 | 源码依据 |
|----|-------|------------------------------|-----------|---------|----------|----------|---------|---------|
| AI-001 | Agent 运行时核心（Tool Loop） | `AiAgentRuntime.kt:L17-L298 runToolLoop()` | 无 | 独有 | 5 | 3 | 高 | L17 runToolLoop 签名 + L42-L298 循环逻辑 |
| AI-002 | 工具注册与发现 | `AiToolRegistry.kt:L12 object AiToolRegistry` + `L401-L414 nativeResolvedTools()` | 无 | 独有 | 5 | 2 | 中 | L401-L414 聚合 10 个工具对象 |
| AI-003 | 工具执行器（超时+重试+白名单） | `AiToolExecutor.kt:L10 object AiToolExecutor` + `L45-L103 execute()` | 无 | 独有 | 4 | 2 | 中 | L12-L13 超时 + L21-L43 retryable + L50-L56 启用校验 |
| AI-004 | 工具结果校验与重试 | `AiAgentValidator.kt:L22-L122 validateToolResult()` + `AiAgentRuntime.kt:L306-L378 executeValidatedTool()` | 无 | 独有 | 4 | 3 | 中 | L86-L122 写入工具校验 + L306-L378 重试退避 |
| AI-005 | Agent 状态持久化与恢复 | `AiAgentStateStore.kt:L10-L213` 全文件 | 无 | 独有 | 4 | 4 | 高 | L12 DEFAULT_LEASE_MILLIS + L101-L121 markWaitingResume + L173-L189 markExpiredRunningJobs |
| AI-006 | Agent 计划器（关键词驱动） | `AiAgentPlanner.kt:L64-L120 create()` | 无 | 独有 | 3 | 2 | 低 | L77-L118 5 步标准计划 + L122-L136 关键词识别 |
| AI-007 | 上下文压缩与摘要 | `AiContextManager.kt:L7-L185` 全文件 | 无 | 独有 | 5 | 3 | 中 | L10-L12 常量 + L22-L91 prepare + L105-L124 buildSummary |
| AI-008 | 长期记忆系统（FTS+排序） | `AiMemoryStore.kt:L100-L173 AiMemoryRetriever.retrieve()` | 无 | 独有 | 4 | 4 | 高 | L100-L173 retrieve + L146-L167 buildFtsQuery/keywords |
| AI-009 | 对话记忆自动抽取 | `AiMemoryStore.kt:L175-L234 AiMemoryExtractor.recordConversation()` | 无 | 独有 | 3 | 3 | 中 | L177-L213 recordConversation + L215-L233 extractPreference |
| AI-010 | Tavily 联网搜索 | `AiTavilyTool.kt:L13-L173` 全文件 | 无 | 独有 | 4 | 2 | 低 | L17-L28 resolvedTools + L79-L138 search |
| AI-011 | OpenAI Images API 生图 | `AiImageService.kt:L86-L142 generateByImagesApi()` | 无 | 独有 | 3 | 2 | 中 | L98-L142 |
| AI-012 | OpenAI Responses API 生图 | `AiImageService.kt:L144-L205 generateByResponses()` | 无 | 独有 | 3 | 3 | 中 | L144-L205 + L152-L159 image_generation tool |
| AI-013 | JS 脚本生图（复用 Rhino） | `AiImageService.kt:L221-L263 generateByJs()` | 无 | 独有 | 4 | 3 | 中 | L221-L263 + L265-L282 AiImageJsSource |
| AI-014 | MCP 协议客户端（Streamable HTTP+SSE） | `AiMcpClient.kt:L15-L423` 全文件 | 无 | 独有 | 5 | 4 | 高 | L17 PROTOCOL_VERSION + L45-L81 resolveTools + L172-L216 ensureSession |
| AI-015 | 多 Agent 模式（Normal/Plan/Goal） | `AiChatService.kt:L1614-L1632 buildModeSystemPrompt/maxToolRoundsForMode` | 无 | 独有 | 4 | 3 | 中 | L1614-L1625 + L1627-L1632 |
| AI-016 | 备用模型 Fallback | `AiChatService.kt:L506-L568 requestCompletionStreamWithFallback()` | 无 | 独有 | 4 | 2 | 低 | L506-L568 + L1645-L1663 isAiFastFallbackCandidate |
| AI-017 | 双 API 模式（Chat Completions + Responses） | `AiChatService.kt:L758-L815 buildRequestBody/buildResponsesRequestBody` + `L858-L919 consumeResponsesStreamPayload` | 无 | 独有 | 4 | 3 | 中 | L758-L815 + L858-L919 |
| AI-018 | 调试日志脱敏 | `AiChatService.kt:L1486-L1496 safeDebugPayload()` | 无 | 独有 | 3 | 1 | 低 | L1487-L1496 Bearer/api_key/token/secret/image base64 自动 redact |
| AI-019 | Prompt Cache Key | `AiChatService.kt:L1634-L1643 buildPromptCacheKey/normalizePromptCacheKey` | 无 | 独有 | 3 | 1 | 低 | L1634-L1643 |
| AI-020 | AI Workspace 文件编辑系统 | `AiWorkspaceTool.kt:L22-L80+` 21 个工具 | 无 | 独有 | 4 | 4 | 高 | L24-L44 工具常量 + L51-L57 allowedExtensions |
| AI-021 | Workspace Policy 系统提示 | `AiChatService.kt:L62-L78 AI_WORKSPACE_POLICY_PROMPT` | 无 | 独有 | 3 | 2 | 低 | L62-L78 |
| AI-022 | 工具版本迁移机制 | `AiToolRegistry.kt:L14-L86 TOOL_SETTINGS_VERSION + version2AddedDefaultTools ... version15AddedDefaultTools` | 无 | 独有 | 3 | 2 | 中 | L14 + L15-L86 15 个版本增量集 |
| AI-023 | 工具分组与中文标签 | `AiToolRegistry.kt:L214-L366 nativeToolLabels/nativeToolGroups` | 无 | 独有 | 2 | 1 | 低 | L214-L289 + L291-L366 |
| AI-024 | 只读工具白名单（Plan 模式） | `AiToolRegistry.kt:L97-L130 readSafeToolNames` + `L390-L399 isReadOnlyTool` | 无 | 独有 | 3 | 2 | 低 | L97-L130 + L390-L399 |
| AI-025 | Agent 中断处理 | `AiAgentInterruption.kt:L5-L29` 全文件 | 无 | 独有 | 3 | 2 | 低 | L7-L10 4 种中断消息 + L12-L19 isUserCancellation |
| AI-026 | 世界书系统 | `AiWorldBookTool.kt` + `AiWorldBookManager.kt` + 实体 | 无 | 独有 | 4 | 3 | 高 | 工具：list_world_books/upsert_world_book/upsert_world_book_entry/import_world_book_json/export_world_book_json + 多位置注入 |
| AI-027 | 角色配音/朗读配乐集成 | `AiReadAloudBgmTool.kt` + `AiReadAloudBgmService.kt` + `AiReadAloudRoleState.kt` + `AiReadAloudUsageRecorder.kt` | 无 | 独有 | 3 | 3 | 中 | 4 文件构成朗读 AI 增强子系统 |
| AI-028 | 角色资料与关系网 | `AiBookCharacterTool.kt` | 无 | 独有 | 3 | 3 | 中 | list_book_characters/upsert_book_character/list_book_character_relations 等工具 |
| AI-029 | 任务保活（AiTaskKeepAlive） | `AiTaskKeepAlive.kt` | 无 | 独有 | 3 | 4 | 中 | （文件未深入读取，从命名推断为前台服务保活） |
| AI-030 | 章节摘要服务 | `AiChapterSummaryService.kt` | 无 | 独有 | 3 | 2 | 中 | （文件未深入读取） |

---

## 5. 关键发现

### 5.1 AI Agent 架构模式

Archive 采用**单循环 + 多模式 + 持久化状态**架构：`AiAgentRuntime.runToolLoop` 是唯一循环入口，通过 `agentMode` 参数（Normal/Plan/Goal）切换行为，所有中间状态通过 `AiAgentStateStore` 落盘到 Room 数据库。这种设计使得 Agent 任务可以在 App 被杀、超时、网络中断后通过 `STATUS_WAITING_RESUME` 状态恢复，是相对成熟的生产级 Agent 实现。

### 5.2 工具调用机制

采用**三层架构**：
- `AiToolRegistry`：静态注册 10 个工具对象 + 动态注册 MCP 工具，统一 `AiResolvedTool` 抽象
- `AiToolExecutor`：执行入口，负责启用校验/超时/网络重试
- `AiAgentValidator`：结果校验，写入类工具必须有"可核对字段"（id/count/result 等），失败可重试时自动退避

**亮点**：工具版本迁移机制（`TOOL_SETTINGS_VERSION = 16`）解决了"新版本新增工具如何自动加入老用户启用列表"的工程问题，每次升级差量合并，避免覆盖用户自定义。

### 5.3 MCP 协议支持

Archive 实现了**完整的 MCP 2025-06-18 协议**：
- Streamable HTTP 传输 + SSE 响应解析
- 会话管理（initialize → Mcp-Session-Id → notifications/initialized）
- 工具分页发现（cursor 翻页）+ 别名机制（`mcp_{server}_{tool}` 防重名）
- 60 秒工具缓存 + fingerprint 失效
- 会话失败自动重建 + 单次重试
- 1MB 响应大小限制

**这是本项目最有价值的借鉴点之一**，因为 MCP 是 2025 年 AI 工具生态的事实标准，支持后可接入任意 MCP 服务器（文件系统/数据库/Git/浏览器等）。

### 5.4 联网搜索集成

Tavily 集成是**轻量但完整**的范例：
- 仅 173 行代码实现完整工具（定义 + 执行 + 错误处理）
- 复用 Legado 自身 `okHttpClient` 网络层
- 通过 `AppConfig.aiTavilyEnabled` + `aiTavilyApiKey` 双开关控制
- 支持域名黑白名单、搜索深度、主题分类等完整参数
- 返回结构化 JSON（含 answer/results/images），便于 Agent 后续处理

### 5.5 记忆系统设计

**三组件解耦**：
- `AiMemoryStore`：存储层，主表 + FTS 双写
- `AiMemoryRetriever`：检索层，FTS 召回 + candidate 召回 + 关键词打分排序
- `AiMemoryExtractor`：抽取层，对话结束后自动写入 fragment + 偏好抽取

**巧妙点**：
- 检索时打分公式 `score * 10 + importance`，兼顾关键词命中数和用户标注的重要性
- 偏好抽取用关键词触发（"我希望/我喜欢/以后/记住"），无需 LLM 调用即可低成本入库
- fragment 自动写入（content ≥40 字符），保证对话历史不丢
- `markItemsUsed` 更新使用时间，支持后续基于时间衰减的排序

### 5.6 图像生成接口

**三种生成分支并存**，覆盖不同 provider：
- OpenAI Images API（`gpt-image-1` 默认）
- OpenAI Responses API + `image_generation` tool（`gpt-5` 默认）
- JS 脚本生图（复用 Legado Rhino 引擎 + BaseSource 体系）

**JS 脚本生图的复用深度**值得注意：
- `AiImageJsSource` 继承 `BaseSource`，可使用书源的 `cookie/cache/header/loginUrl/jsLib`
- 这意味着用户可以编写自定义 JS 脚本接入任意图像 API（如国内厂商），无需 App 内置适配
- 与 Legado 书源脚本机制完全对齐，学习成本极低

### 5.7 与 Legado 现有功能的集成点

Archive AI 模块**深度复用** Legado 基础设施，集成点包括：

| 集成点 | Archive 实现 | 复用的 Legado 模块 |
|--------|-------------|------------------|
| 书源搜索 | `AiBookshelfTool` 调用 `WebBook` | `model/webBook/WebBook` |
| 书源抓取 HTML | `AiBookSourceTool.fetch_source_html` | `model/analyzeRule/AnalyzeUrl` |
| 书源调试 | `AiBookSourceTool.debug_book_source` | `model/Debug` |
| JS 生图脚本 | `AiImageService.generateByJs` | `com.script.rhino.RhinoScriptEngine` + `BaseSource` |
| 书架数据 | `AiBookshelfTool.queryBookshelf` | `data/appDb.bookDao` |
| 阅读记录 | `AiBookshelfTool` 的 `query_read_records` | `data/appDb.readRecordDao`（推断） |
| 角色数据 | `AiBookCharacterTool` | `data/entities/BookCharacter` + `appDb.bookCharacterDao` |
| Cookie 共享 | JS 生图脚本 `bindings["cookie"]` | `help/http/CookieStore` |
| 缓存共享 | JS 生图脚本 `bindings["cache"]` | `help/CacheManager` |
| HTTP 客户端 | 所有 AI HTTP 调用 | `help/http/okHttpClient` |
| 应用配置 | `AppConfig.aiXxx` 系列字段 | `help/config/AppConfig` |
| 事件总线 | `AiBookshelfTool` `postEvent` | `constant/EventBus` |
| 日志 | `AiImageService.logRequest` | `constant/AppLog.put` |

**关键结论**：AI 模块并非孤立子系统，而是**寄生在 Legado 已有基础设施之上**的增强层。这降低了借鉴的工程成本——核心基础设施（HTTP/JS/书源/书架/Cookie/Cache）无需改造，只需新增 AI 专属代码。

### 5.8 工程质量观察

- **错误处理统一**：所有工具返回 `{"ok":bool,"error":string,...}` 结构化 JSON，便于 `AiAgentValidator` 统一校验
- **脱敏严格**：`safeDebugPayload` 自动 redact Bearer/api_key/token/secret/image base64，符合安全规范
- **可观测性**：每次工具调用、模型请求、状态变更都通过 `AiAgentStateStore.trace` 落盘，支持事后复盘
- **版本化设计**：工具启用列表版本化（`TOOL_SETTINGS_VERSION`），MCP 协议版本化（`2025-06-18`），支持平滑升级

---

## 6. 建议决策

### 6.1 借鉴（理由 + 后续 spec 名建议 + 借鉴步骤）

| 借鉴项 | 理由 | 后续 spec 名建议 | 借鉴步骤 |
|-------|------|----------------|---------|
| **MCP 客户端**（AI-014） | MCP 是 2025 AI 工具生态标准，支持后可接入文件系统/数据库/Git 等任意 MCP 服务器，扩展性极强；Archive 实现完整且独立，约 420 行代码可整体移植 | `SA-3-mcp-client.md` | 1. 复制 `AiMcpClient.kt` + `AiMcpServerConfig` 实体 + DAO；2. 移植 SSE 解析逻辑；3. 接入 `AppConfig.aiMcpServerList`；4. 暴露给 Agent 工具注册中心 |
| **Tavily 联网搜索**（AI-010） | 173 行轻量实现，复用现有 `okHttpClient`，立即获得 AI 联网能力；Tavily 免费额度足够个人使用 | `SA-3-tavily-search.md` | 1. 复制 `AiTavilyTool.kt`；2. 新增 `AppConfig.aiTavilyEnabled/aiTavilyApiKey/aiTavilyBaseUrl/aiTavilyTopic/aiTavilySearchDepth/aiTavilyMaxResults` 字段；3. 接入工具注册中心 |
| **AiResolvedTool 抽象 + 工具注册中心**（AI-002） | 这是整个 AI 工具体系的"接口契约"，借鉴后可让本项目任何功能暴露为 AI 工具，不依赖是否引入完整 Agent | `SA-3-tool-registry.md` | 1. 复制 `AiResolvedTool` data class + `AiToolRegistry` object 骨架；2. 简化版本迁移机制（首版仅 v1）；3. 先注册 3-5 个只读工具作为试点 |
| **上下文压缩与摘要**（AI-007） | 长对话必备能力，185 行独立模块，无外部依赖；token 估算公式虽粗略但实用 | `SA-3-context-manager.md` | 1. 复制 `AiContextManager.kt`；2. 复制 `AiContextSummary` 数据类；3. 接入 `AppConfig.aiContextWindowTokens/aiContextCompressionEnabled`；4. 在请求构造前调用 `prepare` |
| **备用模型 Fallback**（AI-016） | 60 行轻量逻辑，遇超时/429/5xx 自动切换备用模型，提升 AI 体验稳定性；与具体 Agent 框架解耦 | `SA-3-model-fallback.md` | 1. 复制 `isAiFastFallbackCandidate` + `isAiRetryableRequestFailure`；2. 在 AI 请求包装层加 `requestCompletionStreamWithFallback`；3. 新增 `fallbackModelConfig` 配置项 |
| **调试日志脱敏**（AI-018） | 10 行正则替换，安全收益高，可直接复制到任何 AI 日志路径 | （并入 `SA-3-tool-registry.md`） | 1. 复制 `safeDebugPayload` 函数；2. 应用到所有 AI 请求/响应日志 |
| **JS 脚本生图**（AI-013） | 复用 Legado 已有 Rhino + BaseSource 体系，用户可自定义接入任意图像 API；与书源脚本机制对齐，学习成本低 | `SA-3-js-image-gen.md` | 1. 复制 `AiImageService.generateByJs` + `AiImageJsSource`；2. 复制图像格式归一化逻辑；3. 新增 `AiImageProviderConfig` 实体（type=js） |
| **工具结果校验机制**（AI-004） | 写入类工具必须有"可核对字段"，避免模型误报成功；约 120 行独立逻辑 | （并入 `SA-3-tool-registry.md`） | 1. 复制 `AiAgentValidator`；2. 在工具执行后调用 `validateToolResult`；3. 失败可重试时退避重试 |

### 6.2 不借鉴（理由）

| 不借鉴项 | 理由 |
|---------|------|
| **Agent 状态持久化与恢复**（AI-005） | 需要新增 3 张数据库表（Session/Job/Trace）+ migration + DAO，工程量大；本项目若仅做轻量 AI 集成，单次会话内存状态足够；待 Agent 任务长期化需求明确后再评估 |
| **长期记忆系统**（AI-008） | 需要 FTS 全文索引表 + 候选集召回 + 关键词打分，复杂度高；本项目若仅做问答式 AI，上下文压缩已足够；待用户表达"AI 应该记住我的偏好"需求后再评估 |
| **完整 AiChatService**（AI-015, AI-017） | 1859 行单文件巨型服务，强耦合 `AiAgentMode/AiChatCompanionConfig/AiWorldBookManager` 等众多子系统，整体移植成本极高；建议仅借鉴其 fallback/双 API 模式等独立片段 |
| **AI Workspace 文件编辑系统**（AI-020） | 21 个工具 + 复杂的备份/差异/正则替换逻辑，约 2000+ 行代码；本项目无类似工作区需求，引入后维护成本高 |
| **世界书系统**（AI-026） | 与 Legado 阅读场景强耦合，需要新增实体 + DAO + 多位置注入逻辑；属于 Archive 特有的"角色扮演阅读"功能，与本项目定位可能不符 |

### 6.3 待评估（理由 + 评估要点）

| 待评估项 | 理由 | 评估要点 |
|---------|------|---------|
| **Agent 计划器**（AI-006） | 关键词驱动生成 5 步计划，逻辑简单但效果依赖模型遵循；若本项目 Agent 任务简单可能收益有限 | 1. 本项目预期 Agent 任务复杂度；2. 模型对计划提示的遵循度；3. 是否有更轻量的替代方案 |
| **对话记忆自动抽取**（AI-009） | 关键词触发偏好抽取，无需 LLM 调用，成本低；但中文关键词识别准确率待验证 | 1. 在本项目实际对话中测试关键词命中率；2. 抽取的偏好是否真的有用；3. 是否会引入噪声 |
| **OpenAI Responses API 支持**（AI-017） | Responses API 是 OpenAI 新标准，支持 reasoning/image_generation 等内置 tool；但 Chat Completions 仍是主流 | 1. 本项目目标用户使用的 provider 是否主推 Responses API；2. 维护双 API 模式的复杂度 |
| **角色配音/朗读配乐**（AI-027） | 4 文件构成的朗读 AI 增强子系统，与 Legado 朗读功能强耦合 | 1. 本项目朗读功能的使用率；2. AI 增强朗读的边际收益；3. 与现有 TTS 引擎的集成成本 |
| **任务保活**（AI-029） | `AiTaskKeepAlive` 文件未深入读取，从命名推断为前台服务保活 | 1. Android 前台服务限制（API 34+）；2. 用户对后台 AI 任务的接受度；3. 替代方案（WorkManager） |

---

## 7. 借鉴实施路径建议

### 路径 1：AI Agent 核心架构（最小可用版）

**目标**：在本项目引入最小可用的 AI Agent 体系，支持工具调用 + 上下文压缩 + 模型 fallback，不引入状态持久化/记忆/世界书等重模块。

**阶段 1：基础抽象（约 800 行新代码）**
- 新增 `help/ai/AiResolvedTool.kt`（10 行 data class）
- 新增 `help/ai/AiToolRegistry.kt`（200 行，简化版，无版本迁移）
- 新增 `help/ai/AiToolExecutor.kt`（110 行，超时+重试+白名单）
- 新增 `help/ai/AiAgentValidator.kt`（150 行，写入工具校验）
- 新增 `help/ai/AiContextManager.kt`（185 行，上下文压缩）
- 新增 `AppConfig` 字段：`aiEnabled/aiContextWindowTokens/aiContextCompressionEnabled/aiEnabledToolNames/aiAgentMaxToolRounds/aiAgentToolMaxAttempts`

**阶段 2：核心服务（约 600 行新代码）**
- 新增 `help/ai/AiChatService.kt`（精简版，约 400 行，仅 Chat Completions + Fallback + 脱敏，不含 Responses API/World Book/Memory）
- 新增 `help/ai/AiAgentRuntime.kt`（300 行，Tool Loop + ValidatedToolExecution，不含 Checkpoint/Goal 模式）
- 新增 `ui/main/ai/AiChatMessage.kt` + `AiProviderConfig.kt` + `AiModelConfig.kt` 数据类

**阶段 3：试点工具（约 300 行新代码）**
- 新增 `help/ai/AiTavilyTool.kt`（173 行，联网搜索，立即可用）
- 新增 `help/ai/AiBookshelfTool.kt`（精简版，仅 `query_bookshelf` + `get_bookshelf_book_info` 2 个工具）
- 验证：完成"问 AI 我书架里有什么书"端到端流程

**阶段 4：MCP 扩展（约 420 行新代码）**
- 新增 `help/ai/AiMcpClient.kt`（420 行，完整移植）
- 新增 `ui/main/ai/AiMcpServerConfig.kt` 数据类 + DAO
- 新增 `AppConfig.aiMcpServerList/aiEnabledMcpServers` 字段
- 验证：完成"通过 MCP 调用外部工具"端到端流程

**阶段 5：JS 脚本生图（约 280 行新代码）**
- 新增 `help/ai/AiImageService.kt`（仅 `generateByJs` 分支 + 图像归一化，约 280 行）
- 新增 `ui/main/ai/AiImageProviderConfig.kt` 数据类
- 验证：完成"用户编写 JS 脚本接入自定义图像 API"端到端流程

**总成本估算**：约 2400 行新代码，分 5 阶段渐进交付，每阶段独立可验证。

**风险与缓解**：
- 风险 1：Archive 的 `AppConfig` 字段众多，移植时需逐一确认；缓解：首版仅移植必需字段，其余按需追加。
- 风险 2：`AiChatService` 强耦合 `AiChatCompanionConfig/AiWorldBookManager` 等；缓解：阶段 2 精简版剔除耦合，仅保留核心请求逻辑。
- 风险 3：UI 层未在本次分析范围；缓解：UI 移植需单独 spec（建议 `SA-3-ai-ui.md`）。

---

## 8. 附录

### 8.1 Archive AI 文件完整清单（35 个）

| 分类 | 文件 | 行数估算 | 职责 |
|------|------|---------|------|
| **Agent 核心** | `AiAgentRuntime.kt` | 505 | Tool Loop 主循环 |
| | `AiAgentRuntimeTypes.kt` | 21 | ToolCall/AssistantTurn/Options 数据类 |
| | `AiAgentStateStore.kt` | 222 | Session/Job/Trace 持久化 |
| | `AiAgentPlanner.kt` | 137 | 关键词驱动计划生成 |
| | `AiAgentValidator.kt` | 153 | 工具结果校验 |
| | `AiAgentInterruption.kt` | 29 | 用户中断处理 |
| **工具体系** | `AiToolRegistry.kt` | 500 | 工具注册中心 + 版本迁移 |
| | `AiToolExecutor.kt` | 128 | 执行器（超时/重试/白名单） |
| **聊天服务** | `AiChatService.kt` | 1859 | 主聊天服务（双 API/多模式/Fallback） |
| | `AiContextManager.kt` | 185 | 上下文压缩与摘要 |
| **联网搜索** | `AiTavilyTool.kt` | 173 | Tavily 搜索工具 |
| **记忆系统** | `AiMemoryStore.kt` | 235 | 存储 + 检索 + 抽取三组件 |
| **图像** | `AiImageService.kt` | 490 | OpenAI + Responses + JS 三分支 |
| | `AiImageTool.kt` | - | 图像工具封装 |
| | `AiImagePromptRewriter.kt` | - | Prompt 重写 |
| | `AiImageGalleryManager.kt` | - | 图库管理 |
| **MCP** | `AiMcpClient.kt` | 423 | MCP 协议客户端 |
| **Legado 集成工具** | `AiBookshelfTool.kt` | - | 书架/章节/阅读记录 |
| | `AiBookSourceTool.kt` | - | 书源 CRUD + 调试 |
| | `AiReadingNetworkTool.kt` | - | Ajax/WebView/抓包 |
| | `AiLibraryTool.kt` | - | （推断）本地书库 |
| | `AiSettingsTool.kt` | - | 应用设置 |
| | `AiWorkspaceTool.kt` | - | 21 个工作区文件工具 |
| | `AiBookCharacterTool.kt` | - | 角色资料 + 关系网 |
| | `AiReadAloudBgmTool.kt` | - | 朗读配乐工具 |
| | `AiReadAloudBgmService.kt` | - | 朗读配乐服务 |
| | `AiReadAloudRoleState.kt` | - | 朗读角色状态 |
| | `AiReadAloudUsageRecorder.kt` | - | 朗读使用记录 |
| | `AiWorldBookTool.kt` | - | 世界书工具 |
| | `AiWorldBookManager.kt` | - | 世界书管理器 |
| **辅助** | `AiSkillPromptTool.kt` | 100+ | Skill 加载工具 |
| | `AiChapterSummaryService.kt` | - | 章节摘要服务 |
| | `AiTaskKeepAlive.kt` | - | 任务保活 |

### 8.2 行号锚点验证清单

| 文件 | 关键行号 | 内容 |
|------|---------|------|
| `AiAgentRuntime.kt` | L13 | `internal object AiAgentRuntime` |
| | L17 | `suspend fun runToolLoop` |
| | L306 | `private suspend fun executeValidatedTool` |
| `AiToolRegistry.kt` | L6 | `data class AiResolvedTool` |
| | L12 | `object AiToolRegistry` |
| | L401 | `private fun nativeResolvedTools` |
| `AiToolExecutor.kt` | L10 | `internal object AiToolExecutor` |
| | L45 | `suspend fun execute` |
| `AiChatService.kt` | L55 | `object AiChatService` |
| | L96 | `suspend fun chat` |
| | L275 | `suspend fun chatStream` |
| | L506 | `requestCompletionStreamWithFallback` |
| | L1614 | `buildModeSystemPrompt` |
| `AiContextManager.kt` | L7 | `object AiContextManager` |
| | L22 | `fun prepare` |
| `AiMemoryStore.kt` | L52 | `object AiMemoryStore` |
| | L100 | `object AiMemoryRetriever` |
| | L175 | `object AiMemoryExtractor` |
| `AiImageService.kt` | L28 | `object AiImageService` |
| | L86 | `generateByImagesApi` |
| | L144 | `generateByResponses` |
| | L221 | `generateByJs` |
| `AiMcpClient.kt` | L15 | `object AiMcpClient` |
| | L17 | `PROTOCOL_VERSION = "2025-06-18"` |
| | L45 | `suspend fun resolveTools` |
| | L172 | `ensureSession` |
| `AiAgentStateStore.kt` | L10 | `object AiAgentStateStore` |
| | L21 | `fun startRun` |
| | L61 | `fun trace` |
| `AiAgentPlanner.kt` | L64 | `object AiAgentPlanner` |
| | L66 | `fun create` |
| `AiAgentValidator.kt` | L22 | `internal object AiAgentValidator` |
| | L36 | `fun validateToolResult` |

---

**报告完成时间**：2026-07-18
**分析文件数**：12（Archive 11 + 本项目 1 验证）
**关键代码段数**：8 段（含 kotlin 代码块）
**差异清单条目数**：30 条
**关键发现条目数**：8 条（含 5.1-5.8）
**建议决策三态**：借鉴 8 项 + 不借鉴 5 项 + 待评估 5 项
**借鉴实施路径**：1 条 5 阶段路径
