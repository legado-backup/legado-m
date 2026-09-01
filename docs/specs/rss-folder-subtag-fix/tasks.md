# tasks.md — 订阅文件夹样式：点进文件夹头部误显标签/箭头

## 1. 准备工作

- [x] 1.1 复核 `renderRssSecondaryTags()` 现行逻辑与 `applyView()` 的标签隐藏交互（已定位根因）

## 2. 核心实现

- [x] 2.1 在 `renderRssSecondaryTags()` 入口加 `if (!isTagMode)` 守卫，非标签样式 `showTags(false)` 后 return
- [x] 2.2 确认 `applyView()` 现有逻辑无需改动（非标签模式本已隐藏标签）

## 3. 验证

- [x] 3.1 编译通过（`./gradlew assembleAppDebug`，App 前缀）※ compileAppDebugKotlin exit 0
- [x] 3.5 updateLog 同步 + 无残留调试日志（本次改动未新增日志；Grep 无新增调试点）
- [x] 3.2 文件夹样式：主页目录无标签 → 点进文件夹子列表头无标签/无向下箭头 ✅ 2026-09-02（脚本 `l2_verify_rss_folder_subtag.py`；MEmu 包 3.26.090204，classic+style=2/mode=1：①目录态=文件夹网格可见（"全部"卡片锚点）+top_bar 内零源标签节点；②进"娱乐"文件夹子列表=top_bar 高度 131（纯标题行，无胶囊条/标签条扩展）+标签区域零源标签——isTagMode 守卫生效；dump 鉴别注记=子列表 y≈266 的"范围源C"为 recycler_view 列表项 @tv_name（源列表内容），非 tagsBar，判定已按 top_bar 区域排除）
- [x] 3.3 标签样式：primaryBar + tagsBar + 向下箭头正常展示 ✅ 2026-09-02（style=2/mode=0：①primaryBar 分组胶囊 5 节点（全部/未分组/科技/新闻/娱乐）+top_bar 高度 217 扩展；②向下箭头=filterToggleButton（ic_expand_more，content-desc="筛选"，ImageButton）存在；③点击箭头展开 tagsBar→源标签节点出现（库内合成源安全名匹配）；证据=ai_tests/reports/tag_mode_dump.xml+tag_expanded_dump.xml）
- [x] 3.4 返回键回文件夹目录：仍隐藏标签 ✅ 2026-09-02（子列表 keyevent 4 →文件夹目录卡片锚点恢复+top_bar 源标签节点保持为 0）

## AOAdapt 日志

- 无阻塞问题。