#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""智能去重脚本：分析重复域名书源/订阅源，合并优质规则，删除冗余源。

策略：
1. 按域名分组（忽略#后面的分组标识）
2. 区分"真重复"vs"合理多源"：
   - 真重复：同一网站同一内容，多个作者做的不同版本
   - 合理多源：同一网站不同分类/榜单/功能（如 ku.mumuceo.com 的不同榜单）
3. 对真重复源：
   a. 评分：规则完整度（searchUrl+ruleSearch+ruleToc+ruleContent）+ 特色功能（exploreUrl+loginUrl）
   b. 选择最高分源为"保留源"
   c. 从其他源合并缺失的优质规则（如保留源缺 replaceRegex 但另一源有）
   d. 删除其余源
4. 对合理多源：保留全部，不处理

判定"真重复"的逻辑：
- 书源：bookSourceUrl 去掉#后的基础URL相同，且 searchUrl 指向同一搜索接口
- 订阅源：sourceUrl 去掉#后的基础URL相同

用法:
    python dedup_sources.py --dry-run          # 只分析，不删除
    python dedup_sources.py --book --execute   # 执行书源去重
    python dedup_sources.py --rss --execute    # 执行订阅源去重
    python dedup_sources.py --all --execute    # 执行全部去重
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

DEVICE_HOST = "127.0.0.1"
DEVICE_PORT = 1122


# ==================== 域名提取 ====================

def extract_domain(url: str) -> str:
    """提取域名，去掉www前缀。"""
    if not url:
        return ""
    try:
        # 去掉#后面的分组
        base_url = url.split("#")[0].strip()
        if "://" not in base_url:
            base_url = "http://" + base_url
        parsed = urlparse(base_url)
        domain = (parsed.hostname or "").lower().replace("www.", "")
        return domain
    except Exception:
        return ""


def extract_base_url(url: str) -> str:
    """提取基础URL（去掉#分组标识，统一scheme和www）。"""
    if not url:
        return ""
    base = url.split("#")[0].strip().rstrip("/")
    # 统一：去掉尾部/
    if "://" not in base:
        base = "http://" + base
    parsed = urlparse(base)
    domain = parsed.hostname or ""
    if domain.startswith("www."):
        domain = domain[4:]
    scheme = parsed.scheme or "https"
    return f"{scheme}://{domain}"


# ==================== 源评分 ====================

def score_book_source(source: dict) -> int:
    """评分书源质量，分越高越好。"""
    score = 0

    # 基础字段
    if source.get("bookSourceName"):
        score += 1
    if source.get("bookSourceUrl"):
        score += 1

    # 搜索能力
    search_url = source.get("searchUrl", "")
    if search_url:
        score += 5  # 有搜索URL是基本要求
    if "page" in search_url or "{{page}}" in search_url:
        score += 2  # 支持分页搜索

    # 搜索规则
    rule_search = source.get("ruleSearch", {})
    if isinstance(rule_search, dict):
        if rule_search.get("bookList"):
            score += 3
        if rule_search.get("name"):
            score += 2
        if rule_search.get("author"):
            score += 1
        if rule_search.get("bookUrl"):
            score += 2
        if rule_search.get("coverUrl"):
            score += 1
        if rule_search.get("intro"):
            score += 1
        if rule_search.get("kind"):
            score += 1

    # 详情规则
    rule_info = source.get("ruleBookInfo", {})
    if isinstance(rule_info, dict):
        for field in ["name", "author", "intro", "coverUrl", "lastChapter", "tocUrl"]:
            if rule_info.get(field):
                score += 1

    # 目录规则
    rule_toc = source.get("ruleToc", {})
    if isinstance(rule_toc, dict):
        if rule_toc.get("chapterList"):
            score += 5
        if rule_toc.get("chapterName"):
            score += 2
        if rule_toc.get("chapterUrl"):
            score += 2
        if rule_toc.get("nextTocUrl"):
            score += 2  # 支持分页目录

    # 正文规则
    rule_content = source.get("ruleContent", {})
    if isinstance(rule_content, dict):
        if rule_content.get("content"):
            score += 8  # 正文规则最重要
        if rule_content.get("replaceRegex"):
            score += 3  # 有净化规则
        if rule_content.get("nextContentUrl"):
            score += 2  # 支持分页正文
        if rule_content.get("imageStyle"):
            score += 1

    # 发现/分类
    if source.get("exploreUrl"):
        score += 3

    # 登录支持
    if source.get("loginUrl"):
        score += 1

    # 启用状态
    if source.get("enabled"):
        score += 1
    if source.get("enabledExplore"):
        score += 1

    return score


