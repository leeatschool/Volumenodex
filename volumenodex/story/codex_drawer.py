"""Integrated Worldbuilding & Character Codex Drawer.

Provides a collapsible push panel beside the right desk gutter. Contains character dossiers,
world lore, custom vector portraits, aliases, secrets, notes, and Live Mention Detection
that illuminates cards in real time as the author types their name or aliases.
"""

from typing import Optional, List, Dict
from PySide6.QtCore import Qt, Signal, QSize, QTimer
from PySide6.QtGui import (
    QFont, QColor, QPixmap, QIcon
)
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QToolButton, QScrollArea, QFrame, QLineEdit, QComboBox,
    QStackedWidget, QTextEdit, QDialog, QFileDialog, QMessageBox,
    QButtonGroup
)

from volumenodex.ui.vector_icons import VectorIconFactory
from volumenodex.pet.companion_figures import CompanionFigureRenderer
from volumenodex.pet.pet_model import PetMood
from volumenodex.story.codex_model import CharacterProfile, LoreEntry, CodexManager


class EntityEditDialog(QDialog):
    """Sleek modal dialog to add or edit a Character profile or Lore entry."""

    def __init__(self, codex_manager: CodexManager, entity_type: str = "character", existing_entity=None, parent=None):
        super().__init__(parent)
        self.codex_manager = codex_manager
        self.entity_type = entity_type
        self.existing_entity = existing_entity

        self.setWindowTitle("Edit Codex Entry" if existing_entity else "New Codex Entry")
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
        if existing_entity:
            self._load_existing()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        # Header Title
        title_text = "Character Dossier" if self.entity_type == "character" else "World Lore Entry"
        lbl_head = QLabel(title_text)
        lbl_head.setStyleSheet("color: #7aa2f7; font-size: 14px; font-weight: 700;")
        layout.addWidget(lbl_head)

        # Name / Title
        layout.addWidget(QLabel("Name / Title:"))
        self.txt_name = QLineEdit(self)
        self.txt_name.setPlaceholderText("e.g. Master Sean or The Salt Fog Harbor")
        layout.addWidget(self.txt_name)

        # Role or Category
        if self.entity_type == "character":
            layout.addWidget(QLabel("Role in Narrative:"))
            self.role_combo = QComboBox(self)
            for r in ["Protagonist", "Antagonist", "Mentor", "Supporting", "Minor"]:
                self.role_combo.addItem(r)
            layout.addWidget(self.role_combo)

            # Portrait Avatar
            layout.addWidget(QLabel("Portrait Avatar:"))
            h_pic = QHBoxLayout()
            self.icon_combo = QComboBox(self)
            for ic in ["quill", "corvus", "ink", "scout", "ignis", "person"]:
                self.icon_combo.addItem(ic.capitalize(), ic)
            h_pic.addWidget(self.icon_combo, stretch=1)

            self.btn_browse_pic = QPushButton("Custom Photo...", self)
            self.btn_browse_pic.setStyleSheet("background-color: #24283b; color: #c0caf5; border: 1px solid #292e42;")
            self.btn_browse_pic.clicked.connect(self._browse_custom_image)
            h_pic.addWidget(self.btn_browse_pic)
            layout.addLayout(h_pic)
            self._custom_image_path = None
        else:
            layout.addWidget(QLabel("Category:"))
            self.cat_combo = QComboBox(self)
            for c in ["Location", "Artifact", "Faction", "Magic/Tech", "History", "Custom"]:
                self.cat_combo.addItem(c)
            layout.addWidget(self.cat_combo)

        # Aliases
        layout.addWidget(QLabel("Aliases & Mention Keywords (comma-separated):"))
        self.txt_aliases = QLineEdit(self)
        self.txt_aliases.setPlaceholderText("e.g. Sean, The Royal Cartographer, The Mapmaker")
        layout.addWidget(self.txt_aliases)

        # Appearance or Description
        desc_label = "Appearance:" if self.entity_type == "character" else "Description:"
        layout.addWidget(QLabel(desc_label))
        self.txt_desc = QTextEdit(self)
        self.txt_desc.setFixedHeight(65)
        layout.addWidget(self.txt_desc)

        # Motivation (for character)
        if self.entity_type == "character":
            layout.addWidget(QLabel("Motivation & Goal:"))
            self.txt_motivation = QTextEdit(self)
            self.txt_motivation.setFixedHeight(50)
            layout.addWidget(self.txt_motivation)

            layout.addWidget(QLabel("Secrets & Flaws:"))
            self.txt_secrets = QTextEdit(self)
            self.txt_secrets.setFixedHeight(50)
            layout.addWidget(self.txt_secrets)

        # Notes
        layout.addWidget(QLabel("Author's Notes:"))
        self.txt_notes = QTextEdit(self)
        self.txt_notes.setFixedHeight(50)
        layout.addWidget(self.txt_notes)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_cancel = QPushButton("Cancel", self)
        self.btn_cancel.setStyleSheet("background-color: #1f2335; color: #787c99; border: 1px solid #292e42;")
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)

        self.btn_save = QPushButton("Save Entry", self)
        self.btn_save.setStyleSheet("background-color: #7aa2f7; color: #16161e; font-weight: bold;")
        self.btn_save.clicked.connect(self._save_and_accept)
        btn_layout.addWidget(self.btn_save)

        layout.addLayout(btn_layout)

    def _browse_custom_image(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Character Portrait", "", "Image Files (*.png *.jpg *.jpeg *.bmp *.webp)"
        )
        if path:
            self._custom_image_path = path
            self.btn_browse_pic.setText("Custom Photo ✓")

    def _load_existing(self) -> None:
        ent = self.existing_entity
        if self.entity_type == "character":
            self.txt_name.setText(ent.name)
            self.role_combo.setCurrentText(ent.role)
            idx = self.icon_combo.findData(ent.icon_type)
            if idx >= 0:
                self.icon_combo.setCurrentIndex(idx)
            self.txt_aliases.setText(", ".join(ent.aliases))
            self.txt_desc.setPlainText(ent.appearance)
            self.txt_motivation.setPlainText(ent.motivation)
            self.txt_secrets.setPlainText(ent.secrets)
            self.txt_notes.setPlainText(ent.notes)
            self._custom_image_path = ent.custom_image_path
            if ent.custom_image_path:
                self.btn_browse_pic.setText("Custom Photo ✓")
        else:
            self.txt_name.setText(ent.title)
            self.cat_combo.setCurrentText(ent.category)
            self.txt_aliases.setText(", ".join(ent.aliases))
            self.txt_desc.setPlainText(ent.description)
            self.txt_notes.setPlainText(ent.notes)

    def _save_and_accept(self) -> None:
        name = self.txt_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Missing Name", "Please enter a name or title for this entry.")
            return

        alias_list = [a.strip() for a in self.txt_aliases.text().split(",") if a.strip()]

        if self.entity_type == "character":
            if self.existing_entity:
                c = self.existing_entity
            else:
                c = CharacterProfile()
                self.codex_manager.add_character(c)

            c.name = name
            c.role = self.role_combo.currentText()
            c.icon_type = self.icon_combo.currentData() or "person"
            c.custom_image_path = self._custom_image_path
            c.aliases = alias_list
            c.appearance = self.txt_desc.toPlainText()
            c.motivation = self.txt_motivation.toPlainText()
            c.secrets = self.txt_secrets.toPlainText()
            c.notes = self.txt_notes.toPlainText()
        else:
            if self.existing_entity:
                l = self.existing_entity
            else:
                l = LoreEntry()
                self.codex_manager.add_lore(l)

            l.title = name
            l.category = self.cat_combo.currentText()
            l.aliases = alias_list
            l.description = self.txt_desc.toPlainText()
            l.notes = self.txt_notes.toPlainText()

        self.accept()


