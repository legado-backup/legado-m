package io.legado.app.model.analyzeRule

import android.app.Application
import org.junit.Assert.assertEquals
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config

/**
 * 内联规则 `{{...}}` 解析上下文回归守护（fix-analyze-inner-rule-context）。
 *
 * 缺陷：`AnalyzeRule.SourceRule.makeUpRule` 的 `jsRuleType` 分支把**上一段规则的输出** `result`
 * 当作内联子规则的解析内容，正确语义应为**当前解析内容**（调用方 content）。
 *
 * 该缺陷在两个真实场景同时爆发（真机实证）：
 * - 订阅列表：JSON 栏目项规则 `{{$.id}}` 在「前序规则的标量输出」上做 JSONPath ⇒ 恒空 ⇒ 条目被判空；
 * - 订阅正文取图：`ruleContent` 的 `{{@@id.nowimg@src}}` 取不到原页面元素 ⇒ 图片地址退化为相对路径。
 *
 * 必须跑 Robolectric：`unitTests.returnDefaultValues = true` 下纯 JVM 的 `android.util.LruCache`
 * 是永 miss 的桩，且本类涉及 `evalJS`/`AppLog` 等 Android 侧依赖。
 *
 * 用例 1/2 在修复前为红（内联子规则取到 "PREV" 而非当前内容），修复后为绿；
 * 用例 3/4 为守护（修复前后均绿），分别钉死「首条内联规则不受影响」与「`@js:` 的 result 语义不变」。
 */
@RunWith(RobolectricTestRunner::class)
@Config(application = Application::class)
class AnalyzeInnerRuleContextRegressionTest {

    /** 场景：JSON 字符串内容（订阅列表 JSON 栏目体）+ 前序规则产出标量。 */
    @Test
    fun inlineJsonPathRule_jsonStringContent_usesHostContent() {
        val ar = AnalyzeRule()
        ar.setContent("""{"id":"777"}""")
        // 前序规则产出标量 "PREV"（模拟 id.allbtn@text 之类的计数/数量段）
        val rules = ar.splitSourceRule("<js>'PREV'</js>") +
            ar.splitSourceRule("<js>u='{{$.id}}'\nu\n</js>")
        assertEquals(2, rules.size)
        // 修复前：{{$.id}} 在 "PREV" 上求值 ⇒ 空；修复后：在当前内容上求值 ⇒ 777
        assertEquals("777", ar.getString(rules))
    }

    /** 场景：列表项为 Map（jayway JsonPath 读取对象返回 LinkedHashMap，与真机一致）。 */
    @Test
    fun inlineJsonPathRule_mapItem_usesHostContent() {
        val ar = AnalyzeRule()
        val item = LinkedHashMap<String, Any?>()
        item["id"] = "888"
        ar.setContent(item)
        val rules = ar.splitSourceRule("<js>'PREV'</js>") +
            ar.splitSourceRule("<js>u='{{$.id}}'\nu\n</js>")
        assertEquals("888", ar.getString(rules))
    }

    /** 边界：内联规则为**首条**时行为不变（内容 == 前序结果）。 */
    @Test
    fun inlineRule_asFirstRule_stillResolvesFromHostContent() {
        val ar = AnalyzeRule()
        val host = """<div id="nowimg" src="https://h/p/1.jpg"></div>"""
        ar.setContent(host)
        val rules = ar.splitSourceRule("<js>u='{{@@id.nowimg@src}}'\nu\n</js>")
        assertEquals("https://h/p/1.jpg", ar.getString(rules))
    }

    /** 守护 R4：`@js:` 规则中的 `result`（上一段输出）语义不得改变。 */
    @Test
    fun atJsRule_stillReceivesPreviousRuleResult() {
        val ar = AnalyzeRule()
        ar.setContent("""{"id":"999"}""")
        val rules = ar.splitSourceRule("<js>'PREV'</js>") +
            ar.splitSourceRule("<js>result + '-suffix'</js>")
        assertEquals("PREV-suffix", ar.getString(rules))
    }
}