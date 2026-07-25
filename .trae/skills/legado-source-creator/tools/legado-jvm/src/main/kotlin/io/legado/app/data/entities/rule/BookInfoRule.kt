package io.legado.app.data.entities.rule

import com.google.gson.JsonDeserializer
import io.legado.app.utils.INITIAL_GSON
import java.io.Serializable

// 简化说明：移除 @Parcelize/: Parcelable，改为 Serializable | 已知上限：失去 Parcelable 高效序列化 | 升级路径：无
/**
 * 书籍详情页规则
 */
data class BookInfoRule(
    var init: String? = null,
    var name: String? = null,
    var author: String? = null,
    var intro: String? = null,
    var kind: String? = null,
    var lastChapter: String? = null,
    var updateTime: String? = null,
    var coverUrl: String? = null,
    var tocUrl: String? = null,
    var wordCount: String? = null,
    var canReName: String? = null,
    var downloadUrls: String? = null
) : Serializable {

    companion object {

        val jsonDeserializer = JsonDeserializer<BookInfoRule?> { json, _, _ ->
            when {
                json.isJsonObject -> INITIAL_GSON.fromJson(json, BookInfoRule::class.java)
                json.isJsonPrimitive -> INITIAL_GSON.fromJson(
                    json.asString,
                    BookInfoRule::class.java
                )
                else -> null
            }
        }

    }

}
