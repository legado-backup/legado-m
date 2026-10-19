package io.legado.app.model.localBook.epubcore.template

import com.google.gson.JsonParser
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File
import java.security.MessageDigest
import java.util.Base64

/**
 * 内置模板资产校验单测（原 4.12 配对；2026-10-17 随用户裁定「删除 11 套旧内置主题 + 新增幽夜回廊」同步重写）。
 *
 * 直接把 `src/main/assets/reader/` 下的**真实资产**读进来逐项校验——这是"内置模板"唯一
 * 能在 JVM 侧拿到强证据的手段（真机只验证观感与交互）。
 *
 * 覆盖：①目录与文件一一对应且 id 一致；②每套通过结构校验（走与用户导入**同一条**路径）；
 * ③**作者契约**在场（`data-reader-flow="body"` 必需、字段槽位合法、滚动模板必须有
 * `data-reader-scroll-viewport`）；④**合规红线**：零外部网络依赖、零外部字体/图片文件、
 * 无第三方 IP 关键词、`sources.json` 在场；⑤三主题态（日/夜/水墨屏）变量在场；
 * ⑥元素/动效规模预算（4.19 / NFR-08）；⑦**素材登记 ↔ 内联字节双向闭合且 SHA-256 一致**。
 *
 * ⚠️ 判据修正（2026-10-17 实证）：`vh` 尺寸扫描必须**先剥除内联 base64 载荷** ——
 * base64 字符表含 `v`/`h`/数字，会随机拼出 `NNvh` 假尺寸（本主题首跑即被误判出 50vh/87vh）。
 * 同族缺陷此前已出现在"IP 关键词扫描"上，故两处一律先剥离载荷再匹配。
 */
class ReaderBuiltinTemplateCatalogTest {

    private val assetsRoot = File("src/main/assets")

    /** 注入文件读取器：把 `assets/` 相对路径映射到仓库内真实文件。 */
    private val reader = ReaderBuiltinTemplateCatalog.AssetReader { path ->
        val file = File(assetsRoot, path)
        if (file.isFile) file.readText() else null
    }

    private fun load() = ReaderBuiltinTemplateCatalog.load(reader)

    @Test
    fun `目录与资产可加载且无错误`() {
        val result = load()
        assertEquals("内置模板加载不得有错误：${result.errors}", emptyList<String>(), result.errors)
        assertTrue("内置清单不得为空（删空后应至少补一套新主题）", result.templates.isNotEmpty())
    }

    @Test
    fun `目录清单 id 与文件 id 一一对应`() {
        val ids = ReaderBuiltinTemplateCatalog.catalogIds(reader).getOrThrow()
        val loaded = load().templates
        assertEquals("目录声明数量与加载数量一致", ids.size, loaded.size)
        ids.forEach { id -> assertTrue("目录 id $id 必须加载成功", loaded.any { it.id == id }) }
        assertEquals("id 不得重复", ids.size, ids.toSet().size)
    }

    @Test
    fun `当前内置集合等于目录声明且均为分页型`() {
        // 滚动（scroll）契约仍由引擎支持，但**内置**已不含滚动模板 ⇒ 断言钉住现状，
        // 避免"内置悄悄混入滚动模板"而 `data-reader-scroll-viewport` 契约无人复核。
        val ids = ReaderBuiltinTemplateCatalog.catalogIds(reader).getOrThrow()
        val loaded = load().templates
        assertEquals("目录声明与加载集合必须一致", ids.toSet(), loaded.map { it.id }.toSet())
        assertEquals("内置主题均为分页型", 0, loaded.count { it.isScroll })
        assertEquals("每套必须附来源声明", loaded.size, loaded.count { it.sources.isNotBlank() })
    }

    @Test
    fun `每套模板通过结构校验`() {
        load().templates.forEach { builtin ->
            val errors = builtin.template.validate()
            assertEquals("${builtin.id} 结构必须合法：$errors", emptyList<String>(), errors)
            assertTrue("${builtin.id} 名称不得为空", builtin.template.name.isNotBlank())
        }
    }

