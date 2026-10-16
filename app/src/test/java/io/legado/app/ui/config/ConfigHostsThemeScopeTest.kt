package io.legado.app.ui.config

import io.legado.app.testutil.ComposeThemeScopeAssert
import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * NEW-74 续 / G-37 放量批 D：`io.legado.app.ui.config` 包内宿主内容根主题作用域守护（**机械改写产物**，一包一测）。
 *
 * 这些宿主原内容块**顶层无主题作用域** ⇒ 子树 `MaterialTheme.colorScheme` 回落 M3 默认亮色基线
 * （夜间/主题包下黑字黑图标、浅色输入框、白底菜单）。现统一上提为唯一主题入口 `LegadoTheme`
 * （色板 + 字号 + 主题字体族）。改写与校验由 `ai_tests/scripts/apply_theme_scope_wrap.py` 机械化完成，
 * 并与门禁 G-37 使用**同一套块定位逻辑**（不会出现「工具改了但门禁不认」）。
 */
class ConfigHostsThemeScopeTest {

    private val hosts = listOf(
        "io/legado/app/ui/config/AiProviderEditActivity.kt",
        "io/legado/app/ui/config/BubbleEditDialog.kt",
        "io/legado/app/ui/config/ConfigActivity.kt",
        "io/legado/app/ui/config/DirectLinkUploadConfig.kt",
        "io/legado/app/ui/config/ImportCheckConfigDialog.kt",
        "io/legado/app/ui/config/RelaySettingsActivity.kt",
        "io/legado/app/ui/config/ThemePackageEditDialog.kt",
        "io/legado/app/ui/config/TopBarEditDialog.kt",
        "ui/config/ThemePackageEditDialog.kt"
    )

    @Test
    fun `包内宿主内容根均已上提 LegadoTheme（顶层主题作用域）`() {
        assertEquals("本文件覆盖的宿主数已变化，请同步更新本测试", 9, hosts.size)
        hosts.forEach { rel ->
            ComposeThemeScopeAssert.assertHostProvidesThemeScope(rel)
            val src = ComposeThemeScopeAssert.sourceText(rel)
            val iTheme = src.indexOf("LegadoTheme {")
            val iFontLayer = src.indexOf("LegadoComposeTheme {")
            // ⚠ 不可断言 `LegadoComposeTheme` 计数为 0：权威嵌套形态是 `LegadoTheme { LegadoComposeTheme { … } }`
            //   （色板层在外、**历史字体层在内**，见铁律 S1）；真正要拦的是**倒置**（字体层在外当内容根）。
            assertEquals(
                "$rel 若仍含历史字体层 `LegadoComposeTheme`，它必须位于 `LegadoTheme` **之内**（不得倒置当作内容根）",
                true,
                iFontLayer < 0 || (iTheme in 0 until iFontLayer)
            )
        }
    }
}
