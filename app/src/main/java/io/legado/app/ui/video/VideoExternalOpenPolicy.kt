package io.legado.app.ui.video

import java.io.File

/**
 * 本地视频外部播放的路径判定（**纯逻辑，可 JVM 单测**）。
 *
 * 为什么单独抽出来：真机崩溃 `FileUriExposedException`（2026-10-22）的修复要点是
 * 「先判定是不是本地文件，再决定走 FileProvider 转 content://」——
 * 判定一旦写错（把网络地址当本地文件）就会退化成"能播的播不了"，
 * 而这部分逻辑不需要 Android 环境即可用期望值钉死。
 */
internal object VideoExternalOpenPolicy {

    private const val FILE_SCHEME = "file://"

    /**
     * 本地文件路径（**恒用 `/` 分隔**，与平台无关）⇒ 可直接 `File(path)` 交 FileProvider；
     * 非本地（http/https/content/协议相对等）⇒ null。
     *
     * 判定口径：
     * - `file://` 前缀（大小写不敏感）⇒ 取其后的**绝对**路径；`file://host/path` 形式一律不支持外发；
     * - 以单个 `/` 开头的绝对路径 ⇒ 直接用（历史播放记录里存在这种裸路径）；
     * - 其余（含 `//host/...` 协议相对、`http://`、`content://`）⇒ null。
     */
    fun localFilePathOf(url: String?): String? {
        if (url.isNullOrBlank()) return null
        if (url.startsWith(FILE_SCHEME, ignoreCase = true)) {
            val path = url.substring(FILE_SCHEME.length)
            return path.takeIf { it.startsWith("/") && !it.startsWith("//") }
        }
        return url.takeIf { it.startsWith("/") && !it.startsWith("//") }
    }

    /** [localFilePathOf] 的 `File` 形式（供 `FileProvider.getUriForFile` 使用）。 */
    fun localFileOf(url: String?): File? = localFilePathOf(url)?.let(::File)
}
