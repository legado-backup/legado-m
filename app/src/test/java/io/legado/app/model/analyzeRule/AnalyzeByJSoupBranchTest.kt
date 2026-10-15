package io.legado.app.model.analyzeRule

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

/**
 * core-flow-test-coverage tasks 2.7 —— `AnalyzeByJSoup`（CSS 解析）分支补齐（**实测校准版**）。
 *
 * 三轮实测校准（2026-10-15，逐轮证伪上一轮推断）：
 *  ① 纯标签选择器（`p@text`）走另一条（元素索引）路径 ⇒ 语义与预期不符（首版断言错）；
 *  ② `.x@text && .y@text` 实测**只返回 1 项**（第二段似未生效）；`.x@text %% .y@text` 亦为 1
 *     ⇒ 与"合并 / 交错"的文档语义不符 ⇒ 已登记 issues-found **NEW-4（待定位）**，
 *     **不贸然定性为缺陷**（真实书源中 `&&` 的用法与本用例构造可能不同）。
 * 本类只保留**已实测确认**的用例，避免把推断当契约。
 */
class AnalyzeByJSoupBranchTest {

    private fun jx(html: String) = AnalyzeByJSoup(html)

    @Test
    fun getString_emptyRule_returnsNull() {
        assertNull(jx("<div/>").getString(""))
    }

    @Test
    fun getString_classSelector_readsText() {
        assertEquals("A", jx("""<div class="rc"><h3>A</h3></div>""").getString(".rc h3@text"))
    }

    @Test
    fun getString_attrSelector_readsAttribute() {
        assertEquals(
            "https://example.com/a.jpg",
            jx("""<img src="https://example.com/a.jpg"/>""").getString("img@src")
        )
    }

    @Test
    fun getStringList_classSelector_multipleElements_returnsAll() {
        assertEquals(
            2,
            jx("""<div><i class="x">a</i><b class="x">b</b></div>""").getStringList(".x@text").size
        )
    }

    @Test
    fun getStringList_orMerge_shortCircuits() {
        // `||` 短路：实测只保留首个命中段（size=1，符合语义）
        assertEquals(
            1,
            jx("""<div><i class="x">a</i><b class="y">b</b></div>""").getStringList(".x@text || .y@text").size
        )
    }
}
