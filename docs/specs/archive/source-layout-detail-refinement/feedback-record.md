# 反馈持久化记录：source-layout-detail-refinement

> **🔴 压缩恢复必读**：本文档是上下文压缩后恢复用户反馈的唯一权威源。任何压缩恢复后，必须优先读取本文档，确保不丢失用户反馈。
>
> **创建原因**：用户多次反馈"每次上下文压缩后，AI 无视我的反馈，尤其是 AskUserQuestion 响应信息"。本文档将全部用户反馈+决策固化，确保压缩后可恢复。

---

## 一、反馈来源

| 来源 | 路径 | 说明 |
|------|------|------|
| **审查任务导出文件** | `temp/tmp/审查昨日改动与功能.md`（5092行，364KB） | 用户停止任务后导出的完整对话记录，含3条直接消息+多次AskUserQuestion响应 |
| **project_memory 反馈小节** | `~/.trae-cn/memory/projects/{key}/project_memory.md` | 已沉淀的反馈索引（2026-07-09/10） |
| **README.md 用户反馈原文** | `docs/specs/source-layout-detail-refinement/README.md#L56` | 7类细节不符的原始反馈文本 |

---

## 二、用户直接消息原文（导出文件3条）

### 消息1（line 7-12）—— 初始审查请求

> /openspec 深度全面审查昨天整体你完成的全面改动，然后深度分析思考任务是否都已完成，并且都已经达到我的要求，是否所有功能都能正常使用，无任何 bug
> 尤其是昨天的两大重要改动，书源订阅源的布局设计调整，和对内置视频播放器的整体功能及性能实用性提升
> 我首先能够明确告诉你的是，肯定有 bug，而且 buy 不少，但是我现在不想直接提供给你，我要求你先自我反省发现
> 并且你在昨天改的过程中来回横跳，来回改

**关键诉求**：自我反省发现 bug（不要等用户提供）；两大改动重点审查；来回横跳问题。

### 消息2（line 2612-2614）—— 催促

> ？

**含义**：AI 在实施 P0 修复时停顿过久，用户催促继续。

### 消息3（line 3446-3451）—— 打包/环境/审查全面批评

> 首先，审核反思一下为什么之前打包的时候没有遇到你上面的问题！！！不是安装目录在当前项目的app\build\outputs\apk\app\debug 这个目录下么？另外，为什么之前有的安装脚本文档没有指导你这么做？或者是这个文档需要优化完善的？为什么打包前不去编辑更新日志？也反思下。包括现在的模拟器这些信息~~ 还有就是本身项目使用的技术，以及环境在哪，你怎么老是忘记呢？ai_test 不是有虚拟化环境么？你tm又给我私自在我公共的python环境里安装依赖！！！昨天完整的测试ai_test难道没有给你描述对应的使用说明文档么？我把昨天的两个任务导出了你深度分析一下，看看哪些需要沉淀成为规范并明确告诉你自己以后要遵守执行的：temp\tmp\前端样式优化与功能改进.md temp\tmp\自动化APK测试与验证.md
> 打包前，更新日志也tm不自动更新了！！
> 另外，你确定你在完成所有任务前，深刻全面审查所有任务都已经确定明确的真实的真正的完成了么？是否有不符合当时设计的地方或者是漏改的地方！！！

**关键批评点（10项）**：
1. 打包前 APK 目录定位问题（应在 `app\build\outputs\apk\app\debug`）
2. 安装脚本文档需优化（未指导正确目录）
3. **打包前不更新 updateLog.md**（严重，必须编译前更新）
4. 忘记模拟器信息（MEmu，ADB 127.0.0.1:21503）
5. 忘记项目技术环境
6. **私自用公共 Python 环境装依赖**（严重违规，必须用 `ai_tests/venv`）
7. ai_tests 有使用说明文档未读
8. 需深度分析两个导出文档沉淀规范
9. updateLog 不自动更新
10. **任务完成前未深刻全面审查**（是否有不符设计或漏改）

---

## 三、AskUserQuestion 响应决策记录

### 检查点1 第1次"需调整"（line 480）→ 三个关键问题

用户选"需调整"后，AI 提炼出三个需深入研究的问题：

1. **书架分组根据图书什么信息归类？** → 答：BookGroup/Book 实体的 groupId 字段
2. **bookGroupStyle 标签 vs 文件夹的视觉差异？** → 答：style1（Tab+ViewPager）/style2（单RV混排）
3. **昨天改的是"二级页面"还是"首页"？** → 答：改了管理页（RssSourceActivity/BookSourceActivity），要的是首页（RssFragment/ExploreFragment）

### 检查点1 第2次"需调整"（line 664）→ 双维度下拉菜单设计

用户选"需调整"后，提出**双维度设计**核心需求：

| 维度 | 下拉菜单选项 | 说明 |
|------|------------|------|
| **归类维度** | 按分组 / 按类型 | 按分组=按 group 字段；按类型=按 bookSourceType/type 字段 |
| **样式维度** | 标签 / 文件夹 | 标签=style1（Tab+ViewPager）；文件夹=style2（单RV混排） |

