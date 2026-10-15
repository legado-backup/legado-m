package io.legado.app.data

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * core-flow-test-coverage tasks 4.1 / design.md AD-04 —— 主线程查库守卫（现状钉桩）。
 *
 * 【AD-02 例外（如实标注）】`appDb` 依赖 `appCtx`（splitties），**纯 JVM 无法构造**
 * ⇒ 无法行为断言，退化为**源码文本探针**。
 *
 * **升级路径（AD-04）**：一旦移除 `.allowMainThreadQueries()`（对齐辞晨 `e506746`），
 * 本测试应切换为「主线程直连 DAO 必抛 IllegalStateException」的严格**行为**断言
 * （参见辞晨 `MainThreadDbGuardTest.rawDaoOnMainThreadStillThrows`）；
 * `allowMainThreadQueriesStillPresent` 此即在切换前**防开关静默漂移**。
 */
class AppDatabaseGuardTest {

    private val source = SourceFileProbe.sourceText("data/AppDatabase.kt")

    @Test
    fun appDbWiresMigrationsAndCallback() {
        assertTrue(source.contains(".fallbackToDestructiveMigrationFrom("))
        assertTrue(source.contains(".addMigrations(*DatabaseMigrations.migrations)"))
        assertTrue(source.contains(".addCallback(AppDatabase.dbCallback)"))
    }

    @Test
    fun allowMainThreadQueriesStillPresent_guardsCurrentSemantics() {
        assertTrue(
            "allowMainThreadQueries 当前仍在（AD-04 现状钉桩）；移除时请将本类切换为「主线程必抛」的行为断言",
            source.contains(".allowMainThreadQueries()")
        )
    }
}
