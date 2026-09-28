package io.legado.app.data.dao

import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * W8 / REQ-31（AD-12）：`SceneBookmarkDao` 契约测试。
 *
 * 锁四条易失守约定：
 * ① 表名与实体一致（`sceneBookmarks`）——写错表名会让全部查询在运行时才炸；
 * ② 两个核心读路径的**排序口径**（全量 `time desc` / 按书 `chapterIndex, time`，跳回原位置依赖后者）；
 * ③ 写路径齐备且幂等（`insert` 返回自增 id + `REPLACE`；`update` / `delete` / `deleteById`）；
 * ④ 按书清空（`deleteByBook`）存在且**不带**通配条件（防误删全表）。
 */
class SceneBookmarkDaoContractTest {

    private fun read(rel: String): String =
        listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
            .readText()
            .replace("\r\n", "\n")

    private val src by lazy { read("src/main/java/io/legado/app/data/dao/SceneBookmarkDao.kt") }

    @Test
    fun declaresDaoInterfaceOnSceneBookmarksTable() {
        assertTrue("必须是 @Dao 接口", src.contains("@Dao") && src.contains("interface SceneBookmarkDao"))
        assertTrue("表名须为 sceneBookmarks", src.contains("from sceneBookmarks"))
        assertFalse("不得出现其它表名", src.contains("from highlights") || src.contains("from books "))
    }

    @Test
    fun readPathsKeepRequiredOrdering() {
        assertTrue("全量流须按时间倒序", src.contains("select * from sceneBookmarks order by time desc"))
        assertTrue(
            "按书查询须按章节+时间排序（跳回原位置依赖）",
            src.contains("where bookUrl = :bookUrl order by chapterIndex, time")
        )
        assertTrue("须暴露 Flow 全量", src.contains("fun flowAll(): Flow<List<SceneBookmark>>"))
        assertTrue("须暴露按书 Flow", src.contains("fun flowByBook(bookUrl: String): Flow<List<SceneBookmark>>"))
        assertTrue("须暴露按书同步查询", src.contains("fun getByBook(bookUrl: String): List<SceneBookmark>"))
        assertTrue("须暴露计数（库页聚合）", src.contains("fun count(): Int"))
    }

    @Test
    fun writePathsAreCompleteAndIdempotent() {
        assertTrue("insert 须返回自增 id", src.contains("fun insert(bookmark: SceneBookmark): Long"))
        assertTrue("insert 须 REPLACE 幂等", src.contains("OnConflictStrategy.REPLACE"))
        assertTrue("须有 update", src.contains("fun update(bookmark: SceneBookmark)"))
        assertTrue("须有 delete(实体)", src.contains("fun delete(bookmark: SceneBookmark)"))
        assertTrue("须有按 id 删除", src.contains("fun deleteById(id: Long)"))
    }

    @Test
    fun deleteByBookIsScopedToTheBook() {
        assertTrue(
            "按书清空必须带 :bookUrl 条件",
            src.contains("delete from sceneBookmarks where bookUrl = :bookUrl")
        )
        assertFalse(
            "不得出现无条件清空（防误删全表）",
            src.contains("delete from sceneBookmarks\"") || src.contains("delete from sceneBookmarks )")
        )
    }
}
