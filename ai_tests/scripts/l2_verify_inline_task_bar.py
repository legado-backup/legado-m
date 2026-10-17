"""l2_verify_inline_task_bar.py — A2.4.5 真机验证：书源管理页 InlineTaskBar（进度横幅 + 取消）

覆盖：
  T1 多选 → 更多菜单 → 「校验所选」→ 确认对话框 → 横幅渲染（含「取消」与「进度」文案）
  T2 点「取消」→ 横幅消失（状态回到 Idle）
  T3 全程无 FATAL EXCEPTION

背景：`InlineTaskBar` 由 `BookSourceScreen` 原私有 `CheckProgressBanner` 提升泛化而来
（A2.4.5 复用提升），本脚本即验证提升后消费点行为不变。

前置：测试包已安装且**书源列表非空**（空列表无法进入多选 → 会明确报 FAIL 原因）。

用法:
    ai_tests\\venv\\Scripts\\python.exe ai_tests/scripts/l2_verify_inline_task_bar.py [--shot out.png]
"""
import argparse
import subprocess
import sys
import time

import uiautomator2 as u2

ADB = r"C:\Android\Sdk\platform-tools\adb.exe"
HOST = "127.0.0.1:21503"
PKG = "io.legado.miss.app.debug"
ACT = "io.legado.app.ui.book.source.manage.BookSourceActivity"

# 断言文案取自 values-zh/strings.xml 实际值（禁臆测）
S_SELECT_ALL_PREFIX = "全选（"   # select_all_count = "全选（%1$d/%2$d）"
S_MORE_MENU = "更多菜单"          # more_menu（contentDescription）
S_CHECK_SELECTED = "校验所选"      # check_select_source
S_CANCEL = "取消"                 # cancel
# 页内横幅**过程文案由代码拼装**（非资源串）：`CheckSourceTaskStore.kt:346`
# `校验中 3/20 · 通过 2 · 失败 1 · 正在校验：源名（搜索）` ⇒ 锚点须取「校验中」。
# ⚠️ 历史锚点 `S_PROGRESS="进度"` 指向的是**通知栏**文案（`progress_show`），页内横幅**无此字样**
# ⇒ 恒不可见（＝2026-10-17 复现的 T1 假失败根因）。
S_PROGRESS = "校验中"             # 页内横幅过程态前缀


def fatal_count() -> int:
    out = subprocess.run([ADB, "-s", HOST, "logcat", "-d", "-s", "AndroidRuntime:E"],
                         capture_output=True, text=True, timeout=60).stdout or ""
    return sum(1 for line in out.splitlines() if "FATAL EXCEPTION" in line)


def rest_report() -> dict:
    """读内置巡检报告腿（`GET /getCheckSourceReport`，READONLY ⇒ 过渡期免令牌）。

    为什么用它做判据：该页**横幅进度文案在 u2 dump 中间隙不可见**（同 §六十九 的「底栏/面板
    dump 不可见」族）⇒ 不能只靠 UI 文本断言「任务确已启动」；报告腿是**App 内置统一结论**的
    唯一读出口径（三端同源），用它取证更强且不依赖 dump 暴露。不可达时返回空 dict（按公示 SKIP）。
    """
    try:
        import json
        import urllib.request
        with urllib.request.urlopen("http://127.0.0.1:1122/getCheckSourceReport", timeout=10) as r:
            return json.loads(r.read().decode("utf-8", "replace")).get("data") or {}
    except Exception:
        return {}


def rest_report_started(timeout_s: int = 20) -> tuple:
    """轮询报告腿直到出现**非 IDLE 且 total>0** 的运行态 ⇒ (是否启动, 计数摘要)。"""
    deadline = time.time() + timeout_s
    last = {}
    while time.time() < deadline:
        last = rest_report()
        if (last.get("total") or 0) > 0 and last.get("status") not in (None, "IDLE"):
            return True, "status=%s total=%s passed=%s failed=%s blocked=%s" % (
                last.get("status"), last.get("total"), last.get("passed"),
                last.get("failed"), last.get("blocked"))
        time.sleep(1)
    return False, "未取到运行态（status=%s total=%s）" % (last.get("status"), last.get("total"))


