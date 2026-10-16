package io.legado.app.ui.association

import io.legado.app.testutil.ComposeThemeScopeAssert
import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * NEW-74 / G-37 放量批 C：`ImportRedThemeDialog`（导入主题弹窗）宿主内容根主题作用域守护。
 *
 * 原内容根无任何主题作用域 ⇒ 进度/结果文案与动作按钮所在子树回落 M3 默认色板
 * （夜间「黑字黑图标」）；现上提为唯一主题入口 `LegadoTheme`。
 */
class ImportRedThemeDialogThemeScopeTest {

    private val rel = "io/legado/app/ui/association/ImportRedThemeDialog.kt"

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
