package io.legado.app.help.audio

import android.content.Context
import io.legado.app.R
import io.legado.app.data.entities.Book
import io.legado.app.data.entities.BookChapter
import io.legado.app.help.book.BookHelp
import io.legado.app.help.book.getBookSource
import io.legado.app.help.exoplayer.ExoPlayerHelper
import io.legado.app.model.analyzeRule.AnalyzeUrl
import io.legado.app.model.analyzeRule.AnalyzeUrl.Companion.getMediaRequest
import io.legado.app.model.webBook.WebBook
import io.legado.app.utils.isJsonArray
import kotlinx.coroutines.currentCoroutineContext

/**
 * 音频缓存媒体请求解析**单源**（book-info-unified-cache AD-08）。
 *
 * 原实现为 `CacheManageActivityViewModel.resolveAudioMediaRequest`（ViewModel 私有），
 * 详情页无法复用。此处提取为共享 object：缓存管理页与详情页缓存卡同调一份，
 * 避免同语义双实现（组件/单源原则）。
 *
 * 解析顺序：已存 `resourceUrl` 直用 → 书源 + 本地已缓存正文 → `WebBook.getContentAwait`
 * → 逐个候选 `AnalyzeUrl.getMediaRequest()`（JSON 数组直接作为请求体）。
 */
object AudioMediaRequestResolver {

    suspend fun resolve(
        context: Context,
        book: Book,
        chapter: BookChapter,
    ): ExoPlayerHelper.MediaRequest {
        chapter.resourceUrl
            ?.takeIf { it.isNotBlank() }
            ?.let { return ExoPlayerHelper.MediaRequest(it) }
        val source = book.getBookSource()
            ?: throw IllegalStateException(context.getString(R.string.book_source_not_found))
        val candidates = linkedSetOf<String>()
        BookHelp.getContent(book, chapter)
            ?.trim()
            ?.takeIf { it.isNotBlank() }
            ?.let(candidates::add)
        WebBook.getContentAwait(source, book, chapter, needSave = true)
            .trim()
            .takeIf { it.isNotBlank() }
            ?.let(candidates::add)
        var lastError: Throwable? = null
        for (content in candidates) {
            try {
                if (content.isJsonArray()) {
                    return ExoPlayerHelper.MediaRequest(content)
                }
                return AnalyzeUrl(
                    content,
                    source = source,
                    ruleData = book,
                    chapter = chapter,
                    coroutineContext = currentCoroutineContext()
                ).getMediaRequest()
            } catch (e: Exception) {
                lastError = e
            }
        }
        throw IllegalStateException(
            lastError?.localizedMessage ?: context.getString(R.string.cache_manage_audio_url_empty)
        )
    }
}
