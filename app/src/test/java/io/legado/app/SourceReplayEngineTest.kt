package io.legado.app

import android.app.Application
import io.legado.app.data.entities.Book
import io.legado.app.data.entities.BookSource
import io.legado.app.model.analyzeRule.AnalyzeRule
import io.legado.app.utils.GSON
import io.legado.app.utils.fromJsonObject
import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Assume
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config
import java.io.File

/**
 * 书源规则的**真实引擎**回放（JVM / Robolectric + 真 `AnalyzeRule`）。
 *
 * 双重目的：
 * 1. `deterministic*` 用例：把「离线模拟器（`.temp/source-batch/legado_sim.js`）」赖以成立的两条
 *    关键语义，钉在**真引擎**上（源码锚点 `AnalyzeByJSoup.kt:200-280` / `:303-404`）——
 *    ① **字段规则**（`getString` 路径）末段非 `text/textNodes/ownText/html/all` ⇒ 按 **属性名** 取值
 *      ⇒ 裸选择器（如 `h3`）恒为空字符串。旧 `rule_replay.js` 把裸选择器当 `@text` ⇒ **假 PASS**（缺陷 B-15）。
 *    ② **列表规则**（`getElements` 路径）下同一裸选择器是合法 CSS ⇒ 两条路径的**不对称**正是假 PASS 根因。
 * 2. `bundleReplay` 用例（需环境变量）：把批量修复产物的每条源 + 其**已存原始响应体**交给真引擎求值，
 *    证明「离线 PASS ⇒ App 内同样 PASS」，并把逐条结果落 JSON 报告供比对（**交叉校验的唯一权威判据**）。
 *
 * 环境变量：
 *   SRC_REPLAY_BUNDLE  bundle JSON 路径，元素形如
 *                      `{"idx":705,"stage":"search","html":"<abs>","source":{...BookSource...}}`
 *   SRC_REPLAY_OUT     报告输出路径（默认 `build/src_replay_report.json`）
 * 未提供 bundle 时**跳过**该用例（不误红常规单测）。
 * 输出安全：只打印/落盘 idx 与计数，不含源名称、URL 原文。
 */
@RunWith(RobolectricTestRunner::class)
@Config(application = Application::class)
class SourceReplayEngineTest {

    private val listHtml = """
        <html><body><ul class="list">
        <li><h3 class="name"><a href="/b/1">第一册</a></h3><p class="author">作者甲</p></li>
        <li><h3 class="name"><a href="/b/2">第二册</a></h3><p class="author">作者乙</p></li>
        </ul></body></html>
    """.trimIndent()

    // ===== 1. B-15 铁证：字段规则里的裸选择器取不到任何值（按属性名取值 ⇒ 空）=====

    @Test
    fun deterministic_fieldRule_bareSelector_readsAttributeName_notText() {
        val ar = AnalyzeRule(Book()).setContent(listHtml)
        assertEquals("字段规则末段为裸选择器 ⇒ 等价 attr(\"h3\") ⇒ 必须为空字符串",
            "", ar.getString("h3"))
        assertEquals("补 @text 后必须取到全部命中文本（多命中以换行连接）",
            "第一册\n第二册", ar.getString("h3 a@text"))
    }

    // ===== 2. 同一裸选择器在**列表规则**下是合法 CSS（两条路径不对称 = 假 PASS 根因）=====

    @Test
    fun deterministic_listRule_bareSelector_isValidCss() {
        val ar = AnalyzeRule(Book()).setContent(listHtml)
        assertEquals("裸 CSS 列表规则必须命中", 2, ar.getElements("ul.list > li").size)
        assertEquals("遗留 class. 前缀列表规则必须命中", 2, ar.getElements("class.list@tag.li").size)
        assertEquals("遗留 tag. 前缀列表规则必须命中", 2, ar.getElements("tag.li").size)
    }

    // ===== 3. @CSS: 前缀 + ## 替换：字段规则两条主流形态在真引擎的行为 =====

    @Test
    fun deterministic_cssPrefixAndRegexReplace_workAsSpec() {
        val ar = AnalyzeRule(Book()).setContent(listHtml)
        // 注意：`text` 取 element.text()，**含后代文本** ⇒ li 的文本含书名与作者
        assertEquals("@CSS: 前缀走 select 路径 ⇒ 取到文本（含后代）", "第一册 作者甲\n第二册 作者乙",
            ar.getString("@CSS:ul.list>li@text"))
        val numbered = AnalyzeRule(Book()).setContent(
            """<html><body><ul><li><a href="/c/12">12</a></li></ul></body></html>"""
        )
        assertEquals("## 正则替换必须生效", "第12话",
            numbered.getString("tag.a@text##(\\d+)##第\$1话"))
    }

    // ===== 4. 真引擎回放批量产物（需 bundle 文件：环境变量优先，否则按仓库相对路径兜底）=====

    /** 定位 bundle：`SRC_REPLAY_BUNDLE` 优先；否则按**仓库相对路径**兜底
     *  （Gradle daemon 的环境变量不随调用刷新 ⇒ 不能只依赖环境变量）。 */
    private fun locateBundle(): File? {
        val env = System.getenv("SRC_REPLAY_BUNDLE")
        val cands = listOfNotNull(
            env?.let { File(it) },
            File("../.temp/source-batch/report/engine_bundle.json"),
            File(".temp/source-batch/report/engine_bundle.json")
        )
        return cands.firstOrNull { it.isFile }
    }

