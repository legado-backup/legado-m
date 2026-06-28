package io.legado.app.model

import java.io.File
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

// 源码参照: app/src/main/java/io/legado/app/model/Debug.kt
// 简化说明: Debug 降级为 println + 日志文件 | 已知上限: 无 UI 日志展示 | 升级路径: 接入日志框架
// 修复说明: 1) 新增 log(sourceUrl, msg) 重载，与真机 Debug.log 签名一致；2) 新增 Callback 接口，支持外部订阅日志；3) 新增日志文件写入功能（LEGADO_DEBUG_LOG 环境变量指定路径，默认临时目录）

object Debug {
    interface Callback {
        fun printLog(state: Int, msg: String)
    }

    @Volatile
    var callback: Callback? = null

    @Volatile
    var debugSource: String? = null

    // 简化说明：使用临时目录替代 appCtx.externalCache | 已知上限：重启后文件丢失 | 升级路径：配置持久化目录
    private val logFile: File? by lazy {
        val path = System.getenv("LEGADO_DEBUG_LOG")
        if (path.isNullOrBlank()) {
            File(System.getProperty("java.io.tmpdir"), "legado-jvm-debug.log")
        } else {
            File(path)
        }.apply { parentFile?.mkdirs() }
    }

    @Suppress("SimpleDateFormat")
    private val timeFormat = SimpleDateFormat("[HH:mm:ss.SSS]", Locale.getDefault())

    /**
     * 带来源 URL 的日志（与真机 Debug.log(sourceUrl, msg) 签名一致）
     * 真机会根据 debugSource 过滤、显示时间、回调 UI；仿真端简化为：回调 Callback + 写入日志文件 + println
     */
    @Synchronized
    fun log(sourceUrl: String?, msg: String, print: Boolean = true, state: Int = 1) {
        val time = timeFormat.format(Date())
        val printMsg = "$time $msg"
        // 回调外部订阅者（如 RuleEngineServer 推送到客户端）
        callback?.printLog(state, printMsg)
        // 写入日志文件
        kotlin.runCatching {
            logFile?.appendText("$printMsg\n")
        }
        // 控制台输出
        println("[Debug] $printMsg")
    }

    /**
     * 不带来源 URL 的日志（与真机 Debug.log(msg) 签名一致）
     * 真机委托 log(debugSource, msg)；仿真端委托 log(null, msg)
     */
    @Synchronized
    fun log(msg: String?) {
        log(debugSource, msg ?: "", true)
    }
}
