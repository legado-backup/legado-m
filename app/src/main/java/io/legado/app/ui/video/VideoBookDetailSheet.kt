package io.legado.app.ui.video

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.itemsIndexed
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.platform.ComposeView
import androidx.compose.ui.platform.ViewCompositionStrategy
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.delay
import io.legado.app.R
import io.legado.app.data.entities.RssEpisode
import io.legado.app.model.VideoPlay
import io.legado.app.ui.theme.LegadoTheme
import io.legado.app.ui.widget.compose.AppDialogFrame
import io.legado.app.ui.widget.compose.AppUiTokens
import io.legado.app.ui.widget.compose.BookCoverImage
import io.legado.app.ui.widget.compose.ComposeDialogFragment

/**
 * 视频书源详情底部抽屉（video-booksource-multiroute AD-06）
 *
 * 书源模式专属：封面/书名/作者/简介（Book 数据）+ 线路 Tab + 集数列表。
 * 订阅源模式不注入入口（无详情数据，UI 零退化）。
 * 切线路/选集动作与悬浮选择器同源（VideoPlay.switchToRoute / playRssEpisode，
 * 书源模式内部已按源类型分派到卷章切片/章节播放链），选择后关闭抽屉起播。
 *
 * ui-standards：ComposeDialogFragment + AppDialogFrame 规范壳 + LegadoTheme 取色，
 * 禁硬编码色值；简介渲染 TextView 纯文本（Book.intro 富文本由书详情页承载）。
 */
class VideoBookDetailSheet : ComposeDialogFragment() {

    /** 抽屉动作回调（VideoFragment 注入，与悬浮选择器同一动作源） */
    interface Callback {
        fun onDetailRouteSelected(routeIndex: Int)
        fun onDetailEpisodeSelected(episodeIndex: Int, episode: RssEpisode)
    }

    private var actionCallback: Callback? = null

    fun setCallback(callback: Callback?): VideoBookDetailSheet = apply { actionCallback = callback }

    /**
     * 当前播放集下标（书源会话权威字段是 `chapterInVolumeIndex`，不能用 `rssEpisodeIndex`，
     * 否则会错位一集——VideoFragment.updatePositionIndicator 同口径）。
     */
    private fun currentEpisodeIndex(): Int {
        val count = VideoPlay.episodes?.size ?: 0
        return if (VideoPlay.book != null && count > 1) {
            VideoPlay.chapterInVolumeIndex.coerceIn(0, count - 1)
        } else {
            VideoPlay.rssEpisodeIndex.coerceAtLeast(0)
        }
    }

    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View {
        return ComposeView(requireContext()).apply {
            setViewCompositionStrategy(ViewCompositionStrategy.DisposeOnViewTreeLifecycleDestroyed)
            setContent {
                LegadoTheme {
                    AppDialogFrame(
                        title = stringResource(R.string.video_book_detail_title),
                        scrollContent = false,
                        content = { DetailContent() },
                        actions = {}
                    )
                }
            }
        }
    }

