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
import io.legado.app.help.book.getBookSource
import io.legado.app.help.book.isVideo
import io.legado.app.help.source.isVideoSource
import io.legado.app.service.kernel.VideoCacheKernel
import io.legado.app.ui.widget.compose.AppManagementCard
import io.legado.app.ui.widget.compose.AppManagementPalette
import io.legado.app.ui.widget.compose.rememberAppManagementPalette
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import kotlinx.coroutines.withTimeoutOrNull

/**
 * 纯策略（单测锁定）：缓存条仅对视频书展示。
 *
 * 传入的 `isVideo` 是**复合身份**：`Book.type` 的视频位 或 书源类型为视频（JS 源常见）。
 */
internal fun videoCacheBarVisible(isVideo: Boolean): Boolean = isVideo

/**
 * 纯策略（单测锁定）：进度百分比；total<=0 时为 0，越界钳到 0..100。
 */
internal fun videoCacheBarPercent(cached: Int, total: Int): Int {
    if (total <= 0) return 0
    return (cached * 100 / total).coerceIn(0, 100)
}

/**
 * 纯策略（单测锁定）：是否已全部缓存完（完成态）。
 *
 * 完成态时右侧动作不再提供「缓存」：全集已落盘，重复点击只会空跑一轮，
 * 用户看到「缓存」按钮会误以为上次失败。清理入口仍在缓存管理页（R3）。
 */
internal fun videoCacheBarDone(cached: Int, total: Int, running: Boolean): Boolean =
    !running && total > 0 && cached >= total

/**
 * 详情页「快速缓存条」（video-cache-and-multiep R2 / AD-10）。
 *
 * 设计为**单一组件**供三种详情页模式共用；当前先接入现代/沉浸两套 Compose 详情页。
 * 仅对视频书源展示（非视频类型的缓存入口仍在既有位置，避免扩大回归面）。
 *
 * 交互：进度 + 右侧「缓存/暂停」；点击缓存时若未入架先自动入架（需求 R2-1）。
 */
