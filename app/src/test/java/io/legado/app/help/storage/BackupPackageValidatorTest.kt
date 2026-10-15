package io.legado.app.help.storage

import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File
import java.nio.file.Files

/**
 * core-flow-test-coverage 批次 5 —— 备份包完整性校验行为用例（G-01 配对 / G-42 行为断言）。
 *
 * 口径要点：**选择性备份合法**（只勾部分类别时，包内会缺其余条目，属正常）⇒ 必须放行；
 * 只有"一条已知条目都没有"或"明文 JSON 被写坏"才拦。
 *
 * ⚠️ 本轮两次修正均由此用例集守住（都属"自造误杀"）：
 *  ① 只勾「书源」等 JSON 类目（包内无 `bookshelf.json`）⇒ 曾因强判必需项被整体拒绝；
 *  ② 只勾**非 JSON** 类目（封面图集 / 背景图片 / 书籍缓存 / `config.xml`）⇒ 曾因"已知条目
 *     只统计 `.json`"而被判空包整体拒绝。
 */
class BackupPackageValidatorTest {

    private val roots = mutableListOf<File>()

    /** 模拟 `BackupSelectorConfig.allItems` 派生出的已知条目清单（含目录与 XML） */
    private val known = listOf(
        "bookshelf.json", "bookSource.json", "highlights.json", "servers.json",
        "config.xml", "bg", "book_cache"
    )

    private fun tempRoot(): File {
        val dir = Files.createTempDirectory("backup-validator").toFile()
        roots.add(dir)
        return dir
    }

    @After
    fun cleanup() {
        roots.forEach { runCatching { it.deleteRecursively() } }
        roots.clear()
    }

    @Test
    fun selectiveBackup_withoutBookshelf_passes() {
        // 用户「只备份书源」⇒ 包内没有 bookshelf.json，不得因此拒绝恢复
        val root = tempRoot()
        File(root, "bookSource.json").writeText("""[{"bookSourceName":"源A"}]""")

        val report = BackupPackageValidator.validate(root, known)

        assertTrue("选择性备份必须放行", report.ok)
        assertEquals(listOf("bookSource.json"), report.present)
        assertEquals(emptyList<String>(), report.malformed)
    }

    @Test
    fun nonJsonOnlyBackup_passes() {
        // 用户只勾非 JSON 类目（配置 XML + 背景图片目录）⇒ 包内无任何 .json，不得判空包
        val root = tempRoot()
        File(root, "config.xml").writeText("<map/>")
        File(root, "bg").mkdirs()

        val report = BackupPackageValidator.validate(root, known)

        assertTrue("仅非 JSON 类目的选择性备份必须放行", report.ok)
        assertEquals(listOf("config.xml", "bg"), report.present)
        assertEquals(emptyList<String>(), report.malformed)
    }

    @Test
    fun directoryOnlyBackup_passes() {
        // 仅书籍缓存目录：目录条目不得被当 JSON 解析（强判会抛异常并误判损坏）
        val root = tempRoot()
        File(root, "book_cache").mkdirs()

        val report = BackupPackageValidator.validate(root, known)

        assertTrue(report.ok)
        assertEquals(listOf("book_cache"), report.present)
        assertEquals(emptyList<String>(), report.malformed)
    }

    @Test
    fun emptyPackage_isRejected() {
        val root = tempRoot()

        val report = BackupPackageValidator.validate(root, known)

        assertFalse(report.ok)
        assertEquals(emptyList<String>(), report.present)
        assertTrue(report.describe().contains("不含任何已知数据文件"))
    }

    @Test
    fun validJsonEntries_pass() {
        val root = tempRoot()
        File(root, "bookshelf.json").writeText("""[{"name":"书A"}]""")
        File(root, "servers.json").writeText("""{"items":[]}""")

        val report = BackupPackageValidator.validate(root, known)

        assertTrue(report.ok)
        assertEquals(listOf("bookshelf.json", "servers.json"), report.present)
    }

    @Test
    fun truncatedPlainJson_isReportedAsMalformed() {
        val root = tempRoot()
        // 截断的半写内容：以 `[` 开头（疑似明文 JSON）但解析失败 ⇒ 必须拦下
        File(root, "bookshelf.json").writeText("[{\"name\":")

        val report = BackupPackageValidator.validate(root, known)

        assertFalse(report.ok)
        assertEquals(listOf("bookshelf.json"), report.malformed)
        assertTrue(report.describe().contains("损坏"))
    }

    @Test
    fun encryptedEntry_isNotTreatedAsMalformed() {
        // 备份里的加密条目（不以 `[`/`{` 开头）不参与解析判定 ⇒ 不得误杀合法包
        val root = tempRoot()
        File(root, "servers.json").writeText("3f9a1c7e5b2d8046a1f3c9e7b5d2046a")

        val report = BackupPackageValidator.validate(root, known)

        assertTrue(report.ok)
        assertEquals(listOf("servers.json"), report.present)
        assertEquals(emptyList<String>(), report.malformed)
    }
}
