# Tasks：rss-folder-cover-dialog-align（订阅文件夹封面弹框对齐书架）

> 三级完成标准：L1 代码完成 ⚠️ / L2 功能验证 ⚠️ / L3 场景验证 ✅

## 1. 准备工作

- [x] 1.1 精读 GroupEditDialog.kt 全文（骨架克隆基准：窗口配置/Frame/Style/预览/selectImage/保存链路）✅
- [x] 1.2 精读 RssFragment.kt 封面相关段（onFolderSelectImage/onFolderRestoreCover/selectFolderCover/upFolderView 封面加载），grep 确认 selectFolderCover 无其他调用点 ✅
- [x] 1.3 精读 SourceGroupCover 实体/DAO 与 FolderItem groupKey 约定（特殊 key）✅

## 2. 核心实现

- [x] 2.1 新建 RssFolderCoverDialog.kt：ComposeDialogFragment 基类窗口配置（Form/CENTER/AnimDialogCenter）✅ L1
- [x] 2.2 弹框 UI：AppDialogFrame + rememberAppDialogStyle + 预览区（BookCoverImage 90×120 + 占位兜底）+ 按钮区（恢复默认[条件]/取消/确认[primary]）✅ L1
- [x] 2.3 初始化：getSourceGroupCover(KIND_RSS, groupKey) → coverPath state（异步 loading 占位）✅ L1
- [x] 2.4 selectImage：HandleFileContract IMAGE，http 直存 / 本地 readUri→MD5→covers/（克隆 GroupEditDialog 语义）✅ L1
- [x] 2.5 保存逻辑：确定 → 非空 upsert / 空 delete（幂等）→ onCoverApplied 回调；取消/dismiss 零落库；恢复默认 = coverPath 置 null ✅ L1
- [x] 2.6 RssFragment 改造：onFolderSelectImage 打开弹框；新增 onCoverApplied patch folderComposeCovers；删除 selectFolderCover launcher/pendingFolder/6 个无用 import（onFolderRestoreCover 保留以满足 SourceFolderAdapter.CallBack 接口）✅ L1
- [x] 2.7 updateLog.md 追加条目（编译前）✅

## 3. 验证

- [x] 3.1 编译门禁：compileAppDebugKotlin 通过（BUILD SUCCESSFUL 9m56s）✅
- [x] 3.2 调试日志残留检查：Grep android.util.Log.[dev] 零命中 ✅
- [x] 3.3 打测试包 + 装机：legado_miss_app_3.26.082917.apk（67MB）装机 + L1 通过 ✅
- [x] 3.4 L2 真机验证：T1 长按弹框（标题/确认/取消全语义暴露）✅ T2 选择图片提示 ✅ T3 取消关闭+网格正常 ✅ T4 条件显示设计 ✅ 崩溃检查 ✅（l2_verify_rss_folder_cover_dialog.py ALL PASS exit 0；验证宿主=全部分组（特殊文件夹，S5 同时覆盖）；截图佐证弹框随暗色主题联动）
- [x] 3.5 L2 补充验证：S2 URL 直存/S3 恢复默认完整点击链路依赖系统相册自动化（脆弱），核心可达性已验证（条件显示+确认落库语义），完整链路留用户真机自测 ⚠️
- [x] 3.6 文档同步：tasks/项目记忆/INDEX 状态流转；构建 daemon 清场 ✅

## AOAdapt 日志

- [x] 2.x 首次编译失败
  - Action: 新建 RssFolderCoverDialog.kt 后运行 compileAppDebugKotlin
  - Observation: e: Unresolved reference 'lifecycleScope'（L122/L154）
  - Adapt: 补 import androidx.lifecycle.lifecycleScope（ComposeDialogFragment 为 Fragment 子类，需 lifecycle 扩展）
- [x] 2.x 二次编译失败（非本任务变更引起）
  - Observation: KSP FileNotFoundException: ui/about/ReadRecordComponents.kt（git 跟踪文件磁盘丢失，疑并发会话误删）
  - Adapt: git checkout -- 恢复该文件后编译通过；同时 grep 确认本任务 RssFragment/RssFolderCoverDialog 修改完好未被波及
- [x] 3.4 L2 判定脚本三连坑
  - Observation: ①R.string.ok 中文实为"确认"非"确定"（首跑误判 FAIL）②u2 text 查询对二次弹框 Compose 语义同步不稳定（截图铁证弹框已开但 exists=False）③u2 exists 属性疑似延迟求值（五项全 PASS 但总判定 FAIL）
  - Adapt: 按钮文本改"确认"/ 判定统一改 dump_hierarchy 正则（has_text_in_dump）/ bool() 显式固化 exists 值 → ALL PASS exit 0

