package io.legado.app.ui.book.source.manage

import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 行组件收敛（2026-09-26）不变量：书源体检结果行由**自绘裸 `Column` + 自绘 Checkbox**
 * 换装为「我的」管理族唯一行 `AppManagementListRow`（源码文本断言，随 theme-consistency-iron-rule K2/K4）。
 */
class SourceQualityReportRowConvergenceTest {

    private fun code(): String {
        val rel = "src/main/java/io/legado/app/ui/book/source/manage/SourceQualityReportActivity.kt"
        val f = listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
        return f.readLines()
            .filterNot { it.trimStart().let { t -> t.startsWith("*") || t.startsWith("//") || t.startsWith("/*") } }
            .joinToString("\n")
    }

    @Test
    fun reportRowUsesSharedManagementRow() {
        val t = code()
        assertTrue("体检结果行须走管理族唯一行", t.contains("AppManagementListRow("))
        assertFalse(
            "不得再自绘 M3 Checkbox（勾选槽由共享行单源提供）",
            t.contains("CheckboxDefaults")
        )
        assertFalse("不得再用 M3 派生键 outlineVariant", t.contains("outlineVariant"))
    }
}