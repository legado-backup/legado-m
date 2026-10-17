package io.legado.app.ui.book.read.epub.loading

import io.legado.app.help.config.EpubLoadingTemplate
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 首屏模板**回落契约与状态机**单测（reader-theme-family 3.12 配对）。
 *
 * 这是本特性**最高价值的一条**：模板机制的失败模式不是"难看"，而是"**白屏/黑屏**"——
 * 一旦模板路径"看起来接管了却什么都没画"，用户会看到空白首屏。故两条不变量必须可证：
 * ①`LoadingTemplateOverlayPolicy.resolve` 只在这三项齐备时给 TEMPLATE（无模板 / 无插画 / 尺寸非法 ⇒ LEGACY）；
 * ②`LoadingOverlayState.endRound()` 必须把模板清空（**防泄漏到下一次开书**）。
 */
class EpubLoadingOverlayFallbackTest {

    private val template = EpubLoadingTemplate.BUILT_IN[0]

    @Test
    fun `无模板必须回落既有遮罩`() {
        assertEquals(
            LoadingOverlayMode.LEGACY,
            LoadingTemplateOverlayPolicy.resolve(null, artworkReady = true, viewWidth = 1000, viewHeight = 800)
        )
    }

    @Test
    fun `插画不可用必须回落既有遮罩`() {
        // SVG 解析失败/资源缺失 ⇒ artworkReady=false ⇒ 绝不能"画个空帧"
        assertEquals(
            LoadingOverlayMode.LEGACY,
            LoadingTemplateOverlayPolicy.resolve(template, artworkReady = false, viewWidth = 1000, viewHeight = 800)
        )
    }

    @Test
    fun `视图尺寸非法必须回落既有遮罩`() {
        assertEquals(
            LoadingOverlayMode.LEGACY,
            LoadingTemplateOverlayPolicy.resolve(template, artworkReady = true, viewWidth = 0, viewHeight = 800)
        )
        assertEquals(
            LoadingOverlayMode.LEGACY,
            LoadingTemplateOverlayPolicy.resolve(template, artworkReady = true, viewWidth = 1000, viewHeight = -1)
        )
    }

    @Test
    fun `三者齐备才走模板`() {
        assertEquals(
            LoadingOverlayMode.TEMPLATE,
            LoadingTemplateOverlayPolicy.resolve(template, artworkReady = true, viewWidth = 1000, viewHeight = 800)
        )
    }

    @Test
    fun `注入模板会带上夜态并重置失败态`() {
        val state = LoadingOverlayState()
        state.markFailed()
        state.inject(template, night = true)
        assertEquals(template, state.template)
        assertTrue("注入时须带上夜态（否则首屏配色与阅读主题不一致）", state.night)
        assertFalse("新注入必须清掉上一轮的失败态", state.failed)
    }

    @Test
    fun `正常加载与失败加载共用同一模板 仅切换失败态`() {
        val state = LoadingOverlayState()
        state.inject(template, night = false)
        state.markFailed()
        assertTrue("失败态：同一遮罩换强调色", state.failed)
        assertEquals("失败时模板仍在（首屏形态不变）", template, state.template)
        state.beginLoading()
        assertFalse("下一次正常加载须复位失败态", state.failed)
    }

    @Test
    fun `一轮结束必须清空模板 防泄漏到下一次开书`() {
        val state = LoadingOverlayState()
        state.inject(template, night = true)
        state.markFailed()
        state.endRound()
        assertNull("endRound 后模板必须为 null（否则下一本书会顶着上一本的模板）", state.template)
        assertFalse("endRound 后失败态须复位", state.failed)
        assertEquals(
            "清空后策略必须判回落",
            LoadingOverlayMode.LEGACY,
            LoadingTemplateOverlayPolicy.resolve(state.template, true, 1000, 800)
        )
    }

    @Test
    fun `清除加载态不得顺手清掉模板`() {
        // clearLoading() 在同一本书"切章"时高频调用；若顺手清模板，切章后首屏就没了模板
        val state = LoadingOverlayState()
        state.inject(template, night = false)
        state.clearFailure()
        assertEquals("clearLoading 只清失败态，模板须保留", template, state.template)
    }
}