@Composable
fun VideoCacheBar(
    book: Book,
    accent: androidx.compose.ui.graphics.Color,
    inShelf: Boolean,
    onAddShelf: () -> Unit,
    palette: AppManagementPalette = rememberAppManagementPalette(),
) {
    // 视频身份双判：`Book.type` 位（静态声明源/运行时已写入）或**书源类型为视频**
    // （JS 单文件源常 `bookSourceType=0`，视频身份在运行时才写入 book.type ⇒ 只看 type 会漏）
    var isVideoBook by remember(book.bookUrl) { mutableStateOf(book.isVideo) }
    LaunchedEffect(book.bookUrl) {
        if (!book.isVideo) {
            isVideoBook = withContext(Dispatchers.IO) {
                book.getBookSource()?.isVideoSource(book.type) == true
            }
        }
    }
    if (!videoCacheBarVisible(isVideoBook)) return
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val states by VideoCacheKernel.states.collectAsState()
    val progress = states[book.bookUrl]
    LaunchedEffect(book.bookUrl) {
        // 进入详情页校准一次真实文件索引（UI 其余时刻只读索引，零额外 IO）
        withContext(Dispatchers.IO) { VideoCacheKernel.refreshIndex(book) }
    }
    val total = progress?.total ?: 0
    val cached = progress?.cached ?: 0
    val running = progress?.running == true
    val percent = videoCacheBarPercent(cached, total)
    val done = videoCacheBarDone(cached, total, running)
    val failed = progress?.failed ?: 0

    AppManagementCard(
        palette = palette,
        modifier = Modifier.fillMaxWidth(),
    ) {
        Column(
            modifier = Modifier.padding(horizontal = 12.dp, vertical = 10.dp),
            verticalArrangement = Arrangement.spacedBy(6.dp),
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(
                    text = (if (total > 0) {
                        stringResource(R.string.book_info_video_cache_count, cached, total)
                    } else {
                        stringResource(R.string.book_info_video_cache_empty)
                    }) + if (failed > 0) {
                        // R2「可看进度与结果」：失败集数必须可见，否则用户只看到进度停滞
                        stringResource(R.string.cache_manage_video_failed_suffix, failed)
                    } else "",
                    color = palette.settings.primaryText,
                    fontSize = 13.sp,
                    fontFamily = palette.settings.bodyFontFamily,
                    modifier = Modifier.weight(1f),
                )
                Text(
                    text = when {
                        running -> stringResource(R.string.pause)
                        done -> stringResource(R.string.book_info_video_cache_done)
                        else -> stringResource(R.string.cache_manage_video_start)
                    },
                    color = if (done) palette.settings.secondaryText else accent,
                    fontSize = 13.sp,
                    fontFamily = palette.settings.bodyFontFamily,
                    modifier = Modifier
                        .clip(RoundedCornerShape(8.dp))
                        .clickable(enabled = running || !done) {
                            if (running) {
                                VideoCacheKernel.stop(context, book.bookUrl)
                            } else {
                                // 搜索书（未入库）先入架并等待入库，再启动缓存服务
                                // （服务要求书籍与目录都在库，直接启动会 fail-fast）
                                scope.launch {
                                    ensureInShelfThenStartCache(context, book, onAddShelf)
                                }
                            }
                        }
                        .padding(horizontal = 10.dp, vertical = 4.dp),
                )
            }
            if (running) {
                // 轻量进度条（避免依赖 M3 LinearProgressIndicator 的版本差异）
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
                        cached,
                        total,
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

/**
 * 按 `bookUrl` 自取书的变体（沉浸式详情页 `BookInfoUiState` 只带 bookUrl，不持有 Book 实例）。
 *
 * 只在进入时查一次库；非视频书由 [videoCacheBarVisible] 策略直接空渲染。
 */
@Composable
fun VideoCacheBar(
    bookUrl: String,
    accent: androidx.compose.ui.graphics.Color,
    inShelf: Boolean,
    onAddShelf: () -> Unit,
    palette: AppManagementPalette = rememberAppManagementPalette(),
) {
    var book by remember(bookUrl) { mutableStateOf<Book?>(null) }
    LaunchedEffect(bookUrl) {
        if (bookUrl.isBlank()) return@LaunchedEffect
        // 先查书架库；搜索书（未入架）回退 searchBook，否则详情页缓存条永远不会出现
        book = withContext(Dispatchers.IO) {
            appDb.bookDao.getBook(bookUrl) ?: appDb.searchBookDao.getSearchBook(bookUrl)?.toBook()
        }
    }
    book?.let { loaded ->
        VideoCacheBar(
            book = loaded,
            accent = accent,
            inShelf = inShelf,
            onAddShelf = onAddShelf,
            palette = palette,
        )
    }
}

/**
 * 「点击缓存」前置：书未入库时先入架并等待入库（含目录加载），成功后才启动缓存服务。
 *
 * 为什么必须等待：`VideoCacheService` 启动即校验「书籍 + 目录 + 书源」三者都在库，
 * 未入库直接启动会 fail-fast（缓存永远不开始，用户视为点击无效）。
 *
 * @return true=已启动缓存；false=入架超时（调用方无需额外提示，详情页状态会刷新）
 */
internal suspend fun ensureInShelfThenStartCache(
    context: Context,
    book: Book,
    onAddShelf: () -> Unit,
): Boolean {
    val stored = withContext(Dispatchers.IO) { appDb.bookDao.getBook(book.bookUrl) }
    if (stored == null) {
        onAddShelf()
        val ready = withTimeoutOrNull(IN_SHELF_WAIT_MS) {
            while (withContext(Dispatchers.IO) { appDb.bookDao.getBook(book.bookUrl) } == null) {
                delay(200)
            }
            true
        } ?: false
        if (!ready) return false
    }
    VideoCacheKernel.start(context, book.bookUrl, from = 0, to = -1)
    return true
}

/** 入架等待上限（图书入库 + 目录加载通常 < 2s，留足弱网余量） */
internal const val IN_SHELF_WAIT_MS = 8_000L
