package io.legado.app.ui.book.explore

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.itemsIndexed
import androidx.compose.foundation.lazy.grid.rememberLazyGridState
import androidx.compose.foundation.lazy.staggeredgrid.LazyVerticalStaggeredGrid
import androidx.compose.foundation.lazy.staggeredgrid.StaggeredGridCells
import androidx.compose.foundation.lazy.staggeredgrid.itemsIndexed
import androidx.compose.foundation.lazy.staggeredgrid.rememberLazyStaggeredGridState
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.derivedStateOf
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.lifecycle.Lifecycle
import io.legado.app.R
import io.legado.app.data.entities.SearchBook
import io.legado.app.help.config.AppConfig
import io.legado.app.ui.main.bookshelf.compose.BookshelfListItemStyle
import io.legado.app.ui.main.bookshelf.compose.rememberBookshelfListRenderConfig
import io.legado.app.ui.widget.compose.SearchBookListItem
import io.legado.app.ui.widget.compose.SearchBookPreviewOverlay
import io.legado.app.ui.widget.compose.SearchBookPreviewState
import io.legado.app.utils.stableSearchBookKey
import io.legado.app.ui.theme.bodyTertiary

/**
 * 单源发现页网格/瀑布布局（video-cache-and-multiep R11 / V7）。
 *
 * 仅承载 `2=瀑布 / 3=三列 / 4=双列` 三种布局；`1=列表` 继续走
 * [ExploreShowComposeScreen] 的既有 LazyColumn 路径（零回归）。
 *
 * @param layoutMode 取自 `AppConfig.discoveryPageLayout`（自适应 1..4）
 */
@Composable
fun ExploreShowGridScreen(
    books: List<SearchBook>,
    layoutMode: Int,
    isLoading: Boolean,
    hasMore: Boolean,
    errorMessage: String?,
    scrollToTopSignal: Int,
    bookshelfTick: Int,
    isInBookshelf: (SearchBook) -> Boolean,
    lifecycle: Lifecycle,
    onBookClick: (SearchBook) -> Unit,
    onBookMore: (SearchBook) -> Unit,
    onLoadMore: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val context = LocalContext.current
    val renderConfig = rememberBookshelfListRenderConfig()
    val palette = renderConfig.palette
    val rounded = AppConfig.bookshelfListItemStyle == BookshelfListItemStyle.RoundedCard
    var previewState by remember { mutableStateOf<SearchBookPreviewState?>(null) }
    val columns = ExploreShowLayout.columns(layoutMode)
    val item: @Composable (SearchBook) -> Unit = { book ->
        val inBookshelf = remember(book.bookUrl, bookshelfTick) { isInBookshelf(book) }
        SearchBookListItem(
            book = book,
            inBookshelf = inBookshelf,
            rounded = rounded,
            renderConfig = renderConfig,
            lifecycle = lifecycle,
            onClick = { onBookClick(book) },
            onMore = { onBookMore(book) },
            onPreview = { bounds -> previewState = SearchBookPreviewState(book, bounds) },
        )
    }

    Box(modifier = modifier.fillMaxSize()) {
        if (ExploreShowLayout.isWaterfall(layoutMode)) {
            val gridState = rememberLazyStaggeredGridState()
            val shouldLoadMore by remember(books, hasMore, isLoading) {
                derivedStateOf {
                    if (!hasMore || isLoading || books.isEmpty()) return@derivedStateOf false
                    val last = gridState.layoutInfo.visibleItemsInfo.lastOrNull()?.index ?: -1
                    last >= books.lastIndex - 2
                }
            }
            LaunchedEffect(shouldLoadMore) { if (shouldLoadMore) onLoadMore() }
            LaunchedEffect(scrollToTopSignal) { if (scrollToTopSignal > 0) gridState.scrollToItem(0) }
            LazyVerticalStaggeredGrid(
                columns = StaggeredGridCells.Fixed(columns),
                state = gridState,
                modifier = Modifier.fillMaxSize(),
                contentPadding = PaddingValues(start = 8.dp, top = 8.dp, end = 8.dp, bottom = 16.dp),
                horizontalArrangement = Arrangement.spacedBy(6.dp),
                verticalItemSpacing = 6.dp,
            ) {
                itemsIndexed(
                    items = books,
                    key = { _, book -> book.stableSearchBookKey() },
                    contentType = { _, _ -> "explore_show_book_grid" },
                ) { _, book -> item(book) }
                if (isLoading || errorMessage != null) {
                    item(
                        key = "explore_show_grid_footer",
                        span = androidx.compose.foundation.lazy.staggeredgrid.StaggeredGridItemSpan.FullLine,
                    ) {
                        ExploreShowStatusRow(
                            loading = isLoading,
                            message = errorMessage?.let { context.getString(R.string.load_error_retry) },
                            palette = palette,
                            onClick = onLoadMore,
                        )
                    }
                }
            }
        } else {
            val gridState = rememberLazyGridState()
            val shouldLoadMore by remember(books, hasMore, isLoading) {
                derivedStateOf {
                    if (!hasMore || isLoading || books.isEmpty()) return@derivedStateOf false
                    val last = gridState.layoutInfo.visibleItemsInfo.lastOrNull()?.index ?: -1
                    last >= books.lastIndex - 2
                }
            }
            LaunchedEffect(shouldLoadMore) { if (shouldLoadMore) onLoadMore() }
            LaunchedEffect(scrollToTopSignal) { if (scrollToTopSignal > 0) gridState.scrollToItem(0) }
            LazyVerticalGrid(
                columns = GridCells.Fixed(columns),
                state = gridState,
                modifier = Modifier.fillMaxSize(),
                contentPadding = PaddingValues(start = 8.dp, top = 8.dp, end = 8.dp, bottom = 16.dp),
                horizontalArrangement = Arrangement.spacedBy(6.dp),
                verticalArrangement = Arrangement.spacedBy(6.dp),
            ) {
                itemsIndexed(
                    items = books,
                    key = { _, book -> book.stableSearchBookKey() },
                    contentType = { _, _ -> "explore_show_book_grid" },
                ) { _, book -> item(book) }
                if (isLoading || errorMessage != null) {
                    item(key = "explore_show_grid_footer", span = { androidx.compose.foundation.lazy.grid.GridItemSpan(columns) }) {
                        ExploreShowStatusRow(
                            loading = isLoading,
                            message = errorMessage?.let { context.getString(R.string.load_error_retry) },
                            palette = palette,
                            onClick = onLoadMore,
                        )
                    }
                }
            }
        }
        if (books.isEmpty() && !isLoading && errorMessage == null) {
            Text(
                text = stringResource(R.string.explore_empty),
                color = palette.secondaryText,
                fontFamily = palette.bodyFontFamily,
                modifier = Modifier
                    .align(Alignment.Center)
                    .padding(24.dp),
            )
        }
        SearchBookPreviewOverlay(
            state = previewState,
            renderConfig = renderConfig,
            fragment = null,
            lifecycle = lifecycle,
            onDismissed = { previewState = null },
            onOpen = { book ->
                previewState = null
                onBookClick(book)
            },
            modifier = Modifier.fillMaxSize(),
        )
    }
}
