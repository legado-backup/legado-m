package io.legado.app.help.video

import android.net.Uri
import io.legado.app.data.entities.Book
import io.legado.app.data.entities.BookChapter
import io.legado.app.help.book.BookHelp
import io.legado.app.help.book.BookVideoCache
import io.legado.app.help.book.isAudio
import io.legado.app.help.book.isImage
import io.legado.app.help.book.isLocalTxt
import io.legado.app.help.book.isVideo
import io.legado.app.help.exoplayer.ExoPlayerHelper

/**
 * 本地优先判定（video-cache-and-multiep AD-11）。
 *
 * 四类内容统一判定"是否已有本地产物"，避免各链路各写一遍导致漏判（本次需求的
 * "视频漏了本地优先"就是散点判定的后果）。纯函数式入口，便于单测。
 *
 * 说明：音频的本地缓存由 ExoPlayer 缓存体系透明接管（`isMediaCached`），因此
 * [localUri] 只对视频返回可直接播放的本地 file Uri，其余类型返回 null 交由既有链路。
 */
object LocalMediaResolver {

    /**
     * 是否已有本地可用的缓存产物。
     */
    fun hasLocal(book: Book, chapter: BookChapter): Boolean {
        return when {
            chapter.isVolume -> false
            book.isVideo -> BookVideoCache.has(book, chapter)
            book.isAudio -> ExoPlayerHelper.isMediaCached(chapter.resourceUrl)
            book.isImage -> BookHelp.hasImageContent(book, chapter)
            book.isLocalTxt -> true
            else -> BookHelp.hasContent(book, chapter)
        }
    }

    /**
     * 视频本地产物的 file Uri；其它类型或无本地文件时返回 null。
     */
    fun localUri(book: Book, chapter: BookChapter): String? {
        if (!book.isVideo || chapter.isVolume) return null
        val file = BookVideoCache.fileOf(book, chapter)
        if (!file.exists() || file.length() <= 0L) return null
        return Uri.fromFile(file).toString()
    }
}
