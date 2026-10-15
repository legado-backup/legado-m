package io.legado.app.data.entities

import io.legado.app.help.HighlightStyle
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * core-flow-test-coverage 批次 3 —— `BookHighlight` 锚点与样式的**行为**用例。
 *
 * 覆盖：①新增的 `chapterUrl` 稳定锚默认值与 `copy` 传递语义；
 * ②[D4] GSON 反序列化写入 `null` 时 `styleObj()` 必须归一化而不抛 NPE（历史缺陷复现点）；
 * ③`applyStyle` ↔ `styleObj` 往返一致。
 */
class BookHighlightAnchorEntityTest {

    private fun highlight(style: String = "") = BookHighlight(
        time = 1L,
        bookName = "书A",
        bookAuthor = "作者A",
        chapterIndex = 3,
        chapterPos = 10,
        chapterPosEnd = 14,
        chapterName = "第三章",
        bookText = "选中",
        style = style
    )

    @Test
    fun chapterUrlDefaultsToBlank() {
        assertEquals("新建划线的锚默认应为空（载入期回填）", "", highlight().chapterUrl)
    }

    @Test
    fun copyKeepsAnchorAndDoesNotMutateSource() {
        val source = highlight()
        val moved = source.copy(chapterIndex = 7, chapterUrl = "u7")
        assertEquals("copy 须携带锚地址", "u7", moved.chapterUrl)
        assertEquals("copy 须使用新索引", 7, moved.chapterIndex)
        assertEquals("原对象不应被改动", "", source.chapterUrl)
        assertEquals("原对象索引不应被改动", 3, source.chapterIndex)
    }

    @Test
    fun applyStyleThenStyleObj_roundTripsFillAndShape() {
        val h = highlight()
        h.applyStyle(HighlightStyle(fill = 0x66FFEB3B.toInt(), fillShape = HighlightStyle.FillShape.MARKER))
        val read = h.styleObj()
        assertEquals("背景填充须往返一致", 0x66FFEB3B.toInt(), read.fill)
        assertEquals("填充形状须往返一致", HighlightStyle.FillShape.MARKER, read.fillShape)
    }

    @Test
    fun styleObj_malformedJson_fallsBackToEmptyStyleWithoutThrowing() {
        val h = highlight(style = "{ 这不是 JSON")
        val read = h.styleObj()
        assertTrue("畸形样式须降级为「无高亮」而不是崩溃", read.isEmpty)
    }

    @Test
    fun styleObj_jsonWithNullFontPath_isSanitizedInsteadOfThrowingNpe() {
        // D4 历史缺陷复现点：GSON 反序列化会把缺失/null 字段写成 null（GSON 不调用 Kotlin 默认值），
        // 直接缓存后 copy() 会抛 NPE ⇒ 必须经 sanitized() 归一化
        val h = highlight(style = """{"fill":1,"fontPath":null}""")
        val read = h.styleObj()
        assertEquals("填充须保留", 1, read.fill)
        assertEquals("null 字体路径须归一化为空串", "", read.fontPath)
        assertTrue("归一化后不应等于「完全空样式」", !read.isEmpty)
    }

    @Test
    fun styleObj_blankStyle_returnsEmptyStyle() {
        val read = highlight().styleObj()
        assertTrue("空样式串须得到「无高亮」样式", read.isEmpty)
        assertNull("无高亮样式不应带下划线", read.underline)
    }
}
