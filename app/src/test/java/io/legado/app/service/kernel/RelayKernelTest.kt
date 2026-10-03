package io.legado.app.service.kernel

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File

/**
 * 公网中继内核回归（web-mcp-productization 四期 · tasks 2.1「S7 一键断电」）。
 *
 * 源码扫描口径（同 [KernelSweepTest]）：`RelayKernel` 依赖 `appCtx` / `RelayService` / `WebService`
 * 等 Android 侧单例，纯 JVM 单测无法真实执行 ⇒ 此处锁**结构性红线**，回归即必须失败：
 *
 * 1. **AD-10**：全链挂起、零 `runBlocking`、不 import `api.controller`（G-23 口径）；
 * 2. **断电链路完整**：令牌吊销 + Web 服务停止 + 中继吊销 + 本机秘密清理**四步齐备**（漏一步即"假断电"）；
 * 3. **顺序安全**：中继吊销必须排在 `RelaySecretStore` 清理**之前** —— 控制证明依赖身份秘钥，
 *    先清则秘钥不可逆丢失 ⇒ 远端吊销永久失败（安全红线，见类 KDoc 顺序说明）；
 * 4. **不误清待补标记**：设备级吊销端点未就绪时 `retryPendingRevoke` 必须**保留**标记，
 *    禁止出现"清位但没真吊销"的静默假成功。
 */
class RelayKernelTest {

    @Test
    fun kernel_isSuspendingAndAvoidsControllerAndRunBlocking() {
        // 注释剥除后再扫：类 KDoc 里就写着「零 `runBlocking`」，扫全文会把这句说明当成违规命中
        val code = source()
        assertTrue("断电主链必须是挂起函数", code.contains("suspend fun shutdown("))
        assertTrue("状态快照必须是挂起函数", code.contains("suspend fun status("))
        assertTrue("补吊销必须是挂起函数", code.contains("suspend fun retryPendingRevoke("))
        assertFalse("内核禁止 runBlocking（AD-10）", code.contains("runBlocking"))
        assertFalse(
            "内核禁止 import api.controller（G-23）",
            Regex("^\\s*import\\s+io\\.legado\\.app\\.web\\.api\\.controller", RegexOption.MULTILINE)
                .containsMatchIn(readSource()),
        )
    }

    @Test
    fun shutdown_coversLocalSteps() {
        val src = source()
        assertTrue("必须停止 Web 服务", src.contains("WebService.stop("))
        assertTrue("必须执行中继远端吊销", src.contains("revokeRelayRemote()"))
        assertTrue("必须清本机中继秘密", src.contains("RelaySecretStore"))
        assertFalse(
            "令牌吊销属上层（TokenManager 在 io.legado.app.web，Kernel 不得反向依赖）⇒ 内核内不得出现",
            src.contains("io.legado.app.web"),
        )
    }

    /**
     * 「一键断电」的令牌吊销由上层执行 ⇒ 必须与内核断电**同一入口**串行，禁止拆散（拆散即可能漏吊销）。
     *
     * 该断言的落点是设置页宿主：`revokeAll()` 必须出现在 `RelayKernel.shutdown()` 之前。
     */
    @Test
    fun upperLayer_revokesTokensBeforeKernelShutdown() {
        val host = listOf(
            File("src/main/java/io/legado/app/ui/config/WebServiceSettingsActivity.kt"),
            File("../app/src/main/java/io/legado/app/ui/config/WebServiceSettingsActivity.kt"),
            File("app/src/main/java/io/legado/app/ui/config/WebServiceSettingsActivity.kt"),
        ).firstOrNull { it.isFile }
            ?: throw AssertionError("未找到设置页宿主（工作目录=${File(".").absolutePath}）")
        val src = host.readText().lines()
            .filterNot { it.trimStart().startsWith("//") || it.trimStart().startsWith("*") }
            .joinToString("\n")
        val revokeAt = src.indexOf("TokenManager.revokeAll()")
        val shutdownAt = src.indexOf("RelayKernel.shutdown()")
        assertTrue("设置页必须调用令牌全量吊销", revokeAt >= 0)
        assertTrue("设置页必须调用内核断电", shutdownAt >= 0)
        assertTrue("令牌吊销必须排在断电之前（否则旧令牌仍可访问）", revokeAt < shutdownAt)
    }

    @Test
    fun relayRevokeMustRunBeforeSecretClear() {
        val src = source()
        val revokeAt = src.indexOf("revokeRelayRemote()")
        val clearAt = src.indexOf("steps[\"relaySecretsCleared\"]")
        assertTrue("回执里必须同时含中继吊销与秘密清理两项", revokeAt >= 0 && clearAt >= 0)
        assertTrue(
            "中继吊销必须排在 RelaySecretStore 清理之前（否则控制证明失效，远端永久吊不掉）",
            revokeAt < clearAt,
        )
    }

    @Test
    fun retryPendingRevoke_neverFalselyClearsFlag() {
        val src = source()
        assertFalse(
            "设备级端点未就绪时禁止把待补标记**写为 false**（假成功）",
            src.contains("putPrefBoolean(PreferKey.publicWebRelayRevokePending, false)"),
        )
        assertTrue(
            "补吊销必须回告 degraded（未真正完成设备级吊销）",
            src.contains("degraded") && src.contains("device_revoke_endpoint_unavailable"),
        )
    }

    private fun source(): String = readSource().lines()
        .filterNot { it.trimStart().startsWith("//") || it.trimStart().startsWith("*") }
        .joinToString("\n")

    private fun readSource(): String {
        val rel = "src/main/java/io/legado/app/service/kernel/RelayKernel.kt"
        val file = listOf(File(rel), File("../app/$rel"), File("app/$rel")).firstOrNull { it.isFile }
            ?: throw AssertionError("未找到源文件（工作目录=${File(".").absolutePath}）：$rel")
        return file.readText()
    }
}