    @Test
    fun `作者契约在场`() {
        load().templates.forEach { builtin ->
            val source = builtin.template.resourceSource()
            assertTrue("${builtin.id} 必须声明正文槽位 data-reader-flow=body", source.contains("data-reader-flow=\"body\""))
            assertTrue("${builtin.id} 必须使用合法字段槽位", source.contains("data-reader-field=\""))
            val fields = FIELD.findAll(source).map { it.groupValues[1] }.toSet()
            assertTrue("${builtin.id} 字段槽位不得越界：$fields", ALLOWED_FIELDS.containsAll(fields))
            if (builtin.isScroll) {
                assertTrue("${builtin.id} 滚动模板必须声明唯一天地画框", source.contains("data-reader-scroll-viewport"))
            } else {
                assertFalse("${builtin.id} 分页模板不应出现滚动画框", source.contains("data-reader-scroll-viewport"))
            }
        }
    }

    @Test
    fun `段落语义类由脚本供给且与样式双向闭合`() {
        // 2026-10-17（用户报「唯一内置主题的段落元素是不是缺失」）实证：本主题此前**只在 CSS 里**声明了
        // `.reader-paragraph.dh-lead`，却没有任何代码给它加类 ⇒ 该规则恒空（**死规则**）。
        // 对照 archive 侧 6 套主题：它们无一例外都在 `beforeLayout` 里按**正文文本**给段落打语义类
        // （首段 / 对白段 / 场景分隔段）—— 那才是"分段正文样式"的可见主体。故此处钉两条不变量：
        // ①三类**都由脚本供给**且与样式**双向闭合**（有类必有样式、有样式必有 toggle，防死规则回潮）；
        // ②分类阈值与 archive **同口径**（同一段正文在两边分类一致 ⇒ 换主题/导入导出观感连续）。
        load().templates.forEach { builtin ->
            val js = builtin.template.javascript
            val css = plainCss(builtin.template.css)
            val source = builtin.template.resourceSource()
            assertTrue(
                "${builtin.id} 段落分类必须读正文根（与 archive 的 readerTemplate.source 同义）",
                js.contains("rt.source") && js.contains("'.reader-paragraph'")
            )
            // 换壳（C1）会整块替换根壳并重新注入正文 ⇒ `beforePage` 上必须再分类一次，否则续页丢类
            listOf("beforeLayout", "beforePage").forEach { hook ->
                assertTrue(
                    "${builtin.id} 段落分类须挂在 $hook 上（只挂 beforeLayout 时换壳后段落丢类）",
                    js.contains("'$hook', classifyParagraphs")
                )
            }
            PARAGRAPH_CLASSES.forEach { semantic ->
                assertTrue("${builtin.id} 段落语义类 $semantic 必须由脚本 toggle", js.contains("'$semantic'"))
                assertTrue(
                    "${builtin.id} 段落语义类 $semantic 必须同时有样式（否则 toggle 是空动作 ⇒ 观感无变化）",
                    css.contains(".$semantic")
                )
                assertTrue(
                    "${builtin.id} 段落语义类 $semantic 必须被正文契约覆盖（源里的段落带 .reader-paragraph）",
                    source.contains("reader-paragraph") || css.contains(".reader-paragraph")
                )
            }
            PARAGRAPH_THRESHOLDS.forEach { pattern ->
                assertTrue(
                    "${builtin.id} 段落分类判据须与 archive 逐字同口径：$pattern",
                    js.contains(pattern)
                )
            }
            assertEquals("段落语义类固定为 3 类（首段 / 对白段 / 场景分隔段）", 3, PARAGRAPH_CLASSES.size)
        }
    }

