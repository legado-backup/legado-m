# -*- coding: utf-8 -*-
"""l2_verify_m3_pages.py — M3 批（设置与阅读器配置页 14 页）真机 L2 验证，按落地顺序增量登记

已覆盖：
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

执行（铁律）：ai_tests\\venv\\Scripts\\python.exe ai_tests/scripts/l2_verify_m3_pages.py [--scenario s1|s3|s4|s5|s6|s7|all]
前置：MEmu 已启动；测试包 io.legado.miss.app.debug 已安装；openssl（Git 自带，脚本自动定位）

口径说明（F192）：跨年分支需要「去年」的日志条目，真机沙箱无法构造跨年数据（AppLog 为内存日志，
时间戳由运行时写入）。本脚本对**同年分支**做真机断言（时间列形状回归），对**跨年分支**做源码存在性断言，
并在 tasks.md 登记为「逻辑分支未构造真机数据」——不伪称真机已覆盖。
"""
import argparse
import re
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


def guarded(fn):
    def inner(d):
        try:
            return fn(d)
        except Exception as e:
            print(f"  [EXC] {type(e).__name__}: {e}")
            return False

    inner.__name__ = getattr(fn, "__name__", "step")
    return inner


STEPS = {
    "s1": guarded(s1_log_page),
    "s2": guarded(s2_rss_sort_page),
    "s3": guarded(s3_browser_page),
    "s4": guarded(s4_qrcode_page),
    "s5": guarded(s5_image_crop_page),
    "s6": guarded(s6_login_page),
    "s7": guarded(s7_favorites_page),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", default="all")
    args = ap.parse_args()
    d = connect_robust()
    since = ca.device_now()
    scen = (args.scenario or "all").strip()
    targets = ["s1", "s2", "s3", "s4", "s5", "s6", "s7"] if scen == "all" else [x.strip() for x in scen.split(",") if x.strip()]
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