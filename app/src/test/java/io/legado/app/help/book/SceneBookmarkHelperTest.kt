package io.legado.app.help.book

import io.legado.app.data.entities.SceneBookmark
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * W8 / REQ-32（AD-12）：名场面书签**锚点装载/读回 + 按书聚合**契约。
 *
 * 为什么要锁：
 * ① 锚点是「一键跳回原位置」的唯一依据 —— 键名漂移（`chapterPos`→`chapter_position`）会让跳转静默失焦，
 *    且编译期无提示（JSON 取名是运行期字符串）；
 * ② `groupByBook` 是库页 `CollapseSectionHeader` 的数据源，书序/组内序一旦漂移，用户看到的回看顺序就会乱。
 */
class SceneBookmarkHelperTest {

    private fun item(
        id: Long = 0,
        bookUrl: String = "",
        bookName: String = "",
        chapterIndex: Int = 0,
        time: Long = 0,
        kind: Int = SceneBookmarkHelper.KIND_TEXT
    ) = SceneBookmark(
        id = id,
        bookUrl = bookUrl,
        bookName = bookName,
        chapterIndex = chapterIndex,
        time = time,
        contentKind = kind
    )

    @Test
    fun textAnchorRoundTrips() {
        val anchor = SceneBookmarkHelper.textAnchor(37)
        assertEquals(37, SceneBookmarkHelper.chapterPosOf(anchor))
        assertEquals("文字路径锚点键口径", "chapterPos", SceneBookmarkHelper.ANCHOR_CHAPTER_POS)
    }

    @Test
    fun mangaAnchorRoundTrips() {
        val anchor = SceneBookmarkHelper.mangaAnchor(5)
        assertEquals(5, SceneBookmarkHelper.pageIndexOf(anchor))
        assertNull("漫画锚点不含文字路径键", SceneBookmarkHelper.chapterPosOf(anchor))
    }

    @Test
    fun imageAnchorRoundTrips() {
        val anchor = SceneBookmarkHelper.imageAnchor("https://example.invalid/a.jpg")
        assertEquals("https://example.invalid/a.jpg", SceneBookmarkHelper.imageUrlOf(anchor))
        assertNull("未传文章链接时不得写入空键", SceneBookmarkHelper.articleLinkOf(anchor))
    }

    @Test
    fun imageAnchorKeepsArticleLinkForJumpBack() {
        val anchor = SceneBookmarkHelper.imageAnchor(
            "https://example.invalid/a.jpg",
            "https://example.invalid/post/1"
        )
        assertEquals("https://example.invalid/post/1", SceneBookmarkHelper.articleLinkOf(anchor))
        assertEquals(
            "新增 articleLink 不得破坏 imageUrl 读回",
            "https://example.invalid/a.jpg",
            SceneBookmarkHelper.imageUrlOf(anchor)
        )
    }

    @Test
    fun legacyImageAnchorWithoutArticleLinkDegradesToNull() {
        assertNull("老数据（无 articleLink 键）应回落 null 而非抛异常", SceneBookmarkHelper.articleLinkOf("{\"imageUrl\":\"u\"}"))
        assertNull("空串按缺省处理", SceneBookmarkHelper.articleLinkOf(""))
        assertNull("损坏锚点", SceneBookmarkHelper.articleLinkOf("{oops"))
    }

    @Test
    fun damagedAnchorDegradesToNull() {
        assertNull("空白锚点", SceneBookmarkHelper.chapterPosOf(""))
        assertNull("非 JSON 锚点", SceneBookmarkHelper.chapterPosOf("chapterPos=1"))
        assertNull("JSON 但缺键", SceneBookmarkHelper.chapterPosOf("{\"pageIndex\":2}"))
        assertNull("图片锚点缺键", SceneBookmarkHelper.imageUrlOf("{\"pageIndex\":2}"))
        assertNull("空串图片地址按缺省处理", SceneBookmarkHelper.imageUrlOf("{\"imageUrl\":\"\"}"))
    }

    @Test
    fun zeroIsAValidAnchorValue() {
        assertEquals("0 是合法下标（不得被当成缺省）", 0, SceneBookmarkHelper.chapterPosOf("{\"chapterPos\":0}"))
        assertEquals("0 是合法页下标", 0, SceneBookmarkHelper.pageIndexOf("{\"pageIndex\":0}"))
    }

    @Test
    fun groupByBookKeepsBookOrderAndSortsInsideByChapter() {
        val items = listOf(
            item(id = 1, bookUrl = "bookA", bookName = "甲书", chapterIndex = 9, time = 100),
            item(id = 2, bookUrl = "bookB", bookName = "乙书", chapterIndex = 3, time = 200),
            item(id = 3, bookUrl = "bookA", bookName = "甲书", chapterIndex = 2, time = 300)
        )
        val groups = SceneBookmarkHelper.groupByBook(items)
        assertEquals("书序取首次出现顺序（DAO 已按时间倒序）", listOf("bookA", "bookB"), groups.map { it.bookUrl })
        assertEquals("组内按章节升序（回看顺序稳定）", listOf(2, 9), groups[0].items.map { it.chapterIndex })
        assertEquals("组头信息取组内首条", "甲书", groups[0].bookName)
        assertEquals("分组不丢项", 3, groups.sumOf { it.items.size })
    }

    @Test
    fun tagsJsonRoundTrips() {
        val json = SceneBookmarkHelper.tagsToJson(listOf("燃", "转折"))
        assertEquals(listOf("燃", "转折"), SceneBookmarkHelper.tagsFromJson(json))
    }

    @Test
    fun damagedTagsJsonDegradesToEmpty() {
        assertTrue("空串", SceneBookmarkHelper.tagsFromJson("").isEmpty())
        assertTrue("损坏 JSON", SceneBookmarkHelper.tagsFromJson("{oops").isEmpty())
        assertTrue("空数组", SceneBookmarkHelper.tagsFromJson("[]").isEmpty())
    }

    @Test
    fun routingKindsMatchEntityContract() {
        assertEquals("文字路径 = 0（与实体注释口径一致）", 0, SceneBookmarkHelper.KIND_TEXT)
        assertEquals("漫画路径 = 1", 1, SceneBookmarkHelper.KIND_MANGA)
        assertEquals("图片订阅路径 = 2", 2, SceneBookmarkHelper.KIND_IMAGE)
    }
}