def tap_banner_cancel(d) -> bool:
    """点**页内横幅**右侧的「取消」。

    横幅位于列表顶部（`BookSourceScreen.kt:180-193` 的 `InlineTaskBar` 在 `Column` 首项），
    故其「取消」的 y 小、x 靠右；`d(text="取消")` 可能匹配多处 ⇒ 按「x>0.75w 且 y<0.40h」
    取最靠上的那个，避免点到别处（实测直接 `tap_text` 会点空 ⇒ 横幅不消失）。
    """
    nodes = d(text=S_CANCEL)
    if nodes.count == 0:
        return False
    w, h = d.window_size()
    best = None
    for i in range(nodes.count):
        b = nodes[i].info.get("bounds") or {}
        x1, y1 = b.get("left", 0), b.get("top", 0)
        if x1 > w * 0.75 and y1 < h * 0.40:
            if best is None or y1 < best[1]:
                best = (x1, y1, b.get("right", 0), b.get("bottom", 0))
    if best is None:
        return False
    d.click((best[0] + best[2]) // 2, (best[1] + best[3]) // 2)
    return True


def tap_text(d, text, exact=True):
    node = d(text=text) if exact else d(textContains=text)
    if node.exists:
        node.click()
        return True
    return False


def tap_desc_bottommost(d, desc):
    """点最靠下的同 description 节点。

    多选态下顶栏与底部操作栏**各有一个**「更多菜单」（contentDescription = `more_menu`），
    需取底部操作栏那个（顶栏那个是全局菜单）。见 `AppManagementScaffold.SelectionMoreMenu`。
    """
    nodes = d(description=desc)
    if nodes.count == 0:
        return False
    best, best_bottom = None, -1
    for i in range(nodes.count):
        node = nodes[i]
        bottom = node.info.get("bounds", {}).get("bottom", -1)
        if bottom > best_bottom:
            best, best_bottom = node, bottom
    if best is not None:
        best.click()
        return True
    return False


def open_check_selected(d) -> bool:
    """打开「更多菜单」弹层并点中「校验所选」。

    **真机坑（2026-10-17 复现，写入本脚本）**：该弹层是**可滚动且右贴边**的列表，u2
    `dump_hierarchy` 只暴露前几项 ⇒ 「校验所选」（实测为第 9 项）**恒不可见**，直接
    `tap_text` 必失败（＝历史上 T1 假失败的主因）。修法：在**弹层内部**上滑检索
    （x 必须落在弹层内 ≈0.90w；y 落在弹层纵向范围内），逐轮复查。
    """
    if not tap_desc_bottommost(d, S_MORE_MENU):
        return False
    time.sleep(1.5)
    w, h = d.window_size()
    for _ in range(5):
        if tap_text(d, S_CHECK_SELECTED):
            return True
        # 弹层右贴边（实测 bounds 约 x1≈0.84w..x2≈0.98w / y1≈0.33h..y2≈0.90h）
        d.swipe(int(w * 0.90), int(h * 0.80), int(w * 0.90), int(h * 0.42), 0.25)
        time.sleep(0.8)
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shot", default=None)
    args = ap.parse_args()
    d = u2.connect(HOST)
    results = []

    subprocess.run([ADB, "-s", HOST, "logcat", "-c"], capture_output=True, timeout=30)
    subprocess.run([ADB, "-s", HOST, "shell", "am", "force-stop", PKG], capture_output=True, timeout=30)
    time.sleep(2)
    subprocess.run([ADB, "-s", HOST, "shell", "am", "start", "-n", f"{PKG}/{ACT}"],
                   capture_output=True, timeout=30)
    time.sleep(4)

    # 报告腿前置（best-effort）：WebService + 端口转发 ⇒ 后续可读内置巡检结论
    subprocess.run([ADB, "-s", HOST, "shell", "am", "start-foreground-service", "-n",
                    f"{PKG}/io.legado.app.service.WebService"], capture_output=True, timeout=30)
    subprocess.run([ADB, "-s", HOST, "forward", "tcp:1122", "tcp:1122"],
                   capture_output=True, timeout=30)
    time.sleep(3)

    # --- T0 进入多选（长按列表首行） ---
    w, h = d.window_size()
    d.long_click(int(w * 0.5), int(h * 0.25))
    time.sleep(1.5)
    xml = d.dump_hierarchy()
    if S_SELECT_ALL_PREFIX not in xml:
        print("[FAIL] T0 未进入多选模式（可能书源列表为空或长按未命中行）")
        if args.shot:
            d.screenshot(args.shot)
        return 1
    print("[PASS] T0 已进入多选模式（底部操作栏出现「全选（N/M）」）")

    # 全选 → 保证有可校验对象
    if tap_text(d, S_SELECT_ALL_PREFIX, exact=False):
        time.sleep(1.0)

    # --- T1 触发校验 → 横幅渲染 ---
    if not open_check_selected(d):
        print("[FAIL] T1 更多菜单中未找到「校验所选」（弹层可滚动，已在弹层内上滑检索）")
        return 1
    time.sleep(2.0)
    # 关键词确认对话框（checkSource() 的中间步骤，见 feature_test_lessons §1.9）
    for label in ("确定", "OK"):
        if tap_text(d, label):
            break
    else:
        node = d(resourceId="android:id/button1")
        if node.exists:
            node.click()
    time.sleep(2.5)

    xml = d.dump_hierarchy()
    has_cancel = S_CANCEL in xml
    has_progress = S_PROGRESS in xml
    print(f"  [T1] 横幅: 取消={'可见' if has_cancel else '缺失'}"
          f" / 过程文案(校验中)={'可见' if has_progress else '不可见'}")
    if args.shot:
        d.screenshot(args.shot)
        print(f"  截图: {args.shot}")
    # T1 判据＝**横幅出现（取消可见 + 过程文案「校验中」可见）**；另加 **T1b**：用免令牌的
    # **报告腿**独立取证「内置巡检任务确已启动」（不依赖 u2 dump 暴露，强于纯 UI 文本断言）。
    results.append(("T1 横幅渲染（取消 + 过程文案）", has_cancel and has_progress))
    started, info = rest_report_started()
    if rest_report() == {}:
        print(f"  [T1b] SKIP(公示)：报告腿不可达 ⇒ 无法独立取证（{info}）")
    else:
        results.append(("T1b 内置巡检确已启动（报告腿）", started))
        print(f"  [T1b] {info}")

    # --- T2 取消 → 横幅消失 ---
    if has_cancel:
        tap_banner_cancel(d)
        time.sleep(2.5)
        xml2 = d.dump_hierarchy()
        gone = S_PROGRESS not in xml2
        results.append(("T2 取消后横幅消失", gone))
        print(f"  [T2] 取消后过程文案: {'已消失' if gone else '仍存在'}")
    else:
        results.append(("T2 取消后横幅消失", False))

    # --- T3 无崩溃 ---
    fatals = fatal_count()
    results.append(("T3 无 FATAL EXCEPTION", fatals == 0))
    print(f"  [T3] FATAL EXCEPTION = {fatals}")

    print()
    all_pass = all(ok for _, ok in results)
    print(f"== L2 总结: {'ALL PASS' if all_pass else 'HAS FAIL'} ({sum(1 for _, ok in results if ok)}/{len(results)}) ==")
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
