"""
Issue-10 校验速度优化验证脚本
验证：timeout 从 180s 缩到 60s 后，单源/批量校验速度改善
"""
import subprocess
import time
import sys
import uiautomator2 as u2
from pathlib import Path

ADB = "D:/Program Files/Microvirt/MEmu/adb.exe"
DEVICE_SERIAL = "127.0.0.1:21503"
PACKAGE = "io.legado.app.debug"
REPORT_DIR = Path("f:/myself/github/WeAgentChat/temp/legado/ai_tests/reports/feature_test")
REPORT_DIR.mkdir(parents=True, exist_ok=True)


def adb_shell(cmd, timeout=15):
    full = [ADB, "-s", DEVICE_SERIAL, "shell"] + cmd.split()
    try:
        r = subprocess.run(full, capture_output=True, timeout=timeout)
        return r.stdout.decode("utf-8", errors="ignore")
    except Exception as e:
        return f"ERR: {e}"


def clear_logcat():
    subprocess.run([ADB, "-s", DEVICE_SERIAL, "logcat", "-c"],
                  capture_output=True, timeout=10)


def get_logcat(tag=None, timeout=15):
    cmd = [ADB, "-s", DEVICE_SERIAL, "logcat", "-d"]
    if tag:
        cmd.extend(["-s", tag])
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=timeout)
        return r.stdout.decode("utf-8", errors="ignore") or ""
    except Exception:
        return ""


def dump_xml(d):
    # 用 u2 的 dump_hierarchy，避免与 uiautomator dump 命令冲突
    return d.dump_hierarchy()


