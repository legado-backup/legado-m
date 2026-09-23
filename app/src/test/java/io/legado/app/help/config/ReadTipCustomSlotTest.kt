package io.legado.app.help.config

import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * B3 · R12「页眉页脚自定义模板」配置侧不变量。
 *
 * 需求（spec R12）：
 * - 6 个槽位各自可设模板（不是全局一份）；
 * - **新装/升级零变化**：哨兵值落在既有枚举之外、模板字段默认空串；
 * - **既有枚举路径不动**（X5 回归风险最小）；
 * - 6 个模板用独立 String 字段而非集合（R8 × Gson 泛型签名门禁）。
 */
class ReadTipCustomSlotTest {

    private fun code(relFromMainJava: String): String {
        val rel = "src/main/java/io/legado/app/$relFromMainJava"
        val file = listOf(File(rel), File("../app/$rel"), File("app/$rel")).firstOrNull { it.isFile }
            ?: throw AssertionError("未找到源文件（工作目录=${File(".").absolutePath}）：$rel")
        return file.readLines()
            .filterNot { it.trimStart().startsWith("//") || it.trimStart().startsWith("*") }
            .joinToString("\n")
    }

    /** 哨兵值必须在既有枚举（0..11）之外，且独立于枚举语义（多槽位可同时自定义）。 */
    @Test
    fun sentinelIsOutsideLegacyEnumRange() {
        val src = code("help/config/ReadTipConfig.kt")
        assertTrue("哨兵值必须落在既有枚举之外", src.contains("const val custom = 100"))
        assertTrue("既有总进度槽位取值必须仍是 11（不得被顶替）", src.contains("const val totalProgress1 = 11"))
        assertTrue(
            "选择列表必须包含哨兵（否则用户无法选中「自定义模板」）",
            src.contains("timeBatteryPercentage, custom")
        )
    }

    /** 槽位下标常量齐备（6 个），且读写走同一套 slotValue/slotTemplate 门面。 */
    @Test
    fun sixSlots_areAddressableByIndex() {
        val src = code("help/config/ReadTipConfig.kt")
        assertTrue(src.contains("const val slotCount = 6"))
        listOf(
            "SLOT_HEADER_LEFT", "SLOT_HEADER_MIDDLE", "SLOT_HEADER_RIGHT",
            "SLOT_FOOTER_LEFT", "SLOT_FOOTER_MIDDLE", "SLOT_FOOTER_RIGHT"
        ).forEach { name ->
            assertTrue("缺少槽位常量 $name", src.contains("const val $name ="))
            assertTrue("slotValue 未覆盖 $name", src.contains("$name -> tip"))
            assertTrue("slotTemplate 未覆盖 $name", src.contains("$name -> tip"))
        }
    }

    /** 6 个模板字段：独立 String（非 Map/List）且默认空串 ⇒ 升级零变化。 */
    @Test
    fun sixTemplateFields_arePlainStringsWithEmptyDefault() {
        val src = code("help/config/ReadBookConfig.kt")
        listOf(
            "tipHeaderLeftTemplate", "tipHeaderMiddleTemplate", "tipHeaderRightTemplate",
            "tipFooterLeftTemplate", "tipFooterMiddleTemplate", "tipFooterRightTemplate"
        ).forEach { name ->
            assertTrue(
                "字段 $name 必须是默认空串的 String（升级零变化 + 规避 Gson 集合签名门禁）",
                src.contains("var $name: String = \"\"")
            )
        }
    }

    /** 模板必须随阅读配置一起分享/导出（否则换机后自定义模板丢失、槽位却仍是 custom ⇒ 空槽位）。 */
    @Test
    fun templatesAreIncludedInSharedConfig() {
        val src = code("help/config/ReadBookConfig.kt")
        listOf(
            "tipHeaderLeftTemplate", "tipHeaderMiddleTemplate", "tipHeaderRightTemplate",
            "tipFooterLeftTemplate", "tipFooterMiddleTemplate", "tipFooterRightTemplate"
        ).forEach { name ->
            assertTrue("分享导出未带上 $name", src.contains("exportConfig.$name = shareConfig.$name"))
        }
    }

    /** 默认槽位取值不得改变（新装/升级 = 零变化）。 */
    @Test
    fun defaultSlotValuesUnchanged() {
        val src = code("help/config/ReadBookConfig.kt")
        assertTrue(src.contains("var tipHeaderLeft: Int = ReadTipConfig.time"))
        assertTrue(src.contains("var tipHeaderRight: Int = ReadTipConfig.battery"))
        assertTrue(src.contains("var tipFooterLeft: Int = ReadTipConfig.chapterTitle"))
        assertTrue(src.contains("var tipFooterRight: Int = ReadTipConfig.pageAndTotal"))
    }

    /** 枚举槽位取值仍互不重复（反查无歧义的前提），哨兵不侵入既有区间。 */
    @Test
    fun legacyEnumValuesStayDistinct() {
        val legacy = ReadTipConfig.tipValues.filter { it != ReadTipConfig.custom }
        assertEquals("枚举槽位数量必须仍是 12", 12, legacy.size)
        assertEquals("枚举槽位取值不得重复（否则按值反查有歧义）", 12, legacy.toSet().size)
        assertTrue("哨兵不得落在既有枚举区间内", ReadTipConfig.custom > 11)
        listOf(
            ReadTipConfig.time, ReadTipConfig.battery,
            ReadTipConfig.chapterTitle, ReadTipConfig.pageAndTotal
        ).forEach { value ->
            assertTrue("默认槽位值 $value 必须仍在枚举集合内", legacy.contains(value))
        }
    }
}