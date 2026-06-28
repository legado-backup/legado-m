package io.legado.app.constant

import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

// 源码参照: app/src/main/java/io/legado/app/constant/AppConst.kt
// 简化说明: 仅保留 AnalyzeUrl 需要的 UA_NAME 常量和 dateFormat | 已知上限: 无 | 升级路径: 无
// 修复说明: 新增 dateFormat，读取 LEGADO_DATE_FORMAT 环境变量，默认 "yyyy/MM/dd HH:mm"，与真机 AppConst.dateFormat 行为一致；用 ThreadLocal 包装 SimpleDateFormat 保证线程安全（真机用 FastDateFormat 天然线程安全）

object AppConst {
    const val UA_NAME = "User-Agent"

    /**
     * 日期格式化器（与真机 AppConst.dateFormat 行为一致）
     * 真机使用 FastDateFormat（线程安全），仿真端用 ThreadLocal<SimpleDateFormat> 保证线程安全
     * 格式可通过 LEGADO_DATE_FORMAT 环境变量覆盖，默认 "yyyy/MM/dd HH:mm"
     */
    val dateFormat: DateFormatWrapper = DateFormatWrapper(
        System.getenv("LEGADO_DATE_FORMAT") ?: "yyyy/MM/dd HH:mm"
    )
}

/**
 * SimpleDateFormat 线程安全包装器，模拟 FastDateFormat 的 format(Date) API
 * 简化说明: 用 ThreadLocal 保证线程安全 | 已知上限: 不支持 parse | 升级路径: 引入 commons-lang3 FastDateFormat
 */
class DateFormatWrapper(private val pattern: String) {
    private val threadLocal = ThreadLocal.withInitial {
        SimpleDateFormat(pattern, Locale.getDefault())
    }

    fun format(date: Date): String = threadLocal.get().format(date)
}
