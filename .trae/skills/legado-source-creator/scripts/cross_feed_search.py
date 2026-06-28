import asyncio, json, sys
sys.path.insert(0, '.')
from legado_client.device.legado_web_client import LegadoWebClient
from urllib.parse import urlparse

async def main():
    client = LegadoWebClient(host='127.0.0.1', port=1122)
    all_sources = await client.get_book_sources()

    with open('reports/full-fix-20260628.json', 'r', encoding='utf-8') as f:
        report = json.load(f)

    book_results = report['results']['book']

    sea_n_det_y_urls = set()
    for r in book_results:
        s = r.get('stages', {})
        if not s.get('search') and s.get('detail') and r.get('status') != 'success':
            sea_n_det_y_urls.add(r.get('source_url', ''))

    search_ok_urls = set()
    for r in book_results:
        s = r.get('stages', {})
        if s.get('search'):
            search_ok_urls.add(r.get('source_url', ''))

    print(f'sea=N det=Y: {len(sea_n_det_y_urls)}, search OK: {len(search_ok_urls)}')

    def get_domain(url):
        if not url: return ''
        try:
            base = url.split('#')[0].strip()
            if '://' not in base: base = 'http://' + base
            return (urlparse(base).hostname or '').lower().replace('www.', '')
        except: return ''

    source_map = {s.get('bookSourceUrl', ''): s for s in all_sources}

    fixed = []
    for url in sea_n_det_y_urls:
        if url not in source_map: continue
        source = source_map[url]
        domain = get_domain(url)
        for s in all_sources:
            if s.get('bookSourceUrl') == url: continue
            if get_domain(s.get('bookSourceUrl', '')) != domain: continue
            if s.get('bookSourceUrl', '') not in search_ok_urls: continue
            if s.get('searchUrl') and '@js:' not in s.get('searchUrl', ''):
                source['searchUrl'] = s['searchUrl']
                if not source.get('ruleSearch', {}).get('bookList'):
                    if s.get('ruleSearch'):
                        source['ruleSearch'] = s['ruleSearch']
                fixed.append(source)
                break

    print(f'Cross-feed fixable: {len(fixed)}')

    if fixed:
        saved = 0
        for i in range(0, len(fixed), 50):
            batch = fixed[i:i+50]
            ok = await client.save_book_sources(batch)
            saved += len(batch) if ok else 0
        print(f'Saved to device: {saved}')

        # Verify first 50
        print('Verifying first 50...')
        improved = 0
        for idx, src in enumerate(fixed[:50]):
            try:
                logs = await asyncio.wait_for(client.ws_debug_book_source(src, '斗破苍穹'), timeout=60)
                for msg in logs:
                    if '列表大小' in msg or '搜索结果' in msg:
                        improved += 1
                        break
            except: pass
            if (idx+1) % 10 == 0:
                print(f'  {idx+1}/50, improved: {improved}')
        print(f'Verified 50, search improved: {improved}')

    await client.close()

asyncio.run(main())
