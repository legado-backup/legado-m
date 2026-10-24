package io.legado.app.ui.book.info.compose

import android.content.Context
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import io.legado.app.R
import io.legado.app.data.appDb
import io.legado.app.data.entities.Book
import io.legado.app.help.audio.AudioMediaRequestResolver
import io.legado.app.help.book.BookHelp
import io.legado.app.help.book.CacheBarKind
import io.legado.app.help.book.CachedChapterResolver
import io.legado.app.help.book.getBookSource
import io.legado.app.help.book.isAudio
import io.legado.app.help.book.isImage
import io.legado.app.help.book.isLocal
import io.legado.app.help.book.isVideo
import io.legado.app.help.source.isVideoSource
import io.legado.app.model.CacheBook
import io.legado.app.service.kernel.VideoCacheKernel
import io.legado.app.ui.book.cache.AudioCacheTaskManager
import io.legado.app.ui.widget.compose.AppManagementCard
import io.legado.app.ui.widget.compose.AppManagementPalette
import io.legado.app.ui.widget.compose.rememberAppManagementPalette
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import kotlinx.coroutines.withTimeoutOrNull

/**
 * 详情页缓存状态快照（book-info-unified-cache AD-03）。
 *
 * 三源聚合后的统一形态：视频/音频来自各自 StateFlow，文本/图片/文件来自目录扫描 + `CacheBook` 模型。
 */
internal data class BookCacheStatus(
    val cached: Int = 0,
    val total: Int = 0,
    val running: Boolean = false,
    val failed: Int = 0,
)

/** 纯策略（单测锁定）：进度百分比；total<=0 时为 0，越界钳到 0..100 */
internal fun bookCachePercent(cached: Int, total: Int): Int {
    if (total <= 0) return 0
    return (cached * 100 / total).coerceIn(0, 100)
}

/** 纯策略（单测锁定）：是否已全部缓存（完成态不再提供「缓存」动作） */
internal fun bookCacheDone(status: BookCacheStatus): Boolean =
    !status.running && status.total > 0 && status.cached >= status.total

/**
 * 详情页「统一缓存条」对外入口（book-info-unified-cache AD-01）。
 *
 * 类型判定在此**异步**完成（书源视频身份 + 目录数），调用方无需自己算：
 * - 视频身份 = `Book.type` 位 或 书源 `isVideoSource`（JS 单文件源常见 `bookSourceType=0`，运行时才写 type）
 * - 无目录（章节数 0）或本地书 ⇒ 不渲染
 */
@Composable
fun BookCacheBar(
    book: Book,
    accent: Color,
    inShelf: Boolean,
    onAddShelf: () -> Unit,
    palette: AppManagementPalette = rememberAppManagementPalette(),
) {
    // 首帧用静态身份（避免等待 IO 造成布局跳动）；随后按书源身份 + 目录数校正
    var kind by remember(book.bookUrl) {
        mutableStateOf(
            CacheBarKind.of(
                isVideo = book.isVideo,
                isAudio = book.isAudio,
                isImage = book.isImage,
                isLocal = book.isLocal,
                hasToc = true,
            )
        )
    }
    LaunchedEffect(book.bookUrl) {
        kind = withContext(Dispatchers.IO) {
            val sourceVideo = !book.isVideo &&
                (book.getBookSource()?.isVideoSource(book.type) == true)
            val tocCount = appDb.bookChapterDao.getChapterCount(book.bookUrl)
            CacheBarKind.of(
                isVideo = book.isVideo || sourceVideo,
                isAudio = book.isAudio,
                isImage = book.isImage,
                isLocal = book.isLocal,
                hasToc = tocCount > 0,
            )
        }
    }
    BookCacheBarForKind(
        book = book,
        kind = kind,
        accent = accent,
        inShelf = inShelf,
        onAddShelf = onAddShelf,
        palette = palette,
    )
}

/**
 * 按 `bookUrl` 自取书的变体（沉浸式详情页 `BookInfoUiState` 只带 bookUrl，不持有 Book 实例）。
 *
 * 只在进入时查一次库；先查书架库，未入架回退搜索书（否则搜索书详情页永远没有缓存条）。
 */
@Composable
fun BookCacheBar(
    bookUrl: String,
    accent: Color,
    inShelf: Boolean,
    onAddShelf: () -> Unit,
    palette: AppManagementPalette = rememberAppManagementPalette(),
) {
    var book by remember(bookUrl) { mutableStateOf<Book?>(null) }
    LaunchedEffect(bookUrl) {
        if (bookUrl.isBlank()) return@LaunchedEffect
        book = withContext(Dispatchers.IO) {
            appDb.bookDao.getBook(bookUrl) ?: appDb.searchBookDao.getSearchBook(bookUrl)?.toBook()
        }
    }
    book?.let { loaded ->
        BookCacheBar(
            book = loaded,
            accent = accent,
            inShelf = inShelf,
            onAddShelf = onAddShelf,
            palette = palette,
        )
    }
}

