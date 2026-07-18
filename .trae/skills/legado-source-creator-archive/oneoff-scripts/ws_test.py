import asyncio, json, websockets, time

async def test():
    try:
        async with websockets.connect('ws://127.0.0.1:1123/bookSourceDebug', open_timeout=5) as ws:
            await ws.send(json.dumps({'tag': 'https://www.biqubo.com', 'key': '斗破苍穹'}, ensure_ascii=False))
            msgs = 0
            start = time.time()
            while time.time() - start < 30:
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=20)
                    msgs += 1
                    if msgs <= 3:
                        print(f'  msg[{msgs}]: {msg[:80]}')
                    if '调试结束' in msg:
                        elapsed = time.time() - start
                        print(f'  Done in {elapsed:.1f}s, total msgs: {msgs}')
                        return
                except asyncio.TimeoutError:
                    print('  WS recv timeout after 20s')
                    return
    except Exception as e:
        print(f'  Error: {e}')

asyncio.run(test())
