package io.legado.app.ui.dict.rule

import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/** B7 R28 分隔线取色不变量（源码文本断言；依据 theme-consistency-iron-rule K2/K4）。 */
class DictRuleScreenTokenTest {

    private fun code(): String {
        val rel = "src/main/java/io/legado/app/ui/dict/rule/DictRuleScreen.kt"
        val f = listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
        return f.readLines()
            .filterNot { it.trimStart().let { t -> t.startsWith("*") || t.startsWith("//") || t.startsWith("/*") } }
            .joinToString("\n")
    }

    @Test
    fun dividerUsesDividerToken() {
        val t = code()
        assertTrue("分隔线应走 dividerColor", t.contains("dividerColor"))
        assertFalse("不得再用 M3 派生键 outlineVariant", t.contains("outlineVariant"))
    }

    @Test
    fun listRowPitchMatchesSharedRow() {
        // 行组件收敛（2026-09-26）：行改由 `AppManagementListRow` 单源渲染 ⇒ 拖动换算节拍须同步为 64dp
        // （minHeight 56dp + Card 垂直外边距 4dp×2），否则拖拽换序会错位
        val t = code()
        assertTrue("拖动节拍须与共享行距一致（64dp）", t.contains("64.dp.toPx()"))
        assertFalse("不得残留旧 72dp 行距节拍", t.contains("72.dp.toPx()"))
    }
}