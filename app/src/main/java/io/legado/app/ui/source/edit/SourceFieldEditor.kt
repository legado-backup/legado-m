package io.legado.app.ui.source.edit

import android.content.Context
import android.content.Intent
import io.legado.app.ui.code.CodeEditActivity
import io.legado.app.ui.code.CodeEditSessionStore
import kotlinx.coroutines.Dispatchers.IO
import kotlinx.coroutines.withContext

/**
 * 非 JS 书源/订阅源编辑页「全屏编辑」的载荷通道（2026-10-27 用户反馈）。
 *
 * 根因：原实现用 `Intent.putExtra("text", currentText)` 双向传正文，大字段会撞 Binder
 * 1MB 事务上限（`TransactionTooLargeException` / 进程被杀），且返回回填依赖瞬时焦点。
 *
 * 方案：复用 JS 书源编排页的 [CodeEditSessionStore] 会话通道——
 * - 打开：正文落到应用私有 cache，Intent 只传会话 id；
 * - 返回：读会话全文，读成功后删除；
 * - 兼容旧 `"text"` 回传（其他调用方零影响）。
 */
object SourceFieldEditor {

    /**
     * 创建编辑器 Intent（IO 线程写会话）。
     *
     * @return 会话创建失败时返回 null（调用方决定小字段内联兜底或提示）
     */
    suspend fun open(
        context: Context,
        text: String,
        title: String?,
        cursorPosition: Int,
    ): Intent? = withContext(IO) {
        val sessionId = runCatching { CodeEditSessionStore.app.create(text) }.getOrNull() ?: return@withContext null
        Intent(context, CodeEditActivity::class.java).apply {
            putExtra(CodeEditSessionStore.ExtraSessionId, sessionId)
            putExtra("title", title.orEmpty())
            putExtra("cursorPosition", cursorPosition)
        }
    }

    /**
     * 读取编辑器返回正文（IO 线程）。
     *
     * - 会话通道：读成功 ⇒ 删除会话；读失败 ⇒ **保留**会话（交 `cleanupStale()` 兜底，不丢用户改动）；
     * - 旧内联通道：直接返回 `"text"`。
     */
    suspend fun readResult(data: Intent?): String? {
        val sessionId = data?.getStringExtra(CodeEditSessionStore.ExtraSessionId)
        if (sessionId != null) {
            val text = withContext(IO) {
                runCatching { CodeEditSessionStore.app.read(sessionId) }.getOrNull()
            }
            if (text != null) {
                withContext(IO) { runCatching { CodeEditSessionStore.app.delete(sessionId) } }
            }
            return text
        }
        return data?.getStringExtra("text")
    }

    /** 用户放弃编辑：删除会话（若存在）。 */
    fun discard(data: Intent?) {
        val sessionId = data?.getStringExtra(CodeEditSessionStore.ExtraSessionId) ?: return
        runCatching { CodeEditSessionStore.app.delete(sessionId) }
    }

    /** 页面打开时清理进程被杀遗留的过期会话。 */
    fun cleanupStale() {
        runCatching { CodeEditSessionStore.app.cleanupStale() }
    }
}
