package io.legado.app.ui.widget.text

import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 底栏角标取色/对比度不变量回归测试（B7 R31，依据 theme-consistency-iron-rule K2/K4）。
 *
 * 缺陷（2026-09-23 审计实证 A3/D3）：`BadgeView` 自建黑白兜底（三套对比度实现之一）⇒ 与
 * Compose 侧角标、标签栏在极端主题下可能给出不同文字色。收敛后统一走 `ColorUtils.contrastOnColor`。
 *
 * 断言跑在去注释后的代码文本上（说明性注释会合法提到旧写法）。
 */
class BadgeViewContrastSourceTest {

    private fun code(): String {
        val rel = "src/main/java/io/legado/app/ui/widget/text/BadgeView.kt"
        val candidates = listOf(File(rel), File("../app/$rel"), File("app/$rel"))
        val f = candidates.firstOrNull { it.isFile }
            ?: throw AssertionError("未找到源文件（工作目录=${File(".").absolutePath}）：$rel")
        return f.readLines()
            .filterNot {
                val t = it.trimStart()
                t.startsWith("*") || t.startsWith("//") || t.startsWith("/*")
            }
            .joinToString("\n")
    }

    /** 角标字色必须走对比度单源，不得再自建黑白兜底。 */
    @Test
    fun badgeTextColor_usesContrastSingleSource() {
        val text = code()
        assertTrue("角标字色应走 contrastOnColor 单源", text.contains("contrastOnColor("))
        assertFalse("不得再自建黑白兜底", text.contains("Color.BLACK") || text.contains("Color.WHITE"))
    }
}