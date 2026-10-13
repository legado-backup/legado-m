package io.legado.app.model.localBook.epubcore.template

import io.legado.app.help.md.MdRichRenderInjector
import io.legado.app.help.md.ReaderTemplateSandboxDocument
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File

/**
 * 模板运行时**契约一致性**单测（epub-md-rich-rendering 阶段 4.1 配对）。
 *
 * 存在理由：模板桥的安全边界由两侧共同实现——Kotlin 侧 [ReaderTemplateBridgePolicy] 是权威判据，
 * 沙箱/宿主 JS 各自还有一份**前置粗筛**表。两份表一旦漂移，就会出现
 * 「JS 放行但 Kotlin 拒收」（消息静默丢失，表现为模板功能莫名失效）或更糟的
 * 「JS 放行且 Kotlin 无登记」（越权字段绕过）。本测试把 JS 资产**当数据读入并逐项比对**。
 *
 * 同时固化 AD-23 的硬约束（可在文本层证伪的低级失守）：
 * ①禁止 `addJavascriptInterface`；②沙箱须为 `allow-scripts` 且**不含** `allow-same-origin`；
 * ③asset 引用不得在 JS 内自行拼路径（必须交 Kotlin 侧解析）。
 */
class ReaderTemplateRuntimeContractTest {

    private val assetsDir = File("src/main/assets/md")

    /** 正则而非字面量：注释里说明"不使用该 API"是允许的，**调用**才是违规。 */
    private val HOST_INTERFACE_INJECTION = Regex("""addJavascriptInterface\s*\(""")

    private fun asset(name: String): String {
        val file = File(assetsDir, name)
        assertTrue("资产缺失：${file.absolutePath}（工作目录=${File(".").absolutePath}）", file.isFile)
        return file.readText()
    }

    /** 抽取 JS 中形如 `type: ['a','b']` 的类型→字段表（本文件内联的两张表形态一致）。 */
    private fun parseTypeTable(js: String, tableName: String): Map<String, List<String>> {
        val start = js.indexOf("$tableName = {")
        assertTrue("未找到类型表 $tableName", start >= 0)
        val end = js.indexOf("};", start)
        assertTrue("类型表 $tableName 未闭合", end > start)
        val body = js.substring(start, end)
        val entry = Regex("""(\S+)\s*:\s*\[([^\]]*)]""").findAll(body)
        return entry.associate { match ->
            val key = match.groupValues[1].trim().trim('\'', '"')
            val fields = match.groupValues[2]
                .split(',')
                .map { it.trim().trim('\'', '"') }
                .filter { it.isNotEmpty() }
            key to fields
        }
    }

    @Test
    fun `沙箱侧类型与字段表与桥策略一致`() {
        val jsTable = parseTypeTable(asset("template-runtime.js"), "SEND_TYPES")
        assertTrue("解析失败：沙箱侧类型表为空", jsTable.isNotEmpty())
        jsTable.forEach { (type, fields) ->
            val policyFields = ReaderTemplateBridgePolicy.allowedFields(
                ReaderTemplateBridgePolicy.Direction.FROM_WEB, type
            )
            assertEquals("类型 $type 的字段表两侧必须一致", policyFields?.toList()?.sorted(), fields.sorted())
        }
        assertEquals(
            "沙箱侧不得漏登记桥策略已放行的类型",
            ReaderTemplateBridgePolicy.Direction.FROM_WEB.let { direction ->
                jsTable.keys.sorted()
            },
            jsTable.keys.sorted()
        )
    }

    @Test
    fun `宿主侧类型与字段表与桥策略一致`() {
        val jsTable = parseTypeTable(asset("template-host.js"), "INBOUND_TYPES")
        assertTrue("解析失败：宿主侧类型表为空", jsTable.isNotEmpty())
        jsTable.forEach { (type, fields) ->
            val policyFields = ReaderTemplateBridgePolicy.allowedFields(
                ReaderTemplateBridgePolicy.Direction.FROM_WEB, type
            )
            assertEquals("类型 $type 的字段表两侧必须一致", policyFields?.toList()?.sorted(), fields.sorted())
        }
    }

    @Test
    fun `两侧上限常量与桥策略一致`() {
        val host = asset("template-host.js")
        // JS 侧以表达式书写，故同时校验表达式文本与数值一致（防只改一边）
        assertTrue("原始字符上限表达式缺失", host.contains("MAX_RAW_CHARS = 256 * 1024"))
        assertEquals("Kotlin 侧上限须等于 JS 表达式", 256 * 1024, ReaderTemplateBridgePolicy.MaxRawChars)
        assertTrue(host.contains("MAX_JSON_DEPTH = ${ReaderTemplateBridgePolicy.MaxJsonDepth}"))
        assertTrue(host.contains("MAX_SELECTION_RECTS = ${ReaderTemplateBridgePolicy.MaxSelectionRects}"))
    }

    @Test
    fun `宿侧沙箱属性为纯 allow-scripts`() {
        val host = asset("template-host.js")
        assertFalse("AD-23 硬约束：禁用宿主对象注入 API", HOST_INTERFACE_INJECTION.containsMatchIn(host))
        // 直接校验属性赋值文本：必须是纯 allow-scripts（多一个标记就等于放弃隔离）
        assertTrue(
            "沙箱属性须精确为 allow-scripts",
            host.contains("setAttribute('sandbox', 'allow-scripts');")
        )
        assertFalse("不得出现同源标记", host.contains("-origin"))
    }

    @Test
    fun `宿主侧不在 JS 内自行拼素材路径`() {
        val host = asset("template-host.js")
        assertFalse("素材别名必须交 Kotlin 侧解析（ReaderAssetPathPolicy）", host.contains("asset://"))
    }

    @Test
    fun `沙箱侧不直接触碰宿主对象`() {
        val runtime = asset("template-runtime.js")
        assertFalse(HOST_INTERFACE_INJECTION.containsMatchIn(runtime))
        assertFalse("沙箱内不得有宿主对象引用", runtime.contains("AndroidAssetBridge"))
        assertTrue("沙箱只能经 parent.postMessage 通信", runtime.contains("parent.postMessage"))
    }

