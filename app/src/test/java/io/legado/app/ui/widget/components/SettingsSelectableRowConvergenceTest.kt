package io.legado.app.ui.widget.components

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 行组件收敛配对测试（用户 2026-09-26 裁定：「同脚手架不同行」必须消除）。
 *
 * 收敛前：`SettingsSelectableRow` 是**自绘裸 `Row`**（固定 72dp 高、无 Card、无圆角、无外边距），
 * 而「我的」下其余管理页统一 `AppManagementScaffold` + `AppManagementListRow`（Miuix Card 家族）。
 *
 * 收敛后：本组件是 `AppManagementListRow` 的**薄壳** —— 视觉/取色/圆角/行距全部由该单源决定，
 * 本组件只做能力位映射（多选 / 开关 / 编辑 / 删除 / 更多 / 拖拽手柄）。
 */
class SettingsSelectableRowConvergenceTest {

    private val rel = "ui/widget/components/SettingsSelectableRow.kt"

    private fun code(): String = SourceFileProbe.rawText(rel)
        .replace(Regex("/\\*[\\s\\S]*?\\*/"), "")
        .lines()
        .filterNot { it.trimStart().startsWith("//") }
        .joinToString("\n")

    @Test
    fun delegatesToSharedRowComponent() {
        val c = code()
        assertTrue("必须转调共享行组件 AppManagementListRow", c.contains("AppManagementListRow("))
        assertTrue(
            "调色板必须走管理页单源 rememberAppManagementPalette",
            c.contains("rememberAppManagementPalette()")
        )
    }

    @Test
    fun alignsWithSourceManageBaselineRow() {
        // 第二批（2026-09-26）：与书源管理基线行（`BookSourceScreen`）逐字对齐——同为 `minHeight` 行高
        // 且**不叠面板纹理图**（`drawPanelImage = false`，书源/订阅源/替换规则同口径）；
        // 行节距不得在薄壳内写死（真实行距 = minHeight + Card 内边距 8×2 + 外边距 4×2 + 项间距 8 = 88dp，
        // 且随字体缩放变化 ⇒ 必须由消费页 `measuredRowPitchPx` 实测）
        val c = code()
        assertTrue("行高须经 minHeight 透传给共享行（与基线同高）", c.contains("minHeight = rowHeight"))
        assertTrue("须与书源管理同口径：不叠面板纹理图", c.contains("drawPanelImage = false"))
        assertFalse(
            "薄壳内不得写死行节距（64/72/88dp 都会与实际行距失配）",
            Regex("\\b(64|72|88)\\.dp\\.toPx\\(\\)").containsMatchIn(c)
        )
    }

    @Test
    fun carriesNoOwnPixelsOrColors() {
        val c = code()
        assertFalse("薄壳不得自带行高（固定 height 会再次制造「不同行」）", c.contains(".height(72.dp)"))
        assertFalse("薄壳不得自带底色（底色由 Card 单源决定）", c.contains(".background("))
        assertFalse("薄壳不得自带内边距", c.contains(".padding("))
        // 取色只允许经 palette，不得出现硬编码色
        assertFalse("不得出现 Color(0x…) 硬编码色", Regex("Color\\(0x").containsMatchIn(c))
    }

    @Test
    fun capabilitySlotsMappedWithoutLoss() {
        val c = code()
        listOf(
            "selected = checked",
            "onToggleSelection = { onToggleSelect(!checked) }",
            "switchChecked = enabled",
            "onSwitchChange = onToggleEnable",
            "onEdit = onEdit",
            "onDelete = onDelete",
            "leadingContent = dragStartIndex"
        ).forEach { marker ->
            assertTrue("能力位映射缺失（会丢功能）：$marker", c.contains(marker))
        }
        assertTrue("拖拽交互须逐字保留（长按拖动 + 结束回调）", c.contains("detectDragGesturesAfterLongPress"))
        assertTrue(c.contains("Icons.Default.DragHandle"))
    }

    @Test
    fun moreActionsConvertedWithBothIconSources() {
        val c = code()
        assertTrue("moreActions 须转为 AppManagementMenuAction", c.contains("AppManagementMenuAction("))
        assertTrue("图标 drawable 源须透传", c.contains("iconRes = action.iconRes"))
        assertTrue("图标 ImageVector 源须透传", c.contains("icon = action.icon"))
    }

    @Test
    fun callSitesAreMyTabSubpagesOnly() {
        // 收敛范围（用户裁定）：仅「我的」下的子页面；书架/发现/订阅栏目页不得改动
        val root = SourceFileProbe.mainJavaRoot()
        listOf(
            "io/legado/app/ui/dict/rule/DictRuleScreen.kt",
            "io/legado/app/ui/book/toc/rule/TxtTocRuleScreen.kt",
            "io/legado/app/ui/autoTask/AutoTaskScreen.kt"
        ).forEach { path ->
            val text = java.io.File(root, path).readText()
            assertTrue("三页须仍复用本组件（不得各自重造行）：$path", text.contains("SettingsSelectableRow("))
        }
    }
}