package io.legado.app.help

import io.legado.app.ui.book.read.config.HighlightRule
import io.legado.app.ui.book.read.config.HighlightRuleStore
import io.legado.app.utils.GSON
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * R12.2 高亮样式「单一真源」单测。
 *
 * 覆盖三处此前的不一致：
 * 1. 样式真源：`styleJson` 优先，legacy 字段仅作降级输入
 * 2. 摘要与渲染同源：`styleSummary()` 必须反映 `styleJson`（而非陈旧的 legacy 字段）
 * 3. 愈合不丢用户样式：内置规则愈合时 `styleJson` 必须原样保留
 */
class HighlightRuleRoundTripTest {

    private val styleJson = GSON.toJson(
        HighlightStyle(
            fill = 0x80FFF176.toInt(),
            textColor = 0xFF00FF00.toInt(),
            bold = true
        )
    )

    /** legacy 与 styleJson 故意冲突：真源应取 styleJson */
    private fun conflictingRule() = HighlightRule(
        id = "dialog_default",
        name = "对话高亮",
        pattern = "“[^”]*”",
        isRegex = true,
        textColor = 0xFF0000FF.toInt(), // legacy 蓝
        styleJson = styleJson            // 真源：绿 + 背景 + 加粗
    )

    @Test
    fun toHighlightStyle_prefersStyleJsonOverLegacy() {
        val style = conflictingRule().toHighlightStyle()
        assertEquals(0xFF00FF00.toInt(), style.textColor)
        assertEquals(0x80FFF176.toInt(), style.fill)
        assertTrue(style.bold)
    }

    @Test
    fun styleSummary_reflectsStyleJson() {
        val summary = conflictingRule().styleSummary()
        // 必须显示真源的绿色与背景，而不是 legacy 的蓝色
        assertTrue("摘要未反映 styleJson 的真源色: $summary", summary.contains("#FF00FF00"))
        assertTrue("摘要缺少背景通道: $summary", summary.contains("背景"))
        assertTrue("摘要缺少加粗: $summary", summary.contains("加粗"))
        assertTrue("摘要仍显示陈旧 legacy 色: $summary", !summary.contains("#FF0000FF"))
    }

    @Test
    fun healBuiltin_keepsUserStyleJson() {
        val userRule = conflictingRule()
        val builtin = HighlightRule(
            id = "dialog_default",
            name = "对话高亮",
            pattern = "“[^”\\n]{1,400}”",
            isRegex = true,
            textColor = 0xFFFF8C00.toInt()
        )
        val healed = HighlightRuleStore.healBuiltin(
            safeRule = userRule,
            builtin = builtin,
            patternIsLegacy = false,
            normalizedGroup = "默认"
        )
        // 愈合（升级内置 pattern）时不得清空用户样式
        assertNotNull("愈合后 styleJson 被清空", healed.styleJson)
        assertEquals(styleJson, healed.styleJson)
    }

    @Test
    fun sanitizeRule_keepsStyleJson() {
        val sanitized = HighlightRuleStore.sanitizeRule(conflictingRule())
        assertEquals(styleJson, sanitized.styleJson)
    }

    @Test
    fun gsonMissingField_sanitizedBeforeCopy() {
        // 真机 L2 实锤回归：GSON 反序列化缺失字段会写入 null（如 fontPath），
        // 直接 copy() 会抛「Parameter specified as non-null is null ... fontPath」→ 必须 sanitized 兜底
        val parsed = GSON.fromJson("{\"textColor\":-1,\"paletteSlot\":\"dialogue\"}", HighlightStyle::class.java)
        val safe = parsed.sanitized()
        assertEquals("", safe.fontPath)
        // 兜底后 copy 不应抛异常
        val copied = safe.copy(textColor = 0xFF00FF00.toInt())
        assertEquals(0xFF00FF00.toInt(), copied.textColor)
    }

    @Test
    fun paletteResolve_toleratesGsonNullFields() {
        // 色板解析入口同样必须容错（draw 路径每列都会调用）
        val parsed = GSON.fromJson("{\"textColor\":-1,\"paletteSlot\":\"dialogue\"}", HighlightStyle::class.java)
        val resolved = HighlightPalette.resolve(parsed, HighlightPalette.Tone.NIGHT)
        assertEquals(
            HighlightPalette.color(HighlightPalette.Slot.DIALOGUE, HighlightPalette.Tone.NIGHT),
            resolved.textColor
        )
    }

    @Test
    fun pureUnderlineRule_hasNoFillSoPreviewDrawsNoBackground() {
        // 预览幻影背景带的根因：样式本身 fill=0。此处锁定「纯下划线规则无填充」这一事实
        val rule = HighlightRule(
            id = "book_title_default",
            name = "书名号高亮",
            pattern = "《[^》\\n]{1,80}》",
            isRegex = true,
            underlineMode = 3,
            underlineColor = 0xFF63C37D.toInt()
        )
        val style = rule.toHighlightStyle()
        assertEquals(0, style.fill)
        assertNotNull(style.underline)
    }
}