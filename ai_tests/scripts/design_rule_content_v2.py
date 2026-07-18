#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RSS 订阅源批量优化 v2 - 阶段8 图片源/视频源ruleContent设计

职责：
1. 读取阶段7处理后的JSON
2. 对 type=1 图片源：根据DOM特征选择模板A/B/C/D
3. 对 type=2 视频源：根据DOM特征选择模板V1/V2/V3或空（依赖嗅探器）
4. 适配PhotoDialog调用链（Rss.getContent + NetworkUtils.getAbsoluteURL）
5. 适配VideoPlayerActivity（内置嗅探器优先）

源码调用链分析（ReadRss.kt 第99-124行）：
- type=1 无ruleContent: PhotoDialog(rssArticle.link) 直接用文章link作为图片URL
- type=1 有ruleContent: Rss.getContent 执行JS返回图片URL → PhotoDialog(url)
- type=2: 不走Rss.getContent，直接 startActivity<VideoPlayerActivity>，record=rssArticle.link

输出安全铁律：
- 脚本输出禁止包含业务字段原文
- 只输出技术指标：idx, type, template_chosen, has_rule
- Playwright 异常消息必须脱敏

输入：output/rss/deep_retry_v2.json（阶段7处理后）
输出：
  - output/rss/rule_content_v2.json（含ruleContent的JSON）
  - output/rss/v2_rule_content_report.json（ruleContent报告，仅技术指标）
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse

PROJECT_ROOT = Path(__file__).parent.parent.parent
INPUT_JSON = PROJECT_ROOT / "output" / "rss" / "deep_retry_v2.json"
# 兜底：如果阶段7未运行，从阶段6读取
INPUT_JSON_FALLBACK = PROJECT_ROOT / "output" / "rss" / "post_validated_v2.json"
# 进一步兜底：直接从阶段5读
INPUT_JSON_FALLBACK2 = PROJECT_ROOT / "output" / "rss" / "optimized_v2.json"

OUTPUT_JSON = PROJECT_ROOT / "output" / "rss" / "rule_content_v2.json"
OUTPUT_REPORT = PROJECT_ROOT / "output" / "rss" / "v2_rule_content_report.json"

PAGE_TIMEOUT = 15000

STEALTH_JS = """
() => {
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
    Object.defineProperty(navigator, 'languages', { get: () => ['zh-CN', 'zh', 'en'] });
    window.chrome = { runtime: {} };
}
"""

# 图片源 ruleContent 模板
IMAGE_TEMPLATE_A = """<js>
(function(){
    var img = document.querySelector('.content img, .main img, .article img, .photo img, main img, .detail img');
    if (img) {
        return img.src || img.getAttribute('data-src') || img.getAttribute('data-original') || '';
    }
    return '';
})();
</js>"""

IMAGE_TEMPLATE_B = """<js>
(function(){
    var img = document.querySelector('img[data-src], img[data-original], img.lazyload, img.lazy');
    if (img) {
        return img.getAttribute('data-src') || img.getAttribute('data-original') || '';
    }
    var fallback = document.querySelector('img[src]:not([src=""])');
    return fallback ? fallback.src : '';
})();
</js>"""

IMAGE_TEMPLATE_C = """<js>
(function(){
    var meta = document.querySelector('meta[property="og:image"], meta[name="og:image"], meta[name="twitter:image"]');
    if (meta) {
        return meta.getAttribute('content') || '';
    }
    return '';
})();
</js>"""

IMAGE_TEMPLATE_D = """@js:
var data = JSON.parse(result);
if (data && data.image_url) {
    return data.image_url;
} else if (data && data.data && data.data.url) {
    return data.data.url;
} else if (data && data.data && data.data.image_url) {
    return data.data.image_url;
}
return '';
"""

# 视频源 ruleContent 模板
VIDEO_TEMPLATE_V1 = """<js>
(function(){
    var scripts = document.querySelectorAll('script');
    for (var i = 0; i < scripts.length; i++) {
        var text = scripts[i].textContent || '';
        var match = text.match(/https?:\\/\\/[^\\s"'<>]+\\.m3u8[^\\s"'<>]*/);
        if (match) return match[0];
        match = text.match(/https?:\\/\\/[^\\s"'<>]+\\.mp4[^\\s"'<>]*/);
        if (match) return match[0];
    }
    var video = document.querySelector('video');
    if (video && video.src) return video.src;
    var source = document.querySelector('video source');
    if (source && source.src) return source.src;
    return '';
})();
</js>"""

