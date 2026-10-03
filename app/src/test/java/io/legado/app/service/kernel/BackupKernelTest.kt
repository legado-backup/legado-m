package io.legado.app.service.kernel

import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 一期 §2.3.3 / §2.3.4：`BackupKernel` 的结构不变量（**源码文本断言**）。
 *
 * 为何用源码不变量：备份链路依赖 `appCtx` / Room / 文件系统，纯 JVM 无法驱动；而本批的四条改动
 * （返回 File / 超时可取消 / 模型 `@Keep` / 临时包唯一命名）**编译期完全无感**，漏改即静默失灵
 * （尤其 `@Keep`：release 包字段被 R8 改名后，网页端备份预览会整页读不到字段）。
 */
class BackupKernelTest {

    private fun read(rel: String): String =
        listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
            .readText()
            .replace("\r\n", "\n")

    /** 剥整行注释后再断言（KDoc 里本就要写 `ReturnData` / `NanoHTTPD` 等字样作说明）。 */
    private val kernel by lazy {
        read("src/main/java/io/legado/app/service/kernel/BackupKernel.kt")
            .lines()
            .filterNot { it.trimStart().startsWith("//") || it.trimStart().startsWith("*") }
            .joinToString("\n")
    }

    @Test
    fun gsonModelsAreKeptForReleaseBuilds() {
        // R8 × Gson 门禁（AGENTS 规则 7）：含 List<Model> 集合字段的序列化模型必须 @Keep
        assertTrue(
            "BackupOverview 必须 @Keep（含 List<BackupItemInfo> 集合字段）",
            Regex("""@Keep\s+data class BackupOverview""").containsMatchIn(kernel)
        )
        assertTrue(
            "BackupItemInfo 必须 @Keep（网页端按字段名读取）",
            Regex("""@Keep\s+data class BackupItemInfo""").containsMatchIn(kernel)
        )
    }

    @Test
    fun kernelDoesNotDependOnHttpOrEnvelope() {
        // 门禁 G-22 的单元级护栏：内核不得依赖 HTTP 响应与 API 信封
        assertFalse("内核不得依赖 ReturnData", kernel.contains("ReturnData"))
        assertFalse("内核不得依赖 web 包", kernel.contains("io.legado.app.web."))
        assertFalse("内核不得引入 runBlocking", kernel.contains("runBlocking"))
        assertFalse("内核不得依赖 NanoHTTPD", kernel.contains("NanoHTTPD"))
    }

    @Test
    fun timeoutIsCancellableAndKeepsOriginalBudget() {
        assertTrue("须由 withTimeout 限时", kernel.contains("withTimeout(BACKUP_TIMEOUT_MS)"))
        assertTrue(
            "超时数值须保持原 120s 语义",
            kernel.contains("const val BACKUP_TIMEOUT_MS = 120_000L")
        )
        assertFalse("不得回退到 CountDownLatch 门闩", kernel.contains("CountDownLatch"))
        assertFalse("不得保留孤儿协程写法", kernel.contains("CoroutineScope("))
    }

    @Test
    fun tempZipIsUniquelyNamedAndSweptBeforeCreation() {
        val sweepAt = kernel.indexOf("""name.startsWith("web_backup")""")
        val createAt = kernel.indexOf("""File(appCtx.externalFiles.absolutePath, "web_backup_${'$'}{System.currentTimeMillis()}""")
        assertTrue("临时包须按时间戳唯一命名（防并发导出互相覆盖）", createAt > 0)
        assertTrue("须清理历史残留临时包", sweepAt > 0)
        assertTrue(
            "清理必须发生在创建本次产物之前（否则会扫到自己）",
            sweepAt < createAt
        )
        assertFalse(
            "不得回退到固定文件名（并发导出会写坏正在被流式读取的文件）",
            kernel.contains("""web_backup_tmp.zip""")
        )
    }

    @Test
    fun previewNeverTriggersABackup() {
        val previewBody = kernel.substringAfter("suspend fun preview(): BackupOverview =")
            .substringBefore("\n\n")
        assertTrue("概览须优先复用缓存", previewBody.contains("cachedBackupOverview"))
        assertFalse(
            "概览不得触发落盘备份（否则点一下预览就产生一次全量备份）",
            previewBody.contains("withStorageLock")
        )
        assertFalse("概览不得调用打包", previewBody.contains("ZipUtils"))
    }

    @Test
    fun backupResultIsReturnedAsFileNotBytes() {
        assertTrue(
            "对外签名须返回 File（解耦 HTTP 响应，供 MCP 等通道复用）",
            kernel.contains("suspend fun backup(): File")
        )
        assertFalse(
            "不得再返回字节数组（大备份会把整包读进内存）",
            kernel.contains("suspend fun backup(): ByteArray")
        )
    }
}
