package io.legado.app.ui.book.explore

import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.background
import androidx.compose.foundation.combinedClickable
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Rect
import androidx.compose.ui.hapticfeedback.HapticFeedbackType
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalHapticFeedback
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.Lifecycle
import io.legado.app.R
import io.legado.app.data.entities.SearchBook
import io.legado.app.help.config.AppConfig
import io.legado.app.ui.main.bookshelf.compose.BookshelfListRenderConfig
import io.legado.app.ui.widget.compose.BookCoverImage
import io.legado.app.ui.widget.compose.appSettingPanelBackground
import io.legado.app.ui.widget.image.CoverImageView
import io.legado.app.utils.BookIntroUtils

/**
 * 发现页网格卡（explore-grid-card-layout）：**图在上、文字在下**的列式卡片。
 *
 * 与订阅源文章网格同构（`RssArticleGridRow`）：封面占满列宽 → 书名 → 作者 →（仅瀑布）简介。
 * 三种网格布局（瀑布 / 双列 / 三列）共用，**不再渲染行尾 ⋮**——⋮ 提供的能力由
 * 「单击=书籍详情（详情页可加入书架）」与「长按=预览浮层」承接（设计 AD-02）。
 *
 * 单独成组件而非复用 [io.legado.app.ui.widget.compose.SearchBookListItem]：
 * 后者基于 `BookListCardSurface`（`RowScope` + 固定封面宽），窄列宽下会被压缩。
 *
 * @param columns 当前网格列数，仅用于字号分档（三列收窄），见 [ExploreShowLayout.gridTitleFontSize]
 * @param introMaxLines 简介最大行数：`Int.MAX_VALUE` = 完整显示（瀑布流，用于高度错落），0 = 不显示（双列/三列）
 */
@OptIn(ExperimentalFoundationApi::class)
@Composable
fun ExploreShowGridCard(
    book: SearchBook,
    inBookshelf: Boolean,
    columns: Int,
    introMaxLines: Int,
    rounded: Boolean,
    renderConfig: BookshelfListRenderConfig,
    lifecycle: Lifecycle,
    onClick: () -> Unit,
    onPreview: (Rect?) -> Unit,
    modifier: Modifier = Modifier,
) {
    val context = LocalContext.current
    val palette = renderConfig.palette
    val haptic = LocalHapticFeedback.current
    // 长按预览浮层以封面实际位置为动画起点（与列表行卡片同一机制）；为空则浮层按默认位置居中
    val coverBounds = remember(book.bookUrl, book.origin, book.coverUrl) {
        mutableStateOf<Rect?>(null)
    }
    val shape = RoundedCornerShape(if (rounded) palette.panelRadius else 4.dp)
    Column(
        modifier = modifier
            .fillMaxWidth()
            .clip(shape)
            .then(
                if (rounded) {
                    Modifier.appSettingPanelBackground(
                        normalColor = palette.rowColor,
                        panelImage = renderConfig.panelImage,
                        borderColor = palette.borderColor,
                        radiusPx = palette.panelRadiusPx
                    )
                } else {
                    Modifier
                }
            )
            .combinedClickable(
                onClick = onClick,
                onLongClick = {
                    // 与行卡片一致：长按先给触觉确认，再弹预览
                    haptic.performHapticFeedback(HapticFeedbackType.LongPress)
                    onPreview(coverBounds.value)
                }
            )
            // 圆角卡与书架圆角卡口径一致（内衬 6dp）；经典卡文字直接贴封面下沿
            .padding(if (rounded) 6.dp else 0.dp)
    ) {
        Box(
            modifier = Modifier
                .fillMaxWidth()
                // 固定 3:4 竖版：封面缺失/加载失败时高度不塌陷（与订阅源网格卡同口径）
                .aspectRatio(ExploreShowLayout.GRID_COVER_ASPECT_RATIO)
        ) {
            BookCoverImage(
                book = book,
                modifier = Modifier.fillMaxSize(),
                style = CoverImageView.CoverStyle.GRID,
                loadOnlyWifi = AppConfig.loadCoverOnlyWifi,
                lifecycle = lifecycle,
                preferThumb = true,
                onBoundsChanged = { coverBounds.value = it }
            )
            if (inBookshelf) {
                // 已入架角标：与行卡片同款小圆点（仅位置随列宽变化）
                Box(
                    modifier = Modifier
                        .align(Alignment.TopEnd)
                        .padding(4.dp)
                        .clip(CircleShape)
                        .background(palette.accent)
                        .size(8.dp)
                )
            }
        }
        Spacer(modifier = Modifier.height(4.dp))
        Text(
            text = book.name,
            color = palette.primaryText,
            fontSize = ExploreShowLayout.gridTitleFontSize(columns).sp,
            fontWeight = FontWeight.Medium,
            fontFamily = palette.titleFontFamily,
            maxLines = ExploreShowLayout.GRID_TITLE_MAX_LINES,
            overflow = TextOverflow.Ellipsis
        )
        if (!book.author.isNullOrBlank()) {
            Spacer(modifier = Modifier.height(2.dp))
            Text(
                text = context.getString(R.string.author_show, book.author),
                color = palette.secondaryText,
                fontSize = 11.sp,
                fontFamily = palette.bodyFontFamily,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis
            )
        }
        if (introMaxLines > 0) {
            val intro = remember(book.intro) { BookIntroUtils.listIntro(book.intro) }
            if (!intro.isNullOrBlank()) {
                Spacer(modifier = Modifier.height(4.dp))
                Text(
                    text = intro,
                    modifier = Modifier.fillMaxWidth(),
                    color = palette.secondaryText,
                    fontSize = 11.sp,
                    lineHeight = 16.sp,
                    fontFamily = palette.bodyFontFamily,
                    // 瀑布流不限行：简介完整撑开卡片 ⇒ 真实高度错落（与订阅源瀑布流同构）
                    maxLines = introMaxLines,
                    overflow = TextOverflow.Ellipsis
                )
            }
        }
    }
}
