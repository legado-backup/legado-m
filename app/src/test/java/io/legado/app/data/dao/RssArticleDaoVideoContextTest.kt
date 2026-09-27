package io.legado.app.data.dao

import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * `RssArticleDao.getListByOriginSort` 的**契约**不变量（Room 编译期约束 + 语义）。
 *
 * 背景（2026-09-27 用户报障）：W1 的「正文含视频自动转内置播放器」路由只有单篇文章上下文，
 * W2 的兜底把它写成 1 篇列表 ⇒ 播放器侧 `size > 1` 的文章模式判定失效 ⇒
 * 沉浸式上下滑切视频 与 传统式上一部下一部**同时失效**。修复靠本查询补齐同源同分类列表。
 *
 * 两条易失守约定：
 * ① 查询口径必须与列表页 `flowByOriginSort` **一致**（同源 + 同分类 + order 倒序），
 *    否则播放器内上下切换的顺序与列表页不一致；
 * ② **不得** select `content`/`description`/`image`/`variable` —— 这些列在部分源可超
 *    CursorWindow 2MB 上限（历史多次 SQLiteBlobTooBigException 铁证）。
 */
class RssArticleDaoVideoContextTest {

    private val dao by lazy {
        listOf(
            File("src/main/java/io/legado/app/data/dao/RssArticleDao.kt"),
            File("../app/src/main/java/io/legado/app/data/dao/RssArticleDao.kt"),
            File("app/src/main/java/io/legado/app/data/dao/RssArticleDao.kt")
        ).first { it.isFile }.readText()
            // 工作副本可能是 CRLF ⇒ 归一到 LF，保证多行断言稳定
            .replace("\r\n", "\n")
    }

    private val queryBlock by lazy {
        val start = dao.indexOf("suspend fun getListByOriginSort(")
        assertTrue("未找到 getListByOriginSort 声明", start > 0)
        // 向上回溯到该函数的 @Query 注解起点
        val annStart = dao.lastIndexOf("@Query(", start)
        assertTrue("getListByOriginSort 必须带 @Query", annStart > 0)
        dao.substring(annStart, start)
    }

    @Test
    fun listContextQueryIsSuspendAndOneShot() {
        assertTrue(
            "同源同分类列表查询须为 suspend 一次性读取（Flow 版另有 flowByOriginSort）",
            dao.contains("suspend fun getListByOriginSort(origin: String, sort: String): List<RssArticle>")
        )
    }

    @Test
    fun listContextQueryMatchesListPageScope() {
        assertTrue("查询须限定 origin（同源）", queryBlock.contains("t1.origin = :origin"))
        assertTrue("查询须限定 sort（同分类）", queryBlock.contains("t1.sort = :sort"))
        assertTrue(
            "排序口径须与列表页一致（order by `order` desc）",
            queryBlock.contains("order by `order` desc")
        )
    }

    @Test
    fun listContextQueryAvoidsCursorWindowBlowupColumns() {
        listOf("t1.content", "t1.description", "t1.image", "t1.variable").forEach { col ->
            assertFalse(
                "列表上下文化查询不得 select $col（大字段会挤满 CursorWindow 2MB 导致取数失败）",
                queryBlock.contains(col)
            )
        }
    }
}