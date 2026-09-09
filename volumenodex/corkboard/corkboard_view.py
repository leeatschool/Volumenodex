"""Visual Corkboard View with authentic cork texture, push-pinned index cards, and status tags."""

import random
from typing import List, Optional
from PySide6.QtCore import Qt, Signal, QRectF, QPointF
from PySide6.QtGui import (
    QPainter, QColor, QPen, QBrush, QFont, QPixmap, QImage,
    QLinearGradient, QRadialGradient
)
from PySide6.QtWidgets import (
    QWidget, QScrollArea, QVBoxLayout, QHBoxLayout, QGridLayout,
    QFrame, QLabel, QLineEdit, QTextEdit, QComboBox, QToolButton,
    QPushButton, QGraphicsDropShadowEffect, QSizePolicy
)

from volumenodex.corkboard.corkboard_model import (
    CorkboardManager, IndexCard, CardStatus, STATUS_COLORS, CARD_COLOR_PRESETS
)


class IndexCardWidget(QFrame):
    """An interactive physical index card pinned to the corkboard."""

    cardChanged = Signal(IndexCard)
    moveUpRequested = Signal(IndexCard)
    moveDownRequested = Signal(IndexCard)
    deleteRequested = Signal(IndexCard)
    jumpToManuscriptRequested = Signal(IndexCard)

    def __init__(self, card: IndexCard, index_number: int, parent=None):
        super().__init__(parent)
        self.card = card
        self.index_number = index_number
        self.setFixedSize(260, 185)

        # Drop shadow for paper card
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(14)
        shadow.setColor(QColor(0, 0, 0, 140))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)

        self._init_ui()
        self._apply_styling()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        # Top: Pin + Order Badge + Status Tag
        h_top = QHBoxLayout()
        h_top.setSpacing(4)

        self.lbl_pin = QLabel("📌")
        self.lbl_pin.setStyleSheet("font-size: 14px;")
        h_top.addWidget(self.lbl_pin)

        self.lbl_num = QLabel(f"#{self.index_number}")
        self.lbl_num.setStyleSheet("font-weight: bold; font-size: 11px; color: #555;")
        h_top.addWidget(self.lbl_num)

        h_top.addStretch()

        self.status_combo = QComboBox()
        for st in CardStatus:
            self.status_combo.addItem(st.value, st)
        self.status_combo.setCurrentText(self.card.status.value)
        self.status_combo.setFixedHeight(22)
        self.status_combo.currentIndexChanged.connect(self._on_status_changed)
        h_top.addWidget(self.status_combo)

        layout.addLayout(h_top)

        # Title Field
        self.txt_title = QLineEdit(self.card.title)
        self.txt_title.setStyleSheet("""
            QLineEdit {
                font-weight: bold;
                font-size: 13px;
                border: none;
                border-bottom: 1px solid rgba(0, 0, 0, 0.15);
                background: transparent;
                padding: 1px;
            }
        """)
        self.txt_title.textChanged.connect(self._on_title_changed)
        layout.addWidget(self.txt_title)

        # Synopsis Editor
        self.txt_synopsis = QTextEdit()
        self.txt_synopsis.setPlainText(self.card.synopsis)
        self.txt_synopsis.setPlaceholderText("Scene synopsis, character motives, goals...")
        self.txt_synopsis.setStyleSheet("""
            QTextEdit {
                border: none;
                background: transparent;
                font-size: 11px;
                line-height: 1.3;
            }
        """)
        self.txt_synopsis.textChanged.connect(self._on_synopsis_changed)
        layout.addWidget(self.txt_synopsis, stretch=1)

        # Bottom Bar: Word Count + Reorder Controls
        h_bot = QHBoxLayout()
        h_bot.setSpacing(4)

        self.lbl_words = QLabel(f"{self.card.word_count:,} w")
        self.lbl_words.setStyleSheet("font-size: 10px; color: #666;")
        h_bot.addWidget(self.lbl_words)

        h_bot.addStretch()

        if self.card.is_linked:
            self.btn_jump = QToolButton()
            self.btn_jump.setText("↗ Open")
            self.btn_jump.setToolTip("Jump to section in manuscript")
            self.btn_jump.setStyleSheet("font-size: 10px; border: 1px solid rgba(0,0,0,0.2); border-radius: 3px; padding: 1px 4px;")
            self.btn_jump.clicked.connect(lambda: self.jumpToManuscriptRequested.emit(self.card))
            h_bot.addWidget(self.btn_jump)

            self.btn_up = QToolButton()
            self.btn_up.setText("◀")
            self.btn_up.setToolTip("Move Earlier in Manuscript")
            self.btn_up.setFixedSize(20, 18)
            self.btn_up.setStyleSheet("border: 1px solid rgba(0,0,0,0.15); border-radius: 2px;")
            self.btn_up.clicked.connect(lambda: self.moveUpRequested.emit(self.card))
            h_bot.addWidget(self.btn_up)

            self.btn_down = QToolButton()
            self.btn_down.setText("▶")
            self.btn_down.setToolTip("Move Later in Manuscript")
            self.btn_down.setFixedSize(20, 18)
            self.btn_down.setStyleSheet("border: 1px solid rgba(0,0,0,0.15); border-radius: 2px;")
            self.btn_down.clicked.connect(lambda: self.moveDownRequested.emit(self.card))
            h_bot.addWidget(self.btn_down)
        else:
            self.btn_del = QToolButton()
            self.btn_del.setText("🗑")
            self.btn_del.setToolTip("Delete Scratch Card")
            self.btn_del.setFixedSize(20, 18)
            self.btn_del.setStyleSheet("border: 1px solid rgba(0,0,0,0.15); border-radius: 2px;")
            self.btn_del.clicked.connect(lambda: self.deleteRequested.emit(self.card))
            h_bot.addWidget(self.btn_del)

        layout.addLayout(h_bot)

    def _apply_styling(self) -> None:
        self.setStyleSheet(f"""
            IndexCardWidget {{
                background-color: {self.card.bg_color};
                color: {self.card.text_color};
                border: 1px solid rgba(0, 0, 0, 0.2);
                border-radius: 6px;
            }}
        """)
        # Update status combo styling with status color
        color = STATUS_COLORS.get(self.card.status, "#7aa2f7")
        self.status_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {color};
                color: #1a1b26;
                font-size: 10px;
                font-weight: bold;
                border-radius: 4px;
                padding: 1px 6px;
                border: none;
            }}
        """)

    def _on_title_changed(self, text: str) -> None:
        self.card.title = text
        self.cardChanged.emit(self.card)

    def _on_synopsis_changed(self) -> None:
        self.card.synopsis = self.txt_synopsis.toPlainText()
        self.cardChanged.emit(self.card)

    def _on_status_changed(self) -> None:
        self.card.status = self.status_combo.currentData()
        self._apply_styling()
        self.cardChanged.emit(self.card)


class CorkboardCanvas(QWidget):
    """The cork-textured board rendering the collection of pinned index cards."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cork_pixmap: Optional[QPixmap] = None
        self._generate_cork_texture()

    def _generate_cork_texture(self) -> None:
        w = 256
        h = 256
        img = QImage(w, h, QImage.Format.Format_RGB32)
        img.fill(QColor(145, 102, 62))  # Base warm cork tone

        painter = QPainter(img)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rng = random.Random(1337)

        # Cork flecks: darker wood flecks and golden ochre flecks
        for _ in range(3500):
            x = rng.randint(0, w - 1)
            y = rng.randint(0, h - 1)
            rad = rng.choice([1, 1, 2, 3])
            val = rng.random()
            if val < 0.4:
                col = QColor(105, 70, 38, rng.randint(40, 160))
            elif val < 0.7:
                col = QColor(185, 138, 88, rng.randint(50, 170))
            else:
                col = QColor(75, 48, 25, rng.randint(30, 120))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(col))
            painter.drawEllipse(QPointF(x, y), rad, rad)

        painter.end()
        self._cork_pixmap = QPixmap.fromImage(img)

    def paintEvent(self, event):
        painter = QPainter(self)
        if self._cork_pixmap:
            painter.drawTiledPixmap(0, 0, self.width(), self.height(), self._cork_pixmap)
        else:
            painter.fillRect(0, 0, self.width(), self.height(), QColor(145, 102, 62))


