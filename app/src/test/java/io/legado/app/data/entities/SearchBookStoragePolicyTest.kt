package io.legado.app.data.entities

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class SearchBookStoragePolicyTest {

    private fun buildBook(
        name: String = "测试书名",
        originName: String = "来源站",
        intro: String? = null,
        coverUrl: String? = null,
        variable: String? = null
    ): SearchBook = SearchBook(
        bookUrl = "https://www.example.com/book/1",
        origin = "https://www.example.com",
        originName = originName,
        name = name,
        author = "作者",
        tocUrl = "https://www.example.com/toc",
        intro = intro,
        coverUrl = coverUrl,
        variable = variable
    )

    @Test
    fun normalRecord_passesThroughUnchanged() {
        val book = buildBook()
        val sanitized = SearchBookStoragePolicy.sanitize(book)
        assertNotNull(sanitized)
        assertEquals(book, sanitized)
    }

    @Test
    fun nameOverLimit_returnsNull() {
        val book = buildBook(name = "n".repeat(SearchBookStoragePolicy.MAX_NAME_BYTES + 1))
        assertNull(SearchBookStoragePolicy.sanitize(book))
    }

    @Test
    fun bookUrlOverLimit_returnsNull() {
        val book = buildBook().copy(bookUrl = "u".repeat(SearchBookStoragePolicy.MAX_BOOK_URL_BYTES + 1))
        assertNull(SearchBookStoragePolicy.sanitize(book))
    }

    @Test
    fun variableOverLimit_returnsNull() {
        val book = buildBook(variable = "v".repeat(SearchBookStoragePolicy.MAX_VARIABLE_BYTES + 1))
        assertNull(SearchBookStoragePolicy.sanitize(book))
    }

    @Test
    fun introOverLimit_truncatedPreservingTag() {
        val content = "c".repeat(SearchBookStoragePolicy.MAX_INTRO_BYTES * 2)
        val book = buildBook(intro = "<useweb>$content</useweb>")
        val sanitized = SearchBookStoragePolicy.sanitize(book)
        assertNotNull(sanitized)
        assertTrue(sanitized!!.intro!!.startsWith("<useweb>"))
        assertTrue(sanitized.intro!!.endsWith("</useweb>"))
        assertTrue(sanitized.intro!!.length < book.intro!!.length)
    }

    @Test
    fun coverUrlOverLimit_setToNull() {
        val book = buildBook(coverUrl = "c".repeat(SearchBookStoragePolicy.MAX_COVER_URL_BYTES + 1))
        val sanitized = SearchBookStoragePolicy.sanitize(book)
        assertNotNull(sanitized)
        assertNull(sanitized!!.coverUrl)
    }

    @Test
    fun originNameOverLimit_truncatedStillStored() {
        val book = buildBook(originName = "o".repeat(SearchBookStoragePolicy.MAX_ORIGIN_NAME_BYTES + 1))
        val sanitized = SearchBookStoragePolicy.sanitize(book)
        assertNotNull(sanitized)
        assertTrue(sanitized!!.originName.length < book.originName.length)
    }

    @Test
    fun storedUtf8ByteCount_countsAsciiCjkAndSurrogate() {
        val book = buildBook().copy(
            bookUrl = "https://www.example.com/book/1",
            origin = "https://www.example.com",
            originName = "中文",
            name = "abc",
            author = "作者",
            tocUrl = "https://www.example.com/toc"
        )
        val count = SearchBookStoragePolicy.storedUtf8ByteCount(book)
        val ascii = "https://www.example.com/book/1https://www.example.comabchttps://www.example.com/toc".toByteArray(Charsets.UTF_8).size
        val cjk = "中文作者".toByteArray(Charsets.UTF_8).size
        assertEquals((ascii + cjk).toLong(), count)
    }

    @Test
    fun utf8ByteCount_countsSurrogatePairAsFour() {
        val value = "a\uD83D\uDE00b"
        assertEquals(1 + 4 + 1, SearchBookStoragePolicy.utf8ByteCount(value).toInt())
    }

    @Test
    fun utf8ByteCount_stopsAfterLimit() {
        val value = "abcdefgh"
        assertEquals(3L, SearchBookStoragePolicy.utf8ByteCount(value, stopAfter = 2))
    }
}
