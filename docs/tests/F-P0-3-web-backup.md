# F-P0-3 Web 端备份管理 - 测试用例文档

> **功能**：Web 端备份管理页面（BackupManager.vue），通过 BookShelf 入口按钮在新窗口打开，调用后端 `/backup` 接口下载 ZIP 备份包，调用 `/backupPreview` 接口展示备份内容详情
> **借鉴来源**：蛋蛋Max（DandanLLab/Legado_Max）
> **测试级别**：Level 1（编译验证）+ Level 2（集成验证）+ Level 3（真机验证）
> **创建日期**：2026-07-06

---

## 测试环境

| 项 | 值 |
|----|-----|
| 前端框架 | Vue 3.5 + Vite 5.4 + TypeScript 5.5 |
| UI 库 | Element Plus 2.8.5 |
| 路由 | vue-router 4.4（hash 模式） |
| 后端 | NanoHTTPD（HttpServer.kt） |
| 构建产物位置 | `app/src/main/assets/web/vue/` |
| 后端接口 | `/backup`（GET，ZIP）、`/backupPreview`（GET，JSON） |

---

## 一、前端构建验证（Level 1）

### TC-01: Vite 构建成功

**关联源码**：HttpServer.kt, WebBackups.kt
**关联 Activity**：HttpServer

**前置条件**：modules/web/ 依赖已安装（npm install）

**测试步骤**：
1. 在 modules/web/ 目录运行 `npm run build`
2. 检查构建输出

**预期结果**：
- ✅ vue-tsc 类型检查通过（无 TypeScript 错误）
- ✅ vite build 成功（1638+ 模块转换）
- ✅ 生成 `dist/index.html`
- ✅ 生成 `dist/assets/BackupManager-*.js`（懒加载 chunk，约 5KB）
- ✅ 生成 `dist/assets/BackupManager-*.css`（约 6KB）
- ✅ 生成 `dist/assets/BookShelf-*.js`（含 goToBackup 方法）
- ✅ 生成 `dist/assets/vendor-*.js`（第三方依赖 chunk）

**实际结果**：✅ 通过（2026-07-06 验证，构建耗时 30.40s）

---

### TC-02: 构建产物正确复制到 APK 资源目录

**关联源码**：HttpServer.kt, WebBackups.kt
**关联 Activity**：HttpServer

**前置条件**：TC-01 通过

**测试步骤**：
1. 清理 `app/src/main/assets/web/vue/` 旧产物
2. 复制 `dist/*` 到 `app/src/main/assets/web/vue/`
3. 检查 vue/assets/ 目录内容

**预期结果**：
- ✅ `vue/index.html` 存在且为最新
- ✅ `vue/assets/BackupManager-*.js` 存在
- ✅ `vue/assets/BackupManager-*.css` 存在
- ✅ 无旧版本 hash 文件残留（如 `BookShelf-BOyAzsrc.js`）

**实际结果**：✅ 通过（15 个文件，8 个旧文件已清理）

---

### TC-03: APK 构建成功

**关联源码**：HttpServer.kt, WebBackups.kt
**关联 Activity**：HttpServer

**前置条件**：TC-02 通过

**测试步骤**：
1. 在项目根目录运行 `.\gradlew.bat :app:assembleAppDebug`
2. 检查构建输出

**预期结果**：
- ✅ BUILD SUCCESSFUL
- ✅ 前端产物正确打包到 APK
- ✅ 无 Kotlin 编译错误（前端变更不影响后端）

**实际结果**：✅ 通过（2026-07-06 验证，构建耗时 1m 4s）

---

## 二、BackupManager 组件功能（Level 3 真机验证）

### TC-04: 备份页面正常加载

**关联源码**：HttpServer.kt, WebBackups.kt
**关联 Activity**：HttpServer

**前置条件**：Web 服务启动，浏览器访问书架页面

**测试步骤**：
1. 在书架页面"基本设定"区域点击"数据备份"按钮
2. 观察新窗口打开的页面

**预期结果**：
- ✅ 新窗口打开（`window.open`）
- ✅ URL 为 `${legado_http_entry_point}#/backup`
- ✅ 页面标题显示"数据备份"
- ✅ 页面显示"数据备份"标题和"一键备份您的所有阅读数据"副标题
- ✅ 显示"点击下载备份压缩包"按钮
- ✅ 按钮为蓝色（#4a7af5），全宽，圆角 6px

---

### TC-05: 备份下载功能 - 正常场景

**关联源码**：HttpServer.kt, WebBackups.kt
**关联 Activity**：HttpServer

**前置条件**：TC-04 通过，后端 `/backup` 接口正常

**测试步骤**：
1. 点击"点击下载备份压缩包"按钮
2. 观察按钮状态变化
3. 等待下载完成

