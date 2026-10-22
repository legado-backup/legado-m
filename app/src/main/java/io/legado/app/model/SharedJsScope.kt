package io.legado.app.model

import androidx.collection.LruCache
import com.google.gson.reflect.TypeToken
import com.script.ScriptBindings
import com.script.rhino.RhinoScriptEngine
import io.legado.app.constant.AppLog
import io.legado.app.constant.AppLog.Level
import io.legado.app.exception.NoStackTraceException
import io.legado.app.help.http.newCallStrResponse
import io.legado.app.help.http.okHttpClient
import io.legado.app.utils.ACache
import io.legado.app.utils.GSON
import io.legado.app.utils.MD5Utils
import io.legado.app.utils.isAbsUrl
import io.legado.app.utils.isJsonObject
import kotlinx.coroutines.runBlocking
import org.mozilla.javascript.BaseFunction
import org.mozilla.javascript.Context
import org.mozilla.javascript.Scriptable
import org.mozilla.javascript.ScriptableObject
import splitties.init.appCtx
import java.io.File
import java.lang.ref.WeakReference
import java.security.SecureRandom
import kotlin.coroutines.CoroutineContext

object SharedJsScope {

    private val cacheFolder = File(appCtx.cacheDir, "shareJs")
    private val aCache = ACache.get(cacheFolder)

    private val scopeMap = LruCache<String, WeakReference<Scriptable>>(16)

    private const val CRYPTO_JS_ASSET = "scripts/cryptojs.min.js"
    @Volatile
    private var cryptoJsText: String? = null
    @Volatile
    private var cryptoScope: WeakReference<Scriptable>? = null
    private val cryptoLock = Any()
    private const val CRYPTO_JS_ERROR_KEY = "cryptojs_load_error"

    /**
     * CryptoJS 的 `WordArray.random` 依赖浏览器 `crypto.getRandomValues`；Rhino 无该宿主 API，
     * 直接调用会抛 "Native crypto module could not be used to get secure random"。
     * 这里把 Java SecureRandom 以临时全局函数注入，替换 `WordArray.random` 后立即删除绑定
     * （与 NG 原版一致；脚本侧不会看到额外全局符号）。
     */
    private fun evalCryptoJs(scope: Scriptable, coroutineContext: CoroutineContext?) {
        val js = loadCryptoJs() ?: return
        RhinoScriptEngine.eval(js, scope, coroutineContext)
        CryptoRandomPatch.install(scope, coroutineContext)
    }

    /**
     * 补丁本体。刻意做成**嵌套 object**：不依赖 appCtx/assets，
     * 单测可直接引用而不触发 SharedJsScope 初始化（后者会访问 appCtx）。
     */
    internal object CryptoRandomPatch {

        private const val SECURE_RANDOM_BINDING = "__legadoSecureRandomInt"
        private val secureRandom by lazy { SecureRandom() }

        /** 用宿主 SecureRandom 回填 CryptoJS 的随机数入口。 */
        private const val SECURE_RANDOM_PATCH = """
            CryptoJS.lib.WordArray.random = (function(nextInt) {
                return function(nBytes) {
                    var words = [];
                    for (var i = 0; i < nBytes; i += 4) {
                        words.push(nextInt());
                    }
                    return CryptoJS.lib.WordArray.create(words, nBytes);
                };
            })(__legadoSecureRandomInt);
        """

        fun install(scope: Scriptable, coroutineContext: CoroutineContext?) {
            val secureRandomFunction = object : BaseFunction() {
                override fun call(
                    cx: Context?,
                    callScope: Scriptable?,
                    thisObj: Scriptable?,
                    args: Array<Any?>?
                ): Any = secureRandom.nextInt().toDouble()
            }.apply {
                parentScope = scope
                prototype = ScriptableObject.getFunctionPrototype(scope)
            }
            ScriptableObject.putProperty(scope, SECURE_RANDOM_BINDING, secureRandomFunction)
            try {
                RhinoScriptEngine.eval(SECURE_RANDOM_PATCH, scope, coroutineContext)
            } finally {
                scope.delete(SECURE_RANDOM_BINDING)
            }
        }
    }

    private fun loadCryptoJs(): String? {
        val cached = cryptoJsText
        if (cached != null) return cached
        return try {
            val text = appCtx.assets.open(CRYPTO_JS_ASSET).bufferedReader().use { it.readText() }
            cryptoJsText = text
            AppLog.putDebugWithTag(
                AppLog.TAG_CRYPTO_SCOPE,
                "asset loaded: asset=$CRYPTO_JS_ASSET, size=${text.length}",
                level = Level.INFO
            )
            text
        } catch (e: Throwable) {
            val msg = "加载CryptoJS失败: ${e.message}"
            runCatching {
                aCache.put(CRYPTO_JS_ERROR_KEY, msg)
                AppLog.putDebugWithTag(
                    AppLog.TAG_CRYPTO_SCOPE,
                    "asset load failed: ${e.message}",
                    e,
                    Level.ERROR
                )
            }
            null
        }
    }

