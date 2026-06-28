package io.legado.app.utils

// 源码参照: app/src/main/java/io/legado/app/utils/LogUtils.kt#L140-L144
// 简化说明: stackTraceStr 已在 ThrowableExtensions.kt 中定义，此处仅保留 asIOException 和 printOnDebug | 已知上限: 无 | 升级路径: 接入日志框架

import java.io.IOException

fun Throwable.asIOException(): IOException {
    val newException = IOException(this.message)
    newException.initCause(this)
    return newException
}

fun Throwable.printOnDebug() {
    // 简化说明：printOnDebug 替换为 printStackTrace，移除 BuildConfig.DEBUG 判断 | 已知上限: 无 | 升级路径: 接入日志框架
    printStackTrace()
}
