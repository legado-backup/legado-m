package io.legado.app.help.config

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 顶栏包 §1.1 图标资产契约收口（JVM 可跑，2026-09-25）。
 *
 * 原状：两侧实现各写死图标资源（`MainTopBarView` 11 处 / `GlassTopAppBar` 1 处）⇒ 换资产必漏改。
 * 归一后：唯一来源 = `TopBarConfig.Icons`，实现内**禁止**再出现图标类 `R.drawable.*` 硬编码。
 */
class TopBarIconContractTest {

    private val config = "help/config/TopBarConfig.kt"
    private val view = "ui/widget/MainTopBarView.kt"
    private val composeBar = "ui/widget/components/GlassTopAppBar.kt"

    /** 契约必须提供的图标键（与 fix 前两侧硬编码逐一对应）。 */
    private val keys = listOf(
        "more" to "ic_more_vert",
        "search" to "ic_search",
        "sort" to "ic_sort",
        "star" to "ic_star_border",
        "refresh" to "ic_refresh_black_24dp",
        "login" to "ic_bottom_person",
        "filterToggle" to "ic_expand_more",
        "titleArrow" to "ic_arrow_drop_down",
        "navBack" to "ic_back",
    )

    @Test
    fun contractDeclaresAllIconKeys() {
        val code = SourceFileProbe.sourceText(config)
        assertTrue("契约必须声明为 object Icons（唯一资产来源）", code.contains("object Icons {"))
        keys.forEach { (key, asset) ->
            assertTrue("契约缺 $key ⇒ 应在 TopBarConfig.Icons.$key = R.drawable.$asset", code.contains("R.drawable.$asset"))
        }
        assertTrue(
            "契约对象须标注 @DrawableRes（防误传非资源值）",
            SourceFileProbe.rawText(config).contains("@DrawableRes")
        )
    }

    @Test
    fun viewSideHasNoIconHardcode() {
        val code = SourceFileProbe.sourceText(view)
        assertFalse(
            "View 侧不得再出现图标类 R.drawable.ic_* 硬编码（应走 TopBarConfig.Icons.*）",
            Regex("R\\.drawable\\.ic_").containsMatchIn(code)
        )
        keys.filter { it.first != "navBack" }.forEach { (key, _) ->
            assertTrue("View 侧必须引用 TopBarConfig.Icons.$key", code.contains("TopBarConfig.Icons.$key"))
        }
    }

    @Test
    fun composeSideHasNoIconHardcode() {
        val code = SourceFileProbe.sourceText(composeBar)
        assertFalse(
            "Compose 顶栏不得再出现 R.drawable.* 图标硬编码（应走 TopBarConfig.Icons.navBack）",
            code.contains("R.drawable.")
        )
        assertTrue(
            "返回位默认资产必须取契约值",
            code.contains("painterResource(TopBarConfig.Icons.navBack)")
        )
    }

    @Test
    fun backgroundAssetIsNotAnIcon() {
        // 回归对照：`bg_discover_embedded_action` 是**背景**资源（非图标）⇒ 不属本契约范围，不得被误搬。
        val code = SourceFileProbe.sourceText(view)
        assertTrue(
            "背景资源应保持原样（不在 Icons 契约范围内）",
            code.contains("R.drawable.bg_discover_embedded_action")
        )
        assertFalse(
            "背景资源不得被误登记进 Icons 契约",
            SourceFileProbe.sourceText(config).contains("bg_discover_embedded_action")
        )
    }
}