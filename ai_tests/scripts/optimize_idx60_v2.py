#!/usr/bin/env python3
"""optimize_idx60_v2.py — idx=60 终极优化：访问最新域名获取地址

idx=60 原HTML提示：
- 备用域名：xxx (已尝试，CF拦截)
- 最新域名获取地址：URL (未尝试)

本脚本访问"最新域名获取地址"，提取所有候选域名，逐个测试可达性，
找到第一个可达域名后用它替换 sourceUrl，然后访问新源提取4字段。

全程脱敏：不输出域名/URL
"""
import json
import re
import sys
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding='utf-8')

INPUT_PATH = 'f:/myself/github/WeAgentChat/temp/legado/output/rss/optimized_final.json'
OUTPUT_PATH = 'f:/myself/github/WeAgentChat/temp/legado/output/rss/optimized_final_v3.json'

TARGET_IDX = 60

EXTRACT_JS = """
(() => {
    const result = {sourceIcon: '', searchUrl: '', sortUrl: '', ruleNextPage: ''};
    const iconLink = document.querySelector('link[rel*="icon"]') || document.querySelector('link[rel="shortcut icon"]');
    if (iconLink && iconLink.href) result.sourceIcon = iconLink.href;
    const forms = document.querySelectorAll('form');
    for (const form of forms) {
        const action = form.action || form.getAttribute('action');
        const textInput = form.querySelector('input[type="text"], input[type="search"], input:not([type])');
        if (action && textInput && textInput.name) {
            let fullAction = action;
            if (action.startsWith('/')) fullAction = location.origin + action;
            const sep = fullAction.includes('?') ? '&' : '?';
            result.searchUrl = fullAction + sep + textInput.name + '={{key}}';
            break;
        }
    }
    const catKeywords = ['最新', '热门', '分类', '全部', '推荐', '排行'];
    const catLinks = [];
    document.querySelectorAll('a').forEach(a => {
        const text = (a.textContent || '').trim();
        const href = a.href;
        if (!href) return;
        for (const kw of catKeywords) {
            if (text.includes(kw) && !catLinks.includes(href)) {
                catLinks.push(href);
                break;
            }
        }
    });
    if (catLinks.length > 0) {
        result.sortUrl = catLinks.slice(0, 5).map(l => '分类::' + l).join('\\n');
    }
    const nextByClass = document.querySelector('a.next, a.next-page, a.page-link.next');
    if (nextByClass && nextByClass.href) {
        result.ruleNextPage = '@CSS:a.next@href';
    } else {
        const nextByRel = document.querySelector('a[rel="next"]');
        if (nextByRel && nextByRel.href) {
            result.ruleNextPage = '@CSS:a[rel="next"]@href';
        } else {
            for (const a of document.querySelectorAll('a')) {
                const text = (a.textContent || '').trim();
                if ((text === '下一页' || text === 'Next' || text === '>') && a.href) {
                    result.ruleNextPage = '@CSS:a:contains(下一页)@href';
                    break;
                }
            }
        }
    }
    return result;
})();
"""


def is_valid_field(field, value):
    if not value or not isinstance(value, str):
        return False
    if value.strip() in ('None', 'null', 'undefined', 'NaN', 'page'):
        return False
    if field == 'ruleNextPage':
        return value.startswith(('@CSS:', '@XPath:', '@js:', '<js>')) or '@href' in value
    if field in ('sourceIcon', 'searchUrl', 'sortUrl'):
        return value.startswith(('http', '/', '@js:', '<js>'))
    return True


def try_fetch_domain(page, url, timeout=20):
    """尝试访问URL，返回 (status, html_len, error_type)
    
    返回 status=200 且 html_len>1000 才算成功
    """
    try:
        resp = page.goto(url, wait_until='domcontentloaded', timeout=timeout*1000)
        status = resp.status if resp else 0
        page.wait_for_timeout(3000)
        try:
            page.wait_for_load_state('networkidle', timeout=10000)
        except Exception:
            pass
        content = page.content() or ''
        return (status, len(content), None)
    except Exception as e:
        err_msg = str(e)
        if 'ERR_HTTP2_PROTOCOL_ERROR' in err_msg:
            return (0, 0, 'http2_error')
        if 'ERR_SSL_PROTOCOL_ERROR' in err_msg:
            return (0, 0, 'ssl_protocol_error')
        if 'ERR_TUNNEL_CONNECTION_FAILED' in err_msg:
            return (0, 0, 'tunnel_failed')
        if 'ERR_CONNECTION_REFUSED' in err_msg:
            return (0, 0, 'connection_refused')
        if 'ERR_NAME_NOT_RESOLVED' in err_msg:
            return (0, 0, 'dns_error')
        if 'Timeout' in type(e).__name__ or 'timeout' in err_msg.lower():
            return (0, 0, 'timeout')
        return (0, 0, f'exception:{type(e).__name__}')


