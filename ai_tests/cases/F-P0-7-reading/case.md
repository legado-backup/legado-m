# F-P0-7 阅读 测试用例（第二波覆盖）

> 阅读核心功能：翻页、目录、字体、背景、书签、高亮、搜索、自动翻页、夜间模式

## 功能概述

阅读是 App 核心功能，支持翻页、目录、字体/背景设置、书签、高亮笔记、全文搜索等。

**入口**：书架 → 点击书籍 → ReadBookActivity
**实现文件**：ReadBookActivity.kt + ReadMenu.kt + BaseReadBookActivity.kt + TextActionMenu.kt + SearchMenu.kt + HighlightNoteDialog.kt

## 测试环境

- 设备：Android 6.0+ 真机
- 构建版本：appDebug
- 前置：已导入至少 1 本可正常阅读的书

---

## TC-F-P0-7-01：进入阅读界面（Level 3，正常用例）

**关联源码**：ReadBookActivity.kt, BaseReadBookActivity.kt
**关联 Activity**：ReadBookActivity

**前置资源**：
[共享] 书架有至少 1 本书

**测试步骤**：
1. 启动 App，进入书架
2. 点击任意书籍

**预期结果**：
- ✅ 跳转到 ReadBookActivity
- ✅ 显示书籍正文内容
- ✅ 状态栏隐藏，沉浸式阅读
- ✅ 不崩溃

## TC-F-P0-7-02：翻页 - 下一页（Level 3，正常用例）

**关联源码**：ReadBookActivity.kt, ReadMenu.kt
**关联 Activity**：ReadBookActivity

**前置资源**：
[共享] 已进入阅读界面

**测试步骤**：
1. 在阅读界面，点击屏幕右侧
2. 观察翻页动画
3. 连续点击 3 次

**预期结果**：
- ✅ 翻页动画流畅
- ✅ 内容正确切换到下一页
- ✅ 翻页进度更新
- ✅ 不崩溃

## TC-F-P0-7-03：翻页 - 上一页（Level 3，正常用例）

**关联源码**：ReadBookActivity.kt, ReadMenu.kt
**关联 Activity**：ReadBookActivity

**前置资源**：
[共享] 已进入阅读界面且非第一页

**测试步骤**：
1. 在阅读界面，点击屏幕左侧
2. 观察翻页动画
3. 连续点击 3 次

**预期结果**：
- ✅ 翻页动画流畅
- ✅ 内容正确切换到上一页
- ✅ 不崩溃

## TC-F-P0-7-04：打开目录跳转（Level 3，正常用例）

**关联源码**：ReadMenu.kt, ReadBookActivity.kt
**关联 Activity**：ReadBookActivity

**前置资源**：
[共享] 已进入阅读界面

**测试步骤**：
1. 点击屏幕中间呼出阅读菜单
2. 点击"目录"图标
3. 等待目录加载
4. 点击任意章节

**预期结果**：
- ✅ 目录列表正常加载
- ✅ 点击章节后跳转到对应位置
- ✅ 当前章节在目录高亮
- ✅ 不崩溃

## TC-F-P0-7-05：字体大小调整（Level 3，正常用例）

**关联源码**：ReadMenu.kt, ReadBookActivity.kt
**关联 Activity**：ReadBookActivity

**前置资源**：
[共享] 已进入阅读界面

**测试步骤**：
1. 点击屏幕中间呼出菜单
2. 点击"Aa"字体设置图标
3. 增大字号
4. 减小字号
5. 确认

**预期结果**：
- ✅ 字体设置面板弹出
- ✅ 字号实时预览
- ✅ 确认后字号生效
- ✅ 不崩溃

## TC-F-P0-7-06：背景色切换（Level 3，正常用例）

**关联源码**：ReadMenu.kt, ReadBookActivity.kt
**关联 Activity**：ReadBookActivity

**前置资源**：
[共享] 已进入阅读界面

**测试步骤**：
1. 呼出阅读菜单
2. 点击背景色设置
3. 选择"羊皮纸"背景
4. 选择"绿色护眼"背景
5. 选择默认白色背景

