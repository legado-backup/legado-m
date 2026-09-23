package io.legado.app.ui.rss.article

import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/** B7 R28/R31 角标字色单源不变量（源码文本断言；依据 theme-consistency-iron-rule K2/K4）。 */
class RssSortActivityTokenTest {

    private fun code(): String {
        val rel = "src/main/java/io/legado/app/ui/rss/article/RssSortActivity.kt"
        val f = listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
        return f.readLines()
            .filterNot { it.trimStart().let { t -> t.startsWith("*") || t.startsWith("//") || t.startsWith("/*") } }
            .joinToString("\n")
    }

    @Test
    fun badgeTextColorUsesContrastSingleSource() {
        val t = code()
        assertTrue("应走对比度兜底单源 contrastOnColor", t.contains("contrastOnColor("))
        assertFalse("不得再取静态白色资源色", t.contains("R.color.white"))
    }
}