package io.legado.app.ui.rss.search

import io.legado.app.testutil.ComposeThemeScopeAssert
import org.junit.Test

/**
 * 宿主主题作用域源契约（fix-compose-theme-scope-and-cache-icon tasks 2.2 / 4.1）。
 *
 * 同类缺陷：RSS 搜索页结果区（`RssSearchResultScreen` 读 onPrimary/primary）原不在
 * `LegadoTheme` 作用域内 ⇒ 夜间/自定义主题下标签与强调底色不随主题。
 */
class ComposeThemeScopeContractTest {

    @Test
    fun rssSearchHost_providesTopLevelThemeScope() {
        ComposeThemeScopeAssert.assertHostProvidesThemeScope(
            "io/legado/app/ui/rss/search/RssSearchActivity.kt"
        )
    }
}