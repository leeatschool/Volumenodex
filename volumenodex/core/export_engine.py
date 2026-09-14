"""Multi-format Document Export Engine for Volumenodex.

Supports:
- EPUB 3 E-Books (with navigation, chapters, and CSS typography)
- High-resolution Page Images (PNG and JPEG with paper drop shadows)
- Markdown (.md)
- Clean HTML5 (.html)
- UTF-8 Plain Text (.txt)
"""

import os
import zipfile
import html
import uuid
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

from PySide6.QtCore import Qt, QRectF, QSizeF, QMarginsF
from PySide6.QtGui import (
    QTextDocument, QTextBlock, QTextCharFormat, QFont,
    QImage, QPainter, QColor, QPageSize, QPageLayout
)
from PySide6.QtPrintSupport import QPrinter

from volumenodex.core.document_model import PageLayoutModel, PaperSizePreset, Orientation


class ExportEngine:
    """Handles publishing and multi-format document conversions."""

    @staticmethod
    def export_plain_text(file_path: str, qdoc: QTextDocument) -> bool:
        """Exports manuscript to clean UTF-8 plain text."""
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(qdoc.toPlainText())
            return True
        except Exception as e:
            print(f"Error exporting plain text: {e}")
            return False

    @staticmethod
    def export_markdown(file_path: str, qdoc: QTextDocument) -> bool:
        """Converts QTextDocument blocks into standard GitHub Flavored Markdown."""
        try:
            lines: List[str] = []
            block = qdoc.firstBlock()

            while block.isValid():
                text = block.text()
                # Check for headings
                user_prop = block.blockFormat().property(0x100000) or ""  # UserProperty
                text_indent = block.blockFormat().indent()

                prefix = ""
                if user_prop == "title":
                    prefix = "# "
                elif user_prop == "h1":
                    prefix = "## "
                elif user_prop == "h2":
                    prefix = "### "
                elif user_prop == "h3":
                    prefix = "#### "
                elif user_prop == "h4":
                    prefix = "##### "
                elif user_prop == "h5":
                    prefix = "###### "
                elif user_prop == "quote":
                    prefix = "> "
                elif text_indent > 0:
                    prefix = "    " * text_indent

                # Format inline runs (bold, italic, strike)
                it = block.begin()
                md_line_parts = []
                while not it.atEnd():
                    frag = it.fragment()
                    if frag.isValid():
                        frag_text = frag.text()
                        cf = frag.charFormat()
                        is_bold = cf.fontWeight() >= 700
                        is_italic = cf.fontItalic()
                        is_strike = cf.fontStrikeOut()

                        styled = frag_text
                        if is_strike:
                            styled = f"~~{styled}~~"
                        if is_bold and is_italic:
                            styled = f"***{styled}***"
                        elif is_bold:
                            styled = f"**{styled}**"
                        elif is_italic:
                            styled = f"*{styled}*"
                        md_line_parts.append(styled)
                    it += 1

                line_content = "".join(md_line_parts) if md_line_parts else text
                if prefix:
                    lines.append(f"{prefix}{line_content}\n")
                else:
                    lines.append(f"{line_content}\n")

                block = block.next()

            with open(file_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            return True
        except Exception as e:
            print(f"Error exporting markdown: {e}")
            return False

    @staticmethod
    def export_html(file_path: str, qdoc: QTextDocument, title: str = "Manuscript") -> bool:
        """Exports self-contained HTML5 with elegant book styling."""
        try:
            body_html = qdoc.toHtml()
            # Wrap in elegant book typography wrapper
            full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(title)}</title>
    <style>
        body {{
            font-family: 'Georgia', 'Cambria', serif;
            line-height: 1.65;
            color: #1a1a1a;
            background-color: #fcfbf9;
            max-width: 780px;
            margin: 48px auto;
            padding: 0 32px;
        }}
        h1, h2, h3, h4, h5 {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, serif;
            color: #111827;
            margin-top: 1.5em;
            margin-bottom: 0.5em;
        }}
        blockquote {{
            margin: 1.5em 0;
            padding-left: 1.2em;
            border-left: 3px solid #7aa2f7;
            color: #4b5563;
            font-style: italic;
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 24px 0;
        }}
        table, th, td {{
            border: 1px solid #d1d5db;
            padding: 8px 12px;
        }}
        th {{
            background-color: #f3f4f6;
            font-weight: 600;
        }}
    </style>
