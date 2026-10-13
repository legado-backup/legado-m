package io.legado.app.ui.widget.compose

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * `AppDialogFrame` 内容区**自适应高度**契约测试（2026-10-13 真机事故沉淀）。
 *
 * 事故链（真机一手证据）：横屏 1600x900 / density 300 ⇒ 可视高仅 **480dp**。
 * `AppDialogFrame` 内容区原为固定 `heightIn(max = 520.dp)` 的**非加权**子项，
 * Column 先量内容再量动作区 ⇒ 内容吃掉全部可用高度后，动作区被压成 0 高
 * ⇒ 「文件选择」弹框的「新建文件夹 / OK」**挤出可视区且不可达**
 * ⇒ 从其它应用导出的 archive ZIP 主题包**无法完成导入**（用户诉求 5 在真机上复现）。
 *
 * 修复口径：内容区改为 `weight(1f, fill = false) + heightIn(max = 520.dp)`——
 * 有界窗口下把**剩余高度**让给内容，动作区先量；内容较短时 `fill=false` 保证仍按内容 wrap，
 * 与修复前完全一致（仅"窗口不足"这一种情况行为改变）。
 *
 * 本测试锁死三件事，防「改回固定高度」与「动作区锚点漂移」：
 *   ①内容区必须同时具备 `weight(1f, fill = false)` 与 `heightIn(max = 520.dp)`；
 *   ②内容区**不得**再出现"先内容后动作"的固定高度写法（即不得只有 heightIn 而无 weight）；
 *   ③`FilePickerDialog` 的确认按钮仍挂在 `R.string.ok` 上（真机 L2 脚本按 `values-zh` 的实际值
 *      「确认」/英文「OK」点击，故锁定**资源名**而非字面值——锁定字面值会随语言包失效）。
 */
class AppDialogFrameAdaptiveHeightTest {

    private val frameRel = "ui/widget/compose/AppComposeDialogs.kt"
    private val pickerRel = "ui/file/FilePickerDialog.kt"

    /**
     * 取 `AppDialogFrame` 内 `contentModifier` 的声明片段（剥注释后的源码文本）。
     *
     * 用**声明片段**而非全文件：`AppComposeDialogs.kt` 内有多个 `heightIn(max = ...)` 用法，
     * 全文断言会假阳性（本项目已多次实证「口径过宽 ⇒ 断言恒真」）。
     */
    private fun contentModifierBlock(): String {
        val code = SourceFileProbe.sourceText(frameRel)
        val start = code.indexOf("val contentModifier")
        assertTrue("未找到 contentModifier 声明（AppDialogFrame 结构已变，测试需同步）", start >= 0)
        val end = code.indexOf("val shouldScrollContent", start)
        assertTrue("未找到 shouldScrollContent（contentModifier 声明块结构已变）", end > start)
        return code.substring(start, end)
    }

    @Test
    fun contentAreaIsAdaptiveWeightedSoActionsStayVisible() {
        val block = contentModifierBlock()
        assertTrue(
            "内容区必须使用 weight(1f, fill = false)：否则矮窗口下动作区会被挤出可视区",
            block.contains("weight(1f, fill = false)")
        )
        assertTrue(
            "内容区必须保留 520dp 视觉上限（高窗口下与旧行为一致）",
            block.contains("heightIn(max = 520.dp)")
        )
    }

    @Test
    fun contentAreaNoLongerUsesFixedHeightOnly() {
        // 归一化空白后再比对：直接按缩进字面量比对会随格式化漂移（本项目已实证此类脆断言）
        val compact = contentModifierBlock().replace(Regex("\\s+"), "")
        assertFalse(
            "内容区不得回到『仅固定最大高度』的旧写法（会让动作区不可达）",
            compact.contains(".fillMaxWidth().heightIn(max=520.dp)")
        )
    }

    @Test
    fun filePickerConfirmActionStaysOnOkStringAnchor() {
        val code = SourceFileProbe.sourceText(pickerRel)
        // L2 脚本按 `R.string.ok` 的**运行值**点击（zh ⇒「确认」、英文 ⇒「OK」）；锚点一旦换串，真机验证会静默失效
        assertTrue(
            "文件选择器确认按钮必须仍使用 R.string.ok（真机 L2 脚本的点击锚点）",
            code.contains("stringResource(R.string.ok)")
        )
        // 两步语义：点文件行只选中（selectFileState），必须再点确认才回传
        assertTrue(
            "文件选择器必须保留『点行仅选中』语义（selectFileState）",
            code.contains("selectFileState = item")
        )
    }
}