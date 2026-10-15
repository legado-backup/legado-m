package io.legado.app.ui.book.read.page.entities

import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * B21：`TextChapter.cleanReadAloudMarkup` 及其中4个专属正则退役守护。
 *
 * 缺陷背景：该 markup 清理实现已被 `ReadAloudTextCleaner`（活兄弟 `readAloudText()`）取代，
 * 零调用；其专属的 4 个 companion 正则（`readAloudUseHtmlRegex` 等）仅被它使用 ⇒ 一并成孤儿退役。
 */
class TextChapterRetiredMarkupTest {

    private fun code(rel: String): String =
        listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
            .readText().replace("\r\n", "\n")

    @Test
    fun `旧朗读markup清理及专属正则已退役且活清理器保留`() {
        val src = code("src/main/java/io/legado/app/ui/book/read/page/entities/TextChapter.kt")
        assertEquals("旧 markup 清理应退役", false, src.contains("fun String.cleanReadAloudMarkup("))
        assertEquals("专属正则应为空", emptyList<String>(),
            listOf("readAloudUseHtmlRegex", "readAloudImgRegex", "readAloudBreakTagRegex", "readAloudTagRegex")
                .filter { src.contains(it) })
        assertEquals("活清理路径必须保留", true, src.contains("ReadAloudTextCleaner.cleanVisibleText("))
    }
}
