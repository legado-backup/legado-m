package io.legado.app.model.localBook.epubcore.template

import com.google.gson.JsonParser
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File
import java.security.MessageDigest
import java.util.Base64

/**
 * 成套美术素材登记校验单测（epub-md-rich-rendering 阶段 4.16 配对）。
 *
 * 4.16 的验收标准是「成套美术齐备 + 素材来源/许可**可考证** + 无第三方 IP 素材」。前两条若只写在
 * `sources.json` 里就是**自证**（改坏素材而登记不变，或登记一条永不被消费的死素材，都不会被发现）。
 * 本测试把两条都钉成**机检契约**：
 *
 * 1. **可考证**＝登记里的 `sha256` 必须与**真实内联字节**（`data:` 解码后 / 内联 SVG 原文）逐一相符
 *    ⇒ 谁都可以拿登记里的来源地址重新下载并复核"未篡改"；
 * 2. **无死登记 / 无走私**＝登记的每一项都要在模板源码里找到消费者（`@font-face` / `background-image`
 *    / `<svg class=…>`），且源码里的每一个 `data:` 内联素材都要有登记项 ⇒ 双向闭合。
 *
 * 另附：许可白名单（OFL-1.1 / CC0 / PD / 自研）、许可原文随包（OFL 要求）与哈希一致。
 */
class ReaderBuiltinTemplateAssetsTest {

    private val assetsRoot = File("src/main/assets")

    private val reader = ReaderBuiltinTemplateCatalog.AssetReader { path ->
        val file = File(assetsRoot, path)
        if (file.isFile) file.readText() else null
    }

    private val loaded by lazy { ReaderBuiltinTemplateCatalog.load(reader) }

    private class Entry(
        val kind: String,
        val type: String,
        val alias: String,
        val license: String,
        val author: String,
        val source: String,
        val sourceUrl: String,
        val purpose: String,
        val sha256: String,
        val marker: String,
        val family: String,
        val licenseFile: String,
        val licenseSha256: String,
    )

    private fun entriesOf(builtin: ReaderBuiltinTemplateCatalog.BuiltinTemplate): List<Entry> {
        val root = JsonParser.parseString(builtin.sources).asJsonObject
        val array = root.getAsJsonArray("assets") ?: return emptyList()
        return array.map { item ->
            val obj = item.asJsonObject
            fun str(name: String) = obj.get(name)?.takeIf { it.isJsonPrimitive }?.asString.orEmpty()
            Entry(
                kind = str("kind"), type = str("type"), alias = str("alias"),
                license = str("license"), author = str("author"), source = str("source"),
                sourceUrl = str("sourceUrl"), purpose = str("purpose"), sha256 = str("sha256"),
                marker = str("marker"), family = str("family"),
                licenseFile = str("licenseFile"), licenseSha256 = str("licenseSha256"),
            )
        }
    }

    private fun flagship(): List<ReaderBuiltinTemplateCatalog.BuiltinTemplate> =
        loaded.templates.filter { it.id in FLAGSHIPS }

    private fun sha256(bytes: ByteArray): String =
        MessageDigest.getInstance("SHA-256").digest(bytes).joinToString("") {
            (it.toInt() and 0xff).toString(16).padStart(2, '0')
        }

    private fun sha256(text: String) = sha256(text.toByteArray(Charsets.UTF_8))

    @Test
    fun `三套旗舰主题成套齐备（开篇图 + 边框 + 页脚图形）`() {
        assertEquals("旗舰主题必须全部加载成功：${loaded.errors}", emptySet<String>(), FLAGSHIPS - loaded.templates.map { it.id }.toSet())
        flagship().forEach { builtin ->
            val kinds = entriesOf(builtin).map { it.kind }.toSet()
            SUITE_KINDS.forEach { kind ->
                assertTrue("${builtin.id} 缺成套美术片段：$kind（实有 $kinds）", kinds.contains(kind))
            }
            // 配色：成套美术要求"统一配色"，日/夜双版由主题基线保证
            assertTrue("${builtin.id} 必须定义日/夜双版配色", builtin.template.css.contains("[data-reader-theme=\"night\"]"))
            // 字体：至少一套字体登记（拉丁 OFL）或显式声明用系统 OFL 字族
            assertTrue(
                "${builtin.id} 成套要求含字体（OFL 随包或系统 OFL 字族）",
                entriesOf(builtin).any { it.kind == "font" } ||
                    builtin.template.css.contains("Noto Serif CJK SC") ||
                    builtin.template.css.contains("Source Han")
            )
        }
    }

