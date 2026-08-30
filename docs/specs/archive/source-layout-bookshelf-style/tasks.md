# Tasks: 书源/订阅源布局参考书架重构（Issue-6 方案D）

## 任务清单

### 阶段0：设计文档审查

- [x] **T0.1** 创建 OpenSpec 设计文档（spec.md / design.md / tasks.md / README.md）
- [x] **T0.2** 在 design.md 中记录已完成的 item_book_source.xml 重构进度
- [x] **T0.3** 第一轮自查：补充 ADR-6~ADR-12
- [x] **T0.4** 第二轮自查：补充 ADR-13~ADR-16
- [x] **T0.5** 子代理深度审计：补充 ADR-17~ADR-21（修复5个阻塞点+8个遗漏点）
- [ ] **T0.6** 用 AskUserQuestion 请用户审查设计文档后再继续实施

### 阶段1：书源布局重构

- [x] **T1.1** 重构 item_book_source.xml（书源列表，参考 item_bookshelf_list.xml）—— 已完成
  - 左侧 FrameLayout 66x90dp + bg_source_folder_cover + tv_source_initial(28sp白色加粗) + v_enabled_dot(8dp)
  - 右侧 cb_book_source(16sp) + tv_book_source_url(13sp, drawableStart=ic_author) + tv_debug_text(13sp, drawableStart=ic_history)
  - 右侧操作 swt_enabled + iv_edit(48dp) + iv_menu_more(48dp) + iv_explore(8dp) + iv_progressBar(25dp)
  - 顶部 tv_host_text（域名分组标题）
- [x] **T1.2** 重构 item_book_source_compact.xml（书源紧凑列表，参考 item_bookshelf_list2.xml）
  - 左侧 FrameLayout 48x64dp + bg_source_folder_cover + tv_source_initial(20sp白色加粗) + v_enabled_dot(8dp)
  - 右侧 cb_book_source(**16sp**, ADR-18字号变更从14sp) + tv_book_source_url(13sp, 合并行格式)
  - 右侧操作 swt_enabled
  - **必须保留 iv_type_badge**（ADR-6，放在 cb_book_source 右侧 swt_enabled 左侧）
  - 控件约束链参考 ADR-19
- [x] **T1.3** 确认 item_book_source_grid.xml 已对齐书架（tv_source_name 12sp 2行居中）—— 无需修改

### 阶段2：订阅源布局重构

- [x] **T2.1** 调查 RssSourceActivity.applyListView 现状，确认已有列表模式（layout=0）—— 已确认（ADR-5）
- [x] **T2.2** 重构 item_rss_source.xml（订阅源列表，参考 item_book_source.xml 结构）
  - 根布局从 **LinearLayout 改为 ConstraintLayout**（ADR-14）
  - 字段差异（ADR-13）：无 iv_explore / iv_progressBar / tv_debug_text
  - 替代：tv_debug_text → **tv_last_update**（显示最后更新时间，ADR-20）
  - 保留：iv_source_cover / tv_source_initial / v_enabled_dot / cb_source / tv_rss_source_url / swt_enabled / iv_edit / iv_menu_more / tv_host_text / vw_foreground
- [x] **T2.3** 重构 item_rss_source_compact.xml（订阅源紧凑列表，参考 item_book_source_compact.xml）
  - cb_source 字号从 14sp 改为 **16sp**（ADR-18）
  - **必须保留 iv_type_badge**（ADR-6，订阅源类型映射：0=网页/1=图片/2=视频，用 item.type）
- [x] **T2.4** 确认 item_rss_source_grid.xml 已对齐书架（ADR-17，12sp 2行居中）—— 无需修改

### 阶段3：Adapter 代码适配

- [x] **T3.1** 新建 `app/src/main/java/io/legado/app/help/source/SourceExt.kt`，新增扩展函数：
  - `BookSourcePart.sourceInitial()`：`bookSourceName.firstOrNull()?.toString() ?: ""`（ADR-12）
  - `RssSource.sourceInitial()`：`sourceName.firstOrNull()?.toString() ?: ""`（ADR-12）
  - `BookSourcePart.sourceUrlHost()`：`lastHost ?: bookSourceUrl` + extractHost（ADR-11）
  - `RssSource.sourceUrlHost()`：`lastHost ?: sourceUrl` + extractHost（ADR-11）
- [x] **T3.2** 修改 BookSourceAdapter.bindViewHolder 绑定新控件（ADR-7）
  - convert payloads.isEmpty 全量分支：tvSourceInitial/tvBookSourceUrl/vEnabledDot
  - areContentsTheSame 增加 lastHost 比较（子代理审计A4）
  - getChangePayload 增加 upHost payload
  - convert payloads 分支：upHost/upName/enabled 同步新控件
- [x] **T3.3** 修改 BookSourceAdapterCompact.bindViewHolder 绑定新控件（ADR-7）
  - convert payloads.isEmpty 全量分支：tvSourceInitial/tvBookSourceUrl/vEnabledDot
  - areContentsTheSame 增加 lastHost 比较
  - **无 getChangePayload，无需 payload 增量代码**（子代理审计A5）
- [x] **T3.4** 检查 BookSourceGridAdapter 已绑定新控件（L78-80）—— 无需修改
- [x] **T3.5** 修改 RssSourceAdapter.bindViewHolder 绑定新控件（ADR-7）
  - convert payloads.isEmpty 全量分支：tvSourceInitial/tvRssSourceUrl/vEnabledDot/tvLastUpdate（ADR-20）
  - areContentsTheSame 增加 lastHost + lastUpdateTime 比较
  - getChangePayload 增加 upHost/upLastUpdate payload
  - convert payloads 分支同步新控件
