package io.legado.app.ui.config

import io.legado.app.testkit.SourceFileProbe
import io.legado.app.ui.book.thought.ObsidianApi
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * NEW-81：Obsidian 批注导出的**四处接线完整性**守护。
 *
 * 缺陷背景：`ThoughtObsidianExporter` / `ObsidianApi` / `ThoughtMarkdownGenerator` 整条链路早已实现，
 * updateLog 亦已宣传「划线批注可导出到 Obsidian」，但 **5 个 `PreferKey.obsidian*` 配置项全仓零 UI、
 * 导出器零调用点** ⇒ 功能完全不可达（用户改了键也无任何效果）。本类把
 * 「弹窗 ↔ 设置页入口 ↔ 搜索索引 ↔ 字符串（中/英双库）」四处接线固化，任一处回退即红。
 *
 * 为什么同时含行为断言：路径编码是导出落点的关键（空格/中文/子路径编码错误 ⇒ 写到 Obsidian 的
 * 错误位置或直接 404），故对 `ObsidianApi.encodePath` 做带期望值的纯函数断言（G-42 口径）。
 */
class ObsidianExportConfigWiringTest {

    private fun text(rel: String): String = SourceFileProbe.sourceTextByPath(rel)

    @Test
    fun `obsidian api path encoding stays url safe`() {
        // 行为断言：逐段编码保留 `/` 分隔符；空格转 %20 而非 `+`
        assertEquals("my%20note.md", ObsidianApi.encodePath("my note.md"))
        assertEquals(
            "notes/thoughts/%E6%B5%8B%E8%AF%95%E4%B9%A6.md",
            ObsidianApi.encodePath("notes/thoughts/测试书.md")
        )
        assertEquals("", ObsidianApi.encodePath(""))
    }

    @Test
    fun `dialog dumps every obsidian field into the single source`() {
        val src = text("src/main/java/io/legado/app/ui/config/ObsidianExportConfig.kt")
        assertTrue("须为 Compose 弹窗（与校验设置弹窗同构）", src.contains("class ObsidianExportConfig : ComposeDialogFragment()"))
        assertTrue("标题须用新登记字符串", src.contains("R.string.obsidian_export_config"))
        assertTrue("本地模式必须提供 SAF 目录选择入口（否则功能半成品）", src.contains("HandleFileContract.DIR_SYS"))
        // 弹窗内全部字段必须一次性交给单源 AppConfig（漏传任一字段即静默不生效）
        listOf(
            "AppConfig.obsidianExportMethod = method",
            "AppConfig.obsidianApiUrl = apiUrl",
            "AppConfig.obsidianApiKey = apiKey",
            "AppConfig.obsidianVaultSubPath = subPath",
            "AppConfig.obsidianLocalDirUri = localDirUri.value",
            "AppConfig.obsidianAutoExport = autoExport"
        ).forEach { line ->
            assertTrue("persist 必须把 `$line` 落库", src.contains(line))
        }
        assertTrue("必须提供手动导出全部入口", src.contains("ThoughtObsidianExporter.exportAll()"))
        assertTrue("必须提供 API 连通性测试入口（复用 ObsidianApi.checkConnection）", src.contains("ObsidianApi.checkConnection("))
    }

    @Test
    fun `settings entry is registered next to the rss check entry`() {
        val src = SourceFileProbe.sourceText("ui/config/OtherConfigFragment.kt")
        assertTrue("设置页须有 Obsidian 导出项", src.contains("key = PreferKey.obsidianExportMethod"))
        assertTrue("标题须引用新字符串", src.contains("R.string.obsidian_export_config"))
        assertTrue("点击须打开同构弹窗", src.contains("showDialogFragment<ObsidianExportConfig>()"))
        assertTrue("须与订阅校验设置并列（保持配置弹窗成组）", src.contains("key = PreferKey.checkRssSource"))
    }

    @Test
    fun `search index xml knows the new entry`() {
        // 设置搜索收录走 `pref_config_other.xml`：漏登记会导致新入口搜不到
        val xml = text("src/main/res/xml/pref_config_other.xml")
        assertTrue("搜索索引须登记 obsidianExportMethod", xml.contains("android:key=\"obsidianExportMethod\""))
        assertTrue("索引条目标题须引用新字符串", xml.contains("@string/obsidian_export_config"))
    }

    @Test
    fun `new strings exist in both default and chinese resources`() {
        // 缺字符串会直接崩（Resources$NotFoundException）⇒ 默认库与中文库都必须有
        listOf(
            "src/main/res/values/strings.xml",
            "src/main/res/values-zh/strings.xml"
        ).forEach { rel ->
            val res = text(rel)
            listOf(
                "obsidian_export_config",
                "obsidian_export_config_summary",
                "obsidian_export_method",
                "obsidian_api_url",
                "obsidian_auto_export",
                "obsidian_export_all",
                "obsidian_export_all_result",
                "obsidian_export_all_failed"
            ).forEach { name ->
                assertTrue("$rel 缺少 <string name=\"$name\">", res.contains("name=\"$name\""))
            }
        }
    }
}
