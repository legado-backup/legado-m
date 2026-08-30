# 测试发现的问题清单：precise-manage

> **创建时间**：2026-08-08
> **用途**：记录真机测试中发现的所有问题，防止压缩上下文后丢失
>
> **权威源性质**：补充权威源（主权威源是 tasks.md，本文件是问题追踪的补充）
> **压缩恢复后**：必须读取本文件才能完整恢复任务状态

## 问题状态统计

- 总计：1
- 待修复：0
- 修复中：0
- 已修复：1

## 问题列表

### Issue-1: DownloadManageActivity `<init>` 期构造 Adapter 崩溃（onCreate 之前访问系统服务）

- **发现时间**：2026-08-08 真机 L2 验证
- **发现方式**：l2_verify_precise_manage.py 下载管理场景，logcat 捕获 FATAL
- **错误信息**：
  ```
  java.lang.IllegalStateException: System services not available to Activities before onCreate()
      at android.view.LayoutInflater.from(Activity.java:6097)
      at io.legado.app.base.adapter.RecyclerAdapter.<init>(RecyclerAdapter.kt:30)
      at io.legado.app.ui.download.DownloadTaskAdapter.<init>(DownloadTaskAdapter.kt:16)
      at io.legado.app.ui.download.DownloadManageActivity.<init>(DownloadManageActivity.kt:34)
  ```
- **根因**：`DownloadManageActivity.kt:34` 类属性初始化时 `private val adapter = DownloadTaskAdapter(this)`，而 `RecyclerAdapter` 构造里 `LayoutInflater.from(context)` 在 Activity `<init>`（onCreate 前）调用 `getSystemService`，系统服务此时不可用
- **修复方案**：改为 `private val adapter: DownloadTaskAdapter by lazy { DownloadTaskAdapter(this) }`（lazy 确保 onCreate 后首次访问才构造，与本项目其他 Activity 标准模式一致）
- **修复状态**：已修复。重编译安装后直接启动 DownloadManageActivity 无 FATAL；L2 全量 6/6 通过
- **影响范围**：仅下载管理页首次进入崩溃；崩溃页面为 DownloadService 桥接 + DownloadState 查询
- **教训**：Activity 的成员属性若在构造期依赖 Context/LayoutInflater，必须 `by lazy`；真机验证有效捕获了 JVM 单测无法覆盖的 Activity 生命周期问题