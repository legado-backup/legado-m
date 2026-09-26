package io.legado.app.ui.book.toc.rule

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertFalse
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

    @Test
    fun listRowPitchMatchesSharedRow() {
        // 行组件收敛（2026-09-26）：行改由 `AppManagementListRow` 单源渲染 ⇒ 拖动换算节拍须同步为 64dp
        // （minHeight 56dp + Card 垂直外边距 4dp×2），否则拖拽换序会错位
        val code = SourceFileProbe.sourceText("ui/book/toc/rule/TxtTocRuleScreen.kt")
        assertTrue("拖动节拍须与共享行距一致（64dp）", code.contains("64.dp.toPx()"))
        assertFalse("不得残留旧 72dp 行距节拍", code.contains("72.dp.toPx()"))
    }
}