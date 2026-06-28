package io.legado.app.data.entities

import io.legado.app.model.analyzeRule.RuleDataInterface
import io.legado.app.utils.GSON

// 源码参照: app/src/main/java/io/legado/app/data/entities/BaseRssArticle.kt
// 简化说明: 移除 RuleBigDataHelp 依赖，putBigVariable/getBigVariable 简化为空实现 | 已知上限: 大数据变量不持久化 | 升级路径: 接入 RuleBigDataHelp

interface BaseRssArticle : RuleDataInterface {

    var origin: String
    var link: String

    var variable: String?

    override fun putVariable(key: String, value: String?): Boolean {
        if (super.putVariable(key, value)) {
            variable = GSON.toJson(variableMap)
        }
        return true
    }

    override fun putBigVariable(key: String, value: String?) {
        // 简化说明：putBigVariable 简化为空实现 | 已知上限：大数据变量不持久化 | 升级路径：接入 RuleBigDataHelp
    }

    override fun getBigVariable(key: String): String? {
        // 简化说明：getBigVariable 简化为返回 null | 已知上限：无法读取大数据变量 | 升级路径：接入 RuleBigDataHelp
        return null
    }

}
