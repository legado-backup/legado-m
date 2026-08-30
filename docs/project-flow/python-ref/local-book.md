# 本地书籍解析 — Python 重构参考

> 迁移自 [modules/local-book.md](../modules/local-book.md) 原「Python 重构参考」章节（2026-08-30 拆分）。本文件为本地书籍 Python 重构实现的唯一权威源：P1 TXT 解析器、P2 EPUB 解析器、P3 PDF 解析器、P4 MOBI 解析器、P5 本地书籍路由。
> Android 侧实现见 [modules/local-book.md](../modules/local-book.md)。
> 小节编号（P1-P5）保留自原文件，便于溯源。

### P1. TXT 文件解析器

```python
import re
from typing import Optional, List


class BookChapter:
    """章节数据类"""
    def __init__(self, title="", start=0, end=0, url="",
                 is_volume=False, word_count=None):
        self.url = url
        self.title = title
        self.start = start
        self.end = end
        self.is_volume = is_volume
        self.word_count = word_count
        self.start_fragment_id = None
        self.end_fragment_id = None
        self.index = 0
        self.book_url = ""


class TxtFileParser:
    """TXT 文件解析器"""

    # 常量
    BUFFER_SIZE = 512000  # 首检/分块缓冲区
    MAX_LENGTH_NO_TOC = 10 * 1024  # 无规则分章大小
    MAX_LENGTH_WITH_TOC = 102400   # 有规则单章上限
    TXT_BUFFER_SIZE = 8 * 1024 * 1024  # 内容读取缓冲区
    OVER_RULE_COUNT = 2  # 规则选择阈值

    def __init__(self, book_path: str, charset: str = None):
        self.book_path = book_path
        self.charset = charset
        self.txt_buffer = None
        self.buffer_start = -1
        self.buffer_end = -1

    # =============================================
    # P1.1 编码检测
    # =============================================
    def detect_encoding(self, first_chunk: bytes) -> str:
        """四级降级编码检测"""
        # 1. BOM 检测
        if first_chunk.startswith(b'\xef\xbb\xbf'):
            return 'utf-8-sig'
        if first_chunk.startswith(b'\xff\xfe'):
            return 'utf-16-le'
        if first_chunk.startswith(b'\xfe\xff'):
            return 'utf-16-be'

        # 2. 参数指定编码（由调用者传入）
        if self.charset:
            try:
                first_chunk.decode(self.charset)
                return self.charset
            except UnicodeDecodeError:
                pass

        # 3. chardet 自动检测
        import chardet
        result = chardet.detect(first_chunk)
        if result and result['encoding'] and result['confidence'] > 0.5:
            return result['encoding']

        # 4. 默认 UTF-8
        return 'utf-8'

    # =============================================
    # P1.2 获取目录规则
    # =============================================
    def get_toc_rule(self, content: str, rules: list) -> dict:
        """
        从多个目录规则中选择最佳匹配

        rules: [{"name": ..., "rule": ..., "replacement": ...}, ...]
        returns: {"rule": ..., "replacement": ...} or None
        """
        best_rule = None
        max_count = -1

        for rule in rules:
            try:
                pattern = re.compile(rule['rule'], re.MULTILINE)
            except re.error:
                continue

            cs_num = 0  # 有效匹配数
            num_e = 0   # 误匹配数（相邻章节字数 < 100）
            start = 0

            for m in pattern.finditer(content):
                content_len = m.start() - start
                if start == 0 or content_len > 1000:
                    title = self.replace_title(m.group(), rule.get('replacement'))
                    if title:
                        cs_num += 1
                    start = m.end()
                elif content_len < 100:
                    num_e += 1

            if cs_num >= num_e * 3 and (cs_num > max_count + self.OVER_RULE_COUNT):
                max_count = cs_num
                best_rule = rule
                if max_count > 70:
                    break  # 够精确，提前终止

        return best_rule

    # =============================================
    # P1.3 章节解析（有规则）
    # =============================================
    def analyze_with_rule(self, rule_regex: str, js_replacement: str = None):
        """使用正则规则解析章节目录"""
        pattern = re.compile(rule_regex, re.MULTILINE)
        toc = []
        book_word_count = 0

        with open(self.book_path, 'rb') as f:
            # BOM 跳过
            cur_offset = 0
            header = f.read(3)
            if header.startswith(b'\xef\xbb\xbf'):
                cur_offset = 3
            else:
                f.seek(0)

            buffer_start = 3 if cur_offset == 3 else 0
            remaining = b''
            last_chapter_word_count = 0
            last_volume_title = ""

            while True:
                chunk = f.read(self.BUFFER_SIZE - buffer_start)
                if not chunk:
                    break

                block_data = remaining + chunk
                length = len(block_data)

                # 调整到最后一个完整行
                if length == self.BUFFER_SIZE:
                    for i in range(length - 1, -1, -1):
                        if block_data[i] == 0x0a:
                            end = i
                            break
                    else:
                        end = length
                else:
                    end = length

                block_content = block_data[:end].decode(self.charset or 'utf-8', errors='replace')
                remaining = block_data[end:]
                buffer_start = length - end

                seek_pos = 0
                for m in pattern.finditer(block_content):
                    chapter_start = m.start()
                    chapter_content = block_content[seek_pos:chapter_start]
                    chapter_content_len = len(chapter_content)
                    chapter_bytes = chapter_content.encode(self.charset or 'utf-8')
                    chapter_length = len(chapter_bytes)
                    title_bytes = m.group().encode(self.charset or 'utf-8')
                    title_length = len(title_bytes)

                    if seek_pos == 0 and chapter_start != 0:
                        if not toc:
                            # 序章/前言
                            title = self.replace_title("前言", js_replacement)
                            if title:
                                toc.append(BookChapter(
                                    title=title,
                                    start=cur_offset,
                                    end=cur_offset + chapter_length
                                ))
                            # 简介取前600字
                            book_intro = chapter_content[:600]

                        title = self.replace_title(m.group(), js_replacement)
                        if not title:
                            continue
                        toc.append(BookChapter(
                            title=title,
                            start=cur_offset + chapter_length + title_length,
                            end=cur_offset + chapter_length + title_length
                        ))
                    else:
                        # 处理上一章
                        if toc:
                            last_ch = toc[-1]
                            if not chapter_content.strip():
                                last_ch.is_volume = True
                                last_volume_title = last_ch.title
                            else:
                                last_ch.is_volume = False
                            last_ch.end = last_ch.start + chapter_length
                            last_ch.word_count = chapter_content_len

                        title = self.replace_title(m.group(), js_replacement)
                        if not title:
                            continue
                        toc.append(BookChapter(
                            title=title,
                            start=(toc[-1].end + title_length) if toc else (cur_offset + title_length),
                            end=(toc[-1].end + title_length) if toc else (cur_offset + title_length)
                        ))

                    book_word_count += chapter_content_len
                    seek_pos += chapter_content_len + len(m.group())

                # block 末尾剩余
                word_count = len(block_content) - seek_pos
                book_word_count += word_count
                last_chapter_word_count += word_count
                cur_offset += length

                if toc:
                    toc[-1].end = cur_offset
                    toc[-1].word_count = last_chapter_word_count

            return toc, book_word_count

    # =============================================
    # P1.4 章节解析（无规则）
    # =============================================
    def analyze_no_rule(self, file_start: int = 0, file_end: int = None):
        """无目录规则时按固定大小切分"""
        toc = []
        book_word_count = 0

        with open(self.book_path, 'rb') as f:
            if file_start == 0:
                header = f.read(3)
                if not header.startswith(b'\xef\xbb\xbf'):
                    f.seek(0)
                    cur_offset = 0
                else:
                    cur_offset = 3
            else:
                f.seek(file_start)
                cur_offset = file_start

            block_pos = 0
            last_chapter_word_count = 0
            remaining = b''
            buffer_start = 0

            while True:
                max_read = min(self.BUFFER_SIZE - buffer_start,
                              file_end - cur_offset - buffer_start) if file_end else self.BUFFER_SIZE - buffer_start
                if max_read <= 0:
                    break

                chunk = f.read(int(max_read))
                if not chunk:
                    break

                block_pos += 1
                data = remaining + chunk
                length = len(data)

                chapter_offset = 0
                chapter_pos = 0
                str_remaining = length

                while str_remaining > 0:
                    chapter_pos += 1
                    if str_remaining > self.MAX_LENGTH_NO_TOC:
                        end = length
                        for i in range(chapter_offset + self.MAX_LENGTH_NO_TOC, length):
                            if data[i] == 0x0a:  # 换行符
                                end = i
                                break

                        content = data[chapter_offset:end].decode(self.charset or 'utf-8', errors='replace')
                        book_word_count += len(content)

                        toc.append(BookChapter(
                            title=f"第{block_pos}章({chapter_pos})",
                            start=toc[-1].end if toc else cur_offset,
                            end=(toc[-1].end if toc else cur_offset) + (end - chapter_offset)
                        ))

                        str_remaining -= (end - chapter_offset)
                        chapter_offset = end
                    else:
                        remaining = data[length - str_remaining:length]
                        length -= str_remaining
                        buffer_start = str_remaining
                        str_remaining = 0

                cur_offset += length

            # 处理剩余内容
            if remaining:
                content = remaining.decode(self.charset or 'utf-8', errors='replace')
                book_word_count += len(content)
                if len(remaining) > 100 or not toc:
                    toc.append(BookChapter(
                        title=f"第{block_pos}章({chapter_pos})",
                        start=toc[-1].end if toc else cur_offset,
                        end=(toc[-1].end if toc else cur_offset) + len(remaining)
                    ))
                elif toc:
                    toc[-1].end += len(remaining)
                    toc[-1].word_count = last_chapter_word_count + len(content)

        return toc, book_word_count

    # =============================================
    # P1.5 获取章节内容
    # =============================================
    def get_content(self, chapter: BookChapter) -> str:
        """根据字节偏移读取章节正文"""
        start = chapter.start
        end = chapter.end

        if self.txt_buffer is None or start > self.buffer_end or end < self.buffer_start:
            # 重新加载缓冲区
            buffer_size = 8 * 1024 * 1024
            self.buffer_start = buffer_size * (start // buffer_size)
            with open(self.book_path, 'rb') as f:
                f.seek(self.buffer_start)
                self.txt_buffer = f.read(buffer_size)
            self.buffer_end = self.buffer_start + len(self.txt_buffer)

        count = end - start
        if start < self.buffer_end and end > self.buffer_end:
            # 跨缓冲区边界
            with open(self.book_path, 'rb') as f:
                f.seek(start)
                buffer = f.read(count)
        else:
            # 在缓冲区内
            offset_in_buffer = int(start - self.buffer_start)
            buffer = self.txt_buffer[offset_in_buffer:offset_in_buffer + count]

        text = buffer.decode(self.charset or 'utf-8', errors='replace')
        # 去除前导空白，替换为全角空格缩进
        text = re.sub(r'^[\n\s]+', '　　', text)
        return text

    # =============================================
    # P1.6 标题净化
    # =============================================
    def replace_title(self, matched: str, js_code: str = None, **context) -> str:
        """
        对匹配到的标题进行 JS 净化
        若 js_code 为空，直接返回原始匹配
        """
        if not js_code:
            return matched

        # 使用 Python 内置 exec 模拟 JS 引擎执行
        # 实际重构中可使用 PyMiniRacer 或类似沙箱
        local_vars = {
            'result': matched,
            'index': context.get('index', 0),
            'prevTitle': context.get('prev_title'),
            'prevLength': context.get('prev_length', -1),
            'lastVolumeTitle': context.get('last_volume_title', ''),
        }

        try:
            exec(js_code, {}, local_vars)
            return str(local_vars.get('result', matched))
        except Exception:
            return matched
```

