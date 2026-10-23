package io.legado.app.ui.book.info.compose

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
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import io.legado.app.R
import io.legado.app.data.entities.Book
import io.legado.app.help.book.isVideo
import io.legado.app.service.kernel.VideoCacheKernel
import io.legado.app.ui.widget.compose.AppManagementCard
import io.legado.app.ui.widget.compose.AppManagementPalette
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

/**
 * 纯策略（单测锁定）：缓存条仅对视频书源展示。
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
    palette: AppManagementPalette,
    accent: androidx.compose.ui.graphics.Color,
    inShelf: Boolean,
    onAddShelf: () -> Unit,
) {
    if (!videoCacheBarVisible(book.isVideo)) return
    val context = LocalContext.current
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
                    text = if (total > 0) {
                        stringResource(R.string.book_info_video_cache_count, cached, total)
                    } else {
                        stringResource(R.string.book_info_video_cache_empty)
                    },
                    color = palette.settings.primaryText,
                    fontSize = 13.sp,
                    fontFamily = palette.settings.bodyFontFamily,
                    modifier = Modifier.weight(1f),
                )
                Text(
                    text = if (running) {
                        stringResource(R.string.pause)
                    } else {
                        stringResource(R.string.cache_manage_video_start)
                    },
                    color = accent,
                    fontSize = 13.sp,
                    fontFamily = palette.settings.bodyFontFamily,
                    modifier = Modifier
                        .clip(RoundedCornerShape(8.dp))
                        .clickable {
                            if (running) {
                                VideoCacheKernel.stop(context, book.bookUrl)
                            } else {
                                if (!inShelf) onAddShelf()
                                VideoCacheKernel.start(context, book.bookUrl, from = 0, to = -1)
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
