package io.legado.app.utils

// 源码参照: app/src/main/java/io/legado/app/utils/MapExtensions.kt
// 简化说明: 纯 JVM 实现，与源码逻辑一致 | 已知上限: 无 | 升级路径: 无

fun HashMap<String, *>.has(key: String, ignoreCase: Boolean = false): Boolean {
    for (item in this) {
        if (key.equals(item.key, ignoreCase)) {
            return true
        }
    }
    return false
}

fun <T> HashMap<String, T>.get(key: String, ignoreCase: Boolean = false): T? {
    for (item in this) {
        if (key.equals(item.key, ignoreCase)) {
            return item.value
        }
    }
    return null
}

inline fun <K, V> MutableMap<K, V>.getOrPutLimit(key: K, maxSize: Int, defaultValue: () -> V): V {
    var value = get(key)
    if (containsKey(key)) {
        @Suppress("UNCHECKED_CAST")
        return value as V
    }
    value = defaultValue()
    if (size < maxSize) {
        put(key, value)
    }
    return value
}
