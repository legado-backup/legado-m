package io.legado.app

import io.legado.app.data.entities.Book
import io.legado.app.data.entities.BookSource
import io.legado.app.help.http.RequestMethod
import io.legado.app.model.CheckStrictness
import io.legado.app.model.DimResult
import io.legado.app.model.DimState
import io.legado.app.model.QualityDim
import io.legado.app.model.SourceQualityChecker
import io.legado.app.model.SourceQualityReport
import io.legado.app.model.SourceQualityScorer
import io.legado.app.model.analyzeRule.AnalyzeRule
import io.legado.app.model.analyzeRule.AnalyzeUrl
import io.legado.app.utils.GSON
import io.legado.app.utils.fromJsonObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Assume
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config
import android.app.Application
import java.io.File

/**
 * 皮皮喵→legado 转换产物的真实引擎验证（JVM）。
 *
 * 规则字符串全部取自转换产物 `皮皮喵漫画书源_legado格式_493条.json` 的原文，
 * 覆盖 2026-10-15 缺陷修复后的全部高风险转换形态：
 * - CSS 列表倒序（[-1:0] 区间反向，AnalyzeByJSoup.ElementsSingle 语义）
 * - ##正则##替换（腾讯章节名）
 * - jsonpath + @js 反转段（哔哩目录）
 * - <js> 取图 + getImgList 补调用 + html→result（漫客栈取图）
 * - @POST 三段式 → option JSON（哔哩搜索，AnalyzeUrl 全链求值）
 * - 页码枚举 <,{{page}}>（土豆）
 * - 相对路径 + {{key}}/{{page}} 模板（腾讯搜索）
 * - GSON 反序列化转换产物为 BookSource（legado 导入路径）
 */
@RunWith(RobolectricTestRunner::class)
@Config(application = Application::class)
class PpcatConvertedRuleVerifyTest {

    private fun makeSource(): BookSource =
        BookSource(bookSourceUrl = "https://test.example.com", bookSourceName = "皮皮喵测试源")

    // 说明：三个走 evalJS 的用例 AnalyzeRule/AnalyzeUrl 的 source 传 null——
    // 真机路径 source 为 BookSource，仅影响 bindings[source]/cache 命名空间，
    // 被验证的 JS 体（getImgList(result)/result.size()/{{key}}/{{page}}）只依赖 result/baseUrl/key/page；
    // JVM 测试传 source 会在 scriptCacheObject → AppConfig 静态初始化炸（Robolectric 下无 appDb），
    // source=null 走 CacheManager 旁路，与 AnalyzeInnerRuleContextRegressionTest 同模式。

    // ===== 1. CSS 列表倒序：`class.chapter-wrap-list@tag.li[-1:0]`（腾讯 chapterList 原文）=====

    @Test
    fun cssList_reverseByRange_returnsReversedOrder() {
        val html = """
            <html><body><div class="chapter-wrap-list">
            <li><a href="/c/1">1</a></li>
            <li><a href="/c/2">2</a></li>
            <li><a href="/c/3">3</a></li>
            </div></body></html>
        """.trimIndent()
        val analyze = AnalyzeRule(Book(), makeSource()).setContent(html)
        val elements = analyze.getElements("class.chapter-wrap-list@tag.li[-1:0]")
        assertEquals(3, elements.size)
        // 皮皮喵 - 前缀倒序语义：最新章在前。断言 [3,2,1] 反向
        val hrefs = elements.map { (it as org.jsoup.nodes.Element).select("a").attr("href") }
        assertEquals(listOf("/c/3", "/c/2", "/c/1"), hrefs)
    }

    // ===== 2. ##正则##替换：`tag.a@text##(\d+)##第$1话`（腾讯 chapterName 原文）=====

