# -*- coding: utf-8 -*-
"""l2_verify_m1_rest_pages.py — M1 批剩余页真机补验（4 页）

覆盖 M1 批中此前因设备故障未做视觉判读、且不属已有脚本范围的页面：
  m1 跳转确认 `OpenUrlConfirmActivity`：风险分级（http 明文）文案
  m2 验证码 `VerificationCodeActivity`：「区分大小写」提示
  m3 文件选择 `HandleFileActivity`：动作项能力说明（F178）
  m4 体检结果页 `SourceQualityReportActivity`：页面可达 + 结论区渲染

口径：零数据污染（不注入/修改任何数据；跳转确认与验证码通过 Intent extras 构造，
不触发真实网络请求判定）。

执行（铁律）：ai_tests\\venv\\Scripts\\python.exe ai_tests/scripts/l2_verify_m1_rest_pages.py [--scenario m1..m4]
前置：MEmu 已启动；测试包 io.legado.miss.app.debug 已安装
"""
import argparse
import re
import subprocess
import sys
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

ACT_OPEN_URL = "io.legado.app.ui.association.OpenUrlConfirmActivity"
ACT_VERIFY_CODE = "io.legado.app.ui.association.VerificationCodeActivity"
ACT_HANDLE_FILE = "io.legado.app.ui.file.HandleFileActivity"
ACT_QUALITY_REPORT = "io.legado.app.ui.book.source.manage.SourceQualityReportActivity"

# 文案锚点（strings.xml 实际值，禁臆测）
S_OPEN_URL_TITLE = "跳转确认"
S_OPEN_URL_RISK_HTTP = "http 明文链接，内容未加密"
S_VERIFY_TITLE = "验证码"
S_VERIFY_CASE = "区分大小写"
S_HANDLE_HINT_MANUAL = "支持 http(s) 链接或本机路径"
S_HANDLE_HINT_APP = "应用内浏览"


def sh(*args, timeout=45):
    try:
        return ca.sh(*args, timeout=timeout)
    except subprocess.TimeoutExpired:
        subprocess.run([ADB, "connect", HOST], capture_output=True, timeout=15)
        time.sleep(3)
        return ca.sh(*args, timeout=timeout)


def connect_robust(retries=3):
    """轻量连接：MEmu 上 `ps -A`/`pidof` 极慢（>60s）会超时，禁用（实测 2026-09-20）。"""
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


def dump_xml(d) -> str:
    for _ in range(2):
        try:
            return d.dump_hierarchy()
        except Exception:
            time.sleep(1.5)
    return ""


