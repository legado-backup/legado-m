# WebBook 搜索 — Python 重构参考

> 迁移自 [modules/webbook-search.md](../modules/webbook-search.md) 原「Python 重构参考」章节（2026-08-30 拆分）。本文件为 WebBook 搜索 Python 重构实现的唯一权威源：P1 WebBook 单例入口、P2 BookInfo 九字段解析、P3 BookContent 五步管线、P4 SearchModel 并发调度、P5 重构注意事项。
> Android 侧实现见 [modules/webbook-search.md](../modules/webbook-search.md)；WebSocket 推送协议见 [modules/web-service-api.md](../modules/web-service-api.md) §5。
> 小节编号（P1-P5）保留自原文件，便于溯源。

### P1. WebBook 单例入口

```python
import asyncio
from dataclasses import dataclass, field
from typing import Any, Callable
from enum import Enum
import re
import json


class NoStackTraceException(Exception):
    """不需要堆栈跟踪的异常，用于空 searchUrl 等场景"""
    pass


class WebBook:
    """网书操作的单例入口"""

    # ============================================================
    # P1.1 搜索书籍 — searchBookAwait
    # ============================================================

    @staticmethod
    async def search_book_await(
        book_source: BookSource,
        key: str,
        page: int = 0,
        filter_: dict | None = None,
        should_break: Callable[[list[SearchResult]], bool] | None = None
    ) -> list[SearchResult]:
        if not book_source.search_url:
            raise NoStackTraceException("搜索源未配置搜索 URL")

        rule_data = RuleData(
            source_url=book_source.search_url,
            base_url=book_source.book_source_url,
            key=key, page=page
        )
        response = await analyze_url_and_request(rule_data, book_source)
        response = await _login_check(book_source, response)
        await _check_redirect(book_source, response)

        results = BookList.analyze_book_list(
            book_source.rule_search, response.html,
            book_source.book_source_url, book_source
        )

        if filter_:
            results = [r for r in results
                       if filter_.get("name", "") in r.name]  # 源码大小写敏感

        if should_break and should_break(results):
            return results

        return results

    # ============================================================
    # P1.2 发现书籍 — exploreBookAwait
    # ============================================================

    @staticmethod
    async def explore_book_await(
        book_source: BookSource,
        key: str, page: int = 0,
        explore_info_map: dict[str, str] = None
    ) -> list[SearchResult]:
        source_url = explore_info_map.get(key, "") if explore_info_map else ""
        if not source_url:
            return []

        rule_data = RuleData(
            source_url=source_url,
            base_url=book_source.source_url,
            key=key, page=page
        )
        response = await analyze_url_and_request(rule_data, book_source)
        response = await _login_check(book_source, response)

        results = BookList.analyze_book_list(
            book_source.rule_explore, response.html,
            book_source.source_url, book_source
        )
        return results

    # ============================================================
    # P1.3 获取书籍详细信息 — getBookInfoAwait
    # ============================================================

    @staticmethod
    async def get_book_info_await(book: Book, book_source: BookSource) -> Book:
        book.remove_all_book_type()
        book.add_type(book_source.book_type)

        if book.info_html:
            BookInfo.analyze_book_info(book, book_source.rule_book_info, book.info_html)
            return book

        rule_data = RuleData(
            source_url=book.book_url,
            base_url=book_source.book_source_url
        )
        response = await analyze_url_and_request(rule_data, book_source)
        response = await _login_check(book_source, response)

        BookInfo.analyze_book_info(book, book_source.rule_book_info, response.html)
        return book

    # ============================================================
    # P1.4 获取目录列表 — getChapterListAwait
    # ============================================================

    @staticmethod
    async def get_chapter_list_await(
        book: Book, book_source: BookSource,
        run_pre_update: bool = True
    ) -> list[Chapter]:
        if run_pre_update:
            await WebBook.run_pre_update_js(book, book_source)

        if book.toc_html:
            BookChapterList.analyze_chapter_list(book, book_source.rule_toc, book.toc_html)
            return book.chapter_list

        rule_data = RuleData(source_url=book.toc_url, base_url=book.book_url)
        response = await analyze_url_and_request(rule_data, book_source)
        response = await _login_check(book_source, response)

        BookChapterList.analyze_chapter_list(book, book_source.rule_toc, response.html)
        return book.chapter_list

    # ============================================================
    # P1.5 获取章节正文 — getContentAwait
    # ============================================================

    @staticmethod
    async def get_content_await(
        chapter: Chapter, book: Book, book_source: BookSource
    ) -> str:
        content_rule = book_source.rule_content

        if not content_rule.content:
            return chapter.get_absolute_url()

        if chapter.is_volume and chapter.url.startswith(chapter.title):
            return ""

        body = book.toc_html if book.toc_html else None

        rule_data = RuleData(
            source_url=chapter.get_absolute_url(),
            base_url=book.toc_url,
            js_str=content_rule.web_js,
            source_regex=content_rule.source_regex
        )
        if body:
            rule_data.body = body

        response = await analyze_url_and_request(rule_data, book_source)
        response = await _login_check(book_source, response)

        content = BookContent.analyze_content(
            response.html, content_rule, chapter, book, book_source
        )
        return content

    # ============================================================
    # P1.6 精准搜索 — preciseSearchAwait
    # ============================================================

    @staticmethod
    async def precise_search_await(book_source: BookSource, key: str) -> Book | None:
        results = await WebBook.search_book_await(
            book_source, key,
            filter_={"name": key},
            should_break=lambda r: len(r) > 0
        )
        if not results:
            return None
        return results[0].to_book()

    # ============================================================
    # P1.7 内部方法 — 登录检测 / 重定向检测
    # ============================================================

    @staticmethod
    async def _login_check(book_source, response):
        login_js = book_source.login_check_js
        if not login_js:
            return response
        analyze_rule = AnalyzeRule(response, book_source)
        result = analyze_rule.eval_js(login_js)
        if result:
            login_response = await http_get(result)
            response = await http_get(response.original_url)
        return response

    @staticmethod
    async def _check_redirect(book_source, response):
        raw = response.raw
        prior = getattr(raw, "prior_response", None)
        if prior and prior.is_redirect:
            logger.debug("[WebBook] 书源 %s 发生重定向", book_source.book_source_url)
```