VIDEO_TEMPLATE_V2 = """@js:
var data = JSON.parse(result);
if (data && data.url) {
    return data.url;
}
if (data && data.data && data.data.play_url) {
    return data.data.play_url;
}
if (data && data.list && data.list[0] && data.list[0].url) {
    return data.list[0].url;
}
return '';
"""

VIDEO_TEMPLATE_V3 = """<js>
(function(){
    var iframe = document.querySelector('iframe[src*="player"], iframe[src*="play"], iframe[src*="video"]');
    if (iframe) return iframe.src;
    return '';
})();
</js>"""

# DOM 特征检测JS
DETECT_FEATURES_JS = """
() => {
    return {
        has_main_img: !!document.querySelector('.content img, .main img, .article img, .photo img, main img, .detail img'),
        has_lazy_img: !!document.querySelector('img[data-src], img[data-original], img.lazyload, img.lazy'),
        has_og_image: !!document.querySelector('meta[property="og:image"], meta[name="og:image"], meta[name="twitter:image"]'),
        is_json_response: document.contentType === 'application/json',
        
        has_m3u8_in_script: /\\.m3u8/.test(document.body.innerHTML),
        has_mp4_in_script: /\\.mp4/.test(document.body.innerHTML),
        has_video_tag: !!document.querySelector('video'),
        has_player_iframe: !!document.querySelector('iframe[src*="player"], iframe[src*="play"], iframe[src*="video"]'),
    };
}
"""


def sanitize_exception(e: Exception) -> str:
    msg = str(e)
    msg = re.sub(r"https?://[^\s\"']+", "[URL]", msg)
    msg = re.sub(r"\b[a-z0-9\-]+\.[a-z]{2,}[^\s]*", "[DOMAIN]", msg, flags=re.IGNORECASE)
    return msg[:200]


def extract_base_url(source_url: str) -> str:
    if "{{" in source_url:
        base = re.sub(r"\{\{.*?\}\}", "", source_url)
        base = base.rstrip("/?")
        if base.startswith(("http://", "https://")):
            return base
    return source_url


def select_image_template(features: Dict) -> Tuple[str, str]:
    """根据DOM特征选择图片模板，返回 (template, reason)"""
    if features.get('is_json_response'):
        return IMAGE_TEMPLATE_D, 'json_api'
    if features.get('has_lazy_img'):
        return IMAGE_TEMPLATE_B, 'lazy_load'
    if features.get('has_og_image'):
        return IMAGE_TEMPLATE_C, 'og_image'
    if features.get('has_main_img'):
        return IMAGE_TEMPLATE_A, 'main_img'
    return '', 'no_template_fallback_to_link'


def select_video_template(features: Dict) -> Tuple[str, str]:
    """根据DOM特征选择视频模板，返回 (template, reason)"""
    if features.get('is_json_response'):
        return VIDEO_TEMPLATE_V2, 'json_api'
    if features.get('has_m3u8_in_script') or features.get('has_mp4_in_script'):
        return VIDEO_TEMPLATE_V1, 'script_m3u8_mp4'
    if features.get('has_player_iframe'):
        return VIDEO_TEMPLATE_V3, 'player_iframe'
    if features.get('has_video_tag'):
        return '', 'video_tag_sniffer'  # 依赖嗅探器
    return '', 'sniffer_default'  # 依赖嗅探器


