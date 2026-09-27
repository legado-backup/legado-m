package io.legado.app.data.entities

import java.io.File
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * W3 / REQ-16（AD-07）：`Book` 的**朗读专用锚点**字段不变量。
 *
 * 为什么不能复用 `durChapterPos`：该字段是**多义共享字段**（文字=首行字符索引；**漫画=图片序号**，
 * 见 `ReadManga.kt` 的 `durChapterPos.coerceIn(0, imageCount - 1)`），朗读若复用会与二者互相覆盖
 * ⇒ 必须另立字段，并与「归属章节」成对使用（防切章后误用旧锚点跳错位置）。
 */
class BookVoiceAnchorFieldTest {

    private val book by lazy {
        listOf(
            File("src/main/java/io/legado/app/data/entities/Book.kt"),
            File("../app/src/main/java/io/legado/app/data/entities/Book.kt"),
            File("app/src/main/java/io/legado/app/data/entities/Book.kt")
        ).first { it.isFile }.readText()
            // 工作副本可能是 CRLF（Windows 检出）⇒ 归一到 LF，保证多行断言稳定
            .replace("\r\n", "\n")
    }

    @Test
    fun anchorFieldsAreDeclaredWithEntityDefaults() {
        assertTrue(
            "须声明朗读段落锚点（章内字符索引）",
            book.contains("var voiceParagraphAnchor: Int = 0")
        )
        assertTrue(
            "须声明锚点归属章节（-1 = 无锚点）",
            book.contains("var voiceParagraphAnchorChapter: Int = -1")
        )
        assertTrue(
            "锚点列默认值须与迁移 DDL 一致（0 / -1）",
            book.contains("@ColumnInfo(defaultValue = \"0\")\n    var voiceParagraphAnchor: Int = 0") &&
                book.contains("@ColumnInfo(defaultValue = \"-1\")\n    var voiceParagraphAnchorChapter: Int = -1")
        )
    }

    @Test
    fun anchorStaysSeparateFromSharedDurChapterPos() {
        assertTrue("多义字段 durChapterPos 必须保留（不得被朗读占用）", book.contains("var durChapterPos: Int = 0"))
        assertTrue(
            "锚点须为独立字段（附「不复用 durChapterPos」的理由注释，防后人合并）",
            book.contains("多义共享字段")
        )
    }
}