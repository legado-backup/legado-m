package io.legado.app.ui.book.import

import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/** B7 R28 取色收口不变量（源码文本断言；依据 theme-consistency-iron-rule K2/K4）。 */
class ImportBookScreenTokenTest {

    private fun code(): String {
        val rel = "src/main/java/io/legado/app/ui/book/import/ImportBookScreen.kt"
        val f = listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
        return f.readLines()
            .filterNot { it.trimStart().let { t -> t.startsWith("*") || t.startsWith("//") || t.startsWith("/*") } }
            .joinToString("\n")
    }

    /** 输入框描边 / 日期弱化文字必须走面 token，不得再用 M3 派生键。 */
    @Test
    fun usesFaceTokensInsteadOfM3DerivedKeys() {
        val t = code()
        assertTrue("描边应走 dividerColor", t.contains("dividerColor"))
        assertTrue("文字应走 settingPalette().secondaryText", t.contains("settingPalette().secondaryText"))
        assertFalse("不得再用 colorScheme.surfaceVariant", t.contains("colorScheme.surfaceVariant"))
        // 词边界：避免把 outlineVariant 误判为 outline（二者同属派生键，本文件已一并收口）
        assertFalse("不得再用 colorScheme.outline", Regex("colorScheme\\.outline\\b").containsMatchIn(t))
        assertFalse("不得再用 outlineVariant", t.contains("outlineVariant"))
    }
}