    @Test
    fun `素材来源与许可逐项在场且许可在白名单内`() {
        flagship().forEach { builtin ->
            entriesOf(builtin).forEach { entry ->
                assertTrue("${builtin.id}:${entry.alias} 许可不得为空", entry.license.isNotBlank())
                assertTrue(
                    "${builtin.id}:${entry.alias} 许可不在白名单：${entry.license}",
                    ALLOWED_LICENSES.contains(entry.license)
                )
                assertTrue("${builtin.id}:${entry.alias} 必须声明来源", entry.source.isNotBlank())
                assertTrue("${builtin.id}:${entry.alias} 必须声明作者/提供方", entry.author.isNotBlank())
                assertTrue("${builtin.id}:${entry.alias} 必须声明用途", entry.purpose.isNotBlank())
                if (entry.type != "svg-inline") {
                    assertTrue(
                        "${builtin.id}:${entry.alias} 外部素材必须可回源复核（sourceUrl）",
                        entry.sourceUrl.startsWith("https://")
                    )
                }
            }
        }
    }

    @Test
    fun `内联字体与纹理字节的 SHA-256 与登记一致`() {
        flagship().forEach { builtin ->
            val source = builtin.template.resourceSource()
            entriesOf(builtin).filter { it.type == "font" || it.type == "image" }.forEach { entry ->
                val prefix = if (entry.type == "font") "data:font/woff2;base64," else "data:image/webp;base64,"
                val payload = findBase64(source, prefix)
                assertTrue("${builtin.id}:${entry.alias} 模板内未找到 ${prefix} 内联素材", payload != null)
                assertEquals(
                    "${builtin.id}:${entry.alias} 内联字节与登记 SHA-256 不一致（素材被改而非登记）",
                    entry.sha256, sha256(Base64.getDecoder().decode(payload!!))
                )
            }
        }
    }

    @Test
    fun `自研 SVG 成套美术的内联标记与登记一致`() {
        flagship().forEach { builtin ->
            val source = builtin.template.resourceSource()
            entriesOf(builtin).filter { it.type == "svg-inline" }.forEach { entry ->
                val block = findSvgByClass(source, entry.marker)
                assertTrue("${builtin.id}:${entry.alias} 未找到内联 SVG（marker=${entry.marker}）", block != null)
                assertEquals(
                    "${builtin.id}:${entry.alias} 内联 SVG 与登记 SHA-256 不一致",
                    entry.sha256, sha256(block!!)
                )
                // 取色必须随主题（否则日/夜双版下装饰会偏色）
                assertTrue(
                    "${builtin.id}:${entry.alias} 自研 SVG 必须用 currentColor 随主题取色",
                    block.contains("currentColor")
                )
            }
        }
    }

    @Test
    fun `登记素材确有消费者（无死登记）`() {
        flagship().forEach { builtin ->
            val css = builtin.template.css
            val source = builtin.template.resourceSource()
            entriesOf(builtin).forEach { entry ->
                when (entry.type) {
                    "font" -> {
                        assertTrue(
                            "${builtin.id}:${entry.alias} 字体未被 @font-face 声明",
                            css.contains("@font-face{font-family:\"${entry.family}\"")
                        )
                        assertTrue(
                            "${builtin.id}:${entry.alias} 字族 ${entry.family} 未被任何选择器消费",
                            css.contains("font-family:\"${entry.family}\"")
                        )
                    }
                    "image" -> assertTrue(
                        "${builtin.id}:${entry.alias} 纹理元素 .${entry.marker} 未消费该背景",
                        Regex("""\.${entry.marker}\{[^}]*background-image:url\("data:image/webp;base64,""").containsMatchIn(css)
                    )
                    else -> assertTrue("${builtin.id}:${entry.alias} SVG 未被消费", source.contains("class=\"${entry.marker}\""))
                }
            }
        }
    }

