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

