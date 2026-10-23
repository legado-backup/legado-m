package io.legado.app.data.dao

import androidx.room.*
import androidx.sqlite.db.SupportSQLiteQuery
import io.legado.app.data.entities.RssArticle
import kotlinx.coroutines.flow.Flow

@Dao
interface RssArticleDao {

    /**
     * 摘要查询（**不含** image/description/content/variable 四个大字段）。
     *
     * 为什么：CursorWindow 单行上限约 2MB，四个大字段任一单行超限即抛
     * `SQLiteBlobTooBigException`（2026-10-20 真机崩溃栈顶为 `getImage`）。
     * 需要完整内容时由 [get]/[getByLink] 的默认实现按块读取补齐（见 [readLargeField]）。
     */
    @Query(
        """select origin, sort, title, `order`, link, pubDate, `group`, read, type, durPos
        from rssArticles where origin = :origin and link = :link and sort = :sort"""
    )
    suspend fun getSummary(origin: String, link: String, sort: String): RssArticle?

    /** 摘要查询（按 origin+link，不含 sort；语义同 [getSummary]）。 */
    @Query(
        """select origin, sort, title, `order`, link, pubDate, `group`, read, type, durPos
        from rssArticles where origin = :origin and link = :link"""
    )
    suspend fun getSummaryByLink(origin: String, link: String): RssArticle?

    // ==================== 对外读写入口（默认实现，全部走安全大字段通道） ====================
    // Room 不支持在 @RawQuery / @Query 里做"先探长度再分块"，故这里用**接口默认方法**
    // 把"安全读取"固化成 DAO 自身的公开 API ⇒ 任何调用方都**不可能**绕过（这也是本轮
    // 把散点调用改成集中的原因：散点改法每加一处新调用就重新引入崩溃风险）。

    /** 存在性判定（翻页去重探针；不带任何大字段，比 `get(...) != null` 省 4 次大字段读取）。 */
    @Query("select exists(select 1 from rssArticles where origin = :origin and link = :link and sort = :sort)")
    fun exists(origin: String, link: String, sort: String): Boolean

    /** 完整文章（含四个大字段；超大内容按块读取，不崩溃、不裁剪）。 */
    suspend fun get(origin: String, link: String, sort: String): RssArticle? =
        getSummary(origin, link, sort)?.let { fillLargeFields(it) }

    /** 完整文章（按 origin+link；语义同 [get]）。 */
    suspend fun getByLink(origin: String, link: String): RssArticle? =
        getSummaryByLink(origin, link)?.let { fillLargeFields(it) }

    /**
     * 列表封面图（订阅文章列表主查询已剥离 `image` ⇒ 逐项按需单行读取）。
     * 单行也走"length 预判 + 分块"，防真机实证过的"单行超窗"崩溃。
     */
    suspend fun getImage(origin: String, link: String): String? =
        readLargeField(origin, link, null, RssLargeColumn.IMAGE)

    /**
     * 批量查询指定 origin 下已读的 link 列表（rss-unified-search 新增）
     *
     * 用于订阅源统一搜索结果已读状态判断：
     * - 搜索结果来自网络返回，read 字段默认 false
     * - 通过此方法查询 rssArticles 表中已读的文章 link，批量判断已读
     *
     * @param origin 订阅源 sourceUrl
     * @param links 搜索结果中的文章 link 列表
     * @return 已读的 link 列表（子集）
     */
    @Query("select link from rssArticles where origin = :origin and link in (:links) and read = 1")
    fun getReadLinks(origin: String, links: List<String>): List<String>

    // ==================== 大字段安全读取（R5：单行超窗修复） ====================
    // 列名与 SQL 一律由 [RssLargeColumn] 白名单 + [readLargeField] 构造，禁止外部拼接。

    /** 执行返回单个标量文本的原始查询（仅 [readLargeField] 内部使用）。 */
    @RawQuery
    suspend fun rawText(query: SupportSQLiteQuery): String?

    /** 执行返回单个标量数字的原始查询（仅 [readLargeField] 内部使用）。 */
    @RawQuery
    suspend fun rawLong(query: SupportSQLiteQuery): Long?

