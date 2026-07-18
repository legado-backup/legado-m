# spec.md 与 tasks.md 最终审查报告

> **审查时间**：2026-07-18
> **审查范围**：`docs/specs/forks-archive-borrow-implementation/spec.md` + `tasks.md`
> **审查背景**：12 项严重问题（A1-A6 / B1-B5 / C1-C2）全量修复后的最终验证
> **审查方法**：Read 完整文档 + Grep 关键修复点 + Glob 文件路径验证

---

## 一、12 项修复验证结果

### 修复验证总表

| 修复项 | 修复位置（文件+行号） | 修复内容（实际内容） | 验证结果 |
|--------|---------------------|---------------------|---------|
| **A1** ReadRecentBook.kt 不存在 | spec.md:353-355 / tasks.md:134-135, 141 | spec 标注"需先创建 ReadRecentBook.kt 实体 + ReadRecentBookDao.kt DAO + 数据库 Migration"；tasks 1.13 拆分为 1.13.1（实体+DAO）+ 1.13.2（Migration）+ 1.13.3（集成）+ 1.13.4（真机验证） | ✅ 到位 |
| **A2** BaseSearchActivity 不存在 | spec.md:151-156 / tasks.md:22 | spec 标注"本项目基类为 VMBaseActivity（`app/src/main/java/io/legado/app/base/VMBaseActivity.kt`），无 BaseSearchActivity"；tasks 1.1.1 "继承 VMBaseActivity 本项目基类" | ✅ 到位 |
| **A3** cacheFirst 已是 true | spec.md:225-229 / tasks.md:66 | spec 标注"数据层已完成（`RssSource.kt:113` `cacheFirst: Boolean = true` 已是默认值），仅 WebView 层需验证"；tasks 1.5.1 标记 `[x]` 已完成 | ✅ 到位 |
| **A4** 6 个文件路径错误 | spec.md:630-642（附录 E）/ tasks.md:101,119,144-145 等 | 新增附录 §E 对照表；EpubFile/RssFragment/VideoPlayerActivity/ChoiceSpeedDialog/Exo2MediaPlayer 5 个路径已修正；ThemeUtils.kt 路径不完整（仅写 `lib/theme/ThemeUtils.kt`，漏写 `app/src/main/java/io/legado/app/` 前缀） | ⚠️ 部分到位 |
| **A5** sora-editor+markwon 已引入 | spec.md:171,433 / tasks.md:36,302 | spec REQ-P0-002 标注"markwon 核心已实现（`app/build.gradle:329-332`）"；spec REQ-P2-002 标注"sora-editor 已实现（`app/build.gradle:356-358`）"；tasks 1.2.0/3.1.2.0 标记 `[x]` 已实现 | ✅ 到位 |
| **A6** ui/rss/search/+ui/video/ 不存在 | spec.md:152,157 / tasks.md:33,63 | spec 标注"本项目 `ui/rss/` 下无 `search/` 和 `video/` 子目录，实施时需新建"；tasks 1.1/1.4 说明需新建子目录 | ✅ 到位 |
| **B1** ADR-002 与 R22 矛盾 | spec.md:122-124 / tasks.md:18 / design.md:90 | 三处统一为"4 个组按文件隔离原则顺序执行（组间逻辑并行但物理串行，主 Agent 单线程），与 design.md ADR-002 + R22 一致" | ✅ 到位 |
| **B2** ADR-013 遗漏 pureSearch | spec.md:355 / tasks.md:135 / design.md:318 | 三处统一为"数据库迁移范围需包含 pureSearch 字段（与 design.md ADR-013 一致）"；design.md ADR-013 已补充"RSS-B-04 pureSearch 字段（ALTER TABLE rssSource ADD COLUMN pureSearch）" | ✅ 到位 |
| **B3** 文件清单遗漏 | spec.md:628 / tasks.md:19,26-28 | spec 附录 D 第 8 项补充"配套文件修改：strings.xml + AndroidManifest.xml + proguard-rules.pro"；tasks 1.1.5/1.1.6/1.1.7 补充 Manifest/strings/proguard 子任务 | ✅ 到位 |
| **B4** ADR-022 minSdk 矛盾 | spec.md:626 / tasks.md:8 / design.md:487 | 四处统一为"minSdk 23（与 `app/build.gradle:66` 实际一致，与 design.md ADR-022 一致）"；实际 build.gradle:66 确为 `minSdk 23` | ✅ 到位 |
| **B5** ADR-010b 冲突合并策略 | spec.md:627 / tasks.md:9 / design.md:271-276 | design.md ADR-010b 补充"冲突合并策略（基于时间戳）+ 代码借鉴冲突合并策略（本项目优先）+ 回退策略 + 数据加密 + 加密密钥丢失恢复机制（从备份恢复 + 用户提示）"；spec/tasks 一致引用 | ✅ 到位 |
| **C1** P0 范围矛盾 | spec.md:49-55 / tasks.md:17 | 两处统一标注"v5.1 调整说明：analysis-task-priority.md §1.1 表格写 P0=10 是 v5.0 版本，v5.1 调整后 P0=14（升级 4 项 P1→P0）" | ✅ 到位 |
| **C2** P1 包含低于下限任务 | spec.md:413 / tasks.md:264,271,278 | spec §4.2.2 标注"⚠️ C2 标注：REQ-P1-016/017/018 用户价值低于 P1 下限，保持 P1=19 数据不变"；tasks 2.2.3/2.2.4/2.2.5 补充"P1 资格提示" | ✅ 到位 |

