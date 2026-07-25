package io.legado.app.model.webBook

import io.legado.app.data.entities.Book
import io.legado.app.data.entities.BookSource

// 源码参照: app/src/main/java/io/legado/app/model/webBook/WebBook.kt
// 简化说明: WebBook 依赖 BookInfo/SearchBook 等未抽取模块，方法抛出 UnsupportedOperationException | 已知上限: reGetBook/refreshTocUrl 不可用 | 升级路径: 抽取 BookInfo/SearchBook 模块后实现

/**
 * WebBook Stub
 * AnalyzeRule.reGetBook/refreshTocUrl 调用此对象的方法
 */
object WebBook {

    /**
     * 精确搜索书籍
     * 源码参照: app/src/main/java/io/legado/app/model/webBook/WebBook.kt#L480-L491
     */
    suspend fun preciseSearchAwait(
        bookSource: BookSource,
        name: String,
        author: String
    ): Result<Book> {
        throw UnsupportedOperationException("JVM 环境不支持 WebBook.preciseSearchAwait，需抽取 BookInfo/SearchBook 模块")
    }

    /**
     * 获取书籍信息
     * 源码参照: app/src/main/java/io/legado/app/model/webBook/WebBook.kt#L192-L210
     */
    suspend fun getBookInfoAwait(
        bookSource: BookSource,
        book: Book,
        canReName: Boolean = true
    ): Book {
        throw UnsupportedOperationException("JVM 环境不支持 WebBook.getBookInfoAwait，需抽取 BookInfo 模块")
    }
}
