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
S_PROGRESS = "进度"               # progress_show = "%1$s      进度 %2$d/%3$d"


def fatal_count() -> int:
    out = subprocess.run([ADB, "-s", HOST, "logcat", "-d", "-s", "AndroidRuntime:E"],
                         capture_output=True, text=True, timeout=60).stdout or ""
    return sum(1 for line in out.splitlines() if "FATAL EXCEPTION" in line)


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
    ok = tap_desc_bottommost(d, S_MORE_MENU)
    time.sleep(1.5)
    if not ok:
        print("[FAIL] T1 未找到「更多菜单」入口（顶栏+底部栏均应各一）")
        return 1
    if not tap_text(d, S_CHECK_SELECTED):
        print("[FAIL] T1 更多菜单中未找到「校验所选」")
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
    results.append(("T1 横幅渲染（取消 + 进度文案）", has_cancel and has_progress))
    print(f"  [T1] 取消={'可见' if has_cancel else '缺失'} / 进度={'可见' if has_progress else '缺失'}")
    if args.shot:
        d.screenshot(args.shot)
        print(f"  截图: {args.shot}")

    # --- T2 取消 → 横幅消失 ---
    if has_cancel:
        tap_text(d, S_CANCEL)
        time.sleep(2.5)
        xml2 = d.dump_hierarchy()
        gone = S_PROGRESS not in xml2
        results.append(("T2 取消后横幅消失", gone))
        print(f"  [T2] 取消后进度文案: {'已消失' if gone else '仍存在'}")
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
