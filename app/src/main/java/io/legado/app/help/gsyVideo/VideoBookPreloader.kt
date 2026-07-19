package io.legado.app.help.gsyVideo

import io.legado.app.constant.AppLog
import io.legado.app.constant.BookSourceType
import io.legado.app.constant.BookType
import io.legado.app.data.appDb
import io.legado.app.data.entities.Book
import io.legado.app.data.entities.SearchBook
import io.legado.app.help.book.addType
import io.legado.app.help.book.isNotShelf
import io.legado.app.model.webBook.WebBook
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers.IO
import kotlinx.coroutines.launch
import kotlinx.coroutines.sync.Semaphore
import kotlinx.coroutines.sync.withPermit
import java.util.concurrent.ConcurrentHashMap

/**
 * 视频书目录预加载器（VIDEO-B-01）。
 *
 * 借鉴 Archive `VideoBookPreloader`：在搜索结果页预加载视频书目录，
 * 用户点击进入播放页时可直接从本地数据库读取章节，提升启动速度。
 *
 * - 使用 Semaphore 限制并发预加载数量（默认 4 个）
 * - 使用 ConcurrentHashMap.newKeySet 去重（同一 bookUrl+origin 不重复预加载）
 * - 仅预加载视频类型书源（source.bookSourceType == video 或 searchBook.type 含 video）
 *
 * 关联任务：VIDEO-B-01（P0）搜索结果页预加载视频书目录。
 */
object VideoBookPreloader {

    private const val DEFAULT_MAX_PRELOAD = 4
    private val runningKeys = ConcurrentHashMap.newKeySet<String>()
    private val preloadSemaphore = Semaphore(DEFAULT_MAX_PRELOAD)

    fun preloadSearchBooks(
        scope: CoroutineScope,
        books: List<SearchBook>,
        maxCount: Int = DEFAULT_MAX_PRELOAD
    ) {
        books.asSequence()
            .filter { it.bookUrl.isNotBlank() && it.origin.isNotBlank() }
            .take(maxCount.coerceAtLeast(1) * 3)
            .forEach { preload(scope, it) }
    }

    fun preload(scope: CoroutineScope, searchBook: SearchBook) {
        val key = "${searchBook.origin}|${searchBook.bookUrl}"
        if (!runningKeys.add(key)) return
        scope.launch(IO) {
            try {
                preloadSemaphore.withPermit {
                    preloadAwait(searchBook)
                }
            } catch (e: CancellationException) {
                throw e
            } catch (e: Throwable) {
                AppLog.put("Video toc preload failed: ${searchBook.name}\n${e.localizedMessage}", e)
            } finally {
                runningKeys.remove(key)
            }
        }
    }

    private suspend fun preloadAwait(searchBook: SearchBook): Boolean {
        if (searchBook.bookUrl.isBlank() || searchBook.origin.isBlank()) return false
        if (appDb.bookChapterDao.getChapterList(searchBook.bookUrl).isNotEmpty()) return true
        val source = appDb.bookSourceDao.getBookSource(searchBook.origin) ?: return false
        if (source.bookSourceType != BookSourceType.video && (searchBook.type and BookType.video) <= 0) {
            return false
        }
        val stored = appDb.bookDao.getBook(searchBook.bookUrl)
        val inBookshelf = stored?.isNotShelf == false
        val book = stored ?: searchBook.toBook()
        val resolvedBook = loadInfoIfNeeded(book)
        val chapters = WebBook.getChapterListAwait(
            bookSource = source,
            book = resolvedBook,
            runPerJs = inBookshelf,
            isFromBookInfo = true
        ).getOrThrow()
        if (chapters.isEmpty()) return false
        if (!inBookshelf) {
            resolvedBook.addType(BookType.notShelf)
        }
        resolvedBook.save()
        appDb.bookChapterDao.delByBook(resolvedBook.bookUrl)
        appDb.bookChapterDao.insert(*chapters.toTypedArray())
        return true
    }

    private suspend fun loadInfoIfNeeded(book: Book): Book {
        val source = appDb.bookSourceDao.getBookSource(book.origin) ?: return book
        return if (book.tocUrl.isBlank()) {
            WebBook.getBookInfoAwait(source, book, canReName = false)
        } else {
            book
        }
    }
}
