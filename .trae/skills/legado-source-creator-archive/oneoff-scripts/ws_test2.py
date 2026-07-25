import asyncio, json, websockets, time

async def test():
    print("Connecting to ws://127.0.0.1:1123/bookSourceDebug...")
    try:
        async with websockets.connect('ws://127.0.0.1:1123/bookSourceDebug', open_timeout=10) as ws:
            print("Connected! Sending test request...")
            await ws.send(json.dumps({'tag': 'https://www.biqubo.com', 'key': '斗破苍穹'}, ensure_ascii=False))
            start = time.time()
            count = 0
            while time.time() - start < 30:
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=15)
                    count += 1
                    if count <= 2 or '调试结束' in msg:
                        print(f"  [{count}] {msg[:100]}")
                    if '调试结束' in msg:
                        print(f"  Done in {time.time()-start:.1f}s, {count} messages")
                        return
                except asyncio.TimeoutError:
                    print("  recv timeout (15s)")
                    return
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")

asyncio.run(test())
print("Script finished")