    @Test
    fun regexReplace_chapterName_convertsNumberToLabel() {
        val html = """<html><body><ul><li><a href="/c/12">12</a></li></ul></body></html>"""
        val analyze = AnalyzeRule(Book(), makeSource()).setContent(html)
        val name = analyze.getString("tag.a@text##(\\d+)##第\$1话")
        assertEquals("第12话", name)
    }

    // ===== 3. jsonpath + @js 反转段（哔哩 chapterList 原文）=====

    @Test
    fun jsonPath_appendJsReverse_returnsReversedList() {
        val json = """{"data":{"ep_list":[{"id":1},{"id":2},{"id":3}]}}"""
        val rule = "$.data.ep_list.*@js:var __o=[];for(var __i=result.size()-1;__i>=0;__i--)" +
            "{__o.push(result.get(__i))}__o"
        val analyze = AnalyzeRule(Book()).setContent(json)
        val elements = analyze.getElements(rule)
        assertEquals(3, elements.size)
        // 反转后第一个应是原列表最后一个 {"id":3}
        val first = analyze.getString("$.id", elements[0])
        assertEquals("3", first)
    }

    // ===== 4. <js> 取图 + getImgList 补调用 + html→result（漫客栈 content 原文）=====

    @Test
    fun jsContent_getImgListContract_returnsImageUrlList() {
        val html = """
            <html><body>
            <img src="https://img.example.com/mkzhan/page-1.jpg"/>
            <img src="https://img.example.com/mkzhan/page-2.jpg"/>
            </body></html>
        """.trimIndent()
        val rule = """<js>function getImgList(){
var list = result.match(/(https.*?page-\d+)/g);
return list;
}
getImgList(result)</js>"""
        val analyze = AnalyzeRule(Book()).setContent(html)
        val urls = analyze.getStringList(rule, isUrl = true)
        assertTrue("取图列表不应为空", !urls.isNullOrEmpty())
        assertTrue(urls!!.any { it.contains("page-1") })
        assertTrue(urls.any { it.contains("page-2") })
    }

    // ===== 5. @POST 三段式 → option JSON（哔哩 searchUrl 原文，AnalyzeUrl 全链）=====

    @Test
    fun analyzeUrl_postOptionJson_methodBodyHeaderResolved() {
        val searchUrl = "/twirp/comic.v1.Comic/Search," +
            """{"method":"POST","body":{"platform":"h5","key_word":"{{key}}","pageSize":10,"page_num":{{page}}},""" +
            """"headers":{"Content-Type":"application/json;charset=UTF-8"}}"""
        val source = BookSource(
            bookSourceUrl = "https://manga.bilibili.com",
            bookSourceName = "哔哩漫画（正版）"
        )
        val analyzeUrl = AnalyzeUrl(
            searchUrl,
            key = "斗罗大陆",
            page = 2,
            baseUrl = source.bookSourceUrl,
            source = null,
            headerMapF = emptyMap()
        )
        // URL 相对路径拼接
        assertEquals("https://manga.bilibili.com/twirp/comic.v1.Comic/Search", analyzeUrl.url)
        // headers 从 option JSON 进 headerMap
        assertEquals("application/json;charset=UTF-8", analyzeUrl.headerMap["Content-Type"])
        // method/body 为 private，反射断言（JVM 单测）
        val methodField = AnalyzeUrl::class.java.getDeclaredField("method").apply { isAccessible = true }
        assertEquals(RequestMethod.POST, methodField.get(analyzeUrl))
        val bodyField = AnalyzeUrl::class.java.getDeclaredField("body").apply { isAccessible = true }
        val body = bodyField.get(analyzeUrl) as String?
        assertTrue("body 应包含已求值的关键词, 实际body=$body", body!!.contains("斗罗大陆"))
        assertTrue("body 应包含已求值的页码 page_num:2, 实际body=$body", body.contains("\"page_num\":2") || body.contains("\"page_num\": 2"))
    }

    // ===== 6. 页码枚举 <,{{page}}>（土豆 exploreUrl 原文）=====