def main():
    print("=" * 80)
    print("RSS v2 阶段8 图片源/视频源ruleContent设计")
    print("=" * 80)

    # 1. 选择输入文件（按优先级）
    input_path = None
    for candidate in [INPUT_JSON, INPUT_JSON_FALLBACK, INPUT_JSON_FALLBACK2]:
        if candidate.exists():
            input_path = candidate
            break

    if not input_path:
        print(f"[FATAL] 输入文件不存在")
        print(f"        尝试顺序: {INPUT_JSON.name} → {INPUT_JSON_FALLBACK.name} → {INPUT_JSON_FALLBACK2.name}")
        return

    print(f"[INFO] 输入文件: {input_path.name}")

    try:
        with open(input_path, "r", encoding="utf-8") as f:
            sources = json.load(f)
    except Exception as e:
        print(f"[FATAL] JSON解析失败: {sanitize_exception(e)}")
        return

    total = len(sources)
    print(f"[INFO] 输入源总数: {total}")

    # 统计图片源和视频源
    image_count = sum(1 for s in sources if s.get('type') == 1)
    video_count = sum(1 for s in sources if s.get('type') == 2)
    print(f"[INFO] 图片源(type=1): {image_count}")
    print(f"[INFO] 视频源(type=2): {video_count}")

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[FATAL] playwright 未安装")
        return

    # 2. 为图片源和视频源设计ruleContent
    final_sources: List[dict] = []
    report_records: List[dict] = []

    template_stats = {
        'image_template_A': 0, 'image_template_B': 0,
        'image_template_C': 0, 'image_template_D': 0, 'image_no_template': 0,
        'video_template_V1': 0, 'video_template_V2': 0, 'video_template_V3': 0,
        'video_sniffer': 0, 'video_no_template': 0,
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
            locale="zh-CN",
        )

        for idx, source in enumerate(sources):
            source_type = source.get('type', 0)

            # 只处理图片源和视频源
            if source_type not in (1, 2):
                final_sources.append(source)
                continue

            # 跳过已有ruleContent的源
            if source.get('ruleContent', '').strip():
                final_sources.append(source)
                report_records.append({
                    "idx": idx, "type": source_type,
                    "template": "existing", "reason": "already_has_ruleContent"
                })
                continue

            source_url = source.get("sourceUrl", "") or ""
            if not source_url.startswith(("http://", "https://")):
                # 不可访问源，跳过
                final_sources.append(source)
                report_records.append({
                    "idx": idx, "type": source_type,
                    "template": "none", "reason": "not_accessible"
                })
                continue

            access_url = extract_base_url(source_url)

            page = None
            template_chosen = ''
            reason = 'failed'

            try:
                page = context.new_page()
                page.add_init_script(STEALTH_JS)
                page.goto(access_url, timeout=PAGE_TIMEOUT, wait_until="domcontentloaded")
                page.wait_for_timeout(2000)

                features = page.evaluate(DETECT_FEATURES_JS)

                if source_type == 1:
                    template_chosen, reason = select_image_template(features)
                    if template_chosen:
                        if reason == 'json_api':
                            template_stats['image_template_D'] += 1
                        elif reason == 'lazy_load':
                            template_stats['image_template_B'] += 1
                        elif reason == 'og_image':
                            template_stats['image_template_C'] += 1
                        else:
                            template_stats['image_template_A'] += 1
                    else:
                        template_stats['image_no_template'] += 1
                elif source_type == 2:
                    template_chosen, reason = select_video_template(features)
                    if template_chosen:
                        if reason == 'json_api':
                            template_stats['video_template_V2'] += 1
                        elif reason == 'script_m3u8_mp4':
                            template_stats['video_template_V1'] += 1
                        elif reason == 'player_iframe':
                            template_stats['video_template_V3'] += 1
                        else:
                            template_stats['video_sniffer'] += 1
                    else:
                        # 空ruleContent，依赖嗅探器
                        if 'sniffer' in reason:
                            template_stats['video_sniffer'] += 1
                        else:
                            template_stats['video_no_template'] += 1

                # 设置ruleContent
                if template_chosen:
                    source['ruleContent'] = template_chosen

                source['sourceComment'] = (source.get("sourceComment", "") or "") + \
                    f"\n[AI_RULE_CONTENT:template={reason}]"

            except Exception as e:
                err_msg = sanitize_exception(e)
                reason = f'failed:{type(e).__name__}'
                if source_type == 1:
                    template_stats['image_no_template'] += 1
                else:
                    template_stats['video_no_template'] += 1
                print(f"  [FAIL] idx={idx} err={err_msg[:80]}")
            finally:
                if page:
                    try:
                        page.close()
                    except Exception:
                        pass

            final_sources.append(source)
            report_records.append({
                "idx": idx, "type": source_type,
                "template": reason, "has_rule": bool(template_chosen)
            })

            if (idx + 1) % 20 == 0:
                print(f"  [PROGRESS] {idx+1}/{total}")

        browser.close()

    # 输出
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(final_sources, f, ensure_ascii=False, indent=2)

    report = {
        "stage": "design_rule_content_v2",
        "input_file": str(input_path.name),
        "output_file": str(OUTPUT_JSON.name),
        "total_sources": total,
        "image_sources": image_count,
        "video_sources": video_count,
        "template_stats": template_stats,
        "records": report_records,
    }

    with open(OUTPUT_REPORT, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n[RESULT] ruleContent设计完成")
    print(f"  - 总源数:           {total}")
    print(f"  - 图片源:           {image_count}")
    print(f"  - 视频源:           {video_count}")
    print(f"\n[TEMPLATE] 模板使用统计:")
    for tpl, count in template_stats.items():
        if count > 0:
            print(f"  - {tpl:30s}: {count}")
    print(f"\n[OUTPUT]")
    print(f"  - ruleContent JSON: {OUTPUT_JSON}")
    print(f"  - 报告:             {OUTPUT_REPORT}")


if __name__ == "__main__":
    main()
