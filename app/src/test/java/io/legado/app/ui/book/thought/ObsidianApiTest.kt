package io.legado.app.ui.book.thought

import org.junit.Assert.assertEquals
import org.junit.Test

class ObsidianApiTest {

    @Test
    fun encodePath_simpleName() {
        assertEquals(
            "%E6%B5%8B%E8%AF%95%E4%B9%A6_20250101.md",
            ObsidianApi.encodePath("测试书_20250101.md")
        )
    }

    @Test
    fun encodePath_subPathPreserved() {
        assertEquals(
            "notes/thoughts/%E6%B5%8B%E8%AF%95%E4%B9%A6.md",
            ObsidianApi.encodePath("notes/thoughts/测试书.md")
        )
    }

    @Test
    fun encodePath_spaceToPercent20() {
        assertEquals("my%20note.md", ObsidianApi.encodePath("my note.md"))
    }

    @Test
    fun encodePath_chineseEncoded() {
        assertEquals("%E4%BD%A0%E5%A5%BD.md", ObsidianApi.encodePath("你好.md"))
    }

    @Test
    fun encodePath_empty() {
        assertEquals("", ObsidianApi.encodePath(""))
    }
}
