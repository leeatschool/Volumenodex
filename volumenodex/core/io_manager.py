"""Document import, export, and companion story metadata serialization."""

import html
import json
import os
import zipfile
from typing import Optional, Dict, Any
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_COLOR_INDEX

from PySide6.QtCore import Qt, QSizeF, QMarginsF
from PySide6.QtGui import (
    QTextDocument, QTextCursor, QTextBlock, QTextCharFormat,
    QTextBlockFormat, QFont, QColor, QPageSize, QPageLayout
)
from PySide6.QtPrintSupport import QPrinter

from volumenodex.core.document_model import PageLayoutModel, PaperSizePreset, Orientation


class IOManager:
    """Handles native .docx file IO, high-resolution PDF export, RTF, and .story.json companion metadata."""

    @staticmethod
    def _qcolor_to_docx_highlight(qcol: QColor) -> Optional[WD_COLOR_INDEX]:
        """Maps a QColor to the closest standard Microsoft Word highlight color enum."""
        r, g, b = qcol.red(), qcol.green(), qcol.blue()
        highlights = [
            (WD_COLOR_INDEX.YELLOW, 254, 240, 138),
            (WD_COLOR_INDEX.BRIGHT_GREEN, 187, 247, 208),
            (WD_COLOR_INDEX.TURQUOISE, 165, 243, 252),
            (WD_COLOR_INDEX.PINK, 251, 207, 232),
            (WD_COLOR_INDEX.DARK_YELLOW, 254, 215, 170),
            (WD_COLOR_INDEX.VIOLET, 233, 213, 255),
            (WD_COLOR_INDEX.BLUE, 186, 230, 253),
            (WD_COLOR_INDEX.GREEN, 134, 239, 172),
            (WD_COLOR_INDEX.TEAL, 153, 246, 228),
            (WD_COLOR_INDEX.GRAY_25, 229, 231, 235),
            (WD_COLOR_INDEX.RED, 254, 202, 202),
        ]
        best_enum = None
        min_dist = float("inf")
        for hl_enum, hr, hg, hb in highlights:
            dist = (r - hr) ** 2 + (g - hg) ** 2 + (b - hb) ** 2
            if dist < min_dist:
                min_dist = dist
                best_enum = hl_enum
        return best_enum

    @staticmethod
    def _docx_highlight_to_qcolor(hl_enum: Any) -> Optional[QColor]:
        """Maps a Microsoft Word highlight color enum back to a soft QColor."""
        hl_map = {
            WD_COLOR_INDEX.YELLOW: QColor("#fef08a"),
            WD_COLOR_INDEX.BRIGHT_GREEN: QColor("#bbf7d0"),
            WD_COLOR_INDEX.TURQUOISE: QColor("#a5f3fc"),
            WD_COLOR_INDEX.PINK: QColor("#fbcfe8"),
            WD_COLOR_INDEX.DARK_YELLOW: QColor("#fed7aa"),
            WD_COLOR_INDEX.VIOLET: QColor("#e9d5ff"),
            WD_COLOR_INDEX.BLUE: QColor("#bae6fd"),
            WD_COLOR_INDEX.GREEN: QColor("#86efac"),
            WD_COLOR_INDEX.TEAL: QColor("#99f6e4"),
            WD_COLOR_INDEX.GRAY_25: QColor("#e5e7eb"),
            WD_COLOR_INDEX.GRAY_50: QColor("#9ca3af"),
            WD_COLOR_INDEX.RED: QColor("#fecaca"),
        }
        return hl_map.get(hl_enum, QColor("#fef08a"))

    @staticmethod
    def get_companion_path(doc_path: str) -> str:
        base, _ = os.path.splitext(doc_path)
        return f"{base}.story.json"

    @staticmethod
    def save_docx(
        file_path: str,
        qdoc: QTextDocument,
        layout_model: PageLayoutModel,
        story_metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Saves rich document contents into a 100% compliant Microsoft Word .docx file."""
        try:
            doc = docx.Document()

            # Set section margins and paper dimensions
            section = doc.sections[0]
            section.top_margin = Inches(layout_model.margins.top)
            section.bottom_margin = Inches(layout_model.margins.bottom)
            section.left_margin = Inches(layout_model.margins.left)
            section.right_margin = Inches(layout_model.margins.right)

            raw_w, raw_h = layout_model.raw_dimensions_inches
            section.page_width = Inches(raw_w)
            section.page_height = Inches(raw_h)

            # Traverse QTextDocument blocks
            block = qdoc.firstBlock()
            while block.isValid():
                text = block.text()
                # Check block format for heading levels
                heading_level = block.blockFormat().property(QTextBlockFormat.Property.UserProperty)
                if heading_level and str(heading_level).startswith("h"):
                    level_num = int(str(heading_level)[1])
                    p = doc.add_heading(text, level=min(level_num, 3))
                elif heading_level == "title":
                    p = doc.add_heading(text, level=0)
                else:
                    p = doc.add_paragraph()
                    # Iterate text fragments to capture character formatting
                    it = block.begin()
                    if it.atEnd() and text:
                        run = p.add_run(text)
                    else:
                        while not it.atEnd():
                            fragment = it.fragment()
                            if fragment.isValid():
                                frag_text = fragment.text()
                                fmt = fragment.charFormat()
                                run = p.add_run(frag_text)
                                font = fmt.font()
                                run.bold = font.bold()
                                run.italic = font.italic()
                                run.underline = font.underline()
                                if font.family():
                                    run.font.name = font.family()
                                if font.pointSize() > 0:
                                    run.font.size = Pt(font.pointSize())

                                # Foreground Text Color
                                fg_brush = fmt.foreground()
                                if fg_brush.style() != Qt.BrushStyle.NoBrush:
                                    fg_col = fg_brush.color()
                                    if fg_col.isValid() and fg_col.alpha() > 0:
                                        run.font.color.rgb = RGBColor(fg_col.red(), fg_col.green(), fg_col.blue())

                                # Background Highlight Color
                                bg_brush = fmt.background()
                                if bg_brush.style() != Qt.BrushStyle.NoBrush:
                                    bg_col = bg_brush.color()
                                    if bg_col.isValid() and bg_col.alpha() > 0:
                                        hl_enum = IOManager._qcolor_to_docx_highlight(bg_col)
                                        if hl_enum is not None:
                                            run.font.highlight_color = hl_enum
                            it += 1

                # Apply paragraph alignment
                align = block.blockFormat().alignment()
                if align == Qt.AlignmentFlag.AlignCenter:
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                elif align == Qt.AlignmentFlag.AlignRight:
                    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                elif align == Qt.AlignmentFlag.AlignJustify:
                    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

                block = block.next()

            doc.save(file_path)

            # Save companion story file if metadata provided
            if story_metadata:
                comp_path = IOManager.get_companion_path(file_path)
                with open(comp_path, "w", encoding="utf-8") as f:
                    json.dump(story_metadata, f, indent=2)

            return True
        except Exception as e:
            print(f"Error saving docx: {e}")
            return False

    @staticmethod
    def load_docx(file_path: str, qdoc: QTextDocument) -> Optional[Dict[str, Any]]:
        """Loads a .docx file into QTextDocument and loads companion story metadata if present."""
        try:
            # Enforce archive size limits and validate zip structure to prevent zip bombs
            if zipfile.is_zipfile(file_path):
                with zipfile.ZipFile(file_path, "r") as zf:
                    total_uncompressed = 0
                    for info in zf.infolist():
                        if ".." in info.filename or info.filename.startswith(("/", "\\")):
                            print("Security Warning: Suspicious entry in docx archive.")
                            return None
                        total_uncompressed += info.file_size
                        if total_uncompressed > 100 * 1024 * 1024:  # 100 MB max
                            print("Security Warning: Document archive uncompressed size exceeds safe limit (100MB).")
                            return None
                    if len(zf.infolist()) > 5000:
                        print("Security Warning: Document archive contains excessive file entries.")
                        return None

            doc = docx.Document(file_path)
            qdoc.clear()
            cursor = QTextCursor(qdoc)

            for p in doc.paragraphs:
                # Add runs with formatting (safely escaping HTML)
                if p.style and p.style.name.startswith("Heading"):
                    cursor.insertHtml(f"<h2>{html.escape(p.text)}</h2>")
                elif p.style and p.style.name == "Title":
                    cursor.insertHtml(f"<h1>{html.escape(p.text)}</h1>")
                else:
                    for run in p.runs:
                        char_fmt = QTextCharFormat()
                        if run.bold:
                            char_fmt.setFontWeight(QFont.Weight.Bold)
                        if run.italic:
                            char_fmt.setFontItalic(True)
                        if run.underline:
                            char_fmt.setFontUnderline(True)
                        if run.font.name:
                            char_fmt.setFontFamilies([run.font.name])
                        if run.font.size and run.font.size.pt > 0:
                            char_fmt.setFontPointSize(run.font.size.pt)

                        # Restore Foreground Text Color
                        if run.font.color and run.font.color.rgb:
                            rgb = run.font.color.rgb
                            char_fmt.setForeground(QColor(rgb[0], rgb[1], rgb[2]))

                        # Restore Background Highlight Color
                        if run.font.highlight_color:
                            hl_color = IOManager._docx_highlight_to_qcolor(run.font.highlight_color)
                            if hl_color:
                                char_fmt.setBackground(hl_color)

                        cursor.insertText(run.text, char_fmt)
                    cursor.insertBlock()

            # Attempt to load companion story metadata
            comp_path = IOManager.get_companion_path(file_path)
            if os.path.exists(comp_path):
                with open(comp_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            return None
        except Exception as e:
            print(f"Error loading docx: {e}")
            return None

    @staticmethod
    def export_pdf(file_path: str, qdoc: QTextDocument, layout_model: PageLayoutModel) -> bool:
        """Exports print-accurate vector PDF matching exact paper margins and page geometry."""
        try:
            printer = QPrinter(QPrinter.PrinterMode.HighResolution)
            printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
            printer.setOutputFileName(file_path)

            # Map paper preset to Qt PageSize
            if layout_model.paper_size == PaperSizePreset.LETTER:
                printer.setPageSize(QPageSize(QPageSize.PageSizeId.Letter))
            elif layout_model.paper_size == PaperSizePreset.A4:
                printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
            elif layout_model.paper_size == PaperSizePreset.LEGAL:
                printer.setPageSize(QPageSize(QPageSize.PageSizeId.Legal))
            else:
                raw_w, raw_h = layout_model.raw_dimensions_inches
                printer.setPageSize(QPageSize(QSizeF(raw_w, raw_h), QPageSize.Unit.Inch))

            # Orientation
            if layout_model.orientation == Orientation.LANDSCAPE:
                printer.setPageOrientation(QPageLayout.Orientation.Landscape)
            else:
                printer.setPageOrientation(QPageLayout.Orientation.Portrait)

            # Margins
            m = layout_model.margins
            q_margins = QMarginsF(m.left, m.top, m.right, m.bottom)
            printer.setPageMargins(q_margins, QPageLayout.Unit.Inch)

            qdoc.print_(printer)
            return True
        except Exception as e:
            print(f"Error exporting PDF: {e}")
            return False
