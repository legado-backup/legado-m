package io.legado.app.exception

// 源码参照: app/src/main/java/io/legado/app/exception/NoStackTraceException.kt
// 简化说明: 纯 JVM 实现，覆写 fillInStackTrace 返回 this 以避免堆栈采集开销 | 已知上限: 无 | 升级路径: 无

/**
 * 不记录错误堆栈的报错
 */
open class NoStackTraceException(msg: String) : Exception(msg) {

    override fun fillInStackTrace(): Throwable {
        stackTrace = emptyStackTrace
        return this
    }

    companion object {
        private val emptyStackTrace = emptyArray<StackTraceElement>()
    }

}
