#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
站点E子站深度HTML分析（脱敏输出）
提取列表项结构/链接路径/播放页特征/搜索URL格式
"""
import sys
import json
import re
from urllib.parse import urlparse, urljoin
from playwright.sync_api import sync_playwright

MS_DOMAINS = {
    "microsoft.com", "microsoftonline.com", "live.com", "office.com",
    "office365.com", "sway.cloud.microsoft", "sway.office.com",
    "azureedge.net", "msftauth.net", "sharepoint.com", "docs.com",
    "skype.com", "bing.com", "msn.com", "windows.net", "xbox.com",
    "github.com", "linkedin.com", "twitter.com", "facebook.com",
    "youtube.com", "youtu.be", "vimeo.com", "soundcloud.com",
    "sketchfab.com", "pickit.com", "google.com", "googleapis.com",
    "gstatic.com", "cloudflare.com", "jsdelivr.net", "unpkg.com",
    "w3.org", "schema.org", "msft.net", "azure.com",
}


def is_ms_domain(domain):
    domain = domain.lower()
    for ms in MS_DOMAINS:
        if domain == ms or domain.endswith("." + ms):
            return True
    return False


def main():
    print("=== 站点E子站深度HTML分析（脱敏）===")
    
    with open("output/siteE_subsites.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    
    subsites = []
    for url in data["subsites"]:
        try:
            parsed = urlparse(url)
            domain = parsed.netloc
            if is_ms_domain(domain):
                continue
            if domain.endswith(".cfd") or domain.endswith(".xyz") or domain.endswith(".buzz"):
                if url not in subsites:
                    subsites.append(url)
        except Exception:
            continue
    
    print(f"共 {len(subsites)} 个子站")
    print()
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=['--disable-blink-features=AutomationControlled', '--no-sandbox']
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            locale="zh-CN",
        )
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            window.chrome = {runtime: {}};
        """)
        page = context.new_page()
        
        for i, url in enumerate(subsites):
            print(f"=== 子站[{i+1}] 深度分析 ===")
            try:
                page.goto(url, timeout=45000, wait_until="domcontentloaded")
                page.wait_for_timeout(5000)
                
                # 检测安全检测页面
                title = page.title()
                if "检测" in title:
                    page.wait_for_timeout(15000)
                    title = page.title()
                
                print(f"  标题: {title[:30]}")
                
                # 深度提取列表项结构
                deep = page.evaluate("""() => {
                    const r = {};
                    // 1. 找所有含链接的div容器（可能是列表项）
                    const allDivs = Array.from(document.querySelectorAll('div'));
                    const listCandidates = [];
                    allDivs.forEach(d => {
                        const links = d.querySelectorAll('a[href]');
                        const imgs = d.querySelectorAll('img');
                        // 列表项特征：有链接+有图片+子元素少
                        if (links.length >= 1 && imgs.length >= 1 && d.children.length <= 6) {
                            const cls = d.className || '';
                            const parentCls = d.parentElement ? (d.parentElement.className || '') : '';
                            // 排除导航/页头等
                            if (cls && !['nav','header','footer','menu'].some(k => cls.toLowerCase().includes(k))) {
                                listCandidates.push({
                                    cls: cls.substring(0, 60),
                                    parentCls: parentCls.substring(0, 40),
                                    childCount: d.children.length,
                                    linkHref: links[0].href,
                                    linkPath: links[0].pathname,
                                    linkText: links[0].textContent.trim().substring(0, 30),
                                    imgSrc: imgs[0].src || imgs[0].getAttribute('data-src') || '',
                                    imgAlt: imgs[0].alt || ''
                                });
                            }
                        }
                    });
                    r.listCandidates = listCandidates.slice(0, 5);
                    r.totalListCandidates = listCandidates.length;
                    
                    // 2. 如果列表候选多，找共同的class模式
                    if (listCandidates.length > 3) {
                        const clsCounts = {};
                        listCandidates.forEach(c => {
                            clsCounts[c.cls] = (clsCounts[c.cls] || 0) + 1;
                        });
                        r.topListClass = Object.entries(clsCounts).sort((a,b) => b[1]-a[1])[0];
                    }
                    
                    // 3. 提取所有链接路径模式（去重）
                    const allLinks = Array.from(document.querySelectorAll('a[href]'));
                    const pathPatterns = {};
                    allLinks.forEach(a => {
                        try {
                            const path = a.pathname;
                            // 提取路径模式（数字替换为{id}）
                            const pattern = path.replace(/\\d+/g, '{id}');
                            if (!pathPatterns[pattern]) {
                                pathPatterns[pattern] = {count: 0, sample: a.href, text: a.textContent.trim().substring(0,20)};
                            }
                            pathPatterns[pattern].count++;
                        } catch(e){}
                    });
                    r.pathPatterns = Object.entries(pathPatterns)
                        .filter(([k,v]) => v.count >= 2)
                        .sort((a,b) => b[1].count - a[1].count)
                        .slice(0, 8)
                        .map(([k,v]) => ({pattern: k, count: v.count, sampleText: v.text}));
                    
                    // 4. 搜索表单详细分析
                    const form = document.querySelector('form');
                    if (form) {
                        r.formAction = form.action;
                        r.formInputs = Array.from(form.querySelectorAll('input,select,button')).map(el => ({
                            tag: el.tagName,
                            name: el.name,
                            type: el.type,
                            value: el.value ? el.value.substring(0,30) : ''
                        }));
                        // select选项
                        const selects = form.querySelectorAll('select');
                        r.selectOptions = [];
                        selects.forEach(s => {
                            Array.from(s.options).slice(0,10).forEach(o => {
                                r.selectOptions.push({name: s.name, value: o.value, text: o.textContent.trim().substring(0,15)});
                            });
                        });
                    }
                    
                    // 5. 检测视频播放相关特征
                    const html = document.documentElement.outerHTML;
                    r.hasPlayerData = html.includes('player_data') || html.includes('player_aaaa');
                    r.hasM3u8 = html.includes('m3u8') || html.includes('.m3u8');
                    r.hasHlsJs = html.includes('hls.js') || html.includes('HlsPlayer');
                    r.hasVideoTag = !!document.querySelector('video');
                    r.hasIframe = document.querySelectorAll('iframe').length;
                    
                    // 6. 分页分析
                    const paginations = document.querySelectorAll('.pagination, .page, .pager, [class*="page"], [class*="pagi"]');
                    r.paginationCount = paginations.length;
                    if (paginations.length > 0) {
                        const pg = paginations[0];
                        r.paginationHTML = pg.outerHTML.substring(0, 300);
                        r.paginationLinks = Array.from(pg.querySelectorAll('a')).slice(0,5).map(a => a.href);
                    }
                    
                    // 7. 导航分类链接
                    const navLinks = allLinks.filter(a => {
                        const p = a.pathname;
                        return p.includes('/list/') || p.includes('/type/') || p.includes('/category/') || p.includes('/vod/') || (p.match(/\\//g) || []).length <= 2;
                    }).slice(0, 15).map(a => ({path: a.pathname.substring(0,40), text: a.textContent.trim().substring(0,15)}));
                    r.navLinks = navLinks;
                    
                    return r;
                }""")
                
                print(f"  列表候选总数: {deep.get('totalListCandidates',0)}")
                if deep.get('topListClass'):
                    print(f"  最常见列表class: {deep['topListClass'][0][:50]} (出现{deep['topListClass'][1]}次)")
                
                print(f"  列表候选样本(前3):")
                for j, c in enumerate(deep.get('listCandidates',[])[:3]):
                    print(f"    [{j}] class={c['cls'][:30]} | 链接路径={c['linkPath'][:40]} | 文本={c['linkText'][:20]}")
                
                print(f"  链接路径模式(前5):")
                for pp in deep.get('pathPatterns',[])[:5]:
                    print(f"    {pp['pattern'][:40]} (x{pp['count']}) 样本文本={pp['sampleText']}")
                
                print(f"  搜索表单:")
                print(f"    action路径: {urlparse(deep.get('formAction','')).path[:30]}")
                print(f"    输入框: {deep.get('formInputs',[])}")
                if deep.get('selectOptions'):
                    print(f"    select选项(前5): {deep['selectOptions'][:5]}")
                
                print(f"  视频特征:")
                print(f"    player_data: {deep.get('hasPlayerData',False)}")
                print(f"    m3u8: {deep.get('hasM3u8',False)}")
                print(f"    hls.js: {deep.get('hasHlsJs',False)}")
                print(f"    video标签: {deep.get('hasVideoTag',False)}")
                print(f"    iframe数: {deep.get('hasIframe',0)}")
                
                print(f"  分页: {deep.get('paginationCount',0)}个")
                if deep.get('paginationLinks'):
                    print(f"    分页链接样本: {urlparse(deep['paginationLinks'][0]).path[:30]}")
                
                print(f"  导航链接(前5):")
                for nl in deep.get('navLinks',[])[:5]:
                    print(f"    路径={nl['path']} | 文本={nl['text']}")
                
                # 保存HTML
                html = page.content()
                with open(f"output/siteE_sub{i+1}.html", "w", encoding="utf-8") as f:
                    f.write(html)
                
                print()
                
            except Exception as e:
                print(f"  [ERROR] {type(e).__name__}: {str(e)[:80]}")
                print()
        
        browser.close()
    
    print("=== 深度分析完成 ===")


if __name__ == "__main__":
    main()
