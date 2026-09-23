package io.legado.app.ui.highlight

import io.legado.app.ui.book.read.config.HighlightRule
import io.legado.app.utils.compress.ZipUtils
import java.io.File
import java.util.zip.ZipEntry
import java.util.zip.ZipOutputStream
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * B6 · R27「高亮规则包导入导出」单测（纯文件，无 Android 依赖）。
 *
 * 验收口径（tasks §6.3）：
 * - **往返一致**（导出 → 导入结果与原文逐字段相等）；
 * - **四类失败均中止**：非法（格式/缺条目）、超限（复用 R21）、越界（ZipSlip）、校验失败（摘要/条数）；
 * - 且中止时**零写入**（校验链全部在 `commit` 之前完成 ⇒ 用「不共享状态」的方式断言：
 *   失败路径只抛异常、不返回可提交列表）。
 */
class HighlightRulePackTest {

    private val workDir: File = File(System.getProperty("java.io.tmpdir"), "hrulepack-${System.nanoTime()}")

    private fun rule(id: String, name: String = "规则$id") = HighlightRule(
        id = id,
        name = name,
        pattern = "回归样本$id",
        isRegex = true,
        styleJson = """{"fill":-123456}"""
    )

    private fun zipOf(entries: Map<String, ByteArray>): File {
        workDir.mkdirs()
        val file = File(workDir, "pack-${System.nanoTime()}.zip")
        ZipOutputStream(file.outputStream()).use { zip ->
            entries.forEach { (name, bytes) ->
                zip.putNextEntry(ZipEntry(name))
                zip.write(bytes)
                zip.closeEntry()
            }
        }
        return file
    }

    private fun packFile(rules: List<HighlightRule>): File {
        workDir.mkdirs()
        val file = File(workDir, "export-${System.nanoTime()}.zip")
        file.writeBytes(HighlightRulePack.exportRules(rules))
        return file
    }

    private fun importDir() = File(workDir, "work-${System.nanoTime()}")

    /** 往返一致：导出 → 导入，字段逐项相等。 */
    @Test
    fun roundTrip_preservesRules() {
        val rules = listOf(rule("a"), rule("b", "带样式的规则$"))
        val pack = packFile(rules)
        val imported = HighlightRulePack.importInto(pack, importDir())
        assertEquals("条数必须一致", rules.size, imported.size)
        assertEquals("内容必须逐字段一致", rules, imported)
    }

    /** R27+：包内规则可携带 R26 新字段（包路径是这些字段的合法分发通道）。 */
    @Test
    fun roundTrip_preservesFontOverrideFields() {
        val rules = listOf(
            HighlightRule(
                id = "font",
                name = "字号规则",
                pattern = "x",
                styleJson = """{"fill":0,"fontScale":1.05,"letterSpacingEm":0.05}"""
            )
        )
        val imported = HighlightRulePack.importInto(packFile(rules), importDir())
        assertEquals(rules, imported)
        val style = imported.first().toHighlightStyle()
        assertEquals(1.05f, style.fontScale!!, 0f)
        assertEquals(0.05f, style.letterSpacingEm!!, 0f)
    }

    /** 非法①：缺条目 ⇒ 中止。 */
    @Test(expected = HighlightRulePack.PackException::class)
    fun missingEntries_aborts() {
        val pack = zipOf(mapOf(HighlightRulePack.ENTRY_RULES to "[]".toByteArray()))
        HighlightRulePack.importInto(pack, importDir())
    }

    /** 非法②：格式不匹配 ⇒ 中止。 */
    @Test(expected = HighlightRulePack.PackException::class)
    fun wrongFormat_aborts() {
        val pack = zipOf(
            mapOf(
                HighlightRulePack.ENTRY_RULES to HighlightRulePack.rulesJson(listOf(rule("a"))).toByteArray(),
                HighlightRulePack.ENTRY_MANIFEST to """{"format":"other.format","version":1,"count":1}""".toByteArray()
            )
        )
        HighlightRulePack.importInto(pack, importDir())
    }

