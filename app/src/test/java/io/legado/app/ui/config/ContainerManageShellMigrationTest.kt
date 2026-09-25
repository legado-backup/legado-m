package io.legado.app.ui.config

import io.legado.app.testkit.SourceFileProbe
import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * CE-b：S3 容器管理页（`activity_s3_container_manage`）换装的 **CB-1 结构不变量**（配对测试，JVM 可跑）。
 *
 * 背景：原 XML = `LinearLayout`（`TitleBar@title_bar` + `tv_summary` + `RecyclerView` + `btn_add`），
 * 两个宿主（`S3ContainerManageActivity` / `LibraryContainerManageActivity`）**共用同一布局**，
 * 且都在 `initComposeContent()` 里 `binding.root.removeAllViews()` 后手拼 `ComposeView`
 * ⇒ 纯「清壳」页，换装只做「运行时清壳 → 合成壳单源」。
 */
class ContainerManageShellMigrationTest {

    private val hosts = listOf(
        "ui/config/S3ContainerManageActivity.kt",
        "ui/config/LibraryContainerManageActivity.kt",
    )

    private fun src(rel: String): String = SourceFileProbe.sourceText(rel)

    @Test
    fun everyHostUsesSingleSourceShell() {
        hosts.forEach { rel ->
            val s = src(rel)
            assertTrue("$rel 必须经 composeShell 创建合成壳", s.contains("composeShell(this)"))
            assertTrue("$rel 必须走 attachComposeContent 单源挂载", s.contains("binding.root.attachComposeContent {"))
            assertFalse("$rel 禁止手写 ComposeView 装配", s.contains("ComposeView("))
            assertFalse("$rel 禁止自行设置合成策略", s.contains("ViewCompositionStrategy"))
            assertFalse("$rel 原来「先清空 root 再手拼」的装配必须消失", s.contains("container.removeAllViews()"))
            assertFalse("$rel 换装后不得再走 viewBinding 委托", s.contains("viewBinding("))
            assertFalse("$rel 换装后不得再引用已退役布局", s.contains("ActivityS3ContainerManageBinding"))
        }
    }

    @Test
    fun xmlIsRetired() {
        assertFalse(
            "activity_s3_container_manage.xml 应已退役（CE-b，两个宿主共用）",
            File(SourceFileProbe.layoutDir(), "activity_s3_container_manage.xml").exists()
        )
    }

    @Test
    fun hostLogicPreserved() {
        val s3 = src(hosts[0])
        listOf(
            "override fun onActivityCreated(",
            "override fun manageBackgroundAlphaEnabled(",
            "private fun reload(",
            "private fun showEditDialog(",
            "private fun containerActions(",
            "private fun confirmDelete(",
            "private fun testConnection(",
            "private fun refreshCapacity(",
            "override fun onDestroy(",
        ).forEach { marker ->
            assertTrue("S3 容器页换装不得删改宿主逻辑：缺少 `$marker`", s3.contains(marker))
        }
        assertTrue("容量换算口径必须保留", s3.contains("internal fun mbToBytes("))

        val library = src(hosts[1])
        listOf(
            "override fun onActivityCreated(",
            "override fun manageBackgroundAlphaEnabled(",
            "private fun reload(",
            "private fun pageMenuActions(",
            "private fun containerActions(",
            "private fun handleImportText(",
            "private fun showExportResult(",
            "private fun confirmDelete(",
            "override fun onDestroy(",
        ).forEach { marker ->
            assertTrue("书库容器页换装不得删改宿主逻辑：缺少 `$marker`", library.contains(marker))
        }
    }
}