package io.legado.app.data.dao

import androidx.sqlite.db.SimpleSQLiteQuery
import io.legado.app.data.entities.RssArticle
import io.legado.app.data.entities.RssStar
import io.legado.app.help.rss.RssLargeFieldReader

/**
 * 订阅表大字段（封面 / 正文 / 描述 / 变量）的**安全读取与补齐**。
 *
 * ### 背景（2026-10-20 真机崩溃）
 * `SQLiteBlobTooBigException: Row too big to fit into CursorWindow` —— CursorWindow 单行上限
 * 约 2MB，只要结果集里**含**某个超大列，该行整行就装不进窗口。此前只把「多行聚合查询」里的
 * 大字段去掉，单行查询仍用 `select image` / `select *` ⇒ 单行超限必崩。
 *
 * ### 做法
 * - 摘要查询（[RssArticleDao.getSummary]/[getSummaryByLink]、[RssStarDao.getSummary]）**不带**大字段；
 * - 需要完整内容时调用 [fillLargeFields]，其内部经 [RssLargeFieldReader] 先 `length()` 预判、超阈值按块
 *   `substr` 拼接 ⇒ **完整读取、不裁剪、不置空**；异常/超上限时返回 null（既不崩也不静默截断）。
 *
 * ### 安全约束
 * 列名只允许来自 [RssLargeColumn] 白名单（编译期枚举），SQL 其余部分为固定字面量，
 * **不存在**外部输入拼接进列名的路径。
 */
enum class RssLargeColumn(val column: String) {
    IMAGE("image"),
    DESCRIPTION("description"),
    CONTENT("content"),
    VARIABLE("variable"),
}

/**
 * 大字段 SQL 构造（**纯函数单源**）。
 *
 * 抽出来的两个理由：①列名只允许来自 [RssLargeColumn] 白名单，集中一处便于断言；
 * ②`@RawQuery` 拿不到 Room 的编译期校验 ⇒ 用"SQL 文本可被 JVM 单测钉住"替代。
 */
internal object RssLargeFieldSql {

    private val allowedTables = setOf("rssArticles", "rssStars")

    fun lengthQuery(table: String, column: RssLargeColumn, where: String): String {
        require(table in allowedTables) { "非法订阅表：$table" }
        return "select length(${column.column}) from $table where $where limit 1"
    }

    fun chunkQuery(table: String, column: RssLargeColumn, where: String): String {
        require(table in allowedTables) { "非法订阅表：$table" }
        return "select substr(${column.column}, ?, ?) from $table where $where limit 1"
    }
}

/** 文章表大字段读取（`sort` 为 null 时按 `origin + link` 定位）。 */
suspend fun RssArticleDao.readLargeField(
    origin: String,
    link: String,
    sort: String?,
    column: RssLargeColumn,
): String? {
    val where = if (sort == null) {
        "origin = ? and link = ?"
    } else {
        "origin = ? and link = ? and sort = ?"
    }
    val keyArgs = if (sort == null) {
        arrayOf<Any?>(origin, link)
    } else {
        arrayOf<Any?>(origin, link, sort)
    }
    return RssLargeFieldReader.read(
        lengthOf = {
            rawLong(
                SimpleSQLiteQuery(
                    RssLargeFieldSql.lengthQuery("rssArticles", column, where),
                    keyArgs
                )
            )
        },
        chunk = { offset, count ->
            rawText(
                SimpleSQLiteQuery(
                    RssLargeFieldSql.chunkQuery("rssArticles", column, where),
                    arrayOf<Any?>(offset + 1, count, *keyArgs)
                )
            )
        }
    )
}

/**
 * 补齐 [RssArticle] 的四个大字段（摘要查询已剥离，这里按需完整读回）。
 *
 * 用于详情/正文/播放器/JS 规则等**确实需要完整内容**的路径；列表渲染请继续按需只取 `image`。
 */
suspend fun RssArticleDao.fillLargeFields(article: RssArticle): RssArticle {
    article.image = readLargeField(article.origin, article.link, article.sort, RssLargeColumn.IMAGE)
    article.description =
        readLargeField(article.origin, article.link, article.sort, RssLargeColumn.DESCRIPTION)
    article.content = readLargeField(article.origin, article.link, article.sort, RssLargeColumn.CONTENT)
    article.variable =
        readLargeField(article.origin, article.link, article.sort, RssLargeColumn.VARIABLE)
    return article
}

/** 封面图（订阅文章列表项按需读取，供 DAO 默认方法 `getImage` 使用）。 */
suspend fun RssArticleDao.readImageField(origin: String, link: String): String? =
    readLargeField(origin, link, null, RssLargeColumn.IMAGE)

/** 封面图（收藏列表项按需读取，供 DAO 默认方法 `getImage` 使用）。 */
suspend fun RssStarDao.readImageField(origin: String, link: String): String? =
    readLargeField(origin, link, RssLargeColumn.IMAGE)

/** 收藏表大字段读取（`rssStars` 主键为 `origin + link`）。 */
suspend fun RssStarDao.readLargeField(
    origin: String,
    link: String,
    column: RssLargeColumn,
): String? {
    val keyArgs = arrayOf<Any?>(origin, link)
    return RssLargeFieldReader.read(
        lengthOf = {
            rawLong(
                SimpleSQLiteQuery(
                    RssLargeFieldSql.lengthQuery("rssStars", column, "origin = ? and link = ?"),
                    keyArgs
                )
            )
        },
        chunk = { offset, count ->
            rawText(
                SimpleSQLiteQuery(
                    RssLargeFieldSql.chunkQuery("rssStars", column, "origin = ? and link = ?"),
                    arrayOf<Any?>(offset + 1, count, *keyArgs)
                )
            )
        }
    )
}

/** 补齐 [RssStar] 的四个大字段（语义同 [fillLargeFields]）。 */
suspend fun RssStarDao.fillLargeFields(star: RssStar): RssStar {
    star.image = readLargeField(star.origin, star.link, RssLargeColumn.IMAGE)
    star.description = readLargeField(star.origin, star.link, RssLargeColumn.DESCRIPTION)
    star.content = readLargeField(star.origin, star.link, RssLargeColumn.CONTENT)
    star.variable = readLargeField(star.origin, star.link, RssLargeColumn.VARIABLE)
    return star
}
