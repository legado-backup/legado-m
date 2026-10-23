package io.legado.app.help.gsyVideo

import android.app.Dialog
import android.content.Context
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.os.Bundle
import android.view.Gravity
import android.view.LayoutInflater
import android.view.View
import android.view.WindowManager
import android.widget.HorizontalScrollView
import android.widget.LinearLayout
import android.widget.TextView
import io.legado.app.R
import io.legado.app.help.config.AppConfig
import io.legado.app.lib.theme.ThemeStore
import io.legado.app.lib.theme.UiCorner
import io.legado.app.lib.theme.themeDividerColorOrDefault
import io.legado.app.utils.ColorUtils
import kotlin.math.roundToInt

/**
 * 倍速选择弹框（video-cache-and-multiep R9 / V5 改版）。
 *
 * 形态由「靠右竖排列表」改为「**底部上浮单排**」：
 *  - 一排固定展示 [VISIBLE_COUNT] 个档位，超出部分横向滑动（不换行 ⇒ 高度恒为一行，不裁剪视频）
 *  - 当前倍速高亮并自动滚到可见位置
 *  - 容器宽度 = 屏宽减左右留白，圆角/底色跟随主题（ThemeStore）
 */
class ChoiceSpeedDialog(private val mContext: Context) : Dialog(
    mContext, R.style.dialog_style
) {
    private var scrollView: HorizontalScrollView? = null
    private var row: LinearLayout? = null
    private var onItemClickListener: OnListItemClickListener? = null
    private var data: List<Float>? = null

    /** 单排可见档位数（需求：剩余正好一排 5 个） */
    private val visibleCount = VISIBLE_COUNT
    /** 横向留白（左右各 16dp） */
    private val sideMarginPx = (16 * mContext.resources.displayMetrics.density).roundToInt()

    interface OnListItemClickListener {
        fun onItemClick(value: Float)
        fun finishDialog()
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
    }

    override fun onStop() {
        onItemClickListener!!.finishDialog()
        super.onStop()
    }

    /**
     * 初始化倍速列表（横向单排，顺序即显示顺序）。
     * @param data 倍速值列表
     * @param onItemClickListener 点击回调
     * @param currentSpeed 当前播放倍速，用于高亮选中项
     */
    fun initList(
        data: List<Float>,
        onItemClickListener: OnListItemClickListener,
        currentSpeed: Float = 1.0f
    ) {
        this.onItemClickListener = onItemClickListener
        this.data = data
        val view: View = LayoutInflater.from(mContext)
            .inflate(R.layout.switch_speed_video_dialog, null)
        scrollView = view.findViewById(R.id.speed_scroll)
        row = view.findViewById(R.id.speed_row)
        setContentView(view)
        val radius = UiCorner.panelRadius(mContext).toFloat()
        view.background = GradientDrawable().apply {
            shape = GradientDrawable.RECTANGLE
            cornerRadius = radius
            setColor(ThemeStore.backgroundColor(mContext))
        }
        buildRow(data, currentSpeed)
        val dialogWindow = window ?: return
        val d = mContext.resources.displayMetrics
        val lp = dialogWindow.attributes
        // 底部上浮：宽度铺满（留左右 8dp 呼吸位），高度随内容（单排）
        lp.width = d.widthPixels - sideMarginPx
        lp.height = WindowManager.LayoutParams.WRAP_CONTENT
        lp.gravity = Gravity.BOTTOM or Gravity.CENTER_HORIZONTAL
        lp.verticalMargin = 0f
        dialogWindow.setAttributes(lp)
        dialogWindow.setDimAmount(0f)
    }

    /**
     * 构建单排档位按钮。
     *
     * 单项宽度 = (弹框宽度 - 行内左右 padding) / visibleCount，
     * 档位数 > visibleCount 时由 HorizontalScrollView 承担横向滑动。
     */
    private fun buildRow(data: List<Float>, currentSpeed: Float) {
        val rowView = row ?: return
        rowView.removeAllViews()
        val d = mContext.resources.displayMetrics
        val rowInnerPaddingPx = (12 * 2 * d.density).roundToInt()
        val available = (d.widthPixels - sideMarginPx) - rowInnerPaddingPx
        val itemWidth = (available / visibleCount).coerceAtLeast((56 * d.density).roundToInt())
        val itemHeight = (44 * d.density).roundToInt()
        val gapPx = (6 * d.density).roundToInt()
        var currentView: TextView? = null
        data.forEachIndexed { index, value ->
            val textView = TextView(mContext).apply {
                layoutParams = LinearLayout.LayoutParams(itemWidth, itemHeight).also {
                    if (index > 0) it.marginStart = gapPx
                }
                gravity = Gravity.CENTER
                textSize = 15f
                text = formatSpeed(value)
                isClickable = true
                isFocusable = true
                setOnClickListener {
                    dismiss()
                    onItemClickListener?.onItemClick(value)
                }
            }
            applyItemStyle(textView, selected = value == currentSpeed)
            if (value == currentSpeed) currentView = textView
            rowView.addView(textView)
        }
        // 当前倍速不在首屏时自动滚到可见位置（分组多时不必手动寻找）
        scrollView?.post {
            val target = currentView ?: return@post
            val left = target.left - (itemWidth * (visibleCount - 1) / 2)
            scrollView?.smoothScrollTo(left.coerceAtLeast(0), 0)
        }
    }

    /** 选中/未选中样式：与改造前口径一致（accent 文字 + accent 20% 圆角底 / 主题描边底） */
    private fun applyItemStyle(textView: TextView, selected: Boolean) {
        val accentColor = ThemeStore.accentColor(mContext)
        val context = mContext
        if (selected) {
            textView.setTextColor(accentColor)
            textView.setTypeface(textView.typeface, Typeface.BOLD)
            val radius = UiCorner.actionRadius(context).toFloat()
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
            val field = ColorUtils.blendColors(
                surface,
                accentColor,
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

    private fun formatSpeed(value: Float): String {
        return if (value == value.toInt().toFloat()) "${value.toInt()}x" else "${value}x"
    }

    companion object {
        /** 单排可见档位数（需求 R9：去掉 0.5 后常用档位正好一排 5 个） */
        const val VISIBLE_COUNT = 5

        /**
         * 倍速档位（去掉 0.5 倍的常用档）。
         *
         * 顺序即显示顺序；更高档位（2.5x 起）保留在末尾，可由横向滑动到达。
         */
        val SPEED_VALUES: List<Float> =
            listOf(0.75f, 1.0f, 1.25f, 1.5f, 2.0f, 2.5f, 3.0f, 5.0f, 10.0f, 15.0f)
    }
}
