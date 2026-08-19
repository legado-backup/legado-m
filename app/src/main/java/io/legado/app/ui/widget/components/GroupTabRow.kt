package io.legado.app.ui.widget.components

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ScrollableTabRow
import androidx.compose.material3.Tab
import androidx.compose.material3.TabRowDefaults
import androidx.compose.material3.TabRowDefaults.tabIndicatorOffset
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

/**
 * 通用分组标签行（发现/订阅/书架共用，M3 ScrollableTabRow + SecondaryIndicator）。
 *
 * 对齐书架 `BookshelfScreen.BookGroupTabs` 的视觉（无硬编码色，token 走 MaterialTheme）。
 *
 * @param groups 标签文本列表（按类型分组时为类型名，按分组分组时为分组名，首项固定「全部」）
 * @param selectedIndex 当前选中索引（0 起）
 * @param onTabSelect 标签点击回调，返回索引
 */
@Composable
fun GroupTabRow(
    groups: List<String>,
    selectedIndex: Int,
    onTabSelect: (Int) -> Unit,
    modifier: Modifier = Modifier
) {
    val index = selectedIndex.coerceIn(0, (groups.size - 1).coerceAtLeast(0))
    ScrollableTabRow(
        selectedTabIndex = index,
        edgePadding = 8.dp,
        containerColor = MaterialTheme.colorScheme.surface,
        indicator = { tabPositions ->
            TabRowDefaults.SecondaryIndicator(
                modifier = Modifier.tabIndicatorOffset(tabPositions[index]),
                color = MaterialTheme.colorScheme.primary,
            )
        },
        modifier = modifier
    ) {
        groups.forEachIndexed { i, label ->
            Tab(
                selected = i == index,
                onClick = { onTabSelect(i) },
                text = { Text(text = label) },
            )
        }
    }
}
