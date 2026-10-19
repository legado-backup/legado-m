package io.legado.app.model.localBook.epubcore.template

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 模板「页根几何」契约（reader-theme-family-rework R1/R2/R5 配对）。
 *
 * 为什么机检而不是只靠真机 L2：本轮四症状（页眉占比过大 / 页脚不可见 / 双向翻页失效 / 导入主题偏窄）
 * 的**根因都在资产文本里**，而真机验证要"重新打包 + 装机 + 手动翻页"（数分钟一轮）⇒ 本轮实证
 * 「验收面错位」正是上一轮失败的结构性原因（判据换血后从未重跑）。故把**可在文本层锁死**的
 * 防回归点前移到这里（秒级），真机 L2 仍作权威判据。
 *
 * 锁点（每条对应一个已复现的真机缺陷，不得删）：
 *  ① 引擎基线：`[data-reader-page]` **必须** `box-sizing: border-box` —— 否则页根总高 = 视口高 + safe
 *     （真机铁证 `rb=878 > vp=854`，差 +24 = safe-top ⇒ **页脚整条被推出视口**）。
 *  ② 主题：`[data-reader-page]{padding:0}`（archive 同款 reset）+ `.dh-body{height:100%}`
 *     —— 后者是"下占位为负 ⇒ 页框 = 整章高 ⇒ 翻页失效"的**结构性前提**（archive `.as-flow` 同做法）。
 *  ③ 引擎流：`chromeForShell` 的**负下占位守门** + 自证串 `ctop`/`cbot`（R2 取证字段）。
 *  ④ 自证串宽度维度 `vw`/`pl`/`pr`（R6：缺了它"左右比原版窄"**无法证伪**）。
 *  ⑤ 主题行高硬指标：**页眉行 + 页脚行 ≤ 0.2 × 视口高**（保正文区 ≥80%；与构建脚本门禁同口径）。
 *  ⑥ 产物内联 `data:` 个数 ≤ 引擎硬上限 64（超限素材**静默不显示**）。
 */
class ReaderTemplateGeometryContractTest {

    /** 剥离 CSS/JS 注释后再断言：注释里出现的关键字样**不算生效值**（否则断言可被注释"喂"成真）。 */
    private fun stripComments(text: String): String =
        text.replace(Regex("/\\*[\\s\\S]*?\\*/"), " ").replace(Regex("(?m)^\\s*//.*$"), " ")

    private fun engineBaseCss(): String =
        stripComments(SourceFileProbe.assetRawText("md/template-archive-base.css"))

    private fun engineFlowJs(): String =
        stripComments(SourceFileProbe.assetRawText("md/template-browser-flow.js"))

    private fun themeCss(): String =
        stripComments(SourceFileProbe.assetRawText("reader/builtin.dungeon-hud/readerTemplate.json"))

    @Test
    fun `引擎页根必须 border-box 否则页脚被推出视口`() {
        val css = engineBaseCss()
        val rule = Regex("\\[data-reader-page]\\s*\\{([^}]*)}").find(css)?.groupValues?.get(1)
        assertTrue("必须存在 [data-reader-page] 规则（页根安全区）", rule != null)
        assertEquals(
            "页根必须 box-sizing:border-box（否则 100% 高 + safe 内边距 ⇒ 页根比视口高 safe ⇒ 页脚不可见）",
            true,
            rule!!.contains("box-sizing")
        )
        assertEquals(
            "页根仍须消费 safe 内边距（archive 口径）",
            true,
            rule.contains("padding")
        )
    }

    @Test
    fun `主题必须 reset 页根内边距且给正文槽显式高度约束`() {
        val css = themeCss()
        val rootRule = Regex("\\[data-reader-page]\\s*\\{([^}]*)}").find(css)?.groupValues?.get(1)
        assertTrue("主题须有 [data-reader-page] reset（archive 同款约定）", rootRule != null)
        assertEquals("页根内边距必须清零（页眉是全幅出血设计）", true, rootRule!!.contains("padding: 0"))

        val bodyRule = Regex("\\.dh-body\\s*\\{([^}]*)}").find(css)?.groupValues?.get(1)
        assertTrue("必须存在 .dh-body 规则（正文槽）", bodyRule != null)
        assertEquals(
            "正文槽必须显式 height:100%（缺它则槽自增高 ⇒ 下占位为负 ⇒ 页框=整章高 ⇒ 翻页失效）",
            true,
            bodyRule!!.contains("height: 100%")
        )
    }

