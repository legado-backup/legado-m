package io.legado.app.data.entities

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.PrimaryKey


@Entity(tableName = "txtTocRules")
data class TxtTocRule(
    @PrimaryKey
    var id: Long = System.currentTimeMillis(),
    var name: String = "",
    var rule: String = "",
    @ColumnInfo(defaultValue = "")
    var replacement: String = "",
    var example: String? = null,
    var serialNumber: Int = -1,
    var enable: Boolean = true
) {

    override fun hashCode(): Int {
        return id.hashCode()
    }

    override fun equals(other: Any?): Boolean {
        if (other is TxtTocRule) {
            return id == other.id
        }
        return false
    }

    /**
     * 导入比较：同 id 时判断业务字段是否完全一致。
     * 不能用 [equals]（它只比主键 id），否则同 id 但内容更新的规则包永远被判"已存在"。
     * 新增业务字段时必须同步补进这里。
     */
    fun hasSameImportContent(other: TxtTocRule): Boolean {
        return name == other.name &&
                rule == other.rule &&
                replacement == other.replacement &&
                example == other.example &&
                serialNumber == other.serialNumber &&
                enable == other.enable
    }

}