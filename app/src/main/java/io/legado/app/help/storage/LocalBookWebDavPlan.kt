package io.legado.app.help.storage

/**
 * R9：本地书自动上传 WebDAV 的路径与冲突判定（纯函数，可 JVM 单测）。
 *
 * 上传目标与既有 `RemoteBookWebDav.upload` 保持一致：`books/{originName}/`；
 * 冲突判定只认**完全同名**（不做模糊匹配），命中即跳过，避免覆盖用户云端文件。
 */
object LocalBookWebDavPlan {

    /** 目标目录 = 根书库地址 + 原始文件名（originName 对本地书即文件名） */
    fun targetDir(rootBookUrl: String, originName: String): String = "$rootBookUrl$originName"

    fun hasNameConflict(existingNames: Collection<String>, fileName: String): Boolean =
        existingNames.any { it == fileName }

    /** 是否应触发自动上传（开关 + 已配置 WebDAV + 书确为本地书） */
    fun shouldAutoUpload(
        switchEnabled: Boolean,
        webDavConfigured: Boolean,
        bookIsLocal: Boolean
    ): Boolean = switchEnabled && webDavConfigured && bookIsLocal
}
