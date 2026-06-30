"""Scan local network to find Legado device - concurrent version."""
import asyncio
import httpx

async def check_ip(client, ip):
    try:
        resp = await client.get(f"http://{ip}:1122/getBookSources", headers={"Authorization": "Bearer pass"})
        if resp.status_code == 200:
            data = resp.json()
            return ip, len(data)
    except:
        pass
    return None

async def scan():
    found = []
    # Scan 192.168.1.x, 192.168.0.x, 192.168.31.x (Mi router)
    for subnet in ["192.168.1", "192.168.0", "192.168.31"]:
        async with httpx.AsyncClient(timeout=httpx.Timeout(3.0, connect=1.5)) as client:
            tasks = [check_ip(client, f"{subnet}.{i}") for i in range(1, 255)]
            results = await asyncio.gather(*tasks)
            for r in results:
                if r:
                    print(f"FOUND Legado at {r[0]}:1122 - {r[1]} book sources")
                    found.append(r[0])
    if not found:
        print("No Legado device found")
    return found

asyncio.run(scan())
