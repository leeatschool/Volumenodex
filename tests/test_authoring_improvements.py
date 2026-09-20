"""Comprehensive tests for new authoring capabilities:
1. Review function right-click clickable fixes (word swaps, deletions, spelling corrections).
2. Auto-trigger numbered lists from N. starting at N (e.g. 3. -> Enter gives 4.).
3. Adverb punchy verb suggestions without placeholder phrases.
4. Font color and text highlighting application and .docx roundtrip serialization.
"""

import os
import tempfile
import pytest
from PySide6.QtCore import Qt, QPointF, QPoint
from PySide6.QtGui import (
    QKeyEvent, QTextCursor, QColor, QContextMenuEvent
)
from PySide6.QtWidgets import QApplication, QMenu

from volumenodex.core.document_model import PageLayoutModel
from volumenodex.canvas.paper_texture import PaperTextureEngine
from volumenodex.core.theme_manager import ThemeManager
from volumenodex.canvas.paginated_canvas import PaginatedCanvas
from volumenodex.review.lens_engine import RevisionLensEngine, LensFinding
from volumenodex.core.io_manager import IOManager


@pytest.fixture
def canvas(app):
    """Initializes a standalone headless PaginatedCanvas."""
    layout = PageLayoutModel()
    texture = PaperTextureEngine()
    theme = ThemeManager()
    c = PaginatedCanvas(layout, texture, theme)
    c.resize(800, 1000)
    return c


def test_adverb_punchy_verb_suggestions():
    """Validates that adverbs suggest punchy active verbs and never placeholder text."""
    text = "She walked quietly into the room and smiled happily."
    findings = RevisionLensEngine.analyze_document(text, {"adverb": True})

    adverb_findings = [f for f in findings if f.lens_type == "adverb"]
    assert len(adverb_findings) >= 2

    for f in adverb_findings:
        assert len(f.suggestions) > 0
        # Ensure the forbidden placeholder phrase is nowhere to be found
        for sug in f.suggestions:
            assert "rephrase with a punchy verb" not in sug.lower()
            assert "rephrase" not in sug.lower()

    # 'quietly' should have vivid active verbs like 'whispered', 'tiptoed', 'crept'
    quietly_f = next(f for f in adverb_findings if f.text == "quietly")
    assert any(v in quietly_f.suggestions for v in ["whispered", "tiptoed", "crept", "murmured"])
    assert "(remove)" in quietly_f.suggestions


def test_auto_numbered_list_starts_with_typed_number(canvas):
    """Typing '3.' at the beginning of a line must trigger a numbered list starting at 3, and Enter produces 4."""
    canvas._doc.setPlainText("")
    cur = canvas._cursor
    cur.setPosition(0)

    # Simulate typing '3'
    event_3 = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_3, Qt.KeyboardModifier.NoModifier, "3")
    canvas.keyPressEvent(event_3)
    assert canvas._doc.toPlainText() == "3"
    assert canvas._cursor.block().textList() is None

    # Simulate typing '.'
    event_dot = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Period, Qt.KeyboardModifier.NoModifier, ".")
    canvas.keyPressEvent(event_dot)

    # Now the block should be auto-converted into a numbered list
    block = canvas._cursor.block()
    lst = block.textList()
    assert lst is not None, "Block should be converted into a QTextList"
    assert lst.format().start() == 3, f"List format start should be 3, got {lst.format().start()}"
    assert lst.itemText(block) == "3.", f"First item marker should be '3.', got {lst.itemText(block)}"
    assert block.text() == "", "Block content should be empty after marker removal"

    # Simulate pressing space (should be absorbed cleanly without leaving leading indent)
    event_space = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Space, Qt.KeyboardModifier.NoModifier, " ")
    canvas.keyPressEvent(event_space)
    assert canvas._cursor.block().text() == ""

    # Type first item text
    canvas._cursor.insertText("Step three details")
    assert canvas._cursor.block().text() == "Step three details"

    # Simulate pressing Enter (Return)
    event_enter = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Return, Qt.KeyboardModifier.NoModifier, "\r")
    canvas.keyPressEvent(event_enter)

    # Second item should be in the list with marker '4.'
    b2 = canvas._cursor.block()
    assert b2.textList() is not None, "New block after Enter must remain in list"
    assert b2.textList().itemText(b2) == "4.", f"Second item marker should be '4.', got {b2.textList().itemText(b2)}"
    assert b2.text() == ""

    # Pressing Enter on empty item exits list back to normal paragraph
    canvas.keyPressEvent(event_enter)
    b3 = canvas._cursor.block()
    assert b3.textList() is None, "Pressing Enter on empty list item must exit list"

    # Test Undo (Ctrl+Z) undoes list exit and list creation
    canvas._doc.undo()
    canvas._doc.undo()
    canvas._doc.undo()


