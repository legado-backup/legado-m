package io.legado.app.lib.theme

import android.content.Context
import android.net.Uri
import io.legado.app.constant.AppLog
import io.legado.app.help.config.ThemeConfig
import io.legado.app.help.config.ThemeConfig.Config
import io.legado.app.utils.GSON
import io.legado.app.utils.externalFiles
import io.legado.app.utils.getFile
import io.legado.app.utils.inputStream
import io.legado.app.utils.fromJsonObject
import java.io.File
import java.io.FileOutputStream
import java.util.zip.ZipEntry
import java.util.zip.ZipInputStream
import java.util.zip.ZipOutputStream

/**
 * 主题包 ZIP 导入导出管理器（THEME-B-03 + THEME-E-04 / P1 / ADR-010a）
 *
 * 设计要点（与 Archive 的差异）：
 * - Archive ThemePackageManager 1428 行，含 5 种 RED 格式兼容、目录化主题包、云端同步等。
 * - 本项目保持极简：仅实现标准 ZIP 格式的导入导出，单一格式（theme.json + 资源文件）。
 * - 5 种 RED 格式兼容留到 P2（THEME-E-01）。
 * - 目录化主题包结构留到 P2（THEME-E-02）。
 *
 * THEME-E-04 格式版本化：
 * - theme.json 中包含 formatVersion 字段，标识主题包格式版本。
 * - 当前版本 FORMAT_VERSION_CURRENT = 1，与 v0（缺失字段）文件结构一致，仅增加版本标识。
 * - 导入时校验 formatVersion，超出已知版本范围时拒绝导入并提示用户升级。
 *
 * ZIP 包结构（THEME-E-04 统一格式）：
 * ```
 * {themeName}.zip
 *   ├── theme.json       (Config JSON，必需，含 formatVersion 字段)
 *   ├── bg_light.*       (日间主题背景图，可选，仅 isNightTheme=false 时写入)
 *   ├── bg_night.*       (夜间主题背景图，可选，仅 isNightTheme=true 时写入)
 *   ├── fonts/
 *     ├── ui.ttf         (UI 字体，可选，从 uiFontPath 读取)
 *     └── title.ttf      (标题字体，可选，从 titleFontPath 读取)
 * ```
 *
 * 关联任务：THEME-B-03（基础导入导出）、THEME-E-04（格式统一）；
 * 依赖：THEME-B-04（Config 字段扩展）、THEME-B-05（ThemeFontHelper 字体加载）。
 */
object ThemePackageManager {

    const val THEME_ENTRY_JSON = "theme.json"

    /**
     * 当前主题包格式版本（THEME-E-04）。
     * - v0（历史）：未版本化，theme.json 不含 formatVersion 字段。
     * - v1（当前）：与 v0 文件结构一致，仅增加 formatVersion 元数据标识。
     */
    const val FORMAT_VERSION_CURRENT = 1

    /**
     * 已知支持的格式版本范围。
     * 导入时若 formatVersion 超出此范围（且非 null），拒绝导入并提示用户升级。
     */
    private val FORMAT_VERSION_SUPPORTED = setOf(null, 0, 1)

    private const val FONT_DIR_IN_ZIP = "fonts/"
    private const val BG_LIGHT_PREFIX = "bg_light"
    private const val BG_NIGHT_PREFIX = "bg_night"
    private const val EXPORT_DIR_NAME = "themeExport"

    /**
     * 导出主题为 ZIP 文件。
     *
     * @param context 上下文
     * @param config 主题配置（将克隆后写入 formatVersion，不污染内存中的 configList）
     * @return 导出的 ZIP 文件（位于 cacheDir/themeExport/），失败返回 null
     */
    fun exportThemeZip(context: Context, config: Config): File? {
        return kotlin.runCatching {
            val exportDir = context.cacheDir.getFile(EXPORT_DIR_NAME).apply {
                if (!exists()) mkdirs()
            }
            val safeName = config.themeName.normalizeFileName().ifBlank { "theme" }
            val zipFile = File(exportDir, "$safeName.zip")
            if (zipFile.exists()) zipFile.delete()

            // 克隆 config 并写入 formatVersion，避免污染内存中的 configList
            val exportConfig = config.copy(formatVersion = FORMAT_VERSION_CURRENT)

            ZipOutputStream(FileOutputStream(zipFile)).use { zos ->
                // 写入 theme.json（含 formatVersion 元数据）
                zos.putNextEntry(ZipEntry(THEME_ENTRY_JSON))
                zos.write(GSON.toJson(exportConfig).toByteArray(Charsets.UTF_8))
                zos.closeEntry()

                // 写入背景图：根据 isNightTheme 选择前缀，避免同时写入造成导入歧义
                writeBackgroundImage(zos, exportConfig)

                // 写入字体文件
                writeFontFile(zos, exportConfig.uiFontPath, "${FONT_DIR_IN_ZIP}ui.ttf")
                writeFontFile(zos, exportConfig.titleFontPath, "${FONT_DIR_IN_ZIP}title.ttf")
            }
            zipFile
        }.onFailure { e ->
            AppLog.put("ThemePackageManager: export theme zip failed", e)
        }.getOrNull()
    }