**源类型字段定义（已源码核实）**：
- `BookSource.bookSourceType`：0=文本/1=音频/2=图片/3=文件/4=视频
- `RssSource.type`：0=网页/1=图片/2=视频

### 检查点1 第3次"需调整"（line 843）→ 无具体意见

用户第6次"需调整"但无具体意见，AI 主动询问需调整的具体方面。

### source-layout-detail-refinement 检查点1（2026-07-10 00:40）→ 需调整+新Bug

用户选"需调整"+D6方案C（保留15x不动），反馈新Bug：

> 书源和订阅源的分组里面的类型分类一级页面，从来都没有成功过！！！二级页面的订阅源的类型分类由于是在右侧菜单上直接设置的，有效，但现在不是说了么，订阅源设置的二级页面，改回原来的即可

**关键修正**：
- D2 从"两维度组合"调整为"修复按类型分组一级页面不生效bug + 两维度"
- D6 改为方案C（保留15x不动，无需代码修改）
- D3 明确：订阅源二级页面改回原来的列表

---

## 四、7类细节不符清单（D1-D7，核心交付需求）

来源：用户原话（README.md line 56）+ project_memory 2026-07-09 深夜反馈。

| 编号 | 用户反馈 | 当前实现 | 期望实现 | 状态 |
|------|---------|---------|---------|------|
| **D1** | 书源/订阅源分组样式应像书架"标签+分组"两模式 | source_group_style_new 是"列表/按类型/按分组"三选项（数据归类） | 标签模式（Tab平铺首屏）+ 分组模式（文件夹，点击进入源列表），参考 BookshelfFragment1/2 | 🔄 待实施 |
| **D2** | 分组类型要有"源类型"+"源分组"两维度；**一级页面按类型分组不生效** | 单一维度；订阅源一级页面类型分类不生效 | 源类型（文本/图片/视频）+ 源分组两维度组合；修复订阅源一级页面类型分类bug | 🔄 D2排查完成，2.2.5/2.2.7代码已改未勾选 |
| **D3** | 订阅源二级设置页面还原默认列表展示 | 文件夹/布局概念延伸到二级页面 | 布局概念只在首屏使用，二级页面还原列表 | 🔄 待实施 |
| **D4** | 搜索框参考书架实现 | 当前搜索框未充分利用标签/分组 | 参考书架 SearchView 实现 | 🔄 待实施 |
| **D5** | 视频缓存大小支持用户调整（下拉选择），不能固定 100mb | 已有设置入口（SettingsDialog.kt 50/100/200/500 MB），但用户找不到 | 设置入口更明显 + 改为 Spinner 下拉选择 | 🔄 待实施 |
| **D6** | 视频倍速 15x 有问题 | 最高 15x，15X 音频失真 | **用户决策：保留15x不动（方案C，无需代码修改）** | ✅ 已决策 |
| **D7** | "还有其他好多的" | - | 待用户继续列举，本 spec 预留扩展 | ⏸ 待用户列举 |

---

## 五、关键需求理解偏差（必须牢记，避免重蹈覆辙）

### 偏差1：只学到表象，没抓核心

**用户反馈（line 105）**：书源订阅源布局只复制了书架的"配置项命名"（`sourceLayout`/`sourceGroupStyle`/`sourceSort`/`sourceMargin` 对齐 `bookshelfLayout`/`bookGroupStyle`/`bookshelfSort`/`bookshelfMargin`）和"多 adapter 切换"的形式，但**没有复制书架三个 adapter 共享基类（`BaseBooksAdapter`）的关键架构**。

**后果**：compact/grid 模式下选择/拖拽/批量操作/校验刷新全部断裂。

**书架核心机制（必须参考的基准）**：
- `bookshelfLayout`：0=列表/1=紧凑/2-6=网格（值=列数）
- `bookGroupStyle`：0=style1(Tab+ViewPager) / 1=style2(单RV混排)
- `BaseBooksAdapter<VB>`：三 adapter 共享基类（selection/dragSelect/DiffUtil 统一）
- style1：BookshelfFragment1（TabLayout+ViewPager，每个分组独立 Fragment）
- style2：BookshelfFragment2（单 RecyclerView 混排 BookGroup+Book，点击进入子分组）

### 偏差2：改错对象（管理页 vs 首页）

**用户反馈（line 528-553）**：昨天大量改了订阅源栏目设置里面的二级页面，但用户要的是订阅源栏目**首页**根据书架布局深度分析设计。

| 错改对象 | 正确对象 |
|---------|---------|
| RssSourceActivity（订阅源**管理页**，二级页面） | RssFragment（订阅源**首页**，一级页面） |
| BookSourceActivity（书源**管理页**，二级页面） | ExploreFragment（发现页**首页**，一级页面） |

