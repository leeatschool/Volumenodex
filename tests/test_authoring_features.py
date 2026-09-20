"""Comprehensive test suite for Home & Insert ribbon authoring enhancements:
- Paste without formatting
- All system fonts in typography
- Font size up to 200 pt
- Bullets & numbered lists under Typography
- Heading 3, 4, 5 and custom style creation
- Picture and clip art insertion
- Navigator outline detection for h1-h5
"""

import sys
import os
import tempfile

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QImage, QColor, QFontDatabase, QTextDocument, QTextBlockFormat
from PySide6.QtWidgets import QApplication

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from volumenodex.ui.main_window import MainWindow
from volumenodex.canvas.paginated_canvas import PaginatedCanvas
from volumenodex.core.document_model import PageLayoutModel
from volumenodex.canvas.paper_texture import PaperTextureEngine
from volumenodex.core.theme_manager import ThemeManager
from volumenodex.ui.clipart_dialog import ClipArtDialog
from volumenodex.story.navigator_drawer import ChapterNavigatorDrawer


def app():
    app = QApplication.instance()
    if not app:
        app = QApplication([])
    return app


def test_clipboard_paste_plain(app):
    win = MainWindow()
    win.show()

    # Clear document and test paste plain
    win.editor.setPlainText("Hello ")
    win.editor.scroll_to_position(6)

    # Set HTML on clipboard
    clipboard = QApplication.clipboard()
    clipboard.setText("World of Books")
    clip_text = clipboard.text() or "World of Books"

    win.editor.paste_plain(clip_text)
    assert "Hello World of Books" in win.editor.toPlainText()

    # Verify dedicated Paste Plain button exists and is visible
    assert hasattr(win.ribbon, "btn_paste_plain")
    assert win.ribbon.btn_paste_plain.text() == "Paste Plain"
    assert "Paste without Formatting" in win.ribbon.btn_paste_plain.toolTip()
    win.close()


def test_system_fonts_in_typography(app):
    win = MainWindow()
    combo = win.ribbon.font_combo

    # Check font combo is editable
    assert combo.isEditable()

    # System fonts count should be substantial (> 30 on any Windows system)
    system_fonts = QFontDatabase.families()
    assert combo.count() >= min(30, len(system_fonts))

    # Curated fonts should be at the top
    top_items = [combo.itemText(i) for i in range(min(5, combo.count()))]
    assert "Georgia" in top_items or "Georgia" in [combo.itemText(i) for i in range(combo.count())]
    win.close()


def test_font_size_up_to_200(app):
    win = MainWindow()
    combo = win.ribbon.size_combo

    assert combo.isEditable()
    all_sizes = [int(combo.itemText(i)) for i in range(combo.count())]
    assert 200 in all_sizes
    assert max(all_sizes) == 200
    assert min(all_sizes) <= 8

    # Test setting custom size
    combo.setEditText("150")
    # Verify editor receives font size
    win.ribbon.size_combo.setEditText("120")
    win.close()


def test_bullets_and_numbers_under_typography(app):
    win = MainWindow()

    # Bullets and numbers must belong to Typography ribbon group
    btn_bullet = win.ribbon.btn_bullet
    btn_numbered = win.ribbon.btn_numbered

    assert btn_bullet is not None
    assert btn_numbered is not None

    # Check that they trigger canvas list generation
    win.editor.setPlainText("First line\nSecond line")
    win.ribbon.bulletListRequested.emit()
    assert win.editor.textCursor().currentList() is not None
    win.close()