### 修复验证汇总

- ✅ 到位：11 项（A1, A2, A3, A5, A6, B1, B2, B3, B4, B5, C1, C2）
- ⚠️ 部分到位：1 项（A4 - ThemeUtils.kt 路径不完整）
- ❌ 未到位：0 项

---

## 二、新矛盾审查

### 新矛盾 1：ThemeUtils.kt 路径在 spec.md 和 tasks.md 中不完整（A4 修复遗留）

| 位置 | 当前内容 | 正确内容 |
|------|---------|---------|
| spec.md 第 641 行（附录 E） | `lib/theme/ThemeUtils.kt` | `app/src/main/java/io/legado/app/lib/theme/ThemeUtils.kt` |
| tasks.md 第 75 行（1.6.2） | `lib/theme/ThemeUtils.kt` | `app/src/main/java/io/legado/app/lib/theme/ThemeUtils.kt` |

**验证证据**：Glob 查询 `lib/theme/ThemeUtils.kt` 返回 `app/src/main/java/io/legado/app/lib/theme/ThemeUtils.kt`，即 spec/tasks 中漏写了 `app/src/main/java/io/legado/app/` 前缀。

**对比**：spec.md 附录 E 中其他 5 个文件路径均使用了完整路径（如 `app/src/main/java/io/legado/app/model/localBook/EpubFile.kt`），仅 ThemeUtils.kt 这一行使用了不完整路径，附录内部不一致。

**影响**：低。实施者可通过 Glob 找到正确文件，但路径不完整违反对照表的准确性要求。

### 新矛盾 2：design.md 多处仍引用 "ThemeColorUtils.kt"（旧描述未更新）

| 位置 | 当前内容 | 应修正为 |
|------|---------|---------|
| design.md 第 89 行（ADR-002 Context） | "ThemeColorUtils.kt 中新增 sanitizeFontColorAgainstSurfaces 方法" | "ThemeUtils.kt 中新增 sanitizeFontColorAgainstSurfaces 方法" |
| design.md 第 100 行（ADR-002 P0 分组） | "THEME-B-02 (字体撞色检测 ThemeColorUtils.kt)" | "THEME-B-02 (字体撞色检测 ThemeUtils.kt)" |
| design.md 第 1023 行 | "THEME-B-02 (字体撞色检测 ThemeColorUtils.kt)" | "THEME-B-02 (字体撞色检测 ThemeUtils.kt)" |
| design.md 第 1146 行 | "ThemeColorUtils（撞色检测）" | "ThemeUtils（撞色检测）" |

**验证证据**：Grep 查询 design.md 中 `ThemeColorUtils` 命中 5 处（第 89/100/872/1023/1146 行），其中第 872 行已修正为正确路径 `app/src/main/java/io/legado/app/lib/theme/ThemeUtils.kt`，其余 4 处仍为旧描述。

