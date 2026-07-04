# Tasks: 同步阅读 Sigma 2026-07 最新提交

## 1. P0 Bug 修复
- [ ] 1.1 修复 AppWebDav.kt forEach 循环提前退出（return → return@forEach，2处）
- [ ] 1.2 修复 ReadBookActivity.kt 预设布局不刷新翻页动画（新增 13 -> upPageAnim()）
- [ ] 1.3 修复 BgTextConfigDialog.kt 事件列表缺少 13（arrayListOf(1,2,5) → arrayListOf(1,2,5,13)）

## 2. P1 内置订阅源更新
- [ ] 2.1 下载上游 rssSources.json 替换本地文件

## 3. P2 配置默认值调整
- [ ] 3.1 AppConfig.kt threadCount 默认值 16 → 32
- [ ] 3.2 AppConfig.kt preDownloadNum 默认值 10 → 2
- [ ] 3.3 ReadBookActivity.kt joinToString 惯用法优化

## 4. 验证
- [ ] 4.1 自动化验证：Grep 确认变更内容存在
- [ ] 4.2 构建验证：assembleAppDebug 编译通过
- [ ] 4.3 更新 updateLog.md