### P2. EPUB 文件解析器

```python
import re
import zipfile
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from urllib.parse import urljoin


class EpubFileParser:
    """EPUB 文件解析器"""

    NSMAP = {
        'container': 'urn:oasis:names:tc:opendocument:xmlns:container',
        'opf': 'http://www.idpf.org/2007/opf',
        'dc': 'http://purl.org/dc/elements/1.1/',
        'ncx': 'http://www.dtd.org/NISO/2005/ncx',
    }

    def __init__(self, epub_path: str):
        self.epub_path = epub_path
        self.zip_file = None
        self.opf_path = None
        self.opf_xml = None
        self.manifest = {}  # {id: {href, media_type}}
        self.spine = []     # [idref, ...]
        self.ncx_path = None
        self.ncx_tree = None

    # =============================================
    # P2.1 解析 container.xml 获取 OPF 路径
    # =============================================
    def parse_container(self):
        """从 META-INF/container.xml 获取 OPF 路径"""
        with zipfile.ZipFile(self.epub_path, 'r') as zf:
            container_xml = zf.read('META-INF/container.xml')

        root = ET.fromstring(container_xml)
        rootfile = root.find('.//container:rootfile', self.NSMAP)
        self.opf_path = rootfile.get('full-path')

    # =============================================
    # P2.2 解析 OPF 文件
    # =============================================
    def parse_opf(self):
        """解析 content.opf 获取元数据、manifest、spine"""
        with zipfile.ZipFile(self.epub_path, 'r') as zf:
            opf_content = zf.read(self.opf_path)

        root = ET.fromstring(opf_content)

        # metadata
        metadata = root.find('opf:metadata', self.NSMAP)
        self.title = self._get_dc_text(metadata, 'title')
        self.creator = self._get_dc_text(metadata, 'creator')
        self.language = self._get_dc_text(metadata, 'language')
        desc_elem = metadata.find('dc:description', self.NSMAP)
        self.description = desc_elem.text if desc_elem is not None else None

        # manifest
        manifest = root.find('opf:manifest', self.NSMAP)
        for item in manifest.findall('opf:item', self.NSMAP):
            item_id = item.get('id')
            href = item.get('href')
            media_type = item.get('media-type')
            self.manifest[item_id] = {
                'href': urljoin(self.opf_path, href),
                'media_type': media_type
            }
            if media_type == 'application/x-dtbncx+xml':
                self.ncx_path = self.manifest[item_id]['href']

        # spine
        spine = root.find('opf:spine', self.NSMAP)
        self.spine_toc = spine.get('toc')
        for itemref in spine.findall('opf:itemref', self.NSMAP):
            idref = itemref.get('idref')
            linear = itemref.get('linear', 'yes')
            self.spine.append({
                'idref': idref,
                'linear': linear == 'yes'
            })

    def _get_dc_text(self, parent, tag):
        elem = parent.find(f'dc:{tag}', self.NSMAP)
        return elem.text if elem is not None else ''

    # =============================================
    # P2.3 解析 NCX 目录
    # =============================================
    def parse_ncx(self):
        """解析 toc.ncx 获取层级目录"""
        if not self.ncx_path:
            return None

        with zipfile.ZipFile(self.epub_path, 'r') as zf:
            ncx_content = zf.read(self.ncx_path)

        soup = BeautifulSoup(ncx_content, 'xml')

        def parse_nav_point(nav_point):
            label = nav_point.find('text')
            content = nav_point.find('content')
            result = {
                'label': label.text if label else '',
                'src': content.get('src') if content else '',
                'children': []
            }
            for child in nav_point.find_all('navPoint', recursive=False):
                result['children'].append(parse_nav_point(child))
            return result

        nav_map = soup.find('navMap')
        toc = []
        if nav_map:
            for nav_point in nav_map.find_all('navPoint', recursive=False):
                toc.append(parse_nav_point(nav_point))

        return toc

    # =============================================
    # P2.4 生成章节列表
    # =============================================
    def get_chapter_list(self):
        """获取完整章节列表"""
        self.parse_container()
        self.parse_opf()
        ncx = self.parse_ncx()

        chapter_list = []

        if ncx:
            # 方式 A: 使用 NCX 目录
            first_ref = self._get_first_ref_from_ncx(ncx)
            self._parse_first_page(chapter_list, first_ref)
            self._parse_menu(chapter_list, ncx, level=0)
        else:
            # 方式 B: 使用 spine
            for i, sp in enumerate(self.spine):
                item = self.manifest.get(sp['idref'])
                if not item:
                    continue
                chapter = BookChapter(
                    url=item['href'],
                    title=self._extract_title_from_xhtml(item['href']),
                    index=i
                )
                if i > 0:
                    chapter_list[-1].put_variable('nextUrl', chapter.url)
                chapter_list.append(chapter)

        return chapter_list

    def _parse_first_page(self, chapter_list, first_ref_href):
        """解析第一章前的所有内容"""
        base_dir = '/'.join(self.opf_path.split('/')[:-1]) + '/'

        for sp in self.spine:
            item = self.manifest.get(sp['idref'])
            if not item:
                continue
            href = item['href']
            clean_href = href.split('#')[0]
            ref_clean = first_ref_href.split('#')[0]

            if clean_href == urljoin(base_dir, ref_clean):
                break

            title = self._extract_title_from_xhtml(href)
            chapter = BookChapter(
                url=href,
                title=title or '--卷首--'
            )
            if chapter_list:
                fragment = href.split('#')
                if len(fragment) > 1:
                    chapter.start_fragment_id = fragment[1]
                    chapter_list[-1].end_fragment_id = fragment[1]
                chapter_list[-1].put_variable('nextUrl', chapter.url)
            chapter_list.append(chapter)

    def _parse_menu(self, chapter_list, refs, level):
        """递归解析 NCX 目录"""
        for ref in refs:
            if ref.get('src'):
                chapter = BookChapter(
                    url=ref['src'],
                    title=ref['label']
                )
                fragment = ref['src'].split('#')
                if len(fragment) > 1:
                    chapter.start_fragment_id = fragment[1]
                if chapter_list:
                    chapter_list[-1].end_fragment_id = chapter.start_fragment_id
                    chapter_list[-1].put_variable('nextUrl', chapter.url)
                chapter.is_volume = bool(ref.get('children'))
                chapter_list.append(chapter)

            if ref.get('children'):
                self._parse_menu(chapter_list, ref['children'], level + 1)

    # =============================================
    # P2.5 获取章节内容
    # =============================================
    def get_content(self, chapter):
        """读取章节正文内容"""
        with zipfile.ZipFile(self.epub_path, 'r') as zf:
            next_url = chapter.get_variable('nextUrl', '')
            next_href = next_url.split('#')[0] if next_url else ''
            current_href = chapter.url.split('#')[0]

            start_fragment = chapter.start_fragment_id
            end_fragment = chapter.end_fragment_id

            elements_html = []
            found_current = False
            include_next = bool(end_fragment)

            for sp in self.spine:
                item = self.manifest.get(sp['idref'])
                if not item:
                    continue

                if not found_current:
                    if item['href'] != current_href:
                        continue
                    found_current = True

                xhtml_content = zf.read(item['href']).decode('utf-8', errors='replace')
                soup = BeautifulSoup(xhtml_content, 'html.parser')

                body = soup.find('body')
                if body:
                    if start_fragment:
                        start_elem = soup.find(id=start_fragment)
                        # 截取从 start_fragment 开始的 html
                    elements_html.append(str(body))

                if next_href and item['href'] == next_href:
                    break

        html = '\n'.join(elements_html)
        return self._format_content(html)

    def _format_content(self, html):
        """格式化正文内容"""
        soup = BeautifulSoup(html, 'html.parser')

        for tag in soup.find_all('title'):
            tag.decompose()

        for tag in soup.find_all(style=re.compile(r'display:\s*none', re.I)):
            tag.decompose()

        for img in soup.find_all('img'):
            src = img.get('src', '')
            if src:
                img['src'] = urljoin(self.opf_path, src)

        return str(soup)

    def _extract_title_from_xhtml(self, href):
        """从 XHTML 文件的 <title> 标签提取标题"""
        try:
            with zipfile.ZipFile(self.epub_path, 'r') as zf:
                content = zf.read(href).decode('utf-8', errors='replace')
            soup = BeautifulSoup(content, 'html.parser')
            title_tag = soup.find('title')
            return title_tag.text.strip() if title_tag else ''
        except Exception:
            return ''

    def _get_first_ref_from_ncx(self, ncx):
        """获取 NCX 中第一个有 src 的条目"""
        for ref in ncx:
            if ref.get('src'):
                return ref['src']
            if ref.get('children'):
                result = self._get_first_ref_from_ncx(ref['children'])
                if result:
                    return result
        return ''
```

