package io.legado.app.ui.book.read.config

import java.io.File
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * R 批 §3.3.2 页眉返回按钮 · 入口与资源（源码/资源文本断言）。
 *
 * 覆盖三段：①版面设置弹窗的开关（含事件回执，否则改了不生效）②布局里的图标与其约束
 * ③中英文案齐备。
 */
class TipConfigHeaderBackUiTest {

    private fun read(rel: String): String {
        val f = listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
        return f.readText()
    }

    @Test
    fun dialogExposesSwitchWiredToConfig() {
        val t = read("src/main/java/io/legado/app/ui/book/read/config/TipConfigDialog.kt")
        assertTrue("须读取当前配置值", t.contains("mutableStateOf(ReadTipConfig.showHeaderBackButton)"))
        assertTrue("须回写配置", t.contains("ReadTipConfig.showHeaderBackButton = it"))
        assertTrue(
            "须广播 UP_CONFIG(2) 让阅读页即时刷新（否则改了不生效）",
            t.contains("postEvent(EventBus.UP_CONFIG, arrayListOf(2))")
        )
    }

    @Test
    fun layoutHasHiddenBackIconBeforeLeftSlot() {
        val t = read("src/main/res/layout/view_book_page.xml")
        assertTrue("须新增页眉返回图标", t.contains("android:id=\"@+id/iv_header_back\""))
        assertTrue("默认必须隐藏", t.contains("android:visibility=\"gone\""))
        assertTrue("图标资产须复用项目 ic_back", t.contains("android:src=\"@drawable/ic_back\""))
        assertTrue(
            "左槽须改为排在图标右侧（否则图标与文字重叠）",
            t.contains("app:layout_constraintLeft_toRightOf=\"@+id/iv_header_back\"")
        )
    }

    @Test
    fun stringsExistInBothLocales() {
        val zh = read("src/main/res/values-zh/strings.xml")
        val en = read("src/main/res/values/strings.xml")
        listOf(zh, en).forEach { t ->
            assertTrue("缺 read_header_back_button", t.contains("name=\"read_header_back_button\""))
            assertTrue("缺 read_header_back_button_hint", t.contains("name=\"read_header_back_button_hint\""))
        }
    }
}