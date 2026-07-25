package io.legado.app.utils

// 源码参照: app/src/main/java/io/legado/app/utils/ThrowableExtensions.kt#L5-L16

val Throwable.stackTraceStr: String
    get() {
        val stackTrace = stackTraceToString()
        val lMsg = this.localizedMessage ?: "noErrorMsg"
        return when {
            stackTrace.isNotEmpty() -> stackTrace
            else -> lMsg
        }
    }
