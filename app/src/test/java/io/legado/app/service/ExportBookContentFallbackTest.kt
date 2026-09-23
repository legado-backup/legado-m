package io.legado.app.service

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotEquals
import org.junit.Test

/**
 * B1 · R2「EPUB 导出正文空值兜底」回归测试。
 *
 * 缺陷（修复前）：调用点写的是 `content ?: if (chapter.isVolume) "" else "null"` ——
 * 非卷章节正文为空时，**字符串字面量 `"null"` 被当作正文**写进 EPUB（用户可见「null」）。
 * 修复：统一走 `ExportBookService.epubChapterContent(content)` ⇒ 空正文一律空字符串。
 */
class ExportBookContentFallbackTest {

    @Test
    fun nullContent_fallsBackToEmptyString_notLiteralNull() {
        assertEquals("空正文必须兜底为空字符串", "", ExportBookService.epubChapterContent(null))
        assertNotEquals("不得再写入字面量 null", "null", ExportBookService.epubChapterContent(null))
    }

    @Test
    fun blankAndNormalContent_passedThrough() {
        assertEquals("", ExportBookService.epubChapterContent(""))
        assertEquals("正文原样透传", "第一章 正文", ExportBookService.epubChapterContent("第一章 正文"))
    }
}