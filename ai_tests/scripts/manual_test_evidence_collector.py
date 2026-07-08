"""ai_tests/scripts/manual_test_evidence_collector.py — M5 实测验证脚本

验证 EvidenceCollector 8 类证据收集能力（对接真实 MEmu 设备）。

用法：
    python ai_tests/scripts/manual_test_evidence_collector.py
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ai_tests.config import REPORTS_DIR, PACKAGE
from ai_tests.lib.memu_controller import MemuController
from ai_tests.lib.evidence_collector import EvidenceCollector


def main() -> int:
    print("=" * 60)
    print("M5 实测验证：EvidenceCollector 8 类证据收集")
    print("=" * 60)

    memu = MemuController()

    # 1. 确保模拟器运行
    if not memu.is_running():
        print("[1] 启动 MEmu...")
        if not memu.start():
            print("[FAIL] MEmu 启动失败")
            return 1

    # 2. 等待 ADB 就绪
    print("[2] 等待 ADB 连接...")
    serial = memu.wait_for_adb()
    if not serial:
        print("[FAIL] ADB 连接失败")
        return 1
    print(f"    ADB serial: {serial}")

    # 3. 创建 EvidenceCollector
    ec = EvidenceCollector(memu)

    # 4. 创建测试目录
    tc_id = "TC-M5-MANUAL-01"
    tc_dir = REPORTS_DIR / f"m5_test_{time.strftime('%Y%m%d_%H%M%S')}" / "cases" / tc_id
    tc_dir.mkdir(parents=True, exist_ok=True)
    print(f"[3] 测试目录: {tc_dir}")

    # 5. 启动 logcat
    print("[4] 启动 logcat...")
    if not ec.start_logcat():
        print("[WARN] start_logcat 失败，继续测试（logcat 证据将为空）")

    # 6. 等待几秒收集一些 log
    print("[5] 等待 3s 收集日志...")
    time.sleep(3)

    # 6.5 创建模拟 ui_xml/screenshot 目录（模拟 M4 UiExecutor 输出）
    # 简化说明：M5 单独测试时无 UiExecutor 产物，用占位文件模拟 | 已知上限：仅用于 M5 独立验证 | 升级路径：完整 E2E 时由 UiExecutor 真实生成
    xml_dir = tc_dir / "xml"
    xml_dir.mkdir(parents=True, exist_ok=True)
    (xml_dir / "step-01-before.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?><hierarchy><node/></hierarchy>',
        encoding="utf-8",
    )
    png_dir = tc_dir / "screenshot"
    png_dir.mkdir(parents=True, exist_ok=True)
    # PNG 文件头（8 bytes）+ 占位内容
    png_header = b'\x89PNG\r\n\x1a\n' + b'\x00' * 100
    (png_dir / "step-01-before.png").write_bytes(png_header)
    print("[5.5] 已创建模拟 ui_xml/screenshot 目录（模拟 M4 产物）")

    # 7. collect_all 并行收集
    print("[6] collect_all 并行收集 8 类证据...")
    web_endpoints = ["/", "/booksource/getBookSource"]  # Legado Web API 示例
    result = ec.collect_all(tc_id, tc_dir, web_endpoints=web_endpoints)

    # 8. 打印结果
    print("\n" + "=" * 60)
    print("证据收集结果：")
    print("=" * 60)
    for ev_type in [
        "logcat", "ui_xml", "screenshot", "activity_stack",
        "db_state", "prefs_state", "web_api", "meminfo"
    ]:
        ev = result.get(ev_type, {})
        collected = ev.get("collected", False)
        degraded = ev.get("degraded", False)
        error = ev.get("error", "")
        reason = ev.get("degradation_reason", "")

        status = "✓ PASS" if collected else ("⚠ 降级" if degraded else "✗ FAIL")
        print(f"\n[{status}] {ev_type}:")
        if collected:
            if ev_type == "logcat":
                print(f"    anomaly_count: {ev.get('anomaly_count', 0)}")
                print(f"    path: {ev.get('path', '')}")
                anomalies = ev.get("anomalies", [])
                if anomalies:
                    print(f"    异常示例（前3条）:")
                    for a in anomalies[:3]:
                        print(f"      - {a['type']}: {a['line'][:80]}")
            elif ev_type in ("ui_xml", "screenshot"):
                print(f"    count: {ev.get('count', 0)}")
                files = ev.get("files", [])
                if files:
                    print(f"    示例: {Path(files[0]).name}")
            elif ev_type == "db_state":
                queries = ev.get("queries", {})
                print(f"    queries: {len(queries)} 个")
                for mod, q in queries.items():
                    if "error" in q:
                        print(f"      {mod}: ERROR")
                    else:
                        print(f"      {mod}: {q.get('rows', 0)} 行")
            elif ev_type == "prefs_state":
                print(f"    count: {ev.get('count', 0)}")
            elif ev_type == "web_api":
                endpoints = ev.get("endpoints", {})
                print(f"    endpoints: {len(endpoints)} 个")
            else:
                print(f"    path: {ev.get('path', '')}")
        if degraded:
            print(f"    降级原因: {reason}")
        if error and not collected:
            print(f"    错误: {error}")

    # 9. 汇总统计
    print("\n" + "=" * 60)
    print("汇总统计：")
    print("=" * 60)
    collected_count = sum(1 for v in result.values() if v.get("collected"))
    degraded_count = sum(1 for v in result.values() if v.get("degraded"))
    failed_count = 8 - collected_count - degraded_count
    print(f"  收集成功: {collected_count}/8")
    print(f"  降级: {degraded_count}/8")
    print(f"  失败: {failed_count}/8")
    print(f"  证据目录: {tc_dir}")

    # 10. 列出证据目录文件
    print("\n证据目录结构：")
    for f in sorted(tc_dir.rglob("*")):
        if f.is_file():
            rel = f.relative_to(tc_dir)
            size = f.stat().st_size
            print(f"  {rel} ({size} bytes)")

    # 判定
    if collected_count >= 5:
        print(f"\n[PASS] M5 实测验证通过（{collected_count}/8 收集成功）")
        return 0
    else:
        print(f"\n[FAIL] M5 实测验证未通过（仅 {collected_count}/8 收集成功，需 ≥5）")
        return 1


if __name__ == "__main__":
    sys.exit(main())
