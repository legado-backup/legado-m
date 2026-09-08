# tasks.md — 主题字体大小：默认值统一与日夜配置生效修复

## 1. 准备工作
- [x] 1.1 AD-02/AD-03 已定稿（2A 仅内置主题 9；移除资产+暗夜紫迁移），AD-04 新增预置主题需求
- [ ] 1.2 Grep 复核 `getFontScale` 全部调用点清单（预期：AppContextWrapper.wrap、MainTopBarView×3、TopBarConfig×1）与暗夜紫 configList 依赖点（App.kt×2、AppearanceKitManager×1），确认与设计一致（验证标准：清单与 File Changes 表零偏差）
- [ ] 1.3 制备磨砂套件资产：图片压缩（背景 1080 宽 JPEG q≈80）+ fontScale 100→9 + 重打包 appearance_kit.json 清单，输出 assets/appearance_kits/frosted_dawn_dusk_kit.zip（验证标准：套件 ≤1.2MB，解包核验 manifest 与图尺寸）

## 2. 核心实现
- [ ] 2.1 AppContextWrapper：wrap() 推导 isNight 并传入；getFontScale 增必传 isNight 参数按 `ThemeRuntimeKeys` 对应键读取；新增 getFontScaleForContext(context)（从 configuration.uiMode night bit 推导）(L1)
  - 验证标准：Grep 确认 fontScaleN 读取点存在；全项目 getFontScale 调用点编译期全部修正
- [ ] 2.2 MainTopBarView（3 处）与 TopBarConfig（1 处）改走 getFontScaleForContext (L1)
  - 验证标准：Grep 无旧签名残留调用
- [ ] 2.3 ThemePackageManager.builtinEntry 日/夜主题 fontScale=9（AD-02）(L1)
  - 验证标准：Read 确认两处 Config 构造含 fontScale = 9
- [ ] 2.4 AppearanceKitManager：新增暗夜紫日/夜 Config + 日/夜顶栏 Config 代码内置常量（字段值按 design.md 字段级设计表）；ensureDarkPurpleKit 改读常量并**同时注册日/夜主题包进对应主题列表**；新增磨砂套件 assets seeding（pref 标记 + localThemeExists 双幂等，走 importPackage）(L1)
  - 验证标准：Grep 确认 ensureDarkPurpleKit 无 configList 依赖；日/夜两包+两顶栏注册逻辑 Read 核验；seeding 函数幂等逻辑 Read 核验
- [ ] 2.5 App.kt：首装预设与可回切注册改读 AppearanceKitManager 内置常量；IO 协程追加磨砂套件 seeding 调用 (L1)
  - 验证标准：Grep App.kt 无 ThemeConfig.configList 暗夜紫依赖残留
- [ ] 2.6 移除历史资产与导入链：themeConfig.json、DefaultData.themeConfigs/importDefaultThemeConfigs、LocalConfig.needUpThemeConfig、Restore.kt:223 调用（AD-03，迁移完成后执行）(L1)
  - 验证标准：Grep importDefaultThemeConfigs/needUpThemeConfig/themeConfigs 零残留；编译通过

## 3. 验证测试
- [ ] 3.1 L1 编译：`build-legado.bat` 通过 (L1)
- [ ] 3.2 updateLog.md：基于 git diff 按三步流程更新（编译前完成）
- [ ] 3.3 L2 模拟器验证（测试包）：夜间主题设字号 9 → 全局文本 0.9 缩放 + 顶栏联动；切白天恢复白天值；重启保持 (L2)
- [ ] 3.4 L2 首装场景：全新安装 → 夜间默认暗夜紫套件生效（字号 0.9）；主题列表含暗夜紫日/夜 + 磨砂晨/昏；磨砂套件应用后背景图正常、字号 0.9 (L2)
- [ ] 3.5 夜间键缺省回退：清除 fontScaleN 后夜间模式回落系统字号，无崩溃 (L2)
- [ ] 3.6 L3 老用户升级：差异字号覆盖安装后各按原值生效；已删磨砂套件用户不被重复 seeding (L3)
- [ ] 3.7 Grep `android.util.Log.d|android.util.Log.e` 无残留调试日志；临时日志零残留

## 4. 文档收尾
- [ ] 4.1 文档同步自查（声明式映射）：主题预置/字号语义变更反映至相关文档；issues-found/INDEX 状态流转
- [ ] 4.2 docs/INDEX.md 状态更新（设计完成 → 开发中 → 已完成）
- [ ] 4.3 AOAdapt 日志核对：开发中问题已在 tasks.md 对应任务下留痕
- [ ] 4.4 检查点 2：最终验收汇报（AskUserQuestion 三选项），通过后归档至 `docs/specs/archive/{日期}-theme-fontscale-daynight/`
