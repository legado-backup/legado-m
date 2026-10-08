package io.legado.app.ui.config

import io.legado.app.testutil.ComposeThemeScopeAssert
import org.junit.Test

/**
 * 宿主主题作用域源契约（fix-compose-theme-scope-and-cache-icon tasks 2.3 / 4.1）。
 *
 * 同类缺陷：导航栏包管理列表（读 onSurface）原不在 `LegadoTheme` 作用域内 ⇒ 条目文字回落 M3 基线。
 */
class ComposeThemeScopeContractTest {

    @Test
    fun navigationBarManageHost_providesTopLevelThemeScope() {
        ComposeThemeScopeAssert.assertHostProvidesThemeScope(
            "io/legado/app/ui/config/NavigationBarManageActivity.kt"
        )
    }
}