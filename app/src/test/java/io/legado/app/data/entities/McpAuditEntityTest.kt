package io.legado.app.data.entities

import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * `McpAudit` 实体契约（一期 3.6）。
 *
 * 为什么用源码断言：Room 实体需要 Android 运行时才能实例化；而「表名 / 列顺序 / 索引 / `@Keep`」
 * 四条契约**编译期无感**，任一条改动都会让迁移 DDL 与实体错位（运行时 schema 校验直接崩）
 * 或让 release 包审计字段被 R8 改名。
 */
class McpAuditEntityTest {

    private fun read(rel: String): String =
        listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
            .readText()
            .replace("\r\n", "\n")

    private val entity by lazy { read("src/main/java/io/legado/app/data/entities/McpAudit.kt") }

    /** 与 migration_112_113 的 DDL 列顺序逐列一致（改实体必须同步改迁移）。 */
    private val expectedProperties = listOf(
        "id", "time", "source", "channel", "level", "target", "method", "success", "errorMsg", "elapsedMs"
    )

    @Test
    fun tableNameAndIndicesAreStable() {
        assertTrue("表名须为 mcp_audit", entity.contains("""tableName = "mcp_audit""""))
        assertTrue(
            "索引须为 time/source/level（审计按这三列检索）",
            entity.contains("""indices = [Index("time"), Index("source"), Index("level")]""")
        )
    }

    @Test
    fun propertyOrderMatchesMigrationDdl() {
        val body = entity.substringAfter("data class McpAudit(").substringBefore("\n)")
        val seen = expectedProperties.map { name ->
            val idx = body.indexOf("val $name:")
            assertTrue("实体缺字段 $name", idx >= 0)
            idx
        }
        assertEquals(
            "字段声明顺序必须与 migration DDL 顺序一致（Room 运行时按序校验）",
            seen.sorted(),
            seen
        )
    }

    @Test
    fun keptForGsonSerialization() {
        assertTrue(
            "@Keep 不可去掉：审计记录会被 Gson 序列化给控制台，R8 改名即字段全读不到",
            Regex("""@Keep\s+@Entity""").containsMatchIn(entity)
        )
    }

    @Test
    fun targetIsDocumentedAsSanitized() {
        // target 不得写明文凭证：实体注释与落库路径（McpAuditor）都须声明脱敏契约
        assertTrue("实体须注明 target 已脱敏", entity.contains("脱敏"))
    }
}