    @Test
    fun analyzeUrl_pageEnum_firstPageEmptySecondPageNumbered() {
        val url = "/update/<,{{page}}>.html"
        val p1 = AnalyzeUrl(url, page = 1, baseUrl = "https://www.tudou.com", headerMapF = emptyMap())
        val p2 = AnalyzeUrl(url, page = 2, baseUrl = "https://www.tudou.com", headerMapF = emptyMap())
        // 第 1 页取枚举首项（空）→ 无后缀
        assertEquals("https://www.tudou.com/update/.html", p1.url)
        // 第 2 页取枚举第 2 项
        assertEquals("https://www.tudou.com/update/2.html", p2.url)
    }

    // ===== 7. 相对路径 + {{key}}/{{page}} 模板（腾讯 searchUrl 原文）=====

    @Test
    fun analyzeUrl_relativeUrlWithKeyPageTemplates_resolved() {
        val searchUrl = "/search/result?word={{key}}&page={{page}}&pageSize=30&style=items"
        val analyzeUrl = AnalyzeUrl(
            searchUrl,
            key = "斗罗大陆",
            page = 3,
            baseUrl = "https://m.ac.qq.com",
            headerMapF = emptyMap()
        )
        assertTrue(
            "URL 应拼接到源域名并完成模板求值",
            analyzeUrl.url.startsWith("https://m.ac.qq.com/search/result?")
        )
        assertTrue("页码应求值为 3", analyzeUrl.url.contains("page=3"))
        assertTrue("关键词应求值（URL 编码）", analyzeUrl.url.contains("word="))
    }

    // ===== 8. GSON 反序列化转换产物为 BookSource（legado 导入路径）=====

    @Test
    fun gsonDeserialize_convertedProduct_parsesToBookSource() {
        val converted = """
        {
          "bookSourceName": "哔哩漫画（正版）",
          "bookSourceUrl": "https://manga.bilibili.com",
          "bookSourceType": 2,
          "bookSourceGroup": "漫画",
          "enabled": true,
          "searchUrl": "/twirp/comic.v1.Comic/Search,{\"method\":\"POST\",\"body\":{\"platform\":\"h5\",\"key_word\":\"{{key}}\",\"pageSize\":10,\"page_num\":{{page}}},\"headers\":{\"Content-Type\":\"application/json;charset=UTF-8\"}}",
          "ruleSearch": {
            "bookList": "{{\nvar json=JSON.parse(result);\nvar out='$.data.list.*||$.data.*';\nif(json.data.list&&json.data.list.length==0){\nout=undefined;\n}\nout\n}}",
            "name": "$.org_title||$.title@put:{pid:$.id||$.season_id}@js:result",
            "bookUrl": "$.id||$.season_id@js:\n'https://example.com/detail?id='+result"
          },
          "ruleToc": {
            "chapterList": "$.data.ep_list.*@js:var __o=[];for(var __i=result.size()-1;__i>=0;__i--){__o.push(result.get(__i))}__o",
            "chapterName": "$.title",
            "chapterUrl": "$.id"
          },
          "ruleContent": { "content": "$.data@js:result" }
        }
        """.trimIndent()
        val source = GSON.fromJsonObject<BookSource>(converted).getOrThrow()
        assertEquals("哔哩漫画（正版）", source.bookSourceName)
        assertEquals("https://manga.bilibili.com", source.bookSourceUrl)
        assertEquals(2, source.bookSourceType)
        assertTrue(source.searchUrl!!.contains("\"method\":\"POST\""))
        assertTrue(source.ruleSearch!!.bookUrl!!.contains("@js:"))
        assertTrue(source.ruleToc!!.chapterList!!.contains("result.get(__i)"))
        assertTrue(source.ruleContent!!.content!!.contains("@js:"))
    }

