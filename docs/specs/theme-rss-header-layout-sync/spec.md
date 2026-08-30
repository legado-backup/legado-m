# spec.md — 主题设置与订阅页/发现页头部布局联动修复

## Intent

用户在主题设置→发现/订阅配置中调整订阅页头部布局时，感知"整体发现有很多问题"。经代码穿透定位，问题收敛为四类：

- **P1 行为不一致**：订阅页头部为 `fragment_rss.xml` L10 单一 `MainTopBarView`（classic/modern 双模式共用）。`applyRegularStyle`（MainTopBarView.kt:489）中 `tagsBar.setSelectedBackgroundVisible(mode == Mode.DISCOVERY)`——RSS 模式（源标签 tagsBar 在 RssFragment modern 模式使用，RssFragment.kt:691/725）无选中背景高亮；而 `applyDefaultStyle`（L437）全模式 `true`。同一组件两种样式行为不一致。
- **P2 非事件驱动**：`ExploreFragment` 无任何 `observeEvent`/`observeLiveBus` 订阅（全文件 0 命中）。`discoveryPageMode` 变更→`applyDiscoveryMode`（L349-359，切 modern/suite/legacy 三容器）、`discoveryPageLayout` 变更→`applyDiscoverBookLayout`（L1718-1722）+`syncDiscoverComposeState`（L1724-1737），当前仅 onResume（L3542-3556）触发。设置页（DiscoverySubscriptionConfigFragment:115-127）发 NOTIFY_MAIN+800ms 补发，MainActivity 收到后只刷顶栏底栏（refreshAppearanceKit），发现页不响应——用户改完设置必须退出重进发现页才生效。
- **P3 刷新链为重建级**：主题色/字体变更链 = ThemeManageActivity 保存→ThemePackageManager.apply→ThemeConfig.applyConfig(notify=true)→ThemeConfig.kt:535 postEvent(RECREATE)→BaseActivity.kt:110-118 recreate()。机制生效但为全量重建，且 MainTopBarView 自身无第二刷新通道，依赖重建后 onAttachedToWindow→applyTopBarStyle(force=true)（MainTopBarView.kt:173-176）。
- **P4/P7/P8 技术债与验证债**：PreferKey.kt 约 :292-296 四个废弃 key 残留（rssViewMode/sourceViewMode/sourceFolderStyle/sourceFolderMargin）；历史 spec（rss-classic-layout-align）文档状态未同步（P6）；联动行为缺少真机 L2 验证（P7/P8）。

目标：订阅页头部样式行为一致化、发现页布局变更事件驱动即时生效、顶栏刷新链加固评估、废弃 key 清理、真机验证清偿验证债。

## Scope

### In（本次实现）

- **P1**：RSS 模式 regular 顶栏源标签选中背景高亮修复（MainTopBarView.kt:489 条件修正，与 default 样式及 DISCOVERY 模式对齐）
- **P2**：ExploreFragment 增加事件驱动刷新（NOTIFY_MAIN 或专项事件），回调中比对 AppConfig 当前值与已应用值，变化才执行 applyDiscoveryMode/applyDiscoverBookLayout；保留 onResume 兜底
- **P3**：MainTopBarView 增加自订阅 TOP_BAR_CHANGED 作为第二刷新通道（recreate 主链不动，加固评估）
- **P4**：废弃 key 查引用确认后清理（PreferKey.kt 四 key + AppConfig 对应属性，引用情况需核实）
- **P6**：文档状态同步（rss-classic-layout-align README 等）
- **真机 L2 验证**（清偿 P7/P8 验证债）

### Out（明确不做）

- **P5 入口统一重组**：订阅布局设置（SourceFolderConfigDialog，间距/视图/排序）入口仅在订阅页分组菜单；主题设置→发现订阅设置页仅 discoveryPageMode/modernDiscoveryPage/modernRssPage/discoveryPageLayout 4 key。入口统一属产品重构，登记后续任务
- 阅读器/播放器等豁免页的主题刷新链
- 顶栏包内容本身的功能变更（只做刷新链路加固，不动包格式/加载逻辑）
- MainActivity.refreshMainTopBars（MainActivity.kt:702-714 递归全树 refreshStyle）机制重写