    /**
     * 从 URI 导入主题 ZIP。
     *
     * @param context 上下文
     * @param uri ZIP 文件 URI（content:// 或 file://）
     * @return 导入成功的 Config（已写入 configList 并落盘），失败返回 null
     */
    fun importThemeZip(context: Context, uri: Uri): Config? {
        return kotlin.runCatching {
            var config: Config? = null
            // 资源文件按 ZIP 内条目名前缀分类暂存，导入完成后根据 config.isNightTheme 选择性应用
            val bgLightFiles = mutableListOf<File>()
            val bgNightFiles = mutableListOf<File>()
            val fontFiles = mutableMapOf<String, File>()

            uri.inputStream(context).getOrThrow().use { input ->
                ZipInputStream(input).use { zis ->
                    var entry = zis.nextEntry
                    while (entry != null) {
                        val entryName = entry.name
                        if (!entry.isDirectory) {
                            when {
                                entryName == THEME_ENTRY_JSON -> {
                                    val json = zis.readBytes().toString(Charsets.UTF_8)
                                    config = parseConfig(json)
                                }
                                entryName.startsWith(BG_LIGHT_PREFIX) -> {
                                    saveEntryToFile(context, zis, "bgLight", entryName.substringAfterLast('.', "jpg"))
                                        ?.let { bgLightFiles.add(it) }
                                }
                                entryName.startsWith(BG_NIGHT_PREFIX) -> {
                                    saveEntryToFile(context, zis, "bgNight", entryName.substringAfterLast('.', "jpg"))
                                        ?.let { bgNightFiles.add(it) }
                                }
                                entryName.startsWith(FONT_DIR_IN_ZIP) -> {
                                    val fontName = entryName.substringAfterLast('/')
                                    saveEntryToFile(context, zis, "themeFonts", fontName.substringAfterLast('.', "ttf"))
                                        ?.let { fontFiles[fontName] = it }
                                }
                            }
                        }
                        zis.closeEntry()
                        entry = zis.nextEntry
                    }
                }
            }

            val cfg = config ?: run {
                AppLog.put("ThemePackageManager: import failed, theme.json missing or invalid")
                return null
            }

            // THEME-E-04 格式版本校验
            if (!FORMAT_VERSION_SUPPORTED.contains(cfg.formatVersion)) {
                AppLog.put("ThemePackageManager: unsupported formatVersion=${cfg.formatVersion}")
                return null
            }

            // 应用资源路径：根据 cfg.isNightTheme 选择对应的背景图前缀
            // (日间主题应用 bg_light.*，夜间主题应用 bg_night.*)
            val bgFiles = if (cfg.isNightTheme) bgNightFiles else bgLightFiles
            bgFiles.firstOrNull()?.let { cfg.backgroundImgPath = it.absolutePath }

            // 应用字体路径（ZIP 内字体已解压到 themeFonts 目录，ThemeFontHelper 按相对路径加载）
            fontFiles["${FONT_DIR_IN_ZIP}ui.ttf"]?.let { cfg.uiFontPath = it.absolutePath }
            fontFiles["${FONT_DIR_IN_ZIP}title.ttf"]?.let { cfg.titleFontPath = it.absolutePath }

            // 清除 formatVersion，避免写入 themeConfig.json 时引入元数据字段
            cfg.formatVersion = null

            ThemeConfig.addConfig(cfg)
            cfg
        }.onFailure { e ->
            AppLog.put("ThemePackageManager: import theme zip failed", e)
        }.getOrNull()
    }

    /**
     * 解析 theme.json 为 Config 对象。
     * 兼容旧版本 Config（缺失 THEME-B-04 扩展字段或 THEME-E-04 formatVersion 时使用 null 默认值）。
     */
    private fun parseConfig(json: String): Config? {
        return GSON.fromJsonObject<Config>(json).getOrNull()
    }

    /**
     * 写入背景图条目到 ZIP。
     * 根据 config.isNightTheme 选择 bg_light 或 bg_night 前缀，避免同时写入造成导入歧义。
     * 仅处理本地文件路径，HTTP URL 在导入时由 ThemeConfig.applyConfig 重新下载。
     */
    private fun writeBackgroundImage(zos: ZipOutputStream, config: Config) {
        val imgPath = config.backgroundImgPath ?: return
        if (imgPath.startsWith("http")) return
        val file = File(imgPath)
        if (!file.exists() || !file.isFile) return
        val prefix = if (config.isNightTheme) BG_NIGHT_PREFIX else BG_LIGHT_PREFIX
        val ext = file.extension.ifBlank { "jpg" }
        val entryName = "$prefix.$ext"
        zos.putNextEntry(ZipEntry(entryName))
        file.inputStream().use { it.copyTo(zos) }
        zos.closeEntry()
    }

    /**
     * 写入字体文件条目到 ZIP。
     */
    private fun writeFontFile(zos: ZipOutputStream, fontPath: String?, entryName: String) {
        if (fontPath.isNullOrBlank()) return
        val file = File(fontPath)
        if (!file.exists() || !file.isFile) return
        zos.putNextEntry(ZipEntry(entryName))
        file.inputStream().use { it.copyTo(zos) }
        zos.closeEntry()
    }

    /**
     * 将 ZIP 条目保存到内部存储指定目录。
     *
     * @return 保存成功返回文件对象，失败返回 null
     */
    private fun saveEntryToFile(
        context: Context,
        zis: ZipInputStream,
        subDir: String,
        fallbackName: String
    ): File? {
        return kotlin.runCatching {
            val targetDir = File(context.externalFiles, subDir)
            if (!targetDir.exists()) targetDir.mkdirs()
            val targetFile = File(targetDir, "theme_${System.currentTimeMillis()}_$fallbackName")
            FileOutputStream(targetFile).use { zis.copyTo(it) }
            targetFile
        }.onFailure { e ->
            AppLog.put("ThemePackageManager: save entry to file failed", e)
        }.getOrNull()
    }

    /**
     * 文件名规范化：保留中英文+数字+下划线+连字符，其余替换为下划线。
     */
    private fun String.normalizeFileName(): String {
        val regex = Regex("[^\\u4e00-\\u9fa5a-zA-Z0-9_\\-]")
        return regex.replace(this, "_").trim('_')
    }
}
