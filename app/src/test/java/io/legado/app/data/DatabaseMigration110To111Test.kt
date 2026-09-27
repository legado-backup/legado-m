package io.legado.app.data

import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * W3 / REQ-16（AD-07）：`110 → 111` 迁移与 schema 快照不变量（G-12 三件证据之①②的 JVM 侧固化）。
 *
 * 覆盖四条易失守约定：
 * ① 库版本与迁移注册**同步**（版本升了但迁移没注册 ⇒ 老用户升级即崩）；
 * ② 迁移只做 `ADD COLUMN`（不 DROP 不重建 ⇒ 零数据风险）；
 * ③ 新版本 schema json **已导出**（Room 编译期产物；缺则无法做运行时 schema 校验）；
 * ④ 不得启用 `fallbackToDestructiveMigration()`（会静默清库）。
 */
class DatabaseMigration110To111Test {

    private fun read(rel: String): String =
        listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
            .readText()
            // 工作副本可能是 CRLF（Windows 检出）⇒ 归一到 LF，保证多行断言稳定
            .replace("\r\n", "\n")

    private val appDatabase by lazy { read("src/main/java/io/legado/app/data/AppDatabase.kt") }
    private val migrations by lazy { read("src/main/java/io/legado/app/data/DatabaseMigrations.kt") }

    @Test
    fun databaseVersionIsBumpedTo111() {
        assertTrue("AppDatabase version 须为 111", appDatabase.contains("version = 111"))
        assertTrue("迁移数组须登记 migration_110_111", migrations.contains("migration_110_111"))
        assertTrue(
            "迁移对象须为 Migration(110, 111)",
            migrations.contains("private val migration_110_111 = object : Migration(110, 111)")
        )
    }

    @Test
    fun migrationOnlyAddsColumnsWithMatchingDefaults() {
        val body = migrations.substringAfter("private val migration_110_111")
            .substringBefore("private val migration_109_110")
        assertTrue(
            "① 锚点列（NOT NULL DEFAULT 0）",
            body.contains("ALTER TABLE `books` ADD COLUMN `voiceParagraphAnchor` INTEGER NOT NULL DEFAULT 0")
        )
        assertTrue(
            "② 归属章节列（NOT NULL DEFAULT -1）",
            body.contains(
                "ALTER TABLE `books` ADD COLUMN `voiceParagraphAnchorChapter` INTEGER NOT NULL DEFAULT -1"
            )
        )
        assertFalse("迁移禁 DROP 表（防数据丢失）", body.contains("DROP TABLE"))
        assertFalse("迁移禁重建表（防数据丢失）", body.contains("RENAME TO"))
    }

    @Test
    fun schemaSnapshotForNewVersionIsExported() {
        val schema = listOf(
            File("schemas/io.legado.app.data.AppDatabase/111.json"),
            File("../app/schemas/io.legado.app.data.AppDatabase/111.json"),
            File("app/schemas/io.legado.app.data.AppDatabase/111.json")
        ).firstOrNull { it.isFile }
        assertTrue("G-12 ①：111.json 必须已由 Room 导出", schema != null)
        val text = schema!!.readText()
        assertTrue("schema 须含锚点列", text.contains("voiceParagraphAnchor"))
        assertTrue("schema 须含归属章节列", text.contains("voiceParagraphAnchorChapter"))
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