    @Test
    fun `派生字段槽位确有消费者`() {
        // 4.15 C2：`page`/`pageCount`/`percent`/`time`/`battery` 是**沙箱派生**字段。
        // 若内置模板一套都不用它们，运行时的派生实现就成了死代码 —— 这条确保它被真实消费。
        val loaded = load().templates
        val used = loaded.flatMap { FIELD.findAll(it.template.resourceSource()).map { m -> m.groupValues[1] } }.toSet()
        assertTrue("至少一套模板须消费派生的页码槽位（否则 C2 派生是死代码）：实际=$used", used.contains("page"))
        assertTrue("至少一套模板须消费派生的时间槽位：实际=$used", used.contains("time"))
    }

    @Test
    fun `内置模板元素与动效规模在预算内（4_19 门禁）`() {
        // 4.19 / NFR-08：重装饰模板连续翻页掉帧的根因就是**元素/动效规模失控**。
        load().templates.forEach { builtin ->
            val css = plainCss(builtin.template.css)
            val source = plainCss(builtin.template.resourceSource())
            val keyframes = Regex("@keyframes").findAll(css).count()
            assertTrue("${builtin.id} @keyframes 数量 $keyframes 超预算（≤$MAX_KEYFRAMES）", keyframes <= MAX_KEYFRAMES)
            val declared = Regex("animation\\s*:").findAll(css).count()
            assertTrue(
                "${builtin.id} animation 声明 $declared 处超预算（≤$MAX_ANIMATION_DECLARATIONS）",
                declared <= MAX_ANIMATION_DECLARATIONS
            )
            val elements = Regex("<[a-zA-Z][^>]*>").findAll(source).count()
            assertTrue("${builtin.id} 结构元素 $elements 个超预算（≤$MAX_ELEMENTS）", elements <= MAX_ELEMENTS)

            // **死规则清零**（reader-theme-family-rework spec R4 Scenario）：CSS 里声明的 `.dh-*` 类
            // 必须全部在 HTML 或 JS 中有供给。旧任务正是漏了两条（`dh-c-bl` / `dh-c-tr`：CSS 声明、
            // HTML 从不出现）⇒ 角饰只画了两角，而这类缺陷**不报错**，只表现为"规则恒空"。
            val declaredClasses = Regex("\\.(dh-[a-z0-9_-]+)").findAll(css).map { it.groupValues[1] }.toSet()
            val suppliedClasses = Regex("dh-[a-z0-9_-]+").findAll(source).map { it.value }.toSet()
            assertEquals(
                "${builtin.id} 存在死规则（CSS 声明了却无供给）：${(declaredClasses - suppliedClasses).sorted()}",
                emptyList<String>(),
                (declaredClasses - suppliedClasses).sorted()
            )
        }
    }

    @Test
    fun `内置模板动效在场且只用双方共有的作者 API`() {
        // 用户目标「基于 archive 主题模式优化内置主题」+「互兼容、行为尽可能一样」：
        // ①每套内置模板必须有动效；②动效只能使用**双方共有的**钩子 + Web Animations。
        val allowedMembers = setOf(
            "on", "source", "viewport", "fields", "pageCount", "pageIndex",
            "motionState", "waitUntil", "requestLayout"
        )
        val allowedHooks = setOf(
            "beforeLayout", "afterLayout", "beforePage", "pageChange", "motionChange", "fieldsChange", "dispose"
        )
        load().templates.forEach { builtin ->
            val js = builtin.template.javascript
            val css = builtin.template.css
            val hasMotion = js.isNotBlank() || Regex("animation\\s*:").containsMatchIn(css)
            assertTrue("${builtin.id} 必须带动效（否则用户点名的「没有动图效果」仍在）", hasMotion)
            if (js.isBlank()) return@forEach
            val members = Regex("readerTemplate\\.([A-Za-z_$][\\w$]*)").findAll(js).map { it.groupValues[1] }.toSet()
            assertTrue("${builtin.id} 用了非共有成员：${members - allowedMembers}", allowedMembers.containsAll(members))
            val hooks = Regex("readerTemplate\\.on\\(\\s*'([a-zA-Z]+)'").findAll(js).map { it.groupValues[1] }.toSet()
            assertTrue("${builtin.id} 注册了非共有钩子：${hooks - allowedHooks}", allowedHooks.containsAll(hooks))
            assertTrue(
                "${builtin.id} 动效须由 motionChange 驱动（否则专注模式/水墨屏停动效失效）",
                js.contains("'motionChange'")
            )
            assertTrue("${builtin.id} 动效须在 dispose 时清理", js.contains("'dispose'"))
        }
    }

