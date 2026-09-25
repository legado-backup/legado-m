package io.legado.app.ui.highlight

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 顶栏包 §1.2 路径 B：`HighlightRuleScreen` 的 `MenuAction → AppManagementMenuAction` 转换必须透传
 * **图标双源**（`icon` / `iconRes`）。
 */
class HighlightRuleOverflowIconResTest {

    @Test
    fun transformPassesBothIconSources() {
        val rel = "ui/highlight/HighlightRuleScreen.kt"
        val code = SourceFileProbe.sourceText(rel)
        assertTrue("转换点必须透传 drawable 源", code.contains("iconRes = menuAction.iconRes,"))
        assertTrue("转换点必须透传 ImageVector 源", code.contains("icon = menuAction.icon,"))
        assertTrue(
            "透传点须带用途注释（防后人「清理无用参数」误删）",
            SourceFileProbe.rawText(rel).contains("图标双源同链透传")
        )
    }
}