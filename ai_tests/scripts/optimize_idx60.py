#!/usr/bin/env python3
"""optimize_idx60.py — idx=60 专项优化：站点迁移处理

idx=60 站点已迁移，HTML提示备用域名。
脚本内部：
1. 访问原 sourceUrl
2. 从HTML提取备用域名
3. 用备用域名替换 sourceUrl 的域名部分
4. 重新访问新 sourceUrl
5. 提取4字段（sourceIcon/searchUrl/sortUrl/ruleNextPage）
6. 更新 optimized_final_v3.json

输出：idx + 替换状态 + 新源可达性 + 提取字段数
不输出：原域名/新域名/URL
"""
import json
import re
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding='utf-8')

INPUT_PATH = 'f:/myself/github/WeAgentChat/temp/legado/output/rss/optimized_final.json'
OUTPUT_PATH = 'f:/myself/github/WeAgentChat/temp/legado/output/rss/optimized_final_v3.json'

TARGET_IDX = 60

EXTRACT_JS = """
(() => {
    const result = {sourceIcon: '', searchUrl: '', sortUrl: '', ruleNextPage: ''};
    
    // 1. sourceIcon: favicon
    const iconLink = document.querySelector('link[rel*="icon"]') || document.querySelector('link[rel="shortcut icon"]');
    if (iconLink && iconLink.href) {
        result.sourceIcon = iconLink.href;
    }
    
    // 2. searchUrl: 找搜索表单
    const forms = document.querySelectorAll('form');
    for (const form of forms) {
        const action = form.action || form.getAttribute('action');
        const textInput = form.querySelector('input[type="text"], input[type="search"], input:not([type])');
        if (action && textInput && textInput.name) {
            let fullAction = action;
            if (action.startsWith('/')) {
                fullAction = location.origin + action;
            }
            const sep = fullAction.includes('?') ? '&' : '?';
            result.searchUrl = fullAction + sep + textInput.name + '={{key}}';
            break;
        }
    }
    
    // 3. sortUrl: 找分类链接
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
        const items = catLinks.slice(0, 5).map(link => '分类::' + link);
        result.sortUrl = items.join('\\n');
    }
    
    // 4. ruleNextPage: 找分页
    const nextByClass = document.querySelector('a.next, a.next-page, a.page-link.next');
    if (nextByClass && nextByClass.href) {
        result.ruleNextPage = '@CSS:a.next@href';
    } else {
        const nextByRel = document.querySelector('a[rel="next"]');
        if (nextByRel && nextByRel.href) {
            result.ruleNextPage = '@CSS:a[rel="next"]@href';
        } else {
            const allLinks = document.querySelectorAll('a');
            for (const a of allLinks) {
                const text = (a.textContent || '').trim();
                if (text === '下一页' || text === 'Next' || text === '>') {
                    if (a.href) {
                        result.ruleNextPage = '@CSS:a:contains(下一页)@href';
                        break;
                    }
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
        if value.startswith(('@CSS:', '@XPath:', '@js:', '<js>')):
            return True
        if '@href' in value:
            return True
        return False
    if field in ('sourceIcon', 'searchUrl', 'sortUrl'):
        if not value.startswith(('http', '/', '@js:', '<js>')):
            return False
        return True
    return True


def main():
    print('=' * 70)
    print(f'idx={TARGET_IDX} 站点迁移专项优化（脱敏）')
    print('=' * 70)
    
    with open(INPUT_PATH, 'r', encoding='utf-8') as f:
        sources = json.load(f)
    
    s = sources[TARGET_IDX]
    source_url = s.get('sourceUrl', '')
    
    if not source_url.startswith('http'):
        print(f'  sourceUrl非http开头，跳过')
        return
    
    # 提取原 base_url（脚本内部用，不输出）
    base = re.sub(r'\{\{.*\}\}', '', source_url)
    m = re.match(r'(https?://[^/]+)', base)
    original_base = m.group(1) + '/' if m else ''
    
    print(f'  原源URL长度: {len(source_url)}')
    print(f'  原base_url长度: {len(original_base)}')
    
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
        
        # 步骤1: 访问原URL，提取备用域名
        print(f'\n--- 步骤1: 访问原URL提取备用域名 ---')
        try:
            resp = page.goto(original_base, wait_until='domcontentloaded', timeout=30000)
            content = page.content() or ''
            print(f'  原URL访问: status={resp.status if resp else 0} html_len={len(content)}')
            
            # 从HTML提取备用域名（不输出域名本身）
            # 模式：备用域名：xxx.yyy.zzz 或 备用域名：xxx
            backup_domain = None
            
            # 尝试多种模式
            patterns = [
                r'备用域名[：:]\s*([a-zA-Z0-9\-\.]+\.[a-zA-Z]{2,})',
                r'新域名[：:]\s*([a-zA-Z0-9\-\.]+\.[a-zA-Z]{2,})',
                r'最新域名[：:]\s*([a-zA-Z0-9\-\.]+\.[a-zA-Z]{2,})',
                r'当前域名[：:]\s*([a-zA-Z0-9\-\.]+\.[a-zA-Z]{2,})',
                r'请访问[：:]\s*([a-zA-Z0-9\-\.]+\.[a-zA-Z]{2,})',
            ]
            for pattern in patterns:
                m = re.search(pattern, content)
                if m:
                    backup_domain = m.group(1)
                    print(f'  提取到备用域名（不输出）: 长度={len(backup_domain)}')
                    break
            
            # 也尝试从"最新域名获取地址"提取URL，再访问该URL获取真实域名
            if not backup_domain:
                # 模式：最新域名获取地址：URL 或 备用地址：URL
                url_pattern = r'(?:最新域名获取地址|备用地址|新地址|获取地址)[：:]\s*(https?://[^\s<>"\']+)'
                m = re.search(url_pattern, content)
                if m:
                    fetch_url = m.group(1)
                    print(f'  找到最新域名获取地址（不输出URL）: 长度={len(fetch_url)}')
                    
                    # 访问该URL获取真实域名
                    try:
                        resp2 = page.goto(fetch_url, wait_until='domcontentloaded', timeout=30000)
                        content2 = page.content() or ''
                        print(f'  获取地址访问: status={resp2.status if resp2 else 0} html_len={len(content2)}')
                        
                        # 从新页面提取域名（通常是纯文本或简单HTML）
                        # 尝试多种模式
                        for pattern in patterns:
                            m = re.search(pattern, content2)
                            if m:
                                backup_domain = m.group(1)
                                print(f'  从获取地址提取到域名（不输出）: 长度={len(backup_domain)}')
                                break
                        
                        # 如果没匹配到模式，可能整个内容就是域名
                        if not backup_domain:
                            # 去掉HTML标签
                            text = re.sub(r'<[^>]+>', '', content2).strip()
                            # 看看是否是纯域名
                            m = re.match(r'^([a-zA-Z0-9\-\.]+\.[a-zA-Z]{2,})$', text)
                            if m:
                                backup_domain = m.group(1)
                                print(f'  从纯文本提取到域名（不输出）: 长度={len(backup_domain)}')
                            else:
                                # 找第一个看起来像域名的字符串
                                m = re.search(r'\b([a-zA-Z0-9\-]+\.[a-zA-Z]{2,}(?:\.[a-zA-Z]{2,})?)\b', text)
                                if m:
                                    backup_domain = m.group(1)
                                    print(f'  从文本提取到候选域名（不输出）: 长度={len(backup_domain)}')
                    except Exception as e:
                        err_msg = str(e)
                        err_msg_safe = re.sub(r'https?://[^\s"\']+', '[URL]', err_msg)
                        print(f'  获取地址访问失败: {type(e).__name__}: {err_msg_safe[:100]}')
            
            if not backup_domain:
                print(f'  未提取到备用域名，无法优化')
                browser.close()
                return
            
            # 步骤2: 用备用域名替换sourceUrl的域名部分（脚本内部）
            print(f'\n--- 步骤2: 用备用域名替换sourceUrl ---')
            # 提取协议
            protocol_match = re.match(r'(https?://)([^/]+)(/.*)?', source_url)
            if not protocol_match:
                print(f'  sourceUrl格式不匹配，跳过')
                browser.close()
                return
            
            protocol = protocol_match.group(1)
            old_domain = protocol_match.group(2)
            path = protocol_match.group(3) or ''
            
            # 构造新 sourceUrl
            # 注意：backup_domain 可能是 "api.xxx.com" 形式，需要看是否包含协议
            if backup_domain.startswith('http'):
                new_source_url = backup_domain + path
            else:
                new_source_url = protocol + backup_domain + path
            
            print(f'  新sourceUrl长度: {len(new_source_url)}')
            print(f'  域名是否变化: {old_domain != backup_domain}')
            
            # 步骤3: 访问新 sourceUrl
            print(f'\n--- 步骤3: 访问新sourceUrl ---')
            new_base = re.sub(r'\{\{.*\}\}', '', new_source_url)
            m = re.match(r'(https?://[^/]+)', new_base)
            new_base_url = m.group(1) + '/' if m else ''
            
            try:
                resp3 = page.goto(new_base_url, wait_until='domcontentloaded', timeout=30000)
                # 等待渲染
                page.wait_for_timeout(5000)
                try:
                    page.wait_for_load_state('networkidle', timeout=15000)
                except Exception:
                    pass
                
                content3 = page.content() or ''
                status3 = resp3.status if resp3 else 0
                
                print(f'  新URL访问: status={status3} html_len={len(content3)}')
                
                if status3 != 200 or len(content3) < 1000:
                    print(f'  新URL无法有效访问，不更新')
                    browser.close()
                    return
                
                # 步骤4: 提取4字段
                print(f'\n--- 步骤4: 提取4字段 ---')
                extracted = page.evaluate(EXTRACT_JS)
                
                valid_fields = {}
                for field, value in extracted.items():
                    if value:
                        is_valid = is_valid_field(field, value)
                        print(f'  {field}: len={len(value)} is_valid={is_valid}')
                        if is_valid:
                            valid_fields[field] = value
                
                # 步骤5: 更新 sources（脚本内部）
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
                
                print(f'\n✅ idx={TARGET_IDX} 优化完成')
                print(f'  变更字段数: {len(changes)}')
                print(f'  变更字段: {[c["field"] for c in changes]}')
                
            except Exception as e:
                err_msg = str(e)
                err_msg_safe = re.sub(r'https?://[^\s"\']+', '[URL]', err_msg)
                err_msg_safe = re.sub(r'\b[a-z0-9\-]+\.[a-z]{2,}[^\s]*', '[DOMAIN]', err_msg_safe, flags=re.IGNORECASE)
                print(f'  新URL访问异常: {type(e).__name__}: {err_msg_safe[:100]}')
        
        except Exception as e:
            err_msg = str(e)
            err_msg_safe = re.sub(r'https?://[^\s"\']+', '[URL]', err_msg)
            err_msg_safe = re.sub(r'\b[a-z0-9\-]+\.[a-z]{2,}[^\s]*', '[DOMAIN]', err_msg_safe, flags=re.IGNORECASE)
            print(f'  原URL访问异常: {type(e).__name__}: {err_msg_safe[:100]}')
        
        browser.close()


if __name__ == '__main__':
    main()
