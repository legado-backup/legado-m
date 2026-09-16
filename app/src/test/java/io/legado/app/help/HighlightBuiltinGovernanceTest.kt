package io.legado.app.help

import io.legado.app.ui.book.read.config.HighlightRule
import io.legado.app.ui.book.read.config.HighlightRuleStore
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * §9.5.1 内置规则语义收敛与退役处置 + §9.5.5 默认启用集三态可读性（L1 门禁）。
 *
 * 设计文档验证标准：
 * - 「`createDefaultRules()` 内无重复正则、无重复正文色值」
 * - 「SP 注入退役 id 条目 → 启动后未被个性化者被移除、已个性化者保留且标注」
 */
class HighlightBuiltinGovernanceTest {

    private val rules: List<HighlightRule> = HighlightRuleStore.defaultRules()

    // ---------------- §9.5.1 收敛门禁 ----------------

    @Test
    fun defaultRules_noDuplicatePattern() {
        val dup = rules.groupBy { it.pattern }.filter { it.value.size > 1 }.keys
        assertTrue("内置规则存在完全重复的正则: $dup", dup.isEmpty())
    }

    @Test
    fun defaultRules_noDuplicateColorAcrossSemantics() {
        // 同一语义族（同一色板槽位，如 3 条对白规则）允许复用色值；**不同语义不得撞色**
        val byColor = rules
            .map { it to resolvedColorOf(it) }
            .filter { it.second != 0 }
            .groupBy({ it.second }, { it.first })
            .filter { it.value.size > 1 }
        byColor.forEach { (color, group) ->
            val slots = group.map { it.toHighlightStyle().paletteSlot }.distinct()
            assertEquals(
                "不同语义槽位撞色 #%08X: %s".format(color, group.map { it.id }),
                1, slots.size
            )
        }
    }

    @Test
    fun variantRules_definedAfterParent_soVariantWinsByOverallPriority() {
        // 「语义包含项改为变体形态」的落地前提：变体必须定义在父规则**之后**
        // （R12.3 整体优先级 = 后定义者整体胜出），否则同区间会出现父规则夺权
        val ids = rules.map { it.id }
        listOf("thought_default", "narrator_default", "system_panel_default").forEach { variant ->
            assertTrue(
                "$variant 必须定义在 bracket_note_default 之后（变体胜出前提）",
                ids.indexOf(variant) > ids.indexOf("bracket_note_default")
            )
        }
    }

    @Test
    fun retiredBuiltinIds_noLongerInDefaults() {
        val ids = rules.map { it.id }
        listOf(
            "markdown_bold_default", "thought_wide_default", "narrator_wide_default",
            "number_wide_default", "poetry_wide_default"
        ).forEach { retired ->
            assertFalse("已退役 id 不应再出现在内置规则集中: $retired", ids.contains(retired))
        }
    }

    @Test
    fun mergedPatterns_coverWideVariantKeywords() {
        // 宽窄并集不得丢能力：原宽版关键词必须仍能被主形态命中
        val thought = rules.first { it.id == "thought_default" }.pattern
        listOf("心想", "盘算").forEach { assertTrue("心理活动缺关键词 $it", thought.contains(it)) }
        val narrator = rules.first { it.id == "narrator_default" }.pattern
        listOf("不再赘述", "省略").forEach { assertTrue("旁白缺关键词 $it", narrator.contains(it)) }
        val number = rules.first { it.id == "number_default" }.pattern
        assertTrue("数字金额缺美元/英镑", number.contains("美元") && number.contains("英镑"))
        val poetry = rules.first { it.id == "poetry_default" }.pattern
        assertTrue("诗词缺题头分支", poetry.contains("七五言"))
    }

    // ---------------- §9.5.1 退役处置 ----------------

    private fun retiredSample(name: String, id: String, pattern: String, styleJson: String? = null) =
        HighlightRule(id = id, name = name, pattern = pattern, styleJson = styleJson)

    @Test
    fun retire_removesUncustomizedBuiltinEntry() {
        val input = listOf(
            retiredSample("Markdown 强调", "markdown_bold_default", "\\*\\*[^\\n*]{1,40}\\*\\*"),
            HighlightRule(id = "dialog_default", name = "对话高亮", pattern = "x")
        )
        val result = HighlightRuleStore.retireBuiltinRules(input)
        assertEquals(1, result.removed)
        assertEquals(0, result.renamed)
        assertEquals(listOf("dialog_default"), result.rules.map { it.id })
    }

