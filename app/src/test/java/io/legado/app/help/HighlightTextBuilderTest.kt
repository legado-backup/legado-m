package io.legado.app.help

import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * F-P1-2 高亮规则系统单元测试
 * 验证 HighlightTextBuilder 的文本重建 + 偏移对齐章内 pos
 *
 * 验证点：
 * - 多行重建后字符串偏移 == 章内 pos
 * - 补齐到 charSize 用空格
 * - 段末 append '\n'（占 1 字符位）
 * - 非文字列传 "" 不影响偏移
 */
class HighlightTextBuilderTest {

    @Test
    fun build_multiLineOffsetAligned() {
        // 正常用例：多行重建后偏移对齐
        val lines = listOf(
            HighlightTextBuilder.LineInput(
                columnTexts = listOf("ab", "cd"),
                charSize = 4,
                isParagraphEnd = false
            ),
            HighlightTextBuilder.LineInput(
                columnTexts = listOf("ef", "gh"),
                charSize = 4,
                isParagraphEnd = false
            )
        )
        val text = HighlightTextBuilder.build(lines)
        // columnTexts 拼接：第 1 行 "ab"+"cd"="abcd"，第 2 行 "ef"+"gh"="efgh"
        assertEquals("abcdefgh", text)
        // 第 2 行 "ef" 起始偏移 = 4（charSize），与章内 pos 对齐
        assertEquals("第 2 行 ef 起始偏移应为 4", 4, text.indexOf("ef"))
    }

    @Test
    fun build_padToCharSizeWithSpaces() {
        // 边界用例：补齐到 charSize 用空格
        val lines = listOf(
            HighlightTextBuilder.LineInput(
                columnTexts = listOf("ab"),  // 仅 2 字符
                charSize = 5,                 // 需补 3 空格
                isParagraphEnd = false
            )
        )
        val text = HighlightTextBuilder.build(lines)
        assertEquals("ab   ", text)  // "ab" + 3 空格
        assertEquals("长度应为 charSize=5", 5, text.length)
    }

    @Test
    fun build_paragraphEndAppendsNewline() {
        // 边界用例：段末 append '\n'（占 1 字符位）
        val lines = listOf(
            HighlightTextBuilder.LineInput(
                columnTexts = listOf("abc"),
                charSize = 3,
                isParagraphEnd = true   // 段末
            ),
            HighlightTextBuilder.LineInput(
                columnTexts = listOf("def"),
                charSize = 3,
                isParagraphEnd = false
            )
        )
        val text = HighlightTextBuilder.build(lines)
        assertEquals("abc\ndef", text)
        // 第 2 行 "def" 起始偏移 = 3（charSize） + 1（段末 \n） = 4
        assertEquals("段末 +1 后第 2 行起始偏移应为 4", 4, text.indexOf("def"))
    }

    @Test
    fun build_nonTextColumnEmptyString() {
        // 边界用例：非文字列传 "" 不影响偏移
        val lines = listOf(
            HighlightTextBuilder.LineInput(
                columnTexts = listOf("ab", "", "cd"),  // 中间列非文字
                charSize = 4,
                isParagraphEnd = false
            )
        )
        val text = HighlightTextBuilder.build(lines)
        // columnTexts 拼接： "ab" + "" + "cd" = "abcd"（4 字符），已达 charSize 无需补齐
        assertEquals("abcd", text)
        assertEquals("长度应为 charSize=4", 4, text.length)
    }

    @Test
    fun build_emptyLinesReturnsEmptyString() {
        // 边界用例：空行列表返回空字符串
        val text = HighlightTextBuilder.build(emptyList())
        assertEquals("", text)
    }
}
