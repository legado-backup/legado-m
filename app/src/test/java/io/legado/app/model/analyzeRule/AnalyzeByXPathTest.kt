package io.legado.app.model.analyzeRule

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

/**
 * core-flow-test-coverage tasks 2.6 —— `AnalyzeByXPath` 零覆盖补齐。
 *
 * 仅测 `getElements`/`getStringList`（**刻意避开 `getString`**：其依赖
 * `android.text.TextUtils`，在纯 JVM（`returnDefaultValues=true`）下为空桩会返回 null）。
 * 以「命中数量」为断言口径 —— 能捕获 `</td>` 自动包裹失效、`||` 短路失效等缺陷。
 */
class AnalyzeByXPathTest {

    private fun jx(html: String) = AnalyzeByXPath(html)

    @Test
    fun getElements_basicXPath_returnsMatches() {
        val nodes = jx("<div><p>a</p><p>b</p></div>").getElements("//p")
        assertEquals(2, nodes?.size)
    }

    @Test
    fun getElements_emptyRule_returnsNull() {
        assertNull(jx("<div/>").getElements(""))
    }

    @Test
    fun getStringList_andMerge_concatenatesResults() {
        val list = jx("<div><p>a</p><span>b</span></div>").getStringList("//p && //span")
        assertEquals(2, list.size)
    }

    @Test
    fun getStringList_orShortCircuit_stopsAtFirstHit() {
        val list = jx("<div><p>a</p><span>b</span></div>").getStringList("//p || //span")
        assertEquals(1, list.size)
    }

    @Test
    fun getElements_attributeXPath_returnsAttributeNodes() {
        val nodes = jx("""<a href="h1">x</a><a href="h2">y</a>""").getElements("//a/@href")
        assertEquals(2, nodes?.size)
    }

    @Test
    fun strToJXDocument_bareTd_wrappedSoTrAncestorExists() {
        // 依赖 `</td>` ⇒ `<tr>…</tr>` 自动包裹：未包裹时不存在 tr 祖先，`//tr/td` 必空
        val list = jx("<td>x</td>").getStringList("//tr/td")
        assertEquals(1, list.size)
    }
}
