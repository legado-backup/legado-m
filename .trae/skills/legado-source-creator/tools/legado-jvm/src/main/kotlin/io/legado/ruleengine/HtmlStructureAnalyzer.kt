package io.legado.ruleengine

import org.jsoup.Jsoup

/**
 * HTML结构分析器
 * 解析HTML，提取class/id+出现次数+建议选择器
 * 简化说明: 大HTML截断前100KB | 已知上限: 截断后可能丢失尾部结构 | 升级路径: 流式解析
 */
class HtmlStructureAnalyzer {

    fun analyze(html: String): String {
        if (html.isBlank()) return "HTML为空，无法分析"

        // 大HTML截断前100KB避免性能问题
        val truncatedHtml = if (html.length > 102400) html.substring(0, 102400) else html
        val doc = Jsoup.parse(truncatedHtml)

        // 提取class+出现次数
        val classCounts = mutableMapOf<String, Int>()
        doc.getAllElements().forEach { el ->
            el.classNames().forEach { cls ->
                classCounts[cls] = classCounts.getOrDefault(cls, 0) + 1
            }
        }

        // 提取id+出现次数
        val ids = mutableMapOf<String, Int>()
        doc.select("[id]").forEach { el ->
            val id = el.id()
            if (id.isNotEmpty()) {
                ids[id] = ids.getOrDefault(id, 0) + 1
            }
        }

        // 提取meta标签（og:novel等结构化数据）
        val metaTags = mutableMapOf<String, String>()
        doc.select("meta[property]").forEach { el ->
            val property = el.attr("property")
            val content = el.attr("content")
            if (property.isNotEmpty() && content.isNotEmpty() &&
                (property.startsWith("og:") || property.startsWith("novel:"))) {
                metaTags[property] = content
            }
        }

        // 提取标签名统计（Web Components自定义元素，包含连字符的标签名）
        val tagCounts = mutableMapOf<String, Int>()
        doc.getAllElements().forEach { el ->
            val tagName = el.tagName()
            if (tagName.contains("-")) {
                tagCounts[tagName] = tagCounts.getOrDefault(tagName, 0) + 1
            }
        }

        // 生成建议选择器
        val suggestions = generateSelectorSuggestions(classCounts)

        return formatResult(classCounts, ids, metaTags, tagCounts, suggestions)
    }

    private fun generateSelectorSuggestions(classCounts: Map<String, Int>): List<String> {
        val suggestions = mutableListOf<String>()
        classCounts.filter { it.value > 1 }.forEach { (cls, count) ->
            when {
                cls.contains("book") || cls.contains("item") || cls.contains("card") ->
                    suggestions.add("书籍/文章列表: class.$cls ($count 次)")
                cls.contains("title") || cls.contains("name") ->
                    suggestions.add("标题: class.$cls ($count 次)")
                cls.contains("author") ->
                    suggestions.add("作者: class.$cls ($count 次)")
                cls.contains("content") || cls.contains("text") ->
                    suggestions.add("正文: class.$cls ($count 次)")
                cls.contains("chapter") || cls.contains("list") ->
                    suggestions.add("章节/列表: class.$cls ($count 次)")
                cls.contains("cover") || cls.contains("img") ->
                    suggestions.add("封面/图片: class.$cls ($count 次)")
            }
        }
        return suggestions
    }

    private fun formatResult(
        classCounts: Map<String, Int>,
        ids: Map<String, Int>,
        metaTags: Map<String, String>,
        tagCounts: Map<String, Int>,
        suggestions: List<String>
    ): String {
        val sb = StringBuilder()

        sb.appendLine("=== HTML结构分析 ===")

        // 输出class统计（按出现次数降序，最多20个）
        sb.appendLine("\n--- Class统计 (top 20) ---")
        classCounts.entries.sortedByDescending { it.value }.take(20).forEach { (cls, count) ->
            sb.appendLine("  .$cls: $count")
        }

        // 输出id统计（最多10个）
        if (ids.isNotEmpty()) {
            sb.appendLine("\n--- ID统计 (top 10) ---")
            ids.entries.sortedByDescending { it.value }.take(10).forEach { (id, count) ->
                sb.appendLine("  #$id: $count")
            }
        }

        // 输出meta标签（og:novel等结构化数据）
        if (metaTags.isNotEmpty()) {
            sb.appendLine("\n--- Meta标签 (og:novel) ---")
            metaTags.forEach { (property, content) ->
                sb.appendLine("  $property: ${content.take(80)}")
            }
        }

        // 输出标签名统计（Web Components自定义元素）
        if (tagCounts.isNotEmpty()) {
            sb.appendLine("\n--- 自定义标签名 (Web Components) ---")
            tagCounts.entries.sortedByDescending { it.value }.take(10).forEach { (tag, count) ->
                sb.appendLine("  <$tag>: $count")
            }
        }

        // 输出建议选择器
        if (suggestions.isNotEmpty()) {
            sb.appendLine("\n--- 建议选择器 ---")
            suggestions.forEach { sb.appendLine("  $it") }
        } else {
            sb.appendLine("\n--- 建议选择器 ---")
            sb.appendLine("  (未识别到常见选择器模式，请手动分析Class统计)")
        }

        return sb.toString()
    }
}
