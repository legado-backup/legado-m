package io.legado.app.ui.book.explore

/**
 * 单源发现页（经典"点源标签"列表）的布局模式（video-cache-and-multiep AD-05）。
 *
 * 取值与 `AppConfig.discoveryPageLayout` 一致，**保留既有语义**：
 * 1=列表（单列）、2=瀑布、3=三列、4=双列（新增，不迁移存量值）。
 */
object ExploreShowLayout {

    const val LIST = 1
    const val WATERFALL = 2
    const val TRIPLE = 3
    const val DUAL = 4

    const val MIN = LIST
    const val MAX = DUAL

    /** 默认瀑布（需求：默认到新版本里为瀑布模式） */
    const val DEFAULT = WATERFALL

    fun normalize(mode: Int): Int = mode.coerceIn(MIN, MAX)

    /** 网格列数：列表返回 1（仍按单列渲染，不启用网格） */
    fun columns(mode: Int): Int = when (normalize(mode)) {
        LIST -> 1
        WATERFALL -> 2
        TRIPLE -> 3
        DUAL -> 2
        else -> 1
    }

    /** 是否为瀑布（错落）布局：仅 WATERFALL 使用 Staggered 网格 */
    fun isWaterfall(mode: Int): Boolean = normalize(mode) == WATERFALL

    /** 是否使用网格容器（列表模式走既有 LazyColumn 路径） */
    fun isGrid(mode: Int): Boolean = normalize(mode) != LIST
}