    // ===== 9. 产物文件全量一致性（真实 GSON + 真实实体 + 真实 L1 判据）=====
    // 需环境变量 PPCAT_PRODUCT 指向产物 JSON；未提供则跳过（不误红常规跑）。
    // 目的：证明「这批源导入本仓不会出问题」——行数守恒 / 主键唯一 / 类型合法 /
    //       搜索规则段齐备 / L1 确定性失败为 0（导入校验同一判据）/ 无空 Referer。

    @Test
    fun productFile_allEntriesConformAndPassL1StaticCheck() {
        val path = System.getenv("PPCAT_PRODUCT")
        Assume.assumeTrue(
            "未提供 PPCAT_PRODUCT，跳过产物文件一致性检查",
            !path.isNullOrBlank() && File(path).isFile
        )
        val raw = File(path!!).readText()
        val list = GSON.fromJsonObject<List<BookSource>>(raw).getOrThrow()

        // NEW-68 宿主专属 API 可移植化（2026-10-16）：皮皮喵宿主 JS API（java.atob / java.aJax /
        // java.postForm / java.getdirecturl）在目标引擎全不存在（`java` = AnalyzeRule 实例，
        // 方法表见 help/JsExtensions.kt + help/JsEncodeUtils.kt）⇒ 残留即该规则必抛 TypeError。
        // 故「已映射符号残留须为 0」，并正向断言已改为目标引擎等价 API（等价性见转换器 NEW-68 段注释）。
        val countOccur = { tok: String -> raw.split(tok).size - 1 }
        listOf("java.atob", "java.aJax(", "java.postForm(", "java.getdirecturl").forEach { tok ->
            assertEquals("宿主 API 未映射残留须为 0：$tok", 0, countOccur(tok))
        }
        assertTrue("应存在 java.base64Decode 映射（atob 等价）", countOccur("java.base64Decode") > 0)
        assertTrue("应存在 java.md5Encode 映射（CryptoJS.MD5 等价）", countOccur("java.md5Encode") > 0)
        assertTrue("应存在 java.aesBase64DecodeToString 映射（AES_Decrypt/CryptStr 等价）",
            countOccur("java.aesBase64DecodeToString") > 0)
        assertTrue("应存在 createSymmetricCrypto 改写（CryptoJS 样板块等价）",
            countOccur("java.createSymmetricCrypto") > 0)

        // 行数守恒（GSON 未静默丢弃条目）+ 主键唯一（Room @PrimaryKey 冲突源）
        assertTrue("条目数应保持数百量级（行数守恒），实际=${list.size}", list.size > 400)
        assertEquals("bookSourceUrl 必须唯一", list.size, list.map { it.bookSourceUrl }.distinct().size)

        // CRITICAL / 类型域 / 规则段齐备
        list.forEachIndexed { i, s ->
            assertTrue("[$i] bookSourceUrl 不可为空", s.bookSourceUrl.isNotBlank())
            assertTrue("[$i] bookSourceName 不可为空", s.bookSourceName.isNotBlank())
            assertTrue("[$i] bookSourceType 须在 0..4，实际=${s.bookSourceType}", s.bookSourceType in 0..4)
            assertTrue("[$i] 搜索规则段不可缺失", s.ruleSearch != null)
        }
        assertEquals("本批应全为图片(漫画)类型", list.size, list.count { it.bookSourceType == 2 })

        // 与导入校验同一判据：L1 确定性失败 ⇒ 导入即被过滤，必须为 0
        val l1Fail = list.count { SourceQualityChecker.l1StaticCheckBookSource(it).deterministicFail }
        assertEquals("L1 确定性失败须为 0（否则导入即被过滤）", 0, l1Fail)

        // 直接回答「**开启**导入校验（L1 结构档 + 宽松档）会不会把我们的源过滤掉」：
        // 逐条走导入过滤的唯一判据 ⇒ 过滤集必须为空（历史担心源于 debug 包残留的开启配置误判）
        val l1Filtered = list.count { s ->
            SourceQualityScorer.isFiltered(
                SourceQualityChecker.l1StaticCheckBookSource(s), CheckStrictness.LENIENT
            ).first
        }
        assertEquals("开启导入校验（L1+宽松）不得误杀任何转换源", 0, l1Filtered)

        // header 不得含空 Referer（noPicReffer 误处理痕迹）
        val emptyReferer = list.count { s ->
            s.header?.let { h ->
                runCatching {
                    GSON.fromJsonObject<Map<String, String>>(h).getOrNull()?.get("Referer") == ""
                }.getOrDefault(false)
            } ?: false
        }
        assertEquals("header.Referer 空值须为 0（否则可能击穿 API 请求）", 0, emptyReferer)
    }

