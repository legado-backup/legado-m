package io.legado.app.help.video

import io.legado.app.constant.BookType
import io.legado.app.data.entities.Book
import io.legado.app.data.entities.BookChapter
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Test

/**
 * video-cache-and-multiep AD-11：本地优先判定的边界契约。
 *
 * 本文件只锁定「不应走本地分支」的短路条件（卷行 / 非视频），
 * 避免为判定引入 Android 上下文依赖。
 */
class LocalMediaResolverTest {

    private fun videoBook(type: Int = BookType.video) = Book(bookUrl = "https://example.com/book/1", name = "剧", type = type)

    @Test
    fun `volume chapter never resolves to local uri`() {
        val book = videoBook()
        val volume = BookChapter(url = "线路一", title = "线路一", index = 0, isVolume = true)
        assertNull(LocalMediaResolver.localUri(book, volume))
        assertFalse(LocalMediaResolver.hasLocal(book, volume))
    }

    @Test
    fun `non video book never resolves to local uri`() {
        val book = videoBook(type = BookType.text)
        val chapter = BookChapter(url = "https://example.com/player/1", title = "第1集", index = 1)
        assertNull(LocalMediaResolver.localUri(book, chapter))
    }
}
