"""Drag and Droppable Screenplay Terms & Phrases Palette Drawer.

Provides a categorized push panel with preloaded industry-standard screenplay terms
(Headings, Light Direction, Setting Notes, Stage Directions, Prop Directions, Acts & Scenes)
and custom user notes for instant drag-and-drop or single-click insertion.
"""

from typing import Optional, List, Dict
from PySide6.QtCore import Qt, Signal, QSize, QPoint, QMimeData
from PySide6.QtGui import (
    QColor, QDrag, QPixmap, QPainter, QFont, QPen, QAction
)
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QToolButton, QScrollArea, QFrame, QLineEdit, QComboBox,
    QStackedWidget, QTextEdit, QDialog, QMessageBox, QMenu
)

from volumenodex.ui.vector_icons import VectorIconFactory
from volumenodex.screenplay.screenplay_model import (
    ScreenplayPhrase, ScreenplayPhraseLibrary
)


class CustomPhraseDialog(QDialog):
    """Modal dialog to create or edit a custom reusable screenplay term/phrase."""

    def __init__(self, library: ScreenplayPhraseLibrary, existing_phrase: Optional[ScreenplayPhrase] = None, parent=None):
        super().__init__(parent)
        self.library = library
        self.existing_phrase = existing_phrase

        self.setWindowTitle("Edit Custom Phrase" if existing_phrase else "New Custom Screenplay Term / Note")
        self.setFixedWidth(440)
        self.setStyleSheet("""
            QDialog {
                background-color: #1a1b26;
                color: #c0caf5;
            }
            QLabel {
                color: #9aa5ce;
                font-size: 11px;
                font-weight: 600;
            }
            QLineEdit, QTextEdit, QComboBox {
                background-color: #16161e;
                color: #c0caf5;
                border: 1px solid #292e42;
                border-radius: 5px;
                padding: 5px 8px;
                font-size: 12px;
            }
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus {
                border-color: #7aa2f7;
            }
            QPushButton {
                border-radius: 5px;
                padding: 6px 14px;
                font-size: 11px;
                font-weight: 600;
            }
        """)

        self._init_ui()
        if existing_phrase:
            self._load_existing()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)

        title_lbl = QLabel(self.windowTitle())
        title_lbl.setStyleSheet("color: #7aa2f7; font-size: 13px; font-weight: 700;")
        layout.addWidget(title_lbl)

        # Category & Subcategory
        h_cat = QHBoxLayout()
        v_c = QVBoxLayout()
        v_c.addWidget(QLabel("Category:"))
        self.combo_cat = QComboBox(self)
        for c in self.library.get_categories():
            self.combo_cat.addItem(c)
        v_c.addWidget(self.combo_cat)
        h_cat.addLayout(v_c)

        v_sub = QVBoxLayout()
        v_sub.addWidget(QLabel("Subcategory / Tag:"))
        self.txt_sub = QLineEdit(self)
        self.txt_sub.setPlaceholderText("e.g. Night, Interiors, Action")
        v_sub.addWidget(self.txt_sub)
        h_cat.addLayout(v_sub)
        layout.addLayout(h_cat)

        # Display Title
        layout.addWidget(QLabel("Display Label / Title:"))
        self.txt_title = QLineEdit(self)
        self.txt_title.setPlaceholderText("e.g. EXTERIOR: ROOFTOP HELIPAD - NIGHT")
        layout.addWidget(self.txt_title)

        # Script Text Snippet to Insert
        layout.addWidget(QLabel("Script Text to Insert (Drag or Click):"))
        self.txt_content = QTextEdit(self)
        self.txt_content.setFixedHeight(90)
        self.txt_content.setPlaceholderText("Exact formatted text to insert into screenplay manuscript...")
        layout.addWidget(self.txt_content)

        # Description / Usage Note
        layout.addWidget(QLabel("Context Note / Tooltip (optional):"))
        self.txt_desc = QLineEdit(self)
        self.txt_desc.setPlaceholderText("e.g. Climax sequence lighting; heavy wind machine and rain")
        layout.addWidget(self.txt_desc)

        # Buttons
        h_btn = QHBoxLayout()
        h_btn.addStretch()

        btn_cancel = QPushButton("Cancel", self)
        btn_cancel.setStyleSheet("background-color: #24283b; color: #a9b1d6;")
        btn_cancel.clicked.connect(self.reject)
        h_btn.addWidget(btn_cancel)

        btn_save = QPushButton("Save Phrase", self)
        btn_save.setStyleSheet("background-color: #7aa2f7; color: #15161e; font-weight: 700;")
        btn_save.clicked.connect(self._save)
        h_btn.addWidget(btn_save)

        layout.addLayout(h_btn)

    def _load_existing(self) -> None:
        p = self.existing_phrase
        idx = self.combo_cat.findText(p.category)
        if idx >= 0:
            self.combo_cat.setCurrentIndex(idx)
        self.txt_sub.setText(p.subcategory)
        self.txt_title.setText(p.title)
        self.txt_content.setPlainText(p.text)
        self.txt_desc.setText(p.description)

    def _save(self) -> None:
        title = self.txt_title.text().strip()
        text = self.txt_content.toPlainText()
        if not title or not text.strip():
            QMessageBox.warning(self, "Validation", "Please provide a title and script text snippet.")
            return

        cat = self.combo_cat.currentText()
        sub = self.txt_sub.text().strip() or "General"
        desc = self.txt_desc.text().strip()

        if self.existing_phrase:
            self.existing_phrase.category = cat
            self.existing_phrase.subcategory = sub
            self.existing_phrase.title = title
            self.existing_phrase.text = text
            self.existing_phrase.description = desc
            self.library.save_custom_phrases()
        else:
            phrase = ScreenplayPhrase(
                category=cat,
                subcategory=sub,
                title=title,
                text=text if text.endswith("\n") else text + "\n",
                description=desc,
                is_custom=True
            )
            self.library.add_custom_phrase(phrase)

        self.accept()


