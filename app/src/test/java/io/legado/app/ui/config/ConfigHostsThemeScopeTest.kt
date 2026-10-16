package io.legado.app.ui.config

import io.legado.app.testkit.SourceFileProbe
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
        "io/legado/app/ui/config/ConfigActivity.kt",
        "io/legado/app/ui/config/ImportCheckConfigDialog.kt",
        "io/legado/app/ui/config/DirectLinkUploadConfig.kt",
        "io/legado/app/ui/config/BubbleEditDialog.kt",
        "io/legado/app/ui/config/AiProviderEditActivity.kt",
        "io/legado/app/ui/config/TopBarEditDialog.kt",
        "io/legado/app/ui/config/ThemePackageEditDialog.kt",
        "io/legado/app/ui/config/RelaySettingsActivity.kt"
    )

    @Test
    fun `包内宿主内容根均已上提 LegadoTheme（顶层主题作用域）`() {
        assertEquals("本文件覆盖的宿主数已变化，请同步更新本测试", 8, hosts.size)
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

    /**
     * NEW-74 批 D 事故回归守卫（**编译期实证**）：`return@setContent` 早退**必须留在 `setContent` 本层**。
     *
     * 事故：机械改写把整个块体移入 `LegadoTheme { … }`，而 `LegadoTheme` 是**非内联** `@Composable`
     * lambda ⇒ Kotlin 报 `'return' is prohibited here`（`ThemePackageEditDialog.kt:92`），
     * **整包 `compileAppDebugKotlin` 失败** —— 而 pre-commit 的 G-45 只跑「改动包」，未覆盖整模块编译，
     * 故该错误逃过提交门禁、在随后的整包构建才暴露。
     * 本守卫锁「早退在 LegadoTheme 之前」这一形态，防回退。
     */
    @Test
    fun `早退必须留在 setContent 本层（不得移入非内联的 LegadoTheme 内）`() {
        // ⚠ 必须用**剥注释**的 SourceFileProbe：`ComposeThemeScopeAssert.sourceText` 是原文读取，
        //   会把注释里提到的 `return@setContent` 也计入（本轮实测 count=2 假失败）。
        val src = SourceFileProbe.sourceText("ui/config/ThemePackageEditDialog.kt")
        val compact = src.replace(Regex("\\s+"), "")
        assertEquals("本文件只应有 1 处 return@setContent 早退（Active 代码）", 1,
            Regex("return@setContent").findAll(src).count())
        assertEquals(
            "早退必须出现在 `LegadoTheme{` 之前（移入其内会被 Kotlin 判 'return' is prohibited here）",
            true,
            compact.indexOf("return@setContent") in 1 until compact.indexOf("LegadoTheme{")
        )
    }
}
