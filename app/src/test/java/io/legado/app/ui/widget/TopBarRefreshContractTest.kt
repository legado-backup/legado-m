package io.legado.app.ui.widget

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 顶栏包 §1.3 + §2.1/§2.2：View 侧顶栏**统一刷新入口 + 签名早退**契约（JVM 可跑，2026-09-25）。
 *
 * 09-08 报障根因：`MainActivity.refreshMainTopBars` 按类型分叉（`MainTopBarView` 全量刷 /
 * `TitleBar` 只刷底色）⇒ 观感不一致。归一后两侧同实现 [TopBarRefreshable]、同判据
 * （`TopBarConfig.currentSignature`，含 `themeUiSignature()`），签名未变即早退。
 */
class TopBarRefreshContractTest {

    private val iface = "ui/widget/TopBarRefreshable.kt"
    private val view = "ui/widget/MainTopBarView.kt"
    private val titleBar = "ui/widget/TitleBar.kt"

    @Test
    fun interfaceIsSingleEntryWithSignatureFriendlyDefault() {
        val code = SourceFileProbe.sourceText(iface)
        assertTrue("统一入口接口必须存在", code.contains("interface TopBarRefreshable"))
        assertTrue(
            "入口方法必须带 force 参数且默认 false（默认走签名早退；变更事件显式传 true）",
            code.contains("fun refreshTopBarStyle(force: Boolean = false)")
        )
    }

    @Test
    fun viewSideImplementsUnifiedEntry() {
        val code = SourceFileProbe.sourceText(view)
        assertTrue("MainTopBarView 必须实现 TopBarRefreshable", code.contains("StatusBarInsetAware, TopBarRefreshable"))
        assertTrue("必须提供 override 实现", code.contains("override fun refreshTopBarStyle(force: Boolean) {"))
        assertTrue(
            "早退判据必须与 applyTopBarStyle 同函数（TopBarConfig.currentSignature）",
            code.contains("val signature = \"\${TopBarConfig.currentSignature(AppConfig.isNightTheme)}|\$mode\"")
        )
        assertTrue(
            "签名未变且非 force ⇒ 必须早退",
            code.contains("if (!force && styleSignature == signature) return")
        )
        assertTrue(
            "旧 refreshStyle() 入口不得残留（否则又出现第二入口）",
            !code.contains("fun refreshStyle()")
        )
        assertTrue(
            "自订阅 TOP_BAR_CHANGED 通道属「变更事件」⇒ 必须 force=true（保行为等价）",
            code.contains("refreshTopBarStyle(force = true)")
        )
    }

    @Test
    fun titleBarImplementsUnifiedEntryWithSameSignature() {
        val code = SourceFileProbe.sourceText(titleBar)
        assertTrue("TitleBar 必须实现 TopBarRefreshable", code.contains("AppBarLayout(context, attrs), TopBarRefreshable"))
        assertTrue("必须提供 override 实现", code.contains("override fun refreshTopBarStyle(force: Boolean) {"))
        assertTrue(
            "TitleBar 判据必须同函数（否则两侧判据再度分叉）",
            code.contains("val signature = \"\${TopBarConfig.currentSignature(AppConfig.isNightTheme)}|\$topBarColorManaged\"")
        )
        assertTrue(
            "签名未变且非 force ⇒ 必须早退",
            code.contains("if (!force && styleSignature == signature) return")
        )
        assertTrue(
            "managed 门槛与墨水屏排除必须保留（原行为不受影响）",
            code.contains("if (!topBarColorManaged || !isEInkModeExcluded()) return")
        )
    }

    @Test
    fun noLegacyTypeForkRemainsInHost() {
        // 宿主（MainActivity）的类型分叉已由 MainTopBarRefreshUnifyTest 断言；此处守住「两侧不再互调对方专有方法」
        assertFalse(
            "MainTopBarView 不得再直接调 TitleBar 专有刷新",
            SourceFileProbe.sourceText(view).contains("refreshTopBarAppearance")
        )
    }
}