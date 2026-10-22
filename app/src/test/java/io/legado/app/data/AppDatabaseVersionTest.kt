package io.legado.app.data

import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 数据库装配面（ng-js-source-port）。
 *
 * `mainJs` 能力要求 `book_sources` 表与 `book_sources_part` 视图同时可见，
 * 这里锁定 DAO 已挂到 AppDatabase（漏挂会让 Room 编译期就失败，但测试兜底更直观），
 * 并确认 115 版 schema 已导出（迁移链的机器可读证据）。
 */
class AppDatabaseVersionTest {

    @Test
    fun bookSourceDao_isExposed() {
        val methods = AppDatabase::class.java.methods.map { it.name }
        assertTrue("AppDatabase 必须暴露 bookSourceDao", methods.contains("getBookSourceDao"))
    }

    @Test
    fun exportedSchema115_exists() {
        val candidates = listOf(
            java.io.File("app/schemas/io.legado.app.data.AppDatabase/115.json"),
            java.io.File("../app/schemas/io.legado.app.data.AppDatabase/115.json"),
        )
        assertTrue("缺少 115 版 schema 导出（Room 迁移校验依赖）", candidates.any { it.isFile })
    }
}
