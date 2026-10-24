package io.legado.app.help.gsyVideo

import android.app.Dialog
import android.content.Context
import android.graphics.drawable.GradientDrawable
import android.os.Bundle
import android.view.Gravity
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.view.WindowManager
import android.widget.HorizontalScrollView
import android.widget.LinearLayout
import android.widget.TextView
import androidx.recyclerview.widget.GridLayoutManager
import androidx.recyclerview.widget.RecyclerView
import io.legado.app.R
import io.legado.app.data.entities.BookChapter
import io.legado.app.help.video.EpisodePager
import io.legado.app.lib.theme.ThemeStore
import io.legado.app.lib.theme.UiCorner
import kotlin.math.ceil
import kotlin.math.min
import kotlin.math.roundToInt

/**
 * 多集选集弹框（video-cache-and-multiep R7 / AD-03 / V4）。
 *
 * 形态：**底部上浮 + 顶部第一行分组（1-10 / 11-20 …）+ 组内集数网格（5 列）**。
 *  - 组数与组内集数由 [EpisodePager] 统一计算（组数 ≤ 10，超长剧按 10 递增扩容）
 *  - 打开时自动定位到当前集所在分组与集数
 *  - 高度按横竖屏剩余空间计算（竖屏 45% / 横屏 55%），保证上方视频完整可见
 *  - 背景无遮罩（dimAmount=0），不打断观看
 *
 * 书源（`BookChapter`）与订阅源（集标题）共用：前者走 [initList]，后者走 [initListByTitles]。
 */
