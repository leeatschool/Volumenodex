"""Comprehensive test suite for:
1. Removal of automatic H1 titles from new documents, startup manuscripts, and templates.
2. Save-on-close prompts, modified status tracking, and close event cancellation/discard/save.
3. Variable background automatic saving (interval configuration, timer, draft recovery vault).
4. Studio Settings dialog and Settings menu bar integration.
5. Header Save button and header settings/autosave controls in the Ribbon.
"""

import os
import sys
import tempfile
import pytest

from PySide6.QtCore import Qt, QSettings
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QApplication, QMessageBox

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from volumenodex.ui.main_window import MainWindow
from volumenodex.core.settings_manager import SettingsManager
from volumenodex.ui.settings_dialog import SettingsDialog
from volumenodex.core.document_model import DocumentMode


def test_no_automatic_title_on_startup(app):
    """Verify that launching the studio starts with an empty canvas without an injected H1 title."""
    win = MainWindow()
    win.show()

    # The editor text should be completely clean
    text = win.editor.toPlainText().strip()
    assert text == "", f"Expected clean empty document on launch, got: {text!r}"
    assert "Untitled Document" not in win.editor.document().toHtml()
    assert not win.editor.document().isModified(), "New document should not start in modified state"
    win.close()


def test_no_automatic_title_in_templates():
    """Verify mode templates do not inject an automatic <h1> title at the top."""
    win = MainWindow()
    acad_html = win._generate_mode_template("Academic Paper", DocumentMode.ACADEMIC)
    assert "<h1>" not in acad_html, "Academic template should not have an automatic H1 title"
    assert "Author Name" in acad_html

    nf_html = win._generate_mode_template("Non-Fiction Book", DocumentMode.NON_FICTION)
    assert "<h1>" not in nf_html, "Non-fiction template should not have an automatic H1 title"

    fiction_html = win._generate_mode_template("Fiction Novel", DocumentMode.CREATIVE_FICTION)
    assert "<h1>" not in fiction_html, "Fiction template should not have an automatic H1 title"
    assert "Chapter One: The Salt and the Stars" in fiction_html


def test_header_save_button_present_and_connected(app):
    """Verify Ribbon header contains the Quick Access Save button and connects to save_document."""
    win = MainWindow()
    win.show()

    assert hasattr(win.ribbon, "btn_header_save"), "Ribbon must have btn_header_save"
    assert win.ribbon.btn_header_save is not None
    assert win.ribbon.btn_header_save.text() == "Save"
    assert "Save Document" in win.ribbon.btn_header_save.toolTip()

    # Verify corner widget placement
    corner_widget = win.ribbon.tab_widget.cornerWidget(Qt.Corner.TopLeftCorner)
    assert corner_widget is not None

    # Track saveRequested signal
    saved_called = []
    win.save_document = lambda: saved_called.append(True) or True
    win.ribbon.btn_header_save.click()
    assert len(saved_called) == 1, "Clicking header Save button should trigger save_document"
    win.close()


def test_save_on_close_prompt_unmodified(app):
    """Verify closing an unmodified document accepts closeEvent immediately without prompt."""
    win = MainWindow()
    win.show()
    assert not win.editor.document().isModified()

    ev = QCloseEvent()
    win.closeEvent(ev)
    assert ev.isAccepted(), "Unmodified document should close without prompt"


def test_save_on_close_prompt_cancel(app):
    """Verify that canceling the save prompt rejects the close event and keeps document open."""
    win = MainWindow()
    win.show()

    # Modify document
    win.editor.setPlainText("Important unsaved chapter prose")
    assert win.editor.document().isModified()

    # Simulate user clicking Cancel
    win._test_save_prompt_response = QMessageBox.StandardButton.Cancel
    ev = QCloseEvent()
    win.closeEvent(ev)
    assert not ev.isAccepted(), "Canceling save prompt must reject the close event"


def test_save_on_close_prompt_discard(app):
    """Verify that choosing Discard accepts the close event and closes document without saving."""
    win = MainWindow()
    win.show()

    win.editor.setPlainText("Draft to be discarded")
    assert win.editor.document().isModified()

    win._test_save_prompt_response = QMessageBox.StandardButton.Discard
    ev = QCloseEvent()
    win.closeEvent(ev)
    assert ev.isAccepted(), "Discarding unsaved changes must accept the close event"