class CharacterCardWidget(QFrame):
    """Visual dossier card for a character in the Codex."""

    insertRequested = Signal(str)
    editRequested = Signal(str)    # char_id
    deleteRequested = Signal(str)  # char_id

    ROLE_COLORS = {
        "Protagonist": "#7aa2f7",  # Fluent blue
        "Antagonist": "#f7768e",   # Rose / Coral
        "Mentor": "#bb9af7",       # Amethyst
        "Supporting": "#73daca",   # Teal
        "Minor": "#565f89",        # Slate
    }

    def __init__(self, character: CharacterProfile, parent=None):
        super().__init__(parent)
        self.character = character
        self._is_mentioned = False
        self._details_expanded = False

        self.setObjectName("characterCard")
        self._init_ui()
        self._update_style()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        # 1. Top row: Vector Avatar Portrait + Name + Role Badge + Edit/Delete
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(8)

        # Vector Avatar Portrait
        self.lbl_avatar = QLabel(self)
        self.lbl_avatar.setFixedSize(36, 36)
        self._render_avatar()
        top_row.addWidget(self.lbl_avatar)

        # Name & Role Column
        name_col = QVBoxLayout()
        name_col.setContentsMargins(0, 0, 0, 0)
        name_col.setSpacing(2)

        self.lbl_name = QLabel(self.character.name, self)
        font = QFont("Segoe UI", 10, QFont.Weight.Bold)
        self.lbl_name.setFont(font)
        self.lbl_name.setStyleSheet("color: #c0caf5; background: transparent; border: none;")
        name_col.addWidget(self.lbl_name)

        # Role badge
        role_col = self.ROLE_COLORS.get(self.character.role, "#7aa2f7")
        self.lbl_role = QLabel(self.character.role.upper(), self)
        self.lbl_role.setStyleSheet(f"""
            QLabel {{
                color: {role_col};
                background: {role_col}18;
                border: 1px solid {role_col}44;
                border-radius: 4px;
                padding: 1px 5px;
                font-size: 9px;
                font-weight: 700;
                letter-spacing: 0.5px;
            }}
        """)
        name_col.addWidget(self.lbl_role, alignment=Qt.AlignmentFlag.AlignLeft)
        top_row.addLayout(name_col, stretch=1)

        # Edit button
        self.btn_edit = QToolButton(self)
        self.btn_edit.setIcon(VectorIconFactory.create_icon("settings", "#787c99", 13))
        self.btn_edit.setIconSize(QSize(13, 13))
        self.btn_edit.setFixedSize(22, 22)
        self.btn_edit.setToolTip("Edit dossier")
        self.btn_edit.clicked.connect(lambda: self.editRequested.emit(self.character.id))
        self.btn_edit.setStyleSheet("""
            QToolButton { background: transparent; border: 1px solid transparent; border-radius: 3px; }
            QToolButton:hover { background: #24283b; border-color: #414868; }
        """)
        top_row.addWidget(self.btn_edit)

        # Delete button
        self.btn_del = QToolButton(self)
        self.btn_del.setIcon(VectorIconFactory.create_icon("close", "#787c99", 11))
        self.btn_del.setIconSize(QSize(11, 11))
        self.btn_del.setFixedSize(22, 22)
        self.btn_del.setToolTip("Delete character")
        self.btn_del.clicked.connect(lambda: self.deleteRequested.emit(self.character.id))
        self.btn_del.setStyleSheet("""
            QToolButton { background: transparent; border: 1px solid transparent; border-radius: 3px; }
            QToolButton:hover { background: #3b242e; border-color: #f7768e; }
        """)
        top_row.addWidget(self.btn_del)

        layout.addLayout(top_row)

        # 2. Live Mention Pulse Pill (Hidden by default, illuminates when user types name)
        self.lbl_mention = QLabel("● Active in current text", self)
        self.lbl_mention.setStyleSheet("""
            QLabel {
                color: #7aa2f7;
                background-color: rgba(122, 162, 247, 0.18);
                border: 1px solid #7aa2f7;
                border-radius: 4px;
                padding: 2px 6px;
                font-size: 10px;
                font-weight: 600;
            }
        """)
        self.lbl_mention.setVisible(False)
        layout.addWidget(self.lbl_mention)

        # 3. Aliases Row
        if self.character.aliases:
            aliases_text = " • ".join(self.character.aliases)
            lbl_aliases = QLabel(aliases_text, self)
            lbl_aliases.setWordWrap(True)
            lbl_aliases.setStyleSheet("color: #787c99; font-size: 10px; font-style: italic; background: transparent; border: none;")
            layout.addWidget(lbl_aliases)

        # 4. Collapsible Dossier Details
        self.details_widget = QWidget(self)
        self.details_widget.setVisible(False)
        det_layout = QVBoxLayout(self.details_widget)
        det_layout.setContentsMargins(0, 4, 0, 4)
        det_layout.setSpacing(4)

        if self.character.appearance:
            det_layout.addWidget(self._make_section_label("APPEARANCE"))
            lbl_app = QLabel(self.character.appearance, self.details_widget)
            lbl_app.setWordWrap(True)
            lbl_app.setStyleSheet("color: #a9b1d6; font-size: 11px;")
            det_layout.addWidget(lbl_app)

        if self.character.motivation:
            det_layout.addWidget(self._make_section_label("MOTIVATION"))
            lbl_mot = QLabel(self.character.motivation, self.details_widget)
            lbl_mot.setWordWrap(True)
            lbl_mot.setStyleSheet("color: #a9b1d6; font-size: 11px;")
            det_layout.addWidget(lbl_mot)

        if self.character.secrets:
            det_layout.addWidget(self._make_section_label("SECRETS & FLAWS"))
            lbl_sec = QLabel(self.character.secrets, self.details_widget)
            lbl_sec.setWordWrap(True)
            lbl_sec.setStyleSheet("color: #e0af68; font-size: 11px;")
            det_layout.addWidget(lbl_sec)

        if self.character.notes:
            det_layout.addWidget(self._make_section_label("NOTES"))
            lbl_not = QLabel(self.character.notes, self.details_widget)
            lbl_not.setWordWrap(True)
            lbl_not.setStyleSheet("color: #787c99; font-size: 11px;")
            det_layout.addWidget(lbl_not)

        layout.addWidget(self.details_widget)

        # 5. Bottom Action Row: Accordion Toggle + Insert Name
        bot_row = QHBoxLayout()
        bot_row.setContentsMargins(0, 2, 0, 0)
        bot_row.setSpacing(6)

        self.btn_toggle_dossier = QPushButton("Dossier ▾", self)
        self.btn_toggle_dossier.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #7aa2f7;
                border: none;
                font-size: 10px;
                font-weight: 600;
                padding: 2px 4px;
            }
            QPushButton:hover {
                text-decoration: underline;
            }
        """)
        self.btn_toggle_dossier.clicked.connect(self._toggle_details)
        bot_row.addWidget(self.btn_toggle_dossier)

        bot_row.addStretch()

        self.btn_insert = QPushButton("Insert", self)
        self.btn_insert.setIcon(VectorIconFactory.create_icon("plus", "#9aa5ce", 11))
        self.btn_insert.setToolTip(f"Insert '{self.character.name}' at cursor")
        self.btn_insert.clicked.connect(lambda: self.insertRequested.emit(self.character.name))
        self.btn_insert.setStyleSheet("""
            QPushButton {
                background-color: #16161e;
                color: #9aa5ce;
                border: 1px solid #292e42;
                border-radius: 4px;
                padding: 2px 7px;
                font-size: 10px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #24283b;
                border-color: #7aa2f7;
                color: #7aa2f7;
            }
        """)
        bot_row.addWidget(self.btn_insert)

        layout.addLayout(bot_row)

    def _make_section_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet("color: #565f89; font-size: 9px; font-weight: 700; letter-spacing: 0.5px;")
        return lbl

    def _render_avatar(self) -> None:
        """Renders vector portrait or custom avatar."""
        pix = CompanionFigureRenderer.render_figure(
            self.character.icon_type,
            size=36,
            mood=PetMood.IDLE,
            custom_image_path=self.character.custom_image_path
        )
        self.lbl_avatar.setPixmap(pix)

    def _toggle_details(self) -> None:
        self._details_expanded = not self._details_expanded
        self.details_widget.setVisible(self._details_expanded)
        self.btn_toggle_dossier.setText("Dossier ▴" if self._details_expanded else "Dossier ▾")

    def set_mentioned(self, mentioned: bool) -> None:
        """Illuminates the card when live mention is detected in the manuscript."""
        if self._is_mentioned != mentioned:
            self._is_mentioned = mentioned
            self.lbl_mention.setVisible(mentioned)
            self._update_style()

    def _update_style(self) -> None:
        if self._is_mentioned:
            self.setStyleSheet("""
                #characterCard {
                    background-color: #20263f;
                    border: 2px solid #7aa2f7;
                    border-radius: 7px;
                }
            """)
        else:
            self.setStyleSheet("""
                #characterCard {
                    background-color: #1f2335;
                    border: 1px solid #292e42;
                    border-radius: 7px;
                }
                #characterCard:hover {
                    background-color: #24283b;
                    border-color: #414868;
                }
            """)


class LoreCardWidget(QFrame):
    """Visual dossier card for worldbuilding lore entries."""

    insertRequested = Signal(str)
    editRequested = Signal(str)    # lore_id
    deleteRequested = Signal(str)  # lore_id

    CATEGORY_COLORS = {
        "Location": "#7aa2f7",    # Sky Blue
        "Artifact": "#e0af68",    # Gold Amber
        "Faction": "#bb9af7",     # Amethyst
        "Magic/Tech": "#7dcfff",  # Cyan
        "History": "#9ece6a",     # Forest Green
        "Custom": "#f7768e",      # Rose
    }

    def __init__(self, lore: LoreEntry, parent=None):
        super().__init__(parent)
        self.lore = lore
        self._is_mentioned = False

        self.setObjectName("loreCard")
        self._init_ui()
        self._update_style()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        # Top row: Icon + Title + Category + Edit/Delete
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(8)

        icon_lbl = QLabel(self)
        icon_lbl.setPixmap(VectorIconFactory.create_icon("lore", "#7aa2f7", 20).pixmap(20, 20))
        top_row.addWidget(icon_lbl)

        # Title & Category
        title_col = QVBoxLayout()
        title_col.setContentsMargins(0, 0, 0, 0)
        title_col.setSpacing(2)

        self.lbl_title = QLabel(self.lore.title, self)
        font = QFont("Segoe UI", 10, QFont.Weight.Bold)
        self.lbl_title.setFont(font)
        self.lbl_title.setStyleSheet("color: #c0caf5; background: transparent; border: none;")
        title_col.addWidget(self.lbl_title)

        cat_col = self.CATEGORY_COLORS.get(self.lore.category, "#7aa2f7")
        self.lbl_cat = QLabel(self.lore.category.upper(), self)
        self.lbl_cat.setStyleSheet(f"""
            QLabel {{
                color: {cat_col};
                background: {cat_col}18;
                border: 1px solid {cat_col}44;
                border-radius: 4px;
                padding: 1px 5px;
                font-size: 9px;
                font-weight: 700;
                letter-spacing: 0.5px;
            }}
        """)
        title_col.addWidget(self.lbl_cat, alignment=Qt.AlignmentFlag.AlignLeft)
        top_row.addLayout(title_col, stretch=1)

        # Edit button
        self.btn_edit = QToolButton(self)
        self.btn_edit.setIcon(VectorIconFactory.create_icon("settings", "#787c99", 13))
        self.btn_edit.setIconSize(QSize(13, 13))
        self.btn_edit.setFixedSize(22, 22)
        self.btn_edit.clicked.connect(lambda: self.editRequested.emit(self.lore.id))
        self.btn_edit.setStyleSheet("""
            QToolButton { background: transparent; border: 1px solid transparent; border-radius: 3px; }
            QToolButton:hover { background: #24283b; border-color: #414868; }
        """)
        top_row.addWidget(self.btn_edit)

        # Delete button
        self.btn_del = QToolButton(self)
        self.btn_del.setIcon(VectorIconFactory.create_icon("close", "#787c99", 11))
        self.btn_del.setIconSize(QSize(11, 11))
        self.btn_del.setFixedSize(22, 22)
        self.btn_del.clicked.connect(lambda: self.deleteRequested.emit(self.lore.id))
        self.btn_del.setStyleSheet("""
            QToolButton { background: transparent; border: 1px solid transparent; border-radius: 3px; }
            QToolButton:hover { background: #3b242e; border-color: #f7768e; }
        """)
        top_row.addWidget(self.btn_del)

        layout.addLayout(top_row)

        # Live Mention Pill
        self.lbl_mention = QLabel("● Active in current text", self)
        self.lbl_mention.setStyleSheet("""
            QLabel {
                color: #7aa2f7;
                background-color: rgba(122, 162, 247, 0.18);
                border: 1px solid #7aa2f7;
                border-radius: 4px;
                padding: 2px 6px;
                font-size: 10px;
                font-weight: 600;
            }
        """)
        self.lbl_mention.setVisible(False)
        layout.addWidget(self.lbl_mention)

        # Aliases
        if self.lore.aliases:
            aliases_text = " • ".join(self.lore.aliases)
            lbl_aliases = QLabel(aliases_text, self)
            lbl_aliases.setWordWrap(True)
            lbl_aliases.setStyleSheet("color: #787c99; font-size: 10px; font-style: italic;")
            layout.addWidget(lbl_aliases)

        # Description
        if self.lore.description:
            lbl_desc = QLabel(self.lore.description, self)
            lbl_desc.setWordWrap(True)
            lbl_desc.setStyleSheet("color: #a9b1d6; font-size: 11px;")
            layout.addWidget(lbl_desc)

        # Notes
        if self.lore.notes:
            lbl_notes = QLabel(self.lore.notes, self)
            lbl_notes.setWordWrap(True)
            lbl_notes.setStyleSheet("color: #787c99; font-size: 10px;")
            layout.addWidget(lbl_notes)

        # Bottom row: Insert
        bot_row = QHBoxLayout()
        bot_row.addStretch()

        self.btn_insert = QPushButton("Insert", self)
        self.btn_insert.setIcon(VectorIconFactory.create_icon("plus", "#9aa5ce", 11))
        self.btn_insert.setToolTip(f"Insert '{self.lore.title}' at cursor")
        self.btn_insert.clicked.connect(lambda: self.insertRequested.emit(self.lore.title))
        self.btn_insert.setStyleSheet("""
            QPushButton {
                background-color: #16161e;
                color: #9aa5ce;
                border: 1px solid #292e42;
                border-radius: 4px;
                padding: 2px 7px;
                font-size: 10px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #24283b;
                border-color: #7aa2f7;
                color: #7aa2f7;
            }
        """)
        bot_row.addWidget(self.btn_insert)
        layout.addLayout(bot_row)

    def set_mentioned(self, mentioned: bool) -> None:
        if self._is_mentioned != mentioned:
            self._is_mentioned = mentioned
            self.lbl_mention.setVisible(mentioned)
            self._update_style()

    def _update_style(self) -> None:
        if self._is_mentioned:
            self.setStyleSheet("""
                #loreCard {
                    background-color: #20263f;
                    border: 2px solid #7aa2f7;
                    border-radius: 7px;
                }
            """)
        else:
            self.setStyleSheet("""
                #loreCard {
                    background-color: #1f2335;
                    border: 1px solid #292e42;
                    border-radius: 7px;
                }
                #loreCard:hover {
                    background-color: #24283b;
                    border-color: #414868;
                }
            """)


class CharacterCodexDrawer(QWidget):
    """Collapsible Right Drawer for narrative worldbuilding and live mention tracking."""

    insertTextRequested = Signal(str)
    collapsedChanged = Signal(bool)
    entityUpdated = Signal()

    EXPANDED_WIDTH = 310
    COLLAPSED_WIDTH = 32

    def __init__(self, codex_manager: CodexManager, parent=None):
        super().__init__(parent)
        self.codex_manager = codex_manager
        self.is_collapsed = False
        self._current_tab = "character"  # "character" or "lore"

        self._char_cards: Dict[str, CharacterCardWidget] = {}
        self._lore_cards: Dict[str, LoreCardWidget] = {}

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
        self.btn_collapse.setToolTip("Collapse Codex (Ctrl+Alt+C)")
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

        icon_lbl = QLabel(self.expanded_page)
        icon_lbl.setPixmap(VectorIconFactory.create_icon("codex", "#7aa2f7", 18).pixmap(18, 18))
        header_bar.addWidget(icon_lbl)

        title_lbl = QLabel("STORY CODEX", self.expanded_page)
        title_lbl.setStyleSheet("color: #c0caf5; font-size: 11px; font-weight: 700; letter-spacing: 0.8px;")
        header_bar.addWidget(title_lbl)

        header_bar.addStretch()
        exp_layout.addLayout(header_bar)

        # 2. Segmented Pill Switcher (Characters vs Lore)
        seg_layout = QHBoxLayout()
        seg_layout.setContentsMargins(0, 0, 0, 0)
        seg_layout.setSpacing(4)

        self.btn_tab_chars = QPushButton("Characters", self.expanded_page)
        self.btn_tab_chars.setCheckable(True)
        self.btn_tab_chars.setChecked(True)
        self.btn_tab_chars.clicked.connect(lambda: self._switch_tab("character"))

        self.btn_tab_lore = QPushButton("World Lore", self.expanded_page)
        self.btn_tab_lore.setCheckable(True)
        self.btn_tab_lore.setChecked(False)
        self.btn_tab_lore.clicked.connect(lambda: self._switch_tab("lore"))

        self.tab_group = QButtonGroup(self)
        self.tab_group.addButton(self.btn_tab_chars)
        self.tab_group.addButton(self.btn_tab_lore)

        pill_style = """
            QPushButton {
                background-color: #1f2335;
                color: #787c99;
                border: 1px solid #292e42;
                border-radius: 5px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #24283b;
                color: #c0caf5;
            }
            QPushButton:checked {
                background-color: rgba(122, 162, 247, 0.18);
                color: #7aa2f7;
                border-color: #7aa2f7;
            }
        """
        self.btn_tab_chars.setStyleSheet(pill_style)
        self.btn_tab_lore.setStyleSheet(pill_style)

        seg_layout.addWidget(self.btn_tab_chars, stretch=1)
        seg_layout.addWidget(self.btn_tab_lore, stretch=1)
        exp_layout.addLayout(seg_layout)

        # 3. Action Bar: Search & Add Entity
        action_bar = QHBoxLayout()
        action_bar.setContentsMargins(0, 0, 0, 0)
        action_bar.setSpacing(6)

        self.search_filter = QLineEdit(self.expanded_page)
        self.search_filter.setPlaceholderText("Filter codex...")
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

        self.btn_add_entity = QPushButton("+ Add", self.expanded_page)
        self.btn_add_entity.setIcon(VectorIconFactory.create_icon("plus", "#7aa2f7", 12))
        self.btn_add_entity.setToolTip("Add new Character or Lore Entry")
        self.btn_add_entity.clicked.connect(self._show_add_dialog)
        self.btn_add_entity.setStyleSheet("""
            QPushButton {
                background-color: #1f2335;
                color: #7aa2f7;
                border: 1px solid #292e42;
                border-radius: 4px;
                padding: 3px 8px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #24283b;
                border-color: #7aa2f7;
            }
        """)
        action_bar.addWidget(self.btn_add_entity)
        exp_layout.addLayout(action_bar)

        # 4. Scrollable Container for Cards
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
        self.cards_layout.setSpacing(8)
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
        self.btn_expand.setToolTip("Expand Story Codex (Ctrl+Alt+C)")
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

        self.btn_strip_icon = QToolButton(self.collapsed_page)
        self.btn_strip_icon.setIcon(VectorIconFactory.create_icon("codex", "#787c99", 18))
        self.btn_strip_icon.setIconSize(QSize(18, 18))
        self.btn_strip_icon.setFixedSize(24, 24)
        self.btn_strip_icon.setToolTip("Story Codex")
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

    def _switch_tab(self, tab_key: str) -> None:
        self._current_tab = tab_key
        self.refresh()

    def refresh(self) -> None:
        """Clears and rebuilds card list for the active tab."""
        # Clear existing cards
        for card in list(self._char_cards.values()) + list(self._lore_cards.values()):
            card.setParent(None)
            card.deleteLater()
        self._char_cards.clear()
        self._lore_cards.clear()

        # Update tab counters
        n_chars = len(self.codex_manager.characters)
        n_lore = len(self.codex_manager.lore_entries)
        self.btn_tab_chars.setText(f"Characters ({n_chars})")
        self.btn_tab_lore.setText(f"World Lore ({n_lore})")

        if self._current_tab == "character":
            for char in self.codex_manager.characters:
                c_card = CharacterCardWidget(char, self.cards_container)
                c_card.insertRequested.connect(self.insertTextRequested.emit)
                c_card.editRequested.connect(self._edit_character)
                c_card.deleteRequested.connect(self._delete_character)
                self.cards_layout.insertWidget(self.cards_layout.count() - 1, c_card)
                self._char_cards[char.id] = c_card
        else:
            for lore in self.codex_manager.lore_entries:
                l_card = LoreCardWidget(lore, self.cards_container)
                l_card.insertRequested.connect(self.insertTextRequested.emit)
                l_card.editRequested.connect(self._edit_lore)
                l_card.deleteRequested.connect(self._delete_lore)
                self.cards_layout.insertWidget(self.cards_layout.count() - 1, l_card)
                self._lore_cards[lore.id] = l_card

        self._filter_cards(self.search_filter.text())

    def highlight_mention(self, text: str) -> None:
        """Live Mention Detection: scans text and illuminates matching character or lore cards."""
        if not text:
            for c in self._char_cards.values():
                c.set_mentioned(False)
            for l in self._lore_cards.values():
                l.set_mentioned(False)
            return

        t_lower = text.lower()

        # Check characters
        first_matched_char: Optional[CharacterCardWidget] = None
        for char_id, card in self._char_cards.items():
            char = card.character
            matched = (char.name.lower() in t_lower) or any(
                a.strip() and a.lower() in t_lower for a in char.aliases
            )
            card.set_mentioned(matched)
            if matched and not first_matched_char:
                first_matched_char = card

        # Check lore
        first_matched_lore: Optional[LoreCardWidget] = None
        for lore_id, card in self._lore_cards.items():
            lore = card.lore
            matched = (lore.title.lower() in t_lower) or any(
                a.strip() and a.lower() in t_lower for a in lore.aliases
            )
            card.set_mentioned(matched)
            if matched and not first_matched_lore:
                first_matched_lore = card

        # Bring matched card smoothly into view if on active tab
        if self._current_tab == "character" and first_matched_char:
            self.scroll_area.ensureWidgetVisible(first_matched_char, 10, 10)
        elif self._current_tab == "lore" and first_matched_lore:
            self.scroll_area.ensureWidgetVisible(first_matched_lore, 10, 10)

    def _show_add_dialog(self) -> None:
        dlg = EntityEditDialog(self.codex_manager, entity_type=self._current_tab, parent=self)
        if dlg.exec():
            self.refresh()
            self.entityUpdated.emit()

    def _edit_character(self, char_id: str) -> None:
        char = next((c for c in self.codex_manager.characters if c.id == char_id), None)
        if char:
            dlg = EntityEditDialog(self.codex_manager, entity_type="character", existing_entity=char, parent=self)
            if dlg.exec():
                self.refresh()
                self.entityUpdated.emit()

    def _delete_character(self, char_id: str) -> None:
        char = next((c for c in self.codex_manager.characters if c.id == char_id), None)
        if char:
            reply = QMessageBox.question(
                self, "Delete Character", f"Remove '{char.name}' from story codex?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.codex_manager.remove_character(char_id)
                self.refresh()
                self.entityUpdated.emit()

    def _edit_lore(self, lore_id: str) -> None:
        lore = next((l for l in self.codex_manager.lore_entries if l.id == lore_id), None)
        if lore:
            dlg = EntityEditDialog(self.codex_manager, entity_type="lore", existing_entity=lore, parent=self)
            if dlg.exec():
                self.refresh()
                self.entityUpdated.emit()

    def _delete_lore(self, lore_id: str) -> None:
        lore = next((l for l in self.codex_manager.lore_entries if l.id == lore_id), None)
        if lore:
            reply = QMessageBox.question(
                self, "Delete Lore", f"Remove '{lore.title}' from world codex?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.codex_manager.remove_lore(lore_id)
                self.refresh()
                self.entityUpdated.emit()

    def _filter_cards(self, query: str) -> None:
        q = (query or "").lower().strip()
        if self._current_tab == "character":
            for card in self._char_cards.values():
                c = card.character
                matched = (
                    not q
                    or q in c.name.lower()
                    or q in c.role.lower()
                    or any(q in a.lower() for a in c.aliases)
                )
                card.setVisible(matched)
        else:
            for card in self._lore_cards.values():
                l = card.lore
                matched = (
                    not q
                    or q in l.title.lower()
                    or q in l.category.lower()
                    or any(q in a.lower() for a in l.aliases)
                )
                card.setVisible(matched)
