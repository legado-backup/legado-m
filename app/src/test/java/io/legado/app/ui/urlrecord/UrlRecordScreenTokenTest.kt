package io.legado.app.ui.urlrecord

import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 行/壳/容器「三件套」收敛不变量（源码文本断言；依据 theme-consistency-iron-rule K2/K4 与
 * 2026-09-26 用户裁定「我的子页/子子页必须同脚手架同行」）。
 */
class UrlRecordScreenTokenTest {

    private fun code(): String {
        val rel = "src/main/java/io/legado/app/ui/urlrecord/UrlRecordScreen.kt"
        val f = listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
        return f.readLines()
            .filterNot { it.trimStart().let { t -> t.startsWith("*") || t.startsWith("//") || t.startsWith("/*") } }
            .joinToString("\n")
    }

    @Test
    fun shellRowAndContainerConverged() {
        // 2026-09-26 收敛：壳层（自绘顶栏/搜索栏/私有溢出菜单）→ AppManagementScaffold；
        // 行 → AppManagementListRow；容器 → AppManagementLazyColumn（项间距/快速滚动条单源）；
        // 行间自绘分隔线清零
        val t = code()
        assertTrue("壳层须改用管理族 AppManagementScaffold", t.contains("AppManagementScaffold("))
        assertTrue("行须走管理族唯一行", t.contains("AppManagementListRow("))
        assertTrue("列表须走管理族容器", t.contains("AppManagementLazyColumn("))
        assertTrue("搜索槽须由壳承载", t.contains("searchQuery = searchKey"))
        assertFalse("不得残留页内自绘顶栏", t.contains("GlassTopAppBar("))
        assertFalse("不得残留页内自绘搜索栏", t.contains("SettingsSearchBar("))
        assertFalse("不得再由页内自绘分隔线", t.contains("HorizontalDivider"))
        assertFalse("不得再用 M3 派生键 outlineVariant", t.contains("outlineVariant"))
    }
}