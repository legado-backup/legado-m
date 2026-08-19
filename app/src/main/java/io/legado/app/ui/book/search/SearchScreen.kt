package io.legado.app.ui.book.search

import android.view.ViewGroup
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyListState
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.derivedStateOf
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import io.legado.app.R
import io.legado.app.data.entities.SearchBook
import io.legado.app.ui.widget.components.AppShapes
import io.legado.app.ui.widget.components.EmptyStatePlaceholder
import io.legado.app.ui.widget.components.LazyListFastScroller
import io.legado.app.ui.widget.components.ListCard
import io.legado.app.ui.widget.components.TagChip
import io.legado.app.ui.widget.image.CoverImageView

/**
 * 搜索结果 Compose 列表（P3-3 §3.1 搜索页 Lazy 化）。
 * 壳 [SearchActivity] 保留 ViewModel/搜索 Job/FAB/输入帮助区，本 Screen 只承载搜索结果主体。
 *
 * 设计要点（对齐 P3-3 design §3.1/§5.1 + AD-P33-04 复杂交互桥接）：
 * - 数据源：壳传入结果快照 [books]（由壳 mutableStateOf 包装触发重组），不重造轮子
 * - 差分：`LazyColumn` + `items(books, key = { it.bookUrl })`（SearchBook.bookUrl 唯一，见 SearchBook.equals/hashCode）
 * - Item：复用 `ListCard`（AD-21）；封面用 `AndroidView(CoverImageView)` 桥接保留 Glide/loadOnlyWifi/名字绘制语义
 *   其余文字/书源数/类型标签走 Compose（AD-P33-04：仅复杂 View 组件桥接，主体原生 Compose）
 * - 滚动增强：`LazyListFastScroller`；触底检测 `derivedStateOf` → 回调壳 [onReachBottom] 加载更多
 * - 空态：`EmptyStatePlaceholder`
 * - [listState] 回传壳，供"到顶/到底"与滚动复位调用
 */
@Composable
fun SearchScreen(
    books: List<SearchBook>,
    loadOnlyWifi: Boolean,
    hasMore: Boolean,
    isInBookshelf: (SearchBook) -> Boolean,
    onBookClick: (SearchBook) -> Unit,
    onListStateReady: (LazyListState) -> Unit = {},
    onReachBottom: () -> Unit = {},
) {
    val listState = rememberLazyListState()
    LaunchedEffect(listState) {
        onListStateReady(listState)
    }

    val latestBooks by rememberUpdatedState(books)
    val latestHasMore by rememberUpdatedState(hasMore)
    val latestOnReachBottom by rememberUpdatedState(onReachBottom)
    // 触底检测：最后可见索引接近末尾且仍可加载更多 → 触发一次加载
    val shouldLoadMore by remember {
        derivedStateOf {
            val count = latestBooks.size
            count > 0 && latestHasMore &&
                listState.layoutInfo.visibleItemsInfo.lastOrNull()?.index == count - 1
        }
    }
    LaunchedEffect(shouldLoadMore) {
        if (shouldLoadMore) {
            latestOnReachBottom()
        }
    }

    if (books.isEmpty()) {
        EmptyStatePlaceholder(
            icon = Icons.Default.Search,
            title = LocalContext.current.getString(R.string.search_result_empty),
            modifier = Modifier.fillMaxSize()
        )
        return
    }

    Box(modifier = Modifier.fillMaxSize()) {
        LazyColumn(
            state = listState,
            modifier = Modifier.fillMaxSize()
        ) {
            items(books.size, key = { index -> books[index].bookUrl }) { index ->
                val book = books[index]
                SearchBookItem(
                    book = book,
                    loadOnlyWifi = loadOnlyWifi,
                    inBookshelf = isInBookshelf(book),
                    onClick = { onBookClick(book) }
                )
            }
        }
        LazyListFastScroller(
            state = listState,
            modifier = Modifier.align(Alignment.CenterEnd)
        )
    }
}

