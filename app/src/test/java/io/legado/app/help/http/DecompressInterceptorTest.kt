package io.legado.app.help.http

import okhttp3.Call
import okhttp3.Connection
import okhttp3.Dns
import okhttp3.Interceptor
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.Protocol
import okhttp3.Request
import okhttp3.Response
import okhttp3.ResponseBody
import okhttp3.ResponseBody.Companion.toResponseBody
import okhttp3.Authenticator
import okhttp3.Cache
import okhttp3.CertificatePinner
import okhttp3.ConnectionPool
import okhttp3.CookieJar
import okhttp3.EventListener
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Test
import java.net.Proxy
import java.net.ProxySelector
import java.util.concurrent.TimeUnit
import java.util.zip.Deflater
import java.util.zip.DeflaterOutputStream
import java.util.zip.GZIPOutputStream
import javax.net.SocketFactory
import javax.net.ssl.HostnameVerifier
import javax.net.ssl.SSLSocketFactory
import javax.net.ssl.X509TrustManager
import java.io.ByteArrayOutputStream

/**
 * DecompressInterceptor 解压逻辑单元测试
 *
 * 验证点（纯 JVM，无网络，用 fake Chain 构造响应）：
 * 1. gzip 分支：成功解压 + Content-Encoding 头被移除
 * 2. deflate 分支：成功解压 + Content-Encoding 头被移除
 * 3. 无 Content-Encoding：原样返回（else 分支透传）
 * 4. 空 body：原样返回
 *
 * 已知上限：br 成功解压路径与 gzip 结构完全同构，此处以 gzip 成功路径覆盖结构性验证；
 * br 成功路径（"br handled" 日志）与异常回退透传（catch 分支）留待真机通过
 * `adb logcat -s Decompress:I` 确认（tasks.md 1.3.5）——原因：br 分支命中后会调用
 * AppLog，而 AppLog 依赖 Android appCtx（AppConfig.<clinit>），纯 JVM 单测无法执行。
 */
class DecompressInterceptorTest {

    // ============ 工具 ============

    private fun gzipBytes(text: String): ByteArray {
        val bos = ByteArrayOutputStream()
        GZIPOutputStream(bos).use { it.write(text.toByteArray()) }
        return bos.toByteArray()
    }

    private fun deflateBytes(text: String): ByteArray {
        val bos = ByteArrayOutputStream()
        DeflaterOutputStream(bos, Deflater(Deflater.DEFAULT_COMPRESSION, true)).use { it.write(text.toByteArray()) }
        return bos.toByteArray()
    }

    private fun fakeChain(response: Response): Interceptor.Chain = object : Interceptor.Chain {
        override fun connectTimeoutMillis(): Int = 0
        override fun readTimeoutMillis(): Int = 0
        override fun writeTimeoutMillis(): Int = 0
        override val followSslRedirects: Boolean = false
        override val followRedirects: Boolean = false
        override val dns: Dns = Dns.SYSTEM
        override val socketFactory: SocketFactory = SocketFactory.getDefault()
        override val retryOnConnectionFailure: Boolean = false
        override val authenticator: Authenticator = Authenticator.NONE
        override val cookieJar: CookieJar = CookieJar.NO_COOKIES
        override val cache: Cache? = null
        override val proxy: Proxy? = null
        override val proxySelector: ProxySelector = ProxySelector.getDefault()
        override val proxyAuthenticator: Authenticator = Authenticator.NONE
        override val sslSocketFactoryOrNull: SSLSocketFactory? = null
        override val x509TrustManagerOrNull: X509TrustManager? = null
        override val hostnameVerifier: HostnameVerifier = okhttp3.internal.tls.OkHostnameVerifier
        override val certificatePinner: CertificatePinner = CertificatePinner.DEFAULT
        override val connectionPool: ConnectionPool = ConnectionPool()
        override val eventListener: EventListener = EventListener.NONE
        override fun request(): Request = response.request
        override fun proceed(request: Request): Response = response
        override fun connection(): Connection? = null
        override fun call(): Call = throw UnsupportedOperationException("not used in test")
        override fun withConnectTimeout(timeout: Int, unit: TimeUnit): Interceptor.Chain = this
        override fun withReadTimeout(timeout: Int, unit: TimeUnit): Interceptor.Chain = this
        override fun withWriteTimeout(timeout: Int, unit: TimeUnit): Interceptor.Chain = this
        override fun withDns(dns: Dns): Interceptor.Chain = this
        override fun withSocketFactory(socketFactory: SocketFactory): Interceptor.Chain = this
        override fun withRetryOnConnectionFailure(retryOnConnectionFailure: Boolean): Interceptor.Chain = this
        override fun withAuthenticator(authenticator: Authenticator): Interceptor.Chain = this
        override fun withCookieJar(cookieJar: CookieJar): Interceptor.Chain = this
        override fun withCache(cache: Cache?): Interceptor.Chain = this
        override fun withProxy(proxy: Proxy?): Interceptor.Chain = this
        override fun withProxySelector(proxySelector: ProxySelector): Interceptor.Chain = this
        override fun withProxyAuthenticator(proxyAuthenticator: Authenticator): Interceptor.Chain = this
        override fun withSslSocketFactory(
            sslSocketFactory: SSLSocketFactory?,
            x509TrustManager: X509TrustManager?
        ): Interceptor.Chain = this
        override fun withHostnameVerifier(hostnameVerifier: HostnameVerifier): Interceptor.Chain = this
        override fun withCertificatePinner(certificatePinner: CertificatePinner): Interceptor.Chain = this
        override fun withConnectionPool(connectionPool: ConnectionPool): Interceptor.Chain = this
    }

