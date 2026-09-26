package io.legado.app.model

import io.legado.app.data.entities.BookSourcePart
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * R 批 §3.2.3 `Q-N5` 校验过程状态机（纯 JVM 行为级）。
 *
 * 覆盖：七阶段推进 / 完成与取消收口 / 计数与进度 / 结果评分均值 / 横幅与行文案 /
 * 结束后事件不再污染状态（`updateItem` 守卫）。
 */
class CheckSourceTaskStoreTest {

    private fun part(url: String, name: String = "源$url") =
        BookSourcePart(bookSourceUrl = url, bookSourceName = name, bookSourceType = 1)

    private fun beginTwo() {
        CheckSourceTaskStore.begin(listOf(part("u1"), part("u2")))
    }

    // ---- 任务建立与阶段推进 ----

    @Test
    fun begin_createsWaitingItems() {
        beginTwo()
        val state = CheckSourceTaskStore.state.value
        assertEquals(CheckSourceTaskStatus.RUNNING, state.status)
        assertEquals(2, state.totalCount)
        assertEquals(0, state.processedCount)
        assertTrue(state.items.all { it.status == CheckSourceItemStatus.WAITING })
    }

    @Test
    fun markStage_advancesSingleItemStage() {
        beginTwo()
        CheckSourceTaskStore.markRunning("u1", "真实名", 2)
        CheckSourceTaskStore.markStage("u1", "真实名", CheckSourceStage.SEARCH)
        val item = CheckSourceTaskStore.state.value.items.first { it.origin == "u1" }
        assertEquals(CheckSourceItemStatus.RUNNING, item.status)
        assertEquals(CheckSourceStage.SEARCH, item.stage)
        assertEquals("真实名", item.sourceName)
        assertEquals(2, item.sourceType)
        assertEquals("校验中·搜索", item.runningStageText())
        // 另一个源未开始 ⇒ 不产生过程噪声
        assertEquals(
            "",
            CheckSourceTaskStore.state.value.items.first { it.origin == "u2" }.runningStageText()
        )
    }

    @Test
    fun stageMarksAfterFinish_areIgnored() {
        beginTwo()
        CheckSourceTaskStore.markRunning("u1", "a", 1)
        CheckSourceTaskStore.finish(cancelled = false)
        CheckSourceTaskStore.markStage("u1", "a", CheckSourceStage.CONTENT)
        val item = CheckSourceTaskStore.state.value.items.first { it.origin == "u1" }
        assertEquals("结束后不得再污染状态", CheckSourceItemStatus.RUNNING, item.status)
    }

    // ---- 完成 / 取消收口 ----

    @Test
    fun passAndFail_countsAndProgress() {
        beginTwo()
        CheckSourceTaskStore.markRunning("u1", "a", 1)
        CheckSourceTaskStore.markPassed("u1", durationMillis = 12L, score = 80)
        CheckSourceTaskStore.markRunning("u2", "b", 1)
        CheckSourceTaskStore.markFailed("u2", "网站失效", durationMillis = 30L)
        CheckSourceTaskStore.finish(cancelled = false)
        val state = CheckSourceTaskStore.state.value
        assertEquals(CheckSourceTaskStatus.COMPLETED, state.status)
        assertEquals(1, state.passedCount)
        assertEquals(1, state.failedCount)
        assertEquals(2, state.processedCount)
        assertEquals(0, state.remainingCount)
        assertEquals(1f, state.progressFraction)
        assertEquals(80, state.averageScore)
        assertEquals("网站失效", state.items.first { it.origin == "u2" }.message)
    }

