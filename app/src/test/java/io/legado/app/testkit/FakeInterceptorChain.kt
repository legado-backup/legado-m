package io.legado.app.testkit

import okhttp3.Authenticator
import okhttp3.Cache
import okhttp3.Call
import okhttp3.CertificatePinner
import okhttp3.Connection
import okhttp3.ConnectionPool
import okhttp3.CookieJar
import okhttp3.Dns
import okhttp3.EventListener
import okhttp3.Interceptor
import okhttp3.Request
import okhttp3.Response
import java.net.Proxy
import java.net.ProxySelector
import java.util.concurrent.TimeUnit
import javax.net.SocketFactory
import javax.net.ssl.HostnameVerifier
import javax.net.ssl.SSLSocketFactory
import javax.net.ssl.X509TrustManager

/**
 * 伪造 `okhttp3.Interceptor.Chain` 单源（core-flow-test-coverage AD-01「缝 B」）。
 *
 * 范式沿用既有 [io.legado.app.help.http.DecompressInterceptorTest] 的 fakeChain，
 * 提炼为单源以避免各测试副本漂移（同 [SourceFileProbe] 的提炼动机）。
 *
 * 用法：`fakeInterceptorChain { throw IOException("x") }` —— 用 lambda 定义 `proceed` 行为。
 */
fun fakeInterceptorChain(
    request: Request = Request.Builder().url("https://example.com/test").build(),
    onProceed: (Request) -> Response,
): Interceptor.Chain = object : Interceptor.Chain {
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
    override fun request(): Request = request
    override fun proceed(request: Request): Response = onProceed(request)
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
        x509TrustManager: X509TrustManager?,
    ): Interceptor.Chain = this
    override fun withHostnameVerifier(hostnameVerifier: HostnameVerifier): Interceptor.Chain = this
    override fun withCertificatePinner(certificatePinner: CertificatePinner): Interceptor.Chain = this
    override fun withConnectionPool(connectionPool: ConnectionPool): Interceptor.Chain = this
}
