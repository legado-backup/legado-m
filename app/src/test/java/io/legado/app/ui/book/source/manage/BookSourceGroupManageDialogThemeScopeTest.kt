package io.legado.app.ui.book.source.manage

import io.legado.app.testutil.ComposeThemeScopeAssert
import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * NEW-74 / G-37 放量批 C：`GroupManageDialog`（书源分组管理弹窗）宿主内容根主题作用域守护。
 *
 * 原内容根无任何主题作用域 ⇒ 弹窗读 M3 派生色的组件（输入框/图标/菜单）在夜间、主题包、
 * 自定义主题色下回落 M3 默认亮色基线（浅色输入框、白底菜单）；现上提为唯一主题入口 `LegadoTheme`
 * （色板 + 字号 + 主题字体族）。
 */
class BookSourceGroupManageDialogThemeScopeTest {

    private val rel = "io/legado/app/ui/book/source/manage/GroupManageDialog.kt"

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
