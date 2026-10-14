package io.legado.app.model.localBook.epubcore.template

import com.google.gson.JsonParser
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File

/**
 * 内置模板资产校验单测（epub-md-rich-rendering 阶段 4.12 配对）。
 *
 * 直接把 `src/main/assets/reader/` 下的**真实资产**读进来逐项校验——这是"内置模板"唯一
 * 能在 JVM 侧拿到强证据的手段（真机只验证观感与交互）。
 *
 * 覆盖：①目录与文件一一对应且 id 一致；②每套通过结构校验（走与用户导入**同一条**路径）；
 * ③**作者契约**在场（`data-reader-flow="body"` 必需、字段槽位合法、滚动模板必须有
 * `data-reader-scroll-viewport`）；④**合规红线**：零外部网络依赖、零外部字体/图片文件、
 * 无第三方 IP 关键词、`sources.json` 在场；⑤日/夜双主题变量在场（可读性底线）；
 * ⑥首批数量与类型覆盖（paged + scroll 两条路径都被覆盖）。
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
        assertTrue("首批至少应交付 2 套（MVP）", result.templates.size >= 2)
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
                assertTrue(
                    "${builtin.id} 滚动模板必须声明唯一天地画框",
                    source.contains("data-reader-scroll-viewport")
                )
                assertEquals(
                    "${builtin.id} 滚动画框必须唯一",
                    1,
                    Regex("data-reader-scroll-viewport").findAll(source).count()
                )
            } else {
                assertFalse("${builtin.id} 分页模板不应出现滚动画框", source.contains("data-reader-scroll-viewport"))
            }
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
        // 运行期自证（`elems=`/`anims=`）只能事后发现；提交期按资产静态计数才能拦在交付前。
        // 预算取宽松值，只拦"数量级失控"而非审美取舍（动效本体由各主题 `javascript` 用 Web Animations 驱动，
        // 不计入本表；本表只数 CSS 侧的 `@keyframes`/`animation:` 声明）。
        load().templates.forEach { builtin ->
            val css = builtin.template.css
            val source = builtin.template.resourceSource()
            val keyframes = Regex("@keyframes").findAll(css).count()
            assertTrue("${builtin.id} @keyframes 数量 $keyframes 超预算（≤$MAX_KEYFRAMES）", keyframes <= MAX_KEYFRAMES)
            val declared = Regex("animation\\s*:").findAll(css).count()
            assertTrue(
                "${builtin.id} animation 声明 $declared 处超预算（≤$MAX_ANIMATION_DECLARATIONS）",
                declared <= MAX_ANIMATION_DECLARATIONS
            )
            val elements = Regex("<[a-zA-Z][^>]*>").findAll(source).count()
            assertTrue("${builtin.id} 结构元素 $elements 个超预算（≤$MAX_ELEMENTS）", elements <= MAX_ELEMENTS)
        }
    }

    @Test
    fun `内置模板动效在场且只用双方共有的作者 API`() {
        // 用户目标「基于 archive 主题模式优化内置主题」+「互兼容、行为尽可能一样」：
        // ①每套内置模板必须有动效（否则就是用户点名的「没有动图效果」）；
        // ②动效只能使用**双方共有的** `readerTemplate` 钩子 API + Web Animations ——
        //   一旦用了任何一方私有的桥字段/变量，导出到另一方就会静默失效（互兼容断掉）。
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
        // 若两者逐字相同，换壳就是空动作 —— C1 实现成了死代码（"看起来实现了，实则没差别"）。
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
            // 开篇页必有"仪式感"元素（整幅插画/大标题），即除正文槽位外还有作者装饰节点；
            // 判据取"节点数更多"这一可机检口径，避免给每套模板写白名单关键词
            assertTrue(
                "${builtin.id} 的首页结构应比续页更满（开篇页 = 封面/题词，续页 = 窄页眉 + 正文）",
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
            // 内联 `data:` 素材自 4.16 起**允许**（成套美术的字体/纹理只能内联：沙箱 iframe 无 base URL、
            // 字体跨源受 CORS 限制）。"不得走私未登记素材"改由 `ReaderBuiltinTemplateAssetsTest`
            // 以"登记数 == 内联数"双向闭合校验（此处不再重复断言，避免两处口径漂移）。
            //
            // ⚠️ 口径变更（2026-10-14，用户目标「内置主题要有动图效果/互兼容、行为尽可能一样」）：
            // 原先"内置模板不得含 `javascript`（纯 CSS）"这条红线**已按新设计作废** —— 内置主题的每页动效
            // 与 archive 主题**同机制**（共有的 `readerTemplate` 钩子 + Web Animations），只写 CSS 做不出来。
            // 取而代之的是**更准确的沙箱边界**：模板 JS 不得自行触达网络 / 宿主 / 存储（隔离纪律不变）。
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
            // 关键词扫描必须**跳过内联 base64 载荷**：base64 是 4 字符表随机串，必然偶然命中
            // `eva` 这类短关键词（实测 neon-night 的字体/纹理载荷即命中）——这是**假阳性**，
            // 而"素材是否含 IP 内容"应由人工看素材本身 + `sources.json` 的来源/许可判定。
            val lower = INLINE_DATA.replace(builtin.template.resourceSource(), " ").lowercase()
            FORBIDDEN_IP_KEYWORDS.forEach { keyword ->
                assertFalse("${builtin.id} 不得出现第三方 IP 素材关键词：$keyword", lower.contains(keyword))
            }
            assertTrue("${builtin.id} 必须附 sources.json", builtin.sources.isNotBlank())
            assertTrue("${builtin.id} 来源声明须含许可字段", builtin.sources.contains("license"))
            // 4.16 起 `assets` 可为空数组（纯 CSS 模板）或成套美术登记表（旗舰主题）⇒
            // 只要求字段在场且是数组；登记项的完整性/可考证性由 `ReaderBuiltinTemplateAssetsTest` 逐项校验。
            val root = JsonParser.parseString(builtin.sources).asJsonObject
            val assets = root.get("assets")
            assertTrue("${builtin.id} 来源声明须含 assets 字段", assets != null && assets.isJsonArray)
        }
    }

    @Test
    fun `日与夜双主题均被定义`() {
        load().templates.forEach { builtin ->
            val css = builtin.template.css
            assertTrue("${builtin.id} 必须有日间基线（:root 变量）", css.contains(":root"))
            assertTrue(
                "${builtin.id} 必须定义夜间主题（[data-reader-theme=\"night\"]）",
                css.contains("[data-reader-theme=\"night\"]")
            )
        }
    }

    @Test
    fun `正文安全区与测量无关的装饰约束`() {
        load().templates.forEach { builtin ->
            val css = builtin.template.css
            // 装饰必须脱离正文测量（蓝图硬约束：装饰区 ∩ 正文安全区 = ∅）。
            // 判据按类型分流，避免拿分页口径套滚动模板：
            // - 分页：装饰用绝对定位/伪元素（不参与正文流）
            // - 滚动：页眉/页脚为固定尺寸外壳（flex:0 0 auto 或 fixed/absolute），正文独占滚动画框
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
            if (builtin.isScroll) {
                // 真机铁证（2026-10-10，data-stream 首版）：模板文档 DOM 是
                // html > body > #reader-template-root > 作者外壳，而**根壳是普通流容器（非定高）**
                // ⇒ 外壳写 `height:100%` 会塌成"内容高"，滚动画框随之失去滚动（页数恒 1、点击翻页无反应）。
                // 正确口径：外壳用**视口单位**（`100vh`）定高（既有卷轴模板即如此）。
                assertTrue(
                    "${builtin.id} 滚动外壳必须用 100vh 定高（height:100% 会塌陷 ⇒ 画框无滚动、翻页失效）",
                    css.contains("100vh")
                )
            }
            // 装饰带高度预算（蓝图：页眉/页脚各 ≤15% 视口高）：除满高容器（100vh）外，
            // 不得出现 >15vh 的装饰块——插画/装饰带挤占正文正是 archive 观感最大的失分点。
            VH_LENGTH.findAll(css).forEach { match ->
                val value = match.groupValues[1].toFloat()
                assertTrue(
                    "${builtin.id} 装饰带高度 ${value}vh 超出 15% 预算（100vh 满高容器除外）",
                    value <= 15f || value == 100f
                )
            }
            // 尊重减少动效（无障碍/省电）：**声明了动效的模板必须给出静默分支**。
            // 零动效模板（本批为纯静态 CSS）不强制写空分支——空 @media 是死 CSS，不构成证据；
            // 该断言随模板引入动效后自动收紧（4.15 内容感知运行时 / 4.16 成套美术）。
            val declaresMotion = MOTION_DECLARATIONS.any { css.contains(it) }
            if (declaresMotion) {
                assertTrue(
                    "${builtin.id} 声明了动效就必须提供 prefers-reduced-motion 静默分支",
                    css.contains("prefers-reduced-motion")
                )
            }
            // 正文区下限可用 [ReaderTemplateDecorationPolicy] 判据（此处校验字号/行高变量被使用）
            assertTrue(
                "${builtin.id} 须支持宿主下发字号/行高",
                css.contains("--md-font-size") && css.contains("--md-line-height")
            )
        }
    }

    @Test
    fun `首批 11 套齐备且两条渲染路径都在`() {
        // 资产是"静默少一套"的高发区（打包漏带/改名错配都不会让编译失败）⇒ 逐 id 点到
        val loaded = load().templates
        val ids = loaded.map { it.id }.toSet()
        val required = setOf(
            "builtin.neon-night",   // A1 旗舰（暗色默认）
            "builtin.minimal-tech", // A4 极简科技（浅色默认，SP-06）
            "builtin.terminal", "builtin.glass", "builtin.cyber-city",
            "builtin.data-stream",  // A6 滚动型
            "builtin.minimal-ink", "builtin.ink", "builtin.star-chart",
            "builtin.pixel-grid", "builtin.paper-scroll"
        )
        assertEquals("缺失内置模板：${required - ids}", emptySet<String>(), required - ids)
        assertTrue("首批不得少于 11 套（当前 ${ids.size}）", ids.size >= 11)
        assertEquals("至少两套滚动模板（scroll 契约需被多套覆盖）", 2, loaded.count { it.isScroll })
        assertEquals("每套都必须附上来源声明", loaded.size, loaded.count { it.sources.isNotBlank() })
    }

    @Test
    fun `paged 与 scroll 两条渲染路径均被覆盖`() {
        val templates = load().templates
        assertTrue("至少一套分页模板", templates.any { !it.isScroll })
        assertTrue("至少一套滚动模板（验证 scroll 契约）", templates.any { it.isScroll })
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
                    {"schemaVersion":2,"type":"paged","id":"builtin.b","name":"错配",
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

        /** 4.19 / NFR-08 元素与动效预算（提交期静态门禁；运行期自证口径见 `template-runtime.js`）。 */
        const val MAX_KEYFRAMES = 8
        const val MAX_ANIMATION_DECLARATIONS = 12
        const val MAX_ELEMENTS = 120

        /** 第三方 IP 关键词（合规红线：不得内置 IP 原作素材）。 */
        val FORBIDDEN_IP_KEYWORDS = listOf(
            "asuka", "eva", "evangelion", "doraemon", "minecraft", "pokemon", "naruto", "hatsune"
        )

        /** 内联 base64 载荷（关键词扫描前必须剔除，否则随机串会假阳性命中短关键词）。 */
        val INLINE_DATA = Regex("""data:[a-zA-Z0-9.+-]+/[a-zA-Z0-9.+-]+;base64,[A-Za-z0-9+/=]+""")
    }
}