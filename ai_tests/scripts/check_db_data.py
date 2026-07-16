"""检查数据库中订阅源/书源数据数量
通过 app 的 Web API（8080端口）查询，或通过 ADB 直接查询 DB
"""
import sys
import subprocess
from pathlib import Path

DEVICE_SERIAL = "127.0.0.1:21503"
PKG = "io.legado.app.debug"
ADB = "D:/Program Files/Microvirt/MEmu/adb.exe"

def run_adb_shell(cmd):
    """执行 adb shell 命令"""
    result = subprocess.run(
        [ADB, "-s", DEVICE_SERIAL, "shell", cmd],
        capture_output=True, text=True, timeout=10
    )
    return result.stdout.strip()

def check_db_data():
    """检查 DB 表数据数量（通过 run-as + sqlite3）"""
    print("=" * 60)
    print("检查数据库数据")
    print("=" * 60)

    # 检查 RSS 源数量
    # 注意：run-as + sqlite3 在某些 Android 版本可能权限不足，用备用方案
    # 备用方案：通过 ContentProvider 或 dumpsys 检查

    # 方案1：直接尝试 sqlite3
    cmd = f"run-as {PKG} sqlite3 /data/data/{PKG}/databases/legado.db 'SELECT COUNT(*) FROM rss_sources;'"
    output = run_adb_shell(cmd)
    print(f"rss_sources 数量: {output}")

    cmd = f"run-as {PKG} sqlite3 /data/data/{PKG}/databases/legado.db 'SELECT COUNT(*) FROM book_sources;'"
    output = run_adb_shell(cmd)
    print(f"book_sources 数量: {output}")

    # 方案2：检查 DB 文件大小
    cmd = f"run-as {PKG} ls -la /data/data/{PKG}/databases/legado.db"
    output = run_adb_shell(cmd)
    print(f"DB 文件: {output}")

    # 方案3：检查 SharedPreferences 中是否有订阅源相关数据
    cmd = f"run-as {PKG} ls /data/data/{PKG}/shared_prefs/"
    output = run_adb_shell(cmd)
    print(f"SharedPreferences 文件列表:\n{output}")

def check_manifest_services():
    """检查 AndroidManifest 中 Service 是否注册"""
    print("\n" + "=" * 60)
    print("检查 AndroidManifest 中 Service 注册")
    print("=" * 60)
    # 通过 dumpsys 检查
    cmd = f"dumpsys package {PKG} | grep -A1 'Service'"
    output = run_adb_shell(cmd)
    print(output[:2000] if output else "无 Service 信息")

def main():
    check_db_data()
    check_manifest_services()

if __name__ == "__main__":
    main()
