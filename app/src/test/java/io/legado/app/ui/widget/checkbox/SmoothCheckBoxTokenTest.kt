package io.legado.app.ui.widget.checkbox

import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/** B7 R28 取色收口不变量（源码文本断言；依据 theme-consistency-iron-rule K2/K4）。 */
class SmoothCheckBoxTokenTest {

    private fun code(): String {
        val rel = "src/main/java/io/legado/app/ui/widget/checkbox/SmoothCheckBox.kt"
        val f = listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
        return f.readLines()
            .filterNot { it.trimStart().let { t -> t.startsWith("*") || t.startsWith("//") || t.startsWith("/*") } }
            .joinToString("\n")
    }

    @Test
    fun defaultColorsUseFaceToken() {
        val t = code()
        assertTrue("默认底应取 tabBackgroundColor token", t.contains("themeTabBackgroundColorOrDefault()"))
        assertFalse("不得再用静态资源色 background_menu", t.contains("R.color.background_menu"))
    }
}