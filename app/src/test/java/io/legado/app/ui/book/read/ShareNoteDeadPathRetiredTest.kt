package io.legado.app.ui.book.read

import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * B15 批死码清理（被活等价实现取代 ⇒ 删除）：划词「分享笔记」链路旧实现整套退役 ——
 * `ReadBookActivity.showShareNoteTemplateDialog` + `shareSelectionAsNoteImage` + 整文件
 * `ShareNoteTemplateSelectDialog.kt` + 随之孤儿的 `ShareNoteImageRenderer.renderShareImage`
 * （自建 WebView 的旧渲染入口）。
 *
 * 为何是"被取代"而非"漏接线"：活链路 `showShareNotePreviewOverlay`（划词菜单直接调用）承载
 * `ShareNotePreviewOverlay`，后者**自带**模板选择面板（`ShareNoteTemplatePanel`/`selectTemplate`/
 * `openTemplateManage`）与挂载式渲染（`renderMountedWebView`）⇒ 旧实现的全部能力都在，且更全。
 *
 * 断言缝说明：均为 Activity/WebView 渲染路径，纯 JVM 不可行为化 ⇒ 源码探针守护（已按 G-42 exception 登记含理由）。
 */
class ShareNoteDeadPathRetiredTest {

    @Test
    fun deadShareNotePathStaysDeleted() {
        val activity = code("src/main/java/io/legado/app/ui/book/read/ReadBookActivity.kt")
        assertFalse("旧模板选择入口不得回潮", activity.contains("showShareNoteTemplateDialog"))
        assertFalse("旧即时分享实现不得回潮", activity.contains("fun shareSelectionAsNoteImage("))
        val renderer = code("src/main/java/io/legado/app/ui/book/read/ShareNoteImageRenderer.kt")
        assertFalse("孤儿的自建 WebView 渲染入口不得回潮", renderer.contains("fun renderShareImage("))
        // B29 **更正**（2026-10-16）：`exportMountedWebView` 一度被按「被取代」退役，复核证明**误判** ——
        // 活路径 `renderHtmlToPngFileWithFallback` **必然先加载模板 HTML**（入参含 entry/payload），
        // 与本函数「不重载、直接导出当前已挂载视图」属**不同语义** ⇒ 无「同语义活替代」⇒ 应**保留**。
        // 本断言为该结论的永久防回退（禁止再当死码删）。
        assertTrue(
            "「仅导出已挂载视图」的低层入口须保留（未接线 / 无同语义替代，禁止当死码删）",
            renderer.contains("fun exportMountedWebView(")
        )
    }

    @Test
    fun liveOverlaySingleSourceRemainsTheOnlyPath() {
        val activity = code("src/main/java/io/legado/app/ui/book/read/ReadBookActivity.kt")
        assertTrue("活链路须仍在（划词 → 预览浮层）", activity.contains("showShareNotePreviewOverlay"))
        assertTrue("预览浮层须仍是承接方", activity.contains("ShareNotePreviewOverlay.show("))
        val overlay = code("src/main/java/io/legado/app/ui/book/read/ShareNotePreviewOverlay.kt")
        assertTrue("模板选择能力须由浮层自带（不依赖已删弹窗）", overlay.contains("ShareNoteTemplatePanel"))
        assertTrue("渲染须走挂载式单源", overlay.contains("ShareNoteImageRenderer.renderMountedWebView"))
    }

    private fun code(rel: String): String =
        listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
            .readText().replace("\r\n", "\n")
}
