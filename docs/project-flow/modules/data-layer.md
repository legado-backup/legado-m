# 数据层模块

> Room 数据库层索引页——**56 个实体、1 个视图（BookSourcePart）、43 个 DAO、版本 108**（以 AppDatabase.kt version 字段为准）。
>
> 详细内容见 database/ 三件套：[overview.md](../database/overview.md)（总览/迁移策略）、[entities.md](../database/entities.md)（核心 21 实体字段）、[tables.md](../database/tables.md)（核心 21 表 DDL）、[entities-extensions.md](../database/entities-extensions.md)（新增 35 实体清单）。

---

## 1. 结构与计数

```kotlin
// AppDatabase.kt:125-147（@Database 声明，权威定义处）
@Database(
    version = 108,
    exportSchema = true,
    entities = [ /* 56 个实体类：核心 21（Book/BookSource/BookChapter/…）+ 扩展期 35（AI 能力/朗读/阅读增强/系统管理） */ ],
    views = [BookSourcePart::class],
    autoMigrations = [ /* v43→v89 共 46 步，5 步带 spec */ ]
)
abstract class AppDatabase : RoomDatabase() {
    abstract val bookDao: BookDao          // 共 43 个 abstract dao 声明（L212 起）
    // ...
}

// 全局单例（AppDatabase.kt:116-123）
val appDb by lazy {
    Room.databaseBuilder(appCtx, AppDatabase::class.java, AppDatabase.DATABASE_NAME)
        .fallbackToDestructiveMigration(false, 1, /* ... 9 */)
        .addMigrations(*DatabaseMigrations.migrations)   // 手动迁移链 v10→v43、v89→v108
        .allowMainThreadQueries()
        .addCallback(AppDatabase.dbCallback)
        .build()
}
```

- 实体注册权威源：`AppDatabase.kt` L125-147；全量表 DDL：`app/schemas/io.legado.app.data.AppDatabase/108.json`（56 张表）
- 幽灵条目（存在于源码、未注册 @Database、无数据库表）：`BookChapterReview`、`ReplaceBook`、`ReadRecordShow`（DAO 查询映射类）

## 2. 实体与表

| 内容 | 位置 |
|------|------|
| 核心 21 实体字段详解（BookSource/Book/SearchBook/BookChapter/ReplaceRule/RssSource 及 5 组规则） | [entities.md](../database/entities.md) |
| v90-v108 新增 35 实体（AI 能力 12 / 朗读 7 / 阅读增强 9 / 系统管理 7，含归属版本） | [entities-extensions.md](../database/entities-extensions.md) |
| 核心 21 表完整 DDL + 新增表速览（highlights/playHistories/source_recycle_bin/ai_memory_items/download_tasks 摘要） | [tables.md](../database/tables.md) |
| 核心接口（BaseBook/BaseSource）与 BookType 位标志、BookGroup 内置分组常量 | [overview.md](../database/overview.md) |

核心 ER 关系：`books ←CASCADE— chapters`、`book_sources ←CASCADE— searchBooks`（仅此两处数据库级外键），其余为逻辑关联（books.group ↔ book_groups 位掩码、readRecord/bookmarks 按 bookName 等），完整 ER 图见 [overview.md](../database/overview.md#实体关系总览)。

## 3. DAO 层

43 个 DAO 位于 `app/src/main/java/io/legado/app/data/dao/`。设计模式（详见 [overview.md#dao-列表](../database/overview.md#dao-列表)）：

- 响应式查询返回 `Flow<T>`，UI 层自动感知变化
- 核心实体写操作使用 `OnConflictStrategy.REPLACE`
- 批量操作使用 `@Insert` / `@Update` 可变参数

## 4. 迁移

迁移链三阶段：手动 Migration（v10→v43，32 步）→ AutoMigration（v43→v89，46 步含 5 个 spec）→ 手动 Migration（v89→v108，19 步，`runCatching` + `AppLog` 容错）。v105→v108（migration_105_106 / 106_107 / 107_108）均已存在于 `DatabaseMigrations.kt`。

迁移模式、破坏性变更三步法与 Schema 校验规则详见 [overview.md#迁移策略](../database/overview.md#迁移策略)。

## 5. TypeConverter 与索引

- 规则字段（SearchRule/BookInfoRule/ContentRule 等）以 JSON 存储，通过 `@TypeConverter` 序列化（使用项目全局单例 `GSON`，非 `Gson()`）；涉及 BookSource 5 个规则字段、Book.variable、RssSource 规则字段等
- 索引设计总览（books 唯一索引 name+author、chapters 复合索引等 13 项）见 [tables.md#3-索引设计总览](../database/tables.md#3-索引设计总览)

## 6. 相关代码锚点

| 功能 | 文件 | 行号 |
|------|------|------|
| @Database 声明（56 实体 + 1 视图 + autoMigrations） | [AppDatabase.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/data/AppDatabase.kt) | L125-208 |
| appDb 全局单例 | [AppDatabase.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/data/AppDatabase.kt) | L116-123 |
| DAO 抽象方法声明 | [AppDatabase.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/data/AppDatabase.kt) | L210 起 |
| 手动迁移链（migrations 数组） | [DatabaseMigrations.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/data/DatabaseMigrations.kt) | L14-30 |
| 实体目录 | [data/entities/](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/data/entities) | — |
| DAO 目录 | [data/dao/](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/data/dao) | — |
| Schema v108（56 表） | [108.json](file:///f:/myself/github/WeAgentChat/temp/legado/app/schemas/io.legado.app.data.AppDatabase/108.json) | — |
