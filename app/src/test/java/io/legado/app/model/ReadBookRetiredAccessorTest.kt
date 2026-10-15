package io.legado.app.model

import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * B18：`ReadBook.currentChapterLoadGeneration` 冗余访问器退役守护。
 *
 * 缺陷背景：该访问器经 `audit_dead_private_fun.py` 判定零调用；其职责（读 `chapterLoadGenerations[index]`）
 * 在活代码中**已由直接字段访问**承担（如 `finishChapterLoad` 内 `chapterLoadGenerations[index] == generation`），
 * 属冗余转发 ⇒ 退役。代次机制本身（字段 + `isChapterLoadRequestCurrent`）必须保留。
 */
class ReadBookRetiredAccessorTest {

    private fun code(rel: String): String =
        listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
            .readText().replace("\r\n", "\n")

    @Test
    fun `冗余代次读取访问器退役且机制保留`() {
        val src = code("src/main/java/io/legado/app/model/ReadBook.kt")
        assertEquals("冗余代次访问器应退役", false, src.contains("fun currentChapterLoadGeneration("))
        assertEquals("代次机制字段与当前性判定必须保留", true,
            src.contains("chapterLoadGenerations") && src.contains("fun isChapterLoadRequestCurrent("))
    }
}
