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

执行（铁律）：ai_tests\\venv\\Scripts\\python.exe ai_tests/scripts/l2_verify_m3_pages.py [--scenario s1|all]
前置：MEmu 已启动；测试包 io.legado.miss.app.debug 已安装

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
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", default="all")
    args = ap.parse_args()
    d = connect_robust()
    since = ca.device_now()
    scen = (args.scenario or "all").strip()
    targets = ["s1", "s2"] if scen == "all" else [x.strip() for x in scen.split(",") if x.strip()]
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