**对比**：design.md 内部不一致——第 872 行已使用正确文件名，但其他 4 处仍引用不存在的 `ThemeColorUtils.kt`。

**影响**：低。design.md 第 872 行已明确"实际文件名 ThemeUtils.kt，无 ThemeColorUtils.kt"，实施者可识别正确文件。

### 新矛盾 3：P1 下限数值在 spec.md 和 tasks.md 中微小不一致

| 位置 | P1 下限数值 |
|------|------------|
| spec.md 第 413 行（§4.2.2 C2 标注） | 3.8 |
| tasks.md 第 264/271/278 行（P1 资格提示） | 4.0 |

**验证证据**：
- spec.md：`REQ-P1-016/017/018 用户价值低于 P1 下限（3.8）`
- tasks.md：`用户价值 2.8 低于 P1 下限（4.0）`

**影响**：极低。不影响 P1=19 数据（两处均明确"保持 P1=19 数据不变"），但 P1 下限数值描述不一致。

### 新矛盾审查汇总

- 新矛盾数量：3 个
- 影响等级：均为低/极低（不阻塞 P0 实施）
- 根因：A4 修复时 ThemeUtils.kt 路径补全不彻底 + design.md 旧描述未同步更新

---

## 三、数据一致性审查

### 优先级数据一致性

| 数据项 | spec.md | tasks.md | design.md | 一致性 |
|--------|---------|----------|-----------|--------|
| P0 数量 | 14 | 14 | 14 | ✅ 一致 |
| P1 数量 | 19 | 19 | 19 | ✅ 一致 |
| P2 数量 | 21 | 21 | 21 | ✅ 一致 |
| 合计 | 54 | 54 | 54 | ✅ 一致 |

### ADR 数量验证

- design.md ADR 列表（第 1223-1249 行）：ADR-001~011 + ADR-010a/010b 拆分 + ADR-013~027
- 准确计数：27 个 ADR（ADR-012 已合并到 ADR-011）
- README.md 第 153 行声明：**27 个**
- 验证结果：✅ 一致

### 模块分布一致性

| 模块 | spec.md P0/P1/P2 | tasks.md P0/P1/P2 | 一致性 |
|------|------------------|-------------------|--------|
| RSS | 5/2/3 | 5/2/3 | ✅ |
| EPUB | 2/4/4 | 2/4/4 | ✅ |
| THEME | 2/5/6 | 2/5/6 | ✅ |
| VIDEO | 4/1/0 | 4/1/0 | ✅ |
| DEPS | 1/2/5 | 1/2/5 | ✅ |
| BUILD | 0/5/3 | 0/5/3 | ✅ |
| **合计** | **14/19/21** | **14/19/21** | ✅ |

### 数据一致性结论

- ✅ 优先级数据完全一致（P0=14 / P1=19 / P2=21 / 合计 54）
- ✅ ADR 数量一致（27 个）
- ✅ 模块分布一致

---

## 四、实施模拟（P0 14 项任务）

### 实施模拟总表

