# F-P0-5 书架管理 测试用例（第二波覆盖）

> 书架核心功能：列表显示、分组、排序、搜索、多选、导出

## 功能概述

书架是 App 主界面，展示用户书籍列表，支持分组、排序、搜索、批量管理。

**入口**：MainActivity（书架 Fragment）
**实现文件**：BookshelfActivity（MainActivity 内 Fragment）+ BookshelfManageActivity.kt + BookAdapter.kt + GroupManageDialog.kt

## 测试环境

- 设备：Android 6.0+ 真机
- 构建版本：appDebug
- 前置：至少导入 3 本书

---

## TC-F-P0-5-01：书架正常显示书籍列表（Level 3，正常用例）

**关联源码**：BookshelfActivity, BookAdapter.kt
**关联 Activity**：MainActivity

**前置资源**：
[共享] 已导入至少 3 本书

**测试步骤**：
1. 启动 App
2. 等待书架加载完成
3. 观察书籍列表

**预期结果**：
- ✅ 书架显示所有已导入书籍
- ✅ 每本书显示封面、书名、作者
- ✅ 列表可上下滚动
- ✅ 不崩溃

## TC-F-P0-5-02：分组管理 - 新建分组（Level 3，正常用例）

**关联源码**：BookshelfManageActivity.kt, GroupManageDialog.kt
**关联 Activity**：BookshelfManageActivity

**前置资源**：
[共享] App 已安装

**测试步骤**：
1. 长按书架任意书籍进入管理模式
2. 点击"移动到分组"
3. 在分组管理对话框点击"新建分组"
4. 输入分组名"测试分组"
5. 确认创建

**预期结果**：
- ✅ 分组管理对话框正常弹出
- ✅ 新建分组成功，列表显示"测试分组"
- ✅ 选中书籍可移动到新分组
- ✅ 不崩溃

## TC-F-P0-5-03：拖拽排序 - 手动排序模式（Level 3，正常用例）

**关联源码**：BookshelfManageActivity.kt, ItemTouchCallback.kt
**关联 Activity**：BookshelfManageActivity

**前置资源**：
[共享] 已启用"手动排序"模式（设置→书架排序→手动）

**测试步骤**：
1. 进入书架管理模式
2. 长按某本书的拖拽手柄
3. 拖动到新位置
4. 松手

**预期结果**：
- ✅ 拖拽过程有视觉反馈（阴影/缩放）
- ✅ 松手后顺序更新成功
- ✅ 退出后重新进入顺序保持
- ✅ 不崩溃

## TC-F-P0-5-04：搜索过滤 - 按书名（Level 3，正常用例）

**关联源码**：BookshelfManageActivity.kt
**关联 Activity**：BookshelfManageActivity

**前置资源**：
[共享] 书架有多本书

**测试步骤**：
1. 进入书架管理模式
2. 点击搜索框
3. 输入部分书名"测试"
4. 观察列表变化

**预期结果**：
- ✅ 列表实时过滤，仅显示匹配书籍
- ✅ 无匹配时显示空状态
- ✅ 清空搜索后恢复完整列表
- ✅ 不崩溃

## TC-F-P0-5-05：长按多选 - 批量选择（Level 3，正常用例）

**关联源码**：BookshelfManageActivity.kt, BookAdapter.kt
**关联 Activity**：BookshelfManageActivity

**前置资源**：
[共享] 书架有多本书

**测试步骤**：
1. 进入书架管理模式
2. 长按第一本书
3. 点击第二本、第三本
4. 观察选择栏

**预期结果**：
- ✅ 长按进入多选模式
- ✅ 点击其他书追加选择
- ✅ 选择栏显示已选数量
- ✅ 支持全选/反选
- ✅ 不崩溃

## TC-F-P0-5-06：移动到分组 - 批量操作（Level 3，正常用例）

**关联源码**：BookshelfManageActivity.kt, GroupSelectDialog.kt
**关联 Activity**：BookshelfManageActivity

**前置资源**：
[共享] 已创建至少 2 个分组

**测试步骤**：
1. 进入书架管理模式
2. 多选 2 本书
3. 点击"移动到分组"
4. 选择目标分组
5. 确认

**预期结果**：
- ✅ 分组选择对话框弹出
- ✅ 选择后书籍移动到目标分组
- ✅ 原分组列表更新
- ✅ 不崩溃

## TC-F-P0-5-07：导出 - 书籍信息导出（Level 3，正常用例）

**关联源码**：BookshelfManageActivity.kt, DirectLinkUpload.kt
**关联 Activity**：BookshelfManageActivity

**前置资源**：
[共享] 已选择至少 1 本书

**测试步骤**：
1. 进入书架管理模式
2. 多选 1 本书
3. 点击导出按钮
4. 选择导出路径
5. 确认导出

**预期结果**：
- ✅ 导出对话框弹出
- ✅ 选择路径后导出成功
- ✅ 显示导出路径并支持复制
- ✅ 不崩溃

## TC-F-P0-5-08：点击书籍进入详情（Level 3，正常用例）

**关联源码**：BookshelfManageActivity.kt, BookInfoActivity.kt
**关联 Activity**：BookshelfManageActivity, BookInfoActivity

**前置资源**：
[共享] 书架有至少 1 本书

**测试步骤**：
1. 在书架正常模式（非管理模式）
2. 点击任意一本书

**预期结果**：
- ✅ 跳转到 BookInfoActivity
- ✅ 显示书籍详情（封面/简介/章节列表）
- ✅ 返回后回到书架
- ✅ 不崩溃
