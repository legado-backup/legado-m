package io.legado.app.help.readaloud

/**
 * R15：冷启动「首点朗读被吞」的待播状态机（抽出以便单测锁定语义）。
 *
 * 场景：TTS 服务初始化成功即 `play()`，但此时正文尚未排版（`ReadBook.curTextChapter == null`），
 * 原 `readAloud()` 直接静默返回 ⇒ 用户首点朗读无任何反应。
 *
 * 契约：
 * - [markPending]：用户发起朗读但正文未就绪时置位；
 * - [consumeIfPending]：章节排版完成回调时调用；**先清标记再返回 true**（防同一回调重入导致双播），
 *   正文仍为空时**保留标记**（等下一次排版完成再补播）；
 * - [cancel]：切书/章节槽整体清空时作废标记。
 */
class ReadAloudPendingState {

    @Volatile
    private var pending = false

    val isPending: Boolean
        get() = pending

    @Synchronized
    fun markPending() {
        pending = true
    }

    /**
     * @param chapterReady 当前章是否已排版完成（`ReadBook.curTextChapter != null`）
     * @return true 表示本次需要补播一次朗读
     */
    @Synchronized
    fun consumeIfPending(chapterReady: Boolean): Boolean {
        if (!pending || !chapterReady) return false
        pending = false
        return true
    }

    @Synchronized
    fun cancel() {
        pending = false
    }
}
