package io.legado.app.help.http

import io.legado.app.help.CacheManagerStub
import io.legado.app.utils.NetworkUtilsStub
import java.util.concurrent.ConcurrentHashMap

// 源码参照: app/src/main/java/io/legado/app/help/http/CookieStore.kt#L21-L137
// 源码参照: app/src/main/java/io/legado/app/help/http/CookieManager.kt#L77-L141
// 简化说明: 使用内存 Map 替代 Room+android.webkit.CookieManager，内联 CookieManager 逻辑 | 已知上限: 重启后 Cookie 丢失，无持久化 | 升级路径: 接入 SQLite 或文件系统

/**
 * Cookie 存储 Stub 实现
 * 使用内存 Map 替代 Android CookieManager 和 Room 数据库
 */
object CookieStoreStub : CookieStoreInterface {

    // 持久 cookie 存储（对应源码 appDb.cookieDao）
    private val cookieStore = ConcurrentHashMap<String, String>()

    // WebCookie 存储（对应源码 android.webkit.CookieManager）
    private val webCookieStore = ConcurrentHashMap<String, String>()

    // 内联源码 AppPattern.semicolonRegex / equalsRegex
    private val semicolonRegex = ";".toRegex()
    private val equalsRegex = "=".toRegex()

    override fun setCookie(url: String, cookie: String?) {
        try {
            val domain = NetworkUtilsStub.getSubDomain(url)
            CacheManagerStub.putMemory("${domain}_cookie", cookie ?: "")
            cookieStore[domain] = cookie ?: ""
        } catch (e: Exception) {
            // 简化说明：AppLog.put 替换为 println | 已知上限：无 UI 日志展示 | 升级路径：接入日志框架
            println("保存Cookie失败\n$e")
        }
    }

    override fun setWebCookie(url: String, cookie: String) {
        // 简化说明：android.webkit.CookieManager 不可用，WebCookie 存储到内存 Map | 已知上限：WebView 无法获取 cookie | 升级路径：集成 Selenium
        try {
            val baseUrl = NetworkUtilsStub.getBaseUrl(url) ?: return
            webCookieStore[baseUrl] = cookie
        } catch (e: Exception) {
            println("设置WebCookie失败\n$e")
        }
    }

    override fun replaceCookie(url: String, cookie: String) {
        if (url.isBlank() || cookie.isBlank()) {
            return
        }
        val oldCookie = getCookieNoSession(url)
        if (oldCookie.isEmpty()) {
            setCookie(url, cookie)
        } else {
            val cookieMap = cookieToMap(oldCookie)
            cookieMap.putAll(cookieToMap(cookie))
            val newCookie = mapToCookie(cookieMap)
            setCookie(url, newCookie ?: "")
        }
    }

    override fun getCookie(url: String): String {
        val domain = NetworkUtilsStub.getSubDomain(url)

        val cookie = getCookieNoSession(url)
        val sessionCookie = getSessionCookie(domain)

        val cookieMap = mergeCookiesToMap(cookie, sessionCookie)

        var ck = mapToCookie(cookieMap) ?: ""
        while (ck.length > 4096) {
            val removeKey = cookieMap.keys.random()
            removeCookieKey(url, removeKey)
            cookieMap.remove(removeKey)
            ck = mapToCookie(cookieMap) ?: ""
        }
        return ck
    }

    override fun getKey(url: String, key: String): String {
        val cookie = getCookie(url)
        val sessionCookie = getSessionCookie(url)
        val cookieMap = mergeCookiesToMap(cookie, sessionCookie)
        return cookieMap[key] ?: ""
    }

    override fun removeCookie(url: String) {
        val domain = NetworkUtilsStub.getSubDomain(url)
        cookieStore.remove(domain)
        CacheManagerStub.deleteMemory("${domain}_cookie")
        CacheManagerStub.deleteMemory("${domain}_session_cookie")
        // 简化说明：android.webkit.CookieManager.getInstance().removeCookie(url) 移除，用内存 Map 清理替代
        webCookieStore.keys.filter { it.contains(domain) }.forEach { webCookieStore.remove(it) }
    }

    override fun cookieToMap(cookie: String): MutableMap<String, String> {
        val cookieMap = mutableMapOf<String, String>()
        if (cookie.isBlank()) {
            return cookieMap
        }
        val pairArray = cookie.split(semicolonRegex).dropLastWhile { it.isEmpty() }.toTypedArray()
        for (pair in pairArray) {
            val pairs = pair.split(equalsRegex, 2).dropLastWhile { it.isEmpty() }.toTypedArray()
            if (pairs.size <= 1) {
                continue
            }
            val key = pairs[0].trim { it <= ' ' }
            val value = pairs[1]
            if (value.isNotBlank() || value.trim { it <= ' ' } == "null") {
                cookieMap[key] = value.trim { it <= ' ' }
            }
        }
        return cookieMap
    }

    override fun mapToCookie(cookieMap: Map<String, String>?): String? {
        if (cookieMap.isNullOrEmpty()) {
            return null
        }
        val builder = StringBuilder()
        cookieMap.keys.forEachIndexed { index, key ->
            if (index > 0) builder.append("; ")
            builder.append(key).append("=").append(cookieMap[key])
        }
        return builder.toString()
    }

    override fun clear() {
        cookieStore.clear()
        webCookieStore.clear()
    }

    // ===== 以下为内联的 CookieManager 逻辑 =====
    // 源码参照: app/src/main/java/io/legado/app/help/http/CookieManager.kt#L77-L141

    private fun getSessionCookieMap(domain: String): MutableMap<String, String>? {
        return getSessionCookie(domain)?.let { cookieToMap(it) }
    }

    private fun getSessionCookie(domain: String): String? {
        return CacheManagerStub.getFromMemory("${domain}_session_cookie") as? String
    }

    private fun mergeCookiesToMap(vararg cookies: String?): MutableMap<String, String> {
        return cookies.filterNotNull().map {
            cookieToMap(it)
        }.reduce { acc, cookieMap ->
            acc.apply { putAll(cookieMap) }
        }
    }

    private fun removeCookieKey(url: String, key: String) {
        val domain = NetworkUtilsStub.getSubDomain(url)

        getSessionCookieMap(domain)?.let {
            it.remove(key)
            mapToCookie(it)?.let { cookie ->
                CacheManagerStub.putMemory("${domain}_session_cookie", cookie)
            }
        }

        val cookie = getCookieNoSession(url)
        if (cookie.isNotEmpty()) {
            val cookieMap = cookieToMap(cookie).apply { remove(key) }
            mapToCookie(cookieMap)?.let {
                setCookie(url, it)
            }
        }
    }

    private fun getCookieNoSession(url: String): String {
        val domain = NetworkUtilsStub.getSubDomain(url)
        val cacheCookie = CacheManagerStub.getFromMemory("${domain}_cookie") as? String

        return if (cacheCookie != null) {
            cacheCookie
        } else {
            cookieStore[domain] ?: ""
        }
    }
}
