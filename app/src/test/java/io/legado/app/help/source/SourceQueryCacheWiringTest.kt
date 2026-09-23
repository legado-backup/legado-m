package io.legado.app.help.source

import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * B4 · R18 接线不变量（结构断言）。
 *
 * 缓存类本身由 `TtlEpochCacheTest` 覆盖行为；这里守的是**接线**——缓存最容易失效的方式不是算法错，
 * 而是「某个写源入口忘了失效」或「改完只接了一半」：
 * - 读路径：`SourceHelp.getSource` 两个重载都必须走缓存（且 key 带类型前缀，防书源/订阅源同串串扰）；
 * - 写路径：**六类写源入口**均须调用 `SourceQueryCache.invalidate()`；
 *   其中「内置源自动更新（RuleUpdate）」经 `SourceHelp.insertBookSource` 写入 ⇒ 由该函数统一失效；
 * - 开关：关闭时直接回库（行为与改造前一致）。
 */
class SourceQueryCacheWiringTest {

    private fun code(relFromMainJava: String): String {
        val rel = "src/main/java/io/legado/app/$relFromMainJava"
        val file = listOf(File(rel), File("../app/$rel"), File("app/$rel")).firstOrNull { it.isFile }
            ?: throw AssertionError("未找到源文件（工作目录=${File(".").absolutePath}）：$rel")
        return file.readLines()
            .filterNot { it.trimStart().startsWith("//") || it.trimStart().startsWith("*") }
            .joinToString("\n")
    }

    /** 读路径：两个重载都走缓存，且 key 带类型前缀（书源/订阅源 key 空间可能同串）。 */
    @Test
    fun readPath_bothOverloadsGoThroughCache() {
        val help = code("help/source/SourceHelp.kt")
        assertTrue(
            "未分类重载必须走缓存",
            help.contains("SourceQueryCache.get(\"any:\$key\")")
        )
        assertTrue(
            "按类型重载必须走缓存（书源）",
            help.contains("SourceQueryCache.get(\"book:\$key\")")
        )
        assertTrue(
            "按类型重载必须走缓存（订阅源）",
            help.contains("SourceQueryCache.get(\"rss:\$key\")")
        )
    }

    /** 写路径：六类入口逐一登记失效（漏一类 ⇒ 该类写完后读到旧值）。 */
    @Test
    fun writeEntries_allSixRegistered() {
        val entries = mapOf(
            "①新增/编辑书源" to "ui/book/source/edit/BookSourceEditViewModel.kt",
            "①新增/编辑订阅源" to "ui/rss/source/edit/RssSourceEditViewModel.kt",
            "②删除源（书源+订阅源均经此）" to "help/source/SourceHelp.kt",
            "③批量导入（旧数据迁移）" to "help/storage/ImportOldData.kt",
            "③批量导入（回收站还原）" to "help/source/SourceRecycleBinHelp.kt",
            "④备份恢复" to "help/storage/Restore.kt",
            "⑥质量修复" to "model/QualityReportApplier.kt"
        )
        entries.forEach { (label, path) ->
            assertTrue(
                "$label 未调用 SourceQueryCache.invalidate()（写完会读到旧值）",
                code(path).contains("SourceQueryCache.invalidate()")
            )
        }
        // ⑤内置源自动更新：经 SourceHelp.insertBookSource 写入 ⇒ 断言该函数含失效调用
        val help = code("help/source/SourceHelp.kt")
        val insertFn = help.substringAfter("fun insertBookSource(").substringBefore("private fun is18Plus")
        assertTrue(
            "insertBookSource 必须失效（RuleUpdate 经它写入）",
            insertFn.contains("SourceQueryCache.invalidate()")
        )
        assertTrue(
            "RuleUpdate 仍经 SourceHelp.insertBookSource 写入（否则 ⑤ 脱离覆盖）",
            code("model/RuleUpdate.kt").contains("SourceHelp.insertBookSource(")
        )
    }

    /** 开关关闭 ⇒ 直接回库（行为与改造前完全一致）；开关是本地技术开关（同 optimizeRender 口径）。 */
    @Test
    fun switchOff_fallsBackToDirectQuery() {
        val cache = code("help/source/SourceQueryCache.kt")
        assertTrue("必须有开关判定", cache.contains("AppConfig.sourceQueryCacheEnabled"))
        assertTrue("关闭分支必须直接回库（不进缓存）", cache.contains("return loader()"))
        assertTrue(
            "默认必须为开（getPrefBoolean(..., true)）",
            code("help/config/AppConfig.kt")
                .contains("getPrefBoolean(PreferKey.sourceQueryCacheEnabled, true)")
        )
        assertTrue(
            "键登记：sourceQueryCacheEnabled",
            code("constant/PreferKey.kt").contains("const val sourceQueryCacheEnabled = \"sourceQueryCacheEnabled\"")
        )
    }

    /** TTL 常量必须是「短时」量级（文档口径 2s）；放大到分钟级会掩盖写入口漏失。 */
    @Test
    fun ttlIsShort() {
        val cache = code("help/source/SourceQueryCache.kt")
        assertTrue("TTL 必须为 2s（口径见 KDoc）", cache.contains("const val TTL_MS = 2_000L"))
        assertEquals(
            "TTL 不得被改成分钟级",
            2_000L,
            SourceQueryCache.TTL_MS
        )
    }
}