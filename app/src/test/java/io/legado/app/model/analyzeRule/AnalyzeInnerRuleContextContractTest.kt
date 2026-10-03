package io.legado.app.model.analyzeRule

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File

/**
 * 内联规则 `{{...}}` 解析上下文 —— **结构契约**守护（fix-analyze-inner-rule-context）。
 *
 * 行为回归由 [AnalyzeInnerRuleContextRegressionTest] 覆盖；本类钉死**结构不变式**，
 * 防止后人把 `makeUpRule` 的 hostContent 参数或 5 处调用点改回「传 result」的旧写法
 * （该写法正是本次缺陷的成因，且行为表现为静默取空，极难在用例之外发现）。
 */
class AnalyzeInnerRuleContextContractTest {

    private val rel = "src/main/java/io/legado/app/model/analyzeRule/AnalyzeRule.kt"

    private fun src(): String {
        val file = listOf(File(rel), File("../app/$rel"), File("app/$rel")).firstOrNull { it.isFile }
            ?: throw AssertionError("未找到源文件（工作目录=${File(".").absolutePath}）：$rel")
        return file.readText()
    }

    /** 契约 1：`makeUpRule` 必须带 hostContent 形参（默认值保证旧调用点可编译）。 */
    @Test
    fun makeUpRuleCarriesHostContentParam() {
        val s = src()
        assertTrue(
            "makeUpRule 必须声明 hostContent 形参：makeUpRule(result: Any?, hostContent: Any? = null)",
            s.contains("fun makeUpRule(result: Any?, hostContent: Any? = null)")
        )
    }

    /** 契约 2：内联子规则分支必须以 hostContent 求值，而非 result。 */
    @Test
    fun innerRuleBranchEvaluatesWithHostContent() {
        val s = src()
        assertTrue(
            "jsRuleType 分支必须以 hostContent 求值：getString(ruleList, hostContent ?: result)",
            s.contains("getString(ruleList, hostContent ?: result)")
        )
        assertTrue(
            "不得残留缺陷写法 getString(ruleList, result)",
            !s.contains("getString(ruleList, result)")
        )
    }

    /** 契约 3：5 处调用点必须显式贯穿调用方内容；不得残留单参调用。 */
    @Test
    fun allCallSitesPassHostContent() {
        val s = src()
        val withContent = Regex("""makeUpRule\(result, content\)""").findAll(s).count()
        val bareCall = Regex("""makeUpRule\(result\)""").findAll(s).count()
        assertEquals("makeUpRule(result, content) 调用点数量必须为 5", 5, withContent)
        assertEquals("不得残留单参 makeUpRule(result) 调用", 0, bareCall)
    }

    /** 契约 4（R4 守护）：`@js:` 段仍以「上一段输出 result」求值，语义未被本修复改变。 */
    @Test
    fun atJsStillEvaluatesWithPreviousResult() {
        val s = src()
        assertTrue(
            "@js 段必须仍以 result 求值（evalJS(rule, result) 至少 1 处）",
            s.contains("evalJS(rule, result)")
        )
    }
}