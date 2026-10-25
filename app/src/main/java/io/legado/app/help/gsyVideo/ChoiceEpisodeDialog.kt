package io.legado.app.help.gsyVideo

import android.app.Dialog
import android.content.Context
import android.graphics.drawable.GradientDrawable
import android.os.Bundle
import android.view.Gravity
import android.view.LayoutInflater
import android.view.View
import android.view.WindowManager
import io.legado.app.R
import io.legado.app.data.entities.BookChapter
import io.legado.app.help.video.EpisodePager
import io.legado.app.lib.theme.ThemeStore
import io.legado.app.lib.theme.UiCorner
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
 *
 * 2026-10-25：分组/网格/倒序/角标的渲染已下沉到 [EpisodePanelBinder]，
 * 传统布局的内嵌面板复用同一 binder（单一实现，行为不可能漂移）。
 */
class ChoiceEpisodeDialog(private val mContext: Context) : Dialog(
    mContext, R.style.dialog_style
) {
    private var binder: EpisodePanelBinder? = null
    private var onItemClickListener: OnListItemClickListener? = null
    private var titles: List<String> = emptyList()
    private var currentSelection = -1

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
        this.currentSelection = if (initialSelection in titles.indices) initialSelection else -1
        this.selectionProvider = selectionProvider
        val view: View = LayoutInflater.from(mContext)
            .inflate(R.layout.switch_episode_video_dialog, null)
        val radius = UiCorner.panelRadius(mContext).toFloat()
        view.background = GradientDrawable().apply {
            shape = GradientDrawable.RECTANGLE
            cornerRadius = radius
            setColor(ThemeStore.backgroundColor(mContext))
        }
        setContentView(view)
        val panel = EpisodePanelBinder(
            context = mContext,
            container = view,
            maxGridHeightPx = { resolveGridMaxHeightPx() },
            onSelect = { fullIndex ->
                dismiss()
                onItemClickListener.onItemClick(fullIndex)
            }
        )
        panel.bind(
            titles = titles,
            initialSelection = currentSelection,
            cachedIndexes = cachedIndexes,
            showHeader = true,
        )
        binder = panel
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
        currentSelection = latest
        binder?.updateSelection(latest)
    }

    override fun onStop() {
        handler.removeCallbacks(selectionPollRunnable)
        onItemClickListener?.finishDialog()
        super.onStop()
    }

    /**
     * 网格高度上限 = 屏幕高度 × 横竖屏系数 − 头部与分组行占位。
     *
     * 保证弹框整体不越过视频可见区（需求：弹框不能影响观看）。
     */
    private fun resolveGridMaxHeightPx(): Int {
        val dm = mContext.resources.displayMetrics
        val isLandscape = dm.widthPixels > dm.heightPixels
        val maxPanelPx = dm.heightPixels * (if (isLandscape) 0.55f else 0.45f)
        val fixedPx = (HEADER_DP + GROUP_ROW_DP + PANEL_PADDING_DP) * dm.density
        return (maxPanelPx - fixedPx).coerceAtLeast(MIN_GRID_DP * dm.density).roundToInt()
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
        private const val HEADER_DP = 44f
        private const val GROUP_ROW_DP = 40f
        private const val PANEL_PADDING_DP = 32f
        private const val MIN_GRID_DP = 132f
        private const val WINDOW_SIDE_MARGIN_DP = 16f

        /** 高亮跟随轮询间隔（自动连播每集 10s~数分钟，500ms 足够且开销可忽略） */
        private const val SELECTION_POLL_MS = 500L
    }
}
