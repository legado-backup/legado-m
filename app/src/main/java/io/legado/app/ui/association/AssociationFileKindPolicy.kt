package io.legado.app.ui.association

import io.legado.app.constant.AppPattern

/**
 * 外部文件类型判据（external-json-open-import-fix / spec R1~R4）。
 *
 * **为什么需要**：原 [FileAssociationViewModel] 判断「外部打开的是不是 JSON」只靠
 * `InputStream.isJson()`——读 128 字节 + `skip(available() - 128)` 再读 128 字节，
 * 要求拼接串**首尾同时**为 `{}`/`[]`。QQ / 微信等跨进程 ContentProvider 的流
 * `available()` 常为 0 或发生短读，第二段取到的是**中间片段**，于是合法书源 JSON 被判成
 * 非 JSON，落入「文件不受支持 → 当作书籍导入 → Unexpected empty File」。
 *
 * 本判据层只做**纯逻辑**（无 Android 依赖，可 JVM 断言）：
 * ①按扩展名 / MIME 定性（确定性快路径，不读内容）；
 * ②扩展名与 MIME 都未知时，由宿主读**首部字节**交给 [looksLikeJson]（不读尾部、不看 available）；
 * ③JSON 物化缓存的命名与过期规则（防目录穿越、防同毫秒覆盖）。
 */
object AssociationFileKindPolicy {

    /** 外部文件判定结果：JSON 走源导入；BOOK 走本地书籍导入；null 交由内容首部兜底。 */
    enum class Kind {
        JSON,
        BOOK
    }

    const val MIME_JSON = "application/json"

    /** 首部采样上限：只判首字符，512 字节足够容纳 BOM + 空白 + 开括号。 */
    const val HEAD_BYTES = 512

    /** JSON 物化上限（32MB）：书源/订阅源配置远超此值属异常，交由本地导入处理。 */
    const val MAX_JSON_BYTES = 32L * 1024 * 1024

    /** 缓存存活时长：1 小时（写入新缓存时顺带清理过期文件）。 */
    const val CACHE_TTL_MS = 60L * 60 * 1000

    /** 缓存文件名主体上限（不含时间戳前缀与 `.json` 后缀），防超长文件名。 */
    const val CACHE_NAME_MAX_CHARS = 64

    /**
     * 按文件名与 MIME 定性。
     *
     * 顺序不可调换：**扩展名优先**（`.json` 是确定性快路径，不读内容），其次书籍扩展名，
     * 最后才是 MIME —— 因为部分 Provider 会给书籍也报 `application/octet-stream`，
     * 而有的会给 JSON 报 `text/plain`，单看 MIME 会误伤。
     *
     * @return [Kind]；两者都没给出结论时返回 null（宿主再读首部兜底）。
     */
    fun kindOf(name: String?, mime: String?): Kind? {
        val fileName = name?.trim().orEmpty()
        if (fileName.endsWith(".json", ignoreCase = true)) return Kind.JSON
        if (fileName.isNotEmpty() && fileName.matches(AppPattern.bookFileRegex)) return Kind.BOOK
        if (mime != null && mime.equals(MIME_JSON, ignoreCase = true)) return Kind.JSON
        return null
    }

    /**
     * 首部是否形似 JSON：只要求**首个非空白字符**为 `{` 或 `[`。
     *
     * 不做「首尾配对」校验——尾部字节在流上取不到（`available()` 不可靠，`skip` 到末尾
     * 对 pipe 型流无效），要求闭合只会把合法 JSON 判成非 JSON。真正的内容合法性由
     * 后续 `importJson` 的解析回执负责。
     *
     * @param head 已读入的首部字节缓冲
     * @param len 实际读入字节数（`<= 0` 视为空文件，判 false）
     */
    fun looksLikeJson(head: ByteArray, len: Int): Boolean {
        val realLen = len.coerceAtMost(head.size)
        if (realLen <= 0) return false
        val text = String(head, 0, realLen, Charsets.UTF_8)
            .removePrefix("\uFEFF")
            .trimStart()
        return text.startsWith("{") || text.startsWith("[")
    }

    /**
     * 生成 JSON 物化缓存文件名：`<now>_<净化后的主体>.json`。
     *
     * 净化规则（防目录穿越 / 防非法字符）：`..` 先整体替换，随后只保留字母、数字与
     * 少量安全符号，其余（含 `/`、`\`、`<>:"|?*`、控制字符）一律替换为 `_`；
     * 主体截断至 [CACHE_NAME_MAX_CHARS] 字符。结果必然落在缓存目录内。
     */
    fun cacheFileName(now: Long, name: String?): String {
        val raw = name?.trim().orEmpty()
        if (raw.isEmpty()) return "import_$now.json"
        val body = if (raw.endsWith(".json", ignoreCase = true)) raw.dropLast(5) else raw
        val safe = body
            .replace("..", "_")
            .map { ch ->
                if (ch.isLetterOrDigit() || ch in SAFE_NAME_CHARS) ch else '_'
            }
            .joinToString("")
            .trim('_')
            .take(CACHE_NAME_MAX_CHARS)
            .ifEmpty { "import" }
        return "${now}_$safe.json"
    }

    /** 缓存是否过期（早于 [CACHE_TTL_MS]）。 */
    fun isCacheExpired(lastModified: Long, now: Long): Boolean =
        now - lastModified > CACHE_TTL_MS

    /** 文件名允许保留的符号（其余字符由 [cacheFileName] 替换为 `_`）。 */
    private const val SAFE_NAME_CHARS = "._- ()（）[]【】"
}
