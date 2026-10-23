package io.legado.app.constant

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotEquals
import org.junit.Test

/**
 * video-cache-and-multiep V1：新增通知 ID 的登记约束（不得与既有服务撞号）。
 */
class NotificationIdTest {

    @Test
    fun `video cache notification id is registered and unique`() {
        val used = listOf(
            NotificationId.ReadAloudService,
            NotificationId.AudioPlayService,
            NotificationId.CacheBookService,
            NotificationId.ExportBookService,
            NotificationId.WebService,
            NotificationId.DownloadService,
            NotificationId.CheckSourceService,
            NotificationId.CheckRssSourceService,
            NotificationId.VideoPlayService,
            NotificationId.AutoTaskService,
            NotificationId.AiTaskService,
            NotificationId.PublicWebRelayService,
            NotificationId.DlnaCastService,
            NotificationId.WebDavTask,
        )
        assertEquals(115, NotificationId.VideoCacheService)
        used.forEach { assertNotEquals(it, NotificationId.VideoCacheService) }
    }
}