class ChoiceEpisodeDialog(private val mContext: Context) : Dialog(
    mContext, R.style.dialog_style
) {
    private var headerView: TextView? = null
    private var orderToggle: TextView? = null
    private var groupScroll: HorizontalScrollView? = null
    private var groupRow: LinearLayout? = null
    private var grid: RecyclerView? = null

    private var onItemClickListener: OnListItemClickListener? = null
    private var titles: List<String> = emptyList()
    private var currentSelection = -1
    private var paging: EpisodePager.Paging? = null
    private var selectedGroup = 0

    /**
     * 已缓存集的**全集下标**集合（book-info-unified-cache AD-05）。
     *
     * 用全集下标而非格子位置：倒序展示时 `renderGrid` 按展示顺序换算成逐格布尔，
     * 角标因此始终对应真实集号。
     */
    private var cachedIndexes: Set<Int> = emptySet()

    /**
     * 展示顺序：false = 正序（1→N，默认，与历史行为一致）；true = 倒序（最新集在前）。
     *
     * 2026-10-24 用户需求：长剧（如 86 集）想从最新集往回找时必须一直翻到底，
     * 故头部提供一键切换。仅影响**展示顺序**，不改变集下标语义（点击仍回传真实全集下标）。
     */
    private var descending = false

    /** 打开期间读取实时当前集（自动连播推进时刷新高亮）；null = 用打开时的快照 */
    private var selectionProvider: (() -> Int)? = null

    /** 高亮轮询句柄（dismiss/onStop 时必须移除，防泄漏） */
    private val selectionPollRunnable = object : Runnable {
        override fun run() {
            refreshSelectionIfChanged()
            if (selectionProvider != null && isShowing) {
                handler.postDelayed(this, SELECTION_POLL_MS)
            }
        }
    }
    private val handler = android.os.Handler(android.os.Looper.getMainLooper())

    interface OnListItemClickListener {
        /** 全集下标（0-based，与 `episodes` / 目录一致） */
        fun onItemClick(position: Int)
        fun finishDialog()
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
    }

    /** 书源分支：目录章节 → 标题列表 */
    fun initList(
        data: List<BookChapter>,
        onItemClickListener: OnListItemClickListener,
        initialSelection: Int = -1
    ) {
        initListByTitles(data.map { it.title }, onItemClickListener, initialSelection)
    }

    /**
     * 通用分支：按集标题展示（书源与订阅源共用）。
     *
     * @param titles 全集标题（顺序即集顺序）
     * @param initialSelection 当前集下标（0-based；-1 表示无选中）
     * @param selectionProvider 弹框打开期间读取**实时**当前集（自动连播会继续推进）；
     *        非空时每 [SELECTION_POLL_MS] 刷新高亮，避免「标题已到第 81 集、高亮还停在第 74 集」
     * @param cachedIndexes 已缓存集的**全集下标**（默认空 = 不显示勾选角标）
     */
    fun initListByTitles(
        titles: List<String>,
        onItemClickListener: OnListItemClickListener,
        initialSelection: Int = -1,
        selectionProvider: (() -> Int)? = null,
        cachedIndexes: Set<Int> = emptySet()
    ) {
        this.onItemClickListener = onItemClickListener
        this.titles = titles
        this.cachedIndexes = cachedIndexes
        this.currentSelection = if (initialSelection in titles.indices) initialSelection else -1
        this.selectionProvider = selectionProvider
        val view: View = LayoutInflater.from(mContext)
            .inflate(R.layout.switch_episode_video_dialog, null)
        headerView = view.findViewById(R.id.listCount)
        orderToggle = view.findViewById(R.id.order_toggle)
        groupScroll = view.findViewById(R.id.group_scroll)
        groupRow = view.findViewById(R.id.group_row)
        grid = view.findViewById(R.id.episode_grid)
        setContentView(view)
        val radius = UiCorner.panelRadius(mContext).toFloat()
        view.background = GradientDrawable().apply {
            shape = GradientDrawable.RECTANGLE
            cornerRadius = radius
            setColor(ThemeStore.backgroundColor(mContext))
        }
        paging = EpisodePager.build(titles.size, currentSelection.coerceAtLeast(0))
        selectedGroup = paging?.currentGroupIndex?.coerceAtLeast(0) ?: 0
        headerView?.text = mContext.getString(R.string.video_episode_picker_header, titles.size)
        // 正序 / 倒序切换：按钮文案显示「点击后会切到」的顺序，符合直觉
        orderToggle?.apply {
            text = mContext.getString(
                if (descending) R.string.video_episode_order_asc
                else R.string.video_episode_order_desc
            )
            setOnClickListener {
                descending = !descending
                text = mContext.getString(
                    if (descending) R.string.video_episode_order_asc
                    else R.string.video_episode_order_desc
                )
                // 分组行与网格共用同一 [descending]，一次切换两者同时重排
                renderGroups()
                renderGrid()
            }
        }
        renderGroups()
        renderGrid()
        applyWindow()
        // 自动连播期间高亮跟随（首帧延后一拍，避免与首次布局竞争）
        if (selectionProvider != null) {
            handler.postDelayed(selectionPollRunnable, SELECTION_POLL_MS)
        }
    }

    /**
     * 当前集变化时只重绘必要部分：组不变 ⇒ 只重绘网格；组变化 ⇒ 分组行也重排并滚到可见。
     */
    private fun refreshSelectionIfChanged() {
        val provider = selectionProvider ?: return
        val latest = provider()
        if (latest !in titles.indices || latest == currentSelection) return
        val p = paging ?: return
        val previousGroup = selectedGroup
        currentSelection = latest
        val newGroup = p.groups.indexOfFirst { latest in it.startIndex..it.endIndex }
        if (newGroup >= 0 && newGroup != selectedGroup) {
            selectedGroup = newGroup
        }
        if (selectedGroup != previousGroup) renderGroups()
        renderGrid()
    }

    override fun onStop() {
        handler.removeCallbacks(selectionPollRunnable)
        onItemClickListener?.finishDialog()
        super.onStop()
    }

    /** 分组行：选中组高亮；点击切换组并重绘网格（展示顺序随 [descending] 变化） */
    private fun renderGroups() {
        val row = groupRow ?: return
        row.removeAllViews()
        val groups = paging?.groups.orEmpty()
        val density = mContext.resources.displayMetrics.density
        // 倒序时最后一批集数排在最前（分组行与网格顺序一致，避免"格子与分组对不上"）
        val displayOrder = EpisodePager.displayGroupOrder(groups.size, descending)
        displayOrder.forEachIndexed { displayIndex, groupIndex ->
            val group = groups[groupIndex]
            val chip = TextView(mContext).apply {
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
            applyVideoChoiceItemStyle(mContext, chip, groupIndex == selectedGroup)
            val lp = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.WRAP_CONTENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            ).also { if (displayIndex > 0) it.marginStart = (6 * density).roundToInt() }
            row.addView(chip, lp)
        }
        // 当前分组可能在横向滚动区域外：滚到可见位置（按展示序号定位，倒序时反向）
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
        // 集的**全集下标**：正序 start..end，倒序 end..start（点击直接回传该下标，无需再做换算）
        val indices = EpisodePager.displayIndices(group, descending)
        val items = indices.map { titles[it] }
        // AD-05：按展示顺序换算逐格「已缓存」布尔（角标随集号而非格子位置）
        val cachedFlags = indices.map { it in cachedIndexes }
        val selectionInGroup = indices.indexOf(currentSelection)
        val layoutManager = GridLayoutManager(mContext, COLUMNS)
        recycler.layoutManager = layoutManager
        recycler.adapter = EpisodeGridAdapter(mContext, items, selectionInGroup, cachedFlags) { positionInGroup ->
            val fullIndex = indices.getOrNull(positionInGroup) ?: return@EpisodeGridAdapter
            dismiss()
            onItemClickListener?.onItemClick(fullIndex)
        }
        resizeGrid(group.count)
        if (selectionInGroup >= 0) {
            layoutManager.scrollToPositionWithOffset(selectionInGroup, 0)
        }
    }

    /**
     * 网格高度 = min(实际行高, 视口剩余高度)。
     *
     * 「视口剩余高度」= 屏幕高度 × 横竖屏系数 − 头部与分组行占位，
     * 保证弹框整体不越过视频可见区（需求：弹框不能影响观看）。
     */
    private fun resizeGrid(itemCount: Int) {
        val recycler = grid ?: return
        val dm = mContext.resources.displayMetrics
        val isLandscape = dm.widthPixels > dm.heightPixels
        val maxPanelPx = dm.heightPixels * (if (isLandscape) 0.55f else 0.45f)
        val fixedPx = (HEADER_DP + GROUP_ROW_DP + PANEL_PADDING_DP) * dm.density
        val gridMaxPx = (maxPanelPx - fixedPx).coerceAtLeast(MIN_GRID_DP * dm.density)
        val rows = ceil(itemCount.toDouble() / COLUMNS).toInt().coerceAtLeast(1)
        val itemHeightPx = ITEM_HEIGHT_DP * dm.density
        val gapPx = ITEM_GAP_DP * dm.density
        val contentPx = rows * itemHeightPx + (rows - 1) * gapPx
        val lp = recycler.layoutParams
            ?: ViewGroup.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT
            )
        lp.height = min(contentPx, gridMaxPx).roundToInt()
        recycler.layoutParams = lp
    }

    private fun applyWindow() {
        val dialogWindow = window ?: return
        val dm = mContext.resources.displayMetrics
        val lp = dialogWindow.attributes
        lp.width = dm.widthPixels - (WINDOW_SIDE_MARGIN_DP * dm.density).roundToInt()
        lp.height = WindowManager.LayoutParams.WRAP_CONTENT
        // 底部上浮：视频在上方完整可见（无居中遮罩）
        lp.gravity = Gravity.BOTTOM or Gravity.CENTER_HORIZONTAL
        dialogWindow.setAttributes(lp)
        dialogWindow.setDimAmount(0f)
    }

    companion object {
        /** 集数网格列数（5 列，与需求「每组展示具体集数」一致） */
        const val COLUMNS = 5

        private const val ITEM_HEIGHT_DP = 40f
        private const val ITEM_GAP_DP = 6f
        private const val HEADER_DP = 44f
        private const val GROUP_ROW_DP = 40f
        private const val PANEL_PADDING_DP = 32f
        private const val MIN_GRID_DP = 132f
        private const val WINDOW_SIDE_MARGIN_DP = 16f

        /** 高亮跟随轮询间隔（自动连播每集 10s~数分钟，500ms 足够且开销可忽略） */
        private const val SELECTION_POLL_MS = 500L
    }
}
