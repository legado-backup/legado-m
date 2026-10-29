package io.legado.app.help.book

import io.legado.app.data.entities.Book

/**
 * R11：换源回滚的进程级单槽快照（AD-16：不做 Room 持久化）。
 *
 * 换源成功后旧书会被 `delete()` 且新书入库，原 `bookUrl/origin/tocUrl` 全部丢失；
 * 这里保存**换源前**的完整 `Book` 副本，供"回滚上一书源"一次性使用。
 *
 * 存副本（[Book.copy]）而非引用：换源流程会改写原对象字段（migrateTo 迁移进度）。
 */
object SourceSwitchHistory {

    @Volatile
    var last: Book? = null
        private set

    /** 记录换源前快照（null 忽略；同一本换源不覆盖自身） */
    @Synchronized
    fun remember(book: Book?) {
        if (book == null) return
        last = book.copy()
    }

    fun peek(): Book? = last

    @Synchronized
    fun clear() {
        last = null
    }
}