    @Test
    fun `沙箱侧白名单拒绝未登记类型`() {
        val runtime = asset("template-runtime.js")
        assertTrue("未登记发送类型须静默丢弃", runtime.contains("if (!allowed) return;"))
        assertTrue("未登记接收类型须丢弃", runtime.contains("RECEIVE_TYPES.indexOf(data.type) < 0"))
    }

    @Test
    fun `浏览器流程覆盖模板结构约定与三种分页`() {
        val flow = asset("template-browser-flow.js")
        assertTrue("须读正文槽位", flow.contains("[data-reader-flow=\"body\"]"))
        assertTrue("须读分栏标记", flow.contains("[data-reader-flow-pagination=\"columns\"]"))
        assertTrue("须读滚动视口", flow.contains("[data-reader-scroll-viewport]"))
        assertTrue("须有自研回退分页", flow.contains("settleManualPagination"))
        assertTrue("须回发结算", flow.contains("onFlowSettled"))
        assertTrue("页框高须有下限守卫（除零/整章被裁成 1 页）", flow.contains("MIN_PAGE_HEIGHT"))
        assertTrue("页数须有上限守卫（作者畸形 DOM 不得拖死宿主）", flow.contains("MAX_PAGES"))
    }

    @Test
    fun `自研回退分页把正文槽位冻结为页框并纵移翻页`() {
        // 真机缺口（2026-10-10）：模板只声明正文槽位、作者 CSS 让正文自由增高（素笺 `.mi-body`
        // 无 height/overflow）⇒ 页数恒 1、翻页无效、后半章溢出读不到。引擎必须自己冻结页框。
        val flow = asset("template-browser-flow.js")
        assertTrue("必须冻结页框（固定高）", flow.contains("function freezePagedSlot("))
        assertTrue("必须以 border-box 固定高（与量取口径一致，含 padding）", flow.contains("boxSizing = 'border-box'"))
        assertTrue("必须裁切（overflow:hidden 仍是可编程滚动容器）", flow.contains("overflow = 'hidden'"))
        assertTrue(
            "页框高须由「视口高 − **当前壳**占位」推出（页眉页脚被自然扣掉）",
            // 口径升级（用户实测「阅读页底部大片空白」）：占位**必须按当前壳**取 —— 首页壳常有
            // hero/封面大块、续页壳没有；沿用"注入前按首页测的那一份"会让续页多扣一次首页专属装饰
            // ⇒ 页框变小、页脚上移、页脚与视口底之间留白。故断言"按壳取占位"这一不变量。
            flow.contains("return vp - chromeForShell(shellName(), slot);")
        )
        assertTrue(
            "「按壳占位」与「整体高」两口径必须分开：前者已排除正文槽 ⇒ 不得再叠加槽位空高",
            // 混用后果：页框多出槽空高一截 ⇒ 页脚被压到视口底之下、正文末行被裁（首页同样错位）。
            // 只有旧的 `chromeHeight`（量 `root.scrollHeight`，已含槽空高）才需要 `slotEmptyHeight` 补偿。
            flow.contains("return vp - chromeHeight + slotEmptyHeight;")
        )
        assertTrue(
            "占位须按壳缓存（否则换壳必漂移），且量取必须是**布局事实**（根壳与正文槽的 rect 之差）",
            // 真机铁证（2026-10-12）：① 沿用"注入前按首页壳测的那一份"⇒ 续页多扣首页专属装饰
            // （页脚上移、底部留白 = 用户实测）；② 改"逐子元素累加"后仍偏小 59px（`offsetHeight`
            // 对 SVG 装饰带恒 undefined，且 margin/伪元素不计）⇒ 占位 241 < 正文槽顶 244，
            // 页框反被撑高、页脚压出视口。故必须用 rect 之差：上占位=槽顶−根顶，下占位=根底−槽底。
            flow.contains("function chromeForShell(") &&
                flow.contains("chromeByShell") &&
                flow.contains("sr.top - rr.top") &&
                flow.contains("rr.bottom - sr.bottom")
        )
        // 真机铁证（2026-10-13）：换壳后**首帧**量取时装饰带（内联 SVG）尚未定型 ⇒ 占位偏小整整一条
        // 行高（实测续页 `chromeNow=71` vs 后续 `91`，箱高 782 vs 763）⇒ 该壳首帧比后续页多一行，
        // 且保存/恢复跨一档页码（用户实测：「每页文字个数的不同，页脚还能自己变动」）。旧实现"同壳
        // 只测一次"会把这份偏小值缓存住 ⇒ 必须改为**每次实测** + 差异超阈值时下一帧重结算一次。
        assertTrue(
            "按壳占位必须每次实测并比对上次（首帧装饰未定型 ⇒ 差一整行，须重测重结算）",
            flow.contains("var prev = chromeByShell[key];") &&
                // 该壳**首次**量取必然偏小 ⇒ 必须延迟重测（rAF 仍可能过早，实测首帧 71 vs 定型 91）
                flow.contains("if (prev === undefined) scheduleResettle(CHROME_FIRST_MEASURE_DELAY_MS);") &&
                flow.contains("var CHROME_FIRST_MEASURE_DELAY_MS = 150;") &&
                flow.contains("else if (Math.abs(prev - total) > CHROME_DRIFT_TOL) scheduleResettle(0);") &&
                flow.contains("var CHROME_DRIFT_TOL = 2;") &&
                flow.contains("function scheduleResettle(delay)") &&
                flow.contains("settle(true);") &&
                // 反向锁：不得再出现"同壳只测一次"的早退缓存（它正是首帧多一行的成因）
                !flow.contains("if (chromeByShell[key] !== undefined)")
        )
        assertFalse(
            "占位不得再逐子元素累加（SVG 装饰带/边距会被漏算 ⇒ 页框被撑高、页脚出屏）",
            flow.contains("total += el.offsetHeight") ||
                flow.contains("total += rect ? rect.height : 0;")
        )
        assertTrue(
            "换章须清空按壳占位缓存（结构可能整体变化）",
            flow.contains("function resetChromeCache(") && flow.contains("resetChromeCache();")
        )
        assertTrue(
            "结算自证须带实际生效占位与壳名（否则'续页仍按首页占位扣减'无法在真机留痕定位）",
            flow.contains("',chromeNow='") && flow.contains("',shell='")
        )
        assertTrue(
            "视口高必须结算时实时读（initialize 那刻沙箱帧可能还没布局完，实测 vp=0 ⇒ 页框算成负数）",
            flow.contains("function currentViewportHeight(")
        )
        assertTrue(
            "自研回退须纵移（用错轴＝点翻页没反应）",
            // 4.15 C1 起口径升级：纵移量改由**结构无关的正文偏移**推出（`scrollTop` 含页眉补偿，
            // 换壳后会整体平移）⇒ 断言从"写 target*visible"改为"落到 bodyOffset"，轴仍是纵轴
            flow.contains("container.scrollTop = bodyOffset") ||
                flow.contains("container.scrollTop = target * visible")
        )
        assertTrue("分栏模板才横移", flow.contains("container.scrollLeft = target * visible"))
        assertTrue(
            "页码必须来自**容器实际位置**（回读静态 config.pageIndex ⇒ 翻页后页码不变、边界判据失真）",
            // 4.15 C1 起口径升级：自研回退分页不再读 `scrollTop`（含页眉补偿，换壳后会整体平移），
            // 改读**结构无关的正文偏移**；但"读实际位置而非静态配置"这条不变量不变（由 bodyOffset 满足）
            flow.contains("function scrollIndex(") &&
                (flow.contains("scrollIndex(slot.scrollTop, visible)") ||
                    flow.contains("indexFromOffset(bodyOffset, visible, totalPages, maxOffset)"))
        )
        assertTrue(
            "页码必须四舍五入（scrollTop 是小数：floor(782.x/783)=0 ⇒ 已翻页却判成第 1 页，2026-10-10 铁证）",
            flow.contains("return isFinite(value) ? Math.round(value) : 0;")
        )
        assertFalse(
            "不得再出现 floor(scrollTop/visible) 这类不容错算法",
            flow.contains("Math.floor(scrollTop / visible)")
        )
    }

