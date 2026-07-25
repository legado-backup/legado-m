package io.legado.app.help.http

import java.security.SecureRandom
import java.security.cert.CertificateException
import java.security.cert.X509Certificate
import javax.net.ssl.HostnameVerifier
import javax.net.ssl.SSLContext
import javax.net.ssl.SSLSocketFactory
import javax.net.ssl.X509TrustManager

// 源码参照: app/src/main/java/io/legado/app/help/http/SSLHelper.kt
// 简化说明: 仅移植 unsafeTrustManager/unsafeSSLSocketFactory/unsafeHostnameVerifier，跳过 X509TrustManagerExtensions(Android依赖) 和 getSslSocketFactory系列(双向认证) | 已知上限: 无双向认证 | 升级路径: 按需移植 getSslSocketFactory

@Suppress("unused")
object SSLHelper {

    /**
     * 信任所有证书的 TrustManager
     */
    val unsafeTrustManager: X509TrustManager = object : X509TrustManager {
        @Throws(CertificateException::class)
        override fun checkClientTrusted(chain: Array<X509Certificate>, authType: String) {
            //do nothing，接受任意客户端证书
        }

        @Throws(CertificateException::class)
        override fun checkServerTrusted(chain: Array<X509Certificate>, authType: String) {
            //do nothing，接受任意服务端证书
        }

        override fun getAcceptedIssuers(): Array<X509Certificate> {
            return arrayOf()
        }
    }

    val unsafeSSLSocketFactory: SSLSocketFactory by lazy {
        try {
            // 修复5.1: BT之家等网站SSL证书链不完整导致PKIX路径验证失败
            // 改用 TLS 协议（与真机 getSslSocketFactoryBase 一致），SSL 协议已过时且部分 JVM 不支持
            // 修复 GAP-82: 显式启用 TLSv1.2+TLSv1.3，避免部分 JVM 默认只启用 TLSv1.0/1.1
            // 测试发现 handshake_failure/internal_error 多因 TLS 协议版本不匹配导致
            val sslContext = SSLContext.getInstance("TLSv1.2")
            sslContext.init(null, arrayOf(unsafeTrustManager), SecureRandom())
            val factory = sslContext.socketFactory
            // 包装 SSLSocketFactory，在创建 Socket 时启用所有可用 TLS 协议
            object : SSLSocketFactory() {
                private val delegate = factory
                override fun createSocket(s: java.net.Socket, host: String, port: Int, autoClose: Boolean): java.net.Socket {
                    return enableAllTlsProtocols(delegate.createSocket(s, host, port, autoClose))
                }
                override fun createSocket(host: String, port: Int): java.net.Socket {
                    return enableAllTlsProtocols(delegate.createSocket(host, port))
                }
                override fun createSocket(host: String, port: Int, localHost: java.net.InetAddress, localPort: Int): java.net.Socket {
                    return enableAllTlsProtocols(delegate.createSocket(host, port, localHost, localPort))
                }
                override fun createSocket(host: java.net.InetAddress, port: Int): java.net.Socket {
                    return enableAllTlsProtocols(delegate.createSocket(host, port))
                }
                override fun createSocket(address: java.net.InetAddress, port: Int, localAddress: java.net.InetAddress, localPort: Int): java.net.Socket {
                    return enableAllTlsProtocols(delegate.createSocket(address, port, localAddress, localPort))
                }
                override fun getDefaultCipherSuites(): Array<String> = delegate.defaultCipherSuites
                override fun getSupportedCipherSuites(): Array<String> = delegate.supportedCipherSuites
                private fun enableAllTlsProtocols(socket: java.net.Socket): java.net.Socket {
                    if (socket is javax.net.ssl.SSLSocket) {
                        socket.enabledProtocols = socket.supportedProtocols
                    }
                    return socket
                }
            }
        } catch (e: Exception) {
            throw RuntimeException(e)
        }
    }

    /**
     * 信任所有主机名的 HostnameVerifier
     */
    val unsafeHostnameVerifier: HostnameVerifier = HostnameVerifier { _, _ -> true }
}
