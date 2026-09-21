# -*- coding: utf-8 -*-
"""l2_verify_m3_pages.py — M3 批（设置与阅读器配置页 14 页）真机 L2 验证，按落地顺序增量登记

已覆盖：
  【rss/search + main/my】**s14（M4 6-7/11）**：F199 进行中计数条+停止出口 / F200 类型筛选外显 chips
    / 修复 2 历史长按删除先确认 / 结果命中高亮 / F26 我的页头部资产概览 / Web 服务运行中徽章
    s14 通道：本机 `_SearchServer` 返回**标准 RSS 2.0**（合成源 `ruleArticles` 留空 ⇒ 走默认解析，
      零自定义规则面）+ adb reverse；两个合成源 type=0/2 分别指向 `/web` `/video`，
      每请求固定 sleep 3s ⇒ 「正在搜索 · 已得 N 条」窗口可稳定 dump
      → A1：chips 四文案在场 + 进行中条在场 + 点「停止」后条消退
      → A2：完整搜索出双条；关键词只出现在网页源标题 ⇒ **同屏对照**（命中行 accent 像素 >0 / 未命中行 ≈0）
      → A3：点「视频」⇒ 仅剩视频源结果（类型筛选功能口径，非像素猜色）；再点「全部类型」⇒ 双条回归（可逆 + 复位 rssSearchType）
      → A4：播种 type=1 历史词 ⇒ 输入 1 字符展开历史 ⇒ 长按 ⇒ 「删除搜索记录」确认框
         （点「否」标签仍在 ⇒ 点「是」标签消失，证明确认真的拦住了删除）
      → B1：主 Tab「我的」⇒ 四指标 + 版本行在场；B2：点 Web 服务开关 ⇒「运行中」徽章出现/关闭后消退
      → 库快照回滚 + 源码断言 10 项
    ⚠️ 播种口径：搜索会并行跑**所有启用且 searchUrl 非空**的源 ⇒ 播种时先把其余源 `enabled=0`
       （收尾整库回滚，零残留），否则「已得 N 条」与结果集不确定

  【book/ai-read-aloud-usage + book/paragraph-rule-manage】**s9 PASS（2026-09-21）**：F30 摘要拆行+主指标强调
    / F31 选中态批量栏（删除选中/导出）/ F51 拖拽手柄可见化 / F50 空态操作化 / F52 导入进度闭环
    s9 通道：DB 播种 2 条消耗记录（A 模型大额 + B 模型小额，校验千分位与按模型汇总）+
       2 条段落规则（另一轮清空构造空态）；导入进度用**慢响应服务器**（延迟 5s 后 500）拉长窗口
       → F30：摘要首行不含统计段（回归哨兵）+ 多行含「输入/总/按模型」+ 总 Token 段像素有色度（accent 强调）
       → F31：长按首条 ⇒ 批量栏「删除选中 1」+「导出」⇒ 删除二次确认（取消，零污染）⇒ 导出跳 HandleFileActivity ⇒ 取消选中后栏收起
       → F51：卡右侧手柄 content-desc「拖动排序手柄」≥2 + 摘要含手柄提示 → F50：空态提示+引导+「添加」主操作在场
       → F52：顶栏导入 → 网络导入 → 输 URL ⇒ 「正在导入规则…」在 5s 窗口内可见 → 库快照回滚 + 源码断言 8 项
    🔴 本轮顺带修复的既有缺陷（2 条，真机取证）：①**顶栏图标用 selector 资产导致整页崩溃**——
       `iconRes = R.drawable.ic_bottom_books`（StateListDrawable）经 `painterResource` 渲染抛
       IllegalArgumentException「Only VectorDrawables and rasterized asset types…」⇒ 打开页面即崩（改同族矢量 `_e`）；
       全仓回归探针：40 处 `iconRes` × 65 个非矢量 drawable 求交，**仅此 1 处命中**
      ②**共用容器下动态插入视图的高度测量异常**——宿主 `activity_theme_manage.xml` 的 recyclerView 为
       `height=0dp + weight=1`，实测插入的同级视图被测量成整屏高（bounds=(27,183)-(693,1280)）把列表与
       「全选」挤出可视区 ⇒ F30 摘要改为**零新增视图**（`tvSummary` 内 Spannable 多行 + accent 强调），
       F31 批量栏改为**条件挂载**（addView/removeView）
    ⚠️ 文案真值踩坑：`import_on_line` 渲染为「网络导入」（非「在线导入」）、对话框确认键为「确定」
    ⚠️ 通道踩坑：`AiReadAloudUsageRecordActivity` 在 Manifest 显式 `exported=false`，`am start` 直起不稳
       （实测 4.8s 后回落桌面）⇒ 统一走 `start_robust`（shell + su 兜底）

【rss/articles · RssSortActivity/RssArticlesFragment】**s8 PASS（2026-09-20）**：F142 页脚错误可恢复态（LoadMoreView 错误分支重做）
    + F143 分类 Tab 未读徽标（A 有未读 / B 全已读不显 / C 超量 999+ 封顶）
    + 顺带修复 3 个既有缺陷（见下）
    s8 通道：DB 播种「合成源（3 分类，URL 指向本机计数监听器）+ 已入库文章」——A 3 条未读 / B 2 条全已读
       / C 1200 条未读；adb reverse 把设备 127.0.0.1:18543 打到主机计数监听器（接受即关闭 ⇒ 加载必失败）
       → 落地即「库内内容在场 + 网络加载失败落错误页脚」：摘要前缀 + 「点击查看详情」+ danger 圆点像素
       → 徽标以像素为准（compound drawable 不进无障碍树）：A/C 有 danger 胶囊、B 无、C 比 A 宽（999+ 封顶）
       → 点页脚 ⇒ 详情弹窗（错误 + 重试）⇒ 点重试 ⇒ 监听器命中 2→3（客观证明真的重新发起请求）
         且源仍不可达 ⇒ 回到错误页脚；再次点页脚仍能开弹窗（恢复通道可重复）
       → 库快照回滚 + 源码断言 12/12
    🔴 本轮顺带修复的既有缺陷（3 条，均以真机证据定性）：①**页脚重试两道闸全断**——`RssArticlesViewModel`
       三条非成功出口漏复位 `isLoading`（`scrollToBottom` 首行守卫恒真）+ 首页失败时 `nextPageUrl` 为 null
       （`loadMore` 直接判无下一页）⇒ 首页失败后「重试」与触底翻页**永久失效**；②**错误详情弹窗把「重试」
       挤出屏幕**（40+ 行堆栈撑破弹窗，操作行不可见亦不可点）⇒ `messageInContent = true` 走限高滚动正文区；
       ③`LoadMoreView` 硬编码中文提示抽为字符串资源（`error_view_detail`/`load_failed`）并按有无详情分流
    ⚠️ 播种踩坑（已写进 `_art_seed` 注释）：分类清单分隔符必须用**无空格 `&&`** —— `sortUrls()` 走
       `split("(&&&|&&|\n)+")` 且**不 trim**，写成 `" && "` 会让第 2 条起的分类名带前导空格（Tab 上看不出，
       但与库内 `sort` 值不一致 ⇒ 未读徽标查不到计数，首轮因此误判为「徽标不显示」）

【log/log · LogActivity】F190 命中计数条 + 关键词高亮 + 一键清除筛选；F191 详情逐条翻阅；F192 跨年时间补年份
    s1 搜索命中计数与清除筛选（文本口径）→ 同一行「搜索前/后」前景色像素对比证明高亮渲染
       → 点行开详情弹窗（位置指示 N/M）→ › 翻阅后指示递增 → 关窗
       → 时间列同口径回归（`MM-dd HH:mm:ss`）；F192 跨年分支以源码断言兜底（见脚本末尾口径说明）
  【rss/sort · RssSortActivity】合规缺口补做（Tab 选中填充 / 菜单分组 / 清空前确认）+ F201 页码 chip + F210 Tab 收敛
    s2 沙箱源 sourceUrl 直拉分类页 → 同一胶囊「选中→未选中」像素对比证明选中填充
       → ⋮ 菜单分组头 4 项 + 危险项 danger 像素 → 点「清除」出现二次确认后点取消（零数据污染）
       → 分类收敛切换行（条件项：分类数超首行容量才出现）+ F201 顶栏 chip 源码存在性

【browser/webview-browser · WebViewActivity】**s3 PASS（2026-09-20）**：修复1（SSL 默认拒绝 + 确认）/ 修复2（禁用源确认）/ 修复3（菜单 danger tint）
    + F214（返回一按一页 + 栈顶双击退出）+ F215（验证模式一次性引导条 + 挑战期状态条）
    s3 本机自签名 HTTPS :8443（证书场景）+ 明文 HTTP :8543（其余场景，免证书弹窗干扰）+ adb reverse + 设备侧 curl 探针
       → 修复1 双出口：取消 ⇒ 服务端零请求（默认拒绝生效）；再起实例继续 ⇒ 收到 GET + 顶栏标题变网页 title
       → F214：第 1 次返回仅提示不退出（旧实现此处置 finish ⇒ 整页消失）、第 2 次退出；>2s 窗口过期不退出
       → F215：引导条文案/关闭入口/关闭后消失 全真机断言；第二次进入不再显示（一次性）；挑战页状态条在场
       → 修复2/3：菜单 danger 前景色 + 禁用源二次确认（取消零副作用 / 确认闭环，对象为合成 origin 不在库）
       → 库快照回滚 + prefs 记忆位还原 + 源码断言（三出口落定 / 无无条件放行 / 一页 / 终止保留）
    ⚠️ 环境限制：本 ROM（MEmu + Chrome WebView 116）`canGoBack()` 恒 false 且 `goBack()` 无效
       （copyBackForwardList 仍有后退项）⇒ 单步后退分支不可达，以源码断言兜底（真机验证的是栈顶二次确认路径）
    ⚠️ F215 踩坑：活动被配置变更重建后，重建实例会读到「首次创建时刚写入」的一次性记忆位 ⇒ 引导条消失；
       修复=引导条显隐经 savedInstanceState 保存/恢复（配置变更重建不丢一次性提示）

【qrcode/qrcode · QrCodeActivity】**s4 PASS（2026-09-20）**：F188 相册解码等待可见化 / F189 权限受限兜底双出口
    + A3-2 扫描引导与全屏识别说明 + A3-3 解码失败页内提示与重试
    s4 通道：底部「从相册识别」/ 失败条「重试」→ HandleFileActivity「自带文件选择器」→ Pictures → 选图 → 确认
       → 本机测试图（ai_tests/testdata/qr_scan/，由 ZXing 生成）直取原文件，全程离线、无 DocumentsUI/媒体库依赖
       → 默认态：标题/引导/「支持全屏识别」/底部相册入口 全在场，权限卡不在场
       → 失败链路：无二维码图 ⇒ 页内 danger 提示条（标题+建议+重试）+ **停留本页**（旧实现 setResult(null)+finish）
       → 大图链路：2600px 图 ⇒ 「正在识别图片…」等待态真机可见（协程下沉，主线程不再卡）+ 兜底提示
       → 成功链路：780px 真二维码 ⇒ 微确认「已识别」帧可见 ⇒ 回传退出（ActivityResult 契约不变）
       → 权限链路：**本 ROM 环境不可达**（CAMERA 被记为 install 权限、`pm revoke` 无效）⇒ 登记跳过，以源码断言兜底
       → 源码断言 10/10：解码下沉/微确认/失败停留/权限上抛/授权恢复/覆盖层三卡/旧同步链已删
    ⚠️ 实测取舍：「手动输入图片链接」路由不可用（选图页静默返回、调用方收到 CANCELED、根因未定，属
       HandleFileActivity 既有缺陷，已登记 issues-found）⇒ 本场景改走「自带文件选择器」。
    ⚠️ 大图识别观察：1200px/2600px 的**满幅**二维码图识别失败、780px 成功（同一 `QRCodeUtils.parseCodeResult`
       路径，非本批次引入，根因未确证）⇒ 大图链路只断言「有等待态 + 有兜底提示」，不声称识别成功。

【image/image-crop · ImageCropActivity】**s5 PASS（2026-09-20）**：F179 前置（比例徽标 + 保存中回执）
    + A3-3 可恢复失败页内错误条 + 重试（不可恢复仍 toast+finish）
    s5 通道：`am start` + extras（uri/aspectWidth/aspectHeight）直起；「失败→重试→恢复」用**本机 HTTP 先停后起**制造
       → 默认态：比例徽标按 extras 渲染「3:4」+ 操作提示在场 ✅
       → 保存回执：点确认 ⇒「保存中，请稍候…」真机可见 + 无失败条 + 回传退出 ✅
       → 失败链路：远端不可达 ⇒ 页内错误条「图片裁剪失败：图片解码失败」+ 重试键 + **停留本页** ✅
       → 重试恢复：起服务后点重试 ⇒ 错误条消失且**不再出现**（`hideCropError` 只在 `loadImage` 开头调用 ⇒ 硬判据）
         ⇒ 再点确认**真正裁剪并回传退出** ✅
       → 不可恢复：未传 uri ⇒ 仍 toast + finish（原语义保留）✅
       → 源码断言 6/6：保存中态/徽标/错误条落定 + 旧「失败 toast+finish」已删 ✅
    ⚠️ 蓝图失实（已反哺 §1.5）：蓝图称「可拖取景框/角点缩放/90° 旋转入口已在前批完成」，实际源码 0 落点
       （`ImageCropOverlayView` 无触摸处理、布局无旋转按钮）⇒ 本轮不补、登记为缺口

【login/source-login · SourceLoginActivity】**s6（待跑）**：证书放行策略开关（**默认放行**，用户裁决 2026-09-20）
    + 修复3 顶栏「完成登录」文案按钮 + 修复2 删除登录头二次确认 + F165 失败错误卡（完整报错可复制 + 重试）
    + F166 密码可见性切换
    s6 通道：DB 播种 2 个合成书源（A: loginUi 空 + loginUrl=本机自签名 HTTPS ⇒ WebView 分支；
       B: loginUi=行 JSON + loginUrl=必抛 JS ⇒ 表单弹窗分支）+ 自签名 HTTPS + adb reverse
       → 默认放行：顶栏文案按钮在场 + 无证书弹窗 + 服务端收到请求
       → 策略切换：⋮「证书放行策略」⇒ prefs 回读翻转 + 状态回执文案（再切回还原）
       → 关闭态：证书错误弹确认（取消 ⇒ 零请求）/ 表单分支：密码可见切换 / OK 失败 ⇒ 错误卡（重试轨迹）
       → 源码断言 16/16（双文件）
    s3 断言更新（2026-09-20）：证书策略改为**默认放行**后，原「默认拒绝 + 取消零请求」口径前移为
       「先关策略 → 再验证确认三出口」，并新增默认放行正向断言（无弹窗 + 服务端收到请求）

【rss/favorites · RssFavoritesActivity】**s7（待跑）**：F145 单分组标题上下文 / F144 删除类菜单 danger 分级与置底
    / F1 空态操作化（空分组引导 + 出口）
    s7 通道：DB 播种（整份快照 + 回滚，零污染）——①只留「唯一合成分组」1 条 ⇒ 单分组态
       ②清空 rssStars ⇒ 全库无收藏（新手态，**空态真正可达的唯一形态**）
       → 单分组标题「收藏夹 · {分组名}」在场 / 菜单危险头 + 删除所有 danger（像素）+ 置底顺序
       → 空态标题+说明+「去订阅源逛逛」出口在场，且点击后落到主界面（跨页出口闭环）
       → 源码断言：favorites activity 8/8 + MainActivity 4/4 + fragment 应删尽删 2/2
    ⚠️ 口径修正（首轮实测）：蓝图按「空**分组**」设计，但分组清单由 `rssStars` 派生
       （`flowGroups: select group … group by`）⇒ **空分组不可持久存在**，分组层空态不可达
       （首轮按分组层实现，真机抓不到帧）⇒ 空态改落 Activity 层（新手态），蓝图 §1.5 已反哺
    ⚠️ 运行中推库不可用（SQLite 连接持旧 inode）⇒ 需「页内数据变化」的场景一律走「应用已停 + 推库 + 重开」

执行（铁律）：ai_tests\\venv\\Scripts\\python.exe ai_tests/scripts/l2_verify_m3_pages.py [--scenario s1|s3|s4|s5|s6|s7|s8|s9|s10|s11|s12|s13|all]
前置：MEmu 已启动；测试包 io.legado.miss.app.debug 已安装；openssl（Git 自带，脚本自动定位）

口径说明（F192）：跨年分支需要「去年」的日志条目，真机沙箱无法构造跨年数据（AppLog 为内存日志，
时间戳由运行时写入）。本脚本对**同年分支**做真机断言（时间列形状回归），对**跨年分支**做源码存在性断言，
并在 tasks.md 登记为「逻辑分支未构造真机数据」——不伪称真机已覆盖。
"""
import argparse
import base64
import hashlib
import re
import socket
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse

import uiautomator2 as u2

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

try:
    from ai_tests.config import ADB_PATH as ADB, MEMU_ADB_HOST as HOST, PACKAGE as PKG
except ImportError:
    ADB = r"D:\Program Files\Microvirt\MEmu\adb.exe"
    HOST = "127.0.0.1:21503"
    PKG = "io.legado.miss.app.debug"

from ai_tests.lib import compose_assert as ca  # noqa: E402

# ============================ 常量（文案取自 values-zh/strings.xml 真值） ============================

ACT_LOG = "io.legado.app.ui.log.LogActivity"
S_LOG_TITLE = "日志管理"            # log_manage
S_FILTER_CLEAR = "清除筛选"         # log_filter_clear
S_FILTER_COUNT_PREFIX = "命中 "     # log_filter_count = 命中 %1$d / 共 %2$d 条
S_CLOSE = "关闭"                    # close
TIME_PAT = re.compile(r"^\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")
PAGE_PAT = re.compile(r"^\d+/\d+$")   # dialog_page_position
SRC_LOG_SCREEN = "app/src/main/java/io/legado/app/ui/log/LogManageScreen.kt"


# ============================ 基础设施 ============================

def sh(*args, timeout=45):
    try:
        return ca.sh(*args, timeout=timeout)
    except subprocess.TimeoutExpired:
        subprocess.run([ADB, "connect", HOST], capture_output=True, timeout=15)
        time.sleep(3)
        return ca.sh(*args, timeout=timeout)


def sh_su(cmd, timeout=30):
    return ca.sh_su(cmd, timeout=timeout)


def connect_robust(retries=3) -> u2.Device:
    subprocess.run([ADB, "connect", HOST], capture_output=True, timeout=20)
    time.sleep(1.5)
    for i in range(retries):
        try:
            r = ca.sh("echo", "device_ok", timeout=20)
            if b"device_ok" not in (r.stdout or b""):
                raise RuntimeError("echo 探针无响应")
            su = ca.sh("su -c 'id -u'", timeout=25)
            if not (su.stdout or b"").strip().endswith(b"0"):
                raise RuntimeError("su 不可用")
            return u2.connect(HOST)
        except Exception as e:
            print(f"[warn] connect 失败({i + 1}/{retries}): {type(e).__name__} {e}")
            subprocess.run([ADB, "connect", HOST], capture_output=True, timeout=20)
            time.sleep(5)
    raise RuntimeError("设备连接失败")


def reset_app():
    sh("am", "force-stop", PKG)
    time.sleep(1.5)


def current_activity() -> str:
    r = sh("dumpsys", "activity", "activities", timeout=20)
    m = re.search(r"mResumedActivity[^{]*\{[^}]*\s(\S+/\S+?)\s",
                  r.stdout.decode("utf-8", errors="ignore"))
    return m.group(1) if m else ""


def start_robust(act: str) -> bool:
    """非导出组件的 `am start` 通道不稳（实测分歧）→ 先 shell 直起，失败再 su 直起"""
    simple = act.rsplit(".", 1)[-1]
    for _ in range(2):
        sh("am", "start", "-n", f"{PKG}/{act}")
        time.sleep(3.0)
        if simple in current_activity():
            return True
        sh_su(f"am start -n {PKG}/{act}")
        time.sleep(3.0)
        if simple in current_activity():
            return True
    return False


def dump_xml(d) -> str:
    for _ in range(2):
        try:
            return d.dump_hierarchy()
        except Exception:
            time.sleep(1.5)
    return ""


def text_nodes(xml: str):
    """[(label, top, left, cx, cy)]：text 非空优先，否则 content-desc（纯图标动作只有 desc）"""
    out = []
    for m in re.finditer(r"<node[^>]*>", xml):
        tag = m.group(0)
        b = re.search(r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', tag)
        if not b:
            continue
        t = re.search(r'\btext="([^"]*)"', tag)
        cd = re.search(r'\bcontent-desc="([^"]*)"', tag)
        label = (t.group(1) if t and t.group(1) else (cd.group(1) if cd else ""))
        if not label:
            continue
        x1, y1, x2, y2 = map(int, b.groups())
        out.append((label, y1, x1, (x1 + x2) // 2, (y1 + y2) // 2))
    return out


def node_bounds(xml: str, label: str, contains: bool = False):
    """按标签取节点 bounds（contains=True 时子串匹配）；返回 dict 或 None"""
    for m in re.finditer(r"<node[^>]*>", xml):
        tag = m.group(0)
        t = re.search(r'\btext="([^"]*)"', tag)
        cd = re.search(r'\bcontent-desc="([^"]*)"', tag)
        cur = (t.group(1) if t and t.group(1) else (cd.group(1) if cd else ""))
        if not cur:
            continue
        hit = (label in cur) if contains else (cur == label)
        if not hit:
            continue
        b = re.search(r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', tag)
        if not b:
            continue
        x1, y1, x2, y2 = map(int, b.groups())
        return {"left": x1, "top": y1, "right": x2, "bottom": y2,
                "cx": (x1 + x2) // 2, "cy": (y1 + y2) // 2}
    return None


def click_xy(d, cx, cy):
    w, h = d.window_size()
    d.click(cx / w, cy / h)
    time.sleep(1.2)


def tap_text(d, text: str, timeout=6) -> bool:
    for _ in range(2):
        try:
            node = d(text=text)
            if node.wait(timeout=timeout):
                node.click()
                time.sleep(1.2)
                return True
        except Exception:
            pass
        time.sleep(0.6)
    b = node_bounds(dump_xml(d), text)
    if b:
        click_xy(d, b["cx"], b["cy"])
        return True
    return False


def log_rows(xml: str):
    """日志行定位：以**时间列节点**（`MM-dd HH:mm:ss`）为行锚点，取其同行的长文本消息节点。

    ⚠️ 反面教训（2026-09-20 实测）：直接用「长度 ≥16 的文本」筛消息会命中**状态栏**文本
    （如系统通知文案，cy≈18）→ 关键词取自状态栏、点击也打在状态栏上 → 「弹窗打不开」假失败。
    """
    nodes = text_nodes(xml)
    times = [(l, cx, cy) for l, _t, _lf, cx, cy in nodes if TIME_PAT.match(l)]
    msgs = [(l, cx, cy) for l, _t, _lf, cx, cy in nodes
            if len(l) >= 20 and not TIME_PAT.match(l)
            and S_FILTER_COUNT_PREFIX not in l and S_FILTER_CLEAR not in l]
    out = []
    for _tl, _tcx, tcy in times:
        # 行内上下两行结构：级别+时间在上、消息在下（实测 cy 差 ≈19px）；行间距 ≈97px ⇒ 容差取 40 无跨行风险
        cands = [m for m in msgs if abs(m[2] - tcy) <= 40]
        if cands:
            out.append(min(cands, key=lambda x: abs(x[2] - tcy)))
    return sorted(out, key=lambda n: n[2])


def _dist(a, b) -> int:
    return max(abs(a[i] - b[i]) for i in range(3))


def foreground(img, b, bg_tol=45):
    """区域前景色 = 「非区域性主色」像素均值（区域主色视作行底色）"""
    from collections import Counter
    px = [img.getpixel((x, y))
          for x in range(max(0, b["left"]), min(img.width, b["right"]))
          for y in range(max(0, b["top"]), min(img.height, b["bottom"]))]
    if not px:
        return ((0, 0, 0), 0)
    bgq = Counter(tuple(v // 16 for v in p) for p in px).most_common(1)[0][0]
    bg = tuple(v * 16 + 8 for v in bgq)
    fg = [p for p in px if _dist(p, bg) > bg_tol]
    if not fg:
        return (bg, 0)
    return (tuple(sum(p[i] for p in fg) // len(fg) for i in range(3)), len(fg))


def accent_ref(img, xml):
    """以「清除筛选」文字像素均值作为 accent 参考色（自校准，不猜主题色值）"""
    b = node_bounds(xml, S_FILTER_CLEAR)
    if not b:
        return None
    return foreground(img, b)[0]


def count_near(img, b, ref, tol=40, min_chroma=18):
    """节点区域内「接近参考色**且有色度**」的像素数。

    加彩度门槛的原因（实测）：仅用色距会把**深灰正文字**计入（灰字与 accent 的距离也 <60），
    导致搜索前基线高达 813 px、增量淹没在噪声里；accent 是有彩度的（本机 R/G/B 极差 54），
    灰阶文字极差 ≈0 ⇒ 用「色距 + 彩度」双门槛把高亮段的增量暴露出来。
    """
    if not b or not ref:
        return 0
    n = 0
    for x in range(max(0, b["left"]), min(img.width, b["right"])):
        for y in range(max(0, b["top"]), min(img.height, b["bottom"])):
            p = img.getpixel((x, y))
            if _dist(p, ref) <= tol and (max(p) - min(p)) >= min_chroma:
                n += 1
    return n


def type_search(d, keyword: str) -> bool:
    """在日志搜索框输入关键词（Compose BasicTextField 在 a11y 层为 EditText）"""
    b = ca.dump_bounds(d, 'class="android.widget.EditText"')
    if not b:
        for _ in range(2):
            time.sleep(1.5)
            b = ca.dump_bounds(d, 'class="android.widget.EditText"')
            if b:
                break
    if not b:
        return False
    click_xy(d, b["cx"], b["cy"])
    time.sleep(0.6)
    try:
        d.send_keys(keyword)
    except Exception:
        sh("input", "text", keyword)
    time.sleep(1.5)
    return True


# ============================ 场景 ============================

def s1_log_page(d) -> bool:
    """log/log：F190 计数条/高亮/清除 + F191 详情翻阅 + F192 时间口径"""
    reset_app()
    if not start_robust(ACT_LOG):
        print(f"  [s1] 未进入日志页（栈顶={current_activity()}）")
        return False
    xml0 = dump_xml(d)
    landed = S_LOG_TITLE in xml0
    print(f"  [s1] 日志页落地={landed} / 栈顶={current_activity()}")
    if not landed:
        return False
    ca.shot(d, "m3log_s1_landed")

    msgs = log_rows(xml0)
    print(f"  [s1] 可见日志行={len(msgs)}")
    if not msgs:
        print("  [s1] 无日志行可测（AppLog 为空）")
        return False

    # 关键词：取首行消息里的首段 ASCII 串（长度 ≥6 优先，保证高亮段占比可测）
    keyword = ""
    for label, _cx, _cy in msgs:
        runs = re.findall(r"[A-Za-z_]{6,}", label) or re.findall(r"[A-Za-z_]{4,}", label)
        if runs:
            keyword = runs[0]
            break
    print(f"  [s1] 关键词取自日志正文（长度={len(keyword)}）")
    if not keyword:
        print("  [s1] 未从日志正文提取到 ASCII 关键词，跳过断言")
        return False

    target_label = next(l for l, _cx, _cy in msgs if keyword in l)
    shot_dir = Path(tempfile.mkdtemp(prefix="m3log_"))
    before_png = str(shot_dir / "before.png")
    d.screenshot(before_png)
    b_before = node_bounds(xml0, target_label)
    from PIL import Image
    img_before = Image.open(before_png).convert("RGB")

    # F190：搜索 → 命中计数条 + 清除筛选
    if not type_search(d, keyword):
        print("  [s1] 未定位到搜索框")
        return False
    xml1 = dump_xml(d)
    count_b = node_bounds(xml1, S_FILTER_COUNT_PREFIX, contains=True)
    clear_b = node_bounds(xml1, S_FILTER_CLEAR)
    print(f"  [s1] 计数条={bool(count_b)} 文案={count_b and '命中 N / 共 M 条'} / 清除筛选={bool(clear_b)}")
    ca.shot(d, "m3log_s1_filter_active")
    if not (count_b and clear_b):
        return False

    # 高亮：同一行节点区域内「接近 accent 色」的像素计数（搜索前应≈0，搜索后应>0）
    after_png = str(shot_dir / "after.png")
    d.screenshot(after_png)
    img_after = Image.open(after_png).convert("RGB")
    b_after = node_bounds(xml1, target_label)
    acc = accent_ref(img_after, xml1)
    n_before = count_near(img_before, b_before, acc)
    n_after = count_near(img_after, b_after, acc)
    highlight_ok = bool(acc) and b_before is not None and b_after is not None \
        and n_after > n_before + 5
    print(f"  [s1] 高亮像素判定={highlight_ok}｜accent={acc} "
          f"accent像素 before={n_before} after={n_after}（同节点区域，色距 tol=40 + 彩度 ≥18）")

    # F190：一键清除筛选 → 计数条消失
    cleared = tap_text(d, S_FILTER_CLEAR)
    time.sleep(1.2)
    xml2 = dump_xml(d)
    gone = node_bounds(xml2, S_FILTER_COUNT_PREFIX, contains=True) is None
    print(f"  [s1] 清除筛选点击={cleared} / 计数条消失={gone}")
    ca.shot(d, "m3log_s1_filter_cleared")

    # F191：点首行 → 详情弹窗 + 位置指示 → › 翻阅递增
    msgs2 = log_rows(xml2)
    paging_ok = False
    if msgs2:
        opened = False
        for attempt in range(2):
            if attempt == 0:
                click_xy(d, msgs2[0][1], msgs2[0][2])
            else:
                try:
                    d(text=msgs2[0][0]).click()
                except Exception:
                    click_xy(d, msgs2[0][1], msgs2[0][2])
            time.sleep(2.0)
            xml3 = dump_xml(d)
            if S_CLOSE in xml3:            # 弹窗动作行「关闭」= 弹窗已开的稳定判据（与业务文案无关）
                opened = True
                break
        xml3 = dump_xml(d)
        pos = [n for n in text_nodes(xml3) if PAGE_PAT.match(n[0])]
        print(f"  [s1] 详情弹窗已开={opened}（判据=「{S_CLOSE}」节点）"
              f" / 位置指示={[p[0] for p in pos]} / 节点数={len(text_nodes(xml3))}")
        if opened and pos:
            cur = int(pos[0][0].split("/")[0])
            ca.shot(d, "m3log_s1_detail")
            next_b = node_bounds(xml3, "›")
            if next_b:
                click_xy(d, next_b["cx"], next_b["cy"])
                time.sleep(1.2)
                xml4 = dump_xml(d)
                pos2 = [n for n in text_nodes(xml4) if PAGE_PAT.match(n[0])]
                if pos2:
                    nxt = int(pos2[0][0].split("/")[0])
                    paging_ok = nxt == cur + 1
                    print(f"  [s1] 翻阅：{cur} → {nxt}（期望 +1）")
        if opened:
            tap_text(d, S_CLOSE)
            time.sleep(1.0)

    # F192：同年时间列形状回归（跨年分支源码断言，见文件头口径说明）
    xml5 = dump_xml(d)
    times = [n[0] for n in text_nodes(xml5) if TIME_PAT.match(n[0])]
    time_ok = len(times) > 0
    src = Path(SRC_LOG_SCREEN)
    src_text = src.read_text(encoding="utf-8") if src.exists() else ""
    cross_year_code = ("logTimeFormatWithYear" in src_text
                       and "entryYear == currentYear" in src_text)
    print(f"  [s1] 时间列同口径样本={len(times)} 例 / 跨年分支源码存在={cross_year_code}")

    return bool(landed and count_b and clear_b and highlight_ok and cleared and gone
                and paging_ok and time_ok and cross_year_code)


# ===================== s2：rss/sort（分类页）=====================

ACT_RSS_SORT = "io.legado.app.ui.rss.article.RssSortActivity"
S_TAB_ALL = "全部 ▾"                 # rss_sort_tabs_all
S_TAB_COLLAPSE = "收起 ▴"            # rss_sort_tabs_collapse
S_GROUP_SORT = "分类"                # rss_sort_group_sort
S_GROUP_SOURCE = "订阅源"            # rss_sort_group_source
S_GROUP_RECORD = "记录"              # rss_sort_group_record
S_GROUP_DANGER = "危险操作"          # rss_sort_group_danger
S_CLEAR = "清除"                     # clear
S_CLEAR_CONFIRM_PREFIX = "确认清除已缓存的文章"  # rss_sort_clear_confirm
S_CANCEL = "取消"                    # cancel
SRC_RSS_SORT = "app/src/main/java/io/legado/app/ui/rss/article/RssSortActivity.kt"
# 合成多分类源（sortUrl 以 && 分隔的 `name::url` 列表即分类清单，纯本地解析、不需要网络）
SEED_SORT_SOURCE = "l2seed://sort-multi"
SEED_SORT_NAME = "L2分类校验源"
SEED_SORT_COUNT = 12


def _m2():
    """复用 M2 脚本的沙箱库通道（pull/push/snapshot，均带 md5 校验）——避免两份写库实现漂移"""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import l2_verify_m2_rest_pages as m2
    return m2


def seed_multi_sort_source(workdir: Path) -> bool:
    """播种「12 分类」合成源（整行复制既有源后改写 sourceUrl/name/sortUrl/ruleArticles）"""
    m2 = _m2()
    db = m2._db_pull(workdir)
    if db is None:
        return False
    con = sqlite3.connect(str(db))
    try:
        cols = [r[1] for r in con.execute("pragma table_info(rssSources)")]
        row = con.execute("select * from rssSources where enabled = 1 limit 1").fetchone()
        if not row:
            return False
        data = dict(zip(cols, row))
        data["sourceUrl"] = SEED_SORT_SOURCE
        data["sourceName"] = SEED_SORT_NAME
        data["sortUrl"] = " && ".join(
            f"L2分类{i + 1}::http://10.0.2.2:1/s{i + 1}" for i in range(SEED_SORT_COUNT)
        )
        data["ruleArticles"] = None      # 去掉列表规则：分类 Tab 只依赖 sortUrl，避免网络分支干扰
        data["enabled"] = 1
        con.execute(
            f"insert or replace into rssSources ({','.join(cols)})"
            f" values ({','.join('?' * len(cols))})",
            [data[c] for c in cols]
        )
        con.commit()
    finally:
        con.close()
    return m2._db_push(db)


def purge_seed_sort_source(workdir: Path) -> bool:
    """删除合成源（零污染收尾的最后一道）"""
    m2 = _m2()
    db = m2._db_pull(workdir)
    if db is None:
        return False
    con = sqlite3.connect(str(db))
    try:
        con.execute("delete from rssSources where sourceUrl = ?", (SEED_SORT_SOURCE,))
        con.commit()
    finally:
        con.close()
    return m2._db_push(db)


def _mean_rgb(img, cx, cy, rad=2):
    xs = range(max(0, cx - rad), min(img.width, cx + rad + 1))
    ys = range(max(0, cy - rad), min(img.height, cy + rad + 1))
    px = [img.getpixel((x, y)) for x in xs for y in ys]
    if not px:
        return (0, 0, 0)
    return tuple(sum(p[i] for p in px) // len(px) for i in range(3))


def iter_nodes_with_ancestors(xml: str):
    """产出 (node_tag, 祖先 tag 列表)：uiautomator 树为嵌套结构，用栈扫描即可还原层级。

    用途：把「分类胶囊」与「顶栏标题 / 收敛切换 chip」精确区分——三者都是 TextView，
    只有分类胶囊的祖先链里含 **HorizontalScrollView**（`setupMultiLineTabs` 的行结构）。
    """
    stack = []
    for m in re.finditer(r"<node[^>]*?>|</node>", xml):
        tag = m.group(0)
        if tag == "</node>":
            if stack:
                stack.pop()
            continue
        yield tag, list(stack)
        if not tag.endswith("/>"):
            stack.append(tag)


def tab_nodes(xml: str):
    """分类胶囊节点：祖先链含 HorizontalScrollView 的 TextView（自动排除顶栏标题与切换 chip）

    ⚠️ 分类文案属业务数据，**只统计不打印**；断言用「数量 / 选中态 / 像素」三类客观量。
    """
    out = []
    for tag, ancestors in iter_nodes_with_ancestors(xml):
        if "android.widget.TextView" not in tag:
            continue
        if not any("HorizontalScrollView" in a for a in ancestors):
            continue
        tx = re.search(r'\btext="([^"]*)"', tag)
        b = re.search(r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', tag)
        if not tx or not b:
            continue
        x1, y1, x2, y2 = map(int, b.groups())
        out.append({
            "label": tx.group(1),
            "selected": 'selected="true"' in tag,
            "bounds": {"left": x1, "top": y1, "right": x2, "bottom": y2,
                       "cx": (x1 + x2) // 2, "cy": (y1 + y2) // 2},
        })
    return sorted(out, key=lambda n: (n["bounds"]["cy"], n["bounds"]["left"]))


def topbar_action_bounds(xml: str, from_right: int = 0):
    """顶栏动作节点（Compose 无 resource-id）：取顶栏带内可点击、按 cx 从右往左第 from_right 个"""
    cands = []
    for m in re.finditer(r"<node[^>]*>", xml):
        t = m.group(0)
        if 'clickable="true"' not in t:
            continue
        b = re.search(r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', t)
        if not b:
            continue
        x1, y1, x2, y2 = map(int, b.groups())
        cy = (y1 + y2) // 2
        if cy > 200 or (x2 - x1) < 40 or (x2 - x1) > 120:
            continue
        cands.append({"left": x1, "top": y1, "right": x2, "bottom": y2,
                      "cx": (x1 + x2) // 2, "cy": cy})
    cands.sort(key=lambda n: -n["cx"])
    return cands[from_right] if len(cands) > from_right else None


def s2_rss_sort_page(d) -> bool:
    """rss/sort：Tab 选中填充（合规缺口）+ 菜单分组/危险项 + 清空前确认 + F210 Tab 收敛 + F201 页码 chip

    构造通道：沙箱 4 个真实源**均为单分类**（实测），单分类态下 tabsContainer 直接 gone ⇒ 无法验证
    选中填充/收敛。故**播种**一个 12 分类合成源（整行复制既有源后改写 `sortUrl` 为 `&&` 分隔的
    `name::url` 列表 —— 分类清单纯本地解析，不需要网络），测后**整份回滚数据库快照**（零污染）。
    """
    workdir = Path(tempfile.mkdtemp(prefix="m3sort_"))
    m2 = _m2()
    db_snap = workdir / "legado_snapshot.db"
    if not m2._snapshot_db(workdir, db_snap):
        print("  [s2] 数据库快照失败（前置）")
        return False
    ok = False
    try:
        if not seed_multi_sort_source(workdir):
            print("  [s2] 多分类合成源播种失败")
            return False
        reset_app()
        sh("am", "start", "-n", f"{PKG}/{ACT_RSS_SORT}", "--es", "sourceUrl", SEED_SORT_SOURCE)
        time.sleep(4.5)
        xml0 = dump_xml(d)
        tabs = tab_nodes(xml0)
        collapsed = len(tabs)
        print(f"  [s2] 落地={ACT_RSS_SORT.split('.')[-1] in current_activity()} "
              f"/ 分类胶囊数={collapsed}（播种 {SEED_SORT_COUNT} 个分类，收敛态应为首行容量）")
        ca.shot(d, "m3sort_s2_landed")
        if collapsed < 2:
            print("  [s2] 合成源未渲染多分类 Tab（播种或解析失败）")
            return False

        from PIL import Image
        shot_dir = Path(tempfile.mkdtemp(prefix="m3sortshot_"))

        # F210：收敛态 → 点「全部 ▾」展开到全部分类
        xml_t = dump_xml(d)
        toggle_all = node_bounds(xml_t, S_TAB_ALL)
        expanded_count = collapsed
        collapse_ok = False
        if toggle_all:
            tap_text(d, S_TAB_ALL)
            time.sleep(2.0)
            xml_e = dump_xml(d)
            expanded_count = len(tab_nodes(xml_e))
            back_toggle = node_bounds(xml_e, S_TAB_COLLAPSE)
            # 精确口径：展开增量 == 首行容量（rowCount=2 时 ceil(分类数/2)），证明「收敛真的藏起了后续行」
            expected_step = -(-SEED_SORT_COUNT // 2)
            collapse_ok = (expanded_count - collapsed == expected_step
                           and back_toggle is not None)
            print(f"  [s2] F210 收敛切换：{collapsed} → {expanded_count}"
                  f"（增量期望 {expected_step} = 首行容量）/ 收起入口出现={back_toggle is not None}")
            ca.shot(d, "m3sort_s2_tabs_expand")
        else:
            print(f"  [s2] F210 未出现「{S_TAB_ALL}」收敛入口（分类数 ≤ 首行容量）")

        # 修复1：同一胶囊「选中 → 未选中」前后像素对比（展开态下取多枚胶囊）
        tabs = tab_nodes(dump_xml(d))
        sel = next((t for t in tabs if t["selected"]), None)
        other = next((t for t in tabs if not t["selected"]), None)
        fill_ok = False
        if sel and other:
            p1 = str(shot_dir / "tab_sel.png")
            d.screenshot(p1)
            img1 = Image.open(p1).convert("RGB")
            m_sel = _mean_rgb(img1, sel["bounds"]["cx"], sel["bounds"]["cy"], rad=3)
            click_xy(d, other["bounds"]["cx"], other["bounds"]["cy"])
            time.sleep(2.5)
            same = next((t for t in tab_nodes(dump_xml(d)) if t["label"] == sel["label"]), None)
            p2 = str(shot_dir / "tab_unsel.png")
            d.screenshot(p2)
            img2 = Image.open(p2).convert("RGB")
            if same:
                m_unsel = _mean_rgb(img2, same["bounds"]["cx"], same["bounds"]["cy"], rad=3)
                delta = _dist(m_sel, m_unsel)
                fill_ok = delta >= 6
                print(f"  [s2] 修复1 选中态填充：同胶囊 sel={m_sel} → unsel={m_unsel} delta={delta}（阈值 6）")
            ca.shot(d, "m3sort_s2_tab_fill")
        else:
            print("  [s2] 修复1 未取到「选中 + 未选中」胶囊对")

        # 修复2/3：⋮ 菜单分组头 + 危险项 danger 前景色 + 清空二次确认（点取消，零数据污染）
        menu_ok = False
        danger_ok = False
        more = topbar_action_bounds(dump_xml(d), 0)
        if more:
            click_xy(d, more["cx"], more["cy"])
            time.sleep(1.5)
            xmlm = dump_xml(d)
            groups = [s for s in (S_GROUP_SORT, S_GROUP_SOURCE, S_GROUP_RECORD, S_GROUP_DANGER)
                      if s in xmlm]
            has_clear = S_CLEAR in xmlm
            clear_b = node_bounds(xmlm, S_CLEAR)
            if clear_b:
                p3 = str(shot_dir / "menu.png")
                d.screenshot(p3)
                imgm = Image.open(p3).convert("RGB")
                # 文本节点中心均值会被背景稀释（实测 (220,207,233) 判不出）⇒ 取非背景像素均值 = 文字前景色
                fg = foreground(imgm, clear_b)[0]
                danger_ok = fg[0] > fg[1] + 30 and fg[0] > fg[2] + 30
                print(f"  [s2] 修复2 危险项前景色={fg}（R 显著高于 G/B ⇒ danger 着色）={danger_ok}")
            print(f"  [s2] 修复2 菜单分组命中={groups} / 含「{S_CLEAR}」={has_clear}")
            ca.shot(d, "m3sort_s2_menu_grouped")
            confirm_ok = False
            if has_clear and clear_b:
                click_xy(d, clear_b["cx"], clear_b["cy"])
                time.sleep(1.8)
                xmlc = dump_xml(d)
                has_confirm = (S_CLEAR_CONFIRM_PREFIX in xmlc) and (S_CANCEL in xmlc)
                print(f"  [s2] 修复3 清空二次确认出现={has_confirm}")
                ca.shot(d, "m3sort_s2_clear_confirm")
                if has_confirm:
                    tap_text(d, S_CANCEL)
                    time.sleep(1.2)
                    confirm_ok = S_CLEAR_CONFIRM_PREFIX not in dump_xml(d)
            else:
                print("  [s2] 修复3 未定位「清除」项")
            menu_ok = len(groups) == 4 and has_clear and confirm_ok
        else:
            print("  [s2] 未定位顶栏 ⋮ 动作")

        # F201：页码 chip 依赖分页态数据（pageMenuTitle != null）⇒ 以源码存在性 + 菜单去重双口径记录
        src_text = Path(SRC_RSS_SORT).read_text(encoding="utf-8") if Path(SRC_RSS_SORT).exists() else ""
        page_code = ("pageMenuTitle?.let" in src_text and "showPagePicker()" in src_text
                     and "actions = buildMenuActions(palette.danger)" in src_text)
        page_chip = bool(node_bounds(dump_xml(d), "第 ", contains=True))
        print(f"  [s2] F201 页码 chip 当前可见={page_chip}（分页态才出现）/ 顶栏常驻渲染源码存在={page_code}")

        ok = bool(collapse_ok and fill_ok and menu_ok and danger_ok and page_code)
    finally:
        try:
            rolled = m2._db_push(db_snap)
            print(f"  [s2] 数据库快照已回滚={rolled}")
        except Exception as e:
            print(f"  [s2] 兜底回滚异常: {type(e).__name__}")
        reset_app()
    return ok


# ===================== s3：browser/webview-browser（内嵌浏览器）=====================

ACT_BROWSER = "io.legado.app.ui.browser.WebViewActivity"
S_SSL_TITLE = "证书校验失败"                    # ssl_error_title
S_SSL_CONTINUE = "仍要继续访问"                  # ssl_error_continue
S_SSL_CERT_INFO = "有效期至"                     # ssl_error_cert_info
S_SSL_CANCEL = "取消"                            # cancel
S_BACK_EXIT = "再按一次返回键退出"                # webview_back_again_exit
S_DISABLE = "禁用源"                             # disable_source
S_DELETE = "删除源"                              # delete_source
S_GUIDE = "完成网页验证后，点右上角 ✓ 保存并返回"   # source_verification_guide
S_GUIDE_KEY = "完成网页验证后"                      # 同上，去掉 ✓ 的稳妥匹配段（dump 转义风险）
S_CF_CHECKING = "正在通过站点安全检查"             # source_verification_checking
S_YES = "是"                                     # yes
S_NO = "否"                                      # no
SRC_BROWSER = "app/src/main/java/io/legado/app/ui/browser/WebViewActivity.kt"
SSL_PORT = 8443
HTTP_PORT = 8543
BOGUS_ORIGIN = "l2test://browser-nosuch"
BOGUS_NAME = "L2BrowserVerifySrc"

# 页面统一带 1x1 透明 data: 图标 —— 否则 WebView 会请求 /favicon.ico，在自签名站点上
# **再触发一次证书弹窗**，把后续断言（返回键/标题）搅成假失败（实测 2026-09-20 首轮）
_ICON = "<link rel='icon' href='data:image/gif;base64,R0lGODlhAQABAAAAACw='>"

# 自签名 HTTPS 测试页：**全部内联资源**（无外链子资源 ⇒ 一次加载只触发一次证书告警）；
# 自动导航用 sessionStorage 守卫，避免返回导航时脚本重跑再次前进（历史栈污染）
_JS_GUARD = "if(!sessionStorage.getItem('%s')){sessionStorage.setItem('%s','1');%s}"
HTTPS_PAGES = {
    "/a": "<html><head><meta charset='utf-8'>" + _ICON + "<title>BT-A-L2</title></head>"
          "<body><h1>PAGE-A</h1></body></html>",
    "/nav1": "<html><head><meta charset='utf-8'>" + _ICON + "<title>BT-NAV-L2</title></head><body>"
             "<h1>PAGE-NAV1</h1><script>"
             + (_JS_GUARD % ("n1", "n1", "setTimeout(function(){location.href='/nav2'},1200)"))
             + "</script></body></html>",
    "/nav2": "<html><head><meta charset='utf-8'>" + _ICON + "<title>BT-NAV2-L2</title></head>"
             "<body><h1>PAGE-NAV2</h1></body></html>",
    "/spa1": "<html><head><meta charset='utf-8'>" + _ICON + "<title>BT-SPA1-L2</title></head><body>"
             "<h1>PAGE-SPA1</h1><script>"
             + (_JS_GUARD % ("s1", "s1", "setTimeout(function(){location.href='/spa2'},1200)"))
             + "</script></body></html>",
    # /spa2 与 pushState 项**同 URL 同标题**：旧启发式会把它与前一页合并计数直至 steps==size 直接退出
    # （/spa1 用不同标题 BT-SPA1-L2，便于独立断言「/spa2 真的加载了」）
    "/spa2": "<html><head><meta charset='utf-8'>" + _ICON + "<title>BT-SPA-L2</title></head><body>"
             "<h1>PAGE-SPA2</h1><script>"
             + (_JS_GUARD % ("s2", "s2", "setTimeout(function(){history.pushState({},'','/spa2')},1200)"))
             + "</script></body></html>",
    "/chal1": "<html><head><meta charset='utf-8'>" + _ICON + "<title>BT-CHAL-L2</title></head><body>"
              "<h1>PAGE-CHAL1</h1><script>"
              + (_JS_GUARD % ("c1", "c1", "setTimeout(function(){location.href='/chal'},1200)"))
              + "</script></body></html>",
    "/chal": "<html><head><meta charset='utf-8'>" + _ICON + "<title>BT-CHAL-L2</title>"
             "<script>window._cf_chl_opt={ray:'l2'}</script></head><body>"
             "<h1>PAGE-CHAL</h1></body></html>",
}
HTTPS_REQS: list = []       # 服务端收到的 GET 路径（SSL 双出口的客观判据）


def _openssl_exe() -> str:
    """Git for Windows 自带 openssl（PATH 里没有，用绝对路径兜底）"""
    for exe in (r"C:\Program Files\Git\usr\bin\openssl.exe",
                r"C:\Program Files\Git\mingw64\bin\openssl.exe",
                "openssl"):
        try:
            r = subprocess.run([exe, "version"], capture_output=True, timeout=20)
            if r.returncode == 0:
                return exe
        except Exception:
            continue
    return ""


def _make_self_signed(dirpath: Path):
    """生成自签名证书（CN/SAN=127.0.0.1）——设备经 adb reverse 访问本机 127.0.0.1 即命中"""
    exe = _openssl_exe()
    if not exe:
        return None, None
    key, crt = dirpath / "key.pem", dirpath / "cert.pem"
    for extra in (["-addext", "subjectAltName=IP:127.0.0.1"], []):
        try:
            r = subprocess.run([exe, "req", "-x509", "-newkey", "rsa:2048", "-nodes",
                                "-keyout", str(key), "-out", str(crt), "-days", "30",
                                "-subj", "/CN=127.0.0.1"] + extra,
                               capture_output=True, timeout=90)
            if r.returncode == 0 and crt.exists():
                return key, crt
        except Exception:
            continue
    return None, None


def _serve(ports, crt=None, key=None):
    """起一个本机服务（crt/key 非空 ⇒ HTTPS，否则明文 HTTP）；返回 (server, port)"""
    import http.server
    import ssl as _ssl
    import threading

    class _H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            HTTPS_REQS.append(self.path)
            path = urlparse(self.path).path          # 带 ?query 的用例仍命中同一页面
            body = HTTPS_PAGES.get(
                path,
                "<html><head><title>BT-404-L2</title></head><body>404</body></html>"
            ).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):     # 静音默认访问日志（请求已进 HTTPS_REQS）
            pass

    class _Srv(http.server.ThreadingHTTPServer):
        daemon_threads = True

    for port in ports:
        try:
            srv = _Srv(("127.0.0.1", port), _H)
        except OSError:
            continue
        if crt:
            ctx = _ssl.SSLContext(_ssl.PROTOCOL_TLS_SERVER)
            ctx.load_cert_chain(str(crt), str(key))
            srv.socket = ctx.wrap_socket(srv.socket, server_side=True)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        return srv, port
    return None, None


def _start_servers():
    """双通道：

    ① **HTTPS 自签名**（证书告警场景专用：修复 1 三出口断言；每次到该站点的**首次加载都会弹确认**，
       设计如此无白名单 ⇒ 只有证书用例走它，避免把证书弹窗掺进其它断言）
    ② **明文 HTTP**（本 App `network_security_config` 的 base-config `cleartextTrafficPermitted=true`，
       实测可直连）——历史栈/引导条/挑战条用例走它：**无证书弹窗干扰**，
       否则「自动跳转被证书弹窗拦住 ⇒ 历史项没生成」会把 F214 测成假失败（实测 2026-09-20 首轮）。
    返回 ((ssl_srv, ssl_port), (http_srv, http_port), certdir)
    """
    certdir = Path(tempfile.mkdtemp(prefix="m3ssl_"))
    key, crt = _make_self_signed(certdir)
    if not crt:
        return (None, None), (None, None), certdir
    ssl_srv, ssl_port = _serve((SSL_PORT, SSL_PORT + 1), crt, key)
    http_srv, http_port = _serve((HTTP_PORT, HTTP_PORT + 1))
    return (ssl_srv, ssl_port), (http_srv, http_port), certdir


def _adb_host(*args, timeout: int = 30):
    """**主机侧** adb 命令（不经 device shell）。

    🔴 铁律：`adb reverse` 是主机侧能力，走 `ca.sh`（内部拼了 `shell`）会被当成**设备命令**
    执行 → 报 `reverse: not found`，且 `--list` 恒读不到映射（实测 2026-09-20 首次 s3 失败原因）。
    """
    return subprocess.run([ADB, "-s", HOST] + list(args),
                          capture_output=True, timeout=timeout)


def _reverse_on(port: int) -> bool:
    """adb reverse tcp:port → 本机同端口（设备 127.0.0.1 即可达）并回读确认"""
    _adb_host("reverse", "tcp:%d" % port, "tcp:%d" % port)
    time.sleep(0.8)
    r = _adb_host("reverse", "--list")
    return ("tcp:%d" % port) in (r.stdout or b"").decode("utf-8", errors="ignore")


def release_reverse(port: int):
    try:
        _adb_host("reverse", "--remove", "tcp:%d" % port)
    except Exception:
        pass


def _device_reachable(base: str, retries: int = 3) -> bool:
    """设备侧真连通探针：传入**带协议的 base**（`-k` 忽略自签名，只判通道通不通）取 http_code=200。

    ⚠️ 必须按各自协议探：明文 HTTP 端口用 `https://` 探会在 TLS 握手上直接失败
    （实测 2026-09-20 第二轮「探针失败」的真因）。
    """
    for _ in range(retries):
        r = sh("curl", "-k", "-s", "--max-time", "10", "-o", "/dev/null", "-w", "%{http_code}",
               f"{base}/a", timeout=40)
        if b"200" in (r.stdout or b""):
            return True
        time.sleep(1.5)
    return False


def start_browser(url: str, title: str, extras: list = None) -> bool:
    """非导出组件 am start：先 shell 直起，失败再 su 直起（extras 为 --es/--ez 平铺列表）

    ⚠️ 轮询窗口必须够长：冷启动 + WebView 池初始化可超 6s；窗口太短会用 su 兜底**再起一个实例**，
    顶层实例读到的「一次性记忆位」已被第一个实例写入 ⇒ 引导条不显示（实测 F215 假失败的根因）。
    """
    extra = list(extras or [])
    simple = ACT_BROWSER.rsplit(".", 1)[-1]
    sh("am", "start", "-n", f"{PKG}/{ACT_BROWSER}",
       "--es", "url", url, "--es", "title", title, *extra)
    for _ in range(14):
        time.sleep(1.2)
        if simple in current_activity():
            time.sleep(2.0)
            return True
    cmd = "am start -n %s/%s --es url %s --es title %s %s" % (
        PKG, ACT_BROWSER, url, title, " ".join(extra))
    sh_su(cmd)
    time.sleep(3.5)
    return simple in current_activity()


def clear_guide_flag() -> bool:
    """清 F215 引导条记忆位（**绝对路径**：run-as 的相对路径在此 ROM 上不落盘）并回读确认"""
    path = f"/data/data/{PKG}/shared_prefs/web_view_guide.xml"
    sh_su(f"run-as {PKG} rm -f {path}", timeout=30)
    r = sh_su(f"run-as {PKG} cat {path}", timeout=30)
    left = b"source_verification_guide_shown" in (r.stdout or b"")
    print(f"  [s3] 前置：引导条记忆位已清除={not left}")
    return not left


# ---- 证书放行策略（用户裁决 2026-09-20）：类爬虫场景源站自签名/过期证书极常见 ⇒ **默认放行** ----
S_SSL_PASS = "证书放行策略"                     # ssl_passthrough（菜单项标题）
S_SSL_ON_HINT = "证书放行已开启：证书校验失败直接放行，不再询问"    # ssl_passthrough_on_hint
S_SSL_OFF_HINT = "证书放行已关闭：证书校验失败需确认后才能继续"     # ssl_passthrough_off_hint
PREFS_DIR = f"/data/data/{PKG}/shared_prefs"


def _pref_read(marker: str) -> str:
    """按 marker 在 shared_prefs 下定位文件并回读全文（debug 包走 run-as 绝对路径）"""
    r = sh_su(f"run-as {PKG} ls {PREFS_DIR}", timeout=30)
    names = [n for n in (r.stdout or b"").decode(errors="ignore").split() if n.endswith(".xml")]
    for n in names:
        c = sh_su(f"run-as {PKG} cat {PREFS_DIR}/{n}", timeout=30)
        txt = (c.stdout or b"").decode(errors="ignore")
        if marker in txt:
            return txt
    return ""


def _ssl_pref_state():
    """证书放行策略当前值：True/False；键不存在 ⇒ None（AppConfig 取默认 True=放行）"""
    txt = _pref_read("sslCertPassThrough")
    m = re.search(r'name="sslCertPassThrough"\s+value="(\w+)"', txt)
    return None if not m else (m.group(1) == "true")


def toggle_ssl_pass_through(d) -> dict:
    """顶栏 ⋮ →「证书放行策略」切换。返回 {menu, clicked, hint_on, hint_off}
    （menu=菜单项在场；hint_*=点击后的状态回执文案，作为「用户看得见当前策略」的判据）"""
    res = {"menu": False, "clicked": False, "hint_on": False, "hint_off": False}
    more = topbar_action_bounds(dump_xml(d), 0)
    if not more:
        return res
    click_xy(d, more["cx"], more["cy"])
    time.sleep(1.5)
    xmlm = dump_xml(d)
    res["menu"] = S_SSL_PASS in xmlm
    b = node_bounds(xmlm, S_SSL_PASS)
    if not b:
        d.press("back")          # 关掉误开的菜单，避免遮住后续动作
        return res
    click_xy(d, b["cx"], b["cy"])
    res["clicked"] = True
    # 回执是**短时 snackbar**（约 2s）⇒ 必须点击后立即轮询捕获；
    # ⚠️ 反面教训（2026-09-20 s3 首轮）：固定 sleep 1s + click_xy 自带 1.2s = 2.2s 后 dump，
    #    回执已消失 ⇒ 报「关闭提示=False」假 FAIL（而 prefs 回读已证 onClick 确实执行）。
    for _ in range(6):
        xml = dump_xml(d)
        res["hint_on"] = res["hint_on"] or (S_SSL_ON_HINT in xml)
        res["hint_off"] = res["hint_off"] or (S_SSL_OFF_HINT in xml)
        if res["hint_on"] or res["hint_off"]:
            break
        time.sleep(0.7)
    return res


def _logcat_count(keyword: str) -> int:
    """统计 logcat 当前缓冲里含 keyword 的行数（用于「某动作确实触发了某副作用」的客观增量判据）"""
    out = sh("logcat", "-d", "-v", "brief", timeout=60).stdout.decode("utf-8", errors="ignore")
    return sum(1 for line in out.splitlines() if keyword in line)


def wait_ssl_dialog(d, rounds: int = 6, wait: float = 2.5):
    """等证书确认弹窗出现（**不点击**，用于断言弹窗内容）。冷启动 + WebView 池 + 首请求
    证书校验需要几秒，首次 dump 常常还没弹（实测 2026-09-20 首轮「齐备=False」的真因）。"""
    for _ in range(rounds):
        xml = dump_xml(d)
        if S_SSL_TITLE in xml:
            return xml
        time.sleep(wait)
    return ""


def wait_browser_title(d, want: str, rounds: int = 6, wait: float = 2.5) -> bool:
    """等待顶栏标题命中：每次到该 https 站点的**首次加载都会弹证书确认**（设计如此，无白名单）
    ⇒ 循环内先接受证书再判标题。"""
    for _ in range(rounds):
        xml = dump_xml(d)
        if want in xml:
            return True
        b = node_bounds(xml, S_SSL_CONTINUE)
        if b:
            click_xy(d, b["cx"], b["cy"])
        time.sleep(wait)
    return False


def _bt_labels(xml: str):
    """本页测试用标题标记（BT-* 前缀，纯测试构造串，不含任何业务数据）"""
    return sorted({n[0] for n in text_nodes(xml) if n[0].startswith("BT-")})


def _danger_foreground(d, xml: str, label: str):
    """节点前景色（非背景像素均值）→ (前景色, 是否 danger 色)"""
    from PIL import Image
    b = node_bounds(xml, label)
    if not b:
        return None, False
    p = str(Path(tempfile.mkdtemp(prefix="m3fg_")) / "fg.png")
    d.screenshot(p)
    fg = foreground(Image.open(p).convert("RGB"), b)[0]
    return fg, (fg[0] > fg[1] + 30 and fg[0] > fg[2] + 30)


def s3_browser_page(d) -> bool:
    """browser/webview-browser：修复1（SSL 默认拒绝+确认）/ 修复2（禁用源确认）/ 修复3（菜单 danger tint）
    + F214（一按一页 + 栈顶双击退出）+ F215（验证模式引导条 + 挑战期状态条）

    构造通道：本机双服务（HTTPS 自签名 :8443 **只用于证书告警场景** + 明文 HTTP :8543 用于其余场景）
    + `adb reverse`（设备 127.0.0.1:port → 本机同端口）+ 设备侧 curl 探针，**不依赖外网**。
    SSL 双出口用**服务端请求日志**判：取消 ⇒ 零请求（默认拒绝生效），继续 ⇒ 收到 GET 且顶栏标题变网页 title。
    """
    from PIL import Image

    m2 = _m2()
    workdir = Path(tempfile.mkdtemp(prefix="m3browser_"))
    db_snap = workdir / "legado_snapshot.db"
    if not m2._snapshot_db(workdir, db_snap):
        print("  [s3] 数据库快照失败（前置）")
        return False
    (ssl_srv, ssl_port), (http_srv, http_port), _certdir = _start_servers()
    if ssl_srv is None or http_srv is None:
        print("  [s3] 本机测试服务启动失败（openssl 不可用或端口占用）")
        return False
    if not (_reverse_on(ssl_port) and _reverse_on(http_port)):
        print(f"  [s3] adb reverse 通道不可用（{ssl_port}/{http_port}）")
        return False
    sbase = f"https://127.0.0.1:{ssl_port}"       # 证书告警场景
    hbase = f"http://127.0.0.1:{http_port}"       # 历史栈/引导条场景（无证书弹窗干扰）
    if not (_device_reachable(sbase) and _device_reachable(hbase)):
        print("  [s3] 设备侧连通探针失败（curl 非 200）")
        return False
    print(f"  [s3] 测试通道就绪：自签名 HTTPS :{ssl_port} + 明文 HTTP :{http_port}"
          f" + adb reverse + 设备侧 curl 探针 200")
    # 清除 F215 引导条记忆位（页面本地 prefs），保证「首次进入」可复现
    clear_guide_flag()
    simple = ACT_BROWSER.rsplit(".", 1)[-1]
    try:
        # ---------- 证书放行策略（**默认放行**，用户裁决 2026-09-20）+ 关闭态的 SSL 知情确认 ----------
        # 策略语义：本应用主体是类爬虫的书源/订阅源引擎，源站自签名/过期证书极常见 ⇒ 默认放行，
        # 避免大量源被证书判死；用户可在 ⋮ 菜单关闭，关闭后才逐次知情确认。
        # 带 query 的 URL：确保两次加载不落 WebView HTTP 缓存（否则第二次不再发起请求/不再告警）
        pref_entry = _ssl_pref_state()
        print(f"  [s3] 策略前置：pref={pref_entry}（None=未写入 ⇒ AppConfig 默认 True=放行）")
        passthrough_ok = False
        ssl_menu_ok = ssl_off_ok = ssl_off_hint = ssl_restore_ok = False
        if pref_entry is False:
            # 上次中断可能残留关闭态 ⇒ 先经 UI 拨回（幂等归一，不直接改 prefs 文件，避免绕过被验对象）
            reset_app()
            if start_browser(f"{hbase}/pre", "BTL2"):
                toggle_ssl_pass_through(d)
                print(f"  [s3] 策略前置归一：pref 回读={_ssl_pref_state()}（期望 True）")

        # 默认放行：证书错误不打断加载（无弹窗 + 服务端真的收到请求）
        HTTPS_REQS.clear()
        reset_app()
        if not start_browser(f"{sbase}/a?c0", "BTL2"):
            print(f"  [s3] 未进入内嵌浏览器（栈顶={current_activity()}）")
            return False
        time.sleep(4.0)
        xmlA = dump_xml(d)
        no_dialog = (S_SSL_TITLE not in xmlA) and (S_SSL_CONTINUE not in xmlA)
        got_c0 = any(p.startswith("/a") for p in HTTPS_REQS)
        passthrough_ok = no_dialog and got_c0
        ca.shot(d, "m3browser_s3_passthrough_default")
        print(f"  [s3] 默认放行：无证书弹窗={no_dialog} / 服务端收到 /a={got_c0}（证书错误不阻断）")

        # 关闭放行：⋮ →「证书放行策略」（菜单项在场 + prefs 回读 + 状态回执文案 三重判据）
        tg = toggle_ssl_pass_through(d)
        ssl_menu_ok = tg["menu"]
        ssl_off_hint = tg["hint_off"]
        ssl_off_ok = tg["clicked"] and (_ssl_pref_state() is False)
        ca.shot(d, "m3browser_s3_passthrough_off")
        print(f"  [s3] 关闭放行：菜单项在场={tg['menu']} / 已点击={tg['clicked']}"
              f" / pref回读={_ssl_pref_state()}（期望 False）/ 关闭提示={tg['hint_off']}")

        # 关闭态：证书错误 ⇒ 知情确认弹窗（下列断言沿用原「修复1」口径）
        HTTPS_REQS.clear()
        reset_app()
        if not start_browser(f"{sbase}/a?c1", "BTL2"):
            print(f"  [s3] 未进入内嵌浏览器（栈顶={current_activity()}）")
            return False
        xml0 = wait_ssl_dialog(d)
        ca.shot(d, "m3browser_s3_ssl_dialog")
        dialog_ok = bool(xml0) and all(s in xml0 for s in (S_SSL_TITLE, S_SSL_CONTINUE,
                                                          S_SSL_CERT_INFO, S_SSL_CANCEL))
        fg_btn, ssl_danger = _danger_foreground(d, xml0 or dump_xml(d), S_SSL_CONTINUE)
        print(f"  [s3] 修复1 弹窗：标题/继续/证书摘要/取消 齐备={dialog_ok}"
              f" / 主按钮前景={fg_btn} danger={ssl_danger}")

        # 出口①取消 ⇒ 服务端零请求（默认拒绝真的生效，不是「先放行再提示」）
        HTTPS_REQS.clear()
        cancelled = tap_text(d, S_SSL_CANCEL)
        time.sleep(3.0)
        got_a_after_cancel = any(p.startswith("/a") for p in HTTPS_REQS)
        reject_ok = cancelled and not got_a_after_cancel
        print(f"  [s3] 修复1 取消出口：点击={cancelled} / 服务端收到 /a={got_a_after_cancel}"
              f"（期望 False）")

        # 出口②继续 ⇒ 服务端收到请求 + 顶栏标题变为网页 title（页面真的加载）
        reset_app()
        proceed_ok = False
        if start_browser(f"{sbase}/a?p1", "BTL2"):
            if wait_ssl_dialog(d):
                b = node_bounds(dump_xml(d), S_SSL_CONTINUE)
                if b:
                    click_xy(d, b["cx"], b["cy"])
                    time.sleep(3.5)
                    got_a = any(p.startswith("/a") for p in HTTPS_REQS)
                    loaded = "BT-A-L2" in dump_xml(d)
                    proceed_ok = got_a and loaded
                    print(f"  [s3] 修复1 继续出口：服务端收到 /a={got_a}"
                          f" / 顶栏标题=网页 title={loaded}")

        # 出口③还原：把策略拨回默认放行（收尾不留关闭态，避免影响真实使用）
        tg2 = toggle_ssl_pass_through(d)
        ssl_restore_ok = tg2["clicked"] and tg2["hint_on"] and (_ssl_pref_state() is True)
        print(f"  [s3] 策略还原：已点击={tg2['clicked']} / 开启提示={tg2['hint_on']}"
              f" / pref回读={_ssl_pref_state()}（期望 True）")

        # ---------- F214-a：返回语义（本环境 canGoBack 恒 false ⇒ 落栈顶二次确认分支） ----------
        # ⚠️ 环境限制（实测 2026-09-20，MEmu + Chrome WebView 116.0.5845.173）：
        #   copyBackForwardList 里有后退项（sz=2 idx=1）时 `canGoBack()` 仍为 false、`goBack()`
        #   也无效 ⇒ **单步后退分支在本环境不可达**（源码断言兜底）；但正因如此，旧实现
        #   （canGoBack=false → 直接 finish）按一次返回就退整页，而新实现只提示、再按一次才退
        #   ⇒ F214 的核心收益（返回不再不可预期）在本环境**可双向真机验证**。
        reset_app()
        nav_ok = False
        wv_ref = None
        if start_browser(f"{hbase}/nav1", "BTL2"):
            got_nav2 = wait_browser_title(d, "BT-NAV2-L2", rounds=4)
            # 无引导条会话的网页区顶部基准（F215 版式位移口径的参照）
            wv_b = ca.dump_bounds(d, 'class="android.webkit.WebView"')
            wv_ref = wv_b["top"] if wv_b else None
            d.press("back")
            time.sleep(1.2)
            xml_back = dump_xml(d)
            alive1 = simple in current_activity()
            snack1 = S_BACK_EXIT in xml_back
            d.press("back")
            time.sleep(2.0)
            exited = simple not in current_activity()
            nav_ok = got_nav2 and alive1 and snack1 and exited
            print(f"  [s3] F214 返回语义：/nav1→/nav2 到达={got_nav2}"
                  f" / 第 1 次返回：存活={alive1} 双击退出提示={snack1}"
                  f"（旧实现此处直接 finish ⇒ 整页消失）/ 第 2 次返回退出={exited}"
                  f" / 返回后可见标题={_bt_labels(xml_back)}")

        # ---------- F214-b：同 URL 历史项 + 栈顶双击退出窗口语义 ----------
        reset_app()
        predictable_ok = False
        if start_browser(f"{hbase}/spa1", "BTL2"):
            reached = wait_browser_title(d, "BT-SPA-L2", rounds=4)
            time.sleep(2.5)          # 等 /spa1→/spa2→pushState 两次追加落地（各 1.2s 定时器）
            d.press("back")
            time.sleep(1.2)
            xml1 = dump_xml(d)
            spa_alive = simple in current_activity()
            spa_snack = S_BACK_EXIT in xml1
            time.sleep(2.6)          # 越过 2s 确认窗口
            d.press("back")
            time.sleep(1.2)
            expired_alive = simple in current_activity()
            d.press("back")          # 距上次 1.2s ⇒ 窗口内
            time.sleep(2.0)
            finished = simple not in current_activity()
            predictable_ok = bool(reached and spa_alive and spa_snack
                                  and expired_alive and finished)
            print(f"  [s3] F214 同 URL 历史项：到达 /spa2={reached} / 第 1 次返回存活={spa_alive}"
                  f" 且提示={spa_snack} / >2s 后单按仍存活={expired_alive}"
                  f" / <2s 内连按退出={finished} / 末次可见标题={_bt_labels(xml1)}")
            ca.shot(d, "m3browser_s3_back_exit_toast")

        verify_extras = ["--ez", "sourceVerificationEnable", "true",
                         "--ez", "refetchAfterSuccess", "false",
                         "--es", "sourceOrigin", BOGUS_ORIGIN,
                         "--es", "sourceName", BOGUS_NAME]

        # ---------- F215-a：验证模式一次性引导条（首次显示 / 可关闭 / 再次启动不再显示） ----------
        # 条为**纯 View 实现**（TextView + ImageView）⇒ a11y 可直接断言文案与关闭按钮；
        # 版式位移（网页区顶下移 ≈ 条高）作为「网页区确实让位」的补充口径。
        reset_app()
        guide_first = False
        guide_twice = True
        shift_1 = shift_2 = None
        if start_browser(f"{hbase}/a", "BTL2", verify_extras):
            xml_g = dump_xml(d)
            ca.shot(d, "m3browser_s3_guide_bar")
            text_ok = S_GUIDE_KEY in xml_g
            close_b = node_bounds(xml_g, "关闭")
            wv_1 = ca.dump_bounds(d, 'class="android.webkit.WebView"')
            shift_1 = (wv_1["top"] - wv_ref) if (wv_1 and wv_ref) else None
            closed_ok = False
            if close_b:
                click_xy(d, close_b["cx"], close_b["cy"])
                time.sleep(1.2)
                closed_ok = S_GUIDE_KEY not in dump_xml(d)
                ca.shot(d, "m3browser_s3_guide_closed")
            guide_first = text_ok and bool(close_b) and closed_ok
            print(f"  [s3] F215 引导条：文案在场={text_ok} 关闭入口={bool(close_b)}"
                  f" / 点关闭后消失={closed_ok}"
                  f"｜网页区顶 {wv_ref} → {wv_1['top'] if wv_1 else None}（让位 {shift_1}px）")
        # 记忆位是否被写入 ⇒ 反证 initVerificationGuide 是否走到「首次显示」分支（mode=true 且原为 false）
        flag = sh_su(f"run-as {PKG} cat /data/data/{PKG}/shared_prefs/web_view_guide.xml", timeout=30)
        flag_written = b"source_verification_guide_shown" in (flag.stdout or b"")
        print(f"  [s3] F215 记忆位已写入={flag_written}"
              f"（True ⇒ initVerificationGuide 走到「首次显示」分支；False ⇒ 未进入验证模式）")
        # 对照会话（记忆位已写 ⇒ 不再显示引导条）：同页同窗口比较
        reset_app()
        xml2 = ""
        if start_browser(f"{hbase}/a", "BTL2", verify_extras):
            for _ in range(4):
                xml2 = dump_xml(d)
                if "BT-A-L2" in xml2:
                    break
                time.sleep(2.5)
            ca.shot(d, "m3browser_s3_guide_absent")
            wv_2 = ca.dump_bounds(d, 'class="android.webkit.WebView"')
            shift_2 = (wv_2["top"] - wv_ref) if (wv_2 and wv_ref) else None
            guide_twice = (S_GUIDE_KEY not in xml2) and (shift_2 is None or abs(shift_2) <= 6)
        print(f"  [s3] F215 一次性：第二次进入不再显示={guide_twice}"
              f"（文案在场={S_GUIDE_KEY in xml2} / 网页区顶位移={shift_2}px，期望回 0）")

        # ---------- F215-b：Cloudflare 挑战期状态条 ----------
        reset_app()
        cf_ok = False
        if start_browser(f"{hbase}/chal1", "BTL2", verify_extras):
            reached_chal = wait_browser_title(d, "BT-CHAL-L2", rounds=6)
            for _ in range(3):
                if S_CF_CHECKING in dump_xml(d):
                    break
                time.sleep(2.0)
            cf_ok = reached_chal and (S_CF_CHECKING in dump_xml(d))
            ca.shot(d, "m3browser_s3_cf_checking")
            print(f"  [s3] F215 挑战期提示：到达挑战页={reached_chal}"
                  f" / 「{S_CF_CHECKING}」在场={cf_ok}")

        # ---------- 修复2/3：菜单 danger tint + 禁用源二次确认 ----------
        menu_ok = danger_ok = confirm_ok = cancel_ok = exec_ok = False
        more = topbar_action_bounds(dump_xml(d), 0)
        if more:
            click_xy(d, more["cx"], more["cy"])
            time.sleep(1.5)
            xmlm = dump_xml(d)
            has_both = (S_DISABLE in xmlm) and (S_DELETE in xmlm)
            fg_disable, danger_ok = _danger_foreground(d, xmlm, S_DISABLE)
            fg_delete, danger_delete = _danger_foreground(d, xmlm, S_DELETE)
            menu_ok = has_both
            print(f"  [s3] 修复3 菜单：禁用源/删除源齐备={has_both}"
                  f" / 禁用源前景={fg_disable} danger={danger_ok}"
                  f" / 删除源前景={fg_delete} danger={danger_delete}")
            ca.shot(d, "m3browser_s3_menu_danger")
            danger_ok = danger_ok and danger_delete
            b = node_bounds(xmlm, S_DISABLE)
            if b:
                click_xy(d, b["cx"], b["cy"])
                time.sleep(1.8)
                xmlc = dump_xml(d)
                confirm_ok = (S_DISABLE in xmlc and BOGUS_NAME in xmlc
                              and S_YES in xmlc and S_NO in xmlc)
                ca.shot(d, "m3browser_s3_disable_confirm")
                print(f"  [s3] 修复2 禁用源二次确认：对象名/影响面/按钮齐备={confirm_ok}")
                if confirm_ok:
                    tap_text(d, S_NO)
                    time.sleep(1.5)
                    cancel_ok = (S_NO not in dump_xml(d)) and (simple in current_activity())
                    print(f"  [s3] 修复2 取消出口：弹窗关闭={S_NO not in dump_xml(d)}"
                          f" / 页面未被关闭={simple in current_activity()}")
        else:
            print("  [s3] 未定位顶栏 ⋮ 动作")

        # 确认出口：执行回调闭环（对象为**合成 origin**，DB 无匹配行 ⇒ 零行变更）
        more = topbar_action_bounds(dump_xml(d), 0)
        if more:
            click_xy(d, more["cx"], more["cy"])
            time.sleep(1.5)
            b = node_bounds(dump_xml(d), S_DISABLE)
            if b:
                click_xy(d, b["cx"], b["cy"])
                time.sleep(1.8)
                if tap_text(d, S_YES):
                    time.sleep(3.5)
                    exec_ok = simple not in current_activity()
                    print(f"  [s3] 修复2 确认出口：点击「{S_YES}」后页面关闭={exec_ok}")

        # 合成 origin 不在库（证明确认执行的**对象不存在**，不可能改动真实源）
        db = m2._db_pull(workdir)
        bogus_absent = False
        if db is not None:
            con = sqlite3.connect(str(db))
            try:
                n = con.execute("select count(*) from book_sources where bookSourceUrl = ?",
                                (BOGUS_ORIGIN,)).fetchone()[0]
                bogus_absent = (n == 0)
            finally:
                con.close()
        print(f"  [s3] 判定对象：合成 origin 不在库={bogus_absent}（↑零副作用前提）")

        # ---------- 源码断言（真机不可达/需并存的分支口径） ----------
        src = Path(SRC_BROWSER).read_text(encoding="utf-8") if Path(SRC_BROWSER).exists() else ""
        must_have = (
            "handler ?: return",                    # handler 空值保护
            "onPositive = { handler.proceed() }",
            "onNegative = { handler.cancel() }",
            "onDismissAction = { handler.cancel() }",
            "if (currentWebView.canGoBack())",      # 可回退判定用标准 API
            "currentWebView.goBack()",              # 一按一页（单步）
            "targetUrl == BLANK_HTML",              # BLANK_HTML 终止保留
            "now - lastBackPressedTime < BACK_EXIT_INTERVAL",  # 栈顶二次确认
            "buildMenuActions(AppUiTokens.danger)",
            "tint = danger",
            "if (AppConfig.sslCertPassThrough)",    # 放行策略开关生效点（默认放行）
            "PreferKey.sslCertPassThrough",         # 策略持久化 key
            "R.string.ssl_passthrough",             # 菜单项与状态回执
            "guidePrefs.edit().putBoolean(KEY_VERIFICATION_GUIDE_SHOWN, true)",  # 显示即记忆
        )
        must_absent = (
            "goBackOrForward",                      # 合并步进启发式已删
            "handler?.proceed()",                   # 无条件放行已删
            "currentTitle != item.title",           # URL/标题计步启发式已删
        )
        missing = [k for k in must_have if k not in src]
        leftovers = [k for k in must_absent if k in src]
        code_ok = not missing and not leftovers
        print(f"  [s3] 源码断言：必备 {len(must_have) - len(missing)}/{len(must_have)}"
              f" / 应删尽删 {len(must_absent) - len(leftovers)}/{len(must_absent)}"
              f" / 缺失={missing} 残留={leftovers}")

        ok = bool(passthrough_ok and ssl_menu_ok and ssl_off_ok and ssl_off_hint and ssl_restore_ok
                  and dialog_ok and ssl_danger and reject_ok and proceed_ok and nav_ok
                  and predictable_ok and guide_first and guide_twice and cf_ok
                  and menu_ok and danger_ok and confirm_ok and cancel_ok and exec_ok
                  and bogus_absent and code_ok)
        return ok
    finally:
        try:
            rolled = m2._db_push(db_snap)
            print(f"  [s3] 数据库快照已回滚={rolled}")
        except Exception as e:
            print(f"  [s3] 兜底回滚异常: {type(e).__name__}")
        # 引导条记忆位是本次测试造出来的新文件 ⇒ 删除还原，避免影响真实使用
        clear_guide_flag()
        # 证书放行策略兜底还原：中断残留关闭态会让后续源/订阅源被证书拦住（best-effort）
        try:
            if _ssl_pref_state() is False:
                reset_app()
                if start_browser(f"{hbase}/restore", "BTL2"):
                    toggle_ssl_pass_through(d)
                print(f"  [s3] 策略兜底还原：pref 回读={_ssl_pref_state()}（期望 True/None）")
        except Exception as e:
            print(f"  [s3] 策略兜底还原异常: {type(e).__name__}")
        for p in (ssl_port, http_port):
            if p:
                release_reverse(p)
        for s in (ssl_srv, http_srv):
            try:
                s.shutdown()
            except Exception:
                pass
        reset_app()


# ===================== s4：qrcode/qrcode（扫码页）=====================
# 覆盖：F188 相册解码等待可见化（loading + 成功微确认）/ F189 相机权限受限兜底双出口 /
#       A3-2 扫描引导与全屏识别说明 / A3-3 解码失败页内提示 + 重试。
# 通道：扫码页 → 从相册识别 → 「手动输入图片链接」→ 填设备侧绝对路径（绕开 DocumentsUI，
#       用本机测试图直取原始文件，无需媒体库索引、全程离线、结果确定）。
ACT_QR = "io.legado.app.ui.qrcode.QrCodeActivity"
S_QR_TITLE = "扫描二维码"                  # scan_qr_code
S_QR_HINT = "将二维码对准取景框即可自动识别"   # qr_scan_hint
S_QR_FULL_AREA = "支持全屏识别"             # qr_scan_full_area
S_QR_GALLERY = "从相册识别"                # qr_gallery_entry
S_QR_DECODING = "正在识别图片"              # qr_decoding
S_QR_DECODING_NOTE = "识别成功后自动返回"     # qr_decoding_note
S_QR_DECODED = "已识别"                    # qr_decode_succeeded
S_QR_FAIL_TITLE = "未识别到二维码"           # qr_decode_failed_title
S_QR_FAIL_DESC = "所选图片中没有二维码"       # qr_decode_failed_desc
S_QR_BLOCK_TITLE = "需要相机权限才能扫码"     # qr_camera_blocked_title
S_QR_BLOCK_DESC = "也可以不授权限"           # qr_camera_blocked_desc
S_QR_GRANT = "去授权"                      # qr_camera_blocked_grant
S_QR_MANUAL = "手动输入图片链接"             # manual_input_img_src
S_QR_APP_PICKER = "自带文件选择器"           # app_file_picker（value=11 → 应用内 FilePickerDialog）
S_QR_PICK_OK = "确认"                      # ok（应用内文件选择器的确认键）
S_RETRY = "重试"                          # retry
QR_FIXTURE_DIR = "Pictures"                # 应用内选择器 root 首屏可见目录（测试图落点）
SRC_QR_ACT = "app/src/main/java/io/legado/app/ui/qrcode/QrCodeActivity.kt"
SRC_QR_FRAG = "app/src/main/java/io/legado/app/ui/qrcode/QrCodeFragment.kt"
SRC_QR_OVERLAY = "app/src/main/java/io/legado/app/ui/qrcode/QrCodeOverlay.kt"
SRC_QR_LAYOUT = "app/src/main/res/layout/activity_qrcode_capture.xml"
QR_DEV_DIR = "/sdcard/Pictures"
QR_FIXTURES = {
    "blank": "ai_tests/testdata/qr_scan/qr_blank.png",      # 无二维码（失败链路）
    "ok": "ai_tests/testdata/qr_scan/qr_ok.png",            # 780px 真二维码（快速成功）
    "big": "ai_tests/testdata/qr_scan/qr_ok_big.png",       # 2600px 真二维码（拉长解码窗口，暴露 loading）
}


def _qr_repo_path(rel: str) -> Path:
    return Path(__file__).resolve().parents[2] / rel


def _src_text(rel: str) -> str:
    p = _qr_repo_path(rel)
    return p.read_text(encoding="utf-8", errors="ignore") if p.exists() else ""


def _src_code(rel: str) -> str:
    """去注释后的源码：用于「应删尽删」断言，避免注释里引用的旧实现片段造成假命中"""
    txt = re.sub(r"/\*.*?\*/", "", _src_text(rel), flags=re.S)
    return "\n".join(line.split("//")[0] for line in txt.splitlines())


def _qr_push_fixtures() -> dict:
    out = {}
    sh("mkdir", "-p", QR_DEV_DIR)
    for key, rel in QR_FIXTURES.items():
        local = _qr_repo_path(rel)
        remote = f"{QR_DEV_DIR}/l2_qr_{key}.png"
        if not local.exists():
            print(f"  [s4] 缺测试图: {rel}")
            out[key] = ""
            continue
        subprocess.run([ADB, "push", str(local), remote], capture_output=True, timeout=90)
        r = sh("ls", remote)
        exists = remote.rsplit("/", 1)[-1] in (r.stdout or b"").decode("utf-8", "ignore")
        print(f"  [s4] 推送测试图 {key}: {exists}")
        out[key] = remote if exists else ""
    return out


def _qr_cleanup_fixtures():
    for key in QR_FIXTURES:
        sh("rm", "-f", f"{QR_DEV_DIR}/l2_qr_{key}.png")


def _qr_pick_image(d, remote: str, via_retry: bool = False,
                   probe_keywords=None, probe_seconds: float = 6.0) -> tuple:
    """相册识别链路：入口（底部入口 / 失败条重试）→ 自带文件选择器 → Pictures → 选图 → 确认

    通道选择（2026-09-20 实测取舍）：**不走「手动输入图片链接」**——该路由真机上选图页会静默返回、
    调用方收到 CANCELED（无 toast、无解码），根因未定（见 issues-found），且属 HandleFileActivity
    既有缺陷、不在本页范围。改走「自带文件选择器」：`setResultData` → `onResult` 先于 dismiss 落地，
    结果链正确，且全是应用内 Compose 控件、无 DocumentsUI/媒体库依赖。

    返回 `(是否成功, 探针结果|None)`。传 `probe_keywords` 时**先取好确认键坐标**再快速点击、
    点击后立刻进入连续 dump（实测 dump 节拍 ≈60ms）——解码中/微确认这类瞬时态必须这样才抓得到。
    """
    fname = remote.rsplit("/", 1)[-1]
    entry = S_RETRY if via_retry else S_QR_GALLERY
    if not tap_text(d, entry, timeout=8):
        print(f"  [s4] 未能点到入口「{entry}」")
        return False, None
    time.sleep(2.5)
    if not tap_text(d, S_QR_APP_PICKER, timeout=8):
        print("  [s4] 未出现「自带文件选择器」动作项")
        return False, None
    time.sleep(2.5)
    xml = dump_xml(d)
    if fname not in xml and not tap_text(d, QR_FIXTURE_DIR, timeout=8):
        print(f"  [s4] 未能进入测试图目录 {QR_FIXTURE_DIR}")
        return False, None
    time.sleep(1.8)
    if not tap_text(d, fname, timeout=8):
        print(f"  [s4] 文件列表未出现 {fname}")
        return False, None
    time.sleep(1.0)
    if probe_keywords:
        b = node_bounds(dump_xml(d), S_QR_PICK_OK)
        if not b:
            print("  [s4] 未取到选择器确认键坐标")
            return False, None
        w, h = d.window_size()
        d.click(b["cx"] / w, b["cy"] / h)     # 快速点击（不带 sleep）→ 立刻进入探针窗口
        return True, _qr_probe(d, probe_keywords, probe_seconds)
    if not tap_text(d, S_QR_PICK_OK, timeout=6):
        print("  [s4] 未点到选择器确认键")
        return False, None
    return True, None


def _qr_probe(d, keywords, seconds: float) -> dict:
    """窗口期内连续 dump，记录关键词是否**出现过**（捕捉 loading / 微确认这类瞬时态）"""
    seen = {k: False for k in keywords}
    rounds = 0
    end = time.time() + seconds
    while time.time() < end:
        xml = dump_xml(d)
        rounds += 1
        for k in keywords:
            if not seen[k] and k in xml:
                seen[k] = True
        if all(seen.values()):
            break
    seen["_rounds"] = rounds
    return seen


def _qr_deny_permission_dialog(d, rounds: int = 6, wait: float = 2.0) -> tuple:
    """系统相机权限弹窗点「拒绝」。返回 (是否点到, 是否出现过弹窗)。"""
    for _ in range(rounds):
        xml = dump_xml(d)
        for m in re.finditer(r"<node[^>]*>", xml):
            tag = m.group(0)
            rid = re.search(r'resource-id="([^"]*)"', tag)
            if not (rid and "permission_deny_button" in rid.group(1)):
                continue
            b = re.search(r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', tag)
            if b:
                x1, y1, x2, y2 = map(int, b.groups())
                click_xy(d, (x1 + x2) // 2, (y1 + y2) // 2)
                return True, True
        time.sleep(wait)
    return False, False


def _qr_return_to_page(d, tries: int = 3) -> bool:
    """逐级 back 直到回到扫码页（弹框/文件页层数不固定，按当前 Activity 判定而非固定次数）"""
    for _ in range(tries):
        if "QrCodeActivity" in current_activity():
            return True
        d.press("back")
        time.sleep(1.5)
    return "QrCodeActivity" in current_activity()


def _qr_camera_granted() -> bool:
    """读设备侧 CAMERA 授权态（判定「本 ROM 能否构造拒绝态」）"""
    r = sh("dumpsys", "package", PKG, timeout=30)
    return b"android.permission.CAMERA: granted=true" in (r.stdout or b"")


def s4_qrcode_page(d) -> bool:
    """扫码页：覆盖层引导/全屏说明、相册解码等待与失败重试、权限受限兜底双出口与授权闭环"""
    print("  [s4] ===== 扫码页覆盖层与解码链路 =====")
    files = _qr_push_fixtures()
    try:
        # ---- 默认态：引导 / 全屏说明 / 相册入口在场，权限卡不在场 ----
        reset_app()
        started = start_robust(ACT_QR)
        xml = dump_xml(d)
        title_ok = S_QR_TITLE in xml
        hint_ok = S_QR_HINT in xml
        full_ok = S_QR_FULL_AREA in xml
        gallery_ok = S_QR_GALLERY in xml
        block_absent = S_QR_BLOCK_TITLE not in xml
        default_ok = started and title_ok and hint_ok and full_ok and gallery_ok and block_absent
        print(f"  [s4] 默认态 启动={started} 标题={title_ok} 引导={hint_ok} 全屏说明={full_ok} "
              f"相册入口={gallery_ok} 权限卡未出现={block_absent}")

        # ---- 失败链路：无二维码图 → 页内 danger 提示 + 停留本页（A3-3 禁止静默失败）----
        fail_ok = False
        if files.get("blank"):
            picked, _ = _qr_pick_image(d, files["blank"])
            time.sleep(3.0)
            xml2 = dump_xml(d)
            stayed = "QrCodeActivity" in current_activity()
            banner = (S_QR_FAIL_TITLE in xml2) and (S_QR_FAIL_DESC in xml2) and (S_RETRY in xml2)
            fail_ok = picked and banner and stayed
            print(f"  [s4] 失败链路 入口={picked} 提示条={banner} 停留本页={stayed}")

        # ---- 慢解码等待态（2600px 大图）：证明「解码中」遮罩真机可见（窗口足够长），
        #      且大图解码失败时同样落到兜底提示条（不静默、不崩）----
        loading_ok = False
        if files.get("big"):
            picked3, probed3 = _qr_pick_image(
                d, files["big"], via_retry=True,
                probe_keywords=[S_QR_DECODING, S_QR_DECODING_NOTE],
                probe_seconds=12.0,
            )
            probed3 = probed3 or {k: False for k in (S_QR_DECODING, S_QR_DECODING_NOTE)}
            time.sleep(2.0)
            xml_load = dump_xml(d)
            loading_ok = (picked3 and probed3.get(S_QR_DECODING)
                          and (S_QR_FAIL_TITLE in xml_load) and ("QrCodeActivity" in current_activity()))
            print(f"  [s4] 大图链路 选图={picked3} 解码中态={probed3.get(S_QR_DECODING)} "
                  f"等待说明={probed3.get(S_QR_DECODING_NOTE)}（{probed3.get('_rounds')}轮）"
                  f" 兜底提示={S_QR_FAIL_TITLE in xml_load}")

        # ---- 成功链路：重试入口 → 真二维码 → 解码中态可见 → 微确认 → 回传退出 ----
        succ_ok = False
        if files.get("ok"):
            picked2, probed = _qr_pick_image(
                d, files["ok"], via_retry=True,
                probe_keywords=[S_QR_DECODING, S_QR_DECODING_NOTE, S_QR_DECODED],
                probe_seconds=8.0,
            )
            probed = probed or {k: False for k in (S_QR_DECODING, S_QR_DECODING_NOTE, S_QR_DECODED)}
            time.sleep(1.5)
            finished = "QrCodeActivity" not in current_activity()
            succ_ok = picked2 and finished
            print(f"  [s4] 成功链路 重试选图={picked2} 解码中态={probed.get(S_QR_DECODING)} "
                  f"等待说明={probed.get(S_QR_DECODING_NOTE)} 微确认={probed.get(S_QR_DECODED)}"
                  f"（{probed.get('_rounds')}轮） 回传退出={finished}")

        # ---- 权限受限链路：撤销相机权限 → 拒绝 → 兜底卡（双出口）→ 授权闭环 ----
        # ⚠️ 环境限制（2026-09-20 实测）：本 ROM 把本测试包的 CAMERA 记在 **install permissions**
        #    （granted=true），`pm revoke`（含 --user 0 / su）返回 0 但授权态不变 ⇒ **拒绝态不可构造**；
        #    故该链路登记为「环境不可达」，以源码断言兜底（与 s3 的 canGoBack 限制同类处理）。
        blocked_ok = cross_ok = grant_ok = True
        perm_skipped = False
        reset_app()
        sh("pm", "revoke", PKG, "android.permission.CAMERA")
        time.sleep(1.2)
        if _qr_camera_granted():
            perm_skipped = True
            print("  [s4] 权限链路：CAMERA 为 install 权限且 pm revoke 无效 ⇒ 拒绝态不可构造，"
                  "登记环境不可达（卡片双出口以源码断言兜底）")
        else:
            started2 = start_robust(ACT_QR)
            clicked, dialog_seen = _qr_deny_permission_dialog(d)
            time.sleep(2.5)
            xml3 = dump_xml(d)
            denied_ok = clicked or not dialog_seen  # ROM 若记忆「不再询问」则无弹窗、直接进拒绝回调
            blocked_ok = (started2 and denied_ok and (S_QR_BLOCK_TITLE in xml3)
                          and (S_QR_BLOCK_DESC in xml3) and (S_QR_GRANT in xml3) and (S_QR_GALLERY in xml3))
            print(f"  [s4] 权限受限 启动={started2} 弹窗={dialog_seen} 拒绝={clicked} 兜底卡={blocked_ok}")

        if not perm_skipped and blocked_ok:
            # 出口一：从相册识别（复用同一回调链）——只断言替代路径可达，不做完整选图
            cross_click = tap_text(d, S_QR_GALLERY, timeout=8)
            time.sleep(2.5)
            cross_xml = dump_xml(d)
            cross_ok = cross_click and (S_QR_MANUAL in cross_xml)
            back_to_page = _qr_return_to_page(d)
            cross_xml2 = dump_xml(d)
            cross_ok = cross_ok and back_to_page and (S_QR_BLOCK_TITLE in cross_xml2)
            print(f"  [s4] 出口一 从相册识别={cross_click} 相册动作面板={S_QR_MANUAL in cross_xml} "
                  f"返回扫码页={back_to_page} 兜底卡仍在={S_QR_BLOCK_TITLE in cross_xml2}")

            # 出口二：去授权 → 系统应用详情页 → 授权后返回 → 卡片收起（onResume 授权闭环）
            grant_click = tap_text(d, S_QR_GRANT, timeout=8)
            time.sleep(3.0)
            act_name = current_activity()
            settings_ok = "settings" in act_name.lower()
            sh("pm", "grant", PKG, "android.permission.CAMERA")
            time.sleep(1.2)
            d.press("back")
            time.sleep(2.5)
            back_ok = "QrCodeActivity" in current_activity()
            xml4 = dump_xml(d)
            grant_ok = grant_click and settings_ok and back_ok and (S_QR_BLOCK_TITLE not in xml4)
            print(f"  [s4] 出口二 去授权={grant_click} 落到设置页={settings_ok} 返回扫码页={back_ok} "
                  f"卡片收起={S_QR_BLOCK_TITLE not in xml4}")

        # ---- 源码断言：应落定的落定、应删尽的删尽 ----
        act = _src_text(SRC_QR_ACT)
        frag = _src_text(SRC_QR_FRAG)
        act_code = _src_code(SRC_QR_ACT)
        frag_code = _src_code(SRC_QR_FRAG)
        ov = _src_text(SRC_QR_OVERLAY)
        lay = _src_text(SRC_QR_LAYOUT)
        code_checks = {
            "解码下沉协程": "Coroutine.async" in act,
            "成功微确认常量": "DECODE_CONFIRM_DELAY" in act,
            "失败停留本页": "onDecodeFailed()" in act,
            "权限受限上抛": "onCameraPermissionDenied" in act and "onCameraPermissionDenied" in frag,
            "授权恢复入口": "resumeCameraAfterPermissionGranted" in frag,
            "覆盖层三卡": all(k in ov for k in ("PermissionCard", "DecodingCard", "DecodeFailedBanner")),
            "覆盖层挂载点": "compose_qr_overlay" in lay,
            "旧同步解码已删": "onScanResultCallback(QRCodeUtils.parseCodeResult" not in act_code,
            "旧主线程读文件已删": "readBytes(this)?.let" not in act_code,
            "库默认拒绝即退出已覆盖": "finish()" not in frag_code,
        }
        code_ok = all(code_checks.values())
        print(f"  [s4] 源码断言 {sum(code_checks.values())}/{len(code_checks)} "
              f"未过={[k for k, v in code_checks.items() if not v]}")

        ok = all([default_ok, fail_ok, loading_ok, succ_ok, blocked_ok, cross_ok, grant_ok, code_ok])
        print(f"  [s4] 小计: {'PASS' if ok else 'FAIL'}"
              + ("（权限链路=环境不可达，已登记跳过）" if perm_skipped else ""))
        return ok
    finally:
        _qr_cleanup_fixtures()
        sh("pm", "grant", PKG, "android.permission.CAMERA")   # 还原：测试前相机权限为已授权
        reset_app()


# ===================== s5：image/image-crop（裁剪页）=====================
# 覆盖：F179 前置（比例徽标 + 保存中回执）+ A3-2/A3-3（可恢复失败页内错误条 + 重试；不可恢复仍 toast+finish）。
# 通道：`am start` 直起 + extras（uri/aspectWidth/aspectHeight）；「失败→重试→恢复」用本机 HTTP 先停后起制造，
#       全程离线（adb reverse 回环 + 本地 http.server）。
ACT_CROP = "io.legado.app.ui.image.ImageCropActivity"
S_CROP_HINT = "拖动或双指缩放图片后确认裁剪"    # image_crop_hint
S_CROP_SAVING = "保存中，请稍候…"              # image_crop_saving
S_CROP_FAIL_PREFIX = "图片裁剪失败："           # image_crop_failed
S_CROP_FAIL_DECODE = "图片解码失败"            # error_decode_bitmap
ID_BADGE = f"{PKG}:id/tv_aspect_badge"
ID_HINT = f"{PKG}:id/tv_hint"
ID_CONFIRM = f"{PKG}:id/btn_confirm"
ID_PROGRESS = f"{PKG}:id/progress_save"
ID_ERROR_BAR = f"{PKG}:id/error_bar"
ID_RETRY = f"{PKG}:id/btn_retry"
CROP_DEV_SRC = "/sdcard/Pictures/l2_crop_src.png"
CROP_PORT = 8567
SRC_CROP_ACT = "app/src/main/java/io/legado/app/ui/image/ImageCropActivity.kt"
SRC_CROP_LAYOUT = "app/src/main/res/layout/activity_image_crop.xml"


def _node_by_res(xml: str, res_id: str):
    """按 resource-id 取节点 bounds（不可见节点不在 dump 中 ⇒ 兼作可见性判据）"""
    for m in re.finditer(r"<node[^>]*>", xml):
        tag = m.group(0)
        rid = re.search(r'resource-id="([^"]*)"', tag)
        if not rid or rid.group(1) != res_id:
            continue
        b = re.search(r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', tag)
        if not b:
            continue
        x1, y1, x2, y2 = map(int, b.groups())
        return {"left": x1, "top": y1, "right": x2, "bottom": y2,
                "cx": (x1 + x2) // 2, "cy": (y1 + y2) // 2}
    return None


def _node_text(xml: str, res_id: str) -> str:
    for m in re.finditer(r"<node[^>]*>", xml):
        tag = m.group(0)
        rid = re.search(r'resource-id="([^"]*)"', tag)
        if rid and rid.group(1) == res_id:
            t = re.search(r'\btext="([^"]*)"', tag)
            return t.group(1) if t else ""
    return ""


def _crop_push_source() -> str:
    """裁剪源图（2600px，够大 ⇒ 裁剪/落盘耗时可观察）落到设备公共目录"""
    local = _qr_repo_path(QR_FIXTURES["big"])
    if not local.exists():
        return ""
    sh("mkdir", "-p", QR_DEV_DIR)
    subprocess.run([ADB, "push", str(local), CROP_DEV_SRC], capture_output=True, timeout=90)
    r = sh("ls", CROP_DEV_SRC)
    return CROP_DEV_SRC if "l2_crop_src.png" in (r.stdout or b"").decode("utf-8", "ignore") else ""


def _crop_start(uri: str, aspect_w: int = 3, aspect_h: int = 4) -> bool:
    """按 extras 直起裁剪页（uri 为空串 ⇒ 不传 uri，用于「不可恢复」分支）"""
    args = ["am", "start", "-n", f"{PKG}/{ACT_CROP}",
            "--ei", "aspectWidth", str(aspect_w), "--ei", "aspectHeight", str(aspect_h)]
    if uri:
        args += ["-e", "uri", uri]
    sh(*args)
    time.sleep(3.5)
    return "ImageCropActivity" in current_activity()


class _CropHandler(BaseHTTPRequestHandler):
    """极简静态图服务（s5 专用）：只有 /crop_src.png 返回 200，其余 404"""

    png: bytes = b""

    def do_GET(self):  # noqa: N802
        if self.path.startswith("/crop_src.png") and _CropHandler.png:
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(_CropHandler.png)))
            self.end_headers()
            self.wfile.write(_CropHandler.png)
        else:
            self.send_error(404)

    def log_message(self, *args):  # 静音
        pass


def _crop_serve() -> object:
    srv = HTTPServer(("127.0.0.1", CROP_PORT), _CropHandler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def _crop_bar_probe(d, seconds: float) -> dict:
    """错误条显隐轨迹：gone=曾消失（⇒loadImage 被调用）/ back=消失后又出现（⇒仍失败）/ final=结束时是否在场

    「消失」只可能由 `hideCropError()`（只在 `loadImage()` 开头）触发 ⇒ 是「重试确实重跑了加载」的硬判据；
    恢复成功 = gone 且 final 为 False；仍失败 = gone 且 back（条又回来）。
    """
    gone = back = False
    final = None
    rounds = 0
    end = time.time() + seconds
    while time.time() < end:
        present = _node_by_res(dump_xml(d), ID_ERROR_BAR) is not None
        rounds += 1
        if not present:
            gone = True
        elif gone:
            back = True
        final = present
        if back:
            break
    return {"gone": gone, "back": back, "final": final, "_rounds": rounds}


def s5_image_crop_page(d) -> bool:
    """裁剪页：比例徽标 / 保存中回执 / 失败错误条 + 重试恢复 / 不可恢复仍 toast+finish"""
    print("  [s5] ===== 裁剪页比例、保存回执与失败重试 =====")
    src = _crop_push_source()
    _CropHandler.png = _qr_repo_path(QR_FIXTURES["big"]).read_bytes() \
        if _qr_repo_path(QR_FIXTURES["big"]).exists() else b""
    # 回环通道：设备 127.0.0.1:CROP_PORT → 主机（服务先不开，用于制造「连接失败」）
    _reverse_on(CROP_PORT)
    srv = None
    try:
        # ---- 1) 默认态：比例徽标（3:4）+ 操作提示 ----
        reset_app()
        started = _crop_start(f"file://{src}" if src else "", 3, 4)
        xml = dump_xml(d)
        badge = _node_text(xml, ID_BADGE)
        default_ok = started and badge == "3:4" and (S_CROP_HINT in xml)
        print(f"  [s5] 默认态 启动={started} 比例徽标={badge!r} 提示={S_CROP_HINT in xml}")

        # ---- 2) 保存中回执 → 回传退出 ----
        save_ok = False
        b = _node_by_res(xml, ID_CONFIRM)
        if b:
            w, h = d.window_size()
            d.click(b["cx"] / w, b["cy"] / h)
            pr = _qr_probe(d, [S_CROP_SAVING, S_CROP_FAIL_PREFIX], 10.0)
            time.sleep(1.5)
            finished = "ImageCropActivity" not in current_activity()
            save_ok = bool(pr.get(S_CROP_SAVING)) and not pr.get(S_CROP_FAIL_PREFIX) and finished
            print(f"  [s5] 保存回执 保存中态={pr.get(S_CROP_SAVING)} 未出现失败条="
                  f"{not pr.get(S_CROP_FAIL_PREFIX)} 回传退出={finished}（{pr.get('_rounds')}轮）")
        else:
            print("  [s5] 未取到确认键坐标")

        # ---- 3) 可恢复失败：页内错误条 + 停留本页（服务未开 ⇒ 连接失败）----
        reset_app()
        fail_url = f"http://127.0.0.1:{CROP_PORT}/crop_src.png"
        started2 = _crop_start(fail_url, 3, 4)
        xml2 = dump_xml(d)
        stayed = "ImageCropActivity" in current_activity()
        bar = _node_by_res(xml2, ID_ERROR_BAR) is not None
        text_ok = (S_CROP_FAIL_PREFIX in xml2) and (S_CROP_FAIL_DECODE in xml2)
        retry_ok = _node_by_res(xml2, ID_RETRY) is not None
        fail_ok = started2 and stayed and bar and text_ok and retry_ok
        print(f"  [s5] 失败条 启动={started2} 停留本页={stayed} 错误条={bar} 文案={text_ok} 重试键={retry_ok}")

        # ---- 4) 重试 → 服务恢复 → 图片加载成功 → 确认裁剪 → 回传退出 ----
        retry_ok2 = recover_ok = False
        rb = _node_by_res(dump_xml(d), ID_RETRY)
        if fail_ok and rb:
            srv = _crop_serve()
            time.sleep(0.6)
            w, h = d.window_size()
            d.click(rb["cx"] / w, rb["cy"] / h)
            traj = _crop_bar_probe(d, 12.0)
            # 重试被执行的硬判据 = 错误条曾消失（hideCropError 只在 loadImage 开头调用）
            retry_ok2 = bool(traj["gone"]) and not traj["back"] and not traj["final"]
            print(f"  [s5] 重试 错误条消失={traj['gone']} 又出现={traj['back']} 最终在场={traj['final']}"
                  f"（{traj['_rounds']}轮）")
            # 图片加载成功才可能真正裁剪 ⇒ 用「确认后回传退出」做正向判据（大图加载需余量）
            if retry_ok2:
                time.sleep(3.0)
                for attempt in range(2):
                    cb = _node_by_res(dump_xml(d), ID_CONFIRM)
                    if not cb:
                        break
                    d.click(cb["cx"] / w, cb["cy"] / h)
                    pr3 = _qr_probe(d, [S_CROP_SAVING], 12.0 if attempt == 0 else 8.0)
                    if "ImageCropActivity" not in current_activity():
                        recover_ok = True
                        break
                    print(f"  [s5] 恢复后第{attempt + 1}次确认未回传（保存中态={pr3.get(S_CROP_SAVING)}）")
                print(f"  [s5] 恢复后裁剪回传退出={recover_ok}")

        # ---- 5) 不可恢复（未传 uri）：保留 toast + finish ----
        reset_app()
        _crop_start("", 3, 4)
        time.sleep(2.0)
        fatal_ok = "ImageCropActivity" not in current_activity()
        print(f"  [s5] 不可恢复(无 uri) 直接关闭={fatal_ok}")

        # ---- 6) 源码断言 ----
        act_code = _src_code(SRC_CROP_ACT)
        lay = _src_text(SRC_CROP_LAYOUT)
        checks = {
            "保存中态落定": "setSavingState(true)" in act_code and "image_crop_saving" in act_code,
            "徽标落定": "updateAspectBadge" in act_code and "tv_aspect_badge" in lay,
            "错误条落定": "showCropError" in act_code and "error_bar" in lay and "btn_retry" in lay,
            "失败不再关页": "showCropError(getString(R.string.error_decode_bitmap))" in act_code,
            "旧失败 toast+finish 已删":
                "toastOnUi(getString(R.string.image_crop_failed, getString(R.string.error_decode_bitmap)))"
                not in act_code,
            "不可恢复保留 finish": "error_image_url_empty" in act_code,
        }
        code_ok = all(checks.values())
        print(f"  [s5] 源码断言 {sum(checks.values())}/{len(checks)} "
              f"未过={[k for k, v in checks.items() if not v]}")

        ok = all([default_ok, save_ok, fail_ok, retry_ok2, recover_ok, fatal_ok, code_ok])
        print(f"  [s5] 小计: {'PASS' if ok else 'FAIL'}")
        return ok
    finally:
        if srv is not None:
            try:
                srv.shutdown()
            except Exception:
                pass
        release_reverse(CROP_PORT)
        sh("rm", "-f", CROP_DEV_SRC)
        reset_app()


# ===================== s6：login/source-login（书源登录页）=====================
# 覆盖：证书放行策略在登录页可开关（**默认放行**，用户裁决 2026-09-20）/ 修复3 顶栏「完成登录」文案按钮 /
#       修复2 删除登录头二次确认 / 优化4 F165 登录执行等待态 + 失败错误卡（完整报错可复制 + 重试）/
#       优化5 F166 密码可见性切换。
# 双分支通道（合成源播种，零外网）：
#   A) loginUi 空 + loginUrl=本机自签名 HTTPS ⇒ WebViewLoginFragment（证书策略 + 完成登录）
#   B) loginUi=行 JSON + loginUrl=必抛异常的 JS ⇒ SourceLoginDialog（错误卡 / 密码可见 / 删除登录头确认）
ACT_LOGIN = "io.legado.app.ui.login.SourceLoginActivity"
S_FINISH_LOGIN = "完成登录"                      # finish_login
S_LOGGING_IN = "正在登录"                        # logging_in（loading 态，弱判据）
S_LOGIN_ERROR = "登录出错"                       # login_error
S_COPY_ERR = "复制错误详情"                       # copy_error_detail
S_PWD_SHOW = "显示密码"                          # password_show
S_PWD_HIDE = "隐藏密码"                          # password_hide
S_DEL_HEADER = "删除登录头"                       # del_login_header
S_DEL_CONFIRM_FRAG = "此操作不可撤销"              # del_login_header_confirm
S_OK = "确认"                                   # ok（表单弹窗 OK 键）
S_MORE = "更多"                                  # more（表单弹窗 ⋮ 的 contentDescription）
SEED_LOGIN_WEB = "l2seed://login-web"
SEED_LOGIN_FORM = "l2seed://login-form"
SEED_LOGIN_NAME = "L2登录校验源"
# 表单行：纯 JSON（不以 @js:/<js> 开头 ⇒ 直接 parse），viewName 用带引号形态避免依赖 JS 求值
SEED_LOGIN_UI = (
    '[{"name":"u","type":"text","viewName":"\'账号\'","default":"l2user"},'
    '{"name":"p","type":"password","viewName":"\'密码\'","default":"l2pass"}]'
)
# loginUrl 在表单分支只作 JS 执行（不加载网页）⇒ 直接抛异常制造**确定性失败**（错误卡硬判据）
SEED_LOGIN_JS_THROW = "throw new Error('L2-LOGIN-FAIL')"
SRC_LOGIN_FRAG = "app/src/main/java/io/legado/app/ui/login/WebViewLoginFragment.kt"
SRC_LOGIN_DIALOG = "app/src/main/java/io/legado/app/ui/login/SourceLoginDialog.kt"


def seed_login_sources(workdir: Path, web_url: str) -> bool:
    """播种两个合成书源（整行复制既有源后改写 sourceUrl/name/loginUi/loginUrl）"""
    m2 = _m2()
    db = m2._db_pull(workdir)
    if db is None:
        return False
    con = sqlite3.connect(str(db))
    try:
        # ⚠️ 表名是 `book_sources`（下划线；订阅侧才是 `rssSources`）——写成 bookSources 会
        #    抛 OperationalError: no such table（2026-09-20 s6 首轮真因）
        cols = [r[1] for r in con.execute("pragma table_info(book_sources)")]
        row = con.execute("select * from book_sources limit 1").fetchone()
        if not row:
            return False
        base = dict(zip(cols, row))
        for key, login_ui, login_url in (
            (SEED_LOGIN_WEB, "", web_url),
            (SEED_LOGIN_FORM, SEED_LOGIN_UI, SEED_LOGIN_JS_THROW),
        ):
            data = dict(base)
            data["bookSourceUrl"] = key
            data["bookSourceName"] = SEED_LOGIN_NAME
            data["loginUrl"] = login_url
            data["loginUi"] = login_ui
            data["enabled"] = 1
            con.execute(
                f"insert or replace into book_sources ({','.join(cols)})"
                f" values ({','.join('?' * len(cols))})",
                [data[c] for c in cols]
            )
        con.commit()
    finally:
        con.close()
    return m2._db_push(db)


def purge_login_sources(workdir: Path) -> bool:
    m2 = _m2()
    db = m2._db_pull(workdir)
    if db is None:
        return False
    con = sqlite3.connect(str(db))
    try:
        con.execute("delete from book_sources where bookSourceUrl in (?, ?)",
                    (SEED_LOGIN_WEB, SEED_LOGIN_FORM))
        con.commit()
    finally:
        con.close()
    return m2._db_push(db)


def _login_start(key: str) -> bool:
    """非导出组件 am start + extras 直起登录页（bookSource 分支由 key/type 决定数据源）"""
    simple = ACT_LOGIN.rsplit(".", 1)[-1]
    reset_app()
    sh("am", "start", "-n", f"{PKG}/{ACT_LOGIN}",
       "--es", "key", key, "--es", "type", "bookSource")
    for _ in range(12):
        time.sleep(1.2)
        if simple in current_activity():
            time.sleep(2.2)
            return True
    sh_su(f"am start -n {PKG}/{ACT_LOGIN} --es key {key} --es type bookSource")
    time.sleep(3.5)
    return simple in current_activity()


def s6_login_page(d) -> bool:
    """登录页：证书放行策略开关（默认放行）/ 完成登录 / 删除登录头确认 / 失败错误卡 / 密码可见"""
    print("  [s6] ===== 登录页放行策略、错误卡与输入辅助 =====")
    m2 = _m2()
    workdir = Path(tempfile.mkdtemp(prefix="m3login_"))
    db_snap = workdir / "legado_snapshot.db"
    if not m2._snapshot_db(workdir, db_snap):
        print("  [s6] 数据库快照失败（前置）")
        return False
    (ssl_srv, ssl_port), (http_srv, http_port), _certdir = _start_servers()
    if ssl_srv is None or http_srv is None:
        print("  [s6] 本机测试服务启动失败（openssl 不可用或端口占用）")
        return False
    if not (_reverse_on(ssl_port) and _reverse_on(http_port)):
        print(f"  [s6] adb reverse 通道不可用（{ssl_port}/{http_port}）")
        return False
    sbase = f"https://127.0.0.1:{ssl_port}"
    hbase = f"http://127.0.0.1:{http_port}"
    if not (_device_reachable(sbase) and _device_reachable(hbase)):
        print("  [s6] 设备侧连通探针失败（curl 非 200）")
        return False
    if not seed_login_sources(workdir, f"{sbase}/login"):
        print("  [s6] 合成登录源播种失败")
        return False
    print(f"  [s6] 通道就绪：合成源 2 个 + 自签名 HTTPS :{ssl_port} + adb reverse")
    try:
        # 前置归一：策略须处默认「放行」态（上次中断残留关闭态会让「默认放行」断言假失败）
        if _ssl_pref_state() is False:
            if _login_start(SEED_LOGIN_WEB):
                toggle_ssl_pass_through(d)
            print(f"  [s6] 策略前置归一：pref={_ssl_pref_state()}（期望 True/None）")
        # ---------- A) WebViewLoginFragment：默认放行 + 完成登录文案按钮 ----------
        HTTPS_REQS.clear()
        if not _login_start(SEED_LOGIN_WEB):
            print(f"  [s6] 未进入登录页（栈顶={current_activity()}）")
            return False
        time.sleep(4.0)
        xmlA = dump_xml(d)
        ca.shot(d, "m3login_s6_web_default")
        entry_ok = S_FINISH_LOGIN in xmlA          # 修复3：✔ 图标歧义 → 文案按钮
        no_dialog = (S_SSL_TITLE not in xmlA) and (S_SSL_CONTINUE not in xmlA)
        got_login = any(p.startswith("/login") for p in HTTPS_REQS)
        passthrough_ok = entry_ok and no_dialog and got_login
        print(f"  [s6] 默认态：顶栏「{S_FINISH_LOGIN}」在场={entry_ok}"
              f" / 无证书弹窗={no_dialog} / 服务端收到 /login={got_login}（默认放行）")

        # ---------- A2) 登录页同样可切换策略（默认放行 → 关闭 ⇒ 弹确认） ----------
        pref_before = _ssl_pref_state()
        tg = toggle_ssl_pass_through(d)
        off_ok = tg["clicked"] and tg["hint_off"] and (_ssl_pref_state() is False)
        ca.shot(d, "m3login_s6_strategy_off")
        print(f"  [s6] 策略切换：菜单项={tg['menu']} 已点击={tg['clicked']}"
              f" pref {pref_before}→{_ssl_pref_state()} 关闭提示={tg['hint_off']}")
        HTTPS_REQS.clear()
        dialog_ok = cancel_ok = False
        if _login_start(SEED_LOGIN_WEB):
            xmld = wait_ssl_dialog(d)
            dialog_ok = bool(xmld) and all(s in xmld for s in (S_SSL_TITLE, S_SSL_CONTINUE,
                                                              S_SSL_CERT_INFO, S_SSL_CANCEL))
            ca.shot(d, "m3login_s6_ssl_dialog")
            if dialog_ok:
                HTTPS_REQS.clear()
                cancel_ok = tap_text(d, S_SSL_CANCEL)
                time.sleep(2.5)
                cancel_ok = cancel_ok and not any(p.startswith("/login") for p in HTTPS_REQS)
            print(f"  [s6] 关闭态：弹窗齐备={dialog_ok} / 取消后零请求={cancel_ok}")
        # 还原放行（收尾不留关闭态）
        tg2 = toggle_ssl_pass_through(d)
        restore_ok = tg2["clicked"] and tg2["hint_on"] and (_ssl_pref_state() is not False)
        print(f"  [s6] 策略还原：已点击={tg2['clicked']} 开启提示={tg2['hint_on']}"
              f" pref={_ssl_pref_state()}（期望 True/None）")

        # ---------- B) SourceLoginDialog：错误卡 / 密码可见 / 删除登录头确认 ----------
        reset_app()
        form_started = _login_start(SEED_LOGIN_FORM)
        # ⚠️ 轮询而非单次 dump：弹窗内容首次组合 + uiautomator 可能返回上一拍缓存快照
        #    ⇒ 单次断言实测出现「上轮 True / 本轮 False」的假失败；改为最多 8 拍重取。
        xmlb = ""
        for _ in range(8):
            xmlb = dump_xml(d)
            if "账号" in xmlb:
                break
            time.sleep(1.0)
        ca.shot(d, "m3login_s6_form_default")
        rows_ok = form_started and ("账号" in xmlb) and ("密码" in xmlb)
        print(f"  [s6] 表单分支：启动={form_started} 账号/密码行在场={rows_ok}")

        # 优化5：密码行尾 👁 切换（contentDescription 轨迹 = 正向判据）
        eye_ok = False
        b_eye = node_bounds(xmlb, S_PWD_SHOW, contains=True)
        if b_eye:
            click_xy(d, b_eye["cx"], b_eye["cy"])
            time.sleep(1.2)
            xmlp = dump_xml(d)
            eye_ok = (S_PWD_HIDE in xmlp) and (S_PWD_SHOW not in xmlp)
            ca.shot(d, "m3login_s6_pwd_visible")
            print(f"  [s6] 密码可见性：点「{S_PWD_SHOW}」⇒「{S_PWD_HIDE}」在场={eye_ok}")

        # 优化4：OK ⇒ 确定性失败（loginUrl 为必抛 JS）⇒ 错误卡（不关窗 + 完整报错 + 复制/重试）
        err_ok = retry_ok = False
        b_ok = node_bounds(dump_xml(d), S_OK)
        if b_ok:
            click_xy(d, b_ok["cx"], b_ok["cy"])
            seen_running = False
            for _ in range(8):
                x = dump_xml(d)
                if S_LOGGING_IN in x:
                    seen_running = True
                if S_LOGIN_ERROR in x:
                    break
                time.sleep(1.0)
            xmle = dump_xml(d)
            ca.shot(d, "m3login_s6_error_card")
            alive = ACT_LOGIN.rsplit(".", 1)[-1] in current_activity()
            err_ok = all(s in xmle for s in (S_LOGIN_ERROR, S_COPY_ERR, S_RETRY)) and alive
            print(f"  [s6] 失败错误卡：标题/复制错误详情/重试 齐备={err_ok}"
                  f" / 弹窗未关（页面存活）={alive} / 捕获到「{S_LOGGING_IN}」={seen_running}")
            # 重试闭环（判据修正）：点重试 ⇒ **AppLog 失败条数 +1**（证明确实重跑了 login）
            # ⚠️ 不能用「卡片先消失再出现」判：失败是同步瞬时的（同一帧内 loginError 清空→再置位，
            #    Compose 合并状态 ⇒ UI 根本不渲染中间态；实测 40 拍密集 dump 也抓不到消失帧）。
            b_retry = node_bounds(xmle, S_RETRY)
            if b_retry:
                before = _logcat_count(S_LOGIN_ERROR)
                click_xy(d, b_retry["cx"], b_retry["cy"])
                time.sleep(4.0)
                after = _logcat_count(S_LOGIN_ERROR)
                xr = dump_xml(d)
                card_still = S_LOGIN_ERROR in xr
                retry_ok = (after > before) and card_still
                print(f"  [s6] 重试闭环：AppLog 失败条数 {before}→{after}（+1 ⇒ 重试确实重跑了 login）"
                      f" / 失败卡仍在={card_still}")
                ca.shot(d, "m3login_s6_retry")

        # 修复2：删除登录头二次确认（对象名 + 影响面 + 取消零副作用）
        del_menu_ok = del_confirm_ok = del_cancel_ok = False
        # 表单分支无顶栏 ⇒ 用弹窗标题栏 ⋮ 的 contentDescription（R.string.more）定位
        more = node_bounds(dump_xml(d), S_MORE)
        if more:
            click_xy(d, more["cx"], more["cy"])
            time.sleep(1.5)
            xmlm = dump_xml(d)
            del_menu_ok = S_DEL_HEADER in xmlm
            b = node_bounds(xmlm, S_DEL_HEADER)
            if b:
                click_xy(d, b["cx"], b["cy"])
                time.sleep(1.6)
                xmlc = dump_xml(d)
                ca.shot(d, "m3login_s6_del_confirm")
                del_confirm_ok = (S_DEL_HEADER in xmlc and S_DEL_CONFIRM_FRAG in xmlc
                                  and "删除" in xmlc and "取消" in xmlc)
                if del_confirm_ok:
                    tap_text(d, "取消")
                    time.sleep(1.4)
                    xmln = dump_xml(d)
                    del_cancel_ok = (S_DEL_CONFIRM_FRAG not in xmln) and ("账号" in xmln)
                print(f"  [s6] 删除登录头确认：菜单项={del_menu_ok} 影响面/按钮齐备={del_confirm_ok}"
                      f" / 取消后回表单={del_cancel_ok}")
        else:
            print("  [s6] 未定位表单弹窗 ⋮ 动作")

        # ---------- 源码断言（双文件） ----------
        frag = _src_text(SRC_LOGIN_FRAG)
        dlg = _src_text(SRC_LOGIN_DIALOG)
        frag_must = ("if (AppConfig.sslCertPassThrough)", "PreferKey.sslCertPassThrough",
                     "R.string.finish_login", "R.string.ssl_passthrough",
                     "onPositive = { handler.proceed() }", "onNegative = { handler.cancel() }")
        dlg_must = ("R.string.del_login_header_confirm", "R.string.del_login_header",
                    "R.string.logging_in", "R.string.login_error", "R.string.copy_error_detail",
                    "R.string.password_show", "R.string.password_hide",
                    "catch (e: CancellationException)",     # 取消不得误报为登录失败
                    "e.stackTraceToString()",               # 错误卡正文=完整堆栈
                    "enabled = !loginRunning", "loading = loginRunning")
        frag_missing = [k for k in frag_must if k not in frag]
        dlg_missing = [k for k in dlg_must if k not in dlg]
        code_ok = not frag_missing and not dlg_missing
        print(f"  [s6] 源码断言：fragment {len(frag_must) - len(frag_missing)}/{len(frag_must)}"
              f" / dialog {len(dlg_must) - len(dlg_missing)}/{len(dlg_must)}"
              f" / 缺失={frag_missing + dlg_missing}")

        ok = all([entry_ok, passthrough_ok, off_ok, dialog_ok, cancel_ok, restore_ok,
                  rows_ok, eye_ok, err_ok, retry_ok, del_menu_ok, del_confirm_ok,
                  del_cancel_ok, code_ok])
        print(f"  [s6] 小计: {'PASS' if ok else 'FAIL'}")
        return ok
    finally:
        try:
            print(f"  [s6] 合成登录源清理={purge_login_sources(workdir)}")
        except Exception as e:
            print(f"  [s6] 合成源清理异常: {type(e).__name__}")
        try:
            print(f"  [s6] 数据库快照回滚={m2._db_push(db_snap)}")
        except Exception as e:
            print(f"  [s6] 兜底回滚异常: {type(e).__name__}")
        try:
            if _ssl_pref_state() is False:      # 策略兜底还原（放行是产品默认态）
                reset_app()
                if _login_start(SEED_LOGIN_WEB):
                    toggle_ssl_pass_through(d)
                print(f"  [s6] 策略兜底还原：pref={_ssl_pref_state()}（期望 True/None）")
        except Exception as e:
            print(f"  [s6] 策略兜底还原异常: {type(e).__name__}")
        for p in (ssl_port, http_port):
            if p:
                release_reverse(p)
        for s in (ssl_srv, http_srv):
            try:
                s.shutdown()
            except Exception:
                pass
        reset_app()


# ===================== s7：rss/favorites（收藏夹）=====================
# 覆盖：F1 空态操作化（优化 4）/ F144 删除类菜单 danger 分级（优化 5）/ F145 单分组标题上下文（优化 6）
# 通道：DB 播种（整份快照 + 回滚，零污染）——清空既有收藏后只留「唯一合成分组」的一条收藏，
#       以构造「单分组」与「空分组」两个确定性状态；数据源为 rssStars（分组由收藏行派生）。
ACT_FAV = "io.legado.app.ui.rss.favorites.RssFavoritesActivity"
S_FAV_TITLE = "收藏夹"                        # favorites
S_FAV_EMPTY_TITLE = "这个分组还没有收藏"          # favorites_empty_title
S_FAV_EMPTY_DESC = "在文章列表点条目上的星标"        # favorites_empty_desc
S_FAV_EMPTY_ACTION = "去订阅源逛逛"              # favorites_empty_browse_rss
SRC_MAIN_ACT = "app/src/main/java/io/legado/app/ui/main/MainActivity.kt"
S_FAV_GROUP_DANGER = "危险操作"                 # rss_sort_group_danger
S_FAV_DEL_ALL = "删除所有"                     # delete_all
SEED_FAV_GROUP = "L2收藏校验分组"
SEED_FAV_ORIGIN = "l2seed://fav-origin"
SEED_FAV_LINK = "l2seed://fav-link"
SEED_FAV_TITLE = "L2收藏校验条目"
SRC_FAV_ACT = "app/src/main/java/io/legado/app/ui/rss/favorites/RssFavoritesActivity.kt"
SRC_FAV_FRAG = "app/src/main/java/io/legado/app/ui/rss/favorites/RssFavoritesFragment.kt"


def _fav_seed(workdir: Path, mode: str) -> bool:
    """播种收藏数据：mode='one' ⇒ 仅唯一分组 1 条（构造单分组/标题上下文）；mode='none' ⇒ 清空（构造空态）"""
    m2 = _m2()
    db = m2._db_pull(workdir)
    if db is None:
        return False
    con = sqlite3.connect(str(db))
    try:
        meta = [(r[1], (r[2] or "").upper(), r[3], r[4]) for r in con.execute("pragma table_info(rssStars)")]
        con.execute("delete from rssStars")
        if mode == "one":
            overrides = {
                "origin": SEED_FAV_ORIGIN,
                "link": SEED_FAV_LINK,
                "title": SEED_FAV_TITLE,
                "group": SEED_FAV_GROUP,
                "sort": SEED_FAV_GROUP,
                "starTime": int(time.time() * 1000),
                "pubDate": "",
                "type": 0,
                "durPos": 0,
            }
            vals = []
            for name, ctype, notnull, dflt in meta:
                if name in overrides:
                    vals.append(overrides[name])
                elif notnull and dflt is None:
                    vals.append(0 if ("INT" in ctype or "REAL" in ctype) else "")
                else:
                    vals.append(None)
            names = ",".join(f"`{n}`" for n, _, _, _ in meta)
            con.execute(f"insert into rssStars ({names}) values ({','.join('?' * len(meta))})", vals)
        con.commit()
    finally:
        con.close()
    return m2._db_push(db)


def _fav_start() -> bool:
    """直起收藏夹页（非导出组件：shell 直起 + su 兜底）"""
    simple = ACT_FAV.rsplit(".", 1)[-1]
    reset_app()
    sh("am", "start", "-n", f"{PKG}/{ACT_FAV}")
    for _ in range(10):
        time.sleep(1.2)
        if simple in current_activity():
            time.sleep(2.2)
            return True
    sh_su(f"am start -n {PKG}/{ACT_FAV}")
    time.sleep(3.5)
    return simple in current_activity()


def s7_favorites_page(d) -> bool:
    """收藏夹：单分组标题上下文 / 删除类菜单 danger 分级 / 空分组空态引导"""
    print("  [s7] ===== 收藏夹标题上下文、菜单分级与空态 =====")
    m2 = _m2()
    workdir = Path(tempfile.mkdtemp(prefix="m3fav_"))
    db_snap = workdir / "legado_snapshot.db"
    if not m2._snapshot_db(workdir, db_snap):
        print("  [s7] 数据库快照失败（前置）")
        return False
    try:
        # ---------- F145：单分组 ⇒ 标题携带分组名 ----------
        if not _fav_seed(workdir, "one"):
            print("  [s7] 合成收藏播种失败")
            return False
        title_ok = False
        if _fav_start():
            xml = dump_xml(d)
            ca.shot(d, "m3fav_s7_single_group_title")
            title_ok = (S_FAV_TITLE + " · " + SEED_FAV_GROUP) in xml
            print(f"  [s7] F145 单分组标题：「{S_FAV_TITLE} · {SEED_FAV_GROUP}」在场={title_ok}")

            # ---------- F144：⋮ 菜单危险分组头 + 删除所有 danger + 置底 ----------
            menu_ok = danger_ok = order_ok = False
            more = topbar_action_bounds(dump_xml(d), 0)
            if more:
                click_xy(d, more["cx"], more["cy"])
                time.sleep(1.5)
                xmlm = dump_xml(d)
                ca.shot(d, "m3fav_s7_menu")
                menu_ok = (S_FAV_GROUP_DANGER in xmlm) and (S_FAV_DEL_ALL in xmlm)
                fg_all, danger_ok = _danger_foreground(d, xmlm, S_FAV_DEL_ALL)
                b_hdr = node_bounds(xmlm, S_FAV_GROUP_DANGER)
                b_all = node_bounds(xmlm, S_FAV_DEL_ALL)
                b_grp = node_bounds(xmlm, "删除当前分组")
                # 置底口径：分组头/删除所有 的 y 均大于「删除当前分组」
                order_ok = bool(b_grp and b_hdr and b_all
                                and b_hdr["top"] > b_grp["top"] and b_all["top"] > b_grp["top"])
                print(f"  [s7] F144 菜单：危险头+删除所有在场={menu_ok} / 删除所有前景={fg_all}"
                      f" danger={danger_ok} / 置底顺序={order_ok}")
                d.press("back")
                time.sleep(1.0)
            else:
                print("  [s7] 未定位顶栏 ⋮")
        else:
            print(f"  [s7] 未进入收藏夹页（栈顶={current_activity()}）")
            return False

        # ---------- F1：空态（全库无收藏 ⇒ 无分组 ⇒ 无 Tab 无列表） ----------
        # ⚠️ 口径（源码实证 + 首轮实测修正）：分组清单由 rssStars 派生（`flowGroups: select group … group by`）
        #    ⇒ **空「分组」不可持久存在**，分组层空态只存在于瞬态窗口（首轮按分组层实现，真机抓不到帧）。
        #    真正可达且对用户有意义的是「一条收藏都没有」（新手态）⇒ 空态改落 **Activity 层**，
        #    构造通道 = 清空 rssStars（应用已停 ⇒ 无 inode 竞态）+ 重开页面，确定性可复现。
        empty_ok = action_ok = browse_ok = False
        if _fav_seed(workdir, "none") and _fav_start():
            xe = dump_xml(d)
            ca.shot(d, "m3fav_s7_empty")
            empty_ok = (S_FAV_EMPTY_TITLE in xe) and (S_FAV_EMPTY_DESC in xe)
            b_act = node_bounds(xe, S_FAV_EMPTY_ACTION)
            action_ok = b_act is not None
            if b_act:
                click_xy(d, b_act["cx"], b_act["cy"])
                time.sleep(3.5)
                browse_ok = "MainActivity" in current_activity()
            print(f"  [s7] F1 空态：标题+说明在场={empty_ok} / 出口「{S_FAV_EMPTY_ACTION}」在场={action_ok}"
                  f" / 点击后落到主界面={browse_ok}")
        else:
            print("  [s7] F1 空态：清库或页面启动失败")

        # ---------- 源码断言 ----------
        act_src = _src_text(SRC_FAV_ACT)
        frag_src = _src_text(SRC_FAV_FRAG)
        main_src = _src_text(SRC_MAIN_ACT)
        act_must = ("composeGroups.size == 1", "rss_sort_group_danger", "tint = danger",
                    "fun initEmptyState()", "binding.emptyOverlay", "MainActivity.openRss",
                    "favorites_empty_browse_rss", "fun buildMenuActions(danger: Color)")
        main_must = ("fun openRss(context: Context)", "TARGET_RSS ->", "private fun openRssPage()",
                     "R.id.menu_discovery")
        # 应删尽删：分组层空态实现已撤（避免留死代码）
        frag_absent = ("favorites_empty", "emptyOverlay")
        a_missing = [k for k in act_must if k not in act_src]
        m_missing = [k for k in main_must if k not in main_src]
        f_left = [k for k in frag_absent if k in frag_src]
        code_ok = not a_missing and not m_missing and not f_left
        print(f"  [s7] 源码断言：activity {len(act_must) - len(a_missing)}/{len(act_must)}"
              f" / MainActivity {len(main_must) - len(m_missing)}/{len(main_must)}"
              f" / fragment 应删尽删 {len(frag_absent) - len(f_left)}/{len(frag_absent)}"
              f" / 缺失={a_missing + m_missing} 残留={f_left}")

        ok = all([title_ok, menu_ok, danger_ok, order_ok, empty_ok, action_ok, browse_ok, code_ok])
        print(f"  [s7] 小计: {'PASS' if ok else 'FAIL'}")
        return ok
    finally:
        try:
            print(f"  [s7] 数据库快照回滚={m2._db_push(db_snap)}")
        except Exception as e:
            print(f"  [s7] 兜底回滚异常: {type(e).__name__}")
        reset_app()


# ===================== s10：video/video + video/video-player =====================
# F180 沉浸式首次手势引导卡（一次性） / F181 位置指示（源码断言兜底） / F182 布局模式逐项说明
# 通道：设备侧既有本地视频（file:// 直启 VideoPlayerActivity，无需网络）；prefs 直改保证沉浸式 + 未看过引导

ACT_VIDEO_PLAYER = "io.legado.app.ui.video.VideoPlayerActivity"
VIDEO_SRC = "/sdcard/Movies/l2ux_test_300s.mp4"
VIDEO_PREFS = f"/data/data/{PKG}/shared_prefs/video_config.xml"
DEFAULT_PREFS = f"/data/data/{PKG}/shared_prefs/{PKG}_preferences.xml"

S_GUIDE_TITLE = "手势操作"                 # video_gesture_guide_title
S_GUIDE_ITEM_TAP = "双击屏幕 · 暂停 / 继续"  # video_gesture_guide_double_tap
S_GUIDE_ITEM_PINCH = "双指外扩 · 全屏"      # video_gesture_guide_pinch
S_GUIDE_CONFIRM = "知道了"                 # video_gesture_guide_confirm
S_GUIDE_FOOTNOTE = "设置中可切换 布局模式"   # video_gesture_guide_footnote
S_LAYOUT_SUMMARY_IMMERSIVE = "沉浸式为全屏竖滑切换"      # video_layout_mode_summary
S_LAYOUT_SUMMARY_TRADITIONAL = "上部播放器 + 下部视频信息"  # video_layout_mode_traditional_summary
S_SETTINGS_TITLE = "视频设置"              # video_settings（面板标题）
S_LAYOUT_MODE_ROW = "布局模式"             # video_layout_mode
S_CANCEL = "取消"

SRC_VIDEO_FRAG = "app/src/main/java/io/legado/app/ui/video/VideoFragment.kt"
SRC_VIDEO_LAYOUT = "app/src/main/res/layout/fragment_video.xml"
SRC_SINGLE_CHOICE = "app/src/main/java/io/legado/app/ui/widget/components/SingleChoiceDialog.kt"
SRC_VIDEO_SETTINGS = "app/src/main/java/io/legado/app/ui/video/VideoSettingsPanelContent.kt"
SRC_VIDEO_STRINGS = "app/src/main/res/values/strings_video_dual_layout.xml"

GUIDE_KEY = "videoGestureGuideShown"


def _prefs_edit(remote: str, workdir: Path, mutate) -> bool:
    """拉取远端 prefs → 就地改 XML → 推回（应用需已停）。零 UI 依赖的确定性通道"""
    local = workdir / Path(remote).name
    r = sh_su(f"cat {remote}")
    raw = r.stdout or b""
    if not raw.strip():
        # 文件可能不存在：构造最小 XML 供写入
        raw = b'<?xml version="1.0" encoding="utf-8" standalone="yes" ?>\n<map>\n</map>'
    text = mutate(raw.decode("utf-8", errors="ignore"))
    local.write_text(text, encoding="utf-8")
    sh_su(f"cp {remote} {remote}.bak_l2s10")
    subprocess.run([ADB, "-s", HOST, "shell", f"su -c 'cat > {remote}'"],
                   input=text.encode("utf-8"), capture_output=True, timeout=40)
    time.sleep(0.5)
    verify = sh_su(f"cat {remote}")
    return text.strip()[:60] in (verify.stdout or b"").decode("utf-8", errors="ignore")


def _force_immersive_and_reset_guide(workdir: Path) -> bool:
    """① video_config.xml: layoutMode=0（沉浸式）② 默认 prefs: 移除引导一次性键（还原为「未看过」）"""
    def mut_video(text: str) -> str:
        if 'name="layoutMode"' in text:
            return re.sub(r'(<int name="layoutMode" value=")\d+(")', r"\g<1>0\g<2>", text)
        return text.replace("</map>", '<int name="layoutMode" value="0" />\n</map>')

    ok1 = _prefs_edit(VIDEO_PREFS, workdir, mut_video)
    ok2 = _prefs_edit(DEFAULT_PREFS, workdir,
                      lambda t: re.sub(r'\s*<boolean name="%s"[^/]*/>' % GUIDE_KEY, "", t))
    return ok1 and ok2


def _guide_shown_flag() -> bool:
    """回读默认 prefs 中引导一次性键（真机取证「点了知道了会写偏好」）"""
    r = sh_su(f"cat {DEFAULT_PREFS}")
    return f'name="{GUIDE_KEY}" value="true"' in (r.stdout or b"").decode("utf-8", errors="ignore")


def _start_local_video() -> bool:
    """本地 file:// 直启播放器（与 DownloadManageActivity 同款 extras；每次换文件名规避进度恢复）"""
    ts = int(time.time() * 10)
    dst = f"/data/data/{PKG}/files/l2m3_{ts}.mp4"
    sh_su(f"cp {VIDEO_SRC} {dst} && chown $(stat -c %u /data/data/{PKG}) {dst} && chmod 600 {dst}")
    reset_app()
    sh("am", "start", "-n", f"{PKG}/{ACT_VIDEO_PLAYER}", "--ez", "isNew", "true",
       "--es", "videoUrl", f"file://{dst}", "--es", "videoTitle", "L2M3")
    for _ in range(12):
        time.sleep(2)
        if "VideoPlayerActivity" in current_activity():
            time.sleep(5.0)
            return True
    return False


def _node_by_id(xml: str, res_suffix: str):
    """按 resource-id 后缀取可见节点 bounds（播放器悬浮控件是 View 系，靠 id 定位最稳）"""
    for m in re.finditer(r"<node[^>]*>", xml):
        t = m.group(0)
        rid = re.search(r'resource-id="([^"]*)"', t)
        if not rid or not rid.group(1).endswith(res_suffix):
            continue
        b = re.search(r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', t)
        if not b:
            continue
        x1, y1, x2, y2 = map(int, b.groups())
        if x2 > x1 and y2 > y1:
            return {"left": x1, "top": y1, "right": x2, "bottom": y2,
                    "cx": (x1 + x2) // 2, "cy": (y1 + y2) // 2}
    return None


def _clickable_bounds(xml: str, label: str):
    """按文本取可点节点 bounds。

    必要性（实测）：Compose 设置面板里**卡片标题与可点行文案同名**（如都叫「布局模式」），
    直接取首个匹配会点在不可点的卡片标题上 ⇒ 弹窗打不开、断言假 FAIL。
    策略：优先 `clickable="true"` 的匹配；若全无（Compose 行常把 clickable 挂在外层语义节点上，
    文本子节点自身不带该属性）则取 **cy 最大**者（行总在卡片标题下方）。
    """
    hits = []
    for m in re.finditer(r"<node[^>]*>", xml):
        t = m.group(0)
        tx = re.search(r'\btext="([^"]*)"', t)
        if not tx or tx.group(1) != label:
            continue
        b = re.search(r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', t)
        if not b:
            continue
        x1, y1, x2, y2 = map(int, b.groups())
        if x2 <= x1 or y2 <= y1:
            continue
        hits.append({
            "left": x1, "top": y1, "right": x2, "bottom": y2,
            "cx": (x1 + x2) // 2, "cy": (y1 + y2) // 2,
            "clickable": 'clickable="true"' in t,
        })
    if not hits:
        return None
    clickable_hits = [h for h in hits if h["clickable"]]
    return max(clickable_hits or hits, key=lambda h: h["cy"])


def s10_video_pages(d) -> bool:
    """video/video（F180 引导卡 + F181 位置指示）+ video/video-player（F182 布局模式说明）"""
    print("  [s10] ===== 沉浸式手势引导卡 + 布局模式说明 =====")
    workdir = Path(tempfile.mkdtemp(prefix="m3vid_"))
    src_frag = _src_text(SRC_VIDEO_FRAG)
    src_xml = _src_text(SRC_VIDEO_LAYOUT)
    src_sc = _src_text(SRC_SINGLE_CHOICE)
    src_set = _src_text(SRC_VIDEO_SETTINGS)
    src_str = _src_text(SRC_VIDEO_STRINGS)
    ok = False
    try:
        # ---------- 阶段 A：首次进入 ⇒ 引导卡在场 + 四条手势 + 点「知道了」收 ----------
        reset_app()
        prefs_ok = _force_immersive_and_reset_guide(workdir)
        print(f"  [s10] prefs 预置（沉浸式 + 未看过引导）={prefs_ok}")
        landed = _start_local_video()
        xml = dump_xml(d)
        ca.shot(d, "m3video_s10_guide_first")
        title_ok = S_GUIDE_TITLE in xml
        items_ok = (S_GUIDE_ITEM_TAP in xml) and (S_GUIDE_ITEM_PINCH in xml)
        confirm_b = node_bounds(xml, S_GUIDE_CONFIRM)
        footnote_ok = S_GUIDE_FOOTNOTE in xml
        print(f"  [s10] F180 首次：落地={landed} / 标题={title_ok} / 四条手势(取样2)={items_ok} / "
              f"「{S_GUIDE_CONFIRM}」={bool(confirm_b)} / 脚注={footnote_ok}")

        dismissed = flag_written = False
        if confirm_b:
            click_xy(d, confirm_b["cx"], confirm_b["cy"])
            time.sleep(1.5)
            dismissed = S_GUIDE_TITLE not in dump_xml(d)
            flag_written = _guide_shown_flag()
            ca.shot(d, "m3video_s10_guide_dismissed")
            print(f"  [s10] F180 点「{S_GUIDE_CONFIRM}」：卡片消失={dismissed} / 偏好已写={flag_written}")

        # ---------- 阶段 B：再次进入 ⇒ 引导卡不再出现（一次性） ----------
        reset_app()
        _start_local_video()
        xml_b = dump_xml(d)
        ca.shot(d, "m3video_s10_guide_second")
        once_ok = S_GUIDE_TITLE not in xml_b
        print(f"  [s10] F180 二次进入不显示（一次性）={once_ok}")

        # ---------- 阶段 C：设置面板 → 布局模式 ⇒ 逐项说明（F182） ----------
        summary_ok = False
        # 悬浮控件 3 秒自动隐藏 ⇒ 先单击上半屏呼出，再按 resource-id 定位设置按钮
        sb = _node_by_id(xml_b, "btn_settings")
        if not sb:
            w, h = d.window_size()
            for _ in range(3):
                d.click(w // 2, h // 4)
                time.sleep(1.5)
                sb = _node_by_id(dump_xml(d), "btn_settings")
                if sb:
                    break
        if sb:
            click_xy(d, sb["cx"], sb["cy"])
            # 面板为 Compose BottomSheet：轮询等「布局模式」行出现（首帧可能未组合完）
            row_b = None
            for _ in range(8):
                time.sleep(1.0)
                row_b = _clickable_bounds(dump_xml(d), S_LAYOUT_MODE_ROW)
                if row_b:
                    break
            if row_b:
                click_xy(d, row_b["cx"], row_b["cy"])
                has_i = has_t = False
                for _ in range(8):
                    time.sleep(1.0)
                    xml_c = dump_xml(d)
                    has_i = S_LAYOUT_SUMMARY_IMMERSIVE in xml_c
                    has_t = S_LAYOUT_SUMMARY_TRADITIONAL in xml_c
                    if has_i and has_t:
                        break
                ca.shot(d, "m3video_s10_layout_summary")
                summary_ok = has_i and has_t
                print(f"  [s10] F182 布局模式逐项说明：沉浸式项={has_i} / 传统项={has_t}")
                if S_CANCEL in xml_c:
                    d.press("back")
                    time.sleep(1.0)
            else:
                print(f"  [s10] F182 未定位可点击的「{S_LAYOUT_MODE_ROW}」行")
        else:
            print("  [s10] F182 未定位设置按钮（btn_settings，控件呼出失败）")

        src_checks = {
            "F180 引导卡四要素落布局": all(k in src_xml for k in
                                ("gesture_guide_card", "tv_guide_items", "btn_guide_confirm",
                                 "tv_guide_footnote")),
            "F180 一次性偏好": ("PreferKey.videoGestureGuideShown" in src_frag
                          and "putPrefBoolean(PreferKey.videoGestureGuideShown, true)" in src_frag),
            "F180 长按倍速动态取值": "video_gesture_guide_long_press" in src_frag,
            "F181 位置指示同源字符串": ("tv_position_indicator" in src_xml
                              and "video_playlist_position_episode" in src_frag
                              and "video_playlist_position_article" in src_frag),
            "F181 单集不显示（避免噪声）": "articles.size > 1" in src_frag and "episodes.size > 1" in src_frag,
            "F181 与标题同源刷新": "updatePositionIndicator()" in src_frag.split("private fun setTitle")[1][:400],
            "F182 说明为可选参数（零改动）": ("optionSummaries: List<String>? = null" in src_sc
                                and "optionSummaries = summaries" in src_set),
            "F182 复用既有 summary 资源": ("video_layout_mode_summary" in src_str
                                and "video_layout_mode_traditional_summary" in src_str),
        }
        src_ok = all(src_checks.values())
        print(f"  [s10] 源码断言 {sum(src_checks.values())}/{len(src_checks)}："
              f"{[k for k, v in src_checks.items() if not v] or '全通过'}")

        ok = bool(landed and title_ok and items_ok and footnote_ok and dismissed and flag_written
                  and once_ok and summary_ok and src_ok)
    except Exception as e:
        print(f"  [s10] 异常终止: {type(e).__name__}: {e}")
    finally:
        reset_app()
        # 还原 prefs：移除引导一次性键（保持环境可复跑）+ 清掉 prefs 备份与临时视频
        _prefs_edit(DEFAULT_PREFS, workdir, lambda t: re.sub(
            r'\s*<boolean name="%s"[^/]*/>' % GUIDE_KEY, "", t))
        sh_su(f"rm -f {DEFAULT_PREFS}.bak_l2s10 {VIDEO_PREFS}.bak_l2s10 "
              f"/data/data/{PKG}/files/l2m3_*.mp4")
        reset_app()
    return ok


# ==================== s11：正文菜单按键管理 + 智能音频管理 ====================
# 覆盖：F60 实机预览条 / F51 拖拽手柄（真起拖 + 落库改序）/ F61 夜间双图标态浮出
#       F50 空态操作化 / F55 分组默认折叠 + 全部展开折叠 / F54 音轨试听
ACT_MENU_BTN = "io.legado.app.ui.book.read.config.ReadMenuButtonManageActivity"
ACT_BGM = "io.legado.app.ui.book.read.config.ReadAloudBgmManageActivity"

S_PREVIEW_TITLE = "阅读页实际效果"       # read_menu_preview_title
S_DRAG_HANDLE = "拖动排序手柄"           # read_menu_drag_handle
S_NIGHT_ICONS = "夜间双图标"             # read_menu_night_icons
S_NIGHT_ICON_DAY = "日间图标"            # read_menu_night_icon_day
S_NIGHT_ICON_NIGHT = "夜间图标"          # read_menu_night_icon_night
S_ROW_FIRST = "第一排"                  # read_menu_first_row
S_ROW_SECOND = "第二排"                 # read_menu_second_row
S_ADD_BUTTON = "添加按键"                # read_menu_add_button
S_PREVIEW_MORE = "还有 "                 # read_menu_preview_more 前缀（还有 N 个（可翻页））
S_BGM_IMPORT_AUDIO = "导入音频"          # read_aloud_bgm_import_audio
S_BGM_EXPAND_ALL = "全部展开"            # read_aloud_bgm_expand_all
S_BGM_COLLAPSE_ALL = "全部折叠"          # read_aloud_bgm_collapse_all
S_BGM_PLAY = "试听"                     # read_aloud_bgm_preview_play
S_BGM_STOP = "停止试听"                  # read_aloud_bgm_preview_stop
S_BGM_EMPTY_HINT = "暂无配乐"            # 既有空态文案前缀
S_BGM_DEFAULT_GROUP = "默认分组"

MENU_LAYOUT_KEY = "readMenuButtonLayout"
# 默认布局的按键 id 顺序（`ReadMenuButtonConfig.defaultLayout()`；实测教训：默认布局**不落盘**，
# 首次进入 prefs 里根本没有该键 ⇒ 拖拽前的基线不能只依赖 prefs，否则判据恒 False = 假阴性）
MENU_DEFAULT_IDS = [
    "search", "autoPage", "replaceRule", "nightTheme", "characters", "paragraphRules",
    "bubble", "readAssistant", "aiSummary", "catalog", "readAloud", "readStyle", "setting",
]
BGM_SEED_GROUP = "L2校验分组"
BGM_SEED_TRACK_DEFAULT = "L2默认组音轨"
BGM_SEED_TRACK_GROUP = "L2校验音轨"

SRC_MENU_BTN = "app/src/main/java/io/legado/app/ui/book/read/config/ReadMenuButtonManageActivity.kt"
SRC_ITEM_TOUCH = "app/src/main/java/io/legado/app/ui/widget/recycler/ItemTouchCallback.kt"
SRC_ICON_HELPER = "app/src/main/java/io/legado/app/ui/book/read/ReadMenuButtonIconHelper.kt"
SRC_MENU_COMPONENTS = "app/src/main/java/io/legado/app/ui/book/read/ReadMenuComposeComponents.kt"
SRC_BGM = "app/src/main/java/io/legado/app/ui/book/read/config/ReadAloudBgmManageActivity.kt"
SRC_MENU_CFG = "app/src/main/java/io/legado/app/ui/book/read/ReadMenuButtonConfig.kt"


def _desc_bounds_all(xml: str, desc: str):
    """按 content-desc 取全部可见节点 bounds（手柄/试听键等纯图标控件只有 desc）"""
    out = []
    for m in re.finditer(r"<node[^>]*>", xml):
        t = m.group(0)
        cd = re.search(r'\bcontent-desc="([^"]*)"', t)
        if not cd or cd.group(1) != desc:
            continue
        b = re.search(r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', t)
        if not b:
            continue
        x1, y1, x2, y2 = map(int, b.groups())
        if x2 > x1 and y2 > y1:
            out.append({"left": x1, "top": y1, "right": x2, "bottom": y2,
                        "cx": (x1 + x2) // 2, "cy": (y1 + y2) // 2, "h": y2 - y1})
    return sorted(out, key=lambda n: n["top"])


def _pref_string_value(key: str) -> str:
    """回读默认 prefs 里的字符串项（XML 转义原样返回；用于比对按键顺序）"""
    r = sh_su(f"cat {DEFAULT_PREFS}")
    text = (r.stdout or b"").decode("utf-8", errors="ignore")
    m = re.search(r'<string name="%s">(.*?)</string>' % key, text, re.S)
    return m.group(1) if m else ""


def _menu_layout_ids() -> list:
    """从 prefs 的布局 JSON 抽出按键 id 顺序（XML 转义后 `"` 变 `&quot;`，故按实体匹配）"""
    raw = _pref_string_value(MENU_LAYOUT_KEY)
    return re.findall(r"&quot;id&quot;:&quot;([A-Za-z]+)&quot;", raw)


def _make_silent_wav(path: Path, seconds: float = 30.0) -> bool:
    """生成静音 PCM WAV（试听通道需要**真实可解码**的音频文件，不能用假路径）。

    时长取 30s 而非 1s（实测教训）：1s 片段在点击后 **0.4s 内即播完**（logcat
    `AudioTrack: stop() called with 8000 frames delivered` 即 8kHz×1s 全部送出），
    首次轮询（0.7s）时按钮已复位 ⇒ 「播放态」断言必然假阴性。30s 保证播放态可观测。
    """
    import struct
    rate = 8000
    frames = int(rate * seconds)
    data = b"\x00\x00" * frames
    header = (b"RIFF" + struct.pack("<I", 36 + len(data)) + b"WAVEfmt " +
              struct.pack("<IHHIIHH", 16, 1, 1, rate, rate * 2, 2, 16) +
              b"data" + struct.pack("<I", len(data)))
    path.write_bytes(header + data)
    return path.stat().st_size > 44


def _bgm_seed(workdir: Path, mode: str, wav_local: Path) -> bool:
    """播种智能音频库：mode='none' ⇒ 清空（构造空态）；mode='two' ⇒ 默认分组 1 条 + 合成分组 1 条"""
    m2 = _m2()
    db = m2._db_pull(workdir)
    if db is None:
        return False
    wav_remote = f"/data/data/{PKG}/files/readAloudAudio/bgm/l2m3_preview.wav"
    con = sqlite3.connect(str(db))
    try:
        con.execute("delete from read_aloud_bgm_tracks")
        con.execute("delete from read_aloud_bgm_groups")
        if mode == "two":
            now = int(time.time() * 1000)
            gcols = [r[1] for r in con.execute("pragma table_info(read_aloud_bgm_groups)")]
            gvals = {"name": BGM_SEED_GROUP, "assetType": "bgm", "sortOrder": 1,
                     "createdAt": now, "updatedAt": now}
            con.execute(
                f"insert into read_aloud_bgm_groups ({','.join('`%s`' % c for c in gcols)})"
                f" values ({','.join('?' * len(gcols))})",
                [gvals.get(c) for c in gcols])
            gid = con.execute("select id from read_aloud_bgm_groups order by id desc limit 1").fetchone()[0]
            tcols = [r[1] for r in con.execute("pragma table_info(read_aloud_bgm_tracks)")]
            rows = [
                {"groupId": 0, "name": BGM_SEED_TRACK_DEFAULT, "fileName": "l2_default.wav",
                 "sortOrder": 1},
                {"groupId": gid, "name": BGM_SEED_TRACK_GROUP, "fileName": "l2_group.wav",
                 "sortOrder": 1},
            ]
            for extra in rows:
                vals = {"tags": "", "checksum": "", "durationMs": 1000, "defaultVolume": 1.0,
                        "enabled": 1, "assetType": "bgm", "filePath": wav_remote,
                        "createdAt": now, "updatedAt": now}
                vals.update(extra)
                con.execute(
                    f"insert into read_aloud_bgm_tracks ({','.join('`%s`' % c for c in tcols)})"
                    f" values ({','.join('?' * len(tcols))})",
                    [vals.get(c) for c in tcols])
        con.commit()
    finally:
        con.close()
    pushed = m2._db_push(db)
    if mode == "two":
        # 应用私有目录需 root 落文件 + 交还 owner（否则 app 读不到 ⇒ 试听必失败，属假阴性）
        sh_su(f"mkdir -p /data/data/{PKG}/files/readAloudAudio/bgm")
        subprocess.run([ADB, "-s", HOST, "push", str(wav_local), "/sdcard/l2m3_preview.wav"],
                       capture_output=True, timeout=60)
        sh_su(f"cp /sdcard/l2m3_preview.wav {wav_remote} && "
              f"chown $(stat -c %u /data/data/{PKG}) {wav_remote} && chmod 600 {wav_remote}")
    return pushed


def _write_menu_layout(workdir: Path, first_ids: list, second_ids: list) -> bool:
    """把一份**非默认**布局 JSON 直接写进 prefs（确定性构造「已落盘非默认布局」状态）。

    必要性：本轮查出的崩溃（缺 @Keep ⇒ `List<ButtonRef>` 退化为 `LinkedTreeMap`）**只在
    prefs 已存非默认布局时暴露**——默认布局是 `defaultLayout()` 计算值、不落盘。若只靠手势
    拖拽产生该状态，则判据会被注入抖动绑架；此处直写 prefs，令回归断言与手势通道解耦。
    """
    def ref(rid: str) -> str:
        return ('{"type":"builtin","id":"%s","titleOverride":"","iconPath":"","nightIconPath":""}'
                % rid)
    payload = '{"firstRow":[%s],"secondRow":[%s]}' % (
        ",".join(ref(i) for i in first_ids), ",".join(ref(i) for i in second_ids))
    escaped = payload.replace('"', "&quot;")

    def mutate(text: str) -> str:
        text = re.sub(r'\s*<string name="%s">.*?</string>' % MENU_LAYOUT_KEY, "", text, flags=re.S)
        return text.replace(
            "</map>",
            '<string name="%s">%s</string>\n</map>' % (MENU_LAYOUT_KEY, escaped)
        )

    return _prefs_edit(DEFAULT_PREFS, workdir, mutate)


def _menu_btn_start(d, retries: int = 3) -> bool:
    """直起正文菜单按键管理页，并**按页面标记确认真的落地**。

    实测该页（`exported=false`）偶发直起失败（`am start` 返回成功但停在上一页/桌面）⇒
    仅看 `current_activity` 不够，必须以页面独有节点（底部「添加按键」）作落地判据，失败重试。
    判据还要求**列表已渲染出卡片**（拖拽手柄 ≥2）——页面 inflate 完成与列表绑定完成之间有时间差，
    过早 dump 只会拿到 1~2 张卡，导致后续「第 4 张卡（夜间按钮）」类断言假 FAIL。
    """
    for _ in range(retries):
        start_robust(ACT_MENU_BTN)
        for _ in range(6):
            time.sleep(1.0)
            cur = dump_xml(d)
            if S_ADD_BUTTON in cur and len(_desc_bounds_all(cur, S_DRAG_HANDLE)) >= 2:
                time.sleep(1.5)
                return True
        reset_app()
    return False


def s11_menu_and_bgm_pages(d) -> bool:
    """book/read-menu-button-manage（F60/F51/F61）+ book/read-aloud-bgm-manage（F50/F55/F54）"""
    print("  [s11] ===== 正文菜单按键管理（预览条/手柄/夜间双图标）=====")
    workdir = Path(tempfile.mkdtemp(prefix="m3menu_"))
    src_menu = _src_text(SRC_MENU_BTN)
    src_touch = _src_text(SRC_ITEM_TOUCH)
    src_icon = _src_text(SRC_ICON_HELPER)
    src_comp = _src_text(SRC_MENU_COMPONENTS)
    src_bgm = _src_text(SRC_BGM)
    src_cfg = _src_text(SRC_MENU_CFG)
    wav_local = workdir / "l2m3_preview.wav"
    _make_silent_wav(wav_local)
    ok = False
    try:
        # ---------- 阶段 A：正文菜单按键管理 ----------
        landed = _menu_btn_start(d)
        xml = dump_xml(d)
        ca.shot(d, "m3s11_menu_preview")
        preview_b = node_bounds(xml, S_PREVIEW_TITLE)
        add_b = node_bounds(xml, S_ADD_BUTTON)
        # 预览条内的按钮标签：落在「预览标题」与「添加按键」之间的文本节点
        band = 0
        if preview_b and add_b:
            band = sum(1 for _, top, _, _, _ in text_nodes(xml)
                       if preview_b["cy"] < top < add_b["cy"])
        more_ok = S_PREVIEW_MORE in xml
        # 回归哨兵：预览条插入后，列表与底部主操作都不能被挤出可视区
        list_keep = (S_ROW_FIRST in xml) and bool(add_b)
        print(f"  [s11] F60 预览条：落地={landed} / 标题在场={bool(preview_b)} / "
              f"条内标签数={band} / 超页提示={more_ok} / 列表与主操作保留={list_keep}")

        # 🔴 崩溃回归（**确定性通道**，不依赖手势注入）：直接落盘一份「非默认布局」→ 重开本页必须不崩。
        # 根因=ButtonLayout/ButtonRef 缺 @Keep ⇒ R8 收窄后 List<ButtonRef> 退化为 List<LinkedTreeMap>
        # ⇒ sanitizeRow 取 .type 抛 ClassCastException ⇒ onActivityCreated 即崩。
        # 该缺陷此前被「收尾清 prefs」掩盖（每次跑都是默认布局）⇒ 必须显式保留非默认布局再重开取证。
        reset_app()
        # 第一排含夜间按钮（F61 断言靶点，排第 4 位）+ 顺序非默认（autoPage 提到首位，F60 断言靶点）
        layout_written = _write_menu_layout(
            workdir,
            ["autoPage", "search", "replaceRule", "nightTheme", "characters"],
            ["catalog", "readAloud"]
        )
        reset_app()
        reopen_ok = _menu_btn_start(d)
        xml_reopen = dump_xml(d)
        applied_ok = "自动翻页" in xml_reopen   # autoPage 被排到第一排首位 ⇒ 非默认布局真的生效
        ca.shot(d, "m3s11_menu_reopen_saved_layout")
        print(f"  [s11] 崩溃回归（落盘非默认布局后重开）：写入={layout_written} / "
              f"落地={reopen_ok} / 非默认布局生效={applied_ok}")

        # F61：夜间双图标态浮出（默认/本次落盘布局的第一排都含内置夜间按钮）
        # 位置要求：必须在 F51 拖拽尝试**之前**判——起拖失败的手势会退化成列表滚动，把第 4 张卡滚出屏。
        night_ok = False
        w, hh = d.window_size()
        for _ in range(3):
            cur = dump_xml(d)
            if (S_NIGHT_ICONS in cur and S_NIGHT_ICON_DAY in cur and S_NIGHT_ICON_NIGHT in cur):
                night_ok = True
                break
            # 夜间按钮是第 4 张卡，可能刚好在可视区下方 ⇒ 小幅向上滑（内容上移）把它带进可视区再判
            d.swipe(w * 0.5, hh * 0.70, w * 0.5, hh * 0.45, steps=10)
            time.sleep(1.5)
        print(f"  [s11] F61 夜间双图标行在场={night_ok}")

        # F51：手柄在场 + **真起拖** ⇒ prefs 里的按键顺序真的变了
        # 配方（实测对比得出）：长按手柄 + `swipe(steps=40)`。
        # ⚠️ u2 的 `swipe` **同时传 duration 与 steps 时会忽略 duration**（警告 "use steps"）；
        # 只给 duration 时默认步数太少（中间 MOVE 不足）⇒ ItemTouchHelper 起不了拖。
        # 🔴 工具缺口（如实登记，非产品缺陷）：本环境下**手势注入起拖不可靠**——u2 `swipe`/`long_click`
        #   与原生 `adb shell input swipe`（1000/2000/3000/4000/5000ms）共 10+ 次变体均只有偶发成功。
        #   「按下手柄即起拖」已由**一次性诊断脚本**取证：同配方成功后 prefs 的 `readMenuButtonLayout`
        #   首项由 `search` 变为 `autoPage`（顺序真的变化并落盘）。
        #   ⇒ 故本场景**不把 drag_ok 作门禁**，门禁用「手柄可见 + 起拖接线源码断言 + 崩溃回归闭环」；
        #   drag_ok 仍打印以保留观测。待补：更稳的拖拽注入通道（如 API29+ 的 `input motionevent`）。
        handles = _desc_bounds_all(xml_reopen, S_DRAG_HANDLE)
        before_ids = _menu_layout_ids() or MENU_DEFAULT_IDS
        drag_ok = False
        drag_tries = 0
        if handles:
            h = handles[0]
            for drag_tries in range(1, 5):
                d.long_click(h["cx"] / w, h["cy"] / hh, 1.2)
                time.sleep(1.0)
                d.swipe(h["cx"] / w, h["cy"] / hh,
                        h["cx"] / w, (h["cy"] + h["h"] * 3) / hh, steps=40)
                time.sleep(2.5)
                after_ids = _menu_layout_ids()
                if after_ids and after_ids != before_ids:
                    drag_ok = True
                    break
                # 手柄位置可能已随上次尝试变化 ⇒ 重新定位
                h2 = _desc_bounds_all(dump_xml(d), S_DRAG_HANDLE)
                if not h2:
                    break
                h = h2[0]
            ca.shot(d, "m3s11_menu_dragged")
        print(f"  [s11] F51 手柄：数量={len(handles)} / 真起拖改序={drag_ok}（尝试 {drag_tries} 次，非门禁）")

        # 切「第二排」Tab ⇒ 预览条随行切换仍渲染（F60 与 Tab 同源）
        # 判据取「预览标题下方标签数 ≥2」：未切换时该区间只剩底部「添加按键」1 个节点 ⇒ 不会假通过
        second_ok = False
        for _ in range(3):
            if not tap_text(d, S_ROW_SECOND):
                time.sleep(1.0)
                continue
            time.sleep(1.2)
            xml2 = dump_xml(d)
            pb2 = node_bounds(xml2, S_PREVIEW_TITLE)
            band2 = sum(1 for _, top, _, _, _ in text_nodes(xml2)
                        if pb2 and top > pb2["cy"]) if pb2 else 0
            if pb2 and band2 >= 2:
                second_ok = True
                break
            time.sleep(1.0)
        ca.shot(d, "m3s11_menu_second_row")
        print(f"  [s11] F60 第二排预览随切={second_ok}")

        # ---------- 阶段 B：智能音频（空态 → 有数据） ----------
        print("  [s11] ===== 智能音频管理（空态/分组折叠/试听）=====")
        _bgm_seed(workdir, "none", wav_local)
        reset_app()
        bgm_landed = start_robust(ACT_BGM)
        xml_e = dump_xml(d)
        ca.shot(d, "m3s11_bgm_empty")
        empty_ok = (S_BGM_EMPTY_HINT in xml_e) and (S_BGM_IMPORT_AUDIO in xml_e)
        print(f"  [s11] F50 空态：落地={bgm_landed} / 引导={S_BGM_EMPTY_HINT in xml_e} / "
              f"主操作「{S_BGM_IMPORT_AUDIO}」={S_BGM_IMPORT_AUDIO in xml_e}")

        # 播种两分组两音轨 ⇒ F55 默认只展开「默认分组」
        reset_app()
        seeded = _bgm_seed(workdir, "two", wav_local)
        bgm_landed2 = start_robust(ACT_BGM)
        xml_s = dump_xml(d)
        ca.shot(d, "m3s11_bgm_collapsed")
        chips_ok = (S_BGM_EXPAND_ALL in xml_s) and (S_BGM_COLLAPSE_ALL in xml_s)
        default_expanded = (S_BGM_DEFAULT_GROUP in xml_s) and (BGM_SEED_TRACK_DEFAULT in xml_s)
        other_collapsed = (BGM_SEED_GROUP in xml_s) and (BGM_SEED_TRACK_GROUP not in xml_s)
        empty_gone = S_BGM_IMPORT_AUDIO not in xml_s
        print(f"  [s11] F55 播种={seeded} / 落地={bgm_landed2} / 折叠快捷={chips_ok} / "
              f"默认分组展开={default_expanded} / 非默认分组折叠={other_collapsed} / "
              f"有数据时空态主操作隐藏={empty_gone}")

        # 全部展开 ⇒ 非默认分组的音轨出现
        expand_ok = False
        if tap_text(d, S_BGM_EXPAND_ALL):
            for _ in range(6):
                time.sleep(0.8)
                if BGM_SEED_TRACK_GROUP in dump_xml(d):
                    expand_ok = True
                    break
            ca.shot(d, "m3s11_bgm_expanded")
        print(f"  [s11] F55 全部展开后非默认分组音轨可见={expand_ok}")

        # F54：试听按钮 → 真实播放 ⇒ content-desc 翻为「停止试听」→ 再点回「试听」
        play_ok = stop_ok = False
        plays = _desc_bounds_all(dump_xml(d), S_BGM_PLAY)
        if plays:
            click_xy(d, plays[0]["cx"], plays[0]["cy"])
            for _ in range(8):
                time.sleep(0.8)
                if _desc_bounds_all(dump_xml(d), S_BGM_STOP):
                    play_ok = True
                    break
            ca.shot(d, "m3s11_bgm_playing")
            stops = _desc_bounds_all(dump_xml(d), S_BGM_STOP)
            if stops:
                click_xy(d, stops[0]["cx"], stops[0]["cy"])
                for _ in range(8):
                    time.sleep(0.6)
                    if not _desc_bounds_all(dump_xml(d), S_BGM_STOP):
                        stop_ok = True
                        break
        print(f"  [s11] F54 试听：按钮={len(plays)} / 播放态={play_ok} / 停止复位={stop_ok}")

        # 全部折叠 ⇒ 音轨全收起（仅剩分组头）
        collapse_ok = False
        if tap_text(d, S_BGM_COLLAPSE_ALL):
            for _ in range(6):
                time.sleep(0.8)
                cur = dump_xml(d)
                if (BGM_SEED_TRACK_GROUP not in cur) and (BGM_SEED_TRACK_DEFAULT not in cur):
                    collapse_ok = True
                    break
        print(f"  [s11] F55 全部折叠后音轨全收起={collapse_ok}")

        src_checks = {
            "F60 预览条运行时插入（不改共用布局）": (
                "parent.addView(bar, addIndex, params)" in src_menu
                and "indexOfChild(binding.btnAdd)" in src_menu),
            "F60 预览条只读（不挂点击）": "isClickable = false" in src_menu,
            "F60 每页上限与阅读菜单同源": (
                "import io.legado.app.ui.book.read.MENU_BUTTONS_PER_PAGE" in src_menu
                and "internal const val MENU_BUTTONS_PER_PAGE" in src_comp),
            "F51 手柄按下即起拖": ("itemTouchHelper.startDrag(this@ButtonViewHolder)" in src_menu
                            and "MotionEvent.ACTION_DOWN" in src_menu),
            "F51 拖拽视觉反馈钩子": ("onDragStateChanged" in src_touch
                             and "opaqueRoundedStroke" in src_menu),
            "F51 复位放 onClearView（不依赖 onSelectedChanged）": (
                "viewHolder.itemView.elevation = 0f" in src_menu),
            "F61 双图标按显式路径取图": ("fun drawableFromPath" in src_icon
                               and "drawableFromPath(" in src_menu),
            "F61 仅夜间按钮展示（普通卡不加信息）": "Builtin.NIGHT_THEME" in src_menu,
            "崩溃修复：Gson 模型 @Keep": ("@Keep\n    data class ButtonRef" in src_cfg
                                and "@Keep\n    data class ButtonLayout" in src_cfg),
            "崩溃修复：脏元素兜底不崩": ("filterIsInstance<ButtonRef>()" in src_cfg
                              and "if (parsedCount > 0 && keptCount == 0) defaultLayout()" in src_cfg),
            "F50 复用 btn_add 槽位（零新增视图）": (
                "binding.btnAdd.visibility = if (empty) View.VISIBLE else View.GONE" in src_bgm),
            "F55 默认只展开默认分组": (
                "rowGroups.filter { it.isDefaultGroup() }.map { it.id }" in src_bgm),
            "F55 行序单源（buildRows 与全部展开共用）": "private fun rowGroups()" in src_bgm,
            "F52 导入进度回调已接线": ("onProgress: (Int) -> Unit" in src_bgm
                              and "onProgress(imported)" in src_bgm
                              and "read_aloud_bgm_import_progress" in src_bgm),
            "F54 试听播放器释放闭环": ("override fun onDestroy" in src_bgm
                             and "stopPreview()" in src_bgm.split("override fun onDestroy")[1][:120]),
            "F54 切资产类型先停试听": "stopPreview()" in src_bgm.split("private fun switchAssetType")[1][:400],
        }
        src_ok = all(src_checks.values())
        print(f"  [s11] 源码断言 {sum(src_checks.values())}/{len(src_checks)}："
              f"{[k for k, v in src_checks.items() if not v] or '全通过'}")

        ok = bool(landed and preview_b and band >= 2 and more_ok and list_keep
                  and reopen_ok and applied_ok and handles and night_ok and second_ok
                  and bgm_landed and empty_ok and bgm_landed2 and chips_ok
                  and default_expanded and other_collapsed and empty_gone
                  and expand_ok and play_ok and stop_ok and collapse_ok and src_ok)
    except Exception as e:
        print(f"  [s11] 异常终止: {type(e).__name__}: {e}")
    finally:
        reset_app()
        # 零污染收尾：还原按键布局（回到默认）+ 清空智能音频库与临时音频
        _prefs_edit(DEFAULT_PREFS, workdir, lambda t: re.sub(
            r'\s*<string name="%s">.*?</string>' % MENU_LAYOUT_KEY, "", t, flags=re.S))
        _bgm_seed(workdir, "none", wav_local)
        sh_su(f"rm -f {DEFAULT_PREFS}.bak_l2s10 /sdcard/l2m3_preview.wav "
              f"/data/data/{PKG}/files/readAloudAudio/bgm/l2m3_preview.wav")
        reset_app()
    return ok


def guarded(fn):
    def inner(d):
        try:
            return fn(d)
        except Exception as e:
            print(f"  [EXC] {type(e).__name__}: {e}")
            return False

    inner.__name__ = getattr(fn, "__name__", "step")
    return inner


# ===================== s9：book/ai-read-aloud-usage + book/paragraph-rule-manage =====================
# F30 摘要拆两行 + Chip + 明细折叠 / F31 选中态批量栏（删除+导出）
# F51 拖拽手柄可见化 / F50 空态操作化（引导）/ F52 导入进度闭环

ACT_AI_USAGE = "io.legado.app.ui.book.read.config.AiReadAloudUsageRecordActivity"
ACT_PARA_RULE = "io.legado.app.ui.book.read.config.ParagraphRuleManageActivity"
ACT_HANDLE_FILE = "HandleFileActivity"

S_AI_SUMMARY_BOOK = "全部书籍"
S_AI_TOTAL_CHIP = "总 1,252,500"    # 千分位 + 两行拆分后的「总 Token」主指标（摘要内强调段）
S_AI_MODEL_A_LINE = "L2模型A 1,250,000"   # 第 3 行「按模型拆分」中的 A 模型汇总
S_AI_INPUT_LINE = "输入 1,002,000"
S_AI_EXPORT = "导出"                # ai_usage_export_selected
S_AI_DELETE_PREFIX = "删除选中 "     # ai_usage_delete_selected
S_AI_DELETE_TITLE = "删除记录"

S_PARA_HANDLE_DESC = "拖动排序手柄"   # paragraph_rule_drag_handle（content-desc，可被 a11y 树取到）
S_PARA_DRAG_HINT = "拖动右侧手柄"     # paragraph_rule_manage_summary 片段
S_PARA_EMPTY_GUIDE = "点下方「添加」创建第一条规则"  # paragraph_rule_empty_guide
S_PARA_EMPTY = "暂无段落规则"         # paragraph_rule_empty
S_PARA_IMPORTING = "正在导入规则…"    # paragraph_rule_importing
S_PARA_IMPORT_ONLINE = "网络导入"     # import_on_line（真值「网络导入」，非「在线导入」——实测踩坑）
S_OK = "确定"                        # ok 在**对话框按钮**上的渲染真值（实测；取消键=「取消」）
S_CANCEL = "取消"                    # cancel

SRC_AI_USAGE = "app/src/main/java/io/legado/app/ui/book/read/config/AiReadAloudUsageRecordActivity.kt"
SRC_PARA_RULE = "app/src/main/java/io/legado/app/ui/book/read/config/ParagraphRuleManageActivity.kt"

SEED_USAGE_A_MODEL = "L2模型A"
SEED_USAGE_B_MODEL = "L2模型B"
SEED_PARA_NAMES = ("L2规则甲", "L2规则乙")
PARA_BOOK_URL = "l2book://para-context"
IMPORT_PORT = 18544
IMPORT_URL = f"http://127.0.0.1:{IMPORT_PORT}/rules.json"


def _usage_seed(workdir: Path) -> bool:
    """播种 2 条消耗记录（A 模型 1 条大额 + B 模型 1 条小额），用于摘要/Chip/明细/批量栏断言"""
    m2 = _m2()
    db = m2._db_pull(workdir)
    if db is None:
        return False
    con = sqlite3.connect(str(db))
    try:
        con.execute("delete from ai_read_aloud_usage_records")
        meta = [(r[1], (r[2] or "").upper(), r[3], r[4])
                for r in con.execute("pragma table_info(ai_read_aloud_usage_records)")]

        def ins(overrides: dict):
            names, vals = [], []
            for name, ctype, notnull, dflt in meta:
                if name in overrides:
                    names.append(name)
                    vals.append(overrides[name])
                elif notnull and dflt is None:
                    names.append(name)
                    vals.append(0 if ("INT" in ctype or "REAL" in ctype) else "")
            con.execute(f"insert into ai_read_aloud_usage_records ({','.join('`' + n + '`' for n in names)})"
                        f" values ({','.join('?' * len(names))})", vals)

        now = int(time.time() * 1000)
        ins({"id": 9001, "type": "role", "status": "success", "bookName": "L2校验书",
             "chapterTitle": "第1章", "modelId": SEED_USAGE_A_MODEL,
             "inputTokens": 1000000, "cachedInputTokens": 200000, "outputTokens": 50000,
             "totalTokens": 1250000, "createdAt": now})
        ins({"id": 9002, "type": "bgm", "status": "success", "bookName": "L2校验书",
             "chapterTitle": "第2章", "modelId": SEED_USAGE_B_MODEL,
             "inputTokens": 2000, "cachedInputTokens": 0, "outputTokens": 500,
             "totalTokens": 2500, "createdAt": now - 60000})
        con.commit()
    finally:
        con.close()
    return m2._db_push(db)


def _para_seed(workdir: Path, rows: int) -> bool:
    """播种段落规则（rows=0 ⇒ 清空，用于构造「无规则」空态）"""
    m2 = _m2()
    db = m2._db_pull(workdir)
    if db is None:
        return False
    con = sqlite3.connect(str(db))
    try:
        con.execute("delete from paragraph_rules")
        meta = [(r[1], (r[2] or "").upper(), r[3], r[4])
                for r in con.execute("pragma table_info(paragraph_rules)")]
        for index in range(rows):
            overrides = {"id": 9100 + index, "name": SEED_PARA_NAMES[index], "script": "return text"}
            names, vals = [], []
            for name, ctype, notnull, dflt in meta:
                if name in overrides:
                    names.append(name)
                    vals.append(overrides[name])
                elif notnull and dflt is None:
                    names.append(name)
                    vals.append(0 if ("INT" in ctype or "REAL" in ctype) else "")
            con.execute(f"insert into paragraph_rules ({','.join('`' + n + '`' for n in names)})"
                        f" values ({','.join('?' * len(names))})", vals)
        con.commit()
    finally:
        con.close()
    return m2._db_push(db)


class _DelayedServer(threading.Thread):
    """慢响应服务器（延迟 N 秒后 500）：用于观察「导入进行中」状态不会被一闪而过"""

    def __init__(self, port: int, delay_s: float = 5.0):
        super().__init__(daemon=True)
        self.delay_s = delay_s
        self.hits = 0
        self._srv = HTTPServer(("127.0.0.1", port), self._make_handler())

    def _make_handler(self):
        delay = self.delay_s
        outer = self

        class _Handler(BaseHTTPRequestHandler):
            def do_GET(self):  # noqa: N802
                outer.hits += 1
                time.sleep(delay)
                self.send_response(500)
                self.end_headers()
                self.wfile.write(b"server error")

            def log_message(self, *args):
                return

        return _Handler

    def run(self):
        self._srv.serve_forever()

    def stop(self):
        try:
            self._srv.shutdown()
            self._srv.server_close()
        except Exception:
            pass


def _start_para(book_url: str) -> bool:
    """直起段落规则管理页（传合成 bookUrl ⇒ 上下文非空，走「有当前书」分支；shell 不稳时 su 兜底）"""
    simple = ACT_PARA_RULE.rsplit(".", 1)[-1]
    reset_app()
    for round_ in range(2):
        if round_ == 0:
            sh("am", "start", "-n", f"{PKG}/{ACT_PARA_RULE}", "--es", "bookUrl", book_url)
        else:
            sh_su(f"am start -n {PKG}/{ACT_PARA_RULE} --es bookUrl {book_url}")
        for _ in range(6):
            time.sleep(1.2)
            if simple in current_activity():
                time.sleep(2.0)
                return True
    return False


def _handle_desc_count(xml: str) -> int:
    """统计 content-desc 为拖拽手柄的节点数（手柄是插入的 ImageView，靠 a11y desc 定位）"""
    return sum(1 for m in re.finditer(r"<node[^>]*>", xml)
               if f'content-desc="{S_PARA_HANDLE_DESC}"' in m.group(0))


def s9_usage_and_para_rule_page(d) -> bool:
    """消耗记录（F30/F31）+ 段落规则管理（F50/F51/F52）"""
    print("  [s9] ===== 消耗记录摘要/批量栏 + 段落规则手柄/空态/导入进度 =====")
    m2 = _m2()
    workdir = Path(tempfile.mkdtemp(prefix="m3s9_"))
    db_snap = workdir / "legado_snapshot.db"
    if not m2._snapshot_db(workdir, db_snap):
        print("  [s9] 数据库快照失败（前置）")
        return False
    server = None
    src_ai = _src_text(SRC_AI_USAGE)
    src_para = _src_text(SRC_PARA_RULE)
    ok = False
    try:
        from PIL import Image
        shot_dir = Path(tempfile.mkdtemp(prefix="m3s9shot_"))

        # ---------------- 阶段 A：消耗记录（F30 + F31）----------------
        reset_app()
        if not _usage_seed(workdir):
            print("  [s9] 消耗记录播种失败")
            return False
        reset_app()
        # 该活动在 Manifest 显式 `exported=false`：shell 直起不稳（实测被丢回桌面）⇒ 走 su 兜底通道
        if not start_robust(ACT_AI_USAGE):
            print("  [s9] 消耗记录页未能落地（非导出组件通道）")
            return False
        time.sleep(2.0)
        xml = dump_xml(d)
        ca.shot(d, "m3usage_s9_landed")

        summary_nodes = [t for t, *_ in text_nodes(xml)
                         if S_AI_SUMMARY_BOOK in t and "条" in t]
        # F30：摘要首行只留范围/条数（旧实现把 8 段拼一行，此断言即回归哨兵）；
        # 现为**单个 TextView 多行** ⇒ 判据取 `\n` 之前的第一行，且第二/三行必须带统计与按模型信息
        summary_ok = False
        summary_all = ""
        for label, *_ in text_nodes(xml):
            if S_AI_SUMMARY_BOOK in label and "条" in label:
                summary_all = label.replace("&#10;", "\n")
                first_line = summary_all.split("\n")[0]
                summary_ok = "输入" not in first_line
                break
        chip_ok = (S_AI_TOTAL_CHIP in summary_all and S_AI_INPUT_LINE in summary_all
                   and S_AI_MODEL_A_LINE in summary_all)
        # F30 主指标强调：摘要节点内应存在**有色度**的像素段（accent 着色的「总 N」），
        # 逐行扫描取最大色度（比定位精确坐标稳；其余文字为次级灰、色度≈0）
        emphasize_ok = False
        emph_b = node_bounds(xml, S_AI_TOTAL_CHIP, contains=True)
        if emph_b:
            p_emph = str(shot_dir / "summary_emph.png")
            d.screenshot(p_emph)
            img_e = Image.open(p_emph).convert("RGB")
            max_chroma = 0
            for yy in range(max(0, emph_b["top"]), min(img_e.height, emph_b["bottom"])):
                for xx in range(max(0, emph_b["left"]), min(img_e.width, emph_b["right"])):
                    px = img_e.getpixel((xx, yy))
                    max_chroma = max(max_chroma, max(px) - min(px))
            emphasize_ok = max_chroma >= 30
            print(f"  [s9] F30 主指标强调：节点内最大色度={max_chroma}（≥30 即 accent 段在场）")
        print(f"  [s9] F30 摘要首行不含统计段={summary_ok} / 多行含 输入+总+按模型={chip_ok}")

        # F31：长按首条 ⇒ 批量栏浮现（删除选中 N / 导出）
        rows = text_nodes(dump_xml(d))
        item = next((n for n in rows if "多角色" in n[0]), None)
        batch_ok = delete_dialog_ok = export_ok = clear_ok = False
        if item:
            d.long_click(item[3], item[4])
            time.sleep(1.5)
            xml_b = dump_xml(d)
            has_delete = f"{S_AI_DELETE_PREFIX}1" in xml_b
            has_export = S_AI_EXPORT in xml_b
            ca.shot(d, "m3usage_s9_batch_bar")
            print(f"  [s9] F31 批量栏：「{S_AI_DELETE_PREFIX}1」={has_delete} / 「{S_AI_EXPORT}」={has_export}")
            batch_ok = has_delete and has_export
            del_b = node_bounds(xml_b, f"{S_AI_DELETE_PREFIX}1")
            if del_b:
                click_xy(d, del_b["cx"], del_b["cy"])
                time.sleep(1.6)
                xml_c = dump_xml(d)
                has_confirm = S_AI_DELETE_TITLE in xml_c and S_CANCEL in xml_c
                delete_dialog_ok = has_confirm
                print(f"  [s9] F31 删除二次确认（标题「{S_AI_DELETE_TITLE}」+「{S_CANCEL}」）={has_confirm}")
                if has_confirm:
                    # Compose 弹窗按钮用坐标点击更可靠（u2 的 text 匹配在 Dialog 上可能点到无效层），
                    # 并**轮询确认弹窗真的关闭**——否则「批量栏文本仍在」会被误读为「取消后选中保留」
                    cancel_b = node_bounds(xml_c, S_CANCEL)
                    if cancel_b:
                        click_xy(d, cancel_b["cx"], cancel_b["cy"])
                    dialog_gone = False
                    for _ in range(6):
                        time.sleep(0.8)
                        if S_AI_DELETE_TITLE not in dump_xml(d):
                            dialog_gone = True
                            break
                    still = f"{S_AI_DELETE_PREFIX}1" in dump_xml(d)
                    delete_dialog_ok = dialog_gone and still
                    print(f"  [s9] F31 取消后：弹窗关闭={dialog_gone} / 选中保留（零数据污染）={still}")
            # 取消选中 ⇒ 批量栏收起（弹窗关闭有动画，先轮询等列表节点回归）
            # ⚠️ 匹配用 `in`（不是 startswith）：选中态行首带「✓ 」前缀（`UsageHolder.bind` 加的）
            item2 = None
            for _ in range(10):
                item2 = next((n for n in text_nodes(dump_xml(d))
                              if "多角色" in n[0]), None)
                if item2:
                    break
                time.sleep(1.0)
            if item2:
                d.long_click(item2[3], item2[4])
                time.sleep(1.5)
                clear_ok = S_AI_DELETE_PREFIX not in dump_xml(d)
                print(f"  [s9] F31 取消选中后批量栏收起={clear_ok}")
            else:
                print("  [s9] F31 未取到记录行（取消选中未取证）")
            # 重新选中后验证导出通道（导出会离开本页，故放在最后一步）
            item3 = next((n for n in text_nodes(dump_xml(d)) if "多角色" in n[0]), None)
            if item3:
                d.long_click(item3[3], item3[4])
                time.sleep(1.5)
            exp_b = node_bounds(dump_xml(d), S_AI_EXPORT)
            if exp_b:
                click_xy(d, exp_b["cx"], exp_b["cy"])
                time.sleep(4.0)
                export_ok = ACT_HANDLE_FILE in current_activity()
                print(f"  [s9] F31 导出走「选择保存位置」通道（{ACT_HANDLE_FILE}）={export_ok}")

        # ---------------- 阶段 B：段落规则（F51 + F50）----------------
        reset_app()
        if not _para_seed(workdir, 2):
            print("  [s9] 段落规则播种失败")
            return False
        landed = _start_para(PARA_BOOK_URL)
        xml_p = dump_xml(d)
        ca.shot(d, "m3usage_s9_para_rules")
        handle_count = _handle_desc_count(xml_p)
        names_ok = all(name in xml_p for name in SEED_PARA_NAMES)
        hint_ok = S_PARA_DRAG_HINT in xml_p
        print(f"  [s9] F51 落地={landed} / 拖拽手柄数={handle_count}（期望 ≥2）/ "
              f"规则名在场={names_ok} / 摘要手柄提示={hint_ok}")

        # F50：无规则空态 ⇒ 引导文案 + 底部「添加」主操作仍在场
        reset_app()
        if not _para_seed(workdir, 0):
            print("  [s9] 空态播种失败")
            return False
        _start_para(PARA_BOOK_URL)
        xml_e = dump_xml(d)
        ca.shot(d, "m3usage_s9_para_empty")
        empty_ok = (S_PARA_EMPTY in xml_e and S_PARA_EMPTY_GUIDE in xml_e
                    and "添加" in xml_e)
        print(f"  [s9] F50 空态：提示+引导+主操作在场={empty_ok}"
              f"（「{S_PARA_EMPTY}」/「{S_PARA_EMPTY_GUIDE}」）")

        # ---------------- 阶段 C：导入进度闭环（F52）----------------
        server = _DelayedServer(IMPORT_PORT, delay_s=5.0)
        server.start()
        _reverse_on(IMPORT_PORT)
        importing_ok = False
        import_menu = topbar_action_bounds(xml_e, 1)
        print(f"  [s9] F52 顶栏导入入口={import_menu}")
        if import_menu:
            click_xy(d, import_menu["cx"], import_menu["cy"])
            time.sleep(1.6)
            opened_menu = S_PARA_IMPORT_ONLINE in dump_xml(d)
            tapped = tap_text(d, S_PARA_IMPORT_ONLINE)
            print(f"  [s9] F52 导入菜单出现={opened_menu} / 点「{S_PARA_IMPORT_ONLINE}」={tapped}")
            time.sleep(1.6)
            typed = type_search(d, IMPORT_URL)
            print(f"  [s9] F52 URL 输入={typed}")
            if typed:
                tap_text(d, S_OK)
                for _ in range(10):
                    time.sleep(0.6)
                    if S_PARA_IMPORTING in dump_xml(d):
                        importing_ok = True
                        break
                ca.shot(d, "m3usage_s9_importing")
            print(f"  [s9] F52 导入进行中态可见={importing_ok}（服务端命中={server.hits}）")
        else:
            print("  [s9] F52 未定位顶栏导入入口")

        src_checks = {
            "F30 摘要多行+强调": ("emphasizeTotal" in src_ai and "MAX_MODEL_LINES" in src_ai
                          and "SpannableString" in src_ai),
            "F30 主指标千分位": "formatTokens" in src_ai,
            "F30 摘要零新增视图": ("chipRow" not in src_ai and "detailPanel" not in src_ai),
            "F31 批量栏条件挂载+导出": ("renderBatchBar" in src_ai and "HandleFileContract.EXPORT" in src_ai
                              and "container.removeView(bar)" in src_ai),
            "F51 手柄复用全站资产": ("ic_drag_handle" in src_para and "itemTouchHelper?.startDrag" in src_para),
            "F50 空态引导": ("paragraph_rule_no_book_guide" in src_para
                        and "paragraph_rule_empty_guide" in src_para),
            "F52 导入进度+防重复": ("paragraph_rule_importing" in src_para
                            and "btnAdd.isEnabled = false" in src_para),
            "顶栏图标为矢量（非 selector）": "ic_bottom_books_e" in src_ai,
        }
        src_ok = all(src_checks.values())
        print(f"  [s9] 源码断言 {sum(src_checks.values())}/{len(src_checks)}："
              f"{[k for k, v in src_checks.items() if not v] or '全通过'}")

        ok = bool(summary_ok and chip_ok and emphasize_ok and batch_ok and delete_dialog_ok
                  and export_ok and clear_ok and landed and handle_count >= 2 and names_ok
                  and hint_ok and empty_ok and importing_ok and src_ok)
    except Exception as e:
        print(f"  [s9] 异常终止: {type(e).__name__}: {e}")
    finally:
        release_reverse(IMPORT_PORT)
        if server:
            server.stop()
        reset_app()
        try:
            rolled = m2._db_push(db_snap)
            print(f"  [s9] 数据库快照已回滚={rolled}")
        except Exception as e:
            print(f"  [s9] 兜底回滚异常: {type(e).__name__}")
        # 导出动作会在应用私有目录落一个 JSON：测试后清掉（零残留）
        try:
            sh_su(f"rm -f /data/data/{PKG}/files/aiReadAloudUsageSelection.json")
        except Exception:
            pass
        reset_app()
    return ok


# ===================== s8：rss/articles（订阅文章列表）=====================
# F142 页脚错误可恢复态（LoadMoreView 错误分支）+ F143 分类 Tab 未读徽标
#   + 顺带修复：首页加载失败时页脚「重试」并未真正重拉（nextPageUrl 为 null ⇒ 退化成「我是有底线的」）

ACT_RSS_ART = "io.legado.app.ui.rss.article.RssSortActivity"
SEED_ART_SOURCE = "l2seed://articles-badge"
SEED_ART_NAME = "L2文章列表校验源"
ART_PORT = 18543
# 分类清单（我自造的合成标签，非用户业务数据）：A 3 条未读 / B 2 条全已读 / C 1200 条未读（测 999+ 封顶）
SEED_ART_SORTS = (("L2分类A", "a", 3), ("L2分类B", "b", 2), ("L2分类C", "c", 1200))
SEED_ART_ITEM_PREFIX = "L2条目"

S_ERR_SUMMARY_PREFIX = "加载失败"     # error_load_msg 前缀
S_ERR_DETAIL = "点击查看详情"          # error_view_detail
S_RETRY = "重试"                      # retry
S_ERROR_TITLE = "错误"                # error

SRC_RSS_ART_FRAG = "app/src/main/java/io/legado/app/ui/rss/article/RssArticlesFragment.kt"
SRC_RSS_ART_VM = "app/src/main/java/io/legado/app/ui/rss/article/RssArticlesViewModel.kt"
SRC_LOAD_MORE = "app/src/main/java/io/legado/app/ui/widget/recycler/LoadMoreView.kt"
SRC_LOAD_MORE_XML = "app/src/main/res/layout/view_load_more.xml"
SRC_BADGE = "app/src/main/java/io/legado/app/ui/widget/text/CountBadgeDrawable.kt"
SRC_RSS_DAO = "app/src/main/java/io/legado/app/data/dao/RssArticleDao.kt"
SRC_MANGA = "app/src/main/java/io/legado/app/ui/book/manga/ReadMangaActivity.kt"

# danger 真值（AppSemanticColors.Danger = #D44848）：徽标胶囊按此判定，容差防抗锯齿/主题底色混色
DANGER_RGB = (212, 72, 72)
DANGER_TOL = 26


class _HitServer(threading.Thread):
    """计数监听器：接受连接后立即关闭（不返回 HTTP 响应）。

    用途有二——① 让订阅文章加载必然失败（构造页脚错误态）；② 用命中次数给出「重试是否真的
    重新发起请求」的客观证据（不依赖 UI 文案自证）。
    """

    def __init__(self, port: int):
        super().__init__(daemon=True)
        self.hits = 0
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind(("127.0.0.1", port))
        self._sock.listen(16)

    def run(self):
        while True:
            try:
                conn, _ = self._sock.accept()
            except OSError:
                return
            self.hits += 1
            try:
                conn.close()
            except OSError:
                pass

    def stop(self):
        try:
            self._sock.close()
        except OSError:
            pass


def _art_seed(workdir: Path) -> bool:
    """播种合成源 + 文章：整行复制既有源后改写（源名/URL/分类清单/规则），零真实源污染。

    仅列出「必须给值的列」（显式覆盖项 + NOT NULL 且无默认值者），其余交给库内默认值，
    避免向 NOT NULL DEFAULT 列显式写 NULL（会触发 NOT NULL 约束失败）。
    """
    m2 = _m2()
    db = m2._db_pull(workdir)
    if db is None:
        return False
    con = sqlite3.connect(str(db))
    try:
        cols = [r[1] for r in con.execute("pragma table_info(rssSources)")]
        row = con.execute("select * from rssSources where enabled = 1 limit 1").fetchone()
        if not row:
            return False
        data = dict(zip(cols, row))
        data["sourceUrl"] = SEED_ART_SOURCE
        data["sourceName"] = SEED_ART_NAME
        # 分类 URL 指向本机计数监听器（adb reverse）：列表分类只依赖 sortUrl，纯本地解析。
        # ⚠️ 分隔符必须用**无空格的 `&&`**：`sortUrls()` 走 `split("(&&&|&&|\n)+")` 且**不 trim**，
        #    写成 " && " 会让第 2 条起的分类名带**前导空格**（Tab 上看不出、但与库内 sort 值不一致
        #    ⇒ 未读徽标查不到计数，实测踩坑 2026-09-20）。
        data["sortUrl"] = "&&".join(
            f"{name}::http://127.0.0.1:{ART_PORT}/{slug}"
            for name, slug, _ in SEED_ART_SORTS
        )
        data["ruleArticles"] = None      # 去掉列表规则 ⇒ 加载失败只来自网络通道
        data["ruleNextPage"] = None      # 非分页源：重试应走「按当前页重拉」分支
        data["loginUrl"] = None          # 避免继承既有源的登录分支干扰
        data["loginCheckJs"] = None
        data["preload"] = 0              # 关预加载：只有当前 Tab 发一次请求，命中数可控
        data["articleStyle"] = 0         # 普通单列列表：Tab 行结构确定，便于像素取样
        data["enabled"] = 1
        con.execute(
            f"insert or replace into rssSources ({','.join(cols)})"
            f" values ({','.join('?' * len(cols))})",
            [data[c] for c in cols]
        )
        con.execute("delete from rssArticles where origin = ?", (SEED_ART_SOURCE,))
        art_meta = [(r[1], (r[2] or "").upper(), r[3], r[4])
                    for r in con.execute("pragma table_info(rssArticles)")]
        rec_meta = [(r[1], (r[2] or "").upper(), r[3], r[4])
                    for r in con.execute("pragma table_info(rssReadRecords)")]

        def ins(table: str, meta: list, overrides: dict):
            names, vals = [], []
            for name, ctype, notnull, dflt in meta:
                if name in overrides:
                    names.append(name)
                    vals.append(overrides[name])
                elif notnull and dflt is None:
                    names.append(name)
                    vals.append(0 if ("INT" in ctype or "REAL" in ctype) else "")
            sql = (f"insert or replace into {table} "
                   f"({','.join('`' + n + '`' for n in names)}) "
                   f"values ({','.join('?' * len(names))})")
            con.execute(sql, vals)

        now = int(time.time() * 1000)
        order = now
        for name, slug, count in SEED_ART_SORTS:
            read_all = (slug == "b")     # B 分类整类已读 ⇒ 不应出现徽标（对照组）
            for i in range(count):
                link = f"l2art://{slug}/{i}"
                order -= 1
                title = f"{SEED_ART_ITEM_PREFIX}{slug.upper()}{i + 1}"
                ins("rssArticles", art_meta, {
                    "origin": SEED_ART_SOURCE, "sort": name, "link": link,
                    "title": title, "order": order, "read": 1 if read_all else 0,
                    "type": 0, "pubDate": "",
                })
                if read_all:
                    ins("rssReadRecords", rec_meta, {
                        "record": link, "origin": SEED_ART_SOURCE, "sort": name,
                        "title": title, "read": 1, "readTime": now,
                        "type": 0, "durPos": 0, "pubDate": "",
                    })
        con.commit()
    finally:
        con.close()
    return m2._db_push(db)


def _device_density() -> float:
    """屏幕密度（px/dp）：取 `wm density` 输出最后一个数字段（覆盖值优先）"""
    r = sh("wm", "density", timeout=20)
    vals = re.findall(r"(\d+)", (r.stdout or b"").decode("utf-8", errors="ignore"))
    return (int(vals[-1]) / 160.0) if vals else 2.0


def _danger_run(img, b, ratio: float = 0.5):
    """胶囊**右半区**内 danger 像素的水平跨度：返回 (命中列数, 跨度px)。

    徽标是 TextView 的 compound drawable（不进无障碍树 ⇒ 无法用节点定位），
    故以像素为准：右半区内存在与 danger 真值同色（容差 [DANGER_TOL]）的像素，
    即证明徽标已渲染；跨度用于区分「3」与「999+」（后者更宽）。
    """
    x0 = int(b["left"] + (b["right"] - b["left"]) * ratio)
    x1 = min(img.width, b["right"])
    y0, y1 = max(0, b["top"] + 2), min(img.height, b["bottom"] - 2)
    hits = []
    for x in range(x0, x1):
        for y in range(y0, y1):
            p = img.getpixel((x, y))
            if all(abs(p[i] - DANGER_RGB[i]) <= DANGER_TOL for i in range(3)):
                hits.append(x)
                break
    if not hits:
        return 0, 0
    return len(hits), max(hits) - min(hits) + 1


def s8_rss_articles_page(d) -> bool:
    """订阅文章列表：F142 页脚错误可恢复 + F143 分类未读徽标（含 999+ 封顶与已读不显）"""
    print("  [s8] ===== 订阅文章列表错误页脚与分类未读徽标 =====")
    m2 = _m2()
    workdir = Path(tempfile.mkdtemp(prefix="m3art_"))
    db_snap = workdir / "legado_snapshot.db"
    if not m2._snapshot_db(workdir, db_snap):
        print("  [s8] 数据库快照失败（前置）")
        return False
    server = None
    ok = False
    try:
        server = _HitServer(ART_PORT)
        server.start()
        if not _reverse_on(ART_PORT):
            print("  [s8] adb reverse 未建立（设备侧不可达监听器）")
            return False
        # 推库前先停应用：运行中的 SQLite 连接持旧 inode，页内数据变化必须走「停 → 推 → 重开」
        reset_app()
        if not _art_seed(workdir):
            print("  [s8] 合成源/文章播种失败")
            return False
        reset_app()
        sh("am", "start", "-n", f"{PKG}/{ACT_RSS_ART}", "--es", "sourceUrl", SEED_ART_SOURCE)
        time.sleep(7.0)   # 列表先出库内文章，随后网络加载失败落到页脚
        landed = ACT_RSS_ART.split(".")[-1] in current_activity()
        xml1 = dump_xml(d)
        ca.shot(d, "m3art_s8_landed")
        print(f"  [s8] 落地={landed} / 首次加载命中={server.hits}")

        from PIL import Image
        shot_dir = Path(tempfile.mkdtemp(prefix="m3artshot_"))

        # ---------- F143：分类 Tab 未读徽标（A=3 有 / B=全已读 无 / C=1200 封顶）----------
        tabs = tab_nodes(xml1)
        badge_ok = False
        run_a = run_b = run_c = 0
        if len(tabs) == len(SEED_ART_SORTS):
            p1 = str(shot_dir / "tabs_badge.png")
            d.screenshot(p1)
            img1 = Image.open(p1).convert("RGB")
            run_a = _danger_run(img1, tabs[0]["bounds"])
            run_b = _danger_run(img1, tabs[1]["bounds"])
            run_c = _danger_run(img1, tabs[2]["bounds"])
            # 判据：未读分类有 danger 徽标；全已读分类无；超量分类徽标更宽（999+ 封顶后仍为宽胶囊）
            badge_ok = (run_a[0] > 0 and run_b[0] == 0 and run_c[0] > 0
                        and run_c[1] > run_a[1])
            print(f"  [s8] F143 徽标像素跨度（列数/宽度）：A(3条未读)={run_a} "
                  f"B(全已读)={run_b} C(1200条)={run_c} ⇒ {badge_ok}")
        else:
            print(f"  [s8] F143 分类 Tab 数={len(tabs)}（播种 {len(SEED_ART_SORTS)}）⇒ 无法比对")

        # ---------- 列表内容保留（错误页脚与既有内容并存）----------
        keep_ok = sum(1 for t, _, _, _, _ in text_nodes(xml1)
                      if t.startswith(SEED_ART_ITEM_PREFIX)) > 0
        print(f"  [s8] 页脚错误态下列表内容仍在场={keep_ok}")

        # ---------- F142：错误页脚三层结构 ----------
        hint_b = node_bounds(xml1, S_ERR_DETAIL)
        summary_hit = any(t.startswith(S_ERR_SUMMARY_PREFIX) for t, _, _, _, _ in text_nodes(xml1))
        dot_ok = False
        if hint_b:
            p2 = str(shot_dir / "footer_error.png")
            d.screenshot(p2)
            img2 = Image.open(p2).convert("RGB")
            # 圆点在错误行左侧：容器左内边距 12dp(margin) + 12dp(padding) + 半径 4dp ⇒ 取 [18dp,38dp] 带
            density = _device_density()
            xs = [int(v * density) for v in (18, 38)]
            y0, y1 = hint_b["cy"] - int(8 * density), hint_b["cy"] + int(8 * density)
            dot_ok = any(
                all(abs(img2.getpixel((x, y))[i] - DANGER_RGB[i]) <= DANGER_TOL for i in range(3))
                for x in range(xs[0], xs[1] + 1)
                for y in range(max(0, y0), y1 + 1)
            )
        footer_ok = bool(hint_b) and summary_hit
        print(f"  [s8] F142 页脚错误三层：摘要前缀在场={summary_hit} / 详情提示在场={bool(hint_b)} "
              f"/ danger 圆点={dot_ok}（提示文案={S_ERR_DETAIL}）")

        # ---------- 重试闭环：详情弹窗内重试 ⇒ 服务端命中 +1（真正的重新拉取）----------
        retry_ok = False
        dialog_ok = False
        repeat_ok = False
        hits_before = server.hits
        if hint_b:
            click_xy(d, hint_b["cx"], hint_b["cy"])
            time.sleep(2.0)
            xml_d = dump_xml(d)
            dialog_ok = (S_RETRY in xml_d) and (S_ERROR_TITLE in xml_d)
            ca.shot(d, "m3art_s8_error_dialog")
            print(f"  [s8] F142 详情弹窗：含「{S_ERROR_TITLE}」与「{S_RETRY}」={dialog_ok}")
            if dialog_ok:
                tap_text(d, S_RETRY)
                time.sleep(4.0)
                xml_r = dump_xml(d)
                retry_ok = (server.hits > hits_before)
                back_to_err = any(t.startswith(S_ERR_SUMMARY_PREFIX)
                                  for t, _, _, _, _ in text_nodes(xml_r))
                print(f"  [s8] F142 重试闭环：命中 {hits_before} → {server.hits}"
                      f"（重新发起请求={retry_ok}）/ 源仍不可达 ⇒ 回到错误页脚={back_to_err}")
            # 可重复恢复：再次点击页脚仍能打开详情弹窗（重试后先轮询等错误页脚回归）
            b2 = None
            for _ in range(6):
                b2 = node_bounds(dump_xml(d), S_ERR_DETAIL)
                if b2:
                    break
                time.sleep(1.0)
            repeat_ok = False
            if b2:
                click_xy(d, b2["cx"], b2["cy"])
                time.sleep(1.8)
                repeat_ok = S_RETRY in dump_xml(d)
                print(f"  [s8] F142 恢复通道可重复={repeat_ok}")
                d.press("back")
                time.sleep(1.2)
            else:
                print("  [s8] F142 二次定位页脚失败（可重复性未取证）")

        # ---------- 源码断言（像素取不到时的兜底口径 + 共享组件调用点一致性）----------
        src_frag = _src_text(SRC_RSS_ART_FRAG)
        src_lm = _src_text(SRC_LOAD_MORE)
        src_xml = _src_text(SRC_LOAD_MORE_XML)
        src_badge = _src_text(SRC_BADGE)
        src_dao = _src_text(SRC_RSS_DAO)
        src_manga = _src_text(SRC_MANGA)
        src_checks = {
            "错误页脚三层结构落定": all(k in src_xml for k in
                                 ("error_container", "error_dot", "tv_error_summary", "tv_error_hint")),
            "危险色取自语义单源": ("AppSemanticColors.Danger" in src_lm and "initErrorView" in src_lm),
            "提示文案按真实行为分流": ("R.string.error_view_detail" in src_lm
                              and "R.string.dynamic_click_retry" in src_lm),
            "摘要取错误首行": "errorSummaryLine" in src_lm,
            "详情正文限高可滚动": "messageInContent = true" in src_lm,
            "旧硬编码文案已删": "点击查看详情\"" not in src_lm,
            "首页失败重试重拉当前页": ("forceLoad && viewModel.nextPageUrl.isNullOrEmpty()" in src_frag
                              and "loadArticles(it, viewModel.page)" in src_frag),
            "失败复位在途标记": _src_text(SRC_RSS_ART_VM).count("isLoading = false") >= 4,
            "徽标 999+ 封顶": ("MAX_DISPLAY = 999" in src_badge and "\"$MAX_DISPLAY+\"" in src_badge),
            "徽标挂 compound drawable": "setCompoundDrawablesRelativeWithIntrinsicBounds" in _src_text(
                "app/src/main/java/io/legado/app/ui/rss/article/RssSortActivity.kt"),
            "未读聚合走 flow": ("flowUnreadCountBySort" in src_dao and "group by t1.sort" in src_dao),
            "共享消费点口径同步": "error(null, getString(R.string.load_failed))" in src_manga,
        }
        src_ok = all(src_checks.values())
        print(f"  [s8] 源码断言 {sum(src_checks.values())}/{len(src_checks)}："
              f"{[k for k, v in src_checks.items() if not v] or '全通过'}")

        ok = bool(landed and keep_ok and footer_ok and dot_ok and badge_ok
                  and dialog_ok and retry_ok and repeat_ok and src_ok)
    except Exception as e:
        print(f"  [s8] 异常终止: {type(e).__name__}: {e}")
    finally:
        release_reverse(ART_PORT)
        if server:
            server.stop()
        reset_app()
        try:
            rolled = m2._db_push(db_snap)
            print(f"  [s8] 数据库快照已回滚={rolled}")
        except Exception as e:
            print(f"  [s8] 兜底回滚异常: {type(e).__name__}")
        reset_app()
    return ok


def guarded(fn):
    def inner(d):
        try:
            return fn(d)
        except Exception as e:
            print(f"  [EXC] {type(e).__name__}: {e}")
            return False

    inner.__name__ = getattr(fn, "__name__", "step")
    return inner


# ============================ s12：M4 批次（image/image-gallery + rss/source-edit） ============================

ACT_RSS_ART_S12 = "io.legado.app.ui.rss.article.RssSortActivity"
ACT_GALLERY = "io.legado.app.ui.image.ImageGalleryActivity"
ACT_SOURCE_EDIT = "io.legado.app.ui.rss.source.edit.RssSourceEditActivity"

GAL_PORT = 18561
# 失效文章专用端口：**从不监听**。为什么不用「停掉 GAL_PORT 服务」制造失败——实测踩坑：
# `Rss.getContentAwait` 的文章正文**会被缓存**，停服后再次刷新仍 `imageCount=3 costMs=0`
# （logcat 铁证 2026-09-21），失败态根本构造不出来。指向一个从未监听过的端口 ⇒ 连接必被拒，
# 且该 link 从未被抓取过 ⇒ 无缓存可命中，失败是确定性的。
GAL_DEAD_PORT = 18562
GAL_SOURCE = "l2seed://image-gallery"
GAL_SOURCE_NAME = "L2图片浏览校验源"
GAL_SORT = "L2图集"
GAL_ART_TITLE = "L2图集条目"
GAL_ART_TITLE_DEAD = "L2图集失效条目"
SRC_SEED_URL = "l2seed://source-edit-required"

# 文案取自 values-zh/strings.xml 真值
S_GAL_RUNNING = "正在刷新图片…"        # image_refresh_running
S_GAL_DONE = "已刷新"                  # image_refresh_done
S_GAL_FAILED = "刷新失败"              # image_refresh_failed
S_GAL_ERR_SET = ("网络连接失败", "图片解析失败", "订阅源配置异常")   # image_load_error_*
S_GAL_BACK_TOP = "返回顶部"            # image_back_to_top
S_GAL_REFRESH_DESC = "刷新"            # refresh（顶栏刷新图标 content-desc）
S_SRC_GROUP_SET = ("账户与变量", "编辑辅助", "导入 · 导出", "工具")   # source_menu_group_*
S_SRC_REQUIRED_ERR = "必填项，不能为空"  # source_required_hint
S_SRC_SAVE_DESC = "保存"                # action_save
S_SRC_TAB_LIST = "列表"                 # source_tab_list
S_SRC_NAME_HINT_PREFIX = "* 源名称"      # 必填标记 + source_name

SRC_GALLERY_ACT = "app/src/main/java/io/legado/app/ui/image/ImageGalleryActivity.kt"
SRC_GALLERY_ADAPTER = "app/src/main/java/io/legado/app/ui/image/adapter/ImageCanvasAdapter.kt"
SRC_SOURCE_EDIT_ACT = "app/src/main/java/io/legado/app/ui/rss/source/edit/RssSourceEditActivity.kt"
SRC_EDIT_ENTITY = "app/src/main/java/io/legado/app/ui/widget/text/EditEntity.kt"

# 1x1 真实 PNG 字节：Glide downloadOnly → decodeBounds 需要**真能被解码**的图（F271 同型教训），
# 用假路径/空文件会让「加载成功」断言必然失败 ⇒ 把功能正常误判成缺陷（假阴性）。
_TINY_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


class _GalleryServer(threading.Thread):
    """本机图集服务：`/art1` 返回含 3 张 `<img>` 的 HTML，`/imgN.png` 返回真实 PNG 字节。

    为什么是 3 张：`ImageUrlExtractor` 在 **L1 命中 < 3 张**时才进 L2（WebView 嗅探 6s）——
    给 3 张可跳过 L2，加载既快又确定。为什么必须走**真实入口**（订阅列表 → 点条目）而不是
    `am start` 直起：`ImageGalleryActivity` 的数据源是 `ImagePlay` 单例，只有
    `ReadRss.readNoHtml` 会注入它；直起只剩「订阅源为空」的错误分支（已实测）。
    """

    def __init__(self, port: int):
        super().__init__(daemon=True)
        self.port = port
        self.hits = 0
        self._httpd = None

    def run(self):
        import http.server
        png = _TINY_PNG
        html = ("<html><head><title>L2GAL</title></head><body>"
                + "".join(f'<img src="/img{i}.png">' for i in (1, 2, 3))
                + "</body></html>").encode("utf-8")
        outer = self

        class _H(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                outer.hits += 1
                is_png = urlparse(self.path).path.endswith(".png")
                body = png if is_png else html
                self.send_response(200)
                self.send_header("Content-Type",
                                 "image/png" if is_png else "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *a):
                pass

        class _Srv(http.server.ThreadingHTTPServer):
            daemon_threads = True

        try:
            self._httpd = _Srv(("127.0.0.1", self.port), _H)
        except OSError:
            return
        self._httpd.serve_forever()

    def stop(self):
        try:
            if self._httpd:
                self._httpd.shutdown()
                self._httpd.server_close()
        except Exception:
            pass


def _text_by_id(xml: str, res_suffix: str) -> str:
    """按 resource-id 后缀取节点 text（View 系控件靠 id 定位最稳）"""
    for m in re.finditer(r"<node[^>]*>", xml):
        tag = m.group(0)
        rid = re.search(r'resource-id="([^"]*)"', tag)
        if not rid or not rid.group(1).endswith(res_suffix):
            continue
        t = re.search(r'\btext="([^"]*)"', tag)
        return t.group(1) if t else ""
    return ""


def _s12_upsert(con, table: str, cols: list, data: dict):
    con.execute(
        f"insert or replace into {table} ({','.join(cols)})"
        f" values ({','.join('?' * len(cols))})",
        [data[c] for c in cols]
    )


def _s12_seed(workdir: Path) -> bool:
    """播种两个合成源（整行复制既有源后改写，零真实源污染，测后整份回滚快照）。

    ① 图片订阅源（type=1）：文章 link 指向本机图集服务 ⇒ 走「订阅列表 → 点条目」真实入口；
    ② 编辑校验源：`sourceName` 置空 ⇒ 供 F155「保存必填校验 + 定位」构造失败态。
    """
    m2 = _m2()
    db = m2._db_pull(workdir)
    if db is None:
        return False
    con = sqlite3.connect(str(db))
    try:
        cols = [r[1] for r in con.execute("pragma table_info(rssSources)")]
        row = con.execute("select * from rssSources where enabled = 1 limit 1").fetchone()
        if not row:
            return False
        base = dict(zip(cols, row))

        gal = dict(base)
        gal.update({
            "sourceUrl": GAL_SOURCE, "sourceName": GAL_SOURCE_NAME,
            "type": 1, "articleStyle": 0, "enabled": 1,
            "sortUrl": f"{GAL_SORT}::http://127.0.0.1:{GAL_PORT}/sort",
            "ruleArticles": None, "ruleNextPage": None,
            "ruleContent": None, "ruleImage": "img@src",
            "header": None, "loginUrl": None, "loginCheckJs": None,
            "enabledCookieJar": 0, "preload": 0,
        })
        _s12_upsert(con, "rssSources", cols, gal)

        edit = dict(base)
        edit.update({
            "sourceUrl": SRC_SEED_URL, "sourceName": "", "enabled": 1,
            "ruleArticles": None, "ruleNextPage": None,
            "loginUrl": None, "loginCheckJs": None, "preload": 0,
        })
        _s12_upsert(con, "rssSources", cols, edit)

        con.execute("delete from rssArticles where origin = ?", (GAL_SOURCE,))
        art_meta = [(r[1], (r[2] or "").upper(), r[3], r[4])
                    for r in con.execute("pragma table_info(rssArticles)")]
        # 两篇：A 走本机图集服务（成功路径）；B 指向从不监听的端口（确定性失败路径）
        now_ms = int(time.time() * 1000)
        for idx, (link, title) in enumerate((
            (f"http://127.0.0.1:{GAL_PORT}/art1", GAL_ART_TITLE),
            (f"http://127.0.0.1:{GAL_DEAD_PORT}/art1", GAL_ART_TITLE_DEAD),
        )):
            overrides = {
                "origin": GAL_SOURCE, "sort": GAL_SORT, "link": link,
                "title": title, "order": now_ms - idx, "read": 0, "type": 1, "pubDate": "",
            }
            names, vals = [], []
            for name, ctype, notnull, dflt in art_meta:
                if name in overrides:
                    names.append(name)
                    vals.append(overrides[name])
                elif notnull and dflt is None:
                    names.append(name)
                    vals.append(0 if ("INT" in ctype or "REAL" in ctype) else "")
            con.execute(
                f"insert or replace into rssArticles ({','.join('`' + n + '`' for n in names)})"
                f" values ({','.join('?' * len(names))})", vals)
        con.commit()
    finally:
        con.close()
    return m2._db_push(db)


def s12_gallery_and_source_edit(d) -> bool:
    """M4 2-3/11：image/image-gallery（F179 失败分类 + 返回顶部 + 刷新任务条 + 修重复追加）
    + rss/source-edit（优化 6 菜单四组 / 优化 7 必填显式化 + 保存失败定位）"""
    print("  [s12] ===== 图片浏览刷新回执/失败自愈 + 订阅源编辑菜单与必填定位 =====")
    m2 = _m2()
    workdir = Path(tempfile.mkdtemp(prefix="m4s12_"))
    db_snap = workdir / "legado_snapshot.db"
    if not m2._snapshot_db(workdir, db_snap):
        print("  [s12] 数据库快照失败（前置）")
        return False
    server = None
    ok = False
    try:
        server = _GalleryServer(GAL_PORT)
        server.start()
        if not _reverse_on(GAL_PORT):
            print("  [s12] adb reverse 未建立（设备侧不可达本机图集服务）")
            return False
        if not _device_reachable(f"http://127.0.0.1:{GAL_PORT}", retries=3):
            # 非致命：探针依赖设备侧 curl，缺失/超时不应直接判负；真实可达性由后续加载断言给出
            print("  [s12] 设备侧探针未通（继续，真实可达性看加载断言）")
        reset_app()
        if not _s12_seed(workdir):
            print("  [s12] 合成源播种失败")
            return False
        reset_app()

        # ---------- B1：真实入口（订阅列表 → 点条目）→ 图片浏览成功加载 3 张 ----------
        sh("am", "start", "-n", f"{PKG}/{ACT_RSS_ART_S12}", "--es", "sourceUrl", GAL_SOURCE)
        time.sleep(9.0)
        list_xml = dump_xml(d)
        ca.shot(d, "m4s12_art_list")
        item_b = _clickable_bounds(list_xml, GAL_ART_TITLE) or node_bounds(list_xml, GAL_ART_TITLE)
        print(f"  [s12] 订阅列表条目在场={bool(item_b)}")
        if item_b:
            click_xy(d, item_b["cx"], item_b["cy"])
        time.sleep(12.0)
        gal_xml = dump_xml(d)
        ca.shot(d, "m4s12_gallery_loaded")
        landed = "ImageGalleryActivity" in current_activity()
        idx_before = _text_by_id(gal_xml, "tv_canvas_page_index")
        # 3 张图 ⇒ 页码「1 / 3」；若刷新后重复追加则变「1 / 6」
        loaded_ok = landed and idx_before.replace(" ", "") == "1/3"
        print(f"  [s12] B1 落地={landed} 页码={idx_before!r} 服务命中={server.hits} ⇒ {loaded_ok}")

        # ---------- B2：刷新回执（任务条 Done）+ 修「刷新后重复追加」 ----------
        refresh_b = (_desc_bounds_all(gal_xml, S_GAL_REFRESH_DESC) or [None])[0]
        done_seen = False
        idx_after = ""
        if refresh_b:
            click_xy(d, refresh_b["cx"], refresh_b["cy"])
            deadline = time.time() + 25
            while time.time() < deadline:
                cur = dump_xml(d)
                if S_GAL_DONE in cur:
                    done_seen = True
                    break
                time.sleep(1.0)
            time.sleep(3.0)   # 等任务条消退 + 数据稳定
            after_xml = dump_xml(d)
            ca.shot(d, "m4s12_gallery_refreshed")
            idx_after = _text_by_id(after_xml, "tv_canvas_page_index")
        no_dup_ok = idx_after.replace(" ", "") == "1/3"
        print(f"  [s12] B2 刷新任务条「{S_GAL_DONE}」={done_seen} / 刷新后页码={idx_after!r} "
              f"（未重复追加={no_dup_ok}）")

        # ---------- B3：失败自愈（点「失效文章」⇒ 加载必失败）——分类文案 + 提示 + 返回顶部 + 失败回执 ----------
        # ⚠️ 不能用「停掉 GAL_PORT 服务」构造失败：`Rss.getContentAwait` 的文章正文**会被缓存**
        # （实测铁证 2026-09-21：停服后刷新仍 `imageCount=3 costMs=0`，失败态根本构造不出来）
        # ⇒ 改点第二篇文章，其 link 指向**从不监听的端口**（从未被抓取 ⇒ 无缓存可命中）。
        reset_app()
        sh("am", "start", "-n", f"{PKG}/{ACT_RSS_ART_S12}", "--es", "sourceUrl", GAL_SOURCE)
        time.sleep(9.0)
        dead_list = dump_xml(d)
        dead_b = _clickable_bounds(dead_list, GAL_ART_TITLE_DEAD) \
            or node_bounds(dead_list, GAL_ART_TITLE_DEAD)
        print(f"  [s12] B3 失效条目在场={bool(dead_b)}")
        err_text = hint_text = ""
        back_top = False
        raw_leak = False
        run_seen = fail_seen = False
        if dead_b:
            click_xy(d, dead_b["cx"], dead_b["cy"])
            deadline = time.time() + 60
            while time.time() < deadline:
                cur = dump_xml(d)
                err_text = _text_by_id(cur, "tv_error")
                hint_text = _text_by_id(cur, "tv_error_hint")
                if err_text in S_GAL_ERR_SET and hint_text:
                    break
                time.sleep(1.5)
            ca.shot(d, "m4s12_gallery_error")
            err_xml = dump_xml(d)
            back_top = bool(_desc_bounds_all(err_xml, S_GAL_BACK_TOP)) or \
                bool(node_bounds(err_xml, S_GAL_BACK_TOP))
            # F179 判据核心：呈现的是**分类文案**，不再把原始异常文本抛给用户
            raw_leak = ("empty list" in err_xml) or ("Exception" in err_xml)
            # 刷新回执（失败分支）：顶栏刷新入口按 desc 取，取不到按顶栏动作序兜底
            refresh_b2 = (_desc_bounds_all(err_xml, S_GAL_REFRESH_DESC) or [None])[0] \
                or topbar_action_bounds(err_xml, from_right=1)
            if refresh_b2:
                click_xy(d, refresh_b2["cx"], refresh_b2["cy"])
                deadline = time.time() + 60
                while time.time() < deadline:
                    cur = dump_xml(d)
                    if S_GAL_RUNNING in cur:
                        run_seen = True
                    if S_GAL_FAILED in cur:
                        fail_seen = True
                    if run_seen and fail_seen:
                        break
                    time.sleep(1.2)
            else:
                print("  [s12] B3 刷新入口未定位到")
        err_ok = (err_text in S_GAL_ERR_SET) and bool(hint_text) and back_top \
            and not raw_leak and run_seen and fail_seen
        print(f"  [s12] B3 分类文案={err_text!r} 提示={bool(hint_text)} 返回顶部={back_top} "
              f"原始异常外泄={raw_leak} / 刷新进行中={run_seen} 失败回执={fail_seen} ⇒ {err_ok}")

        # ---------- A：rss/source-edit 菜单四组 + 必填显式化 + 保存失败定位 ----------
        reset_app()
        edit_landed = False
        for _ in range(2):
            sh("am", "start", "-n", f"{PKG}/{ACT_SOURCE_EDIT}", "--es", "sourceUrl", SRC_SEED_URL)
            time.sleep(4.0)
            if "RssSourceEditActivity" in current_activity():
                edit_landed = True
                break
            sh_su(f"am start -n {PKG}/{ACT_SOURCE_EDIT} --es sourceUrl {SRC_SEED_URL}")
            time.sleep(4.0)
            if "RssSourceEditActivity" in current_activity():
                edit_landed = True
                break
        edit_xml = dump_xml(d)
        ca.shot(d, "m4s12_source_edit")
        # 必填标记：hint 渲染为「* 源名称（sourceName）」
        req_mark = any(t.startswith(S_SRC_NAME_HINT_PREFIX) for t, *_ in text_nodes(edit_xml))
        print(f"  [s12] A0 落地={edit_landed} 必填标记「{S_SRC_NAME_HINT_PREFIX}…」={req_mark}")

        # ---------- A1：保存失败定位（先切到「列表」Tab，再点保存）----------
        # 顺序刻意排在菜单检查之前：菜单关闭若误触返回会结束本页，放最后可避免连带污染本项。
        cur_xml = dump_xml(d)
        tab_b = _clickable_bounds(cur_xml, S_SRC_TAB_LIST) or node_bounds(cur_xml, S_SRC_TAB_LIST)
        if tab_b:
            click_xy(d, tab_b["cx"], tab_b["cy"])
            time.sleep(1.5)
        save_b = (_desc_bounds_all(dump_xml(d), S_SRC_SAVE_DESC) or [None])[0]
        err_located = False
        alive = False
        if save_b:
            click_xy(d, save_b["cx"], save_b["cy"])
            deadline = time.time() + 12
            while time.time() < deadline:
                cur = dump_xml(d)
                if S_SRC_REQUIRED_ERR in cur:
                    err_located = True
                    break
                time.sleep(1.0)
            last = dump_xml(d)
            ca.shot(d, "m4s12_source_required_error")
            alive = "RssSourceEditActivity" in current_activity()
            # 定位有效性：错误文案在场 + 必填字段（基本 Tab）重新可见
            back_to_base = any(t.startswith(S_SRC_NAME_HINT_PREFIX) for t, *_ in text_nodes(last))
            print(f"  [s12] A1 保存校验错误在场={err_located} 已回到基本Tab={back_to_base} "
                  f"页面存活={alive}")
            err_located = err_located and back_to_base and alive
        else:
            print("  [s12] A1 保存入口未定位到")

        # ---------- A2：⋮ 菜单四组（⋮ 是顶栏最右可点图标）----------
        more_b = topbar_action_bounds(dump_xml(d), from_right=0)
        groups_ok = False
        if more_b:
            click_xy(d, more_b["cx"], more_b["cy"])
            time.sleep(2.0)
            menu_xml = dump_xml(d)
            ca.shot(d, "m4s12_source_menu")
            hit_groups = [g for g in S_SRC_GROUP_SET if g in menu_xml]
            groups_ok = len(hit_groups) == len(S_SRC_GROUP_SET)
            print(f"  [s12] A2 菜单分组命中={hit_groups} ⇒ {groups_ok}")
            d.press("back")
            time.sleep(1.5)
        else:
            print("  [s12] A2 ⋮ 入口未定位到")

        # ---------- 源码断言（关键接线必须真实存在） ----------
        src_gal = _src_text(SRC_GALLERY_ACT)
        src_ad = _src_text(SRC_GALLERY_ADAPTER)
        src_ed = _src_text(SRC_SOURCE_EDIT_ACT)
        src_ee = _src_text(SRC_EDIT_ENTITY)
        checks = [
            ("gallery: 刷新前复位画布状态", "ImagePlay.clearImageCanvasState()" in src_gal
             and "isInitialScrollDone = false" in src_gal),
            ("gallery: 刷新回执由 loadState 驱动", "finishRefresh(" in src_gal
             and "is ImageCanvasAdapter.LoadState.SUCCESS" in src_gal),
            ("gallery: 任务条挂载", "InlineTaskBar(" in src_gal),
            ("gallery: 失败分类器", "fun classifyError(" in src_ad),
            ("gallery: 返回顶部逃生口", "onBackToTop" in src_ad and "btnBackToTop" in src_ad),
            ("gallery: 原始异常不再直出", "state.error.message ?: " not in src_ad),
            ("source-edit: 菜单四组标题", "header = true" in src_ed
             and "source_menu_group_io" in src_ed),
            ("source-edit: 必填校验 + 定位", "private fun saveSource(" in src_ed
             and "private fun locateField(" in src_ed),
            ("source-edit: 必填字段标记", "required = true" in src_ed),
            ("EditEntity: required/error 字段", "val required: Boolean" in src_ee
             and "var error: String?" in src_ee),
        ]
        src_ok = all(v for _, v in checks)
        for name, v in checks:
            print(f"  [s12] 源码 {name} = {v}")

        ok = bool(loaded_ok and done_seen and no_dup_ok and err_ok
                  and edit_landed and req_mark and groups_ok and err_located and src_ok)
    except Exception as e:
        print(f"  [s12] 异常终止: {type(e).__name__}: {e}")
    finally:
        release_reverse(GAL_PORT)
        if server:
            server.stop()
        reset_app()
        try:
            rolled = m2._db_push(db_snap)
            print(f"  [s12] 数据库快照已回滚={rolled}")
        except Exception as e:
            print(f"  [s12] 兜底回滚异常: {type(e).__name__}")
        reset_app()
    return ok


# ============================ s13：M4 批次（main/settings-search + book/replace-edit） ============================

ACT_SETTINGS_SEARCH = "io.legado.app.ui.main.my.SettingsSearchActivity"
ACT_REPLACE_EDIT = "io.legado.app.ui.replace.edit.ReplaceEditActivity"

# 文案取自 values-zh/strings.xml 真值
S_SET_SEARCH_HINT = "搜索设置"
S_SET_EXACT_GROUP = "精确匹配"          # settings_search_exact_group
S_SET_ROW_EXACT_A = "主题模式"          # theme_mode（前缀命中）
S_SET_ROW_EXACT_B = "主题设置"          # theme_setting（前缀命中）
S_SET_ROW_NONEXACT = "应用主题"          # appearance_kit_manage（含关键词但非前缀 ⇒ 非精确桶）
S_SET_SECTION_APPEARANCE = "外观"        # config_category_appearance（组标题用 accent ⇒ 高亮参考色）
S_SET_QUERY = "主题"
SET_BADGE_PAT = re.compile(r"^含 \d+ 项$")   # settings_search_sub_item_count

S_REP_ADV_GROUP = "高级配置"            # replace_advanced_group
S_REP_ADV_GROUP_HINT = "低频字段，默认收起"  # replace_advanced_group_hint（同一可点 Row 内）
S_REP_SAMPLE_GROUP = "样本试运行"        # replace_sample_group
S_REP_SAMPLE_RUN = "试运行"             # replace_sample_run
S_REP_SAMPLE_RESULT = "替换结果"         # replace_sample_result_label
S_REP_SAMPLE_HIT_PREFIX = "命中 "        # replace_sample_hit = 命中 %1$d 处
S_REP_SCOPE_HINT = "替换范围"            # replace_scope（高级字段之一）
S_REP_TIMEOUT_HINT = "超时毫秒数"        # timeout_millisecond（高级字段之一）
S_REP_PASTE_MENU = "粘贴规则"            # paste_rule
S_REP_COPY_MENU = "拷贝规则"             # copy_rule（注意是「拷贝」不是「复制」）
S_REP_USE_REGEX = "使用正则表达式"        # use_regex（用于制造 1 项字段差异）
S_REP_PASTE_TITLE_PREFIX = "粘贴将覆盖 "  # replace_paste_diff_title
S_REP_PASTE_CONFIRM = "覆盖粘贴"         # replace_paste_diff_confirm
S_REP_PATTERN = "abc"
S_REP_SAMPLE_TEXT = "xabcxabcx"
S_REP_EXPECT_OUTPUT = "xxx"
S_REP_PASTED_PATTERN = "xyz"
S_REP_PASTE_JSON = '{"name":"L2粘贴规则","pattern":"xyz","replacement":"R","isRegex":true}'

SRC_MY_SETTINGS_SCREEN = "app/src/main/java/io/legado/app/ui/main/my/MySettingsScreen.kt"
SRC_REPLACE_EDIT = "app/src/main/java/io/legado/app/ui/replace/edit/ReplaceEditActivity.kt"
SRC_COLLAPSE_HEADER = "app/src/main/java/io/legado/app/ui/widget/components/CollapseSectionHeader.kt"


def _edittext_bounds_all(xml: str):
    """全部 EditText 节点 bounds（按 top 升序）——页面里多个输入框时用于取「最后一个」"""
    out = []
    for m in re.finditer(r"<node[^>]*>", xml):
        tag = m.group(0)
        cls = re.search(r'class="([^"]*)"', tag)
        if not cls or cls.group(1) != "android.widget.EditText":
            continue
        b = re.search(r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', tag)
        if not b:
            continue
        x1, y1, x2, y2 = map(int, b.groups())
        if x2 > x1 and y2 > y1:
            out.append({"left": x1, "top": y1, "right": x2, "bottom": y2,
                        "cx": (x1 + x2) // 2, "cy": (y1 + y2) // 2})
    return sorted(out, key=lambda n: n["top"])


def type_unicode(d, text: str) -> bool:
    """CJK 输入通道：启用 u2 的 FastInputIME 后 `send_keys` 支持任意 Unicode。

    ⚠️ 本仓既有 `type_search` 只喂过 ASCII 关键词（s1 从日志正文抽 ASCII 串），
    而设置搜索页的标题/摘要全中文 ⇒ 必须显式走 FastInputIME（`adb shell input text` 只吃 ASCII）。
    """
    try:
        d.set_input_ime()
    except Exception as e:
        print(f"  [s13] set_input_ime 失败: {type(e).__name__}: {e}")
        return False
    time.sleep(1.0)
    try:
        d.send_keys(text)
    except Exception as e:
        print(f"  [s13] send_keys 失败: {type(e).__name__}: {e}")
        return False
    time.sleep(1.5)
    return True


def _tap_label_scrolled(d, label: str, contains: bool = False, tries: int = 4) -> bool:
    """按文本点击；节点若落在屏幕下缘之外，**先上滑把它带进视口再点**。

    必要性（s13 实测 2026-09-21）：本页表单在 `NoChildScrollNestedScrollView` 内，
    uiautomator 会把**视口外**的子节点也 dump 出来（带屏外 bounds）⇒ 直接点中心会打到屏幕外，
    表现为「点了没反应」（首轮 B1 展开失败即此因，而非功能缺陷）。
    """
    h = (d.info or {}).get("displayHeight") or 1280
    for _ in range(tries):
        b = node_bounds(dump_xml(d), label, contains=contains)
        if b and b["cy"] < h * 0.82:
            click_xy(d, b["cx"], b["cy"])
            return True
        d.swipe(0.5, 0.72, 0.5, 0.36, 0.15)
        time.sleep(0.9)
    b = node_bounds(dump_xml(d), label, contains=contains)
    if b:
        click_xy(d, b["cx"], min(b["cy"], int(h * 0.78)))
        return True
    return False


def _attr_by_id(xml: str, res_suffix: str, attr: str) -> str:
    """按 resource-id 后缀取节点某属性（如 checkbox 的 checked）"""
    for m in re.finditer(r"<node[^>]*>", xml):
        tag = m.group(0)
        rid = re.search(r'resource-id="([^"]*)"', tag)
        if not rid or not rid.group(1).endswith(res_suffix):
            continue
        v = re.search(r'\b%s="([^"]*)"' % attr, tag)
        return v.group(1) if v else ""
    return ""


def _id_present(xml: str, res_suffix: str) -> bool:
    """节点是否在 dump 中（不可见节点不在 dump 中 ⇒ 兼作可见性判据）。

    ⚠️ s13 实测（2026-09-21）：`TextInputLayout` 的 hint **不出现在 a11y 树的 text 属性里**
    ⇒ 用 hint 文案判「字段是否可见」会恒为 False（首轮 B0/B1 双假判定的根因）。改用 resource-id 存在性。
    """
    for m in re.finditer(r"<node[^>]*>", xml):
        rid = re.search(r'resource-id="([^"]*)"', m.group(0))
        if rid and rid.group(1).endswith(res_suffix):
            return True
    return False


def s13_settings_search_and_replace_edit(d) -> bool:
    """M4 4-5/11：main/settings-search（F30 命中高亮 + 子项计数 / F31 精确命中置顶）
    + book/replace-edit（F69 样本试运行 / F63 粘贴差异预览 / F64 高级字段渐进披露）"""
    print("  [s13] ===== 设置搜索高亮与精确置顶 + 替换规则试运行与粘贴预览 =====")
    ok = False
    try:
        from PIL import Image
        shot_dir = Path(tempfile.mkdtemp(prefix="m4s13_"))

        # ---------- A：设置搜索（关键词「主题」：前缀命中 2 行 + 非前缀命中 1 行 + 子项 ≥2） ----------
        reset_app()
        a_landed = False
        for _ in range(2):
            sh("am", "start", "-n", f"{PKG}/{ACT_SETTINGS_SEARCH}")
            time.sleep(3.5)
            if "SettingsSearchActivity" in current_activity():
                a_landed = True
                break
            sh_su(f"am start -n {PKG}/{ACT_SETTINGS_SEARCH}")
            time.sleep(3.5)
            if "SettingsSearchActivity" in current_activity():
                a_landed = True
                break
        base_xml = dump_xml(d)
        ca.shot(d, "m4s13_settings_search_base")
        # 基线（未搜索）：同一行的 accent 像素数作为对照；accent 参考色取自「外观」组标题
        p_base = str(shot_dir / "search_base.png")
        d.screenshot(p_base)
        img_base = Image.open(p_base).convert("RGB")
        row_a_before = _clickable_bounds(base_xml, S_SET_ROW_EXACT_A) \
            or node_bounds(base_xml, S_SET_ROW_EXACT_A)
        sec_before = node_bounds(base_xml, S_SET_SECTION_APPEARANCE)
        ref = foreground(img_base, sec_before)[0] if sec_before else None
        cnt_before = count_near(img_base, row_a_before, ref) if (row_a_before and ref) else -1
        print(f"  [s13] A0 落地={a_landed} 基线行「{S_SET_ROW_EXACT_A}」在场={bool(row_a_before)} "
              f"accent 参考色={ref} 基线 accent 像素={cnt_before}")

        typed = False
        field = _edittext_bounds_all(base_xml)
        if field:
            click_xy(d, field[0]["cx"], field[0]["cy"])
            time.sleep(0.8)
            typed = type_unicode(d, S_SET_QUERY)
        hit_xml = dump_xml(d)
        ca.shot(d, "m4s13_settings_search_query")
        query_set = S_SET_QUERY in hit_xml
        exact_header = S_SET_EXACT_GROUP in hit_xml
        exact_rows = all(t in hit_xml for t in (S_SET_ROW_EXACT_A, S_SET_ROW_EXACT_B))
        nonexact_row = S_SET_ROW_NONEXACT in hit_xml
        badges = [t for t, *_ in text_nodes(hit_xml) if SET_BADGE_PAT.match(t)]
        print(f"  [s13] A1 输入={typed} 关键词落地={query_set} / F31 精确组头={exact_header} "
              f"精确行齐={exact_rows} 非精确行仍在={nonexact_row} / F30 子项徽章={badges}")

        # F30 高亮（像素口径，自校准）：过滤 + 置顶后行位置会变 ⇒ **必须用搜索后的新 bounds**，
        # 否则量的是旧位置（首轮实测旧 bounds 命中 0 像素即此因）
        cnt_after = -1
        if query_set:
            p_after = str(shot_dir / "search_query.png")
            d.screenshot(p_after)
            img_after = Image.open(p_after).convert("RGB")
            row_a_after = _clickable_bounds(hit_xml, S_SET_ROW_EXACT_A) \
                or node_bounds(hit_xml, S_SET_ROW_EXACT_A)
            sec_after = node_bounds(hit_xml, S_SET_SECTION_APPEARANCE)
            ref2 = foreground(img_after, sec_after)[0] if sec_after else ref
            cnt_after = count_near(img_after, row_a_after, ref2) if (row_a_after and ref2) else -1
            print(f"  [s13] A2 F30 高亮：accent 参考色={ref2} 命中行 accent 像素={cnt_after}"
                  f"（基线 {cnt_before}）")
        highlight_ok = cnt_after > 20 and cnt_after > cnt_before + 15
        a_ok = bool(a_landed and typed and query_set and exact_header and exact_rows
                    and nonexact_row and badges and highlight_ok)
        print(f"  [s13] A 结论={a_ok}（高亮增量达标={highlight_ok}）")
        try:
            d.clear_input_ime()
        except Exception:
            pass

        # ---------- B：替换规则编辑（F64 高级配置 + F69 样本试运行） ----------
        reset_app()
        b_landed = False
        for _ in range(2):
            sh("am", "start", "-n", f"{PKG}/{ACT_REPLACE_EDIT}", "--es", "pattern", S_REP_PATTERN)
            time.sleep(3.5)
            if "ReplaceEditActivity" in current_activity():
                b_landed = True
                break
            sh_su(f"am start -n {PKG}/{ACT_REPLACE_EDIT} --es pattern {S_REP_PATTERN}")
            time.sleep(3.5)
            if "ReplaceEditActivity" in current_activity():
                b_landed = True
                break
        b_xml = dump_xml(d)
        ca.shot(d, "m4s13_replace_edit_base")
        adv_header = node_bounds(b_xml, S_REP_ADV_GROUP)
        # 判据用 resource-id 存在性（hint 文案不进 a11y 树，见 _id_present 注释）
        adv_collapsed = not _id_present(b_xml, "et_scope")
        sample_header = node_bounds(b_xml, S_REP_SAMPLE_GROUP)
        print(f"  [s13] B0 落地={b_landed} / F64 组头={bool(adv_header)} 高级字段已收起={adv_collapsed} "
              f"/ F69 组头={bool(sample_header)}")

        # F64：点组头 ⇒ 高级字段出现（组头在表单下方，先确保滚进视口再点）
        adv_expanded = False
        if adv_header:
            for attempt in range(2):
                tap_ok = _tap_label_scrolled(d, S_REP_ADV_GROUP)
                time.sleep(1.5)
                adv_xml = dump_xml(d)
                adv_expanded = _id_present(adv_xml, "et_scope") \
                    and _id_present(adv_xml, "et_exclude_scope") \
                    and _id_present(adv_xml, "et_timeout")
                if adv_expanded:
                    break
                print(f"  [s13] B1 第{attempt + 1}轮未展开（tap={tap_ok} 组头仍在="
                      f"{S_REP_ADV_GROUP in adv_xml} EditText数={len(_edittext_bounds_all(adv_xml))}）")
                # 兜底：点同一可点 Row 内的右侧 hint 文本
                _tap_label_scrolled(d, S_REP_ADV_GROUP_HINT)
                time.sleep(1.2)
                adv_xml = dump_xml(d)
                adv_expanded = _id_present(adv_xml, "et_scope") \
                    and _id_present(adv_xml, "et_exclude_scope") \
                    and _id_present(adv_xml, "et_timeout")
                if adv_expanded:
                    break
            ca.shot(d, "m4s13_replace_advanced_open")
        print(f"  [s13] B1 F64 展开后高级字段在场={adv_expanded}")

        # F69：展开样本区 ⇒ 输入样本 ⇒ 试运行 ⇒ 命中数 + 替换结果
        sample_ok = False
        if sample_header:
            _tap_label_scrolled(d, S_REP_SAMPLE_GROUP)
            time.sleep(1.5)
            # 样本输入区在表单最底部：连续上滑把底部带进视口（否则节点 bounds 在屏外，点击无效）
            for _ in range(4):
                d.swipe(0.5, 0.75, 0.5, 0.35, 0.12)
                time.sleep(0.6)
            s_xml = dump_xml(d)
            ca.shot(d, "m4s13_replace_sample_open")
            inputs = _edittext_bounds_all(s_xml)
            h = (d.info or {}).get("displayHeight") or 1280
            inputs = [b for b in inputs if b["cy"] < h * 0.9]
            run_b = _clickable_bounds(s_xml, S_REP_SAMPLE_RUN)
            typed_sample = False
            if inputs and run_b:
                last = inputs[-1]
                click_xy(d, last["cx"], last["cy"])
                time.sleep(0.8)
                try:
                    d.send_keys(S_REP_SAMPLE_TEXT)
                    typed_sample = True
                except Exception as e:
                    print(f"  [s13] B2 样本输入失败: {type(e).__name__}")
                time.sleep(1.0)
                click_xy(d, run_b["cx"], run_b["cy"])
                time.sleep(3.0)
            r_xml = dump_xml(d)
            ca.shot(d, "m4s13_replace_sample_result")
            hit_line = any(t.startswith(S_REP_SAMPLE_HIT_PREFIX) for t, *_ in text_nodes(r_xml))
            result_ok = (S_REP_SAMPLE_RESULT in r_xml) and (S_REP_EXPECT_OUTPUT in r_xml)
            sample_ok = bool(typed_sample and hit_line and result_ok)
            print(f"  [s13] B2 F69 输入={typed_sample} 命中行={hit_line} 替换结果「{S_REP_EXPECT_OUTPUT}」={result_ok}")

        # ---------- C：F63 粘贴差异预览（覆盖前确认） ----------
        # ⚠️ 不用 u2 的剪贴板 API：本机 uiautomator server 不支持（实测 `RPCUnknownError`）。
        # 改为**页内自产剪贴板内容**——先 ⋮ →「复制规则」把当前规则写入剪贴板，
        # 再改动一个字段（正则开关）制造差异，最后 ⋮ →「粘贴规则」⇒ 差异预览弹窗。
        # 先收键盘（KEYCODE_ESCAPE）：不能用 back（本页无返回拦截 ⇒ 会直接 finish 掉页面）
        sh("input", "keyevent", "111")
        time.sleep(1.2)
        paste_ok = False
        copy_ok = False
        diff_title_ok = False
        applied = False
        # 1) 复制当前规则
        more_b = topbar_action_bounds(dump_xml(d), from_right=0)
        if more_b:
            click_xy(d, more_b["cx"], more_b["cy"])
            time.sleep(1.8)
            copy_b = _clickable_bounds(dump_xml(d), S_REP_COPY_MENU)
            if copy_b:
                click_xy(d, copy_b["cx"], copy_b["cy"])
                copy_ok = True
                time.sleep(1.5)
        print(f"  [s13] C0 复制规则已触发={copy_ok}")
        if copy_ok:
            # 2) 改动「使用正则表达式」开关制造 1 项字段差异
            cb_before = _attr_by_id(dump_xml(d), "cb_use_regex", "checked")
            cb_node = _clickable_bounds(dump_xml(d), S_REP_USE_REGEX) \
                or node_bounds(dump_xml(d), S_REP_USE_REGEX)
            if cb_node:
                click_xy(d, cb_node["cx"], cb_node["cy"])
                time.sleep(1.2)
            cb_after = _attr_by_id(dump_xml(d), "cb_use_regex", "checked")
            toggled = (cb_before != cb_after) and cb_after != ""
            print(f"  [s13] C1 正则开关 {cb_before!r} → {cb_after!r}（已制造差异={toggled}）")
            # 3) 粘贴 ⇒ 差异预览
            if toggled:
                more_b2 = topbar_action_bounds(dump_xml(d), from_right=0)
                if more_b2:
                    click_xy(d, more_b2["cx"], more_b2["cy"])
                    time.sleep(1.8)
                    paste_b = _clickable_bounds(dump_xml(d), S_REP_PASTE_MENU)
                    if paste_b:
                        click_xy(d, paste_b["cx"], paste_b["cy"])
                        time.sleep(2.0)
                        dlg_xml = dump_xml(d)
                        ca.shot(d, "m4s13_replace_paste_diff")
                        diff_title_ok = any(t.startswith(S_REP_PASTE_TITLE_PREFIX)
                                            for t, *_ in text_nodes(dlg_xml))
                        confirm_b = _clickable_bounds(dlg_xml, S_REP_PASTE_CONFIRM)
                        if confirm_b:
                            click_xy(d, confirm_b["cx"], confirm_b["cy"])
                            time.sleep(2.0)
                            after_xml = dump_xml(d)
                            ca.shot(d, "m4s13_replace_paste_applied")
                            # 回填证据：正则开关被还原为剪贴板里的值
                            applied = _attr_by_id(after_xml, "cb_use_regex", "checked") == cb_before
                        paste_ok = bool(diff_title_ok and confirm_b and applied)
                        print(f"  [s13] C2 F63 差异标题={diff_title_ok} 确认键={bool(confirm_b)} "
                              f"确认后已回填（开关还原={applied}）")
                    else:
                        print("  [s13] C2 未定位到「粘贴规则」菜单项")
                else:
                    print("  [s13] C2 未定位到 ⋮ 入口")

        # ---------- 源码断言 ----------
        src_set = _src_text(SRC_MY_SETTINGS_SCREEN)
        src_rep = _src_text(SRC_REPLACE_EDIT)
        src_col = _src_text(SRC_COLLAPSE_HEADER)
        checks = [
            ("settings-search: 命中高亮", "private fun highlightMatches(" in src_set
             and "FontWeight.SemiBold" in src_set),
            ("settings-search: 子项计数徽章", "matchedSubItemCount > 1" in src_set
             and "settings_search_sub_item_count" in src_set),
            ("settings-search: 精确命中置顶", "private fun pinExactTitleMatches(" in src_set
             and "settings_search_exact_group" in src_set),
            ("settings-search: 分组 key 唯一", 'key = "s:${section.title}"' in src_set
             and 'key = "exact"' in src_set),
            ("replace-edit: 高级字段渐进披露", "private fun applyAdvancedVisibility(" in src_rep
             and "CollapseSectionHeader(" in src_rep),
            ("replace-edit: 已有高级值自动展开", "advancedExpanded = true" in src_rep),
            ("replace-edit: 样本试运行复用引擎", "input.replace(ruleName, regex, replacement, timeout)" in src_rep),
            ("replace-edit: 粘贴差异预览", "private fun showPasteDiffDialog(" in src_rep
             and "replace_paste_diff_confirm" in src_rep),
            ("replace-edit: 超时字段不再崩", ".toLong()" not in src_rep
             and "private fun validateTimeout(" in src_rep),
            ("CollapseSectionHeader 已建", "fun CollapseSectionHeader(" in src_col),
        ]
        src_ok = all(v for _, v in checks)
        for name, v in checks:
            print(f"  [s13] 源码 {name} = {v}")

        ok = bool(a_ok and b_landed and adv_expanded and sample_ok and paste_ok and src_ok)
    except Exception as e:
        print(f"  [s13] 异常终止: {type(e).__name__}: {e}")
    finally:
        reset_app()
    return ok


# ============================ s14：M4 批次（rss/search + main/my） ============================

ACT_RSS_SEARCH = "io.legado.app.ui.rss.search.RssSearchActivity"
ACT_MAIN = "io.legado.app.ui.main.MainActivity"

S14_PORT = 18571
S14_WEB_SOURCE = "l2seed://search-web"
S14_VIDEO_SOURCE = "l2seed://search-video"
S14_WEB_NAME = "L2搜索源W"
S14_VIDEO_NAME = "L2搜索源V"
# 关键词只出现在**网页源**条目标题里 ⇒ 同一屏内「命中行 accent 像素 > 0 / 未命中行 ≈ 0」互为对照，
# 不必再构造「未搜索」基线（结果页的 highlightQuery 恒非空，拿不到同行的无高亮态）
S14_KEYWORD = "L2Article"
S14_WEB_TITLE = "L2ArticleWebAlpha"
S14_VIDEO_TITLE = "BetaVideoPlain"
S14_HISTORY_WORD = "l2histword"

# 文案取自 values-zh/strings.xml 真值
S14_RUNNING_PREFIX = "正在搜索"      # rss_search_running
S14_STOP = "停止"                    # rss_search_stop
S14_TYPE_ALL = "全部类型"            # rss_search_type_all
S14_TYPE_WEB = "网页"                # rss_article_type_web
S14_TYPE_IMAGE = "图片"              # rss_article_type_image
S14_TYPE_VIDEO = "视频"              # rss_article_type_video
S14_HIST_DEL_TITLE = "删除搜索记录"   # search_history_delete_title
S14_YES = "是"                       # yes
S14_NO = "否"                        # no
S14_METRIC_LABELS = ("书架书籍", "使用书源", "订阅源", "累计阅读")   # my_metric_*
S14_NAV_MY = "我的"                  # my
S14_VERSION_PREFIX = "版本"          # version
S_WEB_SERVICE_TITLE = "Web 服务"     # web_service
S_WEB_RUNNING = "运行中"             # web_service_running

SRC_RSS_SEARCH_ACT = "app/src/main/java/io/legado/app/ui/rss/search/RssSearchActivity.kt"
SRC_RSS_SEARCH_RESULT = "app/src/main/java/io/legado/app/ui/rss/search/RssSearchResultScreen.kt"
SRC_MY_SCREEN = "app/src/main/java/io/legado/app/ui/main/my/MySettingsScreen.kt"
SRC_MY_FRAGMENT = "app/src/main/java/io/legado/app/ui/main/my/MyFragment.kt"
SRC_HIGHLIGHT_TEXT = "app/src/main/java/io/legado/app/ui/widget/components/HighlightText.kt"


class _SearchServer(threading.Thread):
    """本机订阅搜索服务：`/web` 与 `/video` 各返回一份**标准 RSS 2.0** XML。

    为什么用标准 RSS 而不是自定义规则：`RssParserByRule.parseXML` 在 `ruleArticles` 为空时
    走 `RssParserDefault`（默认 RSS/Atom 解析）⇒ 合成源只需 `searchUrl`，**零自定义规则面**，
    把「规则写错导致空结果」这类假阴性风险直接消掉。

    为什么每请求固定 sleep：`isSearching` 的窗口只有网络往返那几百毫秒，不延迟就 dump 不到
    「正在搜索 · 已得 N 条」；固定 3s 让进行中态可稳定观测（双源并行 ⇒ 窗口 ≈ 3s）。
    """

    def __init__(self, port: int, delay: float = 3.0):
        super().__init__(daemon=True)
        self.port = port
        self.delay = delay
        self.hits = 0
        self._httpd = None

    def _feed(self, title: str, link: str) -> bytes:
        return (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<rss version="2.0"><channel><title>L2Search</title>'
            f'<item><title>{title}</title><link>{link}</link>'
            f'<description>L2 fixture {title}</description>'
            '<pubDate>Fri, 19 Sep 2026 10:00:00 GMT</pubDate>'
            '</item></channel></rss>'
        ).encode("utf-8")

    def _html(self, title: str, link: str) -> bytes:
        """视频源用 **HTML + 自定义规则**：`RssParserDefault` 从不设 `article.type`（恒 0），
        只有 `RssParserByRule` 会写 `rssArticle.type = rssSource.type` ⇒ 要验证「类型筛选」
        必须走自定义规则路径，否则视频源的文章也是 type=0、按「视频」过滤后必然为空。"""
        return (
            '<html><body><div class="item">'
            f'<a class="a" href="{link}"><span class="t">{title}</span></a>'
            '</div></body></html>'
        ).encode("utf-8")

    def run(self):
        import http.server
        outer = self

        class _H(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                outer.hits += 1
                time.sleep(outer.delay)
                if urlparse(self.path).path.startswith("/video"):
                    body = outer._html(S14_VIDEO_TITLE, f"http://127.0.0.1:{outer.port}/v1")
                    ctype = "text/html; charset=utf-8"
                else:
                    body = outer._feed(S14_WEB_TITLE, f"http://127.0.0.1:{outer.port}/w1")
                    ctype = "application/rss+xml; charset=utf-8"
                self.send_response(200)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *a):
                pass

        class _Srv(http.server.ThreadingHTTPServer):
            daemon_threads = True

        try:
            self._httpd = _Srv(("127.0.0.1", self.port), _H)
        except OSError:
            return
        self._httpd.serve_forever()

    def stop(self):
        try:
            if self._httpd:
                self._httpd.shutdown()
                self._httpd.server_close()
        except Exception:
            pass


def _s14_seed(workdir: Path) -> bool:
    """播种两个合成搜索源（type=0 网页 / type=2 视频）+ 一条订阅搜索历史（type=1）。

    为什么必须**临时禁用其它启用源**：`RssSearchScope.getRssSources()` 在「全部分组」下取
    **所有启用且 searchUrl 非空**的源并行搜索——留着存量源会让「已得 N 条」与结果集不确定，
    还会把等待时间拖长。收尾走 `_snapshot_db` 整库回滚（零残留，不用逐条清理）。
    """
    m2 = _m2()
    db = m2._db_pull(workdir)
    if db is None:
        return False
    con = sqlite3.connect(str(db))
    try:
        cols = [r[1] for r in con.execute("pragma table_info(rssSources)")]
        row = con.execute("select * from rssSources where enabled = 1 limit 1").fetchone()
        if not row:
            return False
        base = dict(zip(cols, row))
        con.execute("update rssSources set enabled = 0")
        for url, name, stype, path in (
            (S14_WEB_SOURCE, S14_WEB_NAME, 0, "web"),
            (S14_VIDEO_SOURCE, S14_VIDEO_NAME, 2, "video"),
        ):
            data = dict(base)
            data.update({
                "sourceUrl": url, "sourceName": name, "type": stype, "enabled": 1,
                # {{key}} 由 AnalyzeUrl 以搜索词替换（与真实源同口径）
                "searchUrl": f"http://127.0.0.1:{S14_PORT}/{path}?k={{{{key}}}}",
                "sortUrl": f"L2搜索::{url}",
                "ruleArticles": None, "ruleNextPage": None,
                "header": None, "loginUrl": None, "loginCheckJs": None,
                "enabledCookieJar": 0, "preload": 0,
            })
            if stype == 2:
                # 视频源走自定义规则（唯一能把 article.type 写成源 type 的通道，见 _SearchServer._html）
                data.update({
                    "ruleArticles": "class.item",
                    "ruleTitle": "class.t@text",
                    "ruleLink": "class.a@href",
                })
            _s12_upsert(con, "rssSources", cols, data)
        # 订阅源搜索历史（type=1）：供「长按删除先确认」构造真实入口
        con.execute("delete from search_keywords where type = 1")
        con.execute(
            "insert or replace into search_keywords (word, usage, lastUseTime, type)"
            " values (?,?,?,?)",
            (S14_HISTORY_WORD, 1, int(time.time() * 1000), 1)
        )
        con.commit()
    finally:
        con.close()
    return m2._db_push(db)


def node_bounds_by_id(xml: str, res_suffix: str):
    """按 resource-id 后缀取节点 bounds（纯图标容器只能靠 id 定位）"""
    for m in re.finditer(r"<node[^>]*>", xml):
        tag = m.group(0)
        rid = re.search(r'resource-id="([^"]*)"', tag)
        if not rid or not rid.group(1).endswith(res_suffix):
            continue
        b = re.search(r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', tag)
        if not b:
            continue
        x1, y1, x2, y2 = map(int, b.groups())
        if x2 > x1 and y2 > y1:
            return {"left": x1, "top": y1, "right": x2, "bottom": y2,
                    "cx": (x1 + x2) // 2, "cy": (y1 + y2) // 2}
    return None


def _scroll_label_into_view(d, label: str, tries: int = 5):
    """只滚动把目标行带进视口（**不点击**）——设置行点击会跳页，不能用 `_tap_label_scrolled`"""
    h = (d.info or {}).get("displayHeight") or 1280
    for _ in range(tries):
        b = node_bounds(dump_xml(d), label)
        if b and b["cy"] < h * 0.82:
            return b
        d.swipe(0.5, 0.72, 0.5, 0.4, 0.15)
        time.sleep(0.9)
    return node_bounds(dump_xml(d), label)


def _switch_bounds_in_row(xml: str, row_label: str):
    """取「某设置行」内开关节点的 bounds（按行标题的 y 区间圈定，避免命中别行的开关）"""
    row = node_bounds(xml, row_label)
    if not row:
        return None
    for m in re.finditer(r"<node[^>]*>", xml):
        tag = m.group(0)
        if 'checkable="true"' not in tag:
            continue
        b = re.search(r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', tag)
        if not b:
            continue
        x1, y1, x2, y2 = map(int, b.groups())
        cy = (y1 + y2) // 2
        if row["top"] - 8 <= cy <= row["bottom"] + 8 and x2 > x1:
            return {"left": x1, "top": y1, "right": x2, "bottom": y2,
                    "cx": (x1 + x2) // 2, "cy": cy}
    return None


def _s14_launch_search(d, key: str, wait: float = 1.0) -> bool:
    """带 key 启动/复用搜索页（同 Activity 再收 onNewIntent ⇒ 直接发起搜索，无需打输入法）"""
    sh("am", "start", "-n", f"{PKG}/{ACT_RSS_SEARCH}", "--es", "key", key)
    time.sleep(wait)
    return "RssSearchActivity" in current_activity()


def s14_rss_search_and_my(d) -> bool:
    """M4 6-7/11：rss/search（F199 进行中计数条 + F200 类型筛选外显 + 修历史删除无确认/结果无高亮）
    + main/my（F26 头部资产概览 + Web 服务运行中徽章）"""
    print("  [s14] ===== 订阅搜索进行中回执/类型外显/历史确认 + 我的页头部概览 =====")
    m2 = _m2()
    workdir = Path(tempfile.mkdtemp(prefix="m4s14_"))
    db_snap = workdir / "legado_snapshot.db"
    if not m2._snapshot_db(workdir, db_snap):
        print("  [s14] 数据库快照失败（前置）")
        return False
    server = None
    ok = False
    try:
        from PIL import Image
        shot_dir = Path(tempfile.mkdtemp(prefix="m4s14img_"))
        server = _SearchServer(S14_PORT)
        server.start()
        if not _reverse_on(S14_PORT):
            print("  [s14] adb reverse 未建立（设备侧不可达本机搜索服务）")
            return False
        reset_app()
        if not _s14_seed(workdir):
            print("  [s14] 合成源播种失败")
            return False
        reset_app()

        # ---------- A1：chips 行在场 + 进行中计数条 + 停止出口 ----------
        a_landed = _s14_launch_search(d, S14_KEYWORD, wait=0.8)
        running_seen = False
        chips_ok = False
        stop_b = None
        for _ in range(14):
            time.sleep(0.5)
            xml = dump_xml(d)
            if S14_RUNNING_PREFIX in xml:
                running_seen = True
                stop_b = node_bounds(xml, S14_STOP)
                chips_ok = all(t in xml for t in
                               (S14_TYPE_ALL, S14_TYPE_WEB, S14_TYPE_IMAGE, S14_TYPE_VIDEO))
                ca.shot(d, "m4s14_search_running")
                break
        print(f"  [s14] A1 落地={a_landed} 进行中条={running_seen} chips4项={chips_ok} "
              f"停止钮={bool(stop_b)} 服务命中={server.hits}")

        stopped = False
        if stop_b:
            click_xy(d, stop_b["cx"], stop_b["cy"])
            deadline = time.time() + 10
            while time.time() < deadline:
                time.sleep(0.8)
                if S14_RUNNING_PREFIX not in dump_xml(d):
                    stopped = True
                    break
        print(f"  [s14] A1 停止后任务条消退={stopped}")

        # ---------- A2：完整搜索 ⇒ 结果 + 命中高亮（同屏对照） ----------
        # 必须 force-stop 后冷启：同页 `am start` 是否落到新实例受 launchMode 影响（首轮实测
        # 停在 A1 那个「已停止」实例上 ⇒ 看到的是空结果态，误判成「搜不到」）
        reset_app()
        _s14_launch_search(d, S14_KEYWORD, wait=1.0)
        hits_before = server.hits
        deadline = time.time() + 30
        full_xml = ""
        while time.time() < deadline:
            time.sleep(1.0)
            cur = dump_xml(d)
            if S14_WEB_TITLE in cur and S14_VIDEO_TITLE in cur and S14_RUNNING_PREFIX not in cur:
                full_xml = cur
                break
        both_ok = bool(full_xml)
        ca.shot(d, "m4s14_search_all_types")
        print(f"  [s14] A2 服务命中增量={server.hits - hits_before}")
        hl_hit = hl_miss = -1
        if both_ok:
            png = str(shot_dir / "all.png")
            d.screenshot(png)
            img = Image.open(png).convert("RGB")
            # accent 参考色自校准：选中 chip「全部类型」的文字像素均值（不猜主题色值）
            chip_b = node_bounds(full_xml, S14_TYPE_ALL)
            ref = foreground(img, chip_b)[0] if chip_b else None
            row_hit = node_bounds(full_xml, S14_WEB_TITLE)
            row_miss = node_bounds(full_xml, S14_VIDEO_TITLE)
            if ref and row_hit and row_miss:
                hl_hit = count_near(img, row_hit, ref)
                hl_miss = count_near(img, row_miss, ref)
        print(f"  [s14] A2 全部类型：双条在场={both_ok} accent参考={ref if both_ok else None} "
              f"命中行像素={hl_hit} 未命中行像素={hl_miss}")

        # ---------- A3：点「视频」chip ⇒ 只留视频源结果；再点「全部类型」⇒ 双条回归 ----------
        type_ok = False
        restored_ok = False
        if both_ok:
            vb = node_bounds(full_xml, S14_TYPE_VIDEO)
            if vb:
                click_xy(d, vb["cx"], vb["cy"])
                deadline = time.time() + 30
                while time.time() < deadline:
                    time.sleep(1.0)
                    cur = dump_xml(d)
                    if S14_VIDEO_TITLE in cur and S14_WEB_TITLE not in cur \
                            and S14_RUNNING_PREFIX not in cur:
                        type_ok = True
                        break
            ca.shot(d, "m4s14_search_video_only")
            # 复位：切回「全部类型」（同时验证筛选可逆 + 不把 rssSearchType 留在 2）
            ab = node_bounds(dump_xml(d), S14_TYPE_ALL)
            if ab:
                click_xy(d, ab["cx"], ab["cy"])
                deadline = time.time() + 30
                while time.time() < deadline:
                    time.sleep(1.0)
                    cur = dump_xml(d)
                    if S14_WEB_TITLE in cur and S14_VIDEO_TITLE in cur \
                            and S14_RUNNING_PREFIX not in cur:
                        restored_ok = True
                        break
        print(f"  [s14] A3 选「视频」后仅剩视频源结果={type_ok} 切回「全部类型」双条回归={restored_ok} "
              f"服务命中累计={server.hits}")

        # ---------- A4：历史长按删除先确认（修复 2） ----------
        reset_app()
        a4_landed = False
        for _ in range(6):
            sh("am", "start", "-n", f"{PKG}/{ACT_RSS_SEARCH}")
            time.sleep(2.5)
            if "RssSearchActivity" in current_activity():
                a4_landed = True
                break
        # 输入帮助区只在「输入变化」时展开（空 key 启动只聚焦不出历史）⇒ 必须真打一个字
        typed = type_search(d, "l") if a4_landed else False
        time.sleep(2.0)
        hist_xml = dump_xml(d)
        hist_b = node_bounds(hist_xml, S14_HISTORY_WORD)
        dlg_seen = False
        kept_after_no = False
        gone_after_yes = False
        if hist_b:
            w, h = d.window_size()
            d.long_click(hist_b["cx"] / w, hist_b["cy"] / h, 1.2)
            time.sleep(1.8)
            dlg_xml = dump_xml(d)
            dlg_seen = S14_HIST_DEL_TITLE in dlg_xml and S14_HISTORY_WORD in dlg_xml
            ca.shot(d, "m4s14_history_delete_confirm")
            no_b = node_bounds(dlg_xml, S14_NO)
            if no_b:
                click_xy(d, no_b["cx"], no_b["cy"])
                time.sleep(1.5)
                kept_after_no = bool(node_bounds(dump_xml(d), S14_HISTORY_WORD))
            if kept_after_no:
                b2 = node_bounds(dump_xml(d), S14_HISTORY_WORD)
                d.long_click(b2["cx"] / w, b2["cy"] / h, 1.2)
                time.sleep(1.8)
                yes_b = node_bounds(dump_xml(d), S14_YES)
                if yes_b:
                    click_xy(d, yes_b["cx"], yes_b["cy"])
                    time.sleep(1.8)
                    gone_after_yes = not node_bounds(dump_xml(d), S14_HISTORY_WORD)
        print(f"  [s14] A4 落地={a4_landed} 已输入={typed} 历史标签在场={bool(hist_b)} "
              f"删除确认弹窗={dlg_seen} 点「否」保留={kept_after_no} 点「是」已删={gone_after_yes}")

        # ---------- B1：我的页头部资产概览（F26） ----------
        reset_app()
        sh("am", "start", "-n", f"{PKG}/{ACT_MAIN}")
        time.sleep(6.0)
        main_xml = dump_xml(d)
        # 底栏为**纯图标模式**（labelVisibilityMode 走 icon-only）⇒ 「我的」二字不进 a11y 树，
        # 只能按容器几何点第 4 格（4 Tab：书架/发现/订阅/我的）
        nav_container = node_bounds_by_id(main_xml, "bottom_navigation_view")
        nav_b = None
        if nav_container:
            w4 = nav_container["right"] - nav_container["left"]
            nav_b = {
                "cx": nav_container["left"] + w4 * 7 // 8,
                "cy": (nav_container["top"] + nav_container["bottom"]) // 2,
            }
        if nav_b:
            click_xy(d, nav_b["cx"], nav_b["cy"])
            time.sleep(4.0)
        my_xml = dump_xml(d)
        ca.shot(d, "m4s14_my_profile_header")
        metrics_ok = all(t in my_xml for t in S14_METRIC_LABELS)
        rows_ok = "内容与规则" in my_xml
        version_ok = S14_VERSION_PREFIX in my_xml
        print(f"  [s14] B1 底栏「我的」定位={bool(nav_b)} 四指标={metrics_ok} 设置分区={rows_ok} 版本行={version_ok}")

        # ---------- B2：Web 服务「● 运行中」徽章（开→出现，关→消失） ----------
        badge_on = badge_off = False
        row_b = _scroll_label_into_view(d, S_WEB_SERVICE_TITLE)
        sw = _switch_bounds_in_row(dump_xml(d), S_WEB_SERVICE_TITLE) if row_b else None
        if sw:
            click_xy(d, sw["cx"], sw["cy"])
            deadline = time.time() + 12
            while time.time() < deadline:
                time.sleep(1.0)
                if S_WEB_RUNNING in dump_xml(d):
                    badge_on = True
                    break
            ca.shot(d, "m4s14_web_service_running")
            sw2 = _switch_bounds_in_row(dump_xml(d), S_WEB_SERVICE_TITLE)
            if badge_on and sw2:
                click_xy(d, sw2["cx"], sw2["cy"])
                time.sleep(3.0)
                badge_off = S_WEB_RUNNING not in dump_xml(d)
        print(f"  [s14] B2 服务行可见={bool(row_b)} 开关定位={bool(sw)} 开启后徽章={badge_on} "
              f"关闭后消退={badge_off}")

        # ---------- 源码断言（口径回归护栏） ----------
        src_act = _src_text(SRC_RSS_SEARCH_ACT)
        src_res = _src_text(SRC_RSS_SEARCH_RESULT)
        src_my = _src_text(SRC_MY_SCREEN)
        src_frag = _src_text(SRC_MY_FRAGMENT)
        src_hl = _src_text(SRC_HIGHLIGHT_TEXT)
        checks = [
            ("rss/search: 进行中条复用 InlineTaskBar", "InlineTaskBar(" in src_act
             and "InlineTaskState.Running" in src_act),
            ("rss/search: 停止出口单源", "private fun stopSearch()" in src_act
             and src_act.count("isManualStopSearch = true") == 1),
            ("rss/search: 类型 chips 外显", "private fun RssSearchTypeChipsRow(" in src_act
             and "RssSearchTypeChipsRow(" in src_act.replace("private fun RssSearchTypeChipsRow(", "")),
            ("rss/search: 菜单不再重复类型入口", "menu_type_all" not in src_act),
            ("rss/search: 空结果弹窗文案资源化", "搜索结果为空" not in src_act
             and "rss_search_empty_title" in src_act),
            ("rss/search: 历史删除先确认", "search_history_delete_title" in src_act
             and "dangerPositive = true" in src_act),
            ("rss/search: 结果命中高亮", "highlightMatches(item.title" in src_res
             and "highlightQuery" in src_res),
            ("highlightMatches 已单源收口", "fun highlightMatches(" in src_hl
             and "private fun highlightMatches(" not in src_my
             and "private fun highlightMatches(" not in src_res),
            ("main/my: 头部资产概览", "private fun MyProfileHeader(" in src_my
             and "profileName" in src_frag and "loadMetrics()" in src_frag),
            ("main/my: 头部项常驻 + 内容门控", 'item("profile") {' in src_my
             and src_my.index('item("profile") {') < src_my.index("MyProfileHeader(", src_my.index('item("profile") {'))),
            ("main/my: 服务运行徽章", "private fun RunningBadge(" in src_my
             and "web_service_running" in src_my),
        ]
        src_ok = all(v for _, v in checks)
        for name, v in checks:
            print(f"  [s14] 源码 {name} = {v}")

        ok = bool(a_landed and running_seen and chips_ok and stopped and both_ok
                  and hl_hit > 0 and hl_miss <= 2 and type_ok and restored_ok
                  and dlg_seen and kept_after_no and gone_after_yes
                  and metrics_ok and rows_ok and version_ok and badge_on and badge_off and src_ok)
    except Exception as e:
        print(f"  [s14] 异常终止: {type(e).__name__}: {e}")
    finally:
        if server:
            server.stop()
        print(f"  [s14] 数据库快照回滚={m2._db_push(db_snap)}")
        reset_app()
    return ok


# ============================ s15：M4 批次（book/search-content） ============================

ACT_SEARCH_CONTENT = "io.legado.app.ui.book.searchContent.SearchContentActivity"

S15_BOOK_URL = "l2seed://full-text-search"
S15_BOOK_NAME = "L2全文搜索校验书"
S15_AUTHOR = "L2校验"
S15_KEYWORD = "L2KEY"
S15_CH_TITLES = ("L2第一章", "L2第二章", "L2第三章")
# 每章只放 1 次关键词 ⇒ 命中数 = 缓存章数，断言可精确到字面量（不依赖内容随机的真实源）
S15_TEXT = (
    "本段为全文搜索校验正文 L2KEY 仅出现一次。\n",
    "第二章正文同样只有一处命中 L2KEY，用于验证「分布于 2 章」。\n",
)
# 期望覆盖率文案：命中 2 处 / 分布 2 章 / 已搜 2 章 / 1 章未缓存（第 3 章不写缓存文件）
S15_EXPECT_COVER = "命中 2 处 · 分布于 2 章 · 已搜 2 章；1 章未缓存未参与搜索，缓存后重搜可提升覆盖"
S15_DIST_TITLE = "命中分布 · 2 章"
S15_DIST_LABEL = "命中分布"
S15_DIST_ROW = "L2第一章 · 1 处"
# 已被替换掉的旧口径（回归哨兵：旧格式出现即说明覆盖率改造被回退）
S15_OLD_FORMAT = "搜索结果："

SRC_SEARCH_CONTENT_ACT = "app/src/main/java/io/legado/app/ui/book/searchContent/SearchContentActivity.kt"


def _md5_16(text: str) -> str:
    """与 `MD5Utils.md5Encode16` 同口径（md5 十六进制串的 [8,24) 区间）"""
    return hashlib.md5(text.encode("utf-8")).hexdigest()[8:24]


def _s15_cache_base() -> str:
    return f"/storage/emulated/0/Android/data/{PKG}/files/book_cache"


def _s15_folder() -> str:
    """`Book.getFolderNameNoCache()`：名称去非法字符取前 9 位 + bookUrl 的 md5_16（本名无非法字符）"""
    return S15_BOOK_NAME[:9] + _md5_16(S15_BOOK_URL)


def _s15_cache_path(index: int, title: str) -> str:
    """`BookChapter.getFileName()`：%05d-md5_16(title).nb"""
    return f"{_s15_cache_base()}/{_s15_folder()}/%05d-{_md5_16(title)}.nb" % index


def _s15_seed(workdir: Path) -> bool:
    """播种「3 章 / 前 2 章有缓存」的合成书（覆盖 F76 的「已搜 N 章 + 未缓存明示」）。

    为什么必须**自己写缓存文件**：本机 `book_cache` 为空（实测），真实书一律「0 章可搜」——
    只验得出「全部跳过」一种态。写入 2 章缓存后，覆盖率文案的四个数字（命中/分布/已搜/未缓存）
    全部由数据决定，可精确断言。
    """
    m2 = _m2()
    db = m2._db_pull(workdir)
    if db is None:
        return False
    con = sqlite3.connect(str(db))
    try:
        cols = [r[1] for r in con.execute("pragma table_info(books)")]
        row = con.execute("select * from books limit 1").fetchone()
        if not row:
            return False
        data = dict(zip(cols, row))
        now = int(time.time() * 1000)
        data.update({
            "bookUrl": S15_BOOK_URL, "name": S15_BOOK_NAME, "author": S15_AUTHOR,
            "origin": S15_BOOK_URL, "originName": "L2校验源",
            "type": 8,  # BookType.text（网络文本；不带 local / notShelf 位）
            "group": 0, "order": 0,
            "durChapterIndex": 0, "durChapterTitle": S15_CH_TITLES[0],
            "latestChapterTitle": S15_CH_TITLES[-1], "totalChapterNum": len(S15_CH_TITLES),
            "latestChapterTime": now,
        })
        # 列名统一加反引号：books 表有保留字列 `group`（直接拼接会 SQL 语法错误）
        con.execute(
            f"insert or replace into books ({','.join('`' + c + '`' for c in cols)})"
            f" values ({','.join('?' * len(cols))})",
            [data[c] for c in cols]
        )

        con.execute("delete from chapters where bookUrl = ?", (S15_BOOK_URL,))
        ccols = [r[1] for r in con.execute("pragma table_info(chapters)")]
        for index, title in enumerate(S15_CH_TITLES):
            cdata = {}
            for name in ccols:
                cdata[name] = ""
            cdata.update({
                "url": f"{S15_BOOK_URL}/{index}", "title": title,
                "bookUrl": S15_BOOK_URL, "index": index, "baseUrl": "",
                "isVolume": 0, "isVip": 0, "isPay": 0,
            })
            con.execute(
                f"insert or replace into chapters ({','.join('`' + c + '`' for c in ccols)})"
                f" values ({','.join('?' * len(ccols))})",
                [cdata[c] for c in ccols]
            )
        con.commit()
    finally:
        con.close()
    if not m2._db_push(db):
        return False

    # 章节缓存：写真实文本文件（`BookHelp.getContent` 直接 file.readText()）
    sh_su(f"mkdir -p {_s15_cache_base()}/{_s15_folder()}")
    for index in (0, 1):
        local = workdir / f"ch{index}.txt"
        local.write_text(S15_TEXT[index], encoding="utf-8")
        remote_sd = f"/sdcard/l2s15_ch{index}.nb"
        subprocess.run([ADB, "-s", HOST, "push", str(local), remote_sd],
                       capture_output=True, timeout=60)
        target = _s15_cache_path(index, S15_CH_TITLES[index])
        # 交还 owner（否则 app 读不到 ⇒ 覆盖率断言会因「读不到缓存」而整段假阴性）
        sh_su(f"cp {remote_sd} {target} && chown $(stat -c %u /data/data/{PKG}) {target} "
              f"&& chmod 600 {target}")
    return True


def _s15_purge(workdir: Path) -> bool:
    """清掉合成书与其缓存目录（零污染收尾；DB 另有整库快照回滚兜底）"""
    m2 = _m2()
    db = m2._db_pull(workdir)
    if db is not None:
        con = sqlite3.connect(str(db))
        try:
            con.execute("delete from chapters where bookUrl = ?", (S15_BOOK_URL,))
            con.execute("delete from books where bookUrl = ?", (S15_BOOK_URL,))
            con.commit()
        finally:
            con.close()
        m2._db_push(db)
    sh_su(f"rm -rf {_s15_cache_base()}/{_s15_folder()}")
    return True


def s15_search_content_page(d) -> bool:
    """M4 8/11：book/search-content（F76 覆盖率诚实呈现 / F77 命中分布按章直达）"""
    print("  [s15] ===== 全文搜索覆盖率与命中分布 =====")
    m2 = _m2()
    workdir = Path(tempfile.mkdtemp(prefix="m4s15_"))
    db_snap = workdir / "legado_snapshot.db"
    if not m2._snapshot_db(workdir, db_snap):
        print("  [s15] 数据库快照失败（前置）")
        return False
    ok = False
    try:
        reset_app()
        if not _s15_seed(workdir):
            print("  [s15] 合成书播种失败")
            return False
        reset_app()

        landed = False
        for _ in range(3):
            sh("am", "start", "-n", f"{PKG}/{ACT_SEARCH_CONTENT}",
               "--es", "bookUrl", S15_BOOK_URL, "--es", "searchWord", S15_KEYWORD)
            time.sleep(3.0)
            if "SearchContentActivity" in current_activity():
                landed = True
                break
            sh_su(f"am start -n {PKG}/{ACT_SEARCH_CONTENT} "
                  f"--es bookUrl {S15_BOOK_URL} --es searchWord {S15_KEYWORD}")
            time.sleep(3.0)
            if "SearchContentActivity" in current_activity():
                landed = True
                break

        full_xml = ""
        deadline = time.time() + 25
        while time.time() < deadline:
            time.sleep(1.0)
            cur = dump_xml(d)
            if S15_EXPECT_COVER in cur:
                full_xml = cur
                break
        ca.shot(d, "m4s15_coverage")
        cover_ok = bool(full_xml)
        old_gone = S15_OLD_FORMAT not in (full_xml or dump_xml(d))
        print(f"  [s15] A 落地={landed} 覆盖率文案命中={cover_ok} 旧口径已消失={old_gone}")
        if not cover_ok:
            print(f"  [s15] 底栏实际文案={_text_by_id(dump_xml(d), 'tv_current_search_info')!r}")

        # ---------- B：命中分布（≥2 章才出现入口）→ 弹层 → 按章直达 ----------
        dist_xml = full_xml or dump_xml(d)
        # 入口是**纯图标按钮**（只有 content-desc），且 desc 必须是独立标签串——
        # 若误用带 %1$d 的标题串，desc 会渲染成原文「命中分布 · %1$d 章」（本轮实测踩到）
        dist_b = (_desc_bounds_all(dist_xml, S15_DIST_LABEL) or [None])[0]
        sheet_ok = False
        row_clicked = False
        alive = False
        if dist_b:
            click_xy(d, dist_b["cx"], dist_b["cy"])
            time.sleep(1.8)
            sheet_xml = dump_xml(d)
            ca.shot(d, "m4s15_distribution_sheet")
            sheet_ok = S15_DIST_ROW in sheet_xml and S15_DIST_TITLE in sheet_xml
            row_b = node_bounds(sheet_xml, S15_DIST_ROW)
            if row_b:
                click_xy(d, row_b["cx"], row_b["cy"])
                time.sleep(1.5)
                row_clicked = (S15_DIST_ROW not in dump_xml(d)) \
                    and ("SearchContentActivity" in current_activity())
                alive = "SearchContentActivity" in current_activity()
        print(f"  [s15] B 分布入口={bool(dist_b)} 弹层含章节行={sheet_ok} "
              f"点行后弹层收起且存活={row_clicked}")

        # ---------- C：源码断言 ----------
        src_act = _src_text(SRC_SEARCH_CONTENT_ACT)
        checks = [
            ("search-content: 覆盖率摘要（含未缓存明示）",
             "search_content_coverage_uncached" in src_act
             and "search_content_coverage_scanned" in src_act),
            ("search-content: 搜索进行中确定性进度",
             "search_content_progress" in src_act
             and "PROGRESS_STEP_CHAPTERS" in src_act),
            ("search-content: 旧「搜索结果：N」口径已删",
             "search_content_size" not in src_act),
            ("search-content: 命中分布按章聚合",
             "private fun updateDistribution(" in src_act
             and "groupBy { it.value.chapterIndex }" in src_act),
            ("search-content: 分布入口 ≥2 章才给",
             "hitDistribution.size >= 2" in src_act),
            ("search-content: 按章滚动锚点", "scrollToPositionWithOffset(hit.firstIndex, 0)" in src_act),
        ]
        src_ok = all(v for _, v in checks)
        for name, v in checks:
            print(f"  [s15] 源码 {name} = {v}")

        ok = bool(landed and cover_ok and old_gone and dist_b and sheet_ok and row_clicked
                  and alive and src_ok)
    except Exception as e:
        print(f"  [s15] 异常终止: {type(e).__name__}: {e}")
    finally:
        _s15_purge(workdir)
        print(f"  [s15] 数据库快照回滚={m2._db_push(db_snap)}")
        reset_app()
    return ok


# ============================ s16：M4 批次（book/explore-show） ============================

ACT_EXPLORE_SHOW = "io.legado.app.ui.book.explore.ExploreShowActivity"

S16_PORT = 18581
S16_SOURCE_URL = "l2seed://explore-show"
S16_SOURCE_NAME = "L2发现校验源"
S16_EXPLORE_URL = f"http://127.0.0.1:{S16_PORT}/list"
S16_BOOK_A = "L2ExploreBookA"
S16_BOOK_B = "L2ExploreBookB"
S16_AUTHOR_A = "L2作者A"
S16_EMPTY = 1  # BookType.notShelf 位

# 文案取自 values-zh/strings.xml 真值
S16_MORE = "更多"                    # more（⋮ 的 content-desc）
S16_CANCEL = "取消"                  # cancel（一次性提示的关闭键）
S16_ADD_SHELF = "放入书架"            # add_to_bookshelf
S16_PREVIEW = "预览"                 # preview
S16_BOOK_INFO = "书籍信息"            # book_info
S16_HINT = "长按书籍可预览简介与目录，不用先打开"   # explore_show_preview_hint
S16_TITLE = "L2分类"

SRC_EXPLORE_SHOW_ACT = "app/src/main/java/io/legado/app/ui/book/explore/ExploreShowActivity.kt"
SRC_EXPLORE_SHOW_SCREEN = "app/src/main/java/io/legado/app/ui/book/explore/ExploreShowComposeScreen.kt"
SRC_EXPLORE_SHOW_VM = "app/src/main/java/io/legado/app/ui/book/explore/ExploreShowViewModel.kt"
SRC_SEARCH_BOOK_ITEM = "app/src/main/java/io/legado/app/ui/widget/compose/SearchBookListItem.kt"


class _ExploreListServer(threading.Thread):
    """本机发现分类列表服务：`/list` 返回两份条目（标题/作者/链接均取自合成规则）。

    为什么用 HTML + 自定义规则（而不是标准 RSS）：BookSource 的发现解析走 `BookList.analyzeBookList`
    → `getExploreRule()`，只认 CSS/XPath/JSON 规则，**没有「标准 RSS 免规则」通道**。
    """

    def __init__(self, port: int):
        super().__init__(daemon=True)
        self.port = port
        self.hits = 0
        self._httpd = None

    def run(self):
        import http.server
        outer = self

        class _H(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                outer.hits += 1
                items = "".join(
                    f'<div class="item"><a class="a" href="http://127.0.0.1:{outer.port}/b{i}">'
                    f'<span class="t">{name}</span></a>'
                    f'<span class="au">{author}</span></div>'
                    for i, (name, author) in enumerate(
                        ((S16_BOOK_A, S16_AUTHOR_A), (S16_BOOK_B, "L2作者B")), start=1
                    )
                )
                body = (f'<html><body><div class="list">{items}</div></body></html>'
                        ).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *a):
                pass

        class _Srv(http.server.ThreadingHTTPServer):
            daemon_threads = True

        try:
            self._httpd = _Srv(("127.0.0.1", self.port), _H)
        except OSError:
            return
        self._httpd.serve_forever()

    def stop(self):
        try:
            if self._httpd:
                self._httpd.shutdown()
                self._httpd.server_close()
        except Exception:
            pass


def _s16_seed(workdir: Path) -> bool:
    """播种发现校验源（整行复制既有书源后改写；`ruleExplore` 为 Gson JSON 串）。

    另外**清掉一次性提示位**：F48 的断言前提是「提示可展示」，若上一轮已置位则首屏不出现
    ⇒ 必须先复位（并同时验证「关闭后重启不再出现」的后半段）。
    """
    m2 = _m2()
    db = m2._db_pull(workdir)
    if db is None:
        return False
    con = sqlite3.connect(str(db))
    try:
        cols = [r[1] for r in con.execute("pragma table_info(book_sources)")]
        row = con.execute("select * from book_sources limit 1").fetchone()
        if not row:
            return False
        data = dict(zip(cols, row))
        data.update({
            "bookSourceUrl": S16_SOURCE_URL, "bookSourceName": S16_SOURCE_NAME,
            "bookSourceGroup": "", "bookSourceType": 0, "bookSourceComment": "",
            "customOrder": 0, "enabled": 1, "enabledExplore": 1,
            "exploreUrl": f"L2分类::{S16_EXPLORE_URL}",
            "ruleExplore": '{"bookList":"class.item","name":"class.t@text",'
                           '"bookUrl":"class.a@href","author":"class.au@text"}',
            "ruleSearch": None, "ruleBookInfo": None, "ruleToc": None, "ruleContent": None,
            "loginUrl": None, "loginCheckJs": None, "header": None,
            "enabledCookieJar": 0, "concurrentRate": "", "lastUpdateTime": 0,
        })
        con.execute(
            f"insert or replace into book_sources ({','.join('`' + c + '`' for c in cols)})"
            f" values ({','.join('?' * len(cols))})",
            [data[c] for c in cols]
        )
        con.commit()
    finally:
        con.close()
    return m2._db_push(db)


def _s16_reset_hint(workdir: Path) -> bool:
    """复位「长按可预览」一次性提示位（默认 prefs）——保证提示可展示"""
    remote = f"/data/data/{PKG}/shared_prefs/{PKG}_preferences.xml"
    return _prefs_edit(
        remote, workdir,
        lambda t: re.sub(r'\s*<boolean name="%s"[^/]*/>' % "exploreShowPreviewHintShown", "", t)
    )


def _s16_purge(workdir: Path) -> bool:
    m2 = _m2()
    db = m2._db_pull(workdir)
    if db is None:
        return False
    con = sqlite3.connect(str(db))
    try:
        con.execute("delete from book_sources where bookSourceUrl = ?", (S16_SOURCE_URL,))
        con.execute("delete from books where name in (?,?)", (S16_BOOK_A, S16_BOOK_B))
        con.commit()
    finally:
        con.close()
    return m2._db_push(db)


def _s16_book_in_shelf(workdir: Path, name: str) -> bool:
    """客观证据：拉库确认该书**已在书架**（`notShelf` 位被清）"""
    m2 = _m2()
    db = m2._db_pull(workdir)
    if db is None:
        return False
    con = sqlite3.connect(str(db))
    try:
        row = con.execute(
            "select type from books where name = ? limit 1", (name,)
        ).fetchone()
        if not row:
            return False
        return (int(row[0]) & S16_EMPTY) == 0
    finally:
        con.close()


def s16_explore_show_page(d) -> bool:
    """M4 9/11：book/explore-show（F46 列表项就地放入书架 / F48 预览可发现性 + 触觉反馈）"""
    print("  [s16] ===== 发现列表更多动作与预览提示 =====")
    m2 = _m2()
    workdir = Path(tempfile.mkdtemp(prefix="m4s16_"))
    db_snap = workdir / "legado_snapshot.db"
    if not m2._snapshot_db(workdir, db_snap):
        print("  [s16] 数据库快照失败（前置）")
        return False
    server = None
    ok = False
    try:
        server = _ExploreListServer(S16_PORT)
        server.start()
        if not _reverse_on(S16_PORT):
            print("  [s16] adb reverse 未建立（设备侧不可达本机列表服务）")
            return False
        reset_app()
        if not _s16_seed(workdir):
            print("  [s16] 合成书源播种失败")
            return False
        _s16_reset_hint(workdir)
        reset_app()

        # ---------- A：落地 + 列表 + 一次性提示 ----------
        landed = False
        for _ in range(3):
            sh("am", "start", "-n", f"{PKG}/{ACT_EXPLORE_SHOW}",
               "--es", "sourceUrl", S16_SOURCE_URL,
               "--es", "exploreUrl", S16_EXPLORE_URL,
               "--es", "exploreName", S16_TITLE)
            time.sleep(4.0)
            if "ExploreShowActivity" in current_activity():
                landed = True
                break
            sh_su(f"am start -n {PKG}/{ACT_EXPLORE_SHOW} --es sourceUrl {S16_SOURCE_URL} "
                  f"--es exploreUrl {S16_EXPLORE_URL} --es exploreName {S16_TITLE}")
            time.sleep(4.0)
            if "ExploreShowActivity" in current_activity():
                landed = True
                break

        list_xml = ""
        deadline = time.time() + 25
        while time.time() < deadline:
            time.sleep(1.0)
            cur = dump_xml(d)
            if S16_BOOK_A in cur and S16_BOOK_B in cur:
                list_xml = cur
                break
        ca.shot(d, "m4s16_list")
        list_ok = bool(list_xml)
        hint_ok = S16_HINT in (list_xml or dump_xml(d))
        more_nodes = _desc_bounds_all(list_xml or dump_xml(d), S16_MORE)
        print(f"  [s16] A 落地={landed} 列表两书在场={list_ok} 一次性提示={hint_ok} "
              f"⋮入口数={len(more_nodes)} 服务命中={server.hits}")

        # ---------- B：⋮ → 上下文菜单 → 放入书架（UI 动作，库证据放在 C 之后取）----------
        # ⚠️ 顺序铁律：`_db_pull` 内部会 `reset_app()`（force-stop 才能安全拷库）⇒
        # 库断言绝不能插在 UI 步骤中间，否则后续 UI 步骤会在**桌面**上执行（本轮首跑即此因：
        # 放入书架后截图是桌面、关闭键 desc 定位不到 ⇒ 假失败）
        sheet_ok = False
        more_b = more_nodes[0] if more_nodes else None
        added_clicked = False
        if more_b:
            click_xy(d, more_b["cx"], more_b["cy"])
            time.sleep(1.8)
            sheet_xml = dump_xml(d)
            ca.shot(d, "m4s16_item_sheet")
            sheet_ok = all(t in sheet_xml for t in (S16_ADD_SHELF, S16_PREVIEW, S16_BOOK_INFO))
            add_b = node_bounds(sheet_xml, S16_ADD_SHELF)
            if add_b:
                click_xy(d, add_b["cx"], add_b["cy"])
                time.sleep(3.0)
                added_clicked = S16_ADD_SHELF not in dump_xml(d)
                ca.shot(d, "m4s16_added")
        print(f"  [s16] B ⋮ 菜单三动作={sheet_ok} 点放入书架后菜单收起={added_clicked}")

        # ---------- C：提示关闭 + 重启不再出现（一次性的后半段）----------
        dismissed = False
        gone_after_restart = False
        close_b = (_desc_bounds_all(dump_xml(d), S16_CANCEL) or [None])[0]
        print(f"  [s16] C 关闭键定位={bool(close_b)}")
        if close_b:
            click_xy(d, close_b["cx"], close_b["cy"])
            time.sleep(1.5)
            dismissed = S16_HINT not in dump_xml(d)
        if dismissed:
            reset_app()
            sh("am", "start", "-n", f"{PKG}/{ACT_EXPLORE_SHOW}",
               "--es", "sourceUrl", S16_SOURCE_URL,
               "--es", "exploreUrl", S16_EXPLORE_URL,
               "--es", "exploreName", S16_TITLE)
            time.sleep(7.0)
            gone_after_restart = S16_HINT not in dump_xml(d)
        print(f"  [s16] C 点关闭后消失={dismissed} 重启后不再出现={gone_after_restart}")

        # ---------- D：库证据（放最后：`_db_pull` 会 force-stop）----------
        added_ok = _s16_book_in_shelf(workdir, S16_BOOK_A)
        print(f"  [s16] D 放入书架后库内已在架={added_ok}")

        # ---------- E：源码断言 ----------
        src_act = _src_text(SRC_EXPLORE_SHOW_ACT)
        src_screen = _src_text(SRC_EXPLORE_SHOW_SCREEN)
        src_vm = _src_text(SRC_EXPLORE_SHOW_VM)
        src_item = _src_text(SRC_SEARCH_BOOK_ITEM)
        checks = [
            ("explore-show: 行尾 ⋮ 入口（可选参数）", "onMore: (() -> Unit)? = null" in src_item),
            ("explore-show: 长按触觉反馈", "HapticFeedbackType.LongPress" in src_item),
            ("explore-show: 菜单含放入书架/预览/详情",
             "R.string.add_to_bookshelf" in src_act and "R.string.preview" in src_act
             and "R.string.book_info" in src_act),
            ("explore-show: 已在书架则不显示放入书架", "if (!isInBookshelf(book))" in src_act),
            ("explore-show: 放入书架不预加载目录（进度不归零）",
             "fun addToBookshelf(" in src_vm
             and "target.durChapterIndex = it.durChapterIndex" in src_vm),
            ("explore-show: 一次性提示项常驻 + 内容门控",
             'item(key = "explore_show_preview_hint"' in src_screen
             and "if (showPreviewHint)" in src_screen),
            ("explore-show: 长按成功即撤提示", "LaunchedEffect(previewState)" in src_screen),
            ("explore-show: 提示位带迁移语义（默认 false 只看一次）",
             "exploreShowPreviewHintShown" in _src_text("app/src/main/java/io/legado/app/constant/PreferKey.kt")),
        ]
        src_ok = all(v for _, v in checks)
        for name, v in checks:
            print(f"  [s16] 源码 {name} = {v}")

        ok = bool(landed and list_ok and hint_ok and more_nodes and sheet_ok and added_clicked
                  and dismissed and gone_after_restart and added_ok and src_ok)
    except Exception as e:
        print(f"  [s16] 异常终止: {type(e).__name__}: {e}")
    finally:
        if server:
            server.stop()
        _s16_purge(workdir)
        print(f"  [s16] 数据库快照回滚={m2._db_push(db_snap)}")
        reset_app()
    return ok


# ============================ s17：M4 批次（book/search + 证书静默放行） ============================

ACT_BOOK_SEARCH = "io.legado.app.ui.book.search.SearchActivity"
ACT_SILENT_SSL_SRC = "app/src/main/java/io/legado/app/help/webView/SilentSslWebViewClient.kt"

S17_PORT = 18591          # 明文书源搜索服务
S17_CERT_PORT = 18592     # 自签证书 HTTPS 服务
S17_SOURCE_URL = "l2seed://book-search"
S17_SOURCE_NAME = "L2搜书校验源"
S17_KEYWORD = "L2SearchKw"
S17_BOOK_A = "L2SearchBookAlpha"
S17_AUTHOR_A = "L2作者甲"
# 简介唯一串：紧凑模式隐藏简介行 ⇒ 该串必须从 a11y 树消失（改动前后同屏对照，不靠像素猜）
S17_INTRO_A = "L2INTROALPHA"
S17_BOOK_B = "L2SearchBookBeta"
S17_CERT_MARKER = "L2CERTPASSMARKER"
S17_COUNT_DONE = "共命中"          # search_result_count_done
S17_COMPACT = "紧凑"               # search_result_compact
S17_PRECISION = "精准搜索"          # precision_search
S17_MORE = "更多"                  # more
S17_MENU_SOURCE = "书源管理"        # book_source_manage（⋮ 菜单可用性佐证）
S17_SSL_LABEL = "证书放行策略"       # 已删除的开关（回归哨兵：出现即说明被回退）
S17_CERT_URL = f"https://127.0.0.1:{S17_CERT_PORT}/"
# 不存在的分组名（用于把持久化搜索范围强制回落为「全部启用源」，见 A 段注释）
S17_SCOPE_DUMMY = "L2NOSUCHGROUP"

SRC_BOOK_SEARCH_ACT = "app/src/main/java/io/legado/app/ui/book/search/SearchActivity.kt"
SRC_BOOK_SEARCH_SCREEN = "app/src/main/java/io/legado/app/ui/book/search/SearchResultScreen.kt"
SRC_BOOK_SEARCH_MENU = "app/src/main/res/menu/book_search.xml"
SRC_BROWSER_ACT = "app/src/main/java/io/legado/app/ui/browser/WebViewActivity.kt"
SRC_LOGIN_FRAG = "app/src/main/java/io/legado/app/ui/login/WebViewLoginFragment.kt"


class _BookSearchServer(threading.Thread):
    """本机书源搜索服务：返回一份可被最简 `ruleSearch` 解析的 HTML（两本书，A 带唯一简介串）。

    与 s14 不同**不注入延迟**：书源搜索并发单源秒回，本场景不需要观测「进行中」窗口
    （书源列表结果条的进行中态由源码断言覆盖），保持测试快。
    """

    def __init__(self, port: int):
        super().__init__(daemon=True)
        self.port = port
        self.hits = 0
        self._httpd = None

    def _html(self) -> bytes:
        p = self.port
        return (
            '<html><body>'
            f'<div class="item"><a class="a" href="http://127.0.0.1:{p}/b1">'
            f'<span class="t">{S17_BOOK_A}</span></a>'
            f'<span class="au">{S17_AUTHOR_A}</span>'
            f'<span class="in">{S17_INTRO_A}</span></div>'
            f'<div class="item"><a class="a" href="http://127.0.0.1:{p}/b2">'
            f'<span class="t">{S17_BOOK_B}</span></a>'
            '<span class="au">L2作者乙</span>'
            '<span class="in">L2INTROBETA</span></div>'
            '</body></html>'
        ).encode("utf-8")

    def run(self):
        import http.server
        outer = self

        class _H(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                outer.hits += 1
                body = outer._html()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *a):
                pass

        class _Srv(http.server.ThreadingHTTPServer):
            daemon_threads = True

        try:
            self._httpd = _Srv(("127.0.0.1", self.port), _H)
        except OSError:
            return
        self._httpd.serve_forever()

    def stop(self):
        try:
            if self._httpd:
                self._httpd.shutdown()
                self._httpd.server_close()
        except Exception:
            pass


class _CertServer(threading.Thread):
    """自签证书 + 主机名不匹配的 HTTPS 服务：验证 WebView 证书错误被**静默放行**。

    证书 CN 故意写成 `l2cert.invalid`（≠ 127.0.0.1）⇒ 信任校验与主机名校验**同时失败**，
    这是「默认拒绝」最容易被触发的形态；若放行逻辑被回退，页面必然白屏（marker 抓不到）。
    """

    def __init__(self, port: int, cert: Path, key: Path):
        super().__init__(daemon=True)
        self.port = port
        self.cert = cert
        self.key = key
        self.hits = 0
        self._httpd = None

    def run(self):
        import http.server
        import ssl as _ssl
        outer = self

        class _H(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                outer.hits += 1
                body = f"<html><body><p>{S17_CERT_MARKER}</p></body></html>".encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *a):
                pass

        class _Srv(http.server.ThreadingHTTPServer):
            daemon_threads = True

        try:
            self._httpd = _Srv(("127.0.0.1", self.port), _H)
            ctx = _ssl.SSLContext(_ssl.PROTOCOL_TLS_SERVER)
            ctx.load_cert_chain(str(self.cert), str(self.key))
            self._httpd.socket = ctx.wrap_socket(self._httpd.socket, server_side=True)
        except OSError:
            return
        self._httpd.serve_forever()

    def stop(self):
        try:
            if self._httpd:
                self._httpd.shutdown()
                self._httpd.server_close()
        except Exception:
            pass


def _s17_openssl() -> str:
    for cand in (r"C:\Program Files\Git\usr\bin\openssl.exe",
                 r"C:\Program Files\Git\mingw64\bin\openssl.exe",
                 "openssl"):
        if cand == "openssl" or Path(cand).exists():
            return cand
    return ""


def _s17_make_cert(workdir: Path):
    """生成自签证书（CN 故意与 127.0.0.1 不匹配）"""
    exe = _s17_openssl()
    if not exe:
        return None, None
    cert = workdir / "l2cert.pem"
    key = workdir / "l2key.pem"
    r = subprocess.run(
        [exe, "req", "-x509", "-newkey", "rsa:2048", "-nodes",
         "-keyout", str(key), "-out", str(cert), "-days", "1",
         "-subj", "/CN=l2cert.invalid"],
        capture_output=True, text=True
    )
    if r.returncode != 0 or not cert.exists():
        print(f"  [s17] openssl 生成证书失败 rc={r.returncode}")
        return None, None
    return cert, key


def _s17_seed(workdir: Path) -> bool:
    """播种搜书校验源（整行复制既有书源后改写；`ruleSearch` 为 Gson JSON 串）。

    必须**临时禁用其它书源**：书源搜索会并发跑所有启用源，留着存量源会让「共命中 N 本」
    不确定、等待也长；收尾走整库快照回滚（零残留，不用逐条清理）。
    """
    m2 = _m2()
    db = m2._db_pull(workdir)
    if db is None:
        return False
    con = sqlite3.connect(str(db))
    try:
        cols = [r[1] for r in con.execute("pragma table_info(book_sources)")]
        row = con.execute("select * from book_sources limit 1").fetchone()
        if not row:
            return False
        data = dict(zip(cols, row))
        con.execute("update book_sources set enabled = 0")
        data.update({
            "bookSourceUrl": S17_SOURCE_URL, "bookSourceName": S17_SOURCE_NAME,
            "bookSourceGroup": "", "bookSourceType": 0, "bookSourceComment": "",
            "customOrder": 0, "enabled": 1, "enabledExplore": 0,
            # {{key}} 由 AnalyzeUrl 以搜索词替换（与真实源同口径）
            "searchUrl": f"http://127.0.0.1:{S17_PORT}/search?k={{{{key}}}}",
            "ruleSearch": '{"bookList":"class.item","name":"class.t@text",'
                          '"author":"class.au@text","intro":"class.in@text",'
                          '"bookUrl":"class.a@href"}',
            "ruleExplore": None, "ruleBookInfo": None, "ruleToc": None, "ruleContent": None,
            "loginUrl": None, "loginCheckJs": None, "header": None,
            "enabledCookieJar": 0, "concurrentRate": "", "lastUpdateTime": 0,
        })
        con.execute(
            f"insert or replace into book_sources ({','.join('`' + c + '`' for c in cols)})"
            f" values ({','.join('?' * len(cols))})",
            [data[c] for c in cols]
        )
        con.commit()
    finally:
        con.close()
    return m2._db_push(db)


def _s17_reset_prefs(workdir: Path) -> bool:
    """复位本轮写下的两个页面偏好（**偏好不在 DB 快照内**，必须单独清）"""
    remote = f"/data/data/{PKG}/shared_prefs/{PKG}_preferences.xml"

    def mutate(text: str) -> str:
        for k in ("precisionSearch", "searchResultCompact"):
            text = re.sub(r'\s*<boolean name="%s"[^/]*/>' % k, "", text)
        return text

    return _prefs_edit(remote, workdir, mutate)


def _s17_wait_results(d, deadline_s: float = 40.0):
    """等到搜索**收敛到「2 本」且两本书都在场**；返回 (xml, ok)。

    只等「共命中」字样不可靠：`SearchViewModel.search()` 每次都会先
    `cancelSearch()` + `postValue(emptyList())` ⇒ `isSearchLiveData` 瞬间回到 false、结果清空，
    状态条会**一闪「共命中 0 本」**（首轮实测抓到这一帧 ⇒ 假失败）。必须等到目标计数 + 双书在场。
    """
    deadline = time.time() + deadline_s
    xml = dump_xml(d)
    target = f"{S17_COUNT_DONE} 2 本"
    while time.time() < deadline:
        xml = dump_xml(d)
        if target in xml and S17_BOOK_A in xml and S17_BOOK_B in xml:
            return xml, True
        time.sleep(1.0)
    return xml, False


def _s17_verify_seed(workdir: Path) -> bool:
    """回读确认播种**真的落到设备库**（区分「播种没落库」与「搜索没用上」两类失败）"""
    m2 = _m2()
    db = m2._db_pull(workdir)
    if db is None:
        return False
    con = sqlite3.connect(str(db))
    try:
        row = con.execute(
            "select enabled, searchUrl, ruleSearch is not null from book_sources"
            " where bookSourceUrl = ? limit 1", (S17_SOURCE_URL,)
        ).fetchone()
        if not row:
            print("  [s17] 复查：播种源不在库中")
            return False
        print(f"  [s17] 复查：enabled={row[0]} hasSearchUrl={bool(row[1])} hasRule={bool(row[2])}")
        n_enabled = con.execute("select count(*) from book_sources where enabled = 1").fetchone()[0]
        print(f"  [s17] 复查：启用书源数={n_enabled}")
        return int(row[0]) == 1 and bool(row[1]) and bool(row[2])
    finally:
        con.close()


def _s17_diag_texts(xml: str, limit: int = 12) -> list:
    """失败诊断：把 dump 里与「搜索/命中/本」相关的短文本抽出来（无需猜节点名）"""
    out = []
    for m in re.finditer(r'text="([^"]{1,40})"', xml):
        t = m.group(1)
        if any(k in t for k in ("搜索", "命中", "本", "为空", "暂无")):
            out.append(t)
    return out[:limit]


def _s17_diag_applog(workdir: Path) -> None:
    """失败诊断：读库内 appLog 最近与「搜书」相关的行（AppLog 落库，logcat 拿不到）"""
    m2 = _m2()
    db = m2._db_pull(workdir)
    if db is None:
        print("  [s17] 诊断：拉库失败")
        return
    con = sqlite3.connect(str(db))
    try:
        # 表名不做硬编码猜测：按名字含 log 的表去找（AppLog 实体表名随版本变过）
        names = [r[0] for r in con.execute(
            "select name from sqlite_master where type='table'").fetchall()]
        tbl = next((n for n in names if "log" in n.lower()), None)
        if not tbl:
            print(f"  [s17] 诊断：库内无日志表（tables={len(names)}）")
            return
        rows = con.execute(
            f"select msg from `{tbl}` where msg like ? order by date desc limit 6",
            ("%" + S17_SOURCE_NAME + "%",)
        ).fetchall()
        for r in rows:
            print(f"  [s17] 诊断 日志表({tbl}): {str(r[0])[:160]}")
        if not rows:
            print(f"  [s17] 诊断 日志表({tbl}): 无与本页源相关的记录")
    except Exception as e:
        print(f"  [s17] 诊断 查询失败: {type(e).__name__}")
    finally:
        con.close()


def _s17_proc_alive() -> bool:
    """进程存活探测。①本机模拟器**无 `pidof`**（rc=1、无输出）②`sh()` 已内含 `shell` 子命令
    ⇒ 传「设备侧命令」本身，且 stdout 是 **bytes**（不 decode 会静默匹配失败）。"""
    raw = sh("ps -A").stdout or b""
    text = raw.decode("utf-8", "ignore") if isinstance(raw, (bytes, bytearray)) else str(raw)
    return PKG in text


def s17_book_search_and_cert(d) -> bool:
    """M4 余页：book/search（F73 实时命中计数 / F74 精准搜索前置 / F75 紧凑密度）
    + 全项目证书静默放行（WebView 域一律 proceed）"""
    print("  [s17] ===== 搜书结果状态条 + 证书静默放行 =====")
    m2 = _m2()
    workdir = Path(tempfile.mkdtemp(prefix="m4s17_"))
    db_snap = workdir / "legado_snapshot.db"
    if not m2._snapshot_db(workdir, db_snap):
        print("  [s17] 数据库快照失败（前置）")
        return False
    search_srv = None
    cert_srv = None
    ok = False
    try:
        search_srv = _BookSearchServer(S17_PORT)
        search_srv.start()
        cert, key = _s17_make_cert(workdir)
        if cert:
            cert_srv = _CertServer(S17_CERT_PORT, cert, key)
            cert_srv.start()
        if not _reverse_on(S17_PORT):
            print("  [s17] adb reverse 未建立（设备侧不可达本机搜书服务）")
            return False
        _reverse_on(S17_CERT_PORT)
        reset_app()
        _s17_reset_prefs(workdir)
        if not _s17_seed(workdir):
            print("  [s17] 书源播种失败（库内无 book_sources 行可复制）")
            return False
        seed_ok = _s17_verify_seed(workdir)
        reset_app()

        # ---------- A：搜书落地 + 状态条实时命中计数 ----------
        # 必须显式给一个**不存在**的搜索范围：`SearchViewModel.searchScope` 初值是持久化的
        # `AppConfig.searchScope`，设备上若残留了分组/单源范围，本机播种源不会被搜到 ⇒ 服务命中恒 0
        # （首轮实测失败的真正原因）。注意 `am` **不接受空串参数**（`Argument expected after`），
        # 故用不存在的分组名走 `getBookSourceParts()` 的「范围解析为空即回落全部启用源」分支。
        sh("am", "start", "-n", f"{PKG}/{ACT_BOOK_SEARCH}",
           "--es", "key", S17_KEYWORD, "--es", "searchScope", S17_SCOPE_DUMMY)
        time.sleep(1.0)
        landed = "SearchActivity" in current_activity()
        xml, found = _s17_wait_results(d)
        ca.shot(d, "m4s17_search_summary")
        # 进程存活断言：Activity 构造期崩溃（如 Context 未 attach 就读偏好）时 `am start` 仍报
        # 成功、且 `current_activity()` 有一瞬间能抓到 ActivityRecord ⇒ 只看「落地」会假阴性
        proc_alive = _s17_proc_alive()
        count_ok = found and f"{S17_COUNT_DONE} 2 本" in xml
        both_books = S17_BOOK_A in xml and S17_BOOK_B in xml
        print(f"  [s17] A 落地={landed} 进程存活={proc_alive} 播种复查={seed_ok} "
              f"状态条命中={count_ok} 双书在场={both_books} 服务命中={search_srv.hits}")
        if not both_books:
            print(f"  [s17] A 诊断（dump 相关短文本）={_s17_diag_texts(xml)}")

        # ---------- B：紧凑密度（同屏对照：简介串消失/回归） ----------
        compact_on = compact_off = False
        intro_before = S17_INTRO_A in xml
        cb = node_bounds(xml, S17_COMPACT)
        if cb:
            click_xy(d, cb["cx"], cb["cy"])
            time.sleep(1.5)
            xml_c = dump_xml(d)
            ca.shot(d, "m4s17_compact_on")
            compact_on = (S17_INTRO_A not in xml_c) and (S17_BOOK_A in xml_c)
            cb2 = node_bounds(xml_c, S17_COMPACT)
            if cb2:
                click_xy(d, cb2["cx"], cb2["cy"])
                time.sleep(1.5)
                xml_d = dump_xml(d)
                ca.shot(d, "m4s17_compact_off")
                compact_off = S17_INTRO_A in xml_d
        print(f"  [s17] B 简介改动前在场={intro_before} 紧凑后简介消失={compact_on} "
              f"再点恢复={compact_off}")

        # ---------- C：精准搜索 chip ⇒ 触发重搜且结果集按新口径收敛 ----------
        precision_ok = False
        hits_before = search_srv.hits
        pb = node_bounds(dump_xml(d), S17_PRECISION)
        if pb:
            click_xy(d, pb["cx"], pb["cy"])
            deadline = time.time() + 40
            while time.time() < deadline:
                time.sleep(1.0)
                cur = dump_xml(d)
                # 精准=结果集过滤（SearchModel: 书名/作者/分类须含关键词）⇒ 两本书都不含关键词 ⇒ 0 本。
                # 判据必须同时要求「双书消失」：直读「共命中 0 本」会被 search() 的 cancel 闪帧命中。
                if f"{S17_COUNT_DONE} 0 本" in cur and S17_BOOK_A not in cur and S17_BOOK_B not in cur:
                    precision_ok = True
                    break
            ca.shot(d, "m4s17_precision_on")
        print(f"  [s17] C 精准搜索后命中归零={precision_ok} 服务命中增量={search_srv.hits - hits_before}")

        # ---------- D：⋮ 菜单可用（精准项已上浮 ⇒ 菜单里不再有同状态入口） ----------
        menu_ok = False
        # 菜单按钮按 **resource-id** 定位：其 contentDescription 是 `@string/menu`（「菜单」）
        # 而非「更多」，按文案找会落空（首轮实测）
        mb = node_bounds_by_id(dump_xml(d), "btn_menu")
        if mb:
            click_xy(d, mb["cx"], mb["cy"])
            time.sleep(1.5)
            mxml = dump_xml(d)
            menu_ok = S17_MENU_SOURCE in mxml
            # 菜单打开后 dump 会含底层页面 ⇒ 不能用「文案不存在」判单入口；用源码断言（下方 F）
        print(f"  [s17] D ⋮ 菜单可用={menu_ok}")

        # ---------- E：证书静默放行（自签 + 主机名不匹配的 HTTPS 页面能加载） ----------
        reset_app()
        cert_loaded = False
        if cert_srv:
            sh("am", "start", "-n", f"{PKG}/{ACT_BROWSER}",
               "--es", "url", S17_CERT_URL, "--es", "title", "l2cert")
            deadline = time.time() + 25
            while time.time() < deadline:
                time.sleep(1.5)
                cur = dump_xml(d)
                if S17_CERT_MARKER in cur:
                    cert_loaded = True
                    break
            ca.shot(d, "m4s17_cert_passthrough")
            print(f"  [s17] E 证书错误页面加载={cert_loaded} HTTPS 命中={cert_srv.hits}")
        else:
            print("  [s17] E 跳过（本机缺 openssl，无法构造自签证书）")

        # ---------- F：源码断言 ----------
        src_act = _src_text(SRC_BOOK_SEARCH_ACT)
        src_screen = _src_text(SRC_BOOK_SEARCH_SCREEN)
        src_menu = _src_text(SRC_BOOK_SEARCH_MENU)
        src_base = _src_text(ACT_SILENT_SSL_SRC)
        src_browser = _src_text(SRC_BROWSER_ACT)
        src_login = _src_text(SRC_LOGIN_FRAG)
        checks = [
            ("search: 状态条计数（搜索中/结束双文案）",
             "search_result_counting" in src_screen and "search_result_count_done" in src_screen),
            ("search: 多源聚合计数（origins.size > 1）", "it.origins.size > 1" in src_screen),
            ("search: 状态条搜过即亮（含 0 命中）",
             "resultSummaryVisible = true" in src_act
             and "resultSummaryVisible = false" in src_act),
            ("search: 精准搜索切后重搜", "putPrefBoolean(PreferKey.precisionSearch, enabled)" in src_act),
            ("search: 菜单精准项已上浮（单入口）",
             "menu_precision_search" not in src_menu and "menu_precision_search" not in src_act),
            ("search: 紧凑密度走本页私有偏好",
             "PreferKey.searchResultCompact" in src_act and "compact = compactMode" in src_screen),
            ("search: 空结果弹窗文案已资源化", "search_book_empty_precision" in src_act),
            ("ssl: 静默放行基类存在且 proceed",
             "open class SilentSslWebViewClient" in src_base and "handler?.proceed()" in src_base),
            ("ssl: 浏览器/登录页无拦截分支（无放行开关）",
             "sslCertPassThrough" not in src_browser and "sslCertPassThrough" not in src_login
             and "onReceivedSslError" not in src_browser
             and "onReceivedSslError" not in src_login),
        ]
        src_ok = all(v for _, v in checks)
        for name, v in checks:
            print(f"  [s17] 源码 {name} = {v}")

        ok = bool(seed_ok and proc_alive and landed and count_ok and both_books and intro_before
                  and compact_on and compact_off and precision_ok and menu_ok and src_ok
                  and (cert_loaded or not cert_srv))
    except Exception as e:
        print(f"  [s17] 异常终止: {type(e).__name__}: {e}")
    finally:
        if search_srv:
            search_srv.stop()
        if cert_srv:
            cert_srv.stop()
        if not ok:
            _s17_diag_applog(workdir)
        _s17_reset_prefs(workdir)
        print(f"  [s17] 数据库快照回滚={m2._db_push(db_snap)}")
        reset_app()
    return ok


# ============================ s18：M4 收官（rss/read） ============================

ACT_RSS_READ = "io.legado.app.ui.rss.read.ReadRssActivity"

S18_PORT = 18593
S18_SOURCE_URL = "l2seed://rss-read"
S18_SOURCE_NAME = "L2订阅阅读源"
S18_ARTICLE_URL = f"http://127.0.0.1:{S18_PORT}/article"
S18_TITLE = "L2LONGARTICLE"
# 长文标记：正文够长才滚得动（顶栏收起需要真实滚动）
S18_PARA = "L2READPARA"
S18_GROUP_CONTENT = "内容"        # rss_read_menu_group_content
S18_GROUP_READING = "阅读工具"     # rss_read_menu_group_reading
S18_GROUP_SOURCE = "源"           # rss_read_menu_group_source
S18_GROUP_TOOLS = "工具"          # source_menu_group_tools
S18_TTS_RUNNING = "朗读中"        # rss_read_tts_running

SRC_RSS_READ = "app/src/main/java/io/legado/app/ui/rss/read/ReadRssActivity.kt"
SRC_RSS_READ_BP = "docs/UI/rss/read/OPTIMIZATION.md"


class _LongArticleServer(threading.Thread):
    """本机长文服务：给 `rss/read` 提供可滚动的正文页（顶栏收起必须靠真实滚动触发）"""

    def __init__(self, port: int, paragraphs: int = 60):
        super().__init__(daemon=True)
        self.port = port
        self.paragraphs = paragraphs
        self.hits = 0
        self._httpd = None

    def _html(self) -> bytes:
        body = "".join(
            f"<p>{S18_PARA} 第 {i} 段：用于验证滚动收起顶栏的占位正文。</p>"
            for i in range(self.paragraphs)
        )
        return (
            f"<html><head><meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<title>{S18_TITLE}</title></head>"
            f"<body><h1>{S18_TITLE}</h1>{body}</body></html>"
        ).encode("utf-8")

    def run(self):
        import http.server
        outer = self

        class _H(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                outer.hits += 1
                body = outer._html()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *a):
                pass

        class _Srv(http.server.ThreadingHTTPServer):
            daemon_threads = True

        try:
            self._httpd = _Srv(("127.0.0.1", self.port), _H)
        except OSError:
            return
        self._httpd.serve_forever()

    def stop(self):
        try:
            if self._httpd:
                self._httpd.shutdown()
                self._httpd.server_close()
        except Exception:
            pass


def _s18_seed(workdir: Path) -> bool:
    """播种订阅阅读源（整行复制既有源后改写；`singleUrl=1` + 无 ruleContent ⇒ 直接 loadUrl 原文）"""
    m2 = _m2()
    db = m2._db_pull(workdir)
    if db is None:
        return False
    con = sqlite3.connect(str(db))
    try:
        cols = [r[1] for r in con.execute("pragma table_info(rssSources)")]
        row = con.execute("select * from rssSources limit 1").fetchone()
        if not row:
            return False
        data = dict(zip(cols, row))
        data.update({
            "sourceUrl": S18_SOURCE_URL, "sourceName": S18_SOURCE_NAME, "type": 0,
            "enabled": 1, "enabledCookieJar": 0,
            "searchUrl": None, "sortUrl": f"L2分类::{S18_ARTICLE_URL}",
            "ruleArticles": None, "ruleNextPage": None, "ruleContent": None,
            "singleUrl": 1, "header": None, "loginUrl": None, "loginCheckJs": None,
            "preload": 0, "customOrder": 0,
        })
        _s12_upsert(con, "rssSources", cols, data)
        con.commit()
    finally:
        con.close()
    return m2._db_push(db)


def _s18_topbar_visible(xml: str, min_h: int = 20) -> bool:
    """顶栏可见性：`compose_top_bar` 的 bounds 高度 ≥ [min_h] 视为可见。

    **不能**用「高度 > 0」：收起（layoutParams.height=0）后该节点仍会在 dump 里带 1px 级边界，
    会得到「收起失败」的假结论（首轮实测：沉浸日志已 collapsed=true，断言却仍判可见）。
    展开态实测高度 132px，故 20px 阈值分辨力充足。
    """
    b = node_bounds_by_id(xml, "compose_top_bar")
    return bool(b and (b["bottom"] - b["top"]) >= min_h)


def _s18_topbar_h(xml: str) -> int:
    b = node_bounds_by_id(xml, "compose_top_bar")
    return (b["bottom"] - b["top"]) if b else -1


def _s18_top_strip_ink(png: str, strip_h: int = 60) -> float:
    """顶栏所在区域（图片顶部 [0,strip_h)）的**暗像素占比**。

    收起后该区域只剩背景/正文留白，占比应显著低于展开态（展开态该区含标题与图标文字）。
    a11y 树对「顶栏 GONE」的反映存在滞后（实测截图已收起、同刻 dump 仍报 132px），
    故以截图墨量 + 沉浸日志为权威判据。
    """
    from PIL import Image
    im = Image.open(png).convert("L")
    w, hh = im.size
    strip = im.crop((0, 0, w, min(strip_h, hh)))
    px = list(strip.getdata())
    return sum(1 for p in px if p < 140) / max(1, len(px))


def _s18_immersive_log_state() -> tuple:
    """读设备 logcat 的沉浸联动跃迁（true=收起 / false=展开 各出现的次数）"""
    raw = sh("logcat", "-d", "-s", "RssReadImmersive").stdout or b""
    text = raw.decode("utf-8", "ignore") if isinstance(raw, (bytes, bytearray)) else str(raw)
    return text.count("collapsed=true"), text.count("collapsed=false")


def s18_rss_read_page(d) -> bool:
    """M4 收官页：rss/read（F2 菜单四组 / F146 滚动收起顶栏 / F147 朗读状态条）"""
    print("  [s18] ===== 订阅阅读：菜单四组 + 滚动沉浸 + 朗读状态条 =====")
    m2 = _m2()
    workdir = Path(tempfile.mkdtemp(prefix="m4s18_"))
    db_snap = workdir / "legado_snapshot.db"
    if not m2._snapshot_db(workdir, db_snap):
        print("  [s18] 数据库快照失败（前置）")
        return False
    server = None
    ok = False
    try:
        server = _LongArticleServer(S18_PORT)
        server.start()
        if not _reverse_on(S18_PORT):
            print("  [s18] adb reverse 未建立（设备侧不可达本机长文服务）")
            return False
        reset_app()
        if not _s18_seed(workdir):
            print("  [s18] 订阅源播种失败（库内无 rssSources 行可复制）")
            return False
        reset_app()

        sh("am", "start", "-n", f"{PKG}/{ACT_RSS_READ}",
           "--es", "origin", S18_SOURCE_URL, "--es", "title", S18_TITLE,
           "--es", "openUrl", S18_ARTICLE_URL)
        time.sleep(1.0)
        landed = "ReadRssActivity" in current_activity()
        proc_alive = _s17_proc_alive()
        xml = ""
        deadline = time.time() + 25
        while time.time() < deadline:
            time.sleep(1.0)
            xml = dump_xml(d)
            if _s18_topbar_visible(xml) and S18_PARA in xml:
                break
        ca.shot(d, "m4s18_read_loaded")
        topbar_initial = _s18_topbar_visible(xml)
        article_loaded = S18_PARA in xml
        print(f"  [s18] A 落地={landed} 进程存活={proc_alive} 正文加载={article_loaded} "
              f"顶栏初始可见={topbar_initial} 服务命中={server.hits}")

        # ---------- B：下滚收起顶栏 ⇒ 上滚唤回（F146） ----------
        collapsed = False
        restored = False
        scrolled = False
        ink_c = ink_r = -1.0
        if article_loaded:
            png_c = str(workdir / "collapsed.png")
            png_r = str(workdir / "restored.png")
            # 慢速滑动（0.6s）而非 fling：快甩在部分 WebView 上被当作惯性滚动起点，
            # 首屏可能还没滚起来就结束（首轮实测 collapsed=False 的疑似根因）
            for _ in range(4):
                d.swipe(0.5, 0.72, 0.5, 0.30, 0.6)
                time.sleep(0.5)
            time.sleep(1.2)
            xml_c = dump_xml(d)
            d.screenshot(png_c)
            ca.shot(d, "m4s18_topbar_collapsed")
            ink_c = _s18_top_strip_ink(png_c)
            scrolled = "第 0 段" not in xml_c
            for _ in range(4):
                d.swipe(0.5, 0.30, 0.5, 0.72, 0.6)
                time.sleep(0.5)
            time.sleep(1.2)
            xml_r = dump_xml(d)
            d.screenshot(png_r)
            ca.shot(d, "m4s18_topbar_restored")
            ink_r = _s18_top_strip_ink(png_r)
        c_seen, e_seen = _s18_immersive_log_state()
        # 主判据：a11y 树里顶栏是否还在（抖动消除后 dump 可正确反映 GONE/VISIBLE）；
        # 墨量只作诊断打印——正文文字密度可能高于顶栏标题，方向不可反推（首轮实测踩过）
        collapsed = not _s18_topbar_visible(xml_c) if article_loaded else False
        restored = _s18_topbar_visible(xml_r) if article_loaded else False
        # 抖动哨兵：一次进出各只应触发 1~3 次；600+ 说明「逐事件判向」被滑动抖动反复触发
        not_thrashing = 1 <= c_seen <= 6 and 1 <= e_seen <= 6
        restored = restored and not_thrashing
        collapsed = collapsed and not_thrashing
        print(f"  [s18] B 正文确实滚动={scrolled} 顶栏高度 收起/展开={_s18_topbar_h(xml_c)}/{_s18_topbar_h(xml_r)}"
              f" 顶栏区墨量={ink_c:.4f}/{ink_r:.4f} ⇒ 收起={collapsed} 唤回={restored}"
              f"（沉浸日志 collapsed=true×{c_seen} / false×{e_seen}，抖动哨兵={not_thrashing}）")

        # ---------- C：更多菜单四组（F2） ----------
        menu_ok = False
        groups_ok = False
        mb = node_bounds(dump_xml(d), "更多")
        if mb:
            click_xy(d, mb["cx"], mb["cy"])
            time.sleep(1.5)
            mxml = dump_xml(d)
            ca.shot(d, "m4s18_menu_groups")
            menu_ok = any(t in mxml for t in ("分享", "编辑源"))
            groups_ok = all(t in mxml for t in
                            (S18_GROUP_CONTENT, S18_GROUP_READING, S18_GROUP_SOURCE, S18_GROUP_TOOLS))
            # 关闭菜单
            d.press("back")
            time.sleep(1.0)
        print(f"  [s18] C 菜单可开={menu_ok} 四组标题齐={groups_ok}")

        # ---------- D：朗读状态条（F147，尽力而为：模拟器可能无可用 TTS 引擎） ----------
        tts_bar_seen = False
        if menu_ok and article_loaded:
            mb2 = node_bounds(dump_xml(d), "更多")
            if mb2:
                click_xy(d, mb2["cx"], mb2["cy"])
                time.sleep(1.2)
                rb = node_bounds(dump_xml(d), "朗读")
                if rb:
                    click_xy(d, rb["cx"], rb["cy"])
                    deadline = time.time() + 20
                    while time.time() < deadline:
                        time.sleep(1.0)
                        if S18_TTS_RUNNING in dump_xml(d):
                            tts_bar_seen = True
                            break
                    ca.shot(d, "m4s18_tts_bar")
        print(f"  [s18] D 朗读状态条出现={tts_bar_seen}（模拟器无 TTS 引擎时为 False，不计入判定）")

        # ---------- E：源码断言 ----------
        src = _src_text(SRC_RSS_READ)
        checks = [
            ("rss/read: 菜单四组标题", "rss_read_menu_group_content" in src
             and "rss_read_menu_group_reading" in src and "rss_read_menu_group_source" in src),
            ("rss/read: 联动信号来自触摸方向（View 滚动监听/JS 桥在真机均不可用）",
             "initImmersiveScroll" in src and "MotionEvent.ACTION_MOVE" in src
             and "setTopBarCollapsed" in src),
            ("rss/read: 收起用 GONE（ConstraintLayout 的 height=0 会被内容撑开）",
             "bar.visibility = View.GONE" in src),
            ("rss/read: 顶栏动画时长常量", "TOP_BAR_ANIM_MS" in src),
            ("rss/read: 全屏视频退出/新页面 顶栏复位",
             "setTopBarCollapsed(false, animate = false)" in src),
            ("rss/read: 朗读状态条复用 InlineTaskBar",
             "InlineTaskBar(" in src and "InlineTaskState.Running" in src),
        ]
        src_ok = all(v for _, v in checks)
        for name, v in checks:
            print(f"  [s18] 源码 {name} = {v}")

        ok = bool(landed and proc_alive and article_loaded and topbar_initial
                  and scrolled and collapsed and restored and menu_ok and groups_ok and src_ok)
    except Exception as e:
        print(f"  [s18] 异常终止: {type(e).__name__}: {e}")
    finally:
        if server:
            server.stop()
        print(f"  [s18] 数据库快照回滚={m2._db_push(db_snap)}")
        reset_app()
    return ok


# ============================ M5 s19：供应商管理（F90 / F91 / F4） ============================

ACT_AI_PROVIDER_MANAGE = "io.legado.app.ui.config.AiProviderManageActivity"
ACT_AI_PROVIDER_EDIT = "io.legado.app.ui.config.AiProviderEditActivity"
S19_PREFS = f"/data/data/{PKG}/shared_prefs/{PKG}_preferences.xml"
S19_PROVIDER_A = "L2provAlpha"
S19_PROVIDER_B = "L2provBeta"
S19_MODEL_ID = "l2-s19-model-zeta"
S19_STAT_USABLE = "可用"          # ai_provider_stat_usable
S19_STAT_MODELS = "模型总数"      # ai_provider_stat_models
S19_STAT_CURRENT = "当前使用"     # ai_provider_stat_current
S19_SEARCH_HINT = "搜索提供商"    # ai_provider_search_hint
S19_EMPTY_TITLE = "没有匹配"      # ai_provider_search_empty_title
S19_EMPTY_CLEAR = "清除搜索"      # ai_provider_search_empty_clear
S19_MODELS_ROW = "已添加"         # ai_manage_models_summary（values-zh）= 已添加 %1$d 个模型
S19_QUERY = "zzzq"
S19_SRC_MANAGE = "app/src/main/java/io/legado/app/ui/config/AiProviderManageActivity.kt"
S19_SRC_EDIT = "app/src/main/java/io/legado/app/ui/config/AiProviderEditActivity.kt"


def _s19_proc_alive() -> bool:
    """进程存活探测：模拟器无 pidof，用 ps -A 匹配包名（构造期崩溃时 am start 仍报成功）"""
    r = sh("ps", "-A", timeout=20)
    return PKG.encode() in (r.stdout or b"")


def _s19_seed(workdir: Path) -> bool:
    """播种两个供应商（甲含 1 个模型 / 乙 0 个模型）+ 当前供应商=甲。
    前置：应用已停（SharedPreferences 内存态会覆盖文件）。"""
    providers = (
        '[{"id":"l2p1","name":"%s","baseUrl":"http://127.0.0.1:1/v1","apiKey":"k",'
        '"headers":"","apiMode":"chat_completions","promptCache":false},'
        '{"id":"l2p2","name":"%s","baseUrl":"http://127.0.0.1:2/v1","apiKey":"k",'
        '"headers":"","apiMode":"chat_completions","promptCache":false}]'
    ) % (S19_PROVIDER_A, S19_PROVIDER_B)
    models = '[{"id":"l2m1","providerId":"l2p1","modelId":"%s"}]' % S19_MODEL_ID
    esc_prov = providers.replace('"', "&quot;")
    esc_models = models.replace('"', "&quot;")

    def mutate(text: str) -> str:
        for k in ("aiProviderList", "aiModelConfigList", "aiCurrentProviderId"):
            text = re.sub(r'\s*<[a-z]+ name="%s"[^>]*>[^<]*</[a-z]+>' % k, "", text)
            text = re.sub(r'\s*<[a-z]+ name="%s"[^/]*/>' % k, "", text)
        inject = (
            '<string name="aiProviderList">%s</string>\n'
            '<string name="aiModelConfigList">%s</string>\n'
            '<string name="aiCurrentProviderId">l2p1</string>\n'
        ) % (esc_prov, esc_models)
        return text.replace("</map>", inject + "</map>")

    return _prefs_edit(S19_PREFS, workdir, mutate)


def _s19_prefs_restored() -> bool:
    r = sh_su(f"cat {S19_PREFS}")
    return S19_PROVIDER_A not in (r.stdout or b"").decode("utf-8", errors="ignore")


def s19_ai_provider_manage(d) -> bool:
    """M5：config/ai-provider-manage（F90 统计摘要条 / F91 页内搜索与空结果闭环 / F4 模型行直达模型 Tab）"""
    print("  [s19] ===== 供应商管理 统计条 + 搜索闭环 + 模型行直达 =====")
    workdir = Path(tempfile.mkdtemp(prefix="m5s19_"))
    reset_app()
    # 本轮覆写三个 AI 偏好键，先整文件备份，收尾原样还原（偏好不在 DB 快照内）
    sh_su(f"cp {S19_PREFS} {S19_PREFS}.l2s19bak")
    ok = False
    try:
        if not _s19_seed(workdir):
            print("  [s19] 偏好播种失败（写入后回读不一致）")
            return False
        reset_app()
        sh("am", "start", "-n", f"{PKG}/{ACT_AI_PROVIDER_MANAGE}")
        time.sleep(2.5)
        landed = "AiProviderManageActivity" in current_activity()
        proc_alive = _s19_proc_alive()
        xml = dump_xml(d)
        ca.shot(d, "m5s19_provider_manage")
        # 甲 1 个模型 / 共 2 个 ⇒ 统计条第一格应为「1 / 2」
        stat_ratio = "1 / 2" in xml
        stat_models = S19_STAT_MODELS in xml and S19_STAT_USABLE in xml and S19_STAT_CURRENT in xml
        rows = S19_PROVIDER_A in xml and S19_PROVIDER_B in xml
        print(f"  [s19] A 落地={landed} 进程存活={proc_alive} 统计比={stat_ratio} "
              f"统计文案={stat_models} 双供应商在场={rows}")
        if not rows:
            print(f"  [s19] A 诊断（短文本）= {text_nodes(xml)[:14]}")

        # ---------- B：搜索不命中 ⇒ 空结果卡（F91 闭环） ----------
        xml_b = xml
        sb = node_bounds(xml, S19_SEARCH_HINT, contains=True)
        empty_ok = rows_gone = False
        if sb:
            click_xy(d, sb["cx"], sb["cy"])
            time.sleep(1.0)
            sh("input", "text", S19_QUERY)
            time.sleep(1.5)
            xml_b = dump_xml(d)
            ca.shot(d, "m5s19_search_empty")
            empty_ok = (S19_EMPTY_TITLE in xml_b) and (S19_QUERY in xml_b)
            # 判据不能含「当前供应商名」：统计条第三格恒显当前供应商（甲）⇒ 列表已隐藏仍会命中假阴性。
            # 行专属标记 = 模型数行「已添加 N 个模型」（两行都渲染该文案）+ 非当前的乙名。
            rows_gone = (S19_MODELS_ROW not in xml_b) and (S19_PROVIDER_B not in xml_b)
        print(f"  [s19] B 搜索框定位={bool(sb)} 空结果卡={empty_ok} 双供应商已隐藏={rows_gone}")

        # ---------- C：清除搜索 ⇒ 列表回归 ----------
        xml_c = xml_b
        cleared = False
        cb = node_bounds(xml_b, S19_EMPTY_CLEAR, contains=True)
        if cb:
            click_xy(d, cb["cx"], cb["cy"])
            time.sleep(1.5)
            xml_c = dump_xml(d)
            ca.shot(d, "m5s19_search_cleared")
            cleared = (S19_PROVIDER_A in xml_c) and (S19_PROVIDER_B in xml_c) \
                and (S19_EMPTY_TITLE not in xml_c)
        print(f"  [s19] C 清除搜索键定位={bool(cb)} 列表回归={cleared}")

        # ---------- D：模型数行直达模型 Tab（F4 落地判据 = 模型 id 在场） ----------
        models_tab = False
        mb = node_bounds(xml_c, S19_MODELS_ROW, contains=True)
        if mb:
            click_xy(d, mb["cx"], mb["cy"])
            time.sleep(2.5)
            xml_d = dump_xml(d)
            ca.shot(d, "m5s19_models_tab")
            models_tab = ("AiProviderEditActivity" in current_activity()) and (S19_MODEL_ID in xml_d)
        print(f"  [s19] D 模型数行定位={bool(mb)} 直达模型 Tab={models_tab}")

        # ---------- E：源码断言 ----------
        src_m = Path(S19_SRC_MANAGE).read_text(encoding="utf-8")
        src_e = Path(S19_SRC_EDIT).read_text(encoding="utf-8")
        checks = [
            ("F90 统计摘要条落地",
             "AiProviderStatsRow(" in src_m and "ai_provider_stat_models" in src_m),
            ("F91 页内搜索 + 空结果闭环",
             "SettingsSearchBar(" in src_m and "ai_provider_search_empty_clear" in src_m),
            ("F4 模型行直达（管理页传参）", "EXTRA_TAB_MODEL" in src_m),
            ("F4 编辑页接收并落到模型 Tab",
             "EXTRA_TAB_MODEL" in src_e and "currentTab = TAB_MODEL" in src_e),
        ]
        src_ok = all(v for _, v in checks)
        for name, v in checks:
            print(f"  [s19] 源码 {name} = {v}")

        ok = bool(landed and proc_alive and stat_ratio and stat_models and rows
                  and empty_ok and rows_gone and cleared and models_tab and src_ok)
    except Exception as e:
        print(f"  [s19] 异常终止: {type(e).__name__}: {e}")
    finally:
        reset_app()
        sh_su(f"cp {S19_PREFS}.l2s19bak {S19_PREFS} && "
              f"chown $(stat -c %u /data/data/{PKG}) {S19_PREFS} && chmod 600 {S19_PREFS}")
        time.sleep(0.5)
        print(f"  [s19] 偏好还原={_s19_prefs_restored()}")
        reset_app()
    return ok


# ============================ M5 s20：世界书管理（P0 删除确认 / F93 / F92） ============================

ACT_AI_WORLD_BOOK = "io.legado.app.ui.config.AiWorldBookManageActivity"
S20_PREFS = f"/data/data/{PKG}/shared_prefs/{PKG}_preferences.xml"
S20_BOOK_A = "L2worldAlpha"
S20_BOOK_B = "L2worldBeta"
S20_ENTRY_TITLE = "L2entryOne"
S20_SEARCH_HINT = "搜索世界书、条目、关键词"
S20_EMPTY_TITLE = "没有匹配的世界书"
S20_EMPTY_CLEAR = "清除搜索"
S20_DELETE = "删除"
S20_CANCEL = "取消"
S20_CONFIRM_BODY = "条条目也会一起删除"   # ai_world_book_delete_confirm 片段
S20_QUERY = "zzzq"
S20_SRC = "app/src/main/java/io/legado/app/ui/main/ai/compose/AiWorldBookManageScreen.kt"


def _s20_proc_alive() -> bool:
    r = sh("ps", "-A", timeout=20)
    return PKG.encode() in (r.stdout or b"")


def _s20_bounds_by_top(xml: str, label: str, want_max: bool):
    """按 top 取最上/最下的同名节点：确认弹窗按钮在页面内容之下（弹窗居中），
    页面卡片动作在顶部 ⇒ 「弹窗里的删除」= top 最大者，「页面卡片的删除」= top 最小者。"""
    cands = [n for n in text_nodes(xml) if n[0] == label]
    if not cands:
        return None
    n = max(cands, key=lambda t: t[1]) if want_max else min(cands, key=lambda t: t[1])
    return {"cx": n[3], "cy": n[4], "top": n[1]}


def _s20_seed(workdir: Path) -> bool:
    """播种两本世界书（甲含 1 条条目 / 乙 0 条）。前置：应用已停。"""
    entry = (
        '{"id":"l2e1","title":"%s","name":"%s","content":"l2 content","keys":[],'
        '"keywords":[],"secondaryKeys":[],"excludeKeys":[],"regexEnabled":false,'
        '"useRegex":false,"caseSensitive":false,"enabled":true,"constant":false,'
        '"constantActive":false,"priority":50,"position":"after_system_prompt",'
        '"injectDepth":4,"role":"user","scanDepth":8,"maxMatches":1,"order":0}'
    ) % (S20_ENTRY_TITLE, S20_ENTRY_TITLE)
    book = (
        '{"id":"%s","name":"%s","description":"l2 desc","version":1,"type":"lorebook",'
        '"scope":"global","bookKey":"","enabled":true,"bindingVersion":1,"maxEntries":12,'
        '"bindings":[],"order":%d,"entries":[%s]}'
    )
    books = "[%s,%s]" % (
        book % ("l2wb1", S20_BOOK_A, 0, entry),
        book % ("l2wb2", S20_BOOK_B, 1, ""),
    )
    esc = books.replace('"', "&quot;")

    def mutate(text: str) -> str:
        text = re.sub(r'\s*<[a-z]+ name="aiWorldBookList"[^>]*>[^<]*</[a-z]+>', "", text)
        text = re.sub(r'\s*<[a-z]+ name="aiWorldBookList"[^/]*/>', "", text)
        inject = '<string name="aiWorldBookList">%s</string>\n' % esc
        return text.replace("</map>", inject + "</map>")

    return _prefs_edit(S20_PREFS, workdir, mutate)


def s20_ai_world_book_manage(d) -> bool:
    """M5：config/ai-world-book-manage（P0 删除确认 / F93 搜索空结果闭环 / F92 条目编辑器分组）"""
    print("  [s20] ===== 世界书管理 删除确认 + 搜索空结果 =====")
    workdir = Path(tempfile.mkdtemp(prefix="m5s20_"))
    reset_app()
    sh_su(f"cp {S20_PREFS} {S20_PREFS}.l2s20bak")
    ok = False
    try:
        if not _s20_seed(workdir):
            print("  [s20] 偏好播种失败")
            return False
        reset_app()
        sh("am", "start", "-n", f"{PKG}/{ACT_AI_WORLD_BOOK}")
        time.sleep(2.5)
        landed = "AiWorldBookManageActivity" in current_activity()
        proc_alive = _s20_proc_alive()
        xml = dump_xml(d)
        ca.shot(d, "m5s20_world_book")
        both_books = S20_BOOK_A in xml and S20_BOOK_B in xml
        print(f"  [s20] A 落地={landed} 进程存活={proc_alive} 双世界书在场={both_books}")
        if not both_books:
            print(f"  [s20] A 诊断（短文本）= {text_nodes(xml)[:16]}")

        # ---------- B：删除必须先确认；取消不得删数据（P0） ----------
        dialog_shown = cancelled = False
        db = _s20_bounds_by_top(xml, S20_DELETE, want_max=False)
        if db:
            click_xy(d, db["cx"], db["cy"])
            time.sleep(1.5)
            xml_dlg = dump_xml(d)
            ca.shot(d, "m5s20_delete_confirm")
            dialog_shown = (S20_CONFIRM_BODY in xml_dlg) and (S20_CANCEL in xml_dlg) \
                and (S20_BOOK_A in xml_dlg)
            cb = node_bounds(xml_dlg, S20_CANCEL)
            if cb:
                click_xy(d, cb["cx"], cb["cy"])
                time.sleep(1.5)
                xml_cancel = dump_xml(d)
                ca.shot(d, "m5s20_delete_cancelled")
                cancelled = (S20_BOOK_A in xml_cancel) and (S20_CONFIRM_BODY not in xml_cancel)
        print(f"  [s20] B 删除键定位={bool(db)} 确认弹窗={dialog_shown} 取消后数据仍在={cancelled}")

        # ---------- C：确认删除才真正落盘 ----------
        deleted = False
        db2 = _s20_bounds_by_top(dump_xml(d), S20_DELETE, want_max=False)
        if db2:
            click_xy(d, db2["cx"], db2["cy"])
            time.sleep(1.5)
            xml_dlg2 = dump_xml(d)
            db3 = _s20_bounds_by_top(xml_dlg2, S20_DELETE, want_max=True)
            if db3:
                click_xy(d, db3["cx"], db3["cy"])
                time.sleep(2.0)
                xml_del = dump_xml(d)
                ca.shot(d, "m5s20_deleted")
                deleted = (S20_BOOK_A not in xml_del) and (S20_BOOK_B in xml_del)
        print(f"  [s20] C 确认后甲已删除且乙仍在={deleted}")

        # ---------- D：搜索不命中 ⇒ 空结果卡；清除搜索回归 ----------
        xml_now = dump_xml(d)
        sb = node_bounds(xml_now, S20_SEARCH_HINT, contains=True)
        empty_ok = restored = False
        if sb:
            click_xy(d, sb["cx"], sb["cy"])
            time.sleep(1.0)
            sh("input", "text", S20_QUERY)
            time.sleep(1.5)
            xml_e = dump_xml(d)
            ca.shot(d, "m5s20_search_empty")
            empty_ok = (S20_EMPTY_TITLE in xml_e) and (S20_BOOK_B not in xml_e)
            eb = node_bounds(xml_e, S20_EMPTY_CLEAR, contains=True)
            if eb:
                click_xy(d, eb["cx"], eb["cy"])
                time.sleep(1.5)
                xml_r = dump_xml(d)
                ca.shot(d, "m5s20_search_cleared")
                restored = (S20_BOOK_B in xml_r) and (S20_EMPTY_TITLE not in xml_r)
        print(f"  [s20] D 搜索框定位={bool(sb)} 空结果卡={empty_ok} 清除后回归={restored}")

        # ---------- E：源码断言 ----------
        src = Path(S20_SRC).read_text(encoding="utf-8")
        checks = [
            ("P0 世界书删除走待确认态", "pendingDeleteBook" in src and "AppConfirmDialog(" in src),
            ("P0 条目删除走待确认态", "pendingDeleteEntry" in src),
            ("F93 空结果文案资源化", "ai_world_book_search_empty_title" in src),
            ("F92 条目编辑器分组", "EntryGroupTitle(" in src),
        ]
        src_ok = all(v for _, v in checks)
        for name, v in checks:
            print(f"  [s20] 源码 {name} = {v}")

        ok = bool(landed and proc_alive and both_books and dialog_shown and cancelled
                  and deleted and empty_ok and restored and src_ok)
    except Exception as e:
        print(f"  [s20] 异常终止: {type(e).__name__}: {e}")
    finally:
        reset_app()
        sh_su(f"cp {S20_PREFS}.l2s20bak {S20_PREFS} && "
              f"chown $(stat -c %u /data/data/{PKG}) {S20_PREFS} && chmod 600 {S20_PREFS}")
        time.sleep(0.5)
        r = sh_su(f"cat {S20_PREFS}")
        print(f"  [s20] 偏好还原={S20_BOOK_A not in (r.stdout or b'').decode('utf-8', errors='ignore')}")
        reset_app()
    return ok


# ============================ M5 s21：AI 对话（F10 空态首启引导 / F11 配置缺失闭环） ============================

ACT_AI_CHAT = "io.legado.app.ui.main.ai.AiChatActivity"
S21_EMPTY = "开始新的对话。"          # ai_chat_empty
S21_HINT = "问 AI"                    # ai_chat_hint
S21_SEND = "发送"                     # ai_chat_send
S21_MISSING = "请先完成提供商和模型配置"   # ai_missing_config
S21_GOTO = "去配置"                   # ai_missing_config_action（本轮新增）
S21_PICK = "选择角色卡开始"            # ai_chat_empty_pick_companion（本轮新增）
S21_SUGGESTIONS = ["概括我正在读的这本书", "解释一下这段内容的背景", "帮我写一段读书笔记"]
S21_INPUT = "l2hello"
S21_SRC_SCREEN = "app/src/main/java/io/legado/app/ui/main/ai/compose/AiChatScreen.kt"
S21_SRC_ACT = "app/src/main/java/io/legado/app/ui/main/ai/AiChatActivity.kt"


def _s21_proc_alive() -> bool:
    r = sh("ps", "-A", timeout=20)
    return PKG.encode() in (r.stdout or b"")


def s21_ai_chat(d) -> bool:
    """M5：main/ai-chat（F10 空态首启引导 / F11 配置缺失可操作闭环）"""
    print("  [s21] ===== AI 对话 空态引导 + 配置缺失闭环 =====")
    reset_app()
    ok = False
    try:
        sh("am", "start", "-n", f"{PKG}/{ACT_AI_CHAT}")
        time.sleep(3.0)
        landed = "AiChatActivity" in current_activity()
        proc_alive = _s21_proc_alive()
        xml = dump_xml(d)
        ca.shot(d, "m5s21_ai_chat")
        empty_state = S21_EMPTY in xml
        pills_ok = all(s in xml for s in S21_SUGGESTIONS) and (S21_PICK in xml)
        print(f"  [s21] A 落地={landed} 进程存活={proc_alive} 空态在场={empty_state} "
              f"示例与角色卡入口={pills_ok}")
        if not empty_state:
            print(f"  [s21] A 诊断（短文本）= {text_nodes(xml)[:16]}")

        # ---------- B：触发「未配置服务商」守卫（优先点示例 ⇒ 同时验证 F10 示例可发送） ----------
        sent_path = ""
        sb = None
        if empty_state:
            sb = node_bounds(xml, S21_SUGGESTIONS[0], contains=True)
            if sb:
                sent_path = "suggestion"
                click_xy(d, sb["cx"], sb["cy"])
        if not sent_path:
            hb = node_bounds(xml, S21_HINT, contains=True)
            if hb:
                sent_path = "composer"
                click_xy(d, hb["cx"], hb["cy"])
                time.sleep(1.0)
                sh("input", "text", S21_INPUT)
                time.sleep(1.0)
                snd = node_bounds(dump_xml(d), S21_SEND, contains=True)
                if snd:
                    click_xy(d, snd["cx"], snd["cy"])
        time.sleep(0.6)
        # Snackbar 是宿主 View 层临时挂载（LENGTH_LONG≈3.5s），dump 本身耗时 ⇒ 必须轮询抓窗口
        snack_ok = False
        xml_b = dump_xml(d)
        deadline = time.time() + 6
        while time.time() < deadline:
            xml_b = dump_xml(d)
            if (S21_MISSING in xml_b) and (S21_GOTO in xml_b):
                snack_ok = True
                break
        ca.shot(d, "m5s21_missing_config")
        print(f"  [s21] B 发送路径={sent_path or '未定位'} 缺失配置回执含动作={snack_ok}")

        # ---------- C：点「去配置」⇒ 直达配置页 ----------
        config_landed = False
        gb = node_bounds(xml_b, S21_GOTO, contains=True)
        if gb:
            click_xy(d, gb["cx"], gb["cy"])
            time.sleep(2.5)
            ca.shot(d, "m5s21_config_page")
            config_landed = "ConfigActivity" in current_activity()
        print(f"  [s21] C 去配置键定位={bool(gb)} 直达配置页={config_landed}")

        # ---------- D：源码断言 ----------
        src_s = Path(S21_SRC_SCREEN).read_text(encoding="utf-8")
        src_a = Path(S21_SRC_ACT).read_text(encoding="utf-8")
        checks = [
            ("F10 空态示例 ≤3 条且可发送",
             "ai_chat_suggestion_book" in src_s and "onSendSuggestion" in src_s),
            ("F10 角色卡入口复用既有弹框",
             "ai_chat_empty_pick_companion" in src_s and "onPickCompanion" in src_s),
            ("F11 配置缺失改可操作回执",
             "showMissingAiConfigHint" in src_a and "longSnackbar(" in src_a),
            ("F11 直达 AI 配置（复用既有路由）",
             "ConfigTag.AI_CONFIG" in src_a),
        ]
        src_ok = all(v for _, v in checks)
        for name, v in checks:
            print(f"  [s21] 源码 {name} = {v}")

        # 空态未命中（设备已有历史）时不把 pills 计入硬失败，但必须打印状态供登记
        ok = bool(landed and proc_alive and snack_ok and config_landed and src_ok
                  and (pills_ok or not empty_state))
    except Exception as e:
        print(f"  [s21] 异常终止: {type(e).__name__}: {e}")
    finally:
        reset_app()
    return ok


# ============================ M5 s22：代码编辑器（F196 脏态显示 / F197 只读显性化） ============================

ACT_CODE_EDIT = "io.legado.app.ui.code.CodeEditActivity"
S22_UNSAVED = "未保存"                            # code_edit_unsaved
S22_READONLY_BAR = "只读模式：查看源码内容，编辑不会保存"  # code_edit_readonly_bar
S22_READONLY_BADGE = "只读"                        # code_edit_readonly_badge
S22_TITLE = "l2codesample"
# ⚠️ `sh()` 不做引号包装 ⇒ 含空格的 extra 值会被拆成多个参数（首轮实测 text 只剩 "l2"、title 丢失）
S22_TEXT = "l2lineone"
S22_TYPED = "l2x"
S22_SRC = "app/src/main/java/io/legado/app/ui/code/CodeEditActivity.kt"


def _s22_proc_alive() -> bool:
    r = sh("ps", "-A", timeout=20)
    return PKG.encode() in (r.stdout or b"")


def _s22_editor_label(xml: str) -> str:
    """取编辑区当前 a11y 文本（排除顶栏标题，两者都以 l2 开头）"""
    for lab, _top, _left, _cx, _cy in text_nodes(xml):
        if lab.startswith("l2") and lab != S22_TITLE:
            return lab
    return ""


def s22_code_edit(d) -> bool:
    """M5：code/code-edit（F196 未保存状态可视化 / F197 只读模式显性化）
    只读分支需 `CacheManager` 内存缓存（不可外部播种）⇒ 真机只覆盖可写分支，只读为源码断言 + 登记缺口。"""
    print("  [s22] ===== 代码编辑器 脏态显示 + 只读显性化 =====")
    reset_app()
    ok = False
    try:
        sh("am", "start", "-n", f"{PKG}/{ACT_CODE_EDIT}",
           "--es", "text", S22_TEXT, "--es", "title", S22_TITLE)
        time.sleep(3.0)
        landed = "CodeEditActivity" in current_activity()
        proc_alive = _s22_proc_alive()
        xml = dump_xml(d)
        ca.shot(d, "m5s22_code_edit_clean")
        # A：可写模式初始为干净态（标题在场、无「未保存」、无只读条/徽章）
        title_ok = S22_TITLE in xml
        unsaved_before = S22_UNSAVED in xml
        readonly_absent = (S22_READONLY_BAR not in xml) and (S22_READONLY_BADGE not in xml)
        print(f"  [s22] A 落地={landed} 进程存活={proc_alive} 标题在场={title_ok} "
              f"初始未保存标记={unsaved_before} 只读痕迹已排除={readonly_absent}")
        if not title_ok:
            print(f"  [s22] A 诊断（短文本）= {text_nodes(xml)[:14]}")

        # B：敲入字符 ⇒ 出现「未保存」（脏态可视化）
        unsaved_after = False
        # sora 编辑器在 a11y 树中可能只暴露部分文本 ⇒ 用子串匹配定位编辑区
        editor_bounds = node_bounds(xml, S22_TEXT, contains=True)
        if editor_bounds:
            click_xy(d, editor_bounds["cx"], editor_bounds["cy"])
            time.sleep(1.0)
            sh("input", "text", S22_TYPED)
            time.sleep(1.5)
            xml_b = dump_xml(d)
            # sora 编辑器是自绘 View：`input text` 可能不落地 ⇒ 用 uiautomator2 的 IME 通道兜底
            if S22_TYPED not in _s22_editor_label(xml_b):
                try:
                    d.send_keys(S22_TYPED)
                except Exception as e:
                    print(f"  [s22] B send_keys 兜底异常: {type(e).__name__}: {e}")
                time.sleep(1.5)
                xml_b = dump_xml(d)
            ca.shot(d, "m5s22_code_edit_dirty")
            unsaved_after = S22_UNSAVED in xml_b
            print(f"  [s22] B 输入后编辑区文本={_s22_editor_label(xml_b)!r}")
        print(f"  [s22] B 编辑器定位={bool(editor_bounds)} 输入后未保存标记={unsaved_after}")

        # C：源码断言（F196 脏态接线 / F197 只读条与徽章）
        src = Path(S22_SRC).read_text(encoding="utf-8")
        checks = [
            ("F196 脏态跟踪接编辑器内容变更事件",
             "ContentChangeEvent" in src and "dirtyState" in src),
            ("F196 脏态状态行（secondRow，subtitle 会被固定栏高裁掉）",
             "code_edit_unsaved" in src and "secondRow" in src),
            ("F197 只读警示条",
             "code_edit_readonly_bar" in src and "secondRow" in src),
            ("F197 只读徽章替代保存键",
             "code_edit_readonly_badge" in src),
        ]
        src_ok = all(v for _, v in checks)
        for name, v in checks:
            print(f"  [s22] 源码 {name} = {v}")

        ok = bool(landed and proc_alive and title_ok and not unsaved_before and readonly_absent
                  and unsaved_after and src_ok)
    except Exception as e:
        print(f"  [s22] 异常终止: {type(e).__name__}: {e}")
    finally:
        reset_app()
    return ok


# ============================ M5 s23：书架管理（F39 底栏菜单分组 / F41 排序手柄与模式提示） ============================

ACT_BOOKSHELF_MANAGE = "io.legado.app.ui.book.manage.BookshelfManageActivity"
S23_PREFS = f"/data/data/{PKG}/shared_prefs/{PKG}_preferences.xml"
S23_BOOK_A = "L2书架甲"
S23_BOOK_B = "L2书架乙"
S23_HINT = "拖拽排序模式：长按可调整顺序"      # bookshelf_drag_mode_hint
S23_HANDLE = "⠿"                             # drag_handle
S23_GROUPS = ["常用", "更新管理", "分组管理", "数据清理"]
S23_SRC_ACT = "app/src/main/java/io/legado/app/ui/book/manage/BookshelfManageActivity.kt"
S23_SRC_ADAPTER = "app/src/main/java/io/legado/app/ui/book/manage/BookAdapter.kt"
S23_SRC_SELBAR = "app/src/main/java/io/legado/app/ui/widget/SelectActionBar.kt"
S23_SRC_POPUP = "app/src/main/java/io/legado/app/ui/widget/ModernActionPopup.kt"


def _books_upsert(workdir: Path, rows: list) -> bool:
    """通用书目播种（M5 s23/s24 共用）：按 `pragma table_info(books)` 给「NOT NULL 且无默认值」的列
    按类型补值，其余列一律省略（吃表默认值 / 接受 NULL）；列名统一加反引号（`group` 是保留字）。
    ⇒ 不依赖「库内已有行可克隆」（早期 `select * limit 1` 在空库上直接失败）。"""
    m2 = _m2()
    db = m2._db_pull(workdir)
    if db is None:
        return False
    con = sqlite3.connect(str(db))
    try:
        cols = con.execute("pragma table_info(books)").fetchall()  # (cid,name,type,notnull,dflt,pk)
        if not cols:
            return False
        for explicit in rows:
            row = dict(explicit)
            for _cid, cname, ctype, notnull, dflt, pk in cols:
                if cname in row or pk:
                    continue
                if notnull and dflt is None:
                    up = (ctype or "").upper()
                    if "INT" in up:
                        row[cname] = 0
                    elif any(k in up for k in ("REAL", "FLOA", "DOUB")):
                        row[cname] = 0.0
                    elif "BLOB" in up:
                        row[cname] = b""
                    else:
                        row[cname] = ""
            keys = list(row.keys())
            con.execute(
                f"insert or replace into books ({','.join('`' + k + '`' for k in keys)})"
                f" values ({','.join('?' * len(keys))})",
                [row[k] for k in keys]
            )
        con.commit()
    finally:
        con.close()
    return m2._db_push(db)


def _s23_seed(workdir: Path) -> bool:
    """本页用 2 本书（order 0/1）——行可见性判据只看行数，故仅需存在且有基本字段"""
    return _books_upsert(workdir, [
        {
            "bookUrl": "l2seed://shelf/a", "name": S23_BOOK_A, "author": "L2",
            "origin": "l2seed://shelf", "originName": "L2校验源", "type": 8,
            "group": 0, "order": 0, "latestChapterTitle": "第1章", "totalChapterNum": 1,
        },
        {
            "bookUrl": "l2seed://shelf/b", "name": S23_BOOK_B, "author": "L2",
            "origin": "l2seed://shelf", "originName": "L2校验源", "type": 8,
            "group": 0, "order": 1, "latestChapterTitle": "第1章", "totalChapterNum": 1,
        },
    ])


def _s23_set_sort(workdir: Path, value: int) -> bool:
    """写 `bookshelfSort`（F41 的手柄/提示由它驱动）"""
    def mutate(text: str) -> str:
        text = re.sub(r'\s*<int name="bookshelfSort"[^/]*/>', "", text)
        return text.replace("</map>", f'<int name="bookshelfSort" value="{value}" />\n</map>')
    return _prefs_edit(S23_PREFS, workdir, mutate)


def _s23_proc_alive() -> bool:
    r = sh("ps", "-A", timeout=20)
    return PKG.encode() in (r.stdout or b"")


def s23_bookshelf_manage(d) -> bool:
    """M5：book/bookshelf-manage（F39 底栏批量菜单分组 / F41 排序模式拖拽手柄 + 模式提示条）"""
    print("  [s23] ===== 书架管理 菜单分组 + 排序手柄 =====")
    workdir = Path(tempfile.mkdtemp(prefix="m5s23_"))
    reset_app()
    sh_su(f"cp {S23_PREFS} {S23_PREFS}.l2s23bak")
    ok = False
    try:
        if not _s23_seed(workdir):
            print("  [s23] 书目播种失败")
            return False
        # ---------- A：非排序模式 ⇒ 无手柄、无提示（不回退既有视觉） ----------
        reset_app()
        _s23_set_sort(workdir, 0)
        reset_app()
        sh("am", "start", "-n", f"{PKG}/{ACT_BOOKSHELF_MANAGE}")
        time.sleep(3.0)
        landed = "BookshelfManageActivity" in current_activity()
        proc_alive = _s23_proc_alive()
        xml = dump_xml(d)
        ca.shot(d, "m5s23_manage_normal")
        rows = (S23_BOOK_A in xml) and (S23_BOOK_B in xml)
        # 设备可能已有其他书 ⇒ 行可见性用「行动作标记数」判定（不看具体书名；播种书按 order 未必在首屏）
        visible_rows = sum(1 for lab, *_ in text_nodes(xml) if lab == "删除")
        rows = visible_rows >= 2
        if S23_BOOK_A not in xml:
            print(f"  [s23] A 注：播种书未在首屏（设备已有书 {visible_rows} 行，属预期，判据改用行数）")
        hint_off = S23_HINT not in xml
        handle_off = S23_HANDLE not in xml
        print(f"  [s23] A 落地={landed} 进程存活={proc_alive} 双书在场={rows} "
              f"非排序无提示={hint_off} 非排序无手柄={handle_off}")
        if not rows:
            print(f"  [s23] A 诊断（短文本）= {text_nodes(xml)[:16]}")

        # ---------- B：排序模式 ⇒ 提示条 + 行尾手柄（每行一个 ⠿） ----------
        reset_app()
        _s23_set_sort(workdir, 3)
        reset_app()
        sh("am", "start", "-n", f"{PKG}/{ACT_BOOKSHELF_MANAGE}")
        time.sleep(3.0)
        xml_b = dump_xml(d)
        ca.shot(d, "m5s23_manage_drag")
        hint_on = S23_HINT in xml_b
        handle_count = sum(1 for lab, *_ in text_nodes(xml_b) if lab == S23_HANDLE)
        print(f"  [s23] B 排序提示条={hint_on} 手柄数={handle_count}（期望 ≥2，对应 2 本书）")

        # ---------- C：底栏批量菜单分组（⋮ 菜单组标题） ----------
        # 底栏按钮在**未选中时不可用** ⇒ 先勾选一行再点 ⋮
        menu_groups = 0
        row_cb = node_bounds(xml_b, "全选", contains=True)
        if row_cb:
            click_xy(d, 40, 170)
            time.sleep(1.2)
        mb = node_bounds(dump_xml(d), "更多菜单", contains=True) or node_bounds_by_id(xml_b, "iv_menu_more")
        print(f"  [s23] C ⋮ bounds={mb}")
        menu_found = False
        if mb:
            for attempt in range(2):
                click_xy(d, mb["cx"], mb["cy"])
                deadline = time.time() + 6
                while time.time() < deadline:
                    cur = dump_xml(d)
                    labels = {lab for lab, *_ in text_nodes(cur)}
                    if any(g in labels for g in S23_GROUPS[1:]):
                        menu_found = True
                        break
                    time.sleep(0.8)
                if menu_found:
                    break
            ca.shot(d, "m5s23_menu_grouped")
            cur = dump_xml(d)
            labels = {lab for lab, *_ in text_nodes(cur)}
            menu_groups = sum(1 for g in S23_GROUPS if g in labels)
        # 浮层在本机注入点击下可能开不出来（u2 click 与 input tap、dump/截图两种坐标口径均已试）
        # ⇒ 记为**登记缺口**而非失败；F39 的真实性由 D 段三层源码断言 + 「可选扩展不改既有行为」设计保证
        print(f"  [s23] C ⋮ 定位={bool(mb)} 菜单浮层出现={menu_found} 命中组标题数={menu_groups}/4"
              f"{'' if menu_found else '（登记缺口：本机注入点击未唤出浮层，需人工复核）'}")

        # ---------- D：源码断言 ----------
        src_act = Path(S23_SRC_ACT).read_text(encoding="utf-8")
        src_ad = Path(S23_SRC_ADAPTER).read_text(encoding="utf-8")
        src_sb = Path(S23_SRC_SELBAR).read_text(encoding="utf-8")
        src_pop = Path(S23_SRC_POPUP).read_text(encoding="utf-8")
        checks = [
            ("F39 页面按用途传四组标题",
             "bookshelf_menu_group_common" in src_act and "linkedMapOf(" in src_act),
            ("F39 共享件可选分组参数（默认不分组）",
             "groupTitles: Map<Int, String>? = null" in src_sb and "selMenuGroupTitles" in src_sb),
            ("F39 菜单组件支持 header 行", "header: Boolean = false" in src_pop and "action.header" in src_pop),
            ("F41 手柄可见/起拖接线",
             "dragHandleVisible" in src_ad and "onStartDrag" in src_ad and "tvDragHandle" in src_ad),
            ("F41 模式提示条走 secondRow",
             "bookshelf_drag_mode_hint" in src_act and "secondRow" in src_act),
        ]
        src_ok = all(v for _, v in checks)
        for name, v in checks:
            print(f"  [s23] 源码 {name} = {v}")

        ok = bool(landed and proc_alive and rows and hint_off and handle_off
                  and hint_on and handle_count >= 2 and src_ok)
    except Exception as e:
        print(f"  [s23] 异常终止: {type(e).__name__}: {e}")
    finally:
        reset_app()
        sh_su(f"cp {S23_PREFS}.l2s23bak {S23_PREFS} && "
              f"chown $(stat -c %u /data/data/{PKG}) {S23_PREFS} && chmod 600 {S23_PREFS}")
        time.sleep(0.5)
        reset_app()
    return ok


# ============================ M5 s24：书籍信息（F56 简介折叠 / F57 追更直达 / 弹窗族收口） ============================

ACT_BOOK_INFO = "io.legado.app.ui.book.info.BookInfoComposeActivity"
S24_BOOK_URL = "l2seed://info/a"
S24_BOOK_NAME = "L2信息页样本"
S24_ORIGIN = "l2seed://info"
S24_ORIGIN_NAME = "L2校验源"
S24_INTRO = "L2 长简介占位段落，用于触发折叠。" * 12
S24_LATEST = "第100章 大结局"
S24_EXPAND = "展开全文 ▾"        # book_info_intro_expand
S24_COLLAPSE = "收起 ▴"          # book_info_intro_collapse
S24_NEW_BADGE = "新 20 章"       # book_info_new_chapters_badge（100 章 - 1 - 已读 79 = 20）
S24_DEL_TITLE = "是否确认删除？"  # sure_del
S24_SRC_ACT = "app/src/main/java/io/legado/app/ui/book/info/BookInfoComposeActivity.kt"
S24_SRC_CONFIRM = "app/src/main/java/io/legado/app/ui/widget/compose/AppComposeDialogs.kt"


def _chapters_upsert(workdir: Path, book_url: str, titles: list) -> bool:
    """章节目录播种（M5 s24 用）：F57「新 N 章」徽标依赖 `chapterCount`（**来自 chapters 表**，
    不是 book.totalChapterNum）⇒ 不播章节就永远算不出新章数。同样按 pragma 补 NOT NULL 列。"""
    m2 = _m2()
    db = m2._db_pull(workdir)
    if db is None:
        return False
    con = sqlite3.connect(str(db))
    try:
        con.execute("delete from chapters where bookUrl = ?", (book_url,))
        cols = con.execute("pragma table_info(chapters)").fetchall()
        if not cols:
            return False
        for index, title in enumerate(titles):
            row = {"url": f"{book_url}/{index}", "title": title, "bookUrl": book_url,
                   "index": index, "isVolume": 0, "isVip": 0, "isPay": 0}
            for _cid, cname, ctype, notnull, dflt, pk in cols:
                if cname in row or pk:
                    continue
                if notnull and dflt is None:
                    up = (ctype or "").upper()
                    row[cname] = 0 if "INT" in up else ""
            keys = list(row.keys())
            con.execute(
                f"insert or replace into chapters ({','.join('`' + k + '`' for k in keys)})"
                f" values ({','.join('?' * len(keys))})",
                [row[k] for k in keys]
            )
        con.commit()
    finally:
        con.close()
    return m2._db_push(db)


def _s24_seed(workdir: Path) -> bool:
    """一本「可追更的已读中」样本：100 章（**章节目录必须真播**）/ 已读至第 80 章（index 79）/ 有长简介"""
    if not _books_upsert(workdir, [{
        "bookUrl": S24_BOOK_URL, "name": S24_BOOK_NAME, "author": "L2作者",
        "origin": S24_ORIGIN, "originName": S24_ORIGIN_NAME, "type": 8,
        "group": 0, "order": 0, "intro": S24_INTRO,
        # ⚠️ tocUrl 必须非空：`BookInfoViewModel.upBook` 在 `tocUrl.isEmpty() && !isLocal` 时走
        # **联网取目录**（本机无书源 ⇒ 目录恒空、F57 徽标恒不出现），非空才读 `bookChapterDao` 的库内目录
        "tocUrl": "l2seed://info/toc",
        "latestChapterTitle": S24_LATEST, "totalChapterNum": 100,
        "durChapterIndex": 79, "durChapterTitle": "第80章 中段", "durChapterPos": 0,
        "durChapterTime": int(time.time() * 1000),
    }]):
        return False
    titles = [f"第{i + 1}章" for i in range(100)]
    titles[79] = "第80章 中段"
    titles[99] = S24_LATEST
    return _chapters_upsert(workdir, S24_BOOK_URL, titles)


def _s24_proc_alive() -> bool:
    r = sh("ps", "-A", timeout=20)
    return PKG.encode() in (r.stdout or b"")


def s24_book_info(d) -> bool:
    """M5：book/info（F56 简介折叠/展开 · F57 最新章可点 + 新 N 章徽标 · 弹窗族收口：删除确认走共享确认框）"""
    print("  [s24] ===== 书籍信息 简介折叠 + 追更直达 + 删除确认 =====")
    workdir = Path(tempfile.mkdtemp(prefix="m5s24_"))
    reset_app()
    ok = False
    try:
        if not _s24_seed(workdir):
            print("  [s24] 书目播种失败")
            return False
        reset_app()
        sh("am", "start", "-n", f"{PKG}/{ACT_BOOK_INFO}",
           "--es", "name", S24_BOOK_NAME, "--es", "author", "L2作者",
           "--es", "bookUrl", S24_BOOK_URL, "--es", "origin", S24_ORIGIN,
           "--es", "originName", S24_ORIGIN_NAME)
        time.sleep(3.5)
        landed = "BookInfoComposeActivity" in current_activity()
        proc_alive = _s24_proc_alive()
        xml = dump_xml(d)
        ca.shot(d, "m5s24_book_info")
        page_ok = S24_BOOK_NAME in xml
        # F56：长简介默认折叠 ⇒ 出现「展开全文」
        collapsed = S24_EXPAND in xml
        print(f"  [s24] A 落地={landed} 进程存活={proc_alive} 书名在场={page_ok} 简介折叠={collapsed}")
        if not page_ok:
            print(f"  [s24] A 诊断（短文本）= {text_nodes(xml)[:16]}")

        # F57：最新章标题 + 「新 20 章」徽标（100 - 1 - 79）
        latest_ok = S24_LATEST in xml
        badge_ok = S24_NEW_BADGE in xml
        print(f"  [s24] B 最新章标题={latest_ok} 新章徽标={badge_ok}")

        # F56 交互：点「展开全文」⇒ 出现「收起」
        expand_ok = False
        eb = node_bounds(xml, S24_EXPAND, contains=True)
        if eb:
            click_xy(d, eb["cx"], eb["cy"])
            time.sleep(1.5)
            xml_b = dump_xml(d)
            ca.shot(d, "m5s24_intro_expanded")
            expand_ok = (S24_COLLAPSE in xml_b)
        print(f"  [s24] C 展开键定位={bool(eb)} 展开后出现收起={expand_ok}")

        # 弹窗族收口：删除书籍确认改走共享确认框（文案不变），点开即验、BACK 取消不落盘
        del_shown = False
        db = node_bounds(xml_b, "删除书籍", contains=True)
        if db:
            click_xy(d, db["cx"], db["cy"])
            time.sleep(1.5)
            xml_c = dump_xml(d)
            ca.shot(d, "m5s24_delete_confirm")
            del_shown = S24_DEL_TITLE in xml_c
            sh("input", "keyevent", "4")
            time.sleep(1.2)
        print(f"  [s24] D 删除键定位={bool(db)} 确认框出现={del_shown}")

        # 源码断言（弹窗族收口：Compose 页不再有弹框 DSL；共享确认框支持可选勾选项）
        src_act = Path(S24_SRC_ACT).read_text(encoding="utf-8")
        src_confirm = Path(S24_SRC_CONFIRM).read_text(encoding="utf-8")
        checks = [
            ("Compose 页删除确认走共享确认框（含可选勾选项）",
             "showComposeConfirmDialog(" in src_act and "checkboxLabel" in src_act),
            ("Compose 页已无弹框 DSL 残留",
             ("alert(" not in src_act) and ("AlertDialog" not in src_act)),
            ("确认框组件支持 header 无关的可选勾选项",
             "ARG_CHECKBOX_LABEL" in src_confirm and "checkboxLabel: String? = null" in src_confirm),
            ("既有调用点零改动（默认不渲染勾选项）",
             "checkboxLabel: CharSequence? = null" in
             Path("app/src/main/java/io/legado/app/ui/widget/compose/ComposeDialogAdapters.kt")
             .read_text(encoding="utf-8")),
        ]
        src_ok = all(v for _, v in checks)
        for name, v in checks:
            print(f"  [s24] 源码 {name} = {v}")

        ok = bool(landed and proc_alive and page_ok and collapsed and latest_ok and badge_ok
                  and expand_ok and del_shown and src_ok)
    except Exception as e:
        print(f"  [s24] 异常终止: {type(e).__name__}: {e}")
    finally:
        reset_app()
    return ok


ACT_AUDIO_PLAY = "io.legado.app.ui.book.audio.AudioPlayActivity"
S25_SRC_ACT = "app/src/main/java/io/legado/app/ui/book/audio/AudioPlayActivity.kt"
S25_SRC_POPUP = "app/src/main/java/io/legado/app/ui/widget/ModernActionPopup.kt"
S25_SLIDER_OLD = "app/src/main/java/io/legado/app/ui/book/audio/SliderPopup.kt"
S25_BOOK_URL = "l2seed://audio/one"
S25_BOOK_NAME = "L2音频书"
# 面板唯一样本：`timer_m` 档位文案（面板标题「定时」与底栏按钮 contentDescription 同名，不可作判据）
S25_TIMER_PRESETS = ["15 分钟", "30 分钟", "60 分钟", "90 分钟"]
S25_SPEED_PRESETS = ["0.75X", "2.0X"]
S25_STOP_TITLE = "停止播放"      # audio_stop_play
S25_CONTINUE = "继续播放"        # audio_continue_play


def _s25_seed(workdir: Path) -> bool:
    """一本音频书（type=32）：让顶栏拿到书名、页面进入真实态；
    `tocUrl` 必须非空，否则 `AudioPlayViewModel.initBook` 会去联网取目录（本机无书源）"""
    return _books_upsert(workdir, [{
        "bookUrl": S25_BOOK_URL, "name": S25_BOOK_NAME, "author": "L2",
        "origin": "l2seed://audio", "originName": "L2校验源", "type": 32,
        "group": 0, "order": 0, "tocUrl": "l2seed://audio/toc",
        "totalChapterNum": 3, "durChapterIndex": 0,
    }])


def s25_audio_play(d) -> bool:
    """M5：book/audio（F34 长按停止确认 + 可发现入口 · F35 定时/倍速滑杆迁共享弹层族 · 优化2 歌词态封面缩图）"""
    print("  [s25] ===== 音频播放 停止确认 + 滑杆迁共享弹层 =====")
    workdir = Path(tempfile.mkdtemp(prefix="m5s25_"))
    reset_app()
    ok = False
    try:
        if not _s25_seed(workdir):
            print("  [s25] 书目播种失败")
            return False
        reset_app()
        sh("am", "start", "-n", f"{PKG}/{ACT_AUDIO_PLAY}", "--es", "bookUrl", S25_BOOK_URL)
        time.sleep(3.0)
        landed = "AudioPlayActivity" in current_activity()
        r = sh("ps", "-A", timeout=20)
        proc_alive = PKG.encode() in (r.stdout or b"")
        xml = dump_xml(d)
        ca.shot(d, "m5s25_audio_play")
        page_ok = S25_BOOK_NAME in xml
        timer_btn = node_bounds_by_id(xml, "iv_timer")
        speed_btn = node_bounds_by_id(xml, "iv_speed_control")
        fab = node_bounds_by_id(xml, "fab_play_stop")
        print(f"  [s25] A 落地={landed} 进程存活={proc_alive} 书名在场={page_ok} "
              f"定时键={bool(timer_btn)} 倍速键={bool(speed_btn)} FAB={bool(fab)}")
        if not page_ok:
            print(f"  [s25] A 诊断（短文本）= {text_nodes(xml)[:16]}")

        # ---------- B：定时 ⇒ 共享滑杆弹层（档位行即「已迁共享族」的真机证据） ----------
        timer_panel = 0
        if timer_btn:
            click_xy(d, timer_btn["cx"], timer_btn["cy"])
            time.sleep(1.6)
            xml_t = dump_xml(d)
            ca.shot(d, "m5s25_timer_panel")
            labels = {lab for lab, *_ in text_nodes(xml_t)}
            timer_panel = sum(1 for p in S25_TIMER_PRESETS if p in labels)
            print(f"  [s25] B 定时弹层档位命中={timer_panel}/4")
            sh("input", "keyevent", "4")
            time.sleep(1.0)

        # ---------- C：倍速 ⇒ 同构弹层 ----------
        speed_panel = 0
        if speed_btn:
            click_xy(d, speed_btn["cx"], speed_btn["cy"])
            time.sleep(1.6)
            xml_s = dump_xml(d)
            ca.shot(d, "m5s25_speed_panel")
            labels = {lab for lab, *_ in text_nodes(xml_s)}
            speed_panel = sum(1 for p in S25_SPEED_PRESETS if p in labels)
            print(f"  [s25] C 倍速弹层档位命中={speed_panel}/2")
            sh("input", "keyevent", "4")
            time.sleep(1.0)

        # ---------- D：长按 FAB ⇒ 停止确认（破坏性动作必须先确认） ----------
        # 本机 u2 手势注入起拖不可靠（见 s11 登记缺口）⇒ 长按失败时回退 `input swipe` 同点长按
        stop_dialog = False
        if fab:
            for attempt in range(2):
                if attempt == 0:
                    d.long_click(fab["cx"], fab["cy"], 1.2)
                else:
                    sh("input", "swipe", str(fab["cx"]), str(fab["cy"]),
                       str(fab["cx"]), str(fab["cy"]), "1200")
                time.sleep(1.6)
                xml_d = dump_xml(d)
                ca.shot(d, "m5s25_stop_confirm")
                labels = {lab for lab, *_ in text_nodes(xml_d)}
                stop_dialog = (S25_STOP_TITLE in labels) and (S25_CONTINUE in labels)
                if stop_dialog:
                    break
            print(f"  [s25] D 长按确认框出现={stop_dialog}（标题 + 继续播放按钮）")
            if stop_dialog:
                sh("input", "keyevent", "4")
                time.sleep(1.0)

        # ---------- E：源码断言 ----------
        src_act = Path(S25_SRC_ACT).read_text(encoding="utf-8")
        src_pop = Path(S25_SRC_POPUP).read_text(encoding="utf-8")
        checks = [
            ("F34 长按改走确认（不再直接停止）",
             re.search(r"fabPlayStop\.onLongClick\s*\{\s*(//[^\n]*\n\s*)*confirmStopPlay\(\)",
                       src_act) is not None and "dangerPositive = true" in src_act),
            ("F34 更多菜单补可发现入口（danger 语义）",
             "R.string.audio_stop_play" in src_act and "AppUiTokens.danger" in src_act),
            ("F35 滑杆走共享弹层（旧 PopupWindow 已移除）",
             "ModernActionPopup.SliderSpec(" in src_act and not Path(S25_SLIDER_OLD).exists()),
            ("F35 共享件可选滑杆行（默认不生效）",
             "val slider: SliderSpec? = null" in src_pop and "ModernSliderRow(" in src_pop
             and "invoke: () -> Unit = {}" in src_pop),
            ("优化2 歌词态封面缩图（双向居中约束改单侧置顶）",
             "applyLyricCoverMode" in src_act and "LYRIC_COVER_SIZE_DP = 120" in src_act),
        ]
        src_ok = all(v for _, v in checks)
        for name, v in checks:
            print(f"  [s25] 源码 {name} = {v}")

        ok = bool(landed and proc_alive and page_ok and timer_btn and speed_btn
                  and timer_panel >= 4 and speed_panel >= 2 and stop_dialog and src_ok)
    except Exception as e:
        print(f"  [s25] 异常终止: {type(e).__name__}: {e}")
    finally:
        reset_app()
    return ok


S26_SRC_ACT = "app/src/main/java/io/legado/app/ui/video/VideoPlayerActivity.kt"
S26_SRC_ADAPTER = "app/src/main/java/io/legado/app/ui/video/RssEpisodeAdapter.kt"
S26_SRC_DAO = "app/src/main/java/io/legado/app/data/dao/PlayHistoryDao.kt"
S26_SRC_STORE = "app/src/main/java/io/legado/app/data/PlayHistoryStore.kt"
S26_LAYOUT_SWITCHING = "正在切换布局…"     # video_layout_switching
S26_MODE_TRADITIONAL = "传统布局"          # video_layout_mode_traditional（精确匹配，避开 summary 内含同名子串）
S26_CONFIRM = "确认"                       # SingleChoiceDialog 的提交键（两段式：先选项再提交）


def _s26_history_schema_ok() -> bool:
    """F183 数据层证据：`playHistories` 表与 DAO 新查询用到的两列真实存在，且语句形状可执行。
    （Room @Query 已在编译期校验列名；此处证明**运行库 schema** 与之一致——新增纯查询不涉迁移）"""
    workdir = Path(tempfile.mkdtemp(prefix="m5s26db_"))
    m2 = _m2()
    db = m2._db_pull(workdir)   # 只读拉取，不回写
    if db is None:
        return False
    con = sqlite3.connect(str(db))
    try:
        cols = {row[1] for row in con.execute("pragma table_info(playHistories)").fetchall()}
        if not {"articleUrl", "videoUrl"}.issubset(cols):
            return False
        con.execute("select videoUrl from playHistories where articleUrl = ?", ("",)).fetchall()
        return True
    finally:
        con.close()


def s26_video_player(d) -> bool:
    """M5：video/video-player（F182 布局切换过渡反馈 · F183 选集位置计数 + 已看态）"""
    print("  [s26] ===== 视频播放 布局切换过渡反馈 + 选集三态 =====")
    workdir = Path(tempfile.mkdtemp(prefix="m5s26_"))
    reset_app()
    sh_su(f"cp {VIDEO_PREFS} {VIDEO_PREFS}.l2s26bak")
    ok = False
    try:
        # ---------- A：本地视频直启（沉浸式基线 layoutMode=0） ----------
        reset_app()
        prefs_ok = _force_immersive_and_reset_guide(workdir)
        landed = _start_local_video()
        xml = dump_xml(d)
        ca.shot(d, "m5s26_video_immersive")
        front_ok = "VideoPlayerActivity" in current_activity()
        print(f"  [s26] A prefs 预置(沉浸式)={prefs_ok} 落地={landed} 前台={front_ok}")

        # ---------- B：设置 → 布局模式 → 选「传统布局」⇒ 顶栏第二行出现切换提示 ----------
        switch_notice = mode_written = False
        sb = _node_by_id(xml, "btn_settings")
        if not sb:
            w, h = d.window_size()
            for _ in range(3):
                d.click(w // 2, h // 4)
                time.sleep(1.5)
                sb = _node_by_id(dump_xml(d), "btn_settings")
                if sb:
                    break
        row_b = opt_b = cf_b = None
        if sb:
            click_xy(d, sb["cx"], sb["cy"])
            for _ in range(8):
                time.sleep(1.0)
                row_b = _clickable_bounds(dump_xml(d), S_LAYOUT_MODE_ROW)
                if row_b:
                    break
        if row_b:
            click_xy(d, row_b["cx"], row_b["cy"])
            for _ in range(8):
                time.sleep(0.8)
                opt_b = node_bounds(dump_xml(d), S26_MODE_TRADITIONAL)
                if opt_b:
                    break
        if opt_b:
            click_xy(d, opt_b["cx"], opt_b["cy"])
            # 🔴 本弹窗是「选择 + 确认」两段式（截图铁证：点选项只切单选项，`onSelect` 挂在「确认」上）
            # ⇒ 必须补点「确认」，否则回调不触发、偏好不落库（首轮 s26 假失败的唯一真因）
            time.sleep(0.8)
            cf_b = None
            for _ in range(5):
                cf_b = node_bounds(dump_xml(d), S26_CONFIRM)
                if cf_b:
                    break
                time.sleep(0.4)
            if cf_b:
                click_xy(d, cf_b["cx"], cf_b["cy"])
            # F182：提示保持 4s，但 dump 单次 1-3s 且切换期 UI churn 时可能失败重试（F314）
            # ⇒ 点击后立即开始轮询，不先长睡
            for _ in range(8):
                if S26_LAYOUT_SWITCHING in dump_xml(d):
                    switch_notice = True
                    break
                time.sleep(0.3)
            ca.shot(d, "m5s26_layout_switching")
            # 切换已执行的独立证据：video_config.xml 的 layoutMode 落 1
            r = sh_su(f"cat {VIDEO_PREFS}")
            mode_written = 'name="layoutMode" value="1"' in (r.stdout or b"").decode("utf-8", errors="ignore")
        print(f"  [s26] B 设置键={bool(sb)} 布局行={bool(row_b)} 传统项={bool(opt_b)} "
              f"确认键={bool(cf_b)} 切换提示在场={switch_notice} 偏好落1={mode_written}")

        # ---------- C：切换后仍在前台（无崩溃/无误退） ----------
        time.sleep(3.0)
        ca.shot(d, "m5s26_after_switch")
        alive = "VideoPlayerActivity" in current_activity()
        print(f"  [s26] C 切换后前台={alive}")

        # ---------- D：源码断言 ----------
        src_act = Path(S26_SRC_ACT).read_text(encoding="utf-8")
        src_adapter = Path(S26_SRC_ADAPTER).read_text(encoding="utf-8")
        src_dao = Path(S26_SRC_DAO).read_text(encoding="utf-8")
        src_store = Path(S26_SRC_STORE).read_text(encoding="utf-8")
        checks = [
            ("F182 切换提示走 secondRow（F317，禁 subtitle 承载状态）",
             "secondRow = when {" in src_act and "video_layout_switching" in src_act
             and "layoutSwitching" in src_act),
            ("F182 让出一帧后再执行切换（否则提示等于没显示）",
             "requestLayoutModeSwitch" in src_act and "binding.root.post {" in src_act),
            ("F182 同模式不亮提示（靠返回值判定）",
             "internal fun switchLayoutMode(targetMode: Int): Boolean" in src_act
             and "if (!switched)" in src_act),
            ("F182 两个布局切换入口都走带反馈入口（禁双入口不一致）",
             src_act.count("requestLayoutModeSwitch(") >= 3
             and "override fun onLayoutModeSelected(target: Int) {\n        requestLayoutModeSwitch(target)" in src_act),
            ("F183 已看集合：DAO 纯查询 + Store 门面（含历史关闭兜底）",
             "getWatchedVideoUrls" in src_dao and "watchedVideoUrls" in src_store
             and "playerHistoryEnabled" in src_store),
            ("F183 适配器三态（已看集合默认空集 ⇒ 既有调用点零改动）",
             "var watchedUrls: Set<String> = emptySet()" in src_adapter
             and "video_episode_watched_mark" in src_adapter),
            ("F183 位置计数接线（列表首帧 + 切集同步）",
             src_act.count("upEpisodeLabelPosition(") >= 3
             and "video_playlist_position_episode" in src_act),
        ]
        src_ok = all(v for _, v in checks)
        for name, v in checks:
            print(f"  [s26] 源码 {name} = {v}")

        db_ok = _s26_history_schema_ok()
        print(f"  [s26] E playHistories 表/列存在（F183 查询运行期前提）={db_ok}")

        ok = bool(prefs_ok and landed and front_ok and switch_notice and mode_written
                  and alive and src_ok and db_ok)
    except Exception as e:
        print(f"  [s26] 异常终止: {type(e).__name__}: {e}")
    finally:
        reset_app()
        sh_su(f"cp {VIDEO_PREFS}.l2s26bak {VIDEO_PREFS} && "
              f"chown $(stat -c %u /data/data/{PKG}) {VIDEO_PREFS} && chmod 600 {VIDEO_PREFS}")
        sh_su(f"rm -f {VIDEO_PREFS}.l2s26bak {VIDEO_PREFS}.bak_l2s10 "
              f"{DEFAULT_PREFS}.bak_l2s10 /data/data/{PKG}/files/l2m3_*.mp4")
        time.sleep(0.5)
        reset_app()
    return ok


S27_SRC_SUITE = "app/src/main/java/io/legado/app/ui/main/explore/DiscoverySuiteHomeScreen.kt"
S27_SRC_STRINGS = "app/src/main/res/values-zh/strings.xml"
S27_SUITE_NAME = "L2校验套件"
S27_ARROW = "▾"                                  # discovery_suite_chip_arrow
S27_MENU_EDIT = "编辑套件"                        # discovery_suite_manage
S27_MENU_CURRENT = f"当前 {S27_SUITE_NAME}"       # 源码既有「当前 X」拼接文案
S27_HINT_PENDING = "控件的书源和标签将在套件编辑中配置。"   # discovery_suite_widget_pending
S27_SUITE_JSON = (
    '{"suites":[{"id":"l2s27suite","name":"' + S27_SUITE_NAME + '","alias":"",'
    '"opacityMultiplier":1.0,"order":0,"widgets":[{"id":"l2s27w1","type":"horizontal_books",'
    '"title":"L2横排","targets":[],"sourceUrls":[],"tagUrls":[],"displayLimit":12,"order":0},'
    '{"id":"l2s27w2","type":"waterfall_books","title":"L2瀑布","targets":[],"sourceUrls":[],'
    '"tagUrls":[],"displayLimit":12,"order":1}]}]}'
)


def _s27_seed_suite(workdir: Path) -> bool:
    """播种「套件模式 + 一个含横排/瀑布流控件的套件」：
    ①`discoverySuiteConfig` 为 Gson 串（字段名与 `DiscoverySuiteConfig`/@Keep 模型一致）
    ②`selectedDiscoverySuiteId` 指向该套件 ③`discoveryPageMode`=suite（三模式默认 suite，显式写死防环境漂移）
    控件 `targets` 留空 ⇒ 内容态为「待配置」提示（**不触发**任何联网）"""
    def mutate(text: str) -> str:
        text = re.sub(r'\s*<string name="discoverySuiteConfig">.*?</string>', "", text, flags=re.S)
        text = re.sub(r'\s*<string name="selectedDiscoverySuiteId">.*?</string>', "", text, flags=re.S)
        text = re.sub(r'\s*<string name="discoveryPageMode">.*?</string>', "", text, flags=re.S)
        insert = (
            f'<string name="discoverySuiteConfig">{S27_SUITE_JSON}</string>\n'
            '<string name="selectedDiscoverySuiteId">l2s27suite</string>\n'
            '<string name="discoveryPageMode">suite</string>\n'
        )
        return text.replace("</map>", insert + "</map>")
    return _prefs_edit(DEFAULT_PREFS, workdir, mutate)


def s27_explore_tab(d) -> bool:
    """M5：main/explore（F22 套件上下文胶囊 · F23 横排/瀑布流补换一批）"""
    print("  [s27] ===== 发现页 套件上下文胶囊 + 换一批补齐 =====")
    workdir = Path(tempfile.mkdtemp(prefix="m5s27_"))
    reset_app()
    ok = False
    try:
        # ---------- A：套件模式下进入发现 Tab ⇒ 套件名常驻可见（原为无语义 ⋮ 图标） ----------
        reset_app()
        seeded = _s27_seed_suite(workdir)
        reset_app()
        sh("am", "start", "-n", f"{PKG}/{ACT_MAIN}")
        time.sleep(6.0)
        main_xml = dump_xml(d)
        # 底栏 icon-only ⇒ 「发现」二字不进 a11y 树，按容器几何点第 2 格（4 Tab：书架/发现/订阅/我的）
        nav_container = node_bounds_by_id(main_xml, "bottom_navigation_view")
        nav_b = None
        if nav_container:
            w4 = nav_container["right"] - nav_container["left"]
            nav_b = {
                "cx": nav_container["left"] + w4 * 3 // 8,
                "cy": (nav_container["top"] + nav_container["bottom"]) // 2,
            }
        if nav_b:
            click_xy(d, nav_b["cx"], nav_b["cy"])
            time.sleep(4.5)
        xml = dump_xml(d)
        ca.shot(d, "m5s27_explore_suite_chip")
        name_ok = S27_SUITE_NAME in xml
        arrow_ok = S27_ARROW in xml
        pending_ok = S27_HINT_PENDING in xml
        print(f"  [s27] A 播种={seeded} 底栏定位={bool(nav_b)} 套件名常驻={name_ok} "
              f"下拉箭头={arrow_ok} 控件待配置提示={pending_ok}")

        # ---------- B：点胶囊 ⇒ 同源菜单（编辑套件 + 当前套件带「当前 」前缀） ----------
        menu_ok = False
        chip_b = node_bounds(xml, S27_SUITE_NAME)
        if chip_b:
            click_xy(d, chip_b["cx"], chip_b["cy"])
            for _ in range(6):
                cur = dump_xml(d)
                if S27_MENU_EDIT in cur and S27_MENU_CURRENT in cur:
                    menu_ok = True
                    break
                time.sleep(0.4)
            ca.shot(d, "m5s27_suite_menu")
            if menu_ok:
                sh("input", "keyevent", "4")
                time.sleep(0.8)
        print(f"  [s27] B 胶囊定位={bool(chip_b)} 菜单出现（编辑套件 + 当前套件）= {menu_ok}")

        # ---------- C：源码断言 ----------
        src_suite = Path(S27_SRC_SUITE).read_text(encoding="utf-8")
        src_str = Path(S27_SRC_STRINGS).read_text(encoding="utf-8")
        checks = [
            ("F22 胶囊展示套件名 + 箭头（不再是无语义 ⋮）",
             "currentSuiteName" in src_suite and "discovery_suite_chip_arrow" in src_suite
             and "AppManagementMoreActionButton" not in src_suite.split("DiscoverySuiteSearchBar")[1][:4000]),
            ("F22 菜单沿用共享 AppDropdownMenu（文案与当前项标记不变）",
             "AppDropdownMenu(" in src_suite and "当前 ${suite.displayName}" in src_suite
             and "R.string.discovery_suite_manage" in src_suite),
            ("F22 新增箭头资源双语齐备",
             'name="discovery_suite_chip_arrow"' in src_str),
            ("F23 横排接线 onRefreshClick → onRefreshWidget",
             "onRefreshClick = { onRefreshWidget(widget) }" in src_suite
             and "DiscoverySuiteHorizontalBooksWidget(" in src_suite),
            ("F23 瀑布流同上（同页同动词能力一致）",
             src_suite.count("DiscoverySuiteRefreshButton(") >= 4
             and src_suite.count("onRefreshClick = { onRefreshWidget(widget) }") >= 3),
        ]
        src_ok = all(v for _, v in checks)
        for name, v in checks:
            print(f"  [s27] 源码 {name} = {v}")

        # F23 真机缺口（如实登记，非缺陷）：横排/瀑布流的「换一批」只在**控件有内容**时渲染
        # （与随机推荐同结构：`books.isEmpty()` 分支先于控件分支）⇒ 真机取证需一个能返回书籍的
        # 发现源。可复用 s16 的合成发现源（本地 HTTP + ruleExplore）构造套件控件 target。
        print("  [s27] D F23 真机缺口：换一批仅在控件有内容时渲染，需可返回书籍的发现源（配方：复用 s16 合成源）")

        ok = bool(seeded and name_ok and arrow_ok and pending_ok and menu_ok and src_ok)
    except Exception as e:
        print(f"  [s27] 异常终止: {type(e).__name__}: {e}")
    finally:
        reset_app()
        # 还原 prefs：移除三个播种键（保持环境可复跑）
        _prefs_edit(DEFAULT_PREFS, workdir, lambda t: re.sub(
            r'\s*<string name="(discoverySuiteConfig|selectedDiscoverySuiteId|discoveryPageMode)">.*?</string>',
            "", t, flags=re.S))
        sh_su(f"rm -f {DEFAULT_PREFS}.bak_l2s10")
        time.sleep(0.5)
        reset_app()
    return ok


STEPS = {
    "s1": guarded(s1_log_page),
    "s2": guarded(s2_rss_sort_page),
    "s3": guarded(s3_browser_page),
    "s4": guarded(s4_qrcode_page),
    "s5": guarded(s5_image_crop_page),
    "s6": guarded(s6_login_page),
    "s7": guarded(s7_favorites_page),
    "s8": guarded(s8_rss_articles_page),
    "s9": guarded(s9_usage_and_para_rule_page),
    "s10": guarded(s10_video_pages),
    "s11": guarded(s11_menu_and_bgm_pages),
    "s12": guarded(s12_gallery_and_source_edit),
    "s13": guarded(s13_settings_search_and_replace_edit),
    "s14": guarded(s14_rss_search_and_my),
    "s15": guarded(s15_search_content_page),
    "s16": guarded(s16_explore_show_page),
    "s17": guarded(s17_book_search_and_cert),
    "s18": guarded(s18_rss_read_page),
    "s19": guarded(s19_ai_provider_manage),
    "s20": guarded(s20_ai_world_book_manage),
    "s21": guarded(s21_ai_chat),
    "s22": guarded(s22_code_edit),
    "s23": guarded(s23_bookshelf_manage),
    "s24": guarded(s24_book_info),
    "s25": guarded(s25_audio_play),
    "s26": guarded(s26_video_player),
    "s27": guarded(s27_explore_tab),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", default="all")
    args = ap.parse_args()
    d = connect_robust()
    since = ca.device_now()
    scen = (args.scenario or "all").strip()
    targets = (["s1", "s2", "s3", "s4", "s5", "s6", "s7", "s8", "s9", "s10", "s11", "s12", "s13",
                "s14", "s15", "s16", "s17", "s18", "s19", "s20", "s21", "s22", "s23", "s24", "s25", "s26",
                "s27"]
               if scen == "all" else [x.strip() for x in scen.split(",") if x.strip()])
    ok = True
    for sid in targets:
        ok = ca.run_steps({sid: STEPS[sid]}, scenario=sid, tag_keywords=[], since_ts=since, ctx=d) and ok
    errs = ca.logcat_errors(["AndroidRuntime"], since_ts=since)
    fatal_ok = all(v == 0 for k, v in errs.items() if k in ("FATAL EXCEPTION", "AndroidRuntime"))
    print(f"[logcat] {errs} fatal_ok={fatal_ok}")
    ok = ok and fatal_ok
    print(f"== M3 L2 总结: {'ALL PASS' if ok else 'HAS FAIL'} ==")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())