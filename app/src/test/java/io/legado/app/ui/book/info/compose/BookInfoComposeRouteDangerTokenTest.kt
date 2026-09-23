package io.legado.app.ui.book.info.compose

import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/** B7 R28/AD-14 danger 单源不变量（源码文本断言；依据 theme-consistency-iron-rule K2/K4）。 */
class BookInfoComposeRouteDangerTokenTest {

    private fun code(): String {
        val rel = "src/main/java/io/legado/app/ui/book/info/compose/BookInfoComposeRoute.kt"
        val f = listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
        return f.readLines()
            .filterNot { it.trimStart().let { t -> t.startsWith("*") || t.startsWith("//") || t.startsWith("/*") } }
            .joinToString("\n")
    }

    /** danger 文字色必须走语义色单源，不得再写字面色值（color.md §7.1）。 */
    @Test
    fun dangerTextUsesSemanticSingleSource() {
        val t = code()
        assertTrue("应走 AppUiTokens.danger", t.contains("AppUiTokens.danger"))
        assertFalse("不得再写 danger 字面色值", t.contains("Color(0xffd64545)"))
    }
}