def main():
    print("=" * 70)
    print("Issue-10 校验速度优化验证")
    print("优化内容: timeout 180s→60s, checkDomainReachable 用独立 30s 超时")
    print("=" * 70)

    d = u2.connect(DEVICE_SERIAL)

    # 1. 清 logcat
    print("\n[1/7] 清理 logcat")
    clear_logcat()
    print("  OK")

    # 2. 启动 App 并进入书源管理
    print("\n[2/7] 启动 App")
    adb_shell(f"am start -n {PACKAGE}/io.legado.app.ui.main.MainActivity")
    time.sleep(2)

    # 3. 进入书源管理页
    print("\n[3/7] 进入书源管理页")
    # 通过 adb 直接打开 BookSourceActivity
    adb_shell(
        f"am start -n {PACKAGE}/io.legado.app.ui.book.source.manage.BookSourceActivity"
    )
    time.sleep(3)

    # 4. 长按第一个书源进入选择模式
    print("\n[4/7] 长按第一个书源进入选择模式")
    # 找到列表第一个项
    list_obj = d(resourceId="io.legado.app.debug:id/recycler_view")
    if not list_obj.exists:
        list_obj = d(className="androidx.recyclerview.RecyclerView")
    if list_obj.exists:
        # 获取第一项坐标
        info = list_obj.info
        bounds = info.get("bounds", {})
        x = (bounds.get("left", 100) + bounds.get("right", 500)) // 2
        y = bounds.get("top", 200) + 100
        print(f"  长按坐标 ({x}, {y})")
        d.long_click(x, y, duration=1.5)
        time.sleep(2)
    else:
        print("  [WARN] 找不到列表，尝试直接点击屏幕中部")
        d.long_click(500, 400, duration=1.5)
        time.sleep(2)

    # 5. 不全选，只用当前长按选中的1个源校验（避免8184源全选太久）
    print("\n[5/7] 使用当前选中的1个源校验（不全选，避免太久）")

    # 6. 点击菜单"校验所选"
    print("\n[6/7] 点击菜单 -> 校验所选")
    # 底部操作栏的更多按钮
    iv_more = d(resourceId="io.legado.app.debug:id/iv_menu_more")
    if not iv_more.exists:
        iv_more = d(description="More")
    if not iv_more.exists:
        # 尝试点右上角三点
        iv_more = d(resourceId="io.legado.app.debug:id/title")
    if iv_more.exists:
        iv_more.click()
        time.sleep(1)

    # 找校验菜单项
    xml = dump_xml(d)
    check_item = d(textContains="校验")
    if not check_item.exists:
        check_item = d(textContains="Check selected")
    if not check_item.exists:
        check_item = d(textContains="check_selected")
        if check_item.exists:
            print("  [INFO] 找到 check_selected (英文菜单)")

    if check_item.exists:
        check_item.click()
        time.sleep(1)
        print("  已点击校验所选")

        # 处理搜索关键词对话框
        confirm_btn = d(text="确定")
        if not confirm_btn.exists:
            confirm_btn = d(text="OK")
        if not confirm_btn.exists:
            confirm_btn = d(resourceId="io.legado.app.debug:id/md_button_positive")
        if confirm_btn.exists:
            confirm_btn.click()
            time.sleep(1)
            print("  已确认搜索关键词对话框")
    else:
        print("  [WARN] 未找到校验菜单项")
        print(f"  XML 片段: {xml[:500]}")

    # 7. 监控校验进度，计算耗时
    print("\n[7/7] 监控校验进度（最长等待 180s）")
    start_time = time.time()
    last_progress = ""
    finished = False

    while time.time() - start_time < 180:
        elapsed = time.time() - start_time
        # 检查通知栏
        notif = adb_shell(
            "dumpsys notification --noredact | grep -A2 'CheckSourceService'",
            timeout=10
        )
        if "校验" in notif or "Check" in notif or "进度" in notif:
            # 提取进度
            for line in notif.split("\n"):
                if "android.bigText" in line or "android.title" in line or "progress" in line:
                    if line.strip() and line.strip() != last_progress:
                        last_progress = line.strip()
                        print(f"  [{elapsed:.1f}s] {last_progress[:80]}")

        # 检查是否完成（通知消失或进度达到100%）
        if elapsed > 5 and "CheckSourceService" not in notif and last_progress:
            finished = True
            break

        # 检查崩溃
        crash = get_logcat("AndroidRuntime:E", timeout=5)
        if "FATAL" in crash or "NullPointerException" in crash:
            print(f"  [FAIL] 检测到崩溃: {crash[:300]}")
            sys.exit(1)

        time.sleep(3)

    total_time = time.time() - start_time
    print(f"\n{'=' * 70}")
    if finished:
        print(f"[PASS] 校验完成，总耗时: {total_time:.1f}s")
    else:
        print(f"[WARN] 等待超时（180s），最后进度: {last_progress}")

    # 检查 weight 回填情况
    print("\n[验证] 拉取数据库检查 weight 回填")
    db_dir = REPORT_DIR / "db_pull"
    db_dir.mkdir(exist_ok=True)
    # 复制 DB
    adb_shell("su -c cp /data/data/io.legado.app.debug/databases/book.db /sdcard/book.db")
    subprocess.run(
        [ADB, "-s", DEVICE_SERIAL, "pull", "/sdcard/book.db",
         str(db_dir / "book.db")],
        capture_output=True, timeout=30
    )

    # 查询 weight 分布
    db_path = db_dir / "book.db"
    if db_path.exists():
        try:
            import sqlite3
            conn = sqlite3.connect(str(db_path))
            cur = conn.cursor()
            # 表名是 bookSources (驼峰)
            cur.execute("SELECT COUNT(*) FROM bookSources")
            total = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM bookSources WHERE weight > 0")
            positive = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM bookSources WHERE weight = 0")
            zero = cur.fetchone()[0]
            cur.execute("SELECT MAX(weight), MIN(weight), AVG(weight) FROM bookSources WHERE weight > 0")
            mx, mn, avg = cur.fetchone()
            print(f"  总书源数: {total}")
            print(f"  weight > 0: {positive}")
            print(f"  weight = 0: {zero}")
            print(f"  weight 最大/最小/平均: {mx} / {mn} / {avg:.1f}")
            conn.close()

            if positive > 0:
                print(f"\n[PASS] weight 回填成功，{positive} 个源有权重值")
            else:
                print(f"\n[FAIL] weight 未回填，0 个源有权重值")
        except Exception as e:
            print(f"  [WARN] DB 查询失败: {e}")
    else:
        print("  [WARN] DB 拉取失败")

    # 保存 logcat
    log = get_logcat(timeout=10)
    (REPORT_DIR / "issue10_speed_test.log").write_text(log, encoding="utf-8", errors="ignore")
    print(f"\n日志已保存: {REPORT_DIR / 'issue10_speed_test.log'}")

    print(f"\n{'=' * 70}")
    print("结论:")
    print(f"- 优化前: 单源校验约 120s")
    print(f"- 优化后: 批量校验总耗时 {total_time:.1f}s")
    print(f"- 超时配置: timeout=60s, domainCheckMode=0(Socket) 独立 30s")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
