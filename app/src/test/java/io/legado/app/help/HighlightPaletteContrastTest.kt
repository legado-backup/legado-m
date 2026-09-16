package io.legado.app.help

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertSame
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * R12.4 语义色板单测：对比度门禁 + 适配边界 + 墨水屏不依赖色相。
 *
 * 说明：本测试只调用 Android 无关的纯函数（`color`/`contrastRatio`/`resolve(style, tone)` 等），
 * 不触碰 `currentTone()`（其依赖阅读器配置，属真机验证范围）。
 */
class HighlightPaletteContrastTest {

    private val slots get() = HighlightPalette.slots()

    @Test
    fun allSlots_meetContrastGate_onDayBackground() {
        assertTrue("色板未登记任何槽位", slots.isNotEmpty())
        slots.forEach { slot ->
            val fg = HighlightPalette.color(slot, HighlightPalette.Tone.DAY)
            val ratio = HighlightPalette.contrastRatio(fg, HighlightPalette.BG_DAY)
            assertTrue(
                "槽位 $slot 浅底对比度不足: $ratio",
                ratio >= HighlightPalette.MIN_CONTRAST_RATIO
            )
        }
    }

    @Test
    fun allSlots_meetContrastGate_onNightBackground() {
        slots.forEach { slot ->
            val fg = HighlightPalette.color(slot, HighlightPalette.Tone.NIGHT)
            val ratio = HighlightPalette.contrastRatio(fg, HighlightPalette.BG_NIGHT)
            assertTrue(
                "槽位 $slot 深底对比度不足: $ratio",
                ratio >= HighlightPalette.MIN_CONTRAST_RATIO
            )
        }
    }

    @Test
    fun slots_areDistinctBetweenDayAndNight() {
        // 三态适配要求：浅底/深底必须取不同色值（否则等于没做适配）
        slots.forEach { slot ->
            assertNotEquals(
                "槽位 $slot 在浅底与深底取到同一颜色",
                HighlightPalette.color(slot, HighlightPalette.Tone.DAY),
                HighlightPalette.color(slot, HighlightPalette.Tone.NIGHT)
            )
        }
    }

    @Test
    fun eink_takesBlackAndMeetsGate() {
        slots.forEach { slot ->
            val fg = HighlightPalette.color(slot, HighlightPalette.Tone.EINK)
            assertEquals("墨水屏正文应取黑", 0xFF000000.toInt(), fg)
            assertTrue(
                HighlightPalette.contrastRatio(fg, 0xFFFFFFFF.toInt()) >=
                    HighlightPalette.MIN_CONTRAST_RATIO
            )
        }
    }

    @Test
    fun eink_resolvesPureColorStyleIntoUnderlinedStyle() {
        // 墨水屏不能靠色相区分 → 仅有颜色通道的「色板派生」样式应补下划线
        val style = HighlightStyle(
            textColor = 0xFF123456.toInt(),
            paletteSlot = HighlightPalette.Slot.DIALOGUE
        )
        val resolved = HighlightPalette.resolve(style, HighlightPalette.Tone.EINK)
        assertEquals(0xFF000000.toInt(), resolved.textColor)
        assertTrue("墨水屏态未补下划线（无法靠色相区分）", resolved.underline != null)
    }

    @Test
    fun eink_keepsExistingDecoration() {
        // 已有装饰（方框）时不再叠加下划线
        val style = HighlightStyle(
            textColor = 0xFF123456.toInt(),
            box = HighlightStyle.Deco(0),
            paletteSlot = HighlightPalette.Slot.DIALOGUE
        )
        val resolved = HighlightPalette.resolve(style, HighlightPalette.Tone.EINK)
        assertNull("已有装饰不应再补下划线", resolved.underline)
        assertTrue(resolved.box != null)
    }

    @Test
    fun paletteStyle_resolvesToToneColor() {
        val style = HighlightStyle(
            textColor = 0xFF999999.toInt(),
            paletteSlot = HighlightPalette.Slot.DIALOGUE
        )
        val day = HighlightPalette.resolve(style, HighlightPalette.Tone.DAY)
        val night = HighlightPalette.resolve(style, HighlightPalette.Tone.NIGHT)
        assertEquals(HighlightPalette.color(HighlightPalette.Slot.DIALOGUE, HighlightPalette.Tone.DAY), day.textColor)
        assertEquals(HighlightPalette.color(HighlightPalette.Slot.DIALOGUE, HighlightPalette.Tone.NIGHT), night.textColor)
    }

    @Test
    fun userPickedColor_isNeverRewritten() {
        // 适配边界：用户显式手选色（无槽位）必须原样返回（同一实例）
        val userStyle = HighlightStyle(textColor = 0xFF00FF00.toInt(), fill = 0x80123456.toInt())
        assertSame(userStyle, HighlightPalette.resolve(userStyle, HighlightPalette.Tone.NIGHT))
        assertSame(userStyle, HighlightPalette.resolve(userStyle, HighlightPalette.Tone.EINK))
    }

    @Test
    fun ensureReadable_raisesLowContrastColor() {
        val lowContrast = 0xFFFFF59D.toInt() // 浅黄压白底，对比度远低于门禁
        assertTrue(
            HighlightPalette.contrastRatio(lowContrast, HighlightPalette.BG_DAY) <
                HighlightPalette.MIN_CONTRAST_RATIO
        )
        val fixed = HighlightPalette.ensureReadable(lowContrast, HighlightPalette.BG_DAY)
        assertTrue(
            HighlightPalette.contrastRatio(fixed, HighlightPalette.BG_DAY) >=
                HighlightPalette.MIN_CONTRAST_RATIO
        )
    }

    @Test
    fun ensureReadable_keepsCompliantColor() {
        val ok = 0xFFB45309.toInt()
        assertEquals(ok, HighlightPalette.ensureReadable(ok, HighlightPalette.BG_DAY))
    }

    @Test
    fun textPresets_meetGate_andEinkHasNoFillPresets() {
        HighlightPalette.textPresets(HighlightPalette.Tone.DAY).forEach {
            assertTrue(HighlightPalette.contrastRatio(it, HighlightPalette.BG_DAY) >= HighlightPalette.MIN_CONTRAST_RATIO)
        }
        HighlightPalette.textPresets(HighlightPalette.Tone.NIGHT).forEach {
            assertTrue(HighlightPalette.contrastRatio(it, HighlightPalette.BG_NIGHT) >= HighlightPalette.MIN_CONTRAST_RATIO)
        }
        assertEquals(0, HighlightPalette.bgPresets(HighlightPalette.Tone.EINK).size)
    }
}