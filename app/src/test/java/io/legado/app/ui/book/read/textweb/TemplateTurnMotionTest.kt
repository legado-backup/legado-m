package io.legado.app.ui.book.read.textweb

import io.legado.app.constant.PageAnim
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 模板面翻页过渡决策的配对测试（4.20）。
 *
 * 为什么机检：档位映射错了**不会报错、也不会白屏**，只会"动画形态与用户设置不符"（选了卷曲却是硬切、
 * 选了无动画却还在滑）—— 真机上极难归因到具体档位，只能靠逐档断言把它钉住。
 */
class TemplateTurnMotionTest {

    @Test
    fun `无动画与滚动档位都不放快照`() {
        assertEquals(TemplateTurnMotion.Style.NONE, TemplateTurnMotion.specOf(PageAnim.noAnim).style)
        assertFalse("无动画档位不得放快照", TemplateTurnMotion.specOf(PageAnim.noAnim).hasOverlay)
        // 模板面本身即分页（没有滚动容器语义）⇒ 不得制造"假滚动"
        assertEquals(TemplateTurnMotion.Style.NONE, TemplateTurnMotion.specOf(PageAnim.scrollPageAnim).style)
    }

    @Test
    fun `覆盖与联动覆盖走快照滑出且联动更长`() {
        assertEquals(TemplateTurnMotion.Style.COVER, TemplateTurnMotion.specOf(PageAnim.coverPageAnim).style)
        assertEquals(
            TemplateTurnMotion.Style.LINKED_COVER,
            TemplateTurnMotion.specOf(PageAnim.linkedCoverPageAnim).style
        )
        assertTrue(
            "联动覆盖时长须更长（视差用时长差近似）",
            TemplateTurnMotion.specOf(PageAnim.linkedCoverPageAnim).durationMs >
                TemplateTurnMotion.specOf(PageAnim.coverPageAnim).durationMs
        )
    }

    @Test
    fun `滑动档位须联动下层`() {
        assertEquals(TemplateTurnMotion.Style.SLIDE, TemplateTurnMotion.specOf(PageAnim.slidePageAnim).style)
    }

    @Test
    fun `卷曲仿真降级为覆盖且不谎称实现`() {
        // 单层 WebView 画不出纸张曲面 ⇒ 必须显式降级为覆盖滑出，不得返回 SLIDE 冒充"联动"
        val spec = TemplateTurnMotion.specOf(PageAnim.simulationPageAnim)
        assertEquals(TemplateTurnMotion.Style.COVER, spec.style)
        assertEquals(TemplateTurnMotion.DurationMillis, spec.durationMs)
    }

    @Test
    fun `未知档位保守回落为覆盖而非硬切`() {
        // 新增档位若忘记登记，宁可"仍有过渡"也不要静默变硬切（硬切在真机上更难被归因）
        assertEquals(TemplateTurnMotion.Style.COVER, TemplateTurnMotion.specOf(99).style)
        assertTrue(TemplateTurnMotion.specOf(99).hasOverlay)
    }
}
