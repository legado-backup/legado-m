#!/usr/bin/env python3
"""专门测试搜索+详情通过但目录失败的源，分析目录失败原因。"""
import subprocess
import json
import sys
import asyncio

sys.path.insert(0, "f:\\myself\\github\\WeAgentChat\\temp\\legado\\.trae\\skills\\legado-source-creator\\scripts")

JAR = "f:\\myself\\github\\WeAgentChat\\temp\\legado\\.trae\\skills\\legado-source-creator\\tools\\legado-jvm\\build\\libs\\legado-jvm.jar"
OUT = "f:\\myself\\github\\WeAgentChat\\temp\\legado\\.trae\\skills\\legado-source-creator\\scripts\\toc_analysis.txt"


def debug_source_verbose(source_json_str, key="斗破苍穹"):
    """详细输出所有日志，不截断。"""
    proc = subprocess.Popen(
        ["java", "-jar", JAR],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    lines = [
        json.dumps({"cmd": "debugBookSource", "sourceJson": source_json_str, "key": key}, ensure_ascii=False),
        '{"cmd":"shutdown"}',
    ]
    input_data = ("\n".join(lines) + "\n").encode("utf-8")
    
    try:
        stdout_bytes, stderr_bytes = proc.communicate(input=input_data, timeout=60)
    except subprocess.TimeoutExpired:
        proc.kill()
        stdout_bytes, stderr_bytes = proc.communicate()
    
    stdout = stdout_bytes.decode("gbk", errors="replace")
    return stdout


async def main():
    with open(OUT, "w", encoding="utf-8") as f:
        from legado_client.storage.database import init_db, get_session_factory
        from legado_client.storage.models import Source
        from sqlalchemy import select

        await init_db()
        sf = get_session_factory()

        # 找炫书网源
        async with sf() as session:
            stmt = select(Source).where(Source.source_name.like("%炫书网%")).limit(3)
            result = await session.execute(stmt)
            sources = list(result.scalars().all())

        # 找起点限免源
        async with sf() as session:
            stmt = select(Source).where(Source.source_name.like("%起点限免%")).limit(1)
            result = await session.execute(stmt)
            qd_sources = list(result.scalars().all())

        all_sources = sources + qd_sources

        for source in all_sources:
            f.write(f"{'='*60}\n")
            f.write(f"源: {source.source_name}\n")
            f.write(f"URL: {source.source_url}\n")
            f.write(f"{'='*60}\n\n")

            source_json = source.source_json
            if isinstance(source_json, dict):
                source_json = json.dumps(source_json, ensure_ascii=False)

            output = debug_source_verbose(source_json)
            
            # 输出所有行
            for line in output.strip().split("\n"):
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    rtype = obj.get("type", "")
                    if rtype == "log":
                        state = obj.get("state", 0)
                        msg = obj.get("msg", "")
                        f.write(f"  [{state}] {msg}\n")
                    elif rtype == "error":
                        f.write(f"  [ERROR] {obj.get('msg', '')}\n")
                    elif rtype == "result":
                        f.write(f"\n  [RESULT] success={obj.get('success')}\n")
                        summary = obj.get("summary", {})
                        f.write(f"  summary: {json.dumps(summary, ensure_ascii=False, indent=2)}\n")
                    elif "status" in obj:
                        f.write(f"  [INIT] {obj}\n")
                except json.JSONDecodeError:
                    f.write(f"  [RAW] {line[:200]}\n")
            
            f.write("\n\n")

        f.write("[DONE]\n")


if __name__ == "__main__":
    asyncio.run(main())
