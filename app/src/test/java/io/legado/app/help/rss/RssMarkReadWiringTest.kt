package io.legado.app.help.rss

import java.io.File
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * W4 / REQ-18：一键全标已读的**接线**不变量（Dao → 编排 → 双入口）。
 *
 * 为什么值得测（实证根因）：文章列表未读判定是 `left join rssReadRecords` + `ifNull(read, 0)`
 * ⇒ 「只 update 已存在行」会留一堆未读 ⇒ 必须**先补缺失记录再置读**；且范围三态（全部/当前源/当前分组）
 * 必须在 UI 上可辨（否则用户会以为只影响当前可见项）。
 */
class RssMarkReadWiringTest {

    private fun read(rel: String): String =
        listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
            .readText()
            .replace("\r\n", "\n")

    private val dao by lazy { read("src/main/java/io/legado/app/data/dao/RssReadRecordDao.kt") }
    private val marker by lazy { read("src/main/java/io/legado/app/help/rss/RssReadRecordMarker.kt") }
    private val readActivity by lazy {
        read("src/main/java/io/legado/app/ui/rss/read/ReadRssActivity.kt")
    }
    private val manageActivity by lazy {
        read("src/main/java/io/legado/app/ui/rss/source/manage/RssSourceActivity.kt")
    }

    @Test
    fun daoProvidesScopedUpdateAndMissingRecordBackfill() {
        assertTrue(
            "须有按 origin 集合的置读 SQL",
            dao.contains("update rssReadRecords set read = 1 where read = 0 and origin in (:origins)")
        )
        assertTrue(
            "须有补缺失记录的 INSERT…SELECT（否则没记录的文章永远算未读）",
            dao.contains("insert into rssReadRecords") && dao.contains("not exists")
        )
        assertTrue("补充记录须标为已读", dao.contains("select link, title, :now, 1, origin, sort, image, type, 0, pubDate"))
    }

    @Test
    fun markerRunsBackfillBeforeUpdateAndReportsChanges() {
        val backfillAt = marker.indexOf("insertMissingAsReadByOrigins(origins, now)")
        val updateAt = marker.indexOf("markAllReadByOrigins(origins)")
        assertTrue("须先补记录后置读", backfillAt > 0 && updateAt > backfillAt)
        assertTrue(
            "新增行数须用总数差值统计（Room INSERT…SELECT 无 rowid）",
            marker.contains("val before = appDb.rssReadRecordDao.countRecords")
        )
        assertTrue("须留可定位诊断日志（计数级，不落标题）", marker.contains("RssMarkRead: origins="))
        assertTrue("空范围须直接返回（不空跑 SQL）", marker.contains("if (origins.isEmpty()) return@withContext 0"))
    }

    @Test
    fun threeScopesAreDistinctAndExplicit() {
        assertTrue("阅读页 = 当前源范围", readActivity.contains("RssReadRecordMarker.markRead(listOf(origin))"))
        assertTrue("源管理页 = 全部范围", manageActivity.contains("RssReadRecordMarker.allOrigins()"))
        assertTrue("源管理页 = 分组范围", manageActivity.contains("RssReadRecordMarker.originsOfGroup(tag)"))
    }

    @Test
    fun bothEntriesConfirmBeforeRunningAndGiveReceipt() {
        assertTrue("阅读页入口须确认", readActivity.contains("showComposeConfirmDialog("))
        assertTrue("源管理页入口须确认（公共流程）", manageActivity.contains("private fun confirmMarkRead("))
        assertTrue("须有结果回执文案（计数）", readActivity.contains("R.string.rss_mark_read_done"))
        assertTrue("源管理页回执", manageActivity.contains("R.string.rss_mark_read_done"))
    }

    @Test
    fun groupScopeHandlesUnprocessedCommaJoinedGroupStrings() {
        assertTrue(
            "分组字符串是逗号扁平串 ⇒ 须先拆分去重再作为标签使用",
            manageActivity.contains("it.splitNotBlank(AppPattern.splitGroupRegex).toList()")
        )
        assertTrue("无分组时给明确提示", manageActivity.contains("R.string.rss_mark_read_no_group"))
    }
}