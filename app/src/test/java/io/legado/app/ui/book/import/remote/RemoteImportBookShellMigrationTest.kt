package io.legado.app.ui.book.import.remote

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * CE-b：网络导入页宿主侧的**换装不变量**（配对测试，JVM 可跑）。
 *
 * 本页与本地导入页共用 `activity_import_book.xml`（同继承 [io.legado.app.ui.book.import.BaseImportBookActivity]）；
 * CE-b 退役该 XML 并把装配下沉基类单源。本测试只锁**本页特有**的事实（WebDAV/远程目录/权限拒绝分支），
 * 防「共用布局退役时网络分支被静默破坏」。
 */
class RemoteImportBookShellMigrationTest {

    private val page = "ui/book/import/remote/RemoteBookActivity.kt"

    private fun src(): String = SourceFileProbe.sourceText(page)

    @Test
    fun usesSharedScaffoldFromBase() {
        val s = src()
        assertTrue("必须改用基类单源工厂", s.contains("installImportBookContent {"))
        assertTrue("底栏配置必须走基类字段", s.contains("selectActionBar.setMainActionText("))
        assertFalse("不得再引用已退役 binding", s.contains("binding.selectActionBar") || s.contains("binding.composeHost"))
    }

    @Test
    fun remoteSpecificSemanticsPreserved() {
        val s = src()
        listOf(
            "R.drawable.ic_refresh_black_24dp", // 刷新一级图标（topbar-icon-semantics-fix 3.3）
            "R.string.add_to_bookshelf",
            "R.string.select_book_folder",
            "showHelp(\"webDavBookHelp\")",
            "LocalConfig.webDavBookHelpVersionIsLast",
        ).forEach { marker ->
            assertTrue("换装不得删改宿主菜单/文案：缺少 `$marker`", s.contains(marker))
        }
        listOf(
            "override fun onActivityCreated(",
            "override fun observeLiveBus(",
            "private fun initSelectActionBar(",
            "private fun initComposeHost(",
            "private fun buildMenuActions(",
            "fun openDir(",
            "fun upCountView(",
            "override fun onDialogDismiss(",
            "override fun onSearchTextChange(",
            "private fun showRemoteBookDownloadAlert(",
        ).forEach { marker ->
            assertTrue("换装不得删改宿主逻辑：缺少 `$marker`", s.contains(marker))
        }
    }
}