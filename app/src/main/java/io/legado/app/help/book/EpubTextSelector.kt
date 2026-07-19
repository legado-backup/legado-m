package io.legado.app.help.book

import android.widget.TextView
import io.legado.app.constant.AppLog

/**
 * EPUB 文本选择器（EPUB-E-06）。
 *
 * 借鉴 Archive `EpubTextSelector`：提供 EPUB 文本选择交互能力，
 * 封装选择文本提取、上下文提取、HTML 标签清理等逻辑。
 *
 * 设计要点：
 * - 选择文本提取：从 TextView 获取当前选中文本
 * - 上下文提取：提取选择文本周围的文字（用于翻译、查字典）
 * - HTML 标签清理：EPUB 内容可能含 HTML 标签（如 em/strong），选择时自动清理
 * - 回调接口：通过 [Callback] 通知调用方处理查字典、翻译、复制、分享
 *
 * 使用方式：调用方在 ActionMode 回调中调用 [handleTextSelection]，
 * 由本类负责提取文本和上下文，然后通过 [Callback] 通知调用方处理。
 *
 * 关联任务：EPUB-E-06（P1）文本选择器。
 */
class EpubTextSelector(private val textView: TextView) {

    /**
     * 文本选择回调接口。
     */
    interface Callback {
        /**
         * 用户选择文本时触发。
         *
         * @param selectedText 选中的文本（已清理 HTML 标签）
         * @param contextText 上下文文本（选择文本前后各 N 个字符，已清理 HTML 标签）
         */
        fun onTextSelected(selectedText: String, contextText: String)
    }

    private var callback: Callback? = null

    /**
     * 设置回调。
     */
    fun setCallback(callback: Callback) {
        this.callback = callback
    }

    /**
     * 处理文本选择事件。
     *
     * 由调用方在 ActionMode 回调中调用此方法，提取选择文本和上下文，
     * 然后通过 [Callback] 通知调用方。
     */
    fun handleTextSelection() {
        val selectedText = getSelectedText() ?: return
        if (selectedText.isBlank()) return
        val contextText = extractContext()
        callback?.onTextSelected(selectedText, contextText)
    }

    /**
     * 获取当前选中的文本（自动清理 HTML 标签）。
     *
     * @return 选中的文本，失败或无选择返回 null
     */
    fun getSelectedText(): String? {
        return runCatching {
            val start = textView.selectionStart
            val end = textView.selectionEnd
            if (start < 0 || end < 0 || start == end) null
            else {
                val raw = textView.text.substring(start, end).toString()
                cleanHtmlTags(raw)
            }
        }.onFailure {
            AppLog.put("EpubTextSelector.getSelectedText failed", it)
        }.getOrNull()
    }

    /**
     * 提取选择文本的上下文。
     *
     * @param contextLength 上下文长度（前后各 contextLength 个字符），默认 50
     * @return 上下文文本（已清理 HTML 标签）
     */
    fun extractContext(contextLength: Int = 50): String {
        return runCatching {
            val start = textView.selectionStart
            val end = textView.selectionEnd
            if (start < 0 || end < 0) return ""
            val text = textView.text
            val ctxStart = (start - contextLength).coerceAtLeast(0)
            val ctxEnd = (end + contextLength).coerceAtMost(text.length)
            cleanHtmlTags(text.substring(ctxStart, ctxEnd).toString())
        }.getOrNull() ?: ""
    }

    /**
     * 清理 HTML 标签。
     *
     * EPUB 内容可能含 HTML 标签（如 <em>、<strong>、<span>），选择文本时需要清理，
     * 避免标签文字被传入查字典、翻译等后续处理。
     *
     * @param text 原始文本
     * @return 清理后的纯文本
     */
    private fun cleanHtmlTags(text: String): String {
        return text.replace(Regex("<[^>]+>"), "").trim()
    }
}
