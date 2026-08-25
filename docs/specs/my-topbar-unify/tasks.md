# tasks.md — 我的页头部统一

## 1. 准备工作
- [ ] 1.1 确认需求范围（用户已确认：改用 MainTopBarView）✅
- [ ] 1.2 阅读相关源码（MainTopBarView / MyFragment / fragment_my_config.xml / MainActivity.refreshMainTopBars）✅

## 2. 核心实现
- [x] 2.1 `MainTopBarView.kt` 新增 `Mode.MY` 分支（searchButton/moreButton 可见、标题字号 20f、applyDefaultStyle 搜索按钮显示）
- [x] 2.2 `fragment_my_config.xml`：`TitleBar` → `MainTopBarView`（id=top_bar），`view_search` 默认 gone
- [x] 2.3 `MyFragment.kt`：移除 `setSupportToolbar`，接线 `topBar`（Mode.MY/标题/搜索入口/更多菜单）
- [x] 2.4 `MyFragment.kt`：新增 `showSettingsSearch()`（显示并聚焦 view_search）
- [x] 2.5 `MyFragment.kt`：迁移帮助菜单（menu_help → moreButton 点击 showHelp）
  - Action: 移除 `onCompatCreateOptionsMenu`/`onCompatOptionsItemSelected` override 及 `main_my` 菜单挂载；新增 `initTopBar()`（moreButton → `showHelp("appHelp")`）
  - Observation: `main_my` 菜单经 Grep 确认已无任何引用
  - Adapt: 直接删除空 override 与 `Menu`/`MenuItem` import，避免死代码

## 3. 验证
- [ ] 3.1 编译门禁（`assembleAppDebug`）通过
- [ ] 3.2 Grep 确认无残留调试日志（`android.util.Log`）
- [ ] 3.3 updateLog 同步（编译前）
- [ ] 3.4 真机 L2 验证：进入「我的」页观感与三页一致；点搜索入口展开就地搜索并过滤；顶栏设置改圆角/胶囊后「我的」页跟随刷新；moreButton 出帮助

## 4. 文档同步
- [ ] 4.1 更新 docs/INDEX.md（功能完成/状态变更）
- [ ] 4.2 更新 docs/project-flow/ 相关文档（若涉及模块结构/配置说明）
- [ ] 4.3 tasks.md 全部勾选 + 记录 AOAdapt 日志

## AOAdapt 日志

（实施过程中遇到的问题与调整记录，按需追加）

- [x] 2.3 编译报错 `Unresolved reference 'applyStatusBarPadding'`（MyFragment.kt:148）
  - Action: `applyStatusBarPadding` 是 `ViewExtensions.kt` 中的 `View` 扩展函数，非 `MainTopBarView` 成员方法；MyFragment 缺该扩展的 import
  - Observation: 书架/订阅/发现页均正常调用同一函数，其 import 完整
  - Adapt: MyFragment 补 `import io.legado.app.utils.applyStatusBarPadding`，编译通过
