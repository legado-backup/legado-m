package io.legado.app.ui.book.read.page

import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * B3 · R12「阅读页自定义模板槽位渲染」不变量。
 *
 * 需求（spec R12）：
 * - 6 个槽位各自模板独立渲染，**不复用按枚举值反查槽位的 `getTipView`**（多槽位同为 custom 时无法反查）；
 * - 模板由可变信息源（时间 / 电量 / 页码进度）驱动刷新，否则翻页后信息停滞；
 * - **既有枚举路径零影响**（X5 回归风险最小）：11 个枚举别名的 tag 赋值与 `getTipView` 必须保留。
 */
class PageViewCustomTipSlotTest {

    private fun code(relFromMainJava: String): String {
        val rel = "src/main/java/io/legado/app/$relFromMainJava"
        val file = listOf(File(rel), File("../app/$rel"), File("app/$rel")).firstOrNull { it.isFile }
            ?: throw AssertionError("未找到源文件（工作目录=${File(".").absolutePath}）：$rel")
        return file.readLines()
            .filterNot { it.trimStart().startsWith("//") || it.trimStart().startsWith("*") }
            .joinToString("\n")
    }

    /** 自定义槽位走「按槽位」渲染，且仅在槽位值 == custom 时生效。 */
    @Test
    fun customSlotsRenderBySlotNotByEnumLookup() {
        val pv = code("ui/book/read/page/PageView.kt")
        assertTrue(
            "必须按槽位下标判定 custom",
            pv.contains("ReadTipConfig.slotValue(slot) == ReadTipConfig.custom")
        )
        assertTrue(
            "槽位视图表必须覆盖 6 个槽位（页眉左中右 + 页脚左中右）",
            pv.contains("binding.tvHeaderLeft") && pv.contains("binding.tvHeaderMiddle") &&
                pv.contains("binding.tvHeaderRight") && pv.contains("binding.tvFooterLeft") &&
                pv.contains("binding.tvFooterMiddle") && pv.contains("binding.tvFooterRight")
        )
        assertTrue(
            "渲染必须复用全项目唯一占位符引擎",
            pv.contains("ReadTipTemplate.render(") && pv.contains("ReadTipTemplate.values(")
        )
        assertTrue(
            "电量占位符在末尾时才走电量图标分支",
            pv.contains("ReadTipTemplate.batteryIconTrailing(template)")
        )
    }

    /** 三个可变信息源都必须驱动自定义槽位刷新（时间 / 电量 / 页码进度）。 */
    @Test
    fun customTipsRefreshDrivenByMutableSources() {
        val pv = code("ui/book/read/page/PageView.kt")
        assertEquals(
            "upCustomTips() 应出现 4 次：定义 1 次 + upTime/upBattery/setProgress 各 1 次",
            4,
            Regex("upCustomTips\\(\\)").findAll(pv).count()
        )
        assertTrue("配置变更路径（upTipStyle）也必须渲染自定义槽位", pv.contains("renderCustomTipSlot(slot"))
    }

    /** X5 回归保护：既有枚举别名路径（按值反查 + 11 个 tag 赋值）不得被削弱。 */
    @Test
    fun legacyEnumPathPreserved() {
        val pv = code("ui/book/read/page/PageView.kt")
        assertTrue("按枚举值反查槽位的方法必须保留", pv.contains("private fun getTipView(tip: Int)"))
        assertEquals(
            "11 个枚举别名的 tag 赋值不得减少（既有槽位行为不变的前提）",
            11,
            Regex("tag = ReadTipConfig\\.").findAll(pv).count()
        )
        assertTrue(
            "章节标题槽位仍走原路径（标题/高级标题包加载不受影响）",
            pv.contains("getTipView(ReadTipConfig.chapterTitle)")
        )
    }
}