    @Test
    fun cancel_marksRunningItemCancelledAndKeepsFinished() {
        beginTwo()
        CheckSourceTaskStore.markRunning("u1", "a", 1)
        CheckSourceTaskStore.markPassed("u1", durationMillis = 1L, score = 60)
        CheckSourceTaskStore.markRunning("u2", "b", 1)
        CheckSourceTaskStore.markStage("u2", "b", CheckSourceStage.CATALOG)
        CheckSourceTaskStore.finish(cancelled = true)
        val state = CheckSourceTaskStore.state.value
        assertEquals(CheckSourceTaskStatus.CANCELLED, state.status)
        assertEquals(
            CheckSourceItemStatus.CANCELLED,
            state.items.first { it.origin == "u2" }.status
        )
        assertEquals(
            "已完成结果不得回滚",
            CheckSourceItemStatus.PASSED,
            state.items.first { it.origin == "u1" }.status
        )
        assertEquals(60, state.averageScore)
    }

    @Test
    fun finishTwice_isIdempotent() {
        beginTwo()
        CheckSourceTaskStore.finish(cancelled = false)
        CheckSourceTaskStore.finish(cancelled = true)
        assertEquals(CheckSourceTaskStatus.COMPLETED, CheckSourceTaskStore.state.value.status)
    }

    @Test
    fun unknownOrigin_isIgnored() {
        beginTwo()
        CheckSourceTaskStore.markRunning("nobody", "x", 1)
        assertTrue(
            "未登记源不得进入状态",
            CheckSourceTaskStore.state.value.items.none { it.origin == "nobody" }
        )
    }

    // ---- 横幅文案（过程 / 结果 / 确认后） ----

    @Test
    fun bannerText_runningShowsProgressAndCurrentStage() {
        beginTwo()
        CheckSourceTaskStore.markRunning("u1", "源甲", 1)
        CheckSourceTaskStore.markStage("u1", "源甲", CheckSourceStage.DISCOVERY)
        val text = CheckSourceTaskStore.state.value.bannerText().orEmpty()
        assertTrue("须含进度与通过/失败计数: $text", text.contains("校验中 0/2"))
        assertTrue("须含当前源名: $text", text.contains("源甲"))
        assertTrue("须含当前阶段: $text", text.contains("发现"))
    }

    @Test
    fun bannerText_completedShowsResultAndAverageScore() {
        beginTwo()
        CheckSourceTaskStore.markRunning("u1", "a", 1)
        CheckSourceTaskStore.markPassed("u1", durationMillis = 1L, score = 70)
        CheckSourceTaskStore.markRunning("u2", "b", 1)
        CheckSourceTaskStore.markFailed("u2", "x", durationMillis = 1L)
        CheckSourceTaskStore.finish(cancelled = false)
        val text = CheckSourceTaskStore.state.value.bannerText().orEmpty()
        assertTrue("须含结果计数: $text", text.contains("通过 1") && text.contains("失败 1"))
        assertTrue("须含结果评分均值: $text", text.contains("平均分 70"))
    }

    @Test
    fun bannerText_cancelledShowsPartialResult() {
        beginTwo()
        CheckSourceTaskStore.markRunning("u1", "a", 1)
        CheckSourceTaskStore.finish(cancelled = true)
        val text = CheckSourceTaskStore.state.value.bannerText().orEmpty()
        assertTrue("须含取消回执: $text", text.contains("已取消"))
    }

    @Test
    fun bannerText_acknowledgedOrIdleIsNull() {
        assertNull("IDLE 无横幅", CheckSourceTaskState().bannerText())
        beginTwo()
        CheckSourceTaskStore.finish(cancelled = false)
        assertNotNull(CheckSourceTaskStore.state.value.bannerText())
        CheckSourceTaskStore.markResultsAcknowledged()
        assertNull("确认后结果回执必须消失", CheckSourceTaskStore.state.value.bannerText())
    }

    @Test
    fun markResultsAcknowledged_doesNotInterruptRunningTask() {
        beginTwo()
        CheckSourceTaskStore.markResultsAcknowledged()
        val state = CheckSourceTaskStore.state.value
        assertEquals(CheckSourceTaskStatus.RUNNING, state.status)
        assertNotNull("进行中不得被确认动作关闭", state.bannerText())
    }
}