    // ===== 10. NEW-68 移植：CryptoJS 样板块 → createSymmetricCrypto（IV=前16B、密文=其余）=====
    // 用原生 javax.crypto 造密文（**不借道被测 API**，避免自证循环），再把转换器实际产出的**改写形态**
    // 逐字交给真实引擎（Rhino + `java` 实例 + `Packages.java.util.Arrays`）执行 ⇒ 同时证明：
    // ①`Packages` Java 互操作在书源 JS 上下文可用（ClassShutter 未拦 java.util.Arrays）
    // ②Java byte[] 编组 / IV 切分 / 字符集（UTF-8）全部正确
    @Test
    fun portedCryptoJsBlock_aesCbcIvPrefixed_decryptsToPlaintext() {
        val plain = """{"images":["https://img.example.com/1.jpg"]}"""
        val key = "9S8\$vJnU2ANeSRoF".toByteArray(Charsets.UTF_8)
        val iv = "0123456789abcdef".toByteArray(Charsets.UTF_8)
        val cipher = javax.crypto.Cipher.getInstance("AES/CBC/PKCS5Padding")
        cipher.init(
            javax.crypto.Cipher.ENCRYPT_MODE,
            javax.crypto.spec.SecretKeySpec(key, "AES"),
            javax.crypto.spec.IvParameterSpec(iv)
        )
        val payload = java.util.Base64.getEncoder()
            .encodeToString(iv + cipher.doFinal(plain.toByteArray(Charsets.UTF_8)))
        // 与转换器 NEW-68 ⑨ 的产出形态逐字一致（仅输入变量名与 key 字面量随源变化）
        val rule = """@js:
var __cjRaw=java.base64DecodeToByteArray(result);
var __cjIv=Packages.java.util.Arrays.copyOfRange(__cjRaw,0,16);
var __cjCt=Packages.java.util.Arrays.copyOfRange(__cjRaw,16,__cjRaw.length);
var decryptedText=java.bytesToStr(java.createSymmetricCrypto("AES/CBC/PKCS5Padding",java.strToBytes("9S8${'$'}vJnU2ANeSRoF"),__cjIv).decrypt(__cjCt));
decryptedText"""
        val analyze = AnalyzeRule(Book()).setContent(payload)
        assertEquals("改写后的 AES 段应解出原文", plain, analyze.getString(rule))
    }

    // ===== 11. NEW-68 移植：getdirecturl → 内联等价式（绝对直返 / 相对拼接）=====
    @Test
    fun portedGetDirectUrlInline_keepsAbsoluteAndJoinsRelative() {
        // 与转换器 NEW-68 ⑧ 的产出表达式逐字一致
        val fn = """(function(b,u){u=String(u==null?"":u);if(/^https?:\/\//.test(u))return u;"""
        val fn2 = """b=String(b);if(b.charAt(b.length-1)!=="/")b+="/";return b+u.replace(/^\//,"")})"""
        val rel = AnalyzeRule(Book()).setContent("page/2.jpg")
            .getString("@js:$fn$fn2(\"https://img.example.com\", result)")
        assertEquals("https://img.example.com/page/2.jpg", rel)
        val abs = AnalyzeRule(Book()).setContent("https://cdn.example.com/a.jpg")
            .getString("@js:$fn$fn2(\"https://img.example.com\", result)")
        assertEquals("https://cdn.example.com/a.jpg", abs)
        val lead = AnalyzeRule(Book()).setContent("/page/3.jpg")
            .getString("@js:$fn$fn2(\"https://img.example.com/\", result)")
        assertEquals("去掉首斜杠后拼接，不得出现双斜杠", "https://img.example.com/page/3.jpg", lead)
    }

