package io.legado.app.ui.book.read

import io.legado.app.testutil.ComposeThemeScopeAssert
import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * NEW-71 / G-37 放量批 B：阅读页内的两个弹层宿主主题作用域守护
 * （`SelectionSearchEngineManageDialog` 划词搜索引擎管理 / `TextActionMenu` 文字动作菜单）。
 *
 * 两者原内容根均为 `LegadoComposeTheme`（只透传色板/字体）⇒ 夜间/主题包下内容回落默认色板；
 * 现均上提为唯一主题入口 `LegadoTheme`（色板 + 字号 + 主题字体族）。
 */
class ReadDialogsThemeScopeTest {

    private val dialogs = listOf(
        "io/legado/app/ui/book/read/SelectionSearchEngineManageDialog.kt",
        "io/legado/app/ui/book/read/TextActionMenu.kt"
    )

    @Test
    fun `两弹层内容根均已上提 LegadoTheme（顶层主题作用域）`() {
        assertEquals("本批覆盖的弹层数必须为 2", 2, dialogs.size)
        dialogs.forEach { rel ->
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
