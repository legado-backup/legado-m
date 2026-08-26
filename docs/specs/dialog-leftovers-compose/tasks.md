# tasks.md — 弹框遗留项 Compose 化：autoTask / urlrecord 旧 View 弹框迁移

## 1. 基类与组件接入（前置）

- [x] 1.1 确认 `ComposeDialogFragment` 基类（`dialogTheme`/`dialogSize`/`dialogGravity`）与 `AppDialogFrame`/`rememberAppDialogStyle` 可用，无版本差异
- [x] 1.2 确认 `dialog_recycler_view` 布局尚有其它复用者（EffectiveReplaces/ChangeRssArticleSource/AppLog/ReadRecord/Servers/CrashLogs/IconListPreference/KeyboardAssistsConfig），**保留布局不删**
- [x] 1.3 确认 `CodeDialog` / `WaitDialog` 原样可用，import 弹框继续按现状复用

## 2. AutoTaskLogDialog Compose 化（最轻量）

- [x] 2.1 `AutoTaskLogDialog` 改继承 `ComposeDialogFragment`，`dialogSize=AppDialogSize`（对应原 `0.9f,WRAP_CONTENT`）
- [x] 2.2 工具栏标题等价迁移：`taskName` 空则 `getString(R.string.log)`；清空动作（原 `R.menu.app_log` 的 `menu_clear`）收敛为界面内动作按钮
- [x] 2.3 单条日志展示：读 `AutoTask.getRules().firstOrNull{it.id==taskId}` 得 `lastRunAt`/`lastLog`/`lastError`/`lastResult`，无则「未运行」占位；时间用 `LogUtils.logTimeFormat`
- [x] 2.4 清空动作调用 `AutoTask.update(taskId){it.copy(lastLog=null,lastError=null,lastResult=null)}` 并刷新列表为「未运行」
- [ ] 2.5 编译通过（`assembleAppDebug`）+ 真机回归（标题/清空/未运行占位）

## 3. ImportAutoTaskDialog Compose 化（中高复杂度）

- [x] 3.1 `ImportAutoTaskDialog` 改继承 `ComposeDialogFragment`，保留 `viewModels<ImportAutoTaskViewModel>()` 与 `RESULT_KEY` 常量
- [x] 3.2 `importSource` 解析链路（`importSourceAwait`：单 JSON→JSON 数组→URL 拉取→本地文件/剪贴板→错格式异常）不变，接入解析
- [x] 3.3 loading（原 rotateLoading）与错误/空提示（`errorLiveData` / `successLiveData<=0` 显示格式错误）改为受控渲染
- [x] 3.4 列表行：`checkTasks` 比对状态映射「新 / 更新 / 已存在」，行勾选 `selectStatus` + 行点击切换勾选 + `tvOpen` 打开 `CodeDialog`
- [x] 3.5 底部动作：`tvCancel` 关闭、`tvFooterLeft` 全选/取消全选 + `upSelectText()` 计数、`tvOk` 校验选中集合 → `importSelect` → `WaitDialog` 遮罩 → 完成回调
- [x] 3.6 完成回调/关闭：`parentFragmentManager.setFragmentResult(RESULT_KEY, bundleOf("refresh" to true))`；`finishOnDismiss` 时 `onDismiss` 中 `activity?.finish()`；`onCodeSave` 更新 `allTasks[index]`
- [ ] 3.7 编译通过（`assembleAppDebug`）+ 真机回归（剪贴板批量导入/勾选全选/逐条编辑/导入成功后父页刷新）

## 4. urlrecord 详情弹框 Compose 化

- [x] 4.1 `UrlRecordActivity.showDetailDialog()` 替换为 Compose 详情弹框（`AlertDialog`/`ConfirmDialog` 样），展示方法/状态/耗时/时间/域名/URL/来源标识
- [x] 4.2 复制按钮回调 `sendToClip(item.url)`；返回/取消可关闭
- [ ] 4.3 编译 + 真机回归（详情字段完整、复制有效）

## 5. urlrecord 过滤弹框收敛单套底部弹框（两级合一）

- [x] 5.1 新增 `UrlRecordFilterSheet`（`ComposeDialogFragment` + `dialogGravity=BOTTOM`），承载「类别 → 值」两级选择
- [x] 5.2 类别级：域名 / 来源 / 方法 / 状态 / 清除过滤；保留四态 `filterDomain`/`filterSourceName`/`filterMethod`/`filterSuccess`
- [x] 5.3 值级：DAO 查询（`flowAllDomains`/`flowAllSourceNames`/`flowAllMethods`）仍在 Activity 协程取，选值后写 `filter*` 并 `loadData()`；值表为空时提示「无可用值」
- [x] 5.4 清除过滤重置四态并 `loadData()`；类别/值切回交互连续
- [ ] 5.5 编译通过（`assembleAppDebug`）+ 真机回归（四维过滤各值回流、清除过滤恢复全量、切换不卡顿）

## 6. 收尾与登记对齐

- [x] 6.1 `migration-registry.md` E1 表回填 7.11an（autoTask 两弹框）/ 7.11an2（urlrecord）状态，与源码一致
- [ ] 6.2 本 spec `README.md` 状态「🔄 设计中」→「✅ 已完成」；`docs/INDEX.md` 登记本 spec
- [ ] 6.3 `updateLog` 编译前同步追加（迁移前补写）
- [ ] 6.4 残留调试日志确认（Grep `android.util.Log.d|Log.e` 0 残留）
- [ ] 6.5 全量回归（autoTask 触发日志入口、导入入口、urlrecord 详情/过滤入口可达性，含墨水瓶模式）

## AOAdapt 日志

- 待实施阶段记录：遇到问题按 `Action → Observation → Adapt` 追加。