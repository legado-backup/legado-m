package io.legado.app.data.dao

import androidx.room.*
import androidx.sqlite.db.SupportSQLiteQuery
import io.legado.app.data.entities.RssStar
import kotlinx.coroutines.flow.Flow

@Dao
interface RssStarDao {

    @get:Query("select * from rssStars order by starTime desc")
    val all: List<RssStar>

    @Query("select `group` from rssStars group by `group` order by `group`")
    fun flowGroups(): Flow<List<String>>

    // ui-theme-gap-audit R1：收藏列表主查询不再 select 大字段（image/content/description/variable），
    // 封面图改为列表项按需单行读取（与订阅文章列表保持一致），
    // 防止大图 base64 多行 select 挤满 CursorWindow 2MB 窗口导致读取失败。
    // 「单行」也不再视为绝对安全（真机实证单行 >2MB ⇒ SQLiteBlobTooBigException）：
    // 单行读取统一走 [readLargeField] 的「length 预判 + 分块 substr」。
    @Query(
        """select origin, sort, title, starTime, link, pubDate, `group`, type, durPos
        from rssStars where `group` = :group order by starTime desc"""
    )
    fun flowByGroup(group: String): Flow<List<RssStar>>

    /**
     * 摘要查询（**不含** image/description/content/variable 四个大字段）。
     *
     * 与文章表同因：CursorWindow 单行上限约 2MB，`select *` 单行超限即抛
     * `SQLiteBlobTooBigException`。完整内容由 [get] 的默认实现按块补齐。
     */
    @Query(
        """select origin, sort, title, starTime, link, pubDate, `group`, type, durPos
        from rssStars where origin = :origin and link = :link"""
    )
    suspend fun getSummary(origin: String, link: String): RssStar?

    // ==================== 对外读写入口（默认实现，全部走安全大字段通道） ====================
    // 与 RssArticleDao 同口径：把"安全读取"固化成 DAO 公开 API，调用方无法绕过。

    /** 完整收藏（含四个大字段；超大内容按块读取，不崩溃、不裁剪）。 */
    suspend fun get(origin: String, link: String): RssStar? =
        getSummary(origin, link)?.let { fillLargeFields(it) }

    /** 收藏列表封面图（主查询已剥离 `image` ⇒ 逐项按需单行读取，同样防单行超窗）。 */
    suspend fun getImage(origin: String, link: String): String? =
        readLargeField(origin, link, RssLargeColumn.IMAGE)

    // ==================== 大字段安全读取（R5：单行超窗修复） ====================

    /** 执行返回单个标量文本的原始查询（仅 [readLargeField] 内部使用）。 */
    @RawQuery
    suspend fun rawText(query: SupportSQLiteQuery): String?

    /** 执行返回单个标量数字的原始查询（仅 [readLargeField] 内部使用）。 */
    @RawQuery
    suspend fun rawLong(query: SupportSQLiteQuery): Long?

    // B27 退役（2026-10-16）：`liveAll()`（全表 Flow）零调用 ⇒ 活读取面＝`all`（@get:Query List）
    // 与 `flowByGroup(group)`（列表主查询，已按需裁剪大字段）。

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    fun insert(vararg rssStar: RssStar)

    @Update
    fun update(vararg rssStar: RssStar)

    @Query("update rssStars set origin = :origin where origin = :oldOrigin")
    fun updateOrigin(origin: String, oldOrigin: String)

    @Query("delete from rssStars where origin = :origin")
    fun delete(origin: String)

    @Query("delete from rssStars where origin = :origin and link = :link")
    fun delete(origin: String, link: String)

    @Query("delete from rssStars where `group` = :group")
    fun deleteByGroup(group: String)

    @Query("delete from rssStars")
    fun deleteAll()
}