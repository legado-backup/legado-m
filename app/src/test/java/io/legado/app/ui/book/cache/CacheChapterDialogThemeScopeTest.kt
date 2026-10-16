package io.legado.app.ui.book.cache

import io.legado.app.testutil.ComposeThemeScopeAssert
import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * NEW-71 / G-37 放量批 B：`CacheChapterDialog` 宿主内容根主题作用域守护。
 *
 * 原内容根为 `LegadoComposeTheme`（只透传色板/字体）⇒ 夜间/主题包下内容回落默认色板；
 * 现上提为唯一主题入口 `LegadoTheme`（色板 + 字号 + 主题字体族）。
 */
class CacheChapterDialogThemeScopeTest {

    private val rel = "io/legado/app/ui/book/cache/CacheChapterDialog.kt"

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
