package io.legado.app.data

import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * W8 / REQ-31（AD-12）：`111 → 112` 迁移与 schema 快照不变量（G-12 三件证据之①②的 JVM 侧固化）。
 *
 * 覆盖五条易失守约定：
 * ① 库版本与迁移注册**同步**（版本升了但迁移没注册 ⇒ 老用户升级即崩）；
 * ② 迁移**只建表**（不 DROP 不重建 ⇒ 零数据风险）；
 * ③ `sceneBookmarks` 的 DDL 列集与实体一致（13 列，全部 NOT NULL）；
 * ④ 新版本 schema json **已导出**且含该表（缺则运行时 schema 校验无从比对）；
 * ⑤ 不得启用裸 `fallbackToDestructiveMigration()`（会静默清库）。
 */
class DatabaseMigration111To112Test {

    private fun read(rel: String): String =
        listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
            .readText()
            .replace("\r\n", "\n")

    private val appDatabase by lazy { read("src/main/java/io/legado/app/data/AppDatabase.kt") }
    private val migrations by lazy { read("src/main/java/io/legado/app/data/DatabaseMigrations.kt") }

    private val expectedColumns = listOf(
        "`id` INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL",
        "`time` INTEGER NOT NULL",
        "`bookUrl` TEXT NOT NULL",
        "`bookName` TEXT NOT NULL",
        "`bookAuthor` TEXT NOT NULL",
        "`chapterIndex` INTEGER NOT NULL",
        "`chapterName` TEXT NOT NULL",
        "`contentKind` INTEGER NOT NULL",
        "`anchor` TEXT NOT NULL",
        "`text` TEXT NOT NULL",
        "`desc` TEXT NOT NULL",
        "`tags` TEXT NOT NULL",
        "`style` TEXT NOT NULL"
    )

    @Test
    fun databaseVersionIsBumpedTo112() {
        // 版本号只能递增：112 之后新增迁移（113 mcp_audit 等）不得让本测试失真
        // ⇒ 断言「不低于 112」而非「恒等于 112」（后者每加一版都要回来改，属脆断言）。
        val version = Regex("""\bversion\s*=\s*(\d+)""").find(appDatabase)?.groupValues?.get(1)?.toInt()
        assertTrue("AppDatabase version 须 ≥ 112（实测 $version）", version != null && version >= 112)
        assertTrue("实体须登记 SceneBookmark", appDatabase.contains("SceneBookmark::class"))
        assertTrue("DAO 须暴露 sceneBookmarkDao", appDatabase.contains("abstract val sceneBookmarkDao"))
        assertTrue("迁移数组须登记 migration_111_112", migrations.contains("migration_111_112"))
        assertTrue(
            "迁移对象须为 Migration(111, 112)",
            migrations.contains("private val migration_111_112 = object : Migration(111, 112)")
        )
    }

    @Test
    fun migrationOnlyCreatesTableWithoutDestructiveDdl() {
        val body = migrations.substringAfter("private val migration_111_112")
            .substringBefore("private val migration_110_111")
        assertTrue("必须创建 sceneBookmarks 表", body.contains("CREATE TABLE IF NOT EXISTS `sceneBookmarks`"))
        expectedColumns.forEach { col ->
            assertTrue("DDL 须含列：$col", body.contains(col))
        }
        assertFalse("迁移禁 DROP 表（防数据丢失）", body.contains("DROP TABLE"))
        assertFalse("迁移禁重建表（防数据丢失）", body.contains("RENAME TO"))
    }

    @Test
    fun schemaSnapshotForNewVersionIsExported() {
        val schema = listOf(
            File("schemas/io.legado.app.data.AppDatabase/112.json"),
            File("../app/schemas/io.legado.app.data.AppDatabase/112.json"),
            File("app/schemas/io.legado.app.data.AppDatabase/112.json")
        ).firstOrNull { it.isFile }
        assertTrue("G-12 ①：112.json 必须已由 Room 导出", schema != null)
        val text = schema!!.readText()
        assertTrue("schema 须含 sceneBookmarks 表", text.contains("sceneBookmarks"))
        assertTrue("schema 须含 bookUrl 列", text.contains("bookUrl"))
        assertTrue("schema 须含 contentKind 列", text.contains("contentKind"))
    }

    @Test
    fun destructiveFallbackIsNotEnabled() {
        assertFalse(
            "不得启用裸 fallbackToDestructiveMigration（会静默清库）",
            appDatabase.contains(".fallbackToDestructiveMigration()")
        )
        assertTrue(
            "既有的古代版本 fallback 白名单须保留原样（仅 1..9）",
            appDatabase.contains(".fallbackToDestructiveMigrationFrom(false, 1, 2, 3, 4, 5, 6, 7, 8, 9)")
        )
    }
}
