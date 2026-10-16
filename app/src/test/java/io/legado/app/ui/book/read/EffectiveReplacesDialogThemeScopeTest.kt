package io.legado.app.ui.book.read

import io.legado.app.testutil.ComposeThemeScopeAssert
import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * NEW-74 / G-37 放量批 C：`EffectiveReplacesDialog`（当前生效替换弹窗）
 * 宿主内容根主题作用域守护。
 *
 * 原内容根无任何主题作用域 ⇒ 替换项列表/关闭按钮子树在夜间/主题包下回落 M3 默认色板；
 * 现上提为唯一主题入口 `LegadoTheme`。
 */
class EffectiveReplacesDialogThemeScopeTest {

    private val rel = "io/legado/app/ui/book/read/EffectiveReplacesDialog.kt"

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