| REQ ID | 决策 ID | 任务描述 | 实施前提验证 | 阻塞点 |
|--------|---------|---------|------------|--------|
| REQ-P0-001 | RSS-B-01 | RssSearchActivity | 继承 VMBaseActivity ✅（文件存在）/ 新建 ui/rss/search/ ✅（已标注）/ AndroidManifest.xml ✅（已补充子任务 1.1.5） | 无 |
| REQ-P0-002 | DEPS-B-01 | markwon 3 扩展 | markwon core 已引入 ✅（build.gradle:329-332）/ 仅需补充 3 个扩展 | 无 |
| REQ-P0-003 | THEME-B-01 | 纸墨风格 | PaperInkHelper.kt 零外部依赖 ✅ | 无 |
| REQ-P0-004 | VIDEO-B-01 | VideoBookPreloader | 单例实现 ✅ / 新建 ui/rss/video/ ✅（已标注） | 无 |
| REQ-P0-005 | RSS-E-06 | cacheFirst 默认值 | 数据层已完成 ✅（RssSource.kt:113 = true）/ 仅 WebView 层需验证 ✅ | 无 |
| REQ-P0-006 | THEME-B-02 | 字体撞色检测 | ⚠️ ThemeUtils.kt 路径不完整（实际 `app/src/main/java/io/legado/app/lib/theme/ThemeUtils.kt`） | 无（实施者可通过 Glob 定位） |
| REQ-P0-007 | RSS-B-02 | SourceSelectDialog | BottomSheetDialog ✅ | 无 |
| REQ-P0-008 | RSS-B-03 | SearchBookMergeUtils | 工具类 ✅ | 无 |
| REQ-P0-009 | EPUB-B-01 | EPUB 章节资源索引 | EpubFile.kt 路径正确 ✅（`app/src/main/java/io/legado/app/model/localBook/EpubFile.kt`） | 无 |
| REQ-P0-010 | EPUB-B-02 | EPUB 资源过滤+标题归一化 | 同上 ✅ | 无 |
| REQ-P0-011 | RSS-B-05 | RssFragment openRssSearch 入口 | RssFragment.kt 路径正确 ✅（`app/src/main/java/io/legado/app/ui/main/rss/RssFragment.kt`） | 无 |
| REQ-P0-012 | VIDEO-B-02 | 章节链接缓存+下一集预加载 | chapterLinkCache + preloadNextEpisode ✅ | 无 |
| REQ-P0-013 | VIDEO-E-01 | 视频书 ReadRecentBook 写入 | 需新增 ReadRecentBook 实体+DAO+Migration ✅（已标注）/ Migration 范围含 pureSearch ✅ | 无 |
| REQ-P0-014 | VIDEO-E-02 | ChoiceSpeedDialog 倍速增强 | ChoiceSpeedDialog.kt 路径正确 ✅ / VideoPlayerActivity.kt 路径正确 ✅ | 无 |

### 实施模拟结论

- ✅ 14 项 P0 任务全部无阻塞性问题
- ⚠️ REQ-P0-006（THEME-B-02）存在 ThemeUtils.kt 路径不完整的小问题，但实施者可通过 Glob 定位正确文件，不阻塞实施
- ✅ 所有文件路径验证通过（5 个关键路径已修正）
- ✅ 所有"已实现"标注准确（markwon core + sora-editor）
- ✅ 所有"新建子目录"标注到位（ui/rss/search/ + ui/rss/video/）
- ✅ 所有"配套文件修改"标注到位（AndroidManifest.xml + strings.xml + proguard-rules.pro）

---

## 五、最终结论

### 综合评估

| 评估维度 | 结果 |
|---------|------|
| 12 项修复验证 | 11 项 ✅ 到位 + 1 项 ⚠️ 部分到位（A4 ThemeUtils.kt 路径） |
| 新矛盾数量 | 3 个（均为低/极低影响，不阻塞 P0 实施） |
| 数据一致性 | ✅ 完全一致（P0=14 / P1=19 / P2=21 / 合计 54 / ADR=27） |
| 实施模拟 | ✅ 14 项 P0 任务全部无阻塞性问题 |

### 最终结论

⚠️ **需要小调整后可以进入 P0 实施阶段**

### 建议调整项（不阻塞 P0 启动，可在实施过程中同步修正）

| 调整项 | 位置 | 当前内容 | 建议修正为 | 优先级 |
|--------|------|---------|-----------|--------|
| 调整 1 | spec.md 第 641 行（附录 E） | `lib/theme/ThemeUtils.kt` | `app/src/main/java/io/legado/app/lib/theme/ThemeUtils.kt` | 低 |
| 调整 2 | tasks.md 第 75 行（1.6.2） | `lib/theme/ThemeUtils.kt` | `app/src/main/java/io/legado/app/lib/theme/ThemeUtils.kt` | 低 |
| 调整 3 | design.md 第 89/100/1023/1146 行 | `ThemeColorUtils.kt` | `ThemeUtils.kt`（或保留并标注"实际文件名 ThemeUtils.kt"） | 低 |
| 调整 4 | spec.md 第 413 行 或 tasks.md 第 264/271/278 行 | P1 下限 3.8 vs 4.0 | 统一为 3.8（与 spec.md §附录 B 优先级判定标准一致） | 极低 |

### 进入 P0 实施的可行性

