package io.legado.app.data.entities

import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * W8 / REQ-31（AD-12）：`SceneBookmark` 实体契约。
 *
 * 锁三条易失守约定：
 * ① **字段全部有默认值**（Room 实体约定；且 `@PrimaryKey(autoGenerate)` 的 id 默认 0）；
 * ② `contentKind` 路由口径 0=文字 / 1=漫画 / 2=图片订阅（三路径跳转依据，改值即破路由）；
 * ③ `@Keep` 与 `@Parcelize` 注解在位（R8 剥离防护 + 跨页传递）。
 */
class SceneBookmarkEntityTest {

    private fun read(rel: String): String =
        listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
            .readText()
            .replace("\r\n", "\n")

    private val src by lazy { read("src/main/java/io/legado/app/data/entities/SceneBookmark.kt") }

    @Test
    fun allFieldsAreDefaulted() {
        val item = SceneBookmark()
        assertEquals("id 默认 0（自增主键）", 0L, item.id)
        assertEquals("bookUrl 默认空", "", item.bookUrl)
        assertEquals("contentKind 默认 0（文字路径）", 0, item.contentKind)
        assertEquals("tags 默认空 JSON 数组", "[]", item.tags)
        assertTrue("time 默认应为当前毫秒时间戳", item.time > 0L)
    }

    @Test
    fun routingKindsAndAnnotationsAreLocked() {
        assertTrue("必须 @Keep（R8 剥离防护）", src.contains("@Keep"))
        assertTrue("必须 @Parcelize", src.contains("@Parcelize"))
        assertTrue("表名须为 sceneBookmarks", src.contains("tableName = \"sceneBookmarks\""))
        assertTrue(
            "contentKind 口径注释须保留（0=文字 1=漫画 2=图片订阅）",
            src.contains("0=文字 1=漫画 2=图片订阅")
        )
    }
}
