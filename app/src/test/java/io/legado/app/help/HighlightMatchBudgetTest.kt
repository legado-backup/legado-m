package io.legado.app.help

import io.legado.app.help.HighlightRuleMatcher
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import java.util.concurrent.CountDownLatch
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicReference

/**
 * §9.5.6 高亮匹配性能治理单测：
 * 1. **整章总预算**封顶（取代逐规则 3s 累加）：超预算即停剩余规则并标记 `truncated`
 * 2. 未超预算时结果与既有 `matchWithTemplate` 完全一致（零回归）
 * 3. `literalMetaWarned` 并发写入不抛异常（原实现为普通 `mutableSetOf`，多线程下会 CME）
 */
class HighlightMatchBudgetTest {

    private fun rule(id: String, pattern: String, literal: Boolean = true) =
        HighlightRuleMatcher.Rule(
            id = id,
            pattern = pattern,
            isRegex = !literal,
            style = HighlightStyle(textColor = 0xFFFF0000.toInt())
        )

    private val text = "他停了一下（暗道不对）。然后说：“走吧。”"

    @Test
    fun budgetExhausted_stopsRemainingRulesAndFlagsTruncated() {
        val rules = listOf(
            rule("r1", "停了一下"),
            rule("r2", "暗道"),
            rule("r3", "走吧")
        )
        // 截止时刻 = 当前时刻 → 第一条规则前即判定越界
        val outcome = HighlightRuleMatcher.matchWithBudget(
            text, rules, deadlineMs = System.currentTimeMillis()
        )
        assertTrue("超预算必须置 truncated", outcome.truncated)
        assertTrue("超预算时不应产出半成品命中", outcome.matches.isEmpty())
    }

    @Test
    fun withinBudget_behavesLikeLegacyMatchTemplate() {
        val rules = listOf(
            rule("r1", "停了一下"),
            rule("r2", "走吧")
        )
        val legacy = HighlightRuleMatcher.matchWithTemplate(text, rules)
        val outcome = HighlightRuleMatcher.matchWithBudget(
            text, rules, deadlineMs = System.currentTimeMillis() + 10_000L, withTemplate = true
        )
        assertFalse(outcome.truncated)
        assertEquals(legacy.map { it.ruleId }, outcome.matches.map { it.ruleId })
        assertEquals(legacy.map { it.start }, outcome.matches.map { it.start })
    }

    @Test
    fun match_defaultOverload_hasNoBudget() {
        // 既有 match()/matchWithTemplate() 调用点（默认 Long.MAX_VALUE）行为不变
        val rules = listOf(rule("r1", "暗道"))
        assertEquals(1, HighlightRuleMatcher.match(text, rules).size)
        assertEquals(1, HighlightRuleMatcher.matchWithTemplate(text, rules).size)
    }

    @Test
    fun literalMetaWarned_concurrentWritesNeverThrow() {
        // 字面量 pattern 含正则元字符 → 触发 literalMetaWarned 登记；多线程并发写入不得抛异常
        val pool = Executors.newFixedThreadPool(8)
        val failure = AtomicReference<Throwable?>(null)
        val start = CountDownLatch(1)
        val threads = 8
        val rounds = 300
        val done = CountDownLatch(threads)
        repeat(threads) { t ->
            pool.execute {
                try {
                    start.await()
                    for (i in 0 until rounds) {
                        val meta = "暗道[t$t-$i]"
                        val rules = listOf(rule("warn$t-$i", meta))
                        HighlightRuleMatcher.match(text.replace("暗道", meta), rules)
                    }
                } catch (e: Throwable) {
                    failure.compareAndSet(null, e)
                } finally {
                    done.countDown()
                }
            }
        }
        start.countDown()
        assertTrue("并发匹配超时未完成", done.await(30, TimeUnit.SECONDS))
        pool.shutdownNow()
        failure.get()?.let { throw AssertionError("并发写入抛异常: $it", it) }
    }
}