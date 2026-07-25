#!/usr/bin/env python3
"""列出数据库中含有 @js 规则的书源及其搜索URL，找可访问的"""
import json
import os
import sys
import asyncio

client_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "legado_client"))
if client_dir not in sys.path:
    sys.path.insert(0, client_dir)

from storage.database import init_db, get_session_factory
from storage.models import Source
from sqlalchemy import select

async def main():
    await init_db()
    sf = get_session_factory()
    async with sf() as session:
        stmt = select(Source).where(
            Source.source_type == "book",
            Source.source_url != "",
            Source.source_url.isnot(None),
        ).limit(200)
        result = await session.execute(stmt)
        sources = result.scalars().all()

    print(f"总书源数: {len(sources)}")
    print()

    js_sources = []
    for src in sources:
        sj = src.source_json
        sj_str = json.dumps(sj, ensure_ascii=False) if isinstance(sj, dict) else sj
        if "@js:" in sj_str or "<js>" in sj_str:
            # 提取搜索URL
            try:
                data = json.loads(sj_str) if isinstance(sj_str, str) else sj_str
                search_url = data.get("searchUrl", "")
                rule_content = data.get("ruleContent", {})
                content_rule = rule_content.get("content", "") if isinstance(rule_content, dict) else ""
                has_js_content = "@js:" in content_rule or "<js>" in content_rule
                js_sources.append((src.source_name, src.source_url, search_url[:80], has_js_content))
            except:
                js_sources.append((src.source_name, src.source_url, "?", False))

    print(f"含 @js 规则的书源: {len(js_sources)} 个")
    print()
    for name, url, search_url, has_js_content in js_sources[:30]:
        flag = " [正文有@js]" if has_js_content else ""
        print(f"  {name}: {url[:50]} | search: {search_url}{flag}")

asyncio.run(main())
