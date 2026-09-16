package io.legado.app.help

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * F-P1-2 高亮规则系统单元测试
 * 验证 HighlightStyle 的 isEmpty + needsPerColumnDraw
 *
 * 注：R12.3 起同区间多命中改为「整体优先级」（后定义者整体胜出），
 * 逐通道 `merge` 已删除，相应用例随之移除（见 HighlightMatcherTest 的整体优先级用例）。
 *
 * 验证点：
 * - isEmpty 全通道关闭时为 true
 * - needsPerColumnDraw 除纯背景填充外任何通道开启时为 true
 */
class HighlightStyleTest {

    @Test
    fun isEmpty_allChannelsOff() {
        // 边界用例：全通道关闭时 isEmpty = true
        val empty = HighlightStyle()
        assertTrue("默认样式 isEmpty", empty.isEmpty)

        val nonEmpty = HighlightStyle(fill = 0x80FFF176.toInt())
        assertFalse("有 fill 不 isEmpty", nonEmpty.isEmpty)
    }

    @Test
    fun needsPerColumnDraw_anyNonFillChannel() {
        // 正常用例：除纯背景填充外任何通道开启时 needsPerColumnDraw = true
        val pureFill = HighlightStyle(fill = 0x80FFF176.toInt())
        assertFalse("仅 fill 不需要逐列绘制", pureFill.needsPerColumnDraw)

        val withText = HighlightStyle(fill = 0x80FFF176.toInt(), textColor = 0xFFFF0000.toInt())
        assertTrue("fill + textColor 需要逐列绘制", withText.needsPerColumnDraw)

        val withUnderline = HighlightStyle(underline = HighlightStyle.Underline())
        assertTrue("仅 underline 需要逐列绘制", withUnderline.needsPerColumnDraw)

        val withBold = HighlightStyle(bold = true)
        assertTrue("仅 bold 需要逐列绘制", withBold.needsPerColumnDraw)
    }

    /** B2-④：线宽/线距未设置时回退旧硬编码默认值（1.5dp / 2dp，观感零回归） */
    @Test
    fun underline_widthDistance_fallbackWhenUnset() {
        val u = HighlightStyle.Underline()
        assertEquals("未设置线宽回退 1.5f", 1.5f, u.resolvedWidth, 0.001f)
        assertEquals("未设置线距回退 2f", 2f, u.resolvedDistance, 0.001f)
    }

    /** B2-④：显式设置后取用户值 */
    @Test
    fun underline_widthDistance_explicitTakesEffect() {
        val u = HighlightStyle.Underline(width = 4f, distance = 6f)
        assertEquals("显式线宽生效", 4f, u.resolvedWidth, 0.001f)
        assertEquals("显式线距生效", 6f, u.resolvedDistance, 0.001f)
    }

    /** B2-④：线距 0 是合法用户值（与"未设置"可区分） */
    @Test
    fun underline_distanceZero_isDistinctFromUnset() {
        val u = HighlightStyle.Underline(distance = 0f)
        assertEquals("0 线距按用户值生效", 0f, u.resolvedDistance, 0.001f)
    }

    /** B2-⑤：阴影半径过小视为无阴影（`"shadow": {}` 空对象兜底），过大则夹到上界 */
    @Test
    fun shadow_normalizedRadiusGate() {
        assertNull("radius=0 → 无阴影", HighlightStyle.Shadow().normalized())
        assertNotNull("radius=2 → 保留", HighlightStyle.Shadow(radius = 2f).normalized())
        assertEquals(
            "半径夹到上界 25f", 25f,
            HighlightStyle.Shadow(radius = 99f).normalized()!!.radius, 0.001f
        )
    }

    /** B2-⑤：仅阴影也算非空样式（isEmpty 纳入新通道） */
    @Test
    fun shadow_affectsIsEmpty() {
        assertTrue("无阴影时 isEmpty", HighlightStyle().isEmpty)
        assertFalse(
            "仅阴影不 isEmpty",
            HighlightStyle(shadow = HighlightStyle.Shadow(radius = 3f)).isEmpty
        )
    }

    /** B2-⑤：sanitized 把空对象阴影归一为 null（渲染层据此不绘制，防整列描边） */
    @Test
    fun sanitized_dropsDegenerateShadow() {
        val s = HighlightStyle(shadow = HighlightStyle.Shadow()).sanitized()
        assertNull("退化阴影被归一为 null", s.shadow)
    }
}
