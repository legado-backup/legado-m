package io.legado.app.data.entities

import io.legado.app.utils.GSON
import io.legado.app.utils.GSONStrict
import io.legado.app.utils.fromJsonObject

// 源码参照: app/src/main/java/io/legado/app/data/entities/BaseSource.kt
// 简化说明: 移除 JsExtensions 继承（132方法）、Android @JavascriptInterface、AppConfig/AppConst/CacheManager/CookieStore 依赖；getHeaderMap 简化为直接解析 header JSON，不执行 JS | 已知上限: 无法执行 @js:/<js> 请求头规则、无登录头部管理、无登录信息加密 | 升级路径: 通过 AnalyzeRule 注入 evalJS，接入 CacheManagerStub/CookieStoreStub

/**
 * 可在js里调用,source.xxx()
 * 简化版：不继承 JsExtensionsInterface，仅保留 AnalyzeRule 需要的方法
 */
@Suppress("unused")
interface BaseSource {

    var concurrentRate: String?

    var loginUrl: String?

    var loginUi: String?

    var header: String?

    var enabledCookieJar: Boolean?

    var jsLib: String?

    fun getTag(): String

    fun getKey(): String

    /**
     * 解析header规则
     * 简化说明：移除 evalJS 调用，直接解析 header JSON | 已知上限：无法执行 @js:/<js> 请求头规则 | 升级路径：通过 AnalyzeRule 注入 evalJS
     */
    fun getHeaderMap(hasLoginHeader: Boolean = false): Map<String, String> {
        val result = HashMap<String, String>()
        header?.let {
            GSONStrict.fromJsonObject<Map<String, String>>(it).getOrNull()?.let { map ->
                result.putAll(map)
            } ?: GSON.fromJsonObject<Map<String, String>>(it).getOrNull()?.let { map ->
                result.putAll(map)
            }
        }
        return result
    }

    /**
     * 保存数据
     */
    fun put(key: String, value: String): String

    /**
     * 获取保存的数据
     */
    fun get(key: String): String

}