/**
 * 详情页「统一缓存条」（book-info-unified-cache AD-01）—— 类型已确定后的实现。
 *
 * 一张卡覆盖全部可缓存类型：视频 → `VideoCacheKernel`、音频 → `AudioCacheTaskManager`、
 * 文本/图片/文件 → `CacheBook`（逐章缓存）。`CacheBarKind.UNSUPPORTED`（本地书 / 无目录）不渲染。
 */
@Composable
private fun BookCacheBarForKind(
    book: Book,
    kind: CacheBarKind,
    accent: Color,
    inShelf: Boolean,
    onAddShelf: () -> Unit,
    palette: AppManagementPalette,
) {
    if (kind == CacheBarKind.UNSUPPORTED) return
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val status = rememberBookCacheStatus(book, kind)
    val percent = bookCachePercent(status.cached, status.total)
    val done = bookCacheDone(status)

    AppManagementCard(palette = palette, modifier = Modifier.fillMaxWidth()) {
        Column(
            modifier = Modifier.padding(horizontal = 12.dp, vertical = 10.dp),
            verticalArrangement = Arrangement.spacedBy(6.dp),
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(
                    text = if (status.total > 0) {
                        countText(kind, status.cached, status.total)
                    } else {
                        stringResource(R.string.book_info_video_cache_empty)
                    } + if (status.failed > 0) {
                        stringResource(R.string.cache_manage_video_failed_suffix, status.failed)
                    } else "",
                    color = palette.settings.primaryText,
                    fontSize = 13.sp,
                    fontFamily = palette.settings.bodyFontFamily,
                    modifier = Modifier.weight(1f),
                )
                Text(
                    text = when {
                        status.running -> stringResource(R.string.pause)
                        done -> stringResource(R.string.book_info_video_cache_done)
                        else -> stringResource(R.string.cache_manage_video_start)
                    },
                    color = if (done) palette.settings.secondaryText else accent,
                    fontSize = 13.sp,
                    fontFamily = palette.settings.bodyFontFamily,
                    modifier = Modifier
                        .clip(RoundedCornerShape(8.dp))
                        .clickable(enabled = status.running || !done) {
                            if (status.running) {
                                stopCache(context, book, kind)
                            } else {
                                scope.launch {
                                    startCache(context, book, kind, onAddShelf)
                                }
                            }
                        }
                        .padding(horizontal = 10.dp, vertical = 4.dp),
                )
            }
            if (status.running) {
                // 轻量进度条（避免依赖 M3 LinerProgressIndicator 的版本差异）
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(3.dp)
                        .clip(RoundedCornerShape(2.dp))
                        .background(Color(palette.settings.rowPressed))
                ) {
                    Box(
                        modifier = Modifier
                            .fillMaxWidth(percent / 100f)
                            .height(3.dp)
                            .background(accent)
                    )
                }
                Text(
                    text = stringResource(
                        R.string.cache_manage_video_caching,
                        status.cached,
                        status.total,
                    ),
                    color = palette.settings.secondaryText,
                    fontSize = 11.sp,
                    fontFamily = palette.settings.bodyFontFamily,
                )
                Spacer(modifier = Modifier.height(0.dp))
            }
        }
    }
}

@Composable
private fun countText(kind: CacheBarKind, cached: Int, total: Int): String = when (kind) {
    CacheBarKind.VIDEO, CacheBarKind.AUDIO ->
        stringResource(R.string.book_info_video_cache_count, cached, total)
    else ->
        stringResource(R.string.book_info_cache_count_chapters, cached, total)
}

/**
 * 状态聚合（AD-03）：视频/音频订阅 StateFlow；文本/图片/文件按目录扫描 + `CacheBook` 模型。
 *
 * 文本类扫描每 1200ms 一轮（`CacheBook` 无 StateFlow，详情页停留短、扫描为文件系统列举，开销可控）。
 */