    @Test
    fun `纵移步长与结算页高同源且页框贴底校正有界`() {
        // 真机铁证（2026-10-12，用户实测「开启模板后只能翻两页、之后翻不动；单页超出可视界面可上下扒拉」）：
        // ① `goto` 纵移若读 `container.clientHeight`，会与 `settle` 的页高（`visibleHeight()`）不一致
        //    （实测 656.67 vs 748）⇒ `bodyOffset` 偏小、页码恒 0 ⇒ 宿主永远判不到"章末"，卡在第 2 页；
        // ② 占位是**注入前估算**（模板装饰多为 vh 单位 SVG）⇒ 冻结后必须用**布局事实**（根壳底 vs 视口底）
        //    再校一次，否则页框超高把页脚压出视口（用户可直接上下扒拉）。
        val flow = asset("template-browser-flow.js")
        assertTrue(
            "纵移步长必须与结算页高同源（用 settled 的 lastPageHeight，不得裸读容器 clientHeight）",
            flow.contains("lastPageHeight > 0 ? lastPageHeight : container.clientHeight")
        )
        assertTrue(
            "必须存在「贴底校正」，判据为根壳底 == 视口底（布局事实，可证伪）",
            flow.contains("function correctFrameHeight(") &&
                flow.contains("root.getBoundingClientRect().bottom - currentViewportHeight()")
        )
        assertTrue(
            "校必须有界（迭代上限 + 容差 + 页高下限守卫，防作者畸形 DOM 抖动/死循环）",
            flow.contains("FRAME_CORRECT_MAX") &&
                flow.contains("FRAME_CORRECT_TOL") &&
                flow.contains("next > MIN_PAGE_HEIGHT")
        )
        assertTrue(
            "校正须**双向**（2026-10-13 用户铁证：冻结成 BFC 后下占位变小 ⇒ 单向收缩会让根壳底够不到视口底）" +
                "，且须防根壳被 CSS 钳定时放大无效（放大前先验是否真有位移）",
            flow.contains("Math.abs(delta) <= FRAME_CORRECT_TOL") &&
                flow.contains("after <= delta + FRAME_CORRECT_TOL") &&
                !flow.contains("overflow <= FRAME_CORRECT_TOL")
        )
        assertTrue(
            "校正结果必须写回按壳占位缓存（否则每次结算重复校正/抖动）",
            flow.contains("chromeByShell[shellName() || 'none'] = ")
        )
        assertTrue(
            "宿主指令的权威量是**页号**（不是那一刻算出的像素）：由 settle 用最终页高折算，防「校正前后页高不一致」漂到半页",
            flow.contains("var authoritativePage = -1;") &&
                flow.contains("authoritativePage = target;") &&
                flow.contains("bodyOffset = clampBodyOffset(authoritativePage * visible, slot, root);")
        )
        assertTrue(
            "**末页必须可达**（末页是部分页：`target*页高` 被夹到最大偏移后 floor 会退回前一页 ⇒ 症状＝只能翻两页）",
            flow.contains("function indexFromOffset(") &&
                flow.contains("offset >= maxOffset - 1") &&
                flow.contains("authoritativeIndex = clampIndex(authoritativePage, totalPages);") &&
                flow.contains("pageIndex: authoritativeIndex >= 0")
        )
        // 真机铁证（2026-10-13）：分页偏移按"页号 × 可见窗口高"取整生成，恢复侧再把"比例 × 区间"
        // 回乘 ⇒ 结果**恰好落在页边界上**；`floor` 会把浮点误差/箱高微差一律判退**一页**
        // （实测 `page=4/14` 冷启恢复成 `3/14`）。与 `scrollIndex` 的既有铁证同源 ⇒ 必须四舍五入。
        assertTrue(
            "偏移→页码的逆映射必须**四舍五入**（页边界上 floor 会把恢复结果判退一页）",
            flow.contains("return clampIndex(Math.round(value), totalPages);") &&
                // 反向锁：分页逆映射不得再用直接相除的 floor 形式
                !flow.contains("return clampIndex(offset / visible, totalPages);")
        )
        // 进度恢复的**内容比例**口径（顾问判定必须根治双壳页数偏差：实测首页壳 17 页 / 续页壳 12 页
        // ⇒ 按页号折算恢复偏 ≤2 页，用户可感知"进度不对"）。比例口径与壳无关 ⇒ 必须三方齐备。
        assertTrue(
            "沙箱须支持按滚动区间比例定位（`ratio × maxBodyOffset`，与保存侧同分母）",
            flow.contains("function gotoRatio(") &&
                flow.contains("authoritativeRatio * maxBodyOffset(slot, root)") &&
                // 反向锁：恢复侧**不得**再拿可见窗口高当分母（曾致精确恢复退化为 ±1 页）
                !flow.contains("authoritativeRatio * Math.max(0, ratioContent - visible)") &&
                flow.contains("gotoRatio: gotoRatio")
        )
        // 保存侧必须与恢复侧**同归一化**（否则往返偏 1~2 页）：沙箱自报 `progressRatio`，
        // 经 SEND_TYPES/策略/编解码三方放行后由宿主保存进度。
        assertTrue(
            "沙箱须自报内容比例（保存侧同归一化的唯一来源）",
            flow.contains("function progressRatio(") &&
                flow.contains("onFlowSettled(") &&
                asset("template-runtime.js").contains("stable: ['pageIndex', 'pageCount', 'progressRatio']") &&
                asset("template-runtime.js").contains("payload.progressRatio = ")
        )
        assertTrue(
            "桥策略须放行 FROM_WEB `progressRatio`",
            ReaderTemplateBridgePolicy.allowedFields(
                ReaderTemplateBridgePolicy.Direction.FROM_WEB, "stable"
            )?.contains("progressRatio") == true
        )
        assertTrue(
            "冻结页框的页眉补偿必须为 0（旧式 `root.scrollHeight − slot.scrollHeight` 对冻结页框为负 ⇒ " +
                "回退后 `readBodyOffset` 恒解出 0 ⇒ 非权威结算把正文打回章首，进度恢复落第 1 页）",
            flow.contains("function pageChrome(") &&
                flow.contains("if (slotIsFrozen(slot)) return 0;") &&
                !flow.contains("chrome = bodyOffset;")
        )
        assertTrue(
            "沙箱运行时分发须认 `ratio` 字段（否则宿主下指令后仍按页号走）",
            asset("template-runtime.js").contains("if (typeof data.ratio === 'number')") &&
                asset("template-runtime.js").contains("flow.gotoRatio(data.ratio);")
        )
        assertTrue(
            "桥策略须放行 `ratio` 字段（未登记即被拒收）",
            ReaderTemplateBridgePolicy.allowedFields(
                ReaderTemplateBridgePolicy.Direction.TO_WEB, "goto-page"
            )?.containsAll(setOf("pageIndex", "ratio")) == true
        )
    }

