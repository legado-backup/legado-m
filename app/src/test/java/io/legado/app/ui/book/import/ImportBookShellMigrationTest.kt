package io.legado.app.ui.book.import

import io.legado.app.testkit.SourceFileProbe
import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * CE-b「本地/网络导入页」换装的**基类结构不变量**（配对测试，JVM 可跑）。
 *
 * 背景：`activity_import_book.xml` 由 **两个** Activity 共用（`ImportBookActivity` 本地导入 /
 * `RemoteBookActivity` 网络导入，均继承 [BaseImportBookActivity]），壳结构为
 * `compose_host`(ComposeView，`0dp` 底边约束到 `select_action_bar` 之上) + `SelectActionBar`(View 多选底栏)。
 * CE-b 把「合成壳 + Compose 主内容 + 程序化底栏」下沉到基类**单源**，页面 XML 随之退役。
 *
 * 本测试锁死四类事实，防回归（只写文档的约束一律失效）：
 *   ①单源装配（composeShell + attachComposeContent + 基类 `installImportBookContent`），且不再引用已退役 binding
 *   ②XML 已退役（`activity_import_book.xml` 不存在）
 *   ③底栏必须是 **Activity 字段 `by lazy`**（组合晚于 `onActivityCreated`，工厂内创建会让宿主配置扑空）
 *   ④两个宿主类均**改用基类单源**，且宿主业务逻辑未消失
 */
class ImportBookShellMigrationTest {

    private fun base(): String = SourceFileProbe.sourceText("ui/book/import/BaseImportBookActivity.kt")

    @Test
    fun baseSingleSourceAssembly() {
        val s = base()
        assertTrue("基类必须经 composeShell 创建合成壳", s.contains("composeShell(this)"))
        assertTrue("基类必须走 attachComposeContent 单源挂载", s.contains("binding.root.attachComposeContent {"))
        assertTrue("主内容 + 底栏必须收敛到基类单源工厂", s.contains("fun installImportBookContent("))
        assertFalse("换装后不得再走 viewBinding 委托", s.contains("viewBinding("))
        assertFalse("换装后不得再引用已退役布局", s.contains("ActivityImportBookBinding"))
    }

    @Test
    fun selectActionBarIsActivityFieldNotFactoryLocal() {
        val s = base()
        assertTrue(
            "底栏必须是 Activity 字段（by lazy）——工厂内创建会让 onActivityCreated 的配置扑空",
            Regex("""val selectActionBar\s*:\s*SelectActionBar\s+by lazy""").containsMatchIn(s)
        )
        assertTrue("底栏必须以 AndroidView 挂载", s.contains("AndroidView(factory = { selectActionBar })"))
        // 原 XML 的 ConstraintLayout 语义（底栏贴底、主内容占其余高度）由 Column + weight(1f) 等价承担
        assertTrue("主内容必须用 weight(1f) 占其余高度", s.contains("Modifier.weight(1f)"))
    }

    @Test
    fun xmlIsRetired() {
        val f = File(SourceFileProbe.layoutDir(), "activity_import_book.xml")
        assertFalse("activity_import_book.xml 应已退役（CE-b）", f.exists())
    }

    @Test
    fun bothHostsUseSharedSingleSource() {
        listOf(
            "ui/book/import/local/ImportBookActivity.kt" to "ui/book/import/local",
            "ui/book/import/remote/RemoteBookActivity.kt" to "ui/book/import/remote",
        ).forEach { (page, _) ->
            val s = SourceFileProbe.sourceText(page)
            assertTrue("$page 必须改用基类单源工厂", s.contains("installImportBookContent {"))
            assertTrue("$page 必须改用基类底栏字段", s.contains("selectActionBar."))
            assertFalse("$page 不得再引用已退役 binding.composeHost", s.contains("binding.composeHost"))
            assertFalse("$page 不得再引用已退役 binding.selectActionBar", s.contains("binding.selectActionBar"))
            assertTrue("$page 必须保留 onActivityCreated", s.contains("override fun onActivityCreated("))
            assertTrue("$page 必须保留 initSelectActionBar", s.contains("private fun initSelectActionBar("))
            assertTrue("$page 必须保留 initComposeHost", s.contains("private fun initComposeHost("))
            assertTrue("$page 必须保留 upCountView", s.contains("fun upCountView()"))
            assertTrue("$page 必须保留空态文案/多选口径", s.contains("checkableCount()"))
        }
    }
}