- ✅ **可以进入 P0 实施阶段**：12 项修复中 11 项完全到位，1 项部分到位但不阻塞实施
- ✅ **数据一致性已确认**：spec.md / tasks.md / design.md 三处优先级数据完全一致
- ✅ **实施模拟无阻塞**：14 项 P0 任务全部可启动
- ⚠️ **建议**：在 P0 实施启动前或实施过程中，同步修正上述 4 个小调整项（非阻塞，可在 REQ-P0-006 实施时一并处理）

---

## 附录：审查工具与证据

### A. 审查工具使用

| 工具 | 用途 | 调用次数 |
|------|------|---------|
| Read | 读取 spec.md / tasks.md / design.md / RssSource.kt / build.gradle / ThemeUtils.kt 完整内容 | 8 |
| Grep | 验证 ADR 引用 / ThemeUtils 引用 / 关键修复点 | 4 |
| Glob | 验证文件路径是否存在（VMBaseActivity / BaseSearchActivity / ReadRecentBook / EpubFile / RssFragment / ChoiceSpeedDialog / Exo2MediaPlayer / VideoPlayerActivity / ThemeUtils / ui/rss 子目录） | 7 |

### B. 关键文件路径验证证据

| 文件 | 验证结果 |
|------|---------|
| `app/src/main/java/io/legado/app/base/VMBaseActivity.kt` | ✅ 存在（本项目基类） |
| `BaseSearchActivity.kt` | ✅ 不存在（A2 修复正确） |
| `app/src/main/java/io/legado/app/data/entities/ReadRecentBook.kt` | ✅ 不存在（本项目，A1 修复正确） |
| `temp/forks-comparison/legado-archive/.../ReadRecentBook.kt` | ✅ 存在（fork 仓库，A1 修复正确） |
| `app/src/main/java/io/legado/app/data/entities/RssSource.kt:113` | ✅ `var cacheFirst: Boolean = true`（A3 修复正确） |
| `app/build.gradle:329-332` | ✅ markwon core+image-glide+tables+html（A5 修复正确） |
| `app/build.gradle:356-358` | ✅ soraEditor BOM+core+language.textmate（A5 修复正确） |
| `app/build.gradle:66` | ✅ `minSdk 23`（B4 修复正确） |
| `app/src/main/java/io/legado/app/model/localBook/EpubFile.kt` | ✅ 存在（A4 路径正确） |
| `app/src/main/java/io/legado/app/ui/main/rss/RssFragment.kt` | ✅ 存在（A4 路径正确） |
| `app/src/main/java/io/legado/app/ui/video/VideoPlayerActivity.kt` | ✅ 存在（A4 路径正确） |
| `app/src/main/java/io/legado/app/help/gsyVideo/ChoiceSpeedDialog.kt` | ✅ 存在（A4 路径正确） |
| `app/src/main/java/io/legado/app/help/gsyVideo/Exo2MediaPlayer.kt` | ✅ 存在（A4 路径正确） |
| `app/src/main/java/io/legado/app/lib/theme/ThemeUtils.kt` | ✅ 存在（A4 路径不完整，实际路径含 `app/src/main/java/io/legado/app/` 前缀） |
| `app/src/main/java/io/legado/app/ui/rss/search/` | ✅ 不存在（A6 修复正确，需新建） |
| `app/src/main/java/io/legado/app/ui/rss/video/` | ✅ 不存在（A6 修复正确，需新建） |

### C. ADR 数量验证证据

design.md 第 1223-1249 行 ADR 列表完整计数：
- ADR-001, 002, 003, 004, 005, 006, 007, 008, 009, 010a, 010b, 011, 013, 014, 015, 016, 017, 018, 019, 020, 021, 022, 023, 024, 025, 026, 027
- 合计：27 个 ✅（ADR-012 已合并到 ADR-011，ADR-010 已拆分为 010a/010b）

---

**审查报告完成**。12 项修复中 11 项完全到位，1 项部分到位（A4 ThemeUtils.kt 路径不完整）。发现 3 个新矛盾（均为低/极低影响）。数据一致性完全确认。14 项 P0 任务实施模拟无阻塞。**建议小调整后进入 P0 实施阶段**（调整项非阻塞，可在实施过程中同步修正）。
