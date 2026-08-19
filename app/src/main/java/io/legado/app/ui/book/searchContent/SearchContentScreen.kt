package io.legado.app.ui.book.searchContent

import android.text.TextUtils
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyListState
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import io.legado.app.R
import io.legado.app.ui.widget.components.EmptyStatePlaceholder
import io.legado.app.ui.widget.components.LazyListFastScroller
import io.legado.app.ui.widget.components.ListCard

/**
 * 全文搜索结果 Compose 列表（P3-3 §3.2 全文搜索 Lazy 化）。
 * 壳 [SearchContentActivity] 保留搜索 Job/ViewModel/底部跳转栏，本 Screen 只承载结果列表。
 *
 * 设计要点（对齐 P3-3 design §3.2/§5.1）：
 * - 数据源：壳传入结果快照 [results]（由壳 mutableStateOf 包装触发重组），非重新造轮子
 * - 差分：`LazyColumn` + `itemsIndexed`（结果按命中顺序追加，无去重需求 → 用 index 作为稳定 key）
 * - Item：复用公共组件 `ListCard`（AD-21）；命中词高亮复用 `SearchResult.getHtmlCompat`
 * - 滚动增强：复用 `LazyListFastScroller`（替代原 FastScrollRecyclerView）
 * - 空态：复用 `EmptyStatePlaceholder`（AD-21）
 * - [listState] 回传壳，供底部"到顶部/到底部"按钮调用
 */
@Composable
fun SearchContentScreen(
    results: List<SearchResult>,
    durChapterIndex: Int,
    textColor: String,
    accentColor: String,
    onResultClick: (SearchResult, Int) -> Unit,
    onListStateReady: (LazyListState) -> Unit = {},
) {
    val listState = rememberLazyListState()
    LaunchedEffect(listState) {
        onListStateReady(listState)
    }

    if (results.isEmpty()) {
        EmptyStatePlaceholder(
            icon = Icons.Default.Search,
            title = LocalContext.current.getString(R.string.search_content_empty),
            modifier = Modifier.fillMaxSize()
        )
        return
    }

    Box(modifier = Modifier.fillMaxSize()) {
        LazyColumn(
            state = listState,
            modifier = Modifier.fillMaxSize()
        ) {
            itemsIndexed(results) { index, result ->
                SearchContentResultItem(
                    result = result,
                    textColor = textColor,
                    accentColor = accentColor,
                    isCurrentChapter = result.chapterIndex == durChapterIndex,
                    onClick = { onResultClick(result, index) }
                )
            }
        }
        LazyListFastScroller(
            state = listState,
            modifier = Modifier.align(Alignment.CenterEnd)
        )
    }
}

@Composable
private fun SearchContentResultItem(
    result: SearchResult,
    textColor: String,
    accentColor: String,
    isCurrentChapter: Boolean,
    onClick: () -> Unit,
) {
    ListCard(
        onClick = onClick,
        containerColor = MaterialTheme.colorScheme.surfaceContainer
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp, vertical = 8.dp)
        ) {
            val spanned = remember(result, textColor, accentColor) {
                result.getHtmlCompat(textColor, accentColor)
            }
            // getHtmlCompat 返回含颜色的 Spanned（命中词高亮），用 TextView 桥接渲染，语义与原版一致
            AndroidView(
                factory = { ctx ->
                    androidx.appcompat.widget.AppCompatTextView(ctx).apply {
                        maxLines = 3
                        ellipsize = TextUtils.TruncateAt.END
                    }
                },
                update = { it.text = spanned },
                modifier = Modifier.fillMaxWidth()
            )
            if (isCurrentChapter) {
                HorizontalDivider(
                    modifier = Modifier.padding(vertical = 6.dp),
                    color = MaterialTheme.colorScheme.outlineVariant
                )
                Text(
                    text = result.chapterTitle,
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.primary,
                    fontWeight = FontWeight.Bold,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )
            }
        }
    }
}