package io.legado.app.ui.widget

import android.annotation.SuppressLint
import android.content.Context
import android.os.Bundle
import android.view.MenuItem
import android.view.View
import android.view.ViewGroup
import androidx.appcompat.widget.Toolbar
import androidx.recyclerview.widget.LinearLayoutManager
import io.legado.app.R
import io.legado.app.base.BaseDialogFragment
import io.legado.app.base.adapter.ItemViewHolder
import io.legado.app.base.adapter.RecyclerAdapter
import io.legado.app.databinding.DialogEditTextBinding
import io.legado.app.databinding.DialogRecyclerViewBinding
import io.legado.app.databinding.ItemBatchGroupBinding
import io.legado.app.lib.dialogs.alert
import io.legado.app.lib.theme.backgroundColor
import io.legado.app.lib.theme.primaryColor
import io.legado.app.ui.widget.recycler.VerticalDivider
import io.legado.app.utils.applyTint
import io.legado.app.utils.dpToPx
import io.legado.app.utils.requestInputMethod
import io.legado.app.utils.setLayout
import io.legado.app.utils.toastOnUi
import io.legado.app.utils.viewbindingdelegate.viewBinding

/**
 * 批量改分组对话框（问题4 P1-3b）
 * 显示源列表 checkbox 多选，工具栏提供 全选/反选/移入分组/移出分组。
 * 选中项以列表索引回调，由调用方映射回真实数据并执行批量分组。
 */
class BatchGroupDialog(
    private val title: String,
    private val names: List<String>,
    private val groups: List<String>,
    private val callBack: CallBack
) : BaseDialogFragment(R.layout.dialog_recycler_view), Toolbar.OnMenuItemClickListener {

    interface CallBack {
        fun addToGroups(selected: List<Int>, group: String)
        fun removeFromGroups(selected: List<Int>, group: String)
    }

    private val binding by viewBinding(DialogRecyclerViewBinding::bind)
    private val adapter by lazy { GroupAdapter(requireContext()) }
    private val selected = linkedSetOf<Int>()

    override fun onStart() {
        super.onStart()
        setLayout(0.9f, 0.9f)
    }

    override fun onFragmentCreated(view: View, savedInstanceState: Bundle?) {
        view.setBackgroundColor(backgroundColor)
        initView()
        adapter.setItems(names)
    }

    private fun initView() = binding.run {
        toolBar.setBackgroundColor(primaryColor)
        toolBar.title = title
        toolBar.inflateMenu(R.menu.batch_group)
        toolBar.menu.applyTint(requireContext())
        toolBar.setOnMenuItemClickListener(this@BatchGroupDialog)
        recyclerView.layoutManager = LinearLayoutManager(requireContext())
        recyclerView.addItemDecoration(VerticalDivider(requireContext()))
        recyclerView.adapter = adapter
    }

    override fun onMenuItemClick(item: MenuItem?): Boolean {
        when (item?.itemId) {
            R.id.menu_select_all -> selectAll()
            R.id.menu_revert_selection -> revertSelection()
            R.id.menu_add_group -> addToGroups()
            R.id.menu_remove_group -> removeFromGroups()
        }
        return true
    }

    private fun selectAll() {
        selected.clear()
        selected.addAll(names.indices)
        adapter.notifyDataSetChanged()
    }

    private fun revertSelection() {
        val reverted = names.indices.filterNot { selected.contains(it) }
        selected.clear()
        selected.addAll(reverted)
        adapter.notifyDataSetChanged()
    }

    @SuppressLint("InflateParams")
    private fun addToGroups() {
        if (selected.isEmpty()) {
            context?.toastOnUi(R.string.please_select_first)
            return
        }
        alert(titleResource = R.string.add_group) {
            val alertBinding = DialogEditTextBinding.inflate(layoutInflater).apply {
                editView.setHint(R.string.group_name)
                editView.setFilterValues(groups)
                editView.dropDownHeight = 180.dpToPx()
            }
            customView { alertBinding.root }
            okButton {
                alertBinding.editView.text?.toString()?.let {
                    if (it.isNotEmpty()) {
                        callBack.addToGroups(selected.toList(), it)
                        dismissAllowingStateLoss()
                    }
                }
            }
            cancelButton()
        }.requestInputMethod()
    }

    @SuppressLint("InflateParams")
    private fun removeFromGroups() {
        if (selected.isEmpty()) {
            context?.toastOnUi(R.string.please_select_first)
            return
        }
        alert(titleResource = R.string.remove_group) {
            val alertBinding = DialogEditTextBinding.inflate(layoutInflater).apply {
                editView.setHint(R.string.group_name)
                editView.setFilterValues(groups)
                editView.dropDownHeight = 180.dpToPx()
            }
            customView { alertBinding.root }
            okButton {
                alertBinding.editView.text?.toString()?.let {
                    if (it.isNotEmpty()) {
                        callBack.removeFromGroups(selected.toList(), it)
                        dismissAllowingStateLoss()
                    }
                }
            }
            cancelButton()
        }.requestInputMethod()
    }

    private inner class GroupAdapter(context: Context) :
        RecyclerAdapter<String, ItemBatchGroupBinding>(context) {

        override fun getViewBinding(parent: ViewGroup): ItemBatchGroupBinding {
            return ItemBatchGroupBinding.inflate(inflater, parent, false)
        }

        override fun convert(
            holder: ItemViewHolder,
            binding: ItemBatchGroupBinding,
            item: String,
            payloads: MutableList<Any>
        ) {
            binding.cbItem.text = item
            binding.cbItem.isChecked = selected.contains(holder.layoutPosition)
        }

        override fun registerListener(holder: ItemViewHolder, binding: ItemBatchGroupBinding) {
            binding.cbItem.setOnUserCheckedChangeListener { isChecked ->
                if (isChecked) {
                    selected.add(holder.layoutPosition)
                } else {
                    selected.remove(holder.layoutPosition)
                }
            }
        }
    }

}
