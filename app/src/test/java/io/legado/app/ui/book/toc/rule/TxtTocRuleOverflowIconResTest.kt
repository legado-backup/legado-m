package io.legado.app.ui.book.toc.rule

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 顶栏包 §1.2 路径 B：`TxtTocRuleScreen` 的 `MenuAction → AppManagementMenuAction` 转换必须透传
 * **图标双源**（`icon` / `iconRes`）。与 `DictRuleScreen` 同构（同批交付），漏传 ⇒ 溢出条目静默无图标。
 */
class TxtTocRuleOverflowIconResTest {

    @Test
    fun transformPassesBothIconSources() {
        val rel = "ui/book/toc/rule/TxtTocRuleScreen.kt"
        val code = SourceFileProbe.sourceText(rel)
        assertTrue("转换点必须透传 drawable 源", code.contains("iconRes = menuAction.iconRes,"))
        assertTrue("转换点必须透传 ImageVector 源", code.contains("icon = menuAction.icon,"))
        assertTrue("一级路径既有透传不得被回退", code.contains("iconRes = action.iconRes,"))
        assertTrue(
            "透传点须带用途注释（防后人「清理无用参数」误删）",
            SourceFileProbe.rawText(rel).contains("图标双源同链透传")
        )
    }
}