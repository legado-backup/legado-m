package io.legado.app.help.rss

import io.legado.app.constant.AppLog
import kotlinx.coroutines.CancellationException

/**
 * 订阅大字段（封面图 / 正文 / 描述 / 变量）**安全读取器**。
 *
 * ### 为什么需要
 * 部分订阅源把封面存成 base64 数据图、把正文/变量存成超大 JSON。Android 的 `CursorWindow`
 * 单行有上限（约 2MB），**单行**超限即抛
 * `SQLiteBlobTooBigException: Row too big to fit into CursorWindow`
 * （2026-10-20 真机崩溃栈顶即 `RssArticleDao.getImage` ⇒ 只拆「多行聚合」并不能防住「单行超大」）。
 *
 * ### 怎么解
 * 先 `length(col)` 取**字符数**：
 * - 未超 [ChunkChars] ⇒ **一次取回**（与改造前逐字节一致，常规字段零行为变化）；
 * - 超阈值 ⇒ 按 [ChunkChars] 分块 `substr` 拼接，**完整保留内容、不裁剪、不置空**。
 *
 * ### 口径与边界
 * - `length()` 对 TEXT 返回**字符数**，而 CursorWindow 限制是**字节**：UTF-8 中文 3 字节/字符 ⇒
 *   256K 字符最坏 ≈768KB 字节，仍远低于 2MB，故「阈值 = 块大小 = 256K 字符」是安全的。
 * - 分块数上限 [MaxChunks]；超限或任意查询抛错时**记日志并返回 null**（既不崩溃，也不静默截断）。
 *   返回 null 调用方已有语义：列表图片不显示、详情回落到规则/URL 取正文。
 * - 不在此处回落「一次性读取」：同一 CursorWindow 限制下它必然以同样方式失败，回落只会把异常重新引入。
 *
 * 读取逻辑与数据库解耦（入参是协程函数）⇒ 可纯 JVM 单测，无需 Room/设备。
 */
object RssLargeFieldReader {

    /** 分块大小（字符）。取 256K：最坏 UTF-8 字节量 ≈768KB，安全裕度充足。 */
    const val ChunkChars = 256 * 1024

    /** 分块数上限（64 块 ≈ 16M 字符）。超过此体量的内容已无法渲染，直接判定为不可读。 */
    const val MaxChunks = 64

    /**
     * 读取一个可能超大的文本字段。
     *
     * @param lengthOf 取字段字符数（未命中行或字段为 NULL 时返回 null）
     * @param chunk 取字段片段：`offset` 为 0 基偏移（对齐 SQLite `substr(col, offset+1, count)` 语义由调用方保证）
     */
    suspend fun read(
        lengthOf: suspend () -> Long?,
        chunk: suspend (offset: Int, count: Int) -> String?,
    ): String? {
        val length = try {
            lengthOf()
        } catch (e: CancellationException) {
            throw e
        } catch (e: Throwable) {
            AppLog.put("订阅大字段长度读取失败，按不可读处理", e)
            return null
        } ?: return null
        if (length <= 0L) return if (length == 0L) "" else null

        // 常规体量：一次取回，保持改造前的行为与内容完全一致
        if (length <= ChunkChars) {
            return try {
                chunk(0, length.toInt())
            } catch (e: CancellationException) {
                throw e
            } catch (e: Throwable) {
                AppLog.put("订阅大字段读取失败，按不可读处理", e)
                null
            }
        }

        val chunkCount = ((length + ChunkChars - 1) / ChunkChars).toInt()
        if (chunkCount > MaxChunks) {
            AppLog.put("订阅大字段超过可读上限(${MaxChunks}块/约${MaxChunks * ChunkChars}字符)，长度=$length")
            return null
        }
        val builder = StringBuilder(length.toInt())
        var offset = 0
        while (offset < length) {
            val count = minOf(ChunkChars.toLong(), length - offset).toInt()
            val piece = try {
                chunk(offset, count)
            } catch (e: CancellationException) {
                throw e
            } catch (e: Throwable) {
                AppLog.put("订阅大字段分块读取失败，按不可读处理", e)
                return null
            } ?: return null
            builder.append(piece)
            offset += count
        }
        return builder.toString()
    }
}