    @Test
    fun `分页模板确有首页与续页两套结构`() {
        // 4.15 C1：`firstPageHtml` / `otherPageHtml` 必须**真的不同**（开篇页 vs 正文页）。
        val paged = load().templates.filter { !it.isScroll }
        assertTrue("至少一套分页模板", paged.isNotEmpty())
        paged.forEach { builtin ->
            val t = builtin.template
            assertTrue("${builtin.id} 必须声明首页结构", t.firstPageHtml.isNotBlank())
            assertTrue("${builtin.id} 必须声明续页结构", t.otherPageHtml.isNotBlank())
            assertTrue(
                "${builtin.id} 的首页结构与续页结构必须不同（否则按页换壳是空动作 ⇒ C1 未落地）",
                t.firstPageHtml.trim() != t.otherPageHtml.trim()
            )
            assertTrue(
                "${builtin.id} 的首页结构应比续页更满（开篇页 = 封面/场景，续页 = 窄页眉 + 正文）",
                t.firstPageHtml.length > t.otherPageHtml.length
            )
        }
    }

    @Test
    fun `合规红线 零外部依赖`() {
        load().templates.forEach { builtin ->
            val source = builtin.template.resourceSource()
            assertFalse("${builtin.id} 不得引用网络资源", source.contains("http://") || source.contains("https://"))
            assertFalse("${builtin.id} 不得使用 @import", source.contains("@import"))
            assertFalse("${builtin.id} 不得有 fetch/XHR", source.contains("fetch(") || source.contains("XMLHttpRequest"))
            // 沙箱边界：模板 JS 不得自行触达网络 / 宿主 / 存储（隔离纪律）
            val js = builtin.template.javascript
            listOf("fetch(", "XMLHttpRequest", "window.parent", "window.top", "localStorage", "document.cookie")
                .forEach { forbidden ->
                    assertFalse("${builtin.id} 的模板 JS 不得触及 $forbidden", js.contains(forbidden))
                }
            assertFalse(
                "${builtin.id} 不得引用宿主桥对象（沙箱禁宿主对象注入）",
                js.contains("legadoBridge") || js.contains("androidBridge") || js.contains("readerBridge")
            )
        }
    }

    @Test
    fun `合规红线 无第三方 IP 关键词且来源声明在场`() {
        load().templates.forEach { builtin ->
            // 关键词扫描必须**跳过内联 base64 载荷**：base64 是 4 字符表随机串，必然偶然命中短关键词。
            val lower = plainCss(builtin.template.resourceSource()).lowercase()
            FORBIDDEN_IP_KEYWORDS.forEach { keyword ->
                assertFalse("${builtin.id} 不得出现第三方 IP 素材关键词：$keyword", lower.contains(keyword))
            }
            assertTrue("${builtin.id} 必须附 sources.json", builtin.sources.isNotBlank())
            assertTrue("${builtin.id} 来源声明须含许可字段", builtin.sources.contains("license"))
            val root = JsonParser.parseString(builtin.sources).asJsonObject
            assertTrue("${builtin.id} 来源声明须含 assets 字段", root.get("assets")?.isJsonArray == true)
            assertTrue(
                "${builtin.id} 须声明「非官方 / 不代表原作方」（第三方素材准入的兜底口径）",
                builtin.sources.contains("非官方") || builtin.sources.contains("不代表")
            )
        }
    }

