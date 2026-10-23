package io.legado.app.ui.code

import io.legado.app.constant.AppLog
import splitties.init.appCtx
import java.io.File
import java.io.IOException
import java.util.UUID

/**
 * 代码编辑器的**会话载荷存储**（2026-10-23 JS 书源编排链路引入）。
 *
 * ### 为什么需要
 * 入方向的 [CodeEditPayloadStore] / [CodeEditPayloadPolicy] 只解决「初始文本」不经 Binder；
 * 但 JS 书源编辑是**多段往返**（编辑器 → 编排页 → 调试页/登录页 → 再回编辑器），
 * 每段都要带走整段脚本。若沿用一个临时文件路径，编排页必须自己管理生命周期与清理；
 * 用**会话 id** 则把「文件在哪、怎么原子替换、何时删」收敛到本类一处。
 *
 * ### 语义
 * - 会话 id 是**唯一**跨 Binder 的值（正文只落在应用私有 cache 目录）；
 * - 写走 `.new` → rename 的原子替换，避免半截文件被读到；
 * - [delete] 由编排页在流程结束时调用；进程被杀导致的残留由 [cleanupStale] 兜底。
 */
class CodeEditSessionStore(
    private val directory: File,
) {

    companion object {
        /** Intent extra：会话 id（**进出双向同键**，语义只有一个——"载荷在这个会话里"）。 */
        const val ExtraSessionId = "textSessionId"

        /** 陈旧会话保留时长（进程被杀留下的残留，超过即清理）。 */
        const val StaleMillis = 24L * 60 * 60 * 1000

        val app: CodeEditSessionStore by lazy {
            CodeEditSessionStore(File(appCtx.cacheDir, "code_edit_sessions"))
        }

        private val sessionIdPattern = Regex(
            "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
        )
    }

    @Synchronized
    fun create(text: String): String {
        val sessionId = UUID.randomUUID().toString()
        write(sessionId, text)
        return sessionId
    }

    @Synchronized
    fun read(sessionId: String): String? {
        val file = sessionFile(sessionId)
        val backup = backupFile(sessionId)
        // 上一次写中断（rename 前进程被杀）⇒ 备份即完整内容
        if (!file.exists() && backup.exists()) {
            backup.renameTo(file)
        }
        return file.takeIf(File::isFile)?.readText(Charsets.UTF_8)
    }

    @Synchronized
    fun write(sessionId: String, text: String) {
        ensureDirectory()
        val file = sessionFile(sessionId)
        val pending = pendingFile(sessionId)
        val backup = backupFile(sessionId)
        pending.delete()
        pending.writeText(text, Charsets.UTF_8)

        if (file.exists()) {
            backup.delete()
            if (!file.renameTo(backup)) {
                pending.delete()
                throw IOException("无法备份代码编辑会话")
            }
        }

        if (!pending.renameTo(file)) {
            backup.renameTo(file)
            pending.delete()
            throw IOException("无法更新代码编辑会话")
        }
        backup.delete()
    }

    @Synchronized
    fun delete(sessionId: String) {
        sessionFile(sessionId).delete()
        pendingFile(sessionId).delete()
        backupFile(sessionId).delete()
        directory.delete()
    }

    /**
     * 清理超过 [maxAgeMillis] 的残留会话文件（进程被杀导致 [delete] 未执行）。
     * 只记数量不记文件名（会话 id 无业务含义，但仍保持日志脱敏口径）。
     */
    @Synchronized
    fun cleanupStale(maxAgeMillis: Long = StaleMillis, now: Long = System.currentTimeMillis()) {
        val files = directory.listFiles() ?: return
        var removed = 0
        files.forEach { file ->
            if (now - file.lastModified() > maxAgeMillis && file.delete()) {
                removed++
            }
        }
        if (removed > 0) {
            AppLog.putDebug("代码编辑会话清理：过期文件 $removed 个")
        }
    }

    private fun ensureDirectory() {
        if (!directory.exists() && !directory.mkdirs()) {
            throw IOException("无法创建代码编辑会话目录")
        }
        if (!directory.isDirectory) {
            throw IOException("代码编辑会话目录不可用")
        }
    }

    private fun sessionFile(sessionId: String): File {
        require(sessionIdPattern.matches(sessionId)) { "无效的代码编辑会话" }
        return File(directory, "$sessionId.txt")
    }

    private fun pendingFile(sessionId: String): File {
        require(sessionIdPattern.matches(sessionId)) { "无效的代码编辑会话" }
        return File(directory, "$sessionId.new")
    }

    private fun backupFile(sessionId: String): File {
        require(sessionIdPattern.matches(sessionId)) { "无效的代码编辑会话" }
        return File(directory, "$sessionId.bak")
    }
}
