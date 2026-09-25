package io.legado.app.ui.widget.components

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 顶栏包 §1.3 + §2.2（Compose 侧）：`GlassTopAppBar` 必须用**契约签名**做样式解析的记忆键。
 *
 * 为什么必须（两件事同源）：
 * ①**刷新判定统一**——View 侧（`MainTopBarView` / `TitleBar`）已统一以 `TopBarConfig.currentSignature`
 *   判定是否重刷；Compose 侧若只看 `ThemeSync.version`（主题信号抖动即重算），两侧判据就再度分叉。
 * ②**门禁 §3.1 / H13 的前置**——G-03 现机制是「文件内子串出现」校验（非调用校验），
 *   若 Compose 顶栏宿主**不真实引用**该函数，把它登记进门禁就是恒 PASS 的假安全。
 *
 * 因此本测试锁死：宿主真实引用契约签名，且**样式解析的 remember 键**是该签名（而非 themeVersion），
 * 从而具备「签名未变 ⇒ 复用、签名变化 ⇒ 重算」的真实早退语义。
 */
class GlassTopAppBarSignatureKeyTest {

    private val page = "ui/widget/components/GlassTopAppBar.kt"

    private fun src(): String = SourceFileProbe.sourceText(page)

    @Test
    fun hostReferencesContractSignature() {
        val s = src()
        assertTrue(
            "Compose 顶栏宿主必须真实引用契约签名（G-03 扩展的前置）",
            s.contains("TopBarConfig.currentSignature(AppConfig.isNightTheme)")
        )
        assertTrue(
            "签名须存为可复用的槽（styleSignature）",
            s.contains("val styleSignature = remember(themeVersion) {")
        )
    }

    @Test
    fun styleResolutionIsKeyedBySignatureNotThemeVersion() {
        val s = src()
        assertTrue("配置解析必须以签名为键", s.contains("val config = remember(styleSignature) {"))
        assertTrue(
            "壁纸解析必须以签名为键（否则主题信号抖动会重复读盘）",
            s.contains("val wallpaperFile = remember(styleSignature, isRegular) {")
        )
        assertTrue(
            "底色解析必须以签名为键",
            s.contains("val defaultColor = remember(styleSignature) {")
        )
        assertTrue(
            "圆角解析必须以签名为键",
            s.contains("val cornerRadius = remember(styleSignature, isRegular) {")
        )
    }

    @Test
    fun themeVersionSubscriptionStillKept() {
        val s = src()
        assertTrue(
            "主题信号订阅不得删除（签名槽本身也是按主题信号重算的）",
            s.contains("val themeVersion = ThemeSync.version")
        )
        assertTrue(
            "签名槽必须以主题信号为键（否则主题真变化时签名不会更新）",
            s.contains("val styleSignature = remember(themeVersion) {")
        )
    }
}