    @Test
    fun `运行时在正文注入前量页框并立即结算一次`() {
        // 两条顺序/完备性不变量，各自对应一类真实失守：
        // ①先注入后量 ⇒ 正文自身被算进"固定占位"，页框被算成 0 高；
        // ②不立即结算 ⇒ 无富渲染元素的章节拿不到 stable，宿主只能 8s 超时回落 canvas。
        val runtime = asset("template-runtime.js")
        val iInit = runtime.indexOf("flow.initialize(config.flow)")
        val iBody = runtime.indexOf("applyBody(config.bodyHtml)")
        assertTrue("continueInit 必须调用 flow.initialize", iInit >= 0)
        assertTrue("正文注入必须在页框量取之后：$iInit < $iBody", iInit in 0 until iBody)
        val iSettle = runtime.indexOf("flow.settle(false)")
        assertTrue("必须在初始化阶段立即结算一次", iSettle > iBody)
    }

    @Test
    fun `沙箱富渲染驱动与注入器全局名单源`() {
        val runtime = asset("template-runtime.js")
        // 沙箱跨源 ⇒ 宿主读不到它的 DOM，只能靠它自己驱动注入器并回发消息
        assertTrue(
            "沙箱必须驱动阶段 3.8/3.9 注入器（同一全局名；改名漏改 = 注入永不生效）",
            runtime.contains("window.${MdRichRenderInjector.StatusGlobal}")
        )
        assertTrue("必须调用可重复运行入口", runtime.contains("status.run"))
        assertTrue(
            "完成后须回发 renderState 且**带渲染计数**（只看'脚本跑了'在空文档上也会成立）",
            runtime.contains("'inject-done,mermaid='")
        )
        assertTrue("未注入时须明确回报，不得静默", runtime.contains("'inject-unavailable'"))
    }

    @Test
    fun `宿主放行指令与 Kotlin 侧 TO_WEB 表一致`() {
        val host = asset("template-host.js")
        val arrayText = Regex("""\[([^\]]*)]\.indexOf\(type\)""").find(host)?.groupValues?.get(1)
        assertTrue("未找到宿主侧放行类型数组（post 的准入判据）", !arrayText.isNullOrBlank())
        val jsTypes = arrayText!!.split(',').map { it.trim().trim('\'', '"') }.filter { it.isNotEmpty() }
        // 权威源 = Kotlin 策略表（不是测试里再抄一份清单，否则"两侧一起漂"就测不出来）
        val kotlinTypes = ReaderTemplateBridgePolicy
            .registeredTypes(ReaderTemplateBridgePolicy.Direction.TO_WEB)
            .toList()
        // 两侧不一致即"Kotlin 放行但宿主 JS 拒发"（功能静默失效）或反之（越权通道）
        assertEquals("宿主放行集合必须与 Kotlin TO_WEB 表逐项相等", kotlinTypes.sorted(), jsTypes.sorted())
    }

    @Test
    fun `厂商脚本按 URL 加载且不内联`() {
        val runtime = asset("template-runtime.js")
        assertTrue("必须提供安装入口", runtime.contains("function installVendors(urls, done)"))
        assertTrue(
            "必须用 `<script src>` 按 URL 加载（体量走浏览器流式加载，不经消息体；也不经过 HTML 解析）",
            runtime.contains("script.src = url")
        )
        assertTrue("加载失败必须回报（跨源无调试器，静默失败无从定位）", runtime.contains("'vendor-load-failed'"))
        assertTrue("加载须有界等待（失败也要继续，不白屏）", runtime.contains("'vendor-load-timeout'"))
        assertTrue("厂商就位后才继续初始化", runtime.contains("installVendors(config.vendorUrls, function () {"))
        assertTrue("其余初始化必须在回调内完成", runtime.contains("function continueInit(config)"))
        assertFalse(
            "沙箱文档不得内联厂商脚本（srcdoc 由 Kotlin 侧构造，此处锁死脚本侧不引入内联路径）",
            runtime.contains("document.write")
        )
    }

