package io.legado.app.ui.adapter

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File

/**
 * 「书源分组配置弹窗」**拆分归属**契约单测（G-38 存量超限拆分配套）。
 *
 * 为什么这类拆分要配一个测试：拆分本身不产生行为，但它有两个可被机检的**归属不变量**，
 * 而历史上这两条都真的出过失守：
 * ①**每份产出文件 ≤800 行**（否则拆了等于没拆、门禁仍要豁免）；
 * ②**每个组件只在唯一一份文件里声明**（拆分器最危险的失败是"块边界切错 ⇒ 同一 composable
 *    在两个文件里各有一份"，编译能过、运行取到的是旧那份 —— 症状是"改了代码没生效"）。
 * 另加一条：宿主与数据模型必须留在**原文件**（调用点零改动的前提）。
 *
 * 注：Compose 面无法在 JVM 行为化（无 Compose 运行时、无 appCtx）⇒ 本测试为**结构契约**，
 * 但每条断言都带**期望值**（不是"存在即可"的弱形态）。UI 正确性由编译期 + 真机 L1/既有 UI 壳测试兜底。
 */
class SourceFolderConfigDialogSplitTest {

    private val dir = File("src/main/java/io/legado/app/ui/adapter")

    private fun lines(name: String) = File(dir, name).readLines().size

    private fun text(name: String) = File(dir, name).readText()

    private val keepFile = "SourceFolderConfigDialog.kt"
    private val partFiles = listOf(
        "SourceFolderConfigPanelParts.kt",
        "SourceFolderConfigOptionParts.kt",
        "SourceFolderConfigRowParts.kt"
    )

    @Test
    fun `四份产出文件都在且均不超 800 行`() {
        (listOf(keepFile) + partFiles).forEach { name ->
            val file = File(dir, name)
            assertTrue("拆分目标文件缺失：$name", file.isFile)
            assertTrue("$name 共 ${lines(name)} 行，超过 800 行阈值（拆了等于没拆）", lines(name) <= 800)
        }
        assertEquals("产出文件数固定为 1 保留 + 3 分片", 4, (listOf(keepFile) + partFiles).size)
    }

    @Test
    fun `宿主与数据模型必须留在原文件`() {
        val keep = text(keepFile)
        assertTrue("数据模型必须留在原文件（同包调用点零改动的前提）", keep.contains("data class SourceFolderConfigValues("))
        assertTrue("弹窗宿主必须留在原文件", keep.contains("class SourceFolderConfigDialog : ComposeDialogFragment()"))
        assertTrue("内容根 composable 必须留在原文件（宿主直接调它）", keep.contains("private fun SourceFolderConfigContent("))
    }

    @Test
    fun `每个组件只在唯一一份文件里声明`() {
        val composables = listOf(
            "SourceFolderConfigPanel", "SourceFolderConfigSection",
            "SourceFolderOptionGrid", "SourceFolderSelectTile",
            "SourceFolderChoicePopupPanel", "SourceFolderChoiceChip",
            "SourceFolderAscendingRow", "SourceFolderSliderRow", "SourceFolderFooterActions"
        )
        val all = (listOf(keepFile) + partFiles).map { it to text(it) }
        composables.forEach { name ->
            val owners = all.filter { (_, body) -> body.contains("fun $name(") }.map { it.first }
            assertEquals("组件 $name 必须恰好在一份文件里声明（多份 = 块边界切错）", 1, owners.size)
            assertTrue("组件 $name 不得留在原文件（否则行数没降下来）", owners.first() != keepFile)
        }
    }

    @Test
    fun `分片按职责分组且互不重复`() {
        val panel = text("SourceFolderConfigPanelParts.kt")
        val option = text("SourceFolderConfigOptionParts.kt")
        val row = text("SourceFolderConfigRowParts.kt")
        // 容器/分区
        assertTrue(panel.contains("fun SourceFolderConfigPanel("))
        assertTrue(panel.contains("fun SourceFolderConfigSection("))
        // 选项网格/磁贴/选择面板
        assertTrue(option.contains("fun SourceFolderOptionGrid("))
        assertTrue(option.contains("fun SourceFolderSelectTile("))
        assertTrue(option.contains("fun SourceFolderChoicePopupPanel("))
        assertTrue(option.contains("fun SourceFolderChoiceChip("))
        // 排序/滑杆/页脚动作
        assertTrue(row.contains("fun SourceFolderAscendingRow("))
        assertTrue(row.contains("fun SourceFolderSliderRow("))
        assertTrue(row.contains("fun SourceFolderFooterActions("))
        // 三份分片各自都必须带 package 行（漏它 ⇒ 声明落入默认包 ⇒ 全模块级联 Unresolved）
        listOf(panel, option, row).forEach { body ->
            assertTrue("分片缺少 package 行", body.trimStart().startsWith("package io.legado.app.ui.adapter"))
        }
    }
}
