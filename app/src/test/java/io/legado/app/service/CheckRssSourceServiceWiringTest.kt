package io.legado.app.service

import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 订阅源侧接线不变量（源码文本断言；测试缝不可行为化 ⇒ 见 `empty_test_allowlist.json` 的 exception 登记）。
 *
 * 为什么只能结构断言：`CheckRssSourceService` 的实例化依赖 `BaseService` + `appCtx`，且分组读写走
 * Android `TextUtils`（JVM 下不可执行，见 `QualityReportApplierTest` 类注释）⇒ 判定内核用纯函数单测
 * （`RssCheckFailureUnificationTest`），**接线本身**用本文件守护。
 */
class CheckRssSourceServiceWiringTest {

    private fun code(): String {
        val rel = "src/main/java/io/legado/app/service/CheckRssSourceService.kt"
        val f = listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
        return f.readText()
    }

    @Test
    fun failureAttributionDelegatesToSingleSource() {
        val t = code()
        // 归因与分组名必须与书源侧共用同一单源（缺口2 续），不得再自带 when 分支
        assertTrue("归因须委托单源", t.contains("checkFailureGroupName(it)"))
        assertTrue("不得再自带归因 when 分支", !t.contains("is TimeoutCancellationException -> source.addGroup"))
        assertTrue("不得再内联「校验超时」字面量", !t.contains("\"校验超时\""))
    }

    @Test
    fun groupBackfillDelegatesToSharedOrchestration() {
        val t = code()
        assertTrue(
            "须用结果→维度态适配器",
            t.contains("QualityReportApplier.rssResultToDimStates(result)")
        )
        assertTrue(
            "须走唯一编排写组",
            t.contains("QualityReportApplier.applyRssGroupsFromDims(")
        )
        assertTrue(
            "服务侧不得再内联任何分组字面量",
            !Regex("addGroup\\(\"").containsMatchIn(t) && !Regex("removeGroup\\(\"").containsMatchIn(t)
        )
    }

    @Test
    fun suspectSkipIsWired() {
        val t = code()
        // 订阅源侧同样接入底座「存疑」入口：存疑源失败不写失效分组（防误杀）
        assertTrue("须用存疑单源入口", t.contains("SourceQualityChecker.staticSuspectsOf(source)"))
        assertTrue("跳过原因须用同源文案", t.contains("suspectSkipLabel(suspectReasons)"))
    }

    @Test
    fun duplicateMarkerIsClearedEachRound() {
        val t = code()
        // 「重复源」不属「失效」口径 ⇒ removeInvalidGroups() 不会清 ⇒ 必须每轮显式清一次
        assertEquals(
            "须显式清一次「重复源」标记",
            1,
            Regex("source\\.removeGroup\\(SourceCheckGroups\\.RSS_DUPLICATE\\)").findAll(t).count()
        )
        assertTrue("去重标记须取自单源常量", t.contains("addGroup(SourceCheckGroups.RSS_DUPLICATE)"))
    }
}
