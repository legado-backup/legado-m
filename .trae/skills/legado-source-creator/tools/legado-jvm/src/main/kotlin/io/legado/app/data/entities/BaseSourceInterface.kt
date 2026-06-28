package io.legado.app.data.entities

import cn.hutool.crypto.symmetric.AES
import com.script.ScriptBindings
import com.script.buildScriptBindings
import com.script.rhino.RhinoScriptEngine
import io.legado.app.model.analyzeRule.AnalyzeRule
import io.legado.app.constant.AppConst
import io.legado.app.help.CacheManagerStub
import io.legado.app.help.ConcurrentRateLimiter
import io.legado.app.help.http.CookieStoreStub
import io.legado.app.help.source.getShareScope
import io.legado.app.utils.GSON
import io.legado.app.utils.GSONStrict
import io.legado.app.utils.fromJsonObject

// 源码参照: app/src/main/java/io/legado/app/data/entities/BaseSource.kt
// 简化说明: 从 BaseSource 接口抽取，补全 evalJS/login/getHeaderMap/getLoginInfo 等 17 个方法 | 已知上限: AES key 用固定值、getLoginInfoMap 无 RowUi 解析、refreshExplore/refreshJSLib 空实现 | 升级路径: 接入 RowUi、AppConst.androidId、SharedJsScope
// 修复说明: concurrentRate/loginUrl/loginUi/header/enabledCookieJar/jsLib 由 val 改为 var，与真机 BaseSource.kt 签名一致（真机均为 var，支持运行时修改）

/**
 * BaseSource 接口
 * 包含 AnalyzeUrl/AnalyzeRule 需要的方法签名及 JS 执行/登录/缓存相关默认实现
 */
interface BaseSourceInterface {
    /**
     * 并发率
     */
    var concurrentRate: String?

    /**
     * 登录地址
     */
    var loginUrl: String?

    /**
     * 登录UI
     * 源码参照: app/src/main/java/io/legado/app/data/entities/BaseSource.kt#L47
     */
    var loginUi: String?

    /**
     * 请求头
     */
    var header: String?

    /**
     * 启用cookieJar
     */
    var enabledCookieJar: Boolean?

    /**
     * js库
     */
    var jsLib: String?

    fun getTag(): String

    fun getKey(): String

    // ==================== JS 执行 (GAP-15) ====================

    /**
     * 执行JS
     * 源码参照: app/src/main/java/io/legado/app/data/entities/BaseSource.kt#L324-L343
     * 修复内容: 添加 sharedScope 分支，支持 jsLib 共享 JS 作用域
     * 简化说明: SharedJsScope 简化版，不支持 jsLib URL 下载 | 已知上限: jsLib 中的 URL 会被跳过 | 升级路径: 接入 OkHttp 同步下载
     */
    @Throws(Exception::class)
    fun evalJS(jsStr: String, bindingsConfig: ScriptBindings.() -> Unit = {}): Any? {
        val bindings = buildScriptBindings { bindings ->
            bindings["java"] = this
            bindings["source"] = this
            bindings["baseUrl"] = getKey()
            bindings["cookie"] = CookieStoreStub
            bindings["cache"] = CacheManagerStub
            bindings.apply(bindingsConfig)
        }
        val sharedScope = getShareScope()
        val scope = if (sharedScope == null) {
            RhinoScriptEngine.getRuntimeScope(bindings)
        } else {
            bindings.apply {
                prototype = sharedScope
            }
        }
        val evalResult = RhinoScriptEngine.eval(jsStr, scope)
        // 修复 NativeJavaObject 序列化 Bug
        return AnalyzeRule.unwrapRhinoResult(evalResult)
    }

    // ==================== 请求头解析 (GAP-14) ====================

