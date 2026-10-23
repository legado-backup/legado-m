package io.legado.app.data.dao

import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 大字段 SQL 构造白名单（2026-10-23 js-source-parity-and-crash-fix R5）。
 *
 * `@RawQuery` 失去 Room 的编译期校验 ⇒ 用本测试钉住两点：
 * ① 列名只能来自 [RssLargeColumn]（不存在外部输入拼接路径）；
 * ② 生成 SQL 形状固定（`limit 1` + `substr` 的 1 基偏移由调用方保证）。
 */
class RssLargeFieldSqlTest {

    @Test
    fun lengthQueryIsFixedShape() {
        val sql = RssLargeFieldSql.lengthQuery(
            "rssArticles",
            RssLargeColumn.IMAGE,
            "origin = ? and link = ? and sort = ?"
        )
        assertEquals(
            "select length(image) from rssArticles where origin = ? and link = ? and sort = ? limit 1",
            sql
        )
    }

    @Test
    fun chunkQueryIsFixedShape() {
        val sql = RssLargeFieldSql.chunkQuery(
            "rssStars",
            RssLargeColumn.VARIABLE,
            "origin = ? and link = ?"
        )
        assertEquals(
            "select substr(variable, ?, ?) from rssStars where origin = ? and link = ? limit 1",
            sql
        )
    }

    @Test
    fun allWhitelistedColumnsArePlainIdentifiers() {
        RssLargeColumn.entries.forEach { column ->
            assertTrue(
                "白名单列名必须是纯标识符（防注入）：${column.column}",
                Regex("[A-Za-z_][A-Za-z0-9_]*").matches(column.column)
            )
            assertTrue(
                "生成 SQL 必须包含该列名",
                RssLargeFieldSql.lengthQuery("rssArticles", column, "origin = ?").contains(column.column)
            )
        }
    }

    @Test
    fun unknownTableRejected() {
        assertThrows(IllegalArgumentException::class.java) {
            RssLargeFieldSql.lengthQuery("rssArticles; drop table books", RssLargeColumn.IMAGE, "1=1")
        }
        assertThrows(IllegalArgumentException::class.java) {
            RssLargeFieldSql.chunkQuery("otherTable", RssLargeColumn.IMAGE, "1=1")
        }
    }
}
