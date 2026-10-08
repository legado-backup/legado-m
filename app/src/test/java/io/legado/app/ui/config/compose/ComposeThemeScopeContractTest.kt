package io.legado.app.ui.config.compose

import io.legado.app.testutil.ComposeThemeScopeAssert
import org.junit.Test

/**
 * 宿主主题作用域源契约（fix-compose-theme-scope-and-cache-icon tasks 2.4 / 4.1）。
 *
 * 同类缺陷（变体形态）：`setContent` 只包 `LegadoComposeTheme`（字体层）而**没有** `LegadoTheme`
 * ⇒ 设置页内的 `SettingsSearchBar`（读 onSurface/onSurfaceVariant）回落 M3 默认基线。
 */
class ComposeThemeScopeContractTest {

    @Test
    fun composeSettingHost_providesTopLevelThemeScope() {
        ComposeThemeScopeAssert.assertHostProvidesThemeScope(
            "io/legado/app/ui/config/compose/ComposeSettingFragment.kt"
        )
    }
}