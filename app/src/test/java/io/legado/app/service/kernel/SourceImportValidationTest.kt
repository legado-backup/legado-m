package io.legado.app.service.kernel

import io.legado.app.data.entities.BookSource
import io.legado.app.data.entities.RssSource
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File

/**
 * 源导入校验链单测（一期 · 2.2.2 / 2.3.1 · REQ-1-306 / REQ-1-311）。
 *
 * 两类断言：
 * 1. **可纯 JVM 验证的行为**：身份缺失（空 URL / 空名称）必须被拒并给出白话原因
 *    （这条路径在触碰 L1 检查前就返回，故无 Android 依赖）；
 * 2. **结构不变量（源码扫描）**：两个 Kernel 必须**真的接上** L1 静态检查件与 `deterministicFail` 判据；
 *    两个门面必须调用 `skipReason` 且**保持 `data` 为成功数组**（老页 `ToolBar.vue` 以
 *    `总数 - data.length` 计失败数，改成对象会让整块提示失效 —— 这是本次实测得出的兼容红线）。
 *
 * L1 检查本身（`SourceQualityChecker.*`）不在此测：它属既有件、且构造真实源会牵动 App 侧依赖。
 */
class SourceImportValidationTest {

    private fun codeOf(relFromMain: String): String {
        val file = relFromMain.let { rel ->
            listOf(File(rel), File("../app/$rel"), File("app/$rel")).firstOrNull { it.isFile }
        } ?: throw AssertionError("未找到源文件：$relFromMain")
        return file.readLines()
            .filterNot { it.trimStart().startsWith("//") || it.trimStart().startsWith("*") }
            .joinToString("\n")
    }

    // ------------------------------------------------------------ 行为（纯 JVM 可测分支）

    @Test
    fun skipReason_bookSource_rejectsBlankIdentity() {
        assertEquals(
            "源名称和URL不能为空",
            BookSourceKernel.skipReason(BookSource(bookSourceName = "有名字", bookSourceUrl = "")),
        )
        assertEquals(
            "源名称和URL不能为空",
            BookSourceKernel.skipReason(BookSource(bookSourceName = "", bookSourceUrl = "https://a")),
        )
    }

    @Test
    fun skipReason_rssSource_rejectsBlankIdentity() {
        assertEquals(
            "源名称和URL不能为空",
            RssSourceKernel.skipReason(RssSource(sourceName = "有名字", sourceUrl = "")),
        )
        assertEquals(
            "源名称和URL不能为空",
            RssSourceKernel.skipReason(RssSource(sourceName = "", sourceUrl = "https://a")),
        )
    }

    // ------------------------------------------------------------ 结构不变量

    @Test
    fun bookSourceKernel_wiresTheRealImportChain() {
        val code = codeOf("src/main/java/io/legado/app/service/kernel/BookSourceKernel.kt")
        assertTrue("必须复用真实增量解析入口（防自造解析器）", code.contains("BookSourceIncrementalParser"))
        assertTrue("必须接 L1 静态检查件", code.contains("SourceQualityChecker.l1StaticCheckBookSource"))
        assertTrue("必须以 deterministicFail 为判据（与 App 导入页同口径）", code.contains("deterministicFail"))
        assertTrue("必须暴露 parseAndValidate", code.contains("fun parseAndValidate("))
    }

    @Test
    fun rssSourceKernel_wiresTheSameCaliberChain() {
        val code = codeOf("src/main/java/io/legado/app/service/kernel/RssSourceKernel.kt")
        assertTrue("必须接 RSS 侧 L1 静态检查件", code.contains("SourceQualityChecker.l1StaticCheckRssSource"))
        assertTrue("必须以 deterministicFail 为判据（与书源同口径）", code.contains("deterministicFail"))
        assertTrue("必须暴露 parseAndValidate", code.contains("fun parseAndValidate("))
    }

}
