#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
查询 articleStyle=2 的图片源（技术字段，不输出业务文本）
通过 stdin 传 SQL 给 sqlite3，避免 shell 转义问题
"""
import subprocess
import sys
import os

ADB = r"C:\Android\Sdk\platform-tools\adb.exe"
DEVICE = "127.0.0.1:21503"
PKG = "io.legado.miss.app.debug"
DB_PATH = f"/data/data/{PKG}/databases/legado.db"

def run_sql(sql):
    """通过 stdin 传 SQL 给 sqlite3"""
    cmd = [
        ADB, "-s", DEVICE, "exec-out",
        "run-as", PKG, "sh", "-c",
        f"sqlite3 {DB_PATH}"
    ]
    result = subprocess.run(cmd, input=sql + "\n.exit\n",
                          capture_output=True, text=True, encoding="utf-8", errors="replace")
    return result.stdout, result.stderr

def run_sql_via_cat(sql):
    """通过 cat 文件方式执行 SQL（避免 run-as 权限问题）"""
    # 1. 把 SQL 写到本地文件
    sql_file = os.path.join(os.environ.get("TEMP", "/tmp"), "query.sql")
    with open(sql_file, "w", encoding="utf-8") as f:
        f.write(sql + "\n.exit\n")
    # 2. push 到设备可读目录
    remote_sql = "/data/local/tmp/query.sql"
    subprocess.run([ADB, "-s", DEVICE, "push", sql_file, remote_sql], capture_output=True)
    # 3. run-as 复制 db 到可读目录并执行
    # 由于 sqlite3 不在应用 PATH，换用 cat + run-as 方式
    cmd = [
        ADB, "-s", DEVICE, "shell",
        f"run-as {PKG} sh -c 'sqlite3 {DB_PATH} < {remote_sql}'"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return result.stdout, result.stderr

def main():
    # 用最简单的 SQL，避免特殊字符
    sql = "SELECT type, articleStyle, length(ruleContent), length(ruleImage), enabled FROM rss_sources WHERE articleStyle=2 LIMIT 5;"

    print("[尝试方式1] exec-out + stdin")
    out, err = run_sql(sql)
    if out.strip():
        print("成功:")
        print(out)
        return 0
    print(f"失败: {err.strip()}")

    print("\n[尝试方式2] shell + run-as + sqlite3 < file")
    out, err = run_sql_via_cat(sql)
    if out.strip():
        print("成功:")
        print(out)
        return 0
    print(f"失败: {err.strip()}")

    print("\n[尝试方式3] 直接 adb shell + sqlite3（需 root 或可读 db）")
    # MuMu 模拟器通常 root
    cmd = [ADB, "-s", DEVICE, "shell", f"sqlite3 {DB_PATH} '{sql}'"]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.stdout.strip():
        print("成功:")
        print(result.stdout)
        return 0
    print(f"失败: {result.stderr.strip()}")

    return 1

if __name__ == "__main__":
    sys.exit(main())