**预期结果**：
- ✅ 按钮文本变为"正在备份..."
- ✅ 按钮变为灰色（#999），disabled 状态
- ✅ 浏览器触发下载 `backup.zip`
- ✅ 下载完成后按钮恢复为"点击下载备份压缩包"
- ✅ 页面显示备份成功结果区域

---

### TC-06: 备份预览展示 - 正常场景

**关联源码**：HttpServer.kt, WebBackups.kt
**关联 Activity**：HttpServer

**前置条件**：TC-05 通过，后端 `/backupPreview` 接口正常

**测试步骤**：
1. 备份下载完成后，观察结果区域

**预期结果**：
- ✅ 显示"✓ 备份成功"标题
- ✅ 显示备份时间（格式：YYYY/MM/DD HH:MM:SS）
- ✅ 显示文件名、大小（B/KB/MB 自适应）、项目数
- ✅ 显示分类列表（书籍相关/源相关/规则相关/语音相关/配置相关/其他）
- ✅ 每个分类显示图标、名称、项目数、总大小
- ✅ 分类默认展开（expandedCategories 全部设为 true）
- ✅ 展开后显示每个备份项的图标、名称、描述、数量、大小、文件名

---

### TC-07: 分类展开/折叠

**关联源码**：HttpServer.kt, WebBackups.kt
**关联 Activity**：HttpServer

**前置条件**：TC-06 通过，备份预览已展示

**测试步骤**：
1. 点击某个分类的头部区域
2. 观察分类详情的展开/折叠状态
3. 再次点击该分类头部

**预期结果**：
- ✅ 第一次点击：分类折叠（详情隐藏，箭头旋转回原位）
- ✅ 第二次点击：分类展开（详情显示，箭头旋转 90 度）
- ✅ 展开/折叠有过渡动画（0.25s ease）
- ✅ 不同分类的展开/折叠状态相互独立

---

### TC-08: 文件图标正确显示

**关联源码**：HttpServer.kt, WebBackups.kt
**关联 Activity**：HttpServer

**前置条件**：TC-06 通过

**测试步骤**：
1. 观察各备份项的图标

**预期结果**：
- ✅ `bookshelf.json` → 📖
- ✅ `bookmark.json` → 🔖
- ✅ `bookSource.json` → 📡
- ✅ `rssSource.json` → 📰
- ✅ `replaceRule.json` → 🔄
- ✅ `readRecord.json` → 📊
- ✅ `httpTTS.json` → 🔊
- ✅ `config.json` → ⚙️
- ✅ 未知文件 → 📄

---

### TC-09: 文件大小格式化

**关联源码**：HttpServer.kt, WebBackups.kt
**关联 Activity**：HttpServer

**前置条件**：TC-06 通过

**测试步骤**：
1. 观察各备份项的大小显示

**预期结果**：
- ✅ < 1024 B → "XXX B"（如 "512 B"）
- ✅ < 1 MB → "XX.X KB"（如 "12.5 KB"）
- ✅ >= 1 MB → "X.XX MB"（如 "1.25 MB"）

---

### TC-10: 夜间模式适配

**关联源码**：HttpServer.kt, WebBackups.kt
**关联 Activity**：HttpServer

**前置条件**：阅读 App 主题设置为夜间模式（theme == 6）

**测试步骤**：
1. 在夜间模式下打开备份页面
2. 观察页面样式

**预期结果**：
- ✅ 页面背景为深色（#141414）
- ✅ 卡片背景为深色（#1f1f1f）
- ✅ 标题文字为浅色（#e5eaf3）
- ✅ 副标题文字为灰色（#666）
- ✅ 分类项边框为深色（#2e2e2e）
- ✅ 分类头部背景为深色（#262626）
- ✅ 详情项背景为深色（#1f1f1f）

**注意**：夜间模式依赖 `useBookStore().isNight`，新窗口打开时可能未加载配置（isNight 默认 false）。如需夜间模式生效，需在 BackupManager.vue 的 onMounted 中调用 `store.loadWebConfig()`。

---

## 三、BookShelf 入口按钮（Level 3 真机验证）

### TC-11: 入口按钮显示

**关联源码**：HttpServer.kt, WebBackups.kt
**关联 Activity**：HttpServer

**前置条件**：Web 服务启动，浏览器访问书架页面

**测试步骤**：
1. 在书架页面左侧导航栏找到"基本设定"区域

**预期结果**：
- ✅ "基本设定"下方显示两个 setting-item
- ✅ 第一个为连接状态标签（原有功能）
- ✅ 第二个为"数据备份"标签（新增）
- ✅ "数据备份"标签为蓝色，可点击

---

### TC-12: 入口按钮点击跳转

**关联源码**：HttpServer.kt, WebBackups.kt
**关联 Activity**：HttpServer

**前置条件**：TC-11 通过

