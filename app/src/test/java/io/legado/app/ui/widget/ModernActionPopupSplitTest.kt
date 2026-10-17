package io.legado.app.ui.widget

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File

/**
 * 「现代动作弹层」**布局族拆分归属**契约单测（G-38 存量超限拆分配套）。
 *
 * 拆分口径 = 「**测量与定位**」（纯几何：锚点快照 + 面板偏移 + 变换原点 + 宽高估算 + 安全高）与
 * 「**弹层编排 + 内容渲染**」（Compose 运行时）分家 —— 两者职责不同，混在一处才需要 800+ 行。
 *
 * 被钉住的三条不变量（都是拆分器真实会出错的地方）：
 * ①**行数**：两份都 ≤800（否则拆了等于没拆，门禁仍要豁免——本条此前正是靠豁免挂着）；
 * ②**唯一归属**：几何族只在**新文件**里声明，原文件**不得残留**（残留 = 同名顶层与对象成员争用名字解析）；
 * ③**可见性**：拆出的声明必须是顶层 `internal`（`private` 顶层是**文件可见** ⇒ 原文件调用不到，
 *    编译期就会挂；这里显式断言，避免有人"为了干净"改回 private）。
 *
 * 注：几何族用到 `dpToPx()`（依赖 Android `Resources`）⇒ 纯 JVM 无法行为化其数值；
 * 数值正确性由编译期 + 真机弹层行为兜底，本测试只守上述结构不变量（每条带期望值）。
 */
class ModernActionPopupSplitTest {

    private val dir = File("src/main/java/io/legado/app/ui/widget")
    private val keepFile = "ModernActionPopup.kt"
    private val layoutFile = "ModernActionPopupLayout.kt"

    private fun text(name: String) = File(dir, name).readText()

    private fun lines(name: String) = text(name).lines().size

    private val geometryFuns = listOf(
        "calculateAnchorSnapshot", "calculatePanelOffset", "calculateTransformOrigin",
        "estimatePanelWidthPx", "estimatePanelHeightPx"
    )

    private val geometryConstants = listOf(
        "MIN_WIDTH_DP", "MAX_WIDTH_DP", "ROW_HEIGHT_DP", "SLIDER_WIDTH_DP", "SLIDER_ROW_HEIGHT_DP"
    )

    @Test
    fun `两份文件都在且均不超 800 行`() {
        listOf(keepFile, layoutFile).forEach { name ->
            assertTrue("文件缺失：$name", File(dir, name).isFile)
            assertTrue("$name 共 ${lines(name)} 行，超 800（拆了等于没拆）", lines(name) <= 800)
        }
        assertEquals("原文件应从 814 行降到 ≤800", true, lines(keepFile) <= 800)
        assertEquals("新布局文件应有实质内容（≥100 行）", true, lines(layoutFile) >= 100)
    }

    @Test
    fun `几何族只在新文件声明且原文件不得残留`() {
        val keep = text(keepFile)
        val layout = text(layoutFile)
        geometryFuns.forEach { funName ->
            assertTrue("$layoutFile 缺少几何函数 $funName（应拆过来）", layout.contains("internal fun $funName("))
            assertTrue("原文件仍残留 $funName（拆分未清干净 ⇒ 同名顶层与成员争用名字解析）", !keep.contains("fun $funName("))
        }
        assertTrue("安全高扩展函数应拆到新文件", layout.contains("internal fun View.safePopupHostHeight("))
        assertTrue("原文件不得残留安全高扩展", !keep.contains("fun View.safePopupHostHeight("))
    }

    @Test
    fun `宽度与行高常量单源且随几何族迁移`() {
        val keep = text(keepFile)
        val layout = text(layoutFile)
        geometryConstants.forEach { constName ->
            assertEquals(
                "常量 $constName 必须只声明一次（重复声明会让『改一处不生效』）",
                1, Regex("const val $constName\\b").findAll(keep + layout).count()
            )
            assertTrue("$constName 应随几何族迁到 $layoutFile", layout.contains("internal const val $constName"))
        }
    }

    @Test
    fun `锚点快照类型随之迁移且为顶层 internal`() {
        val layout = text(layoutFile)
        val keep = text(keepFile)
        assertTrue("AnchorSnapshot 应为新文件里的顶层 internal data class", layout.contains("internal data class AnchorSnapshot("))
        assertTrue("原文件不得再声明 AnchorSnapshot（否则对象成员遮蔽顶层声明）", !keep.contains("private data class AnchorSnapshot("))
    }

    @Test
    fun `弹层编排与内容渲染仍留在原对象`() {
        val keep = text(keepFile)
        assertTrue("弹层入口对象必须留在原文件", keep.contains("object ModernActionPopup {"))
        assertTrue("滑杆行描述必须留在原文件（对外 API）", keep.contains("data class SliderSpec("))
        assertTrue("动作模型必须留在原文件（对外 API）", keep.contains("data class Action("))
        assertTrue("弹窗生命周期句柄必须留在原文件", keep.contains("class Handle internal constructor("))
        assertTrue("弹层本体 composable 留在原文件", keep.contains("private fun ModernActionPopupOverlay("))
        assertTrue("滑杆行 composable 留在原文件", keep.contains("private fun ModernSliderRow("))
    }
}