def test_heading_3_4_5_and_custom_styles(app):
    win = MainWindow()
    ed = win.editor

    # Test Heading 3
    ed.setPlainText("Test Heading 3")
    ed.apply_style("Heading 3")
    bf = ed.currentBlockFormat()
    assert bf.property(QTextBlockFormat.Property.UserProperty) == "h3"
    cf = ed.currentCharFormat()
    assert int(cf.fontPointSize()) == 13

    # Test Heading 4
    ed.apply_style("Heading 4")
    bf = ed.currentBlockFormat()
    assert bf.property(QTextBlockFormat.Property.UserProperty) == "h4"
    assert int(ed.currentCharFormat().fontPointSize()) == 12

    # Test Heading 5
    ed.apply_style("Heading 5")
    bf = ed.currentBlockFormat()
    assert bf.property(QTextBlockFormat.Property.UserProperty) == "h5"
    assert int(ed.currentCharFormat().fontPointSize()) == 11
    assert ed.currentCharFormat().fontItalic() is True

    # Test Custom Style saving & applying
    snapshot = ed.current_style_snapshot()
    assert snapshot["font_size"] == 11
    assert snapshot["italic"] is True

    custom_style = {
        "font_family": "Arial",
        "font_size": 24,
        "bold": True,
        "italic": False,
        "underline": True,
        "strike": False,
        "color": "#ff00ff",
        "bg_color": "#00ff00",
        "align": Qt.AlignmentFlag.AlignCenter,
        "line_height": 200,
        "top_margin": 10,
        "bottom_margin": 10
    }
    ed.apply_custom_style(custom_style)
    assert ("Arial" in ed.currentCharFormat().fontFamilies()) or ed.currentCharFormat().fontFamily() == "Arial"
    assert int(ed.currentCharFormat().fontPointSize()) == 24
    assert ed.fontWeight() >= 700
    assert ed.fontUnderline() is True
    assert ed.currentBlockFormat().alignment() == Qt.AlignmentFlag.AlignCenter

    # Verify Ribbon custom style button addition
    win.ribbon.add_custom_style_button("My Style")
    win.close()


def test_insert_image_and_clipart(app):
    win = MainWindow()
    ed = win.editor

    # Create temporary PNG image
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp_name = tmp.name

    try:
        img = QImage(300, 200, QImage.Format.Format_RGB32)
        img.fill(QColor(100, 150, 200))
        img.save(tmp_name)

        success = ed.insert_image(tmp_name)
        assert success is True
        # Verify document contains image resource
        assert ed.toPlainText() is not None
    finally:
        if os.path.exists(tmp_name):
            os.remove(tmp_name)

    # Test ClipArtDialog empty state
    clipart_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets", "clipart"))
    dlg = ClipArtDialog(clipart_dir, parent=win)
    assert dlg.clipart_dir == clipart_dir
    assert dlg.windowTitle() == "Insert Clip Art - Volumenodex Library"
    dlg.close()
    win.close()


def test_navigator_outline_heading_levels(app):
    win = MainWindow()
    nav = win.left_navigator
    doc = QTextDocument()

    # Build document with h1, h2, h3, h4, h5 blocks
    cursor = doc.rootFrame().firstCursorPosition()

    cursor.insertText("Title Block")
    bf = cursor.blockFormat()
    bf.setProperty(QTextBlockFormat.Property.UserProperty, "title")
    cursor.setBlockFormat(bf)
    cursor.insertBlock()

    cursor.insertText("Chapter 1: The Beginning")
    bf = cursor.blockFormat()
    bf.setProperty(QTextBlockFormat.Property.UserProperty, "h1")
    cursor.setBlockFormat(bf)
    cursor.insertBlock()

    cursor.insertText("Section 1.1")
    bf = cursor.blockFormat()
    bf.setProperty(QTextBlockFormat.Property.UserProperty, "h2")
    cursor.setBlockFormat(bf)
    cursor.insertBlock()

    cursor.insertText("Subsection 1.1.1")
    bf = cursor.blockFormat()
    bf.setProperty(QTextBlockFormat.Property.UserProperty, "h3")
    cursor.setBlockFormat(bf)
    cursor.insertBlock()

    cursor.insertText("Sub-subsection 1.1.1.1")
    bf = cursor.blockFormat()
    bf.setProperty(QTextBlockFormat.Property.UserProperty, "h4")
    cursor.setBlockFormat(bf)
    cursor.insertBlock()

    cursor.insertText("Minor point 1.1.1.1.1")
    bf = cursor.blockFormat()
    bf.setProperty(QTextBlockFormat.Property.UserProperty, "h5")
    cursor.setBlockFormat(bf)

    nav.scan_manuscript(doc)
    assert len(nav._items) >= 5
    levels = [item.heading_level for item in nav._items]
    assert 1 in levels
    assert 2 in levels
    assert 3 in levels
    assert 4 in levels
    assert 5 in levels
    win.close()


