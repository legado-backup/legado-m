# 文件夹封面替换回归修复 — 任务清单

## 1. 准备工作
- [x] 1.1 确认订阅根因（已完成：`folderComposeCovers` 未同步，铁证 L209-214 / L1287-1298）
- [x] 1.2 阅读 RssFragment 替换/恢复两入口现状
- [x] 1.3 阅读 SourceFolderComposeGrid 渲染数据源

## 2. 订阅端修复（核心）
- [x] 2.1 替换封面入口：同步更新 `folderComposeCovers`
  - Action: 在 selectFolderCover 的 savedPath 分支补 `folderComposeCovers = folderComposeCovers + (folder.groupKey to path)`
  - Observation: 仅 `folderAdapter.updateCover` 不触发 Compose 重组
  - Adapt: 双数据源同步写入，附注释标注
- [x] 2.2 恢复默认封面入口：同步更新 `folderComposeCovers`
  - Action: 在 onFolderRestoreCover 补 `folderComposeCovers = folderComposeCovers + (folder.groupKey to null)`
  - Observation: 恢复也仅更新 View adapter
  - Adapt: 与替换入口一致的双写
- [x] 2.3 确认初始化路径无需改动（`initFolderComposeView` 已一次性加载 DB covers）

## 3. 书架端验证
- [ ] 3.1 真机验证书架文件夹替换封面是否生效
- [ ] 3.2 若失效：对齐 `BookshelfScreen` / `GroupCover` 刷新链路修复

## 4. 验证（Level 2）
- [x] 4.1 编译通过（无新错误）
- [ ] 4.2 订阅替换封面后界面立即刷新
- [ ] 4.3 订阅恢复默认后立即恢复默认图标
- [ ] 4.4 重启后封面持久化生效（无回归）
- [ ] 4.5 书架替换封面（据 3.1 结论）生效
- [ ] 4.6 确认无残留调试日志（Grep 0 命中）

## 5. 收尾
- [ ] 5.1 updateLog.md 追加变更说明
- [ ] 5.2 更新 docs/INDEX.md 状态
- [ ] 5.3 强制检查点 2 / 3 用户审核