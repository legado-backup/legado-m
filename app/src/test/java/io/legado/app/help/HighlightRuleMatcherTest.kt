package io.legado.app.help

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * F-P1-2 高亮规则系统单元测试
 * 验证 HighlightRuleMatcher 的正则/字面量匹配 + 超时保护 + 非法正则跳过
 *
 * 验证点：
 * - 正则匹配正确产出半开区间 [start, end)
 * - 字面量匹配不重叠
 * - 非法正则静默跳过，不抛异常
 * - 空文本/空规则返回 emptyList
 * - 零宽匹配步进 1，不产出
 */
class HighlightRuleMatcherTest {

    private val style = HighlightStyle(textColor = 0xFFFF0000.toInt())

    @Test
    fun regexMatch_producesHalfOpenInterval() {
        // 正常用例：正则匹配 "对话" 文本中的引号内容
        val text = "她说：“你好”。然后走了。"
        val rule = HighlightRuleMatcher.Rule(
            id = "1",
            pattern = "“[^”]+”",
            isRegex = true,
            style = style
        )
        val matches = HighlightRuleMatcher.match(text, listOf(rule))
        assertEquals("应匹配到 1 处", 1, matches.size)
        val m = matches[0]
        assertEquals("start 应为 3", 3, m.start)
        assertEquals("end 应为 7", 7, m.end)
        assertEquals("匹配内容应为 “你好”", "“你好”", text.substring(m.start, m.end))
    }

    @Test
    fun literalMatch_doesNotOverlap() {
        // 边界用例：字面量匹配不重叠
        val text = "aaa aaa aaa"
        val rule = HighlightRuleMatcher.Rule(
            id = "1",
            pattern = "aaa",
            isRegex = false,
            style = style
        )
        val matches = HighlightRuleMatcher.match(text, listOf(rule))
        assertEquals("应匹配到 3 处（不重叠）", 3, matches.size)
        assertEquals("第 1 处 start=0", 0, matches[0].start)
        assertEquals("第 2 处 start=4", 4, matches[1].start)
        assertEquals("第 3 处 start=8", 8, matches[2].start)
    }

    @Test
    fun invalidRegex_silentlySkipped() {
        // 异常用例：非法正则静默跳过，不抛异常
        val text = "测试文本"
        val invalidRule = HighlightRuleMatcher.Rule(
            id = "1",
            pattern = "[unclosed",  // 非法正则
            isRegex = true,
            style = style
        )
        val validRule = HighlightRuleMatcher.Rule(
            id = 2L,
            pattern = "测试",
            isRegex = false,
            style = style
        )
        val matches = HighlightRuleMatcher.match(text, listOf(invalidRule, validRule))
        assertEquals("非法正则跳过，仅有效规则匹配", 1, matches.size)
        assertEquals("匹配来自有效规则", "2", matches[0].ruleId)
    }

    @Test
    fun emptyTextOrRules_returnsEmptyList() {
        // 边界用例：空文本/空规则返回 emptyList
        val rule = HighlightRuleMatcher.Rule(
            id = "1",
            pattern = "a",
            isRegex = false,
            style = style
        )
        assertEquals("空文本返回空列表", emptyList<HighlightRuleMatcher.RuleMatch>(), HighlightRuleMatcher.match("", listOf(rule)))
        assertEquals("空规则返回空列表", emptyList<HighlightRuleMatcher.RuleMatch>(), HighlightRuleMatcher.match("abc", emptyList()))
    }

    @Test
    fun zeroWidthMatch_stepForwardWithoutProduce() {
        // 边界用例：零宽匹配步进 1，不产出
        val text = "abc"
        val rule = HighlightRuleMatcher.Rule(
            id = "1",
            pattern = "(?=b)",  // 零宽断言
            isRegex = true,
            style = style
        )
        val matches = HighlightRuleMatcher.match(text, listOf(rule))
        assertTrue("零宽匹配不产出，结果应为空", matches.isEmpty())
    }

    @Test
    fun multipleRules_allMatched() {
        // 正常用例：多规则全部匹配
        val text = "Hello 世界 123"
        val rules = listOf(
            HighlightRuleMatcher.Rule(id = "1", pattern = "Hello", isRegex = false, style = style),
            HighlightRuleMatcher.Rule(id = "2", pattern = "\\d+", isRegex = true, style = style)
        )
        val matches = HighlightRuleMatcher.match(text, rules)
        assertEquals("应匹配到 2 处", 2, matches.size)
        assertEquals("第 1 处 ruleId=1", "1", matches[0].ruleId)
        assertEquals("第 2 处 ruleId=2", "2", matches[1].ruleId)
    }
}
