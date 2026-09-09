"""Revision Inspector Drawer and Interactive Finding Cards.

Provides an expandable push panel sidebar that aggregates all findings from
the active proofreading lenses (Adverbs, Passive Voice, Pacing Cadence,
Filler Words, and Dialogue Flow). Features one-click jump to manuscript
and smart suggestion chips that instantly apply replacements.
"""

from typing import List, Optional, Dict
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QFont, QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QToolButton, QScrollArea, QFrame, QLineEdit, QComboBox,
    QStackedWidget, QButtonGroup, QProgressBar
)

from volumenodex.ui.vector_icons import VectorIconFactory
from volumenodex.review.lens_engine import LensFinding, RevisionLensEngine


class FindingCardWidget(QFrame):
    """Visual card for a single proofreading finding with suggestions and jump button."""

    jumpRequested = Signal(int, int)       # (start_pos, end_pos)
    replaceRequested = Signal(int, int, str) # (start_pos, end_pos, new_text)
    addToDictionaryRequested = Signal(str)

    CATEGORY_BADGES = {
        "spelling": ("SPELLING", "#f7768e", "rgba(247, 118, 142, 0.15)"),
        "adverb": ("ADVERB", "#e0af68", "rgba(224, 175, 104, 0.15)"),
        "passive": ("PASSIVE", "#f7768e", "rgba(247, 118, 142, 0.15)"),
        "filler": ("FILLER", "#bb9af7", "rgba(187, 154, 247, 0.15)"),
        "dialogue": ("DIALOGUE", "#7dcfff", "rgba(125, 207, 255, 0.15)"),
        "pacing": ("PACING", "#7aa2f7", "rgba(122, 162, 247, 0.15)"),
    }

    def __init__(self, finding: LensFinding, parent=None):
        super().__init__(parent)
        self.finding = finding
        self.setObjectName("findingCard")
        self._init_ui()
        self._update_style()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        # 1. Top row: Category Badge + Jump Button
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(6)

        cat_title, cat_col, cat_bg = self.CATEGORY_BADGES.get(
            self.finding.lens_type, ("INSIGHT", "#7aa2f7", "rgba(122, 162, 247, 0.15)")
        )

        if self.finding.lens_type == "pacing":
            badge_text = f"PACING • {self.finding.pacing_tier.upper()}"
        else:
            badge_text = cat_title

        self.lbl_badge = QLabel(badge_text, self)
        self.lbl_badge.setStyleSheet(f"""
            QLabel {{
                color: {cat_col};
                background-color: {cat_bg};
                border: 1px solid {cat_col}55;
                border-radius: 4px;
                padding: 1px 6px;
                font-size: 9px;
                font-weight: 700;
                letter-spacing: 0.5px;
            }}
        """)
        top_row.addWidget(self.lbl_badge)

        top_row.addStretch()

        # Jump Button
        self.btn_jump = QPushButton("↗ Jump", self)
        self.btn_jump.setToolTip("Jump to and highlight this occurrence in the manuscript")
        self.btn_jump.setStyleSheet("""
            QPushButton {
                background-color: #16161e;
                color: #7aa2f7;
                border: 1px solid #292e42;
                border-radius: 4px;
                padding: 2px 7px;
                font-size: 10px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #24283b;
                border-color: #7aa2f7;
            }
        """)
        self.btn_jump.clicked.connect(lambda: self.jumpRequested.emit(self.finding.start_pos, self.finding.end_pos))
        top_row.addWidget(self.btn_jump)

        # Add to Dictionary Button (for spelling findings)
        if self.finding.lens_type == "spelling":
            self.btn_add_dict = QPushButton("+ Dict", self)
            self.btn_add_dict.setToolTip(f"Add '{self.finding.text}' to custom author dictionary")
            self.btn_add_dict.setStyleSheet("""
                QPushButton {
                    background-color: #16161e;
                    color: #9ece6a;
                    border: 1px solid #283b28;
                    border-radius: 4px;
                    padding: 2px 7px;
                    font-size: 10px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: #243b28;
                    border-color: #9ece6a;
                }
            """)
            self.btn_add_dict.clicked.connect(lambda: self.addToDictionaryRequested.emit(self.finding.text))
            top_row.addWidget(self.btn_add_dict)

        layout.addLayout(top_row)

        # 2. Flagged Snippet Context
        snippet_text = self.finding.context_snippet or f"[{self.finding.text}]"
        self.lbl_snippet = QLabel(snippet_text, self)
        self.lbl_snippet.setWordWrap(True)
        self.lbl_snippet.setStyleSheet("color: #c0caf5; font-size: 11px; font-weight: 500;")
        layout.addWidget(self.lbl_snippet)

        # 3. Guidance Message
        self.lbl_msg = QLabel(self.finding.message, self)
        self.lbl_msg.setWordWrap(True)
        self.lbl_msg.setStyleSheet("color: #787c99; font-size: 10px; font-style: italic;")
        layout.addWidget(self.lbl_msg)

        # 4. Smart Suggestions Row (if any)
        if self.finding.suggestions:
            sug_row = QHBoxLayout()
            sug_row.setContentsMargins(0, 2, 0, 0)
            sug_row.setSpacing(4)

            sug_title = QLabel("Replace:", self)
            sug_title.setStyleSheet("color: #565f89; font-size: 9px; font-weight: 700;")
            sug_row.addWidget(sug_title)

            for s in self.finding.suggestions[:4]:
                chip = QPushButton(s, self)
                chip.setToolTip(f"Replace '{self.finding.text}' with '{s}'")
                chip.setStyleSheet("""
                    QPushButton {
                        background-color: #16161e;
                        color: #9ece6a;
                        border: 1px solid #283b28;
                        border-radius: 9px;
                        padding: 1px 7px;
                        font-size: 10px;
                        font-weight: 600;
                    }
                    QPushButton:hover {
                        background-color: #243b28;
                        border-color: #9ece6a;
                    }
                """)
                replacement = "" if s == "(remove)" else s
                chip.clicked.connect(
                    lambda _, r=replacement: self.replaceRequested.emit(
                        self.finding.start_pos, self.finding.end_pos, r
                    )
                )
                sug_row.addWidget(chip)

            sug_row.addStretch()
            layout.addLayout(sug_row)

    def _update_style(self) -> None:
        self.setStyleSheet("""
            #findingCard {
                background-color: #1f2335;
                border: 1px solid #292e42;
                border-radius: 6px;
            }
            #findingCard:hover {
                background-color: #24283b;
                border-color: #414868;
            }
        """)


