# 发现/订阅源文件夹封面替换 — 需求规格

> 状态：🔄 设计中 | 创建日期：2026-08-16

## Intent

用户提出：最新版本改动的「发现」和「订阅源」布局，没有学到书架布局文件夹的精髓——**可替换文件夹封面**。书架文件夹（`BookGroup` 实体 + `GroupEditDialog`）支持长按选图替换封面，而发现/订阅源文件夹（`SourceFolderAdapter` 数据项仅是 `List<String>`）没有任何封面加载逻辑。

本次目标：让发现页与订阅源主页的文件夹视图具备与书架一致的封面替换能力，并将两个管理页改为固定平铺。

## Scope

### 做什么

1. 新增 Room 实体 `SourceGroupCover`（kind + groupName 复合主键 + cover 字段），DB version 103→104 手动迁移
2. `SourceFolderAdapter` 数据项从 `String` 改造为 `FolderItem(groupKey, groupLabel, isSpecial)`，convert 中按 kind+groupKey 加载封面
3. 文件夹卡片长按弹菜单：「选图」「恢复默认封面」（交互对齐书架 `GroupEditDialog`）
4. 选图复制到 `externalFiles/covers/`（MD5 命名，与书架 `BookGroup.cover` 同目录），写入 `SourceGroupCover.cover`；恢复默认 = 删除该行记录
5. 特殊分组（全部分组/未分组/各类型 folder）用固定英文 key 存表，支持换封面
6. 书源管理页（BookSourceActivity）与订阅源管理页（RssSourceActivity）改为固定平铺，去掉文件夹视图；`showConfigDialog` 新增 `showGroupStyle` 参数，管理页隐藏「分组样式」选项
7. 更新 `docs/INDEX.md`、`app/src/main/assets/updateLog.md`

### 不做什么

- ❌ 不改书架分组（BookGroup）任何行为
- ❌ 不改分组管理对话框（GroupManageDialog）
- ❌ 不新增分组增删改能力（仅封面替换）
- ❌ 不改变 `sourceGroupStyle` 全局配置语义（仍控制发现页/订阅源主页的文件夹模式）
- ❌ 不做封面图片压缩/裁剪（沿用书架逻辑原样复制）
- ❌ 不做云端同步（纯本地数据）

## Approach

### Selected Approach

**独立分组封面表 + 双命名空间（kind 字段）+ FolderItem 数据项改造**

- 新建 `SourceGroupCover(kind, groupName, cover)` 表，复合主键 `(kind, groupName)`，kind 取 `"book"`（发现页）/ `"rss"`（订阅源页）
- `SourceFolderAdapter` 数据项改造成 `FolderItem(groupKey, groupLabel, isSpecial)`，`groupKey` 是稳定表 key（真实分组=分组名，特殊分组=固定英文 key），`groupLabel` 是本地化显示文本
- convert 中按 kind+groupKey 查询封面，非空则 Glide 加载到 `iv_folder_cover`，为空则保持渐变背景 + 首字叠加
- 长按菜单「选图/恢复默认封面」：选图复制到 `externalFiles/covers/` → `upsert`；恢复默认 → `delete`
- 管理页：`isFolderViewMode` 强制 `false`，不进入文件夹模式；`showConfigDialog` 加 `showGroupStyle` 参数隐藏分组样式行

### Alternatives Considered

| 方案 | 描述 | 否决理由 |
|------|------|---------|
| 单表不含 kind | 仅 groupName 主键 + cover，书源与 RSS 同名分组共享一个封面 | 发现页与订阅源页是两套独立分组命名空间，同名分组（如「漫画」）需各自独立封面；合并会互相覆盖 |
| 两张独立表 | bookSourceGroupCover 与 rssSourceGroupCover 各一张表 | 语义最清晰但冗余较多；DAO/迁移/注册逻辑翻倍，kind 单表足够表达 |
| 不建表、存 AppConfig JSON | 用 AppConfig 持久化 groupKey→cover 映射 | 失去 Room 的响应式 Flow 能力，无法在卡片刷新时自动更新；JSON 键值难维护 |
| 复用 BookGroup 表 | 在书架分组表上加 kind 字段扩展 | 书架与源分组语义完全不同，污染现有实体与 onOpen 兜底插入逻辑 |
| 数据项保持 String 不改 | 用「分组名+kind」字符串拼接传参 | 特殊分组显示文本是本地化 R.string，切语言后表 key 漂移丢失封面；需稳定 key 与显示文本分离 |

### Drawbacks

| 缺点 | 说明 | 接受理由 |
|------|------|---------|
| 数据库版本升级 v104 | 需手动 Migration + 真机覆盖安装验证 | 已有成熟范例（migration_102_103），成本可控 |
| 特殊分组固定 key 需同步维护 | 新增类型 folder 时需在映射处补充 key | 类型集合稳定（书源 6 类/RSS 3 类），且集中在一个映射函数管理 |
| 管理页失去文件夹视图 | 用户需滚动长列表管理源 | 用户明确要求「固定平铺」，管理页重点在增删改而非浏览 |
| adapter 数据项类型变更 | 涉及 ExploreFragment/RssFragment/BookSourceActivity/RssSourceActivity 四处调用点 | 变更集中在 adapter 接口，改动量可控 |

