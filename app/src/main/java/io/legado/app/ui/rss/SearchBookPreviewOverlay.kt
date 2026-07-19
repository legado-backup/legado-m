package io.legado.app.ui.rss

import android.os.Bundle
import android.view.View
import io.legado.app.R
import io.legado.app.base.BaseDialogFragment
import io.legado.app.data.entities.SearchBook
import io.legado.app.databinding.DialogSearchBookPreviewBinding
import io.legado.app.help.config.AppConfig
import io.legado.app.utils.gone
import io.legado.app.utils.setLayout
import io.legado.app.utils.visible
import io.legado.app.utils.viewbindingdelegate.viewBinding

/**
 * 搜索结果预览覆盖层（RSS-E-05 / P1）
 *
 * 设计要点（与 Archive Compose 实现的差异）：
 * - Archive 使用 Compose + BookshelfListRenderConfig + CoverImageView.CoverStyle.PREVIEW，
 *   依赖复杂（palette/panelImage/graphicsLayer 动画等）。
 * - 本项目使用 BaseDialogFragment + 简单 ConstraintLayout 布局，避免引入 Compose 依赖。
 * - 复用本项目 CoverImageView.load(SearchBook) 扩展函数加载封面。
 * - 关联任务：RSS-E-05；依赖 RSS-B-03（SearchBookMergeUtils 已实现，origins 字段已合并）。
 *
 * 与 SearchActivity 集成：
 * - SearchActivity 实现 Callback，点击搜索结果时弹出本 Dialog
 * - 用户点击"查看详情"按钮 → Callback.onOpenBookInfo(book) → 跳转 BookInfoActivity
 * - 用户点击"关闭"按钮或外部 → dismiss()
 */
class SearchBookPreviewOverlay(
) : BaseDialogFragment(R.layout.dialog_search_book_preview) {

    constructor(book: SearchBook) : this() {
        arguments = Bundle().apply {
            putParcelable("book", book)
        }
    }

    private val binding by viewBinding(DialogSearchBookPreviewBinding::bind)

    interface Callback {
        fun onOpenBookInfo(book: SearchBook)
    }

    private var callback: Callback? = null

    fun setCallback(callback: Callback) {
        this.callback = callback
    }

    override fun onStart() {
        super.onStart()
        // 简化说明: 占屏宽 92%，高度自适应；与 PhotoDialog 风格不同（PhotoDialog 全屏）
        // 已知上限: 横屏下宽度可能过宽，未来可基于资源限定符细化
        setLayout(0.92f, -1)
    }

    override fun onFragmentCreated(view: View, savedInstanceState: Bundle?) {
        val book = arguments?.getParcelable<SearchBook>("book") ?: run {
            dismiss()
            return
        }
        bindBook(book)
        binding.btnClose.setOnClickListener { dismiss() }
        binding.btnOpen.setOnClickListener {
            callback?.onOpenBookInfo(book)
            dismiss()
        }
    }

    private fun bindBook(book: SearchBook) {
        binding.run {
            tvName.text = book.name
            tvAuthor.text = getString(R.string.author_show, book.author)
            // 来源数：origins 已由 SearchBookMergeUtils 合并，包含多源信息
            val originCount = book.origins.size.coerceAtLeast(1)
            tvOriginCount.text = getString(R.string.search_preview_origin_count, originCount)
            // 最新章节
            if (book.latestChapterTitle.isNullOrBlank()) {
                tvLasted.gone()
            } else {
                tvLasted.text = getString(R.string.lasted_show, book.latestChapterTitle)
                tvLasted.visible()
            }
            // kind 标签
            val kinds = book.getKindList()
            if (kinds.isEmpty()) {
                llKind.gone()
            } else {
                llKind.visible()
                llKind.setLabels(kinds)
            }
            // 简介
            tvIntroduce.text = book.trimIntro(requireContext())
            // 封面：复用 CoverImageView.load(SearchBook) 扩展
            ivCover.load(book, AppConfig.loadCoverOnlyWifi, this@SearchBookPreviewOverlay, viewLifecycleOwner.lifecycle)
        }
    }

}
