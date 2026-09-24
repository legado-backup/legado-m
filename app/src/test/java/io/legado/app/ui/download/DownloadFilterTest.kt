package io.legado.app.ui.download

import io.legado.app.service.DownloadStatus
import io.legado.app.service.DownloadTask
import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * CP-2 回归测试：下载管理页 Tab 过滤与空态语义。
 *
 * 缺陷（2026-09-24 用户报障）：
 * ①「切 Tab 不生效」—— `DownloadManageActivity.onTabChange` 只写 `tabIndex`，
 *    过滤仅在 `DownloadState.tasks.collect{}` 内重算 ⇒ 无任务发射时点了没反应。
 * ②「上滑列表收缩消失」—— 筛后为空时 `when` 落到整页空态，列表容器被整体替换。
 *
 * 本测试覆盖：过滤纯函数口径（可 JVM 验证）+ 宿主/Screen 结构不变量（无 Robolectric，
 * 按源码结构断言，与同包 [DownloadHostRefreshHookTest] 同口径）。
 */
class DownloadFilterTest {

    private fun task(
        id: Long,
        status: DownloadStatus,
        startTime: Long
    ) = DownloadTask(
        id = id,
        url = "https://example.invalid/$id",
        fileName = "f$id",
        startTime = startTime,
        status = status
    )

    /** 混合状态样本：同一份数据换 Tab 必须得到不同结果（① 的核心回归面） */
    private val tasks = listOf(
        task(1, DownloadStatus.RUNNING, 100),
        task(2, DownloadStatus.WAITING, 200),
        task(3, DownloadStatus.PAUSED, 300),
        task(4, DownloadStatus.COMPLETED, 400),
        task(5, DownloadStatus.FAILED, 500)
    )

    private fun ids(tab: DownloadTab) = DownloadFilter.apply(tasks, tab.ordinal).map { it.id }

    @Test
    fun allTab_keepsEveryTask_sortedByStartTimeDesc() {
        assertEquals(listOf(5L, 4L, 3L, 2L, 1L), ids(DownloadTab.ALL))
    }

    @Test
    fun runningTab_coversRunningAndWaitingOnly() {
        assertEquals(listOf(2L, 1L), ids(DownloadTab.RUNNING))
    }

    @Test
    fun pausedCompletedFailedTabs_areScoped() {
        assertEquals(listOf(3L), ids(DownloadTab.PAUSED))
        assertEquals(listOf(4L), ids(DownloadTab.COMPLETED))
        assertEquals(listOf(5L), ids(DownloadTab.FAILED))
    }

    @Test
    fun sameTasks_differentTab_produceDifferentResults() {
        val completed = ids(DownloadTab.COMPLETED)
        assertFalse("点「已完成」后不应再出现下载中任务", completed.contains(1L))
        assertFalse(completed.contains(2L))
        assertTrue("换 Tab 必须得到不同结果（复现基线的反面）", completed != ids(DownloadTab.RUNNING))
    }

    @Test
    fun outOfRangeTabIndex_fallsBackToAll() {
        assertEquals(5, DownloadFilter.apply(tasks, -1).size)
        assertEquals(5, DownloadFilter.apply(tasks, DownloadTab.entries.size).size)
    }

    @Test
    fun screen_distinguishesCategoryEmptyFromGlobalEmpty() {
        val text = read("src/main/java/io/legado/app/ui/download/DownloadManageScreen.kt")
        assertTrue(
            "筛后为空须用区分文案（保留列表容器），不再整页替换",
            text.contains("R.string.download_tab_empty")
        )
        assertTrue("全空文案仍保留", text.contains("R.string.download_empty"))
        assertTrue(
            "空态判定须基于未过滤总量，否则无法区分两种语义",
            text.contains("totalTaskCount == 0")
        )
    }

    @Test
    fun activity_recomputesOnTabChange() {
        val text = read("src/main/java/io/legado/app/ui/download/DownloadManageActivity.kt")
        assertTrue("过滤口径须收口到纯函数", text.contains("DownloadFilter.apply("))
        assertFalse("内联过滤应已移除（防两套口径并存）", text.contains("private fun filterTasks("))
        val start = text.indexOf("onTabChange = { index ->")
        assertTrue("未找到 onTabChange 绑定", start >= 0)
        val block = text.substring(start, minOf(text.length, start + 240))
        assertTrue("点 Tab 必须立即重算（① 的根因修复）", block.contains("renderItems()"))
    }

    private fun read(relFromRepoRoot: String): String {
        val candidates = listOf(
            File(relFromRepoRoot),
            File("../$relFromRepoRoot"),
            File("../../$relFromRepoRoot")
        )
        return candidates.firstOrNull { it.isFile }?.readText()
            ?: throw AssertionError("未找到文件（工作目录=${File(".").absolutePath}）：$relFromRepoRoot")
    }
}