package io.legado.app.ui.main.my

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * W8 9.4（REQ-32）：名场面库的**「我的 → 工具」入口**不变量（防死页面）。
 *
 * 本主线已多次实证「页面做了但入口没接 = 用户永远到不了」（design §11.2#2 明确点名本任务）。
 * 入口链两段都必须在位：① 工具分区的 `actionRow`；② `handleSettingsRowClick` 的跳转分支。
 * 另锁双 `strings.xml` 齐备（缺 values-zh 会显示为资源名）。
 */
class SceneBookmarkEntryTest {

    private val data by lazy { SourceFileProbe.sourceText("ui/main/my/MySettingsData.kt") }
    private val strings by lazy { SourceFileProbe.resValuesText("strings.xml") }
    private val stringsZh by lazy {
        SourceFileProbe.sourceTextByPath("src/main/res/values-zh/strings.xml")
    }

    @Test
    fun toolsSectionCarriesTheLibraryEntry() {
        val tools = data.substringAfter("R.string.config_category_tools")
            .substringBefore("R.string.read_record_summary")
        assertTrue(
            "工具分区缺「名场面书签」入口",
            tools.contains("actionRow(\"sceneBookmark\", R.string.scene_bookmark_library")
        )
        assertTrue(
            "入口应与书签入口相邻（同族分组）",
            tools.contains("actionRow(\"bookmark\"")
        )
    }

    @Test
    fun clickRouteOpensTheLibraryActivity() {
        assertTrue(
            "handleSettingsRowClick 缺跳转分支（入口点了没反应）",
            data.contains("\"sceneBookmark\" -> startActivity<SceneBookmarkActivity>()")
        )
    }

    @Test
    fun bothStringSetsHaveTheEntryTexts() {
        listOf("scene_bookmark_library", "scene_bookmark_summary").forEach { key ->
            assertTrue("默认 values 缺 $key", strings.contains("name=\"$key\""))
            assertTrue("values-zh 缺 $key", stringsZh.contains("name=\"$key\""))
        }
    }
}
