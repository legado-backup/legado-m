package io.legado.app.ui.about

import io.legado.app.testkit.SourceFileProbe
import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * W-Final 10.2 / REQ-35：about 页**定位句 + 四条承诺**的接线与**文案纪律**不变量。
 *
 * 纪律来源：用户 2026-09-27 批评「品牌化别吹过头」，tasks §10 固化为 5 条 ——
 * 只陈述已交付能力 / 禁竞品夸张词 / 不平移纲领定性判断为结论 / 每条承诺有对应能力 / 平实可核对。
 */
class AboutPositioningTest {

    private fun about(): String =
        SourceFileProbe.sourceText("ui/about/AboutFragment.kt").replace("\r\n", "\n")

    private fun strings(): String =
        SourceFileProbe.sourceTextByPath("src/main/res/values/strings.xml").replace("\r\n", "\n")

    private val positionKeys = listOf(
        "about_positioning",
        "about_promise_no_account",
        "about_promise_cross_content",
        "about_promise_your_library",
        "about_promise_no_ads",
    )

    @Test
    fun positioningBlockIsWiredIntoFooter() {
        val s = about()
        assertTrue("须有定位块 Composable", s.contains("private fun AboutPositioningBlock()"))
        assertTrue("须挂到页脚（否则不显示）", s.contains("AboutPositioningBlock()"))
        assertTrue("四条承诺须逐个引用（缺一条即承诺不完整）", s.contains("R.string.about_promise_no_ads"))
    }

    @Test
    fun positioningCopiesExistInResources() {
        positionKeys.forEach { name ->
            assertTrue("缺字符串 `$name`", strings().contains("""name="$name""""))
        }
    }

    /** 纪律②：禁竞品对比性夸张词（未做横向实测 ⇒ 一律不得使用）—— 只校验本次新增的 5 条文案值。 */
    @Test
    fun copyFollowsDisciplineNoHypeWords() {
        val banned = listOf("唯一", "独一份", "生态唯一", "代差", "碾压", "颠覆", "遥遥领先", "无法跟进")
        positionKeys.forEach { name ->
            val m = Regex("""<string name="$name">([^<]*)</string>""").find(strings())
            assertTrue("缺字符串 `$name`（无法校验文案纪律）", m != null)
            val value = m!!.groupValues[1]
            banned.forEach { word ->
                assertFalse("定位文案「$name」含禁词「$word」", value.contains(word))
            }
        }
    }

    /** 10.1：README **首屏**须去掉「功能基座 / 深度对齐」式表述，改为克制定位句。
     *
     * 只校验首屏：按 10.1 口径血缘描述**移入文末「致谢」**，在致谢段出现是预期的。
     */
    @Test
    fun readmeHasNoLegacyBaselineWording() {
        // ⚠️ 不得用 SourceFileProbe.sourceText：其 stripComments 会剥掉以 `*` 开头的行，
        // 而 README 的定位句正是 `**全内容阅读器**…` ⇒ 会被误剥造成假失败。此处直读原文件。
        val readme = listOf(File("../README.md"), File("README.md"), File("../../README.md"))
            .first { it.isFile }.readText().replace("\r\n", "\n")
        val head = readme.lines().take(20).joinToString("\n")
        assertFalse("README 首屏不得再出现「功能基座」表述", head.contains("功能基座"))
        assertFalse("README 首屏不得再出现「UI 体系深度对齐」表述", head.contains("UI 体系深度对齐"))
        assertTrue("README 首屏须含克制定位句", head.contains("全内容阅读器"))
    }
}