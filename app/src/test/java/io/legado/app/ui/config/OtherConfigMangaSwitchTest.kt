package io.legado.app.ui.config

import java.io.File
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * W5 6.3 / REQ-22：设置页「音量键翻页」条目的**双栈渲染**不变量。
 *
 * 该页实际渲染由 Compose spec 列表（`otherSettingItems()`）驱动，
 * XML（`pref_config_other.xml`）用于设置搜索收录 ⇒ 两处都要有条目，
 * 且文案键必须在两个 strings 目录都存在（否则显示为资源名）。
 */
class OtherConfigMangaSwitchTest {

    private fun read(rel: String): String =
        listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
            .readText()
            .replace("\r\n", "\n")

    private val fragment by lazy { read("src/main/java/io/legado/app/ui/config/OtherConfigFragment.kt") }
    private val strings by lazy { read("src/main/res/values/strings.xml") }
    private val stringsZh by lazy { read("src/main/res/values-zh/strings.xml") }

    @Test
    fun switchSitsNextToShowMangaUiWithSameDefaults() {
        val spec = fragment.substringAfter("otherSettingItems(): List<SettingItemSpec> {")
        val mangaUiAt = spec.indexOf("PreferKey.showMangaUi")
        val volumeAt = spec.indexOf("PreferKey.mangaVolumeKeyPage")
        assertTrue("音量键条目须存在", volumeAt > 0)
        assertTrue("须与「漫画浏览」相邻（同族分组）", volumeAt - mangaUiAt in 1..900)
    }

    @Test
    fun switchTitleAndSummaryComeFromStrings() {
        assertTrue("标题须走资源键", fragment.contains("R.string.manga_volume_key_page"))
        assertTrue("副标题须走资源键", fragment.contains("R.string.manga_volume_key_page_summary"))
        assertTrue("默认 values 须有该键", strings.contains("name=\"manga_volume_key_page\""))
        assertTrue("values-zh 须有该键", stringsZh.contains("name=\"manga_volume_key_page\""))
        assertTrue("默认 values 须有副标题键", strings.contains("name=\"manga_volume_key_page_summary\""))
        assertTrue("values-zh 须有副标题键", stringsZh.contains("name=\"manga_volume_key_page_summary\""))
    }
}