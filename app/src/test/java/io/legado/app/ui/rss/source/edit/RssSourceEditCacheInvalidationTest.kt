package io.legado.app.ui.rss.source.edit

import java.io.File
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * B4 · R18 写源入口 ①「新增/编辑订阅源」的缓存失效接线（与书源侧同构）。
 *
 * 订阅源与书源共用同一查询缓存（`any:` 前缀键）⇒ 漏一边会出现「编辑订阅源后，按 key 取仍是旧对象」。
 */
class RssSourceEditCacheInvalidationTest {

    private fun code(): String {
        val rel = "src/main/java/io/legado/app/ui/rss/source/edit/RssSourceEditViewModel.kt"
        val file = listOf(File(rel), File("../app/$rel"), File("app/$rel")).firstOrNull { it.isFile }
            ?: throw AssertionError("未找到源文件：$rel")
        return file.readLines()
            .filterNot { it.trimStart().startsWith("//") || it.trimStart().startsWith("*") }
            .joinToString("\n")
    }

    @Test
    fun savingRssSourceInvalidatesQueryCache() {
        val source = code()
        val saveBlock = source.substringAfter("appDb.rssSourceDao.insert(source)")
            .substringBefore("concurrentRecordMap.remove")
        assertTrue(
            "写入后必须立即失效查询缓存",
            saveBlock.contains("SourceQueryCache.invalidate()")
        )
        assertTrue(
            "书源侧与订阅源侧必须用同一出口（防各写一套）",
            source.contains("io.legado.app.help.source.SourceQueryCache") ||
                source.contains("import io.legado.app.help.source.SourceQueryCache")
        )
    }
}