**测试步骤**：
1. 点击"数据备份"标签
2. 观察浏览器行为

**预期结果**：
- ✅ 在新窗口/新标签页打开（`window.open`）
- ✅ URL 为 `${legado_http_entry_point}#/backup`
- ✅ 原书架页面不受影响（不跳转、不刷新）
- ✅ 新窗口加载完成后显示备份管理页面

---

## 四、后端接口对接（Level 2 集成验证）

### TC-13: /backup 接口 - 正常请求

**关联源码**：HttpServer.kt, WebBackups.kt
**关联 Activity**：HttpServer

**前置条件**：Web 服务启动

**测试步骤**：
1. 浏览器访问 `${legado_http_entry_point}backup`
2. 检查响应

**预期结果**：
- ✅ HTTP 200
- ✅ Content-Type 为 `application/zip`（或 NanoHTTPD 默认二进制类型）
- ✅ 响应体为 ZIP 文件二进制流
- ✅ ZIP 包含 bookshelf.json、bookSource.json、rssSource.json 等备份文件
- ✅ 响应头包含 `Access-Control-Allow-Methods: GET, POST`
- ✅ 响应头包含 `Access-Control-Allow-Origin`

---

### TC-14: /backupPreview 接口 - 正常请求

**关联源码**：HttpServer.kt, WebBackups.kt
**关联 Activity**：HttpServer

**前置条件**：Web 服务启动

**测试步骤**：
1. 浏览器访问 `${legado_http_entry_point}backupPreview`
2. 检查响应

**预期结果**：
- ✅ HTTP 200
- ✅ Content-Type 为 `application/json`
- ✅ 响应体为 JSON 格式
- ✅ JSON 结构：`{ isSuccess: true, errorMsg: "", data: { fileName, totalSize, createTime, items: [...] } }`
- ✅ items 数组每项包含 fileName、displayName、description、count、size
- ✅ 响应头包含 CORS 头

---

### TC-15: /backup 接口 - 备份内容完整性

**关联源码**：HttpServer.kt, WebBackups.kt
**关联 Activity**：HttpServer

**前置条件**：TC-13 通过

**测试步骤**：
1. 下载 /backup 返回的 ZIP 文件
2. 解压并检查内容

**预期结果**：
- ✅ 包含 bookshelf.json（书架数据）
- ✅ 包含 bookSource.json（书源）
- ✅ 包含 rssSource.json（订阅源）
- ✅ 包含 replaceRule.json（净化规则）
- ✅ 包含 readRecord.json（阅读记录）
- ✅ 包含 readRecordDetail.json（阅读记录详情，F-P0-2 新增）
- ✅ 包含 highlightRule.json（高亮规则，F-P0-2 新增）
- ✅ 包含 config.json（配置）
- ✅ 各 JSON 文件格式合法

---

## 五、异常场景（Level 3 真机验证）

### TC-16: 后端服务未启动

**关联源码**：HttpServer.kt, WebBackups.kt
**关联 Activity**：HttpServer

**前置条件**：Web 服务未启动（端口未监听）

**测试步骤**：
1. 打开备份页面
2. 点击"点击下载备份压缩包"按钮

**预期结果**：
- ✅ 按钮显示"正在备份..."（loading 状态）
- ✅ fetch 请求失败（网络错误）
- ✅ 按钮恢复为"点击下载备份压缩包"
- ✅ 显示错误消息（红色背景，#fff2f0）
- ✅ 错误消息内容明确（如 "Failed to fetch" 或 "备份过程中发生错误"）

---

### TC-17: /backup 接口返回错误

**关联源码**：HttpServer.kt, WebBackups.kt
**关联 Activity**：HttpServer

**前置条件**：Web 服务启动，但后端备份逻辑异常

**测试步骤**：
1. 模拟后端 /backup 返回 500 错误
2. 点击备份按钮

**预期结果**：
- ✅ 按钮显示 loading 状态
- ✅ fetch 检测到 !response.ok
- ✅ 显示错误消息 "备份失败: Internal Server Error"（或对应 statusText）
- ✅ 按钮恢复可点击状态

---

### TC-18: /backupPreview 返回空数据

**关联源码**：HttpServer.kt, WebBackups.kt
**关联 Activity**：HttpServer

**前置条件**：TC-05 通过，但 /backupPreview 返回空 items

**测试步骤**：
1. 模拟 /backupPreview 返回 `{ isSuccess: true, data: { items: [] } }`
2. 完成备份下载

**预期结果**：
- ✅ 备份下载成功（ZIP 文件正常下载）
- ✅ 结果区域显示"备份成功"
- ✅ 文件名、大小、项目数（0 项）正确显示
- ✅ 分类列表为空（无分类项显示）

---

### TC-19: /backupPreview 返回错误格式

**关联源码**：HttpServer.kt, WebBackups.kt
**关联 Activity**：HttpServer