def extract_all_domains(text):
    """从文本中提取所有可能的域名（不输出域名本身，只返回列表）"""
    # 匹配域名模式：xxx.yyy[.zzz]
    pattern = r'\b([a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.(?:com|net|org|cn|cc|xyz|top|info|biz|tv|me|live|club|shop|site|online|store|news|today|click|life|monster|pro|fun|skin|cfd|mom|buzz|cc|gov|edu|io|app|dev)(?:\.[a-zA-Z]{2,})?)\b'
    matches = re.findall(pattern, text, re.IGNORECASE)
    # 去重
    seen = set()
    unique = []
    for d in matches:
        if d.lower() not in seen:
            seen.add(d.lower())
            unique.append(d)
    return unique


def main():
    print('=' * 70)
    print(f'idx={TARGET_IDX} 终极优化（脱敏）')
    print('=' * 70)
    
    with open(INPUT_PATH, 'r', encoding='utf-8') as f:
        sources = json.load(f)
    
    s = sources[TARGET_IDX]
    source_url = s.get('sourceUrl', '')
    
    if not source_url.startswith('http'):
        print(f'  sourceUrl非http开头，跳过')
        return
    
    base = re.sub(r'\{\{.*\}\}', '', source_url)
    m = re.match(r'(https?://[^/]+)', base)
    original_base = m.group(1) + '/' if m else ''
    original_protocol = m.group(1).split('://')[0] if m else 'https'
    
    print(f'  原sourceUrl长度: {len(source_url)}')
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-blink-features=AutomationControlled']
        )
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080},
            locale='zh-CN',
        )
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3,4,5]});
        """)
        
        page = context.new_page()
        
        # 步骤1: 访问原URL，提取所有域名线索
        print(f'\n--- 步骤1: 访问原URL提取所有域名线索 ---')
        try:
            resp = page.goto(original_base, wait_until='domcontentloaded', timeout=30000)
            content = page.content() or ''
            print(f'  原URL访问: status={resp.status if resp else 0} html_len={len(content)}')
            
            # 提取所有域名
            all_domains = extract_all_domains(content)
            print(f'  提取到候选域名数: {len(all_domains)}')
            
            # 提取所有URL
            url_pattern = r'https?://[^\s<>"\'<>]+'
            all_urls = re.findall(url_pattern, content)
            print(f'  提取到候选URL数: {len(all_urls)}')
            
            # 从"最新域名获取地址"提取URL
            fetch_url_pattern = r'(?:最新域名获取地址|备用地址|新地址|获取地址|当前域名)[：:]\s*(https?://[^\s<>"\']+)'
            fetch_urls = re.findall(fetch_url_pattern, content)
            print(f'  "最新域名获取地址"类URL数: {len(fetch_urls)}')
            
            # 收集所有要测试的候选域名
            candidate_domains = list(all_domains)
            
            # 对每个 fetch_url，访问后提取域名
            for fetch_url in fetch_urls[:3]:  # 最多3个
                print(f'\n  访问"最新域名获取地址"（不输出URL）...')
                try:
                    resp2 = page.goto(fetch_url, wait_until='domcontentloaded', timeout=20000)
                    content2 = page.content() or ''
                    print(f'    获取地址访问: status={resp2.status if resp2 else 0} html_len={len(content2)}')
                    
                    # 提取域名
                    domains_from_fetch = extract_all_domains(content2)
                    print(f'    从获取地址提取域名数: {len(domains_from_fetch)}')
                    
                    # 也尝试从纯文本提取（去掉HTML标签）
                    text = re.sub(r'<[^>]+>', '\n', content2)
                    domains_from_text = extract_all_domains(text)
                    print(f'    从纯文本提取域名数: {len(domains_from_text)}')
                    
                    # 合并
                    for d in domains_from_fetch + domains_from_text:
                        if d not in candidate_domains:
                            candidate_domains.append(d)
                except Exception as e:
                    err_msg = str(e)
                    err_msg_safe = re.sub(r'https?://[^\s"\']+', '[URL]', err_msg)
                    print(f'    获取地址访问失败: {type(e).__name__}')
            
            print(f'\n  总候选域名数: {len(candidate_domains)}')
            
            if not candidate_domains:
                print(f'  无候选域名，无法优化')
                browser.close()
                return
            
            # 步骤2: 逐个测试候选域名可达性
            print(f'\n--- 步骤2: 逐个测试候选域名可达性 ---')
            reachable_domain = None
            
            for i, domain in enumerate(candidate_domains):
                # 跳过明显不是站点域名的（如 googleapis.com、cloudflare.com 等）
                skip_domains = ['googleapis', 'cloudflare', 'gstatic', 'google', 'jquery', 'bootstrap', 'fontawesome', 'jsdelivr']
                if any(skip in domain.lower() for skip in skip_domains):
                    continue
                
                test_url = f'{original_protocol}://{domain}/'
                print(f'\n  候选[{i+1}]: 域名长度={len(domain)}')
                status, html_len, err = try_fetch_domain(page, test_url, timeout=15)
                print(f'    测试结果: status={status} html_len={html_len} err={err}')
                
                if status == 200 and html_len > 1000:
                    reachable_domain = domain
                    print(f'    ✅ 域名可达！')
                    break
                else:
                    print(f'    ❌ 不可达或内容太少')
            
            if not reachable_domain:
                print(f'\n  所有候选域名都不可达，无法优化')
                browser.close()
                return
            
            # 步骤3: 用可达域名替换sourceUrl并提取4字段
            print(f'\n--- 步骤3: 用可达域名替换sourceUrl ---')
            protocol_match = re.match(r'(https?://)([^/]+)(/.*)?', source_url)
            protocol = protocol_match.group(1)
            path = protocol_match.group(3) or ''
            
            new_source_url = protocol + reachable_domain + path
            print(f'  新sourceUrl长度: {len(new_source_url)}')
            
            # 访问新 base_url
            new_base = f'{protocol}{reachable_domain}/'
            print(f'  访问新base_url...')
            
            resp = page.goto(new_base, wait_until='domcontentloaded', timeout=30000)
            page.wait_for_timeout(5000)
            try:
                page.wait_for_load_state('networkidle', timeout=15000)
            except Exception:
                pass
            
            content = page.content() or ''
            status = resp.status if resp else 0
            print(f'  访问结果: status={status} html_len={len(content)}')
            
            if status != 200 or len(content) < 1000:
                print(f'  新base_url无法有效访问')
                browser.close()
                return
            
            # 提取4字段
            print(f'\n--- 步骤4: 提取4字段 ---')
            extracted = page.evaluate(EXTRACT_JS)
            
            valid_fields = {}
            for field, value in extracted.items():
                if value:
                    is_valid = is_valid_field(field, value)
                    print(f'  {field}: len={len(value)} is_valid={is_valid}')
                    if is_valid:
                        valid_fields[field] = value
            
            # 步骤5: 更新 sources
            print(f'\n--- 步骤5: 更新源数据 ---')
            changes = []
            
            # 更新 sourceUrl
            s['sourceUrl'] = new_source_url
            changes.append({'field': 'sourceUrl', 'change_type': 'domain_migrated'})
            print(f'  sourceUrl: 域名已迁移')
            
            # 更新4字段
            for field, new_value in valid_fields.items():
                current_value = s.get(field, '')
                current_valid = is_valid_field(field, current_value)
                if not current_valid:
                    s[field] = new_value
                    changes.append({
                        'field': field,
                        'before_len': len(current_value) if current_value else 0,
                        'after_len': len(new_value),
                    })
                    print(f'  {field}: before_len={len(current_value) if current_value else 0} after_len={len(new_value)}')
            
            # 保存
            with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
                json.dump(sources, f, ensure_ascii=False, indent=2)
            
            print(f'\n✅ idx={TARGET_IDX} 终极优化完成')
            print(f'  变更字段数: {len(changes)}')
            print(f'  变更字段: {[c["field"] for c in changes]}')
        
        except Exception as e:
            err_msg = str(e)
            err_msg_safe = re.sub(r'https?://[^\s"\']+', '[URL]', err_msg)
            err_msg_safe = re.sub(r'\b[a-z0-9\-]+\.[a-z]{2,}[^\s]*', '[DOMAIN]', err_msg_safe, flags=re.IGNORECASE)
            print(f'  异常: {type(e).__name__}: {err_msg_safe[:100]}')
        
        browser.close()


if __name__ == '__main__':
    main()
