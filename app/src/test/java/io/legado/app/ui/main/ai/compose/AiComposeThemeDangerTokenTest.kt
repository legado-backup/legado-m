package io.legado.app.ui.main.ai.compose

import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/** B7 R28/AD-14 danger 单源不变量（源码文本断言；依据 theme-consistency-iron-rule K2/K4）。 */
class AiComposeThemeDangerTokenTest {

    private fun code(): String {
        val rel = "src/main/java/io/legado/app/ui/main/ai/compose/AiComposeTheme.kt"
        val f = listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
        return f.readLines()
            .filterNot { it.trimStart().let { t -> t.startsWith("*") || t.startsWith("//") || t.startsWith("/*") } }
            .joinToString("\n")
    }

    @Test
    fun dangerUsesSemanticSingleSource() {
        val t = code()
        assertTrue("应走 AppSemanticColors.Danger", t.contains("AppSemanticColors.Danger"))
        assertFalse("不得再写字面色值", t.contains("Color(0xfff44336"))
    }
}