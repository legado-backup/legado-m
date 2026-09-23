package io.legado.app.ui.main.bookshelf.compose

import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/** B7 R28/A4 未读角标取色不变量（源码文本断言；依据 theme-consistency-iron-rule K2/K4）。 */
class BookshelfComposeListBadgeTokenTest {

    private fun code(): String {
        val rel = "src/main/java/io/legado/app/ui/main/bookshelf/compose/BookshelfComposeList.kt"
        val f = listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
        return f.readLines()
            .filterNot { it.trimStart().let { t -> t.startsWith("*") || t.startsWith("//") || t.startsWith("/*") } }
            .joinToString("\n")
    }

    /** 无新章未读角标：底走面 token、字走对比度单源（原为硬编码黑底白字，不随主题）。 */
    @Test
    fun unreadBadgeUsesFaceTokenAndContrastSingleSource() {
        val t = code()
        assertTrue("角标底应走 tabBackgroundColor", t.contains("tabBackgroundColor"))
        assertTrue("角标字应走 contrastOn", t.contains("contrastOn("))
        assertFalse("不得再用硬编码黑底（0.58 透明度）", t.contains("Color.Black.copy(alpha = 0.58f)"))
    }
}