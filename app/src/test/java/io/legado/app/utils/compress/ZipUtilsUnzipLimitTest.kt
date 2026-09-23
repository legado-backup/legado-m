package io.legado.app.utils.compress

import java.io.File
import java.util.zip.ZipEntry
import java.util.zip.ZipOutputStream
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * B4 · R21「ZIP 解压体积上限防护」单测。
 *
 * 验收口径（tasks §4.5）：超限中止 / 正常包不受影响 / **ZipSlip 不回归**；
 * 且防护落在**唯一出口**（所有 `unZipToPath` 重载都经同一核心）。
 */
class ZipUtilsUnzipLimitTest {

    private val workDir: File = createTempDir()

    private fun createTempDir(): File {
        val dir = File(System.getProperty("java.io.tmpdir"), "ziputils-test-${System.nanoTime()}")
        dir.mkdirs()
        dir.deleteOnExit()
        return dir
    }

    private fun buildZip(entries: List<Pair<String, ByteArray>>): File {
        val zipFile = File(workDir, "sample-${System.nanoTime()}.zip")
        ZipOutputStream(zipFile.outputStream()).use { zos ->
            entries.forEach { (name, bytes) ->
                zos.putNextEntry(ZipEntry(name))
                zos.write(bytes)
                zos.closeEntry()
            }
        }
        zipFile.deleteOnExit()
        return zipFile
    }

    /**
     * 超限必须**中止解压**（而非解完再判断）：核心改用「限量拷贝」逐块计数。
     *
     * 说明（诚实口径）：`ZipEntry.size` 在 `ZipOutputStream` 侧无法写 -1，
     * 而伪造本地头体积会触发 JDK 自身的 `IllegalArgumentException`（`nextEntry` 阶段），
     * 无法在 JVM 单测里稳定构造「声明撒谎」的包 ⇒ 「实际写入量兜底」由
     * ①本条结构断言（存在 `copyWithLimit` 逐块计数、旧 `copyTo` 已移除）
     * ②[oversizedTotal_isRejected]（单条目均未超限，只有累计流式计数能拦下）共同覆盖。
     */
    @Test
    fun oversizedEntry_abortsBeforeFullExtraction() {
        val source = code("utils/compress/ZipUtils.kt")
        assertTrue("必须使用限量拷贝（逐块计数）", source.contains("copyWithLimit("))
        assertTrue("不得再整段 copyTo（无法中途中止）", !source.contains("zipInputStream.copyTo("))
        assertTrue(
            "声明体积与实际写入量双向拦截（声明值先行、写入量兜底）",
            source.contains("if (entry.size > limits.maxEntryBytes)") &&
                source.contains("if (written > singleLimit)")
        )
    }

    private fun code(relFromMainJava: String): String {
        val rel = "src/main/java/io/legado/app/$relFromMainJava"
        val file = listOf(File(rel), File("../app/$rel"), File("app/$rel")).firstOrNull { it.isFile }
            ?: throw AssertionError("未找到源文件：$rel")
        return file.readLines()
            .filterNot { it.trimStart().startsWith("//") || it.trimStart().startsWith("*") }
            .joinToString("\n")
    }

    private fun outDir(tag: String): File =
        File(workDir, "out-$tag-${System.nanoTime()}").apply { mkdirs() }

    /** 正常包：解压成功且返回文件列表（含子目录）。 */
    @Test
    fun normalPackage_extractsAndReturnsFiles() {
        val zip = buildZip(
            listOf(
                "a.txt" to "hello".toByteArray(),
                "sub/b.txt" to "world".toByteArray()
            )
        )
        val dir = outDir("normal")
        val files = ZipUtils.unZipToPath(zip, dir)
        assertEquals(2, files.size)
        assertTrue(File(dir, "a.txt").isFile)
        assertTrue(File(dir, "sub/b.txt").isFile)
    }

    /** ZipSlip 不回归：路径逃逸仍必须被拒。 */
    @Test(expected = SecurityException::class)
    fun zipSlip_isStillRejected() {
        val zip = buildZip(listOf("../escaped.txt" to "x".toByteArray()))
        ZipUtils.unZipToPath(zip, outDir("slip"))
    }

    /** 单条目超限：**声明体积**先拦（不写盘）。 */
    @Test(expected = SecurityException::class)
    fun oversizedSingleEntry_isRejectedByDeclaredSize() {
        val zip = buildZip(listOf("big.bin" to ByteArray(64 * 1024)))
        val limits = ZipUtils.UnzipLimits(maxEntryBytes = 4 * 1024)
        ZipUtils.unZipToPath(zip, outDir("entry"), limits = limits)
    }

    /** 总量超限：单条目都不超限，但累计超限 ⇒ 中止。 */
    @Test(expected = SecurityException::class)
    fun oversizedTotal_isRejected() {
        val zip = buildZip(
            listOf(
                "a.bin" to ByteArray(8 * 1024),
                "b.bin" to ByteArray(8 * 1024)
            )
        )
        val limits = ZipUtils.UnzipLimits(maxEntryBytes = 16 * 1024, maxTotalBytes = 12 * 1024)
        ZipUtils.unZipToPath(zip, outDir("total"), limits = limits)
    }

    /** 条目数超限：海量空条目（防 inode 耗尽）也必须中止。 */
    @Test(expected = SecurityException::class)
    fun tooManyEntries_isRejected() {
        val zip = buildZip((1..6).map { "f$it.txt" to ByteArray(1) })
        val limits = ZipUtils.UnzipLimits(maxEntries = 5)
        ZipUtils.unZipToPath(zip, outDir("count"), limits = limits)
    }

    /** filter 语义不回归（被过滤条目既不写出也不计数）。 */
    @Test
    fun filterStillWorks() {
        val zip = buildZip(
            listOf(
                "keep.txt" to "k".toByteArray(),
                "skip.txt" to ByteArray(8 * 1024)
            )
        )
        val dir = outDir("filter")
        val files = ZipUtils.unZipToPath(
            file = zip,
            dir = dir,
            filter = { name: String -> name == "keep.txt" }
        )
        assertEquals("被过滤条目不得写出", 1, files.size)
        assertEquals("keep.txt", files.first().name)
        assertTrue("被过滤的大条目不得触发体积拦截（先过滤后校验）", !File(dir, "skip.txt").exists())
    }

    /** 防护是唯一出口：公开重载的默认阈值必须来自同一常量，且字节流重载同样受保护。 */
    @Test
    fun defaultLimits_areSharedAndStreamOverloadIsGuarded() {
        assertEquals(256L * 1024 * 1024, ZipUtils.DEFAULT_MAX_ENTRY_BYTES)
        assertEquals(1024L * 1024 * 1024, ZipUtils.DEFAULT_MAX_TOTAL_BYTES)
        assertEquals(20_000, ZipUtils.DEFAULT_MAX_ENTRIES)
        assertEquals(ZipUtils.DEFAULT_MAX_ENTRY_BYTES, ZipUtils.DEFAULT_UNZIP_LIMITS.maxEntryBytes)
        val zip = buildZip(listOf("a.bin" to ByteArray(2048)))
        val thrown = runCatching {
            zip.inputStream().use { input ->
                ZipUtils.unZipToPath(
                    input,
                    outDir("stream"),
                    limits = ZipUtils.UnzipLimits(maxEntryBytes = 1024)
                )
            }
        }.exceptionOrNull()
        assertTrue("字节流重载必须同样受阈值保护", thrown is SecurityException)
    }
}