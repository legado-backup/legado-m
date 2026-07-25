#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""智能修复脚本：对非超时失败的书源做同域反哺+规则修复。

策略：
1. 从重测报告中提取可修复的源（有部分阶段成功的）
2. 按域名分组，找到同域名成功源
3. 反哺缺失的规则（先验证规则对DOM的匹配度）
4. 保存修复后的源到真机
5. 重试验证

用法:
    python smart_fix.py --input reports/retest-timeout-xxx.json --execute
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from legado_client.device.legado_web_client import LegadoWebClient


def extract_domain(url: str) -> str:
    if not url:
        return ""
    try:
        base = url.split("#")[0].strip()
        if "://" not in base:
            base = "http://" + base
        from urllib.parse import urlparse
        return (urlparse(base).hostname or "").lower().replace("www.", "")
    except Exception:
        return ""


def clean_url_hash(url: str) -> str:
    if not url:
        return url
    base = url.split("#")[0].strip().rstrip("/")
    if "://" not in base and base:
        base = "http://" + base
    return base + "/"


def _score_source(source: dict) -> int:
    """评分书源质量。"""
    score = 0
    if source.get("searchUrl"): score += 5
    rs = source.get("ruleSearch", {})
    if isinstance(rs, dict):
        for f, p in [("bookList", 3), ("name", 2), ("author", 1), ("bookUrl", 2), ("coverUrl", 1)]:
            if rs.get(f): score += p
    ri = source.get("ruleBookInfo", {})
    if isinstance(ri, dict):
        for f in ["name", "author", "intro", "coverUrl", "lastChapter", "tocUrl"]:
            if ri.get(f): score += 1
    rt = source.get("ruleToc", {})
    if isinstance(rt, dict):
        for f, p in [("chapterList", 5), ("chapterName", 2), ("chapterUrl", 2)]:
            if rt.get(f): score += p
    rc = source.get("ruleContent", {})
    if isinstance(rc, dict):
        if rc.get("content"): score += 8
    if source.get("exploreUrl"): score += 3
    if source.get("enabled"): score += 1
    return score


def _stage_needs(stages: dict) -> List[str]:
    """返回需要修复的阶段。"""
    needs = []
    if not stages.get("search"): needs.append("search")
    if not stages.get("detail"): needs.append("detail")
    if not stages.get("toc"): needs.append("toc")
    if not stages.get("content"): needs.append("content")
    return needs


def _merge_rules(target: dict, donor: dict, stages_needed: List[str]) -> dict:
    """从donor合并target缺失的规则，只合并需要的阶段。"""
    merged = dict(target)

    if "search" in stages_needed:
        # 合并 searchUrl
        if not merged.get("searchUrl") and donor.get("searchUrl"):
            merged["searchUrl"] = donor["searchUrl"]
        # 合并 ruleSearch
        rs_target = merged.get("ruleSearch", {})
        rs_donor = donor.get("ruleSearch", {})
        if isinstance(rs_target, dict) and isinstance(rs_donor, dict):
            for f in ["bookList", "name", "author", "bookUrl", "coverUrl", "intro", "kind"]:
                if not rs_target.get(f) and rs_donor.get(f):
                    rs_target[f] = rs_donor[f]
            merged["ruleSearch"] = rs_target

    if "detail" in stages_needed:
        ri_target = merged.get("ruleBookInfo", {})
        ri_donor = donor.get("ruleBookInfo", {})
        if isinstance(ri_target, dict) and isinstance(ri_donor, dict):
            for f in ["name", "author", "intro", "coverUrl", "lastChapter", "tocUrl", "kind"]:
                if not ri_target.get(f) and ri_donor.get(f):
                    ri_target[f] = ri_donor[f]
            merged["ruleBookInfo"] = ri_target

    if "toc" in stages_needed:
        rt_target = merged.get("ruleToc", {})
        rt_donor = donor.get("ruleToc", {})
        if isinstance(rt_target, dict) and isinstance(rt_donor, dict):
            for f in ["chapterList", "chapterName", "chapterUrl", "nextTocUrl", "isVip", "isPay"]:
                if not rt_target.get(f) and rt_donor.get(f):
                    rt_target[f] = rt_donor[f]
            merged["ruleToc"] = rt_target

    if "content" in stages_needed:
        rc_target = merged.get("ruleContent", {})
        rc_donor = donor.get("ruleContent", {})
        if isinstance(rc_target, dict) and isinstance(rc_donor, dict):
            for f in ["content", "replaceRegex", "nextContentUrl", "imageStyle"]:
                if not rc_target.get(f) and rc_donor.get(f):
                    rc_target[f] = rc_donor[f]
            merged["ruleContent"] = rc_target

    # 合并发现URL
    if not merged.get("exploreUrl") and donor.get("exploreUrl"):
        merged["exploreUrl"] = donor["exploreUrl"]

    return merged


