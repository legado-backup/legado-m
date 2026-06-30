"""Quick check of real device source counts."""
import asyncio
from legado_client.device.legado_web_client import LegadoWebClient

async def main():
    c = LegadoWebClient('192.168.1.7', 1122, 'pass')
    books = await c.get_book_sources()
    print(f"Book sources: {len(books)}")
    rss = await c.get_rss_sources()
    print(f"RSS sources: {len(rss)}")
    await c.close()

asyncio.run(main())
