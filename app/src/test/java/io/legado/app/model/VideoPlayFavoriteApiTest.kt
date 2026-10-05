package io.legado.app.model

import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * video-live-favorite-fix AD-01/AD-04：`VideoPlay` 收藏权威源与记录链兜底的**接线不变量**。
 *
 * 为什么用源码文本断言：`VideoPlay` 是依赖 `appCtx` 的全局 `object`，其判定逻辑本身
 * 已在纯函数 `VideoFavoriteResolver`（另见其单测）中覆盖；此处只锁定三件易失守的接线约定：
 * ① 三个薄封装必须存在且**全部委托**给纯函数（禁止在 VideoPlay 内重新内联判定）；
 * ② `ensureReadRecord` 必须在 `initSource` 与 `switchToArticle` **两处**都被调用；
 * ③ 兜底写记录必须是「先查后插」（容忍 `rssReadRecords` 主键冲突），且失败不抛。
 */
class VideoPlayFavoriteApiTest {

    private fun res(rel: String): String =
        listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }.readText()

    private val videoPlay by lazy { res("src/main/java/io/legado/app/model/VideoPlay.kt") }

    @Test
    fun exposesFavoriteAuthorityThinWrappers() {
        assertTrue("须暴露当前条目解析", videoPlay.contains("fun currentRssArticle(): RssArticle?"))
        assertTrue("须暴露可见性判定", videoPlay.contains("fun canFavoriteCurrent(): Boolean"))
        assertTrue("须暴露收藏构造", videoPlay.contains("fun buildCurrentStar(): RssStar?"))
    }

    @Test
    fun wrappersDelegateToPureResolver() {
        assertTrue(videoPlay.contains("VideoFavoriteResolver.pickArticle("))
        assertTrue(videoPlay.contains("VideoFavoriteResolver.canFavorite("))
        assertTrue(videoPlay.contains("VideoFavoriteResolver.buildStar("))
        assertTrue(videoPlay.contains("VideoFavoriteResolver.buildRecord("))
    }

    @Test
    fun ensureReadRecordIsCalledFromInitSourceAndSwitchToArticle() {
        val callCount = Regex("""ensureReadRecord\(\)""").findAll(videoPlay).count()
        // 1 处定义（private suspend fun ensureReadRecord()）+ 2 处调用
        assertTrue("ensureReadRecord 应有定义 1 处 + 调用 2 处，实际=$callCount", callCount >= 3)
        val initSourceAt = videoPlay.indexOf("suspend fun initSource(")
        assertTrue("initSource 内须调用兜底", videoPlay.indexOf("ensureReadRecord()", initSourceAt) > initSourceAt)
        val switchAt = videoPlay.indexOf("fun switchToArticle(")
        assertTrue("switchToArticle 内须调用兜底", videoPlay.indexOf("ensureReadRecord()", switchAt) > switchAt)
    }

    @Test
    fun ensureReadRecordIsQueryFirstThenInsert() {
        val fnAt = videoPlay.indexOf("private suspend fun ensureReadRecord()")
        assertTrue(fnAt > 0)
        val body = videoPlay.substring(fnAt, minOf(fnAt + 1400, videoPlay.length))
        val getAt = body.indexOf("rssReadRecordDao.getRecord(")
        val insertAt = body.indexOf("rssReadRecordDao.insertRecord(")
        assertTrue("须先查", getAt > 0)
        assertTrue("须后插", insertAt > getAt)
        assertTrue("插入须容错（不抛）", body.contains("runCatching"))
    }
}