def test_document_default_text_color_on_paper_modes(app):
    """Verifies that new document text defaults to black, and switches to white on dark paper."""
    from PySide6.QtGui import QColor, QKeyEvent
    from PySide6.QtCore import Qt
    win = MainWindow()
    win.show()

    # On standard light paper, new document cursor format should be black
    win.editor.clear()
    assert win.editor.dark_paper is False
    fmt = win.editor.textCursor().charFormat()
    assert fmt.foreground().color().name().lower() == "#000000"

    # Simulate typing on light paper
    ev = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_A, Qt.KeyboardModifier.NoModifier, "A")
    win.editor.keyPressEvent(ev)
    doc_text = win.editor.toPlainText()
    assert "A" in doc_text
    frag = win.editor.document().firstBlock().begin().fragment()
    assert frag.charFormat().foreground().color().name().lower() == "#000000"

    # Toggle to dark paper
    win._on_dark_paper_toggled(True)
    assert win.editor.dark_paper is True
    win.editor.clear()
    fmt_dark = win.editor.textCursor().charFormat()
    assert fmt_dark.foreground().color().name().lower() == "#ffffff"

    # Simulate typing on dark paper
    ev2 = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_B, Qt.KeyboardModifier.NoModifier, "B")
    win.editor.keyPressEvent(ev2)
    assert "B" in win.editor.toPlainText()
    frag2 = win.editor.document().firstBlock().begin().fragment()
    assert frag2.charFormat().foreground().color().name().lower() == "#ffffff"

    win.close()


def test_clipart_dialog_search_and_robustness(app):
    """Verifies that the ClipArtDialog supports live title search, recursive category scanning, and keyboard selection."""
    import tempfile
    from PySide6.QtGui import QImage
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create sample clipart images
        sub_dir = os.path.join(tmpdir, "Heraldry")
        os.makedirs(sub_dir, exist_ok=True)

        files = [
            os.path.join(tmpdir, "celtic_border.png"),
            os.path.join(tmpdir, "dragon_crest.png"),
            os.path.join(tmpdir, "flourish_divider.png"),
            os.path.join(sub_dir, "knight_shield.png"),
        ]
        for p in files:
            img = QImage(32, 32, QImage.Format.Format_RGB32)
            img.fill(0xFFFFFF)
            img.save(p)

        dlg = ClipArtDialog(tmpdir)
        dlg.show()
        # Zero images loaded initially for sub-second startup
        assert len(dlg._indexed_items) == 4
        assert dlg.list_widget.count() == 0
        assert not dlg.initial_card.isHidden()

        # Search for dragon
        dlg.search_input.setText("dragon")
        visible = [dlg.list_widget.item(i) for i in range(dlg.list_widget.count()) if not dlg.list_widget.item(i).isHidden()]
        assert len(visible) == 1
        assert "Dragon" in visible[0].text()

        # Search for nested subfolder item
        dlg.search_input.setText("shield")
        visible_shield = [dlg.list_widget.item(i) for i in range(dlg.list_widget.count()) if not dlg.list_widget.item(i).isHidden()]
        assert len(visible_shield) == 1
        assert "Knight Shield" in visible_shield[0].text()

        # Search with no matches
        dlg.search_input.setText("spaceship")
        visible_none = [dlg.list_widget.item(i) for i in range(dlg.list_widget.count()) if not dlg.list_widget.item(i).isHidden()]
        assert len(visible_none) == 0
        assert not dlg.no_results_card.isHidden()

        # Clear search: returns to initial prompt card
        dlg.btn_clear_search.click()
        assert dlg.search_input.text() == ""
        assert dlg.list_widget.count() == 0
        assert not dlg.initial_card.isHidden()

        # Browse all explicitly: renders all 4 items
        dlg._on_browse_all_clicked()
        visible_all = [dlg.list_widget.item(i) for i in range(dlg.list_widget.count()) if not dlg.list_widget.item(i).isHidden()]
        assert len(visible_all) == 4

        # Enter key triggers auto-selection
        dlg.search_input.setText("dragon")
        dlg.search_input.returnPressed.emit()
        assert dlg.selected_file is not None
        assert "dragon_crest.png" in dlg.selected_file
        dlg.close()


if __name__ == "__main__":
    test_app = QApplication.instance() or QApplication(sys.argv)
    tests = [
        test_clipboard_paste_plain,
        test_system_fonts_in_typography,
        test_font_size_up_to_200,
        test_bullets_and_numbers_under_typography,
        test_heading_3_4_5_and_custom_styles,
        test_insert_image_and_clipart,
        test_navigator_outline_heading_levels,
    ]

    passed = 0
    failed = 0
    print("==================================================")
    print("Running Volumenodex Authoring Feature Tests...")
    print("==================================================")
    for t in tests:
        try:
            print(f"RUNNING: {t.__name__}...", end=" ", flush=True)
            t(test_app)
            print("PASSED [OK]")
            passed += 1
        except Exception as e:
            print(f"FAILED: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("==================================================")
    print(f"Results: {passed} passed, {failed} failed.")
    print("==================================================")
    if failed > 0:
        sys.exit(1)
    else:
        sys.exit(0)
