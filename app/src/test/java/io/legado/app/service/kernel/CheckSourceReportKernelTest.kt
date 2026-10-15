package io.legado.app.service.kernel

import io.legado.app.data.entities.BookSourcePart
import io.legado.app.model.CheckSourceItemStatus
import io.legado.app.model.CheckSourceTaskStore
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 巡检报告读出口径（`SourceDebugKernel.checkSourceReport`）行为护栏 —— 缺口4 后半。
 *
 * 不变量：①与 App 内导出**同源**（都读 `CheckSourceTaskStore` 结构化任务态）；
 * ②出参面向 HTTP/MCP 边界 ⇒ **源地址打码 + 消息截断**（用户自己的 CSV 导出才保留原文）；
 * ③空/未跑过巡检时不报错，`total=0`。
 */
class CheckSourceReportKernelTest {

    private val origin = "http://a.example/search?token=SECRET123"

    @Test
    fun report_projectsStructuredTaskState_andMasksOrigin() = runBlocking {
        // 全局单例状态：先收口其他用例可能遗留的 RUNNING 态，否则 begin 会被静默忽略
        // （定向单跑通过、全套件跑挂的典型顺序依赖 —— 见本文件类 KDoc）
        CheckSourceTaskStore.finish(cancelled = true)
        CheckSourceTaskStore.begin(listOf(BookSourcePart(bookSourceUrl = origin)))
        CheckSourceTaskStore.markRunning(origin, "源甲", 0)
        CheckSourceTaskStore.markPassed(origin, durationMillis = 1200L, score = 90)
        CheckSourceTaskStore.finish(cancelled = false)

        val report = SourceDebugKernel.checkSourceReport()
        assertEquals("COMPLETED", report["status"])
        assertEquals("总数须与任务态一致", 1, report["total"])
        assertEquals("通过数须与任务态一致", 1, report["passed"])
        assertEquals("平均分须取通过项均分", 90, report["averageScore"])

        @Suppress("UNCHECKED_CAST")
        val items = report["items"] as List<Map<String, Any?>>
        assertEquals(1, items.size)
        val item = items.single()
        assertEquals("源甲", item["name"])
        assertEquals(CheckSourceItemStatus.PASSED.name, item["status"])
        assertEquals(1200L, item["durationMs"])
        assertEquals(90, item["score"])
        val masked = item["origin"] as String
        assertFalse("出参边界不得回传原文凭据", masked.contains("SECRET123"))
        assertTrue("敏感 query 须打码为 ***", masked.contains("***"))
    }

    @Test
    fun report_emptyRun_returnsZerosWithoutError() = runBlocking {
        CheckSourceTaskStore.finish(cancelled = true)
        CheckSourceTaskStore.begin(emptyList())
        CheckSourceTaskStore.finish(cancelled = false)

        val report = SourceDebugKernel.checkSourceReport()
        assertEquals("空跑不得报错，计数为 0", 0, report["total"])
        @Suppress("UNCHECKED_CAST")
        assertTrue("空跑 items 为空表", (report["items"] as List<*>).isEmpty())
        assertEquals(0, report["averageScore"] ?: 0)
    }
}
