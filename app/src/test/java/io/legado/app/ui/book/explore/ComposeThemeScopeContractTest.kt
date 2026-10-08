package io.legado.app.ui.book.explore

import io.legado.app.testutil.ComposeThemeScopeAssert
import org.junit.Test

/**
 * 宿主主题作用域源契约（fix-compose-theme-scope-and-cache-icon tasks 2.1 / 4.1）。
 *
 * 守护 2026-10-08 用户报障：发现页书籍列表 ⋮ 弹层在夜间主题下「图标与文字全黑」——
 * 根因是内容区（列表 + 弹层）未处于 `LegadoTheme` 作用域内（`LegadoTheme` 原先只包顶栏）。
 */
class ComposeThemeScopeContractTest {

    @Test
    fun exploreHost_providesTopLevelThemeScope() {
        ComposeThemeScopeAssert.assertHostProvidesThemeScope(
            "io/legado/app/ui/book/explore/ExploreShowActivity.kt"
        )
    }
}