    // ===== 12. NEW-68 移植：atob → java.base64Decode（UTF-8 解码等价）=====
    @Test
    fun portedAtob_base64Decode_equalsOriginalText() {
        val text = "https://img.example.com/1.jpg\$qingtiandy\$https://img.example.com/2.jpg"
        val payload = java.util.Base64.getEncoder().encodeToString(text.toByteArray(Charsets.UTF_8))
        val analyze = AnalyzeRule(Book()).setContent(payload)
        assertEquals(text, analyze.getString("@js:java.base64Decode(result)"))
    }

    // ===== 13. 「开启导入校验」门限语义（回答「开启后会不会把我们的源过滤掉」）=====
    // 判据单源：`ImportBookSourceViewModel` 的过滤决定＝`SourceQualityScorer.isFiltered(report, strictness)`；
    // L1 结构档报告由 `SourceQualityChecker.l1StaticCheckBookSource` 构造（无联网、可 JVM 断言）。
    @Test
    fun importCheckGate_rejectsStructuralFailButReleasesSuspectAndNetworkFailure() {
        // ① 结构残缺（既无搜索也无发现）⇒ 所有档过滤，且给出白话原因
        val broken = BookSource(bookSourceUrl = "https://a.example.com", bookSourceName = "残缺源")
        val r1 = SourceQualityChecker.l1StaticCheckBookSource(broken)
        val (f1, why1) = SourceQualityScorer.isFiltered(r1, CheckStrictness.LENIENT)
        assertTrue("结构残缺源应被过滤", f1)
        assertEquals("搜索和发现规则均为空", why1)

        // ② 结构齐全但依赖 jsLib（存疑五类之一）⇒ 宽松/标准档**放行**（不误杀）
        val suspect = BookSource(
            bookSourceUrl = "https://b.example.com",
            bookSourceName = "存疑源",
            searchUrl = "/s?q={{key}}",
            jsLib = "function f(){return 1}"
        )
        val r2 = SourceQualityChecker.l1StaticCheckBookSource(suspect)
        assertEquals("存疑源在宽松档不得被过滤", false,
            SourceQualityScorer.isFiltered(r2, CheckStrictness.LENIENT).first)

        // ③ 入口维度「异常型失败」（网络/超时）⇒ 宽松档放行、标准档过滤（档位语义，非源缺陷）
        val netFail = SourceQualityReport(
            sourceUrl = "https://c.example.com",
            sourceType = 0,
            checkedDepth = 2,
            dimensions = mapOf(
                QualityDim.SEARCH to DimResult(DimState.FAIL, evidence = "搜索请求失败", failedByException = true)
            )
        )
        assertEquals(false, SourceQualityScorer.isFiltered(netFail, CheckStrictness.LENIENT).first)
        assertTrue(SourceQualityScorer.isFiltered(netFail, CheckStrictness.STANDARD).first)

        // ④ 入口维度「确定性 0 结果」（非环境问题，是规则匹配不到）⇒ 所有档过滤
        val zeroHits = SourceQualityReport(
            sourceUrl = "https://d.example.com",
            sourceType = 0,
            checkedDepth = 2,
            dimensions = mapOf(
                QualityDim.SEARCH to DimResult(DimState.FAIL, evidence = "搜索不到结果")
            )
        )
        assertTrue(SourceQualityScorer.isFiltered(zeroHits, CheckStrictness.LENIENT).first)
    }
}