    @Test
    fun `宿主驱动翻页在流程层有落点`() {
        val flow = asset("template-browser-flow.js")
        assertTrue("流程层必须提供 goto（沙箱跨源 ⇒ 只有它能改内部滚动）", flow.contains("function goto("))
        assertTrue("必须按滚动/分页两类容器分别处理", flow.contains("scrollTop") && flow.contains("scrollLeft"))
        assertTrue("跳转后必须重新结算", flow.contains("return settle(false);"))
        val runtime = asset("template-runtime.js")
        assertTrue("运行时必须把 goto-page 交给流程层", runtime.contains("flow.goto(data.pageIndex)"))
    }

    @Test
    fun `init 不进沙箱接收白名单而由 bootstrap 转发`() {
        val runtime = asset("template-runtime.js")
        assertTrue(
            "接收类型表须与 Kotlin 侧 TO_WEB 表一致（注入/重测/主题/翻页/动效）",
            runtime.contains(
                "RECEIVE_TYPES = ['inject-mermaid', 'inject-katex', 'remeasure', 'set-theme', 'goto-page', 'set-motion']"
            )
        )
        assertFalse("init 不得进入接收白名单（否则与 bootstrap 双重处理同一消息）", runtime.contains("'init',"))
        val bootstrap = ReaderTemplateSandboxDocument.bootstrapScript()
        assertTrue("bootstrap 必须独占 init 转发", bootstrap.contains("data.type!=='init'"))
        assertTrue(
            "bootstrap 必须调用沙箱运行时入口",
            bootstrap.contains("window.ReaderTemplateRuntime.init(data)")
        )
    }

    @Test
    fun `模板运行时覆盖内容注入与内容感知字段`() {
        val runtime = asset("template-runtime.js")
        assertTrue(runtime.contains("[data-reader-field]"))
        assertTrue("须支持进度百分比变量", runtime.contains("--rp-percent"))
        assertTrue("须支持小时变量与阶段类", runtime.contains("--rp-hour"))
        assertTrue(runtime.contains("data-rp-phase"))
        assertTrue("须下发主题", runtime.contains("data-reader-theme"))
    }

    @Test
    fun `首页续页双结构按页换壳`() {
        // 4.15 C1：paged 的 firstPageHtml / otherPageHtml 是**两套 HTML**（开篇页 vs 正文页），
        // 只渲染首屏那套 = "开篇仪式感缺失"（archive 原文能力的核心差距 G1）。
        val runtime = asset("template-runtime.js")
        assertTrue("须有换壳入口", runtime.contains("function applyPageShell(which)"))
        assertTrue("须暴露当前结构（流程层与诊断都要读）", runtime.contains("function currentPageShell()"))
        assertTrue("须有首页结构读取", runtime.contains("function openingHtml()"))
        assertTrue("须有续页结构读取，且空时退回首页结构（作者只写一套时不白屏）",
            runtime.contains("function continuationHtml()") && runtime.contains("return other || openingHtml();"))
        assertTrue("滚动模板不得换壳（单份 scrollHtml）", runtime.contains("if (template.type === 'scroll') return false;"))
        assertTrue("状态初值须为空串（否则首次 applyPageShell 直接返回 ⇒ 根壳恒空）",
            runtime.contains("var pageShell = '';"))
        assertTrue("首屏必须经单一写入点挂载（绕过它会留下 DOM 与状态不一致）",
            runtime.contains("applyPageShell('opening');"))
        assertFalse("paged 分支不得再直接 mountMarkup（绕过状态机）",
            runtime.contains("mountMarkup(state.pageIndex === 0"))
        // 换壳会整块替换根壳 innerHTML ⇒ 必须把正文再注入回来（否则续页"页眉页脚在、正文全空"）
        assertTrue("换壳后必须重新注入正文", runtime.contains("applyBody(state.bodyHtml);"))
        assertTrue("正文 HTML 必须被缓存以便换壳复用", runtime.contains("state.bodyHtml = bodyHtml || '';"))

        // 流程层：换壳必须发生在页边界且带滚动补偿（否则正文错位/页码跳飞）
        val flow = asset("template-browser-flow.js")
        assertTrue("goto 须按目标页切换结构", flow.contains("switchShellForPage(target)"))
        assertTrue("须两个方向都切（只切一个方向 ⇒ 翻回首页时开篇页不再出现）",
            flow.contains("var want = target <= 0 ? 'opening' : 'continuation';"))
        assertTrue("须有流程层结构副本以跳过无谓重建", flow.contains("var flowShell = '';"))
        assertTrue("同结构连续换页不得重建 DOM", flow.contains("if (want === flowShell) return false;"))
        assertTrue("横向分栏/滚动模板不换壳", flow.contains("if (isScrollMode() || isColumnsMode()) return false;"))
        assertTrue("页码须由**结构无关的正文偏移**推出（读 scrollTop 会因页眉补偿而跳页）",
            flow.contains("indexFromOffset(bodyOffset, visible, totalPages, maxOffset)"))
        assertTrue("须有正文偏移反解（跨结构可比量）", flow.contains("function readBodyOffset("))
        assertTrue("须有正文偏移定位", flow.contains("function applyBodyOffset("))
        assertTrue("结算须回发结构自证（否则换壳失守只能肉眼比对）", flow.contains("settle,shell="))
    }

