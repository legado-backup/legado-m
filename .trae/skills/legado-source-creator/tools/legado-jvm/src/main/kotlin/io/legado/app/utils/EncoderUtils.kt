package io.legado.app.utils

import java.util.Base64

/**
 * 编码工具 escape base64
 * 简化说明：android.util.Base64 替换为 java.util.Base64 | 已知上限：URL_SAFE flag 处理简化 | 升级路径：无
 */
@Suppress("unused")
object EncoderUtils {

    fun escape(src: String): String {
        val tmp = StringBuilder()
        for (char in src) {
            val charCode = char.code
            if (charCode in 48..57 || charCode in 65..90 || charCode in 97..122) {
                tmp.append(char)
                continue
            }

            val prefix = when {
                charCode < 16 -> "%0"
                charCode < 256 -> "%"
                else -> "%u"
            }
            tmp.append(prefix).append(charCode.toString(16))
        }
        return tmp.toString()
    }

    // 简化说明：android.util.Base64 flags 映射：URL_SAFE(8)→urlDecoder, 其他→basicDecoder | 已知上限：CRLF 等 flag 未处理 | 升级路径：无
    @JvmOverloads
    fun base64Decode(str: String, flags: Int = 0): String {
        val bytes = if (flags and 8 != 0) {
            Base64.getUrlDecoder().decode(str)
        } else {
            Base64.getDecoder().decode(str)
        }
        return String(bytes)
    }

    // 简化说明：android.util.Base64 flags 映射：URL_SAFE(8)→urlEncoder, NO_WRAP(2)→无换行(默认) | 已知上限：CRLF 等 flag 未处理 | 升级路径：无
    @JvmOverloads
    fun base64Encode(str: String, flags: Int = 2): String? {
        return if (flags and 8 != 0) {
            Base64.getUrlEncoder().encodeToString(str.toByteArray())
        } else {
            Base64.getEncoder().encodeToString(str.toByteArray())
        }
    }

    @JvmOverloads
    fun base64Encode(bytes: ByteArray, flags: Int = 2): String {
        return if (flags and 8 != 0) {
            Base64.getUrlEncoder().encodeToString(bytes)
        } else {
            Base64.getEncoder().encodeToString(bytes)
        }
    }

    @JvmOverloads
    fun base64DecodeToByteArray(str: String, flags: Int = 0): ByteArray {
        return if (flags and 8 != 0) {
            Base64.getUrlDecoder().decode(str)
        } else {
            Base64.getDecoder().decode(str)
        }
    }

}
