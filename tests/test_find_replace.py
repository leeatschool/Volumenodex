"""Comprehensive test suite for Volumenodex Find & Replace Suite:
- FindReplaceBar HUD overlay initialization, visibility, docking
- Case sensitive, whole word, and regular expression searching
- Match counting, cursor proximity selection, and invalid regex handling
- Directional cycling forward (find_next) and backward (find_prev)
- Canvas search highlight rendering and clearing
- Single replace and atomic batch Replace All
- Single-step undo for batch Replace All
- Shortcut triggers and Ribbon signal integration
"""

import sys
import os

from PySide6.QtCore import Qt, QEvent
from PySide6.QtGui import QKeyEvent, QTextCursor
from PySide6.QtWidgets import QApplication

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from volumenodex.ui.main_window import MainWindow
from volumenodex.canvas.paginated_canvas import PaginatedCanvas
from volumenodex.ui.find_replace_bar import FindReplaceBar


def test_find_replace_bar_initialization(app):
    win = MainWindow()
    win.show()
    canvas = win.canvas_area
    bar = canvas.find_replace_bar

    assert bar is not None
    assert isinstance(bar, FindReplaceBar)
    assert not bar.isVisible()
    assert not bar.replace_mode

    # Showing find mode
    canvas.show_find(replace_mode=False)
    assert bar.isVisible()
    assert not bar.replace_mode
    assert not bar.replace_widget.isVisible()

    # Showing replace mode
    canvas.show_find(replace_mode=True)
    assert bar.isVisible()
    assert bar.replace_mode
    assert bar.replace_widget.isVisible()

    # Closing find bar
    bar.close_bar()
    assert not bar.isVisible()
    assert len(canvas._search_matches) == 0

    win.close()


def test_search_matching_and_toggles(app):
    win = MainWindow()
    canvas = win.canvas_area
    bar = canvas.find_replace_bar

    text_sample = "The quick brown fox jumps over the lazy dog. The fox is quick and the Fox is clever."
    canvas.setPlainText(text_sample)

    # 1. Default case-insensitive search for "fox"
    bar.show_find(replace_mode=False)
    bar.input_search.setText("fox")
    bar.run_search()

    assert len(bar.matches) == 3
    assert bar.lbl_count.text() == "1 of 3"
    assert len(canvas._search_matches) == 3

    # 2. Case-sensitive search ("fox" should match 2 occurrences, ignoring "Fox")
    bar.btn_case.setChecked(True)
    bar.run_search()
    assert len(bar.matches) == 2
    assert bar.lbl_count.text() == "1 of 2"

    # Reset case
    bar.btn_case.setChecked(False)

    # 3. Whole word search ("quick" vs "quickly")
    canvas.setPlainText("He is quick. She moves quickly.")
    bar.input_search.setText("quick")
    bar.btn_word.setChecked(False)
    bar.run_search()
    assert len(bar.matches) == 2

    bar.btn_word.setChecked(True)
    bar.run_search()
    assert len(bar.matches) == 1
    bar.btn_word.setChecked(False)

    # 4. Regular expression search
    canvas.setPlainText("Chapter 1: The Beginning\nChapter 2: The Middle\nChapter 10: The End")
    bar.btn_regex.setChecked(True)
    bar.input_search.setText(r"Chapter \d+")
    bar.run_search()
    assert len(bar.matches) == 3
    assert bar.lbl_count.text() == "1 of 3"

    # 5. Invalid regex handling
    bar.input_search.setText(r"Chapter [0-9")
    bar.run_search()
    assert len(bar.matches) == 0
    assert bar.lbl_count.text() == "Invalid Regex"

    bar.btn_regex.setChecked(False)
    win.close()


