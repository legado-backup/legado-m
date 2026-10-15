package io.legado.app.model

import io.legado.app.data.entities.BookChapter
import io.legado.app.data.entities.BookHighlight
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * core-flow-test-coverage 批次 3 —— 划线锚点同步策略行为用例。
 *
 * 覆盖 `HighlightSyncPolicy.planAnchorFixes` 的四条解析路径与三种真实重排场景，
 * 全部为**对返回值的断言**（非源码文本探针，遵 G-42）。
 */
class HighlightSyncPolicyTest {

    private fun chapter(index: Int, title: String, url: String = "u$index") =
        BookChapter(index = index, title = title, url = url)

    private fun highlight(
        index: Int,
        name: String,
        url: String = "",
        pos: Int = 10
    ) = BookHighlight(
        time = 1000L + index,
        bookName = "书A",
        bookAuthor = "作者A",
        chapterIndex = index,
        chapterPos = pos,
        chapterPosEnd = pos + 4,
        chapterName = name,
        chapterUrl = url,
        bookText = "选中文本"
    )

    @Test
    fun urlHit_returnsFixWithSameUrlAndNewIndex() {
        // 目录整体后移（前面插了一章）⇒ 原 index 0 的章现在在 index 1，URL 不变
        val h = highlight(0, "第一章", url = "u0")
        val fixes = HighlightSyncPolicy.planAnchorFixes(
            listOf(h),
            listOf(chapter(0, "序章", "u9"), chapter(1, "第一章", "u0"))
        )
        assertEquals("应产出 1 条修正", 1, fixes.size)
        assertEquals("URL 锚命中后索引应纠正为 1", 1, fixes[0].index)
        assertEquals("URL 应保持原值", "u0", fixes[0].url)
        assertTrue("修正对象应是入参实例", fixes[0].highlight === h)
    }

    @Test
    fun urlMiss_fallsBackToChapterName() {
        // 换源场景：目录地址全变，标题留存 ⇒ 按标题找回并重新锚定 URL
        val h = highlight(2, "第三章", url = "/old/source/ch3")
        val fixes = HighlightSyncPolicy.planAnchorFixes(
            listOf(h),
            listOf(chapter(4, "第三章", "/new/source/c3"), chapter(5, "第四章", "/new/source/c4"))
        )
        assertEquals(1, fixes.size)
        assertEquals("标题命中后索引应为 4", 4, fixes[0].index)
        assertEquals("应把 URL 重新锚定到新地址", "/new/source/c3", fixes[0].url)
    }

    @Test
    fun bothMiss_keepsHighlightUntouched() {
        // 地址未命中 + 标题未命中 + 同下标章节标题也不一致 ⇒ 无法定位，不得误锚
        val h = highlight(2, "第三章", url = "/old/ch3")
        val fixes = HighlightSyncPolicy.planAnchorFixes(
            listOf(h),
            listOf(chapter(0, "第一章"), chapter(2, "第九章"))
        )
        assertTrue("无法定位时应返回空结果", fixes.isEmpty())
    }

    @Test
    fun alreadyCorrect_producesNoFix() {
        val h = highlight(1, "第二章", url = "u1")
        val fixes = HighlightSyncPolicy.planAnchorFixes(
            listOf(h),
            listOf(chapter(0, "第一章"), chapter(1, "第二章"))
        )
        assertTrue("索引与锚均正确时不应产生落库动作", fixes.isEmpty())
    }

    @Test
    fun reverseToc_indexMirrored() {
        // 切换「反转目录」：同一 URL 的章节从 index 0 变成 index 2
        val h = highlight(0, "第一章", url = "u0")
        val fixes = HighlightSyncPolicy.planAnchorFixes(
            listOf(h),
            listOf(chapter(0, "第三章", "u2"), chapter(1, "第二章", "u1"), chapter(2, "第一章", "u0"))
        )
        assertEquals(1, fixes.size)
        assertEquals("反转目录后应按锚镜像到 2", 2, fixes[0].index)
    }

    @Test
    fun legacyBlankUrl_backfilledByPositionWhenTitleMatches() {
        // 老数据无 URL：同下标章节标题与存的一致 ⇒ 认定位置有效并回填 URL（索引不变）
        val h = highlight(1, "第二章", url = "")
        val fixes = HighlightSyncPolicy.planAnchorFixes(
            listOf(h),
            listOf(chapter(0, "第一章"), chapter(1, "第二章"))
        )
        assertEquals(1, fixes.size)
        assertEquals("回填时索引应保持 1", 1, fixes[0].index)
        assertEquals("应回填该章地址", "u1", fixes[0].url)
    }

    @Test
    fun legacyBlankUrlAndBlankName_backfilledByPosition() {
        // 名称也未记录（极老数据）⇒ 位置兜底回填 URL
        val h = highlight(0, "", url = "")
        val fixes = HighlightSyncPolicy.planAnchorFixes(listOf(h), listOf(chapter(0, "第一章")))
        assertEquals(1, fixes.size)
        assertEquals(0, fixes[0].index)
        assertEquals("u0", fixes[0].url)
    }

    @Test
    fun legacyBlankUrl_titleMismatchAtPosition_isNotAnchored() {
        // 目录已整体重排且无锚 ⇒ 位置处的标题对不上，宁可保持原样也不回填错误地址
        val h = highlight(1, "第二章", url = "")
        val fixes = HighlightSyncPolicy.planAnchorFixes(
            listOf(h),
            listOf(chapter(0, "第一章"), chapter(1, "新插入的第三章"))
        )
        assertTrue(fixes.isEmpty())
    }

    @Test
    fun blankUrlButTitleMoved_relocatesButKeepsStoredIndexConsistency() {
        // 老数据（无 URL）且标题被移到别的下标 ⇒ 按标题重定位并回填新地址
        val h = highlight(0, "第五章", url = "")
        val fixes = HighlightSyncPolicy.planAnchorFixes(
            listOf(h),
            listOf(chapter(0, "第一章"), chapter(6, "第五章", "u6"))
        )
        assertEquals(1, fixes.size)
        assertEquals(6, fixes[0].index)
        assertEquals("u6", fixes[0].url)
    }

    @Test
    fun emptyInputs_produceNoFix() {
        assertTrue(HighlightSyncPolicy.planAnchorFixes(emptyList(), listOf(chapter(0, "第一章"))).isEmpty())
        assertTrue(HighlightSyncPolicy.planAnchorFixes(listOf(highlight(0, "第一章")), emptyList()).isEmpty())
    }

    @Test
    fun multipleHighlights_onlyOutdatedOnesAreFixed() {
        val correct = highlight(1, "第二章", url = "u1")
        val shifted = highlight(3, "第四章", url = "u3")
        val chapters = listOf(
            chapter(0, "第一章"), chapter(1, "第二章"), chapter(2, "第三章"),
            chapter(3, "插章", "u8"), chapter(4, "第四章")
        )
        val fixes = HighlightSyncPolicy.planAnchorFixes(listOf(correct, shifted), chapters)
        assertEquals("只有错位的那条产出修正", 1, fixes.size)
        assertEquals("修正对象应是错位划线", shifted, fixes[0].highlight)
        assertEquals(4, fixes[0].index)
    }
}