### P2. BookInfo 九字段解析

```python
class BookInfo:
    @staticmethod
    def analyze_book_info(book: Book, rule: BookInfoRule, html: str,
                          can_rename: bool = True) -> Book:
        # Step 1: 执行 init JS
        if rule.init:
            analyze_rule = AnalyzeRule(book, html)
            analyze_rule.eval_js(rule.init)
            html = analyze_rule.get_current_html()

        # Step 2: 提取各字段
        analyze_rule = AnalyzeRule(html, base_url=book.book_url)
        fields = {
            "name": rule.name, "author": rule.author,
            "cover_url": rule.cover_url, "intro": rule.intro,
            "kind": rule.kind, "latest_chapter_title": rule.last_chapter,
            "toc_url": rule.toc_url, "word_count": rule.word_count,
        }

        for field_name, rule_expr in fields.items():
            if not rule_expr:
                continue
            value = analyze_rule.extract_string(rule_expr)
            if can_rename:
                setattr(book, field_name, value)
            else:
                existing = getattr(book, field_name, None)
                if not existing:
                    setattr(book, field_name, value)
        return book
```

### P3. BookContent 五步管线

```python
class BookContent:
    @staticmethod
    def analyze_content(html, rule, chapter, book, book_source) -> str:
        # Step 1: content 规则提取正文
        content = _extract_content(html, rule.content, chapter.get_absolute_url())

        # Step 2: nextContentUrl 分页处理
        if rule.next_content_url:
            content = BookContent._process_pagination(content, rule, chapter, book, book_source)

        # Step 3: subContent 副文本处理
        if rule.sub_content:
            content = BookContent._process_sub_content(content, rule.sub_content, html)

        # Step 4: replaceRegex 替换
        if rule.replace_regex:
            content = BookContent._apply_replace_regex(content, rule.replace_regex)

        # Step 5: htmlFormatter + unescapeHtml
        content = _html_formatter(content)
        content = _unescape_html(content)

        return content.strip()

    @staticmethod
    def _process_pagination(base_content, rule, chapter, book, book_source) -> str:
        contents = [base_content]
        page_url = _get_next_page_url(html, rule.next_content_url)
        page_count = _get_page_count(rule)
        max_pages = page_count if page_count and page_count > 0 else 50

        for i in range(1, max_pages):
            next_url = _build_page_url(page_url, i)
            if not next_url:
                break
            page_html = _fetch_page_content(next_url, chapter, book, book_source)
            page_content = _extract_content(page_html, rule.content, next_url)
            if page_content:
                contents.append(page_content)
            elif not page_count:
                break
        return "\n".join(contents)

    @staticmethod
    def _process_sub_content(base_content, sub_rule, original_html) -> str:
        analyze_rule = AnalyzeRule(original_html)
        sub_text = analyze_rule.extract_string(sub_rule)
        if sub_text:
            return base_content + "\n\n" + sub_text
        return base_content

    @staticmethod
    def _apply_replace_regex(content, replace_rules) -> str:
        for rule_entry in replace_rules:
            pattern = rule_entry.get("pattern", "")
            replacement = rule_entry.get("replacement", "")
            if pattern:
                try:
                    content = re.sub(pattern, replacement, content)
                except re.error:
                    continue
        return content
```

### P4. SearchModel 并发调度

