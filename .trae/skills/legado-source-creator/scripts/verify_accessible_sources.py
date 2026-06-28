#!/usr/bin/env python3
"""用起点中文（优+）和起点限免源测试，这两个源之前出现过 NativeJavaObject Bug"""
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

async def get_sources():
    await init_db()
    sf = get_session_factory()
    async with sf() as session:
        # 取起点相关源
        stmt = select(Source).where(
            Source.source_name.like("%起点%"),
            Source.source_type == "book",
        ).limit(10)
        result = await session.execute(stmt)
        return [(s.source_name, s.source_json) for s in result.scalars()]

sources = asyncio.run(get_sources())
print(f"起点相关书源: {len(sources)} 个")

for name, sj in sources:
    print(f"\n{'='*60}")
    print(f"测试源: {name}")
    sj_str = json.dumps(sj, ensure_ascii=False) if isinstance(sj, dict) else sj

    # 检查是否含 @js
    has_js = "@js:" in sj_str or "<js>" in sj_str
    print(f"含 @js 规则: {has_js}")

    # 检查 ruleContent.content 规则
    try:
        data = json.loads(sj_str)
        content_rule = data.get("ruleContent", {}).get("content", "")
        print(f"正文规则: {content_rule[:100]}")
    except:
        content_rule = ""

    cmd = json.dumps({"cmd": "debugBookSource", "sourceJson": sj_str, "key": "斗破苍穹"}, ensure_ascii=False)
    input_data = (cmd + '\n{"cmd":"shutdown"}\n').encode("utf-8")

    proc = subprocess.Popen(
        ["java", "-jar", JAR],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    try:
        stdout_bytes, stderr_bytes = proc.communicate(input=input_data, timeout=180)
    except subprocess.TimeoutExpired:
        proc.kill()
        stdout_bytes, stderr_bytes = proc.communicate()

    # 分析 stderr
    stderr_text = stderr_bytes.decode("gbk", errors="replace")
    diag_lines = [l for l in stderr_text.split("\n") if "[DIAG]" in l]
    njo_lines = [l for l in diag_lines if "NativeJavaObject" in l]

    print(f"  DIAG 行数: {len(diag_lines)}, 含 NJO: {len(njo_lines)}")

    # 打印所有 DIAG 行
    for l in diag_lines:
        print(f"  DIAG: {l[:200]}")

    # 分析 stdout
    stdout_text = stdout_bytes.decode("gbk", errors="replace")
    result_found = False
    for line in stdout_text.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            if obj.get("type") == "result":
                result_found = True
                data = obj.get("data", {})
                stages = data.get("stages", {})
                search = stages.get("search", {})
                detail = stages.get("detail", {})
                toc = stages.get("toc", {})
                content = stages.get("content", {})
                cl = content.get("contentLength", 0)
                cp = content.get("contentPreview", "")[:200]

                print(f"  搜索: {search.get('bookCount', 0)} 本")
                print(f"  详情: {detail.get('bookName', '无')}")
                print(f"  目录: {toc.get('chapterCount', 0)} 章")
                print(f"  正文长度: {cl}")
                if cp:
                    print(f"  正文预览: {cp}")

                if "NativeJavaObject@" in cp:
                    print("  ❌ NativeJavaObject Bug 仍存在！")
                elif cl > 100:
                    print("  ✅ 正文正常！")
                elif cl == 0:
                    print("  ⚠️ 正文为空")
                else:
                    print(f"  ⚠️ 正文长度异常 ({cl})")
                break
        except json.JSONDecodeError:
            pass

    if not result_found:
        # 打印最后几行 stdout
        lines = stdout_text.strip().split("\n")
        print(f"  未找到 result 行，stdout 总行数: {len(lines)}")
        # 尝试找 log 行看进度
        for line in lines[-10:]:
            try:
                obj = json.loads(line.strip())
                if obj.get("type") == "log":
                    print(f"  LOG: state={obj.get('state')} msg={obj.get('msg','')[:80]}")
            except:
                pass