</head>
<body>
{body_html}
</body>
</html>"""
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(full_html)
            return True
        except Exception as e:
            print(f"Error exporting HTML: {e}")
            return False

    @staticmethod
    def export_epub(
        file_path: str,
        qdoc: QTextDocument,
        title: str = "Manuscript",
        author: str = "Author",
    ) -> bool:
        """Packages manuscript into a compliant, valid EPUB 3 digital e-book."""
        try:
            book_id = str(uuid.uuid4())
            now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

            # Parse manuscript chapters based on headings or title
            chapters: List[Dict[str, str]] = []
            curr_title = "Chapter 1"
            curr_paras: List[str] = []

            block = qdoc.firstBlock()
            while block.isValid():
                text = block.text().strip()
                user_prop = block.blockFormat().property(0x100000) or ""

                if user_prop in ("title", "h1", "h2") and text:
                    if curr_paras:
                        chapters.append({
                            "title": curr_title,
                            "content": "\n".join(curr_paras)
                        })
                        curr_paras = []
                    curr_title = text
                    curr_paras.append(f"<h2>{html.escape(text)}</h2>")
                elif text:
                    curr_paras.append(f"<p>{html.escape(text)}</p>")
                block = block.next()

            if curr_paras or not chapters:
                chapters.append({
                    "title": curr_title,
                    "content": "\n".join(curr_paras) if curr_paras else "<p>...</p>"
                })

            # Create EPUB ZIP Archive
            with zipfile.ZipFile(file_path, "w", zipfile.ZIP_DEFLATED) as zf:
                # 1. mimetype (Must be first, uncompressed)
                zf.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)

                # 2. META-INF/container.xml
                container_xml = """<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
    <rootfiles>
        <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
    </rootfiles>
</container>"""
                zf.writestr("META-INF/container.xml", container_xml)

                # 3. CSS Stylesheet
                css_content = """body {
    font-family: Georgia, serif;
    line-height: 1.5;
    margin: 5%;
    text-align: justify;
}
h1, h2, h3 {
    text-align: center;
    font-family: sans-serif;
}
p {
    text-indent: 1.25em;
    margin-top: 0;
    margin-bottom: 0;
}
"""
                zf.writestr("OEBPS/styles.css", css_content)

                # 4. Chapter XHTML files
                manifest_items = [
                    '<item id="css" href="styles.css" media-type="text/css"/>',
                    '<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>',
                    '<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>'
                ]
                spine_items = []

                nav_points = []
                nav_lis = []

                for idx, ch in enumerate(chapters, start=1):
                    ch_id = f"ch_{idx}"
                    ch_fname = f"chapter_{idx}.xhtml"
                    manifest_items.append(f'<item id="{ch_id}" href="{ch_fname}" media-type="application/xhtml+xml"/>')
                    spine_items.append(f'<itemref idref="{ch_id}"/>')

                    ch_html = f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="en">
<head>
    <title>{html.escape(ch["title"])}</title>
    <link rel="stylesheet" type="text/css" href="styles.css"/>
</head>
<body>
{ch["content"]}
</body>
</html>"""
                    zf.writestr(f"OEBPS/{ch_fname}", ch_html)

                    nav_points.append(f"""    <navPoint id="np_{idx}" playOrder="{idx}">
        <navLabel><text>{html.escape(ch["title"])}</text></navLabel>
        <content src="{ch_fname}"/>
    </navPoint>""")
                    nav_lis.append(f'<li><a href="{ch_fname}">{html.escape(ch["title"])}</a></li>')

                # 5. OEBPS/nav.xhtml (EPUB 3 Navigation)
                nav_xhtml = f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="en">
