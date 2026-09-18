"""EPUB extraction and parsing engine for the Writers Reference Library."""

import os
import re
import html
import zipfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any
from urllib.parse import unquote
from PySide6.QtCore import QUrl
from PySide6.QtGui import QImage, QPixmap, QTextDocument


@dataclass
class EpubChapter:
    """Represents a chapter or reading section in an EPUB."""
    id: str
    title: str
    href: str
    anchor: str = ""
    spine_index: int = 0
    content_html: str = ""


@dataclass
class EpubBook:
    """Full representation of an EPUB book with metadata, chapters, and resources."""
    file_path: str
    title: str
    author: str
    description: str = ""
    language: str = "en"
    publisher: str = ""
    cover_image_bytes: Optional[bytes] = None
    chapters: List[EpubChapter] = field(default_factory=list)
    spine_order: List[str] = field(default_factory=list)
    manifest: Dict[str, str] = field(default_factory=dict)
    media_types: Dict[str, str] = field(default_factory=dict)
    opf_dir: str = ""
    file_size_bytes: int = 0

    @property
    def file_size_mb(self) -> float:
        return self.file_size_bytes / (1024 * 1024)

    @property
    def total_chapters(self) -> int:
        return len(self.chapters)


class EpubParser:
    """Fast, dependency-free EPUB parser using Python standard library zipfile & XML."""

    NAMESPACES = {
        'container': 'urn:oasis:names:tc:opendocument:xmlns:container',
        'opf': 'http://www.idpf.org/2007/opf',
        'dc': 'http://purl.org/dc/elements/1.1/',
        'ncx': 'http://www.daisy.org/z3986/2005/ncx/',
        'xhtml': 'http://www.w3.org/1999/xhtml',
    }

    @classmethod
    def parse_metadata_only(cls, epub_path: str) -> Optional[EpubBook]:
        """Fast metadata extraction without loading chapter text."""
        if not os.path.exists(epub_path):
            return None

        try:
            file_size = os.path.getsize(epub_path)
            with zipfile.ZipFile(epub_path, 'r') as z:
                opf_path, opf_dir = cls._locate_opf(z)
                if not opf_path:
                    return None

                opf_content = z.read(opf_path)
                tree = ET.fromstring(opf_content)

                title_elem = tree.find('.//dc:title', cls.NAMESPACES)
                raw_title = title_elem.text if title_elem is not None and title_elem.text else os.path.splitext(os.path.basename(epub_path))[0]
                clean_title = raw_title.replace("\n", " ").replace("\r", " ").strip()
                # Split at subtitle if too long
                if " / " in clean_title:
                    clean_title = clean_title.split(" / ")[0].strip()

                creator_elem = tree.find('.//dc:creator', cls.NAMESPACES)
                author = creator_elem.text.strip() if creator_elem is not None and creator_elem.text else "Public Domain Reference"

                desc_elem = tree.find('.//dc:description', cls.NAMESPACES)
                desc = desc_elem.text.strip() if desc_elem is not None and desc_elem.text else ""

                # Extract manifest & spine
                manifest = {}
                media_types = {}
                for item in tree.findall('.//opf:item', cls.NAMESPACES):
                    i_id = item.get('id')
                    i_href = item.get('href')
                    i_media = item.get('media-type', '')
                    if i_id and i_href:
                        manifest[i_id] = i_href
                        media_types[i_id] = i_media

                spine_order = []
                for itemref in tree.findall('.//opf:itemref', cls.NAMESPACES):
                    idref = itemref.get('idref')
                    if idref and idref in manifest:
                        spine_order.append(manifest[idref])

                # Check for cover image
                cover_bytes = cls._extract_cover_image(z, tree, manifest, opf_dir)

                return EpubBook(
                    file_path=epub_path,
                    title=clean_title,
                    author=author,
                    description=desc,
                    cover_image_bytes=cover_bytes,
                    spine_order=spine_order,
                    manifest=manifest,
                    media_types=media_types,
                    opf_dir=opf_dir,
                    file_size_bytes=file_size,
                )
        except Exception as e:
            print(f"Error parsing EPUB metadata for {epub_path}: {e}")
            return None

    @classmethod
    def load_full_book(cls, epub_path: str) -> Optional[EpubBook]:
        """Loads complete book including Table of Contents and chapter spine mapping."""
        book = cls.parse_metadata_only(epub_path)
        if not book:
            return None

        try:
            with zipfile.ZipFile(epub_path, 'r') as z:
                # 1. Look for NCX or nav TOC
                chapters = cls._extract_toc(z, book)

                # 2. If no NCX TOC was found, synthesize from spine
                if not chapters:
                    chapters = []
                    for idx, href in enumerate(book.spine_order):
                        clean_href = unquote(href)
                        title = f"Section {idx + 1}"
                        chapters.append(EpubChapter(
                            id=f"spine_{idx}",
                            title=title,
                            href=clean_href,
                            spine_index=idx
                        ))

                book.chapters = chapters
                return book
        except Exception as e:
            print(f"Error loading full EPUB {epub_path}: {e}")
            return book

    @classmethod
    def get_chapter_html(cls, book: EpubBook, chapter: EpubChapter) -> str:
        """Reads and pre-processes the HTML content for a given chapter."""
        if not os.path.exists(book.file_path):
            return "<p><i>Book file not found on disk.</i></p>"

        try:
            with zipfile.ZipFile(book.file_path, 'r') as z:
                # Resolve path within zip
                href = chapter.href.split('#')[0]
                possible_paths = [
                    href,
                    os.path.normpath(os.path.join(book.opf_dir, href)).replace("\\", "/"),
                    os.path.basename(href),
                ]
                zip_names = z.namelist()
                matched_path = None
                for p in possible_paths:
                    if p in zip_names:
                        matched_path = p
                        break

                if not matched_path:
                    # Fallback to finding by basename
                    bname = os.path.basename(href)
                    for n in zip_names:
                        if n.endswith("/" + bname) or n == bname:
                            matched_path = n
                            break

                if not matched_path:
                    return f"<p><i>Chapter content '{chapter.href}' not found in archive.</i></p>"

                raw_bytes = z.read(matched_path)
                try:
                    html_text = raw_bytes.decode('utf-8')
                except UnicodeDecodeError:
                    html_text = raw_bytes.decode('latin-1', errors='replace')

                # Clean and sanitize HTML for QTextBrowser
                cleaned = cls._sanitize_html_for_qt(html_text)
                return cleaned
        except Exception as e:
            return f"<p><i>Error loading chapter content: {e}</i></p>"

    @classmethod
    def inject_images_into_document(cls, book: EpubBook, qdoc: QTextDocument) -> None:
        """Extracts images from the EPUB archive and registers them with QTextDocument resources."""
        if not os.path.exists(book.file_path):
            return

        try:
            with zipfile.ZipFile(book.file_path, 'r') as z:
                for zname in z.namelist():
                    lower_name = zname.lower()
                    if any(lower_name.endswith(ext) for ext in ('.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg')):
                        data = z.read(zname)
                        pix = QPixmap()
                        pix.loadFromData(data)
                        if not pix.isNull():
                            # Register with various relative and absolute URL keys
                            qdoc.addResource(QTextDocument.ResourceType.ImageResource, QUrl(zname), pix)
                            bname = os.path.basename(zname)
                            qdoc.addResource(QTextDocument.ResourceType.ImageResource, QUrl(bname), pix)
                            qdoc.addResource(QTextDocument.ResourceType.ImageResource, QUrl("images/" + bname), pix)
                            qdoc.addResource(QTextDocument.ResourceType.ImageResource, QUrl("../images/" + bname), pix)
                            qdoc.addResource(QTextDocument.ResourceType.ImageResource, QUrl("./images/" + bname), pix)
        except Exception as e:
            print(f"Error injecting EPUB images into document: {e}")

    @classmethod
    def search_book(cls, book: EpubBook, query: str) -> List[Dict[str, Any]]:
        """Performs full-text search across all chapters in the book."""
        query_clean = query.strip()
        if not query_clean or not os.path.exists(book.file_path):
            return []

        results = []
        try:
            with zipfile.ZipFile(book.file_path, 'r') as z:
                seen_hrefs = set()
                for idx, ch in enumerate(book.chapters):
                    clean_href = ch.href.split('#')[0]
                    if clean_href in seen_hrefs:
                        continue
                    seen_hrefs.add(clean_href)

                    possible_paths = [
                        clean_href,
                        os.path.normpath(os.path.join(book.opf_dir, clean_href)).replace("\\", "/"),
                    ]
                    matched_path = next((p for p in possible_paths if p in z.namelist()), None)
                    if not matched_path:
                        continue

                    try:
                        raw = z.read(matched_path).decode('utf-8', errors='ignore')
                    except Exception:
                        continue

                    # Strip HTML tags for plain text searching
                    plain = re.sub(r'<[^>]+>', ' ', raw)
                    plain = html.unescape(plain)
                    plain_clean = re.sub(r'\s+', ' ', plain)

                    matches = [m.start() for m in re.finditer(re.escape(query_clean), plain_clean, re.IGNORECASE)]
                    if matches:
                        # Extract first snippet
                        start = max(0, matches[0] - 60)
                        end = min(len(plain_clean), matches[0] + len(query_clean) + 80)
                        snippet = ("…" if start > 0 else "") + plain_clean[start:end].strip() + ("…" if end < len(plain_clean) else "")
                        results.append({
                            "chapter_index": idx,
                            "chapter_title": ch.title,
                            "count": len(matches),
                            "snippet": snippet,
                            "chapter": ch,
                        })
        except Exception as e:
            print(f"Error searching EPUB {book.title}: {e}")

        return results

    # --- Internal Helpers ---

    @classmethod
    def _locate_opf(cls, z: zipfile.ZipFile) -> Tuple[str, str]:
        if 'META-INF/container.xml' in z.namelist():
            c_xml = z.read('META-INF/container.xml')
            ct = ET.fromstring(c_xml)
            rf = ct.find('.//{urn:oasis:names:tc:opendocument:xmlns:container}rootfile')
            if rf is not None and rf.get('full-path'):
                opf_path = rf.get('full-path')
                return opf_path, os.path.dirname(opf_path)

        # Fallback: scan for any .opf
        for name in z.namelist():
            if name.endswith('.opf'):
                return name, os.path.dirname(name)

        return "", ""

    @classmethod
    def _extract_cover_image(
        cls, z: zipfile.ZipFile, tree: ET.Element, manifest: Dict[str, str], opf_dir: str
    ) -> Optional[bytes]:
        # 1. Look for meta cover item
        meta_cover = tree.find(".//opf:meta[@name='cover']", cls.NAMESPACES)
        cover_id = meta_cover.get('content') if meta_cover is not None else None
        cover_href = manifest.get(cover_id) if cover_id else None

        if not cover_href:
            # Look for item with id containing cover or properties="cover-image"
            for item in tree.findall('.//opf:item', cls.NAMESPACES):
                props = item.get('properties', '')
                i_id = item.get('id', '').lower()
                if 'cover-image' in props or 'cover' in i_id:
                    cover_href = item.get('href')
                    break

        if cover_href:
            possible_paths = [
                cover_href,
                os.path.normpath(os.path.join(opf_dir, cover_href)).replace("\\", "/"),
            ]
            for p in possible_paths:
                if p in z.namelist():
                    return z.read(p)

        return None

    @classmethod
    def _extract_toc(cls, z: zipfile.ZipFile, book: EpubBook) -> List[EpubChapter]:
        chapters = []
        ncx_files = [n for n in z.namelist() if n.endswith('.ncx')]
        if ncx_files:
            try:
                ncx_xml = z.read(ncx_files[0])
                tree = ET.fromstring(ncx_xml)
                nav_map = tree.find('.//ncx:navMap', cls.NAMESPACES)
                if nav_map is not None:
                    cls._parse_nav_points(nav_map, chapters)
            except Exception as e:
                print(f"Error reading NCX TOC: {e}")

        return chapters

    @classmethod
    def _parse_nav_points(cls, parent: ET.Element, chapters: List[EpubChapter], depth: int = 0) -> None:
        for nav in parent.findall('ncx:navPoint', cls.NAMESPACES):
            c_id = nav.get('id', f"nav_{len(chapters)}")
            text_elem = nav.find('.//ncx:text', cls.NAMESPACES)
            title = text_elem.text.strip() if text_elem is not None and text_elem.text else f"Chapter {len(chapters) + 1}"
            content_elem = nav.find('ncx:content', cls.NAMESPACES)
            src = content_elem.get('src', '') if content_elem is not None else ''

            clean_src = unquote(src)
            anchor = clean_src.split('#')[1] if '#' in clean_src else ""
            href = clean_src.split('#')[0]

            # Indent nested sections slightly in table of contents
            display_title = ("  " * depth + title) if depth > 0 else title

            chapters.append(EpubChapter(
                id=c_id,
                title=display_title,
                href=href,
                anchor=anchor,
                spine_index=len(chapters),
            ))

            # Recurse into nested sub-sections
            cls._parse_nav_points(nav, chapters, depth + 1)

    @classmethod
    def _sanitize_html_for_qt(cls, raw_html: str) -> str:
        """Strips scripts, xml headers, and cleans body content for high-fidelity Qt rendering."""
        # Strip XML declaration & doctype
        s = re.sub(r'<\?xml[^>]*\?>', '', raw_html, flags=re.IGNORECASE)
        s = re.sub(r'<!DOCTYPE[^>]*>', '', s, flags=re.IGNORECASE)

        # Remove javascript script tags
        s = re.sub(r'<script[^>]*>.*?</script>', '', s, flags=re.IGNORECASE | re.DOTALL)

        # Ensure image tags don't have broken zero sizing
        s = re.sub(r'style="[^"]*display:\s*none[^"]*"', '', s, flags=re.IGNORECASE)

        # Enhance styling for rich literary presentation
        style_block = """
        <style>
            body {
                font-family: 'Georgia', 'Garamond', serif;
                font-size: 15px;
                line-height: 1.65;
                margin: 20px 28px;
            }
            h1, h2, h3, h4, h5, h6 {
                font-family: 'Segoe UI', 'Helvetica Neue', sans-serif;
                margin-top: 1.2em;
                margin-bottom: 0.5em;
                line-height: 1.3;
            }
            p {
                margin-bottom: 0.9em;
                text-indent: 1.5em;
            }
            p.no-indent, h1 + p, h2 + p, h3 + p {
                text-indent: 0;
            }
            blockquote {
                margin: 1.2em 2em;
                font-style: italic;
                color: #555;
            }
            img {
                max-width: 90%;
                height: auto;
                margin: 12px auto;
                display: block;
            }
            table {
                border-collapse: collapse;
                width: 100%;
                margin: 14px 0;
            }
            td, th {
                border: 1px solid #ccc;
                padding: 6px 10px;
            }
        </style>
        """

        if "<head>" in s:
            s = s.replace("<head>", f"<head>{style_block}", 1)
        elif "<html>" in s:
            s = s.replace("<html>", f"<html><head>{style_block}</head>", 1)
        else:
            s = f"<html><head>{style_block}</head><body>{s}</body></html>"

        return s
