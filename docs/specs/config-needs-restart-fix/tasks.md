# tasks.md — 配置修改需重启生效 + 视效对齐 archive（实施完成版）

## 0. 实施就绪（权威顺序声明）

执行顺序（单一权威）：**订阅 collector 泄漏修复 → 书架事件分类重排 + STRUCTURE 事件 → style2 双监听 → BookshelfScreen 参数化 + 三配置接入 → 新发现 bug 修复 → 视效对齐 → 编译门禁 → 文档同步**。恢复检查点 = 本 §0 + design.md 卡点表 + project 记忆「当前任务状态」。

- [x] 0.1 需求确认（订阅顶栏残留 + 书架布局需重启；合并决策 08-28）
- [x] 0.2 穿透审查：三实锤（rssFlowJob 泄漏 / style2 零监听 / remember 快照+分类过宽）全部源码级核实
- [x] 0.3 统一四文档生成（修订版）+ 删旧两独立 spec + INDEX 同步
- [x] 0.4 OURS vs archive 视效差异清单（design.md 附录 A，8 维度）；新发现 K7/K8；K3 核实回退 REFRESH
- [x] 0.5 用户审核：二次审核 → 补充完善（附录 A/B）→ 规范评估（AD-07）→ **终审通过（2026-08-28 23:50，验收标准=仅编译通过，真机 L2 延后）**

## 1. 订阅顶栏修复（实锤 1）

- [x] 1.1 `resetRssModeState()` 无条件取消 groupsFlowJob + rssFlowJob 并置 null（RssFragment.kt:372-379）
- [x] 1.2 核实取消后无其他消费方依赖（groupsFlowJob/rssFlowJob 均模式私有）
- [x] 1.3 ~~验证日志~~（用户裁决仅编译验证，未插桩）
- [x] 1.4 编译通过（真机场景 A 验证延后，登记 R2）

## 2. 书架事件分类重排 + STRUCTURE 事件（实锤 3 事件侧）

- [x] 2.1 `EventBus.kt` 新增 `BOOKSHELF_STRUCTURE_CHANGED`（EventBus.kt:8）
- [x] 2.2 `applyBookshelfConfig` 按 design 权威表重排（structure 仅 layout/showBookname；refresh=margin/style/introLines/unread/updateTime/fastScroller/waitUpCount；sort 仅 upSort；returnToTopAfterRead 仅存值）（BaseBookshelfFragment.kt:290-365）
- [x] 2.3 STRUCTURE 发布用 `view?.post { postEvent(...) }`（BaseBookshelfFragment.kt:358-362）
- [x] 2.4 ~~验证日志~~（未插桩）

## 3. style2 双监听 + 双侧 rebuild（实锤 2）

- [x] 3.1 `BookshelfFragment2` 补 REFRESH+STRUCTURE 双监听 + rebuildBookshelfContent（BookshelfFragment2.kt:141-147）
- [x] 3.2 `BookshelfFragment1` 补 STRUCTURE 监听 + rebuild（BookshelfFragment1.kt:190-192）
- [x] 3.3 rebuild 不丢分组/书籍状态（Fragment 状态字段独立于 composition）

## 4. BookshelfScreen 参数化 + 三配置接入（实锤 3 渲染侧）

- [x] 4.1 Fragment1/2 新增 8 项配置 mutableStateOf 字段 + refreshShelfRenderConfig/rebuildBookshelfContent
- [x] 4.2 `BookshelfScreen` 删 remember 快照与 :214 直读，新签名 8 配置受控入参
- [x] 4.3 margin 接入：网格 contentPadding/spacedBy + 列表 contentPadding + 分组容器（K9）
- [x] 4.4 introLines 接入：BookListItem 简介行（book.getDisplayIntro()，maxLines 0-3，0=隐藏）
- [x] 4.5 listItemStyle 接入：Classic/RoundedCard 双样式分档（行高 82/112/112/154、封面 58/78/68/94、padding 分档、row 填充+边框+actionRadius 圆角）
- [x] 4.6 数据类开关走 REFRESH 仅刷数据不重建

## 4A. 新发现 bug 修复（K7/K8，已裁决）

