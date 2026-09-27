package io.legado.app.data.dao

import java.io.File
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * W4 / REQ-18：`RssReadRecordDao` 新增接口的**契约**不变量（Room 编译期约束 + 语义）。
 *
 * Room 对 `@Query` 的校验在编译期：INSERT 查询函数只能返回 void/long ⇒ `INSERT…SELECT` 不能回传行数，
 * 新增数须由调用方以 `countRecords` 差值统计（见 `RssReadRecordMarker`）。若有人把返回类型改回 `Int`，
 * 编译即失败；此处把这个约束**写进测试注释与断言**，避免下次重复踩坑。
 */
class RssReadRecordDaoContractTest {

    private val dao by lazy {
        listOf(
            File("src/main/java/io/legado/app/data/dao/RssReadRecordDao.kt"),
            File("../app/src/main/java/io/legado/app/data/dao/RssReadRecordDao.kt"),
            File("app/src/main/java/io/legado/app/data/dao/RssReadRecordDao.kt")
        ).first { it.isFile }.readText()
            // 工作副本可能是 CRLF（Windows 检出）⇒ 归一到 LF，保证多行断言稳定
            .replace("\r\n", "\n")
    }

    @Test
    fun insertMissingBackfillReturnsVoid() {
        assertTrue(
            "INSERT…SELECT 必须返回 void（Room 限制：INSERT 只能 void/long）",
            dao.contains("fun insertMissingAsReadByOrigins(origins: List<String>, now: Long)\n")
        )
    }

    @Test
    fun scopedUpdateReturnsAffectedRows() {
        assertTrue(
            "UPDATE 可返回受影响行数（回执用）",
            dao.contains("fun markAllReadByOrigins(origins: List<String>): Int")
        )
    }

    @Test
    fun backfillOnlyTouchesArticlesWithoutRecord() {
        assertTrue("补记录须带 not exists 守卫（幂等，不重复插入）", dao.contains("not exists"))
        assertTrue("补记录须限定 origin 集合（范围语义）", dao.contains("where origin in (:origins) and not exists"))
    }
}