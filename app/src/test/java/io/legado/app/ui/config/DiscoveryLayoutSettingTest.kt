package io.legado.app.ui.config

import io.legado.app.ui.book.explore.ExploreShowLayout
import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Test

/**
 * video-cache-and-multiep R11 / V7：发现页布局设置项接线不变量。
 */
class DiscoveryLayoutSettingTest {

    private fun read(rel: String): String =
        listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
            .readText()
            .replace("\r\n", "\n")

    private val fragment by lazy {
        read("src/main/java/io/legado/app/ui/config/DiscoverySubscriptionConfigFragment.kt")
    }

    @Test
    fun pickerValuesCoverFourModesInRequirementOrder() {
        assertEquals(
            "选择器须为 列表/瀑布/双列/三列",
            listOf(
                ExploreShowLayout.LIST,
                ExploreShowLayout.WATERFALL,
                ExploreShowLayout.DUAL,
                ExploreShowLayout.TRIPLE,
            ),
            ExploreShowLayout.pickerValues,
        )
        assertEquals("四种模式列数", listOf(1, 2, 2, 3), ExploreShowLayout.pickerValues.map(ExploreShowLayout::columns))
    }

    @Test
    fun settingReusesSinglePickerSource() {
        org.junit.Assert.assertTrue(
            "设置项取值须复用 ExploreShowLayout.pickerValues（防两处顺序漂移）",
            fragment.contains("DISCOVERY_LAYOUT_VALUES = ExploreShowLayout.pickerValues"),
        )
    }

    @Test
    fun settingVisibleInBothDiscoveryModes() {
        assertFalse(
            "布局为全局配置，传统/新版发现页均生效 ⇒ 不得按发现页模式隐藏设置项",
            fragment.contains("visible = discoveryMode =="),
        )
    }
}
