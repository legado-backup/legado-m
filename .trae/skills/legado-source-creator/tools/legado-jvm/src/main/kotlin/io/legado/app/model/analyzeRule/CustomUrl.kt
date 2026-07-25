package io.legado.app.model.analyzeRule

import io.legado.app.utils.GSON
import io.legado.app.utils.fromJsonObject
import java.util.regex.Pattern

@Suppress("unused")
class CustomUrl(url: String) {

    private val mUrl: String
    private val attribute = hashMapOf<String, Any>()

    init {
        val urlMatcher = paramPattern.matcher(url)
        mUrl = if (urlMatcher.find()) {
            val attr = url.substring(urlMatcher.end())
            GSON.fromJsonObject<Map<String, Any>>(attr).getOrNull()?.let {
                attribute.putAll(it)
            }
            url.take(urlMatcher.start())
        } else {
            url
        }
    }

    fun putAttribute(key: String, value: Any?): CustomUrl {
        if (value == null) {
            attribute.remove(key)
        } else {
            attribute[key] = value
        }
        return this
    }

    fun getUrl(): String {
        return mUrl
    }

    fun getAttr(): Map<String, Any> {
        return attribute
    }

    override fun toString(): String {
        if (attribute.isEmpty()) {
            return mUrl
        }
        return mUrl + "," + GSON.toJson(attribute)
    }

    companion object {
        // 简化说明：从 AnalyzeUrl.kt#L768 内联，避免依赖 AnalyzeUrl（D级类，阶段二抽取） | 已知上限：无 | 升级路径：阶段二抽取 AnalyzeUrl 后可改回引用
        private val paramPattern: Pattern = Pattern.compile("\\s*,\\s*(?=\\{)")
    }

}
