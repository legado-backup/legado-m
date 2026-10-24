package io.legado.app.service.kernel

import android.content.Context
import io.legado.app.constant.IntentAction
import io.legado.app.data.appDb
import io.legado.app.data.entities.Book
import io.legado.app.data.entities.BookChapter
import io.legado.app.help.book.BookHelp
import io.legado.app.help.book.BookVideoCache
import io.legado.app.service.VideoCacheService
import io.legado.app.utils.startService
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import java.util.concurrent.ConcurrentHashMap

/**
 * 书源视频缓存内核（video-cache-and-multiep AD-09 / AD-13 / AD-14）。
 *
 * 职责：
 * 1) 单一事实来源：详情页缓存条与缓存管理都读同一份 [Progress]；
 * 2) 内存索引：`cachedIndexes` 让列表与进度统计零 IO（扫描只在 refreshIndex 时进行）；
 * 3) 任务控制：启动/停止/清理统一通过本内核，服务只做执行与回传。
 *
 * 不变量：
 * - [Progress.total] 只统计**正片集**（非卷行）；卷行恒不计入已缓存。
 * - 索引与真实文件的一致性由 [refreshIndex]（进入缓存页/启动前）与完成回调共同保证。
 */
object VideoCacheKernel {

    /**
     * 单本书的缓存进度快照。
     */
    data class Progress(
        val bookUrl: String = "",
        val running: Boolean = false,
        val total: Int = 0,
        val cached: Int = 0,
        val failed: Int = 0,
        val currentIndex: Int = -1,
        val currentTitle: String = "",
        val finished: Boolean = false,
        val lastError: String? = null,
    ) {
        val percent: Int
            get() = if (total <= 0) 0 else (cached * 100 / total).coerceIn(0, 100)
    }

    private val _states = MutableStateFlow<Map<String, Progress>>(emptyMap())
    val states: StateFlow<Map<String, Progress>> = _states.asStateFlow()

    private val indexes = ConcurrentHashMap<String, Set<Int>>()

    /**
     * 本会话内失败过的集（内存态，不落盘）。
     *
     * 用途：重跑缓存时把「上轮已失败」的集**排到末尾**——失败集多为站点限制（锁定/下架）页，
     * 每次嗅探都要跑满 15s 超时；若排在开头，用户在真能缓存的集之前要白等数分钟，
     * 感知即「缓存好慢 / 缓存不了」。排到末尾后正常集先落盘，失败集仅作最终补充尝试。
     */
    private val failedIndexes = ConcurrentHashMap<String, MutableSet<Int>>()

    /** 该集本轮是否已失败过（服务据此决定处理顺序） */
    fun isFailed(bookUrl: String, index: Int): Boolean =
        failedIndexes[bookUrl]?.contains(index) == true

    /**
     * 处理顺序：未失败集按原序在前，已失败集在后（稳定排序，保证断点续传语义不变）。
     */
    fun orderPositions(bookUrl: String, positions: List<Int>): List<Int> =
        positions.sortedBy { if (isFailed(bookUrl, it)) 1 else 0 }

    fun progressOf(bookUrl: String): Progress = _states.value[bookUrl] ?: Progress(bookUrl = bookUrl)

    fun cachedIndexes(bookUrl: String): Set<Int> = indexes[bookUrl].orEmpty()

    fun isCached(bookUrl: String, index: Int): Boolean = indexes[bookUrl]?.contains(index) == true

    /** 正片集（非卷行）列表，按目录顺序 */
    fun episodesOf(chapters: List<BookChapter>): List<BookChapter> =
        chapters.filter { !it.isVolume }

    /**
     * 重新扫描并重建某本书的缓存索引（IO 调用；UI 只读索引，不做 IO）。
     */
    suspend fun refreshIndex(book: Book) {
        val chapters = appDb.bookChapterDao.getChapterList(book.bookUrl)
        val episodes = episodesOf(chapters)
        val cached = episodes
            .filter { BookVideoCache.has(book, it) }
            .mapTo(linkedSetOf()) { it.index }
        indexes[book.bookUrl] = cached
        val old = progressOf(book.bookUrl)
        _states.value = _states.value + (
            book.bookUrl to old.copy(
                bookUrl = book.bookUrl,
                total = episodes.size,
                cached = cached.size,
            )
            )
    }

    fun markCached(bookUrl: String, index: Int) {
        indexes[bookUrl] = indexes[bookUrl].orEmpty() + index
    }

    fun markCleared(bookUrl: String) {
        indexes.remove(bookUrl)
        failedIndexes.remove(bookUrl)
        _states.value = _states.value - bookUrl
    }

    /** 启动缓存：范围 [from, to]（含端点；to < 0 表示到最后一集） */
    fun start(context: Context, bookUrl: String, from: Int = 0, to: Int = -1) {
        context.startService<VideoCacheService> {
            action = IntentAction.start
            putExtra("bookUrl", bookUrl)
            putExtra("start", from)
            putExtra("end", to)
        }
        _states.value = _states.value + (
            bookUrl to progressOf(bookUrl).copy(
                running = true,
                finished = false,
                lastError = null,
            )
            )
    }

    fun stop(context: Context, bookUrl: String) {
        context.startService<VideoCacheService> {
            action = IntentAction.stop
            putExtra("bookUrl", bookUrl)
        }
    }

    /** 清理该书的视频缓存（文件整目录由 BookHelp.clearCache 负责） */
    fun clear(context: Context, book: Book) {
        BookHelp.clearCache(book)
        markCleared(book.bookUrl)
    }

    // ---- 服务回传（internal：仅同模块服务可写） ----

    internal fun onStarted(bookUrl: String, total: Int) {
        _states.value = _states.value + (
            bookUrl to progressOf(bookUrl).copy(
                running = true, finished = false, total = total, lastError = null,
            )
            )
    }

    internal fun onEpisodeStart(bookUrl: String, index: Int, title: String) {
        _states.value = _states.value + (
            bookUrl to progressOf(bookUrl).copy(currentIndex = index, currentTitle = title)
            )
    }

    internal fun onEpisodeDone(bookUrl: String, index: Int) {
        markCached(bookUrl, index)
        failedIndexes[bookUrl]?.remove(index)
        val p = progressOf(bookUrl)
        _states.value = _states.value + (bookUrl to p.copy(cached = p.cached + 1))
    }

    internal fun onEpisodeFailed(bookUrl: String, index: Int, message: String?) {
        failedIndexes.getOrPut(bookUrl) { java.util.Collections.synchronizedSet(mutableSetOf()) }
            .add(index)
        val p = progressOf(bookUrl)
        _states.value = _states.value + (
            bookUrl to p.copy(failed = p.failed + 1, lastError = message)
            )
    }

    internal fun onFinished(bookUrl: String) {
        val p = progressOf(bookUrl)
        _states.value = _states.value + (
            bookUrl to p.copy(running = false, finished = true, currentIndex = -1)
            )
    }

    internal fun onStopped(bookUrl: String) {
        val p = progressOf(bookUrl)
        _states.value = _states.value + (bookUrl to p.copy(running = false))
    }
}
