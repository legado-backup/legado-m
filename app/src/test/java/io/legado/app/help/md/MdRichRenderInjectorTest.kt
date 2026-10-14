package io.legado.app.help.md

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Markdown 富渲染注入器单测（epub-md-rich-rendering 阶段 3.8/3.9 配对）。
 *
 * 覆盖【验证标准】中**可 JVM 断言**的部分：
 * ①mermaid 安全与稳定选项齐备（`startOnLoad:false` / `securityLevel:'strict'` / `htmlLabels:false` / `suppressErrors:true`）；
 * ②KaTeX 安全与限额选项齐备（`trust:false` / `strict:'warn'` / `throwOnError:false` / `maxSize` / `maxExpand`）；
 * ③按需注入（无 mermaid/公式/代码块 ⇒ 不注入对应运行时，2.4MB 不白带）；
 * ④降级分支存在（缺失/异常 ⇒ `md-rich-fallback` 外观，不中断）；
 * ⑤防二次渲染标记；⑥主题名白名单（防注入）；⑦超时兜底信号。
 * 真正的"渲染为 SVG 而非代码块"属真机 L2。
 */
class MdRichRenderInjectorTest {

    private val assets = MdRichRenderInjector.Assets(
        mermaidJs = "/*MERMAID_JS*/",
        katexJs = "/*KATEX_JS*/",
        katexCss = "/*KATEX_CSS*/",
        highlightJs = "/*HLJS*/",
        highlightCss = "/*HLJS_CSS*/"
    )

    private fun build(
        options: MdRichRenderInjector.Options = MdRichRenderInjector.Options(),
        assets: MdRichRenderInjector.Assets = this.assets,
        needsMermaid: Boolean = true,
        needsMath: Boolean = true
    ) = MdRichRenderInjector.build(options, assets, needsMermaid, needsMath)

    @Test
    fun `mermaid 运行时安全与稳定选项齐备`() {
        val script = build().script
        assertTrue("必须离线内联运行时", script.contains("/*MERMAID_JS*/"))
        assertTrue(script.contains("startOnLoad:false"))
        assertTrue(script.contains("securityLevel:'strict'"))
        assertTrue(script.contains("htmlLabels:false"))
        assertTrue("单图失败不得中断整页", script.contains("suppressErrors:true"))
        assertTrue("渲染时机须由我们控制（字体/DOM 就绪后）", script.contains("runMermaid()"))
    }

    @Test
    fun `katex 运行时安全与限额选项齐备`() {
        val script = build().script
        assertTrue(script.contains("/*KATEX_JS*/"))
        assertTrue("须拒 href 等危险命令", script.contains("trust:false"))
        assertTrue(script.contains("strict:'warn'"))
        assertTrue("错误渲染为文本而非抛异常", script.contains("throwOnError:false"))
        assertTrue(script.contains("maxSize:200"))
        assertTrue(script.contains("maxExpand:1000"))
    }

    @Test
    fun `代码高亮在就绪后执行且可选关闭`() {
        assertTrue(build().script.contains("/*HLJS*/"))
        assertTrue(build().script.contains("highlightElement"))
        val off = build(MdRichRenderInjector.Options(highlightCode = false))
        assertFalse(off.script.contains("/*HLJS*/"))
    }

    @Test
    fun `无 mermaid 标注时不注入 mermaid 运行时`() {
        val injection = build(needsMermaid = false)
        assertFalse("不得白带 2.4MB 运行时", injection.script.contains("/*MERMAID_JS*/"))
        assertFalse(injection.script.contains("runMermaid"))
    }

    @Test
    fun `无公式标注时不注入 katex 运行时`() {
        val injection = build(needsMath = false)
        assertFalse(injection.script.contains("/*KATEX_JS*/"))
        assertFalse(injection.css.contains("/*KATEX_CSS*/"))
    }

