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
    fun listUsesSharedContainerAndRow() {
        // 2026-09-26 收敛：列表容器 → AppManagementLazyColumn（项间距/快速滚动条/导航栏内边距单源），
        // 行间自绘分隔线移除（卡片行间距改由容器承载，与书源管理一致）
        val code = SourceFileProbe.sourceText("ui/book/toc/rule/TxtTocRuleScreen.kt")
        assertTrue("应走管理族列表容器", code.contains("AppManagementLazyColumn("))
        assertFalse("不得再由页内自绘分隔线", code.contains("HorizontalDivider"))
    }

    @Test
    fun dragPitchIsMeasuredNotHardcoded() {
        // 拖拽行节拍必须实测（真实行高 = minHeight + Card 内外边距 + 项间距，且随字体缩放变化），
        // 硬编码 dp 会失配 ⇒ 换序错位（2026-09-26 实测：旧写死 64dp ≠ 真实 88dp）
        val code = SourceFileProbe.sourceText("ui/book/toc/rule/TxtTocRuleScreen.kt")
        assertTrue("须从 layoutInfo 实测行节拍", code.contains("measuredRowPitchPx("))
        assertFalse("不得再写死 64dp/72dp 行节拍", code.contains("64.dp.toPx()") || code.contains("72.dp.toPx()"))
    }
}