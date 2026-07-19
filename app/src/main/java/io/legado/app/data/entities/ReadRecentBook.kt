package io.legado.app.data.entities

import androidx.room.Entity
import androidx.room.PrimaryKey
import kotlinx.parcelize.Parcelize

/**
 * 最近阅读记录实体（VIDEO-E-01）。
 *
 * 借鉴 Archive `ReadRecentBook`：记录用户最近阅读的书籍 bookUrl + 时间戳，
 * 用于"最近阅读"页面展示。视频书播放时写入此表，使视频书出现在最近阅读列表。
 *
 * - @Parcelize 遵循项目 Room 实体规范（与 Book/BookChapter/BookGroup 等一致）
 * - @PrimaryKey bookUrl 唯一标识，重复插入覆盖（OnConflictStrategy.REPLACE）
 * - lastRead 默认值 System.currentTimeMillis() 确保向后兼容
 *
 * 关联任务：VIDEO-E-01（P0）视频书最近阅读记录写入。
 */
@Parcelize
@Entity(tableName = "readRecentBooks")
data class ReadRecentBook(
    @PrimaryKey
    val bookUrl: String,
    val lastRead: Long = System.currentTimeMillis()
) : android.os.Parcelable
