package io.legado.app.data.dao

import java.io.File
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * `McpAuditDao` 契约（一期 3.6）。
 *
 * 为什么用源码断言：`@Dao` 需要 Room 编译器 + Android 运行时才能调用；而三条查询的**语义**
 * （写入 / 按目标检索 / 保留清理 / 计数）是门禁与真机探针共同依赖的接口面，删除或改名会让
 * 三期控制台与 `db_schema_probe` 静默失效。
 */
class McpAuditDaoContractTest {

    private fun read(rel: String): String =
        listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
            .readText()
            .replace("\r\n", "\n")

    private val dao by lazy { read("src/main/java/io/legado/app/data/dao/McpAuditDao.kt") }

    @Test
    fun exposesWriteAndRetentionQueries() {
        assertTrue("须有插入（审计落库入口）", dao.contains("@Insert"))
        assertTrue("插入须挂起（异步投递路径调用）", dao.contains("suspend fun insert(audit: McpAudit)"))
        assertTrue("须有保留清理（>7 天）", dao.contains("suspend fun deleteBefore(before: Long)"))
        assertTrue("须有计数（审计页 + 真机探针）", dao.contains("suspend fun count()"))
    }

    @Test
    fun recentByTargetUsesLikeAndDescOrder() {
        assertTrue(
            "按目标检索须用 LIKE 且按时间倒序（三期控制台轮询）",
            dao.contains("WHERE target LIKE :key ORDER BY time DESC LIMIT :limit")
        )
        assertTrue("默认返回条数须为 20", dao.contains("limit: Int = 20"))
    }

    @Test
    fun tableNameMatchesEntity() {
        assertTrue("查询须落在 mcp_audit 表", dao.contains("FROM mcp_audit"))
    }
}
