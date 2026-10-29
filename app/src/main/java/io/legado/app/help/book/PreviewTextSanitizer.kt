package io.legado.app.help.book

/**
 * R12：换源前正文预览的文本清洗（纯函数，可 JVM 单测）。
 *
 * 预览只用于"判断源对不对"，因此要求：
 * 1. 去 HTML 标签与实体残留，避免弹窗里出现 `<img src=...>`；
 * 2. 压缩连续空白/换行（含全角空格），避免高空白把 300 字挤成 2 行有效内容；
 * 3. 截断到固定长度（不足原样返回，绝不截半个代理对）。
 */
object PreviewTextSanitizer {

    private val TAG_REGEX = Regex("<[^>]*>")
    private val WHITESPACE_REGEX = Regex("[\\s\u00A0\u3000]+")

    private val ENTITY_REPLACEMENTS = mapOf(
        "&nbsp;" to " ",
        "&amp;" to "&",
        "&lt;" to "<",
        "&gt;" to ">",
        "&quot;" to "\"",
        "&#39;" to "'",
        "&ldquo;" to "“",
        "&rdquo;" to "”",
        "&hellip;" to "…"
    )

    fun clean(html: String?): String {
        if (html.isNullOrEmpty()) return ""
        var text = TAG_REGEX.replace(html, " ")
        for ((entity, replacement) in ENTITY_REPLACEMENTS) {
            text = text.replace(entity, replacement)
        }
        return WHITESPACE_REGEX.replace(text, " ").trim()
    }

    fun snippet(html: String?, maxLength: Int = 300): String {
        val text = clean(html)
        if (maxLength <= 0) return ""
        if (text.length <= maxLength) return text
        // 防止把 emoji 等代理对切成两半（截断点落在高代理项时回退一位）
        var end = maxLength
        if (Character.isHighSurrogate(text[end - 1])) end -= 1
        return text.substring(0, end)
    }
}
