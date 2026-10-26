package io.legado.app.web.mcp.tools

import io.legado.app.web.TokenManager
import io.legado.app.web.mcp.McpToolCatalog
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 长任务工具声明 与 `task_result` 轮询工具 单元测试（design AD-11 / tasks 3.8）。
 *
 * 断言要点（带期望值）：
 * 1. **长任务工具必须声明覆盖 15s 的超时**（否则站点抗压时必然被截断——本轮真实踩坑）；
 * 2. `task_result` 存在、级别 `MANAGE`、`taskId` 为必填参数；
 * 3. 目录里**所有**工具名唯一（`task_result` 不得与既有工具重名）。
 */
class LongTaskToolDeclarationTest {

    /** 必须声明长超时的工具名（多次网络往返 / 站点抗压场景）。 */
    private val longTaskTools = listOf(
        "js_source_debug",
        "source_search_test",
        "source_info_test",
        "source_toc_test",
        "source_content_test",
        "source_explore_test",
        "rss_search_test",
        "rss_article_test",
        "validate_source",
        "validate_rss_source",
    )

    @Test
    fun longTaskTools_declareTimeoutAboveDefault() {
        val defaultMs = io.legado.app.web.mcp.McpToolExecutor.DEFAULT_TOOL_TIMEOUT_MS
        longTaskTools.forEach { name ->
            val tool = McpToolCatalog.find(name)
            assertNotNull("工具应存在：$name", tool)
            val declared = tool!!.timeoutMs
            assertNotNull("长任务工具必须显式声明 timeoutMs（不得靠 15s 默认）：$name", declared)
            assertTrue(
                "声明超时必须大于全局默认（实测 $defaultMs ms 不足以完成多次网络往返）：$name",
                declared!! > defaultMs,
            )
            assertTrue("长任务工具应允许 async 异步模式：$name", tool.asyncEligible)
        }
    }

    @Test
    fun taskResultTool_isDeclaredForPolling() {
        val tool = McpToolCatalog.find("task_result")
        assertNotNull("轮询工具 task_result 必须存在（异步长任务的结果出口）", tool)
        assertEquals("级别应为 MANAGE（与长工具同级）", TokenManager.Level.MANAGE, tool!!.level)
        val required = tool.inputSchema.getAsJsonArray("required").map { it.asString }
        assertTrue("taskId 必须是必填参数，否则轮询无从下手", "taskId" in required)
        assertTrue("说明里应提到用 taskId 轮询", tool.description.contains("taskId"))
    }

    @Test
    fun longTaskTools_areDistinctFromPollingTool() {
        val names = McpToolCatalog.all().map { it.name }
        assertEquals("工具名必须唯一（含 task_result）", names.size, names.toSet().size)
    }
}