    private fun buildResponse(
        request: Request,
        contentEncoding: String?,
        bodyBytes: ByteArray
    ): Response {
        val builder = Response.Builder()
            .request(request)
            .protocol(Protocol.HTTP_1_1)
            .code(200)
            .message("OK")
            .body(bodyBytes.toResponseBody("application/octet-stream".toMediaType()))
        if (contentEncoding != null) {
            builder.header("Content-Encoding", contentEncoding)
        }
        return builder.build()
    }

    private fun request(url: String = "https://example.com/test"): Request =
        Request.Builder().url(url).build()

    // ============ 测试 ============

    @Test
    fun gzipResponse_decompressedAndHeadersRemoved() {
        val original = "这是一个 gzip 压缩的响应内容"
        val resp = buildResponse(request(), "gzip", gzipBytes(original))

        val out = DecompressInterceptor.intercept(fakeChain(resp))

        assertEquals(200, out.code)
        assertNull("Content-Encoding 应被移除", out.header("Content-Encoding"))
        assertNull("Content-Length 应被移除", out.header("Content-Length"))
        val bodyText = out.body!!.string()
        assertEquals("解压后内容应与原文一致", original, bodyText)
    }

    @Test
    fun deflateResponse_decompressedAndHeadersRemoved() {
        val original = "deflate 压缩响应"
        val resp = buildResponse(request(), "deflate", deflateBytes(original))

        val out = DecompressInterceptor.intercept(fakeChain(resp))

        assertEquals(200, out.code)
        assertNull("Content-Encoding 应被移除", out.header("Content-Encoding"))
        assertEquals("解压后内容应与原文一致", original, out.body!!.string())
    }

    @Test
    fun noContentEncoding_responseReturnedUnchanged() {
        val resp = buildResponse(request(), null, "plain".toByteArray())

        val out = DecompressInterceptor.intercept(fakeChain(resp))

        assertEquals(200, out.code)
        assertNull("无编码时不应设置 Content-Encoding", out.header("Content-Encoding"))
        assertEquals("无编码时 body 原样返回", "plain", out.body!!.string())
    }

    @Test
    fun emptyBody_withCompressedHeader_returnsOriginalResponse() {
        // body == ResponseBody.EMPTY 时直接返回原响应
        val resp = Response.Builder()
            .request(request())
            .protocol(Protocol.HTTP_1_1)
            .code(200)
            .message("OK")
            .body(ResponseBody.EMPTY)
            .build()

        val out = DecompressInterceptor.intercept(fakeChain(resp))

        assertEquals("空 body 应原样返回", 200, out.code)
        assertNotNull("返回的应是非空响应", out.body)
    }
}