    @Test
    fun `页框恒定冻结并整行对齐（短章留白与末行裁切）`() {
        // 2026-10-13 用户真机铁证三条（必须逐条钉住，否则会随重构回退）：
        // ①短章外壳塌陷 ⇒ 底部一大片空白、页脚紧贴正文末尾（续页壳同因"只在溢出时冻结"而留 91px）；
        // ②页高不是行高整数倍 ⇒ 裁切边界落在某行中间，「最后一行的字能显示一半」；
        // ③用 `zoom` 收紧外壳 ⇒ 缩放的是元素自身盒宽，块级页眉/页脚右侧空出一条（「左右不占满屏幕」）。
        val flow = asset("template-browser-flow.js")
        assertTrue("⑤ 须有整行对齐入口（把「箱高 − 槽顶部内边距」向下取整到整行）",
            flow.contains("function alignToWholeLines(") &&
                flow.contains("Math.floor(room / lh)"))
        assertTrue("⑤ 须取正文槽的实际行高（computed 才是最终生效值）", flow.contains("function lineHeightOf("))
        assertTrue("⑤ 须取正文槽顶部内边距（网格原点必须含它）", flow.contains("function slotPaddingTop("))
        assertTrue(
            "①⑤ 箱高与可见窗口必须**分开**（箱高铺满/不可拖/页脚贴底；窗口整行对齐/不裁字）",
            flow.contains("function freezePagedSlot(slot, boxHeight)") &&
                flow.contains("slot.style.paddingBottom = Math.max(0, Math.floor(gutter)) + 'px';")
        )
        assertTrue(
            "① 必须**恒定冻结**（短章也要冻结；旧的『仅在溢出时冻结』守卫须已删除）",
            flow.contains("freezePagedSlot(slot, box)") &&
                !flow.contains("if ((slot.scrollHeight || 0) > visible + 1)")
        )
        assertTrue(
            "最大正文偏移须用**箱高**口径（用可见窗口高会多滚一段 ⇒ 章末页底部露白）",
            flow.contains("var box = (slot && slot.clientHeight) || 0;") &&
                flow.contains("var page = box > 0 ? box : (lastPageHeight > 0 ? lastPageHeight : visibleHeight());")
        )
        assertTrue("换章须作废页高/箱高（不得跨章复用）",
            flow.contains("lastPageHeight = 0;") && flow.contains("lastBoxHeight = 0;"))
        assertTrue("① 贴底校正须**双向**（冻结成 BFC 后下占位变小 ⇒ 欠填须放大到贴底）",
            flow.contains("Math.abs(delta) <= FRAME_CORRECT_TOL"))
        assertTrue("① 校正后须**重算可见窗口**（否则裁切边界又落到行中间）",
            Regex("""visible = freezePagedSlot\(slot, box\);""").findAll(flow).count() >= 2)
        assertTrue("① 换壳须用**箱高**冻结新壳（否则新壳比视口矮 ⇒ 又能上下扒拉）",
            flow.contains("freezePagedSlot(fresh, boxHeight);"))
        assertTrue("① 放大前须先验根壳是否真的下移（根壳被 CSS 钳定时放大只是裁掉正文）",
            flow.contains("after <= delta + FRAME_CORRECT_TOL"))
        val layoutCss = asset("template-layout.css")
        assertTrue("① 画布须恒铺满视口（否则整行对齐残量处露出异色画布底）",
            layoutCss.contains("min-height: 100vh"))
        assertTrue("⑤ 沙箱文档自身不得可滚动（否则整页仍能被上下拖出一截）",
            layoutCss.contains("overflow: hidden"))
        assertTrue("⑤ 正文须落在**整行网格**上（段距非整行会让页边界落在行中间 ⇒ 末行被裁半）",
            layoutCss.contains("--rp-line-height") &&
                layoutCss.contains("padding-top: var(--rp-line-height") &&
                layoutCss.contains("margin-bottom: var(--rp-line-height"))

        val runtime = asset("template-runtime.js")
        assertTrue("⑤ 运行时须按 computed 行高写入整行网格变量", runtime.contains("function applyLineGrid()") &&
            runtime.contains("setProperty('--rp-line-height'"))
        assertTrue("⑤ 整行网格须在页眉/页脚占位量取（flow.initialize）之前应用",
            runtime.indexOf("applyLineGrid();") in 1 until runtime.indexOf("flow.initialize(config.flow);"))
        assertFalse("③ 引擎不得再对模板外壳施加 zoom（右侧会空出一条）", runtime.contains("setProperty('zoom'"))
        assertFalse("③ 收紧入口须已移除", runtime.contains("function tightenChrome("))
        assertTrue("空白归属须可自证（html/body/根壳三层底色）", runtime.contains(",bg=' + backgroundFacts()"))
    }

    @Test
    fun `元素与动画预算自证（4_19）`() {
        // 4.19 / NFR-08：重装饰模板卡顿的**第一手数字**是元素数与"当前真的在跑"的动画数。
        // 口径要点：①只报告不改行为（不擅自删节点/停动画，否则症状变成"模板莫名少一块"）；
        // ②动画数用 document.getAnimations()（而非数 animation-name：后者会把不在当前页的也算进来）；
        // ③取不到（旧内核无该 API）返回 -1 且**不算超限**（避免误报）。
        val runtime = asset("template-runtime.js")
        assertTrue("须有元素计数", runtime.contains("function elementCounts()"))
        assertTrue("动画数须取 getAnimations（只含真正在跑的）", runtime.contains("document.getAnimations"))
        assertTrue("须有预算判据", runtime.contains("function budgetState()"))
        assertTrue("预算常量须在（元素）", runtime.contains("var MAX_ELEMENTS = 3000;"))
        assertTrue("预算常量须在（动画）", runtime.contains("var MAX_ANIMATIONS = 120;"))
        assertTrue("取不到计数不得算超限", runtime.contains("if (counts.elements > MAX_ELEMENTS) return 'over';"))
        assertTrue("预算与规模必须随自证回发", runtime.contains("',elems='") && runtime.contains("',anims='") && runtime.contains("',budget='"))
    }

