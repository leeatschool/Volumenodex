"""Integrated Chapter & Scene Outline Navigator Drawer.

Provides a collapsible push panel beside the left desk gutter. Automatically scans
the manuscript for headings (H1, H2, Title, Chapter prefixes), counts words per chapter,
displays status pills, enables reordering, and jumps the cursor to any chapter with one click.
"""

import re
from typing import List, Optional
from PySide6.QtCore import Qt, Signal, QTimer, QSize
from PySide6.QtGui import (
    QFont, QColor, QTextDocument, QTextBlock, QTextBlockFormat,
    QTextCursor
)
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QToolButton, QScrollArea, QFrame, QLineEdit, QComboBox,
    QStackedWidget, QSizePolicy
)

from volumenodex.ui.vector_icons import VectorIconFactory
from volumenodex.story.codex_model import ChapterSceneItem


class ChapterCardWidget(QFrame):
    """Visual card for a single chapter or scene in the outline."""

    clicked = Signal(int)             # doc_position
    reorderRequested = Signal(int, int)  # (current_idx, direction: -1 for up, 1 for down)
    statusChanged = Signal(int, str)  # (card_index, new_status)
    deleteRequested = Signal(int)     # card_index

    STATUS_COLORS = {
        "Draft": "#e0af68",          # Warm amber
        "In Progress": "#7aa2f7",    # Fluent blue
        "Needs Revision": "#f7768e", # Rose / Coral
        "Completed": "#9ece6a",      # Forest green
    }

    def __init__(self, item: ChapterSceneItem, index: int, total_items: int, parent=None):
        super().__init__(parent)
        self.item = item
        self.index = index
        self.total_items = total_items
        self._is_active = False

        self.setObjectName("chapterCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._init_ui()
        self._update_style()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        # Top row: Reorder handles + Chapter Title + Actions
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(4)

        # Move Up button
        self.btn_up = QToolButton(self)
        self.btn_up.setIcon(VectorIconFactory.create_icon("arrow_up", "#787c99", 12))
        self.btn_up.setIconSize(QSize(12, 12))
        self.btn_up.setFixedSize(20, 20)
        self.btn_up.setToolTip("Move chapter earlier")
        self.btn_up.setEnabled(self.index > 0)
        self.btn_up.clicked.connect(lambda: self.reorderRequested.emit(self.index, -1))
        self.btn_up.setStyleSheet("""
            QToolButton {
                background: #1a1b26;
                border: 1px solid #282b3d;
                border-radius: 3px;
            }
            QToolButton:hover {
                background: #24283b;
                border-color: #7aa2f7;
            }
            QToolButton:disabled {
                background: transparent;
                border: none;
            }
        """)
        top_row.addWidget(self.btn_up)

        # Move Down button
        self.btn_down = QToolButton(self)
        self.btn_down.setIcon(VectorIconFactory.create_icon("arrow_down", "#787c99", 12))
        self.btn_down.setIconSize(QSize(12, 12))
        self.btn_down.setFixedSize(20, 20)
        self.btn_down.setToolTip("Move chapter later")
        self.btn_down.setEnabled(self.index < self.total_items - 1)
        self.btn_down.clicked.connect(lambda: self.reorderRequested.emit(self.index, 1))
        self.btn_down.setStyleSheet("""
            QToolButton {
                background: #1a1b26;
                border: 1px solid #282b3d;
                border-radius: 3px;
            }
            QToolButton:hover {
                background: #24283b;
                border-color: #7aa2f7;
            }
            QToolButton:disabled {
                background: transparent;
                border: none;
            }
        """)
        top_row.addWidget(self.btn_down)

        # Chapter Title Label
        clean_title = self.item.title.strip() or "Untitled Chapter"
        self.lbl_title = QLabel(clean_title, self)
        font = QFont("Segoe UI", 10, QFont.Weight.Bold)
        self.lbl_title.setFont(font)
        self.lbl_title.setStyleSheet("color: #c0caf5; background: transparent; border: none;")
        self.lbl_title.setWordWrap(True)
        top_row.addWidget(self.lbl_title, stretch=1)

        layout.addLayout(top_row)

        # Second row: Word count pill & Status selector
        meta_row = QHBoxLayout()
        meta_row.setContentsMargins(0, 0, 0, 0)
        meta_row.setSpacing(6)

        # Word count pill
        wc_text = f"{self.item.word_count:,} w"
        self.lbl_words = QLabel(wc_text, self)
        self.lbl_words.setStyleSheet("""
            QLabel {
                color: #9aa5ce;
                background-color: #16161e;
                border: 1px solid #292e42;
                border-radius: 9px;
                padding: 1px 7px;
                font-size: 10px;
                font-weight: 500;
            }
        """)
        meta_row.addWidget(self.lbl_words)

        # Status dropdown pill
        self.status_combo = QComboBox(self)
        for s in ["Draft", "In Progress", "Needs Revision", "Completed"]:
            self.status_combo.addItem(s)
        self.status_combo.setCurrentText(self.item.status)
        self.status_combo.currentTextChanged.connect(self._on_status_changed)
        self._update_combo_style(self.item.status)
        meta_row.addWidget(self.status_combo)

        meta_row.addStretch()
        layout.addLayout(meta_row)

    def _on_status_changed(self, new_status: str) -> None:
        self.item.status = new_status
        self._update_combo_style(new_status)
        self.statusChanged.emit(self.index, new_status)

    def _update_combo_style(self, status: str) -> None:
        col = self.STATUS_COLORS.get(status, "#7aa2f7")
        self.status_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: #16161e;
                color: {col};
                border: 1px solid {col}55;
                border-radius: 9px;
                padding: 1px 6px;
                font-size: 10px;
                font-weight: 600;
            }}
            QComboBox::drop-down {{
                border: none;
                width: 12px;
            }}
            QComboBox QAbstractItemView {{
                background-color: #1f2335;
                color: #c0caf5;
                selection-background-color: #2e344e;
                border: 1px solid #292e42;
            }}
        """)

    def set_active(self, active: bool) -> None:
        if self._is_active != active:
            self._is_active = active
            self._update_style()

    def _update_style(self) -> None:
        if self._is_active:
            self.setStyleSheet("""
                #chapterCard {
                    background-color: #24283b;
                    border: 1.5px solid #7aa2f7;
                    border-radius: 6px;
                }
                #chapterCard:hover {
                    background-color: #292e42;
                }
            """)
        else:
            self.setStyleSheet("""
                #chapterCard {
                    background-color: #1f2335;
                    border: 1px solid #292e42;
                    border-radius: 6px;
                }
                #chapterCard:hover {
                    background-color: #24283b;
                    border: 1px solid #414868;
                }
            """)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.item.block_number)
        super().mousePressEvent(event)


class ChapterNavigatorDrawer(QWidget):
    """Collapsible Left Drawer for manuscript navigation and chapter structure."""

    chapterSelected = Signal(int)         # doc position or block number
    newChapterRequested = Signal()
    reorderChaptersRequested = Signal(int, int) # (from_idx, to_idx)
    collapsedChanged = Signal(bool)

    EXPANDED_WIDTH = 270
    COLLAPSED_WIDTH = 32

    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_collapsed = False
        self._items: List[ChapterSceneItem] = []
        self._cards: List[ChapterCardWidget] = []
        self._active_block_num = -1

        # Debounce timer for manuscript scanning
        self._target_doc: Optional[QTextDocument] = None
        self._scan_timer = QTimer(self)
        self._scan_timer.setSingleShot(True)
        self._scan_timer.setInterval(350)
        self._scan_timer.timeout.connect(self._on_scan_timer_timeout)

        self._init_ui()
        self.setFixedWidth(self.EXPANDED_WIDTH)

    def _init_ui(self) -> None:
        root_layout = QHBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.stack = QStackedWidget(self)
        root_layout.addWidget(self.stack)

        # Page 0: Expanded View
        self.expanded_page = QWidget(self)
        self.expanded_page.setStyleSheet("background-color: #16161e; border-right: 1px solid #24283b;")
        exp_layout = QVBoxLayout(self.expanded_page)
        exp_layout.setContentsMargins(10, 8, 10, 8)
        exp_layout.setSpacing(8)

        # 1. Header Bar
        header_bar = QHBoxLayout()
        header_bar.setContentsMargins(0, 0, 0, 0)
        header_bar.setSpacing(6)

        icon_lbl = QLabel(self.expanded_page)
        icon_lbl.setPixmap(VectorIconFactory.create_icon("navigator", "#7aa2f7", 18).pixmap(18, 18))
        header_bar.addWidget(icon_lbl)

        title_lbl = QLabel("OUTLINE NAVIGATOR", self.expanded_page)
        title_lbl.setStyleSheet("color: #c0caf5; font-size: 11px; font-weight: 700; letter-spacing: 0.8px;")
        header_bar.addWidget(title_lbl)

        header_bar.addStretch()

        self.btn_collapse = QToolButton(self.expanded_page)
        self.btn_collapse.setIcon(VectorIconFactory.create_icon("chevron_left", "#787c99", 16))
        self.btn_collapse.setIconSize(QSize(16, 16))
        self.btn_collapse.setFixedSize(24, 24)
        self.btn_collapse.setToolTip("Collapse Navigator (Ctrl+Alt+N)")
        self.btn_collapse.clicked.connect(self.toggle_collapsed)
        self.btn_collapse.setStyleSheet("""
            QToolButton {
                background: transparent;
                border: 1px solid transparent;
                border-radius: 4px;
            }
            QToolButton:hover {
                background: #24283b;
                border-color: #414868;
            }
        """)
        header_bar.addWidget(self.btn_collapse)
        exp_layout.addLayout(header_bar)

        # 2. Quick Action Toolbar (+ Chapter & Filter)
        action_bar = QHBoxLayout()
        action_bar.setContentsMargins(0, 0, 0, 0)
        action_bar.setSpacing(6)

        self.btn_add_chapter = QPushButton("+ Chapter", self.expanded_page)
        self.btn_add_chapter.setIcon(VectorIconFactory.create_icon("plus", "#7aa2f7", 13))
        self.btn_add_chapter.setToolTip("Insert a new chapter heading and page break")
        self.btn_add_chapter.clicked.connect(self.newChapterRequested.emit)
        self.btn_add_chapter.setStyleSheet("""
            QPushButton {
                background-color: #1f2335;
                color: #7aa2f7;
                border: 1px solid #292e42;
                border-radius: 4px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #24283b;
                border-color: #7aa2f7;
            }
        """)
        action_bar.addWidget(self.btn_add_chapter)

        self.search_filter = QLineEdit(self.expanded_page)
        self.search_filter.setPlaceholderText("Filter outline...")
        self.search_filter.textChanged.connect(self._filter_cards)
        self.search_filter.setStyleSheet("""
            QLineEdit {
                background-color: #1f2335;
                color: #c0caf5;
                border: 1px solid #292e42;
                border-radius: 4px;
                padding: 3px 6px;
                font-size: 11px;
            }
            QLineEdit:focus {
                border-color: #7aa2f7;
            }
        """)
        action_bar.addWidget(self.search_filter, stretch=1)
        exp_layout.addLayout(action_bar)

        # 3. Stats / Summary Pill
        self.lbl_summary = QLabel("0 Chapters • 0 words", self.expanded_page)
        self.lbl_summary.setStyleSheet("color: #787c99; font-size: 10px; font-weight: 500;")
        exp_layout.addWidget(self.lbl_summary)

        # 4. Scrollable Cards Container
        self.scroll_area = QScrollArea(self.expanded_page)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background: #16161e;
                width: 6px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background: #282b3d;
                border-radius: 3px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #414868;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        self.cards_container = QWidget()
        self.cards_container.setStyleSheet("background: transparent;")
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(6)
        self.cards_layout.addStretch()

        self.scroll_area.setWidget(self.cards_container)
        exp_layout.addWidget(self.scroll_area, stretch=1)

        self.stack.addWidget(self.expanded_page)

        # Page 1: Collapsed Strip View
        self.collapsed_page = QWidget(self)
        self.collapsed_page.setStyleSheet("background-color: #16161e; border-right: 1px solid #24283b;")
        col_layout = QVBoxLayout(self.collapsed_page)
        col_layout.setContentsMargins(4, 8, 4, 8)
        col_layout.setSpacing(12)

        self.btn_expand = QToolButton(self.collapsed_page)
        self.btn_expand.setIcon(VectorIconFactory.create_icon("chevron_right", "#7aa2f7", 16))
        self.btn_expand.setIconSize(QSize(16, 16))
        self.btn_expand.setFixedSize(24, 24)
        self.btn_expand.setToolTip("Expand Chapter Navigator (Ctrl+Alt+N)")
        self.btn_expand.clicked.connect(self.toggle_collapsed)
        self.btn_expand.setStyleSheet("""
            QToolButton {
                background: transparent;
                border: 1px solid transparent;
                border-radius: 4px;
            }
            QToolButton:hover {
                background: #24283b;
                border-color: #7aa2f7;
            }
        """)
        col_layout.addWidget(self.btn_expand, alignment=Qt.AlignmentFlag.AlignCenter)

        # Strip vertical icon button
        self.btn_strip_icon = QToolButton(self.collapsed_page)
        self.btn_strip_icon.setIcon(VectorIconFactory.create_icon("navigator", "#787c99", 18))
        self.btn_strip_icon.setIconSize(QSize(18, 18))
        self.btn_strip_icon.setFixedSize(24, 24)
        self.btn_strip_icon.setToolTip("Outline Navigator")
        self.btn_strip_icon.clicked.connect(self.toggle_collapsed)
        self.btn_strip_icon.setStyleSheet("""
            QToolButton {
                background: transparent;
                border: none;
            }
            QToolButton:hover {
                background: #24283b;
            }
        """)
        col_layout.addWidget(self.btn_strip_icon, alignment=Qt.AlignmentFlag.AlignCenter)

        col_layout.addStretch()
        self.stack.addWidget(self.collapsed_page)

    def toggle_collapsed(self) -> None:
        """Toggles between expanded and collapsed flush side panel."""
        self.is_collapsed = not self.is_collapsed
        if self.is_collapsed:
            self.setFixedWidth(self.COLLAPSED_WIDTH)
            self.stack.setCurrentIndex(1)
        else:
            self.setFixedWidth(self.EXPANDED_WIDTH)
            self.stack.setCurrentIndex(0)
        self.collapsedChanged.emit(self.is_collapsed)

    def set_collapsed(self, collapsed: bool) -> None:
        if self.is_collapsed != collapsed:
            self.toggle_collapsed()

    def request_scan(self, doc: QTextDocument) -> None:
        """Schedules debounced scan of the manuscript."""
        self._target_doc = doc
        self._scan_timer.start()

    def _on_scan_timer_timeout(self) -> None:
        if self._target_doc:
            self.scan_manuscript(self._target_doc)

    def scan_manuscript(self, doc: QTextDocument) -> None:
        """Parses document blocks to discover chapter and scene boundaries."""
        if not doc:
            return

        discovered: List[ChapterSceneItem] = []
        current_item: Optional[ChapterSceneItem] = None
        current_words = 0
        total_words = 0

        block = doc.firstBlock()
        while block.isValid():
            text = block.text().strip()
            fmt = block.blockFormat()
            user_prop = str(fmt.property(QTextBlockFormat.Property.UserProperty) or "")

            is_heading = False
            heading_lvl = 1

            if user_prop in ("title", "h1"):
                is_heading = True
                heading_lvl = 1
            elif user_prop == "h2":
                is_heading = True
                heading_lvl = 2
            elif user_prop == "h3":
                is_heading = True
                heading_lvl = 3
            elif user_prop == "h4":
                is_heading = True
                heading_lvl = 4
            elif user_prop == "h5":
                is_heading = True
                heading_lvl = 5
            elif re.match(r"^(chapter\s+\w+|#+\s+|\bact\s+\w+|\bprologue\b|\bepilogue\b)", text, re.IGNORECASE):
                is_heading = True
                heading_lvl = 1
            elif len(text) > 0 and len(text) < 80:
                # Check character format for bold heading
                cf = block.charFormat()
                if cf.fontWeight() >= 700 and cf.fontPointSize() >= 14:
                    is_heading = True

            if is_heading and text:
                if current_item:
                    current_item.word_count = current_words
                    discovered.append(current_item)
                clean_t = re.sub(r"^#+\s*", "", text).strip()
                current_item = ChapterSceneItem(
                    title=clean_t,
                    block_number=block.position(),
                    heading_level=heading_lvl,
                    status="Draft"
                )
                current_words = 0
            else:
                words_in_block = len(text.split()) if text else 0
                current_words += words_in_block
                total_words += words_in_block

            block = block.next()

        if current_item:
            current_item.word_count = current_words
            discovered.append(current_item)

        # Preserve statuses of known items if matching title
        old_status_map = {item.title.lower(): item.status for item in self._items}
        for d in discovered:
            if d.title.lower() in old_status_map:
                d.status = old_status_map[d.title.lower()]

        self._items = discovered
        self._rebuild_cards()

        # Update summary label
        c_count = len(self._items)
        self.lbl_summary.setText(f"{c_count} Chapter{'s' if c_count != 1 else ''} • {total_words:,} words total")

    def _rebuild_cards(self) -> None:
        """Refreshes the card widgets in the outline."""
        # Clear existing card widgets
        for c in self._cards:
            c.setParent(None)
            c.deleteLater()
        self._cards.clear()

        # Re-populate
        for idx, item in enumerate(self._items):
            card = ChapterCardWidget(item, idx, len(self._items), self.cards_container)
            card.clicked.connect(self._on_card_clicked)
            card.reorderRequested.connect(self._on_card_reorder)
            card.statusChanged.connect(self._on_card_status_changed)
            # Insert before the bottom stretch
            self.cards_layout.insertWidget(self.cards_layout.count() - 1, card)
            self._cards.append(card)

        self._filter_cards(self.search_filter.text())

    def _on_card_clicked(self, doc_pos: int) -> None:
        self._active_block_num = doc_pos
        for c in self._cards:
            c.set_active(c.item.block_number == doc_pos)
        self.chapterSelected.emit(doc_pos)

    def _on_card_reorder(self, card_idx: int, direction: int) -> None:
        target_idx = card_idx + direction
        if 0 <= target_idx < len(self._items):
            self.reorderChaptersRequested.emit(card_idx, target_idx)

    def _on_card_status_changed(self, card_idx: int, new_status: str) -> None:
        if 0 <= card_idx < len(self._items):
            self._items[card_idx].status = new_status

    def _filter_cards(self, query: str) -> None:
        q = (query or "").lower().strip()
        for card in self._cards:
            if not q or q in card.item.title.lower() or q in card.item.status.lower():
                card.show()
            else:
                card.hide()

    def get_items(self) -> List[ChapterSceneItem]:
        return self._items
