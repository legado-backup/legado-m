package io.legado.app.utils

import io.legado.app.lib.icu4j.CharsetDetector
import org.jsoup.Jsoup

/**
 * 自动获取文件的编码
 *
 * 源码参照: app/src/main/java/io/legado/app/utils/EncodingDetect.kt
 * */
@Suppress("MemberVisibilityCanBePrivate", "unused")
object EncodingDetect {

    private val headTagRegex = "(?i)<head>[\\s\\S]*?</head>".toRegex()
    private val headOpenBytes = "<head>".toByteArray()
    private val headCloseBytes = "</head>".toByteArray()

    fun getHtmlEncode(bytes: ByteArray): String {
        try {
            var head: String? = null
            val startIndex = bytes.indexOf(headOpenBytes)
            if (startIndex > -1) {
                val endIndex = bytes.indexOf(headCloseBytes, startIndex)
                if (endIndex > -1) {
                    head = String(bytes.copyOfRange(startIndex, endIndex + headCloseBytes.size))
                }
            }
            val doc = Jsoup.parseBodyFragment(head ?: headTagRegex.find(String(bytes))!!.value)
            val metaTags = doc.getElementsByTag("meta")
            var charsetStr: String
            for (metaTag in metaTags) {
                charsetStr = metaTag.attr("charset")
                if (charsetStr.isNotEmpty()) {
                    return charsetStr
                }
                val httpEquiv = metaTag.attr("http-equiv")
                if (httpEquiv.equals("content-type", true)) {
                    val content = metaTag.attr("content")
                    val idx = content.indexOf("charset=", ignoreCase = true)
                    charsetStr = if (idx > -1) {
                        content.substring(idx + "charset=".length)
                    } else {
                        content.substringAfter(";")
                    }
                    if (charsetStr.isNotEmpty()) {
                        return charsetStr
                    }
                }
            }
        } catch (ignored: Exception) {
        }
        return getEncode(bytes)
    }

    /**
     * 得到字节流的编码
     */
    fun getEncode(bytes: ByteArray): String {
        val match = CharsetDetector().setText(bytes).detect()
        return match?.name ?: "UTF-8"
    }

    /**
     * 得到文件的编码
     */
    fun getEncode(filePath: String): String {
        return getEncode(java.io.File(filePath))
    }

    /**
     * 得到文件的编码
     */
    fun getEncode(file: java.io.File): String {
        val tempByte = getFileBytes(file)
        if (tempByte.isEmpty()) {
            return "UTF-8"
        }
        return getEncode(tempByte)
    }

    private fun getFileBytes(file: java.io.File): ByteArray {
        val byteArray = ByteArray(8000)
        var pos = 0
        try {
            file.inputStream().buffered().use {
                while (pos < byteArray.size) {
                    val n = it.read(byteArray, pos, 1)
                    if (n == -1) {
                        break
                    }
                    if (byteArray[pos] < 0) {
                        pos++
                    }
                }
            }
        } catch (e: Exception) {
            System.err.println("Error: $e")
        }
        return byteArray.copyOf(pos)
    }

    private fun ByteArray.indexOf(sub: ByteArray, fromIndex: Int = 0): Int {
        if (sub.isEmpty()) return 0
        if (fromIndex >= size) return -1
        val first = sub[0]
        for (i in fromIndex..size - sub.size) {
            if (this[i] == first) {
                var found = true
                for (j in 1 until sub.size) {
                    if (this[i + j] != sub[j]) {
                        found = false
                        break
                    }
                }
                if (found) return i
            }
        }
        return -1
    }
}