    @Composable
    private fun DetailContent() {
        val book = VideoPlay.book ?: return
        val routes = VideoPlay.rssRoutes ?: return
        var selectedRoute by remember { mutableIntStateOf(VideoPlay.rssRouteIndex) }
        // 集数展示顺序：false = 正序（历史行为）；true = 倒序（最新集在前，2026-10-24 用户需求）
        var descending by remember { mutableStateOf(false) }
        // 当前集下标：抽屉打开期间播放会继续（含自动连播），高亮必须跟着走，
        // 否则用户看到「标题已是第 80 集、高亮还停在第 72 集」（真机实证 2026-10-24）。
        var currentEpisode by remember { mutableIntStateOf(currentEpisodeIndex()) }
        LaunchedEffect(Unit) {
            while (true) {
                delay(CURRENT_EPISODE_POLL_MS)
                currentEpisode = currentEpisodeIndex()
            }
        }
        // 弹层取色单源（AD-06）：走 AppDialogStyle 直色（ThemeStore 链），禁 M3 派生色
        val palette = AppUiTokens.dialogStyle()
        Column(Modifier.padding(horizontal = 16.dp)) {
            // 上半区：封面 + 书名 + 作者
            Row(verticalAlignment = Alignment.Top) {
                BookCoverImage(
                    book = book,
                    modifier = Modifier
                        .width(72.dp)
                        .clip(RoundedCornerShape(8.dp))
                )
                Column(Modifier.padding(start = 12.dp)) {
                    Text(
                        text = book.name,
                        style = MaterialTheme.typography.titleMedium,
                        color = palette.primaryText,
                        maxLines = 2,
                        overflow = TextOverflow.Ellipsis
                    )
                    if (book.getRealAuthor().isNotEmpty()) {
                        Text(
                            text = book.getRealAuthor(),
                            style = MaterialTheme.typography.bodySmall,
                            color = palette.secondaryText,
                            modifier = Modifier.padding(top = 4.dp)
                        )
                    }
                }
            }
            // 简介区（可滚动，最多 160dp）
            if (book.intro?.isNotBlank() == true) {
                Text(
                    text = book.intro!!,
                    style = MaterialTheme.typography.bodySmall,
                    color = palette.secondaryText,
                    maxLines = Int.MAX_VALUE,
                    overflow = TextOverflow.Ellipsis,
                    modifier = Modifier
                        .padding(top = 8.dp)
                        .heightIn(max = 160.dp)
                        .verticalScroll(rememberScrollState())
                )
            }
            // 线路 Tab（多线路时显示）
            if (routes.size > 1) {
                Text(
                    text = stringResource(R.string.video_route_label),
                    style = MaterialTheme.typography.labelMedium,
                    color = palette.secondaryText,
                    modifier = Modifier.padding(top = 12.dp, bottom = 4.dp)
                )
                LazyRow(
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    items(routes.size) { index ->
                        val selected = index == selectedRoute
                        Box(
                            modifier = Modifier
                                .clip(RoundedCornerShape(16.dp))
                                .background(
                                    if (selected) palette.accent
                                    else palette.fieldSurface
                                )
                                .clickable {
                                    selectedRoute = index
                                    actionCallback?.onDetailRouteSelected(index)
                                    dismiss()
                                }
                                .padding(horizontal = 14.dp, vertical = 6.dp)
                        ) {
                            Text(
                                text = routes.getOrNull(index)?.name ?: "",
                                style = MaterialTheme.typography.labelLarge,
                                color = if (selected) palette.onAccent
                                else palette.secondaryText
                            )
                        }
                    }
                }
            }
            // 集数列表（当前线路）；2026-10-24 用户需求：支持正序 / 倒序一键切换
            val episodes = routes.getOrNull(selectedRoute)?.episodes.orEmpty()
            Row(
                verticalAlignment = Alignment.CenterVertically,
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = 12.dp, bottom = 4.dp)
            ) {
                Text(
                    text = stringResource(R.string.video_episode_label),
                    style = MaterialTheme.typography.labelMedium,
                    color = palette.secondaryText,
                    modifier = Modifier.weight(1f)
                )
                // 文案显示「点击后切到」的顺序，符合直觉；仅改展示顺序，点击仍按真实集下标派发
                Text(
                    text = stringResource(
                        if (descending) R.string.video_episode_order_asc
                        else R.string.video_episode_order_desc
                    ),
                    style = MaterialTheme.typography.labelMedium,
                    color = palette.accent,
                    modifier = Modifier
                        .clip(RoundedCornerShape(12.dp))
                        .clickable { descending = !descending }
                        .padding(horizontal = 10.dp, vertical = 4.dp)
                )
            }
            val displayEpisodes = if (descending) episodes.asReversed() else episodes
            LazyVerticalGrid(
                columns = GridCells.Adaptive(minSize = 64.dp),
                verticalArrangement = Arrangement.spacedBy(6.dp),
                horizontalArrangement = Arrangement.spacedBy(6.dp),
                modifier = Modifier
                    .fillMaxWidth()
                    .heightIn(max = 240.dp)
            ) {
                itemsIndexed(displayEpisodes) { displayIndex, episode ->
                    // 高亮按**原始下标**比较（倒序展示时 displayIndex 与真实集下标相反）
                    val rawIndex = if (descending) episodes.lastIndex - displayIndex else displayIndex
                    val selected = rawIndex == currentEpisode
                    Box(
                        modifier = Modifier
                            .clip(RoundedCornerShape(8.dp))
                            .background(
                                if (selected) palette.accent.copy(alpha = 0.15f)
                                else palette.fieldSurface
                            )
                            .clickable {
                                // 倒序展示下仍用**原始下标**（rawIndex）派发，保证播的是用户点的这一集
                                if (rawIndex in episodes.indices) {
                                    actionCallback?.onDetailEpisodeSelected(rawIndex, episode)
                                }
                                dismiss()
                            }
                            .padding(vertical = 8.dp),
                        contentAlignment = Alignment.Center
                    ) {
                        Text(
                            text = episode.title,
                            style = MaterialTheme.typography.labelMedium,
                            color = if (selected) palette.accent else palette.primaryText,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis
                        )
                    }
                }
            }
        }
    }

    private companion object {
        /** 高亮跟随播放进度的轮询间隔（500ms 足够，自动连播切换时不至于明显滞后） */
        const val CURRENT_EPISODE_POLL_MS = 500L
    }
}
