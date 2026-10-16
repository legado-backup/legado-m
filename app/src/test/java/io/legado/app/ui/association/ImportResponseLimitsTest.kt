package io.legado.app.ui.association

import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * 导入链路「legacy 全量缓冲助手」整族退役守护。
 *
 * 缺陷背景：`ImportResponseLimits.kt`（`MAX_LEGACY_IMPORT_BYTES` / `useLimitedImportStream` /
 * `readLimitedImportText`）是**旧导入路径**的「把整个响应体读进内存（4MB 上限）再整表反序列化」助手；
 * 现行导入路径已按 **REQ-05 / AD-13** 改为**增量解析**（`BookSourceIncrementalParser` 直接在流上解析，
 * 消除「原始字节 + 整表反序列化中间副本」双份常驻）⇒ 该助手**全仓零消费者**、被取代。
 *
 * 本类守护：①legacy 符号不得回流；②活替代（增量解析）必须在位 —— 否则「无上限缓冲」会重新变成唯一路径。
 */
class ImportResponseLimitsTest {

    private fun code(rel: String): String =
        listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
            .readText().replace("\r\n", "\n")

    private val main = "src/main/java/io/legado/app/ui/association/"

    private fun dirText(): String {
        val dir = listOf(File(main), File("../app/$main"), File("app/$main")).first { it.isDirectory }
        return dir.listFiles { f -> f.extension == "kt" }!!.joinToString("\n") { it.readText() }
    }

    @Test
    fun `legacy 全量缓冲导入助手已退役`() {
        val all = dirText()
        assertEquals("退役取值器不得回流", false, all.contains("fun ResponseBody.readLimitedImportText("))
        assertEquals("legacy 上限常量不得回流", false, all.contains("MAX_LEGACY_IMPORT_BYTES"))
    }

    @Test
    fun `增量解析为活替代且必须在位`() {
        val vm = code(main + "ImportBookSourceViewModel.kt")
        assertEquals("书源导入须走增量解析（活替代）", true, vm.contains("BookSourceIncrementalParser"))
    }
}
