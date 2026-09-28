// G-12 自检样本（违例侧）：模拟「数据库版本升到 999，但既无 schema 导出、也无迁移链覆盖、
// 更无覆盖安装证据」的**缺证据**违例。
//
// ⚠ 2026-09-28 修正（G-15 元门禁发现 G-12 probe 失效）：原样本 version=111 且
// `dbmig_violation_schemas/` 内**恰好**提供了 111 的 schema ⇒ 组装的 probe 命令
// （未传 `--base`）实际扫到真实仓库的 ②迁移链与 ③evidence（111 条目本就在 W3 落地）
// ⇒ 三项全 PASS、违例未被拦住（exit 0）。改为 **version=999**：本样本 schemas 目录与真实仓库
// 都不存在 999 的 schema ⇒ ① 必然 FAIL ⇒ probe 恢复「违例 exit 1」语义。
//
// 用途：audit_db_migration.py --app-db <本文件> --schemas-dir <dbmig_violation_schemas> 的
// 「① 违例 ⇒ exit 1」probe（G-15 自检用）。
// 注意：位于 ai_tests/testsets/ 下，不参与 App 编译（非源码目录）。
package ai_tests.testsets.selfcheck

import androidx.room.Database
import androidx.room.RoomDatabase

@Database(
    version = 999,
    entities = []
)
abstract class DbmigViolationAppDatabase : RoomDatabase()