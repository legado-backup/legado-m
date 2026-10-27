package io.legado.app.ui.source.edit

import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import com.google.android.material.tabs.TabLayout

/**
 * TabLayout 默认 TextAppearance 会强制全大写；英文标签（如 WebView）会显示成 WEBVIEW。
 *
 * 编辑页按用户裁定保留英文规范单词 `WebView`，故在 tab 视图挂载后关闭 allCaps。
 * 中文标签不受影响。
 */
fun TabLayout.applyNoCapsTabLabels() {
    post {
        for (index in 0 until tabCount) {
            getTabAt(index)?.view?.findTextViews()?.forEach { it.isAllCaps = false }
        }
    }
}

private fun View.findTextViews(): List<TextView> = buildList {
    if (this@findTextViews is TextView) add(this@findTextViews)
    if (this@findTextViews is ViewGroup) {
        for (i in 0 until childCount) {
            addAll(getChildAt(i).findTextViews())
        }
    }
}
