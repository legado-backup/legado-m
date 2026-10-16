package io.legado.app.ui.book.read.config

import io.legado.app.testutil.ComposeThemeScopeAssert
import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * NEW-71 / G-37 放量批 B：`ParagraphRuleEditActivity` 两处宿主的主题作用域守护。
 *
 * - 页内容根原为「先 `Column`、`LegadoTheme` 只包顶栏」（铁律 S1 点名的典型失守形态）；
 * - 脚本模板弹层原内容根为 `LegadoComposeTheme`（只透传色板/字体）。
 *
 * 现两处均上提为唯一主题入口 `LegadoTheme`（色板 + 字号 + 主题字体族）。
 */
class ParagraphRuleEditActivityThemeScopeTest {

    private val rel = "io/legado/app/ui/book/read/config/ParagraphRuleEditActivity.kt"

    @Test
    fun `两处宿主内容根均已上提 LegadoTheme（顶层主题作用域）`() {
        ComposeThemeScopeAssert.assertHostProvidesThemeScope(rel)
        val src = ComposeThemeScopeAssert.sourceText(rel)
        assertEquals(
            "不得再以 LegadoComposeTheme 作内容根",
            0,
            Regex("LegadoComposeTheme\\s*\\{").findAll(src).count()
        )
        assertEquals(
            "两处宿主内容根均须为 LegadoTheme（少改一处即失败）",
            2,
            Regex("(?<![A-Za-z0-9_])LegadoTheme\\s*\\{").findAll(src).count()
        )
    }
}
