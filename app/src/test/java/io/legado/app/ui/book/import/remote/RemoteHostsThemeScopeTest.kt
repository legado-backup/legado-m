package io.legado.app.ui.book.import.remote

import io.legado.app.testutil.ComposeThemeScopeAssert
import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * NEW-74 续 / G-37 放量批 D：`io.legado.app.ui.book.import.remote` 包内宿主内容根主题作用域守护（**机械改写产物**，一包一测）。
 *
 * 这些宿主原内容块**顶层无主题作用域** ⇒ 子树 `MaterialTheme.colorScheme` 回落 M3 默认亮色基线
 * （夜间/主题包下黑字黑图标、浅色输入框、白底菜单）。现统一上提为唯一主题入口 `LegadoTheme`
 * （色板 + 字号 + 主题字体族）。改写与校验由 `ai_tests/scripts/apply_theme_scope_wrap.py` 机械化完成，
 * 并与门禁 G-37 使用**同一套块定位逻辑**（不会出现「工具改了但门禁不认」）。
 */
class RemoteHostsThemeScopeTest {

    private val hosts = listOf(
        "io/legado/app/ui/book/import/remote/ServersDialog.kt"
    )

    @Test
    fun `包内宿主内容根均已上提 LegadoTheme（顶层主题作用域）`() {
        assertEquals("本文件覆盖的宿主数已变化，请同步更新本测试", 1, hosts.size)
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