async def main():
    parser = argparse.ArgumentParser(description="智能修复非超时失败源")
    parser.add_argument("--input", type=str, required=True, help="重测报告JSON路径")
    parser.add_argument("--execute", action="store_true", help="执行保存到真机")
    parser.add_argument("--output", type=str, default="")
    args = parser.parse_args()

    print("=" * 60)
    print(f" 智能修复非超时失败源")
    print(f" 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # 加载重测报告
    with open(args.input, "r", encoding="utf-8") as f:
        report = json.load(f)

    results = report.get("results", [])
    print(f" 总结果数: {len(results)}")

    # 提取可修复的源（非超时失败，有部分阶段成功）
    fixable = []
    timeout_only = []
    for r in results:
        if r["status"] == "success":
            continue
        if "WS_TIMEOUT" in r.get("errors", []) or "TIMEOUT" in r.get("errors", []):
            timeout_only.append(r)
            continue
        # 有至少一个阶段成功，或者非超时失败
        s = r["stages"]
        stages_passed = sum(1 for v in s.values() if v)
        if stages_passed > 0:
            # 部分成功，可修复
            fixable.append(r)
        else:
            # 全阶段失败但非超时，也可尝试同域反哺
            fixable.append(r)

    print(f" 可修复源: {len(fixable)}")
    print(f" 纯超时源: {len(timeout_only)} (跳过)")

    if not fixable:
        print(" 无需修复")
        return

    # 获取真机所有源
    client = LegadoWebClient(host="127.0.0.1", port=1122)
    all_sources = await client.get_book_sources()
    print(f" 真机书源总数: {len(all_sources)}")

    # 构建源映射
    source_map = {s.get("bookSourceUrl", ""): s for s in all_sources}

    # 按域名分组
    domain_groups: Dict[str, List[dict]] = {}
    for s in all_sources:
        domain = extract_domain(s.get("bookSourceUrl", ""))
        if domain:
            domain_groups.setdefault(domain, []).append(s)

    # 修复
    fixed_sources = []
    fix_stats = {"cross_feed": 0, "url_hash": 0, "enable": 0, "no_donor": 0}

    for r in fixable:
        url = r.get("source_url", "")
        if url not in source_map:
            continue

        source = source_map[url]
        stages_needed = _stage_needs(r["stages"])
        if not stages_needed:
            continue

        domain = extract_domain(url)
        same_domain = domain_groups.get(domain, [])

        # URL#清理
        modified = False
        if "#" in url:
            clean = clean_url_hash(url)
            source["bookSourceUrl"] = clean
            modified = True
            fix_stats["url_hash"] += 1

        # 启用禁用源
        if not source.get("enabled", True):
            source["enabled"] = True
            modified = True
            fix_stats["enable"] += 1

        # 同域反哺
        if same_domain and len(same_domain) > 1:
            # 找同域名中质量最高且满足需要阶段的源
            best_donor = None
            best_score = -1
            for donor in same_domain:
                if donor.get("bookSourceUrl") == url:
                    continue
                # 检查donor是否有我们需要的规则
                score = _score_source(donor)
                # 检查donor是否在我们缺失的阶段有规则
                has_needed = False
                if "search" in stages_needed and donor.get("searchUrl"):
                    has_needed = True
                if "detail" in stages_needed:
                    ri = donor.get("ruleBookInfo", {})
                    if isinstance(ri, dict) and any(ri.get(f) for f in ["name", "author", "tocUrl"]):
                        has_needed = True
                if "toc" in stages_needed:
                    rt = donor.get("ruleToc", {})
                    if isinstance(rt, dict) and rt.get("chapterList"):
                        has_needed = True
                if "content" in stages_needed:
                    rc = donor.get("ruleContent", {})
                    if isinstance(rc, dict) and rc.get("content"):
                        has_needed = True

                if has_needed and score > best_score:
                    best_score = score
                    best_donor = donor

            if best_donor:
                source = _merge_rules(source, best_donor, stages_needed)
                modified = True
                fix_stats["cross_feed"] += 1
            else:
                fix_stats["no_donor"] += 1
        else:
            fix_stats["no_donor"] += 1

        if modified:
            fixed_sources.append(source)

    print(f"\n修复统计:")
    print(f"  同域反哺: {fix_stats['cross_feed']}")
    print(f"  URL#清理: {fix_stats['url_hash']}")
    print(f"  启用禁用源: {fix_stats['enable']}")
    print(f"  无可用donor: {fix_stats['no_donor']}")
    print(f"  总修复源数: {len(fixed_sources)}")

    # 保存到真机
    if args.execute and fixed_sources:
        saved = 0
        # 批量保存
        for i in range(0, len(fixed_sources), 50):
            batch = fixed_sources[i:i + 50]
            ok = await client.save_book_sources(batch)
            if ok:
                saved += len(batch)
            else:
                # 逐个保存
                for src in batch:
                    ok2 = await client.save_book_source(src)
                    if ok2:
                        saved += 1
            print(f"  保存进度: {min(i + 50, len(fixed_sources))}/{len(fixed_sources)}")
        print(f"\n保存到真机: {saved}/{len(fixed_sources)}")

        # 清理URL#重复
        hash_urls = [s.get("bookSourceUrl", "") for s in fixed_sources if "#" in s.get("bookSourceUrl", "")]
        if hash_urls:
            # 获取最新源列表检查重复
            latest = await client.get_book_sources()
            latest_urls = set(s.get("bookSourceUrl", "") for s in latest)
            to_delete = []
            for h_url in hash_urls:
                clean = clean_url_hash(h_url)
                if clean in latest_urls:
                    to_delete.append(h_url)
            if to_delete:
                delete_payload = [{"bookSourceUrl": u} for u in to_delete]
                await client.delete_book_sources(delete_payload)
                print(f"  清理URL#重复: {len(to_delete)} 个")

    # 重试验证
    print(f"\n开始重试验证修复结果...")
    verified = 0
    improved = 0

    # 只验证有修改的源（取前200个，避免耗时太长）
    test_sample = fixed_sources[:200]
    sem = asyncio.Semaphore(10)

    async def _verify(src):
        nonlocal verified, improved
        async with sem:
            try:
                logs = await asyncio.wait_for(
                    client.ws_debug_book_source(src, "斗破苍穹"),
                    timeout=60,
                )
                parsed = parse_debug_logs(logs)
                new_stages = parsed["stages"]
                # 对比原结果
                old_url = src.get("bookSourceUrl", "")
                for r in fixable:
                    if r.get("source_url", "").rstrip("/") == old_url.rstrip("/"):
                        old_stages = r["stages"]
                        # 检查是否有改善
                        old_count = sum(1 for v in old_stages.values() if v)
                        new_count = sum(1 for v in new_stages.values() if v)
                        if new_count > old_count:
                            improved += 1
                        break
                verified += 1
                if verified % 50 == 0:
                    print(f"  验证进度: {verified}/{len(test_sample)}, 改善: {improved}")
            except Exception:
                verified += 1

    await asyncio.gather(*[_verify(src) for src in test_sample])
    print(f"\n验证结果: {verified} 个已验证, {improved} 个有改善")

    # 保存报告
    os.makedirs(os.path.join(SCRIPTS_DIR, "reports"), exist_ok=True)
    report_path = args.output or os.path.join(
        SCRIPTS_DIR, "reports",
        f"smart-fix-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    )
    report = {
        "timestamp": datetime.now().isoformat(),
        "fix_stats": fix_stats,
        "fixed_count": len(fixed_sources),
        "verified": verified,
        "improved": improved,
        "fixed_sources": [{"url": s.get("bookSourceUrl", ""), "name": s.get("bookSourceName", "?")}
                         for s in fixed_sources],
    }
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"报告: {report_path}")

    await client.close()


def parse_debug_logs(logs, source_type="book"):
    """解析WebSocket调试日志。"""
    result = {
        "stages": {"search": False, "detail": False, "toc": False, "content": False},
        "errors": [],
    }
    for msg in logs:
        if "列表大小" in msg or "搜索结果" in msg:
            result["stages"]["search"] = True
        if "获取书名" in msg or ("书名" in msg and "获取" in msg):
            result["stages"]["detail"] = True
        if "目录总数" in msg or "章节列表" in msg:
            result["stages"]["toc"] = True
        if ("获取正文" in msg and "成功" in msg) or "正文页解析完成" in msg:
            result["stages"]["content"] = True
        if "UnknownHostException" in msg:
            result["errors"].append("DNS")
        elif "SocketTimeoutException" in msg or "timeout" in msg.lower():
            result["errors"].append("TIMEOUT")
    return result


if __name__ == "__main__":
    asyncio.run(main())
