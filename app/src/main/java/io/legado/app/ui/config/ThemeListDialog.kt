package io.legado.app.ui.config

import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.view.MenuItem
import android.view.View
import android.view.ViewGroup
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.widget.Toolbar
import androidx.core.content.FileProvider
import androidx.recyclerview.widget.LinearLayoutManager
import io.legado.app.R
import io.legado.app.base.BaseDialogFragment
import io.legado.app.base.adapter.ItemViewHolder
import io.legado.app.base.adapter.RecyclerAdapter
import io.legado.app.constant.AppConst
import io.legado.app.constant.AppLog
import io.legado.app.databinding.DialogRecyclerViewBinding
import io.legado.app.databinding.ItemThemeConfigBinding
import io.legado.app.help.config.ThemeConfig
import io.legado.app.lib.dialogs.alert
import io.legado.app.lib.theme.ThemePackageManager
import io.legado.app.lib.theme.primaryColor
import io.legado.app.ui.widget.recycler.VerticalDivider
import io.legado.app.utils.*
import io.legado.app.utils.viewbindingdelegate.viewBinding
import java.io.File

class ThemeListDialog : BaseDialogFragment(R.layout.dialog_recycler_view),
    Toolbar.OnMenuItemClickListener,
    ThemePreviewDialog.Callback {

    private val binding by viewBinding(DialogRecyclerViewBinding::bind)
    private val adapter by lazy { Adapter(requireContext()) }

    // BUG-001 修复：ZIP 文件导入 launcher（THEME-B-03 / THEME-E-04）
    // 简化说明：使用 ActivityResultContracts.OpenDocument 选择 ZIP 文件
    // 已知上限：仅支持 application/zip 和 application/octet-stream MIME，未覆盖所有 ZIP 变体
    // 升级路径：未来可支持 GetContent + 多选导入多个 ZIP
    private val importZipLauncher = registerForActivityResult(
        ActivityResultContracts.OpenDocument()
    ) { uri: Uri? ->
        if (uri != null) {
            val cfg = ThemePackageManager.importThemeZip(requireContext(), uri)
            if (cfg != null) {
                initData()
                toastOnUi("主题包导入成功：${cfg.themeName}")
            } else {
                toastOnUi("ZIP 导入失败，请检查文件格式或 formatVersion")
            }
        }
    }

    override fun onStart() {
        super.onStart()
        setLayout(0.9f, 0.9f)
    }

    override fun onFragmentCreated(view: View, savedInstanceState: Bundle?) {
        binding.toolBar.setBackgroundColor(primaryColor)
        binding.toolBar.setTitle(R.string.theme_list)
        initView()
        initMenu()
        initData()
    }

    private fun initView() = binding.run {
        recyclerView.layoutManager = LinearLayoutManager(requireContext())
        recyclerView.addItemDecoration(VerticalDivider(requireContext()))
        recyclerView.adapter = adapter
    }

    private fun initMenu() = binding.run {
        toolBar.setOnMenuItemClickListener(this@ThemeListDialog)
        toolBar.inflateMenu(R.menu.theme_list)
        toolBar.menu.applyTint(requireContext())
    }

    fun initData() {
        adapter.setItems(ThemeConfig.configList)
    }

    override fun onMenuItemClick(item: MenuItem?): Boolean {
        when (item?.itemId) {
            R.id.menu_import -> {
                requireContext().getClipText()?.let {
                    if (ThemeConfig.addConfig(it)) {
                        initData()
                    } else {
                        toastOnUi("格式不对,添加失败")
                    }
                }
            }
            // BUG-001 修复：从 ZIP 文件导入主题（THEME-B-03）
            R.id.menu_import_zip -> {
                importZipLauncher.launch(arrayOf("application/zip", "application/octet-stream"))
            }
            // BUG-001 修复：导出所有主题为 ZIP 文件并分享（THEME-B-03 + THEME-E-04 formatVersion）
            R.id.menu_export_zip -> {
                exportAllThemesAsZip()
            }
        }
        return true
    }

    /**
     * 导出所有主题为 ZIP 文件并分享（THEME-B-03 + THEME-E-04）。
     *
     * 简化说明：循环调用 ThemePackageManager.exportThemeZip 导出每个主题为独立 ZIP 文件，
     * 然后用 Intent.ACTION_SEND_MULTIPLE 分享所有 ZIP 文件。
     * 已知上限：所有 ZIP 文件位于 cacheDir/themeExport/，导出后不自动清理（用户清理缓存时删除）。
     * 升级路径：未来可支持选择导出单个主题或打包为单一 ZIP。
     */
    private fun exportAllThemesAsZip() {
        if (ThemeConfig.configList.isEmpty()) {
            toastOnUi("没有可导出的主题")
            return
        }
        val zipFiles = mutableListOf<File>()
        ThemeConfig.configList.forEach { config ->
            ThemePackageManager.exportThemeZip(requireContext(), config)?.let { zipFiles.add(it) }
        }
        if (zipFiles.isEmpty()) {
            toastOnUi("导出失败")
            return
        }
        shareZipFiles(zipFiles)
        AppLog.putDebug("ThemeListDialog: export ${zipFiles.size} themes as zip")
    }

    /**
     * 分享多个 ZIP 文件（Intent.ACTION_SEND_MULTIPLE）。
     */
    private fun shareZipFiles(zipFiles: List<File>) {
        kotlin.runCatching {
            val context = requireContext()
            val uris = zipFiles.map {
                FileProvider.getUriForFile(context, AppConst.authority, it)
            }
            val intent = Intent(Intent.ACTION_SEND_MULTIPLE).apply {
                type = "application/zip"
                putParcelableArrayListExtra(Intent.EXTRA_STREAM, ArrayList(uris))
                addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            }
            startActivity(Intent.createChooser(intent, "主题包导出"))
        }.onFailure { e ->
            AppLog.put("ThemeListDialog: share zip files failed", e)
            // 简化说明：多文件分享失败时回退到单文件分享（仅分享第一个 ZIP）
            zipFiles.firstOrNull()?.let { requireContext().share(it, "application/zip") }
        }
    }

    fun delete(index: Int) {
        alert(R.string.delete, R.string.sure_del) {
            yesButton {
                ThemeConfig.delConfig(index)
                initData()
            }
            noButton()
        }
    }

    fun share(index: Int) {
        val json = GSON.toJson(ThemeConfig.configList[index])
        requireContext().share(json, "主题分享")
    }

    inner class Adapter(context: Context) :
        RecyclerAdapter<ThemeConfig.Config, ItemThemeConfigBinding>(context) {

        override fun getViewBinding(parent: ViewGroup): ItemThemeConfigBinding {
            return ItemThemeConfigBinding.inflate(inflater, parent, false)
        }

        override fun convert(
            holder: ItemViewHolder,
            binding: ItemThemeConfigBinding,
            item: ThemeConfig.Config,
            payloads: MutableList<Any>
        ) {
            binding.apply {
                tvName.text = item.themeName
            }
        }

        override fun registerListener(holder: ItemViewHolder, binding: ItemThemeConfigBinding) {
            binding.apply {
                root.setOnClickListener {
                    ThemeConfig.applyConfig(context, ThemeConfig.configList[holder.layoutPosition])
                }
                // THEME-E-05: 长按预览主题（不破坏单击应用主题的现有体验）
                root.setOnLongClickListener {
                    val config = ThemeConfig.configList[holder.layoutPosition]
                    ThemePreviewDialog(config).apply {
                        setCallback(this@ThemeListDialog)
                    }.show(childFragmentManager, "themePreview")
                    true
                }
                ivShare.setOnClickListener {
                    share(holder.layoutPosition)
                }
                ivDelete.setOnClickListener {
                    delete(holder.layoutPosition)
                }
            }
        }

    }

    /**
     * ThemePreviewDialog.Callback：用户在预览 Dialog 点击"应用主题"时应用主题
     */
    override fun onApplyTheme(config: ThemeConfig.Config) {
        ThemeConfig.applyConfig(requireContext(), config)
    }
}