    @Test
    fun `资产缺失时按需跳过且不抛异常`() {
        val empty = MdRichRenderInjector.Assets()
        val injection = build(assets = empty)
        assertFalse(injection.script.contains("MERMAID_JS"))
        assertFalse(injection.script.contains("KATEX_JS"))
        assertTrue("无任何可注入内容时脚本为空", injection.script.isBlank())
    }

    @Test
    fun `三项全关时不产出脚本`() {
        val injection = build(
            MdRichRenderInjector.Options(renderMermaid = false, renderMath = false, highlightCode = false)
        )
        assertTrue(injection.isEmpty)
        assertTrue(MdRichRenderInjector.wrapHtml(injection).isBlank())
    }

    @Test
    fun `降级分支存在且给出可见外观`() {
        val script = build().script
        assertTrue("缺失时降级", script.contains("'mermaid-missing'"))
        assertTrue("运行异常时降级", script.contains("'mermaid-run'"))
        assertTrue(script.contains("'katex'"))
        assertTrue("降级须落到可见类名", script.contains("md-rich-fallback"))
        assertTrue("降级标记须可诊断", script.contains("data-md-fallback"))
    }

    @Test
    fun `降级外观绝不打在整页根上`() {
        // 2026-10-14 真机铁证：模板主题下出现「左右异色带（黑边）+ 底色不对」。根因是库缺失分支把
        // `md-rich-fallback` 打在 `document.body` 上 —— 该类的 `border-left:3px` 在 content-box 下
        // 吃掉内容盒宽度（实测 body.borderLeftWidth=2.7px ⇒ 页根 480→477、整体右移 3px，右侧露出
        // 画布底色），`background:var(--md-code-bg)` 又把整页底色改成代码块色。
        // "库缺失"是**全局状态**（没有对应的失败块）⇒ 只应记入 status.error。
        val script = build().script
        assertFalse(
            "不得对 document.body / documentElement 打降级外观类",
            script.contains("markFallback(document.body") || script.contains("markFallback(document.documentElement")
        )
        assertTrue(
            "须有整页根守护（命中 body/html 时只记状态、不打类）",
            script.contains("if(el===document.body||el===document.documentElement){status.error=status.error||kind;return;}")
        )
        assertTrue(
            "库缺失须改为标记各自目标节点（图/代码块），保住可见降级契约",
            script.contains("function markFallbackTargets(") &&
                script.contains("markFallbackTargets('pre.mermaid,div.mermaid','mermaid-missing')") &&
                script.contains("markFallbackTargets('pre code','hljs-missing')")
        )
        // 反向锁：katex 缺失没有明确目标节点，禁止退化成通配标记（那会把降级外观撒满整页）
        assertFalse("katex 缺失不得用通配选择器标满全页", script.contains("markFallbackTargets('*'"))
    }

    @Test
    fun `防二次渲染标记被选择器与写入两侧同时使用`() {
        val script = build().script
        val attribute = MdRichRenderInjector.RenderedAttribute
        assertTrue("选择器须排除已渲染节点", script.contains("!n.getAttribute('$attribute')"))
        assertTrue("渲染后须打标", script.contains("setAttribute('$attribute','mermaid')"))
        assertTrue(script.contains("setAttribute('$attribute','math')"))
        assertTrue(script.contains("setAttribute('$attribute','code')"))
    }

    @Test
    fun `公式扫描跳过代码块避免误渲染`() {
        val script = build().script
        assertTrue(script.contains("tag==='code'"))
        assertTrue(script.contains("tag==='pre'"))
    }

    @Test
    fun `mermaid 主题名走白名单防注入`() {
        val injected = build(MdRichRenderInjector.Options(mermaidTheme = "';alert(1);//"))
        assertTrue(injected.script.contains("theme:'default'"))
        assertFalse(injected.script.contains("alert(1)"))

        val dark = build(MdRichRenderInjector.Options(mermaidTheme = MdRichRenderInjector.MermaidThemeDark))
        assertTrue(dark.script.contains("theme:'dark'"))
    }

