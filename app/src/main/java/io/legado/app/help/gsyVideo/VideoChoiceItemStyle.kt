package io.legado.app.help.gsyVideo

import android.content.Context
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.widget.TextView
import io.legado.app.help.config.AppConfig
import io.legado.app.lib.theme.ThemeStore
import io.legado.app.lib.theme.UiCorner
import io.legado.app.lib.theme.themeDividerColorOrDefault
import io.legado.app.utils.ColorUtils

/**
 * 视频选集/倍速项的**统一样式**（video-cache-and-multiep V4 抽取）。
 *
 * 原逻辑散落在历史列表适配器与 [ChoiceSpeedDialog] 内；选集网格改用 RecyclerView 后
 * 需要第二份 ⇒ 抽为单点函数，避免多处样式漂移（选中 accent 文字 + accent 20% 圆角底 /
 * 未选中主题文字 + 混色底 + divider 描边）。
 */
internal fun applyVideoChoiceItemStyle(
    context: Context,
    textView: TextView,
    selected: Boolean,
) {
    if (selected) {
        val accentColor = ThemeStore.accentColor(context)
        textView.setTextColor(accentColor)
        textView.setTypeface(textView.typeface, Typeface.BOLD)
        val radius = UiCorner.panelRadius(context).toFloat()
        textView.background = GradientDrawable().apply {
            cornerRadius = radius
            setColor(
                Color.argb(
                    0x33,
                    Color.red(accentColor),
                    Color.green(accentColor),
                    Color.blue(accentColor)
                )
            )
        }
    } else {
        textView.setTextColor(ThemeStore.textColorPrimary(context))
        textView.setTypeface(textView.typeface, Typeface.NORMAL)
        val surface = ThemeStore.backgroundColor(context)
        val accent = ThemeStore.accentColor(context)
        val field = ColorUtils.blendColors(
            surface,
            accent,
            if (AppConfig.isNightTheme) 0.10f else 0.05f
        )
        val radius = UiCorner.actionRadius(context).toFloat()
        textView.background = GradientDrawable().apply {
            cornerRadius = radius
            setColor(field)
            setStroke(
                context.resources.displayMetrics.density.toInt().coerceAtLeast(1),
                context.themeDividerColorOrDefault()
            )
        }
    }
}
