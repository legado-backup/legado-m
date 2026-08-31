package io.legado.app.model.analyzeRule

import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * C0-F1 缓存污染修复回归守护（master-track-orchestration tasks 1.3/1.4）
 *
 * 纯 JVM（build.gradle returnDefaultValues=true：android.util.LruCache stub 退化为永 miss，
 * 不影响断言语义——本类聚焦 SourceRule 不可变性与 ResolvedSourceRule 快照语义，缓存路径由 L2 S2/L3 兜底）。
 *
 * 三向量复现依据：C0 分册 §3.6（V1 跨分支键访问/V2 replaceRegex 残留/V3 重入半更新，已源码逐点核实）。
 * makeUpRule_doesNotMutateRuleField 在修复前为红（rule 字段被原地改写），修复后为绿。
 */
class AnalyzeRuleCachePollutionTest {

    @Test
    fun makeUpRule_doesNotMutateRuleField() {
        val analyzeRule = AnalyzeRule()
        val sourceRule = analyzeRule.splitSourceRule("""{{"abc"}}""").first()
        val originalRule = sourceRule.rule
        sourceRule.makeUpRule("anything")
        // 修复前：rule 被原地改写为 jsEval 结果 "abc"（≠ 原始定义），缓存复用即污染
        assertEquals(originalRule, sourceRule.rule)
    }

    @Test
    fun makeUpRule_snapshotIndependentPerCall() {
        val analyzeRule = AnalyzeRule()
        val sourceRule = analyzeRule.splitSourceRule("""{{"abc"}}##re""").first()
        val s1 = sourceRule.makeUpRule("r1")
        val s2 = sourceRule.makeUpRule("r2")
        // 同一 SourceRule 两次解析：快照独立且幂等一致，无跨调用残留
        assertEquals(s1, s2)
        assertEquals(s1.rule, s2.rule)
        assertEquals(s1.replaceRegex, s2.replaceRegex)
    }

    @Test
    fun makeUpRule_snapshotCarriesParams() {
        val analyzeRule = AnalyzeRule()
        val sourceRule = analyzeRule.splitSourceRule("""{{"abc"}}##re##rp###""").first()
        val snapshot = sourceRule.makeUpRule("r1")
        assertEquals("abc", snapshot.rule)
        assertEquals("re", snapshot.replaceRegex)
        assertEquals("rp", snapshot.replacement)
        assertEquals(true, snapshot.replaceFirst)
        // 原始规则定义恒不被改写（快照化核心断言）
        assertEquals("""{{"abc"}}##re##rp###""", sourceRule.rule)
    }
}
