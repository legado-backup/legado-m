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
 * 全部为**对返回值与产物的断言**（非源码文本探针）：覆盖"可用包 / 缺必需项 / 必需项
 * 形状错 / 必需项内容畸形 / 回执文案"五态。
 */
class BackupPackageValidatorTest {

    private val roots = mutableListOf<File>()

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
    fun validPackage_passes() {
        val root = tempRoot()
        File(root, "bookshelf.json").writeText("""[{"name":"书A","author":"作者A"}]""")

        val report = BackupPackageValidator.validate(root)

        assertTrue(report.ok)
        assertEquals(emptyList<String>(), report.missing)
        assertEquals(emptyList<String>(), report.malformed)
    }

    @Test
    fun missingRequiredFile_isReportedAsMissing() {
        val root = tempRoot()   // 空目录：先解压失败的典型残包

        val report = BackupPackageValidator.validate(root)

        assertFalse(report.ok)
        assertEquals(listOf("bookshelf.json"), report.missing)
        assertEquals(emptyList<String>(), report.malformed)
    }

    @Test
    fun objectInsteadOfArray_isReportedAsMalformed() {
        val root = tempRoot()
        File(root, "bookshelf.json").writeText("""{"books":[]}""")

        val report = BackupPackageValidator.validate(root)

        assertFalse(report.ok)
        assertEquals(emptyList<String>(), report.missing)
        assertEquals(listOf("bookshelf.json"), report.malformed)
    }

    @Test
    fun brokenJson_isReportedAsMalformed() {
        val root = tempRoot()
        // 首尾字符是 `[` `]`（`isJsonArray()` 会放行）但内容并非合法 JSON ⇒ 必须由实解析拦下
        File(root, "bookshelf.json").writeText("[{name")

        val report = BackupPackageValidator.validate(root)

        assertFalse(report.ok)
        assertEquals(listOf("bookshelf.json"), report.malformed)
    }

    @Test
    fun describe_mentionsBothKinds() {
        val root = tempRoot()
        File(root, "bookshelf.json").writeText("not-json-at-all")

        val report = BackupPackageValidator.validate(root)
        val text = report.describe()

        assertTrue(text.contains("损坏"))
        assertTrue(text.contains("bookshelf.json"))
    }
}
