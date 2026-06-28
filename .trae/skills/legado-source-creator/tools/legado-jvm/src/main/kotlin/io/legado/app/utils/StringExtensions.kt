package io.legado.app.utils

import io.legado.app.constant.AppPattern
import java.net.InetAddress

// 简化说明：从源码 StringExtensions.kt 抽取 splitNotBlank/isDataUrl/isJson/isJsonObject/isJsonArray/isXml/parseIpsFromString，纯 JVM 实现 | 已知上限：无 | 升级路径：无

fun String.splitNotBlank(vararg delimiter: String, limit: Int = 0): Array<String> = run {
    this.split(*delimiter, limit = limit).map { it.trim() }.filterNot { it.isBlank() }
        .toTypedArray()
}

fun String.splitNotBlank(regex: Regex, limit: Int = 0): Array<String> = run {
    this.split(regex, limit).map { it.trim() }.filterNot { it.isBlank() }.toTypedArray()
}

// 源码参照: app/src/main/java/io/legado/app/utils/StringExtensions.kt#L43-L56
fun String?.isDataUrl() =
    this?.let {
        AppPattern.dataUriRegex.matches(it)
    } ?: false

fun String?.isJson(): Boolean =
    this?.run {
        val str = this.trim()
        when {
            str.startsWith("{") && str.endsWith("}") -> true
            str.startsWith("[") && str.endsWith("]") -> true
            else -> false
        }
    } ?: false

fun String?.isJsonObject(): Boolean =
    this?.run {
        val str = this.trim()
        str.startsWith("{") && str.endsWith("}")
    } ?: false

fun String?.isJsonArray(): Boolean =
    this?.run {
        val str = this.trim()
        str.startsWith("[") && str.endsWith("]")
    } ?: false

fun String?.isXml(): Boolean =
    this?.run {
        val str = this.trim()
        str.startsWith("<") && str.endsWith(">")
    } ?: false

// 源码参照: app/src/main/java/io/legado/app/utils/StringExtensions.kt#L153-L165
fun String.parseIpsFromString(): List<InetAddress>? =
    split(",")
        .map { it.trim() }
        .filter { it.isNotEmpty() }
        .mapNotNull { ip ->
            kotlin.runCatching { InetAddress.getByName(ip) }.getOrNull()
        }
        .takeIf { it.isNotEmpty() }
