package io.legado.app.help.video

/**
 * 集数分组内核（video-cache-and-multiep AD-03）。
 *
 * 书源（卷章/扁平目录）与订阅源（routes/episodes）**共用**的分组与定位规则，
 * 纯函数、无 Android 依赖，便于单测穷举边界。
 *
 * 规则：
 * 1. 组内默认 10 集；当总集数导致组数 > [MAX_GROUPS] 时，按 10 递增扩大组内集数，
 *    直到组数 ≤ [MAX_GROUPS]（1000 集 ⇒ 每组 100 集、正好 10 组）。
 * 2. 最后一组可不满（按实际集数收尾）。
 * 3. 索引一律 0-based（与 `BookChapter.index` / `episodes` 列表下标语义一致）。
 */
object EpisodePager {

    /** 需求「最多支持 5 到 10 个分组」的上限 */
    const val MAX_GROUPS = 10

    /** 默认组内集数 */
    const val DEFAULT_GROUP_SIZE = 10

    /** 单组上限（防御性：极大剧集也不会无限增长） */
    const val MAX_GROUP_SIZE = 100

    data class Group(
        val startIndex: Int,
        val endIndex: Int,
    ) {
        /** 展示用：1-based 且闭区间，如 `1-10` */
        val label: String get() = "${startIndex + 1}-${endIndex + 1}"
        val count: Int get() = endIndex - startIndex + 1
    }

    data class Paging(
        val groups: List<Group>,
        val currentGroupIndex: Int,
        val groupSize: Int,
    ) {
        val hasGroups: Boolean get() = groups.isNotEmpty()
    }

    /**
     * 组内集数：保证组数 ≤ [MAX_GROUPS]，且组内不超过 [MAX_GROUP_SIZE]。
     */
    fun groupSizeFor(total: Int, maxGroups: Int = MAX_GROUPS): Int {
        if (total <= 0) return DEFAULT_GROUP_SIZE
        val limit = maxGroups.coerceAtLeast(1)
        var size = DEFAULT_GROUP_SIZE
        while (ceilDiv(total, size) > limit && size < MAX_GROUP_SIZE) {
            size += DEFAULT_GROUP_SIZE
        }
        return size
    }

    /**
     * 生成分组并定位当前集所在组。
     *
     * @param total 集数总数（<=0 返回空分组）
     * @param currentIndex 当前集索引（0-based；越界会被钳到合法范围）
     */
    fun build(
        total: Int,
        currentIndex: Int,
        maxGroups: Int = MAX_GROUPS,
    ): Paging {
        if (total <= 0) return Paging(emptyList(), -1, DEFAULT_GROUP_SIZE)
        val size = groupSizeFor(total, maxGroups)
        val groups = ArrayList<Group>(Math.min(total, maxGroups) + 1)
        var start = 0
        while (start < total) {
            val end = Math.min(start + size - 1, total - 1)
            groups.add(Group(start, end))
            start = end + 1
        }
        val safeCurrent = currentIndex.coerceIn(0, total - 1)
        return Paging(
            groups = groups,
            currentGroupIndex = safeCurrent / size,
            groupSize = size,
        )
    }

    private fun ceilDiv(a: Int, b: Int): Int = (a + b - 1) / b
}
