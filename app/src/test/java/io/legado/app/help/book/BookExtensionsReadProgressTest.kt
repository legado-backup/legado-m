package io.legado.app.help.book

import io.legado.app.data.entities.Book
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class BookExtensionsReadProgressTest {

    @Test
    fun unread_book_returns_null() {
        val book = Book(name = "未读书")
        assertNull(book.readProgress())
    }

    @Test
    fun read_first_chapter_with_pos_returns_progress() {
        val book = Book(name = "多章书", totalChapterNum = 10, durChapterIndex = 0, durChapterPos = 100)
        assertEquals(0f, book.readProgress())
    }

    @Test
    fun single_chapter_book_read_returns_one() {
        val book = Book(name = "单章书", totalChapterNum = 1, durChapterIndex = 0, durChapterPos = 200)
        assertEquals(1f, book.readProgress())
    }

    @Test
    fun normal_progress_ratio() {
        val book = Book(name = "多章书", totalChapterNum = 11, durChapterIndex = 5, durChapterPos = 100)
        assertEquals(0.5f, book.readProgress())
    }

    @Test
    fun out_of_range_index_clamped_to_one() {
        val book = Book(name = "多章书", totalChapterNum = 10, durChapterIndex = 100, durChapterPos = 100)
        assertEquals(1f, book.readProgress())
    }

    @Test
    fun negative_clamped_to_zero() {
        val book = Book(name = "异常书", totalChapterNum = 10, durChapterIndex = -3, durChapterPos = 100)
        assertEquals(0f, book.readProgress())
    }
}