## Approach

### Selected Approach

**「小步修复 + 增量刷新评估」**，不动 RECREATE 主链，逐点精准修复：

1. **P1 一致性修复**：MainTopBarView.kt:489 `tagsBar.setSelectedBackgroundVisible(mode == Mode.DISCOVERY)` 改为 RSS 模式也显示选中背景（与 applyDefaultStyle L437 及 DISCOVERY 行为对齐），使 regular 样式与 default 样式在该属性上收敛一致
2. **P2 事件驱动**：ExploreFragment 订阅 NOTIFY_MAIN（或专项事件），回调中比对 AppConfig 当前值（discoveryPageMode/discoveryPageLayout 等）与已应用值，有变化才调用 applyDiscoveryMode（L349-359）/applyDiscoverBookLayout（L1718-1722）+syncDiscoverComposeState（L1724-1737）；onResume 兜底保留（L3542-3556），形成事件即时 + onResume 兜底双保险
3. **P3 第二刷新通道**：MainTopBarView 增加自订阅 TOP_BAR_CHANGED（observeEvent 生命周期绑定防泄漏），收到后 applyTopBarStyle(force=true)，与 RECREATE 主链并存（主链负责全局主题色/字体兜底，第二通道负责增量换装）
4. **P4 key 清理**：全项目查引用（PreferKey.kt:292-296 四 key 及 AppConfig 对应属性），确认 0 引用或仅历史残留后删除；覆盖安装用户无损（key 未被新版本读写）
5. **P6 文档同步**：更新 rss-classic-layout-align README 状态，docs/INDEX.md 登记
6. **真机 L2 验证**：按 Scenarios 清单在测试包（io.legado.miss.app.debug）逐场景验证

### Alternatives Considered

| 方案 | 否决理由 |
|------|---------|
| 发现页改 Compose 全响应式重构 | 改动过大风险高，超出本次"联动问题修复"范围；现有 View 体系经事件驱动即可满足即时生效 |
| 给所有 Fragment 加全局 SharedPreferences 监听 | 监听泄漏风险高（需手动反注册）；事件总线（observeEvent/observeLiveBus）已是项目既有范式，遵循范式更稳 |
| MainTopBarView 改 Compose 重写 | 双模式（classic/modern）共用实例的历史竞态高发区，重写风险不可控，且 P1 仅一行条件修正即可解决 |
| 只靠 onResume 兜底不修事件驱动 | 用户已感知"设置后不生效需退出重进"，体验问题真实存在，不修等于未响应需求 |
| 废弃 RECREATE 改纯事件驱动顶栏换装 | RECREATE 主链对全局主题色/字体变更是正确兜底，动主链影响面不可控；只增加第二通道做增量加固 |

### Drawbacks

- P1 改动影响 DISCOVERY/RSS 两模式共享分支，需回归验证两模式选中高亮均正常
- P2 事件驱动增加少量重复刷新风险，用值比对防抖收敛（值未变化不触发重建，防闪屏）
- P3 自订阅需 observeEvent 生命周期绑定防泄漏；第二通道与 RECREATE 主链并存，需确认 applyTopBarStyle 幂等、无双重 apply 副作用
- P4 废弃 key 删除需查引用充分防误删（AppConfig 对应属性引用情况需核实后决定删除范围）
- 修复面跨 MainTopBarView/ExploreFragment/设置页多文件，回归面较广，依赖真机 L2 全场景清偿

### Prior Art

- config-needs-restart-fix：事件双轨 + 值比对防抖范式（BOOKSHELF_STRUCTURE_CHANGED → rebuildBookshelfContent）
- rss-classic-layout-align S3：BOOKSHELF_STRUCTURE_CHANGED 跨页监听范式
- BookshelfScreen 受控入参范式：Compose remember 快照改受控入参响应配置变化
- ui-style-unify-deep-fix S 批：监听 guard/状态重置/事件兜底六项修复范式

## Requirements

