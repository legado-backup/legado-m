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

    /**
     * 布局选择器的取值顺序（列表 / 瀑布 / 双列 / 三列）。
     *
     * 设置项弹框与页内右上角切换共用此顺序，避免两处顺序漂移。
     */
    val pickerValues: List<Int> = listOf(LIST, WATERFALL, DUAL, TRIPLE)

    /**
     * 布局切换入口的顶栏分级：true=一级图标直出（需求 R11「右上角加按钮」）。
     *
     * 置 false 会把入口退化为 ⋮ 二级菜单；需求原文要求一键可见，故锁定为 true。
     */
    const val TOP_BAR_ACTION_ALWAYS_SHOW = true

    fun normalize(mode: Int): Int = mode.coerceIn(MIN, MAX)

    /**
     * 网格卡片书名最大行数：固定 2 行。
     *
     * 1 行对长书名截断过重；3 行会显著抬高同排列高（三列尤甚）。口径外置于此，
     * 便于单测锁定，避免散落在 Composable 内。
     */
    const val GRID_TITLE_MAX_LINES = 2

    /**
     * 网格卡片封面宽高比（`width / height`）= 3:4 竖版，与订阅源网格卡同口径。
     *
     * 固定比例容器：封面缺失 / 加载失败时卡片高度不塌陷（否则瀑布流会跳变）。
     */
    const val GRID_COVER_ASPECT_RATIO = 0.75f

    /**
     * 网格卡片书名字号（sp）：三列列宽窄，收窄到 12sp；双列/瀑布 13sp。
     *
     * 红队第 5 轮实测：三列约 124dp 列宽，13sp 下 2 行仍会挤，故按列数分档。
     */
    fun gridTitleFontSize(columns: Int): Int = if (columns >= TRIPLE) 12 else 13

    /**
     * 网格卡片是否渲染行尾 ⋮：三种网格布局一律 false（用户要求「去掉三个竖点」）。
     *
     * 该口径由「单击=书籍详情（详情页可加入书架）/ 长按=预览」承接，见设计 AD-02。
     */
    fun gridShowsMore(mode: Int): Boolean = false

    /**
     * 网格卡片简介最大行数。
     *
     * 瀑布流**不限行**（完整展示简介，卡片高度随文案自然变化 ⇒ 真实错落，与订阅源瀑布流同构）；
     * 双列 / 三列返回 0（不展示简介，保持等高卡，避免同排参差影响阅读节奏）。
     */
    fun gridIntroMaxLines(mode: Int): Int = if (isWaterfall(mode)) Int.MAX_VALUE else 0

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