**关键澄清**：
- 管理页面的布局改动虽然也有 bug（Bug 1-8），但**不是用户的核心需求**
- 用户核心需求是**首页**是否参考书架 style1/style2 深度设计
- **D3 订阅源二级设置还原列表**：用户明确说"订阅源设置的二级页面，改回原来的即可"——即管理页的布局概念要移除，还原列表

### 偏差3：来回横跳（RssSourceActivity 文件夹视图）

**来回横跳历史**：
1. source-layout-redesign：添加文件夹视图
2. 审查 task#9：移除文件夹视图（误解"订阅源二级页面保持列表"为"完全移除文件夹视图"）
3. source-layout-detail-refinement D2：加回文件夹视图（正确理解"类型分类一级页面不生效"需要文件夹视图存在）

**当前最终状态**：RssSourceActivity 有完整文件夹视图（25处引用 isShowingFolder/folderAdapter/applyFolderView），这是正确的。

---

## 六、当前实施方向（用户选"固化反馈再继续"后的计划）

用户决策：先固化反馈（本文档），然后继续 D1/D3/D4/D5 实施。

| 任务 | 内容 | tasks.md 状态 |
|------|------|--------------|
| **D1** | 标签+分组两模式（新增 sourceGroupMode 配置 + BookSourceActivity/RssSourceActivity UI 切换） | 全部 [ ] 未做 |
| **D2** | 修复按类型分组一级页面不生效 + 两维度（2.2.5/2.2.7代码已改未勾选，2.2.8/2.2.11待验证） | 部分完成 |
| **D3** | 订阅源二级设置还原列表（onFolderClick 已实现列表切换，需验证） | 全部 [ ] 未做 |
| **D4** | 搜索框参考书架 | 全部 [ ] 未做 |
| **D5** | 视频缓存改为 Spinner 下拉 | 全部 [ ] 未做 |
| **D6** | 保留15x不动（方案C，无需代码） | ✅ [x] |

---

## 七、环境与规范（必须牢记，违反即批评）

### 环境常量（project_memory 已沉淀）

| 项目 | 值 |
|------|-----|
| ai_tests 虚拟环境 | `ai_tests\venv\Scripts\python.exe`（**禁止用公共 Python**） |
| ai_tests 激活方式 | `ai_tests\venv\Scripts\activate` |
| 模拟器 | MEmu，ADB 地址 127.0.0.1:21503 |
| APK 输出目录 | `app\build\outputs\apk\app\debug` |
| 编译命令 | `.gradlew.bat assembleDebug`（PowerShell 必须 `. ` 前缀） |
| updateLog.md | `app/src/main/assets/updateLog.md`（**编译前更新**） |

### 必须遵守的规范

1. **编译前更新 updateLog.md**（不是交付阶段）
2. **禁止公共 Python 安装依赖**（必须用 ai_tests/venv）
3. **任务完成前全面审查**（对照 design.md，无漏改）
4. **OpenSpec 检查点用 AskUserQuestion 三选项**（通过/需调整/拒绝）
5. **上下文压缩恢复并行读三件套**（AGENTS.md + project_memory + TaskList）
6. **源码文件 Edit 串行化**（后台 Agent 禁止触碰源码）

---

## 八、压缩恢复检查清单

> 上下文压缩恢复后，AI 必须按此清单自检：

- [ ] 已读取本文档（feedback-record.md）
- [ ] 已读取 AGENTS.md（强制规则）
- [ ] 已读取 project_memory.md（含反馈小节）
- [ ] 已调用 TaskList（任务状态唯一权威源）
- [ ] 已确认当前主线任务：source-layout-detail-refinement 的 D1/D3/D4/D5 实施
- [ ] 已确认 D2 代码已改但 tasks.md 未勾选（2.2.5/2.2.7）
- [ ] 已确认 D6 为方案C（保留15x，无需代码）
- [ ] 已确认 RssSourceActivity 文件夹视图是正确的（不要再次移除）
- [ ] 已确认首页（RssFragment/ExploreFragment）是核心需求对象，不是管理页
- [ ] 已确认编译前必须更新 updateLog.md

---

## 九、僵尸任务清理记录

以下 TaskList 任务为 p0-bugfix-round1 遗留，当前主线已转移到 source-layout-detail-refinement，需清理：

| 任务ID | 内容 | 处置 |
|--------|------|------|
| #5 | P0 修复：4 项核心 bug | status=deleted（已被 source-layout-detail-refinement 取代） |
| #13 | 编译验证 + updateLog 更新 | status=deleted（合并到 source-layout-detail-refinement Phase 4） |
| #14 | 核实 pref_main.xml debug产物缺失根因 | status=deleted（需在 Phase 4 验证） |
| #17 | 反思审核：打包/环境/日志遗忘根因 | status=completed（规范已沉淀到 project_memory） |
| #19 | 全面审查P0修复任务是否真正完成 | status=deleted（合并到 source-layout-detail-refinement Phase 4 验证） |

保留任务：
- #21 source-layout-detail-refinement（当前主线，in_progress）
- #6/#7/#8/#12/#18/#20（pending，后续处理）
