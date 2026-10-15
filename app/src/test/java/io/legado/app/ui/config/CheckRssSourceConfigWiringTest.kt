package io.legado.app.ui.config

import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * NEW-33：订阅源校验设置入口的**接线完整性**守护。
 *
 * 缺陷背景（本条测试存在的理由）：`CheckRssSource` 的 8 个配置项与 `check_rss_source_config_summary`
 * 等字符串早已就位，却**全仓零消费者**（`summary` 无人读、设置页无入口）⇒ 订阅源巡检长期只能跑默认档，
 * 用户可感（无法调超时/检查项/去重）。本类把「弹窗 ↔ 设置页入口 ↔ 搜索索引 ↔ 字符串」四处接线固化，
 * 任一处回退即红。
 *
 * 为什么主要用文本探针：Compose 弹窗的 `onClick → applyConfig` 需要真实宿主（appCtx/Compose），
 * 纯 JVM 不可行为化；本类同时包含一条**可行为化**的纯函数断言（[filterAsciiDigits]），
 * 其余为接线形态探针（与 `RssCheckConfigWiringTest` 同口径）。
 */
class CheckRssSourceConfigWiringTest {

    private fun code(rel: String): String =
        listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
            .readText().replace("\r\n", "\n")

    @Test
    fun filterAsciiDigitsKeepsOnlyAsciiDigits() {
        // 行为断言：超时输入行必须拒绝全角数字/字母（否则 toLongOrNull 解析失败或误收脏输入）
        assertEquals("", "１２３".filterAsciiDigits())
        assertEquals("123", "1a2b3".filterAsciiDigits())
        assertEquals("", "".filterAsciiDigits())
        assertEquals("45", "  4 5  ".filterAsciiDigits())
    }

    @Test
    fun dialogDropsEveryConfigFieldIntoTheModelInOneCall() {
        val src = code("src/main/java/io/legado/app/ui/config/CheckRssSourceConfig.kt")
        assertTrue("须为 Compose 弹窗（与书源侧同构）", src.contains("class CheckRssSourceConfig : ComposeDialogFragment()"))
        assertTrue("标题须用新登记字符串", src.contains("R.string.check_rss_source_config"))
        assertTrue("超时标签须用订阅源专属字符串", src.contains("R.string.check_rss_source_timeout"))
        // 8 个字段必须一次性交给单源保存入口（漏传即静默不生效）
        val saveBody = src.substringAfter("private fun saveConfig(")
        listOf(
            "checkDomain = checkDomain", "domainCheckMode = domainCheckMode",
            "checkArticles = checkArticles", "checkSearch = checkSearch",
            "checkSort = checkSort", "checkContent = checkContent", "enableDedup = enableDedup"
        ).forEach { arg ->
            assertTrue("saveConfig 必须把 `$arg` 交给 applyConfig", saveBody.contains(arg))
        }
        assertTrue("必须走单源保存入口", saveBody.contains("CheckRssSource.applyConfig("))
        assertTrue(
            "必须回写设置页摘要键（否则设置页看不到当前配置）",
            saveBody.contains("putPrefString(PreferKey.checkRssSource, CheckRssSource.summary)")
        )
    }

    @Test
    fun settingsEntryIsRegisteredNextToBookSourceEntry() {
        val src = code("src/main/java/io/legado/app/ui/config/OtherConfigFragment.kt")
        assertTrue("设置页须有订阅源校验设置项", src.contains("key = PreferKey.checkRssSource"))
        assertTrue("标题须引用新字符串", src.contains("R.string.check_rss_source_config"))
        assertTrue("摘要须实时反映配置", src.contains("summary = CheckRssSource.summary"))
        assertTrue("点击须打开同构弹窗", src.contains("showDialogFragment<CheckRssSourceConfig>()"))
        assertTrue("须与书源校验设置并列（成对出现）", src.contains("key = PreferKey.checkSource"))
    }

    @Test
    fun searchIndexXmlKnowsTheNewEntry() {
        // 设置搜索收录走 `pref_config_other.xml`：漏登记会导致新入口搜不到（与书源侧不成对）
        val xml = code("src/main/res/xml/pref_config_other.xml")
        assertTrue("搜索索引须登记 checkRssSource", xml.contains("android:key=\"checkRssSource\""))
        assertTrue("索引条目标题须引用新字符串", xml.contains("@string/check_rss_source_config"))
    }

    @Test
    fun newStringsExistInBothDefaultAndChineseResources() {
        // 缺字符串会直接崩（Resources$NotFoundException）⇒ 默认库与中文库都必须有
        listOf(
            "src/main/res/values/strings.xml",
            "src/main/res/values-zh/strings.xml"
        ).forEach { rel ->
            val res = code(rel)
            listOf("check_rss_source_config", "check_rss_source_timeout", "dedup").forEach { name ->
                assertTrue("$rel 缺少 <string name=\"$name\">", res.contains("name=\"$name\""))
            }
        }
    }
}
