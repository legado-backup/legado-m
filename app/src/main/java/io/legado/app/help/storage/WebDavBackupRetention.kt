package io.legado.app.help.storage

/**
 * R6：WebDAV 云端备份保留策略（纯函数，可 JVM 单测）。
 *
 * 并发安全要点（AD-09）：删除集合必须以**清理开始前**的列表为基准，再与**执行前重新拉取**的
 * 当前列表取交集 —— 否则其他设备刚上传、排在"旧集合"之外的新备份不会被动；
 * 反过来，若直接按当前列表删除尾部，会把并发上传的新备份误删。
 */
object WebDavBackupRetention {

    /**
     * @param existingNewestFirst 清理前已存在的备份名（新 → 旧）
     * @param current 执行前重新拉取的当前备份名（新 → 旧）
     * @param retain 保留数量（<=0 表示关闭自动清理）
     * @return 需要删除的备份名（旧 → 顺序按 existingNewestFirst 的尾部顺序）
     */
    fun namesToDelete(
        existingNewestFirst: List<String>,
        current: List<String>,
        retain: Int
    ): List<String> {
        if (retain <= 0) return emptyList()
        if (existingNewestFirst.size <= retain) return emptyList()
        val currentSet = current.toSet()
        return existingNewestFirst
            .filter { it in currentSet }
            .drop(retain)
    }
}