    @Test
    fun `渲染完成信号与超时兜底齐备`() {
        val script = build().script
        assertTrue(script.contains("window.${MdRichRenderInjector.StatusGlobal}=status"))
        assertTrue("须有 done 标记供宿主轮询", script.contains("status.done=true"))
        assertTrue("超时也必须置完成，避免分页永久等待", script.contains("setTimeout(finish,"))
        assertTrue(script.contains("clearTimeout(timeout);finish();"))
    }

    @Test
    fun `超时阈值可按需收紧`() {
        val script = build(MdRichRenderInjector.Options(timeoutMillis = 1_500L)).script
        assertTrue(script.contains("setTimeout(finish,1500)"))
    }

    @Test
    fun `包裹后的 HTML 带稳定 id 便于宿主定位`() {
        val html = MdRichRenderInjector.wrapHtml(build())
        assertTrue(html.startsWith("<style id=\"legado-md-vendor-css\">"))
        assertTrue(html.contains("<script id=\"legado-md-rich-render\">"))
        assertTrue(html.endsWith("</script>"))
    }

    @Test
    fun `资产路径与阶段零导入的 vendor 布局一致`() {
        assertEquals("md/md-reader.css", MdRichRenderInjector.MdReaderCssAsset)
        assertEquals("md/vendor/mermaid.min.js", MdRichRenderInjector.MermaidAsset)
        assertEquals("md/vendor/katex.min.js", MdRichRenderInjector.KatexAsset)
        assertEquals("md/vendor/katex.min.css", MdRichRenderInjector.KatexCssAsset)
        assertEquals("md/vendor/highlight.min.js", MdRichRenderInjector.HighlightAsset)
        assertEquals("md/vendor/hljs-light.min.css", MdRichRenderInjector.HighlightLightCssAsset)
        assertEquals("md/vendor/hljs-dark.min.css", MdRichRenderInjector.HighlightDarkCssAsset)
        assertEquals("md/template-decoration.css", MdRichRenderInjector.TemplateDecorationCssAsset)
        assertEquals("md/template-layout.css", MdRichRenderInjector.TemplateLayoutCssAsset)
    }

    @Test
    fun `布局基线提供响应式收紧与竖排规格`() {
        // 4.15 C9/C10：布局基线必须**与装饰基线分离**（装饰基线禁止声明几何，见上一测试），
        // 且规则全部由运行时写在 <html> 上的状态开关驱动（作者未声明对应状态时一条都不生效）。
        val css = SourceFileProbe.assetRawText(MdRichRenderInjector.TemplateLayoutCssAsset)
        assertTrue("C9：须有窄屏开关（供作者 CSS 消费）", css.contains("data-rp-narrow"))
        assertTrue("C9：须有横屏开关（供作者 CSS 消费）", css.contains("data-rp-landscape"))
        assertTrue("C9：收紧系数保留为**可选变量**（宿主/运行时单源）", css.contains("--rp-chrome-scale"))
        // 2026-10-13（AD-36）：引擎级收紧**已废止** —— `transform: scale()` 只缩视觉不动布局盒（留下大片空白），
        // `zoom` 缩放元素自身盒宽（页眉页脚右侧空出一条）。收紧的正解是模板用相对单位声明 + 引擎把剩余空间交还正文槽。
        assertFalse(
            "C9：引擎不得再对模板外壳施加缩放（两种实现都已被真机证伪；注释里回顾旧实现不算）",
            css.contains("transform: scale(var(")
        )
        assertTrue(
            "分页前提：正文须落在**整行网格**上（否则段距推移网格 ⇒ 末行被裁半）",
            css.contains("--rp-line-height") && css.contains("padding-top: var(--rp-line-height")
        )
        assertTrue("整行对齐残量须有底色兜底（画布恒铺满视口）", css.contains("min-height: 100vh"))
        assertFalse("职责分离：布局基线不得重复装饰强度规则（那是装饰基线的职责）", css.contains("data-rp-decoration"))
        assertTrue("C10：须有竖排开关", css.contains("data-rp-writing=\"vertical\""))
        assertTrue("C10：段距须走逻辑属性 block 轴", css.contains("margin-block-end"))
        assertTrue("C10：图片须按逻辑轴区域约束", css.contains("max-inline-size") && css.contains("max-block-size"))
        assertTrue("C10：须有接排去重缩进落点", css.contains("data-reader-continued"))
    }

