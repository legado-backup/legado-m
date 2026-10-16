package io.legado.app.ui.highlight

import io.legado.app.testutil.ComposeThemeScopeAssert
import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * NEW-74 / G-37 放量批 C：`HighlightRuleGroupManageDialog`（高亮规则分组管理弹窗）
 * 宿主内容根主题作用域守护。
 *
 * 原内容根无任何主题作用域 ⇒ 分组列表/输入框/确认按钮子树回落 M3 默认色板；
 * 现上提为唯一主题入口 `LegadoTheme`（其「危险色」取色单源另由
 * `HighlightRuleGroupManageDialogDangerTokenTest` 守护）。
 */
class HighlightRuleGroupManageDialogThemeScopeTest {

    private val rel = "io/legado/app/ui/highlight/HighlightRuleGroupManageDialog.kt"

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