1. **R1 RSS 模式源标签选中高亮**（P1）：RSS 模式 regular 顶栏源标签（tagsBar）选中项有背景高亮，与 default 样式及 DISCOVERY 模式一致。验收：真机 RSS 页 modern 顶栏选中源标签可见选中背景；DISCOVERY 模式行为不回归
2. **R2 发现布局即时生效**（P2）：设置页修改发现页布局/模式后，返回发现页无需退出重进即生效。验收：改 discoveryPageLayout 后发现页布局立即变化；改 discoveryPageMode 后 modern/suite/legacy 三容器正确切换；值未变化时不触发重建（无闪屏）
3. **R3 顶栏包换装时效**（P3）：顶栏包应用后订阅页头部 1s 内换装。验收：ThemePackageManager.apply 后经 RECREATE 主链或 TOP_BAR_CHANGED 第二通道任一生效，头部样式（含 RSS 模式）与包配置一致
4. **R4 主题色变更头部正确**（P3）：主题色/字体变更后订阅页头部颜色字体正确。验收：换主题后订阅页头部 primaryBar/tagsBar 颜色与新主题一致，无旧色残留
5. **R5 废弃 key 清零**（P4）：rssViewMode/sourceViewMode/sourceFolderStyle/sourceFolderMargin 全项目 0 引用。验收：四 key 在 PreferKey.kt 定义删除后全项目 Grep 0 命中，AppConfig 对应属性（如存在引用则保留属性仅删 key，如无引用一并删除）处理完成，编译通过
6. **R6 编译门禁**：`gradlew assembleAppDebug` BUILD SUCCESSFUL。验收：编译 0 error
7. **R7 真机 L2 场景全过**（清偿 P7/P8）：本 spec Scenarios 全部场景真机通过。验收：测试包 io.legado.miss.app.debug 逐场景验证，问题记入 issues-found.md
8. **R8 临时日志 0 残留**：验收：Grep `android.util.Log.d|android.util.Log.e` 及自定义诊断 tag 0 残留

## Scenarios

### 正常流程

**场景 A：改发现页布局即时生效**（P2 主场景，R2）
1. 进入发现页，记当前布局
2. 主题设置→发现订阅设置→修改发现页布局（discoveryPageLayout）
3. 返回发现页（不退出重进）
4. **期望**：布局立即变化，无闪屏；值未变时反复进出不重建

**场景 B：改订阅页模式头部切换**（R1/R2 关联）
1. 设置页切换订阅页模式（modern/classic，discoveryPageMode 相关链路）
2. 返回订阅页
3. **期望**：头部立即切换为对应模式样式；modern 模式下源标签选中项有背景高亮（R1）

**场景 C：顶栏包应用头部换装**（R3）
1. 主题设置→顶栏包→应用某顶栏包
2. 观察订阅页头部
3. **期望**：1s 内头部换装完成，样式与包配置一致（含 RSS 模式顶栏）

**场景 D：主题色变更头部变色**（R4）
1. 主题设置→切换主题色
2. 返回订阅页/发现页
3. **期望**：头部 primaryBar/tagsBar 颜色与新主题一致，无旧色残留

### 异常流程

**场景 E：事件丢失时 onResume 兜底收敛**（P2 兜底，R2）
1. 修改发现布局后事件未被消费（模拟时序竞态/进程后台回收）
2. 重新进入发现页触发 onResume
3. **期望**：onResume 兜底比对 AppConfig 值后应用变更，最终状态收敛正确

**场景 F：订阅页不在前台时设置变更**
1. 当前在书架/我的 Tab，修改顶栏/订阅相关设置
2. 切回订阅页
3. **期望**：头部状态正确（RECREATE 或第二通道/onResume 兜底任一路径收敛），无残留旧样式

### 边界条件

**场景 G：classic 模式下 tagsBar 不存在时 P1 修复不崩**（R1 边界）
1. 切到 classic 模式（无 tagsBar 或 tagsBar 隐藏态）
2. 触发顶栏刷新（applyRegularStyle/applyDefaultStyle）
3. **期望**：不崩溃、不 NPE；classic 样式表现不回归

**场景 H：discoveryPageLayout 弹框取消不变更**（R2 边界）
1. 打开发现布局选择弹框，点取消/外部关闭
2. 返回发现页
3. **期望**：布局不变、不触发重建、无闪烁
