package io.legado.app.help.source

import kotlinx.coroutines.CoroutineName
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * P0-S3 书源弹窗拦截策略单测（分册 §9.1 T20）
 *
 * SourceInteractionPolicy 为协程上下文 Element + AtomicBoolean，纯 JVM 可测：
 * 运行中翻转状态（updateBlockDialogs）随 SearchModel/ChangeBookSourceViewModel 挂载点实时生效。
 */
class SourceInteractionPolicyTest {

    @Test
    fun updateBlockDialogs_flipsStateAtRuntime() {
        val policy = SourceInteractionPolicy(false)
        assertFalse(policy.blockDialogs)
        // 运行中翻转（协程树传播场景：批量搜索中途开关）
        policy.updateBlockDialogs(true)
        assertTrue(policy.blockDialogs)
        policy.updateBlockDialogs(false)
        assertFalse(policy.blockDialogs)
        // 协程上下文 Element 语义：context[SourceInteractionPolicy] 可检索到自身（子协程传播前提）
        val retrieved: SourceInteractionPolicy? = (CoroutineName("t") + policy)[SourceInteractionPolicy]
        assertEquals(policy, retrieved)
    }
}