# ==============================================================================
# DRAGGABLE PHRASE CARD WIDGET
# ==============================================================================

class DraggablePhraseItem(QFrame):
    """A drag-and-drop enabled card representing a screenplay phrase/term."""

    insertRequested = Signal(str)
    editRequested = Signal(str)
    deleteRequested = Signal(str)

    CATEGORY_COLORS = {
        "Headings": "#7aa2f7",
        "Light Direction": "#ff9e64",
        "Setting Notes": "#2ac3de",
        "Stage Directions": "#bb9af7",
        "Prop Directions": "#e0af68",
        "Act & Scene Markers": "#9ece6a",
        "Custom Notes": "#f7768e",
    }

    def __init__(self, phrase: ScreenplayPhrase, parent=None):
        super().__init__(parent)
        self.phrase = phrase
        self._drag_start_pos: Optional[QPoint] = None
        self.setObjectName("PhraseItem")
        self._init_ui()

    def _init_ui(self) -> None:
        cat_color = self.CATEGORY_COLORS.get(self.phrase.category, "#7aa2f7")
        self.setStyleSheet(f"""
            QFrame#PhraseItem {{
                background-color: #1a1b26;
                border: 1px solid #292e42;
                border-left: 3px solid {cat_color};
                border-radius: 5px;
                padding: 3px;
            }}
            QFrame#PhraseItem:hover {{
                border-color: {cat_color};
                background-color: #1f2335;
            }}
        """)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        if self.phrase.description:
            self.setToolTip(f"{self.phrase.title}\n{self.phrase.description}\n(Drag into manuscript or click ➕)")
        else:
            self.setToolTip(f"{self.phrase.title}\n(Drag into manuscript or click ➕)")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 4, 4, 4)
        layout.setSpacing(6)

        # Drag grip indicator icon
        grip_lbl = QLabel("⋮⋮", self)
        grip_lbl.setStyleSheet("color: #414868; font-size: 11px; font-weight: 700;")
        layout.addWidget(grip_lbl)

        # Title & Subcategory
        text_col = QVBoxLayout()
        text_col.setSpacing(1)

        title_lbl = QLabel(self.phrase.title, self)
        title_lbl.setStyleSheet("color: #c0caf5; font-size: 11px; font-weight: 600;")
        title_lbl.setWordWrap(True)
        text_col.addWidget(title_lbl)

        if self.phrase.subcategory:
            sub_lbl = QLabel(self.phrase.subcategory.upper(), self)
            sub_lbl.setStyleSheet("color: #565f89; font-size: 8px; font-weight: 700; letter-spacing: 0.5px;")
            text_col.addWidget(sub_lbl)

        layout.addLayout(text_col, stretch=1)

        # Insert button
        btn_insert = QToolButton(self)
        btn_insert.setText("➕")
        btn_insert.setToolTip("Insert at Cursor")
        btn_insert.setFixedSize(22, 22)
        btn_insert.setStyleSheet("""
            QToolButton {
                background: #24283b;
                color: #7aa2f7;
                border: 1px solid #292e42;
                border-radius: 4px;
                font-size: 10px;
            }
            QToolButton:hover {
                background: #7aa2f7;
                color: #15161e;
            }
        """)
        btn_insert.clicked.connect(lambda: self.insertRequested.emit(self.phrase.text))
        layout.addWidget(btn_insert)

        # Context menu for custom phrases
        if self.phrase.is_custom:
            btn_menu = QToolButton(self)
            btn_menu.setIcon(VectorIconFactory.create_icon("gear", "#787c99", 12))
            btn_menu.setFixedSize(20, 20)
            btn_menu.setStyleSheet("background: transparent; border: none;")
            btn_menu.clicked.connect(self._show_context_menu)
            layout.addWidget(btn_menu)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_pos = event.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.MouseButton.LeftButton) or not self._drag_start_pos:
            return

        dist = (event.pos() - self._drag_start_pos).manhattanLength()
        from PySide6.QtWidgets import QApplication
        if dist >= QApplication.startDragDistance():
            self._start_drag()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.insertRequested.emit(self.phrase.text)
        super().mouseDoubleClickEvent(event)

    def _start_drag(self) -> None:
        drag = QDrag(self)
        mime_data = QMimeData()
        mime_data.setText(self.phrase.text)
        mime_data.setData("application/x-volumenodex-screenplay-phrase", self.phrase.text.encode("utf-8"))
        drag.setMimeData(mime_data)

        # Create drag thumbnail pixmap
        pixmap = QPixmap(190, 26)
        pixmap.fill(QColor("#1f2335"))
        painter = QPainter(pixmap)
        cat_color = self.CATEGORY_COLORS.get(self.phrase.category, "#7aa2f7")
        painter.fillRect(0, 0, 4, 26, QColor(cat_color))
        painter.setPen(QPen(QColor("#7aa2f7"), 1))
        painter.drawRect(0, 0, 189, 25)
        painter.setPen(QPen(QColor("#c0caf5")))
        font = QFont("Segoe UI", 9, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(10, 17, self.phrase.title[:24])
        painter.end()

        drag.setPixmap(pixmap)
        drag.setHotSpot(QPoint(15, 13))
        drag.exec(Qt.DropAction.CopyAction)

    def _show_context_menu(self) -> None:
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #1a1b26;
                color: #c0caf5;
                border: 1px solid #292e42;
                padding: 4px;
            }
            QMenu::item:selected {
                background-color: #24283b;
                color: #7aa2f7;
            }
        """)
        act_edit = menu.addAction("Edit Phrase...")
        act_edit.triggered.connect(lambda: self.editRequested.emit(self.phrase.id))

        act_del = menu.addAction("Delete Custom Phrase")
        act_del.triggered.connect(lambda: self.deleteRequested.emit(self.phrase.id))

        menu.exec(self.mapToGlobal(QPoint(0, self.height())))


# ==============================================================================
# MAIN PALETTE DRAWER
# ==============================================================================

class ScreenplayPaletteDrawer(QWidget):
    """Collapsible right-side drawer housing categorized drag-and-drop screenplay terms."""

    insertTextRequested = Signal(str)
    collapsedChanged = Signal(bool)
    codexSwitchRequested = Signal()

    EXPANDED_WIDTH = 320
    COLLAPSED_WIDTH = 32

    def __init__(self, library: Optional[ScreenplayPhraseLibrary] = None, parent=None):
        super().__init__(parent)
        self.library = library or ScreenplayPhraseLibrary()
        self.is_collapsed = False
        self._active_category: str = "All"
        self._item_widgets: List[DraggablePhraseItem] = []

        self._init_ui()
        self.setFixedWidth(self.EXPANDED_WIDTH)
        self.refresh()

    def _init_ui(self) -> None:
        root_layout = QHBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.stack = QStackedWidget(self)
        root_layout.addWidget(self.stack)

        # Page 0: Expanded View
        self.expanded_page = QWidget(self)
        self.expanded_page.setStyleSheet("background-color: #16161e; border-left: 1px solid #24283b;")
        exp_layout = QVBoxLayout(self.expanded_page)
        exp_layout.setContentsMargins(10, 8, 10, 8)
        exp_layout.setSpacing(8)

        # 1. Header Bar
        header_bar = QHBoxLayout()
        header_bar.setContentsMargins(0, 0, 0, 0)
        header_bar.setSpacing(6)

        self.btn_collapse = QToolButton(self.expanded_page)
        self.btn_collapse.setIcon(VectorIconFactory.create_icon("chevron_right", "#787c99", 16))
        self.btn_collapse.setIconSize(QSize(16, 16))
        self.btn_collapse.setFixedSize(24, 24)
        self.btn_collapse.setToolTip("Collapse Palette")
        self.btn_collapse.clicked.connect(self.toggle_collapsed)
        header_bar.addWidget(self.btn_collapse)

        icon_lbl = QLabel(self.expanded_page)
        icon_lbl.setPixmap(VectorIconFactory.create_icon("table", "#7aa2f7", 18).pixmap(18, 18))
        header_bar.addWidget(icon_lbl)

        title_lbl = QLabel("TERMS & PHRASES", self.expanded_page)
        title_lbl.setStyleSheet("color: #c0caf5; font-size: 11px; font-weight: 700; letter-spacing: 0.8px;")
        header_bar.addWidget(title_lbl)

        header_bar.addStretch()

        # Switch to Screenplay Codex Button
        self.btn_goto_codex = QPushButton("🎬 Codex", self.expanded_page)
        self.btn_goto_codex.setToolTip("Switch to Screenplay Codex Drawer")
        self.btn_goto_codex.setStyleSheet("""
            QPushButton {
                background-color: #1f2335;
                color: #7aa2f7;
                font-size: 10px;
                font-weight: 600;
                padding: 3px 8px;
                border: 1px solid #292e42;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #24283b;
                border-color: #7aa2f7;
            }
        """)
        self.btn_goto_codex.clicked.connect(self.codexSwitchRequested.emit)
        header_bar.addWidget(self.btn_goto_codex)

        exp_layout.addLayout(header_bar)

        # 2. Category Selector Dropdown & Filter Line Edit
        ctrl_bar = QHBoxLayout()
        ctrl_bar.setSpacing(6)

        self.combo_filter_cat = QComboBox(self.expanded_page)
        self.combo_filter_cat.addItem("All Categories", "All")
        for cat in self.library.get_categories():
            self.combo_filter_cat.addItem(cat, cat)
        self.combo_filter_cat.setStyleSheet("""
            QComboBox {
                background-color: #1f2335;
                color: #c0caf5;
                border: 1px solid #292e42;
                border-radius: 4px;
                padding: 3px 6px;
                font-size: 10px;
            }
        """)
        self.combo_filter_cat.currentIndexChanged.connect(self._on_category_changed)
        ctrl_bar.addWidget(self.combo_filter_cat, stretch=1)

        self.btn_add_custom = QPushButton("+ Custom", self.expanded_page)
        self.btn_add_custom.setToolTip("Add Reusable Custom Phrase / Note")
        self.btn_add_custom.setStyleSheet("""
            QPushButton {
                background-color: #7aa2f7;
                color: #15161e;
                font-size: 10px;
                font-weight: 700;
                padding: 3px 8px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #89b4fa;
            }
        """)
        self.btn_add_custom.clicked.connect(self._on_add_custom_phrase)
        ctrl_bar.addWidget(self.btn_add_custom)

        exp_layout.addLayout(ctrl_bar)

        # 3. Search Filter Bar
        self.search_bar = QLineEdit(self.expanded_page)
        self.search_bar.setPlaceholderText("Search headings, lighting, props...")
        self.search_bar.setStyleSheet("""
            QLineEdit {
                background-color: #1f2335;
                color: #c0caf5;
                border: 1px solid #292e42;
                border-radius: 4px;
                padding: 3px 7px;
                font-size: 11px;
            }
            QLineEdit:focus {
                border-color: #7aa2f7;
            }
        """)
        self.search_bar.textChanged.connect(self.refresh)
        exp_layout.addWidget(self.search_bar)

        # 4. Drag Instructions Hint
        hint_lbl = QLabel("Drag any term onto the page, or click ➕ to insert at cursor.", self.expanded_page)
        hint_lbl.setStyleSheet("color: #565f89; font-size: 9px; font-style: italic;")
        hint_lbl.setWordWrap(True)
        exp_layout.addWidget(hint_lbl)

        # 5. Scroll Area of Categorized Cards
        self.scroll_area = QScrollArea(self.expanded_page)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.container_widget = QWidget()
        self.container_layout = QVBoxLayout(self.container_widget)
        self.container_layout.setContentsMargins(0, 0, 0, 0)
        self.container_layout.setSpacing(4)
        self.container_layout.addStretch()

        self.scroll_area.setWidget(self.container_widget)
        exp_layout.addWidget(self.scroll_area, stretch=1)

        self.stack.addWidget(self.expanded_page)

        # Page 1: Collapsed Strip
        self.collapsed_page = QWidget(self)
        self.collapsed_page.setStyleSheet("background-color: #16161e; border-left: 1px solid #24283b;")
        col_layout = QVBoxLayout(self.collapsed_page)
        col_layout.setContentsMargins(4, 8, 4, 8)
        col_layout.setSpacing(6)

        self.btn_expand = QToolButton(self.collapsed_page)
        self.btn_expand.setIcon(VectorIconFactory.create_icon("chevron_left", "#787c99", 16))
        self.btn_expand.setIconSize(QSize(16, 16))
        self.btn_expand.setFixedSize(24, 24)
        self.btn_expand.setToolTip("Expand Screenplay Terms & Phrases")
        self.btn_expand.clicked.connect(self.toggle_collapsed)
        col_layout.addWidget(self.btn_expand)

        self.btn_strip_icon = QToolButton(self.collapsed_page)
        self.btn_strip_icon.setIcon(VectorIconFactory.create_icon("table", "#787c99", 18))
        self.btn_strip_icon.setIconSize(QSize(18, 18))
        self.btn_strip_icon.setFixedSize(24, 24)
        self.btn_strip_icon.setToolTip("Screenplay Terms & Phrases")
        self.btn_strip_icon.clicked.connect(self.toggle_collapsed)
        col_layout.addWidget(self.btn_strip_icon)

        col_layout.addStretch()
        self.stack.addWidget(self.collapsed_page)
        self.stack.setCurrentWidget(self.expanded_page)

    def _on_category_changed(self) -> None:
        self._active_category = self.combo_filter_cat.currentData()
        self.refresh()

    def set_collapsed(self, collapsed: bool) -> None:
        self.is_collapsed = collapsed
        if collapsed:
            self.stack.setCurrentWidget(self.collapsed_page)
            self.setFixedWidth(self.COLLAPSED_WIDTH)
        else:
            self.stack.setCurrentWidget(self.expanded_page)
            self.setFixedWidth(self.EXPANDED_WIDTH)
        self.collapsedChanged.emit(collapsed)

    def toggle_collapsed(self) -> None:
        self.set_collapsed(not self.is_collapsed)

    def refresh(self) -> None:
        """Populates cards filtered by selected category and search keyword."""
        # Clear existing items
        for w in self._item_widgets:
            self.container_layout.removeWidget(w)
            w.deleteLater()
        self._item_widgets.clear()

        filter_kw = self.search_bar.text().strip().lower()
        active_cat = self._active_category

        all_phrases = self.library.get_all_phrases()
        grouped: Dict[str, List[ScreenplayPhrase]] = {}

        for p in all_phrases:
            if active_cat != "All" and p.category != active_cat:
                continue
            if filter_kw:
                match = (
                    filter_kw in p.title.lower()
                    or filter_kw in p.text.lower()
                    or filter_kw in p.subcategory.lower()
                    or filter_kw in p.description.lower()
                )
                if not match:
                    continue
            grouped.setdefault(p.category, []).append(p)

        # Render section headers and phrase cards
        for cat, phrases in grouped.items():
            cat_header = QLabel(f"<b>{cat.upper()}</b> ({len(phrases)})", self.container_widget)
            cat_header.setStyleSheet("color: #787c99; font-size: 9px; font-weight: 700; margin-top: 6px; letter-spacing: 0.5px;")
            self.container_layout.insertWidget(self.container_layout.count() - 1, cat_header)
            self._item_widgets.append(cat_header)

            for p in phrases:
                item = DraggablePhraseItem(p, self.container_widget)
                item.insertRequested.connect(self.insertTextRequested.emit)
                item.editRequested.connect(self._on_edit_custom_phrase)
                item.deleteRequested.connect(self._on_delete_custom_phrase)
                self.container_layout.insertWidget(self.container_layout.count() - 1, item)
                self._item_widgets.append(item)

    def _on_add_custom_phrase(self) -> None:
        dlg = CustomPhraseDialog(self.library, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.refresh()

    def _on_edit_custom_phrase(self, phrase_id: str) -> None:
        p = next((x for x in self.library.custom_phrases if x.id == phrase_id), None)
        if p:
            dlg = CustomPhraseDialog(self.library, existing_phrase=p, parent=self)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                self.refresh()

    def _on_delete_custom_phrase(self, phrase_id: str) -> None:
        self.library.remove_custom_phrase(phrase_id)
        self.refresh()