**前置条件**：TC-05 通过

**测试步骤**：
1. 模拟 /backupPreview 返回 `{ isSuccess: false, errorMsg: "预览失败" }`
2. 完成备份下载

**预期结果**：
- ✅ 备份下载成功（ZIP 文件正常下载）
- ✅ 不显示备份结果区域
- ✅ 显示错误消息 "预览失败"（来自 previewData.errorMsg）

---

## 六、移动端适配（Level 3 真机验证）

### TC-20: 移动端窄屏适配

**关联源码**：HttpServer.kt, WebBackups.kt
**关联 Activity**：HttpServer

**前置条件**：浏览器窗口宽度 < 520px

**测试步骤**：
1. 在窄屏设备上打开备份页面
2. 观察页面布局

**预期结果**：
- ✅ 卡片 padding 从 40px 缩小到 24px 18px
- ✅ 标题字号从 24px 缩小到 20px
- ✅ 结果信息区域 flex-wrap 换行
- ✅ info-item 最小宽度 80px
- ✅ 整体布局居中，不溢出屏幕

---

## 七、路由集成验证（Level 2 集成验证）

### TC-21: 路由配置正确

**关联源码**：HttpServer.kt, WebBackups.kt
**关联 Activity**：HttpServer

**前置条件**：前端构建成功

**测试步骤**：
1. 检查 `modules/web/src/router/index.ts`
2. 检查 `modules/web/src/router/backupRouter.ts`

**预期结果**：
- ✅ `router/index.ts` 导入 backupRoutes
- ✅ routes 数组包含 bookRoutes、sourceRoutes、backupRoutes
- ✅ `backupRouter.ts` 定义 `/backup` 路由，name 为 'backup'
- ✅ `/backup` 路由懒加载 BackupManager.vue
- ✅ afterEach 钩子设置 backup 路由的 document.title 为"数据备份"

---

### TC-22: API 类型定义正确

**关联源码**：HttpServer.kt, WebBackups.kt
**关联 Activity**：HttpServer

**前置条件**：前端构建成功

**测试步骤**：
1. 检查 `modules/web/src/api/api.ts`

**预期结果**：
- ✅ 导出 `BackupItemInfo` 接口（fileName/displayName/description/count/size）
- ✅ 导出 `BackupOverview` 接口（fileName/totalSize/createTime/items）
- ✅ 导出 `getBackupPreview()` 方法（调用 backupPreview 接口）
- ✅ 导出 `getBackupUrl()` 方法（返回 `${legado_http_entry_point}backup`）
- ✅ default 导出对象包含 getBackupPreview 和 getBackupUrl

---

## 测试总结

| 类别 | 用例数 | 通过 | 待真机验证 |
|------|--------|------|-----------|
| 前端构建验证（Level 1） | 3 | 3 | 0 |
| BackupManager 功能（Level 3） | 7 | 0 | 7 |
| BookShelf 入口（Level 3） | 2 | 0 | 2 |
| 后端接口对接（Level 2） | 3 | 0 | 3 |
| 异常场景（Level 3） | 4 | 0 | 4 |
| 移动端适配（Level 3） | 1 | 0 | 1 |
| 路由集成验证（Level 2） | 2 | 0 | 2 |
| **合计** | **22** | **3** | **19** |

**Level 1 通过率**：100%（3/3）
**Level 2/3 待验证**：19 个用例需在真机/Web 服务环境中验证

---

## 依赖关系

- **前置依赖**：F-P0-2 备份选择器（后端 `/backup` 和 `/backupPreview` 接口已实现）
- **后端接口**：HttpServer.kt 第 79-84 行（/backup）、第 99 行（/backupPreview）
- **前端文件**：
  - `modules/web/src/views/BackupManager.vue`（新增，631 行）
  - `modules/web/src/router/backupRouter.ts`（新增，14 行）
  - `modules/web/src/router/index.ts`（修改，集成 backupRoutes）
  - `modules/web/src/views/BookShelf.vue`（修改，增加入口按钮和 goToBackup 方法）
  - `modules/web/src/api/api.ts`（修改，新增备份类型和方法）

## 已知限制

1. **夜间模式依赖配置加载**：新窗口打开时 `useBookStore().isNight` 默认 false，需调用 `loadWebConfig()` 才能获取真实主题。当前未调用，夜间模式可能不生效。
2. **fetch 直接调用**：BackupManager.vue 直接用 `fetch` 调用接口，未走 axios 实例（不走拦截器）。如需统一错误处理，可改用 `API.getBackupPreview()`。
3. **多页面构建未启用**：当前项目 vite.config.ts 未配置 `rollupOptions.input`，采用单页面 + hash 路由方案（`/#/backup`），而非蛋蛋Max 的多页面方案（`/backup/`）。
