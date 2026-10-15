package io.legado.app.utils.compress

import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Test

/** B21：`ZipUtils.createOrExistsFile` 通用工具残留退役守护。 */
class ZipUtilsRetiredHelperTest {

    private fun code(rel: String): String =
        listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
            .readText().replace("\r\n", "\n")

    @Test
    fun `零调用文件创建助手已退役`() {
        val src = code("src/main/java/io/legado/app/utils/compress/ZipUtils.kt")
        assertEquals("零调用工具残留应退役", false, src.contains("fun createOrExistsFile("))
        assertEquals("其唯一下游 createOrExistsDir 应随级联退役", false, src.contains("fun createOrExistsDir("))
        assertEquals("活实现 unzip 相关入口必须保留", true, src.contains("fun unZipToPath("))
    }
}
