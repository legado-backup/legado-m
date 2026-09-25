package io.legado.app.ui.book.import.local

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * CE-b：本地导入页宿主侧的**换装不变量**（配对测试，JVM 可跑）。
 *
 * 本页是 `activity_import_book.xml` 的两个使用者之一（另一个是 `RemoteBookActivity`）；CE-b 把
 * 「合成壳 + Compose 主内容 + 程序化 `SelectActionBar` 底栏」下沉到基类 [BaseImportBookActivity] 单源。
 * 本测试只锁**本页特有**的事实，防「下沉时把本地分支的菜单/多选/目录扫描逻辑丢了」。
 */
class LocalImportBookShellMigrationTest {

    private val page = "ui/book/import/local/ImportBookActivity.kt"

    private fun src(): String = SourceFileProbe.sourceText(page)

    @Test
    fun usesSharedScaffoldFromBase() {
        val s = src()
        assertTrue("必须改用基类单源工厂", s.contains("installImportBookContent {"))
        assertTrue("底栏配置必须走基类字段", s.contains("selectActionBar.setMainActionText("))
        assertFalse("不得再引用已退役 binding", s.contains("binding.selectActionBar") || s.contains("binding.composeHost"))
    }

    @Test
    fun localMenuAndSelectionSemanticsPreserved() {
        val s = src()
        listOf(
            "R.drawable.ic_folder_open", // 选目录一级图标（topbar-icon-semantics-fix 3.3）
            "R.string.sort_by_name",
            "R.string.sort_by_size",
            "R.string.sort_by_time",
            "R.string.scan_folder",
            "R.string.import_file_name",
            "R.menu.import_book_sel",
            "R.id.menu_del_selection",
            "R.string.add_to_bookshelf",
            "R.string.empty_msg_import_book",
        ).forEach { marker ->
            assertTrue("换装不得删改宿主菜单/文案：缺少 `$marker`", s.contains(marker))
        }
        listOf(
            "override fun onActivityCreated(",
            "private fun initSelectActionBar(",
            "private fun initComposeHost(",
            "private fun buildMenuActions(",
            "private fun onItemClick(",
            "private fun toggleSelect(",
            "override fun selectAll(",
            "override fun revertSelection(",
            "override fun onClickSelectBarMainAction(",
            "private fun deleteSelection(",
            "private fun initData(",
            "private fun refreshComposeItems(",
            "private fun buildPath(",
            "private fun initRootDoc(",
            "private fun scanFolder(",
            "private fun alertImportFileName(",
            "private fun goBackDir(",
            "fun startRead(",
        ).forEach { marker ->
            assertTrue("换装不得删改宿主逻辑：缺少 `$marker`", s.contains(marker))
        }
    }
}