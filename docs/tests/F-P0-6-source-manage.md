# F-P0-6 书源管理 测试用例（第二波覆盖）

> 书源核心功能：列表、启用/禁用、导入导出、编辑、排序、搜索、分组、验证

## 功能概述

书源管理用于管理书源规则，支持 JSON 导入导出、批量启用/禁用、编辑、排序、分组、验证。

**入口**：书架（首页）→ 底部导航栏"我的"Tab → "书源管理"Preference 项
**实现文件**：BookSourceActivity.kt + SourceEditActivity.kt + SourcePickerDialog.kt + BookSourceAdapter.kt

## 测试环境

- 设备：Android 6.0+ 真机
- 构建版本：appDebug
- 前置：至少导入 2 个书源

---

## TC-F-P0-6-01：书源列表正常显示（Level 3，正常用例）

**关联源码**：BookSourceActivity.kt, BookSourceAdapter.kt
**关联 Activity**：BookSourceActivity

**前置资源**：
[共享] 已导入至少 2 个书源

**测试步骤**：
1. 点击"我的"
2. 点击"书源管理"
3. 观察列表

**预期结果**：
- ✅ 显示所有已导入书源
- ✅ 每条显示书源名、URL、启用状态
- ✅ 列表可滚动
- ✅ 不崩溃

## TC-F-P0-6-02：启用/禁用书源（Level 3，正常用例）

**关联源码**：BookSourceActivity.kt
**关联 Activity**：BookSourceActivity

**前置资源**：
[共享] 有至少 1 个已启用书源

**测试步骤**：
1. 点击"我的"
2. 点击"书源管理"
3. 长按任意书源进入多选模式
4. 点击"禁用"按钮
5. 观察书源状态变化
6. 再次选中，点击"启用"

**预期结果**：
- ✅ 禁用后书源状态变为"已禁用"
- ✅ 启用后恢复为"已启用"
- ✅ 状态持久化（重启后保持）
- ✅ 不崩溃

## TC-F-P0-6-03：导入书源 - JSON 文本（Level 3，正常用例）

**关联源码**：BookSourceActivity.kt, ImportBookSourceDialog.kt
**关联 Activity**：BookSourceActivity

**前置资源**：
[AI自备] 准备一段有效的书源 JSON 文本

**测试步骤**：
1. 点击"我的"
2. 点击"书源管理"
3. 点击右上角菜单 → 导入
4. 选择"网络导入"或"本地导入"
5. 粘贴 JSON 文本或输入 URL
6. 确认导入

**预期结果**：
- ✅ 导入对话框弹出
- ✅ 导入成功后列表更新
- ✅ 新书源默认启用
- ✅ 不崩溃

## TC-F-P0-6-04：导入书源 - 无效 JSON（Level 3，异常用例）

**关联源码**：BookSourceActivity.kt
**关联 Activity**：BookSourceActivity

**前置资源**：
[AI自备] 准备一段无效 JSON 文本（如 `{invalid`）

**测试步骤**：
1. 点击"我的"
2. 点击"书源管理"
3. 点击导入
4. 粘贴无效 JSON
5. 确认导入

**预期结果**：
- ✅ 显示"JSON 格式错误"提示
- ✅ 不导入任何书源
- ✅ 不崩溃

## TC-F-P0-6-05：编辑书源（Level 3，正常用例）

**关联源码**：SourceEditActivity.kt, BookSourceActivity.kt
**关联 Activity**：SourceEditActivity

**前置资源**：
[共享] 有至少 1 个书源

**测试步骤**：
1. 点击"我的"
2. 点击"书源管理"
3. 点击任意书源
4. 修改书源名称
5. 修改搜索 URL
6. 点击保存

**预期结果**：
- ✅ 跳转到 SourceEditActivity
- ✅ 修改后保存成功
- ✅ 返回列表显示新名称
- ✅ 不崩溃

## TC-F-P0-6-06：删除书源（Level 3，正常用例）

**关联源码**：BookSourceActivity.kt
**关联 Activity**：BookSourceActivity

**前置资源**：
[共享] 有至少 2 个书源

**测试步骤**：
1. 点击"我的"
2. 点击"书源管理"
3. 长按任意书源进入多选
4. 选中 1 个书源
5. 点击"删除"
6. 确认删除

**预期结果**：
- ✅ 删除确认对话框弹出
- ✅ 确认后书源从列表消失
- ✅ 删除后列表更新
- ✅ 不崩溃

## TC-F-P0-6-07：书源排序 - 拖拽（Level 3，正常用例）

**关联源码**：BookSourceActivity.kt, ItemTouchCallback.kt
**关联 Activity**：BookSourceActivity

**前置资源**：
[共享] 有至少 3 个书源

**测试步骤**：
1. 点击"我的"
2. 点击"书源管理"
3. 点击菜单 → 排序 → 手动
4. 长按某书源拖拽手柄
5. 拖到新位置
6. 松手

**预期结果**：
- ✅ 拖拽过程有反馈
- ✅ 松手后顺序更新
- ✅ 重新进入顺序保持
- ✅ 不崩溃

## TC-F-P0-6-08：书源搜索过滤（Level 3，正常用例）

**关联源码**：BookSourceActivity.kt
**关联 Activity**：BookSourceActivity

**前置资源**：
[共享] 有多个书源

**测试步骤**：
1. 点击"我的"
2. 点击"书源管理"
3. 点击搜索图标
4. 输入书源名关键词
5. 观察列表

**预期结果**：
- ✅ 列表实时过滤
- ✅ 无匹配显示空状态
- ✅ 清空恢复完整列表
- ✅ 不崩溃

## TC-F-P0-6-09：书源分组管理（Level 3，正常用例）

**关联源码**：BookSourceActivity.kt, SourceFolderAdapter.kt
**关联 Activity**：BookSourceActivity

**前置资源**：
[共享] 有多个书源

**测试步骤**：
1. 点击"我的"
2. 点击"书源管理"
3. 点击菜单 → 点击"分组管理"
4. 点击"新建分组"
5. 输入"测试书源组"
6. 选择若干书源加入分组
7. 确认

**预期结果**：
- ✅ 新建分组成功
- ✅ 书源可加入分组
- ✅ 分组在列表显示为文件夹
- ✅ 不崩溃

## TC-F-P0-6-10：书源验证 - 批量检测可用性（Level 3，正常用例）

**关联源码**：BookSourceActivity.kt, BookSourceCheckService.kt
**关联 Activity**：BookSourceActivity

**前置资源**：
[共享] 有至少 2 个书源，网络可用

**测试步骤**：
1. 点击"我的"
2. 点击"书源管理"
3. 长按进入多选
4. 全选书源
5. 点击"验证"
6. 等待验证完成

**预期结果**：
- ✅ 验证进度条显示
- ✅ 验证完成后显示可用/不可用数量
- ✅ 不可用书源标记状态
- ✅ 不崩溃
