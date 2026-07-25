package io.legado.app.data.entities

import io.legado.app.utils.GSON
import io.legado.app.utils.fromJsonObject
import java.io.Serializable

// 源码参照: app/src/main/java/io/legado/app/data/entities/Book.kt
// 简化说明: 移除 Room 注解(@Entity/@PrimaryKey/@ColumnInfo/@TypeConverters)/Parcelable/@Parcelize/ReadConfig 嵌套类，保留源码字段 | 已知上限: 失去 Room 持久化、Parcelable 序列化、ReadConfig 配置 | 升级路径: 需要持久化时接入 Room

@Suppress("unused")
data class Book(
    // 详情页Url(本地书源存储完整文件路径)
    override var bookUrl: String = "",
    // 目录页Url (toc=table of Contents)
    var tocUrl: String = "",
    // 书源URL(默认BookType.local)
    var origin: String = "local",
    //书源名称 or 本地书籍文件名
    var originName: String = "",
    // 书籍名称(书源获取)
    override var name: String = "",
    // 作者名称(书源获取)
    override var author: String = "",
    // 分类信息(书源获取)
    override var kind: String? = null,
    // 分类信息(用户修改)
    var customTag: String? = null,
    // 封面Url(书源获取)
    var coverUrl: String? = null,
    // 封面Url(用户修改)
    var customCoverUrl: String? = null,
    // 简介内容(书源获取)
    var intro: String? = null,
    // 简介内容(用户修改)
    var customIntro: String? = null,
    // 自定义字符集名称(仅适用于本地书籍)
    var charset: String? = null,
    // 类型,详见BookType
    var type: Int = 0,
    // 自定义分组索引号
    var group: Long = 0,
    // 最新章节标题
    var latestChapterTitle: String? = null,
    // 最新章节标题更新时间
    var latestChapterTime: Long = System.currentTimeMillis(),
    // 最近一次更新书籍信息的时间
    var lastCheckTime: Long = System.currentTimeMillis(),
    // 最近一次发现新章节的数量
    var lastCheckCount: Int = 0,
    // 书籍目录总数
    var totalChapterNum: Int = 0,
    // 当前章节名称
    var durChapterTitle: String? = null,
    // 当前章节索引
    var durChapterIndex: Int = 0,
    // 当前卷索引
    var durVolumeIndex: Int = 0,
    // 相对于卷的索引
    var chapterInVolumeIndex: Int = 0,
    // 当前阅读的进度(首行字符的索引位置)
    var durChapterPos: Int = 0,
    // 最近一次阅读书籍的时间(打开正文的时间)
    var durChapterTime: Long = System.currentTimeMillis(),
    //字数
    override var wordCount: String? = null,
    // 刷新书架时更新书籍信息
    var canUpdate: Boolean = true,
    // 手动排序
    var order: Int = 0,
    //书源排序
    var originOrder: Int = 0,
    // 自定义书籍变量信息(用于书源规则检索书籍信息)
    override var variable: String? = null,
    //同步时间
    var syncTime: Long = 0L,
    //详情页HTML
    override var infoHtml: String? = null,
    //目录页HTML
    override var tocHtml: String? = null
) : Serializable, BaseBook {

    override fun equals(other: Any?): Boolean {
        if (other is Book) {
            return other.bookUrl == bookUrl
        }
        return false
    }

    override fun hashCode(): Int {
        return bookUrl.hashCode()
    }

    override val variableMap: HashMap<String, String> by lazy {
        GSON.fromJsonObject<HashMap<String, String>>(variable).getOrNull() ?: hashMapOf()
    }

}