    /** 非法③：版本不受支持（未来版本）⇒ 中止（防新字段被旧版静默丢弃）。 */
    @Test(expected = HighlightRulePack.PackException::class)
    fun futureVersion_aborts() {
        val payload = HighlightRulePack.rulesJson(listOf(rule("a"))).toByteArray()
        val pack = zipOf(
            mapOf(
                HighlightRulePack.ENTRY_RULES to payload,
                HighlightRulePack.ENTRY_MANIFEST to """{"format":"${HighlightRulePack.FORMAT}","version":${HighlightRulePack.VERSION + 1},"count":1}""".toByteArray()
            )
        )
        HighlightRulePack.importInto(pack, importDir())
    }

    /** 校验失败①：摘要不符（内容被改）⇒ 中止。 */
    @Test(expected = HighlightRulePack.PackException::class)
    fun digestMismatch_aborts() {
        val pack = zipOf(
            mapOf(
                HighlightRulePack.ENTRY_RULES to HighlightRulePack.rulesJson(listOf(rule("a"))).toByteArray(),
                HighlightRulePack.ENTRY_MANIFEST to """{"format":"${HighlightRulePack.FORMAT}","version":1,"count":1,"sha256":"deadbeef"}""".toByteArray()
            )
        )
        HighlightRulePack.importInto(pack, importDir())
    }

    /** 校验失败②：条数与清单不符 ⇒ 中止。 */
    @Test(expected = HighlightRulePack.PackException::class)
    fun countMismatch_aborts() {
        val payload = HighlightRulePack.rulesJson(listOf(rule("a"))).toByteArray()
        val sha = io.legado.app.utils.Utf8Sha256.hex(payload)
        val pack = zipOf(
            mapOf(
                HighlightRulePack.ENTRY_RULES to payload,
                HighlightRulePack.ENTRY_MANIFEST to """{"format":"${HighlightRulePack.FORMAT}","version":1,"count":9,"sha256":"$sha"}""".toByteArray()
            )
        )
        HighlightRulePack.importInto(pack, importDir())
    }

    /** 越界（ZipSlip）：复用 R21 防护 ⇒ SecurityException。 */
    @Test(expected = SecurityException::class)
    fun zipSlip_aborts() {
        val pack = zipOf(mapOf("../evil.json" to "{}".toByteArray()))
        HighlightRulePack.importInto(pack, importDir())
    }

    /** 超限：复用 R21 阈值（测试传更严档）⇒ 中止。 */
    @Test(expected = SecurityException::class)
    fun oversizedEntry_aborts() {
        val pack = zipOf(mapOf(HighlightRulePack.ENTRY_RULES to ByteArray(8 * 1024)))
        HighlightRulePack.importInto(
            pack,
            importDir(),
            limits = ZipUtils.UnzipLimits(maxEntryBytes = 1024)
        )
    }

    /** 失败路径必须**不留工作目录**（解压中间产物不得残留在缓存目录）。 */
    @Test
    fun failedImport_leavesNoWorkDir() {
        val dir = importDir()
        val pack = zipOf(mapOf(HighlightRulePack.ENTRY_RULES to "not-json".toByteArray()))
        runCatching { HighlightRulePack.importInto(pack, dir) }
        assertTrue("失败后工作目录必须被清理", !dir.exists())
    }

    /** 零写入保证（结构）：`commit` 是唯一写入口，且校验链在 `readFromDir` 内完成。 */
    @Test
    fun zeroWriteOnFailure_isStructural() {
        val source = File("src/main/java/io/legado/app/ui/highlight/HighlightRulePack.kt").let {
            val f = listOf(it, File("../app/${it.path}"), File("app/${it.path}")).first { f -> f.isFile }
            f.readText()
        }
        assertTrue("存储写入必须集中在 commit()", source.contains("fun commit(context: Context, incoming: List<HighlightRule>)"))
        assertTrue("commit 内不得做解压/解析", !source.substringAfter("fun commit(").substringBefore("fun exportToFile(").contains("unZipToPath"))
        assertTrue("导入必须复用 R21 出口", source.contains("ZipUtils.unZipToPath(zip, workDir, limits = limits)"))
    }
}