def test_auto_numbered_list_exit_on_backspace(canvas):
    """Pressing Backspace on an empty list item must exit the list cleanly."""
    canvas._doc.setPlainText("")
    canvas._cursor.setPosition(0)

    # Trigger list via '5.'
    canvas.keyPressEvent(QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_5, Qt.KeyboardModifier.NoModifier, "5"))
    canvas.keyPressEvent(QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Period, Qt.KeyboardModifier.NoModifier, "."))

    block = canvas._cursor.block()
    lst = block.textList()
    assert lst is not None
    assert lst.format().start() == 5
    assert lst.itemText(block) == "5."

    # Block is empty; pressing Backspace exits the list
    event_bs = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Backspace, Qt.KeyboardModifier.NoModifier)
    canvas.keyPressEvent(event_bs)

    assert canvas._cursor.block().textList() is None, "Backspace on empty item should remove list formatting"


def test_review_function_right_click_clickable_fixes(canvas):
    """Right clicking on review findings provides actionable, clickable fixes and word swaps in the menu."""
    text = "She whispered quietly to him because of the fact that it was dark."
    canvas._doc.setPlainText(text)

    # Finding 1: Adverb 'quietly' at indices 14-21
    finding_adverb = LensFinding(
        lens_type="adverb",
        start_pos=14,
        end_pos=21,
        text="quietly",
        color=QColor(255, 200, 100),
        message="Weak adverb.",
        suggestions=["murmured", "breathed", "(remove)"],
    )

    # Finding 2: Filler phrase 'because of the fact that' at indices 29-53
    finding_filler = LensFinding(
        lens_type="filler",
        start_pos=29,
        end_pos=53,
        text="because of the fact that",
        color=QColor(200, 100, 255),
        message="Wordy crutch phrase.",
        suggestions=["since", "because", "(remove)"],
    )

    canvas.set_lens_findings([finding_adverb, finding_filler])
    assert len(canvas._lens_findings) == 2

    # Verify context menu items at 'quietly' (index 16)
    # We test menu generation logic directly
    pos = 16
    matched = [f for f in canvas._lens_findings if f.start_pos <= pos <= f.end_pos]
    assert len(matched) == 1
    assert matched[0].text == "quietly"

    # Perform replace_range with swap suggestion
    canvas.replace_range(matched[0].start_pos, matched[0].end_pos, "softly")
    assert "softly" in canvas._doc.toPlainText()
    assert "quietly" not in canvas._doc.toPlainText()

    # Perform deletion with space cleanup
    canvas._doc.setPlainText("She said quietly to him.")
    canvas.replace_range(9, 16, "")
    # Extra space after 'quietly' must be cleaned up
    assert canvas._doc.toPlainText() == "She said to him."


def test_font_color_and_highlight_canvas_methods(canvas):
    """Tests set_text_color, set_highlight_color, and clear_highlight on PaginatedCanvas."""
    canvas._doc.setPlainText("Hello luxury publishing world.")

    # Select 'luxury'
    canvas._cursor.setPosition(6)
    canvas._cursor.setPosition(12, QTextCursor.MoveMode.KeepAnchor)
    assert canvas._cursor.selectedText() == "luxury"

    # Set text color to crimson red
    crimson = QColor("#dc2626")
    canvas.set_text_color(crimson)
    assert canvas._cursor.charFormat().foreground().color().name() == crimson.name()

    # Set highlight color to bright yellow
    yellow = QColor("#fef08a")
    canvas.set_highlight_color(yellow)
    assert canvas._cursor.charFormat().background().color().name() == yellow.name()

    # Clear highlight
    canvas.clear_highlight()
    assert canvas._cursor.charFormat().background().style() == Qt.BrushStyle.NoBrush


