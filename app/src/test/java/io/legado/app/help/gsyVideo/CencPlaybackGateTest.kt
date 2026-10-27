package io.legado.app.help.gsyVideo

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * CENC 播放门禁纯函数单测（AD-01/AD-07）
 *
 * 锁定两条铁律：
 * 1. 网络地址 + 合法 kid + cenc-aes-ctr ⇒ 激活（真机源的播放地址可能被 302 改写，不能做 URL 全等比较）
 * 2. 本地明文降级文件（file://）⇒ 绝不激活（否则明文会被当加密轨解析，真机曾抛 AIOOBE）
 */
class CencPlaybackGateTest {

    private val kid = "0123456789abcdef0123456789abcdef"

    @Test
    fun activatesForNetworkCenc() {
        assertTrue(isCencPlaybackActive("https://v.example/a.mp4", kid, "cenc-aes-ctr"))
        assertTrue(isCencPlaybackActive("http://v.example/a.mp4", kid.uppercase(), " CENC-AES-CTR "))
    }

    @Test
    fun inactiveForLocalDecryptedFile() {
        assertFalse(isCencPlaybackActive("file:///data/user/0/app/cache/cenc/x.mp4", kid, "cenc-aes-ctr"))
        assertFalse(isCencPlaybackActive("/data/local/x.mp4", kid, "cenc-aes-ctr"))
    }

    @Test
    fun inactiveWithoutValidDeclaration() {
        assertFalse(isCencPlaybackActive("https://v.example/a.mp4", null, "cenc-aes-ctr"))
        assertFalse(isCencPlaybackActive("https://v.example/a.mp4", "bad-kid", "cenc-aes-ctr"))
        assertFalse(isCencPlaybackActive("https://v.example/a.mp4", kid, "aes-128"))
        assertFalse(isCencPlaybackActive("https://v.example/a.mp4", kid, null))
    }
}
