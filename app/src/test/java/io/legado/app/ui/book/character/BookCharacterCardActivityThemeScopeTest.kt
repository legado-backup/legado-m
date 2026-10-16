package io.legado.app.ui.book.character

import io.legado.app.testutil.ComposeThemeScopeAssert
import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * NEW-74 / G-37 放量批 C：`BookCharacterCardActivity`（角色卡页）宿主内容根主题作用域守护。
 *
 * 原 `composeView.setContent` 无任何主题作用域 ⇒ 页内读 M3 派生色的组件在夜间/主题包下
 * 回落 M3 默认色板；现上提为唯一主题入口 `LegadoTheme`。
 */
class BookCharacterCardActivityThemeScopeTest {

    private val rel = "io/legado/app/ui/book/character/BookCharacterCardActivity.kt"

    @Test
    fun `内容根已上提 LegadoTheme（顶层主题作用域）`() {
        ComposeThemeScopeAssert.assertHostProvidesThemeScope(rel)
        val src = ComposeThemeScopeAssert.sourceText(rel)
        assertEquals(
            "不得再以 LegadoComposeTheme 作内容根",
            0,
            Regex("LegadoComposeTheme\\s*\\{").findAll(src).count()
        )
    }
}
