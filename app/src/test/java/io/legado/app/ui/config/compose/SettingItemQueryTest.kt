package io.legado.app.ui.config.compose

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 页内检索匹配判据单测（ui-subpage-optimization B1.2 优化 1）。
 *
 * 覆盖 [SettingItemSpec.matchesQuery] 的四个匹配维度与大小写/空查询语义——
 * 该判据是「设置页框架级检索」的过滤核心，设备不可用时以此保证逻辑正确性。
 */
class SettingItemQueryTest {

    private fun switchItem(
        key: String,
        title: String,
        summary: String? = null,
        searchKeys: List<String> = emptyList()
    ) = SettingSwitchSpec(
        key = key,
        title = title,
        checked = false,
        onCheckedChange = {},
        summary = summary,
        searchKeys = searchKeys
    )

    @Test
    fun `空查询恒命中`() {
        val item = switchItem("k", "主题")
        assertTrue(item.matchesQuery(""))
    }

    @Test
    fun `按标题匹配`() {
        val item = switchItem("k", "主题列表")
        assertTrue(item.matchesQuery("主题"))
        assertFalse(item.matchesQuery("书源"))
    }

    @Test
    fun `按摘要匹配`() {
        val item = switchItem("k", "标题", summary = "调整界面配色与明暗")
        assertTrue(item.matchesQuery("配色"))
        assertFalse(item.matchesQuery("朗读"))
    }

    @Test
    fun `摘要为空时不误命中`() {
        val item = switchItem("k", "标题")
        assertFalse(item.matchesQuery("任意"))
    }

    @Test
    fun `按键名匹配`() {
        val item = switchItem("themeCardColor", "卡片")
        assertTrue(item.matchesQuery("themeCard"))
    }

    @Test
    fun `按 searchKeys 匹配`() {
        val item = switchItem("k", "标题", searchKeys = listOf("夜间模式", "darkMode"))
        assertTrue(item.matchesQuery("夜间"))
        assertTrue(item.matchesQuery("dark"))
        assertFalse(item.matchesQuery("白天"))
    }

    @Test
    fun `忽略大小写`() {
        val item = switchItem("k", "DarkMode")
        assertTrue(item.matchesQuery("darkmode"))
        assertTrue(item.matchesQuery("DARKMODE"))
    }

    @Test
    fun `命中任一维度即通过`() {
        // 标题不含、摘要不含、键名含 ⇒ 仍应命中
        val item = switchItem("fontScale", "字号", summary = "全局字号档位")
        assertTrue(item.matchesQuery("fontScale"))
        assertTrue(item.matchesQuery("字号"))
    }
}