### P3. PDF 文件解析器

```python
import math


class PdfFileParser:
    """PDF 文件解析器"""

    PAGE_SIZE = 10  # 每段页数（与 Legado 一致）

    def __init__(self, pdf_path: str):
        import fitz  # PyMuPDF
        self.doc = fitz.open(pdf_path)
        self.total_pages = len(self.doc)

    def get_chapter_list(self):
        """生成章节列表"""
        count = math.ceil(self.total_pages / self.PAGE_SIZE)
        chapters = []
        for i in range(count):
            chapters.append(BookChapter(
                title=f"分段_{i}",
                url=f"pdf_{i}",
                index=i,
                start=i * self.PAGE_SIZE,
                end=min((i + 1) * self.PAGE_SIZE, self.total_pages)
            ))
        return chapters

    def get_content(self, chapter) -> str:
        """提取章节文本（若 PDF 有文本层）"""
        text_parts = []
        start = chapter.start
        end = chapter.end

        for page_num in range(start, end):
            page = self.doc[page_num]
            text = page.get_text()
            if text.strip():
                text_parts.append(text)

        return '\n\n'.join(text_parts)

    def get_book_info(self) -> dict:
        """从 PDF 元数据获取书名"""
        metadata = self.doc.metadata
        return {
            'title': metadata.get('title', ''),
            'author': metadata.get('author', ''),
        }

    def close(self):
        self.doc.close()
```