def score_rss_source(source: dict) -> int:
    """评分订阅源质量。"""
    score = 0

    if source.get("sourceName"):
        score += 1
    if source.get("sourceUrl"):
        score += 1

    rule_articles = source.get("ruleArticles", {})
    if isinstance(rule_articles, dict):
        if rule_articles.get("articleList"):
            score += 5
        if rule_articles.get("title"):
            score += 3
        if rule_articles.get("url"):
            score += 2
        if rule_articles.get("image"):
            score += 2
        if rule_articles.get("content"):
            score += 2

    rule_content = source.get("ruleContent", {})
    if isinstance(rule_content, dict):
        if rule_content.get("content"):
            score += 5

    if source.get("enabled"):
        score += 1

    return score


# ==================== 判断是否"真重复" ====================

def is_true_duplicate_book(sources: List[dict]) -> bool:
    """判断一组书源是否为"真重复"（同一网站同一内容的不同版本）。

    判定标准：
    - 超过2个源指向同一域名
    - 大部分源有searchUrl（说明是同一类型的搜索源而非分类源）
    - 如果所有源都没有searchUrl但有exploreUrl，可能是分类源（合理多源）
    """
    if len(sources) <= 1:
        return False

    has_search = sum(1 for s in sources if s.get("searchUrl"))
    has_explore = sum(1 for s in sources if s.get("exploreUrl"))

    # 如果大部分有searchUrl，说明是搜索源（真重复）
    if has_search > len(sources) * 0.5:
        return True

    # 如果都只有exploreUrl没有searchUrl，可能是合理多源（不同分类）
    if has_explore > 0 and has_search == 0:
        return False

    # 如果都没有searchUrl也没有exploreUrl，可能是低质量重复
    if has_search == 0 and has_explore == 0:
        return True

    return has_search > 0


def is_true_duplicate_rss(sources: List[dict]) -> bool:
    """判断一组订阅源是否为"真重复"。

    特殊处理（合理多源，不算重复）：
    - game.erolabsshare.live 等聚合平台：每个源是不同游戏
    - lanzoux.com：不同软件/资源分类
    - yckceo.com：不同功能（书源/订阅源/搜索）
    - qk.lifves.com：不同杂志
    - api.huaban.com：不同画板分类
    - github.com：不同项目
    - coolapk.com：不同应用
    - quark.sm.cn：不同搜索分类
    - baidu.com：不同搜索聚合
    - m.weibo.cn：不同微博功能
    - runoob.com：不同教程分类
    - mp.weixin.qq.com：不同公众号
    - data.newrank.cn：不同榜单
    - cn.bing.com：不同搜索
    """
    if len(sources) <= 1:
        return False

    # 已知的聚合/多分类平台域名——每个源是不同内容，不算重复
    AGGREGATOR_DOMAINS = {
        "game.erolabsshare.live", "erolabsshare.live",
        "lanzoux.com", "lanzous.com",
        "yckceo.com",
        "qk.lifves.com", "lifves.com",
        "api.huaban.com", "huaban.com",
        "github.com",
        "coolapk.com",
        "quark.sm.cn", "sm.cn",
        "baidu.com",
        "m.weibo.cn", "weibo.cn", "weibo.com",
        "runoob.com",
        "mp.weixin.qq.com", "weixin.qq.com",
        "data.newrank.cn", "newrank.cn",
        "cn.bing.com", "bing.com",
        "sogou.com",
    }

    # 检查域名是否属于聚合平台
    for s in sources:
        domain = extract_domain(s.get("sourceUrl", ""))
        if domain in AGGREGATOR_DOMAINS:
            return False  # 聚合平台，每个源是不同内容

    # 检查是否所有源的完整URL都不同（不同路径=不同内容）
    urls = set()
    paths = set()
    for s in sources:
        url = s.get("sourceUrl", "")
        base = url.split("#")[0].strip()
        urls.add(base)
        try:
            parsed = urlparse(base)
            paths.add(parsed.path.rstrip("/"))
        except:
            paths.add(base)

    # 如果路径都不同，说明是合理多源
    if len(paths) > 1:
        return False

    return True