- [x] **T3.6** 修改 RssSourceAdapterCompact.bindViewHolder 绑定新控件（ADR-7）
  - convert payloads.isEmpty 全量分支：tvSourceInitial/tvRssSourceUrl/vEnabledDot
  - areContentsTheSame 增加 lastHost 比较
  - **无 getChangePayload，无需 payload 增量代码**（子代理审计A5）
- [x] **T3.7** 检查 RssSourceGridAdapter 已绑定新控件（L78-80）—— 无需修改（子代理审计B6）

### 阶段3.5：订阅源 upSourceHost 链路改造（子代理审计A2/B1）

- [x] **T3.5.1** RssSourceAdapter.CallBack 接口新增 `fun getSourceHost(origin: String): String`
- [x] **T3.5.2** RssSourceActivity.getSourceHost 从 private 改为 override
- [x] **T3.5.3** RssSourceActivity.getSourceHost 修复异常输入处理（对齐 BookSourceActivity，空/http/https 返回 #）
- [x] **T3.5.4** RssSourceAdapter 新增 showSourceHost 字段 + upSourceHost + isItemHeader + getHeaderText（参考 BookSourceAdapter L251-309）
- [x] **T3.5.5** RssSourceAdapter.onCurrentListChanged 触发 upSourceHost 更新（参考 BookSourceAdapter L157-164）
- [x] **T3.5.6** RssSourceActivity 设置 adapter.showSourceHost = groupSourcesByDomain

### 阶段4：编译验证

- [ ] **T4.1** 编译通过（gradle assembleDebug）
- [ ] **T4.2** 无新增 lint error

### 阶段5：真机测试

- [ ] **T5.1** 安装到 MEmu 模拟器
- [ ] **T5.2** 书源3种模式切换正常（列表/紧凑/网格）
- [ ] **T5.3** 书源视觉与书架3种模式对应一致
- [ ] **T5.4** 订阅源3种模式切换正常
- [ ] **T5.5** 订阅源视觉与书架3种模式对应一致
- [ ] **T5.6** 多选 CheckBox 可点击
- [ ] **T5.7** 启用开关 Switch 可切换 + vEnabledDot 同步更新
- [ ] **T5.8** 编辑按钮可点击进入编辑页
- [ ] **T5.9** 更多按钮可点击弹出菜单
- [ ] **T5.10** 切换3种模式不崩溃
- [ ] **T5.11** 紧凑列表 root 点击=编辑 / root 长按=删除（ADR-8）
- [ ] **T5.12** 网格 root 点击=编辑 / root 长按=选择切换（ADR-8）
- [ ] **T5.13** 网格选中状态 backgroundTintList 半透明遮罩（ADR-8）
- [ ] **T5.14** 书源域名分组 tv_host_text 正常显示
- [ ] **T5.15** 订阅源域名分组 tv_host_text 正常显示（T3.5 改造后）
- [ ] **T5.16** 校验后 lastHost 回填，tv_book_source_url 刷新（子代理审计A4）
- [ ] **T5.17** vw_foreground 不拦截 ivEdit/ivMenuMore 点击（子代理审计C4）
- [ ] **T5.18** 紧凑列表 ivTypeBadge 类型徽章正确显示（书源5种类型/订阅源3种类型）

### 阶段6：交付同步

- [ ] **T6.1** 更新 updateLog.md（基于 git diff 分析真实代码变更）
- [ ] **T6.2** 更新 issues-found.md（Issue-6 状态改为已修复）
- [ ] **T6.3** 更新 docs/INDEX.md（新增 spec 目录索引）
- [ ] **T6.4** 更新 project_memory.md（记录完成结果）
- [ ] **T6.5** Git 提交并推送

## 进度跟踪

### 已完成

- T0.1~T0.5 设计文档创建+三轮审查（自查2轮+子代理审计1轮）
- T1.1 item_book_source.xml 重构 ✅
- T1.3 / T2.1 / T2.4 / T3.4 / T3.7 检查项已确认无需修改

### 进行中

- T0.6 等待用户审查设计文档（第三轮，含子代理审计结果）

### 待实施

- T1.2 / T2.2 / T2.3（3个布局XML重构）
- T3.1~T3.6（Adapter代码适配，含 SourceExt.kt 新建）
- T3.5.1~T3.5.6（订阅源 upSourceHost 链路改造）
- T4.x / T5.x / T6.x

## 子代理审计发现的阻塞点（已补充到ADR）

| 编号 | 阻塞点 | ADR | 严重程度 |
|------|--------|-----|---------|
| A1 | sourceUrlHost() 接收者类型错误（编译失败） | ADR-11 | 🔴 严重 |
| A2 | RssSourceAdapter 缺 upSourceHost 链路 | ADR-15 + T3.5 | 🟠 高 |
| A3 | RssSourceActivity.getSourceHost 异常输入处理不完整 | ADR-15 | 🟠 高 |
| A4 | diffItemCallback 不追踪 lastHost 变化 | ADR-7 | 🟡 中 |
| A5 | Compact 无 getChangePayload，ADR-7 payload 代码是死代码 | ADR-7 | 🟡 中 |
