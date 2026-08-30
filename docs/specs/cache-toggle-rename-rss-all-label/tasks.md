# tasks.md - 文案调整：视频缓存开关改名 + 订阅「全部」分组标签缩短

## 1. 字符串资源修改

- [x] 1.1 `values/strings.xml`：`cache_play` 值改为「播放时缓存」 ✅ L1673
- [x] 1.2 `values/strings.xml`：`all_groups` 值改为 `All` ✅ L774
- [x] 1.3 `values-zh/strings.xml`：`all_groups` 值改为「全部」 ✅ L742
- [x] 1.4 `values-zh-rHK/strings.xml`：`all_groups` 值改为「全部」 ✅ L622
- [x] 1.5 `values-zh-rTW/strings.xml`：`all_groups` 值改为「全部」 ✅ L630

## 2. 版本交付同步

- [x] 2.1 基于 git diff 更新 `updateLog.md` ✅ 2026/08/30 优化段新增两条文案优化条目（位于 cronet 版本行之后）

## 3. 验证

- [x] 3.1 编译通过（`assembleAppDebug`，注意构建后 stop-daemons.bat 清场） ✅ BUILD SUCCESSFUL 3m14s + daemon 已清
- [x] 3.2 真机/模拟器 L1-L2 验证：视频设置面板显示「播放时缓存」+ 开关行为不变 ✅ 用户裁决跳过 L2（纯文案低风险，编译+Grep 已过），后续真机自行体验确认（Level 1）
- [x] 3.3 真机/模拟器 L1-L2 验证：订阅页标签栏/文件夹视图显示「全部」+ 点击行为不变 + 长按换封面正常（KEY_ALL_GROUPS 映射不破坏） ✅ 同上，用户裁决跳过（Level 1；封面 key 按资源 ID 比对，静态确认不受影响）
- [x] 3.4 Grep 复核：仓库内无残留调试代码；本次 5 处字符串值变更与设计文档一致 ✅ 5 处全为新值，无旧文案残留

## AOAdapt 日志

（实施过程中遇到问题时记录）
