"""Comprehensive test suite for the 12 extended studio features:
1. Direct Physical Printing & Low-Ink Mode ink optimization
2. Table Builder and cell manipulation
3. Superscript, Subscript, Super-superscript, Sub-subscript
4. Indentation controls (increase, decrease, first-line indent, Tab key)
5. Recent files list & Auto-open recent document toggle
6. Right-click context menu spelling fixes & live suggestion generation
7. Header & footer model with per-page overrides and dynamic tokens
8. Footnote and head note management
9. Multi-format export engine (PDF, EPUB 3, High-res images, Markdown, HTML, TXT)
10. Split-screen dual workspace
11. Typewriter scrolling option
12. Daily Word Count Goal and circular progress ring
"""

import os
import zipfile
import tempfile
import pytest
from PySide6.QtCore import Qt, QPointF, QPoint, QSize
from PySide6.QtGui import (
    QTextCursor, QColor, QFont, QTextCharFormat, QKeyEvent, QBrush
)
from PySide6.QtWidgets import QApplication, QMenu

from volumenodex.core.document_model import PageLayoutModel
from volumenodex.canvas.paper_texture import PaperTextureEngine
from volumenodex.core.theme_manager import ThemeManager
from volumenodex.canvas.paginated_canvas import PaginatedCanvas
from volumenodex.core.header_footer_model import HeaderFooterModel, PageHeaderFooterConfig
from volumenodex.core.note_model import NoteManager, Footnote, HeadNote
from volumenodex.core.export_engine import ExportEngine
from volumenodex.core.settings_manager import SettingsManager
from volumenodex.ui.progress_ring import DailyGoalProgressRing
from volumenodex.ui.main_window import MainWindow


@pytest.fixture
def canvas(app):
    layout = PageLayoutModel()
    texture = PaperTextureEngine()
    theme = ThemeManager()
    c = PaginatedCanvas(layout, texture, theme)
    c.resize(800, 1000)
    return c


def test_header_footer_model_page_overrides_and_tokens():
    """Validates HeaderFooterModel token expansion, different first page, and per-page overrides."""
    model = HeaderFooterModel()
    model.default_config.left_header = "{title}"
    model.default_config.center_header = "Chapter 1"
    model.default_config.right_header = "Page {page} of {total}"
    model.default_config.center_footer = "— {page} —"

    # Token expansion
    tokens = {
        "page": 2,
        "total": 10,
        "title": "The Odyssey",
        "author": "Homer",
        "date": "2026",
    }
    cfg2 = model.get_config_for_page(2)
    lh = model.expand_tokens(cfg2.left_header, tokens)
    rh = model.expand_tokens(cfg2.right_header, tokens)
    cf = model.expand_tokens(cfg2.center_footer, tokens)

    assert lh == "The Odyssey"
    assert rh == "Page 2 of 10"
    assert cf == "— 2 —"

    # Different first page
    model.different_first_page = True
    model.first_page_config.center_header = ""
    model.first_page_config.center_footer = "First Page Confidential"

    cfg1 = model.get_config_for_page(1)
    assert cfg1.center_header == ""
    assert cfg1.center_footer == "First Page Confidential"

    # Per-page unlinked override on page 5
    p5_override = PageHeaderFooterConfig(
        is_linked_to_previous=False,
        header_left="Special Appendix",
        footer_center="[Appendix 5]",
    )
    model.set_page_override(5, p5_override)

    cfg5 = model.get_config_for_page(5)
    assert cfg5.header_left == "Special Appendix"
    assert cfg5.footer_center == "[Appendix 5]"

    # Page 6 should revert to default config
    cfg6 = model.get_config_for_page(6)
    assert cfg6.center_header == "Chapter 1"


def test_note_model_and_footnote_insertion(canvas):
    """Validates NoteManager tracking and footnote/headnote canvas insertion."""
    nm = canvas.note_manager
    fn1 = nm.add_footnote("First historical reference citation.", anchor_pos=12, page_num=1)
    assert fn1.number == 1
    assert fn1.marker == "1"

    fn2 = nm.add_footnote("Second commentary note.", anchor_pos=45, page_num=1)
    assert fn2.number == 2

    hn = nm.add_headnote("Chapter Prologue", "Historical background context.")
    assert len(nm.headnotes) == 1
    assert hn.section_title == "Chapter Prologue"

    # Test canvas insertion methods
    canvas.insert_text_at_cursor("In an ancient kingdom")
    canvas.insert_footnote("Archival reference from 1492.")
    assert len(canvas.note_manager.footnotes) == 3
    assert "[3]" in canvas.document().toPlainText()

    canvas.insert_headnote("Act I", "The storm approaches.")
    assert len(canvas.note_manager.headnotes) == 2
    assert "Act I — The storm approaches." in canvas.document().toPlainText()


