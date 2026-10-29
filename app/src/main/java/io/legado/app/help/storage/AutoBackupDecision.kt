package io.legado.app.help.storage

import java.util.concurrent.TimeUnit

/**
 * R16：自动备份的跨设备判据（纯函数，可 JVM 单测）。
 *
 * 背景：备份文件名包含「本机名 + 日期」（`Backup.getNowZipFileName`），多设备每天各传一份，
 * 云端会堆积 N 份同日期的不同设备备份 ⇒ 改为只认云端最近备份的 `lastModify`：
 * 距上次云端备份不足 [INTERVAL_MS] 则跳过本次自动备份。
 *
 * 边界：`lastModify <= 0`（未配置 WebDAV / 查询失败 / 文件无时间戳）一律**不跳过**，
 * 回退到原有的精确文件名判据（宁可多备份，也不因查询失败长期不备份）。
 */
object AutoBackupDecision {

    /** 自动备份间隔：24 小时 */
    val INTERVAL_MS: Long = TimeUnit.DAYS.toMillis(1)

    fun shouldSkipByCloudLastModify(lastModifyMs: Long, nowMs: Long): Boolean =
        lastModifyMs > 0 && nowMs - lastModifyMs < INTERVAL_MS

    /**
     * 回写本地时间戳：禁止把「未来时间」写进 `LocalConfig.lastBackup`
     * （设备时间漂移会让 `shouldBackup()` 长期判定为「刚备份过」）。
     */
    fun normalizeLastBackupTime(cloudLastModifyMs: Long, nowMs: Long): Long =
        minOf(cloudLastModifyMs, nowMs)
}
