package io.legado.app.ui.adapter

import io.legado.app.testkit.SourceFileProbe
import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * CF 6.2 死件退役配对测试（书源/订阅源文件夹视图）。
 *
 * 背景（实测取证 2026-09-26）：`SourceFolderAdapter` 原是 View 层 `RecyclerAdapter`
 * （inflate `item_source_folder_grid`），但宿主 `RssFragment` 的文件夹目录早已改用 Compose 网格
 * （`SourceFolderComposeGrid`）⇒ Adapter 实例再未被创建，`item_source_folder_grid` 随之成为死布局。
 * 现收窄为 `object`，仅保留外部仍引用的契约与工具（`CallBack` / `calculateSpanCount` / `spacingPx`）。
 */
class SourceFolderAdapterRetiredTest {

    private fun mainJava(rel: String): File =
        File(SourceFileProbe.mainJavaRoot(), "io/legado/app/$rel")

    @Test
    fun deadItemLayoutIsGone() {
        assertFalse(
            "死 item 布局应已退役：item_source_folder_grid.xml",
            File(SourceFileProbe.layoutDir(), "item_source_folder_grid.xml").isFile
        )
    }

    @Test
    fun adapterNoLongerInflatesItemLayout() {
        val src = SourceFileProbe.sourceText("ui/adapter/SourceFolderAdapter.kt")
        assertFalse(
            "SourceFolderAdapter 不得再继承 RecyclerAdapter（已收窄为纯工具 object）",
            src.contains("RecyclerAdapter<")
        )
        assertFalse(
            "SourceFolderAdapter 不得再引用已退役的 item 布局 / ViewBinding",
            src.contains("item_source_folder_grid") || src.contains("ItemSourceFolderGridBinding")
        )
    }

    @Test
    fun retainedApiStillDeclared() {
        val src = SourceFileProbe.sourceText("ui/adapter/SourceFolderAdapter.kt")
        listOf(
            "object SourceFolderAdapter",
            "interface CallBack",
            "fun calculateSpanCount(context: Context, marginDp: Int): Int",
            "fun spacingPx(context: Context, marginDp: Int): Int",
            "data class FolderItem("
        ).forEach { decl ->
            assertTrue("保留项缺失：$decl", src.contains(decl))
        }
    }

    @Test
    fun retainedApiStillConsumedByHost() {
        val rss = SourceFileProbe.sourceText("ui/main/rss/RssFragment.kt")
        assertTrue("宿主应仍实现 SourceFolderAdapter.CallBack", rss.contains("SourceFolderAdapter.CallBack"))
        assertTrue("宿主应仍使用 SourceFolderAdapter.spacingPx", rss.contains("SourceFolderAdapter.spacingPx("))
        assertTrue(
            "宿主应仍使用 SourceFolderAdapter.calculateSpanCount",
            rss.contains("SourceFolderAdapter.calculateSpanCount(")
        )
    }
}