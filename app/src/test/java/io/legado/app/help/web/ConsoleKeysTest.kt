package io.legado.app.help.web

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import java.util.Base64

/**
 * 控制台包验签公钥常量回归（web-mcp-productization 四期 · tasks 0.3.1 / REQ-4-111）。
 *
 * 锁三件事：
 * 1. **公钥形态**：raw 32 字节的 Base64（Ed25519 公钥长度固定 32B）—— 形态错会让验签永远失败；
 * 2. **不是私钥**：常量里**绝不能**出现 PEM 私钥头（防"为了省事把私钥贴进来"这类事故）；
 * 3. **签名后缀稳定**：发布侧签名脚本与 App 侧取签名的文件名约定必须一致。
 */
class ConsoleKeysTest {

    @Test
    fun publicKey_isRawEd25519Base64() {
        val raw = Base64.getDecoder().decode(ConsoleKeys.CONSOLE_PUBLIC_KEY_BASE64)
        assertEquals("Ed25519 公钥必须是 raw 32 字节", 32, raw.size)
    }

    @Test
    fun publicKeyFile_containsNoPrivateKeyMarker() {
        // 防自伤：本测试**不写出**私钥 PEM 头的完整字面量，改用拼接（否则本文件自身会被扫描命中）
        val marker = "BEGIN " + "PRIVATE KEY"
        val content = ConsoleKeys.CONSOLE_PUBLIC_KEY_BASE64
        assertFalse("公钥常量里不得出现私钥标记", content.contains(marker))
    }

    @Test
    fun signatureSuffix_isStable() {
        assertEquals(".sig", ConsoleKeys.SIGNATURE_SUFFIX)
        assertTrue("签名后缀应以点开头", ConsoleKeys.SIGNATURE_SUFFIX.startsWith("."))
    }
}