    fun getCryptoScope(coroutineContext: CoroutineContext?): Scriptable? {
        val cached = cryptoScope?.get()
        if (cached != null) {
            // F9/2.19：高频命中路径 1/50 采样（原逐次 INFO=真机日志 1211 条噪音源）
            AppLog.putSampled(
                "CryptoScope_cache_hit",
                "cache hit: scope=${cached::class.simpleName}",
                n = 50,
                level = Level.DEBUG,
                tag = AppLog.TAG_CRYPTO_SCOPE
            )
            return cached
        }
        synchronized(cryptoLock) {
            val second = cryptoScope?.get()
            if (second != null) return second
            loadCryptoJs() ?: return null
            val scope = RhinoScriptEngine.getRuntimeScope(ScriptBindings())
            try {
                evalCryptoJs(scope, coroutineContext)
            } catch (e: Throwable) {
                AppLog.putDebugWithTag(
                    AppLog.TAG_CRYPTO_SCOPE,
                    "eval failed: ${e.message}",
                    e,
                    Level.ERROR
                )
                return null
            }
            if (scope is ScriptableObject) {
                scope.preventExtensions()
            }
            cryptoScope = WeakReference(scope)
            return scope
        }
    }

    /**
     * 把 CryptoJS 注入指定脚本作用域。
     * 单文件 JS 书源导入期需在临时作用域解析 `config`（含加密字段），此时缓存作用域不可复用。
     */
    fun installCryptoJs(scope: Scriptable, coroutineContext: CoroutineContext?) {
        runCatching { evalCryptoJs(scope, coroutineContext) }
    }

    fun getScope(jsLib: String?, coroutineContext: CoroutineContext?): Scriptable? {
        if (jsLib.isNullOrBlank()) {
            return null
        }
        val key = MD5Utils.md5Encode(jsLib)
        var scope = scopeMap[key]?.get()
        if (scope == null) {
            scope = RhinoScriptEngine.run {
                getRuntimeScope(ScriptBindings())
            }
            loadCryptoJs()?.let {
                runCatching { evalCryptoJs(scope, coroutineContext) }
            }
            if (jsLib.isJsonObject()) {
                // ng-js-source-port：新版 JSON jsLib 支持「内联资源包」
                // （format=legado.js.library/1 + scripts + resources），与旧
                // 「Map<String,String>（值为 URL）」语义并存：识别成功走资源包，否则保持原逻辑。
                val bundle = JsLibraryBundle.parse(jsLib)
                if (bundle != null) {
                    bundle.scripts.forEach { script ->
                        RhinoScriptEngine.eval(script, scope, coroutineContext)
                    }
                } else {
                    val jsMap: Map<String, String> = GSON.fromJson(
                        jsLib,
                        TypeToken.getParameterized(
                            Map::class.java,
                            String::class.java,
                            String::class.java
                        ).type
                    )
                    jsMap.values.forEach { value ->
                        if (value.isAbsUrl()) {
                            val fileName = MD5Utils.md5Encode(value)
                            var js = aCache.getAsString(fileName)
                            if (js == null) {
                                js = runBlocking {
                                    okHttpClient.newCallStrResponse {
                                        url(value)
                                    }.body
                                }
                                if (js != null) {
                                    aCache.put(fileName, js)
                                } else {
                                    throw NoStackTraceException("下载jsLib-${value}失败")
                                }
                            }
                            RhinoScriptEngine.eval(js, scope, coroutineContext)
                        }
                    }
                }
            } else {
                RhinoScriptEngine.eval(jsLib, scope, coroutineContext)
            }
            if (scope is ScriptableObject) {
                /**
                 * 阻止新全局增加（即函数内未用var的隐性全局变量创建）,会直接隐性创建失败,提示变量未定义
                 */
                scope.preventExtensions()
            }
            scopeMap.put(key, WeakReference(scope))
        }
        return scope
    }

    fun remove(jsLib: String?) {
        if (jsLib.isNullOrBlank()) {
            return
        }
        if (jsLib.isJsonObject()) {
            // 资源包（legado.js.library/1）没有 URL 缓存项，只需清作用域缓存；
            // 不能按 Map<String,String> 解析（值是数组/对象会抛异常并中断删除流程）。
            if (runCatching { JsLibraryBundle.parse(jsLib) }.getOrNull() == null) {
                val jsMap: Map<String, String> = GSON.fromJson(
                    jsLib,
                    TypeToken.getParameterized(
                        Map::class.java,
                        String::class.java,
                        String::class.java
                    ).type
                )
                jsMap.values.forEach { value ->
                    if (value.isAbsUrl()) {
                        val fileName = MD5Utils.md5Encode(value)
                        aCache.remove(fileName)
                    }
                }
            }
        }
        val key = MD5Utils.md5Encode(jsLib)
        scopeMap.remove(key)
    }

}