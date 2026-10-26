package io.legado.app.constant

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 调试卷支路开关键 单元测试（design AD-03 / tasks 2.5）。
 *
 * 断言要点（带期望值）：
 * 1. 键名**稳定**（调试脚本与设置页按此键读写，改名即静默失效）；
 * 2. 与既有三级令牌/严格模式键**不冲突**（避免误关主令牌校验）；
 * 3. 命名遵循项目既有 `web*` 前缀分组（便于设置页归类）。
 */
class PreferKeyDebugBranchTest {

    @Test
    fun webAuthDebugBranch_keyIsStable() {
        assertEquals(
            "支路开关键名必须稳定（脚本/设置页按此键读写）",
            "webAuthDebugBranch",
            PreferKey.webAuthDebugBranch,
        )
    }

    @Test
    fun webAuthDebugBranch_doesNotCollideWithTokenKeys() {
        val authKeys = listOf(
            PreferKey.webTokenReadonly,
            PreferKey.webTokenManage,
            PreferKey.webTokenAdmin,
            PreferKey.webAuthStrict,
            PreferKey.webServiceFirstLaunchDone,
        )
        authKeys.forEach { existing ->
            assertNotEquals(
                "支路开关键不得与既有鉴权键同名（否则会互相覆盖）：$existing",
                existing,
                PreferKey.webAuthDebugBranch,
            )
        }
    }

    @Test
    fun webAuthDebugBranch_followsWebPrefixConvention() {
        assertTrue(
            "键名应遵循 web* 前缀分组（设置页按前缀归类）",
            PreferKey.webAuthDebugBranch.startsWith("web"),
        )
    }
}