@Composable
private fun rememberBookCacheStatus(book: Book, kind: CacheBarKind): BookCacheStatus {
    val videoStates by VideoCacheKernel.states.collectAsState()
    val audioStates by AudioCacheTaskManager.states.collectAsState()
    var scanned by remember(book.bookUrl, kind) { mutableStateOf(BookCacheStatus()) }

    LaunchedEffect(book.bookUrl, kind) {
        if (kind == CacheBarKind.VIDEO) {
            // 进入详情页校准一次真实文件索引（其余时刻只读内存索引）
            withContext(Dispatchers.IO) { VideoCacheKernel.refreshIndex(book) }
        }
    }
    LaunchedEffect(book.bookUrl, kind) {
        if (kind == CacheBarKind.TEXT || kind == CacheBarKind.IMAGE) {
            while (true) {
                scanned = scanChapterCache(book)
                delay(TEXT_CACHE_POLL_MS)
            }
        }
    }
    return when (kind) {
        CacheBarKind.VIDEO -> videoStates[book.bookUrl]?.let {
            BookCacheStatus(it.cached, it.total, it.running, it.failed)
        } ?: scanned
        CacheBarKind.AUDIO -> audioStates[book.bookUrl]?.let {
            BookCacheStatus(it.completedChapters, it.totalChapters, it.active, 0)
        } ?: scanned
        CacheBarKind.IMAGE, CacheBarKind.TEXT -> scanned
        CacheBarKind.UNSUPPORTED -> scanned
    }
}

private suspend fun scanChapterCache(book: Book): BookCacheStatus = withContext(Dispatchers.IO) {
    val chapters = appDb.bookChapterDao.getChapterList(book.bookUrl)
    if (chapters.isEmpty()) return@withContext BookCacheStatus()
    val names = BookHelp.getChapterFiles(book)
    val cached = chapters.count { CachedChapterResolver.isCached(book, it, names) }
    val model = CacheBook.cacheBookMap[book.bookUrl]
    BookCacheStatus(
        cached = cached,
        total = chapters.size,
        running = model?.isRun() == true,
        failed = 0,
    )
}

private suspend fun startCache(
    context: Context,
    book: Book,
    kind: CacheBarKind,
    onAddShelf: () -> Unit,
) {
    when (kind) {
        CacheBarKind.VIDEO -> ensureInShelfThenStartVideoCache(context, book, onAddShelf)
        CacheBarKind.AUDIO -> {
            val targets = withContext(Dispatchers.IO) { audioCacheTargets(book) }
            if (targets.isEmpty()) return
            AudioCacheTaskManager.start(
                book = book,
                chapters = targets,
                resolver = { b, c -> AudioMediaRequestResolver.resolve(context, b, c) },
            )
        }
        CacheBarKind.TEXT, CacheBarKind.IMAGE -> {
            if (!ensureInShelf(context, book, onAddShelf)) return
            val total = withContext(Dispatchers.IO) {
                appDb.bookChapterDao.getChapterList(book.bookUrl).size
            }
            if (total <= 0) return
            CacheBook.start(context, book, 0, total - 1)
        }
        CacheBarKind.UNSUPPORTED -> Unit
    }
}

private fun stopCache(context: Context, book: Book, kind: CacheBarKind) {
    when (kind) {
        CacheBarKind.VIDEO -> VideoCacheKernel.stop(context, book.bookUrl)
        CacheBarKind.AUDIO -> AudioCacheTaskManager.cancel(book.bookUrl)
        CacheBarKind.TEXT, CacheBarKind.IMAGE -> CacheBook.remove(context, book.bookUrl)
        CacheBarKind.UNSUPPORTED -> Unit
    }
}

private suspend fun audioCacheTargets(book: Book) = withContext(Dispatchers.IO) {
    appDb.bookChapterDao.getChapterList(book.bookUrl)
        .filterNot { it.isVolume }
        .filterNot { io.legado.app.help.exoplayer.ExoPlayerHelper.isMediaCached(it.resourceUrl) }
}

/**
 * 视频缓存启动前置：未入架时先入架并等待入库（`VideoCacheService` 要求书与目录均在库）。
 */
internal suspend fun ensureInShelfThenStartVideoCache(
    context: Context,
    book: Book,
    onAddShelf: () -> Unit,
): Boolean {
    if (!ensureInShelf(context, book, onAddShelf)) return false
    VideoCacheKernel.start(context, book.bookUrl, from = 0, to = -1)
    return true
}

private suspend fun ensureInShelf(
    context: Context,
    book: Book,
    onAddShelf: () -> Unit,
): Boolean {
    val stored = withContext(Dispatchers.IO) { appDb.bookDao.getBook(book.bookUrl) }
    if (stored != null) return true
    onAddShelf()
    return withTimeoutOrNull(IN_SHELF_WAIT_MS) {
        while (withContext(Dispatchers.IO) { appDb.bookDao.getBook(book.bookUrl) } == null) {
            delay(200)
        }
        true
    } ?: false
}

/** 入架等待上限（入库 + 目录加载通常 < 2s，留足弱网余量） */
internal const val IN_SHELF_WAIT_MS = 8_000L

/** 文本/图片缓存进度轮询间隔（`CacheBook` 无 StateFlow） */
private const val TEXT_CACHE_POLL_MS = 1_200L
