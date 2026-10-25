package io.legado.app.help.gsyVideo

import android.content.Context
import android.view.Gravity
import android.view.View
import android.widget.HorizontalScrollView
import android.widget.LinearLayout
import android.widget.TextView
import androidx.recyclerview.widget.GridLayoutManager
import androidx.recyclerview.widget.RecyclerView
import io.legado.app.R
import io.legado.app.help.video.EpisodePager
import kotlin.math.ceil
import kotlin.math.min
import kotlin.math.roundToInt

/**
 * 选集面板绑定器（2026-10-25 episode-switch-loading-and-legacy-inline）。
 *
 * 把「分组行 + 5 列集数网格 + 正序/倒序 + 当前集高亮 + 已缓存角标」的渲染收敛为**单一实现**：
 * - 选集弹框 [ChoiceEpisodeDialog]（沉浸式 / 播放器内浮层）
 * - 传统布局信息区内嵌面板（`activity_video_player.xml` 的 `<include layout="@layout/switch_episode_video_dialog"/>`）
 *
 * 分页算法仍由 [EpisodePager] 提供；单元格样式与角标由 [EpisodeGridAdapter] 负责，本类只做编排。
 *
 * @param container 即 `switch_episode_video_dialog` 的根视图
 * @param maxGridHeightPx 网格高度上限；null = 不限（内嵌面板随内容展开，外层 NestedScrollView 滚动）
 * @param onSelect 点击某一集的回调，参数为**全集下标**（0-based，倒序展示时已换算回真实集号）
 */
