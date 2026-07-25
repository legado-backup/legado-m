package io.legado.app.data.entities

import io.legado.app.model.analyzeRule.RuleDataInterface
import io.legado.app.utils.GSON
import io.legado.app.utils.fromJsonObject
import java.io.Serializable

// 源码参照: app/src/main/java/io/legado/app/data/entities/BookChapter.kt
// 简化说明: 移除 Room 注解(@Entity/@ForeignKey/@Index)/Parcelable/@Parcelize，仅保留 AnalyzeRule 使用的字段 | 已知上限: 失去 Room 持久化、Parcelable 序列化 | 升级路径: 需要持久化时接入 Room

@Suppress("unused")
data class BookChapter(
    var url: String = "",               // 章节地址
    var title: String = "",             // 章节标题
    var isVolume: Boolean = false,      // 是否是卷名
    var baseUrl: String = "",           // 用来拼接相对url
    var bookUrl: String = "",           // 书籍地址
    var index: Int = 0,                 // 章节序号
    var isVip: Boolean = false,         // 是否VIP
    var isPay: Boolean = false,         // 是否已购买
    var resourceUrl: String? = null,    // 音频真实URL
    var tag: String? = null,            // 更新时间或其他章节附加信息
    var wordCount: String? = null,      // 本章节字数
    var start: Long? = null,            // 章节起始位置
    var end: Long? = null,              // 章节终止位置
    var startFragmentId: String? = null,  //EPUB书籍当前章节的fragmentId
    var endFragmentId: String? = null,    //EPUB书籍下一章节的fragmentId
    var variable: String? = null,        //变量
    var imgUrl: String? = null           // 标题段评图或者视频封面
) : Serializable, RuleDataInterface {

    override val variableMap: HashMap<String, String> by lazy {
        variable?.let { GSON.fromJsonObject<HashMap<String, String>>(it).getOrNull() } ?: hashMapOf()
    }

    override fun putBigVariable(key: String, value: String?) {
        // 简化说明：putBigVariable 简化为空实现 | 已知上限：大数据变量不持久化 | 升级路径：接入 RuleBigDataHelp
    }

    override fun getBigVariable(key: String): String? {
        // 简化说明：getBigVariable 简化为返回 null | 已知上限：无法读取大数据变量 | 升级路径：接入 RuleBigDataHelp
        return null
    }

}