- [x] 4A.1 showBookname 语义错位修复（K7）：弹框值映射改 [隐藏→0, 显示→1, 遮罩→2]（BookshelfConfigDialog.kt:260-264）；存量迁移 migrateLegacyShowBookname（BaseBookshelfFragment.kt:370-383，幂等 key=bookshelfShowBooknameMigrated，双侧 Fragment onFragmentCreated 调用）
- [x] 4A.2 列表封面正方形 bug（K8）：width+aspectRatio(0.75f) 前置修复，网格/列表/分组封面统一 0.75f
- [x] 4A.3 取色归位（AD-07）：surfaceContainerHigh→UiCorner.surfaceColor(cardColor)；outline/onSurfaceVariant→palette.secondaryText；primary→palette.accent；surfaceVariant track→cardColor；RoundedCard→palette.settings.row+border+actionRadius（基线 B）；角标双态 accent/muted；scrim 遮罩改对齐 archive 纯白字叠印（白字随遮罩豁免，收尾登记 migration-registry）

## 5. 视效对齐 archive（K10 已裁决：全量对齐）

- [x] 5.1 差异清单（design.md 附录 A，8 维度）
- [x] 5.2 A3 全量对齐裁决
- [x] 5.3 实施对齐：行高 heightIn(min) 分档 / 封面尺寸分档 / meta 图标行（Person/History/Schedule 14dp）/ compact 合并单行 / 状态右列（角标+更新时间 11sp）/ 角标双态色 / 书名遮罩对齐 archive（白字 12sp titleFontFamily BottomStart）/ 分组名 minLines=2+titleFontFamily / 分组列表副文本 / 网格 contentPadding margin 联动 / 封面投影 bookCoverShadow 开关 / 字体 titleTypeface 注入
- [x] 5.4 临时日志：本任务未插桩，Grep Log.d/Log.e = 0 残留
- [x] 5.5 updateLog.md 已更新（08/29 优化段 8 条，面向用户语言）

## 6. 验证

- [x] 6.1 编译门禁：`compileAppDebugKotlin` **BUILD SUCCESSFUL in 8m 5s**（第一轮 3 类错：FontFamily 包裹/import 重复/Icons.AutoMirrored.Outlined.History；第二轮 2 类错：prefBool 扩展 import/重复 import；第三轮通过）
- [x] 6.2 静态核验：Grep 事件发布+双侧消费/migrate/双 cancel 存在；BookshelfScreen 无 Log/无 colorScheme.surface/outline/onSurfaceVariant 残留；调用点仅 Fragment1/2
- [ ] 6.3 真机 L2 场景 A-F（**用户裁决延后**，登记 R2 复测：订阅 modern→classic 顶栏、书架布局/书名/边距即时生效、K7 迁移后书名显示）

## 7. 收尾

- [x] 7.1 文档同步：how-to.md 严禁清单 +13/14 条（配置快照禁令/collector 泄漏禁令）；INDEX 状态流转
- [x] 7.2 用户验收（检查点 2 通过 2026-08-29 00:45 + 检查点 3 终验收通过 2026-08-29 00:55）
- [x] 7.3 daemon 清理 ✅、migration-registry 六.3 豁免登记 ✅

## 8. 真机复测反馈修复（2026-08-28 深夜，用户复测订阅切换仍异常）

- [x] 8.1 真机日志插桩（`RssModeSwitch` tag，7 点位：NOTIFY_MAIN/onResume/applyRssMode/applyClassicRssMode/modernCollector/renderRssSourceSelector/upTabLayout）+ 诊断包 082823 构建
- [x] 8.2 MEmu 自动化复现（uiautomator2 直连 subscriptionConfig 路由）+ logcat 锁根：**切换链路正常（事件收到/切换执行/collector 取消/胶囊提交），真残留源=rss_fragment_container 全屏容器 classic 侧未隐藏（z 序最高盖住经典列表）**——082822 包不含此修复
- [x] 8.3 修复：applyClassicRssMode 补 rssFragmentContainer/rssWebContainer/pbRssLoading 隐藏（对齐 applyModernRssMode 对称性）+ destroyModernRssChildren 改 commitNow 同步移除（RssFragment.kt:407-413/446-449）
- [x] 8.4 增量构建 BUILD SUCCESSFUL（2m32s）→ 装机复现：onResume needSwitch=false 状态一致 ✅（截图视觉验证受 ViewPager2 多 tab 叠加与截图审查限制，最终确认交用户复测）
- [x] 8.5 交付包：output\apk\test\legado_miss_app_3.26.082823.apk（23:57:53，67.35MB，含全部修复+诊断日志）
- [ ] 8.6 用户复测通过后：移除 RssModeSwitch 插桩日志 + 删诊断脚本（diag_rss_switch/diag_topbar_dump/diag_topbar_classify）+ 最终包
- [ ] 8.7 真机 L2 场景 A-F（含书架配置即时生效）仍待用户复测