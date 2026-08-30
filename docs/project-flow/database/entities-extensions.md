# 扩展实体清单（v90-v108 新增 35 实体）

> **权威源**：`AppDatabase.kt` L125-147（@Database entities 注册）+ `app/schemas/io.legado.app.data.AppDatabase/108.json`（56 表 schema，全量 DDL 以此为准）。本文为速查索引，字段级细节以实体源码为准。
>
> **归属版本**：以 `DatabaseMigrations.kt` 手动迁移链（migration_89_90 … migration_107_108）核实。核心 21 实体见 [entities.md](entities.md)。

## 一、AI 能力（12 个）

| 实体类 | 表名 | 用途 | 版本 |
|--------|------|------|------|
| AiAgentSession | ai_agent_sessions | AI 智能体会话（目标/任务/步骤/上下文 JSON） | v106 |
| AiAgentJob | ai_agent_jobs | AI 智能体任务队列与执行状态 | v106 |
| AiAgentTrace | ai_agent_traces | AI 智能体执行轨迹追踪 | v106 |
| AiMemoryItem | ai_memory_items | AI 长期记忆条目（SPO 三元组 + 置信度/重要性，fingerprint 唯一索引） | v106 |
| AiMemoryFragment | ai_memory_fragments | AI 记忆片段 | v106 |
| AiMemoryItemFts | ai_memory_items_fts | 记忆条目 FTS4 全文索引（虚拟表） | v106 |
| AiMemoryFragmentFts | ai_memory_fragments_fts | 记忆片段 FTS4 全文索引（虚拟表） | v106 |
| AiImageGroup | ai_image_groups | AI 绘画分组 | v106 |
| AiGeneratedImage | ai_generated_images | AI 生成图片记录 | v106 |
| BookAiChapterSummary | book_ai_chapter_summaries | AI 章节摘要缓存 | v106 |
| BookCharacter | book_characters | 书籍角色档案 | v106 |
| BookCharacterRelation | book_character_relations | 角色关系图谱 | v106 |

> 注：`AiMemoryItemFts` / `AiMemoryFragmentFts` 与本体实体同文件（`AiMemoryFts.kt` 单文件双实体）。

## 二、朗读 / BGM（7 个）

| 实体类 | 表名 | 用途 | 版本 |
|--------|------|------|------|
| AiReadAloudRoleCache | ai_read_aloud_role_caches | AI 朗读角色缓存 | v106 |
| ReadAloudBgmGroup | read_aloud_bgm_groups | 朗读背景音乐分组 | v106 |
| ReadAloudBgmTrack | read_aloud_bgm_tracks | BGM 音轨 | v106 |
| ReadAloudBgmAssignmentCache | read_aloud_bgm_assignment_caches | BGM 分配缓存（章节→音轨映射） | v106 |
| ReadAloudSpeakerGroup | read_aloud_speaker_groups | 朗读发言人分组 | v106 |
| ReadAloudSpeakerGroupItem | read_aloud_speaker_group_items | 发言人分组明细 | v106 |
| AiReadAloudUsageRecord | ai_read_aloud_usage_records | AI 朗读用量记录 | v106 |

## 三、阅读增强（9 个）

| 实体类 | 表名 | 用途 | 版本 |
|--------|------|------|------|
| BookHighlight | highlights | 手动划线高亮（借鉴阅读T） | v92 |
| ReadRecordDetail | readRecordDetail | 阅读记录详情（四复合 PK：设备+书名+作者+日期） | v90 |
| PlayHistory | playHistories | 播放历史（复合 PK：articleUrl+videoUrl，进度恢复） | v101 |
| ReadRecordDaily | readRecordDaily | 每日阅读时长统计（PK：date） | v105 |
| ReadRecentBook | readRecentBooks | 最近阅读书籍（PK：bookUrl） | v105 |
| ParagraphRule | paragraph_rules | 智能分段规则（JS 脚本） | v105 |
| BookParagraphRule | book_paragraph_rules | 书籍↔分段规则绑定（FK CASCADE） | v105 |
| ParagraphRuleVar | paragraph_rule_vars | 分段规则变量（FK CASCADE） | v105 |
| ReadMenuCustomButton | read_menu_custom_buttons | 阅读菜单自定义按钮（JS 扩展） | v105 |

## 四、系统管理（7 个）

| 实体类 | 表名 | 用途 | 版本 |
|--------|------|------|------|
| CoverGalleryGroup | cover_gallery_groups | 封面画廊分组 | v90 |
| CoverGalleryImage | cover_gallery_images | 封面画廊图片（FK CASCADE） | v90 |
| AutoTaskRule | auto_task_rules | 自动任务规则（cron 调度 + JS 执行；源码在 `model/AutoTaskRule.kt`，不在 data/entities/） | v91 |
| SourceRecycleBin | source_recycle_bin | 源回收站（删除快照 + 过期时间，type/key 有索引） | v102 |
| UrlRecord | url_records | 网址访问记录（domain/timestamp 索引） | v103 |
| SourceGroupCover | source_group_covers | 源分组封面（复合 PK：kind+groupName） | v104 |
| DownloadTaskEntity | download_tasks | 下载任务持久化（v107 创建，v108 重建清除 errorMsg/resumePointJson/segmentsJson 僵尸列） | v107-v108 |

## 计数核对

12（AI 能力）+ 7（朗读/BGM）+ 9（阅读增强）+ 7（系统管理）= **35** ✓
35（新增）+ 21（核心，见 entities.md）= **56** = AppDatabase.kt 注册实体数 = schemas/108.json 表数 ✓

| 版本 | 新增表数 | 迁移 |
|------|---------|------|
| v90-v92 | 5（画廊 2 + readRecordDetail + auto_task_rules + highlights） | migration_89_90 / 90_91 / 91_92 |
| v101-v104 | 4（playHistories + source_recycle_bin + url_records + source_group_covers） | migration_100_101 … 103_104 |
| v105 | 6（阅读增强 6 表） | migration_104_105 |
| v106 | 19（AI 能力 12 + 朗读 7，含 2 张 FTS4 虚拟表） | migration_105_106 |
| v107-v108 | 1（download_tasks 创建+重建） | migration_106_107 / 107_108 |