**预期结果**：
- ✅ 背景色实时切换
- ✅ 切换后文字对比度合适
- ✅ 设置持久化
- ✅ 不崩溃

## TC-F-P0-7-07：添加书签（Level 3，正常用例）

**关联源码**：ReadBookActivity.kt, ReadMenu.kt
**关联 Activity**：ReadBookActivity

**前置资源**：
[共享] 已进入阅读界面

**测试步骤**：
1. 呼出阅读菜单
2. 点击"书签"图标
3. 选择"添加书签"
4. 呼出菜单，再次点击书签图标
5. 查看书签列表

**预期结果**：
- ✅ 书签添加成功提示
- ✅ 书签列表显示当前页书签
- ✅ 点击书签可跳转回原位置
- ✅ 不崩溃

## TC-F-P0-7-08：文本高亮 - 添加（Level 3，正常用例）

**关联源码**：TextActionMenu.kt, HighlightNoteDialog.kt, ReadBookActivity.kt
**关联 Activity**：ReadBookActivity

**前置资源**：
[共享] 已进入阅读界面

**测试步骤**：
1. 长按屏幕选择一段文字
2. 拖动选择手柄扩大选区
3. 在弹出菜单点击"高亮"
4. 选择高亮颜色

**预期结果**：
- ✅ 文字选择功能正常
- ✅ 高亮菜单弹出
- ✅ 选择颜色后文字高亮显示
- ✅ 不崩溃

## TC-F-P0-7-09：高亮笔记 - 编辑（Level 3，正常用例）

**关联源码**：HighlightNoteDialog.kt, TextActionMenu.kt
**关联 Activity**：ReadBookActivity

**前置资源**：
[共享] 已有至少 1 处高亮

**测试步骤**：
1. 点击已高亮的文字
2. 在弹出菜单点击"笔记"
3. 输入笔记内容"测试笔记"
4. 保存

**预期结果**：
- ✅ 笔记编辑对话框弹出
- ✅ 保存后笔记与高亮关联
- ✅ 在高亮列表可查看笔记
- ✅ 不崩溃

## TC-F-P0-7-10：全文搜索（Level 3，正常用例）

**关联源码**：SearchMenu.kt, ReadBookActivity.kt
**关联 Activity**：ReadBookActivity

**前置资源**：
[共享] 已进入阅读界面

**测试步骤**：
1. 呼出阅读菜单
2. 点击"搜索"图标
3. 输入搜索关键词"主角"
4. 等待搜索结果

**预期结果**：
- ✅ 搜索结果列表显示匹配章节
- ✅ 点击结果跳转到对应位置
- ✅ 关键词高亮显示
- ✅ 不崩溃

## TC-F-P0-7-11：夜间模式切换（Level 3，正常用例）

**关联源码**：ReadMenu.kt, ReadBookActivity.kt
**关联 Activity**：ReadBookActivity

**前置资源**：
[共享] 已进入阅读界面

**测试步骤**：
1. 呼出阅读菜单
2. 点击"夜间模式"图标
3. 观察界面变化
4. 再次点击切回日间模式

**预期结果**：
- ✅ 切换到夜间模式后背景变暗
- ✅ 文字颜色适配（变白/灰）
- ✅ 切回日间模式恢复正常
- ✅ 不崩溃

## TC-F-P0-7-12：阅读进度记忆（Level 3，正常用例）

**关联源码**：ReadBookActivity.kt, ReadBookViewModel.kt
**关联 Activity**：ReadBookActivity

**前置资源**：
[共享] 已进入阅读界面并翻到第 3 页

**测试步骤**：
1. 翻到任意位置（非第 1 页）
2. 按返回键退出阅读
3. 回到书架
4. 再次点击同一本书

**预期结果**：
- ✅ 退出后进度自动保存
- ✅ 重新进入恢复到上次阅读位置
- ✅ 进度条显示正确百分比
- ✅ 不崩溃