    @Test
    fun `素材登记与内联字节双向闭合且SHA-256一致`() {
        // 「无走私 / 无死登记」的机检口径：登记项数 == 内联 data: 项数，且**两边的 SHA-256 集相等**。
        // 只数个数会被"登记 A 却在 CSS 里内联 B"绕过；逐字节比 SHA 才能钉住"登记即内联的那一份"。
        load().templates.forEach { builtin ->
            val assets = JsonParser.parseString(builtin.sources).asJsonObject.getAsJsonArray("assets")
            assertNotNull("${builtin.id} 来源声明缺 assets 数组", assets)
            val inline = INLINE_DATA.findAll(builtin.template.resourceSource()).toList()
            assertEquals(
                "${builtin.id} 内联 data: 素材数 ${inline.size} 与登记数 ${assets.size()} 不符（有走私或死登记）",
                assets.size(), inline.size
            )
            val registered = assets.map { it.asJsonObject.get("sha256").asString }.toSet()
            val actual = inline.map { sha256(Base64.getDecoder().decode(it.value.substringAfter("base64,"))) }.toSet()
            assertEquals("${builtin.id} 登记 SHA 集与内联字节 SHA 集不一致（素材被改或登记失真）", registered, actual)
        }
    }

    @Test
    fun `三主题态变量均被定义`() {
        load().templates.forEach { builtin ->
            val css = builtin.template.css
            assertTrue("${builtin.id} 必须有日间基线（:root 变量）", css.contains(":root"))
            assertTrue(
                "${builtin.id} 必须定义夜间主题（[data-reader-theme=\"night\"]）",
                css.contains("[data-reader-theme=\"night\"]")
            )
            assertTrue(
                "${builtin.id} 必须定义水墨屏主题（[data-reader-theme=\"eink\"]）",
                css.contains("[data-reader-theme=\"eink\"]")
            )
        }
    }

    @Test
    fun `正文安全区与测量无关的装饰约束`() {
        load().templates.forEach { builtin ->
            val css = plainCss(builtin.template.css)
            // 装饰必须脱离正文测量（蓝图硬约束：装饰区 ∩ 正文安全区 = ∅）。
            val decorationsDetached = if (builtin.isScroll) {
                (css.contains("flex:0 0 auto") || css.contains("position:fixed") || css.contains("position:absolute")) &&
                    css.contains("overflow-y:auto")
            } else {
                css.contains("position:absolute") || css.contains("::after") || css.contains("::before")
            }
            assertTrue(
                "${builtin.id} 装饰须脱离正文流（分页用绝对定位/伪元素；滚动用固定页眉页脚外壳）",
                decorationsDetached
            )
            // 装饰带高度预算（蓝图：页眉/页脚各 ≤15% 视口高）
            VH_LENGTH.findAll(css).forEach { match ->
                val value = match.groupValues[1].toFloat()
                assertTrue(
                    "${builtin.id} 装饰带高度 ${value}vh 超出 15% 预算（100vh 满高容器除外）",
                    value <= 15f || value == 100f
                )
            }
            val declaresMotion = MOTION_DECLARATIONS.any { css.contains(it) }
            if (declaresMotion) {
                assertTrue(
                    "${builtin.id} 声明了动效就必须提供 prefers-reduced-motion 静默分支",
                    css.contains("prefers-reduced-motion")
                )
            }
            // 正文区下限可用判据：字号/行高变量必须被宿主下发并被消费
            assertTrue(
                "${builtin.id} 须支持宿主下发字号/行高",
                css.contains("--md-font-size") && css.contains("--md-line-height")
            )
        }
    }

    @Test
    fun `缺失模板文件时给出可诊断错误`() {
        val broken = ReaderBuiltinTemplateCatalog.load { path ->
            if (path == ReaderBuiltinTemplateCatalog.CatalogAsset) {
                "{\"schemaVersion\":1,\"templates\":[\"builtin.missing\"]}"
            } else {
                null
            }
        }
        assertEquals(0, broken.templates.size)
        assertTrue(broken.errors.single().contains("缺少内置模板文件"))
    }

