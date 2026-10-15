package io.legado.app.ui.rss.source.manage

import java.io.File
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * W4 / REQ-19（AD-09）：OPML 导入导出的**入口接线**不变量。
 *
 * 三条约定：
 * ① 菜单两项可达且**挂载位**与设计一致（导入在「导入校验配置」之后；导出在「帮助」之前）；
 * ② 导入用**独立 launcher**（OPML 与 JSON 解析器完全不同，不能串用既有 ImportRssSourceDialog）；
 * ③ 四类错误各有明确文案（超限 / 过深 / 空 / 非法），不静默失败。
 */
class RssSourceOpmlMenuWiringTest {

    private val activity by lazy {
        listOf(
            File("src/main/java/io/legado/app/ui/rss/source/manage/RssSourceActivity.kt"),
            File("../app/src/main/java/io/legado/app/ui/rss/source/manage/RssSourceActivity.kt"),
            File("app/src/main/java/io/legado/app/ui/rss/source/manage/RssSourceActivity.kt")
        ).first { it.isFile }.readText()
            .replace("\r\n", "\n")
    }

    @Test
    fun bothMenuEntriesExistAtDesignedAnchors() {
        val importAt = activity.indexOf("AppManagementMenuAction(getString(R.string.opml_import))")
        val checkConfigAt = activity.indexOf("R.string.import_check_config")
        val exportAt = activity.indexOf("AppManagementMenuAction(getString(R.string.opml_export_library))")
        val helpAt = activity.indexOf("AppManagementMenuAction(getString(R.string.help))")
        assertTrue("导入 OPML 菜单须存在", importAt > 0)
        assertTrue("导入 OPML 须排在「导入校验配置」之后", importAt > checkConfigAt && checkConfigAt > 0)
        assertTrue("导出 OPML 菜单须存在", exportAt > 0)
        assertTrue("导出 OPML 须排在「帮助」之前", exportAt < helpAt && helpAt > 0)
    }

    @Test
    fun opmlImportUsesDedicatedLauncherWithItsOwnExtensions() {
        assertTrue("须有独立 OPML launcher", activity.contains("private val importOpmlDoc = registerForActivityResult"))
        assertTrue("须限定 .opml/.xml 扩展名", activity.contains("""allowExtensions = arrayOf("opml", "xml")"""))
        // OPML 回调体必须走自己的解析链，不得复用 JSON 导入弹窗
        val launcherBody = activity.substringAfter("private val importOpmlDoc")
            .substringBefore("private val exportOpmlDoc")
        assertTrue("OPML launcher 回调须调 importOpml(uri)", launcherBody.contains("importOpml(uri)"))
        assertTrue("OPML launcher 回调不得走 JSON 弹窗", !launcherBody.contains("ImportRssSourceDialog"))
    }

    @Test
    fun importGuardsSizeAndCharsetAndReportsAllErrorReasons() {
        assertTrue("读取须带上限（防 OOM）", activity.contains("if (total > OpmlParser.MAX_BYTES) return@use null"))
        assertTrue("编码须复用 REQ-09 链", activity.contains("EncodingDetect.resolveEncode(declared, bytes)"))
        listOf(
            "OpmlParseResult.Reason.TOO_LARGE",
            "OpmlParseResult.Reason.TOO_DEEP",
            "OpmlParseResult.Reason.EMPTY",
            "OpmlParseResult.Reason.INVALID"
        ).forEach { reason ->
            assertTrue("缺错误映射：$reason", activity.contains(reason))
        }
    }

    @Test
    fun exportWritesUtf8OpmlThroughSeparateSafCallback() {
        assertTrue("导出须生成 OPML 内容", activity.contains("OpmlExporter.export(sources)"))
        assertTrue("导出须 UTF-8", activity.contains("writeText(OpmlExporter.export(sources), Charsets.UTF_8)"))
        assertTrue("须有独立导出回调（不串用 JSON 导出的 DirectLink 提示）", activity.contains("private val exportOpmlDoc = registerForActivityResult"))
        assertTrue("整库导出须用 text/xml MIME", activity.contains("""HandleFileContract.FileData("rssLibrary.opml", file, "text/xml")"""))
    }

    @Test
    fun emptyLibraryGivesReceiptInsteadOfWritingEmptyFile() {
        assertTrue("无订阅源时须明确提示", activity.contains("toastOnUi(R.string.opml_error_empty)"))
    }

    // ---- NEW-28（订阅源巡检接线）：选择态入口不得再缺 ----

    @Test
    fun selectionCheckEntryIsWiredToRssCheckService() {
        // 此前 `CheckRssSourceService` 全链**无任何 UI 入口**（选择态菜单只有启用/禁用/置顶/导出/分享/
        // 分组/删除）⇒ 整条订阅源巡检 + 去重标注不可达。现按书源管理页同构补「校验所选」入口。
        assertTrue(
            "选择态须有「校验所选」入口（与书源管理页同构）",
            activity.contains("text = getString(R.string.check_select_source)")
        )
        assertTrue("入口须落在 bottomActions 内且调 checkRssSelected", activity.contains("onClick = ::checkRssSelected"))
        assertTrue("须有落地方法", activity.contains("private fun checkRssSelected()"))
        assertTrue("须启动订阅源校验服务", activity.contains("CheckRssSource.start(this, selection)"))
        assertTrue("跑完须退出选择态（避免与巡检态混淆）", activity.contains("selectedUrls.value = emptySet()"))
    }
}