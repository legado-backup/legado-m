package io.legado.app.ui.about

import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/** B7 R28 分隔线取色不变量（源码文本断言；依据 theme-consistency-iron-rule K2/K4）。 */
class ReadRecordScreenTokenTest {

    private fun code(): String {
        val rel = "src/main/java/io/legado/app/ui/about/ReadRecordScreen.kt"
        val f = listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
        return f.readLines()
            .filterNot { it.trimStart().let { t -> t.startsWith("*") || t.startsWith("//") || t.startsWith("/*") } }
            .joinToString("\n")
    }

    @Test
    fun dividerUsesDividerToken() {
        val t = code()
        assertTrue("分隔线应走 dividerColor", t.contains("dividerColor"))
        assertFalse("不得再用 M3 派生键 outlineVariant", t.contains("outlineVariant"))
    }
}