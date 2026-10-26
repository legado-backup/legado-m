package io.legado.app.web.mcp

import com.google.gson.JsonObject
import io.legado.app.web.TokenManager
import kotlinx.coroutines.delay
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * MCP 按工具超时 / 长任务异步化 / 失败语义分离 单元测试（design AD-11 / tasks 3.8）。
 *
 * 断言要点（带期望值）：
 * 1. **工具声明值优先于全局默认**（`resolveTimeoutMs`）；
 * 2. 超时分支的 `errorKind == "timeout"`，业务失败分支为 `"tool_error"`（**可区分**，不靠文案解析）；
 * 3. `async=true` 时立即返回 `taskId`（不在同步调用里等待），且任务随后可被 `McpTaskRegistry.status` 查到。
 *
 * 已知上限：不覆盖真机 90s 长任务（真机档见 tasks 5.4）| 升级路径：设备档脚本按 `task_result` 轮询取证。
 */
class McpToolTimeoutTest {

    private fun tool(
        name: String = "t",
        timeoutMs: Long? = null,
        asyncEligible: Boolean = false,
        block: suspend (McpArgs) -> Any? = { "ok" },
    ) = McpTool(
        name = name,
        level = TokenManager.Level.MANAGE,
        timeoutMs = timeoutMs,
        asyncEligible = asyncEligible,
        invoke = block,
    )

    private fun args(json: String = "{}") = McpArgs(McpJson.gson.fromJson(json, JsonObject::class.java))

    // ============ 1. 超时优先级 ============

    @Test
    fun resolveTimeoutMs_prefersToolDeclaration() {
        assertEquals(
            "工具声明值必须优先于 15s 全局默认",
            90_000L,
            McpToolExecutor.resolveTimeoutMs(tool(timeoutMs = 90_000L)),
        )
    }

    @Test
    fun resolveTimeoutMs_fallsBackToDefault() {
        assertEquals(
            "未声明时用全局默认",
            McpToolExecutor.DEFAULT_TOOL_TIMEOUT_MS,
            McpToolExecutor.resolveTimeoutMs(tool(timeoutMs = null)),
        )
        assertEquals(
            "非正值视为未声明（防御性）",
            McpToolExecutor.DEFAULT_TOOL_TIMEOUT_MS,
            McpToolExecutor.resolveTimeoutMs(tool(timeoutMs = 0L)),
        )
    }

    // ============ 2. 失败语义分离 ============

    @Test
    fun timeout_producesTimeoutErrorKind() = runBlocking {
        val env = McpToolExecutor.execute(
            tool = tool(block = { delay(500); "late" }),
            args = args(),
            requestId = "r1",
            timeoutMs = 10L,
        )
        assertEquals("超时必须 ok=false", false, env.get("ok").asBoolean)
        assertEquals(
            "超时必须标注 errorKind=timeout（与业务失败可区分）",
            McpToolExecutor.ERROR_KIND_TIMEOUT,
            env.get("errorKind").asString,
        )
    }

    @Test
    fun businessFailure_producesToolErrorKind() = runBlocking {
        val env = McpToolExecutor.execute(
            tool = tool(block = { throw IllegalStateException("站点返回异常结构") }),
            args = args(),
            requestId = "r2",
            timeoutMs = 1000L,
        )
        assertEquals("业务失败 ok=false", false, env.get("ok").asBoolean)
        assertEquals(
            "业务失败必须标注 errorKind=tool_error",
            McpToolExecutor.ERROR_KIND_TOOL,
            env.get("errorKind").asString,
        )
        assertTrue(
            "业务失败文案应含原始原因（便于定位）",
            env.get("error").asString.contains("站点返回异常结构"),
        )
    }

    @Test
    fun success_hasNoErrorKind() = runBlocking {
        val env = McpToolExecutor.execute(
            tool = tool(block = { mapOf("n" to 1) }),
            args = args(),
            requestId = "r3",
            timeoutMs = 1000L,
        )
        assertEquals("成功 ok=true", true, env.get("ok").asBoolean)
        assertNull("成功信封不应带 errorKind", env.get("errorKind"))
    }

    // ============ 3. 长任务异步化 ============

    @Test
    fun asyncCall_returnsTaskIdImmediately_andTaskIsQueryable() = runBlocking {
        McpTaskRegistry.clearForTest()
        val env = McpToolExecutor.execute(
            tool = tool(name = "long_tool", timeoutMs = 5_000L, asyncEligible = true,
                block = { delay(200); mapOf("done" to true) }),
            args = args("""{"async":true}"""),
            requestId = "r4",
        )
        assertEquals("异步提交应立即返回 ok=true", true, env.get("ok").asBoolean)
        val data = env.get("data").asJsonObject
        val taskId = data.get("taskId").asString
        assertTrue("taskId 应形如 task-xxx", taskId.startsWith("task-"))
        assertEquals("提交时应为 running", "running", data.get("state").asString)

        delay(600)
        val entry = McpTaskRegistry.status(taskId)
        assertNotNull("任务应可被轮询到", entry)
        assertEquals("任务应已完成", McpTaskRegistry.State.DONE, entry!!.state)
        assertEquals("结果应携带业务数据", true, entry.result!!.get("ok").asBoolean)
    }

    @Test
    fun asyncFlagWithoutEligibility_staysSynchronous() = runBlocking {
        // 未声明 asyncEligible 的工具，即使调用方传 async=true 也保持同步语义（不改变既有行为）
        val env = McpToolExecutor.execute(
            tool = tool(name = "short_tool", asyncEligible = false, block = { mapOf("n" to 2) }),
            args = args("""{"async":true}"""),
            requestId = "r5",
            timeoutMs = 1000L,
        )
        assertEquals("应直接返回业务结果（ok=true）", true, env.get("ok").asBoolean)
        val data: JsonObject = env.get("data").asJsonObject
        assertEquals("不应返回 taskId", false, data.has("taskId"))
        assertEquals("应返回业务载荷", 2, data.get("n").asInt)
    }
}