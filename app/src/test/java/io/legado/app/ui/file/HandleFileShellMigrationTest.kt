package io.legado.app.ui.file

import io.legado.app.testkit.SourceFileProbe
import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * CE-b：`HandleFileActivity` 换装的 **CB-1 结构不变量**（配对测试，JVM 可跑）。
 *
 * 该页共用 `activity_translucence` 透明壳（与 `ui/association` 的 4 个宿主同一批），换装后骨架来自
 * `TransparentShellViews` 共享装配；本页**只挂壳、不接线卡槽**（原 XML 两卡槽恒 gone）。
 *
 * 本测试锁死三类事实：
 *  ①单源装配（composeShell + attachComposeContent 共享装配），不再手写 ComposeView / viewBinding / 引用 R.layout
 *  ②XML 已退役（`activity_translucence.xml` 不存在）
 *  ③宿主业务逻辑未因换装消失（模式分派、系统选择器与权限回退、弹框托管）
 */
class HandleFileShellMigrationTest {

    private val page = "ui/file/HandleFileActivity.kt"

    private fun src(): String = SourceFileProbe.sourceText(page)

    @Test
    fun singleSourceAssemblyAndNoLegacyBinding() {
        val s = src()
        assertTrue("必须经 composeShell 创建合成壳", s.contains("composeShell(this)"))
        assertTrue("必须装配共享透明壳", s.contains("shell.install(binding.root)"))
        assertTrue(
            "必须复用共享装配（与 association 包 4 个宿主同一单源）",
            s.contains("private val shell by lazy { TransparentShellViews(this) }")
        )
        assertFalse("禁止手写 ComposeView 装配", s.contains("ComposeView("))
        assertFalse("禁止自行设置合成策略", s.contains("ViewCompositionStrategy"))
        assertFalse("换装后不得再走 viewBinding 委托", s.contains("viewBinding("))
        assertFalse("换装后不得再引用已退役布局", s.contains("ActivityTranslucenceBinding"))
    }

    @Test
    fun xmlIsRetired() {
        assertFalse(
            "activity_translucence.xml 应已退役（CE-b）",
            File(SourceFileProbe.layoutDir(), "activity_translucence.xml").exists()
        )
    }

    @Test
    fun slotStaysUntouched() {
        val s = src()
        assertFalse(
            "本页不接线卡槽（原 XML 里两卡槽恒 gone ⇒ 零占位）",
            s.contains("shell.resultCard") || s.contains("shell.importProgress")
        )
        assertFalse("本页不需要 loading 显隐（选择器为系统页）", s.contains("shell.rotateLoading"))
    }

    @Test
    fun hostLogicPreserved() {
        val s = src()
        listOf(
            "override fun onActivityCreated(",
            "private fun showInputDirectoryDialog(",
            "private fun showInputImgSrcDialog(",
            "private val selectDocTree =",
            "private val selectDoc =",
            "private val selectImage =",
        ).forEach { marker ->
            assertTrue("换装不得删改宿主逻辑：缺少 `$marker`", s.contains(marker))
        }
        // 三模式分派与系统选择器失败回退链（换装不得带掉）
        listOf(
            "HandleFileContract.DIR_SYS -> getDirActions(true)",
            "HandleFileContract.DIR -> getDirActions()",
            "HandleFileContract.FILE -> getFileActions()",
            "HandleFileContract.IMAGE -> getImageActions()",
            "selectDocTree.launch()",
            "selectDoc.launch(typesOfExtensions(allowExtensions))",
            "selectImage.launch()",
            "showComposeActionListDialog(",
        ).forEach { marker ->
            assertTrue("选择器/分派链不得缺失：`$marker`", s.contains(marker))
        }
        assertFalse("原 View alert 弹框已由 Compose 托管替代", s.contains("MaterialAlertDialogBuilder"))
    }
}