<head>
    <title>Table of Contents</title>
    <link rel="stylesheet" type="text/css" href="styles.css"/>
</head>
<body>
    <nav epub:type="toc" id="toc">
        <h1>Table of Contents</h1>
        <ol>
            {"".join(nav_lis)}
        </ol>
    </nav>
</body>
</html>"""
                zf.writestr("OEBPS/nav.xhtml", nav_xhtml)

                # 6. OEBPS/toc.ncx (EPUB 2 compatibility)
                ncx_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
    <head>
        <meta name="dtb:uid" content="{book_id}"/>
        <meta name="dtb:depth" content="1"/>
        <meta name="dtb:totalPageCount" content="0"/>
        <meta name="dtb:maxPageNumber" content="0"/>
    </head>
    <docTitle><text>{html.escape(title)}</text></docTitle>
    <docAuthor><text>{html.escape(author)}</text></docAuthor>
    <navMap>
{"".join(nav_points)}
    </navMap>
</ncx>"""
                zf.writestr("OEBPS/toc.ncx", ncx_xml)

                # 7. OEBPS/content.opf
                opf_content = f"""<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" unique-identifier="BookId" version="3.0">
    <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
        <dc:identifier id="BookId">urn:uuid:{book_id}</dc:identifier>
        <dc:title>{html.escape(title)}</dc:title>
        <dc:creator>{html.escape(author)}</dc:creator>
        <dc:language>en</dc:language>
        <meta property="dcterms:modified">{now_iso}</meta>
    </metadata>
    <manifest>
        {"".join(manifest_items)}
    </manifest>
    <spine toc="ncx">
        {"".join(spine_items)}
    </spine>
</package>"""
                zf.writestr("OEBPS/content.opf", opf_content)

            return True
        except Exception as e:
            print(f"Error exporting EPUB: {e}")
            return False

    @staticmethod
    def export_page_image(
        file_path: str,
        qdoc: QTextDocument,
        layout_model: PageLayoutModel,
        page_index: int = 0,
        dpi_scale: float = 2.0,
        image_format: str = "PNG",
    ) -> bool:
        """Renders an individual document page into a high-resolution PNG or JPEG image."""
        painter = None
        try:
            pw = int(layout_model.page_width_px_base * dpi_scale)
            ph = int(layout_model.page_height_px_base * dpi_scale)

            img = QImage(pw, ph, QImage.Format.Format_ARGB32)
            img.fill(QColor("#ffffff"))

            painter = QPainter(img)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

            # Sliced page rendering
            ph_print = layout_model.printable_height_px_base * dpi_scale
            pw_print = layout_model.printable_width_px_base * dpi_scale
            mx = layout_model.margins.left * 96.0 * dpi_scale
            my = layout_model.margins.top * 96.0 * dpi_scale

            painter.save()
            painter.translate(mx, my - page_index * ph_print)
            from PySide6.QtGui import QAbstractTextDocumentLayout
            ctx = QAbstractTextDocumentLayout.PaintContext()
            ctx.clip = QRectF(0, page_index * ph_print, pw_print, ph_print)

            # Temporarily set doc page size
            old_size = qdoc.pageSize()
            qdoc.setPageSize(QSizeF(pw_print, ph_print))
            qdoc.documentLayout().draw(painter, ctx)
            qdoc.setPageSize(old_size)
            painter.restore()

            painter.end()
            del painter
            painter = None

            ext = os.path.splitext(file_path)[1].lower()
            fmt = "PNG" if ext == ".png" else "JPEG"
            return img.save(file_path, fmt, 95)
        except Exception as e:
            print(f"Error exporting page image: {e}")
            return False
        finally:
            if painter is not None and painter.isActive():
                painter.end()
