// G-12 自检样本（违例侧）：模拟「数据库版本升到 999，但既无 schema 导出、也无迁移链覆盖、
// 更无覆盖安装证据」的**缺证据**违例。
//
// ⚠ 2026-09-28 修正（两处，缺一不可）：
//  ① 样本 `version` 由 111 改为 **999**：原 111 时 `dbmig_violation_schemas/` 内**恰好**提供了
//     111 的 schema，且真实仓库的 `migration_110_111` 与 evidence 的 111 条目本就在 W3 落地
//     ⇒ ①②③ 三项全 PASS、违例未被拦住（exit 0）。改为 999 后三者都不可得 ⇒ ① 必然 FAIL。
//  ② 违例 probe 的**基准必须不可读**（registry 已显式传 `--base` = git 空树
//     `4b825dc642cb6eb9a060e54bf8d69288fbee4904`）。原因：`audit_db_migration.py` 的 `--base`
//     默认 `HEAD`，会**读取同一路径在 HEAD 的内容**；本样本一旦被 `git add -f` 跟踪（19618cc 即如此）
//     ⇒ 基准版本 == 当前版本 ⇒ 被判「无版本变更」⇒ probe 假 PASS（G-15 实测复现）。
//     用空树作基准使 probe 与「样本是否被跟踪」**解耦**；若日后又改回默认基准，本样本必须保持**未跟踪**。
//
// 用途：audit_db_migration.py --base <空树> --app-db <本文件> --schemas-dir <dbmig_violation_schemas>
// 的「① 违例 ⇒ exit 1」probe（G-15 自检用）。
// 注意：位于 ai_tests/testsets/ 下，不参与 App 编译（非源码目录）。
package ai_tests.testsets.selfcheck

import androidx.room.Database
import androidx.room.RoomDatabase

@Database(
    version = 999,
    entities = []
)
abstract class DbmigViolationAppDatabase : RoomDatabase()