# 发现/订阅源文件夹封面替换 — 任务清单

> 状态：🔄 设计中 | 创建日期：2026-08-16

## 1. 数据层

- [ ] 1.1 新增实体 `SourceGroupCover.kt`（kind+groupName 复合主键 + cover + 索引 + KIND 常量）
- [ ] 1.2 新增 `SourceGroupCoverDao.kt`（getSourceGroupCover / upsert / delete）
- [ ] 1.3 `AppDatabase.kt`：version 103→104、注册 sourceGroupCoverDao、更新版本注释
- [ ] 1.4 `DatabaseMigrations.kt`：新增 migration_103_104（runCatching + CREATE TABLE + 索引 + AppLog）+ 注册进 migrations 数组
- [ ] 1.5 编译导出 schema 104.json

## 2. Adapter 改造

- [ ] 2.1 `SourceFolderAdapter.kt`：数据项 String → `FolderItem(groupKey, groupLabel, isSpecial)`，diff 按 groupKey
- [ ] 2.2 adapter 构造增加 `kind: String` 参数
- [ ] 2.3 convert 封面加载：查询 kind+groupKey → cover 非空 Glide 加载到 iv_folder_cover + 隐藏首字；为空恢复渐变+首字
- [ ] 2.4 长按菜单：「选图」「恢复默认封面」；选图走 HandleFileContract + 复制到 externalFiles/covers/ + upsert；恢复默认走 delete；均刷新该项
- [ ] 2.5 特殊分组 key 映射函数（R.string → 固定英文 key）

## 3. 调用点适配

- [ ] 3.1 `ExploreFragment.kt`：adapter 传 kind="book"，upFolderView 组装 FolderItem
- [ ] 3.2 `RssFragment.kt`：adapter 传 kind="rss"，upFolderView 组装 FolderItem
- [ ] 3.3 `BookSourceActivity.kt`：isFolderViewMode 强制 false、去掉文件夹分支、showGroupStyle=false
- [ ] 3.4 `RssSourceActivity.kt`：同上
- [ ] 3.5 `showConfigDialog` 增加 `showGroupStyle: Boolean = true`，false 时隐藏 spGroupStyle 行

## 4. 验证

- [ ] 4.1 编译通过（./gradlew assembleAppDebug）
- [ ] 4.2 单元测试（./gradlew test）不回归
- [ ] 4.3 真机验证：发现页分组/特殊分组换封面 + 恢复默认 + 重启持久保留
- [ ] 4.4 真机验证：订阅源页同名分组独立封面
- [ ] 4.5 真机验证：管理页固定平铺 + 配置对话框无分组样式行 + 发现页文件夹不受影响
- [ ] 4.6 真机验证：v103 覆盖安装 v104 迁移无损

## 5. 文档同步

- [ ] 5.1 更新 `app/src/main/assets/updateLog.md`
- [ ] 5.2 更新 `docs/INDEX.md`（移动到「进行中的工作 → 开发中/已完成」）
- [ ] 5.3 清理临时文件、确认无调试日志残留