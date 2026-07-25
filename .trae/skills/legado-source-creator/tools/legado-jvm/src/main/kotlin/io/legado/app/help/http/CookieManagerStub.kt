package io.legado.app.help.http

import io.legado.app.utils.NetworkUtilsStub
import okhttp3.Cookie
import okhttp3.Headers
import okhttp3.HttpUrl
import okhttp3.Request
import okhttp3.Response

// 源码参照: app/src/main/java/io/legado/app/help/http/CookieManager.kt#L18-L105
// 简化说明: 内联 CookieManager 的 cookieJarHeader 和 mergeCookies 方法，委托 CookieStoreStub | 已知上限: 无 WebView Cookie 同步 | 升级路径: 接入 Selenium

object CookieManager {
    const val cookieJarHeader = "CookieJar"

    fun mergeCookies(vararg cookies: String?): String? {
        val cookieMap = mergeCookiesToMap(*cookies)
        return CookieStoreStub.mapToCookie(cookieMap)
    }

    fun mergeCookiesToMap(vararg cookies: String?): MutableMap<String, String> {
        return cookies.filterNotNull().map {
            CookieStoreStub.cookieToMap(it)
        }.reduce { acc, cookieMap ->
            acc.apply { putAll(cookieMap) }
        }
    }

    // 修复 GAP-80: CookieJar 网络拦截器所需的 loadRequest/saveResponse 方法
    // 源码参照: app/src/main/java/io/legado/app/help/http/CookieManager.kt#L29-L75

    /**
     * 从响应中保存Cookies（对齐真机 CookieManager.saveResponse 第29-33行）
     * 真机模式: 解析 Set-Cookie 头，区分 session cookie 和 persistent cookie
     * 简化说明: 仿真端统一保存到 CookieStoreStub，不区分 session/persistent | 已知上限: 无 session cookie 独立管理 | 升级路径: 补充 session cookie 逻辑
     */
    fun saveResponse(response: Response) {
        val url = response.request.url
        val headers = response.headers
        saveCookiesFromHeaders(url, headers)
    }

    private fun saveCookiesFromHeaders(url: HttpUrl, headers: Headers) {
        val domain = NetworkUtilsStub.getSubDomain(url.toString())
        val cookies = Cookie.parseAll(url, headers)
        if (cookies.isEmpty()) return

        // 简化说明: 真机区分 session/persistent，仿真端统一保存 | 已知上限: 无 | 升级路径: 补充 session cookie 逻辑
        val cookieBuilder = StringBuilder()
        cookies.forEachIndexed { index, cookie ->
            if (index > 0) cookieBuilder.append("; ")
            cookieBuilder.append(cookie.name).append('=').append(cookie.value)
        }
        CookieStoreStub.replaceCookie(domain, cookieBuilder.toString())
    }

    /**
     * 加载Cookies到请求中（对齐真机 CookieManager.loadRequest 第55-75行）
     * 真机模式: 从 CookieStore 获取 cookie，合并到请求头
     */
    fun loadRequest(request: Request): Request {
        val url = request.url.toString()
        val domain = NetworkUtilsStub.getSubDomain(url)

        val cookie = CookieStoreStub.getCookie(domain)
        val requestCookie = request.header("Cookie")

        val newCookie = mergeCookies(requestCookie, cookie) ?: return request

        return kotlin.runCatching {
            request.newBuilder()
                .header("Cookie", newCookie)
                .build()
        }.getOrElse {
            CookieStoreStub.removeCookie(url)
            request
        }
    }
}
