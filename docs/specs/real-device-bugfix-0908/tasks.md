# real-device-bugfix-0908 子任务

> 规格：./spec.md。红队 ≥3 轮记录见 tasks.md 末尾。验收：每项自测通过 + 模拟器 L2。

## 子任务
- [x] T1 Bug2 替换净化双搜索框：ReplaceRuleActivity initComposeContent 改 GONE（titleBar/selectActionBar）+ 注释修正
- [x] T2 Bug5 订阅栏目文件夹残留：RssFragment.applyModernRssMode 补 folderComposeView.gone()
- [x] T3 Bug4 书架媒体删除：MySettingsData 入口+路由 / MyFeatureBooksActivity / Manifest / 字符串（values+values-zh）
- [x] T4 Bug3 透明弹框：SourcePickerPanel 补 surface 背景 + ComposeDialogFragment dim 补偿（dialogAlpha<100 时按比例提升 dimAmount）
- [x] T5 Bug1 域名分组卡死止血：①删 sourcesSignature 巨串改 dataVersion ②域名模式扁平 RowModel+items(key) ③hostMap 收敛 IO 线程局部表 ④SnapshotListUpdates equals no-op
- [x] T6 统一自测：模拟器安装 → 逐 bug L2 → 零 FATAL（详见下方 L2 留痕）
- [x] T7 提交推送 + updateLog + INDEX 登记

## L2 自测留痕（l2_verify_bugfix_0908.py，白名单固化）
- 环境：MEmu 实例0（127.0.0.1:21503），包 io.legado.miss.app.debug，APK 3.26.090800（updateLog 第九批已入包）
- **t1 替换净化**：resumed=ReplaceRuleActivity，EditText 计数=1（无重复搜索框）✅
- **t2 订阅栏目**（全 UI 复刻用户路径：我的→主题设置→发现与订阅→订阅页管理 + 订阅栏目三点菜单→布局设置→按分组+文件夹）：
  步骤A（经典+文件夹）folder_compose_view=V ✅；步骤B（UI 切新版订阅后）folder_compose_view=G 且 recycler_view=G（无残留）✅
- **t3 我的入口**：dump 文本节点 26 个，"书架媒体"命中=False；MyFeatureBooksActivity 启动报不存在 ✅
- **t4 弹框 dim 补偿**：dialogAlpha=60 写入回读通过，"同步任务"弹框（PackageSyncTaskDialog）打开+节点可达，弹框窗口带 DIM_BEHIND 标志 ✅。
  ⚠️ 环境限制：本 MEmu 实例 screencap 全黑（已知 GPU 渲染故障，重启实例无效），dim 数值/亮度差判定留真机人工复核
- **t5 万级书源域名分组**：DB 合成 10500 条（200 主机×52 源）→ 更多菜单→按域名分组显示 点击生效 → 页面存活、ANR=0、FATAL=0 ✅。
  ⚠️ 环境限制：uiautomator dump 在万级行上可访问性树过重（52s 超时返回空树），分组头渲染断言为 best-effort，真机复核滚动流畅度
- 全场景 FATAL EXCEPTION 计数 = 0
- 测后清理：合成源已从模拟器 DB 删除

## 红队对抗审查记录
- [x] R1 正确性/回归面：GONE 替代 removeView 需防与父容器假设耦合（本布局两者不同父容器，removeView 静默 no-op 实锤）；RssFragment 只补 folderComposeView 隐藏不影响经典自愈路径；ComposeDialogFragment dim 补偿 E-Ink 分支不受影响、alpha=100 零改动
- [x] R2 边界/性能：T5 host 表随 flow map 步（IO）构建，消除主线程写 Map；dataVersion 仅在实际变更时递增，identical 重发射不触发 UI 重置；replaceAt 等值 no-op 消除 O(n) 移位
- [x] R3 盲区/兼容性：t2 需全 UI 路径验证（shell am start 非导出 Activity 会回落桌面，prefs 直写会被外观套件快照机制覆盖——均实测沉淀）；t5 需容忍低配模拟器 uiautomator 固有限制，判定口径以稳定性证据为主
