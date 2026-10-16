package io.legado.app.ui.widget

import io.legado.app.testutil.ComposeThemeScopeAssert
import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * NEW-74 / G-37 放量批 C·续：`SourceSelectDialog`（书源/项目选择弹窗）
 * 宿主内容根主题作用域守护。
 *
 * 原 `dialog.setContentView(ComposeView(...).setContent { … })` 无任何主题作用域 ⇒ 标题/列表/
 * 选中态子树在夜间/主题包下回落 M3 默认色板；现上提为唯一主题入口 `LegadoTheme`。
 */
class SourceSelectDialogThemeScopeTest {

    private val rel = "io/legado/app/ui/widget/SourceSelectDialog.kt"

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
