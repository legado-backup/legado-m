package io.legado.app.ui.book.read.epub

import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * B20：EPUB 视图/渲染器零调用残留退役守护。
 *
 * 缺陷背景（三档分诊结论）：
 * - `EpubReadView.dp`：零调用且本文件未引入任何共享 dp 工具 ⇒ **遗留冗余助手**，退役；
 * - `EpubPageRenderer.resolvedTextRole`：零调用纯映射（返回 rt/sup/sub/ruby），其枚举分支
 *   仅被自身使用 ⇒ **遗留冗余助手**，退役。
 * 未接线候选（`drawLoading` / `startProgrammaticScroll`）已登记豁免台账，不在本批。
 */
class EpubRetiredHelperTest {

    private fun code(rel: String): String =
        listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
            .readText().replace("\r\n", "\n")

    @Test
    fun `EPUB 零调用残留助手已退役且活实现仍在`() {
        val view = code("src/main/java/io/legado/app/ui/book/read/epub/EpubReadView.kt")
        assertEquals("遗留 dp 助手应退役", false, view.contains("fun dp(value: Int)"))
        assertEquals("活实现 setPages 必须保留", true, view.contains("fun setPages("))

        val renderer = code("src/main/java/io/legado/app/ui/book/read/epub/EpubPageRenderer.kt")
        assertEquals("遗留角色映射助手应退役", false, renderer.contains("fun EpubMeasuredTextFragment.resolvedTextRole("))
        assertEquals("活实现 resolveMeasuredBaseline 必须保留", true,
            renderer.contains("fun resolveMeasuredBaseline("))
    }
}
