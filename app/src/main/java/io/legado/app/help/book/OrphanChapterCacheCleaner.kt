package io.legado.app.help.book

import io.legado.app.constant.AppLog
import io.legado.app.data.appDb
import io.legado.app.data.entities.Book
import io.legado.app.data.entities.BookChapter
import io.legado.app.utils.FileUtils
import kotlinx.coroutines.Dispatchers.IO
import kotlinx.coroutines.withContext
import java.io.File

/**
 * R7：缓存维护「孤立章节缓存清理 + 字数回填」。
 *
 * 判定口径（AD-10）：以清单所在目录为基准，「目录内章节缓存文件」−「当前章节表推导出的应存在集合」= 差集。
 * - 书籍已删除（清单里的 bookUrl 查不到书）⇒ 整本目录 + 清单一起清；
 * - 章节表为空 / 查询异常 ⇒ **跳过该书**（禁止把「查不到」当成「全部失效」而全删）；
 * - 只动章节缓存命名文件（`%05d-{titleMd5}.nb/.nr`），图片/EPUB/字体等一律不碰。
 *
 * 字数回填（AD-11）：仅当 `Book.wordCount <= 0` 且**全部非卷章节** `wordCount > 0` 时求和写回，
 * 部分章节为 0 一律跳过（写错统计比保留 0 更糟）。
 */
object OrphanChapterCacheCleaner {

    private val CHAPTER_FILE_REGEX = Regex("""^\d{5}-.+\.(nb|nr)$""")

    data class CleanReport(
        val deletedFiles: Int = 0,
        val freedBytes: Long = 0,
        val booksDeleted: Int = 0,
        val wordsBackfilled: Int = 0,
        val dryRun: Boolean = true
    ) {
        fun summary(): String {
            val head = if (dryRun) "预计清理" else "已清理"
            val parts = buildList {
                add("$head ${deletedFiles} 个章节缓存文件")
                if (freedBytes > 0) add("释放 ${formatSize(freedBytes)}")
                if (booksDeleted > 0) add("${if (dryRun) "待" else ""}移除 ${booksDeleted} 本已删除书的缓存")
                if (wordsBackfilled > 0) add("${if (dryRun) "待" else ""}回填 ${wordsBackfilled} 本书的字数")
            }
            return parts.joinToString("，")
        }
    }

    fun isChapterCacheFile(name: String): Boolean = CHAPTER_FILE_REGEX.matches(name)

    /** 当前章节表推导出的「应存在」章节缓存文件名集合（不含卷章节） */
    fun keepFileNames(chapters: List<BookChapter>): Set<String> =
        chapters.asSequence()
            .filterNot { it.isVolume }
            .flatMap { sequenceOf(it.getFileName("nb"), it.getFileName("nr")) }
            .toSet()

    /** 目录内属于孤立集合的章节缓存文件（纯函数，可 JVM 单测） */
    fun orphanFileNames(dirFileNames: Collection<String>, keep: Set<String>): List<String> =
        dirFileNames.filter { isChapterCacheFile(it) && it !in keep }

    /**
     * 解析章节字数文本为原始字数（`BookChapter.wordCount` 实为 String，
     * 缓存链路写入的是 `StringUtils.wordCountFormat` 产物：`"123字"` / `"1.2万字"`）。
     * 非数字/不可解析返回 null。
     */
    fun parseWordCount(text: String?): Long? {
        val value = text?.trim().orEmpty()
        if (value.isEmpty()) return null
        return kotlin.runCatching {
            when {
                value.endsWith("万字") ->
                    (value.removeSuffix("万字").toDouble() * 10_000).toLong()
                value.endsWith("字") ->
                    value.removeSuffix("字").toDoubleOrNull()?.toLong()
                else -> value.toLongOrNull()
            }
        }.getOrNull()?.takeIf { it > 0 }
    }

    /**
     * 可回填的字数文本；不可回填返回 null。
     *
     * 条件（AD-11「齐备才写」）：书级字数为空/非正，且**全部非卷章节**字数均可解析且 >0。
     * 任一章缺失即放弃（写错统计比保留空值更糟）。
     */
    fun backfillWordCount(bookWordCount: String?, chapters: List<BookChapter>): String? {
        if (parseWordCount(bookWordCount) != null) return null
        val real = chapters.filterNot { it.isVolume }
        if (real.isEmpty()) return null
        var total = 0L
        for (chapter in real) {
            val count = parseWordCount(chapter.wordCount) ?: return null
            total += count
        }
        if (total <= 0L) return null
        return io.legado.app.utils.StringUtils.wordCountFormat(total.toInt())
    }

    suspend fun run(dryRun: Boolean): CleanReport = withContext(IO) {
        var deletedFiles = 0
        var freedBytes = 0L
        var booksDeleted = 0
        var wordsBackfilled = 0

        CacheManifestHelper.listCacheDirs().forEach { dir ->
            val manifest = CacheManifestHelper.read(File(dir, CacheManifestHelper.MANIFEST_FILE_NAME))
            val book = manifest?.bookUrl?.takeIf { it.isNotBlank() }
                ?.let { kotlin.runCatching { appDb.bookDao.getBook(it) }.getOrNull() }

            if (book == null) {
                // 清单可读且书已删除 ⇒ 整本缓存（含清单）清掉；清单不可读的目录保守保留
                if (manifest != null) {
                    booksDeleted++
                    freedBytes += dirSize(dir)
                    if (!dryRun) {
                        FileUtils.delete(dir.absolutePath)
                    }
                }
                return@forEach
            }

            val chapters = kotlin.runCatching {
                appDb.bookChapterDao.getChapterList(book.bookUrl)
            }.getOrNull()
            if (chapters.isNullOrEmpty()) {
                // 章节表为空/异常：不得按「全部失效」删除
                AppLog.putDebug("OrphanChapterCacheCleaner 跳过（章节表不可用）: ${book.name}")
                return@forEach
            }

            val keep = keepFileNames(chapters)
            val orphans = orphanFileNames(dir.listFiles()?.map { it.name }.orEmpty(), keep)
            orphans.forEach { name ->
                val file = File(dir, name)
                val length = file.length()
                deletedFiles++
                freedBytes += length
                if (!dryRun) {
                    file.delete()
                }
            }

            if (!dryRun && orphans.isNotEmpty()) {
                // 清单同步自愈：按文件实际存在性重写 cached 标记，避免残留"已缓存"假象
                kotlin.runCatching {
                    CacheManifestHelper.write(book, chapters) { chapter ->
                        File(dir, chapter.getFileName("nb")).isFile
                    }
                }
            }

            backfillWordCount(book.wordCount, chapters)?.let { formatted ->
                wordsBackfilled++
                if (!dryRun) {
                    kotlin.runCatching {
                        appDb.bookDao.update(book.copy(wordCount = formatted))
                    }.onFailure {
                        AppLog.put("字数回填失败 ${book.name}: ${it.localizedMessage}")
                    }
                }
            }
        }

        CleanReport(
            deletedFiles = deletedFiles,
            freedBytes = freedBytes,
            booksDeleted = booksDeleted,
            wordsBackfilled = wordsBackfilled,
            dryRun = dryRun
        )
    }

    private fun dirSize(dir: File): Long =
        dir.listFiles()?.sumOf { if (it.isFile) it.length() else dirSize(it) } ?: 0L

    private fun formatSize(bytes: Long): String = when {
        bytes >= 1024L * 1024L -> "%.1f MB".format(bytes / (1024.0 * 1024.0))
        bytes >= 1024L -> "%.1f KB".format(bytes / 1024.0)
        else -> "${bytes}B"
    }
}