def test_navigation_cycling(app):
    win = MainWindow()
    canvas = win.canvas_area
    bar = canvas.find_replace_bar

    canvas.setPlainText("alpha beta alpha gamma alpha delta")
    bar.show_find(replace_mode=False)
    bar.input_search.setText("alpha")
    bar.run_search()

    assert len(bar.matches) == 3
    assert bar.current_match_idx == 0
    assert bar.lbl_count.text() == "1 of 3"

    # Forward navigation
    bar.find_next()
    assert bar.current_match_idx == 1
    assert bar.lbl_count.text() == "2 of 3"

    bar.find_next()
    assert bar.current_match_idx == 2
    assert bar.lbl_count.text() == "3 of 3"

    # Forward wrap-around
    bar.find_next()
    assert bar.current_match_idx == 0
    assert bar.lbl_count.text() == "1 of 3"

    # Backward wrap-around
    bar.find_prev()
    assert bar.current_match_idx == 2
    assert bar.lbl_count.text() == "3 of 3"

    bar.find_prev()
    assert bar.current_match_idx == 1
    assert bar.lbl_count.text() == "2 of 3"

    win.close()


def test_single_replace_and_advance(app):
    win = MainWindow()
    canvas = win.canvas_area
    bar = canvas.find_replace_bar

    canvas.setPlainText("apple banana apple cherry apple")
    bar.show_find(replace_mode=True)
    bar.input_search.setText("apple")
    bar.input_replace.setText("orange")
    bar.run_search()

    assert len(bar.matches) == 3
    assert bar.current_match_idx == 0

    # Replace the first apple
    bar.replace_current()
    assert "orange banana apple cherry apple" in canvas.toPlainText()
    assert len(bar.matches) == 2
    assert "Replaced" in bar.lbl_replace_status.text()

    win.close()


def test_atomic_replace_all_with_undo(app):
    win = MainWindow()
    canvas = win.canvas_area
    bar = canvas.find_replace_bar

    original = "The stone was cold. Every stone told a story. Another stone fell."
    canvas.setPlainText(original)
    bar.show_find(replace_mode=True)
    bar.input_search.setText("stone")
    bar.input_replace.setText("gem")
    bar.run_search()

    assert len(bar.matches) == 3

    # Batch replace all
    bar.replace_all()
    replaced_text = canvas.toPlainText()
    assert replaced_text == "The gem was cold. Every gem told a story. Another gem fell."
    assert "Replaced 3 occurrences" in bar.lbl_replace_status.text()

    # Single-step Undo test
    canvas.undo()
    assert canvas.toPlainText() == original

    # Redo test
    canvas.redo()
    assert canvas.toPlainText() == replaced_text

    win.close()


def test_selection_prefill_and_shortcuts(app):
    win = MainWindow()
    canvas = win.canvas_area
    bar = canvas.find_replace_bar

    canvas.setPlainText("Whispers in the dark forest.")
    # Select 'forest'
    cursor = canvas.textCursor()
    cursor.setPosition(21)
    cursor.setPosition(27, QTextCursor.MoveMode.KeepAnchor)
    canvas.setTextCursor(cursor)
    assert canvas.cursor.selectedText() == "forest"

    # Trigger show_find -> prefill should be 'forest'
    canvas.show_find(replace_mode=False)
    assert bar.input_search.text() == "forest"
    assert len(bar.matches) == 1
    assert bar.lbl_count.text() == "1 of 1"

    # Test escape key closes bar
    event_esc = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier)
    bar.keyPressEvent(event_esc)
    assert not bar.isVisible()

    win.close()


def test_ribbon_signals_open_hud(app):
    win = MainWindow()
    win.show()
    canvas = win.canvas_area
    bar = canvas.find_replace_bar

    assert not bar.isVisible()

    # Home tab Find button click
    win.ribbon.btn_find.click()
    assert bar.isVisible()
    assert not bar.replace_mode

    bar.close_bar()
    assert not bar.isVisible()

    # Home tab Replace button click
    win.ribbon.btn_replace.click()
    assert bar.isVisible()
    assert bar.replace_mode

    win.close()


if __name__ == "__main__":
    test_app = QApplication.instance() or QApplication(sys.argv)
    tests = [
        test_find_replace_bar_initialization,
        test_search_matching_and_toggles,
        test_navigation_cycling,
        test_single_replace_and_advance,
        test_atomic_replace_all_with_undo,
        test_selection_prefill_and_shortcuts,
        test_ribbon_signals_open_hud,
    ]

    passed = 0
    failed = 0
    print("==================================================")
    print("Running Volumenodex Find & Replace Suite Tests...")
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
