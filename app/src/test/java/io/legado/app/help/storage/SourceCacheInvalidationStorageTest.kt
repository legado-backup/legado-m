package io.legado.app.help.storage

import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * B4 · R18 写源入口接线（备份恢复 / 旧数据导入）。
 *
 * 为什么单独测：这两处是**绕过 `SourceHelp.insertBookSource` 直接写 DAO** 的恢复路径，
 * 若漏调失效，用户「恢复备份后立即用新源」会读到恢复前的旧源缓存（表现为"恢复没生效"）。
 */
class SourceCacheInvalidationStorageTest {

    private fun code(relFromMainJava: String): String {
        val rel = "src/main/java/io/legado/app/$relFromMainJava"
        val file = listOf(File(rel), File("../app/$rel"), File("app/$rel")).firstOrNull { it.isFile }
            ?: throw AssertionError("未找到源文件：$rel")
        return file.readLines()
            .filterNot { it.trimStart().startsWith("//") || it.trimStart().startsWith("*") }
            .joinToString("\n")
    }

    @Test
    fun restoreInvalidatesAfterBothSourceTables() {
        val restore = code("help/storage/Restore.kt")
        // 恢复段：书源块 → 订阅源块（取到 rssStar 之前）
        val sourceRestore = restore.substringAfter("fileToListT<BookSource>").substringBefore("fileToListT<RssStar>")
        assertTrue("恢复书源块必须存在", sourceRestore.contains("appDb.bookSourceDao.insert"))
        assertTrue("恢复订阅源块必须存在", sourceRestore.contains("appDb.rssSourceDao.insert"))
        assertEquals(
            "书源与订阅源恢复各需一次失效（漏一处 ⇒ 该表恢复后读到旧值）",
            2,
            Regex("SourceQueryCache\\.invalidate\\(\\)").findAll(sourceRestore).count()
        )
        assertTrue(
            "旧格式导入分支必须存在（其内部已自失效）",
            sourceRestore.contains("ImportOldData.importOldSource(")
        )
    }

    @Test
    fun importOldDataInvalidates() {
        val import = code("help/storage/ImportOldData.kt")
        assertTrue("旧数据导入书源后必须失效缓存", import.contains("SourceQueryCache.invalidate()"))
    }
}