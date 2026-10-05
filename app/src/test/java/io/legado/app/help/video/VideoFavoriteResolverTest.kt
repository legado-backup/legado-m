package io.legado.app.help.video

import io.legado.app.data.entities.RssArticle
import io.legado.app.data.entities.RssReadRecord
import io.legado.app.data.entities.RssStar
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * video-live-favorite-fix AD-01/AD-02/AD-04：收藏判定与派生的**纯函数**单测。
 *
 * 覆盖三类易失守约定：
 * ① 「当前条目」解析优先级（收藏 > 记录 > 文章列表）—— 直播「首次点入无记录」靠第三级兜底；
 * ② 收藏可见性判定（订阅源视频恒真；书源/单 URL/无上下文恒假）；
 * ③ 收藏/记录实体的构造口径（标题=文章标题、分组=默认分组、type 透传、主键=link）。
 */
class VideoFavoriteResolverTest {

    private fun article(
        title: String = "直播频道A",
        link: String = "http://example.invalid/live/1.flv?wsTime=1",
        origin: String = "http://example.invalid",
        type: Int = 2,
        sort: String = "分类X"
    ) = RssArticle(
        origin = origin, sort = sort, title = title, link = link, type = type
    )

    // ---------------- pickArticle：三级优先级 ----------------

    @Test
    fun pickArticlePrefersStar() {
        val star = RssStar(origin = "o", link = "l", title = "收藏标题", type = 2)
        val record = RssReadRecord(record = "l", origin = "o", title = "记录标题", type = 2)
        val picked = VideoFavoriteResolver.pickArticle(star, record, listOf(article(title = "列表标题")), 0)
        assertEquals("收藏实体优先级最高", "收藏标题", picked?.title)
    }

    @Test
    fun pickArticleFallsBackToRecordWhenNoStar() {
        val record = RssReadRecord(record = "l", origin = "o", title = "记录标题", type = 2)
        val picked = VideoFavoriteResolver.pickArticle(null, record, listOf(article(title = "列表标题")), 0)
        assertEquals("无收藏时次选阅读记录", "记录标题", picked?.title)
    }

    @Test
    fun pickArticleFallsBackToArticleListWhenNeitherExists() {
        val picked = VideoFavoriteResolver.pickArticle(null, null, listOf(article(title = "列表标题")), 0)
        assertEquals("均无时兜底文章列表当前项（直播首次点入场景）", "列表标题", picked?.title)
    }

    @Test
    fun pickArticleReturnsNullWhenEverythingIsEmpty() {
        assertNull(VideoFavoriteResolver.pickArticle(null, null, null, 0))
        assertNull(VideoFavoriteResolver.pickArticle(null, null, emptyList(), 0))
    }

    @Test
    fun pickArticleReturnsNullOnIndexOutOfBounds() {
        assertNull(VideoFavoriteResolver.pickArticle(null, null, listOf(article()), 5))
        assertNull(VideoFavoriteResolver.pickArticle(null, null, listOf(article()), -1))
    }

    // ---------------- canFavorite：可见性判定 ----------------

    @Test
    fun canFavoriteTrueForRssSourceWithArticle() {
        assertTrue(
            VideoFavoriteResolver.canFavorite(
                singleUrl = false, hasBook = false, isRssSource = true, article = article()
            )
        )
    }

    @Test
    fun canFavoriteFalseForBookSourceVideo() {
        assertEquals(
            false,
            VideoFavoriteResolver.canFavorite(
                singleUrl = false, hasBook = true, isRssSource = true, article = article()
            )
        )
    }

    @Test
    fun canFavoriteFalseForSingleUrlDirectPlay() {
        assertEquals(
            false,
            VideoFavoriteResolver.canFavorite(
                singleUrl = true, hasBook = false, isRssSource = false, article = article()
            )
        )
    }

    @Test
    fun canFavoriteFalseForNonRssSource() {
        assertEquals(
            false,
            VideoFavoriteResolver.canFavorite(
                singleUrl = false, hasBook = false, isRssSource = false, article = article()
            )
        )
    }

    @Test
    fun canFavoriteFalseWithoutArticleContext() {
        assertEquals(
            false,
            VideoFavoriteResolver.canFavorite(
                singleUrl = false, hasBook = false, isRssSource = true, article = null
            )
        )
    }

    // ---------------- buildStar：字段口径 ----------------

    @Test
    fun buildStarCopiesTitleGroupTypeAndLink() {
        val star = VideoFavoriteResolver.buildStar(article())
        assertEquals("标题取文章标题", "直播频道A", star?.title)
        assertEquals("分组取默认分组", "默认分组", star?.group)
        assertEquals("类型透传（2=视频）", 2, star?.type)
        assertEquals("主键 link 透传", "http://example.invalid/live/1.flv?wsTime=1", star?.link)
        assertEquals("origin 透传", "http://example.invalid", star?.origin)
        assertTrue("收藏时间须为正", (star?.starTime ?: 0L) > 0L)
    }

    @Test
    fun buildStarReturnsNullWithoutArticle() {
        assertNull(VideoFavoriteResolver.buildStar(null))
    }

    // ---------------- buildRecord：主键与字段口径 ----------------

    @Test
    fun buildRecordUsesLinkAsPrimaryKey() {
        val record = VideoFavoriteResolver.buildRecord(article())
        assertEquals("记录主键 = 文章 link", "http://example.invalid/live/1.flv?wsTime=1", record?.record)
        assertEquals("origin 透传", "http://example.invalid", record?.origin)
        assertEquals("类型透传", 2, record?.type)
        assertTrue("阅读时间须为正", (record?.readTime ?: 0L) > 0L)
    }

    @Test
    fun buildRecordReturnsNullWithoutArticle() {
        assertNull(VideoFavoriteResolver.buildRecord(null))
    }
}