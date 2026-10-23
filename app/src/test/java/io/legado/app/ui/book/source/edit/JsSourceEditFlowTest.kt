package io.legado.app.ui.book.source.edit

import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Test

/**
 * JS 书源编排状态机契约（2026-10-23 js-source-parity-and-crash-fix R1）。
 *
 * 编排跨「编辑器 → 调试页/登录页 → 编辑器」三次 Activity 往返，中途还可能被系统重建；
 * 把迁移表钉死，才能保证任何一条路径都不会"卡在中间态"或"重建后做错事"。
 */
class JsSourceEditFlowTest {

    @Test
    fun editorResultMapsToStage() {
        assertEquals(
            JsSourceEditStage.SAVING,
            stageForEditorResult(debugRequested = false, loginRequested = false)
        )
        assertEquals(
            JsSourceEditStage.SAVING_FOR_DEBUG,
            stageForEditorResult(debugRequested = true, loginRequested = false)
        )
        assertEquals(
            JsSourceEditStage.SAVING_FOR_LOGIN,
            stageForEditorResult(debugRequested = false, loginRequested = true)
        )
        // 两个动作同时给（理论不可达）时登录优先，避免"登录被当成调试"这类静默错配
        assertEquals(
            JsSourceEditStage.SAVING_FOR_LOGIN,
            stageForEditorResult(debugRequested = true, loginRequested = true)
        )
    }

    @Test
    fun restoreActionCoversEveryStage() {
        JsSourceEditStage.entries.forEach { stage ->
            // 每个阶段都必须有确定的恢复动作（不抛异常即为覆盖）
            stage.restoreAction()
        }
        assertEquals(
            JsSourceEditRestoreAction.OPEN_EDITOR,
            JsSourceEditStage.READY.restoreAction()
        )
        assertEquals(
            JsSourceEditRestoreAction.SAVE_AND_FINISH,
            JsSourceEditStage.SAVING.restoreAction()
        )
        assertEquals(
            JsSourceEditRestoreAction.SAVE_FOR_DEBUG,
            JsSourceEditStage.SAVING_FOR_DEBUG.restoreAction()
        )
        assertEquals(
            JsSourceEditRestoreAction.SAVE_FOR_LOGIN,
            JsSourceEditStage.SAVING_FOR_LOGIN.restoreAction()
        )
        assertEquals(
            JsSourceEditRestoreAction.LAUNCH_DEBUG,
            JsSourceEditStage.DEBUG_READY.restoreAction()
        )
        assertEquals(
            JsSourceEditRestoreAction.LAUNCH_LOGIN,
            JsSourceEditStage.LOGIN_READY.restoreAction()
        )
        // 三个"外部页面已打开"的中间态只能等结果，不能重复打开
        assertEquals(
            JsSourceEditRestoreAction.AWAIT_RESULT,
            JsSourceEditStage.EDITOR_OPEN.restoreAction()
        )
        assertEquals(
            JsSourceEditRestoreAction.AWAIT_RESULT,
            JsSourceEditStage.DEBUG_OPEN.restoreAction()
        )
        assertEquals(
            JsSourceEditRestoreAction.AWAIT_RESULT,
            JsSourceEditStage.LOGIN_OPEN.restoreAction()
        )
    }

    @Test
    fun successfulSaveAdvancesStage() {
        assertEquals(
            JsSourceEditStage.READY,
            JsSourceEditStage.SAVING.afterSuccessfulSave()
        )
        assertEquals(
            JsSourceEditStage.DEBUG_READY,
            JsSourceEditStage.SAVING_FOR_DEBUG.afterSuccessfulSave()
        )
        assertEquals(
            JsSourceEditStage.LOGIN_READY,
            JsSourceEditStage.SAVING_FOR_LOGIN.afterSuccessfulSave()
        )
    }

    @Test
    fun illegalSaveTransitionFailsFast() {
        // 非"保存中"阶段收到保存成功 ⇒ 必须显式报错，而不是静默停留（静默会让编排页永久卡住）
        assertThrows(IllegalStateException::class.java) {
            JsSourceEditStage.READY.afterSuccessfulSave()
        }
        assertThrows(IllegalStateException::class.java) {
            JsSourceEditStage.EDITOR_OPEN.afterSuccessfulSave()
        }
    }

    @Test
    fun externalPageResultsReturnToReady() {
        assertEquals(JsSourceEditStage.READY, JsSourceEditStage.DEBUG_OPEN.afterDebugResult())
        assertEquals(JsSourceEditStage.READY, JsSourceEditStage.LOGIN_OPEN.afterLoginResult())
        // 阶段不匹配 ⇒ 立即暴露（否则会出现"没打开调试页却收到调试结果"的错配）
        assertThrows(IllegalStateException::class.java) {
            JsSourceEditStage.READY.afterDebugResult()
        }
        assertThrows(IllegalStateException::class.java) {
            JsSourceEditStage.READY.afterLoginResult()
        }
    }
}
