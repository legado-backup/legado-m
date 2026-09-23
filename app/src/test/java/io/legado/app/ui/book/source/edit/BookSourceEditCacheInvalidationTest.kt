package io.legado.app.ui.book.source.edit

import java.io.File
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * B4 · R18 写源入口 ①「新增/编辑书源」的缓存失效接线。
 *
 * 保存后不失效 ⇒ 编辑完源、回到阅读/WebView 仍走旧源（表现为"改了没生效"）。
 */
class BookSourceEditCacheInvalidationTest {

    private fun code(): String {
        val rel = "src/main/java/io/legado/app/ui/book/source/edit/BookSourceEditViewModel.kt"
        val file = listOf(File(rel), File("../app/$rel"), File("app/$rel")).firstOrNull { it.isFile }
            ?: throw AssertionError("未找到源文件：$rel")
        return file.readLines()
            .filterNot { it.trimStart().startsWith("//") || it.trimStart().startsWith("*") }
            .joinToString("\n")
    }

    @Test
    fun savingSourceInvalidatesQueryCache() {
        val source = code()
        val saveBlock = source.substringAfter("appDb.bookSourceDao.insert(source)")
            .substringBefore("concurrentRecordMap.remove")
        assertTrue(
            "写入后必须立即失效查询缓存（写完即读到最新）",
            saveBlock.contains("SourceQueryCache.invalidate()")
        )
        assertTrue(
            "改 URL 时走的删除分支也必须失效（经 SourceHelp.deleteBookSource）",
            source.contains("SourceHelp.deleteBookSource(")
        )
    }
}