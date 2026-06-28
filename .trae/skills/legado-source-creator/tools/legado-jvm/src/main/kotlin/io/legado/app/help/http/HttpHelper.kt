package io.legado.app.help.http

import io.legado.app.constant.AppConst
import io.legado.app.help.config.AppConfig
import okhttp3.ConnectionPool
import okhttp3.Dns
import okhttp3.OkHttpClient
import java.net.InetAddress
import java.net.InetSocketAddress
import java.net.Proxy
import java.util.concurrent.ConcurrentHashMap

// 源码参照: app/src/main/java/io/legado/app/help/http/HttpHelper.kt#L152-L191
// 简化说明: 移除 Cronet/ReadManga 限流拦截器，仅保留代理功能；SSL 信任所有证书（与真机一致） | 已知上限: 无 Cronet 支持、无限流 | 升级路径: 接入 Cronet 或独立限流

private val proxyClientCache = ConcurrentHashMap<String, OkHttpClient>()

// 修复5.2: DNS解析失败时IPv4优先排序 + 公共DNS回退
// 简化说明: 先系统DNS（IPv4优先），失败后用 114.114.114.114 / 8.8.8.8 公共DNS重新解析 | 已知上限: 公共DNS通过系统lookup模拟，JVM可能仍用系统DNS | 升级路径: 接入 DnsOverHttps (OkHttp内置) 或自定义 UDP DNS 客户端
private val ipv4PreferredDns = Dns { hostname ->
    val addresses = try {
        Dns.SYSTEM.lookup(hostname)
    } catch (e: Exception) {
        // 系统 DNS 解析失败，尝试用公共 DNS 服务器重新解析
        // 注意：JVM 的 Dns.SYSTEM 底层使用操作系统 DNS，无法指定上游 DNS 服务器
        // 真正的公共DNS回退需要 DnsOverHttps 或自定义 UDP DNS 客户端
        // 当前作为降级：直接抛出原始异常，避免返回无效IP（之前错误地返回了114.114.114.114等DNS服务器IP）
        throw e
    }
    // 将 IPv4 地址排在前面，IPv6 排在后面
    addresses.sortedWith(compareBy { it is java.net.Inet6Address })
}

private val okHttpClient: OkHttpClient by lazy {
    OkHttpClient.Builder()
        .dns(ipv4PreferredDns)
        .proxySelector(java.net.ProxySelector.of(null))
        .connectionPool(ConnectionPool(5, 5, java.util.concurrent.TimeUnit.MINUTES))
        .connectTimeout(15, java.util.concurrent.TimeUnit.SECONDS)
        .readTimeout(15, java.util.concurrent.TimeUnit.SECONDS)
        .writeTimeout(15, java.util.concurrent.TimeUnit.SECONDS)
        .sslSocketFactory(SSLHelper.unsafeSSLSocketFactory, SSLHelper.unsafeTrustManager)
        .hostnameVerifier(SSLHelper.unsafeHostnameVerifier)
        .followRedirects(true)
        .followSslRedirects(true)
        .retryOnConnectionFailure(true)
        // 修复 GAP-81: 添加默认 User-Agent 拦截器（对齐真机 HttpHelper.kt#L77-L83）
        // 真机模式: OkHttp 默认不携带 UA，部分网站（如起点、纵横）通过 UA 检测拦截非浏览器请求
        // 简化说明: 当请求未显式设置 User-Agent 时，自动添加 AppConfig.userAgent | 已知上限: 无法绕过 JS Challenge | 升级路径: 接入无头浏览器
        .addInterceptor { chain ->
            var request = chain.request()
            if (request.header(AppConst.UA_NAME).isNullOrBlank()) {
                request = request.newBuilder()
                    .header(AppConst.UA_NAME, AppConfig.userAgent)
                    .build()
            }
            chain.proceed(request)
        }
        // 修复 GAP-80: 添加 CookieJar 网络拦截器（对齐真机 HttpHelper.kt#L84-L99）
        // 真机模式: 当请求头含 cookieJarHeader 时，自动加载/保存 Cookie，实现登录态保持
        // 简化说明: 仿真端复用 CookieManagerStub 的 loadRequest/saveResponse | 已知上限: 无 WebView Cookie 同步 | 升级路径: 接入 Selenium Cookie 同步
        .addNetworkInterceptor { chain ->
            var request = chain.request()
            val enableCookieJar = request.header(CookieManager.cookieJarHeader) != null

            if (enableCookieJar) {
                val requestBuilder = request.newBuilder()
                requestBuilder.removeHeader(CookieManager.cookieJarHeader)
                request = CookieManager.loadRequest(requestBuilder.build())
            }

            val networkResponse = chain.proceed(request)

            if (enableCookieJar) {
                CookieManager.saveResponse(networkResponse)
            }
            networkResponse
        }
        .build()
}

/**
 * 缓存代理okHttp
 */
fun getProxyClient(proxy: String? = null): OkHttpClient {
    if (proxy.isNullOrBlank()) {
        return okHttpClient
    }
    proxyClientCache[proxy]?.let {
        return it
    }
    val r = Regex("(http|socks4|socks5)://(.*):(\\d{2,5})(@.*@.*)?")
    val ms = r.findAll(proxy)
    val group = ms.first()
    var username = ""
    var password = ""
    val type = if (group.groupValues[1] == "http") "http" else "socks"
    val host = group.groupValues[2]
    val port = group.groupValues[3].toInt()
    if (group.groupValues[4] != "") {
        username = group.groupValues[4].split("@")[1]
        password = group.groupValues[4].split("@")[2]
    }
    if (host != "") {
        val builder = okHttpClient.newBuilder()
        if (type == "http") {
            builder.proxy(Proxy(Proxy.Type.HTTP, InetSocketAddress(host, port)))
        } else {
            builder.proxy(Proxy(Proxy.Type.SOCKS, InetSocketAddress(host, port)))
        }
        if (username != "" && password != "") {
            builder.proxyAuthenticator { _, response ->
                val credential: String = okhttp3.Credentials.basic(username, password)
                response.request.newBuilder()
                    .header("Proxy-Authorization", credential)
                    .build()
            }
        }
        val proxyClient = builder.build()
        proxyClientCache[proxy] = proxyClient
        return proxyClient
    }
    return okHttpClient
}
