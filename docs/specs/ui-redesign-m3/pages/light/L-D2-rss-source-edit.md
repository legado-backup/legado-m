# L-D2 订阅源编辑（RssSourceEdit）轻量设计文档

> **轻量版**：本页继承族文档 `pages/P7-rss.md`（S2 语义）+ `pages/P10-booksource-edit.md`（S3 表单/编辑器骨架样板），本文只写「继承 + 差异」。开发本页只读本文档 + P10（骨架范式）+ P7（RSS 语义）+ ui-standards §3.4 规格书。

## 0. 页面身份

- **页面名 / 文件锚点**：RssSourceEditActivity（`ui/rss/source/edit/`，View，4 Tab + KeyboardToolPop + CodeView 内核）
- **所属族文档**：`pages/P10-booksource-edit.md`（S3 表单/编辑器骨架样板）+ `pages/P7-rss.md`
- **骨架归类**：S3 表单/编辑器页
- **对应 task**：tasks.md `12.16n`（v2.8 预审，V1-V20 违例）；pages-inventory D2（优先级 P1）
- **fork 借鉴来源**：无独立借鉴（本仓新增仅 Issue-1 并发继承显示 + Issue-5 引入 V15 双源冲突）

## 1. 继承声明（本页复用什么）

- 复用骨架：S3 表单/编辑器骨架（见 P10 §2）：GlassTopAppBar + SettingsCard 分组字段 + CodeView 编辑器内核（AndroidView 桥接保留 View 栈）+ KeyboardToolPop + 底部保存/取消
- 复用组件（§3.4）：`GlassTopAppBar`、`SettingsCard`、`SettingsClickRow`、`AppEditDialog`
- 复用状态范式：VM 数据类 + 未保存退出拦截 `runCatching` 对比原始值（getRssSource vs rssSource.equal）
- **内核红线**：CodeView 语法色 R.color.md_* 豁免；KeyboardToolPop 为 PopupWindow 强依赖 View 体系，保留 AndroidView 桥接不重写 IME 探测

## 2. 差异点（与族文档唯一不同处）

| 维度 | 本页差异 | 说明 |
|------|---------|------|
| 布局结构 | 4 Tab（基础 16 字段实测/启动/列表 ruleArticles 等/WebView enableJs 等+Routes+Episodes 视频 textVideoOnly 等） | P10 为 6 Tab，本页 4 Tab；pages-inventory 原记「17 字段」实测 sourceEntities 16 项 |
| 交互 | 顶部快捷条：cbIsEnable/cbSingleUrl/cbIsEnableCookie/cbIsEnablePreload + spType rss_type 0/1/2 切换显隐 textVideoOnly+lyType articleStyle+editParseConcurrency（0=继承全局） | 表单页差异组件 |
| 功能点 | **规则补全 ruleComplete**（Title/PubDate/Description/Link 补自 Articles/Image/NextPage，7 个保存调用点原样搬入 VM） | RuleComplete.kt 纯正则零 UI 依赖 |
| 菜单 | 保存/全屏编辑→CodeEditActivity/调试/登录/源变量/清 cookie/自动补全/复制粘贴 JSON/扫码/分享/日志/帮助 | 菜单动态显隐正确（menu_login / menu_auto_complete checkable） |
| 功能缺陷 | **V15 parseConcurrency 双源冲突**（顶栏 editParseConcurrency 读 0..32 coerce :418-419，被 sourceEntities 旧值覆盖 0..20 :435-436，顶栏编辑值保存时被静默覆盖丢失） | **P1 修复**：统一上下限 |
| 死菜单 | V16 menu_search 无处理分支（source_edit.xml:30-33） | 待清理 |

## 3. 组件选型（§3.4 规格引用，仅列差异组件）

| 组件 | §3.4 规格摘要 | 本页使用点 |
|------|-------------|-----------|
| `GlassTopAppBar` | surface 实底 + titleMedium | 顶栏（V1 待修） |
| `SettingsCard` | 卡 18dp、标题 h16 v12、surfaceVariant、1dp elevation | 字段分组表单容器（V2 待修，替代裸字段流） |
| `AppEditDialog` | M3 AlertDialog 字段输入 | 规则字段编辑/变量/URL 选项弹窗 |
| `CodeView`（N 不迁移） | AndroidView 桥接保留 | 规则代码编辑区 |

## 4. 三态（继承族文档，仅列差异）

| 状态 | 组件 | 说明 |
|------|------|------|
| 加载 | `LinearProgressIndicator` | 字段区 loading 态（同 P10 §6），字段区顶部，初始化可省略 |
| 空态/错误 | — | 表单页错误以 Snackbar/校验提示呈现 |

## 5. i18n 与无障碍

- 新文案 `strings.xml` 双语；无硬编码中文/色/字号（3 kt+3 布局全 @color 资源，硬编码色 0）
- ⚠️ 待修：V3 Activity:225 `text="WEB_VIEW"` 第 4 Tab 文案硬编码、V4 shouldOverrideUrlLoading hint 硬编码、V5 getDisplayVariableComment 默认文案、V6 helpActions 5 项硬编码、V7 VM:93 toastOnUi("格式不对")、V8 "jsLib" label 非资源、V9 资源缺双语、V10 source_parse_concurrency 无 values-zh
- V18 触控目标 <48dp tools:ignore 掩盖（4 CheckBox+2 Spinner+60dp 宽输入）待修

## 6. 验收标准（轻量）

- [ ] 复用 S3 骨架 + CodeView/KeyboardToolPop AndroidView 桥接，无私有复制组件
- [ ] 功能点对照 pages-inventory D2 无遗漏（4 Tab/顶部快捷/ruleComplete/菜单）
- [ ] **V15 parseConcurrency 双源冲突已修复（P1）**；V1-V7/V9/V14-V18/V20 P1 必清项完成
- [ ] 真机功能点覆盖用例通过；§3.3 实施回执已填

## 7. 变更记录

- 2026-08-13：初始建立（关联 pages-inventory D2，task 12.16n）
