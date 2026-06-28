package io.legado.app.data.entities

import io.legado.app.model.analyzeRule.RuleDataInterface
import io.legado.app.utils.GSON
import io.legado.app.utils.splitNotBlank

// 源码参照: app/src/main/java/io/legado/app/data/entities/BaseBook.kt
// 简化说明: 移除 RuleBigDataHelp 依赖，putBigVariable/getBigVariable 简化为空实现 | 已知上限: 大数据变量不持久化 | 升级路径: 接入 RuleBigDataHelp

interface BaseBook : RuleDataInterface {

    var name: String
    var author: String
    var bookUrl: String
    var kind: String?
    var wordCount: String?
    var variable: String?

    var infoHtml: String?
    var tocHtml: String?

    override fun putVariable(key: String, value: String?): Boolean {
        if (super.putVariable(key, value)) {
            variable = GSON.toJson(variableMap)
        }
        return true
    }

    fun putCustomVariable(value: String?) {
        putVariable("custom", value)
    }

    fun getCustomVariable(): String {
        return getVariable("custom")
    }

    override fun putBigVariable(key: String, value: String?) {
        // 简化说明：putBigVariable 简化为空实现 | 已知上限：大数据变量不持久化 | 升级路径：接入 RuleBigDataHelp
    }

    override fun getBigVariable(key: String): String? {
        // 简化说明：getBigVariable 简化为返回 null | 已知上限：无法读取大数据变量 | 升级路径：接入 RuleBigDataHelp
        return null
    }

    fun getKindList(): List<String> {
        val kindList = arrayListOf<String>()
        wordCount?.let {
            if (it.isNotBlank()) kindList.add(it)
        }
        kind?.let {
            val kinds = it.splitNotBlank(",", "\n")
            kindList.addAll(kinds)
        }
        return kindList
    }
}