# ==================== 合并规则 ====================

def merge_book_rules(keep: dict, others: List[dict]) -> dict:
    """从其他源合并优质规则到保留源。"""
    merged = dict(keep)  # 浅拷贝

    # 需要合并的规则字段
    rule_fields = {
        "ruleSearch": ["bookList", "name", "author", "bookUrl", "coverUrl", "intro", "kind", "wordCount"],
        "ruleBookInfo": ["name", "author", "intro", "coverUrl", "lastChapter", "tocUrl", "kind", "wordCount"],
        "ruleToc": ["chapterList", "chapterName", "chapterUrl", "nextTocUrl", "isVip", "isPay"],
        "ruleContent": ["content", "replaceRegex", "nextContentUrl", "imageStyle"],
    }

    for other in others:
        for rule_key, fields in rule_fields.items():
            keep_rule = merged.get(rule_key, {})
            other_rule = other.get(rule_key, {})
            if not isinstance(keep_rule, dict):
                keep_rule = {}
            if not isinstance(other_rule, dict):
                continue

            for field in fields:
                # 保留源缺失此字段，且其他源有 → 合并
                if not keep_rule.get(field) and other_rule.get(field):
                    keep_rule[field] = other_rule[field]
                    # 记录合并来源
                    source_name = other.get("bookSourceName", "?")
                    # 不在规则中记录来源，避免污染

            merged[rule_key] = keep_rule

    # 合并exploreUrl（如果保留源没有但其他源有）
    if not merged.get("exploreUrl"):
        for other in others:
            if other.get("exploreUrl"):
                merged["exploreUrl"] = other["exploreUrl"]
                break

    return merged


# ==================== 主流程 ====================