    @Test
    fun `派生字段补齐宿主未提供的槽位`() {
        // 4.15 C2：内置模板页脚声明 `data-reader-field="page"`/`"time"`，而宿主 init 只给
        // bookName/chapterTitle/progress/hour ⇒ 不派生则这两个槽位**恒空且不报错**。
        val runtime = asset("template-runtime.js")
        assertTrue("须有派生入口", runtime.contains("function derivedField(key)"))
        assertTrue("页码须由沙箱派生（分页结果是它算的）", runtime.contains("case 'page': return String(state.pageIndex + 1)"))
        assertTrue("总页数须派生", runtime.contains("case 'pageCount'"))
        assertTrue("percent 须是 progress 的别名", runtime.contains("case 'percent'"))
        assertTrue("时间须派生（本地时钟）", runtime.contains("case 'time': return localTime()"))
        assertTrue("电量须派生（取不到不冒写假值）", runtime.contains("case 'battery': return state.battery || null"))
        assertTrue("须有本地时间格式化", runtime.contains("function localTime()"))
        assertTrue("宿主提供的字段优先于派生", runtime.contains("(supplied === undefined || supplied === null) ? derivedField(key)"))
        assertTrue("结算后须回填页码槽位", runtime.contains("refreshFields();"))
        assertTrue("须有电池状态监听（增强信息）", runtime.contains("navigator.getBattery"))
        assertTrue("须有分钟级时钟刷新（C5 时间驱动）", runtime.contains("function startClock()"))
        assertTrue("字段槽位必须自证（派生字段失效是纯静默的）", runtime.contains("',fields='"))
    }

    @Test
    fun `运行时提供响应式收紧竖排判定与素材治理`() {
        // 4.15 C9/C10/C11：三块能力的状态都只活在沙箱 <html> 上（跨源宿主读不到）⇒
        // 源码级钉住"运行时真的会写这些开关 + 自证回发"，否则真机只能靠"看起来对不对"判断。
        val runtime = asset("template-runtime.js")
        // C9 响应式收紧：自量沙箱帧 ⇒ 断点属性 + 尺寸变量 + 收紧系数
        assertTrue("C9：须有响应式收紧入口", runtime.contains("function applyViewport()"))
        assertTrue("C9：须置窄屏开关", runtime.contains("data-rp-narrow"))
        assertTrue("C9：须置横屏开关", runtime.contains("data-rp-landscape"))
        assertTrue("C9：须下发帧宽高变量（竖排确定宽高的基准）", runtime.contains("--rp-vp-w") && runtime.contains("--rp-vp-h"))
        assertTrue("C9：收紧系数须走变量单源", runtime.contains("--rp-chrome-scale"))
        assertTrue("C9：窄屏断点须有常量口径", runtime.contains("NARROW_WIDTH = 480"))
        // C10 竖排规格：判定书写方向（显式声明优先，computed 兜底）
        assertTrue("C10：须有竖排判定入口", runtime.contains("function applyWritingMode()"))
        assertTrue("C10：须置竖排开关", runtime.contains("data-rp-writing"))
        assertTrue("C10：须读 computed writing-mode", runtime.contains("writingMode"))
        assertTrue("C10：须支持作者显式声明", runtime.contains("getAttribute('data-rp-writing')"))
        // C11 素材治理：按需解码 + 去重 + 就绪后才提交
        assertTrue("C11：须有素材治理入口", runtime.contains("function materializeMaterials("))
        assertTrue("C11：须用 img.decode 预解码", runtime.contains(".decode()"))
        assertTrue("C11：须按 src 去重（同一素材只解码一次）", runtime.contains("state.decodedSrcs[src]"))
        assertTrue("C11：须有界等待（单图卡住不得拖死分页）", runtime.contains("MATERIAL_TIMEOUT_MS"))
        assertTrue("C11：须解耦结算（解码就绪后才提交可翻阅页面）", runtime.contains("materializeMaterials(function () {"))
        assertTrue(
            "三块状态必须自证回发（跨源读不到 <html>）",
            runtime.contains("',vp='") && runtime.contains("',writing='") && runtime.contains("',decoded='")
        )
    }

    @Test
    fun `响应式与竖排在结算之前完成且素材治理不吞掉结算`() {
        // 顺序即正确性：页框量取/分页以 `--rp-vp-w/h` 与 `data-rp-writing` 为依据 ⇒ 滞后一拍就按错尺寸分页；
        // 而结算必须发生在素材就绪回调内（否则图片未解码就提交了可翻阅页面 = C11 形同虚设）。
        //
        // ⚠️ 锚点用法（2026-10-13 修正）：`applyViewport();` 在**两个位置**都出现（`continueInit` 与
        // `remeasure` 分支），而 `markDecorations();` 只出现在 `continueInit` ⇒ 旧实现以
        // `markDecorations();` 之后的第一个 `applyViewport();` 为锚会恒取到 −1（位置断言假失败）。
        // 改为以 `flow.initialize(config.flow);`（continueInit 内的唯一锚）为中心：向前找其一、向后找其余。
        val runtime = asset("template-runtime.js")
        val init = runtime.indexOf("flow.initialize(config.flow);")
        assertTrue("未找到 continueInit 的 flow.initialize 锚点", init > 0)
        val iViewport = runtime.lastIndexOf("applyViewport();", init)
        val iWriting = runtime.indexOf("applyWritingMode();", init)
        val iMaterials = runtime.indexOf("materializeMaterials(function () {", init)
        val iSettle = runtime.indexOf("flow.settle(false)", init)
        val iMark = runtime.indexOf("markDecorations();", init)
        assertTrue("响应式断点须在锚点之前（早于页眉/页脚占位量取，否则首屏按旧尺寸分页）",
            iViewport in 1 until init)
        assertTrue("竖排判定须在锚点之后", iWriting > init)
        assertTrue("素材治理须在竖排之后", iMaterials > iWriting)
        assertTrue("结算必须发生在素材就绪回调内", iSettle > iMaterials)
        assertTrue("装饰分层须在结算之前完成（首个 stable 即带最终外观）", iMark in 1 until iSettle)
    }

