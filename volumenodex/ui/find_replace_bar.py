"""Modern Fluent Find & Replace Floating HUD for Volumenodex.

Provides a luxury, floating overlay panel docked cleanly above the paginated
paper canvas with real-time match counting, regex / case matching, instant
directional navigation, and single or atomic batch replacements with undo support.
"""

import re
from typing import List, Tuple, Optional
from PySide6.QtCore import Qt, Signal, QSize, QRect
from PySide6.QtGui import QColor, QFont, QTextCursor
from PySide6.QtWidgets import (
    QFrame, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QToolButton, QLabel, QGraphicsDropShadowEffect
)

from volumenodex.ui.vector_icons import VectorIconFactory


class FindReplaceBar(QFrame):
    """Floating HUD overlay for high-speed manuscript search and replacement."""

    closed = Signal()
    findNextRequested = Signal()
    findPrevRequested = Signal()

    def __init__(self, canvas, parent=None):
        super().__init__(parent or (canvas.viewport() if canvas else None))
        self.canvas = canvas
        self.setObjectName("findReplaceBar")
        self.setFixedWidth(460)
        self.replace_mode = False

        self.matches: List[Tuple[int, int]] = []
        self.current_match_idx: int = -1

        self._init_ui()
        self._apply_styling()

        # Connect document changes so search matches stay in sync during typing
        if self.canvas and self.canvas.document():
            self.canvas.document().contentsChanged.connect(self._on_doc_contents_changed)

    def _init_ui(self) -> None:
        self.root_layout = QVBoxLayout(self)
        self.root_layout.setContentsMargins(10, 8, 10, 8)
        self.root_layout.setSpacing(6)

        # ----------------------------------------------------
        # Row 1: Find Controls
        # ----------------------------------------------------
        self.find_row = QHBoxLayout()
        self.find_row.setContentsMargins(0, 0, 0, 0)
        self.find_row.setSpacing(4)

        # Search Icon
        lbl_search_icon = QLabel(self)
        lbl_search_icon.setPixmap(VectorIconFactory.create_icon("search", "#7aa2f7", 16).pixmap(16, 16))
        self.find_row.addWidget(lbl_search_icon)

        # Search Input
        self.input_search = QLineEdit(self)
        self.input_search.setPlaceholderText("Find in document...")
        self.input_search.setClearButtonEnabled(True)
        self.input_search.textChanged.connect(self._on_search_text_changed)
        self.input_search.returnPressed.connect(self.find_next)
        self.find_row.addWidget(self.input_search, stretch=1)

        # Match Count Badge
        self.lbl_count = QLabel("", self)
        self.lbl_count.setMinimumWidth(55)
        self.lbl_count.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.lbl_count.setStyleSheet("color: #7aa2f7; font-size: 11px; font-weight: 600;")
        self.find_row.addWidget(self.lbl_count)

        # Navigation Buttons (Previous / Next)
        self.btn_prev = self._create_icon_button("arrow_up", "Previous Match (Shift+Enter / Shift+F3)")
        self.btn_prev.clicked.connect(self.find_prev)
        self.find_row.addWidget(self.btn_prev)

        self.btn_next = self._create_icon_button("arrow_down", "Next Match (Enter / F3)")
        self.btn_next.clicked.connect(self.find_next)
        self.find_row.addWidget(self.btn_next)

        # Option Toggles (Case, Whole Word, Regex)
        self.btn_case = self._create_toggle_button("Aa", "Match Case (Alt+C)")
        self.btn_case.toggled.connect(self._on_option_toggled)
        self.find_row.addWidget(self.btn_case)

        self.btn_word = self._create_toggle_button(r"\b", "Match Whole Word (Alt+W)")
        self.btn_word.toggled.connect(self._on_option_toggled)
        self.find_row.addWidget(self.btn_word)

        self.btn_regex = self._create_toggle_button(".*", "Regular Expression (Alt+R)")
        self.btn_regex.toggled.connect(self._on_option_toggled)
        self.find_row.addWidget(self.btn_regex)

        # Replace Drawer Expander
        self.btn_toggle_replace = self._create_icon_button("replace", "Toggle Replace Mode (Ctrl+H)", checkable=True)
        self.btn_toggle_replace.clicked.connect(self.toggle_replace_mode)
        self.find_row.addWidget(self.btn_toggle_replace)

        # Close Button
        self.btn_close = self._create_icon_button("close", "Close (Esc)")
        self.btn_close.clicked.connect(self.close_bar)
        self.find_row.addWidget(self.btn_close)

        self.root_layout.addLayout(self.find_row)

        # ----------------------------------------------------
        # Row 2: Replace Controls (Collapsible)
        # ----------------------------------------------------
        self.replace_widget = QWidget(self)
        self.replace_layout = QHBoxLayout(self.replace_widget)
        self.replace_layout.setContentsMargins(0, 0, 0, 0)
        self.replace_layout.setSpacing(4)

        lbl_rep_icon = QLabel(self.replace_widget)
        lbl_rep_icon.setPixmap(VectorIconFactory.create_icon("replace", "#bb9af7", 16).pixmap(16, 16))
        self.replace_layout.addWidget(lbl_rep_icon)

        # Replace Input
        self.input_replace = QLineEdit(self.replace_widget)
        self.input_replace.setPlaceholderText("Replace with...")
        self.input_replace.setClearButtonEnabled(True)
        self.input_replace.returnPressed.connect(self.replace_current)
        self.replace_layout.addWidget(self.input_replace, stretch=1)

        # Replace Button
        self.btn_replace = QPushButton("Replace", self.replace_widget)
        self.btn_replace.setToolTip("Replace Current Match")
        self.btn_replace.setStyleSheet(self._action_button_style())
        self.btn_replace.clicked.connect(self.replace_current)
        self.replace_layout.addWidget(self.btn_replace)

        # Replace All Button
        self.btn_replace_all = QPushButton("Replace All", self.replace_widget)
        self.btn_replace_all.setToolTip("Replace All Occurrences across Manuscript")
        self.btn_replace_all.setStyleSheet(self._action_button_style())
        self.btn_replace_all.clicked.connect(self.replace_all)
        self.replace_layout.addWidget(self.btn_replace_all)

        # Status Toast Label
        self.lbl_replace_status = QLabel("", self.replace_widget)
        self.lbl_replace_status.setStyleSheet("color: #9ece6a; font-size: 10px; font-weight: 600;")
        self.replace_layout.addWidget(self.lbl_replace_status)

        self.root_layout.addWidget(self.replace_widget)
        self.replace_widget.setVisible(False)

    def _create_icon_button(self, icon_name: str, tooltip: str, checkable: bool = False) -> QToolButton:
        btn = QToolButton(self)
        btn.setIcon(VectorIconFactory.create_icon(icon_name, "#787c99", 16))
        btn.setIconSize(QSize(16, 16))
        btn.setFixedSize(26, 26)
        btn.setToolTip(tooltip)
        btn.setCheckable(checkable)
        btn.setStyleSheet("""
            QToolButton {
                background-color: transparent;
                border: 1px solid transparent;
                border-radius: 4px;
            }
            QToolButton:hover {
                background-color: #24283b;
                border-color: #414868;
            }
            QToolButton:checked {
                background-color: rgba(122, 162, 247, 0.25);
                border-color: #7aa2f7;
            }
        """)
        return btn

    def _create_toggle_button(self, text: str, tooltip: str) -> QToolButton:
        btn = QToolButton(self)
        btn.setText(text)
        btn.setToolTip(tooltip)
        btn.setCheckable(True)
        btn.setFixedSize(26, 26)
        btn.setStyleSheet("""
            QToolButton {
                background-color: #1f2335;
                color: #787c99;
                border: 1px solid #292e42;
                border-radius: 4px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 11px;
                font-weight: 700;
            }
            QToolButton:hover {
                background-color: #24283b;
                color: #c0caf5;
            }
            QToolButton:checked {
                background-color: rgba(122, 162, 247, 0.25);
                color: #7aa2f7;
                border-color: #7aa2f7;
            }
        """)
        return btn

    def _action_button_style(self) -> str:
        return """
            QPushButton {
                background-color: #1f2335;
                color: #c0caf5;
                border: 1px solid #292e42;
                border-radius: 4px;
                padding: 3px 10px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #24283b;
                border-color: #7aa2f7;
                color: #ffffff;
            }
            QPushButton:pressed {
                background-color: #16161e;
            }
        """

    def _apply_styling(self) -> None:
        self.setStyleSheet("""
            #findReplaceBar {
                background-color: #1a1b26;
                border: 1px solid #292e42;
                border-radius: 8px;
            }
            QLineEdit {
                background-color: #16161e;
                color: #c0caf5;
                border: 1px solid #292e42;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 12px;
                selection-background-color: #7aa2f7;
                selection-color: #16161e;
            }
            QLineEdit:focus {
                border-color: #7aa2f7;
            }
        """)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 160))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)

    def set_replace_mode(self, enabled: bool) -> None:
        """Shows or collapses the second-row replace bar."""
        self.replace_mode = enabled
        self.btn_toggle_replace.setChecked(enabled)
        self.replace_widget.setVisible(enabled)
        self.adjustSize()
        if self.canvas:
            self.canvas._reposition_find_bar()

    def toggle_replace_mode(self) -> None:
        self.set_replace_mode(not self.replace_mode)

    def show_find(self, replace_mode: bool = False, prefill: str = "") -> None:
        """Opens or focuses the find bar, optionally enabling replace mode."""
        self.set_replace_mode(replace_mode)
        if prefill:
            self.input_search.setText(prefill)

        self.show()
        self.raise_()

        if replace_mode and prefill:
            self.input_replace.setFocus()
            self.input_replace.selectAll()
        else:
            self.input_search.setFocus()
            self.input_search.selectAll()

        self.run_search(keep_index=False)
        if self.canvas:
            self.canvas._reposition_find_bar()

    def close_bar(self) -> None:
        """Hides the bar, clears highlights, and restores focus to canvas."""
        self.hide()
        if self.canvas:
            self.canvas.clear_search_matches()
            self.canvas.setFocus()
        self.closed.emit()

    def _on_search_text_changed(self) -> None:
        self.lbl_replace_status.setText("")
        self.run_search(keep_index=False)

    def _on_option_toggled(self) -> None:
        self.run_search(keep_index=True)

    def _on_doc_contents_changed(self) -> None:
        """Re-runs search dynamically if text changes while find bar is open."""
        if self.isVisible() and self.input_search.text():
            self.run_search(keep_index=True)

    def run_search(self, keep_index: bool = False) -> None:
        """Executes the search across the manuscript text and highlights matches."""
        query = self.input_search.text()
        if not query or not self.canvas or not self.canvas.document():
            self.matches = []
            self.current_match_idx = -1
            self.lbl_count.setText("")
            if self.canvas:
                self.canvas.clear_search_matches()
            return

        text = self.canvas.document().toPlainText()
        match_case = self.btn_case.isChecked()
        whole_word = self.btn_word.isChecked()
        use_regex = self.btn_regex.isChecked()

        flags = 0 if match_case else re.IGNORECASE

        if use_regex:
            try:
                pattern = re.compile(query, flags)
            except re.error:
                self.matches = []
                self.current_match_idx = -1
                self.lbl_count.setText("Invalid Regex")
                self.lbl_count.setStyleSheet("color: #f7768e; font-size: 10px; font-weight: 600;")
                self.canvas.clear_search_matches()
                return
        else:
            pat_str = re.escape(query)
            if whole_word:
                pat_str = rf"\b{pat_str}\b"
            pattern = re.compile(pat_str, flags)

        self.matches = [(m.start(), m.end()) for m in pattern.finditer(text)]

        if not self.matches:
            self.current_match_idx = -1
            self.lbl_count.setText("No matches")
            self.lbl_count.setStyleSheet("color: #f7768e; font-size: 10px; font-weight: 600;")
            self.canvas.clear_search_matches()
            return

        # Pick match index: closest to current cursor position or preserved
        if not keep_index or self.current_match_idx < 0:
            cursor_pos = self.canvas.cursor.position()
            best_idx = 0
            for idx, (s, e) in enumerate(self.matches):
                if s >= cursor_pos:
                    best_idx = idx
                    break
            self.current_match_idx = best_idx
        else:
            self.current_match_idx = min(max(0, self.current_match_idx), len(self.matches) - 1)

        self._update_ui_for_match(scroll=True)

    def _update_ui_for_match(self, scroll: bool = True) -> None:
        total = len(self.matches)
        if total == 0:
            self.lbl_count.setText("No matches")
            self.lbl_count.setStyleSheet("color: #f7768e; font-size: 10px; font-weight: 600;")
            return

        self.lbl_count.setText(f"{self.current_match_idx + 1} of {total}")
        self.lbl_count.setStyleSheet("color: #7aa2f7; font-size: 10px; font-weight: 600;")

        self.canvas.set_search_matches(self.matches, self.current_match_idx)
        if scroll:
            self.canvas.scroll_to_match(self.current_match_idx)

    def find_next(self) -> None:
        """Cycles forward to the next match."""
        if not self.matches:
            return
        self.current_match_idx = (self.current_match_idx + 1) % len(self.matches)
        self._update_ui_for_match(scroll=True)
        self.findNextRequested.emit()

    def find_prev(self) -> None:
        """Cycles backward to the previous match."""
        if not self.matches:
            return
        self.current_match_idx = (self.current_match_idx - 1 + len(self.matches)) % len(self.matches)
        self._update_ui_for_match(scroll=True)
        self.findPrevRequested.emit()

    def replace_current(self) -> None:
        """Replaces the active match with the replacement string and advances."""
        if not self.matches or self.current_match_idx < 0 or self.current_match_idx >= len(self.matches):
            return

        start_pos, end_pos = self.matches[self.current_match_idx]
        rep_text = self.input_replace.text()

        self.canvas.replace_range(start_pos, end_pos, rep_text)
        self.lbl_replace_status.setText("Replaced")
        self.lbl_replace_status.setStyleSheet("color: #9ece6a; font-size: 10px; font-weight: 600;")

        self.run_search(keep_index=True)

    def replace_all(self) -> None:
        """Batch-replaces all matches in a single atomic undoable block."""
        if not self.matches:
            return

        rep_text = self.input_replace.text()
        count = len(self.matches)

        doc = self.canvas.document()
        cursor = self.canvas.cursor
        cursor.beginEditBlock()
        try:
            # Process in reverse order so character offsets do not drift
            for start_pos, end_pos in reversed(self.matches):
                c = QTextCursor(doc)
                c.setPosition(start_pos)
                c.setPosition(end_pos, QTextCursor.MoveMode.KeepAnchor)
                c.insertText(rep_text)
        finally:
            cursor.endEditBlock()

        self.lbl_replace_status.setText(f"Replaced {count} occurrences")
        self.lbl_replace_status.setStyleSheet("color: #9ece6a; font-size: 10px; font-weight: 600;")

        self.run_search(keep_index=False)
        self.canvas.viewport().update()

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.close_bar()
            event.accept()
            return

        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                self.find_prev()
            else:
                if self.input_replace.hasFocus():
                    self.replace_current()
                else:
                    self.find_next()
            event.accept()
            return

        # Alt shortcuts
        if event.modifiers() & Qt.KeyboardModifier.AltModifier:
            if event.key() == Qt.Key.Key_C:
                self.btn_case.toggle()
                event.accept()
                return
            elif event.key() == Qt.Key.Key_W:
                self.btn_word.toggle()
                event.accept()
                return
            elif event.key() == Qt.Key.Key_R:
                self.btn_regex.toggle()
                event.accept()
                return

        super().keyPressEvent(event)