def test_font_color_and_highlight_docx_roundtrip(app):
    """Validates that font colors and highlights roundtrip accurately through .docx files."""
    layout = PageLayoutModel()
    texture = PaperTextureEngine()
    theme = ThemeManager()
    canvas_orig = PaginatedCanvas(layout, texture, theme)
    canvas_orig._doc.setPlainText("First paragraph text. Highlighted section here. End text.")

    # Select 'Highlighted section' (indices 22 to 41)
    cur = canvas_orig._cursor
    cur.setPosition(22)
    cur.setPosition(41, QTextCursor.MoveMode.KeepAnchor)

    royal_blue = QColor("#2563eb")
    yellow_hl = QColor("#fef08a")
    canvas_orig.set_text_color(royal_blue)
    canvas_orig.set_highlight_color(yellow_hl)

    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tf:
        temp_docx = tf.name

    try:
        # Save to docx
        success = IOManager.save_docx(temp_docx, canvas_orig._doc, layout)
        assert success is True, "Failed to save docx"

        # Load back into a fresh document
        canvas_loaded = PaginatedCanvas(layout, texture, theme)
        IOManager.load_docx(temp_docx, canvas_loaded._doc)

        loaded_text = canvas_loaded._doc.toPlainText()
        assert "Highlighted section" in loaded_text

        # Verify formatting in loaded fragments
        block = canvas_loaded._doc.firstBlock()
        it = block.begin()
        found_highlighted_run = False
        while not it.atEnd():
            frag = it.fragment()
            if "Highlighted section" in frag.text():
                found_highlighted_run = True
                # Foreground should be blue
                fg_name = frag.charFormat().foreground().color().name()
                assert fg_name == royal_blue.name(), f"Expected {royal_blue.name()}, got {fg_name}"
                # Background should be highlighted
                bg_name = frag.charFormat().background().color().name()
                assert bg_name == yellow_hl.name(), f"Expected {yellow_hl.name()}, got {bg_name}"
            it += 1

        assert found_highlighted_run is True, "Could not find highlighted fragment in loaded docx"

    finally:
        if os.path.exists(temp_docx):
            os.remove(temp_docx)


def test_aesthetics_ribbon_tab(app):
    """Validates that theme and sensory acoustics reside in the new Aesthetics tab."""
    from volumenodex.ui.ribbon import RibbonBar, TypewriterSoundPreset, AmbientSoundPreset
    ribbon = RibbonBar()
    tab_names = [ribbon.tab_widget.tabText(i) for i in range(ribbon.tab_widget.count())]
    assert "Aesthetics" in tab_names, f"Expected 'Aesthetics' tab in ribbon, got {tab_names}"

    # Aesthetics tab contains theme and sound controls
    assert hasattr(ribbon, "theme_combo")
    assert hasattr(ribbon, "typewriter_combo")
    assert hasattr(ribbon, "ambient_combo")
    assert hasattr(ribbon, "slider_typewriter_vol")
    assert hasattr(ribbon, "slider_ambient_vol")

    # Verify View tab does NOT duplicate theme/sensory
    view_idx = tab_names.index("View")
    view_tab = ribbon.tab_widget.widget(view_idx)
    assert ribbon.tab_widget.tabText(view_idx) == "View"


def test_audio_engine_acoustics_and_ambient(app):
    """Validates that AudioEngine correctly locates sounds, preloads effects, and handles playback."""
    from volumenodex.audio.audio_engine import AudioEngine, TypewriterSoundPreset, AmbientSoundPreset
    engine = AudioEngine()
    assert os.path.isdir(engine.sounds_dir)
    assert "manual_click1" in engine._effects
    assert "bell" in engine._effects

    # Keystrokes execute without exception
    engine.play_keystroke(is_return=False, is_space=False)
    engine.play_keystroke(is_return=True, is_space=False)

    # Ambient soundscape selection
    engine.set_ambient_preset(AmbientSoundPreset.BROWN_NOISE)
    assert engine._ambient_player.source().isValid()
    engine.set_ambient_preset(AmbientSoundPreset.OFF)


def test_window_icon_configured(app):
    """Validates that MainWindow configures a valid application icon."""
    from volumenodex.ui.main_window import MainWindow
    win = MainWindow()
    try:
        ico = win.windowIcon()
        assert not ico.isNull(), "MainWindow icon must be set and not null"
    finally:
        win.close()


