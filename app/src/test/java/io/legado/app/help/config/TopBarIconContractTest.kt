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
        // 2026-09-26 §3.2 补齐：选择态关闭位（原写死在管理族动作槽 AppManagementScaffold）
        "close" to "ic_baseline_close",
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
        // navBack / close 属 Compose 侧语义（返回位归一 / 管理族选择态关闭位）⇒ View 侧不引用
        keys.filter { it.first != "navBack" && it.first != "close" }.forEach { (key, _) ->
            assertTrue("View 侧必须引用 TopBarConfig.Icons.$key", code.contains("TopBarConfig.Icons.$key"))
        }
    }

    /**
     * 顶栏包 §3.2（2026-09-26）：契约消费面从「两侧实现」扩到**顶栏实现文件全集合** ——
     * 主 Tab 实现 / Compose 顶栏 / 顶栏动作槽 / 管理族动作槽，任一文件写死图标资产即失败
     * （同口径机检门禁 20 `ai_tests/scripts/audit_topbar_hardcode.py`）。
     */
    @Test
    fun implementationFilesHaveNoIconHardcode() {
        val impls = listOf(
            "ui/widget/MainTopBarView.kt",
            "ui/widget/components/GlassTopAppBar.kt",
            "ui/widget/components/AppMenuSheet.kt",
            "ui/widget/compose/AppManagementScaffold.kt",
        )
        impls.forEach { rel ->
            val code = SourceFileProbe.sourceText(rel)
            assertFalse(
                "$rel 不得写死图标资产 R.drawable.ic_*（应走 TopBarConfig.Icons.*）",
                Regex("R\\.drawable\\.ic_").containsMatchIn(code)
            )
        }
        val family = SourceFileProbe.sourceText("ui/widget/compose/AppManagementScaffold.kt")
        assertTrue("管理族兜底图标须取契约值", family.contains("TopBarConfig.Icons.more"))
        assertTrue("管理族搜索位图标须取契约值", family.contains("TopBarConfig.Icons.search"))
        assertTrue("管理族选择态关闭位须取契约值", family.contains("TopBarConfig.Icons.close"))
        val sheet = SourceFileProbe.sourceText("ui/widget/components/AppMenuSheet.kt")
        assertTrue("顶栏动作槽溢出图标须取契约值", sheet.contains("TopBarConfig.Icons.more"))
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