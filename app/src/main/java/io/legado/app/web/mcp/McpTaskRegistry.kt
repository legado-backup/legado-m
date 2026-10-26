package io.legado.app.web.mcp

import com.google.gson.JsonObject
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch
import java.util.concurrent.ConcurrentHashMap

/**
 * MCP **长任务异步注册表**（design AD-11 / spec Requirement A-6）。
 *
 * 背景（实测根因）：`McpToolExecutor` 的超时原为**全局硬编码 15s**，而五链调试 / 取流验证 /
 * 质量报告这类工具需要多次网络往返，站点抗压时单请求可达 0.4s↔20s ⇒ 必然在 15s 处被截断，
 * 表现为「明明在做，却总是超时」。
 *
 * 三层解法：
 * 1. **按工具覆盖超时**：`McpTool.timeoutMs`（`null` ⇒ 全局默认）；
 * 2. **长任务异步化**（本类）：工具声明 `asyncEligible = true` 且调用方传 `async = true` 时，
 *    立即返回任务 id（`state=running`），由 `task_result` 轮询取结果 —— 不再占用同步请求；
 * 3. **语义分离**：超时（`errorKind=timeout`）与业务失败（`errorKind=tool_error`）在信封里可区分。
 *
 * 保留策略：最多保留 [MAX_ENTRIES] 条最近任务（超出按完成时间淘汰最旧），
 * 避免长会话下无界增长；单任务结果已按 [McpToolExecutor.MAX_RESPONSE_BYTES] 截断。
 */
object McpTaskRegistry {

    /** 任务状态。 */
    enum class State { RUNNING, DONE, FAILED }

    /** 一条任务记录（`result` 为 `McpToolExecutor` 组好的信封）。 */
    data class Entry(
        val id: String,
        val tool: String,
        val state: State,
        val startedAt: Long,
        val finishedAt: Long?,
        val result: JsonObject?,
    )

    /** 最多保留的历史任务数。 */
    const val MAX_ENTRIES = 64

    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    private val entries = ConcurrentHashMap<String, Entry>()
    private val order = ArrayDeque<String>()

    /**
     * 提交长任务，立即返回任务 id。
     *
     * @param block 实际执行体；其返回值为 `McpToolExecutor` 组好的**信封**（含 ok/error/elapsedMs）
     */
    fun submit(toolName: String, block: suspend () -> JsonObject): String {
        val id = "task-" + java.util.UUID.randomUUID().toString().replace("-", "").take(16)
        val entry = Entry(
            id = id, tool = toolName, state = State.RUNNING,
            startedAt = System.currentTimeMillis(), finishedAt = null, result = null,
        )
        put(id, entry)
        scope.launch {
            val finished = try {
                val env = block()
                entry.copy(
                    state = if (env.get("ok")?.asBoolean == true) State.DONE else State.FAILED,
                    finishedAt = System.currentTimeMillis(),
                    result = env,
                )
            } catch (e: Throwable) {
                // 长任务体内的未捕获异常也必须成为**可轮询的结果**，否则调用方永远看不到原因
                entry.copy(
                    state = State.FAILED,
                    finishedAt = System.currentTimeMillis(),
                    result = McpToolExecutor.envelope(
                        ok = false, data = null,
                        errorMsg = e.localizedMessage ?: e.message ?: "长任务执行失败",
                        elapsedMs = System.currentTimeMillis() - entry.startedAt,
                        requestId = id, errorKind = McpToolExecutor.ERROR_KIND_TOOL,
                    ),
                )
            }
            put(id, finished)
        }
        return id
    }

    /** 查询任务；不存在返回 `null`。 */
    fun status(id: String): Entry? = entries[id]

    private fun put(id: String, entry: Entry) {
        entries[id] = entry
        synchronized(order) {
            if (order.lastOrNull() != id) order.addLast(id)
            while (order.size > MAX_ENTRIES) {
                val evicted = order.removeFirst()
                entries.remove(evicted)
            }
        }
    }

    /** 仅供单测：清空注册表。 */
    internal fun clearForTest() {
        entries.clear()
        synchronized(order) { order.clear() }
    }
}