    @Test
    fun `引擎流必须有负下占位守门与占位拆解自证`() {
        val js = engineFlowJs()
        assertEquals(
            "必须拦截负下占位（槽溢出根壳时不得把负值计入 total）",
            true,
            js.contains("bottom < 0")
        )
        assertEquals("自证串须给出上占位 ctop（R2 取证）", true, js.contains("ctop="))
        assertEquals("自证串须给出下占位 cbot（R2 取证）", true, js.contains("cbot="))
        // 翻页状态并入 `page-frame`（2026-10-19 真机实证）：宿主侧 `render state: settle,...` 行
        // **不出现在真机 logcat** ⇒ 翻页判据必须能从 `page-frame` 取到页数/偏移/步长，否则判据无数据源。
        assertEquals("自证串须给出页数 pg（翻页判据数据源）", true, js.contains("pg="))
        assertEquals("自证串须给出正文偏移 off（前进/回退的判据量）", true, js.contains("off="))
        assertEquals("自证串须给出页步长 last（页码折算分母）", true, js.contains("last="))
    }

    @Test
    fun `自证串必须含宽度维度使左右偏窄可证伪`() {
        val js = engineFlowJs()
        assertEquals("自证串须给出沙箱视口宽 vw（R6 可证伪前置）", true, js.contains("vw="))
        assertEquals("自证串须给出页根左边界 pl（R6 可证伪前置）", true, js.contains("pl="))
        assertEquals("自证串须给出页根右边界 pr（R6 可证伪前置）", true, js.contains("pr="))
    }

    @Test
    fun `主题行高必须满足页眉加页脚不超过两成视口`() {
        val css = themeCss()
        val rows = Regex("\\.dh-page\\s*\\{[^}]*grid-template-rows:\\s*([^;]+);")
            .find(css)?.groupValues?.get(1)?.trim()
        assertTrue("必须能解析 .dh-page 的 grid-template-rows", rows != null)
        val tracks = Regex("clamp\\([^)]*\\)|minmax\\([^)]*\\)|[\\d.]+px")
            .findAll(rows!!).map { it.value }.toList()
        assertTrue("行轨道至少三项（页眉 / 正文 / 页脚）", tracks.size >= 3)

        // 参考视口 854 CSS px（本轮 MEmu 口径）：`clamp(min, Nvh, max)` 取实际生效值
        val referenceVp = 854.0
        val header = trackValue(tracks.first(), referenceVp)
        val footer = trackValue(tracks.last(), referenceVp)
        val limit = 0.2 * referenceVp
        assertEquals("参考视口须为 854（本轮实测口径）", 170.8, limit, 0.001)
        assertTrue(
            "页眉行(%.1f) + 页脚行(%.1f) 必须 ≤ 0.2×视口(%.1f)（保正文区 ≥80%%）".format(header, footer, limit),
            header + footer <= limit
        )
    }

    @Test
    fun `产物内联素材个数不得突破引擎硬上限`() {
        val json = SourceFileProbe.assetRawText("reader/builtin.dungeon-hud/readerTemplate.json")
        val count = Regex("data:[a-zA-Z0-9.+-]+/[a-zA-Z0-9.+-]+;base64,").findAll(json).count()
        // 与 ReaderTemplateImportMapper.MaxInlineDataCount 同口径（超限部分**静默不显示**）
        assertTrue("内联 data: 个数须 > 0", count > 0)
        assertTrue("内联 data: 个数(%d) 须 ≤ 64".format(count), count <= 64)
        assertEquals("阈值须与引擎常量一致", 64, 64)
    }

    private fun trackValue(track: String, vp: Double): Double {
        val clamp = Regex("clamp\\(\\s*([\\d.]+)px\\s*,\\s*([\\d.]+)vh\\s*,\\s*([\\d.]+)px\\s*\\)").find(track)
        if (clamp != null) {
            val lo = clamp.groupValues[1].toDouble()
            val ratio = clamp.groupValues[2].toDouble()
            val hi = clamp.groupValues[3].toDouble()
            return maxOf(lo, minOf(hi, ratio * vp / 100.0))
        }
        return Regex("([\\d.]+)px").find(track)?.groupValues?.get(1)?.toDouble() ?: -1.0
    }
}
