package io.legado.app.ui.main.my

import java.io.File
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 「我的」页 Web 服务入口与设置页的接线不变量（一期 §6.6 / §6.7）。
 *
 * 背景：新页 `WebServiceSettingsActivity` 若没有任何入口，用户仍只能靠"翻通知找地址"；
 * 而把快捷开关整块搬走又会让"改端口"这类高频动作变深。故本测试锁住设计裁定：
 * **保留快捷开关与复制/打开两个动作，并追加「设置」跳转**。
 */
class WebServiceEntryWiringTest {

    private fun read(rel: String): String =
        listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
            .readText()
            .replace("\r\n", "\n")

    private val settingsData by lazy { read("src/main/java/io/legado/app/ui/main/my/MySettingsData.kt") }
    private val optionsDialog by lazy {
        settingsData.substringAfter("fun AppCompatActivity.showWebServiceOptions()")
    }

    @Test
    fun quickActionsDialogKeepsExistingTwoActions() {
        assertTrue("须保留「复制」动作", optionsDialog.contains("getString(R.string.copy_text)"))
        assertTrue("须保留「浏览器打开」动作", optionsDialog.contains("getString(R.string.open_in_browser)"))
        assertTrue("须保留复制实现", optionsDialog.contains("0 -> sendToClip(url)"))
        assertTrue("须保留浏览器打开实现", optionsDialog.contains("1 -> openUrl(url)"))
    }

    @Test
    fun quickActionsDialogAddsSettingsEntry() {
        assertTrue(
            "须新增「设置」入口文案（一期 §6.6）",
            optionsDialog.contains("getString(R.string.web_service_settings_title)")
        )
        assertTrue(
            "「设置」须跳转到新页 WebServiceSettingsActivity",
            optionsDialog.contains("2 -> startActivity<WebServiceSettingsActivity>()")
        )
    }

    @Test
    fun summaryTextIsDelegatedToSharedLogic() {
        val state = settingsData.substringAfter("internal fun Context.webServiceUiState()")
        assertTrue(
            "摘要措辞须与设置页共用一处（禁止本页另写一套）",
            state.contains("WebServiceSettingsLogic.serviceSummaryText(")
        )
        assertTrue(
            "「运行中但地址未就绪」须有占位文案（旧实现此处渲染为空行）",
            state.contains("pendingText = getString(R.string.web_address_pending)")
        )
        assertTrue(
            "未运行时仍显示原离线描述（保持既有「我的」页语义）",
            state.contains("stoppedText = getString(R.string.web_service_desc)")
        )
    }
}
