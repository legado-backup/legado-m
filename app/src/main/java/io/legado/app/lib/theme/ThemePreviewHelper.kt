package io.legado.app.lib.theme

import android.content.Context
import android.graphics.Color
import android.graphics.drawable.Drawable
import android.widget.ImageView
import androidx.core.graphics.drawable.toDrawable
import io.legado.app.constant.AppLog
import io.legado.app.help.config.ThemeConfig.Config
import io.legado.app.utils.BitmapUtils
import io.legado.app.utils.MD5Utils
import io.legado.app.utils.externalFiles
import io.legado.app.utils.stackBlur
import splitties.init.appCtx
import java.io.File

/**
 * 主题预览工具类（THEME-E-05 / P1 / ADR-010a）
 *
 * 设计要点（与 Archive 的差异）：
 * - Archive 通过 AppearanceKit 套件完整接管 UI 渲染，预览直接复用渲染管线。
 * - 本项目保持极简：仅提供 Config → 预览视图 的数据映射工具，不引入渲染框架。
 *
 * 职责：
 * - 解析 Config 颜色字段为 ColorInt（容错处理无效色值）。
 * - 加载背景图缩略图（本地路径/HTTP URL 缓存路径，失败回退到背景色）。
 * - 获取字体显示名（路径 → 文件名，未配置时返回默认标识）。
 *
 * 关联任务：THEME-E-05；
 * 依赖：THEME-B-04（Config 扩展字段）、THEME-B-05（ThemeFontHelper 字体加载）。
 */
object ThemePreviewHelper {

    private const val DEFAULT_FONT_LABEL = "默认"

    /**
     * 解析颜色字符串为 ColorInt。
     * 支持 "#RRGGBB" / "#AARRGGBB" / "RRGGBB" 格式，解析失败返回 fallback。
     */
    fun parseColor(colorHex: String?, fallback: Int): Int {
        if (colorHex.isNullOrBlank()) return fallback
        return kotlin.runCatching {
            if (colorHex.startsWith("#")) {
                Color.parseColor(colorHex)
            } else {
                Color.parseColor("#$colorHex")
            }
        }.getOrDefault(fallback)
    }

    /**
     * 加载背景图到 ImageView。
     * - 本地路径：直接 decode + 模糊（与 ThemeConfig.getBgImage 一致体验）。
     * - HTTP URL：从缓存目录查找（ThemeConfig.getUrlToFile 命名规则），找不到则回退到背景色。
     * - null/空：清空 ImageView 内容。
     *
     * @param context 上下文
     * @param imageView 目标 ImageView
     * @param config 主题配置
     * @param blurRadius 模糊半径（与 ThemeConfig.applyConfig 中 bgImageBlurring 配合）
     */
    fun loadBackgroundThumbnail(
        context: Context,
        imageView: ImageView,
        config: Config,
        blurRadius: Int = config.backgroundImgBlur
    ) {
        val imgPath = config.backgroundImgPath
        if (imgPath.isNullOrBlank()) {
            imageView.setImageDrawable(null)
            imageView.setBackgroundColor(parseColor(config.backgroundColor, Color.WHITE))
            return
        }
        val drawable = kotlin.runCatching {
            when {
                imgPath.startsWith("http") -> {
                    // 从缓存目录查找（命名规则参考 ThemeConfig.getUrlToFile）
                    val cacheFile = findCachedBgImage(imgPath, config.isNightTheme)
                    if (cacheFile?.exists() == true) {
                        decodeBgDrawable(cacheFile.absolutePath, blurRadius)
                    } else null
                }
                else -> {
                    if (File(imgPath).exists()) decodeBgDrawable(imgPath, blurRadius) else null
                }
            }
        }.onFailure { e ->
            AppLog.put("ThemePreviewHelper: load background thumbnail failed", e)
        }.getOrNull()
        if (drawable != null) {
            imageView.setImageDrawable(drawable)
        } else {
            // 加载失败时回退为背景色
            imageView.setImageDrawable(null)
            imageView.setBackgroundColor(parseColor(config.backgroundColor, Color.WHITE))
        }
    }

    /**
     * 获取字体显示名（路径 → 文件名，去扩展名）。
     * 未配置或路径为空时返回 "默认"。
     */
    fun getFontDisplayName(fontPath: String?): String {
        if (fontPath.isNullOrBlank()) return DEFAULT_FONT_LABEL
        val file = File(fontPath)
        return kotlin.runCatching {
            file.nameWithoutExtension.takeIf { it.isNotBlank() } ?: DEFAULT_FONT_LABEL
        }.getOrDefault(DEFAULT_FONT_LABEL)
    }

    /**
     * 在缓存目录中查找背景图。
     * 命名规则参考 ThemeConfig.getUrlToFile（MD5+后缀）。
     */
    private fun findCachedBgImage(url: String, isNight: Boolean): File? {
        return kotlin.runCatching {
            val fileRoot = appCtx.externalFiles
            val preferenceKey = if (isNight) "bgImageN" else "bgImage"
            val bgDir = File(fileRoot, preferenceKey)
            if (!bgDir.exists()) return null
            // 简化匹配：查找 .9.png/.png/.jpg/.webp/.gif 中任一存在的缓存文件
            val md5 = MD5Utils.md5Encode16(url)
            listOf(".9.png", ".png", ".jpg", ".webp", ".gif").forEach { ext ->
                val file = File(bgDir, "$md5$ext")
                if (file.exists()) return file
            }
            null
        }.getOrNull()
    }

    /**
     * 解码背景图为 Drawable。
     * .9.png 走 decodeNinePatchDrawable（返回 Drawable?），其他走 decodeBitmap + 可选模糊。
     */
    private fun decodeBgDrawable(path: String, blurRadius: Int): Drawable? {
        return if (path.endsWith(".9.png")) {
            BitmapUtils.decodeNinePatchDrawable(path)
        } else {
            val metrics = appCtx.resources.displayMetrics
            val bitmap = BitmapUtils.decodeBitmap(path, metrics.widthPixels, metrics.heightPixels)
                ?: return null
            val processed = if (blurRadius > 0) bitmap.stackBlur(blurRadius) else bitmap
            processed.toDrawable(appCtx.resources)
        }
    }
}