    // R4.3 修复：去掉 t1.content 字段（大文章 content 超 CursorWindow 2MB 限制）
    // app-stability-round2 P1-1 修复：再去掉 t1.description 字段（部分源 description 也可能超大触发 SQLiteBlobTooBigException）
    // rss-parse-optimization P0 修复：再去掉 t1.variable 字段（部分源 variable JSON 超大导致 CursorWindow 溢出 30+次/会话）
    // ui-theme-gap-audit R1 修复：image 字段部分源存 base64 数据图，多行大图一次性 select
    // 会挤满 CursorWindow 2MB 窗口 → 单行分配失败 → 订阅文章界面获取数据失败。
    // 列表主查询不再 select image（大图改为列表项按需读取）。
    // ⚠️「单行绝对安全」的假设已被真机推翻（2026-10-20 崩溃：单行 image 超 CursorWindow）⇒
    // 单行读取统一走 [readLargeField]（length 预判 + 分块 substr），摘要查询走 [getSummary]/[getSummaryByLink]。
    @Query(
        """select t1.link, t1.sort, t1.origin, t1.`order`, t1.title,
            t1.`group`, t1.pubDate, t1.type, t1.durPos, ifNull(t2.read, 0) as read
        from rssArticles as t1 left join rssReadRecords as t2
        on t1.link = t2.record  where t1.origin = :origin and t1.sort = :sort
        order by `order` desc"""
    )
    fun flowByOriginSort(origin: String, sort: String): Flow<List<RssArticle>>

    /**
     * 同源同分类文章列表（一次性读取版，无 Flow）。
     *
     * 用途：`ReadRssViewModel` 的「正文含视频自动转内置播放器」路由只有**单篇文章**上下文，
     * 直接写入会让 `VideoPlay.rssArticles` 退化为 1 篇，击穿播放器侧 `size > 1` 的
     * 文章模式判定（沉浸式上下滑切视频 / 传统式上一部下一部**同时失效**）。
     * 本查询补齐与列表页 `flowByOriginSort` **同口径**的上下文（同样不 select
     * content/description/image/variable，规避 CursorWindow 2MB 溢出）。
     */
    @Query(
        """select t1.link, t1.sort, t1.origin, t1.`order`, t1.title,
            t1.`group`, t1.pubDate, t1.type, t1.durPos, ifNull(t2.read, 0) as read
        from rssArticles as t1 left join rssReadRecords as t2
        on t1.link = t2.record  where t1.origin = :origin and t1.sort = :sort
        order by `order` desc"""
    )
    suspend fun getListByOriginSort(origin: String, sort: String): List<RssArticle>

    /**
     * F28（ui-subpage-optimization）：存在未读文章的订阅源集合（sourceUrl 去重）。
     *
     * 未读口径与列表主查询 [flowByOriginSort] 完全一致——rssArticles.read 列无写入方，
     * 真实已读态由 rssReadRecords（record = link）承担，故「无对应阅读记录」即未读。
     * 返回量级 = 源数量级，供订阅页源卡未读标记一次性取用（不逐项查询）。
     */
    @Query(
        """select distinct t1.origin from rssArticles as t1
        left join rssReadRecords as t2 on t1.link = t2.record
        where t2.record is null"""
    )
    suspend fun getUnreadOrigins(): List<String>

    /**
     * F143（ui-subpage-optimization）：按分类聚合未读数，供分类 Tab 未读徽标使用。
     *
     * 未读口径与列表主查询 [flowByOriginSort] 完全一致——rssArticles.read 列无写入方，
     * 真实已读态由 rssReadRecords（record = link）承担，故「无对应阅读记录」即未读。
     * 聚合在库内完成（group by sort，命中 idx_origin_sort 索引），返回量级 = 分类数，
     * 不逐分类查询、不拉整表。Flow 版：文章入库/已读记录变化时自动重算，徽标无陈旧窗口。
     */
    @Query(
        """select t1.sort as sort, count(*) as unreadCount from rssArticles as t1
        left join rssReadRecords as t2 on t1.link = t2.record
        where t1.origin = :origin and t2.record is null
        group by t1.sort"""
    )
    fun flowUnreadCountBySort(origin: String): Flow<List<RssUnreadSortCount>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    fun insert(vararg rssArticle: RssArticle)

    @Insert(onConflict = OnConflictStrategy.IGNORE)
    fun append(vararg rssArticle: RssArticle)

    @Query("delete from rssArticles where origin = :origin and sort = :sort and `order` < :order")
    fun clearOld(origin: String, sort: String, order: Long)

    @Update
    fun update(vararg rssArticle: RssArticle)

    @Query("update rssArticles set origin = :origin where origin = :oldOrigin")
    fun updateOrigin(origin: String, oldOrigin: String)

    @Query("delete from rssArticles where origin = :origin")
    fun delete(origin: String)

}

/** F143：分类未读聚合投影（sort 与 rssArticles.sort 同口径，即分类 Tab 名） */
data class RssUnreadSortCount(
    val sort: String,
    val unreadCount: Int
)