    @Test
    fun `archive 契约层齐备（变量_字段_作者 API）`() {
        // AD-38 / archive-template-compat：archive 主题（如内置「明日香」`builtin.asuka_sync`）的
        // CSS 依赖一组 `--reader-*`、页脚依赖 `data-reader-field="pageIndex/pageCount"`、JS 依赖
        // `readerTemplate` 对象与钩子。三样缺一 ⇒ 主题明文失效（JS 首行抛 / 变量回落 UA 值 /
        // 页脚恒空），真机观感即用户实测的「死图」「完全效果都不一样」。
        val runtime = asset("template-runtime.js")
        // R1 变量：asuka 实测消费的 12 个 + archive baseCss 的 4 个 padding
        listOf(
            "--reader-text-color", "--reader-page-background", "--reader-accent",
            "--reader-font-size", "--reader-line-height", "--reader-font-family",
            "--reader-paragraph-indent", "--reader-paragraph-spacing",
            "--reader-safe-left", "--reader-safe-top", "--reader-safe-right", "--reader-safe-bottom",
            "--reader-padding-left", "--reader-padding-top", "--reader-padding-right", "--reader-padding-bottom",
            "--reader-selection-color"
        ).forEach { name ->
            assertTrue("须登记契约变量 $name", runtime.contains("'$name'"))
        }
        assertTrue("变量须有注入入口", runtime.contains("function applyReaderVars(config)"))
        assertTrue(
            "变量须在渲染作者 CSS 之前注入（否则首帧按回落值画一帧再跳变）",
            runtime.indexOf("applyReaderVars(config);") in 1 until runtime.indexOf("renderShell();")
        )
        // R2 字段：页脚 0 基页号
        assertTrue(
            "须补 pageIndex 派生字段（archive 页脚口径为 0 基）",
            runtime.contains("case 'pageIndex': return String(state.pageIndex)")
        )
        // R3 作者 API 与钩子
        assertTrue("须暴露 window.readerTemplate（缺则 archive 主题 JS 首行抛）", runtime.contains("window.readerTemplate = authorApi;"))
        assertTrue("须支持 on 注册", runtime.contains("readerTemplate.on requires a function"))
        assertTrue("须提供 .source（首个正文槽位）", runtime.contains("get source()"))
        assertTrue(
            "须提供 .pageCount/.pageIndex/.viewport/.motionState/.type 只读属性",
            runtime.contains("get pageCount()") && runtime.contains("get pageIndex()") &&
                runtime.contains("get viewport()") && runtime.contains("get motionState()") &&
                runtime.contains("get type()")
        )
        listOf("beforeLayout", "afterLayout", "pageChange", "motionChange", "fieldsChange", "dispose", "beforePage")
            .forEach { hook ->
                assertTrue("须触发 archive 钩子 $hook", runtime.contains("emitHook('$hook'"))
            }
        assertTrue(
            "beforePage 载荷须带页元素（doraemon/vertical 依赖它做每页逻辑）",
            runtime.contains("function pageEvent(shellName)") && runtime.contains("emitHook('beforePage', pageEvent(")
        )
        // R5 多正文槽顺序
        assertTrue(
            "须按 data-reader-order 排序正文槽位",
            runtime.contains("function orderedBodySlots()") && runtime.contains("data-reader-order")
        )
        // R8 段落/标题语义类归一：archive 主题 JS 只点选 `.reader-paragraph`，而我方 md/在线正文
        // 管线产出裸 `<p>` ⇒ 不补类则主题段落语义装饰"点空"（观感退回死图）
        assertTrue(
            "须补段落/标题语义类归一",
            runtime.contains("function normalizeReaderClasses()") &&
                runtime.contains("classList.add('reader-paragraph')") &&
                runtime.contains("classList.add('reader-chapter-title')")
        )
        // 装饰基线须并集 archive 主题的**作者自标**属性 `data-reader-decoration`
        // （`builtin.magazine` / `builtin.vertical` 的装饰元素用它）⇒ 导入主题同样吃
        // "装饰强度 / 专注模式"设置，否则这两套主题的设置项形同虚设。
        assertTrue(
            "装饰基线须并集 data-reader-decoration",
            asset("template-decoration.css").contains("[data-reader-decoration]")
        )
        // R3 载荷：钩子必须带"页元素"——archive 主题在 `event.pages` / `event.page` 上查询
        // （`.as-scan`/`.as-wave i`/`.as-live-dot`）并用 Web Animations 起"每页动图"；
        // 载荷为 null/空数组时主题**静默失效**（动图与进度同步全无，即用户实测的「死图」）。
        assertTrue("须提供页元素（模板根壳）", runtime.contains("function authorPage()"))
        assertTrue(
            "afterLayout 载荷须带页元素数组 pages",
            runtime.contains("emitHook('afterLayout', { pages: shell ? [shell] : []")
        )
        assertTrue(
            "pageChange 载荷须带页元素 page",
            runtime.contains("emitHook('pageChange', { page: shell,")
        )
        assertTrue(
            "motionChange 载荷须带 page/state/reducedMotion",
            runtime.contains("function motionEvent()") && runtime.contains("reducedMotion: false")
        )
        assertTrue(
            "结算后须补发一次动效事件（否则首屏/换壳后主题动图永不启动）",
            runtime.contains("emitHook('motionChange', motionEvent());")
        )
    }

    @Test
    fun `分栏判据须要列布局证据否则退回自研回退分页`() {
        // 真机铁证（2026-10-13，archive「明日香」）：作者只声明
        // `data-reader-flow-pagination="columns"` 却不写 `column-*` ⇒ 旧判据（只认声明）掉进
        // `settleColumns` 的"只读结果"路径：`scrollWidth == clientWidth` ⇒ 页数恒 1、且该路径
        // 从不冻结页框（`lastPageHeight == 0`）⇒ 正文溢出视口、页脚缺失、无法翻页。
        // 判据必须要求"列布局证据"，否则退回自研回退分页（纵向冻结 + 首/续页换壳照常生效）。
        val flow = asset("template-browser-flow.js")
        assertTrue("须有列布局证据判据", flow.contains("function authorProvidesColumns()"))
        assertTrue(
            "证据①：正文槽已产生横向溢出（作者的 column-* 真在起作用）",
            flow.contains("(slot.scrollWidth || 0) > (slot.clientWidth || 0) + 1")
        )
        assertTrue(
            "证据②：作者显式声明列数/列宽",
            flow.contains("cs.columnCount") && flow.contains("cs.columnWidth")
        )
        assertTrue(
            "isColumnsMode 必须要求证据（不得只认声明）",
            flow.contains("return authorProvidesColumns();")
        )
        assertTrue(
            "竖排必须仍走分栏（横移；退回纵移会打错轴）",
            flow.contains("function isVerticalWriting()") && flow.contains("if (isVerticalWriting()) return true;")
        )
        assertTrue(
            "竖排判据须与运行时单源（<html data-rp-writing>）",
            flow.contains("getAttribute('data-rp-writing') === 'vertical'")
        )
    }
}