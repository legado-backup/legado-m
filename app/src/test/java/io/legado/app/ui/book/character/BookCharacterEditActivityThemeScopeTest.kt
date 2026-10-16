package io.legado.app.ui.book.character

import io.legado.app.testutil.ComposeThemeScopeAssert
import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * NEW-71 / G-37 放量批 B：`BookCharacterEditActivity` 两处宿主（页内容根 + 头像选择弹层）
 * 的主题作用域守护。
 *
 * 页内容根原**完全无主题作用域**（`setContent { CharacterEditScreen(…) }`）、弹层原内容根为
 * `LegadoComposeTheme`（只透传色板/字体）⇒ 两者在夜间/主题包下均回落默认色板；
 * 现均上提为唯一主题入口 `LegadoTheme`（色板 + 字号 + 主题字体族）。
 */
class BookCharacterEditActivityThemeScopeTest {

    private val rel = "io/legado/app/ui/book/character/BookCharacterEditActivity.kt"

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
            "两处 setContent 内容根均须为 LegadoTheme（少改一处即失败）",
            2,
            Regex("(?<![A-Za-z0-9_])LegadoTheme\\s*\\{").findAll(src).count()
        )
    }
}
