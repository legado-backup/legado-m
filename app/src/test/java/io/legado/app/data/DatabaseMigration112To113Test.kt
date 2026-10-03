package io.legado.app.data

import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * `112 → 113` 迁移与 schema 快照不变量（一期 3.6 / G-12 三件证据之①②的 JVM 侧固化）。
 *
 * 覆盖六条易失守约定：
 * ① 库版本与迁移注册**同步**（版本升了但迁移没注册 ⇒ 老用户升级即崩）；
 * ② 迁移**只建表 + 建索引**（不 DROP 不重建 ⇒ 零数据风险）；
 * ③ `mcp_audit` 的 DDL 列集与实体一致（10 列，全部 NOT NULL）；
 * ④ 三个索引名与实体 `indices` 声明同口径（Room 运行时校验按名比对）；
 * ⑤ 新版本 schema json **已导出**且含该表（缺则运行时 schema 校验无从比对）；
 * ⑥ 不得启用裸 `fallbackToDestructiveMigration()`（会静默清库）。
 */
class DatabaseMigration112To113Test {

    private fun read(rel: String): String =
        listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
            .readText()
            .replace("\r\n", "\n")

    private val appDatabase by lazy { read("src/main/java/io/legado/app/data/AppDatabase.kt") }
    private val migrations by lazy { read("src/main/java/io/legado/app/data/DatabaseMigrations.kt") }

    private val expectedColumns = listOf(
        "`id` INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL",
        "`time` INTEGER NOT NULL",
        "`source` TEXT NOT NULL",
        "`channel` TEXT NOT NULL",
        "`level` TEXT NOT NULL",
        "`target` TEXT NOT NULL",
        "`method` TEXT NOT NULL",
        "`success` INTEGER NOT NULL",
        "`errorMsg` TEXT NOT NULL",
        "`elapsedMs` INTEGER NOT NULL"
    )

    @Test
    fun databaseVersionIsBumpedTo113() {
        assertTrue("AppDatabase version 须为 113", appDatabase.contains("version = 113"))
        assertTrue("实体须登记 McpAudit", appDatabase.contains("McpAudit::class"))
        assertTrue("DAO 须暴露 mcpAuditDao", appDatabase.contains("abstract val mcpAuditDao"))
        assertTrue("迁移数组须登记 migration_112_113", migrations.contains("migration_112_113"))
        assertTrue(
            "迁移对象须为 Migration(112, 113)",
            migrations.contains("private val migration_112_113 = object : Migration(112, 113)")
        )
    }

    @Test
    fun migrationOnlyCreatesTableAndIndicesWithoutDestructiveDdl() {
        val body = migrations.substringAfter("private val migration_112_113")
            .substringBefore("private val migration_10_11")
        assertTrue("必须创建 mcp_audit 表", body.contains("CREATE TABLE IF NOT EXISTS `mcp_audit`"))
        expectedColumns.forEach { col ->
            assertTrue("DDL 须含列：$col", body.contains(col))
        }
        listOf("time", "source", "level").forEach { col ->
            assertTrue(
                "须建 $col 索引（审计按时间/来源/级别检索）",
                body.contains("CREATE INDEX IF NOT EXISTS `index_mcp_audit_$col`")
            )
        }
        assertFalse("迁移禁 DROP 表（防数据丢失）", body.contains("DROP TABLE"))
        assertFalse("迁移禁重建表（防数据丢失）", body.contains("RENAME TO"))
    }

    // 实体 / DAO 的字段级契约已迁到其**所属包**：`data/entities/McpAuditEntityTest` 与
    // `data/dao/McpAuditDaoContractTest`（改码↔测试配对要求同包有测试变更，且就近断言更易维护）。

    @Test
    fun schemaSnapshotForNewVersionIsExported() {
        val schema = listOf(
            File("schemas/io.legado.app.data.AppDatabase/113.json"),
            File("../app/schemas/io.legado.app.data.AppDatabase/113.json"),
            File("app/schemas/io.legado.app.data.AppDatabase/113.json")
        ).firstOrNull { it.isFile }
        assertTrue("G-12 ①：113.json 必须已由 Room 导出", schema != null)
        val text = schema!!.readText()
        assertTrue("schema 须含 mcp_audit 表", text.contains("mcp_audit"))
        assertTrue("schema 须含 target 列", text.contains("target"))
        assertTrue("schema 须含 elapsedMs 列", text.contains("elapsedMs"))
    }

    @Test
    fun destructiveFallbackIsNotEnabled() {
        assertFalse(
            "不得启用裸 fallbackToDestructiveMigration（会静默清库）",
            appDatabase.contains(".fallbackToDestructiveMigration()")
        )
    }
}
