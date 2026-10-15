package io.legado.app.data.dao

import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * B25：`data/dao` 零调用窄查询退役 + **活替代者存活** 的双侧守护。
 *
 * 为什么必须双侧（实证教训）：本轮删除时曾把「活替代者 `successCandidatesByChapterContent`」
 * 与被删的 `latestSuccessByChapterContent` 一起误删（两者 SQL 仅 `LIMIT` 不同），
 * 靠编译期才发现 ⇒ 单侧断言（只证"已删"）无法防此类回归，故同时锁住替代者仍在。
 *
 * 为什么只能文本探针：`@Dao` 接口方法必须由 Room 生成实现、且需 appCtx 构造数据库，
 * 纯 JVM 无法行为化「方法不存在」这一命题 ⇒ 登记 `empty_test_allowlist.json` 的 `exception`。
 */
class RetiredDaoQueryTest {

    private fun code(rel: String): String {
        val f = listOf(File(rel), File("../app/$rel"), File("app/$rel")).firstOrNull { it.isFile }
        if (f == null) throw AssertionError("找不到源文件 $rel（工作目录 ${File(".").absolutePath}）")
        return f.readText().replace("\r\n", "\n")
    }

    private val urlRecordDao by lazy { code("src/main/java/io/legado/app/data/dao/UrlRecordDao.kt") }
    private val roleCacheDao by lazy { code("src/main/java/io/legado/app/data/dao/AiReadAloudRoleCacheDao.kt") }
    private val characterDao by lazy { code("src/main/java/io/legado/app/data/dao/BookCharacterDao.kt") }
    private val castingDao by lazy { code("src/main/java/io/legado/app/data/dao/TtsCastingTemplateDao.kt") }

    @Test
    fun retiredNarrowQueriesDoNotComeBack() {
        // 退役项：全仓零调用且已有活替代 ⇒ 不得回潮（回潮即「同一判定两处实现」）
        listOf(
            urlRecordDao to "fun flowByDomain(",
            urlRecordDao to "fun flowBySourceName(",
            urlRecordDao to "fun flowByMethod(",
            urlRecordDao to "fun flowByStatus(",
            urlRecordDao to "fun getBySourceName(",
            roleCacheDao to "fun latestByChapter(",
            roleCacheDao to "fun latestSuccessByChapterContent(",
            characterDao to "fun flowCharacters(",
            characterDao to "fun flowRelations(",
            characterDao to "fun deleteCharacterById(",
            castingDao to "fun flowById(",
            castingDao to "fun deleteUserTemplates("
        ).forEach { (src, decl) ->
            assertFalse("零调用窄查询已退役，不得回潮：$decl", src.contains(decl))
        }
    }

    @Test
    fun liveReplacementsOfRetiredQueriesStayIntact() {
        // 活替代者：删除时必须留存的"另一半"，被误删即此处红
        assertTrue("网址记录的组合筛选超集须保留", urlRecordDao.contains("fun flowFilter("))
        assertTrue("域/来源名去重列表供筛选下拉使用，须保留", urlRecordDao.contains("fun flowAllDomains("))
        assertTrue("按域直查（List 版）在用，须保留", urlRecordDao.contains("fun getByDomain(domain: String)"))
        assertTrue("按章节取可用缓存须保留", roleCacheDao.contains("fun latestUsableByChapter("))
        assertTrue("按内容取成功候选（供择优）须保留", roleCacheDao.contains("fun successCandidatesByChapterContent("))
        assertTrue("角色 List 版列表查询须保留", characterDao.contains("fun characters(bookUrl: String)"))
        assertTrue("关系 List 版列表查询须保留", characterDao.contains("fun relations(bookUrl: String)"))
        assertTrue("级联删除角色（事务）须保留", characterDao.contains("fun deleteCharacterWithRelations("))
        assertTrue("模板按 id 直取（suspend 版）须保留", castingDao.contains("fun get(id: String)"))
    }
}
