package io.legado.app.ui.book.storage

import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 行/容器收敛不变量（源码文本断言；依据 theme-consistency-iron-rule K2/K4 与 2026-09-26
 * 用户裁定「我的」管理族列表必须同脚手架同行）。
 */
class StorageManageScreenTokenTest {

    private fun code(): String {
        val rel = "src/main/java/io/legado/app/ui/book/storage/StorageManageScreen.kt"
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
    fun listRowUsesSharedManagementRow() {
        // 行组件收敛（2026-09-26）：分项存储行由另一行族 SettingsClickRow → 管理族唯一行
        // AppManagementListRow（消除「同脚手架不同行」），行尾取色一并收口到面 token accent
        val t = code()
        assertTrue("行须走管理族唯一行", t.contains("AppManagementListRow("))
        assertFalse("不得再用另一行族 SettingsClickRow", t.contains("SettingsClickRow("))
        assertFalse(
            "行尾取色不得再用 M3 派生键 primary",
            Regex("colorScheme\\.primary\\b").containsMatchIn(t)
        )
    }
}