### Prior Art

- 书架文件夹封面替换：`BookGroup.cover` + `GroupEditDialog.kt` + `GroupCover`（BookshelfScreen.kt:349-383），选图复制到 `externalFiles/covers/` MD5 命名——本次完全复用该文件处理与存储约定
- 数据库手动迁移范例：`migration_102_103`（DatabaseMigrations.kt:791-816）
- Glide 封面加载：`BookCover.load(context, cover).into(view)`（BookshelfScreen.kt:379）

## Requirements

### R1 分组封面表

- R1.1 新增实体 `SourceGroupCover`：`kind: String` + `groupName: String` 复合主键 + `cover: String?`（null=默认）
- R1.2 DB version 103→104，手动 Migration 创建 `source_group_covers` 表 + 复合主键索引，注册到 `DatabaseMigrations.kt` migrations 数组
- R1.3 导出新 schema `104.json`

### R2 DAO

- R2.1 `getSourceGroupCover(kind, groupName)` 查询单条（suspend 或 Flow）
- R2.2 `upsert(...)` 插入/更新
- R2.3 `delete(kind, groupName)` 删除

### R3 Adapter 数据项与封面加载

- R3.1 `SourceFolderAdapter` 数据项从 `String` 改为 `FolderItem(groupKey, groupLabel, isSpecial)`；diffItemCallback 按 groupKey 比较
- R3.2 adapter 增加 `kind: String` 参数
- R3.3 convert 中查询 kind+groupKey 封面，cover 非空则 Glide 加载到 `iv_folder_cover`，为空保持渐变背景+首字
- R3.4 `groupKey` 稳定规则：真实分组=分组名；特殊分组=固定英文 key（`all_groups`/`no_group`/`type_text`/`type_audio`/`type_image`/`type_file`/`type_video`/`type_web`）

### R4 长按交互

- R4.1 文件夹卡片长按弹菜单：「选图」「恢复默认封面」
- R4.2 选图：`HandleFileContract`(IMAGE) → 复制到 `externalFiles/covers/`（MD5 命名）→ `upsert(kind, groupKey, cover)` → 刷新该项
- R4.3 恢复默认封面：`delete(kind, groupKey)` → 刷新该项

### R5 特殊分组

- R5.1 特殊分组同样存表（用固定英文 key 作 groupName）
- R5.2 展示时 `groupLabel` 用本地化 R.string（切语言不丢封面）

### R6 管理页固定平铺

- R6.1 BookSourceActivity：`isFolderViewMode` 强制 false，不进入文件夹模式，不调用 upFolderView/onFolderClick
- R6.2 RssSourceActivity：同上
- R6.3 `showConfigDialog` 新增 `showGroupStyle: Boolean = true` 参数；管理页传 false 隐藏「分组样式」行，其余选项保留
- R6.4 发现页（ExploreFragment）与订阅源主页（RssFragment）仍按 `sourceGroupStyle` 显示文件夹视图

### R7 文档同步

- R7.1 更新 `docs/INDEX.md`
- R7.2 更新 `app/src/main/assets/updateLog.md`

## Scenarios

### S1 发现页分组换封面（正常路径）

1. 用户打开「发现」页，分组模式下看到文件夹卡片
2. 长按某分组文件夹 → 弹菜单「选图/恢复默认封面」
3. 点「选图」→ 系统图库选择 → 选一张图
4. 图片复制到 `externalFiles/covers/`（MD5 命名），`source_group_covers` 插入 `('book', '玄幻', 'xxx.jpg')`
5. 卡片 `iv_folder_cover` 立即刷新显示该图，`tv_folder_initial` 首字不再可见（或按视觉决策叠加）
6. 重启 App 后封面持久保留

### S2 订阅源页同名分组独立封面

1. 发现页「漫画」分组设封面 A，订阅源页「漫画」分组设封面 B
2. 两页各自显示 A / B，互不覆盖

### S3 恢复默认封面

1. 长按已换封面的文件夹 → 弹菜单 → 点「恢复默认封面」
2. `delete(kind, groupKey)`，卡片回到渐变背景 + 首字叠加

### S4 特殊分组换封面

1. 长按「全部分组」文件夹 → 选图 → 封面存 `('book', 'all_groups', ...)`
2. 切换语言（如中→英）后，「全部分组」显示为 "All Groups" 但仍保留封面（key 未变）

### S5 管理页平铺

1. 用户进入书源管理页（`sourceGroupStyle` 非 0）
2. 页面固定平铺显示全部源，不再显示文件夹；配置对话框无「分组样式」行
3. 发现页文件夹视图不受影响

### S6 覆盖安装迁移

1. 已装 v103 数据库的 App 覆盖安装 v104 新版
2. `source_group_covers` 表自动创建，原数据无损，App 正常启动