package io.legado.app.help.source

import io.legado.app.exception.NoStackTraceException
import io.legado.app.model.jsSource.JsSourceUpsert
import java.io.InputStream
import java.io.PushbackInputStream

/**
 * 书源导入的「脚本 / JSON」分流。
 *
 * 与 NG 上游 `BookSourceImportReader` 同一判定口径：**首个有效字符**是 `[` 或 `{` 视为 JSON，
 * 否则视为单文件 JS 书源脚本。拒绝把整份文件先读成字符串（JSON 合集可能数十 MB）。
 */
object BookSourceScriptImport {

    private const val MAX_BYTES = JsSourceUpsert.MAX_SOURCE_BYTES

    /** 嗅探回退上限：BOM + 前导空白，超过即按 JSON 交给增量解析（其本身容忍前导空白）。 */
    const val SNIFF_BYTES = 64

    /** 文本形态（粘贴/剪贴板）判定：忽略空白与 BOM 后的首字符不是 `[` / `{` 即为脚本。 */
    fun isScriptText(text: String): Boolean {
        val first = text.firstOrNull { !it.isWhitespace() && it != '\uFEFF' } ?: return false
        return first != '[' && first != '{'
    }

    /**
     * 流形态判定：只回退已读取的嗅探字节，不消耗后续内容。
     * 调用方随后仍可把同一流交给 JSON 增量解析或 [readScript]。
     */
    fun isScriptStream(input: PushbackInputStream): Boolean {
        val sniffed = ArrayList<Byte>(8)
        var current = input.read()
        // 跳过 UTF-8 BOM(EF BB BF) 与空白
        while (current != -1) {
            sniffed.add(current.toByte())
            if (sniffed.size >= SNIFF_BYTES) break
            if (current == 0xEF || current == 0xBB || current == 0xBF) {
                current = input.read()
                continue
            }
            if (current.toChar().isWhitespace()) {
                current = input.read()
                continue
            }
            break
        }
        // 回退顺序必须与读取顺序相反（unread 是插入到回退缓冲区头部）
        for (index in sniffed.indices.reversed()) {
            input.unread(sniffed[index].toInt())
        }
        if (current == -1) throw NoStackTraceException("书源内容为空")
        if (sniffed.size >= SNIFF_BYTES) return false
        return current.toChar() != '[' && current.toChar() != '{'
    }

    /** 读取脚本正文：超过 1 MiB 立即失败（与 [JsSourceUpsert.MAX_SOURCE_BYTES] 同口径）。 */
    fun readScript(input: InputStream): String {
        val reader = input.reader(Charsets.UTF_8)
        val text = StringBuilder()
        val buffer = CharArray(8192)
        while (true) {
            val count = reader.read(buffer)
            if (count == -1) break
            text.appendRange(buffer, 0, count)
            if (text.length > MAX_BYTES) throw NoStackTraceException("JS 书源不能超过 1 MiB")
        }
        val script = text.toString().trim().removePrefix("\uFEFF").trim()
        if (script.isEmpty()) throw NoStackTraceException("JS 书源内容为空")
        return script
    }
}
