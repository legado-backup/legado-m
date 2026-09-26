package io.legado.app.data.dao

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * R 批 Q7/Q8（2026-09-26）`BookDao` 两处数据层修正的**结构不变量**测试。
 *
 * Q7 临时书「身份化清理」：原 `deleteNotShelfBook`（`delete from books where type & notShelf > 0`）
 *   在 `MainViewModel.init` 每次启动全删临时书 —— 会把「从搜索结果直接读过」的书（`readRecentBooks`
 *   有身份记录）连同其阅读进度一起删掉，并留下指向已删书的悬空最近在读行。
 * Q8 进度戳单列写：新增 `updateReadTime` 供「只戳时间」的场景使用，取代 `@Update` 整行写
 *   （整行写会以内存快照回写全部列 ⇒ 覆盖并发协程期间改过的其它列 = lost update）。
 *
 * 均为 Room `@Query` 形态，JVM 单测无法跑真库（`room-testing` 只在 androidTest 侧）⇒
 * 按本仓既有口径锁**源码结构**（SQL 语义在注释里逐条说明，防「改回全删/整行写」静默回退）。
 */
class BookDaoTempCleanupTest {

    private fun src(): String = SourceFileProbe.sourceText("data/dao/BookDao.kt")

    @Test
    fun tempCleanupIsIdentityAware() {
        val s = src()
        assertTrue("必须提供身份化的临时书清理 API", s.contains("fun deleteTempByIdentity()"))
        assertTrue(
            "身份化口径不得丢失：必须排除有阅读身份记录的临时书",
            s.contains("and bookUrl not in (select bookUrl from readRecentBooks)")
        )
        assertTrue(
            "仍必须只针对临时书（type & BookType.notShelf）",
            s.contains("where type & \${BookType.notShelf} > 0")
        )
        assertFalse(
            "全删形态（deleteNotShelfBook）必须已退役——它会在启动时误删用户读过的临时书",
            s.contains("fun deleteNotShelfBook()")
        )
    }

    @Test
    fun readTimeHasSingleColumnApi() {
        val s = src()
        assertTrue("必须提供单列更新时间戳的 API", s.contains("fun updateReadTime(bookUrl: String, readTime: Long)"))
        assertTrue(
            "单列语义不得漂移（只 set durChapterTime）",
            s.contains("@Query(\"update books set durChapterTime = :readTime where bookUrl = :bookUrl\")")
        )
    }

    @Test
    fun existingWriteApisUntouched() {
        val s = src()
        listOf(
            "fun updateReadProgress(",
            "fun upProgress(bookUrl: String, pos: Int)",
            "fun updateCustomTag(bookUrl: String, customTag: String?)",
        ).forEach { marker ->
            assertTrue("既有写 API 不得误删：$marker", s.contains(marker))
        }
    }
}