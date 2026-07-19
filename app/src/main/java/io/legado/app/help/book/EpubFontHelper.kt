package io.legado.app.help.book

import android.graphics.Typeface
import io.legado.app.constant.AppLog
import io.legado.app.data.entities.Book
import io.legado.app.model.localBook.EpubFile
import io.legado.app.utils.MD5Utils
import splitties.init.appCtx
import java.io.File
import java.io.FileOutputStream

/**
 * EPUB 字体内嵌支持（EPUB-E-02）。
 *
 * 借鉴 Archive `EpubFontHelper`：解析 EPUB 内嵌字体（@font-face CSS 规则），
 * 提取字体文件到缓存目录，提供 Typeface 给阅读页使用。
 *
 * 设计要点：
 * - 字体提取：通过 [EpubFile.getFontStream] 获取字体流，写入缓存目录
 * - 缓存复用：用 book.bookUrl 的 MD5 作为缓存目录名，避免重复提取
 * - 字体加载：用 [Typeface.createFromFile] 加载本地字体文件
 * - 版权注意：仅支持 EPUB 内嵌的用户自有字体，不内置商业字体
 *
 * 关联任务：EPUB-E-02（P1）字体内嵌支持。
 */
object EpubFontHelper {

    private const val CACHE_DIR_NAME = "epub_fonts"

    /**
     * 加载 EPUB 内嵌字体为 Typeface（带磁盘缓存）。
     *
     * 调用流程：
     * 1. 计算缓存文件路径（cacheDir/epub_fonts/{bookMd5}/{fontName}）
     * 2. 缓存未命中时，从 EPUB 提取字体到缓存文件
     * 3. 用 [Typeface.createFromFile] 加载为 Typeface
     *
     * @param epubFile EPUB 文件解析器
     * @param book 书籍实体（用于计算缓存目录）
     * @param href 字体在 EPUB 中的 href
     * @return Typeface，加载失败返回 null
     */
    fun loadTypeface(epubFile: EpubFile, book: Book, href: String): Typeface? {
        val cacheFile = getCacheFile(book, href)
        // 缓存未命中，从 EPUB 提取
        if (!cacheFile.exists()) {
            cacheFile.parentFile?.mkdirs()
            runCatching {
                epubFile.getFontStream(href)?.use { input ->
                    FileOutputStream(cacheFile).use { output ->
                        input.copyTo(output)
                    }
                } ?: return null
            }.onFailure {
                AppLog.put("EpubFontHelper.loadTypeface extract failed href=$href", it)
                return null
            }
        }
        return runCatching {
            Typeface.createFromFile(cacheFile)
        }.onFailure {
            AppLog.put("EpubFontHelper.loadTypeface createFromFile failed file=${cacheFile.name}", it)
        }.getOrNull()
    }

    /**
     * 批量预提取 EPUB 内嵌字体到缓存。
     *
     * 用于书籍导入时预提取字体，避免阅读时首次加载延迟。
     *
     * @param epubFile EPUB 文件解析器
     * @param book 书籍实体
     * @param hrefs 字体 href 列表
     * @return 提取成功的字体文件列表
     */
    fun preloadFonts(epubFile: EpubFile, book: Book, hrefs: List<String>): List<File> {
        val extracted = mutableListOf<File>()
        hrefs.forEach { href ->
            val cacheFile = getCacheFile(book, href)
            if (cacheFile.exists()) {
                extracted.add(cacheFile)
                return@forEach
            }
            cacheFile.parentFile?.mkdirs()
            runCatching {
                epubFile.getFontStream(href)?.use { input ->
                    FileOutputStream(cacheFile).use { output ->
                        input.copyTo(output)
                    }
                    extracted.add(cacheFile)
                }
            }.onFailure {
                AppLog.put("EpubFontHelper.preloadFonts failed href=$href", it)
            }
        }
        return extracted
    }

    /**
     * 获取字体缓存文件路径。
     *
     * @param book 书籍实体
     * @param href 字体在 EPUB 中的 href
     * @return 缓存文件 File（可能不存在）
     */
    private fun getCacheFile(book: Book, href: String): File {
        val bookMd5 = MD5Utils.md5Encode(book.bookUrl)
        val fontName = href.substringAfterLast("/").ifEmpty { "font_${System.currentTimeMillis()}" }
        return File(appCtx.cacheDir, "$CACHE_DIR_NAME/$bookMd5/$fontName")
    }

    /**
     * 清理指定书籍的字体缓存。
     *
     * @param book 书籍实体
     */
    fun clearCache(book: Book) {
        runCatching {
            val bookMd5 = MD5Utils.md5Encode(book.bookUrl)
            File(appCtx.cacheDir, "$CACHE_DIR_NAME/$bookMd5").deleteRecursively()
        }
    }

    /**
     * 清理所有 EPUB 字体缓存。
     */
    fun clearAllCache() {
        runCatching {
            File(appCtx.cacheDir, CACHE_DIR_NAME).deleteRecursively()
        }
    }
}
