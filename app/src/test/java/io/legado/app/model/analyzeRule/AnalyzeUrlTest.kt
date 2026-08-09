package io.legado.app.model.analyzeRule

import com.google.gson.Gson
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

/**
 * B3 resolveIp 兼容：旧书源使用 resolveIp 字段，需能反序列化到 dnsIp。
 * 用独立 Gson 实例测试 @SerializedName alternate 机制（GSONStrict 依赖规则反序列化器，JVM 不可用）。
 */
class AnalyzeUrlTest {

    private val gson = Gson()

    @Test
    fun `legacy resolveIp field maps to dnsIp`() {
        val json = """{"resolveIp":"192.168.1.100"}"""
        val option = gson.fromJson(json, AnalyzeUrl.UrlOption::class.java)
        assertEquals("192.168.1.100", option.getDnsIp())
    }

    @Test
    fun `dnsIp field still maps normally`() {
        val json = """{"dnsIp":"10.0.0.1"}"""
        val option = gson.fromJson(json, AnalyzeUrl.UrlOption::class.java)
        assertEquals("10.0.0.1", option.getDnsIp())
    }

    @Test
    fun `setDnsIp trims whitespace`() {
        val option = AnalyzeUrl.UrlOption()
        option.setDnsIp(" 203.0.113.5 ")
        assertEquals("203.0.113.5", option.getDnsIp())
    }

    @Test
    fun `setDnsIp blank becomes null`() {
        val option = AnalyzeUrl.UrlOption()
        option.setDnsIp("   ")
        assertNull(option.getDnsIp())
    }

    @Test
    fun `missing dns fields yields null`() {
        val json = """{"method":"GET"}"""
        val option = gson.fromJson(json, AnalyzeUrl.UrlOption::class.java)
        assertNull(option.getDnsIp())
    }
}
