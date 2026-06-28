#!/usr/bin/env python3
"""最终验证：用起点中文（优+）源完整测试，带长超时"""
import subprocess
import json
import os
import sys
import asyncio

JAR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "tools", "legado-jvm", "build", "libs", "legado-jvm.jar"))
client_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "legado_client"))
if client_dir not in sys.path:
    sys.path.insert(0, client_dir)

from storage.database import init_db, get_session_factory
from storage.models import Source
from sqlalchemy import select

async def get_source():
    await init_db()
    sf = get_session_factory()
    async with sf() as session:
        stmt = select(Source).where(
            Source.source_name == "起点中文（优+）"
        ).limit(1)
        result = await session.execute(stmt)
        src = result.scalar_one_or_none()
        if src:
            return src.source_name, src.source_json
        # 备选
        stmt2 = select(Source).where(Source.source_name.like("%起点中文%")).limit(1)
        result2 = await session.execute(stmt2)
        src2 = result2.scalar_one_or_none()
        if src2:
            return src2.source_name, src2.source_json
        return None, None

name, sj = asyncio.run(get_source())
if not sj:
    print("❌ 未找到起点中文源")
    sys.exit(1)

print(f"测试源: {name}")

sj_str = json.dumps(sj, ensure_ascii=False) if isinstance(sj, dict) else sj
cmd = json.dumps({"cmd": "debugBookSource", "sourceJson": sj_str, "key": "斗破苍穹"}, ensure_ascii=False)
input_data = (cmd + '\n{"cmd":"shutdown"}\n').encode("utf-8")

print("启动 JAR 测试...")
proc = subprocess.Popen(
    ["java", "-jar", JAR],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
)

try:
    stdout_bytes, stderr_bytes = proc.communicate(input=input_data, timeout=300)
except subprocess.TimeoutExpired:
    proc.kill()
    stdout_bytes, stderr_bytes = proc.communicate()

stderr_text = stderr_bytes.decode("gbk", errors="replace")
diag_lines = [l for l in stderr_text.split("\n") if "[DIAG]" in l]
njo_lines = [l for l in diag_lines if "NativeJavaObject" in l]

print(f"\nDIAG 日志: {len(diag_lines)} 行, 含 NativeJavaObject: {len(njo_lines)}")

# 打印所有 DIAG 行
for l in diag_lines:
    print(f"  {l[:200]}")

if njo_lines:
    print("\n⚠️ 仍有 NativeJavaObject 出现！")
    for l in njo_lines:
        print(f"  {l[:300]}")
else:
    print("\n✅ 无 NativeJavaObject 类型出现")

# 解析结果
stdout_text = stdout_bytes.decode("gbk", errors="replace")
for line in stdout_text.strip().split("\n"):
    line = line.strip()
    if not line:
        continue
    try:
        obj = json.loads(line)
        if obj.get("type") == "result":
            data = obj.get("data", {})
            stages = data.get("stages", {})
            search = stages.get("search", {})
            detail = stages.get("detail", {})
            toc = stages.get("toc", {})
            content = stages.get("content", {})
            cl = content.get("contentLength", 0)
            cp = content.get("contentPreview", "")[:300]

            print(f"\n{'='*60}")
            print(f"全链路结果:")
            print(f"  搜索: {search.get('bookCount', 0)} 本")
            print(f"  详情: {detail.get('bookName', '无')}")
            print(f"  目录: {toc.get('chapterCount', 0)} 章")
            print(f"  正文长度: {cl}")
            if cp:
                print(f"  正文预览: {cp}")

            if "NativeJavaObject@" in cp:
                print("\n❌ NativeJavaObject Bug 仍存在！正文是 NativeJavaObject@hash")
            elif cl > 100:
                print("\n✅ 正文正常！Bug 已修复！")
            elif cl == 0:
                print("\n⚠️ 正文为空（可能需要VIP/登录或网站不可达）")
            else:
                print(f"\n⚠️ 正文长度异常 ({cl})")
            break
    except json.JSONDecodeError:
        pass
