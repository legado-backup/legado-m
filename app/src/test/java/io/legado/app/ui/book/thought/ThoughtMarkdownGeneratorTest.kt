package io.legado.app.ui.book.thought

import io.legado.app.data.entities.BookHighlight
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class ThoughtMarkdownGeneratorTest {

    private fun highlight(
        chapterIndex: Int,
        chapterName: String,
        bookText: String,
        note: String,
        time: Long
    ) = BookHighlight(
        time = time,
        bookName = "测试书",
        bookAuthor = "作者A",
        chapterIndex = chapterIndex,
        chapterName = chapterName,
        bookText = bookText,
        note = note
    )

    @Test
    fun generate_includesBookHeader() {
        val md = ThoughtMarkdownGenerator.generate(
            "测试书", "作者A", "http://cover.jpg", "这是一本测试书简介",
            listOf(highlight(0, "第一章", "正文内容", "想法1", 1700000000000))
        )
        assertTrue(md.contains("《测试书》"))
        assertTrue(md.contains("作者：作者A"))
        assertTrue(md.contains("<img src=\"http://cover.jpg\" width=\"150\">"))
        assertTrue(md.contains("### 书籍简介"))
        assertTrue(md.contains("这是一本测试书简介"))
    }

    @Test
    fun generate_groupsByChapterIndexAndName() {
        val md = ThoughtMarkdownGenerator.generate(
            "测试书", "作者A", null, null,
            listOf(
                highlight(0, "第一章", "内容A", "", 1700000000000),
                highlight(1, "第二章", "内容B", "", 1700000001000),
                highlight(0, "第一章", "内容C", "", 1700000002000)
            )
        )
        assertTrue(md.indexOf("### 第一章") < md.indexOf("### 第二章"))
        assertTrue(md.contains("内容A"))
        assertTrue(md.contains("内容C"))
        assertTrue(md.contains("内容B"))
    }

    @Test
    fun generate_includesQuoteAndTimestamp() {
        val md = ThoughtMarkdownGenerator.generate(
            "测试书", "作者A", null, null,
            listOf(highlight(0, "第一章", "划线内容", "我的批注", 1700000000000))
        )
        assertTrue(md.contains("划线内容"))
        assertTrue(md.contains("> 我的批注"))
        assertTrue(md.contains("<font>"))
    }

    @Test
    fun generate_emptyThoughtsStillHasHeader() {
        val md = ThoughtMarkdownGenerator.generate(
            "测试书", "作者A", null, null,
            emptyList()
        )
        assertTrue(md.contains("《测试书》"))
        assertTrue(md.contains("作者：作者A"))
    }

    @Test
    fun generate_blankTextOrNoteSkipped() {
        val md = ThoughtMarkdownGenerator.generate(
            "测试书", "作者A", null, null,
            listOf(highlight(0, "第一章", "   ", "   ", 1700000000000))
        )
        assertTrue(!md.contains(">   "))
    }

    @Test
    fun generate_escapesBookNameInFileName_onlyHeader() {
        val md = ThoughtMarkdownGenerator.generate(
            "测/试:书", "作者A", null, null,
            listOf(highlight(0, "第一章", "内容", "", 1700000000000))
        )
        assertTrue(md.contains("《测/试:书》"))
    }
}
