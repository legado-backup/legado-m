package io.legado.app.model

import io.legado.app.constant.BookType
import io.legado.app.data.entities.Book
import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * R 批 §3.1.1（P0-7）：视频「是否已在书架」身份判定
 *
 * 覆盖两层：
 * 1. 纯函数语义 —— [resolveVideoBookshelfState] 以「库中存在且未打 notShelf 位」为准；
 * 2. 接线不变量 —— `VideoPlay.initSource` 按库中身份解析、singleUrl 分支不再硬编码已入架。
 */
class VideoBookshelfStateTest {

    private fun bookOf(type: Int): Book = Book(
        bookUrl = "u",
        name = "n",
        author = "a",
        origin = "o",
    ).apply { this.type = type }

    @Test
    fun storedBookWithoutNotShelfIsInShelf() {
        assertTrue(resolveVideoBookshelfState(bookOf(BookType.video)))
    }

    @Test
    fun storedBookWithNotShelfIsNotInShelf() {
        assertFalse(resolveVideoBookshelfState(bookOf(BookType.video or BookType.notShelf)))
    }

    @Test
    fun absentStoredBookIsNotInShelf() {
        // 库中无记录 = 仅搜索过、还没入架 ⇒ 退出播放器时应走「加入书架」询问链路
        assertFalse(resolveVideoBookshelfState(null))
    }

    @Test
    fun initSourceResolvesShelfStateFromStoredIdentity() {
        val code = SourceFileProbe.sourceText("model/VideoPlay.kt")
        assertTrue(
            "initSource 必须先取库中身份（bookDao，不是 searchBookDao 派生对象）",
            code.contains("val storedBook = bookUrl?.let { appDb.bookDao.getBook(it) }")
        )
        assertTrue(
            "initSource 必须按库中身份解析 inBookshelf",
            code.contains("inBookshelf = resolveVideoBookshelfState(storedBook)")
        )
    }

    @Test
    fun singleUrlBranchUsesIdentityInsteadOfHardcodedTrue() {
        val code = SourceFileProbe.sourceText("model/VideoPlay.kt")
        assertTrue(
            "singleUrl 分支必须按身份判定（无身份时保持已入架）",
            code.contains("inBookshelf = book?.let { resolveVideoBookshelfState(it) } ?: true")
        )
        assertFalse(
            "singleUrl 分支不得再硬编码 inBookshelf = true",
            code.contains("inBookshelf = true\n                val analyzeUrl")
        )
    }

    @Test
    fun helperIsDefinedOnceWithShelfSemantics() {
        val code = SourceFileProbe.sourceText("model/VideoPlay.kt")
        assertTrue(
            code.contains(
                "internal fun resolveVideoBookshelfState(storedBook: Book?): Boolean = " +
                    "storedBook?.isNotShelf == false"
            )
        )
    }
}