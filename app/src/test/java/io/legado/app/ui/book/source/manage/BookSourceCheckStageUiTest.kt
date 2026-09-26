package io.legado.app.ui.book.source.manage

import java.io.File
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * R 批 §3.2.3 `Q-N5` 页面接线不变量（源码文本断言）：
 * 书源管理页须把结构化校验状态接进横幅与列表行，且**保留**既有失效源自动筛选链路。
 */
class BookSourceCheckStageUiTest {

    private fun read(rel: String): String {
        val f = listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
        return f.readText()
    }

    private fun activity() = read("src/main/java/io/legado/app/ui/book/source/manage/BookSourceActivity.kt")

    private fun screen() = read("src/main/java/io/legado/app/ui/book/source/manage/BookSourceScreen.kt")

    @Test
    fun activitySubscribesTaskStoreAndFeedsBanner() {
        val t = activity()
        assertTrue("须订阅结构化状态", t.contains("CheckSourceTaskStore.state.collect"))
        assertTrue("横幅须优先用结构化文案", t.contains("bannerText() ?: checkBannerState.value"))
        assertTrue("须下发单源过程文案", t.contains("runningStageText()"))
    }

    @Test
    fun resultStateCancelBecomesDismissOnly() {
        val t = activity()
        assertTrue("结果态动作须退化为确认回执", t.contains("CheckSourceTaskStore.markResultsAcknowledged()"))
        // 回归护栏：只有「已结束」态才关闭回执；RUNNING/IDLE（旧路径未建状态）必须仍走既有停止逻辑
        assertTrue(
            "取消按钮不得在未建状态的链路上变成空动作",
            t.contains(
                "status == CheckSourceTaskStatus.COMPLETED || status == CheckSourceTaskStatus.CANCELLED"
            )
        )
    }

    @Test
    fun existingAutoFilterIsPreserved() {
        val t = activity()
        // 回归护栏：CHECK_SOURCE_DONE 后「自动筛选失效源」链路必须保留
        assertTrue(t.contains("EventBus.CHECK_SOURCE_DONE"))
        assertTrue(t.contains("updateSearchQuery(FAILED_SOURCE_GROUP_KEY)"))
        assertTrue(t.contains("发现有失效书源，已为您自动筛选！"))
    }

    @Test
    fun screenRendersStageTextAndResultBanner() {
        val t = screen()
        assertTrue("行副标题须用过程文案", t.contains("checkStageTexts[source.bookSourceUrl]"))
        assertTrue(
            "结果态横幅须停止转圈",
            t.contains("if (checkBannerRunning) InlineTaskState.Running else InlineTaskState.Done")
        )
    }
}