    @Test
    fun retire_keepsCustomizedEntryWithLabel() {
        val input = listOf(
            // 用户改过 pattern（不命中历史登记值）→ 保留并标注
            retiredSample("心理活动（宽版）", "thought_wide_default", "（我自己写的正则）"),
            // 用户存过自定义样式 → 保留并标注
            retiredSample(
                "数字金额（宽版）", "number_wide_default", "[0-9]+[%％]",
                styleJson = "{\"textColor\":-65536}"
            ),
            HighlightRule(id = "dialog_default", name = "对话高亮", pattern = "x")
        )
        val result = HighlightRuleStore.retireBuiltinRules(input)
        assertEquals(0, result.removed)
        assertEquals(2, result.renamed)
        val kept = result.rules.filter { it.id != "dialog_default" }
        assertEquals(2, kept.size)
        kept.forEach {
            assertTrue(
                "已个性化退役条目必须保留并标注: ${it.id} name=${it.name}",
                it.name.endsWith(HighlightRuleStore.RETIRED_SUFFIX)
            )
        }
    }

    @Test
    fun retire_isIdempotent() {
        val input = listOf(
            retiredSample("Markdown 强调", "markdown_bold_default", "\\*\\*[^\\n*]{1,40}\\*\\*"),
            retiredSample("心理活动（宽版）", "thought_wide_default", "（我自己写的正则）")
        )
        val first = HighlightRuleStore.retireBuiltinRules(input)
        assertTrue(first.changed)
        val second = HighlightRuleStore.retireBuiltinRules(first.rules)
        assertFalse("退役处置必须幂等（二次执行零变更）", second.changed)
        assertEquals(first.rules.map { it.id }, second.rules.map { it.id })
        assertEquals(first.rules.map { it.name }, second.rules.map { it.name })
    }

    @Test
    fun retire_ignoresActiveBuiltinRules() {
        val input = listOf(
            HighlightRule(id = "thought_default", name = "心理活动", pattern = "（[^）]*心想[^）]*）")
        )
        val result = HighlightRuleStore.retireBuiltinRules(input)
        assertFalse(result.changed)
        assertEquals(input.map { it.name }, result.rules.map { it.name })
    }

    // ---------------- §9.5.5 默认启用集三态可读性 ----------------

    @Test
    fun defaultEnabledRules_readableInDayAndNight() {
        val enabled = rules.filter { it.enabled }
        assertTrue("默认启用集为空，门禁失效", enabled.isNotEmpty())
        listOf(
            HighlightPalette.Tone.DAY to HighlightPalette.BG_DAY,
            HighlightPalette.Tone.NIGHT to HighlightPalette.BG_NIGHT
        ).forEach { (tone, bg) ->
            enabled.forEach { rule ->
                val style = HighlightPalette.resolve(rule.toHighlightStyle(), tone)
                val fg = foregroundOf(style)
                assertTrue("${rule.id} 在 $tone 下无色通道（既无字色也无装饰色）", fg != 0)
                val ratio = HighlightPalette.contrastRatio(fg, bg)
                assertTrue(
                    "${rule.id} 在 $tone 对比度 %.2f < %.1f".format(ratio, HighlightPalette.MIN_CONTRAST_RATIO),
                    ratio >= HighlightPalette.MIN_CONTRAST_RATIO
                )
            }
        }
    }

    @Test
    fun defaultEnabledRules_identifiableInEInk() {
        // 墨水屏色相不可用：正文取黑，或保留装饰（线型/方框/着重号）保证可辨识
        rules.filter { it.enabled }.forEach { rule ->
            val style = HighlightPalette.resolve(rule.toHighlightStyle(), HighlightPalette.Tone.EINK)
            val hasDecoration = style.underline != null || style.strike != null ||
                style.box != null || style.emphasis != null
            assertTrue(
                "${rule.id} 墨水屏下既非黑字也无装饰，不可辨识",
                style.textColor == 0xFF000000.toInt() || hasDecoration
            )
        }
    }

    private fun foregroundOf(style: HighlightStyle): Int {
        return style.textColor.takeIf { it != 0 }
            ?: style.underline?.color?.takeIf { it != 0 }
            ?: style.box?.color?.takeIf { it != 0 }
            ?: style.emphasis?.color?.takeIf { it != 0 }
            ?: 0
    }

    private fun resolvedColorOf(rule: HighlightRule): Int =
        foregroundOf(HighlightPalette.resolve(rule.toHighlightStyle(), HighlightPalette.Tone.DAY))
}