class CorkboardView(QWidget):
    """Full-featured Corkboard & Storyboard workspace with two-way manuscript synchronization."""

    returnToManuscriptRequested = Signal()
    jumpToSectionRequested = Signal(IndexCard)
    reorderManuscriptRequested = Signal(list)  # list of IndexCard in new order

    def __init__(self, manager: CorkboardManager, parent=None):
        super().__init__(parent)
        self.manager = manager
        self.active_tab = 0  # 0: Linked Scenes, 1: Idea Scratchpad

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # 1. Top Corkboard Action Header
        self._build_header(root_layout)

        # 2. Scrollable Cork Canvas
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        self.cork_canvas = CorkboardCanvas(self.scroll_area)
        self.grid_layout = QGridLayout(self.cork_canvas)
        self.grid_layout.setContentsMargins(32, 32, 32, 32)
        self.grid_layout.setSpacing(24)

        self.scroll_area.setWidget(self.cork_canvas)
        root_layout.addWidget(self.scroll_area, stretch=1)

        self.refresh_cards()

    def _build_header(self, parent_layout: QVBoxLayout) -> None:
        header = QFrame(self)
        header.setFixedHeight(48)
        header.setStyleSheet("""
            QFrame {
                background-color: #1a1b26;
                border-bottom: 1px solid #2f334d;
                padding: 4px 12px;
            }
        """)

        h = QHBoxLayout(header)
        h.setContentsMargins(12, 4, 12, 4)
        h.setSpacing(10)

        # Return Button
        self.btn_back = QPushButton("← Return to Manuscript")
        self.btn_back.setStyleSheet("""
            QPushButton {
                background-color: #24273a;
                color: #c0caf5;
                font-weight: bold;
                border: 1px solid #3b3e58;
                border-radius: 6px;
                padding: 5px 12px;
            }
            QPushButton:hover {
                background-color: #2f334d;
                border: 1px solid #7aa2f7;
            }
        """)
        self.btn_back.clicked.connect(self.returnToManuscriptRequested.emit)
        h.addWidget(self.btn_back)

        h.addSpacing(16)

        # View Mode Toggle: Linked Scenes vs Idea Scratchpad
        self.btn_view_linked = QToolButton()
        self.btn_view_linked.setText("📌 Manuscript Scene Cards")
        self.btn_view_linked.setCheckable(True)
        self.btn_view_linked.setChecked(True)
        self.btn_view_linked.clicked.connect(lambda: self._switch_tab(0))
        h.addWidget(self.btn_view_linked)

        self.btn_view_scratch = QToolButton()
        self.btn_view_scratch.setText("💡 Idea Scratchpad")
        self.btn_view_scratch.setCheckable(True)
        self.btn_view_scratch.setChecked(False)
        self.btn_view_scratch.clicked.connect(lambda: self._switch_tab(1))
        h.addWidget(self.btn_view_scratch)

        h.addStretch()

        # Add Card Button
        self.btn_add_card = QPushButton("+ Add Card")
        self.btn_add_card.setStyleSheet("""
            QPushButton {
                background-color: #7aa2f7;
                color: #1a1b26;
                font-weight: bold;
                border-radius: 6px;
                padding: 5px 14px;
            }
            QPushButton:hover {
                background-color: #89b4fa;
            }
        """)
        self.btn_add_card.clicked.connect(self._on_add_card)
        h.addWidget(self.btn_add_card)

        parent_layout.addWidget(header)

    def _switch_tab(self, tab_idx: int) -> None:
        self.active_tab = tab_idx
        self.btn_view_linked.setChecked(tab_idx == 0)
        self.btn_view_scratch.setChecked(tab_idx == 1)
        self.btn_add_card.setText("+ Add Scene Card" if tab_idx == 0 else "+ Add Idea Note")
        self.refresh_cards()

    def refresh_cards(self) -> None:
        # Clear existing grid widgets
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        cards = self.manager.linked_cards if self.active_tab == 0 else self.manager.scratch_cards

        cols = 4  # Display in 4 columns
        for idx, card in enumerate(cards):
            card_widget = IndexCardWidget(card, idx + 1, self.cork_canvas)
            card_widget.moveUpRequested.connect(self._on_move_card_up)
            card_widget.moveDownRequested.connect(self._on_move_card_down)
            card_widget.deleteRequested.connect(self._on_delete_scratch_card)
            card_widget.jumpToManuscriptRequested.connect(self.jumpToSectionRequested.emit)

            row = idx // cols
            col = idx % cols
            self.grid_layout.addWidget(card_widget, row, col)

    def _on_add_card(self) -> None:
        if self.active_tab == 0:
            self.manager.add_linked_card(
                title=f"New Scene {len(self.manager.linked_cards) + 1}",
                synopsis="Describe the conflict, objective, and outcome of this scene..."
            )
            self.reorderManuscriptRequested.emit(self.manager.linked_cards)
        else:
            self.manager.add_scratch_card(
                title="New Story Idea",
                synopsis="Jot down a fleeting thought, theme, dialogue snippet, or twist..."
            )
        self.refresh_cards()

    def _on_move_card_up(self, card: IndexCard) -> None:
        if card in self.manager.linked_cards:
            idx = self.manager.linked_cards.index(card)
            if idx > 0:
                self.manager.move_card(idx, idx - 1)
                self.refresh_cards()
                self.reorderManuscriptRequested.emit(self.manager.linked_cards)

    def _on_move_card_down(self, card: IndexCard) -> None:
        if card in self.manager.linked_cards:
            idx = self.manager.linked_cards.index(card)
            if idx < len(self.manager.linked_cards) - 1:
                self.manager.move_card(idx, idx + 1)
                self.refresh_cards()
                self.reorderManuscriptRequested.emit(self.manager.linked_cards)

    def _on_delete_scratch_card(self, card: IndexCard) -> None:
        if card in self.manager.scratch_cards:
            self.manager.scratch_cards.remove(card)
            self.refresh_cards()