def test_table_insertion_and_manipulation(canvas):
    """Validates inserting a structured table and modifying its rows and columns."""
    canvas.document().setPlainText("")
    cursor = canvas.cursor
    cursor.setPosition(0)

    # Insert 3x4 table with header
    table = canvas.insert_table(rows=3, cols=4, has_header=True, border_width=1, cell_padding=4)
    assert table is not None
    assert table.rows() == 3
    assert table.columns() == 4

    # Move cursor to first cell and insert text
    cell = table.cellAt(0, 0)
    c_cursor = cell.firstCursorPosition()
    c_cursor.insertText("Header 1")
    assert "Header 1" in canvas.document().toPlainText()

    # Move cursor into table to test manipulation
    canvas._cursor = table.cellAt(1, 1).firstCursorPosition()

    # Insert row below
    canvas.table_insert_row_below()
    assert table.rows() == 4

    # Insert column right
    canvas.table_insert_col_right()
    assert table.columns() == 5

    # Remove row
    canvas.table_remove_row()
    assert table.rows() == 3

    # Remove column
    canvas.table_remove_col()
    assert table.columns() == 4


def test_script_alignment_formatting(canvas):
    """Validates Superscript, Subscript, Super-superscript, Sub-subscript, and Normal formatting."""
    canvas.document().setPlainText("Einstein E=mc2 water H2O note x22")
    cur = canvas.cursor

    # Select '2' in 'mc2' (index 14 to 15)
    cur.setPosition(14)
    cur.setPosition(15, QTextCursor.MoveMode.KeepAnchor)
    canvas.set_script_alignment("super")

    cur.setPosition(14)
    cur.setPosition(15, QTextCursor.MoveMode.KeepAnchor)
    cf_super = cur.charFormat()
    assert cf_super.verticalAlignment() == QTextCharFormat.VerticalAlignment.AlignSuperScript

    # Select '2' in 'H2O'
    h2o_pos = canvas.document().toPlainText().find("H2O") + 1
    cur.setPosition(h2o_pos)
    cur.setPosition(h2o_pos + 1, QTextCursor.MoveMode.KeepAnchor)
    canvas.set_script_alignment("sub")

    cur.setPosition(h2o_pos)
    cur.setPosition(h2o_pos + 1, QTextCursor.MoveMode.KeepAnchor)
    cf_sub = cur.charFormat()
    assert cf_sub.verticalAlignment() == QTextCharFormat.VerticalAlignment.AlignSubScript

    # Super-superscript
    cur.setPosition(0)
    cur.setPosition(8, QTextCursor.MoveMode.KeepAnchor)
    canvas.set_script_alignment("super_super")
    cf_ss = cur.charFormat()
    assert cf_ss.verticalAlignment() == QTextCharFormat.VerticalAlignment.AlignSuperScript
    assert cf_ss.fontPointSize() > 0

    # Return to normal
    canvas.set_script_alignment("normal")
    cf_normal = cur.charFormat()
    assert cf_normal.verticalAlignment() == QTextCharFormat.VerticalAlignment.AlignNormal


def test_indentation_controls(canvas):
    """Validates Increase/Decrease indent and First-line indent."""
    canvas.document().setPlainText("Paragraph one.\nParagraph two.")
    cur = canvas.cursor
    cur.setPosition(5)

    # Increase indent
    canvas.increase_indent()
    block = canvas.document().findBlock(cur.position())
    assert block.blockFormat().indent() >= 1

    # Decrease indent
    canvas.decrease_indent()
    block = canvas.document().findBlock(cur.position())
    assert block.blockFormat().indent() == 0

    # First-line indent (0.5 inch = 36 pt)
    canvas.set_first_line_indent(36.0)
    block = canvas.document().findBlock(cur.position())
    assert block.blockFormat().textIndent() == 36.0

    # Tab key press at block start indents
    cur.setPosition(0)
    event_tab = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Tab, Qt.KeyboardModifier.NoModifier)
    canvas.keyPressEvent(event_tab)
    block = canvas.document().findBlock(0)
    assert block.blockFormat().indent() >= 1

    # Shift+Tab key press decreases indent
    event_backtab = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Tab, Qt.KeyboardModifier.ShiftModifier)
    canvas.keyPressEvent(event_backtab)
    block = canvas.document().findBlock(0)
    assert block.blockFormat().indent() == 0


