# Tasks：rss-folder-cover-dialog-align（订阅文件夹封面弹框对齐书架）

> 三级完成标准：L1 代码完成 ⚠️ / L2 功能验证 ⚠️ / L3 场景验证 ✅

## 1. 准备工作

- [ ] 1.1 精读 GroupEditDialog.kt 全文（骨架克隆基准：窗口配置/Frame/Style/预览/selectImage/保存链路）
- [ ] 1.2 精读 RssFragment.kt 封面相关段（onFolderSelectImage/onFolderRestoreCover/selectFolderCover/upFolderView 封面加载），grep 确认 selectFolderCover 无其他调用点
- [ ] 1.3 精读 SourceGroupCover 实体/DAO 与 FolderItem groupKey 约定（特殊 key）

## 2. 核心实现

- [ ] 2.1 新建 RssFolderCoverDialog.kt：ComposeDialogFragment 基类窗口配置（Form/CENTER/AnimDialogCenter）
- [ ] 2.2 弹框 UI：AppDialogFrame + rememberAppDialogStyle + 预览区（BookCoverImage 90×120 + 占位兜底）+ 按钮区（恢复默认[条件]/取消/确定[primary]）
- [ ] 2.3 初始化：getSourceGroupCover(KIND_RSS, groupKey) → coverPath state（异步 loading 占位）
- [ ] 2.4 selectImage：HandleFileContract IMAGE，http 直存 / 本地 readUri→MD5→covers/（克隆 GroupEditDialog 语义）
- [ ] 2.5 保存逻辑：确定 → 非空 upsert / 空且有旧值 delete → onCoverApplied 回调；取消/dismiss 零落库；恢复默认 = coverPath 置 null
- [ ] 2.6 RssFragment 改造：onFolderSelectImage 打开弹框；新增 onCoverApplied patch folderComposeCovers；删除 selectFolderCover launcher 与旧落库链路、onFolderRestoreCover 遗留入口
- [ ] 2.7 updateLog.md 追加条目（编译前）

## 3. 验证

- [ ] 3.1 编译门禁：compileAppDebugKotlin 通过
- [ ] 3.2 调试日志残留检查：Grep android.util.Log.[de] 零命中
- [ ] 3.3 打测试包 + 装机（quick_build_install.py）
- [ ] 3.4 L2 真机验证 S1（长按弹框/预览/选图/确定即时刷新）+ S4（取消不落库）+ S6（主题联动）
- [ ] 3.5 L2 补充验证 S2（URL 直存）+ S3（恢复默认）+ S5（特殊文件夹）
- [ ] 3.6 文档同步：tasks/项目记忆/INDEX 状态流转；构建 daemon 清场

## AOAdapt 日志

（实施过程中记录）
