package io.legado.app.help.web

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File

/**
 * 控制台**按需分发安装器**回归（web-mcp-productization 四期 · tasks 1.3/1.4 / REQ-4-103~109）。
 *
 * 为什么用源码扫描而不是直调 [ConsoleInstaller]：它依赖 `appCtx.filesDir` / [io.legado.app.web.FileWeb] /
 * OkHttp，纯 JVM 单测构造不出 Android 环境（与 `FileWebTest` / `Phase3RouteEnvelopeTest` 同口径）。
 *
 * 锁死的都是**安全红线**（回归即必须失败）：
 * 1. 私钥材料**不存在**于移动端（只持公钥）；
 * 2. Ed25519 不可用时**拒绝安装**（不得静默跳过验签）；
 * 3. 解压**逐条目**路径穿越校验（拒 `..` / 绝对路径 / 盘符 / NUL）；
 * 4. 安装落点与 [io.legado.app.web.FileWeb] **同源**（防"装了包但静态源读不到"）；
 * 5. 原子切换以 `renameTo` 完成（不是 copy ⇒ 不产生半包窗口）。
 */
class ConsoleInstallerTest {

    @Test
    fun channel_and_state_enums_areStable() {
        assertEquals(
            listOf("RELAY", "GITHUB", "NONE"),
            ConsoleInstaller.Channel.entries.map { it.name },
        )
        assertEquals(
            listOf("NOT_INSTALLED", "INSTALLING", "INSTALLED", "FAILED"),
            ConsoleInstaller.State.entries.map { it.name },
        )
    }

    @Test
    fun installer_neverCarriesPrivateKeyMaterial() {
        val src = source()
        assertTrue(
            "验签必须使用 ConsoleKeys 的公钥常量",
            src.contains("ConsoleKeys.CONSOLE_PUBLIC_KEY_BASE64"),
        )
        assertFalse(
            "移动端安装器不得出现私钥材料（PRIVATE KEY）",
            src.contains("PRIVATE KEY"),
        )
    }

    @Test
    fun ed25519Unavailable_mustRefuseNotSkip() {
        val src = source()
        assertTrue(
            "平台无 Ed25519 时必须抛 VERIFY_UNSUPPORTED 拒绝安装（安全底线，不得降级放行）",
            src.contains("VERIFY_UNSUPPORTED"),
        )
        // 本地上传是唯一豁免验签的通道：验签调用只允许 `localBypass` 一个开关
        assertTrue("验签入口须显式区分本地上传豁免", src.contains("localBypass"))
    }

    /**
     * sha256 比对必须**仅在线通道生效**（本地上传豁免）。
     *
     * 根因（2026-09-29 L3 实测）：包内 `manifest.json` 无法携带"包含它自己的 zip 的哈希"（自引用不可实现）
     * ⇒ 若本地通道也比对，合规包会被判 `SHA_MISMATCH` 而**永远装不上**（本地上传是断网兜底通道，属 P0 可用性）。
     */
    @Test
    fun sha256Comparison_isGuardedByLocalBypass() {
        val src = source()
        assertTrue("必须存在 SHA_MISMATCH 拒绝分支（在线通道用）", src.contains("SHA_MISMATCH"))
        assertTrue(
            "sha256 比对必须包在 `!localBypass` 内（本地通道豁免，否则合规包装不上）",
            Regex("""if\s*\(!localBypass\)\s*\{\s*\n\s*val actualSha""").containsMatchIn(src),
        )
        assertTrue(
            "包内 manifest 的 sha256 字段须可缺省（默认空串）",
            src.contains("val sha256: String = \"\""),
        )
    }

    @Test
    fun unzip_rejectsPathTraversalPerEntry() {
        val src = source()
        assertTrue("非法条目必须报 ENTRY_UNSAFE", src.contains("ENTRY_UNSAFE"))
        assertTrue("逐条目拒绝 `..`", src.contains("\"..\""))
        assertTrue("须做 canonicalPath 前缀校验（防 symlink/规范化绕过）", src.contains("canonicalPath"))
    }

    @Test
    fun installTarget_sharesFileWebConsoleDir() {
        val src = source()
        assertTrue(
            "安装落点必须复用 FileWeb.consoleDir（同源，避免装完静态源读不到）",
            src.contains("FileWeb.consoleDir"),
        )
    }

    @Test
    fun atomicInstall_usesRenameAndKeepsPrevious() {
        val src = source()
        assertTrue("原子切换必须用 renameTo", src.contains(".renameTo("))
        assertTrue("必须保留上一版目录以支持回退", src.contains("previousDir"))
        assertTrue("失败必须能回滚（rollback 端点依赖）", src.contains("fun rollback("))
    }

    private fun source(): String {
        val rel = "src/main/java/io/legado/app/help/web/ConsoleInstaller.kt"
        val file = listOf(File(rel), File("../app/$rel"), File("app/$rel")).firstOrNull { it.isFile }
            ?: throw AssertionError("未找到源文件（工作目录=${File(".").absolutePath}）：$rel")
        return file.readLines()
            .filterNot { it.trimStart().startsWith("//") || it.trimStart().startsWith("*") }
            .joinToString("\n")
    }
}