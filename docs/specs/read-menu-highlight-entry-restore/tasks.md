# tasks — 阅读页三个点菜单补回漏挂动作项（7 项）

## 1. 准备
- [x] 1.1 git 排查入口消失根因（e706bae53 漏译，非有意移除）
- [x] 1.2 全面排查：XML `book_read.xml` 全量逐项比对 Compose 三个点弹层，确认漏挂 6 项（高亮规则/设置字符集/TXT目录规则/删除注音标签/删除H标签/核心调度模式）；底部按钮行（可配置体系）与长按子弹层（换源/刷新）无漏项；`menu_enable_review` 为注释死代码非损失
- [x] 1.3 穿透自审：CallBack 实现类唯一（编译安全）；实锤阻塞点 P1（isEpub 语义混淆）+ 存量 bug（段落规则在普通 EPUB 误显示，第 7 项）；修正 TXT目录规则/设置字符集"唯一入口"误判（目录页/离线缓存页有替代入口）

## 2. 核心实现
- [x] 2.1 ReadMenuComposeComponents.kt：`ReadMenuTitleBarState` 拆 3 字段（isLocalTxt/isEpub 真实值/isEpubCoreMode）；`ReadMenuTitleBarActions` +6 回调；`buildOverflowActions` 扩参 +6 条件动作项（按 XML 相对顺序精确插入）+ 段落规则条件改真实 isEpub；勾选态读 ReadBook.book；三点 clickable 透传 ✅ Level1（Grep 产出验证：L77/827/860/893 关键段在位）
- [x] 2.2 ReadMenu.kt：`CallBack` 接口 +6 方法；调用点 wiring；state 构造补 3 字段（isEpub 改读 ReadBook.book?.isEpub）✅ Level1（L389-392/418-423/845-850 验证在位；补 isLocalTxt 扩展属性 import）
- [x] 2.3 ReadBookActivity.kt：实现 6 个 CallBack 方法；del ruby/h tag 翻转逻辑提取为私有方法 toggleDelTag 供 XML 路径与新回调共用 ✅ Level1（L4893-4935 + L940-948 验证在位；showCharsetConfig 由 BaseReadBookActivity 既有 final 方法自动满足接口）

## 3. 验证
- [x] 3.1 编译门禁：`./gradlew compileAppDebugKotlin` BUILD SUCCESSFUL ✅（第一轮失败 2 错误已修，见 AOAdapt）
- [x] 3.2 L2 真机验证 ALL PASS ✅ Level3（固化脚本 `l2_verify_read_menu_overflow.py`，APK legado_miss_app_3.26.083019.apk 装机）：
  - S1 高亮规则管理：弹层存在 + 位置校验（添加书签 top=146 < 高亮规则 top=212）+ 点击进入管理页（12 复选框行）PASS
  - S2 本地性互斥：在线书不含[设置字符集] PASS（书架书为在线书）
  - S3 EPUB 互斥：SKIP（设备书架无 EPUB 样本；条件逻辑经编译+代码审查核验，EPUB/核心模式场景留用户抽验）
  - S4 既有锚点回归：添加书签/反转内容在位 PASS；截图 l2_overflow_s4_0.png 佐证 11 项顺序与替换净化勾选态不变
  - logcat：App 进程 0 FATAL（FATAL 均为 uiautomator dump 工具进程自身冲突，与 App 无关）
- [x] 3.3 Grep 确认无临时日志残留 ✅（ui/book/read 包 Log.d/e、println 0 匹配）

## 4. 交付物
- 测试包：output/apk/test 或 app/build/outputs/apk/app/debug/legado_miss_app_3.26.083019.apk（已装机）
- 固化脚本：ai_tests/scripts/l2_verify_read_menu_overflow.py（新增）
- 辅助探针：ai_tests/scripts/probe_shelf.py（书架层级探针，复用价值）

## AOAdapt 日志

- [x] 1.1 初判仅高亮规则 1 项漏挂
  - Action: 按用户"全面排查"要求，对 book_read.xml 26 项做全量逐项比对（含处理逻辑调用链核查）
  - Observation: 另有 5 项同批漏挂（字符集/目录规则/EPUB×3），均为"处理逻辑存在但入口丢失"特征
  - Adapt: 设计范围从 1 项扩大为 6 项，spec/design/tasks 同步重写
- [x] 1.3 二轮穿透自审发现阻塞点与存量 bug
  - Action: 核查 CallBack 实现类、isEpubCoreBook() 实现语义、全库替代入口
  - Observation: ①isEpubCoreBook()=isEpub&&useExperimentalEpubCore，现 wiring 混用致普通 EPUB 书段落规则误显示（存量 bug）②ruby/H 若沿用现 wiring 会漏显 ③TXT目录规则/字符集有替代入口（修正误判）
  - Adapt: State 拆 isEpub/isEpubCoreMode 双字段（AD-03）；范围扩为 7 项；设计文档同步修订
- [x] 3.1 编译第一轮失败 2 错误
  - Action: compileAppDebugKotlin 首跑 FAILED，捕获 `e:` 行定位
  - Observation: ①ReadMenu.kt:390 Unresolved isLocalTxt——Book.isLocalTxt 是 BookExtensions.kt:58 扩展属性，缺 import ②OkHttpStreamFetcher.kt:75 internal 函数暴露 private 返回类型——HEAD 9ba0aac3d（并行会话画质增强提交）即带编译断裂，与本任务无关但阻塞门禁
  - Adapt: ①补 `import io.legado.app.help.book.isLocalTxt` ②BoundedRead 改 `internal class`（最小修复，与测试文件访问需求一致）；教训：HEAD 提交未过编译门禁即推送，门禁失败先归因再修
- [x] 3.1 IDE 工具通道故障（复现 ng-benchmark 同类）
  - Action: 二轮编译后台运行中，CheckCommandStatus/RunCommand/Glob 相继超时，Edit 对确认存在的字符串报 not found，Write 超时
  - Observation: Read 通道存活（文件可读且内容完整），命令/编辑通道间歇性卡死；判定为 IDE 命令通道过载（Kotlin 编译 daemon 高 CPU）而非文件真实变更；用户裁决"立即重试"
  - Adapt: 切换 Read/Grep/Write 文件通道继续工作（tasks.md 改用 Write 全量重写，重试后落盘）；命令通道恢复后续跑编译
- [x] 3.2 L2 脚本三连修（uiautomator 残留/开书锚点/弹层滚动）
  - Action: 首跑 AccessibilityServiceAlreadyRegisteredError → 次跑书架打不开书 → 三跑弹层滚动采不到帮助
  - Observation: ①前会话残留 com.github.uiautomator 进程占锁 accessibility（pkill -f 误杀自身，须 ps 定位 PID 精确 kill）②书架卡片文本节点 clickable=False 且点击先进详情页（需"阅读/继续阅读"二跳）③弹层锚定右上角，x=0.5w 的纵向滑动落在遮罩上直接 dismiss 弹层
  - Adapt: ①定点 kill 20332 ②开书流程兼容详情页二跳 ③滑动 x 改 0.70w 仍被弹层手势吞掉——放弃脚本内滚动，S4 硬断言改用可靠捕获的顶部/中部锚点（添加书签/反转内容），底部项以截图 l2_overflow_s4_0.png 佐证；沉淀：ModernActionPopup 弹层对纵向滑动敏感，脚本勿在弹层上做滚动手势