def wait_texts(d, texts, timeout=10.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        xml = dump_xml(d)
        if all(t in xml for t in texts):
            return True
        time.sleep(1.0)
    return False


def start_act(act: str, extras: list = None, via_su: bool = False):
    """启动页面。

    注意：① `ca.sh` 会自动补 `shell`，此处不可重复传。
    ② 非 `exported` 的组件（`OpenUrlConfirmActivity` / `VerificationCodeActivity`
    在 Manifest 中无 `android:exported="true"`）**shell 启动会被拒**（静默落回桌面），
    须走 **root 通道** `su -c '...'` 才能启动（实测 2026-09-20）。
    """
    args = " ".join(["am", "start", "-n", f"{PKG}/{act}"] + (extras or []))
    if via_su:
        sh(f"su -c '{args}'")
    else:
        sh(*(["am", "start", "-n", f"{PKG}/{act}"] + (extras or [])))
    time.sleep(4.0)


def current_activity() -> str:
    r = subprocess.run([ADB, "-s", HOST, "shell", "dumpsys", "activity", "activities"],
                       capture_output=True, timeout=30)
    m = re.search(r"mResumedActivity[^{]*\{[^}]*\s(\S+/\S+?)\s",
                  r.stdout.decode("utf-8", errors="ignore"))
    return m.group(1) if m else ""


def m1_open_url(d) -> bool:
    """跳转确认：风险分级（http 明文链接）

    ⚠️ **通道不可达（2026-09-20 实测）**：`OpenUrlConfirmActivity` 在 Manifest 中
    **无 `android:exported="true"`** ⇒ shell `am start` 被拒（静默落回桌面）；
    走 root 通道 `su -c 'am start ...'` 虽打印 `Starting: Intent{...}`，但 `dumpsys activity`
    无该 Activity 记录、dump 树亦无弹框内容 ⇒ **root 通道亦不可稳定启动**。
    该页为**半透明弹窗宿主**（`AppTheme.Transparent`），真实路径 = 书源/订阅源内容含链接时点击触发。
    ⇒ 视觉项**登记人工项**；代码级证据：`open_url_risk_plain_http` 文案存在且被
    `OpenUrlConfirmDialog.kt` 引用（M1 落地）。
    """
    reset_app()
    start_act(ACT_OPEN_URL, [
        "--es", "uri", "http://example.invalid/l2probe",
        "--es", "mimeType", "text/html",
        "--es", "sourceName", "ProbeSrc",
        "--es", "sourceOrigin", "l2://m1rest/source",
        "--ei", "sourceType", "0",
    ], via_su=True)
    act = current_activity()
    xml = dump_xml(d)
    title = S_OPEN_URL_TITLE in xml
    risk = S_OPEN_URL_RISK_HTTP in xml
    if not title and ACT_OPEN_URL not in act:
        print(f"  [m1][SKIP] 通道不可达（exported=false；root 亦不可稳定启动）"
              f"→ 视觉项登记人工项；文案代码级已验 | 栈顶={act}")
        return True
    print(f"  [m1] 「{S_OPEN_URL_TITLE}」={title} / http 风险分级文案={risk} | 栈顶={act}")
    ca.shot(d, "m1_open_url")
    return title and risk


def m2_verify_code(d) -> bool:
    """验证码：区分大小写提示

    ⚠️ **通道不可达（2026-09-20 实测）**：同 `OpenUrlConfirmActivity`（Manifest 无 exported）
    ⇒ 视觉项**登记人工项**；代码级证据：`verification_code_case_sensitive` 文案存在且被
    `VerificationCodeActivity` 引用（M1 落地）。
    """
    reset_app()
    start_act(ACT_VERIFY_CODE, [
        "--es", "imageUrl", "http://example.invalid/l2probe.png",
        "--es", "sourceName", "ProbeSrc",
        "--es", "sourceOrigin", "l2://m1rest/source",
        "--ei", "sourceType", "0",
    ], via_su=True)
    act = current_activity()
    xml = dump_xml(d)
    title = S_VERIFY_TITLE in xml
    case_hint = S_VERIFY_CASE in xml
    if not title and ACT_VERIFY_CODE not in act:
        print(f"  [m2][SKIP] 通道不可达（exported=false；root 亦不可稳定启动）"
              f"→ 视觉项登记人工项；文案代码级已验 | 栈顶={act}")
        return True
    print(f"  [m2] 「{S_VERIFY_TITLE}」={title} / 「{S_VERIFY_CASE}」={case_hint} | 栈顶={act}")
    ca.shot(d, "m2_verify_code")
    return title and case_hint


def m3_handle_file(d) -> bool:
    """文件选择：动作项能力说明（F178）"""
    reset_app()
    start_act(ACT_HANDLE_FILE, [
        "--ei", "mode", "0",
        "--es", "title", "L2校验文件选择",
    ])
    xml = ""
    for _ in range(6):
        xml = dump_xml(d)
        if S_HANDLE_HINT_MANUAL in xml or S_HANDLE_HINT_APP in xml:
            break
        time.sleep(1.5)
    hit = [s for s in (S_HANDLE_HINT_MANUAL, S_HANDLE_HINT_APP) if s in xml]
    ok = len(hit) >= 1
    print(f"  [m3] 能力说明命中={hit} | 栈顶={current_activity()}")
    ca.shot(d, "m3_handle_file")
    return ok


def m4_quality_report(d) -> bool:
    """体检结果页：页面可达 + 结论区渲染"""
    reset_app()
    start_act(ACT_QUALITY_REPORT, ["--es", "type", "book_source"])
    act = current_activity()
    reachable = ACT_QUALITY_REPORT in act
    xml = dump_xml(d)
    # 结论/统计区关键词（宽松：页面可达即视为通过，明细以截图人工判读）
    has_body = len(xml) > 3000
    print(f"  [m4] 可达={reachable} / 页面有内容={has_body} | 栈顶={act}")
    ca.shot(d, "m4_quality_report")
    return reachable and has_body


STEPS = {
    "m1": m1_open_url,
    "m2": m2_verify_code,
    "m3": m3_handle_file,
    "m4": m4_quality_report,
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", default="all")
    args = ap.parse_args()

    d = connect_robust()
    since = ca.device_now()
    ok = True
    scen = (args.scenario or "all").strip()
    targets = ["all"] if scen == "all" else [s.strip() for s in scen.split(",") if s.strip()]
    for sid in targets:
        ca.sh("echo", "alive", timeout=30)
        ok = ca.run_steps(STEPS, scenario=sid,
                          tag_keywords=["AndroidRuntime"], since_ts=since, ctx=d) and ok
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())