package io.legado.app.ui.book.character

import io.legado.app.testutil.ComposeThemeScopeAssert
import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * NEW-74 / G-37 放量批 C·续：角色「管理页」与「关系网页」宿主内容根主题作用域守护。
 *
 * 两页原 `composeView.setContent` 均无任何主题作用域 ⇒ 页内读 M3 派生色的组件在夜间/主题包/
 * 自定义主题色下回落 M3 默认色板；现均上提为唯一主题入口 `LegadoTheme`。
 */
class BookCharacterScreensThemeScopeTest {

    private val hosts = listOf(
        "io/legado/app/ui/book/character/BookCharacterManageActivity.kt",
        "io/legado/app/ui/book/character/BookCharacterRelationActivity.kt"
    )

    @Test
    fun `两页内容根均已上提 LegadoTheme（顶层主题作用域）`() {
        assertEquals("本批覆盖的宿主数必须为 2", 2, hosts.size)
        hosts.forEach { rel ->
            ComposeThemeScopeAssert.assertHostProvidesThemeScope(rel)
            val src = ComposeThemeScopeAssert.sourceText(rel)
            assertEquals(
                "$rel 不得再以 LegadoComposeTheme 作内容根",
                0,
                Regex("LegadoComposeTheme\\s*\\{").findAll(src).count()
            )
        }
    }
}
