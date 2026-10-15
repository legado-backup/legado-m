package io.legado.app.model.analyzeRule

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

/**
 * core-flow-test-coverage tasks 2.1/2.2/2.3 —— 正则可选捕获组回归守护。
 *
 * [BUG-1] `AnalyzeByRegex.getElement` 对**未参与匹配的可选捕获组**使用 `resM.group(i)!!`
 * ⇒ 抛 NullPointerException（同文件 `getElements` 已用 `?: ""`，两处语义不一致）。
 * `getElement_optionalGroupNotMatched_groupFallsBackToEmpty` 在修复前为**红**，修复后转绿。
 *
 * 纯 JVM：`build.gradle` 已开 `returnDefaultValues=true`，`android.util.LruCache`
 * 退化为恒 miss 桩（仅影响缓存命中，不影响正则匹配语义）。
 */
class AnalyzeByRegexTest {

    // ===== BUG-1 复现与修复守护 =====

    @Test
    fun getElement_optionalGroupNotMatched_groupFallsBackToEmpty() {
        // `(a)?b` 对 "b"：group(1) 未参与匹配 ⇒ JVM 正则返回 null
        // 修复前：`resM.group(1)!!` 抛 NPE
        val element = AnalyzeByRegex.getElement("b", arrayOf("(a)?b"))
        assertEquals(listOf("b", ""), element)
    }

    @Test
    fun getElements_optionalGroupNotMatched_groupFallsBackToEmpty() {
        // 存量行为守护：getElements 早已用 `?: ""`，此用例应在修复前后恒绿
        val books = AnalyzeByRegex.getElements("b", arrayOf("(a)?b"))
        assertEquals(1, books.size)
        assertEquals(listOf("b", ""), books[0])
    }

    // ===== 正常路径守护 =====

    @Test
    fun getElement_multipleGroupsMatched_returnsWholeAndGroups() {
        // group(0) 为整体匹配，其后逐组
        val element = AnalyzeByRegex.getElement("x=1", arrayOf("(\\w+)=(\\d+)"))
        assertEquals(listOf("x=1", "x", "1"), element)
    }

    @Test
    fun getElement_noMatch_returnsNull() {
        assertNull(AnalyzeByRegex.getElement("zzz", arrayOf("(\\d+)")))
    }

    @Test
    fun getElements_noMatch_returnsEmptyList() {
        assertEquals(0, AnalyzeByRegex.getElements("zzz", arrayOf("(\\d+)")).size)
    }

    @Test
    fun getElement_multiSegmentRegex_chainsSegments() {
        // 多段规则：前段把全部匹配的 group() 拼成新串，末段取组
        // 段1 `a(\d+)` 对 "a1b a2c" 拼接 "a1"+"a2" = "a1a2"；段2 `(\d+)` 命中 "1" ⇒ [整体, 组]
        val element = AnalyzeByRegex.getElement("a1b a2c", arrayOf("a(\\d+)", "(\\d+)"))
        assertEquals(listOf("1", "1"), element)
    }

    @Test
    fun getElements_multiSegmentRegex_chainsSegments() {
        // 段1 `a(\d+)` 拼接 "a1"+"a2" = "a1a2"；段2 `(\d+)` 对该串**逐次**匹配 ⇒ 两组结果
        val books = AnalyzeByRegex.getElements("a1b a2c", arrayOf("a(\\d+)", "(\\d+)"))
        assertEquals(2, books.size)
        assertEquals(listOf("1", "1"), books[0])
        assertEquals(listOf("2", "2"), books[1])
    }

    @Test
    fun getElement_optionalGroupMatched_groupKeepsValue() {
        // 可选组**参与**匹配时须保留其值（防止修复把真实值也吞成空串）
        val element = AnalyzeByRegex.getElement("ab", arrayOf("(a)?b"))
        assertEquals(listOf("ab", "a"), element)
    }
}