```python
class SearchModel:
    MAX_THREAD = 9

    async def search(self, key, search_id, precision=False, filter=None):
        if search_id != self.search_id:
            if self.search_key:
                await self.close()
            if not key:
                self.search_key = ""
                return
            self.search_key = key
            self.search_books.clear()
            self.book_source_parts = self.callback.get_search_scope().get_book_source_parts()
            if not self.book_source_parts:
                self._on_search_cancel(NoStackTraceException("书源列表为空"))
                return
            self.search_id = search_id
            self.search_page = 1
            self._init_search_pool()
        else:
            self.search_page += 1
        await self._start_search(precision, filter)

    async def _search_flow(self, precision, filter):
        self.callback.on_search_start()
        semaphore = asyncio.Semaphore(self.thread_count)

        async def search_one_source(bs):
            async with semaphore:
                try:
                    return await asyncio.wait_for(
                        self._search_source(bs, precision, filter), timeout=30.0)
                except asyncio.TimeoutError:
                    return []
                except Exception:
                    return []

        for bs_part in self.book_source_parts:
            for book_source in bs_part.book_sources:
                await self._wait_if_paused()
                items = await search_one_source(book_source)
                if items:
                    for item in items:
                        self._release_html_data(item)
                    await self._insert_search_results(items)
                    self._merge_items(items, precision)
                    self.callback.on_search_success(self.search_books)
                if self.search_id == 0:
                    return
        self._on_search_finish(not items, bool(items))

    def _merge_items(self, new_data, precision=False):
        key = self.search_key  # 注意：源码使用大小写敏感比较，不调用 .lower()
        equal_data, tags_data, contains_data, other_data = [], [], [], []

        for book in self.search_books:
            # 源码直接字符串比较（大小写敏感），不转小写
            if book.name == key or book.author == key:
                equal_data.append(book)
            elif book.kind and key in book.kind:
                tags_data.append(book)
            elif key in book.name or key in book.author:
                contains_data.append(book)
            else:
                other_data.append(book)

        def insert_with_dedup(target_group, new_book):
            for existing in target_group:
                # 源码使用直接字符串比较（大小写敏感），不转小写
                if existing.name == new_book.name and \
                   existing.author == new_book.author:
                    if new_book.origin not in existing.origins:
                        existing.origins.append(new_book.origin)
                    return
            target_group.append(new_book)

        for new_book in new_data:
            # 源码直接字符串比较（大小写敏感）
            if new_book.name == key or new_book.author == key:
                insert_with_dedup(equal_data, new_book)
            elif new_book.kind and key in new_book.kind:
                insert_with_dedup(tags_data, new_book)
            elif key in new_book.name or key in new_book.author:
                insert_with_dedup(contains_data, new_book)
            else:
                insert_with_dedup(other_data, new_book)

        for group in [equal_data, tags_data, contains_data, other_data]:
            group.sort(key=lambda x: len(x.origins), reverse=True)

        self.search_books.clear()
        self.search_books.extend(equal_data + tags_data + contains_data)
        if not precision:
            self.search_books.extend(other_data)

    async def pause(self):   self.working_state = False
    async def resume(self):  self.working_state = True
    async def cancel_search(self):
        await self.close()
        self._on_search_cancel()

    async def close(self):
        if self.search_job: self.search_job.cancel(); self.search_job = None
        if self.search_pool: self.search_pool.shutdown(wait=False); self.search_pool = None
        self.search_id = 0
```

### P5. 重构注意事项

1. **并发控制**：Legado 使用 `CoroutineScope(SupervisorJob() + ctx)` 管理协程生命周期，Python 重构可用 `asyncio.TaskGroup` + `asyncio.gather()`
2. **超时机制**：每个网络请求默认 30s 超时，分页请求单页超时不阻断整体
3. **缓存策略**：infoHtml / tocHtml 缓存当前会话有效；跨会话需要重新请求
4. **preUpdateJs 安全**：JS 执行环境必须沙箱化（Python 可用 `quickjs` 或 `pyexecjs`），禁止文件 IO 和网络访问
5. **正文分页**：Legado 的并行模式可能同时发起 10+ 并发的分页请求，重构时需限制最大并发数（推荐 ≤ 5）
6. **音频类型**：content 为空时返回 URL 而非 HTML，前端直接用于音频播放
7. **replaceRegex 性能**：正则替换列表可能很长（有的书源配置 50+ 条替换规则），应编译 pattern 后再执行替换
8. **toBook() 防丢失**：搜索结果 → Book 时，tocUrl 默认 = bookUrl，若 bookInfo 阶段有独立 tocUrl 会覆盖
9. **canRename 参数**：在 getBookInfoAwait 内部默认 canRename=true，外部调用时可控制是否覆盖已有字段
10. **checkRedirect 日志**：重定向仅记录调试日志，不影响业务流程，但过多的重定向提示可能意味着书源配置过时
