package io.legado.app.help

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

/**
 * F-P1-2 高亮规则系统单元测试
 * 验证 HighlightMatcher 的章内 pos → 每行每列样式映射
 *
 * 验证点：
 * - 单规则覆盖多列时正确分配样式
 * - 同区间多命中取整体优先级（R12.3：后定义者整体胜出，手动高亮 > 规则）
 * - 半开区间交集正确计算
 * - 跨行按 charSize 推进
 * - 段末 +1
 * - 无交集返回 null
 */
class HighlightMatcherTest {

    private val styleRed = HighlightStyle(textColor = 0xFFFF0000.toInt())
    private val styleBlue = HighlightStyle(fill = 0x800000FF.toInt())

    @Test
    fun singleRule_coversMultipleColumns() {
        // 正常用例：单规则覆盖 3 列
        val pageBase = 0
        val lines = listOf(
            HighlightMatcher.LineSpec(
                charSize = 5,
                columnCharLengths = listOf(1, 1, 1, 1, 1),
                isParagraphEnd = false
            )
        )
        val ranges = listOf(
            HighlightMatcher.Range(start = 1, end = 4, style = styleRed)  // 覆盖第 1/2/3 列
        )
        val result = HighlightMatcher.resolve(pageBase, lines, ranges)
        assertEquals("应返回 1 行", 1, result.size)
        val row = result[0]
        assertEquals("应返回 5 列", 5, row.size)
        assertNull("第 0 列无高亮", row[0])
        assertEquals("第 1 列有高亮", styleRed, row[1])
        assertEquals("第 2 列有高亮", styleRed, row[2])
        assertEquals("第 3 列有高亮", styleRed, row[3])
        assertNull("第 4 列无高亮", row[4])
    }

    @Test
    fun multipleRules_lastDefinedWinsEntirely() {
        // R12.3：同区间多命中取「整体优先级」——后定义者整体胜出，禁止逐通道拼接成第三条样式
        val pageBase = 0
        val lines = listOf(
            HighlightMatcher.LineSpec(
                charSize = 3,
                columnCharLengths = listOf(1, 1, 1),
                isParagraphEnd = false
            )
        )
        val ranges = listOf(
            HighlightMatcher.Range(start = 0, end = 3, style = styleRed),      // 全行红字
            HighlightMatcher.Range(start = 1, end = 2, style = styleBlue)      // 第 1 列蓝底
        )
        val result = HighlightMatcher.resolve(pageBase, lines, ranges)
        val row = result[0]
        assertEquals("第 0 列仅红字", styleRed, row[0])
        // 第 1 列整体取后定义的蓝底样式（不得出现「红字 + 蓝底」的混合样式）
        assertEquals("第 1 列整体取后定义样式", styleBlue, row[1])
        assertEquals("第 2 列仅红字", styleRed, row[2])
    }

    @Test
    fun manualHighlight_notOverriddenByRule() {
        // R12.3 优先级层级：手动高亮/划线 > 规则（ranges 顺序即优先级：规则在前、手动在后）
        val pageBase = 0
        val lines = listOf(
            HighlightMatcher.LineSpec(
                charSize = 2,
                columnCharLengths = listOf(1, 1),
                isParagraphEnd = false
            )
        )
        val ruleStyle = HighlightStyle(textColor = 0xFFFF0000.toInt())
        val manualStyle = HighlightStyle(fill = 0x80FFF176.toInt(), bold = true)
        val ranges = listOf(
            HighlightMatcher.Range(start = 0, end = 2, style = ruleStyle),    // 规则：红字
            HighlightMatcher.Range(start = 0, end = 1, style = manualStyle)   // 手动：黄底加粗（后者胜出）
        )
        val result = HighlightMatcher.resolve(pageBase, lines, ranges)
        val row = result[0]
        assertEquals("手动高亮列取手动完整样式", manualStyle, row[0])
        assertEquals("未手动标注列仍用规则样式", ruleStyle, row[1])
    }

    @Test
    fun crossLine_advanceByCharSize() {
        // 边界用例：跨行按 charSize 推进
        val pageBase = 0
        val lines = listOf(
            HighlightMatcher.LineSpec(charSize = 3, columnCharLengths = listOf(1, 1, 1), isParagraphEnd = false),
            HighlightMatcher.LineSpec(charSize = 3, columnCharLengths = listOf(1, 1, 1), isParagraphEnd = false)
        )
        // 覆盖第 1 行末尾 + 第 2 行开头（跨行）
        val ranges = listOf(
            HighlightMatcher.Range(start = 2, end = 5, style = styleRed)  // 第 1 行 col 2 + 第 2 行 col 0/1
        )
        val result = HighlightMatcher.resolve(pageBase, lines, ranges)
        assertNull("第 1 行 col 0 无高亮", result[0][0])
        assertNull("第 1 行 col 1 无高亮", result[0][1])
        assertEquals("第 1 行 col 2 有高亮", styleRed, result[0][2])
        assertEquals("第 2 行 col 0 有高亮", styleRed, result[1][0])
        assertEquals("第 2 行 col 1 有高亮", styleRed, result[1][1])
        assertNull("第 2 行 col 2 无高亮", result[1][2])
    }

    @Test
    fun paragraphEnd_addsOneExtraChar() {
        // 边界用例：段末 +1
        val pageBase = 0
        val lines = listOf(
            HighlightMatcher.LineSpec(charSize = 3, columnCharLengths = listOf(1, 1, 1), isParagraphEnd = true),
            HighlightMatcher.LineSpec(charSize = 3, columnCharLengths = listOf(1, 1, 1), isParagraphEnd = false)
        )
        // 第 2 行 col 0 应在章内 pos = 3（charSize） + 1（段末） = 4
        val ranges = listOf(
            HighlightMatcher.Range(start = 4, end = 5, style = styleRed)  // 仅第 2 行 col 0
        )
        val result = HighlightMatcher.resolve(pageBase, lines, ranges)
        assertNull("第 1 行全部无高亮", result[0][0])
        assertNull("第 1 行全部无高亮", result[0][1])
        assertNull("第 1 行全部无高亮", result[0][2])
        assertEquals("第 2 行 col 0 有高亮（段末 +1 后正确推进）", styleRed, result[1][0])
        assertNull("第 2 行 col 1 无高亮", result[1][1])
    }

    @Test
    fun emptyRanges_allColumnsNull() {
        // 边界用例：空 ranges 时所有列返回 null
        val pageBase = 0
        val lines = listOf(
            HighlightMatcher.LineSpec(charSize = 3, columnCharLengths = listOf(1, 1, 1), isParagraphEnd = false)
        )
        val result = HighlightMatcher.resolve(pageBase, lines, emptyList())
        assertEquals("应返回 1 行", 1, result.size)
        assertEquals("应返回 3 列", 3, result[0].size)
        result[0].forEach { assertNull("所有列应为 null", it) }
    }
}