/**
 * 搜索结果条目：忠实复刻 item_search.xml 布局语义。
 * - 左侧封面：`AndroidView(CoverImageView)` 桥接（保留 Glide 加载 + loadOnlyWifi + 缺封名绘制）
 * - 右上书源数徽标：Compose `Surface` 圆角徽标（原 BadgeView）
 * - 已入书架绿点：Compose `Box` 圆点（原 CircleImageView + md_green_600）
 * - 名称/作者/最新章节/简介/类型标签：Compose（原 LabelsBar → FlowRow + TagChip）
 */
@Composable
private fun SearchBookItem(
    book: SearchBook,
    loadOnlyWifi: Boolean,
    inBookshelf: Boolean,
    onClick: () -> Unit,
) {
    val context = LocalContext.current
    val coverParams = remember(book.bookUrl) {
        ViewGroup.LayoutParams(160, 220)
    }
    Box(Modifier.fillMaxWidth()) {
        ListCard(onClick = onClick) {
            Row(Modifier.fillMaxWidth().padding(vertical = 2.dp)) {
                Box(Modifier.width(80.dp).height(110.dp)) {
                    AndroidView(
                        factory = { ctx ->
                            CoverImageView(ctx).apply {
                                layoutParams = coverParams
                            }
                        },
                        update = { it.load(book, loadOnlyWifi) },
                        modifier = Modifier.fillMaxSize()
                    )
                }
                Column(
                    Modifier
                        .weight(1f)
                        .padding(start = 12.dp, top = 2.dp)
                ) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        if (inBookshelf) {
                            Box(
                                Modifier
                                    .size(8.dp)
                                    .background(Color(0xFF4CAF50), AppShapes.Chip)
                            )
                        }
                        Text(
                            text = book.name,
                            style = MaterialTheme.typography.bodyLarge,
                            fontWeight = FontWeight.Medium,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis,
                            modifier = Modifier.padding(start = if (inBookshelf) 6.dp else 0.dp)
                        )
                    }
                    Text(
                        text = context.getString(R.string.author_show, book.author),
                        style = MaterialTheme.typography.bodySmall,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                        modifier = Modifier.padding(top = 2.dp)
                    )
                    book.getKindList().takeIf { it.isNotEmpty() }?.let { kinds ->
                        KindLabels(kinds)
                    }
                    if (!book.latestChapterTitle.isNullOrEmpty()) {
                        Text(
                            text = context.getString(R.string.lasted_show, book.latestChapterTitle),
                            style = MaterialTheme.typography.bodySmall,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis,
                            modifier = Modifier.padding(top = 2.dp)
                        )
                    }
                    Text(
                        text = book.trimIntro(context),
                        style = MaterialTheme.typography.bodySmall,
                        maxLines = 3,
                        overflow = TextOverflow.Ellipsis,
                        modifier = Modifier.padding(top = 2.dp)
                    )
                }
            }
        }
        // 右上书源数徽标（原 BadgeView 语义，Compose 圆角徽标）
        Surface(
            modifier = Modifier
                .align(Alignment.TopEnd)
                .padding(top = 8.dp, end = 8.dp),
            shape = AppShapes.Chip,
            color = MaterialTheme.colorScheme.secondaryContainer,
            contentColor = MaterialTheme.colorScheme.onSecondaryContainer
        ) {
            Text(
                text = book.origins.size.toString(),
                style = MaterialTheme.typography.labelSmall,
                modifier = Modifier.padding(horizontal = 6.dp, vertical = 1.dp)
            )
        }
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun KindLabels(kinds: List<String>) {
    FlowRow(
        modifier = Modifier.padding(top = 2.dp),
        horizontalArrangement = Arrangement.spacedBy(4.dp),
        verticalArrangement = Arrangement.spacedBy(2.dp),
        maxItemsInEachRow = 6
    ) {
        kinds.forEach { Kind -> TagChip(Kind) }
    }
}