    @Test
    fun `装饰基线 css 只动观感不动几何且用户设置优先`() {
        // 4.8d / AD-33：装饰强度**不得**参与正文测量（否则改档位会改页数）。
        // 该不变量在 CSS 层只能靠"只用 opacity/animation"保证 ⇒ 源码级钉住：
        // 装饰基线里若出现尺寸/间距/字号声明，说明有人把装饰写成了布局的一部分。
        val css = SourceFileProbe.assetRawText(MdRichRenderInjector.TemplateDecorationCssAsset)
        assertTrue("必须存在装饰强度规则", css.contains("data-rp-decoration"))
        assertTrue("用户设置必须先于作者 CSS（否则选'无'仍可能看到装饰）", css.contains("opacity: 0 !important"))
        listOf("width:", "height:", "margin", "padding", "font-size").forEach { banned ->
            assertFalse("装饰基线不得声明 $banned（装饰不参与正文测量）", css.contains(banned))
        }
    }

    @Test
    fun `厂商脚本独立返回且运行时脚本不含厂商本体`() {
        val assets = MdRichRenderInjector.Assets(
            mermaidJs = "MERMAID_BLOB",
            katexJs = "KATEX_BLOB",
            highlightJs = "HIGHLIGHT_BLOB"
        )
        val vendors = MdRichRenderInjector.vendorScripts(true, true, true, assets)
        assertEquals("三份厂商脚本各自独立返回", 3, vendors.size)
        assertTrue(vendors[0].contains("MERMAID_BLOB"))
        assertTrue(vendors[1].contains("KATEX_BLOB"))
        assertTrue(vendors[2].contains("HIGHLIGHT_BLOB"))

        val runtime = MdRichRenderInjector.runtimeScript(MdRichRenderInjector.Options(), true, true, true)
        // 关键不变量（真机铁证）：厂商 JS 的 `var` 依赖顶层作用域，被包进 IIFE 即失效
        // （mermaid 尾部读 globalThis.__esbuild_esm_mermaid.default ⇒ TypeError）
        assertFalse("运行时脚本不得内嵌厂商 JS 本体", runtime.contains("MERMAID_BLOB"))
        assertFalse(runtime.contains("KATEX_BLOB"))
        assertFalse(runtime.contains("HIGHLIGHT_BLOB"))
        assertTrue("运行时脚本仍是自建 IIFE", runtime.startsWith("(function(){"))
        assertTrue(runtime.contains("window.${MdRichRenderInjector.StatusGlobal}"))
    }

    @Test
    fun `build 把厂商脚本放在 IIFE 之外`() {
        val assets = MdRichRenderInjector.Assets(mermaidJs = "MERMAID_BLOB", highlightJs = "HIGHLIGHT_BLOB")
        val injection = MdRichRenderInjector.build(
            MdRichRenderInjector.Options(),
            assets,
            needsMermaid = true,
            needsMath = false
        )
        val vendorAt = injection.script.indexOf("MERMAID_BLOB")
        val iifeAt = injection.script.indexOf("(function(){")
        assertTrue("厂商脚本须在场", vendorAt >= 0)
        assertTrue("厂商脚本必须先于运行时 IIFE 且位于其外", vendorAt < iifeAt)
    }