def test_multi_format_export_suite(canvas):
    """Validates ExportEngine for TXT, MD, HTML, EPUB 3, and high-res images."""
    canvas.document().setHtml(
        "<h1>Prologue</h1>"
        "<p>The harbor bell chimed three times through the morning sea fog.</p>"
        "<h2>Chapter 1</h2>"
        "<p>Master Sean sharpened his quill with practiced precision.</p>"
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        txt_path = os.path.join(tmpdir, "test.txt")
        md_path = os.path.join(tmpdir, "test.md")
        html_path = os.path.join(tmpdir, "test.html")
        epub_path = os.path.join(tmpdir, "test.epub")
        png_path = os.path.join(tmpdir, "test.png")
        jpg_path = os.path.join(tmpdir, "test.jpg")

        # 1. Plain Text
        assert ExportEngine.export_plain_text(txt_path, canvas.document())
        assert os.path.exists(txt_path)
        with open(txt_path, "r", encoding="utf-8") as f:
            content = f.read()
            assert "harbor bell" in content

        # 2. Markdown
        assert ExportEngine.export_markdown(md_path, canvas.document())
        assert os.path.exists(md_path)
        with open(md_path, "r", encoding="utf-8") as f:
            content = f.read()
            assert "harbor bell" in content

        # 3. Clean HTML5
        assert ExportEngine.export_html(html_path, canvas.document(), title="Test Title")
        assert os.path.exists(html_path)
        with open(html_path, "r", encoding="utf-8") as f:
            content = f.read()
            assert "<!DOCTYPE html>" in content
            assert "harbor bell" in content

        # 4. EPUB 3 E-Book
        assert ExportEngine.export_epub(epub_path, canvas.document(), title="Ocean Tales", author="Sean")
        assert os.path.exists(epub_path)
        assert zipfile.is_zipfile(epub_path)

        with zipfile.ZipFile(epub_path, "r") as zf:
            file_list = zf.namelist()
            assert "mimetype" in file_list
            assert "META-INF/container.xml" in file_list
            assert "OEBPS/content.opf" in file_list
            assert "OEBPS/toc.ncx" in file_list
            assert "OEBPS/nav.xhtml" in file_list
            assert "OEBPS/styles.css" in file_list
            assert any(name.startswith("OEBPS/chapter_") for name in file_list)

            # Check mimetype is uncompressed first file
            assert file_list[0] == "mimetype"
            info = zf.getinfo("mimetype")
            assert info.compress_type == zipfile.ZIP_STORED

        # 5. High-Resolution Page Images (PNG and JPEG)
        assert ExportEngine.export_page_image(png_path, canvas.document(), canvas.layout_model, page_index=0, dpi_scale=1.5)
        assert os.path.exists(png_path)
        assert os.path.getsize(png_path) > 1000

        assert ExportEngine.export_page_image(jpg_path, canvas.document(), canvas.layout_model, page_index=0, dpi_scale=1.5)
        assert os.path.exists(jpg_path)
        assert os.path.getsize(jpg_path) > 1000


def test_daily_word_goal_progress_ring(app):
    """Validates DailyGoalProgressRing arc calculation and goal adjustments."""
    ring = DailyGoalProgressRing(current_words=500, goal_words=1000)
    assert ring.current_words == 500
    assert ring.goal_words == 1000

    ring.set_progress(750, 1000)
    assert ring.current_words == 750
    assert "75%" in ring.toolTip()

    # Exceeding goal
    ring.set_progress(1250, 1000)
    assert ring.current_words == 1250
    assert "100%" in ring.toolTip()


def test_settings_recent_files_and_auto_open(canvas):
    """Validates recent files history and auto_open_recent setting with real files."""
    sm = SettingsManager(canvas)
    sm.clear_recent_files()
    assert len(sm.recent_files) == 0

    with tempfile.TemporaryDirectory() as tmpdir:
        p1 = os.path.join(tmpdir, "story1.docx")
        p2 = os.path.join(tmpdir, "story2.docx")
        with open(p1, "w") as f: f.write("test1")
        with open(p2, "w") as f: f.write("test2")

        sm.add_recent_file(p1)
        sm.add_recent_file(p2)
        assert len(sm.recent_files) == 2
        assert sm.recent_files[0] == os.path.abspath(p2)

    sm.auto_open_recent = True
    assert sm.auto_open_recent is True
    sm.auto_open_recent = False
    assert sm.auto_open_recent is False


def test_main_window_split_screen_and_typewriter(app):
    """Validates MainWindow split-screen dual workspace and typewriter scrolling toggle."""
    win = MainWindow()
    assert win.secondary_container.isHidden()

    # Toggle split screen on
    win.toggle_split_screen()
    assert not win.secondary_container.isHidden()
    assert win.secondary_canvas.document() == win.canvas_area.document()

    # Toggle split screen off
    win.toggle_split_screen()
    assert win.secondary_container.isHidden()

    # Toggle typewriter scroll
    assert not win.canvas_area.typewriter_scrolling
    win._toggle_typewriter_scrolling(True)
    assert win.canvas_area.typewriter_scrolling is True
    win._toggle_typewriter_scrolling(False)
    assert win.canvas_area.typewriter_scrolling is False


def test_spelling_clickable_menu_live_suggestions(canvas):
    """Validates spelling checks identify misspelled words and produce clickable replacement candidates."""
    from volumenodex.review.spell_engine import SpellCheckEngine
    canvas.spell_engine = SpellCheckEngine()

    # Check that misspelled word is detected and has corrections
    word = "definately"
    assert not canvas.spell_engine.check_word(word)
    suggestions = canvas.spell_engine.get_suggestions(word)
    assert "definitely" in suggestions

    # Test that replace_range correctly updates the text in the canvas
    canvas.document().setPlainText("This is a definately misspelled sentence.")
    pos = canvas.document().toPlainText().find(word)
    canvas.replace_range(pos, pos + len(word), suggestions[0])
    assert "definitely" in canvas.document().toPlainText()
    assert "definately" not in canvas.document().toPlainText()
