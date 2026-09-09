"""Document import, export, and companion story metadata serialization."""

import json
import os
from typing import Optional, Dict, Any
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

from PySide6.QtCore import Qt, QSizeF, QMarginsF
from PySide6.QtGui import (
    QTextDocument, QTextCursor, QTextBlock, QTextCharFormat,
    QTextBlockFormat, QFont, QPageSize, QPageLayout
)
from PySide6.QtPrintSupport import QPrinter

from volumenodex.core.document_model import PageLayoutModel, PaperSizePreset, Orientation


class IOManager:
    """Handles native .docx file IO, high-resolution PDF export, RTF, and .story.json companion metadata."""

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
            doc = docx.Document(file_path)
            qdoc.clear()
            cursor = QTextCursor(qdoc)

            for p in doc.paragraphs:
                # Add runs with formatting
                if p.style and p.style.name.startswith("Heading"):
                    cursor.insertHtml(f"<h2>{p.text}</h2>")
                elif p.style and p.style.name == "Title":
                    cursor.insertHtml(f"<h1>{p.text}</h1>")
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
                            char_fmt.setFontFamily(run.font.name)
                        if run.font.size:
                            char_fmt.setFontPointSize(run.font.size.pt)
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
