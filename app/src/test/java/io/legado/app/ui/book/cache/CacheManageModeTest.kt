package io.legado.app.ui.book.cache

import io.legado.app.constant.BookType
import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * video-cache-and-multiep R3：缓存管理类型与书籍类型位一一对应。
 */
class CacheManageModeTest {

    @Test
    fun `video mode maps to video book type bit`() {
        assertEquals(BookType.video, CacheManageMode.VIDEO.bookType)
    }

    @Test
    fun `four modes use four distinct type bits`() {
        val bits = CacheManageMode.entries.map { it.bookType }
        assertEquals(4, CacheManageMode.entries.size)
        assertEquals(bits.size, bits.toSet().size)
    }
}
