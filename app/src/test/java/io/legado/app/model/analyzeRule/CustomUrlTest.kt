package io.legado.app.model.analyzeRule

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * core-flow-test-coverage tasks 2.8 —— `CustomUrl` 零覆盖补齐。
 *
 * 覆盖后缀属性解析（`AnalyzeUrl.paramPattern = \s*,\s*(?=\{)`）与往返语义。
 * 纯 JVM：仅依赖 `GSON`（Gson）与 `Pattern`。
 */
class CustomUrlTest {

    @Test
    fun noAttribute_urlPassedThrough() {
        val cu = CustomUrl("https://example.com/book/1")
        assertEquals("https://example.com/book/1", cu.getUrl())
        assertTrue(cu.getAttr().isEmpty())
        assertEquals("https://example.com/book/1", cu.toString())
    }

    @Test
    fun trailingJsonAttribute_parsedAndStrippedFromUrl() {
        val cu = CustomUrl("""https://example.com/book/1, {"a":1}""")
        assertEquals("https://example.com/book/1", cu.getUrl())
        assertEquals(setOf("a"), cu.getAttr().keys)
    }

    @Test
    fun malformedJsonAttribute_urlStillSplit_attributeDropped() {
        val cu = CustomUrl("""https://example.com/book/1, {bad""")
        assertEquals("https://example.com/book/1", cu.getUrl())
        assertTrue("畸形 JSON 属性应静默丢弃而非崩溃", cu.getAttr().isEmpty())
    }

    @Test
    fun putAttribute_nullValue_removesKey() {
        val cu = CustomUrl("https://example.com/book/1")
        cu.putAttribute("k", "v")
        assertEquals("v", cu.getAttr()["k"])
        cu.putAttribute("k", null)
        assertTrue(cu.getAttr().isEmpty())
    }

    @Test
    fun toString_roundTripsWithAttribute() {
        val cu = CustomUrl("https://example.com/book/1")
        cu.putAttribute("k", 1)
        val text = cu.toString()
        assertTrue("带属性时须拼回 `url,{json}` 形态", text.startsWith("https://example.com/book/1,"))
        val reparsed = CustomUrl(text)
        assertEquals(1.0, (reparsed.getAttr()["k"] as Number).toDouble(), 0.0)
    }
}
