package io.legado.app.help.readaloud

import io.legado.app.constant.AppLog
import java.io.File

/**
 * R17：TTS 混合缓存（`cacheDir/httpTTS`）清扫单一来源。
 *
 * 抽自 `HttpReadAloudService.removeCacheFile`，供两处复用：
 * - 播放中换章清理（保留当前章）；
 * - **App 启动兜底清扫**（保留各书持久化进度所在章 + 预合成保留名单）。
 *
 * 判据（与既有实现逐条对齐）：
 * 1. 保留名单（预合成产物）任何情况不删；
 * 2. `*.part` 半成品仅在陈旧（超 [TTL_MS]）时删（活跃写入中的 lastModified 会持续更新）；
 * 3. 2160 字节的「静音缓存」直接删（合成失败留下的固定长度产物）；
 * 4. 其余文件：命中保留集（当前章标题 md5 前缀）时保留，否则陈旧即删。
 */
object TtsCacheSweep {

    /** 陈旧阈值：10 分钟未触达即可驱逐（与既有实现一致） */
    const val TTL_MS = 600_000L

    /** 合成失败留下的固定长度静音产物长度 */
    const val SILENT_SOUND_LENGTH = 2160L

    /**
     * 单文件判据（纯函数，可 JVM 单测）。
     *
     * @param keepStems 需保留的文件名前缀集合（一般为章节标题的 md5），空集表示不额外保留
     * @param reserved 预合成保留名单（键为不含 `.mp3` 的文件名）
     */
    fun shouldDelete(
        name: String,
        length: Long,
        lastModified: Long,
        now: Long,
        keepStems: Set<String>,
        reserved: Set<String>
    ): Boolean {
        val stem = name.removeSuffix(".mp3")
        if (stem in reserved) return false
        val stale = now - lastModified > TTL_MS
        if (name.endsWith(".part")) return stale
        if (length == SILENT_SOUND_LENGTH) return true
        if (keepStems.any { name.startsWith(it) }) return false
        return stale
    }

    /**
     * 执行清扫。
     *
     * @return 实际删除的文件数（用于诊断日志）
     */
    fun sweep(
        cacheDir: File,
        keepStems: Set<String>,
        reserved: Set<String>,
        now: Long = System.currentTimeMillis()
    ): Int {
        if (!cacheDir.isDirectory) return 0
        var deleted = 0
        cacheDir.listFiles()?.forEach { file ->
            kotlin.runCatching {
                if (shouldDelete(file.name, file.length(), file.lastModified(), now, keepStems, reserved)) {
                    if (file.delete()) deleted++
                } else if (file.name.removeSuffix(".mp3") in reserved) {
                    // TtsTrace 真机联调：保留名单驱逐防护证据（与既有 removeCacheFile 日志同口径）
                    AppLog.putDebugWithTag(
                        AppLog.TAG_TTS_TRACE,
                        "保留名单防护 file=${file.name.takeLast(20)} 跳过清理",
                        level = AppLog.Level.INFO
                    )
                }
            }
        }
        return deleted
    }
}
