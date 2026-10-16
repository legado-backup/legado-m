package io.legado.app.ui.dict.rule

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 顶栏包 §1.2 路径 B：`DictRuleScreen` 的 `MenuAction → AppManagementMenuAction` 转换必须透传
 * **图标双源**（`icon` / `iconRes`）。漏传 ⇒ 溢出条目（导入/导出/拷贝/粘贴/帮助等）**静默无图标**
 * （2026-09-25 实测缺口：这几页溢出条目用的是 ImageVector 源）。
 */
class DictRuleOverflowIconResTest {

    @Test
    fun transformPassesBothIconSources() {
        val rel = "ui/dict/rule/DictRuleScreen.kt"
        val code = SourceFileProbe.sourceText(rel)
        assertTrue("转换点必须透传 drawable 源", code.contains("iconRes = menuAction.iconRes,"))
        assertTrue("转换点必须透传 ImageVector 源", code.contains("icon = menuAction.icon,"))
        assertTrue("一级路径既有透传不得被回退", code.contains("iconRes = action.iconRes,"))
        assertTrue(
            "透传点须带用途注释（防后人「清理无用参数」误删）",
            SourceFileProbe.rawText(rel).contains("图标双源同链透传")
        )
    }

    /**
     * 批 7 死码收口：`DictRuleViewModel.upSortNumber()` 全仓零调用（原为零引用分诊「无契约」档），
     * 其职责（按新顺序重排 `sortNumber` 并持久化）已由 `DictRuleActivity.commitOrder` 覆盖
     * —— 后者是拖拽排序结束的唯一入口，且带 `size`/顺序一致性守卫（活方更完备）⇒ 判 A 档退役。
     * 双侧断言：死判据不得回潮 + 活替代必须健在（只证一侧防不住误伤活方，B25 实证）。
     */
    @Test
    fun retiredUpSortNumberStaysRemovedAndLiveCommitOrderKeeps() {
        assertFalse(
            "死判据不得回潮",
            SourceFileProbe.sourceText("ui/dict/rule/DictRuleViewModel.kt").contains("fun upSortNumber(")
        )
        val activity = SourceFileProbe.sourceText("ui/dict/rule/DictRuleActivity.kt")
        assertTrue("活替代 commitOrder 必须健在", activity.contains("fun commitOrder("))
        assertTrue("活替代须写回 sortNumber", activity.contains("sortNumber = index + 1"))
    }
}