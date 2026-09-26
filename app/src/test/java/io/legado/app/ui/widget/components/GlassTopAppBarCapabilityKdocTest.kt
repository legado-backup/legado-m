package io.legado.app.ui.widget.components

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 顶栏包 §6.2 配对测试：`GlassTopAppBar` 的**能力边界 KDoc**（名实一致声明）。
 *
 * 依据用户裁定（2026-09-24「最后一次全量审核」）：`GlassTopAppBar` 名为 "Glass" 却**不渲染真实毛玻璃**
 * （无 blur shader），且 `navIcon` 的渲染门槛是 `onNavClick != null`（不是「navIcon 非空」）。
 * 两处若在 KDoc 上写错，会直接误导后续按字面实现 ⇒ 用测试锁住声明与实现的**边界一致性**。
 *
 * 注意：KDoc 属注释，须用 `rawText`（不剥注释）读取；实现断言用 `sourceText`（剥注释，防注释造假）。
 */
class GlassTopAppBarCapabilityKdocTest {

    private val kdoc: String
        get() = SourceFileProbe.rawText("ui/widget/components/GlassTopAppBar.kt")

    private val impl: String
        get() = SourceFileProbe.sourceText("ui/widget/components/GlassTopAppBar.kt")

    @Test
    fun kdocDeclaresNoRealBlur() {
        assertTrue(
            "KDoc 必须显式声明「不渲染真实毛玻璃/模糊」",
            kdoc.contains("不渲染真实毛玻璃")
        )
        assertTrue(
            "KDoc 必须指向真毛玻璃的唯一样本（View 侧 setBackdropBlur + API ≥ 33）",
            kdoc.contains("setBackdropBlur") && kdoc.contains("API ≥ 33")
        )
    }

    @Test
    fun implementationHasNoBlurShader() {
        assertFalse(
            "实现中不得出现 RenderEffect（真模糊），否则「不含 blur shader」的声明失真",
            impl.contains("RenderEffect") || impl.contains("setRenderEffect")
        )
    }

    @Test
    fun kdocDeclaresNavIconRenderRule() {
        assertTrue(
            "KDoc 必须写明渲染门槛是 onNavClick 非 null（而非 navIcon 非空）",
            kdoc.contains("仅当 [onNavClick] 非 null 时才渲染返回位")
        )
        assertTrue(
            "KDoc 必须写明 painter 回退口径 navIcon ?: ic_back",
            kdoc.contains("painter = [navIcon] ?: `ic_back`")
        )
    }

    @Test
    fun boundaryClaimStillHoldsForViewSide() {
        val mainTopBar = SourceFileProbe.sourceText("ui/widget/MainTopBarView.kt")
        assertTrue(
            "层 1 View 侧必须仍提供 setBackdropBlur（否则「真毛玻璃仅 View 侧提供」的声明失真）",
            mainTopBar.contains("fun setBackdropBlur(")
        )
    }
}