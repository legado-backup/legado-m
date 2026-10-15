package io.legado.app.model.analyzeRule

import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * core-flow-test-coverage tasks 2.4/2.5 —— 规则切分边界回归守护。
 *
 * [BUG-2] `RuleAnalyzer.trim()` 的 `queue[pos]` **无边界检查** ⇒ 空串 / 全空白 / 仅 `@`
 * 时越界抛 `StringIndexOutOfBoundsException`；经 `AnalyzeByJSoup` 的 `splitRule` 产出
 * 空段后可达（`AnalyzeByJSoup.kt:155`、`:210`）。
 * 三个 `*_doesNotThrow` 用例在修复前为**红**，修复后转绿。
 *
 * 纯 JVM：`RuleAnalyzer` 零 Android 依赖。
 */
class RuleAnalyzerTrimTest {

    // ===== BUG-2 复现与修复守护（越界）=====

    @Test
    fun trim_emptyString_thenSplit_noThrowAndEmptyRule() {
        val analyzer = RuleAnalyzer("")
        analyzer.trim() // 修复前：StringIndexOutOfBoundsException
        assertEquals(arrayListOf(""), analyzer.splitRule("@"))
    }

    @Test
    fun trim_allWhitespace_thenSplit_noThrowAndEmptyRule() {
        val analyzer = RuleAnalyzer("   ")
        analyzer.trim() // 修复前：while 越界
        assertEquals(arrayListOf(""), analyzer.splitRule("@"))
    }

    @Test
    fun trim_onlyAtPrefix_thenSplit_noThrowAndEmptyRule() {
        val analyzer = RuleAnalyzer("@")
        analyzer.trim() // 修复前：pos 越过 length
        assertEquals(arrayListOf(""), analyzer.splitRule("@"))
    }

    @Test
    fun trim_whitespaceOnly_thenSplit_noThrow() {
        val analyzer = RuleAnalyzer("\t \n")
        analyzer.trim()
        assertEquals(arrayListOf(""), analyzer.splitRule("@"))
    }

    /**
     * 复现 AnalyzeByJSoup 的真实调用路径：`"a&&"` 经 `splitRule("&&")` 产出尾空段，
     * 空段再交给 `RuleAnalyzer("").trim()`（`AnalyzeByJSoup.kt:210`）。
     */
    @Test
    fun splitThenTrimEmptyTailSegment_noThrow() {
        val analyzer = RuleAnalyzer("a&&")
        val rules = analyzer.splitRule("&&")
        assertEquals(arrayListOf("a", ""), rules)
        RuleAnalyzer(rules[1]).trim() // 修复前：越界
    }

    // ===== 正常路径不回归守护 =====

    @Test
    fun trim_leadingWhitespaceAndAt_trimsToFirstMeaningfulChar() {
        val analyzer = RuleAnalyzer("  @div.class")
        analyzer.trim()
        assertEquals(arrayListOf("div.class"), analyzer.splitRule("@"))
    }

    @Test
    fun trim_noLeadingJunk_keepsRuleIntact() {
        val analyzer = RuleAnalyzer("div.class")
        analyzer.trim()
        assertEquals(arrayListOf("div.class"), analyzer.splitRule("@"))
    }
}
