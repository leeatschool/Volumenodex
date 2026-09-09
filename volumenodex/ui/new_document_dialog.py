"""New Document Creation Dialog for Volumenodex.

Prompts the author for a document title and operating mode (Creative Fiction,
General Non-Fiction, or Academic & Scholarly Research).
"""

from typing import Tuple
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QRadioButton, QButtonGroup, QFrame, QCheckBox
)

from volumenodex.core.document_model import DocumentMode, DOCUMENT_MODE_TITLES


class NewDocumentDialog(QDialog):
    """Dialog presented when creating a new manuscript or project."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create New Document — Volumenodex")
        self.setFixedWidth(520)
        self.setStyleSheet("""
            QDialog {
                background-color: #1a1b26;
                color: #c0caf5;
            }
            QLabel {
                color: #c0caf5;
            }
            QLineEdit {
                background-color: #16161e;
                color: #c0caf5;
                border: 1px solid #292e42;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border-color: #7aa2f7;
            }
            QRadioButton {
                color: #c0caf5;
                font-size: 12px;
                spacing: 8px;
            }
            QRadioButton::indicator {
                width: 16px;
                height: 16px;
                border-radius: 8px;
                border: 2px solid #3b4261;
                background-color: #16161e;
            }
            QRadioButton::indicator:checked {
                border-color: #7aa2f7;
                background-color: #7aa2f7;
            }
            QCheckBox {
                color: #9aa5ce;
                font-size: 11px;
                spacing: 6px;
            }
            QCheckBox::indicator {
                width: 14px;
                height: 14px;
                border-radius: 3px;
                border: 1px solid #3b4261;
                background-color: #16161e;
            }
            QCheckBox::indicator:checked {
                background-color: #7aa2f7;
                border-color: #7aa2f7;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(14)

        # Header Title
        lbl_header = QLabel("Start a New Document", self)
        font_h = QFont("Segoe UI", 15, QFont.Weight.Bold)
        lbl_header.setFont(font_h)
        lbl_header.setStyleSheet("color: #7aa2f7;")
        layout.addWidget(lbl_header)

        # Document Title Input
        lbl_title_tag = QLabel("DOCUMENT TITLE", self)
        lbl_title_tag.setStyleSheet("color: #787c99; font-size: 10px; font-weight: 700; letter-spacing: 0.5px;")
        layout.addWidget(lbl_title_tag)

        self.txt_title = QLineEdit(self)
        self.txt_title.setPlaceholderText("e.g. The Architecture of Silence or Quantum Entanglement in Neural Nets")
        self.txt_title.setText("Untitled Document")
        self.txt_title.selectAll()
        layout.addWidget(self.txt_title)

        # Mode Selection Group
        lbl_mode_tag = QLabel("AUTHORING MODE & STUDIO FOCUS", self)
        lbl_mode_tag.setStyleSheet("color: #787c99; font-size: 10px; font-weight: 700; letter-spacing: 0.5px; margin-top: 6px;")
        layout.addWidget(lbl_mode_tag)

        self.btn_group = QButtonGroup(self)

        # Card 1: Creative Fiction
        self.card_fiction = self._create_mode_card(
            DocumentMode.CREATIVE_FICTION,
            "Creative Fiction & Narrative",
            "Story Codex with character dossiers, world lore, chapter outline navigator, and creative companion sparks.",
            checked=True
        )
        layout.addWidget(self.card_fiction)

        # Card 2: General Non-Fiction
        self.card_nonfiction = self._create_mode_card(
            DocumentMode.NON_FICTION,
            "General Non-Fiction & Essays",
            "Structured exposition, research notes, argument flow, and companion guidance for clarity and evidence.",
            checked=False
        )
        layout.addWidget(self.card_nonfiction)

        # Card 3: Academic & Scholarly
        self.card_academic = self._create_mode_card(
            DocumentMode.ACADEMIC,
            "Academic & Research Paper",
            "Replaces Story Codex with built-in Citation & Bibliography Generator (APA, MLA, Chicago, IEEE). Scholarly tone tips.",
            checked=False
        )
        layout.addWidget(self.card_academic)

        # Template Checkbox
        self.chk_template = QCheckBox("Generate starter manuscript outline template for this mode", self)
        self.chk_template.setChecked(True)
        layout.addWidget(self.chk_template)

        # Dynamic Mode Banner
        self.banner = QFrame(self)
        self.banner.setStyleSheet("""
            QFrame {
                background-color: #1f2335;
                border: 1px solid #292e42;
                border-radius: 6px;
                padding: 6px 10px;
            }
        """)
        b_layout = QVBoxLayout(self.banner)
        b_layout.setContentsMargins(8, 6, 8, 6)
        self.lbl_banner_desc = QLabel("", self.banner)
        self.lbl_banner_desc.setWordWrap(True)
        self.lbl_banner_desc.setStyleSheet("color: #7aa2f7; font-size: 11px;")
        b_layout.addWidget(self.lbl_banner_desc)
        layout.addWidget(self.banner)

        self._update_banner()

        # Dialog Buttons
        layout.addSpacing(6)
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_cancel = QPushButton("Cancel", self)
        btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #24283b;
                color: #9aa5ce;
                border: 1px solid #3b4261;
                border-radius: 6px;
                padding: 7px 16px;
                font-weight: 600;
            }
            QPushButton:hover { background-color: #2e344e; color: #c0caf5; }
        """)
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

        btn_create = QPushButton("Create Document", self)
        btn_create.setDefault(True)
        btn_create.setStyleSheet("""
            QPushButton {
                background-color: #7aa2f7;
                color: #1a1b26;
                border: none;
                border-radius: 6px;
                padding: 7px 20px;
                font-weight: 700;
            }
            QPushButton:hover { background-color: #89b4fa; }
        """)
        btn_create.clicked.connect(self.accept)
        btn_layout.addWidget(btn_create)

        layout.addLayout(btn_layout)

    def _create_mode_card(self, mode: DocumentMode, title: str, subtitle: str, checked: bool = False) -> QFrame:
        card = QFrame(self)
        card.setObjectName("modeCard")
        card.setStyleSheet("""
            #modeCard {
                background-color: #16161e;
                border: 1px solid #24283b;
                border-radius: 7px;
                padding: 8px 12px;
            }
            #modeCard:hover {
                border-color: #3b4261;
            }
        """)

        h_box = QHBoxLayout(card)
        h_box.setContentsMargins(4, 4, 4, 4)
        h_box.setSpacing(10)

        rb = QRadioButton(card)
        rb.setChecked(checked)
        self.btn_group.addButton(rb)
        setattr(rb, "_doc_mode", mode)
        rb.toggled.connect(self._update_banner)
        h_box.addWidget(rb)

        v_text = QVBoxLayout()
        v_text.setSpacing(2)
        lbl_t = QLabel(f"<b>{title}</b>", card)
        lbl_t.setStyleSheet("color: #c0caf5; font-size: 12px;")
        v_text.addWidget(lbl_t)

        lbl_s = QLabel(subtitle, card)
        lbl_s.setWordWrap(True)
        lbl_s.setStyleSheet("color: #787c99; font-size: 10px;")
        v_text.addWidget(lbl_s)

        h_box.addLayout(v_text, stretch=1)
        return card

    def _update_banner(self) -> None:
        mode = self.selected_mode
        if mode == DocumentMode.ACADEMIC:
            self.lbl_banner_desc.setText(
                "🎓 <b>Academic Mode:</b> Story Codex is replaced with the built-in <b>Citation & Reference Generator</b>. "
                "Writing companion provides scholarly tone, thesis alignment, and academic hedging feedback."
            )
            self.banner.show()
        elif mode == DocumentMode.NON_FICTION:
            self.lbl_banner_desc.setText(
                "📝 <b>Non-Fiction Mode:</b> Tailored for essays, journalism, and non-fiction books. "
                "Writing companion focuses on argument structure, illustrative evidence, and clear topic transitions."
            )
            self.banner.show()
        else:
            self.lbl_banner_desc.setText(
                "🪶 <b>Creative Fiction Mode:</b> Story Codex is active with character dossiers and world lore. "
                "Writing companion provides creative plot sparks, pacing, and dialogue insights."
            )
            self.banner.show()

    @property
    def document_title(self) -> str:
        text = self.txt_title.text().strip()
        return text if text else "Untitled Document"

    @property
    def selected_mode(self) -> DocumentMode:
        for btn in self.btn_group.buttons():
            if btn.isChecked():
                return getattr(btn, "_doc_mode", DocumentMode.CREATIVE_FICTION)
        return DocumentMode.CREATIVE_FICTION

    @property
    def generate_template(self) -> bool:
        return self.chk_template.isChecked()

    @classmethod
    def prompt_new_document(cls, parent=None) -> Tuple[bool, str, DocumentMode, bool]:
        """Convenience factory returning (confirmed, title, mode, generate_template)."""
        dlg = cls(parent)
        result = dlg.exec()
        if result == QDialog.DialogCode.Accepted:
            return (True, dlg.document_title, dlg.selected_mode, dlg.generate_template)
        return (False, "", DocumentMode.CREATIVE_FICTION, False)
