package io.legado.app.lib.theme

import android.graphics.Canvas
import android.graphics.Paint
import io.legado.app.help.config.ReadBookConfig

/**
 * 纸墨风格工具类（THEME-B-01）。
 *
 * 借鉴 Archive 项目 `io.legado.app.help.PaperInkHelper`，改写为本地 `lib/theme/` 包路径。
 *
 * 核心原理：通过 [Paint.setShadowLayer] 为文字添加墨迹晕染阴影，模拟纸质印刷效果。
 * - strength=0：禁用（直接绘制，无阴影）
 * - strength=100：最强（radius=3.3f, offset=5.0f）
 *
 * 字段依赖：[ReadBookConfig.paperInkStrength]（Int 类型，coerceIn(0, 100) 限定范围）。
 *
 * 关联任务：THEME-B-01（P0）
 */
object PaperInkHelper {

    val strength: Int
        get() = ReadBookConfig.paperInkStrength

    /**
     * 绘制背景（空实现）。
     * 文字阴影不改背景，避免页面发灰或发黄。
     */
    fun drawBackground(canvas: Canvas, width: Int, height: Int, paint: Paint) {
        // 文字阴影不改背景，避免页面发灰或发黄。
    }

    /**
     * 绘制带纸墨效果的文字（指定起止位置）。
     *
     * @param enableBlend 是否启用阴影混合（默认 true）；false 时退化为直接绘制
     */
    fun drawText(
        canvas: Canvas,
        text: String,
        start: Int,
        end: Int,
        x: Float,
        y: Float,
        paint: Paint,
        enableBlend: Boolean = true
    ) {
        if (strength <= 0 || !enableBlend) {
            canvas.drawText(text, start, end, x, y, paint)
            return
        }
        drawTextBlock(canvas, paint) {
            canvas.drawText(text, start, end, x, y, paint)
        }
    }

    /**
     * 绘制带纸墨效果的文字（全文本）。
     */
    fun drawText(
        canvas: Canvas,
        text: String,
        x: Float,
        y: Float,
        paint: Paint,
        enableBlend: Boolean = true
    ) {
        drawText(canvas, text, 0, text.length, x, y, paint, enableBlend)
    }

    /**
     * 纸墨效果绘制块：在 [draw] lambda 执行期间临时为 [paint] 设置阴影层，执行后清除。
     *
     * 阴影参数计算：
     * - ratio = strength / 100f（0.0 ~ 1.0）
     * - radius = 0.3f + 3.0f * ratio（0.3 ~ 3.3，模糊半径）
     * - offset = 0.5f + 4.5f * ratio（0.5 ~ 5.0，阴影偏移）
     * - shadowColor = 0xFF000000（纯黑，alpha=255）
     */
    fun drawTextBlock(canvas: Canvas, paint: Paint, draw: () -> Unit) {
        val strength = strength
        if (strength <= 0) {
            draw()
            return
        }
        val ratio = strength / 100f
        val radius = 0.3f + 3.0f * ratio
        val offset = 0.5f + 4.5f * ratio
        paint.setShadowLayer(radius, offset, offset, 0xFF000000.toInt())
        draw()
        paint.clearShadowLayer()
    }

}
