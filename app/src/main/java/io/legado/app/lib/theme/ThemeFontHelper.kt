package io.legado.app.lib.theme

import android.content.Context
import android.graphics.Typeface
import android.net.Uri
import android.os.Build
import android.widget.TextView
import androidx.collection.LruCache
import io.legado.app.constant.AppLog
import io.legado.app.utils.FileUtils
import io.legado.app.utils.RealPathUtil
import io.legado.app.utils.externalFiles
import splitties.init.appCtx
import java.io.File

/**
 * 主题字体内嵌支持（THEME-B-05 / P1 / ADR-010a）
 *
 * 设计要点（与 Archive 的差异）：
 * - Archive 通过 AppearanceKit 套件完整接管 UI 字体渲染（含 TextView/Toolbar/TabLayout 等组件替换）。
 * - 本项目保持极简：仅提供通用字体加载工具，由调用方按需应用到目标 View。
 * - 复用本项目 ChapterProvider.getTypeface 的路径兼容逻辑（支持 contentScheme/普通路径/Android O+ FileDescriptor），
 *   但解耦于阅读页字体缓存，独立 LruCache 避免互相污染。
 *
 * 路径格式支持：
 * - contentScheme（content://...）：Android O+ 用 openFileDescriptor，旧版本用 RealPathUtil 转 path
 * - 普通文件路径（/sdcard/.../ui.ttf）：直接 Typeface.createFromFile
 * - 主题包内相对路径（fonts/ui.ttf）：相对于 externalFiles/themeFonts/ 解析
 *
 * 关联任务：THEME-B-05；依赖 THEME-B-04（Config.uiFontPath/titleFontPath 字段）。
 */
object ThemeFontHelper {

    private const val FONT_DIR_NAME = "themeFonts"
    private const val MAX_CACHE_SIZE = 8

    private val typefaceCache = LruCache<String, Typeface>(MAX_CACHE_SIZE)

    /**
     * 加载字体文件为 Typeface。
     *
     * @param path 字体文件路径。可为 contentScheme URI、普通文件绝对路径、主题包内相对路径。
     *             为空或空白时返回 null（调用方按"使用默认字体"处理）。
     * @return 加载成功的 Typeface，加载失败返回 null（已记录日志，调用方无需再 try-catch）
     */
    fun loadTypeface(path: String?): Typeface? {
        if (path.isNullOrBlank()) return null
        typefaceCache[path]?.let { return it }
        val typeface = kotlin.runCatching {
            when {
                path.isContentScheme() && Build.VERSION.SDK_INT >= Build.VERSION_CODES.O -> {
                    appCtx.contentResolver
                        .openFileDescriptor(Uri.parse(path), "r")!!
                        .use { fd ->
                            Typeface.Builder(fd.fileDescriptor).build()
                        }
                }
                path.isContentScheme() -> {
                    Typeface.createFromFile(RealPathUtil.getPath(appCtx, Uri.parse(path)))
                }
                isRelativePath(path) -> {
                    val file = File(appCtx.externalFiles, FONT_DIR_NAME).let { File(it, path) }
                    if (file.exists()) Typeface.createFromFile(file) else null
                }
                else -> Typeface.createFromFile(path)
            }
        }.onFailure { e ->
            AppLog.put("ThemeFontHelper: load typeface failed, path=${path.takeLast(64)}", e)
        }.getOrNull() ?: return null
        typefaceCache.put(path, typeface)
        return typeface
    }

    /**
     * 将外部 URI 字体文件复制到内部存储 themeFonts 目录，返回内部存储绝对路径。
     * 用于用户从文件选择器导入字体到主题包。
     *
     * @param context 上下文
     * @param uri 字体文件 URI（content:// 或 file://）
     * @param targetName 目标文件名（如 "ui.ttf"），若为空则使用 URI 最后一段
     * @return 复制成功返回内部存储绝对路径，失败返回 null
     */
    fun copyFontToInternalStorage(context: Context, uri: Uri, targetName: String? = null): String? {
        return kotlin.runCatching {
            val fontDir = File(context.externalFiles, FONT_DIR_NAME)
            if (!fontDir.exists()) fontDir.mkdirs()
            val fileName = targetName?.takeIf { it.isNotBlank() }
                ?: uri.lastPathSegment?.substringAfterLast('/')
                ?: "font_${System.currentTimeMillis()}.ttf"
            val targetFile = File(fontDir, fileName)
            context.contentResolver.openInputStream(uri)?.use { input ->
                targetFile.outputStream().use { output ->
                    input.copyTo(output)
                }
            } ?: return null
            targetFile.absolutePath
        }.onFailure { e ->
            AppLog.put("ThemeFontHelper: copy font failed", e)
        }.getOrNull()
    }

    /**
     * 应用 UI 字体到 TextView。
     *
     * @param textView 目标 TextView
     * @param path 字体文件路径，为空时恢复默认 Typeface
     */
    fun applyToTextView(textView: TextView, path: String?) {
        if (path.isNullOrBlank()) {
            textView.typeface = Typeface.DEFAULT
            return
        }
        loadTypeface(path)?.let { textView.typeface = it }
    }

    /**
     * 清空字体缓存。切换主题时调用，避免旧主题字体残留。
     */
    fun clearCache() {
        typefaceCache.evictAll()
    }

    /**
     * 清理 themeFonts 目录中未被任何主题引用的字体文件。
     * 在主题删除或主题包卸载时调用。
     *
     * @param inUsePaths 仍被引用的字体路径列表
     */
    fun cleanupOrphanFonts(inUsePaths: Set<String>) {
        kotlin.runCatching {
            val fontDir = File(appCtx.externalFiles, FONT_DIR_NAME)
            if (!fontDir.exists()) return
            fontDir.listFiles()?.forEach { file ->
                if (file.absolutePath !in inUsePaths) {
                    FileUtils.delete(file.absolutePath)
                }
            }
        }.onFailure { e ->
            AppLog.put("ThemeFontHelper: cleanup orphan fonts failed", e)
        }
    }

    private fun isRelativePath(path: String): Boolean {
        return !path.startsWith("/") && !path.startsWith("content:") && !path.startsWith("file:")
    }

    private fun String.isContentScheme(): Boolean = startsWith("content:")
}
