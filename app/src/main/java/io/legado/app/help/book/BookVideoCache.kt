package io.legado.app.help.book

import io.legado.app.data.entities.Book
import io.legado.app.data.entities.BookChapter
import java.io.File

/**
 * 书源视频缓存产物的定位与判定（video-cache-and-multiep AD-01）。
 *
 * 复用 `BookHelp` 的缓存目录 `externalFiles/book_cache/{folder}`，仅以 `.mp4` 后缀区分：
 * 主名 `c-{md5}.mp4`（与文本 `.nb` 同目录），兼容名 `{index:05d}-{titleMD5}.mp4`。
 *
 * 独立成单源对象的原因：`BookHelp` 已接近单文件行数上限（G-38），且视频判定只服务
 * 视频链路（播放前本地命中、缓存统计、缓存服务落盘），职责可清晰剥离。
 */
object BookVideoCache {

    const val suffix = "mp4"

    /** 卷行不可缓存（线路名不是一集） */
    fun isCacheable(chapter: BookChapter): Boolean = !chapter.isVolume

    /** 主名（写入用文件名，纯函数便于单测锁定命名契约） */
    fun primaryNameOf(chapter: BookChapter): String = chapter.contentCacheFileName(suffix)

    /** 主名目标文件（写入用） */
    fun fileOf(book: Book, chapter: BookChapter): File {
        return File(BookHelp.getCacheDir(book), primaryNameOf(chapter))
    }

    /** 兼容名文件（历史/其它写入方可能采用） */
    fun legacyFileOf(book: Book, chapter: BookChapter): File {
        return File(BookHelp.getCacheDir(book), chapter.getFileName(suffix))
    }

    /** 该集可能存在的候选文件名（缓存管理按目录列表比对时使用，避免额外 IO） */
    fun cacheFileNames(book: Book, chapter: BookChapter): Set<String> {
        return linkedSetOf(fileOf(book, chapter).name, legacyFileOf(book, chapter).name)
    }

    /** 是否已缓存且文件非空；卷行恒判不可缓存 */
    fun has(book: Book, chapter: BookChapter): Boolean {
        if (!isCacheable(chapter)) return false
        return listOf(fileOf(book, chapter), legacyFileOf(book, chapter))
            .any { it.exists() && it.length() > 0L }
    }
}
