package io.legado.app.ui.config

import android.os.Bundle
import android.view.View
import io.legado.app.R
import io.legado.app.base.BaseDialogFragment
import io.legado.app.databinding.DialogThemePreviewBinding
import io.legado.app.help.config.ThemeConfig.Config
import io.legado.app.lib.theme.ThemePreviewHelper
import io.legado.app.utils.GSON
import io.legado.app.utils.fromJsonObject
import io.legado.app.utils.setLayout
import io.legado.app.utils.viewbindingdelegate.viewBinding

/**
 * 主题预览 Dialog（THEME-E-05 / P1 / ADR-010a）
 *
 * 设计要点（与 Archive 的差异）：
 * - Archive 主题预览集成在 AppearanceKit 渲染管线中，依赖 Compose + palette + graphicsLayer。
 * - 本项目使用 BaseDialogFragment + ConstraintLayout 简化实现，仅展示核心视觉要素。
 *
 * 与 ThemeListDialog 集成：
 * - 长按主题项弹出本 Dialog（不破坏单击直接应用主题的现有体验）。
 * - 用户点击"应用主题"按钮 → Callback.onApplyTheme(config) → ThemeConfig.applyConfig
 * - 用户点击"关闭"按钮或外部 → dismiss()
 *
 * Config 传递：通过 arguments 用 JSON 序列化（Config 不是 Parcelable）。
 * Dialog 重建时从 arguments 反序列化恢复 Config。
 *
 * 关联任务：THEME-E-05；
 * 依赖：THEME-B-04（Config 扩展字段）、ThemePreviewHelper（预览工具）。
 */
class ThemePreviewDialog() : BaseDialogFragment(R.layout.dialog_theme_preview) {

    private val binding by viewBinding(DialogThemePreviewBinding::bind)

    interface Callback {
        fun onApplyTheme(config: Config)
    }

    private var callback: Callback? = null

    fun setCallback(callback: Callback) {
        this.callback = callback
    }

    constructor(config: Config) : this() {
        arguments = Bundle().apply {
            putString(ARG_CONFIG_JSON, GSON.toJson(config))
        }
    }

    override fun onStart() {
        super.onStart()
        // 简化说明: 占屏宽 92%，高度自适应
        // 已知上限: 横屏下宽度可能过宽，未来可基于资源限定符细化
        setLayout(0.92f, -1)
    }

    override fun onFragmentCreated(view: View, savedInstanceState: Bundle?) {
        val config = loadConfigFromArgs() ?: run {
            dismiss()
            return
        }
        bindConfig(config)
        binding.btnClose.setOnClickListener { dismiss() }
        binding.btnApply.setOnClickListener {
            callback?.onApplyTheme(config)
            dismiss()
        }
    }

    private fun loadConfigFromArgs(): Config? {
        val json = arguments?.getString(ARG_CONFIG_JSON) ?: return null
        return GSON.fromJsonObject<Config>(json).getOrNull()
    }

    private fun bindConfig(config: Config) {
        binding.run {
            tvTitle.text = config.themeName
            tvThemeMode.text = getString(
                if (config.isNightTheme) R.string.theme_preview_night else R.string.theme_preview_day
            )

            // 颜色色块
            vColorPrimary.setBackgroundColor(
                ThemePreviewHelper.parseColor(config.primaryColor, 0xFF795548.toInt())
            )
            vColorAccent.setBackgroundColor(
                ThemePreviewHelper.parseColor(config.accentColor, 0xFFD32F2F.toInt())
            )
            vColorBackground.setBackgroundColor(
                ThemePreviewHelper.parseColor(config.backgroundColor, 0xFFF5F5F5.toInt())
            )
            vColorBottom.setBackgroundColor(
                ThemePreviewHelper.parseColor(config.bottomBackground, 0xFFEEEEEE.toInt())
            )

            // 背景图缩略图
            ThemePreviewHelper.loadBackgroundThumbnail(requireContext(), ivBackground, config)

            // 字体显示名
            tvFontUi.text = getString(
                R.string.theme_preview_font_ui,
                ThemePreviewHelper.getFontDisplayName(config.uiFontPath)
            )
            tvFontTitle.text = getString(
                R.string.theme_preview_font_title,
                ThemePreviewHelper.getFontDisplayName(config.titleFontPath)
            )
        }
    }

    companion object {
        private const val ARG_CONFIG_JSON = "configJson"
    }
}