> **注意**：若 PDF 为扫描版（纯图片无文字），需额外集成 OCR（如 PaddleOCR / Tesseract）。

### P4. MOBI 文件解析器

```python
import struct


class MobiFileParser:
    """MOBI 文件解析器"""

    def __init__(self, mobi_path: str):
        self.mobi_path = mobi_path
        self.raw = open(mobi_path, 'rb').read()
        self.records = []
        self.sections = []
        self.toc = []
        self.metadata = {}
        self._parse_pdb()
        self._parse_mobi_header()

    # =============================================
    # P4.1 PDB 头解析
    # =============================================
    def _parse_pdb(self):
        """解析 PDB 文件头"""
        data = self.raw
        self.pdb_name = data[0:32].decode('latin-1').rstrip('\x00')
        self.pdb_attrs = struct.unpack_from('>H', data, 32)[0]
        self.pdb_version = struct.unpack_from('>H', data, 34)[0]
        self.pdb_type = data[60:64].decode('ascii')
        self.pdb_creator = data[64:68].decode('ascii')
        self.num_records = struct.unpack_from('>H', data, 76)[0]

        record_list_offset = 78
        self.record_offsets = []
        for i in range(self.num_records):
            offset = struct.unpack_from('>I', data, record_list_offset + i * 8)[0]
            self.record_offsets.append(offset)

    # =============================================
    # P4.2 MOBI 头解析
    # =============================================
    def _parse_mobi_header(self):
        """解析 MOBI 头（在第一条记录中）"""
        first_rec_offset = self.record_offsets[0]
        data = self.raw[first_rec_offset:]

        self.compression = struct.unpack_from('>H', data, 0)[0]

        # MOBI header (偏移 16 字节)
        mobi_offset = 16
        self.mobi_header_len = struct.unpack_from('>I', data, mobi_offset)[0]
        self.mobi_type = struct.unpack_from('>I', data, mobi_offset + 4)[0]

        # EXTH header
        exth_offset = mobi_offset + self.mobi_header_len
        if exth_offset + 4 < len(data):
            exth_id = struct.unpack_from('>I', data, exth_offset)[0]
            if exth_id == 0x45585448:  # "EXTH"
                exth_len = struct.unpack_from('>I', data, exth_offset + 4)[0]
                self._parse_exth(data, exth_offset + 8, exth_offset + exth_len)

    def _parse_exth(self, data, start, end):
        """解析 EXTH 扩展头"""
        pos = start
        while pos + 8 <= end:
            rec_type = struct.unpack_from('>I', data, pos)[0]
            rec_len = struct.unpack_from('>I', data, pos + 4)[0]
            rec_data = data[pos + 8:pos + rec_len]

            if rec_type == 100:  # author
                self.metadata['author'] = rec_data.decode('utf-8', errors='replace').rstrip('\x00')
            elif rec_type == 105:  # cover offset
                self.metadata['cover_offset'] = struct.unpack_from('>I', rec_data, 0)[0]

            pos += rec_len

    def get_chapter_list(self):
        """获取章节列表（简化版，需解析 INDX/CTOC 索引记录）"""
        return []

    def get_content(self, chapter):
        """获取章节内容（需要解压记录）"""
        pass

    def close(self):
        if hasattr(self, 'raw'):
            del self.raw
```

> **重构建议**：Python 环境下建议直接使用 `calibre` 生态中的 `ebooklib` 或 `mobi` 库：
> ```bash
> pip install mobi  # 或使用 calibre 的 ebook-convert 命令行
> ```

### P5. 本地书籍路由

```python
import os


class LocalBookRouter:
    """本地书籍解析路由"""

    SUFFIX_MAP = {
        '.epub': EpubFileParser,
        '.pdf':  PdfFileParser,
        '.mobi': MobiFileParser,
        '.azw3': MobiFileParser,
        '.umd':  None,  # UMD 小众格式，可自行实现
        '.txt':  TxtFileParser,
    }

    @classmethod
    def get_parser(cls, book_path: str):
        _, ext = os.path.splitext(book_path.lower())
        parser_cls = cls.SUFFIX_MAP.get(ext, TxtFileParser)
        return parser_cls(book_path)

    @classmethod
    def get_chapter_list(cls, book_path: str):
        parser = cls.get_parser(book_path)
        return parser.get_chapter_list()

    @classmethod
    def get_content(cls, book_path: str, chapter):
        parser = cls.get_parser(book_path)
        return parser.get_content(chapter)
```

