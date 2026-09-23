package io.legado.app.ui.file

import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/** B7 R28 取色收口不变量（源码文本断言；依据 theme-consistency-iron-rule K2/K4）。 */
class FileManageScreenTokenTest {

    private fun code(): String {
        val rel = "src/main/java/io/legado/app/ui/file/FileManageScreen.kt"
        val f = listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
        return f.readLines()
            .filterNot { it.trimStart().let { t -> t.startsWith("*") || t.startsWith("//") || t.startsWith("/*") } }
            .joinToString("\n")
    }

    @Test
    fun iconTintUsesFaceToken() {
        val t = code()
        assertTrue("应走 settingPalette().secondaryText", t.contains("settingPalette().secondaryText"))
        assertFalse("不得再用 colorScheme.outline", Regex("colorScheme\\.outline\\b").containsMatchIn(t))
        assertFalse("不得再用 outlineVariant", t.contains("outlineVariant"))
    }
}