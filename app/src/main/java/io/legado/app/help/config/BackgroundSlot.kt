package io.legado.app.help.config

import android.graphics.drawable.Drawable

/**
 * 共享背景 Drawable 的持有槽（跨 ReadBookActivity 实例共享）。
 *
 * 抽成独立类型是为了让"替换背景不得回收旧位图"这条红线可以被纯行为单测覆盖，
 * 而不依赖 ReadBookConfig 的初始化（它会在测试环境读 assets/配置文件）。
 */
internal class BackgroundSlot(
    @Volatile
    var drawable: Drawable? = null
)

/**
 * 替换背景并返回旧值。
 *
 * 🔴 禁止在此回收旧位图：旧窗口的 PageView 可能仍在绘制同一 Bitmap
 * （`Canvas: trying to use a recycled bitmap` 的根因）。
 */
internal fun swapBackground(slot: BackgroundSlot, next: Drawable?): Drawable? {
    val old = slot.drawable
    slot.drawable = next
    return old
}
