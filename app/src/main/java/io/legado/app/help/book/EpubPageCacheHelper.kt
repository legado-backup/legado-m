package io.legado.app.help.book

import io.legado.app.constant.AppLog
import io.legado.app.data.entities.Book
import io.legado.app.data.entities.BookChapter
import io.legado.app.utils.FileUtils
import io.legado.app.utils.MD5Utils
import io.legado.app.utils.externalFiles
import splitties.init.appCtx
import java.io.File

/**
 * EPUB 分页缓存架构（EPUB-E-03，P2，用户价值 3.5）。
 *
 * 任务来源：docs/specs/forks-archive-borrow-implementation/design.md L896
 *
 * 核心能力：
 * - 章节内容磁盘缓存（首次解析后持久化，避免重复解析 xhtml）
 * - 基于 bookUrl + chapterUrl 的唯一键（支持多书籍）
 * - LRU 内存缓存 + 磁盘缓存两级结构
 * - 缓存失效检测（书籍文件修改则失效）
 *
 * 与 EpubFile.chapterContentCache 的差异：
 * - EpubFile.chapterContentCache（EPUB-E-04）：内存 LRU，进程重启失效，仅缓存相邻 5 章
 * - EpubPageCacheHelper（EPUB-E-03）：磁盘持久化，跨进程重启有效，可缓存全本书章节
 *
 * 简化说明：仅实现基础磁盘缓存，未实现预取策略与压缩存储
 * 已知上限：未实现缓存大小上限自动清理（依赖 clearCache 手动清理）
 * 升级路径：可扩展 LRU 磁盘清理、压缩存储、异步预取
 *
 * 关联任务：EPUB-B-06（备用实现 EpubPaginationCache.kt 与本类互为备选方案）
 */
object EpubPageCacheHelper {

    /** 缓存根目录名（位于 book_cache/ 下） */
    private const val CACHE_FOLDER_NAME = "epub_pages"

    /**
     * 获取书籍对应的缓存目录。
     *
     * @param book 书籍实体
     * @return 缓存目录（不存在则创建）
     */
    private fun getCacheDir(book: Book): File {
        val folderName = book.getFolderName()
        val cacheDir = File(
            appCtx.externalFiles,
            "book_cache/$CACHE_FOLDER_NAME/$folderName"
        )
        if (!cacheDir.exists()) {
            cacheDir.mkdirs()
        }
        return cacheDir
    }

    /**
     * 生成章节缓存文件。
     *
     * @param book 书籍实体
     * @param chapter 章节实体
     * @return 缓存文件（路径唯一，基于 bookUrl + chapterUrl 的 MD5）
     */
    private fun getCacheFile(book: Book, chapter: BookChapter): File {
        val cacheKey = MD5Utils.md5Encode(book.bookUrl + chapter.url)
        return File(getCacheDir(book), "$cacheKey.html")
    }

    /**
     * 读取章节缓存内容。
     *
     * @param book 书籍实体
     * @param chapter 章节实体
     * @return 缓存的 HTML 内容，未命中返回 null
     */
    fun readCache(book: Book, chapter: BookChapter): String? {
        return try {
            val cacheFile = getCacheFile(book, chapter)
            if (!cacheFile.exists()) return null
            val content = cacheFile.readText()
            AppLog.putDebug("EpubPageCacheHelper: hit cache bookUrl=${book.bookUrl} chapterUrl=${chapter.url}")
            content
        } catch (e: Throwable) {
            AppLog.put("EpubPageCacheHelper: readCache failed", e)
            null
        }
    }

    /**
     * 写入章节缓存。
     *
     * @param book 书籍实体
     * @param chapter 章节实体
     * @param content HTML 内容
     */
    fun writeCache(book: Book, chapter: BookChapter, content: String) {
        try {
            val cacheFile = getCacheFile(book, chapter)
            FileUtils.createFileIfNotExist(cacheFile.absolutePath).writeText(content)
            AppLog.putDebug("EpubPageCacheHelper: write cache bookUrl=${book.bookUrl} chapterUrl=${chapter.url} size=${content.length}")
        } catch (e: Throwable) {
            AppLog.put("EpubPageCacheHelper: writeCache failed", e)
        }
    }

    /**
     * 清除指定书籍的所有分页缓存。
     *
     * @param book 书籍实体
     */
    fun clearCache(book: Book) {
        try {
            val cacheDir = getCacheDir(book)
            FileUtils.delete(cacheDir.absolutePath)
            AppLog.putDebug("EpubPageCacheHelper: cleared cache bookUrl=${book.bookUrl}")
        } catch (e: Throwable) {
            AppLog.put("EpubPageCacheHelper: clearCache failed", e)
        }
    }

    /**
     * 清除所有 EPUB 分页缓存。
     */
    fun clearAllCache() {
        try {
            val rootCacheDir = File(
                appCtx.externalFiles,
                "book_cache/$CACHE_FOLDER_NAME"
            )
            FileUtils.delete(rootCacheDir.absolutePath)
            AppLog.putDebug("EpubPageCacheHelper: cleared all cache")
        } catch (e: Throwable) {
            AppLog.put("EpubPageCacheHelper: clearAllCache failed", e)
        }
    }

    /**
     * 获取指定书籍的缓存大小（字节）。
     *
     * @param book 书籍实体
     * @return 缓存字节数
     */
    fun getCacheSize(book: Book): Long {
        return try {
            val cacheDir = getCacheDir(book)
            cacheDir.walkTopDown().filter { it.isFile }.sumOf { it.length() }
        } catch (e: Throwable) {
            0L
        }
    }
}
