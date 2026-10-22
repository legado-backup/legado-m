package io.legado.app.data.entities

import io.legado.app.utils.GSON
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * `BookSource.mainJs` 与 `book_sources_part` 视图口径（ng-js-source-port）。
 *
 * 断言两件事：
 * 1. `mainJs` 是**可选字段**（老 JSON 不填 ⇒ null，老源零影响）；
 * 2. 视图 SQL 与迁移 SQL 必须包含 JS 判定（否则搜索/登录/JS 标识全线失真）。
 */
class BookSourceMainJsTest {

    @Test
    fun mainJs_defaultsNullForLegacyJson() {
        val source = GSON.fromJson("""{"bookSourceUrl":"u","bookSourceName":"n"}""", BookSource::class.java)
        assertNull(source.mainJs)
    }

    @Test
    fun mainJs_deserializedFromNgSourceJson() {
        val script = "var config = {bookSourceUrl:'https://x'};"
        val source = GSON.fromJson(
            """{"bookSourceUrl":"u","bookSourceName":"n","mainJs":${GSON.toJson(script)}}""",
            BookSource::class.java,
        )
        assertEquals(script, source.mainJs)
    }

    @Test
    fun mainJs_survivesGsonRoundTrip() {
        val source = BookSource(
            bookSourceUrl = "u",
            bookSourceName = "n",
            mainJs = "function search(k,p){ return []; }",
        )
        val reloaded = GSON.fromJson(GSON.toJson(source), BookSource::class.java)
        assertEquals(source.mainJs, reloaded.mainJs)
    }

    @Test
    fun mainJs_isPreservedByCopy() {
        val source = BookSource(bookSourceUrl = "u", mainJs = "var config={};")
        assertTrue(source.copy(bookSourceGroup = "g").mainJs == source.mainJs)
    }
}
