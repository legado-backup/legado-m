package io.legado.app.data.entities.rule

import com.google.gson.annotations.SerializedName

data class RowUi(
    val name: String = "",
    val type: String = "text",
    val action: String? = null,
    val chars: Array<String?>? = null,
    val default: String? = null,
    var viewName: String? = null,
    val style: FlexChildStyle? = null,
    // ---- 动态登录 V2（NG 单文件 JS 源 loginUi 渲染协议）新增字段，老书源不填即为 null ----
    /** 字段键名：V2 用 key 提交表单值，区别于老版按 name 绑定 */
    @SerializedName("key")
    val key: String? = null,
    /** 输入提示 */
    @SerializedName("hint")
    val hint: String? = null,
    /** 初始值 / toggle 的 "true"/"false" */
    @SerializedName("value")
    val value: String? = null,
    /** select 的候选项（值为显示文本） */
    @SerializedName("options")
    val options: List<String>? = null,
    /** 按钮倒计时秒数（<0 视为非法行） */
    @SerializedName("countdown")
    val countdown: Int? = null
) {

    @Suppress("ConstPropertyName")
    object Type {

        const val text = "text"
        const val password = "password"
        const val button = "button"
        const val label = "label"
        const val toggle = "toggle"
        const val select = "select"

    }

    fun style(): FlexChildStyle {
        return style ?: FlexChildStyle.defaultStyle
    }

    override fun equals(other: Any?): Boolean {
        if (other is RowUi) {
            return other.name == name
                    && other.type == type
                    && other.action == action
                    && other.default == default
        }
        return false
    }

    override fun hashCode(): Int {
        var result = name.hashCode() + type.hashCode()
        result = 31 * result + (action?.hashCode() ?: 0)
        result = 31 * result + (default?.hashCode() ?: 0)
        return result
    }

}