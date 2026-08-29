# 订阅搜索范围上下文修复 tasks

> 状态：🔄 设计中（2026-08-28）
> 完成标记规范：✅ Level3 场景验证 / ⚠️ Level1-2 注明缺失项；遇到问题必须补 AOAdapt 日志（Action/Observation/Adapt）
> 执行约束：源码修改由主代理串行 Edit，禁止子代理并行修改同一文件（并发文件修改规范）

## 1. 准备工作

- [x] 1.1 精读 RssSearchScope.kt 全文 + RssFragment.kt 相关段 ✅ 2026-08-28（15 写点全定性：胶囊/文件夹/返回键/resetRssModeState/配置变更均正确互斥或重置；唯一并存路径=更多菜单分组跳转 L955-960 仅设 currentGroup 不清 currentType，buildSearchScope 以 currentGroup 优先判定与列表查询一致兜底；现代形态核实=源选择列表无分组浏览，无需同步）
- [x] 1.2 核实 RssSourceDao noGroup 查询 + RssSource.hasGroup ✅ 2026-08-28（noGroup SQL=`is null or =''` 精确匹配未分组，无 enabled 过滤→内存补过滤；hasGroup=splitGroupRegex 切分 HashSet 判定，可复用）
- [x] 1.3 核实 strings.xml 既有范围文案资源 ✅ 2026-08-28（no_group/type_web/type_image/type_video 全部已存在，display 映射全部复用，2.5 无需新增）

## 2. 核心实现

- [x] 2.1 RssSearchScope：token 判定（`@type:0/1/2`、`@no_group`）+ getRssSources 先解析后分派（类型→DAO 按类型查询、未分组→noGroup、普通分组→getByGroup + hasGroup 精确过滤、空=全部）✅ 2026-08-28 Level1（编译通过）
- [x] 2.2 RssSearchScope：display/displayNames token→友好文案映射；save() 对 token scope 短路不持久化（防污染 AppConfig.rssSearchScope）✅ 2026-08-28 Level1
- [x] 2.3 RssSourceDao：新增按类型查启用源查询（`type=:type and enabled=1`）✅ 2026-08-28 Level1（getEnabledByType L176-177）
- [x] 2.4 RssFragment：新增 buildSearchScope() 私有函数 + 经典形态搜索按钮 onClick 改传 scope ✅ 2026-08-28 Level1（buildSearchScope L900-911，onClick L941-945）
- [x] 2.5 strings.xml：新增范围文案 ✅ 2026-08-28（1.3 核实 no_group/type_web/type_image/type_video 全部已存在，复用零新增）

## 3. 编译与验证

- [x] 3.1 编译前基于 git diff 更新 app/src/main/assets/updateLog.md ✅ 2026-08-28（08/28 块首追加订阅搜索范围优化条目，日期头唯一）
- [x] 3.2 编译通过 ✅ 2026-08-28（build-legado.bat 测试包 BUILD SUCCESSFUL 6m18s，APK legado_miss_app_3.26.082813.apk 已归档 output\apk\test\；启动前 Get-CimInstance 校验发现 Gradle/Kotlin daemon 残留已先 stop-daemons.bat 清理，构建后 bat 内置清场）
- [ ] 3.3 模拟器真机验证（测试包 io.legado.miss.app.debug）：
  - ① 文件夹视图进分组→搜索结果仅该分组内源
  - ② 类型视图进类型文件夹/胶囊→搜索结果仅该类型源
  - ③ 进"未分组"→仅未分组源
  - ④ 根目录"全部"→全局搜索不变
  - ⑤ 搜索页顶部范围显示为友好文案（非原始 token），手动切换范围能力仍可用
- [ ] 3.4 回归验证：现代形态源内搜索（RssFragment:897）不变、设置页订阅源搜索入口（MySettingsData:283）全局不变、书源搜索（SearchScope）不受影响
- [ ] 3.5 Grep 确认无 android.util.Log 调试日志残留、无临时注释代码

## 4. 文档同步与收尾

- [ ] 4.1 tasks.md 全部标记完成级别；真机问题记录到 issues-found 与项目记忆
- [ ] 4.2 文档同步：docs/INDEX.md 状态更新；docs/project-flow/task-navigation.md 若模块锚点有变则更新；docs/project-flow/modules/ 订阅搜索相关文档核对
- [ ] 4.3 🛑 提交用户最终验收（检查点 3），验收后 README.md 状态改"✅ 已完成"

## AOAdapt 日志

（实施期间遇到问题必须在此记录，格式如下）

- [ ] X.Y 任务名
  - Action: 执行了什么操作
  - Observation: 观察到了什么结果
  - Adapt: 基于观察做了什么调整
