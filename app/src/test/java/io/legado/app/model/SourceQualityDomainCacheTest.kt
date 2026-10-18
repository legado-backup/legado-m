package io.legado.app.model

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

/**
 * AD-04 域名缓存策略（2026-10-18）
 *
 * 真机巡检 2502 条 DOMAIN 失败里含**大量同 host 源** ⇒ 负向结果若跨源复用，会把「一个源瞬时失败」
 * 连坐成「整 host 全失效」（8282 事故同族）⇒ 收敛为**只缓存正向**、负向逐源复探。
 *
 * 注：`SourceQualitySession` 含 Android 依赖、JVM 下不可实例化 ⇒ 用**纯函数决策** `positiveOnlyCacheValue`
 * 做单测（与生产实现共用同一判据，避免口径漂移）。
 */
class SourceQualityDomainCacheTest {

    @Test
    fun `正向结果允许入缓存`() {
        assertEquals(true, positiveOnlyCacheValue(true))
    }

    @Test
    fun `负向结果不入缓存(防整 host 连坐)`() {
        assertNull(positiveOnlyCacheValue(false))
    }
}
