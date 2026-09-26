package io.legado.app.ui.dict.rule

import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 行/容器收敛不变量（源码文本断言；依据 theme-consistency-iron-rule K2/K4 与 2026-09-26 用户裁定
 * 「我的」管理族列表必须同脚手架同行）。
 */
class DictRuleScreenTokenTest {

    private fun code(): String {
        val rel = "src/main/java/io/legado/app/ui/dict/rule/DictRuleScreen.kt"
        val f = listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
        return f.readLines()
            .filterNot { it.trimStart().let { t -> t.startsWith("*") || t.startsWith("//") || t.startsWith("/*") } }
            .joinToString("\n")
    }

    @Test
    fun listUsesSharedContainerAndRow() {
        // 2026-09-26 收敛：列表容器 → AppManagementLazyColumn（项间距/快速滚动条/导航栏内边距单源），
        // 行间自绘分隔线移除（卡片行间距改由容器承载，与书源管理一致）
        val t = code()
        assertTrue("应走管理族列表容器", t.contains("AppManagementLazyColumn("))
        assertFalse("不得再由页内自绘分隔线", t.contains("HorizontalDivider"))
        assertFalse("不得再用 M3 派生键 outlineVariant", t.contains("outlineVariant"))
    }

    @Test
    fun dragPitchIsMeasuredNotHardcoded() {
        // 拖拽行节拍必须实测（真实行高 = minHeight + Card 内外边距 + 项间距，且随字体缩放变化），
        // 硬编码 dp 会失配 ⇒ 换序错位（2026-09-26 实测：旧写死 64dp ≠ 真实 88dp）
        val t = code()
        assertTrue("须从 layoutInfo 实测行节拍", t.contains("measuredRowPitchPx("))
        assertFalse("不得再写死 64dp/72dp 行节拍", t.contains("64.dp.toPx()") || t.contains("72.dp.toPx()"))
    }
}