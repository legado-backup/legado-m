package io.legado.app.ui.widget.components

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 顶栏包 §1.2（2026-09-25）：`MenuAction` **图标双源全链透传**契约（JVM 可跑）。
 *
 * 实测缺口：`MenuAction` 声明了双源（`icon: ImageVector?` / `iconRes: Int?`），但
 * `AppDropdownMenu` 渲染条目时**只传 `leadingIcon = action.icon`** ⇒ iconRes-only 动作
 * 在溢出菜单里**静默无图标**（顶栏一级路径 `AppManagementScaffold` 已正确，缺口只在溢出路径）。
 *
 * 本测试锁死四件事：
 *   ①`MenuAction` 必须保持双源字段（icon 与 iconRes 都是可选）
 *   ②`AppDropdownMenu` 必须**同时**透传两个源（缺一即回归）
 *   ③顶层 drop-in 缺口的守护：不得出现「只传 icon 不传 iconRes」的老写法
 *   ④一级路径（`AppManagementScaffold`）不得被本批误改（它已正确，是回归对照基线）
 */
class MenuActionIconResPassthroughTest {

    private val dropdownPage = "ui/widget/components/AppDropdownMenu.kt"
    private val sheetPage = "ui/widget/components/AppMenuSheet.kt"

    private fun dropdown(): String = SourceFileProbe.sourceText(dropdownPage)
    private fun sheet(): String = SourceFileProbe.sourceText(sheetPage)

    /** 注释/KDoc 断言专用：`sourceText` 会剥掉 `//` 行与 KDoc 星号行 ⇒ 须用原文（§8-⑤）。 */
    private fun rawDropdown(): String = SourceFileProbe.rawText(dropdownPage)
    private fun rawSheet(): String = SourceFileProbe.rawText(sheetPage)

    @Test
    fun menuActionKeepsDualIconSource() {
        val s = sheet()
        assertTrue("MenuAction 必须保留 ImageVector 源", s.contains("val icon: ImageVector? = null"))
        assertTrue("MenuAction 必须保留 drawable 资源源", s.contains("val iconRes: Int? = null"))
        assertTrue(
            "双源关系须在 KDoc 写明（icon 优先），否则后人易误删其一",
            rawSheet().contains("双源二选一，icon 优先")
        )
    }

    @Test
    fun dropdownPassesBothIconSources() {
        val s = dropdown()
        assertTrue("必须仍透传 ImageVector 源", s.contains("leadingIcon = action.icon,"))
        assertTrue(
            "必须补透传 drawable 资源源（否则 iconRes-only 动作静默无图标）",
            s.contains("leadingIconRes = action.iconRes,")
        )
        assertTrue(
            "透传点须带用途注释（防后人「清理无用参数」时误删）",
            rawDropdown().contains("iconRes-only 动作在溢出菜单里静默无图标")
        )
    }

    @Test
    fun noLegacyIconOnlyCallRemains() {
        val s = dropdown()
        // 老写法（只传 icon、紧跟 tint）不得残留 —— 同时出现两者即为「新分支已接但调用点没跟上」
        assertFalse(
            "不得残留「leadingIcon = action.icon, 紧接 tint = action.tint」的老写法",
            s.contains("leadingIcon = action.icon,\n                    tint = action.tint")
        )
        assertTrue("条目渲染必须显式走 start 对齐（AppDropdownMenu 既有口径）", s.contains("textAlign = TextAlign.Start"))
    }

    @Test
    fun firstLevelIconPathUntouched() {
        // 回归对照：一级路径（AppManagementScaffold，位于 ui/widget/compose）本来就透传 iconRes，
        // 本批**不得改它** —— 它也是「icon 优先、fallback iconRes」这条口径的既有基线
        val scaffold = SourceFileProbe.sourceText("ui/widget/compose/AppManagementScaffold.kt")
        assertTrue(
            "一级路径必须仍在使用 iconRes（本批的「已正确」基线）",
            scaffold.contains("val iconRes: Int? = null")
        )
        assertTrue(
            "一级路径必须仍声明 icon 优先 / fallback iconRes 的语义",
            SourceFileProbe.rawText("ui/widget/compose/AppManagementScaffold.kt").contains("fallback iconRes")
        )
    }
}