def test_save_on_close_prompt_save_success(app):
    """Verify that choosing Save invokes save_document and accepts close if save succeeds."""
    win = MainWindow()
    win.show()

    win.editor.setPlainText("Manuscript to be saved")
    assert win.editor.document().isModified()

    save_called = []
    def mock_save():
        save_called.append(True)
        win.editor.document().setModified(False)
        return True

    win.save_document = mock_save
    win._test_save_prompt_response = QMessageBox.StandardButton.Save

    ev = QCloseEvent()
    win.closeEvent(ev)
    assert len(save_called) == 1, "Save button should call save_document"
    assert ev.isAccepted(), "Successful save should allow close event to be accepted"


def test_modification_title_star(app):
    """Verify window title dynamically reflects unsaved status with an asterisk."""
    win = MainWindow()
    win.show()

    assert not win.editor.document().isModified()
    assert "*" not in win.windowTitle()

    # Make a change
    win.editor.setPlainText("Typing some text...")
    assert win.editor.document().isModified()
    assert "*" in win.windowTitle(), f"Title should have asterisk when modified: {win.windowTitle()}"

    # Reset modified
    win.editor.document().setModified(False)
    assert "*" not in win.windowTitle(), f"Title should not have asterisk when clean: {win.windowTitle()}"
    win.close()


def test_settings_manager_and_variable_autosave():
    """Verify SettingsManager handles intervals, enabled states, and persistence."""
    sm = SettingsManager()
    sm.set_autosave(enabled=True, interval_minutes=5)
    assert sm.autosave_enabled is True
    assert sm.autosave_interval_minutes == 5
    assert sm.get_autosave_label() == "Auto-Save: 5m"

    sm.set_autosave(enabled=False, interval_minutes=5)
    assert sm.get_autosave_label() == "Auto-Save: Off"

    # Reset back to enabled default
    sm.set_autosave(enabled=True, interval_minutes=2)


def test_settings_menu_bar_integration(app):
    """Verify the Settings menu in menuBar contains variable autosave intervals and preferences action."""
    win = MainWindow()
    win.show()

    menu_bar = win.menuBar()
    settings_menu = None
    for action in menu_bar.actions():
        if "Settings" in action.text():
            settings_menu = action.menu()
            break

    assert settings_menu is not None, "Settings menu must exist in menu bar"
    assert win.menu_autosave is not None, "Auto-Save submenu must exist in Settings menu"

    # Check interval actions
    assert 1 in win._autosave_interval_actions
    assert 2 in win._autosave_interval_actions
    assert 5 in win._autosave_interval_actions
    assert 10 in win._autosave_interval_actions

    # Triggering interval updates settings
    win._on_menu_autosave_interval_triggered(10)
    assert win.settings_manager.autosave_interval_minutes == 10
    assert win.ribbon.lbl_autosave_badge.text() == "Auto-Save: 10m"
    assert win._autosave_timer.interval() == 10 * 60 * 1000
    win.close()


def test_autosave_timer_with_active_file(app):
    """Verify autosave executes without error when an active file is open."""
    win = MainWindow()
    win.show()

    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tf:
        temp_docx = tf.name

    try:
        win.current_file_path = temp_docx
        win.editor.setPlainText("Autosaved content directly to disk")
        assert win.editor.document().isModified()

        win._on_autosave_timer()

        assert not win.editor.document().isModified(), "Autosave should reset modified state"
        assert "Auto-Saved" in win.ribbon.lbl_autosave_badge.text()
    finally:
        if os.path.exists(temp_docx):
            try:
                os.remove(temp_docx)
            except Exception:
                pass
        win.close()


def test_autosave_draft_recovery_for_untitled(app):
    """Verify untitled documents are safely backed up to recovery vault on autosave."""
    win = MainWindow()
    win.show()

    win.current_file_path = None
    win.editor.setPlainText("Untitled brilliance that must not be lost")
    assert win.editor.document().isModified()

    win._on_autosave_timer()

    recovery_path = os.path.expanduser("~/.volumenodex/autosave/untitled_recovery.docx")
    assert os.path.exists(recovery_path), "Recovery draft file must be written for untitled document"
    assert "Draft Saved" in win.ribbon.lbl_autosave_badge.text()
    win.close()
