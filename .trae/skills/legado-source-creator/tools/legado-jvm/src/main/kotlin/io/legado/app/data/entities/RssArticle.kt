package io.legado.app.data.entities

import io.legado.app.utils.GSON
import io.legado.app.utils.fromJsonObject
import java.io.Serializable

// 源码参照: app/src/main/java/io/legado/app/data/entities/RssArticle.kt
// 简化说明: 移除 Room 注解(@Entity/@ColumnInfo)/Parcelable/@Parcelize，仅保留 AnalyzeRule 使用的字段 | 已知上限: 失去 Room 持久化、Parcelable 序列化 | 升级路径: 需要持久化时接入 Room

@Suppress("unused")
data class RssArticle(
    override var origin: String = "",
    var sort: String = "",
    var title: String = "",
    var order: Long = 0,
    override var link: String = "",
    var pubDate: String? = null,
    var description: String? = null,
    var content: String? = null,
    var image: String? = null,
    var group: String = "默认分组",
    var read: Boolean = false,
    override var variable: String? = null,
    /**类型 0网页，1图片，2视频**/
    var type: Int = 0,
    /**阅读进度**/
    var durPos: Int = 0
) : Serializable, BaseRssArticle {

    override fun hashCode() = link.hashCode()

    override fun equals(other: Any?): Boolean {
        other ?: return false
        return if (other is RssArticle) origin == other.origin && link == other.link && sort == other.sort else false
    }

    override val variableMap: HashMap<String, String> by lazy {
        GSON.fromJsonObject<HashMap<String, String>>(variable).getOrNull() ?: hashMapOf()
    }

}
