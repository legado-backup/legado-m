package io.legado.app.help.export

import io.legado.app.help.config.ReadBookConfig
import java.util.Locale

/**
 * R8：把**当前阅读样式快照**生成为标准 CSS，追加到导出 EPUB 的 `Styles/main.css`。
 *
 * 为什么这样接：`assets/epub/chapter.html` 已显式引用 `../Styles/main.css`
 * （见 `ExportBookService.setAssets`）⇒ 只需把文本追加到该资源字节末尾，零模板改动。
 *
 * 只写固定安全属性集（font-family / font-size / line-height / letter-spacing /
 * color / background-color / margin-bottom / text-indent / text-align），
 * 不进入 `EpubCss` 的 shorthand 展开链（那是面向 EPUB 内容 CSS 的归一化流程）。
 */
object ReaderStyleCss {

    /** 与 [ReadBookConfig] 一一对应的纯数据快照（可在 JVM 单测中构造） */
    data class Snapshot(
        val textSizeSp: Int = 20,
        val lineSpacingExtra: Int = 12,
        val letterSpacingEm: Float = 0.1f,
        val paragraphSpacing: Int = 2,
        val paragraphIndent: String = "　　",
        /** ARGB；null = 不写该属性 */
        val textColor: Int? = null,
        val backgroundColor: Int? = null,
        /** 0=居左 1=居中 2=隐藏 */
        val titleMode: Int = 0,
        /** 0 = 继承正文 */
        val titleSizeSp: Int = 0
    )

    fun fromReadBookConfig(): Snapshot = Snapshot(
        textSizeSp = ReadBookConfig.textSize,
        lineSpacingExtra = ReadBookConfig.lineSpacingExtra,
        letterSpacingEm = ReadBookConfig.letterSpacing,
        paragraphSpacing = ReadBookConfig.paragraphSpacing,
        paragraphIndent = ReadBookConfig.paragraphIndent,
        textColor = ReadBookConfig.textColor,
        // bgMeanColor = 背景图取色；为 0 表示未设置/纯色未知 ⇒ 不写背景
        backgroundColor = ReadBookConfig.bgMeanColor.takeIf { it != 0 },
        titleMode = ReadBookConfig.titleMode,
        titleSizeSp = ReadBookConfig.titleSize
    )

    fun build(snapshot: Snapshot): String {
        val body = buildList {
            add("font-family: system-ui, -apple-system, serif")
            add("font-size: ${snapshot.textSizeSp.coerceAtLeast(1)}px")
            add("line-height: ${lineHeight(snapshot)}")
            add("letter-spacing: ${em(snapshot.letterSpacingEm)}")
            snapshot.textColor?.let { add("color: ${cssColor(it)}") }
            snapshot.backgroundColor?.let { add("background-color: ${cssColor(it)}") }
        }.joinToString("; ")

        val p = buildList {
            add("margin-bottom: ${snapshot.paragraphSpacing.coerceAtLeast(0)}px")
            indentEm(snapshot.paragraphIndent)?.let { add("text-indent: $it") }
        }.joinToString("; ")

        val title = buildTitle(snapshot)

        return buildString {
            append("\n/* 阅读器当前样式（导出快照，batch-20261029 R8） */\n")
            append("body { $body; }\n")
            append("p { $p; }\n")
            append(title)
        }
    }

    /** 标题块：隐藏模式直接 display:none；否则对齐 + 可选字号 */
    private fun buildTitle(snapshot: Snapshot): String {
        if (snapshot.titleMode == 2) {
            return "h1, h2, h3 { display: none; }\n"
        }
        val align = if (snapshot.titleMode == 1) "center" else "left"
        val size = snapshot.titleSizeSp.takeIf { it > 0 }?.let { " font-size: ${it}px;" }.orEmpty()
        return "h1, h2, h3 { text-align: $align;$size }\n"
    }

    /** 行高 = (字号 + 行间距) / 字号，保留 2 位小数（导出阅读器观感等价） */
    fun lineHeight(snapshot: Snapshot): String {
        val textSize = snapshot.textSizeSp.coerceAtLeast(1)
        val ratio = (textSize + snapshot.lineSpacingExtra.coerceAtLeast(0)).toFloat() / textSize
        return em(ratio)
    }

    /** 段首缩进：全角空格按 1em/字换算；空串/纯 ASCII 空格无法确定宽度时返回 null（不写该属性） */
    fun indentEm(indent: String): String? {
        if (indent.isEmpty()) return null
        val fullWidth = indent.count { it == '　' || it == '\u3000' }
        return if (fullWidth > 0) "${fullWidth}em" else null
    }

    private fun em(value: Float): String = String.format(Locale.US, "%.2f", value)

    /** ARGB → `#RRGGBB`（不透明）或 `rgba(r,g,b,a)`（半透明） */
    fun cssColor(argb: Int): String {
        val alpha = (argb ushr 24) and 0xFF
        val r = (argb ushr 16) and 0xFF
        val g = (argb ushr 8) and 0xFF
        val b = argb and 0xFF
        return if (alpha == 0xFF) {
            String.format(Locale.US, "#%02X%02X%02X", r, g, b)
        } else {
            String.format(Locale.US, "rgba(%d,%d,%d,%.2f)", r, g, b, alpha / 255f)
        }
    }
}