    @Test
    fun `id 不一致时拒绝并入并报错`() {
        val mismatched = ReaderBuiltinTemplateCatalog.load { path ->
            when (path) {
                ReaderBuiltinTemplateCatalog.CatalogAsset ->
                    "{\"schemaVersion\":1,\"templates\":[\"builtin.a\"]}"
                ReaderBuiltinTemplateCatalog.templatePath("builtin.a") -> """
                    {"schemaVersion":1,"type":"paged","id":"builtin.b","name":"错配",
                     "firstPageHtml":"<div data-reader-flow=\"body\"></div>",
                     "otherPageHtml":"<div data-reader-flow=\"body\"></div>",
                     "scrollHtml":"","css":":root{}[data-reader-theme=\"night\"]{}","javascript":""}
                """.trimIndent()
                else -> null
            }
        }
        assertEquals(0, mismatched.templates.size)
        assertTrue(mismatched.errors.single().contains("与目录不一致"))
    }

    /** 剥除内联 base64 载荷（关键词/尺寸类扫描必须先做，否则随机串会造假阳性）。 */
    private fun plainCss(text: String): String = INLINE_DATA.replace(text, " ")

    private fun sha256(bytes: ByteArray): String =
        MessageDigest.getInstance("SHA-256").digest(bytes).joinToString("") {
            (it.toInt() and 0xff).toString(16).padStart(2, '0')
        }

    private companion object {
        val FIELD = Regex("""data-reader-field="([^"]+)"""")

        /** 字段槽位白名单 = TPL-15 C2 口径（宿主提供 + 沙箱派生）。 */
        val ALLOWED_FIELDS = setOf(
            "bookName", "chapterTitle", "progress", "page", "pageCount", "time", "battery", "percent"
        )

        /** 动效声明特征：出现任一项即必须提供 `prefers-reduced-motion` 静默分支。 */
        val MOTION_DECLARATIONS = listOf("@keyframes", "animation:", "transition:", "scroll-behavior: smooth")

        /** 视口高尺寸声明（用于装饰带高度预算校验）。 */
        val VH_LENGTH = Regex("""(\d+(?:\.\d+)?)vh""")

        /** 4.19 / NFR-08 元素与动效预算（提交期静态门禁）。
         *  ⚠️ 2026-10-19（reader-theme-family-rework R4）：用户明确要求「怪物/特效多引、页眉密度上去」
         *  ⇒ 元素/动效规模必然上升。引擎运行时的元素上限是 `MAX_ELEMENTS = 3000`（`md/template-runtime.js`），
         *  本门禁只是**提交期静态门禁**，故按"仍远离运行时上限"上调（原 8 / 12 / 120）。
         *  实测现值：keyframes 12 / animation 声明 14 / 结构元素 172（均留余量）。 */
        const val MAX_KEYFRAMES = 14
        const val MAX_ANIMATION_DECLARATIONS = 20
        const val MAX_ELEMENTS = 200

        /** 段落语义类（与 archive 主题 as-lead / as-dialogue / as-scene 同构的三类）。 */
        val PARAGRAPH_CLASSES = listOf("dh-lead", "dh-dialogue", "dh-scene")

        /** 段落分类判据（**与 archive 主题逐字同口径**：场景分隔段 / 对白段）。 */
        val PARAGRAPH_THRESHOLDS = listOf(
            """/^[*＊※·•—_\-\s]{3,}$/""",
            """/^[“「『"]/"""
        )

        /** 第三方 IP 关键词（合规红线：不得内置 IP 原作素材）。 */
        val FORBIDDEN_IP_KEYWORDS = listOf(
            "asuka", "eva", "evangelion", "doraemon", "minecraft", "pokemon", "naruto", "hatsune"
        )

        /** 内联 base64 载荷（关键词/尺寸扫描前必须剔除）。 */
        val INLINE_DATA = Regex("""data:[a-zA-Z0-9.+-]+/[a-zA-Z0-9.+-]+;base64,[A-Za-z0-9+/=]+""")
    }
}
