package io.legado.app.help.rss

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * W4 / REQ-19（AD-09 / AD-18）：OPML 解析与导出的**纯逻辑**不变量。
 *
 * 覆盖五类样本（design tasks 5.3 要求）：单层分组 / 多级嵌套（扁平化 + 回执计数）/ 编码与转义 /
 * XXE（DTD 拒绝）/ 超限（2MB / 8 层）；以及导出侧「单层 outline + 转义 + 标签集合一致」。
 */
class OpmlRoundTripTest {

    private val singleLevel = """
        <?xml version="1.0" encoding="UTF-8"?>
        <opml version="2.0">
          <head><title>t</title></head>
          <body>
            <outline text="科技">
              <outline type="rss" text="源A" title="源A" xmlUrl="https://example.invalid/a.xml" htmlUrl="https://example.invalid/a"/>
            </outline>
            <outline type="rss" text="源B" xmlUrl="https://example.invalid/b.xml"/>
          </body>
        </opml>
    """.trimIndent()

    @Test
    fun parsesSingleLevelGroupAndUngroupedFeed() {
        val result = OpmlParser.parseText(singleLevel)
        assertTrue("应解析成功", result is OpmlParseResult.Ok)
        val ok = result as OpmlParseResult.Ok
        assertEquals(2, ok.feeds.size)
        assertEquals("单层分组不做扁平化计数", 0, ok.flattenedGroups)
        assertEquals(listOf("科技"), ok.feeds.first { it.xmlUrl.endsWith("a.xml") }.groupTags)
        assertEquals("未分组源 groupTags 为空", emptyList<String>(), ok.feeds.first { it.xmlUrl.endsWith("b.xml") }.groupTags)
    }

    @Test
    fun multiLevelNestingIsFlattenedIntoOneTagWithReceiptCount() {
        val xml = """
            <opml version="2.0"><body>
              <outline text="父"><outline text="子"><outline text="孙">
                <outline type="rss" text="源C" xmlUrl="https://example.invalid/c.xml"/>
              </outline></outline></outline>
              <outline text="父2"><outline text="子2">
                <outline type="rss" text="源D" xmlUrl="https://example.invalid/d.xml"/>
              </outline></outline>
            </body></opml>
        """.trimIndent()
        val ok = OpmlParser.parseText(xml) as OpmlParseResult.Ok
        assertEquals(2, ok.feeds.size)
        assertEquals("多级须拼成单个扁平标签（/ 连接）", listOf("父/子/孙"), ok.feeds.first().groupTags)
        assertEquals("回执须统计被扁平化的多级分组数", 2, ok.flattenedGroups)
        assertTrue("标签内不得含逗号（与扁平串分隔符冲突）", ok.feeds.all { it.groupTags.none { t -> t.contains(",") } })
    }

    @Test
    fun doctypeIsRejectedToBlockXxe() {
        val xxe = """
            <?xml version="1.0"?>
            <!DOCTYPE opml [ <!ENTITY xxe SYSTEM "file:///etc/passwd"> ]>
            <opml version="2.0"><body>
              <outline type="rss" text="&xxe;" xmlUrl="https://example.invalid/evil.xml"/>
            </body></opml>
        """.trimIndent()
        val result = OpmlParser.parseText(xxe)
        assertEquals(
            "含 DTD 的文档必须被安全拒绝（AD-18）",
            OpmlParseResult.Reason.INVALID,
            (result as OpmlParseResult.Error).reason
        )
    }

    @Test
    fun oversizeAndTooDeepAreRejectedWithDedicatedReasons() {
        val big = ByteArray(OpmlParser.MAX_BYTES + 1) { 'x'.code.toByte() }
        assertEquals(
            OpmlParseResult.Reason.TOO_LARGE,
            (OpmlParser.parse(big) as OpmlParseResult.Error).reason
        )

        val deep = buildString {
            append("<opml version=\"2.0\"><body>")
            repeat(OpmlParser.MAX_DEPTH + 1) { append("<outline text=\"g$it\">") }
            append("<outline type=\"rss\" text=\"deep\" xmlUrl=\"https://example.invalid/deep.xml\"/>")
            repeat(OpmlParser.MAX_DEPTH + 1) { append("</outline>") }
            append("</body></opml>")
        }
        assertEquals(
            OpmlParseResult.Reason.TOO_DEEP,
            (OpmlParser.parseText(deep) as OpmlParseResult.Error).reason
        )
    }

    @Test
    fun invalidAndEmptyDocumentsReportDedicatedReasons() {
        assertEquals(OpmlParseResult.Reason.INVALID, (OpmlParser.parseText("not xml at all") as OpmlParseResult.Error).reason)
        assertEquals(
            OpmlParseResult.Reason.INVALID,
            (OpmlParser.parseText("<html><body/></html>") as OpmlParseResult.Error).reason
        )
        assertEquals(
            OpmlParseResult.Reason.EMPTY,
            (OpmlParser.parseText("<opml version=\"2.0\"><body/></opml>") as OpmlParseResult.Error).reason
        )
    }

    @Test
    fun exporterEmitsFlatSingleLevelOutlinesAndEscapes() {
        val sources = listOf(
            io.legado.app.data.entities.RssSource(
                sourceUrl = "https://example.invalid/a.xml",
                sourceName = "A & \"B\" <C>",
                sourceGroup = "科技, 阅读"
            ),
            io.legado.app.data.entities.RssSource(
                sourceUrl = "https://example.invalid/b.xml",
                sourceName = "B",
                sourceGroup = null
            )
        )
        val xml = OpmlExporter.export(sources)
        assertTrue("须带 XML 声明", xml.startsWith("<?xml version=\"1.0\" encoding=\"UTF-8\"?>"))
        assertTrue("须含版本号", xml.contains("<opml version=\"2.0\">"))
        assertTrue("特殊字符须转义", xml.contains("A &amp; &quot;B&quot; &lt;C&gt;"))
        assertEquals("每个标签各一条单层 outline", 2, Regex("""<outline text="(科技|阅读)"""").findAll(xml).count())
        assertTrue("源不得嵌套在标签之外重复出现在标签内?", xml.contains("xmlUrl=\"https://example.invalid/a.xml\""))
    }

    @Test
    fun exportThenImportKeepsFlatTagSetIdentical() {
        val sources = listOf(
            io.legado.app.data.entities.RssSource(
                sourceUrl = "https://example.invalid/a.xml",
                sourceName = "A",
                sourceGroup = "科技"
            ),
            io.legado.app.data.entities.RssSource(
                sourceUrl = "https://example.invalid/b.xml",
                sourceName = "B",
                sourceGroup = "科技,k2"
            )
        )
        val ok = OpmlParser.parseText(OpmlExporter.export(sources)) as OpmlParseResult.Ok
        // 往返判据 = **标签集合一致**（非层级一致）：A 的标签 {科技}、B 的标签 {科技,k2}
        val byUrl = ok.feeds.associateBy { it.xmlUrl }
        assertEquals(listOf("科技"), byUrl["https://example.invalid/a.xml"]?.groupTags)
        assertEquals("同一订阅的多标签须在往返后合并回来", listOf("科技", "k2"), byUrl["https://example.invalid/b.xml"]?.groupTags)
        assertEquals("单层分组不计入扁平化", 0, ok.flattenedGroups)
    }
}