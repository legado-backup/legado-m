#!/usr/bin/env python3
"""deep_optimize_58_60.py — 对 idx=58 和 60 单独深度分析

这两个源 status=200 但 html_len 很小（56/130字节），
可能是：
1. JS 渲染前的空壳（需要等待 networkidle）
2. 反爬返回的极简页面
3. 重定向页面

输出脱敏的 HTML 片段（去掉URL/域名/IP/cookie），判断页面类型。
"""
import json
import re
import sys
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding='utf-8')

INPUT_PATH = 'f:/myself/github/WeAgentChat/temp/legado/output/rss/optimized_final.json'

TARGET_IDX = [58, 60]


def sanitize_html(html):
    """脱敏HTML：去掉URL/域名/IP/cookie/敏感字段"""
    # 去掉URL
    html = re.sub(r'https?://[^\s"\'<>]+', '[URL]', html)
    # 去掉域名
    html = re.sub(r'\b[a-z0-9\-]+\.(?:com|net|org|cn|cc|xyz|top|info|biz|tv|me|live|club|shop|site|online|store|news|today|click|life|monster|pro|fun|skin|cfd|mom|buzz)\b[^\s"\'<>]*', '[DOMAIN]', html, flags=re.IGNORECASE)
    # 去掉IP
    html = re.sub(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', '[IP]', html)
    # 去掉可能的cookie
    html = re.sub(r'cookie[^;]*;?', '[COOKIE]', html, flags=re.IGNORECASE)
    # 截断
    return html[:500]


def main():
    print('=' * 70)
    print('idx=58 和 60 深度分析（脱敏HTML片段）')
    print('=' * 70)
    
    with open(INPUT_PATH, 'r', encoding='utf-8') as f:
        sources = json.load(f)
    
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
        
        for idx in TARGET_IDX:
            s = sources[idx]
            source_url = s.get('sourceUrl', '')
            
            # 提取 base_url
            base = re.sub(r'\{\{.*\}\}', '', source_url)
            m = re.match(r'(https?://[^/]+)', base)
            base_url = m.group(1) + '/' if m else ''
            
            print(f'\n  [idx={idx}] base_url_len={len(base_url)}')
            
            if not base_url:
                print(f'    跳过: sourceUrl非http开头')
                continue
            
            try:
                # 第一次访问
                resp = page.goto(base_url, wait_until='domcontentloaded', timeout=30000)
                status = resp.status if resp else 0
                
                # 等5秒让JS渲染
                page.wait_for_timeout(5000)
                
                content1 = page.content() or ''
                html_len1 = len(content1)
                
                print(f'    第一次访问: status={status} html_len={html_len1}')
                
                # 尝试等待 networkidle
                try:
                    page.wait_for_load_state('networkidle', timeout=15000)
                except Exception:
                    pass
                
                content2 = page.content() or ''
                html_len2 = len(content2)
                
                print(f'    networkidle后: html_len={html_len2}')
                
                # 输出脱敏HTML片段
                if html_len2 < 2000:
                    print(f'    HTML片段（脱敏）:')
                    sanitized = sanitize_html(content2)
                    print(f'    {sanitized}')
                else:
                    # 输出前500+后500
                    print(f'    HTML前500字节（脱敏）:')
                    sanitized = sanitize_html(content2[:500])
                    print(f'    {sanitized}')
                
                # 检查页面是否含关键字
                page_text = page.inner_text('body') or ''
                page_text_lower = page_text.lower()
                keywords = {
                    'cf_challenge': 'just a moment' in page_text_lower or 'cf-challenge' in content2.lower(),
                    'login_required': 'login' in page_text_lower or '登录' in page_text or '请登录' in page_text,
                    '404': '404' in page_text_lower or 'not found' in page_text_lower,
                    '403': '403' in page_text_lower or 'forbidden' in page_text_lower,
                    'cloudflare': 'cloudflare' in content2.lower(),
                    'captcha': 'captcha' in page_text_lower or '验证码' in page_text,
                    'maintenance': 'maintenance' in page_text_lower or '维护' in page_text,
                }
                print(f'    页面关键字检测:')
                for k, v in keywords.items():
                    if v:
                        print(f'      {k}: True')
                
                # 提取页面标题
                title = page.title() or ''
                print(f'    页面标题长度: {len(title)}')
                
            except Exception as e:
                err_msg = str(e)
                err_msg_safe = re.sub(r'https?://[^\s"\']+', '[URL]', err_msg)
                err_msg_safe = re.sub(r'\b[a-z0-9\-]+\.[a-z]{2,}[^\s]*', '[DOMAIN]', err_msg_safe, flags=re.IGNORECASE)
                err_msg_safe = err_msg_safe[:200]
                print(f'    异常: exception:{type(e).__name__} msg={err_msg_safe}')
        
        browser.close()


if __name__ == '__main__':
    main()
