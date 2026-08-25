# 文件夹封面比例对齐 Archive — tasks

## 1. 准备工作
- [ ] 1.1 确认三处文件夹封面比例位置（BookshelfScreen / SourceFolderComposeGrid / item_source_folder_grid.xml）
- [ ] 1.2 确认 Archive/原版 CoverImageView 比例为 0.75（已核实 width*4/3）

## 2. 核心实现
- [ ] 2.1 `BookshelfScreen.kt` FolderGroupGridContent 封面 `aspectRatio(0.7f)` → `0.75f`
- [ ] 2.2 `SourceFolderComposeGrid.kt` 封面 `aspectRatio(0.7f)` → `0.75f`
- [ ] 2.3 `item_source_folder_grid.xml` `dimensionRatio` `0.7` → `0.75`

## 3. 验证
- [ ] 3.1 编译门禁（`.\\gradlew assembleAppDebug` 或 `build-legado.bat`），确认无错误
- [ ] 3.2 Grep 确认无错误遗留改动（书籍封面 395/520 行仍为 0.7）
- [ ] 3.3 验证书架/发现页文件夹网格边界与文案

## 4. 文档同步
- [ ] 4.1 更新 `docs/INDEX.md`（设计中 → 完成后移动）
- [ ] 4.2 检查 docs/project-flow 对应章节与代码一致（本次仅比例参数，无结构变更，确认无需更新）

## AOAdapt 日志
（如实施遇阻在此记录 Action/Observation/Adapt）