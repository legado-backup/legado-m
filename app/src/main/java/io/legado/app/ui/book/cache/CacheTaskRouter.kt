package io.legado.app.ui.book.cache

import android.content.Context
import io.legado.app.data.entities.Book
import io.legado.app.help.book.isVideo
import io.legado.app.model.CacheBook
import io.legado.app.service.kernel.VideoCacheKernel

/**
 * 离线缓存页「开始 / 停止」的动作路由（单源，供图标真值与点击动作共用）。
 *
 * 背景：视频书缓存由独立前台服务（[VideoCacheKernel]）承担，**不进入** [CacheBook] 任务表；
 * 若沿用 CacheBook 判定/启动，会出现两类真机症状：
 * 1) 统计显示 0（已缓存文件按文本口径比对）；
 * 2) 点 ▶ 调 `CacheBook.start`（文本管线）对视频书等于没反应，且图标恒为三角 ⇒「缓存不了」。
 */
internal object CacheTaskRouter {

    /** 该书籍当前是否正在缓存（图标语义 = 点击语义的真实来源） */
    fun isRunning(book: Book): Boolean {
        if (book.isVideo) return VideoCacheKernel.progressOf(book.bookUrl).running
        return isCacheRunning(CacheBook.cacheBookMap[book.bookUrl]?.isStop())
    }

    /** 开始缓存：视频书 → 视频缓存服务；文本/音频 → CacheBook 任务 */
    fun start(context: Context, book: Book, from: Int) {
        if (book.isVideo) {
            VideoCacheKernel.start(context, book.bookUrl, from)
            return
        }
        CacheBook.start(context, book, from, book.lastChapterIndex)
    }

    /** 停止缓存：与 [start] 同源分支，避免「视频任务用文本停止接口」空转 */
    fun stop(context: Context, book: Book) {
        if (book.isVideo) {
            VideoCacheKernel.stop(context, book.bookUrl)
            return
        }
        CacheBook.remove(context, book.bookUrl)
    }
}