    @Test
    fun `不需要任何运行时则不产出脚本`() {
        val assets = MdRichRenderInjector.Assets()
        val injection = MdRichRenderInjector.build(
            MdRichRenderInjector.Options(),
            assets,
            needsMermaid = true,
            needsMath = true
        )
        assertEquals("", injection.script)
        assertEquals(0, MdRichRenderInjector.vendorScripts(true, true, true, assets).size)
    }

    @Test
    fun `运行时暴露可重复运行入口并仍自动跑一次`() {
        val assets = MdRichRenderInjector.Assets(mermaidJs = "MERMAID_BLOB", katexJs = "KATEX_BLOB")
        val script = MdRichRenderInjector.runtimeScript(
            MdRichRenderInjector.Options(),
            wantMermaid = true,
            wantMath = true,
            wantHighlight = false
        )
        // 模板沙箱在正文经 init 注入后必须能再跑一次；且重跑要能覆盖上一轮的失败结论
        assertTrue("必须暴露 status.run", script.contains("status.run=runAll;"))
        assertTrue("重跑须重置完成标记", script.contains("status.done=false;status.error=null;"))
        assertTrue("自动驱动仍须跑一次（文本富渲染面依赖它）", script.contains("whenReady().then(runAll)"))
        assertTrue("完成标记语义不变（宿主轮询依赖）", script.contains("function finish(){status.done=true;}"))
    }

    @Test
    fun `模板基线资产按 archive 口径登记且顺序单源`() {
        // 2026-10-14：archive 原版基准对照暴露"导入主题左右露出底色 / 正文区偏小"的根因＝
        // 我方只注入 `--reader-*` 变量值、缺 archive `EpubTemplateDocument.baseCss` 的**页基线规则**。
        // 本包配对测试：资产登记、路径正确、顺序单源，且基线文件确实含那几组口径。
        assertEquals("md/template-archive-base.css", MdRichRenderInjector.ArchiveBaseCssAsset)
        assertEquals(
            "基线顺序单源（layout 的整行网格 !important 必须最后）",
            listOf(
                MdRichRenderInjector.MdReaderCssAsset,
                MdRichRenderInjector.ArchiveBaseCssAsset,
                MdRichRenderInjector.TemplateDecorationCssAsset,
                MdRichRenderInjector.TemplateLayoutCssAsset
            ),
            MdRichRenderInjector.TemplateBaselineCssAssets
        )
        val base = SourceFileProbe.assetRawText("md/template-archive-base.css")
        assertTrue("画布须铺满（html 定高 + body 以页背景兜底）",
            base.contains("height: 100%") && base.contains("--reader-page-background"))
        assertTrue("页根安全区须消费 --reader-safe-*", base.contains("[data-reader-page]") && base.contains("--reader-safe-"))
        assertTrue("段落基线须在场（段距/缩进/孤寡行）",
            base.contains(".reader-paragraph") && base.contains("orphans: 2") && base.contains("widows: 2"))
        assertTrue("body 无内边距须强制（否则根壳恒窄 ⇒ 左右露出底色）",
            base.contains("padding: 0 !important"))
        // 2026-10-14 真机铁证（「下面展示不全」）：archive 主题的页根是 `.as-page{width:100%;height:100%}`，
        // 其 `height:100%` 只在父级**有确定 height 属性**才解析 —— 父级仅靠 `min-height` 撑开时按规范
        // 落回 auto（实测页根 477×826 而视口 480×854 ⇒ 页脚整体下移、底部多 28px 空白）。
        // 故基线必须同时给"确定的 body 高"与"确定的页根宽高"，缺任一条都复现该缺陷。
        assertTrue("body 必须同时给确定 height 与 min-height（前者使子元素百分比高度可解析）",
            base.contains("height: 100%;\n  min-height: 100%;"))
        assertTrue("页根容器必须给确定宽高（作者主题以它为百分比基准）",
            base.contains("#reader-template-root {") && base.contains("width: 100%;\n  height: 100%;"))
    }
}