class RevisionInspectorDrawer(QWidget):
    """Collapsible Right Push Panel displaying real-time findings from all active lenses."""

    jumpRequested = Signal(int, int)       # (start_pos, end_pos)
    replaceRequested = Signal(int, int, str) # (start_pos, end_pos, new_text)
    addToDictionaryRequested = Signal(str)
    collapsedChanged = Signal(bool)
    filterChanged = Signal(str)

    EXPANDED_WIDTH = 320
    COLLAPSED_WIDTH = 32

    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_collapsed = False
        self._current_filter = "all"
        self._findings: List[LensFinding] = []
        self._cards: List[FindingCardWidget] = []

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
        self.btn_collapse.setToolTip("Collapse Revision Inspector")
        self.btn_collapse.clicked.connect(self.toggle_collapsed)
        self.btn_collapse.setStyleSheet("""
            QToolButton { background: transparent; border: 1px solid transparent; border-radius: 4px; }
            QToolButton:hover { background: #24283b; border-color: #414868; }
        """)
        header_bar.addWidget(self.btn_collapse)

        icon_lbl = QLabel(self.expanded_page)
        icon_lbl.setPixmap(VectorIconFactory.create_icon("highlight", "#7aa2f7", 18).pixmap(18, 18))
        header_bar.addWidget(icon_lbl)

        title_lbl = QLabel("REVISION INSPECTOR", self.expanded_page)
        title_lbl.setStyleSheet("color: #c0caf5; font-size: 11px; font-weight: 700; letter-spacing: 0.8px;")
        header_bar.addWidget(title_lbl)

        header_bar.addStretch()
        exp_layout.addLayout(header_bar)

        # 2. Overall Summary Label
        self.lbl_summary = QLabel("0 Findings Detected", self.expanded_page)
        self.lbl_summary.setStyleSheet("color: #7aa2f7; font-size: 11px; font-weight: 600;")
        exp_layout.addWidget(self.lbl_summary)

        # 3. Pacing Rhythm Cadence Meter
        self.pacing_meter_box = QFrame(self.expanded_page)
        self.pacing_meter_box.setStyleSheet("""
            QFrame {
                background-color: #1a1b26;
                border: 1px solid #24283b;
                border-radius: 6px;
                padding: 4px 6px;
            }
        """)
        pm_layout = QVBoxLayout(self.pacing_meter_box)
        pm_layout.setContentsMargins(4, 4, 4, 4)
        pm_layout.setSpacing(3)

        self.lbl_meter_title = QLabel("Prose Rhythm & Cadence Breakdown:", self.pacing_meter_box)
        self.lbl_meter_title.setStyleSheet("color: #787c99; font-size: 9px; font-weight: 700; text-transform: uppercase;")
        pm_layout.addWidget(self.lbl_meter_title)

        self.lbl_meter_stats = QLabel("Short: 0% • Balanced: 0% • Long: 0%", self.pacing_meter_box)
        self.lbl_meter_stats.setStyleSheet("color: #9aa5ce; font-size: 10px; font-weight: 500;")
        pm_layout.addWidget(self.lbl_meter_stats)
        exp_layout.addWidget(self.pacing_meter_box)

        # 4. Filter Switcher Bar
        filter_bar = QHBoxLayout()
        filter_bar.setContentsMargins(0, 0, 0, 0)
        filter_bar.setSpacing(4)

        self.btn_filter_all = QPushButton("All", self.expanded_page)
        self.btn_filter_spelling = QPushButton("Spelling", self.expanded_page)
        self.btn_filter_adverb = QPushButton("Adverbs", self.expanded_page)
        self.btn_filter_passive = QPushButton("Passive", self.expanded_page)
        self.btn_filter_filler = QPushButton("Fillers", self.expanded_page)
        self.btn_filter_pacing = QPushButton("Pacing", self.expanded_page)

        self.filter_buttons = [
            ("all", self.btn_filter_all),
            ("spelling", self.btn_filter_spelling),
            ("adverb", self.btn_filter_adverb),
            ("passive", self.btn_filter_passive),
            ("filler", self.btn_filter_filler),
            ("pacing", self.btn_filter_pacing),
        ]

        btn_style = """
            QPushButton {
                background-color: #1f2335;
                color: #787c99;
                border: 1px solid #292e42;
                border-radius: 4px;
                padding: 3px 6px;
                font-size: 10px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #24283b;
                color: #c0caf5;
            }
            QPushButton:checked {
                background-color: rgba(122, 162, 247, 0.2);
                color: #7aa2f7;
                border-color: #7aa2f7;
            }
        """

        self.filter_group = QButtonGroup(self)
        for key, btn in self.filter_buttons:
            btn.setCheckable(True)
            btn.setStyleSheet(btn_style)
            self.filter_group.addButton(btn)
            btn.clicked.connect(lambda _, k=key: self._set_filter(k))
            filter_bar.addWidget(btn)

        self.btn_filter_all.setChecked(True)
        exp_layout.addLayout(filter_bar)

        # 5. Scroll Area of Finding Cards
        self.scroll_area = QScrollArea(self.expanded_page)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setStyleSheet("""
            QScrollArea { background: transparent; border: none; }
            QScrollBar:vertical { background: #16161e; width: 6px; margin: 0; }
            QScrollBar::handle:vertical { background: #282b3d; border-radius: 3px; min-height: 20px; }
            QScrollBar::handle:vertical:hover { background: #414868; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
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
        self.collapsed_page.setStyleSheet("background-color: #16161e; border-left: 1px solid #24283b;")
        col_layout = QVBoxLayout(self.collapsed_page)
        col_layout.setContentsMargins(4, 8, 4, 8)
        col_layout.setSpacing(12)

        self.btn_expand = QToolButton(self.collapsed_page)
        self.btn_expand.setIcon(VectorIconFactory.create_icon("chevron_left", "#7aa2f7", 16))
        self.btn_expand.setIconSize(QSize(16, 16))
        self.btn_expand.setFixedSize(24, 24)
        self.btn_expand.setToolTip("Expand Revision Inspector")
        self.btn_expand.clicked.connect(self.toggle_collapsed)
        self.btn_expand.setStyleSheet("""
            QToolButton { background: transparent; border: 1px solid transparent; border-radius: 4px; }
            QToolButton:hover { background: #24283b; border-color: #7aa2f7; }
        """)
        col_layout.addWidget(self.btn_expand, alignment=Qt.AlignmentFlag.AlignCenter)

        self.btn_strip_icon = QToolButton(self.collapsed_page)
        self.btn_strip_icon.setIcon(VectorIconFactory.create_icon("highlight", "#787c99", 18))
        self.btn_strip_icon.setIconSize(QSize(18, 18))
        self.btn_strip_icon.setFixedSize(24, 24)
        self.btn_strip_icon.setToolTip("Revision Inspector")
        self.btn_strip_icon.clicked.connect(self.toggle_collapsed)
        self.btn_strip_icon.setStyleSheet("""
            QToolButton { background: transparent; border: none; }
            QToolButton:hover { background: #24283b; }
        """)
        col_layout.addWidget(self.btn_strip_icon, alignment=Qt.AlignmentFlag.AlignCenter)

        col_layout.addStretch()
        self.stack.addWidget(self.collapsed_page)

    def toggle_collapsed(self) -> None:
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

    def update_findings(self, findings: List[LensFinding]) -> None:
        """Updates the inspector cards list and metrics breakdown."""
        self._findings = findings

        # Clear existing card widgets
        for c in self._cards:
            c.setParent(None)
            c.deleteLater()
        self._cards.clear()

        # Update metrics summary
        counts: Dict[str, int] = {}
        for f in findings:
            counts[f.lens_type] = counts.get(f.lens_type, 0) + 1

        total_issues = len([f for f in findings if f.lens_type not in ("pacing", "dialogue")])
        parts = []
        if counts.get('spelling'):
            parts.append(f"{counts['spelling']} Spelling")
        if counts.get('adverb'):
            parts.append(f"{counts['adverb']} Adverbs")
        if counts.get('passive'):
            parts.append(f"{counts['passive']} Passive")
        if counts.get('filler'):
            parts.append(f"{counts['filler']} Fillers")

        breakdown = f" ({', '.join(parts)})" if parts else ""
        self.lbl_summary.setText(f"{total_issues} Editorial Opportunities{breakdown}")

        # Update Pacing Meter
        pacing_findings = [f for f in findings if f.lens_type == "pacing"]
        if pacing_findings:
            tot = len(pacing_findings)
            n_short = len([f for f in pacing_findings if f.pacing_tier in ("staccato", "brisk")])
            n_mod = len([f for f in pacing_findings if f.pacing_tier == "moderate"])
            n_long = len([f for f in pacing_findings if f.pacing_tier == "lyrical"])
            self.lbl_meter_stats.setText(
                f"⚡ Punchy/Brisk: {int(n_short/tot*100)}% | 🌊 Balanced: {int(n_mod/tot*100)}% | 📜 Winding: {int(n_long/tot*100)}%"
            )
            self.pacing_meter_box.setVisible(True)
        else:
            self.pacing_meter_box.setVisible(False)

        # Populate cards
        for f in findings:
            card = FindingCardWidget(f, self.cards_container)
            card.jumpRequested.connect(self.jumpRequested.emit)
            card.replaceRequested.connect(self.replaceRequested.emit)
            card.addToDictionaryRequested.connect(self.addToDictionaryRequested.emit)
            self.cards_layout.insertWidget(self.cards_layout.count() - 1, card)
            self._cards.append(card)

        self._filter_cards(self._current_filter)

    def set_filter(self, filter_key: str) -> None:
        """Changes the active filter category and updates filter button states."""
        self._current_filter = filter_key
        for k, btn in self.filter_buttons:
            btn.setChecked(k == filter_key)
        self._filter_cards(filter_key)
        self.filterChanged.emit(filter_key)

    def _set_filter(self, filter_key: str) -> None:
        self.set_filter(filter_key)

    def _filter_cards(self, filter_key: str) -> None:
        for card in self._cards:
            if filter_key == "all":
                card.setVisible(card.finding.lens_type != "pacing") # don't overwhelm with all sentences unless pacing chosen
            else:
                card.setVisible(card.finding.lens_type == filter_key)
