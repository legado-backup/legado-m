package io.legado.app.help.config

import io.legado.app.ui.book.explore.ExploreShowLayout
import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * video-cache-and-multiep R11 / V7：发现页布局全局默认值不变量。
 *
 * 为什么值得测：默认值由 1 翻成 2（瀑布）是单字符改动，极易被后续重构改回；
 * 取值范围 1..4 若漏改，双列（4）写入就会被静默钳成三列（3）。
 */
class AppConfigDiscoveryLayoutDefaultTest {

    private fun read(rel: String): String =
        listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
            .readText()
            .replace("\r\n", "\n")

    private val appConfig by lazy { read("src/main/java/io/legado/app/help/config/AppConfig.kt") }

    @Test
    fun defaultMatchesExploreShowLayoutDefault() {
        assertEquals("默认布局须为瀑布", 2, ExploreShowLayout.DEFAULT)
        assertTrue(
            "AppConfig 读取默认值须与 ExploreShowLayout.DEFAULT 一致",
            appConfig.contains("getPrefInt(PreferKey.discoveryPageLayout, ${ExploreShowLayout.DEFAULT})")
        )
    }

    @Test
    fun rangeCoversAllPickerValues() {
        assertTrue(
            "读写须钳制在 1..4（含双列）",
            appConfig.contains("coerceIn(1, 4)")
        )
        assertEquals(ExploreShowLayout.MIN, 1)
        assertEquals(ExploreShowLayout.MAX, 4)
        assertTrue(
            "选择器取值必须全部落在可写区间内",
            ExploreShowLayout.pickerValues.all { it in ExploreShowLayout.MIN..ExploreShowLayout.MAX }
        )
    }
}