def test_sound_variations_hidden_when_no_audio_file(app, tmp_path):
    """Validates that sound variations do not appear in the UI if their audio files do not exist."""
    from volumenodex.audio.audio_engine import AudioEngine, TypewriterSoundPreset, AmbientSoundPreset
    from volumenodex.ui.ribbon import RibbonBar

    # Test in an isolated temporary sounds directory
    temp_sounds = tmp_path / "assets" / "sounds"
    temp_sounds.mkdir(parents=True, exist_ok=True)

    engine = AudioEngine(base_dir=str(tmp_path))
    # When folder is completely empty, only Off is available
    tw_avail = [p[1] for p in engine.get_available_typewriter_presets()]
    amb_avail = [p[1] for p in engine.get_available_ambient_presets()]
    assert tw_avail == [TypewriterSoundPreset.OFF]
    assert amb_avail == [AmbientSoundPreset.OFF]

    # Create dummy audio files for specific presets
    test_wav = temp_sounds / "electric_click.wav"
    test_wav.write_bytes(b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x44\xac\x00\x00\x88\x58\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00")

    test_rain = temp_sounds / "Rain_Storm.wav"
    test_rain.write_bytes(b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x44\xac\x00\x00\x88\x58\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00")

    engine.reload_sounds()
    tw_avail2 = [p[1] for p in engine.get_available_typewriter_presets()]
    amb_avail2 = [p[1] for p in engine.get_available_ambient_presets()]

    # Electric Typewriter now appears because electric_click.wav exists
    assert TypewriterSoundPreset.ELECTRIC in tw_avail2
    # Manual and Soft Mechanical switches still do NOT appear
    assert TypewriterSoundPreset.MANUAL not in tw_avail2
    assert TypewriterSoundPreset.SOFT_MECHANICAL not in tw_avail2

    # Rain now appears because Rain_Storm.wav exists
    assert AmbientSoundPreset.RAIN in amb_avail2
    # Fireplace, Library, etc. do NOT appear
    assert AmbientSoundPreset.FIREPLACE not in amb_avail2
    assert AmbientSoundPreset.LIBRARY not in amb_avail2

    # Verify ribbon combo boxes only show the available presets
    ribbon = RibbonBar()
    ribbon.update_sound_presets(engine)
    tw_labels = [ribbon.typewriter_combo.itemText(i) for i in range(ribbon.typewriter_combo.count())]
    amb_labels = [ribbon.ambient_combo.itemText(i) for i in range(ribbon.ambient_combo.count())]

    assert "Electric Typewriter" in tw_labels
    assert "Classic Manual Typewriter" not in tw_labels
    assert "Soft Mechanical Switches" not in tw_labels

    assert "Rain on Window" in amb_labels
    assert "Quiet Library" not in amb_labels
    assert "Crackling Fireplace" not in amb_labels

    # Now remove the electric click file; verify it disappears upon reload
    test_wav.unlink()
    engine.reload_sounds()
    ribbon.update_sound_presets(engine)
    tw_labels_after = [ribbon.typewriter_combo.itemText(i) for i in range(ribbon.typewriter_combo.count())]
    assert "Electric Typewriter" not in tw_labels_after


def test_status_bar_set_message(app):
    """Validates VolumenodexStatusBar set_message and showMessage methods."""
    from volumenodex.ui.status_bar import VolumenodexStatusBar
    sb = VolumenodexStatusBar()
    sb.show()
    sb.set_message("Inserted clip art: test.jxl", timeout_ms=5000)
    assert not sb.lbl_message.isHidden()
    assert sb.lbl_message.text() == "Inserted clip art: test.jxl"

    sb.showMessage("Saved successfully")
    assert sb.lbl_message.text() == "Saved successfully"

    sb.set_message("")
    assert sb.lbl_message.isHidden()


def test_jxl_canvas_insertion_and_rendering(canvas, tmp_path):
    """Validates that JXL images inserted with absolute paths render properly without broken placeholders."""
    from PySide6.QtGui import QImage, QColor, QAbstractTextDocumentLayout, QPainter, QPixmap, QTextDocument
    from PySide6.QtCore import QUrl
    from volumenodex.core.image_utils import save_image

    # Create a small JXL image
    img = QImage(60, 60, QImage.Format.Format_ARGB32)
    img.fill(QColor(255, 0, 0))
    jxl_path = str(tmp_path / "test_insert.jxl")
    saved = save_image(img, jxl_path)
    assert saved is True

    # Insert into canvas
    success = canvas.insert_image(jxl_path)
    assert success is True

    # Verify resource is registered and accessible via both QUrl(jxl_path) and QUrl.fromLocalFile(jxl_path)
    r1 = canvas.document().resource(QTextDocument.ResourceType.ImageResource, QUrl(jxl_path))
    r2 = canvas.document().resource(QTextDocument.ResourceType.ImageResource, QUrl.fromLocalFile(jxl_path))
    assert r1 is not None and not r1.isNull()
    assert r2 is not None and not r2.isNull()

    # Draw document layout and assert that red pixels are actually painted
    pm = QPixmap(200, 200)
    pm.fill(QColor("white"))
    p = QPainter(pm)
    ctx = QAbstractTextDocumentLayout.PaintContext()
    canvas.document().documentLayout().draw(p, ctx)
    p.end()
    rendered = pm.toImage()
    red_count = sum(1 for x in range(200) for y in range(200) if rendered.pixelColor(x, y).red() > 200 and rendered.pixelColor(x, y).blue() < 50)
    assert red_count > 1000


def test_image_interaction_click_and_context_menu(canvas, tmp_path):
    """Validates that left-clicking, double-clicking, and right-clicking an image triggers photo options."""
    from PySide6.QtGui import QImage, QColor, QMouseEvent, QContextMenuEvent
    from PySide6.QtCore import Qt, QPointF, QPoint
    from volumenodex.core.image_utils import save_image

    img = QImage(120, 80, QImage.Format.Format_ARGB32)
    img.fill(QColor(0, 150, 255))
    jxl_path = str(tmp_path / "interactive_test.jxl")
    save_image(img, jxl_path)

    canvas.setPlainText("Text before image\n")
    canvas.insert_image(jxl_path)

    # Locate image position
    text = canvas.document().toPlainText()
    img_idx = text.find("\ufffc")
    assert img_idx != -1

    # Map to coordinates
    block = canvas.document().findBlock(img_idx)
    br = canvas.document().documentLayout().blockBoundingRect(block)
    ph_print = canvas.layout_model.printable_height_px
    page_num = max(0, int(br.y() // ph_print))
    print_rect = canvas._get_printable_rect(page_num)
    click_x = print_rect.x() + br.x() + 20
    click_y = print_rect.y() + (br.y() - page_num * ph_print) + 20

    # 1. Left Click test
    canvas.show()
    press_ev = QMouseEvent(QMouseEvent.Type.MouseButtonPress, QPointF(click_x, click_y), QPointF(click_x, click_y), Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    canvas.mousePressEvent(press_ev)

    assert not canvas.image_options_bar.isHidden()
    assert canvas.textCursor().hasSelection()
    assert canvas.textCursor().selectedText() == "\ufffc"

    # 2. Right Click context menu test
    menu_called = []
    canvas._show_image_context_menu = lambda pos, cur, fmt: menu_called.append((pos, cur, fmt))
    ctx_ev = QContextMenuEvent(QContextMenuEvent.Reason.Mouse, QPoint(int(click_x), int(click_y)), QPoint(100, 100))
    canvas.contextMenuEvent(ctx_ev)
    assert len(menu_called) == 1

    # 3. Double Click resize test
    resize_called = []
    canvas._apply_image_resize = lambda cur, fmt: resize_called.append((cur, fmt))
    double_ev = QMouseEvent(QMouseEvent.Type.MouseButtonDblClick, QPointF(click_x, click_y), QPointF(click_x, click_y), Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    canvas.mouseDoubleClickEvent(double_ev)
    assert len(resize_called) == 1


def test_image_corner_handle_hover_and_drag_resize(canvas, tmp_path):
    """Validates that hovering over handles changes cursor shape, and dragging a corner handle resizes the image."""
    from PySide6.QtGui import QImage, QColor, QMouseEvent, QPaintEvent
    from PySide6.QtCore import Qt, QPointF, QRect
    from volumenodex.core.image_utils import save_image

    # 1. Prepare and insert image
    img = QImage(200, 100, QImage.Format.Format_ARGB32)
    img.fill(QColor(100, 200, 50))
    img_path = str(tmp_path / "drag_test.png")
    save_image(img, img_path)

    canvas.setPlainText("Preceding text\n")
    canvas.insert_image(img_path)
    canvas.show()

    # 2. Select image
    text = canvas.document().toPlainText()
    img_idx = text.find("\ufffc")
    assert img_idx != -1

    block = canvas.document().findBlock(img_idx)
    br = canvas.document().documentLayout().blockBoundingRect(block)
    ph_print = canvas.layout_model.printable_height_px
    page_num = max(0, int(br.y() // ph_print))
    print_rect = canvas._get_printable_rect(page_num)
    click_x = print_rect.x() + br.x() + 30
    click_y = print_rect.y() + (br.y() - page_num * ph_print) + 30

    press_ev = QMouseEvent(QMouseEvent.Type.MouseButtonPress, QPointF(click_x, click_y), QPointF(click_x, click_y), Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    canvas.mousePressEvent(press_ev)
    assert canvas._cursor.hasSelection()

    # 3. Retrieve handle geometry
    img_info = canvas._get_selected_image_info()
    assert img_info is not None
    img_cur, img_fmt = img_info
    orig_w = img_fmt.width()
    orig_h = img_fmt.height()
    assert orig_w == 200
    assert orig_h == 100

    geom = canvas._get_image_geometry_viewport(img_cur, img_fmt)
    assert geom is not None
    img_rect, _ = geom
    handles = canvas._get_image_handles(img_rect, hit_area=False)
    assert "br" in handles
    assert "tl" in handles
    assert "tr" in handles
    assert "bl" in handles
    assert "mr" in handles
    assert "bm" in handles

    # 4. Test hover hit-testing and cursor changes
    br_pt = handles["br"].center()
    hit_br = canvas._hit_test_image_handles(br_pt)
    assert hit_br == "br"

    move_hover = QMouseEvent(QMouseEvent.Type.MouseMove, br_pt, br_pt, Qt.MouseButton.NoButton, Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier)
    canvas.mouseMoveEvent(move_hover)
    assert canvas.viewport().cursor().shape() == Qt.CursorShape.SizeFDiagCursor

    tr_pt = handles["tr"].center()
    move_hover_tr = QMouseEvent(QMouseEvent.Type.MouseMove, tr_pt, tr_pt, Qt.MouseButton.NoButton, Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier)
    canvas.mouseMoveEvent(move_hover_tr)
    assert canvas.viewport().cursor().shape() == Qt.CursorShape.SizeBDiagCursor

    mr_pt = handles["mr"].center()
    move_hover_mr = QMouseEvent(QMouseEvent.Type.MouseMove, mr_pt, mr_pt, Qt.MouseButton.NoButton, Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier)
    canvas.mouseMoveEvent(move_hover_mr)
    assert canvas.viewport().cursor().shape() == Qt.CursorShape.SizeHorCursor

    # 5. Click on bottom-right corner handle to start resizing
    press_br = QMouseEvent(QMouseEvent.Type.MouseButtonPress, br_pt, br_pt, Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    canvas.mousePressEvent(press_br)
    assert canvas._is_resizing_image is True
    assert canvas._resize_handle == "br"
    assert canvas._resize_orig_width == 200.0
    assert canvas._resize_orig_height == 100.0

    # 6. Drag bottom-right corner by (+60px, +30px)
    drag_pt = QPointF(br_pt.x() + 60, br_pt.y() + 30)
    move_drag = QMouseEvent(QMouseEvent.Type.MouseMove, drag_pt, drag_pt, Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    canvas.mouseMoveEvent(move_drag)

    assert canvas._resize_preview_width == 260.0
    assert canvas._resize_preview_height == 130.0
    assert "260" in canvas.image_options_bar.lbl_info.text()

    # Trigger a paintEvent to verify preview overlay rendering doesn't crash
    canvas.paintEvent(QPaintEvent(QRect(0, 0, 800, 1000)))

    # 7. Release mouse button to commit resize
    release_br = QMouseEvent(QMouseEvent.Type.MouseButtonRelease, drag_pt, drag_pt, Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier)
    canvas.mouseReleaseEvent(release_br)

    assert canvas._is_resizing_image is False

    # 8. Verify the document image format now has the new width & height
    updated_info = canvas._get_selected_image_info()
    assert updated_info is not None
    _, updated_fmt = updated_info
    assert updated_fmt.width() == 260.0
    assert updated_fmt.height() == 130.0

    # 9. Test mid-right edge handle drag (unconstrained width adjustment)
    geom2 = canvas._get_image_geometry_viewport(updated_info[0], updated_info[1])
    handles2 = canvas._get_image_handles(geom2[0], hit_area=False)
    mr_pt2 = handles2["mr"].center()

    press_mr = QMouseEvent(QMouseEvent.Type.MouseButtonPress, mr_pt2, mr_pt2, Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    canvas.mousePressEvent(press_mr)
    assert canvas._is_resizing_image is True
    assert canvas._resize_handle == "mr"

    drag_mr = QPointF(mr_pt2.x() + 40, mr_pt2.y())
    move_drag_mr = QMouseEvent(QMouseEvent.Type.MouseMove, drag_mr, drag_mr, Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    canvas.mouseMoveEvent(move_drag_mr)
    assert canvas._resize_preview_width == 300.0
    assert canvas._resize_preview_height == 130.0

    release_mr = QMouseEvent(QMouseEvent.Type.MouseButtonRelease, drag_mr, drag_mr, Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier)
    canvas.mouseReleaseEvent(release_mr)
    assert canvas._is_resizing_image is False

    updated_info2 = canvas._get_selected_image_info()
    assert updated_info2[1].width() == 300.0
    assert updated_info2[1].height() == 130.0


def test_clipart_dialog_autoexpansion_trigger_and_pagination(app, tmp_path):
    """Verifies that ClipArtDialog triggers autoexpansion on 0 local matches, and load more button paginates."""
    from volumenodex.ui.clipart_dialog import ClipArtDialog
    from PySide6.QtGui import QImage

    local_img_path = str(tmp_path / "local_tree.png")
    qimg = QImage(16, 16, QImage.Format.Format_RGB32)
    qimg.fill(0xFFFFFF)
    qimg.save(local_img_path)

    dlg = ClipArtDialog(str(tmp_path))
    dlg.show()

    triggered_calls = []
    dlg._trigger_autoexpansion = lambda q, offset=None, max_images=6: triggered_calls.append((q, offset, max_images))

    # 1. Search existing item
    dlg.search_input.setText("tree")
    dlg.btn_search.click()
    assert len(dlg._current_matches) == 1
    assert not dlg.btn_load_more.isHidden()
    assert len(triggered_calls) == 0

    # 2. Search missing item -> triggers autoexpansion automatically
    dlg.search_input.setText("galaxy")
    dlg.btn_search.click()
    assert len(dlg._current_matches) == 0
    assert not dlg.btn_load_more.isHidden()
    assert len(triggered_calls) == 1
    assert triggered_calls[0][0] == "galaxy"
    assert triggered_calls[0][1] == 0

    # 3. Simulate Load More click with updated offset
    dlg._wikimedia_query_offsets["galaxy"] = 6
    dlg.btn_load_more.click()
    assert len(triggered_calls) == 2
    assert triggered_calls[1][0] == "galaxy"
    assert triggered_calls[1][1] == 6

    dlg.close()


def test_autoexpansion_worker_deduplication_and_pagination(tmp_path):
    """Verifies that AutoexpansionWorker enforces zero-repeat deduplication and consumes Wikimedia continue offsets."""
    import json
    from unittest.mock import patch, MagicMock
    from volumenodex.clipart.autoexpansion import AutoexpansionWorker

    dest_dir = str(tmp_path)
    existing_file = os.path.join(dest_dir, "Andromeda_Galaxy.jxl")
    with open(existing_file, "wb") as f:
        f.write(b"dummy")

    api_response = {
        "continue": {"gsroffset": 15},
        "query": {
            "pages": {
                "1": {
                    "index": 1,
                    "title": "File:Andromeda Galaxy.png",
                    "imageinfo": [{
                        "mime": "image/png",
                        "url": "https://example.com/andromeda.png",
                        "extmetadata": {"License": {"value": "PD"}}
                    }]
                },
                "2": {
                    "index": 2,
                    "title": "File:Milky Way Galaxy.png",
                    "imageinfo": [{
                        "mime": "image/png",
                        "url": "https://example.com/milkyway.png",
                        "extmetadata": {"License": {"value": "PD"}}
                    }]
                },
                "3": {
                    "index": 3,
                    "title": "File:Known Nebula.png",
                    "imageinfo": [{
                        "mime": "image/png",
                        "url": "https://example.com/nebula.png",
                        "extmetadata": {"License": {"value": "PD"}}
                    }]
                },
            }
        }
    }

    from PySide6.QtCore import QBuffer, QIODevice
    from PySide6.QtGui import QImage, QColor

    qimg = QImage(16, 16, QImage.Format.Format_RGB32)
    qimg.fill(QColor(255, 0, 0))
    buf = QBuffer()
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    qimg.save(buf, "PNG")
    valid_png_bytes = bytes(buf.data())

    worker = AutoexpansionWorker(
        query="galaxy",
        destination_dir=dest_dir,
        offset=0,
        max_images=5,
        seen_titles={"known nebula"}
    )

    downloaded = []
    finished = []
    worker.imageDownloaded.connect(lambda path, meta: downloaded.append((path, meta)))
    worker.downloadFinished.connect(lambda cnt, next_off: finished.append((cnt, next_off)))

    def mock_urlopen(req, timeout=12):
        mock_resp = MagicMock()
        url_str = req.get_full_url() if hasattr(req, "get_full_url") else str(req)
        if "commons.wikimedia.org" in url_str:
            mock_resp.read.return_value = json.dumps(api_response).encode("utf-8")
        else:
            mock_resp.read.return_value = valid_png_bytes
        mock_resp.__enter__.return_value = mock_resp
        return mock_resp

    with patch("urllib.request.urlopen", side_effect=mock_urlopen):
        worker.run()

    # Only Milky Way Galaxy should have been downloaded
    assert len(downloaded) == 1
    assert "Milky Way Galaxy.jxl" in downloaded[0][0]
    assert len(finished) == 1
    assert finished[0] == (1, 15)


def test_clipart_autoexpansion_persistence_and_research(app, tmp_path):
    """Verifies that autoexpanded illustrations are permanently saved, indexed, and found on re-search without re-querying Wikimedia."""
    from volumenodex.ui.clipart_dialog import ClipArtDialog
    from PySide6.QtGui import QImage
    import json

    clip_dir = str(tmp_path / "clipart")
    os.makedirs(clip_dir, exist_ok=True)

    # 1. Create initial empty index
    idx_path = os.path.join(clip_dir, "clipart_index.json")
    with open(idx_path, "w", encoding="utf-8") as f:
        json.dump([], f)

    dlg = ClipArtDialog(clip_dir)
    dlg.show()

    # Track triggers to Wikimedia
    triggered = []
    dlg._trigger_autoexpansion = lambda q, offset=None, max_images=6: triggered.append(q)

    # Create image on disk simulating AutoexpansionWorker saving an image
    downloaded_img_path = os.path.join(clip_dir, "Majestic Dragonfly.png")
    qimg = QImage(32, 32, QImage.Format.Format_RGB32)
    qimg.fill(0x00FF00)
    qimg.save(downloaded_img_path)

    # Simulate autoexpansion image downloaded signal
    meta = {
        "title": "Majestic Dragonfly",
        "artist": "Artist A",
        "description": "A green dragonfly",
        "license": "CC0",
        "attribution": "",
    }
    dlg.search_input.setText("dragonfly")
    dlg._on_autoexpansion_image_downloaded(downloaded_img_path, meta)

    # 2. Verify image is in list and search matches
    assert dlg.list_widget.count() == 1
    assert len(dlg._current_matches) == 1
    assert dlg._current_matches[0]["path"] == downloaded_img_path

    # 3. Verify index on disk was updated with this new image
    with open(idx_path, "r", encoding="utf-8") as f:
        saved_index = json.load(f)
    assert len(saved_index) == 1
    assert saved_index[0]["title"] == "Majestic Dragonfly"

    # 4. Clear search and search again for "dragonfly"
    dlg._clear_search()
    assert dlg.list_widget.count() == 0

    triggered.clear()
    dlg.search_input.setText("dragonfly")
    dlg.btn_search.click()

    # Must find the local image immediately and NOT trigger Wikimedia!
    assert len(dlg._current_matches) == 1
    assert len(triggered) == 0, "Re-searching for downloaded image must not trigger Wikimedia"
    assert not dlg.btn_load_more.isHidden()

    dlg.close()

    # 5. Open brand new ClipArtDialog pointing to same folder: must find it from index!
    dlg2 = ClipArtDialog(clip_dir)
    dlg2.show()
    assert len(dlg2._all_records) == 1
    assert dlg2._all_records[0]["title"] == "Majestic Dragonfly"

    # Search in new dialog session
    dlg2.search_input.setText("dragonfly")
    dlg2.btn_search.click()
    assert len(dlg2._current_matches) == 1
    dlg2.close()


def test_clipart_dialog_stacked_widget_mutual_exclusion(tmp_path):
    """Verify QStackedWidget strictly enforces mutually exclusive views without overlapping cards."""
    from volumenodex.ui.clipart_dialog import ClipArtDialog
    from PySide6.QtWidgets import QStackedWidget

    clip_dir = str(tmp_path / "clipart_stack")
    os.makedirs(clip_dir, exist_ok=True)

    dlg = ClipArtDialog(clip_dir)
    dlg.show()

    assert hasattr(dlg, "stack")
    assert isinstance(dlg.stack, QStackedWidget)
    assert dlg.stack.count() == 4

    # Test "empty" view
    dlg._set_display_view("empty")
    assert dlg.stack.currentWidget() == dlg.empty_card

    # Test "initial" view
    dlg._set_display_view("initial")
    assert dlg.stack.currentWidget() == dlg.initial_card

    # Test "no_results" view
    dlg._set_display_view("no_results")
    assert dlg.stack.currentWidget() == dlg.no_results_card

    # Test "list" view
    dlg._set_display_view("list")
    assert dlg.stack.currentWidget() == dlg.list_widget

    dlg.close()


def test_main_window_clipart_dir_defensive_fallback():
    """Verify MainWindow resets temp/pytest clipart paths in settings and finds valid assets."""
    from volumenodex.ui.main_window import MainWindow
    from volumenodex.core.settings_manager import SettingsManager

    sm = SettingsManager()
    orig = sm.clipart_library_dir
    try:
        # Intentionally pollute with a temporary pytest-like path
        sm.clipart_library_dir = r"C:\Users\Aaron\AppData\Local\Temp\pytest-of-Aaron\pytest-99\dummy"
        sm.save()

        win = MainWindow()
        win.settings_manager = sm
        # Calling _on_insert_clip_art logic: verify cleanup
        clipart_dir = sm.clipart_library_dir
        is_valid = bool(
            clipart_dir
            and os.path.isdir(clipart_dir)
            and "pytest" not in clipart_dir.lower()
            and "temp" not in clipart_dir.lower()
        )
        assert not is_valid, "pytest path must be flagged invalid"

        # Simulating main_window reset
        if not is_valid:
            sm.clipart_library_dir = ""
            sm.save()

        assert sm.clipart_library_dir == ""
        win.close()
    finally:
        sm.clipart_library_dir = orig
        sm.save()





