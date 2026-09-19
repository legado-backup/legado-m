"""l2_verify_theme_fontcolor_preserve.py — A3.4a 真机验证：用户自选字体色原值保留

背景（A3.4a 用户主题数据保护）：
    改造前 `ThemeConfig.applyFontColorPrefs` 会把「撞色 sanitize 后的结果」写回用户 pref，
    而该 pref key 与用户在设置界面自选字体色**是同一个 key** → 用户自选色被永久覆盖且不可恢复。
    改造后：sanitize 只作运行时派生（内存缓存），**禁止写回 pref**。

本脚本验证（真机）：
    T1 写入撞色探针字体色 → 启动 App → 读回 pref，**原值必须保留**（未被 sanitize 覆盖）
    T2 同一次运行截图留档（生效值仍受撞色防护，界面文字应可读）

用法:
    python ai_tests/scripts/l2_verify_theme_fontcolor_preserve.py [--shot 输出png]

注意（踩坑固化，勿改）：
    - 写 prefs 必须 `sh -c "cat TMP > PREFS"` 单参数形式 + 回读校验（多参数传参会被拆散致 prefs 截断为 0 字节）
    - 启动 Activity 必须用**全限定类名**（`<applicationId>/.ui.X` 会按 applicationId 解析成不存在的类）
    - `themeMode` 是 **string** 型 prefs（值 "0"-"3"），非 int
"""
import argparse
import re
import subprocess
import sys
import time
from pathlib import Path

ADB = r"C:\Android\Sdk\platform-tools\adb.exe"
HOST = "127.0.0.1:21503"
PKG = "io.legado.miss.app.debug"
PREFS = f"/data/data/{PKG}/shared_prefs/{PKG}_preferences.xml"
TMP = "/data/local/tmp/prefs_a34a.xml"

# 撞色探针：夜间深底上黑字 / 日间白底上白字，对比度均≈1.0 → 必然低于阈值触发 sanitize
PROBE_NIGHT = "#000000"
PROBE_DAY = "#FFFFFF"


def run(args, timeout=40):
    return subprocess.run([ADB, "-s", HOST] + args, capture_output=True, timeout=timeout)


def sh(args, timeout=40):
    return run(["shell"] + args, timeout)


def read_prefs():
    return run(["exec-out", "cat", PREFS]).stdout.decode("utf-8", errors="ignore")


def get_str(xml, key):
    m = re.search(rf'<string name="{key}">([^<]*)</string>', xml)
    return m.group(1) if m else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shot", default=None)
    args = ap.parse_args()
    failed = []

    sh(["am", "force-stop", PKG])
    time.sleep(1.5)

    xml = read_prefs()
    if "</map>" not in xml:
        print("!! 无法读取 prefs，放弃")
        return 2
    mode = get_str(xml, "themeMode")
    print(f"  当前 themeMode={mode}")

    # 两个 key 都设撞色探针，保证无论当前日夜模式均触发 sanitize
    new_xml = xml
    for key, probe in (("ui_font_color_night", PROBE_NIGHT), ("ui_font_color", PROBE_DAY)):
        if f'<string name="{key}">' in new_xml:
            new_xml = re.sub(rf'<string name="{key}">[^<]*</string>',
                             f'<string name="{key}">{probe}</string>', new_xml)
        else:
            new_xml = new_xml.replace("</map>", f'    <string name="{key}">{probe}</string>\n</map>')
    if new_xml == xml:
        print("  探针已在位，跳过写入步骤")
    else:
        tmp_local = Path("ai_tests/reports/prefs_a34a_tmp.xml")
        tmp_local.parent.mkdir(parents=True, exist_ok=True)
        tmp_local.write_text(new_xml, encoding="utf-8")
        run(["push", str(tmp_local), TMP])
        # 单参数形式：重定向必须交由**设备 shell** 处理
        # （写成 ["shell","sh","-c","cat A > B"] 多参数会被拆散，`>` 语义丢失致写回失败）
        run(["shell", f"cat {TMP} > {PREFS}"])

    # 回读校验：探针必须落盘（校验目标键值，而非仅比长度）
    xml2 = read_prefs()
    for key, probe in (("ui_font_color_night", PROBE_NIGHT), ("ui_font_color", PROBE_DAY)):
        got = get_str(xml2, key)
        ok = got == probe
        print(f"  [写入校验] {key}={got} expect={probe} {'OK' if ok else 'FAIL'}")
        if not ok:
            failed.append(f"探针写入失败: {key}")

    # 启动 App（全限定类名）→ 触发取色链读取（getter/兜底派生）
    sh(["am", "start", "-n", f"{PKG}/io.legado.app.ui.welcome.WelcomeActivity"])
    time.sleep(7.0)

    # T1：原值保留（核心断言）
    xml3 = read_prefs()
    for key, probe in (("ui_font_color_night", PROBE_NIGHT), ("ui_font_color", PROBE_DAY)):
        got = get_str(xml3, key)
        ok = got == probe
        print(f"  [T1 原值保留] {key}={got} expect={probe} {'PASS' if ok else 'FAIL'}")
        if not ok:
            failed.append(f"T1 原值被覆盖: {key} {probe} -> {got}")

    # T2：截图留档（生效值仍受撞色防护）
    if args.shot:
        r = subprocess.run([ADB, "-s", HOST, "exec-out", "screencap", "-p"],
                           capture_output=True, timeout=40)
        out = Path(args.shot)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(r.stdout)
        print(f"  [T2 截图] {args.shot} ({len(r.stdout)} bytes)")

    print()
    if failed:
        print("[FAIL] " + "; ".join(failed))
        return 1
    print("[PASS] A3.4a 验证通过：启动/取色后用户自选字体色原值保留")
    return 0


if __name__ == "__main__":
    sys.exit(main())
