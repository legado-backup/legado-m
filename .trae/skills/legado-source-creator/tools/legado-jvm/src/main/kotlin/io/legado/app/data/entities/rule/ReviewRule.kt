package io.legado.app.data.entities.rule

import com.google.gson.JsonDeserializer
import io.legado.app.utils.INITIAL_GSON
import java.io.Serializable

// 简化说明：移除 @Parcelize/: Parcelable，改为 Serializable | 已知上限：失去 Parcelable 高效序列化 | 升级路径：无
data class ReviewRule(
    var reviewUrl: String? = null,          // 段评URL
    var avatarRule: String? = null,         // 段评发布者头像
    var contentRule: String? = null,        // 段评内容
    var postTimeRule: String? = null,       // 段评发布时间
    var reviewQuoteUrl: String? = null,     // 获取段评回复URL

    // 这些功能将在以上功能完成以后实现
    var voteUpUrl: String? = null,          // 点赞URL
    var voteDownUrl: String? = null,        // 点踩URL
    var postReviewUrl: String? = null,      // 发送回复URL
    var postQuoteUrl: String? = null,       // 发送回复段评URL
    var deleteUrl: String? = null,          // 删除段评URL
) : Serializable {

    companion object {

        val jsonDeserializer = JsonDeserializer<ReviewRule?> { json, _, _ ->
            when {
                json.isJsonObject -> INITIAL_GSON.fromJson(json, ReviewRule::class.java)
                json.isJsonPrimitive -> INITIAL_GSON.fromJson(json.asString, ReviewRule::class.java)
                else -> null
            }
        }

    }

}
