# tasks.md — video-regression-fix-0906

## 1. 准备工作
- [x] 1.1 分支确认（master 最新 ef7bf8b55 之后）与工作区干净校验
- [x] 1.2 备份待改文件到 bak/video-regression-fix-0906/（VideoPlayerActivity/VideoPlay/VideoPlaybackPipeline/DohDns/BookInfo 两版/MyFeatureBooks/ExploreShowActivity）
- [x] 1.3 重读关键文件确认当前符号位置（并发规范：Edit 前必 Read）

## 2. 核心实现

### 修复1a：解码失败重建重试
- [x] 2.1 VideoPlayerActivity 播放错误处理处拦截 4003（ERROR_CODE_DECODING_FAILED）：同 token 未重试过 → 释放重建播放器同 URL 重试一次
  - 验证标准：Read 核对重试守卫（token+单次标记）；AppLog 留"解码失败重建重试"标记
- [x] 2.2 重试仍失败走既有"播放失败"提示（不无限重试）
  - 验证标准：Grep 确认重试计数逻辑单次生效

### 修复1b：DoH server#2 熔断
- [x] 2.3 DohDns：server#2 连续失败计数 ≥5 → 会话级熔断（解析与 preheat 均跳过），AppLog 留熔断标记
  - 验证标准：Read 核对计数与熔断条件；模拟器日志观察熔断后仅 #1 解析

### 修复2：书源切布局短路重采集
- [x] 2.4 startPlayBookChapter/Pipeline 入口快速路径：book 非空 && videoUrl 非空 && chapter 未变 → 跳过 invalidate/getContent/嗅探直接 setUp+seekOnStart
  - 验证标准：Read 核对守卫条件非空壳；AppLog 留"短路重采集"标记
- [x] 2.5 复用起播失败自动回退全量采集链（onError 清 videoUrl 重走一次）
  - 验证标准：Read 核对回退分支

### 修复3：书源上滑恢复
- [x] 2.6 队列兜底注入：BookInfoActivity/BookInfoComposeActivity/MyFeatureBooksActivity 启动播放器前 VideoPlaylistHolder.set（兄弟列表或单元素）
  - 验证标准：Grep 三处 set 调用存在；详情页直进后 VideoPlaylistHolder.containsBookUrl 为真（真机）
- [x] 2.7 switchToBookFromList 邻居空时降级 upDurIndex（仅 offset 未越出集内边界），越界直接 toast；**严禁再转投 switchToBookFromList（防 upDurIndex↔switchToBookFromList 互递归，红队 R2 实锤）**
  - 验证标准：Read 核对降级分支无回环路径；真机上滑单集书源 toast 边界提示；末集上滑不卡死
- [x] 2.8 onBookVerticalFling 静默返回改 toast
  - 验证标准：Grep 无静默 return 残留

### 修复4：分类列表页三点
- [x] 2.9 ExploreShowActivity：moreButton 接 ModernActionPopup（"第 N 页"复用 NumberPickerDialog），删除三横线 pageButton
  - 验证标准：Read 核对监听存在；真机点击弹出菜单且跳页行为与原按钮一致；Grep pageButton 零残留

## 3. 验证测试
- [x] 3.1 编译：build-legado.bat（构建前 Get-Process 校验）
- [x] 3.2 updateLog.md：git diff 三步流程追加（编译前）
- [x] 3.3 L2 真机（测试包，l2_verify_ui_batch_fix_0905.py 扩展场景 + 手动项）：
  - [x] 3.3.1 快速连续切换视频（≤2s 间隔 5 次）无"播放失败"终态；4003 注入路径重建重试成功（日志标记）
  - [x] 3.3.2 书源切布局：秒级起播（无三层嗅探等待），日志"短路重采集"标记；失效回退分支日志可观测
  - [x] 3.3.3 书源上滑：列表入口跨影片切换；详情页直进集内切换；边界 toast
  - [x] 3.3.4 分类列表页三点弹菜单+跳页；发现主页分组弹窗回归
  - [x] 3.3.5 DoH 熔断：模拟器断 server#2 场景（或日志观察）仅 #1 解析
  - [x] 3.3.6 回归：ui-batch-fix-0905 T1-T8 全量重跑（防本次改动破坏上批修复）
- [x] 3.4 四错误模式 + FATAL 计数 = 0（logcat 扫描）

## 4. 文档收尾
- [x] 4.1 docs/specs/video-booksource-align-rss/design.md 追加 AD-04 增补记录；issues-found.md 记录真机问题
- [x] 4.2 临时日志清理（SwipeTest/log.d Grep 清零）；bak 清理；git 提交推送 origin+gitee
- [x] 4.3 INDEX.md 状态流转；SOP 脚本表如新增场景同步登记
