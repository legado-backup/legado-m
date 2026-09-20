# -*- coding: utf-8 -*-
"""l2_verify_m3_pages.py — M3 批（设置与阅读器配置页 14 页）真机 L2 验证，按落地顺序增量登记

已覆盖：
  【log/log · LogActivity】F190 命中计数条 + 关键词高亮 + 一键清除筛选；F191 详情逐条翻阅；F192 跨年时间补年份
    s1 搜索命中计数与清除筛选（文本口径）→ 同一行「搜索前/后」前景色像素对比证明高亮渲染
       → 点行开详情弹窗（位置指示 N/M）→ › 翻阅后指示递增 → 关窗
       → 时间列同口径回归（`MM-dd HH:mm:ss`）；F192 跨年分支以源码断言兜底（见脚本末尾口径说明）

执行（铁律）：ai_tests\\venv\\Scripts\\python.exe ai_tests/scripts/l2_verify_m3_pages.py [--scenario s1|all]
前置：MEmu 已启动；测试包 io.legado.miss.app.debug 已安装

口径说明（F192）：跨年分支需要「去年」的日志条目，真机沙箱无法构造跨年数据（AppLog 为内存日志，
时间戳由运行时写入）。本脚本对**同年分支**做真机断言（时间列形状回归），对**跨年分支**做源码存在性断言，
并在 tasks.md 登记为「逻辑分支未构造真机数据」——不伪称真机已覆盖。
"""
import argparse
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

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
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", default="all")
    args = ap.parse_args()
    d = connect_robust()
    since = ca.device_now()
    scen = (args.scenario or "all").strip()
    targets = ["s1"] if scen == "all" else [x.strip() for x in scen.split(",") if x.strip()]
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