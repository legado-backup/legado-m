package io.legado.app.help.http

import okhttp3.Interceptor
import okhttp3.OkHttpClient
import okhttp3.Protocol
import okhttp3.Request
import okhttp3.Response
import okhttp3.ResponseBody.Companion.toResponseBody
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import java.net.ConnectException
import java.net.NoRouteToHostException
import java.net.SocketException
import java.net.SocketTimeoutException
import java.net.UnknownHostException
import javax.net.ssl.SSLException

/**
 * 【2026-10-18 · 网络层统一修复 · B-54】「坏 IP 自愈」行为护栏。
 *
 * 语义：只有**连接阶段**失败才上报 `HostAccessStrategy.reportBadIpSuspect` 并**重试一次**
 * （重试时 `DohDns` 已因该 host 退避而改走系统 DNS ⇒ 消除「DoH 解析到不可达 IP ⇒ 打满 callTimeout」）；
 * 读超时（服务端慢）/ DNS 名称不存在 / TLS 错误**不重试**（重试无益，只翻倍耗时）。
 *
 * 取法：用**真 OkHttpClient** 装配（含 `BadIpSelfHealInterceptor` 作最外层）+ **末位拦截器直接返回响应**
 * ⇒ 全程**零网络**，但走的是真实 OkHttp 拦截链（避免手写 `Interceptor.Chain` 的抽象成员风险）。
 */
class BadIpSelfHealTest {

    // ---------- 纯判据 ----------

    @Test
    fun connectPhaseFailures_areRecognized() {
        assertTrue(isConnPhaseFailure(ConnectException("Connection refused")))
        assertTrue(isConnPhaseFailure(NoRouteToHostException("no route")))
        assertTrue(isConnPhaseFailure(SocketException("Connection reset")))
        assertTrue(isConnPhaseFailure(SocketTimeoutException("connect timed out")))
    }

    @Test
    fun nonConnectFailures_areNotRetried() {
        // 读超时（服务端慢）：重试无益
        assertFalse(isConnPhaseFailure(SocketTimeoutException("timeout")))
        assertFalse(isConnPhaseFailure(SocketTimeoutException("read timed out")))
        // 域名不存在 / TLS 错误：换 IP 也救不了
        assertFalse(isConnPhaseFailure(UnknownHostException("nope")))
        assertFalse(isConnPhaseFailure(SSLException("handshake")))
        assertFalse(isConnPhaseFailure(IllegalStateException("other")))
    }

    // ---------- 拦截器行为（真 OkHttp 链 · 零网络） ----------

    /** 第 1 次抛指定异常、之后直接返回 200（不 `proceed` ⇒ 不触发任何真实连接）。 */
    private class FlakyTail(private val first: Throwable?) : Interceptor {
        var calls = 0
            private set

        override fun intercept(chain: Interceptor.Chain): Response {
            calls++
            if (calls == 1 && first != null) throw first
            return Response.Builder()
                .request(chain.request())
                .protocol(Protocol.HTTP_1_1)
                .code(200).message("OK")
                .body("ok".toResponseBody(null))
                .build()
        }
    }

    /** 每次都抛指定异常（用于验证「重试仍失败 ⇒ 原样上抛且只重试一次」）。 */
    private class AlwaysFailTail(private val e: Throwable) : Interceptor {
        var calls = 0
            private set

        override fun intercept(chain: Interceptor.Chain): Response {
            calls++
            throw e
        }
    }

    private fun clientWith(tail: Interceptor): OkHttpClient =
        OkHttpClient.Builder()
            .addInterceptor(BadIpSelfHealInterceptor)
            .addInterceptor(tail)
            .build()

    private fun call(client: OkHttpClient, url: String = "https://host-a.example/x") =
        client.newCall(Request.Builder().url(url).build()).execute()

    @Test
    fun connFail_retriesOnceAndSucceeds() {
        HostAccessStrategy.clearHost("host-a.example")
        val tail = FlakyTail(ConnectException("Connection refused"))
        val resp = call(clientWith(tail))
        assertEquals(200, resp.code)
        resp.close()
        assertEquals(2, tail.calls)   // 失败 1 次 + 重试 1 次
        // 上报后该 host 进入退避 ⇒ 后续 lookup 直走系统 DNS
        assertTrue(HostAccessStrategy.isSystemDnsPreferred("host-a.example"))
        HostAccessStrategy.clearHost("host-a.example")
    }

    @Test
    fun readTimeout_doesNotRetry() {
        HostAccessStrategy.clearHost("host-a.example")
        val tail = FlakyTail(SocketTimeoutException("timeout"))
        var thrown: Throwable? = null
        try {
            call(clientWith(tail)).close()
        } catch (t: Throwable) {
            thrown = t
        }
        assertTrue("读超时应原样抛出", thrown is SocketTimeoutException)
        assertEquals(1, tail.calls)   // 不重试
        assertFalse(HostAccessStrategy.isSystemDnsPreferred("host-a.example"))
    }

    @Test
    fun socketReset_alsoRetriesOnce() {
        // 连接被重置（SocketException 家族）同样属**连接层**失败 ⇒ 应上报 + 重试一次
        HostAccessStrategy.clearHost("host-a.example")
        val tail = FlakyTail(SocketException("Connection reset by peer"))
        val resp = call(clientWith(tail))
        assertEquals(200, resp.code)
        resp.close()
        assertEquals(2, tail.calls)
        assertTrue(HostAccessStrategy.isSystemDnsPreferred("host-a.example"))
        HostAccessStrategy.clearHost("host-a.example")
    }

    @Test
    fun retryFailsAgain_exceptionPropagates() {
        // 重试仍失败 ⇒ 异常原样上抛（不吞错、不无限重试：恰好 2 次）
        HostAccessStrategy.clearHost("host-a.example")
        val tail = AlwaysFailTail(ConnectException("refused"))
        var thrown: Throwable? = null
        try {
            call(clientWith(tail)).close()
        } catch (t: Throwable) {
            thrown = t
        }
        assertTrue(thrown is ConnectException)
        assertEquals(2, tail.calls)   // 首次 + 重试（末位拦截器每次 `proceed` 各调用 1 次）
        HostAccessStrategy.clearHost("host-a.example")
    }

    @Test
    fun okResponse_passesThroughUntouched() {
        val tail = FlakyTail(null)
        val resp = call(clientWith(tail))
        assertEquals(200, resp.code)
        resp.close()
        assertEquals(1, tail.calls)
    }
}