    @Test
    fun bundleReplay_realEngineVerifiesRepairedRules() {
        val bundle = locateBundle()
        Assume.assumeTrue("未找到 engine_bundle.json，跳过真引擎批量回放", bundle != null)
        val arr = JSONArray(bundle!!.readText())
        assertTrue("bundle 不得为空", arr.length() > 0)

        val rows = JSONArray()
        var evaluated = 0
        var enginePass = 0
        val failures = ArrayList<String>()

        for (i in 0 until arr.length()) {
            val e = arr.getJSONObject(i)
            val idx = e.getInt("idx")
            val stage = e.getString("stage")
            val html = File(e.getString("html"))
            if (!html.isFile) {
                rows.put(report(idx, stage, 0, 0, 0, "NO-HTML"))
                continue
            }
            val src = GSON.fromJsonObject<BookSource>(e.getJSONObject("source").toString()).getOrThrow()
            val ar = AnalyzeRule(Book()).setContent(html.readText())
            val offline = e.getJSONObject("source").optJSONObject("_repair")

            val n: Int; val hitA: Int; val hitB: Int; val js: Boolean
            when (stage) {
                "search" -> {
                    val seg = src.ruleSearch
                    js = hasJs(seg?.bookList, seg?.name, seg?.bookUrl, seg?.author, seg?.coverUrl)
                    val els = ar.getElements(seg?.bookList ?: "")
                    n = els.size
                    hitA = els.count { ar.getString(seg?.name, it).isNotBlank() }
                    hitB = els.count { ar.getString(seg?.bookUrl, it).isNotBlank() }
                }

                "explore" -> {
                    val seg = src.ruleExplore
                    js = hasJs(seg?.bookList, seg?.name, seg?.bookUrl, seg?.author, seg?.coverUrl)
                    val els = ar.getElements(seg?.bookList ?: "")
                    n = els.size
                    hitA = els.count { ar.getString(seg?.name, it).isNotBlank() }
                    hitB = els.count { ar.getString(seg?.bookUrl, it).isNotBlank() }
                }

                "bookinfo" -> {
                    val seg = src.ruleBookInfo
                    js = hasJs(seg?.init, seg?.name, seg?.author, seg?.coverUrl)
                    n = 1
                    hitA = if (ar.getString(seg?.name).isNotBlank()) 1 else 0
                    hitB = if (ar.getString(seg?.author).isNotBlank()) 1 else 0
                }

                "toc" -> {
                    val seg = src.ruleToc
                    js = hasJs(seg?.chapterList, seg?.chapterName, seg?.chapterUrl)
                    val els = ar.getElements(seg?.chapterList ?: "")
                    n = els.size
                    hitA = els.count { ar.getString(seg?.chapterName, it).isNotBlank() }
                    hitB = els.count { ar.getString(seg?.chapterUrl, it).isNotBlank() }
                }

                "content" -> {
                    val seg = src.ruleContent
                    js = hasJs(seg?.content)
                    n = 1
                    hitA = if (ar.getString(seg?.content).isNotBlank()) 1 else 0
                    hitB = 0
                }

                else -> {
                    rows.put(report(idx, stage, 0, 0, 0, "UNKNOWN-STAGE"))
                    continue
                }
            }

            val ok = when (stage) {
                "search", "explore" -> n >= 1 && hitA >= 1 && hitB >= 1
                "bookinfo" -> hitA >= 1 || hitB >= 1
                "toc" -> n >= 1 && hitA >= 1 && hitB >= 1
                else -> hitA >= 1
            }
            val verdict = when {
                // 列表型阶段（搜索/发现）即便含 JS 也必须过 —— 真引擎本身支持 JS 运行时
                js && stage != "search" && stage != "explore" -> "SKIP-JS"
                ok -> "PASS"
                else -> "FAIL"
            }
            if (verdict != "SKIP-JS") {
                evaluated++
                if (ok) enginePass++
            }
            val r = report(idx, stage, n, hitA, hitB, verdict)
            if (offline != null) {
                r.put("offlineN", offline.optInt("n", -1))
                r.put("offlineNameHit", offline.optInt("nameHit", -1))
                r.put("offlineUrlHit", offline.optInt("urlHit", -1))
            }
            rows.put(r)
            if (verdict == "FAIL") failures.add("idx=$idx stage=$stage n=$n hitA=$hitA hitB=$hitB")
        }

        // 报告默认落在 bundle 同目录（report/），便于管线读取与溯源
        val out = System.getenv("SRC_REPLAY_OUT")?.let { File(it) }
            ?: File(bundle.parentFile, "engine_replay_report.json")
        out.parentFile?.mkdirs()
        out.writeText(rows.toString(1))

        println("[真引擎回放] 条目=${arr.length()} 已判=${evaluated} 引擎PASS=$enginePass 失败=${failures.size}")
        println("[真引擎回放] 报告=${out.path}")
        failures.take(20).forEach { println("[真引擎回放·FAIL] $it") }

        assertTrue("bundle 至少要有 1 条可判条目", evaluated >= 1)
        assertTrue(
            "真引擎判定通过的条目须为多数（失败=${failures.size}）：${failures.take(10)}",
            failures.isEmpty()
        )
    }

    private fun report(idx: Int, stage: String, n: Int, a: Int, b: Int, verdict: String): JSONObject =
        JSONObject().put("idx", idx).put("stage", stage)
            .put("n", n).put("hitA", a).put("hitB", b).put("verdict", verdict)

    /** 规则段是否含 JS 运行时依赖（`@js:`/`<js>`/`@JS:`/`@webjs`/`@WebJs`） */
    private fun hasJs(vararg rules: String?): Boolean =
        rules.any { r ->
            r != null && (
                r.contains("@js:", true) || r.contains("<js>", true) ||
                    r.contains("@webjs", true)
                )
        }
}
