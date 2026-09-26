package io.legado.app.help.http

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertEquals
import org.junit.Assert.assertSame
import org.junit.Assert.assertTrue
import org.junit.Test
import java.net.InetAddress

/**
 * R 批 §3.3.4：DNS 解析 **IPv4 优先**
 *
 * 覆盖纯函数语义（[preferIpv4First]）+ 两处接线（系统 DNS 通道 / DoH 成功通道）。
 */
class DohDnsIpv4PreferenceTest {

    private fun v4(ip: String) = InetAddress.getByName(ip)
    private fun v6(ip: String) = InetAddress.getByName(ip)

    @Test
    fun ipv4ComesFirstWhileKeepingFamilyOrder() {
        val v6a = v6("2001:db8::1")
        val v6b = v6("2001:db8::2")
        val v4a = v4("1.1.1.1")
        val v4b = v4("8.8.8.8")
        val ordered = preferIpv4First(listOf(v6a, v4a, v6b, v4b))
        assertEquals(listOf(v4a, v4b, v6a, v6b), ordered)
    }

    @Test
    fun ipv4OnlyIsReturnedUnchanged() {
        val list = listOf(v4("1.1.1.1"), v4("8.8.8.8"))
        assertSame("全 IPv4 无需重排（保持同一实例）", list, preferIpv4First(list))
    }

    @Test
    fun ipv6OnlyIsReturnedUnchanged() {
        val list = listOf(v6("2001:db8::1"), v6("2001:db8::2"))
        assertEquals(list, preferIpv4First(list))
    }

    @Test
    fun emptyAndSingleAreReturnedAsIs() {
        val empty = emptyList<InetAddress>()
        assertSame(empty, preferIpv4First(empty))
        val single = listOf(v6("2001:db8::1"))
        assertSame(single, preferIpv4First(single))
    }

    @Test
    fun ipv6IsKeptAsFallback() {
        assertEquals(
            "IPv6 只调整顺序、不得被过滤删除",
            2,
            preferIpv4First(listOf(v6("2001:db8::1"), v4("1.1.1.1"))).size
        )
    }

    @Test
    fun systemDnsAndDohPathsBothPreferIpv4() {
        val code = SourceFileProbe.sourceText("help/http/DohDns.kt")
        assertTrue(
            "系统 DNS 通道必须走 IPv4 优先包装",
            code.contains("preferIpv4First(Dns.SYSTEM.lookup(hostname))")
        )
        assertTrue(
            "DoH 成功分支必须排序后再入缓存（缓存命中路径即已排序）",
            code.contains("val orderedAddresses = preferIpv4First(validAddresses)")
        )
        assertTrue(
            "排序结果必须真正返回（不得只排序不返回）",
            code.contains("return orderedAddresses")
        )
    }
}