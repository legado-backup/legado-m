package io.legado.app.model.analyzeRule

import io.legado.app.exception.NoStackTraceException
import org.junit.Assert.fail
import org.junit.Test

/**
 * core-flow-test-coverage —— 规则引擎异常类型契约：**畸形规则不得抛 `java.lang.Error`**。
 *
 * 背景（先红后绿）：`RuleAnalyzer` 的 `splitRule` 在书源规则**括号不平衡**（用户数据，
 * 如 `b[ && a`）时原实现为 `throw Error(...)`；`java.lang.Error` **不是 `Exception`**
 * ⇒ 任何 `catch (e: Exception)` 层（UI 点击回调 / 服务 / 源校验链路）都拦不住 ⇒ 潜在崩溃。
 * 项目规范（AGENTS.md）明定「所有业务异常继承 `NoStackTraceException`」。
 */
class RuleAnalyzerMalformedRuleTest {

    @Test
    fun unbalancedBracketRule_throwsBusinessExceptionInsteadOfError() {
        try {
            RuleAnalyzer("b[ && a").splitRule("&&", "||")
            fail("畸形规则（括号不平衡）应抛出可被捕获的异常")
        } catch (e: NoStackTraceException) {
            // 期望：业务异常 → 可被 catch (e: Exception) 捕获，源优雅失败
        } catch (e: Throwable) {
            fail("畸形规则抛出 ${e.javaClass.name}（应为 NoStackTraceException；Error 会绕过 Exception 捕获层）")
        }
    }
}
