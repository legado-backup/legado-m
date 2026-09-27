package io.legado.app.ui.rss.read

import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * W4 / REQ-18：阅读页「本订阅标为已读」入口的**接线**不变量（配对 [ReadRssActivity] 菜单项）。
 *
 * 为什么值得测（实证根因）：本页与订阅源管理页是同一能力的**双入口**，
 * 但**范围语义不同** —— 本页只允许作用于「当前源」，若误调全库/分组范围
 * 会把用户没打算动的订阅一起置读（不可撤销的数据面影响）。
 * 另：置读是 DB 写 + 归档补记录，必须在协程里执行，不能在 `onClick` 主线程同步跑。
 */
class ReadRssMarkReadWiringTest {

    private fun read(rel: String): String =
        listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
            .readText()
            .replace("\r\n", "\n")

    private val activity by lazy {
        read("src/main/java/io/legado/app/ui/rss/read/ReadRssActivity.kt")
    }

    /** 只截取本菜单项的实现段，避免同页其它 `markRead`/菜单项造成误判。 */
    private val markReadBlock by lazy {
        val start = activity.indexOf("REQ-18：本订阅一键标为已读")
        val end = activity.indexOf("rss-unified-search", start)
        if (start > 0 && end > start) activity.substring(start, end) else activity
    }

    @Test
    fun entryScopeIsCurrentSourceOnly() {
        assertTrue(
            "入口须取当前订阅源 key 作为 origin",
            markReadBlock.contains("val origin = viewModel.rssSource?.sourceUrl")
        )
        assertTrue(
            "须只对当前源置读（listOf(origin)，非全库）",
            markReadBlock.contains("RssReadRecordMarker.markRead(listOf(origin))")
        )
        assertFalse(
            "本页不得使用全库/分组范围（那是订阅源管理页的语义）",
            markReadBlock.contains("allOrigins()") || markReadBlock.contains("originsOfGroup(")
        )
    }

    @Test
    fun blankOriginIsGuardedWithOwnPrompt() {
        assertTrue("origin 为空须拦截", markReadBlock.contains("origin.isNullOrBlank()"))
        assertTrue(
            "空源须给独立提示（与「已完成」回执区分）",
            markReadBlock.contains("R.string.rss_mark_read_no_source")
        )
    }

    @Test
    fun confirmsBeforeRunningAndReportsCountInCoroutine() {
        assertTrue("执行前须确认", markReadBlock.contains("showComposeConfirmDialog("))
        assertTrue(
            "确认文案须说明影响面",
            markReadBlock.contains("message = getString(R.string.rss_mark_read_confirm_message)")
        )
        assertTrue("DB 写入须在协程内执行", markReadBlock.contains("lifecycleScope.launch {"))
        assertTrue(
            "须回执实际变更条数（用户可辨是否生效）",
            markReadBlock.contains("getString(R.string.rss_mark_read_done, changed)")
        )
    }

    @Test
    fun entryIsReachableFromMenuWithDistinctTitle() {
        assertTrue(
            "须是菜单项（MenuAction）而非隐式手势",
            markReadBlock.contains("MenuAction(")
        )
        assertTrue(
            "标题须与源管理页的「全部/分组」区分",
            markReadBlock.contains("R.string.rss_mark_read_current_source")
        )
    }
}