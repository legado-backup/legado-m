package io.legado.app.help.http

// 源码参照: app/src/main/java/io/legado/app/help/http/CookieStore.kt#L21-L137
// 源码参照: app/src/main/java/io/legado/app/help/http/api/CookieManagerInterface.kt
// 简化说明: 合并 CookieManagerInterface 和 CookieStore 自身方法为统一接口 | 已知上限: 无 | 升级路径: 无

/**
 * Cookie 存储接口
 * 包含 CookieStore object 的所有 public 方法签名
 */
interface CookieStoreInterface {

    /**
     * 保存cookie到数据库，会自动识别url的二级域名
     */
    fun setCookie(url: String, cookie: String?)

    /**
     * 设置WebCookie（源码中依赖 android.webkit.CookieManager）
     */
    fun setWebCookie(url: String, cookie: String)

    /**
     * 替换cookie
     */
    fun replaceCookie(url: String, cookie: String)

    /**
     * 获取url所属的二级域名的cookie
     */
    fun getCookie(url: String): String

    /**
     * 获取cookie中指定key的值
     */
    fun getKey(url: String, key: String): String

    /**
     * 移除cookie
     */
    fun removeCookie(url: String)

    /**
     * cookie字符串转Map
     */
    fun cookieToMap(cookie: String): MutableMap<String, String>

    /**
     * Map转cookie字符串
     */
    fun mapToCookie(cookieMap: Map<String, String>?): String?

    /**
     * 清除所有cookie
     */
    fun clear()
}
