package io.legado.app.ui.widget.dialog

import android.content.Context
import android.os.Bundle
import android.view.View
import android.view.ViewGroup
import androidx.fragment.app.FragmentManager
import androidx.recyclerview.widget.LinearLayoutManager
import io.legado.app.R
import io.legado.app.base.BaseDialogFragment
import io.legado.app.base.adapter.ItemViewHolder
import io.legado.app.base.adapter.RecyclerAdapter
import io.legado.app.data.entities.RssSource
import io.legado.app.databinding.DialogRecyclerViewBinding
import io.legado.app.databinding.ItemLogBinding
import io.legado.app.utils.setLayout
import io.legado.app.utils.viewbindingdelegate.viewBinding

/**
 * RSS 源选择对话框（RSS-B-02）。
 *
 * 弹窗显示 RSS 源列表，用户点击选源后通过回调返回 [RssSource]。
 *
 * 借鉴 Archive 项目 SourceSelectDialog（Compose 实现），改写为本地 View 实现：
 * - 继承 [BaseDialogFragment] + [RecyclerAdapter]（与 [TextListDialog] 同模式）
 * - 复用 `dialog_recycler_view.xml` 布局（Toolbar + RecyclerView + 空态提示）
 * - 复用 `item_log.xml`（简单 TextView，避免引入完整源管理布局的复杂交互）
 *
 * 关联任务：RSS-B-02（P0）
 */
class SourceSelectDialog() : BaseDialogFragment(R.layout.dialog_recycler_view) {

    constructor(
        title: String,
        sources: ArrayList<RssSource>,
        onSelect: (RssSource) -> Unit
    ) : this() {
        arguments = Bundle().apply {
            putString("title", title)
            putParcelableArrayList("sources", sources)
        }
        this.onSelect = onSelect
    }

    private val binding by viewBinding(DialogRecyclerViewBinding::bind)
    private val adapter by lazy { SourceAdapter(requireContext()) }
    private var onSelect: ((RssSource) -> Unit)? = null
    private var sources: ArrayList<RssSource>? = null

    override fun onStart() {
        super.onStart()
        setLayout(0.9f, 0.9f)
    }

    override fun onFragmentCreated(view: View, savedInstanceState: Bundle?) {
        binding.run {
            arguments?.let {
                toolBar.title = it.getString("title").orEmpty()
                // 简化说明: 用 getParcelableArrayList 兼容 API 33 以下; 上限: API 33+ 会触发 deprecation 警告; 升级路径: 改用 getParcelableArrayList(key, RssSource::class.java)
                sources = it.getParcelableArrayList("sources")
            }
            if (sources.isNullOrEmpty()) {
                tvMsg.visibility = View.VISIBLE
                tvMsg.text = getString(R.string.empty)
                recyclerView.visibility = View.GONE
                return
            }
            recyclerView.layoutManager = LinearLayoutManager(requireContext())
            recyclerView.adapter = adapter
            adapter.setItems(sources)
        }
    }

    private inner class SourceAdapter(context: Context) :
        RecyclerAdapter<RssSource, ItemLogBinding>(context) {

        override fun getViewBinding(parent: ViewGroup): ItemLogBinding {
            return ItemLogBinding.inflate(inflater, parent, false)
        }

        override fun convert(
            holder: ItemViewHolder,
            binding: ItemLogBinding,
            item: RssSource,
            payloads: MutableList<Any>
        ) {
            // 显示源名称（仅技术字段引用，业务值由数据源提供）
            binding.textView.text = item.sourceName
        }

        override fun registerListener(holder: ItemViewHolder, binding: ItemLogBinding) {
            binding.root.setOnClickListener {
                getItem(holder.layoutPosition)?.let { source ->
                    onSelect?.invoke(source)
                    dismiss()
                }
            }
        }
    }

    companion object {
        /**
         * 显示源选择对话框。
         *
         * @param fragmentManager FragmentManager
         * @param title 对话框标题
         * @param sources 可选源列表（调用方应预先过滤出有 searchUrl 的源）
         * @param onSelect 选中源回调（注意：Fragment 重建时回调会丢失，需调用方自行降级处理）
         */
        fun show(
            fragmentManager: FragmentManager,
            title: String,
            sources: ArrayList<RssSource>,
            onSelect: (RssSource) -> Unit
        ) {
            SourceSelectDialog(title, sources, onSelect).show(fragmentManager, "SourceSelectDialog")
        }
    }
}
