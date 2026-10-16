package io.legado.app.ui.config

import io.legado.app.testutil.ComposeThemeScopeAssert
import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * NEW-74 / G-37 放量批 C：`CoverRuleConfigDialog`（封面规则设置弹窗）
 * 宿主内容根主题作用域守护。
 *
 * 原内容根无任何主题作用域 ⇒ 开关行/输入框/预览区子树在夜间/主题包下回落 M3 默认色板；
 * 现上提为唯一主题入口 `LegadoTheme`（内层 `CompositionLocalProvider` 字体层保持不变）。
 */
class CoverRuleConfigDialogThemeScopeTest {

    private val rel = "io/legado/app/ui/config/CoverRuleConfigDialog.kt"

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