    /**
     * 解析header规则
     * 源码参照: app/src/main/java/io/legado/app/data/entities/BaseSource.kt#L104-L133
     * 简化说明: AppConfig.userAgent 替换为固定 UA | 已知上限: UA 不可配置 | 升级路径: 接入 AppConfig
     */
    fun getHeaderMap(hasLoginHeader: Boolean = false): Map<String, String>? {
        val headerMap = HashMap<String, String>()
        header?.let {
            try {
                val json = when {
                    it.startsWith("@js:", true) -> evalJS(it.substring(4)).toString()
                    it.startsWith("<js>", true) -> evalJS(
                        it.substring(4, it.lastIndexOf("<"))
                    ).toString()
                    else -> it
                }
                GSONStrict.fromJsonObject<Map<String, String>>(json).getOrNull()?.let { map ->
                    headerMap.putAll(map)
                } ?: GSON.fromJsonObject<Map<String, String>>(json).getOrNull()?.let { map ->
                    headerMap.putAll(map)
                }
            } catch (e: Exception) {
                // 简化说明: AppLog.put 替换为 println | 已知上限: 无 UI 日志展示 | 升级路径: 接入日志框架
                println("执行请求头规则出错\n$e")
            }
        }
        if (!headerMap.containsKey(AppConst.UA_NAME)) {
            headerMap[AppConst.UA_NAME] =
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        if (hasLoginHeader) {
            getLoginHeaderMap()?.let {
                headerMap.putAll(it)
            }
        }
        return headerMap
    }

    // ==================== 登录 (GAP-16) ====================

    /**
     * 获取登录JS
     * 源码参照: app/src/main/java/io/legado/app/data/entities/BaseSource.kt#L72-L80
     */
    fun getLoginJs(): String? {
        val loginJs = loginUrl
        return when {
            loginJs == null -> null
            loginJs.startsWith("@js:") -> loginJs.substring(4)
            loginJs.startsWith("<js>") -> loginJs.substring(4, loginJs.lastIndexOf("<"))
            else -> loginJs
        }
    }

    /**
     * 调用login函数 实现登录请求
     * 源码参照: app/src/main/java/io/legado/app/data/entities/BaseSource.kt#L86-L99
     */
    fun login() {
        val loginJs = getLoginJs()
        if (!loginJs.isNullOrBlank()) {
            val js = """$loginJs
                if(typeof login=='function'){
                    login.apply(this);
                } else {
                    throw('Function login not implements!!!')
                }
            """.trimIndent()
            evalJS(js)
        }
    }

    // ==================== 登录头部信息 ====================

    /**
     * 获取用于登录的头部信息
     * 源码参照: app/src/main/java/io/legado/app/data/entities/BaseSource.kt#L139-L141
     * 简化说明: CacheManager 替换为 CacheManagerStub | 已知上限: 缓存不持久 | 升级路径: 接入持久化缓存
     */
    fun getLoginHeader(): String? {
        return CacheManagerStub.get("loginHeader_${getKey()}")
    }

    /**
     * 获取登录头部Map
     * 源码参照: app/src/main/java/io/legado/app/data/entities/BaseSource.kt#L143-L146
     */
    fun getLoginHeaderMap(): Map<String, String>? {
        val cache = getLoginHeader() ?: return null
        return GSON.fromJsonObject<Map<String, String>>(cache).getOrNull()
    }

    /**
     * 保存登录头部信息
     * 源码参照: app/src/main/java/io/legado/app/data/entities/BaseSource.kt#L151-L158
     * 简化说明: CookieStore 替换为 CookieStoreStub | 已知上限: Cookie 不持久 | 升级路径: 接入持久化 CookieStore
     */
    fun putLoginHeader(header: String) {
        val headerMap = GSON.fromJsonObject<Map<String, String>>(header).getOrNull()
        val cookie = headerMap?.get("Cookie") ?: headerMap?.get("cookie")
        cookie?.let {
            CookieStoreStub.replaceCookie(getKey(), it)
        }
        CacheManagerStub.put("loginHeader_${getKey()}", header, 0)
    }

    /**
     * 移除登录头部信息
     * 源码参照: app/src/main/java/io/legado/app/data/entities/BaseSource.kt#L160-L163
     */
    fun removeLoginHeader() {
        CacheManagerStub.delete("loginHeader_${getKey()}")
        CookieStoreStub.removeCookie(getKey())
    }

    // ==================== 登录用户信息（AES 加密） ====================

    /**
     * 获取用户信息,可以用来登录
     * 用户信息采用aes加密存储
     * 源码参照: app/src/main/java/io/legado/app/data/entities/BaseSource.kt#L170-L179
     * 简化说明: AppConst.androidId 替换为环境变量/固定值 | 已知上限: AES key 固定，非真机 androidId | 升级路径: 接入 AppConst.androidId
     */
    fun getLoginInfo(): String? {
        try {
            val key = getAesKey()
            val cache = CacheManagerStub.get("userInfo_${getKey()}") ?: return null
            return AES(key).decryptStr(cache)
        } catch (e: Exception) {
            println("获取登陆信息出错\n$e")
            return null
        }
    }

    /**
     * 保存用户信息,aes加密
     * 源码参照: app/src/main/java/io/legado/app/data/entities/BaseSource.kt#L221-L231
     * 简化说明: SymmetricCryptoAndroid 替换为 hutool AES | 已知上限: 加密方式可能与真机不同 | 升级路径: 接入 SymmetricCryptoAndroid
     */
    fun putLoginInfo(info: String): Boolean {
        return try {
            val key = getAesKey()
            val encodeStr = AES(key).encryptBase64(info)
            CacheManagerStub.put("userInfo_${getKey()}", encodeStr, 0)
            true
        } catch (e: Exception) {
            println("保存登陆信息出错\n$e")
            false
        }
    }

    /**
     * 移除用户信息
     * 源码参照: app/src/main/java/io/legado/app/data/entities/BaseSource.kt#L234-L236
     */
    fun removeLoginInfo() {
        CacheManagerStub.delete("userInfo_${getKey()}")
    }

    /**
     * 构建登录信息绑定的 ScriptBindings 配置
     * 源码参照: app/src/main/java/io/legado/app/data/entities/BaseSource.kt#L181-L185
     */
    fun configureScriptBindings(): ScriptBindings.() -> Unit = {
        put("result", mutableMapOf<String, String>())
        put("book", null)
        put("chapter", null)
    }

    /**
     * 获取登录信息Map
     * 源码参照: app/src/main/java/io/legado/app/data/entities/BaseSource.kt#L187-L215
     * 简化说明: 移除 RowUi 依赖，仅解析已存储的 loginInfo JSON | 已知上限: 不支持从 loginUi 生成默认值 | 升级路径: 接入 RowUi
     */
    fun getLoginInfoMap(): MutableMap<String, String> {
        val json = getLoginInfo() ?: return mutableMapOf()
        return GSON.fromJsonObject<MutableMap<String, String>>(json).getOrNull() ?: mutableMapOf()
    }

    // ==================== 变量管理 ====================

    /**
     * 保存数据
     * 源码参照: app/src/main/java/io/legado/app/data/entities/BaseSource.kt#L275-L278
     * 简化说明: CacheManager 替换为 CacheManagerStub | 已知上限: 缓存不持久 | 升级路径: 接入持久化缓存
     */
    fun put(key: String, value: String): String {
        CacheManagerStub.put("v_${getKey()}_${key}", value, 0)
        return value
    }

    /**
     * 获取保存的数据
     * 源码参照: app/src/main/java/io/legado/app/data/entities/BaseSource.kt#L284-L286
     * 简化说明: CacheManager 替换为 CacheManagerStub | 已知上限: 缓存不持久 | 升级路径: 接入持久化缓存
     */
    fun get(key: String): String {
        return CacheManagerStub.get("v_${getKey()}_${key}") ?: ""
    }

    /**
     * 设置变量（整个变量字符串）
     * 源码参照: app/src/main/java/io/legado/app/data/entities/BaseSource.kt#L242-L246
     * 真机签名: fun setVariable(variable: String?) - 单参数，存储到 CacheManager
     */
    fun setVariable(variable: String?) {
        if (variable != null) {
            CacheManagerStub.put("sourceVariable_${getKey()}", variable, 0)
        } else {
            CacheManagerStub.delete("sourceVariable_${getKey()}")
        }
    }

    /**
     * 获取变量（整个变量字符串）
     * 源码参照: app/src/main/java/io/legado/app/data/entities/BaseSource.kt#L267-L269
     * 真机签名: fun getVariable(): String - 无参数，从 CacheManager 获取
     */
    fun getVariable(): String {
        return CacheManagerStub.get("sourceVariable_${getKey()}") ?: ""
    }

    /**
     * 设置自定义变量（put 别名）
     * 源码参照: app/src/main/java/io/legado/app/data/entities/BaseSource.kt#L255-L261
     */
    fun putVariable(variable: String?) {
        setVariable(variable)
    }

    // ==================== 刷新与并发 ====================

    /**
     * 刷新发现
     * 源码参照: app/src/main/java/io/legado/app/data/entities/BaseSource.kt#L291-L300
     * 简化说明: JVM 端无缓存，空实现 | 已知上限: 不清除发现缓存 | 升级路径: 接入 clearExploreKindsCache
     */
    fun refreshExplore() {
        // 简化说明: JVM 端无 BookSource 缓存，无需刷新 | 已知上限: 无 | 升级路径: 接入 clearExploreKindsCache
    }

    /**
     * 刷新JSLib
     * 源码参照: app/src/main/java/io/legado/app/data/entities/BaseSource.kt#L305-L312
     * 修复内容: 调用 SharedJsScope.remove 清除 JS 库缓存
     * 简化说明: SharedJsScope 简化版，不支持 jsLib URL 下载 | 已知上限: jsLib 中的 URL 会被跳过 | 升级路径: 接入 OkHttp 同步下载
     */
    fun refreshJSLib() {
        io.legado.app.model.SharedJsScope.remove(jsLib)
    }

    /**
     * 设置并发率
     * 源码参照: app/src/main/java/io/legado/app/data/entities/BaseSource.kt#L317-L319
     * 修复说明: 调用 ConcurrentRateLimiter.updateConcurrentRate，与真机 putConcurrent 行为一致
     */
    fun putConcurrent(value: String) {
        ConcurrentRateLimiter.updateConcurrentRate(getKey(), value)
    }

    // ==================== 私有辅助方法 ====================

    /**
     * 获取 AES 加密 key
     * 简化说明: AppConst.androidId 替换为环境变量/固定值 | 已知上限: AES key 固定 | 升级路径: 接入 AppConst.androidId
     */
    private fun getAesKey(): ByteArray {
        val androidId = System.getenv("LEGADO_ANDROID_ID") ?: "000000000000000"
        return androidId.encodeToByteArray(0, 16)
    }
}
