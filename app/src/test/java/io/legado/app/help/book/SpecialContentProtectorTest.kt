package io.legado.app.help.book

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * SpecialContentProtector 特殊内容保护单元测试
 *
 * 验证点（纯 JVM，无 Android 依赖）：
 * 1. usehtml/img/newpage 三种特殊内容 protect → restore 往返后格式块完整
 * 2. 计数正确（useHtmlCount/imgCount/newPageCount）
 * 3. 无特殊内容时 protect 原样透传，计数全 0
 * 4. 特殊内容保护后不再被正则破坏（模拟替换规则删 `<img>`）
 * 5. 残留占位符检测 residualCount/hasResidual
 */
class SpecialContentProtectorTest {

    @Test
    fun mixedContent_protectRestore_roundTripComplete() {
        val content = buildString {
            append("第一章 正文开头\n")
            append("<usehtml><div style='color:red'>特殊样式</div></usehtml>\n")
            append("普通段落文字\n")
            append("<img src='https://example.com/a.png' alt='图'>\n")
            append("[newpage]\n")
            append("下一页内容\n")
        }

        val protected = SpecialContentProtector.protect(content)
        assertEquals("usehtml 应命中 1 个", 1, protected.useHtmlCount)
        assertEquals("img 应命中 1 个", 1, protected.imgCount)
        assertEquals("newpage 应命中 1 个", 1, protected.newPageCount)
        assertFalse("保护后不应残留原始特殊内容", protected.content.contains("<usehtml>"))
        assertFalse("保护后不应残留原始 img 标签", protected.content.contains("<img"))
        assertFalse("保护后不应残留原始 newpage", protected.content.contains("[newpage]"))
        assertEquals("恢复后应与原文一致", content, protected.restore(protected.content))
        assertEquals("恢复后无残留占位符", 0, SpecialContentProtector.residualCount(protected.restore(protected.content)))
    }

    @Test
    fun replaceRuleMimic_protectedContentSurvives() {
        val content = "正文\n<usehtml><b>加粗</b></usehtml>\n<img src='x.png'>\n[newpage]\n后文"
        val protected = SpecialContentProtector.protect(content)
        // 模拟替换规则把 img 标签和 newpage 删掉（对占位符无影响）
        val afterReplace = protected.content.replace(Regex("""<img\b[^>]*>"""), "")
            .replace("[newpage]", "")
        val restored = protected.restore(afterReplace)
        assertTrue("usehtml 块应完整保留", restored.contains("<usehtml><b>加粗</b></usehtml>"))
        assertTrue("img 应被还原", restored.contains("<img src='x.png'>"))
        assertTrue("newpage 应被还原", restored.contains("[newpage]"))
        assertTrue("正文应保留", restored.startsWith("正文"))
    }

    @Test
    fun noSpecialContent_passthroughWithZeroCounts() {
        val content = "普通文本\n第二行\n没有特殊格式\n"

        val protected = SpecialContentProtector.protect(content)

        assertEquals(0, protected.useHtmlCount)
        assertEquals(0, protected.imgCount)
        assertEquals(0, protected.newPageCount)
        assertEquals("无特殊内容应原样透传", content, protected.content)
        assertEquals("restore 应原样返回", content, protected.restore(protected.content))
        assertFalse(SpecialContentProtector.hasResidual(protected.content))
    }

    @Test
    fun partialContent_someProtected() {
        val content = "<img src='a.png'>\n纯文字"

        val protected = SpecialContentProtector.protect(content)

        assertEquals(0, protected.useHtmlCount)
        assertEquals(1, protected.imgCount)
        assertEquals(0, protected.newPageCount)
        assertEquals(content, protected.restore(protected.content))
    }

    @Test
    fun residualDetection_catchesUnrestoredPlaceholder() {
        val content = "有 <img src='a.png'> 图"
        val protected = SpecialContentProtector.protect(content)
        val stillHasPlaceholder = protected.content

        assertTrue("占位符应被检测为残留", SpecialContentProtector.hasResidual(stillHasPlaceholder))
        assertTrue("残留计数应 > 0", SpecialContentProtector.residualCount(stillHasPlaceholder) > 0)
        val restored = protected.restore(stillHasPlaceholder)
        assertEquals("restore 后残留应为 0", 0, SpecialContentProtector.residualCount(restored))
        assertFalse(SpecialContentProtector.hasResidual(restored))
    }

    @Test
    fun useHtmlMarkerDetected() {
        assertTrue(SpecialContentProtector.hasResidual("\uE000LEGADO_USEHTML_0\uE001"))
        assertFalse(SpecialContentProtector.hasResidual("普通文本"))
    }

    @Test
    fun multipleImagesCounted() {
        val content = "<img src='1.png'><img src='2.png'><img src='3.png'>"
        val protected = SpecialContentProtector.protect(content)
        assertEquals(3, protected.imgCount)
        assertEquals("全部图片应还原", content, protected.restore(protected.content))
    }

    @Test
    fun newPageWithWhitespace_matches() {
        val content = "正文\n  [newpage]  \n后文"
        val protected = SpecialContentProtector.protect(content)
        assertEquals("带空白 newpage 应命中", 1, protected.newPageCount)
        assertTrue("newpage 应被还原", protected.restore(protected.content).contains("[newpage]"))
    }
}
