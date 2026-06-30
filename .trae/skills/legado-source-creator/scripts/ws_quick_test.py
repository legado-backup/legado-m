import asyncio, json, sys
sys.path.insert(0, '.')
from legado_client.device.legado_web_client import LegadoWebClient

async def test():
    client = LegadoWebClient(host='127.0.0.1', port=1122)
    sources = await client.get_book_sources()
    src = sources[0]
    name = src.get("bookSourceName", "?")
    url = src.get("bookSourceUrl", "")[:40]
    print(f"Testing: {name} ({url})")
    logs = await asyncio.wait_for(client.ws_debug_book_source(src, "斗破苍穹"), timeout=30)
    print(f"Got {len(logs)} logs")
    for l in logs[:3]:
        print(f"  {l[:80]}")
    if logs:
        print(f"  ... last: {logs[-1][:80]}")
    await client.close()

asyncio.run(test())