    @Test
    fun `模板内不得出现未登记的内联素材（无走私）`() {
        loaded.templates.forEach { builtin ->
            val inline = INLINE_DATA.findAll(builtin.template.resourceSource()).count()
            val registered = entriesOf(builtin).count { it.type == "font" || it.type == "image" }
            assertEquals(
                "${builtin.id} 内联 data: 素材数 $inline 与登记数 $registered 不符（未登记素材不得入库）",
                registered, inline
            )
        }
    }

    @Test
    fun `OFL 许可原文随包且与登记哈希一致`() {
        flagship().forEach { builtin ->
            entriesOf(builtin).filter { it.licenseFile.isNotBlank() }.forEach { entry ->
                val path = ReaderBuiltinTemplateCatalog.sourcesPath(builtin.id).substringBeforeLast('/') +
                    "/" + entry.licenseFile
                val file = File(assetsRoot, path)
                assertTrue("${builtin.id} 缺许可原文随包：$path", file.isFile)
                val text = file.readText()
                assertTrue("${builtin.id} 许可原文须为 OFL 正文", text.contains("SIL OPEN FONT LICENSE"))
                // 行尾归一后再比：本仓 `core.autocrlf=true`，同一份许可在克隆/检出后会是 CRLF，
                // 逐字节比较会把"行尾被 git 改写"误判成"许可被篡改"（内容未变）。
                assertEquals(
                    "${builtin.id} 许可原文与登记哈希不一致",
                    entry.licenseSha256, sha256(text.replace("\r\n", "\n"))
                )
            }
        }
        // 至少一套必须真的带 OFL 原文（否则"字体随包"是空话）
        assertTrue(
            "旗舰主题至少一套须随包 OFL 许可原文",
            flagship().any { b -> entriesOf(b).any { it.licenseFile.isNotBlank() } }
        )
    }

    @Test
    fun `纯 CSS 模板保持零素材登记`() {
        loaded.templates.filter { it.id !in FLAGSHIPS }.forEach { builtin ->
            val entries = entriesOf(builtin)
            assertTrue("${builtin.id} 非旗舰模板不应登记素材（本轮不改动）", entries.isEmpty())
            assertFalse(
                "${builtin.id} 非旗舰模板不应出现内联 data: 素材",
                builtin.template.resourceSource().contains("data:")
            )
        }
    }

    private fun findBase64(source: String, prefix: String): String? {
        val index = source.indexOf(prefix)
        if (index < 0) return null
        val rest = source.substring(index + prefix.length)
        return rest.takeWhile { it.isLetterOrDigit() || it == '+' || it == '/' || it == '=' }
    }

    private fun findSvgByClass(source: String, marker: String): String? {
        val start = source.indexOf("<svg class=\"$marker\"")
        if (start < 0) return null
        val end = source.indexOf("</svg>", start)
        if (end < 0) return null
        return source.substring(start, end + "</svg>".length)
    }

    private companion object {
        val FLAGSHIPS = setOf("builtin.neon-night", "builtin.star-chart", "builtin.ink")
        val SUITE_KINDS = listOf("opening", "border", "footer")

        /** 许可白名单（AD-21 四条口径）：OFL / CC0 / 公有领域 / 自研随包分发。 */
        val ALLOWED_LICENSES = setOf("OFL-1.1", "CC0", "Public domain", "自研（随应用分发）")

        val INLINE_DATA = Regex("""data:[a-zA-Z0-9.+-]+/[a-zA-Z0-9.+-]+;base64,""")
    }
}