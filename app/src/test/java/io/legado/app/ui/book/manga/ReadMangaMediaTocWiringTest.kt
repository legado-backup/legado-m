package io.legado.app.ui.book.manga

import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * NEW-59 接线契约（漫画打开链路）：`MediaTocRefresh` 的**生产调用点**必须在正文加载之前。
 *
 * 存在理由：这类「少一行」的接线单测抓不到（`MediaTocRefresh` 是纯逻辑 + Android 单例依赖），
 * 而漏接的后果不可见 —— 设置项「自动刷新媒体目录」开着却毫无效果。故把调用点**按顺序与数量**钉在源码层：
 *  - 调用点必须存在且位于 `//开始加载内容` 之前（先修目录再取正文，顺序反了等于没修）；
 *  - 刷新入口唯一（防旁路实现绕过 `MediaTocRefresh` 自带的三重校验）；
 *  - 失败分支必须保留旧目录（只记日志），不得因刷新失败打断本来能读的书。
 */
class ReadMangaMediaTocWiringTest {

    private fun read(rel: String): String =
        listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
            .readText()
            .replace("\r\n", "\n")

    private val viewModel by lazy {
        read("src/main/java/io/legado/app/ui/book/manga/ReadMangaViewModel.kt")
    }

    @Test
    fun `占位目录刷新须在正文加载之前接线`() {
        val call = viewModel.indexOf("maybeRefreshMediaTocAwait(book)")
        val loadContent = viewModel.indexOf("//开始加载内容")
        assertTrue("必须存在生产调用点（否则设置项永远不生效）", call > 0)
        assertTrue("接线须位于正文加载之前", loadContent > 0 && call < loadContent)
    }

    @Test
    fun `刷新入口唯一且经 MediaTocRefresh`() {
        assertEquals(
            "刷新入口须唯一（防旁路实现绕过自带校验）",
            1,
            Regex("""MediaTocRefresh\.refresh\(""").findAll(viewModel).count()
        )
        assertTrue("须先过 shouldRefresh 门禁", viewModel.contains("MediaTocRefresh.shouldRefresh(chapter)"))
    }

    @Test
    fun `本地书籍与空目录不触发刷新`() {
        assertTrue(
            "须排除本地书籍与无章节场景",
            viewModel.contains("if (book.isLocal || ReadManga.chapterSize <= 0) return")
        )
    }

    @Test
    fun `刷新失败保留旧目录不打断阅读`() {
        assertTrue("失败须走 runCatching", viewModel.contains("}.onFailure {"))
        assertTrue("失败语义须为保留旧目录", viewModel.contains("媒体目录自动刷新失败，保留旧目录"))
    }
}
