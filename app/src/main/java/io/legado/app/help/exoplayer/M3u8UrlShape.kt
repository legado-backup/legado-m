package io.legado.app.help.exoplayer

import java.net.URLDecoder

/**
 * m3u8 URL 形态判定（video-legacy-parity-hls AD-03）。
 *
 * 背景：`getMimeType` 原只认「路径以 `.m3u8` 结尾」与显式 `format=m3u8|type=m3u8`。
 * 代理型播放地址（形如 `/api/v1/m3u8/proxy?path=<相对路径>.m3u8`）两类判据都不命中
 * ⇒ 返回 null（UNKNOWN）⇒ 依赖 6s 内容预检，预检超时/被拒即落 Progressive 解析
 * ⇒ `UnrecognizedInputFormatException(3003)` 黑屏。
 *
 * 判据（任一命中即视为 HLS 形态）：
 * 1. 去 query/fragment 后的路径以 `.m3u8` 结尾（原有）
 * 2. URL 含显式 `format=m3u8` / `type=m3u8`（原有）
 * 3. 去 query 后的路径含 `/m3u8/` 段（代理端点，如 `/api/v1/m3u8/proxy`）
 * 4. 某个 query 参数值是**相对路径**且以 `.m3u8` 结尾（`?path=xxx.m3u8`）
 *
 * 判据 4 刻意排除「参数值是绝对 URL」的情况 —— 历史铁证：`Play.php?uu=https%3A%2F%2F…%2Findex.m3u8`
 * 曾被过宽匹配误判为 HLS，导致 HLS 解析器读非清单内容抛 3002（PARSING_MANIFEST_MALFORMED）。
 * 故仅当值为相对路径时判定，绝对 URL（含 `://`）不参与。
 */
object M3u8UrlShape {

    private const val M3U8_PATH_SEGMENT = "/m3u8/"

    /** 是否为 HLS 形态的地址（纯函数，JVM 可测） */
    fun matches(url: String): Boolean {
        if (url.isBlank()) return false
        val lower = url.lowercase()
        val withoutQuery = lower.substringBefore('?').substringBefore('#')
        if (withoutQuery.endsWith(".m3u8")) return true
        if (lower.contains("format=m3u8") || lower.contains("type=m3u8")) return true
        if (withoutQuery.contains(M3U8_PATH_SEGMENT)) return true
        return queryHasRelativeM3u8(lower)
    }

    private fun queryHasRelativeM3u8(lowerUrl: String): Boolean {
        val query = lowerUrl.substringAfter('?', "")
        if (query.isEmpty()) return false
        return query.split('&').any { pair ->
            val raw = pair.substringAfter('=', "")
            if (raw.isEmpty()) return false
            val value = runCatching { URLDecoder.decode(raw, "UTF-8") }.getOrDefault(raw)
            // 绝对 URL 交给内容预检判定（避免历史 3002 误判）
            value.endsWith(".m3u8") && !value.contains("://")
        }
    }

    /**
     * HLS 请求头兜底：**AES-128 加密清单**的 `#EXT-X-KEY` 请求常要求 `Referer`（真机铁证：
     * 同一 key URL 无 Referer 时 `URLError`，带 `Referer=<清单 URL>` 返回 200/16 字节；
     * 分片本身不需要 Referer）。
     *
     * 规则：
     * - 已有 `Referer`（大小写不敏感）⇒ 原样返回，绝不覆盖书源显式配置
     * - 非 HLS 形态 URL ⇒ 原样返回（避免给 mp4 直链塞 Referer）
     * - 其余 ⇒ 追加 `Referer = 清单 URL`（同源兜底，成功率高且不触发跨站校验）
     *
     * 纯函数，供 `ExoPlayerHelper` 与单测共用。
     */
    fun headersWithHlsReferer(headers: Map<String, String>, url: String): Map<String, String> {
        if (!matches(url)) return headers
        if (headers.keys.any { it.equals("Referer", ignoreCase = true) }) return headers
        val merged = LinkedHashMap(headers)
        merged["Referer"] = url
        return merged
    }
}
