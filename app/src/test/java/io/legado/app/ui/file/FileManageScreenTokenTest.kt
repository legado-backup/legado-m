package io.legado.app.ui.file

import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/** B7 R28 取色收口不变量（源码文本断言；依据 theme-consistency-iron-rule K2/K4）。 */
class FileManageScreenTokenTest {

    private fun code(): String {
        val rel = "src/main/java/io/legado/app/ui/file/FileManageScreen.kt"
        val f = listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
        return f.readLines()
            .filterNot { it.trimStart().let { t -> t.startsWith("*") || t.startsWith("//") || t.startsWith("/*") } }
            .joinToString("\n")
    }

    @Test
    fun iconTintUsesFaceToken() {
        val t = code()
        assertTrue("应走 settingPalette().secondaryText", t.contains("settingPalette().secondaryText"))
        assertFalse("不得再用 colorScheme.outline", Regex("colorScheme\\.outline\\b").containsMatchIn(t))
        assertFalse("不得再用 outlineVariant", t.contains("outlineVariant"))
    }

    @Test
    fun listRowUsesSharedManagementRow() {
        // 行组件收敛（2026-09-26）：`FileManageItemRow` 原为自绘裸 Row（56dp / 无 Card / 无圆角），
        // 与「我的」管理族其余列表页观感不一致 ⇒ 必须走共享行 AppManagementListRow
        val t = code()
        assertTrue("行须走管理族唯一行", t.contains("AppManagementListRow("))
        assertFalse("行高不得再由页面自绘（须由共享行 minHeight 单源决定）", t.contains("height(56.dp)"))
        assertTrue("行首图标取色须走面 token accent", t.contains("palette.settings.accent"))
    }
}