class EpisodePanelBinder(
    private val context: Context,
    container: View,
    private val maxGridHeightPx: (() -> Int)? = null,
    private val onSelect: (Int) -> Unit,
) {
    private val listCount: TextView? = container.findViewById(R.id.listCount)
    private val orderToggle: TextView? = container.findViewById(R.id.order_toggle)
    private val groupScroll: HorizontalScrollView? = container.findViewById(R.id.group_scroll)
    private val groupRow: LinearLayout? = container.findViewById(R.id.group_row)
    private val grid: RecyclerView? = container.findViewById(R.id.episode_grid)

    private var titles: List<String> = emptyList()
    private var cachedIndexes: Set<Int> = emptySet()
    private var currentSelection = -1
    private var paging: EpisodePager.Paging? = null
    private var selectedGroup = 0

    /** 展示顺序：false = 正序（默认）；true = 倒序。仅影响展示，点击仍回传真实全集下标 */
    private var descending = false

    init {
        orderToggle?.apply {
            text = orderButtonText()
            setOnClickListener {
                descending = !descending
                text = orderButtonText()
                renderGroups()
                renderGrid()
            }
        }
    }

    /**
     * 绑定数据并首次渲染。
     *
     * @param titles 全集标题（顺序即集顺序）
     * @param initialSelection 当前集下标（0-based，-1 = 无选中）
     * @param cachedIndexes 已缓存集的**全集下标**集合
     * @param showHeader 是否显示「全 N 集」头行（内嵌面板已有外层标题，传 false 隐藏）
     * @param groupRowTopPaddingDp 内嵌面板在集数标题下方时需要的上间距（弹框为 0）
     */
    fun bind(
        titles: List<String>,
        initialSelection: Int,
        cachedIndexes: Set<Int> = emptySet(),
        showHeader: Boolean = true,
        groupRowTopPaddingDp: Int = 0,
    ) {
        this.titles = titles
        this.cachedIndexes = cachedIndexes
        this.currentSelection = if (initialSelection in titles.indices) initialSelection else -1
        listCount?.apply {
            visibility = if (showHeader) View.VISIBLE else View.GONE
            if (showHeader) text = context.getString(R.string.video_episode_picker_header, titles.size)
        }
        groupScroll?.setPadding(
            0,
            (groupRowTopPaddingDp * context.resources.displayMetrics.density).roundToInt(),
            0,
            0
        )
        paging = EpisodePager.build(titles.size, currentSelection.coerceAtLeast(0))
        selectedGroup = paging?.currentGroupIndex?.coerceAtLeast(0) ?: 0
        renderGroups()
        renderGrid()
    }

    /** 仅更新角标集合（缓存扫描是 IO 任务，完成后再回主线程刷新） */
    fun updateCachedIndexes(cached: Set<Int>) {
        if (cached == cachedIndexes) return
        cachedIndexes = cached
        renderGrid()
    }

    /**
     * 当前集变化时刷新高亮（自动连播推进/外部切集）。
     *
     * 组不变 ⇒ 只重绘网格；组变化 ⇒ 分组行也重排。
     */
    fun updateSelection(current: Int) {
        if (current !in titles.indices || current == currentSelection) return
        val p = paging ?: return
        val previousGroup = selectedGroup
        currentSelection = current
        val newGroup = p.groups.indexOfFirst { current in it.startIndex..it.endIndex }
        if (newGroup >= 0) selectedGroup = newGroup
        if (selectedGroup != previousGroup) renderGroups()
        renderGrid()
    }

    /** 分组行：选中组高亮；点击切换组并重绘网格（顺序随 [descending] 变化） */
    private fun renderGroups() {
        val row = groupRow ?: return
        row.removeAllViews()
        val groups = paging?.groups.orEmpty()
        val density = context.resources.displayMetrics.density
        val displayOrder = EpisodePager.displayGroupOrder(groups.size, descending)
        displayOrder.forEachIndexed { displayIndex, groupIndex ->
            val group = groups[groupIndex]
            val chip = TextView(context).apply {
                text = EpisodePager.displayLabel(group, descending)
                textSize = 13f
                gravity = Gravity.CENTER
                setPadding(
                    (12 * density).roundToInt(), (7 * density).roundToInt(),
                    (12 * density).roundToInt(), (7 * density).roundToInt()
                )
                isClickable = true
                setOnClickListener {
                    if (selectedGroup != groupIndex) {
                        selectedGroup = groupIndex
                        renderGroups()
                        renderGrid()
                    }
                }
            }
            applyVideoChoiceItemStyle(context, chip, groupIndex == selectedGroup)
            val lp = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.WRAP_CONTENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            ).also { if (displayIndex > 0) it.marginStart = (6 * density).roundToInt() }
            row.addView(chip, lp)
        }
        groupScroll?.post {
            val displayIndexOfSelected = displayOrder.indexOf(selectedGroup)
            if (displayIndexOfSelected < 0) return@post
            val selected = row.getChildAt(displayIndexOfSelected) ?: return@post
            val left = selected.left - (groupScroll!!.width / 3)
            groupScroll?.smoothScrollTo(left.coerceAtLeast(0), 0)
        }
    }

    /** 集数网格：仅渲染当前分组，当前集高亮并自动定位；顺序由 [EpisodePager.displayIndices] 决定 */
    private fun renderGrid() {
        val recycler = grid ?: return
        val p = paging ?: return
        val group = p.groups.getOrNull(selectedGroup) ?: return
        val indices = EpisodePager.displayIndices(group, descending)
        val items = indices.map { titles[it] }
        val cachedFlags = indices.map { it in cachedIndexes }
        val selectionInGroup = indices.indexOf(currentSelection)
        val layoutManager = GridLayoutManager(context, COLUMNS)
        recycler.layoutManager = layoutManager
        recycler.adapter = EpisodeGridAdapter(context, items, selectionInGroup, cachedFlags) { positionInGroup ->
            val fullIndex = indices.getOrNull(positionInGroup) ?: return@EpisodeGridAdapter
            onSelect(fullIndex)
        }
        resizeGrid(group.count)
        if (selectionInGroup >= 0) {
            layoutManager.scrollToPositionWithOffset(selectionInGroup, 0)
        }
    }

    /**
     * 网格高度：
     * - 弹框（[maxGridHeightPx] 非空）：min(内容高, 视口剩余高)，保证上方视频可见
     * - 内嵌面板（null）：wrap_content，由外层 NestedScrollView 滚动
     */
    private fun resizeGrid(itemCount: Int) {
        val recycler = grid ?: return
        val limit = maxGridHeightPx?.invoke() ?: return
        val density = context.resources.displayMetrics.density
        val heightPx = gridHeightPx(
            itemCount = itemCount,
            columns = COLUMNS,
            itemHeightPx = ITEM_HEIGHT_DP * density,
            gapPx = ITEM_GAP_DP * density,
            limitPx = limit.toFloat(),
        )
        val lp = recycler.layoutParams
            ?: android.view.ViewGroup.LayoutParams(
                android.view.ViewGroup.LayoutParams.MATCH_PARENT,
                android.view.ViewGroup.LayoutParams.WRAP_CONTENT
            )
        lp.height = heightPx
        recycler.layoutParams = lp
    }

    private fun orderButtonText(): String = context.getString(
        if (descending) R.string.video_episode_order_asc else R.string.video_episode_order_desc
    )

    companion object {
        /** 集数网格列数（5 列，与需求「每组展示具体集数」一致） */
        const val COLUMNS = 5

        private const val ITEM_HEIGHT_DP = 40f
        private const val ITEM_GAP_DP = 6f

        /**
         * 网格高度 = min(内容实际高, 上限)。纯函数（单测锁定）：行数按列数向上取整，
         * 行间含间距、行尾不含 ⇒ 与 `GridLayoutManager` 的 5 列排布一致。
         */
        internal fun gridHeightPx(
            itemCount: Int,
            columns: Int,
            itemHeightPx: Float,
            gapPx: Float,
            limitPx: Float,
        ): Int {
            val safeColumns = columns.coerceAtLeast(1)
            val rows = ceil(itemCount.toDouble() / safeColumns).toInt().coerceAtLeast(1)
            val contentPx = rows * itemHeightPx + (rows - 1) * gapPx
            return min(contentPx, limitPx).roundToInt()
        }
    }
}
