package io.legado.app.lib.theme

import android.content.Context
import android.graphics.Color
import android.graphics.drawable.Drawable
import androidx.annotation.AttrRes
import androidx.core.graphics.ColorUtils

/**
 * @author Aidan Follestad (afollestad)
 */
object ThemeUtils {

    @JvmOverloads
    fun resolveColor(context: Context, @AttrRes attr: Int, fallback: Int = 0): Int {
        val a = context.theme.obtainStyledAttributes(intArrayOf(attr))
        return try {
            a.getColor(0, fallback)
        } catch (e: Exception) {
            fallback
        } finally {
            a.recycle()
        }
    }

    @JvmOverloads
    fun resolveFloat(context: Context, @AttrRes attr: Int, fallback: Float = 0.0f): Float {
        val a = context.theme.obtainStyledAttributes(intArrayOf(attr))
        return try {
            a.getFloat(0, fallback)
        } catch (e: Exception) {
            fallback
        } finally {
            a.recycle()
        }
    }

    fun resolveDrawable(context: Context, @AttrRes attr: Int): Drawable? {
        val a = context.theme.obtainStyledAttributes(intArrayOf(attr))
        return try {
            a.getDrawable(0)
        } finally {
            a.recycle()
        }
    }

    /**
     * 字体撞色检测与回退（THEME-B-02）。
     *
     * 检测 [fontColor] 与给定表面色列表 [surfaces] 的对比度，若任意表面对比度低于阈值 [minContrast]，
     * 则从 [fallbackColors] 中选择"与所有表面最小对比度最大"的颜色作为回退。
     *
     * 借鉴 Archive 项目 `ThemeConfig.sanitizeFontColorAgainstSurfaces`，改写为：
     * - 使用 `androidx.core.graphics.ColorUtils` 替代 Archive `AndroidColorUtils`
     * - 移除对 Archive 私有方法 `normalizeThemeColor` 的依赖（调用方负责颜色规范化）
     * - 移除对 Archive 私有方法 `defaultThemeTextColorHex` 的依赖（调用方提供 [fallbackColors]）
     *
     * @param fontColor 待检测的文字颜色（ARGB int）
     * @param surfaces 表面色列表（ARGB int）
     * @param fallbackColors 撞色时的回退候选色列表（调用方提供，如日夜模式默认文字色）
     * @param minContrast 最小对比度阈值（默认 1.3，借鉴 Archive `MIN_FONT_SURFACE_CONTRAST`）
     * @return 撞色时返回回退色，未撞色时返回原 [fontColor]
     *
     * 关联任务：THEME-B-02（P0）
     */
    fun sanitizeFontColorAgainstSurfaces(
        fontColor: Int,
        surfaces: List<Int>,
        fallbackColors: List<Int>,
        minContrast: Double = 1.3
    ): Int {
        if (surfaces.isEmpty()) return fontColor
        // 检测是否撞色：任意表面对比度 < 阈值
        val isClashed = surfaces.any { fontSurfaceContrast(fontColor, it) < minContrast }
        if (!isClashed) return fontColor
        // 撞色：从 fallbackColors 中选择"与所有表面最小对比度最大"的颜色
        return fallbackColors.maxByOrNull { fallback ->
            surfaces.minOf { fontSurfaceContrast(fallback, it) }
        } ?: fontColor
    }

    /**
     * 计算字体与表面的对比度（THEME-B-02）。
     *
     * 借鉴 Archive `fontSurfaceContrast` 方法：
     * - 表面 alpha 强制为 255（不透明）
     * - 字体 alpha < 255 时与表面合成
     * - 调用 `ColorUtils.calculateContrast` 计算对比度
     */
    private fun fontSurfaceContrast(foreground: Int, surface: Int): Double {
        val opaqueSurface = ColorUtils.setAlphaComponent(surface, 255)
        val opaqueForeground = if (Color.alpha(foreground) == 255) {
            foreground
        } else {
            ColorUtils.compositeColors(foreground, opaqueSurface)
        }
        return ColorUtils.calculateContrast(opaqueForeground, opaqueSurface)
    }
}