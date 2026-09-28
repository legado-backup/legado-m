package io.legado.app.service.kernel

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File

/**
 * 内核层**架构不变量**扫描（一期 · 2.4 / REQ-1-202 · REQ-1-203）。
 *
 * 逐文件扫描 `service/kernel/`，锁住四条契约（design §1.3.1 / §1.4.3）：
 * 1. **零 `runBlocking`** —— Kernel 必须全链挂起（REQ-1-202）；
 * 2. **不依赖上层** —— 不得 import `api.controller` / `web`（依赖方向：上层 → Kernel 单向，§2.4.1）；
 * 3. **不返回 HTTP 信封** —— 不得出现 `ReturnData`（否则二期 MCP 被 HTTP 语义污染，REQ-1-203）；
 * 4. **对外 API 挂起化** —— 每个 Kernel 至少暴露一个 `suspend fun`。
 *
 * 为什么用源码扫描：`appDb` 依赖 Room + Context，纯 JVM 构造不出（本仓既有范式即如此）。
 */
class KernelSweepTest {

    private val kernelDir = listOf(
        File("src/main/java/io/legado/app/service/kernel"),
        File("../app/src/main/java/io/legado/app/service/kernel"),
        File("app/src/main/java/io/legado/app/service/kernel"),
    ).firstOrNull { it.isDirectory }
        ?: throw AssertionError("未找到 service/kernel 目录（工作目录=${File(".").absolutePath}）")

    /** 已落地内核文件（2.3.3 BackupKernel 落地后须把 "BackupKernel.kt" 补入 —— 一期目标为 5 个）。 */
    private val expectedKernels = setOf(
        "BookKernel.kt",
        "BookSourceKernel.kt",
        "RssSourceKernel.kt",
        "ReplaceRuleKernel.kt",
    )

    private fun kernelFiles(): List<File> =
        kernelDir.listFiles { f -> f.isFile && f.name.endsWith(".kt") }?.sortedBy { it.name } ?: emptyList()

    /** 剥整行注释后再断言（KDoc 里本就要写 `runBlocking` / `ReturnData` 等字样作说明）。 */
    private fun code(file: File): String = file.readLines()
        .filterNot { it.trimStart().startsWith("//") || it.trimStart().startsWith("*") }
        .joinToString("\n")

    @Test
    fun kernelSet_matchesLandedScope() {
        assertEquals(
            "已落地内核集合不得被静默增删（新增内核须同步本清单与门禁）",
            expectedKernels,
            kernelFiles().map { it.name }.toSet(),
        )
    }

    @Test
    fun everyKernel_hasZeroRunBlocking() {
        kernelFiles().forEach { file ->
            assertTrue(
                "${file.name} 不得出现 runBlocking（REQ-1-202：Kernel 全链挂起）",
                !code(file).contains("runBlocking"),
            )
        }
    }

    @Test
    fun everyKernel_doesNotDependOnUpperLayers() {
        kernelFiles().forEach { file ->
            val src = code(file)
            assertTrue(
                "${file.name} 不得 import api.controller（依赖方向门禁 §2.4.1）",
                !src.contains("io.legado.app.api.controller"),
            )
            assertTrue("${file.name} 不得依赖 web 层", !src.contains("io.legado.app.web"))
        }
    }

    @Test
    fun everyKernel_doesNotReturnHttpEnvelope() {
        kernelFiles().forEach { file ->
            assertTrue(
                "${file.name} 不得出现 ReturnData（Kernel 只返回领域对象，REQ-1-203）",
                !code(file).contains("ReturnData"),
            )
        }
    }

    @Test
    fun everyKernel_exposesSuspendApi() {
        kernelFiles().forEach { file ->
            assertTrue("${file.name} 须暴露 suspend 方法", code(file).contains("suspend fun"))
        }
    }
}
