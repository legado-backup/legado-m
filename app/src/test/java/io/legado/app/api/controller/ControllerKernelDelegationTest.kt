package io.legado.app.api.controller

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File

/**
 * Web 门面「已下沉」结构断言（一期 · 2.1.6 / 2.2.4 / 2.3.1 / 2.3.2）。
 *
 * 锁两件事（下沉的全部价值就在这两条上）：
 * 1. **门面不再直访 DAO**（`appDb.` / `Dao.` 命中 0）—— 业务逻辑归 `service/kernel/`；
 * 2. **门面确实委派对应 Kernel**（防止有人为图省事把逻辑又内联回 Controller，
 *    那会让二期 MCP 只能复制实现 —— 正是本期要消灭的状态）。
 *
 * 为什么用源码扫描：`appDb` 依赖 Room + Context，纯 JVM 构造不出（本仓既有范式）。
 * 行为级验证见 `BookKernelTest`（纯逻辑）与 `KernelSweepTest`（全内核不变量）。
 */
class ControllerKernelDelegationTest {

    /** 门面 → 其必须委派的内核。 */
    private val pairs = listOf(
        "BookController.kt" to "BookKernel.",
        "BookSourceController.kt" to "BookSourceKernel.",
        "RssSourceController.kt" to "RssSourceKernel.",
        "ReplaceRuleController.kt" to "ReplaceRuleKernel.",
    )

    /** 剥整行注释后再断言（类注释里本就要写 `appDb.` / `Dao.` 作说明）。 */
    private fun code(name: String): String {
        val rel = "src/main/java/io/legado/app/api/controller/$name"
        val file = listOf(File(rel), File("../app/$rel"), File("app/$rel"))
            .firstOrNull { it.isFile }
            ?: throw AssertionError("未找到源文件（工作目录=${File(".").absolutePath}）：$rel")
        return file.readLines()
            .filterNot { it.trimStart().startsWith("//") || it.trimStart().startsWith("*") }
            .joinToString("\n")
    }

    @Test
    fun everyController_delegatesToItsKernel() {
        pairs.forEach { (file, kernelRef) ->
            assertTrue(
                "$file 必须委派 $kernelRef（否则业务逻辑又回流到 Web 层）",
                code(file).contains(kernelRef),
            )
        }
    }

    @Test
    fun noControllerTouchesDatabaseDirectly() {
        pairs.forEach { (file, _) ->
            val src = code(file)
            assertFalse("$file 不得直访 appDb（下沉判据 §2.1.6）", src.contains("appDb."))
            assertFalse("$file 不得出现 Dao 调用", src.contains("Dao."))
        }
    }
}