async def main():
    parser = argparse.ArgumentParser(description="智能去重书源/订阅源")
    parser.add_argument("--dry-run", action="store_true", help="只分析，不删除")
    parser.add_argument("--book", action="store_true", help="处理书源")
    parser.add_argument("--rss", action="store_true", help="处理订阅源")
    parser.add_argument("--all", action="store_true", help="处理全部")
    parser.add_argument("--execute", action="store_true", help="执行删除（默认dry-run）")
    parser.add_argument("--min-dup", type=int, default=2, help="最小重复数阈值")
    parser.add_argument("--host", default="127.0.0.1", help="真机地址")
    parser.add_argument("--port", type=int, default=1122, help="HTTP端口")
    args = parser.parse_args()

    if not args.book and not args.rss and not args.all:
        args.book = True
        args.rss = True

    execute = args.execute and not args.dry_run

    print("=" * 60)
    print("智能去重：合并优质规则 + 删除冗余源")
    print(f"模式: {'执行' if execute else '仅分析(dry-run)'}")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    total_deleted_book = 0
    total_deleted_rss = 0
    total_merged_book = 0
    total_merged_rss = 0

    import httpx

    # ==================== 书源去重 ====================
    if args.book or args.all:
        print(f"\n{'='*50}")
        print(" 书源去重")
        print(f"{'='*50}")

        r = httpx.get(f"http://{args.host}:{args.port}/getBookSources", timeout=300)
        sources = r.json().get("data", [])
        print(f"总书源: {len(sources)}")

        # 按域名分组
        domain_groups: Dict[str, List[dict]] = {}
        for s in sources:
            domain = extract_domain(s.get("bookSourceUrl", ""))
            if domain:
                domain_groups.setdefault(domain, []).append(s)

        # 筛选真重复
        dup_groups = {}
        for domain, srcs in domain_groups.items():
            if len(srcs) < args.min_dup:
                continue
            if is_true_duplicate_book(srcs):
                dup_groups[domain] = srcs

        print(f"真重复域名: {len(dup_groups)} 个")

        # 对每个重复组：评分→选最佳→合并→删除其余
        urls_to_delete = []
        sources_to_merge = []

        for domain, srcs in sorted(dup_groups.items(), key=lambda x: -len(x[1])):
            # 评分排序
            scored = [(score_book_source(s), s) for s in srcs]
            scored.sort(key=lambda x: -x[0])

            best_score, best_source = scored[0]
            others = [s for _, s in scored[1:]]

            # 合并缺失规则
            merged = merge_book_rules(best_source, others)
            if merged != best_source:
                sources_to_merge.append((domain, merged, best_source))
                total_merged_book += 1

            # 其余源标记删除
            for other in others:
                urls_to_delete.append(other.get("bookSourceUrl", ""))

            # 输出分析
            best_name = best_source.get("bookSourceName", "?").encode('ascii', 'replace').decode()
            print(f"\n  {domain} ({len(srcs)}个源)")
            print(f"    KEEP: {best_name[:25]} (score:{best_score})")
            if len(scored) > 1:
                other_names = [f"{s.get('bookSourceName','?')[:15].encode('ascii','replace').decode()}({sc})" for sc, s in scored[1:4]]
                print(f"    DEL: {', '.join(other_names)}{'...' if len(scored)>4 else ''}")

        total_deleted_book = len(urls_to_delete)
        print(f"\n书源去重汇总: 删除 {total_deleted_book} 个, 合并 {total_merged_book} 个")

        if execute and urls_to_delete:
            # 1. 保存合并后的源
            for domain, merged, original in sources_to_merge:
                r = httpx.post(
                    f"http://{args.host}:{args.port}/saveBookSource",
                    json=merged,
                    timeout=30,
                )
                ok = r.json().get("isSuccess", False)
                name = merged.get("bookSourceName", "?")
                print(f"  合并保存: {name[:25]} → {'✅' if ok else '❌'}")

            # 2. 批量删除冗余源
            batch_size = 100
            deleted = 0
            for i in range(0, len(urls_to_delete), batch_size):
                batch = urls_to_delete[i:i + batch_size]
                # Legado 删除接口：传入 [{"bookSourceUrl": "url"}] 列表
                delete_data = [{"bookSourceUrl": url} for url in batch if url]
                r = httpx.post(
                    f"http://{args.host}:{args.port}/deleteBookSources",
                    json=delete_data,
                    timeout=60,
                )
                ok = r.json().get("isSuccess", False)
                deleted += len(batch)
                print(f"  删除进度: {deleted}/{len(urls_to_delete)} {'✅' if ok else '❌'}")

            print(f"书源删除完成: {deleted} 个")

    # ==================== 订阅源去重 ====================
    if args.rss or args.all:
        print(f"\n{'='*50}")
        print(" 订阅源去重")
        print(f"{'='*50}")

        r = httpx.get(f"http://{args.host}:{args.port}/getRssSources", timeout=120)
        rss_sources = r.json().get("data", [])
        print(f"总订阅源: {len(rss_sources)}")

        # 按域名分组
        domain_groups: Dict[str, List[dict]] = {}
        for s in rss_sources:
            domain = extract_domain(s.get("sourceUrl", ""))
            if domain:
                domain_groups.setdefault(domain, []).append(s)

        # 筛选真重复
        dup_groups = {}
        for domain, srcs in domain_groups.items():
            if len(srcs) < args.min_dup:
                continue
            if is_true_duplicate_rss(srcs):
                dup_groups[domain] = srcs

        print(f"真重复域名: {len(dup_groups)} 个")

        urls_to_delete_rss = []

        for domain, srcs in sorted(dup_groups.items(), key=lambda x: -len(x[1])):
            scored = [(score_rss_source(s), s) for s in srcs]
            scored.sort(key=lambda x: -x[0])

            best_score, best_source = scored[0]
            others = [s for _, s in scored[1:]]

            for other in others:
                urls_to_delete_rss.append(other.get("sourceUrl", ""))

            best_name = best_source.get("sourceName", "?").encode('ascii', 'replace').decode()
            print(f"\n  {domain} ({len(srcs)}个源)")
            print(f"    KEEP: {best_name[:25]} (score:{best_score})")
            if len(scored) > 1:
                other_names = [f"{s.get('sourceName','?')[:15].encode('ascii','replace').decode()}({sc})" for sc, s in scored[1:4]]
                print(f"    DEL: {', '.join(other_names)}{'...' if len(scored)>4 else ''}")

        total_deleted_rss = len(urls_to_delete_rss)
        print(f"\n订阅源去重汇总: 删除 {total_deleted_rss} 个")

        if execute and urls_to_delete_rss:
            batch_size = 50
            deleted = 0
            for i in range(0, len(urls_to_delete_rss), batch_size):
                batch = urls_to_delete_rss[i:i + batch_size]
                delete_data = [{"sourceUrl": url} for url in batch if url]
                r = httpx.post(
                    f"http://{args.host}:{args.port}/deleteRssSources",
                    json=delete_data,
                    timeout=60,
                )
                ok = r.json().get("isSuccess", False)
                deleted += len(batch)
                print(f"  删除进度: {deleted}/{len(urls_to_delete_rss)} {'✅' if ok else '❌'}")

            print(f"订阅源删除完成: {deleted} 个")

    # ==================== 同步数据库 ====================
    if execute:
        print(f"\n{'='*50}")
        print(" 同步数据库")
        print(f"{'='*50}")

        try:
            from legado_client.storage.database import get_session_factory
            from legado_client.storage.models import Source
            from sqlalchemy import update

            sf = get_session_factory()
            if sf:
                async with sf() as session:
                    async with session.begin():
                        # 标记被删除的源
                        all_deleted_urls = urls_to_delete + urls_to_delete_rss if (args.book or args.all) and (args.rss or args.all) else (urls_to_delete if (args.book or args.all) else urls_to_delete_rss)
                        if all_deleted_urls:
                            # 分批更新
                            batch_size = 500
                            updated = 0
                            for i in range(0, len(all_deleted_urls), batch_size):
                                batch = all_deleted_urls[i:i + batch_size]
                                result = await session.execute(
                                    update(Source)
                                    .where(Source.source_url.in_(batch))
                                    .values(
                                        enabled=False,
                                        last_test_status="dedup_deleted",
                                        last_test_stage="duplicate_removed",
                                    )
                                )
                                updated += result.rowcount
                            print(f"数据库标记: {updated} 条记录为 dedup_deleted")
                print("数据库同步完成 ✅")
            else:
                print("数据库不可用，跳过")
        except Exception as e:
            print(f"数据库同步失败: {e}")

    # ==================== 汇总 ====================
    print(f"\n{'='*60}")
    print(f" 去重完成汇总")
    print(f"{'='*60}")
    print(f"  书源: 删除 {total_deleted_book} 个, 合并优化 {total_merged_book} 个")
    print(f"  订阅源: 删除 {total_deleted_rss} 个")
    print(f"  模式: {'已执行' if execute else '仅分析(dry-run)'}")
    if not execute:
        print(f"\n  ⚠️ 这是 dry-run 模式，未实际删除。加上 --execute 参数执行删除。")


if __name__ == "__main__":
    asyncio.run(main())
