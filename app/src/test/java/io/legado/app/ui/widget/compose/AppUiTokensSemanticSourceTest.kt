package io.legado.app.ui.widget.compose

import java.io.File
import org.junit.Assert.assertTrue
import org.junit.Test

/** B7 R28/AD-14 语义色单源不变量（源码文本断言；依据 theme-consistency-iron-rule K2/K4）。 */
class AppUiTokensSemanticSourceTest {

    private fun code(): String {
        val rel = "src/main/java/io/legado/app/ui/widget/compose/AppUiTokens.kt"
        val f = listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
        return f.readLines()
            .filterNot { it.trimStart().let { t -> t.startsWith("*") || t.startsWith("//") || t.startsWith("/*") } }
            .joinToString("\n")
    }

    /** 语义色单源必须提供 Compose 与 Int（View）两种形式，供全站复用，避免各处再写色值。 */
    @Test
    fun dangerSingleSourceExposesBothComposeAndArgbForms() {
        val t = code()
        assertTrue("应声明 Danger（Compose）", t.contains("val Danger = Color("))
        assertTrue("应声明 DangerArgb（View/Int 场景）", t.contains("val DangerArgb"))
    }
}