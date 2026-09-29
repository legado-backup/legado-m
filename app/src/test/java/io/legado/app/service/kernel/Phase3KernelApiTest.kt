package io.legado.app.service.kernel

import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File

/**
 * 三期 §1 对 Kernel 的**新增/补方法**回归锚点（web-mcp-productization 三期 · tasks §1）。
 *
 * 三期端点全部**复用二期内核**，少数缺口由本期在已有 Kernel 文件里补方法。补方法是"一期看不到、
 * 二期也没写"的**唯一新增业务代码**，最容易被后续重构静默删掉（删了不会编译错，只会让某个端点
 * 运行时抛 `NoSuchMethod`/返回错值）⇒ 用源码扫描把方法名钉住。
 *
 * 扫描方式与 `KernelSweepTest` 同口径（读源码 + 剥行注释），避免依赖 Room/Context（纯 JVM 构造不出）。
 */
class Phase3KernelApiTest {

    private val kernelDir = listOf(
        File("src/main/java/io/legado/app/service/kernel"),
        File("../app/src/main/java/io/legado/app/service/kernel"),
        File("app/src/main/java/io/legado/app/service/kernel"),
    ).firstOrNull { it.isDirectory }
        ?: throw AssertionError("未找到 service/kernel 目录")

    private fun code(fileName: String): String {
        val file = File(kernelDir, fileName)
        assertTrue("内核文件须存在：$fileName", file.isFile)
        return file.readLines()
            .filterNot { it.trimStart().startsWith("//") || it.trimStart().startsWith("*") }
            .joinToString("\n")
    }

    /** 三期补的 Kernel 方法（文件 → 方法名）。 */
    private val phase3KernelMethods = mapOf(
        "DiagReadKernel.kt" to listOf("recentAudit"),
        "TtsKernel.kt" to listOf("testTts"),
        "BookshelfKernel.kt" to listOf("searchBookshelf"),
        "AppSettingsKernel.kt" to listOf("appInfo"),
        "ContentKernel.kt" to listOf(
            "rssArticles", "rssArticleContent", "markRssRead", "readStats", "saveBookmark", "restoreBackup",
        ),
        "RssSourceKernel.kt" to listOf("markArticleRead"),
    )

    @Test
    fun phase3AddedKernelMethods_areStillPresent() {
        phase3KernelMethods.forEach { (fileName, methods) ->
            val src = code(fileName)
            methods.forEach { method ->
                assertTrue(
                    "$fileName 应保留三期补的方法 $method（三期端点依赖它；删除不会编译错但会运行期失效）",
                    Regex("""\bfun\s+$method\s*\(""").containsMatchIn(src),
                )
            }
        }
    }

    @Test
    fun phase3AddedKernelMethods_areSuspend() {
        phase3KernelMethods.forEach { (fileName, methods) ->
            val src = code(fileName)
            methods.forEach { method ->
                assertTrue(
                    "$fileName 的 $method 须是 suspend（内核契约：全链挂起）",
                    Regex("""suspend\s+fun\s+$method\s*\(""").containsMatchIn(src),
                )
            }
        }
    }
}