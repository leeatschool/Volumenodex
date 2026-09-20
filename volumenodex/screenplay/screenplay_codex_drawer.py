"""Integrated Screenplay Codex Drawer: Screenplay-optimized Writers Codex push panel.

Contains cast dossiers, casting ideas, dialogue voice signatures, character arcs, scene sluglines,
lighting setups, setting notes, act beat outlines, and Live Mention Detection that illuminates cards in real time.
"""

from typing import Optional, List, Dict
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QToolButton, QScrollArea, QFrame, QLineEdit, QComboBox,
    QStackedWidget, QTextEdit, QDialog, QMessageBox, QButtonGroup
)

from volumenodex.ui.vector_icons import VectorIconFactory
from volumenodex.screenplay.screenplay_model import (
    ScreenplayCharacter, ScreenplayScene, ScreenplayAct, ScreenplayCodexManager
)


class ScreenplayEntityDialog(QDialog):
    """Modal dialog for creating or editing Cast Members, Scenes/Locations, and Act Beats."""

    def __init__(self, codex_manager: ScreenplayCodexManager, entity_type: str = "character", existing_entity=None, parent=None):
        super().__init__(parent)
        self.codex_manager = codex_manager
        self.entity_type = entity_type
        self.existing_entity = existing_entity

        titles = {
            "character": "Cast Member Dossier",
            "scene": "Scene Location & Atmosphere Profile",
            "act": "Act Outline & Beat Structure"
        }
        self.setWindowTitle(f"{'Edit' if existing_entity else 'New'} {titles.get(entity_type, 'Screenplay Entry')}")
        self.setFixedWidth(460)
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
        layout.setSpacing(10)

        # Header Title
        title_lbl = QLabel(self.windowTitle())
        title_lbl.setStyleSheet("color: #7aa2f7; font-size: 14px; font-weight: 700;")
        layout.addWidget(title_lbl)

        if self.entity_type == "character":
            # Character Name
            layout.addWidget(QLabel("Character Name (Screenplay UPPERCASE):"))
            self.txt_name = QLineEdit(self)
            self.txt_name.setPlaceholderText("e.g. DETECTIVE MARCUS VANCE or ELENA ROSTOVA")
            layout.addWidget(self.txt_name)

            # Role & Casting Ideas
            h_row1 = QHBoxLayout()
            v_role = QVBoxLayout()
            v_role.addWidget(QLabel("Role:"))
            self.role_combo = QComboBox(self)
            for r in ["Lead", "Protagonist", "Antagonist", "Supporting", "Minor", "Cameo", "Voiceover"]:
                self.role_combo.addItem(r)
            v_role.addWidget(self.role_combo)
            h_row1.addLayout(v_role)

            v_first = QVBoxLayout()
            v_first.addWidget(QLabel("First Scene Entrance:"))
            self.txt_first_scene = QLineEdit(self)
            self.txt_first_scene.setPlaceholderText("e.g. EXT. DOCKS - NIGHT")
            v_first.addWidget(self.txt_first_scene)
            h_row1.addLayout(v_first)
            layout.addLayout(h_row1)

            # Actor & Casting Notes
            layout.addWidget(QLabel("Actor & Casting Notes (timbre, archetype, physical presence):"))
            self.txt_actor = QLineEdit(self)
            self.txt_actor.setPlaceholderText("e.g. Late 40s, deep gravelly baritone voice, weathered face")
            layout.addWidget(self.txt_actor)

            # Dialogue Voice & Mannerisms
            layout.addWidget(QLabel("Dialogue Voice (cadence, contractions, speech mannerisms):"))
            self.txt_voice = QLineEdit(self)
            self.txt_voice.setPlaceholderText("e.g. Speaks in short, curt sentences. Never uses slang.")
            layout.addWidget(self.txt_voice)

            # Character Arc & Dramatic Need
            layout.addWidget(QLabel("Character Arc & Flaw:"))
            self.txt_arc = QLineEdit(self)
            self.txt_arc.setPlaceholderText("e.g. Obsessed with redemption, must learn to trust his partner")
            layout.addWidget(self.txt_arc)

            # Wardrobe & Visual Signature
            layout.addWidget(QLabel("Wardrobe & Visual Signature:"))
            self.txt_wardrobe = QLineEdit(self)
            self.txt_wardrobe.setPlaceholderText("e.g. Scuffed charcoal trench coat, vintage pocket watch")
            layout.addWidget(self.txt_wardrobe)

            # Aliases & Mentions
            layout.addWidget(QLabel("Aliases / Mention Keywords (comma-separated):"))
            self.txt_aliases = QLineEdit(self)
            self.txt_aliases.setPlaceholderText("e.g. Marcus, Vance, Detective")
            layout.addWidget(self.txt_aliases)

        elif self.entity_type == "scene":
            # Scene Heading (Slugline)
            layout.addWidget(QLabel("Scene Heading / Slugline:"))
            self.txt_heading = QLineEdit(self)
            self.txt_heading.setPlaceholderText("e.g. EXT. SUBURBAN HOME - NIGHT")
            layout.addWidget(self.txt_heading)

            h_slug = QHBoxLayout()
            v_type = QVBoxLayout()
            v_type.addWidget(QLabel("Int / Ext:"))
            self.combo_type = QComboBox(self)
            for t in ["EXT.", "INT.", "INT./EXT.", "EST."]:
                self.combo_type.addItem(t)
            v_type.addWidget(self.combo_type)
            h_slug.addLayout(v_type)

            v_loc = QVBoxLayout()
            v_loc.addWidget(QLabel("Location Name:"))
            self.txt_loc = QLineEdit(self)
            self.txt_loc.setPlaceholderText("SUBURBAN HOME")
            v_loc.addWidget(self.txt_loc)
            h_slug.addLayout(v_loc, stretch=1)

            v_tod = QVBoxLayout()
            v_tod.addWidget(QLabel("Time of Day:"))
            self.combo_tod = QComboBox(self)
            for d in ["DAY", "NIGHT", "DUSK", "DAWN", "CONTINUOUS", "LATER", "MOMENTS LATER"]:
                self.combo_tod.addItem(d)
            v_tod.addWidget(self.combo_tod)
            h_slug.addLayout(v_tod)
            layout.addLayout(h_slug)

            # Lighting Setup
            layout.addWidget(QLabel("Lighting Setup & Direction:"))
            self.txt_lighting = QLineEdit(self)
            self.txt_lighting.setPlaceholderText("e.g. LOW LIGHTING, LIT BY STREET LIGHTS ALONE")
            layout.addWidget(self.txt_lighting)

            # Setting Notes & Atmosphere
            layout.addWidget(QLabel("Setting Notes & Atmospheric Texture:"))
            self.txt_setting = QTextEdit(self)
            self.txt_setting.setFixedHeight(55)
            self.txt_setting.setPlaceholderText("Environmental sensory details, weather, architecture, mood...")
            layout.addWidget(self.txt_setting)

            # Stage & Camera Directions
            layout.addWidget(QLabel("Stage & Camera Directions:"))
            self.txt_camera = QLineEdit(self)
            self.txt_camera.setPlaceholderText("e.g. Low tracking shot following headlights across rain-slick asphalt")
            layout.addWidget(self.txt_camera)

            # Props
            layout.addWidget(QLabel("Props in Scene:"))
            self.txt_props = QLineEdit(self)
            self.txt_props.setPlaceholderText("e.g. [PROP: Encrypted USB drive, steaming mug of coffee]")
            layout.addWidget(self.txt_props)

        elif self.entity_type == "act":
            # Act Number
            h_act = QHBoxLayout()
            v_num = QVBoxLayout()
            v_num.addWidget(QLabel("Act / Section:"))
            self.combo_act_num = QComboBox(self)
            for a in ["COLD OPEN", "ACT I", "ACT II - PART 1", "ACT II - PART 2", "ACT III", "TAG / EPILOGUE"]:
                self.combo_act_num.addItem(a)
            v_num.addWidget(self.combo_act_num)
            h_act.addLayout(v_num)

            v_title = QVBoxLayout()
            v_title.addWidget(QLabel("Act Beat Title:"))
            self.txt_act_title = QLineEdit(self)
            self.txt_act_title.setPlaceholderText("e.g. The Waterfront Stakeout")
            v_title.addWidget(self.txt_act_title)
            h_act.addLayout(v_title, stretch=1)
            layout.addLayout(h_act)

            layout.addWidget(QLabel("Turning Point / Major Reversal:"))
            self.txt_turning = QLineEdit(self)
            self.txt_turning.setPlaceholderText("e.g. Marcus uncovers the encrypted ledger implicating his captain")
            layout.addWidget(self.txt_turning)

            layout.addWidget(QLabel("Act Beat Synopsis:"))
            self.txt_act_synopsis = QTextEdit(self)
            self.txt_act_synopsis.setFixedHeight(70)
            self.txt_act_synopsis.setPlaceholderText("Summary of scene goals, narrative momentum, and escalations...")
            layout.addWidget(self.txt_act_synopsis)

        # Buttons
        h_btn = QHBoxLayout()
        h_btn.addStretch()

        btn_cancel = QPushButton("Cancel", self)
        btn_cancel.setStyleSheet("background-color: #24283b; color: #a9b1d6;")
        btn_cancel.clicked.connect(self.reject)
        h_btn.addWidget(btn_cancel)

        btn_save = QPushButton("Save Entry", self)
        btn_save.setStyleSheet("background-color: #7aa2f7; color: #15161e; font-weight: 700;")
        btn_save.clicked.connect(self._save_and_close)
        h_btn.addWidget(btn_save)
        layout.addLayout(h_btn)

    def _load_existing(self) -> None:
        if self.entity_type == "character":
            c: ScreenplayCharacter = self.existing_entity
            self.txt_name.setText(c.name)
            idx = self.role_combo.findText(c.role)
            if idx >= 0:
                self.role_combo.setCurrentIndex(idx)
            self.txt_first_scene.setText(c.first_scene)
            self.txt_actor.setText(c.actor_notes)
            self.txt_voice.setText(c.dialogue_voice)
            self.txt_arc.setText(c.character_arc)
            self.txt_wardrobe.setText(c.wardrobe_notes)
            self.txt_aliases.setText(", ".join(c.aliases))
        elif self.entity_type == "scene":
            s: ScreenplayScene = self.existing_entity
            self.txt_heading.setText(s.heading)
            idx_t = self.combo_type.findText(s.int_ext)
            if idx_t >= 0:
                self.combo_type.setCurrentIndex(idx_t)
            self.txt_loc.setText(s.location_name)
            idx_d = self.combo_tod.findText(s.time_of_day)
            if idx_d >= 0:
                self.combo_tod.setCurrentIndex(idx_d)
            self.txt_lighting.setText(s.lighting_setup)
            self.txt_setting.setPlainText(s.setting_notes)
            self.txt_camera.setText(s.stage_directions)
            self.txt_props.setText(s.props)
        elif self.entity_type == "act":
            a: ScreenplayAct = self.existing_entity
            idx_a = self.combo_act_num.findText(a.act_number)
            if idx_a >= 0:
                self.combo_act_num.setCurrentIndex(idx_a)
            self.txt_act_title.setText(a.title)
            self.txt_turning.setText(a.turning_point)
            self.txt_act_synopsis.setPlainText(a.synopsis)

    def _save_and_close(self) -> None:
        if self.entity_type == "character":
            name = self.txt_name.text().strip().upper()
            if not name:
                QMessageBox.warning(self, "Validation", "Please provide a character name.")
                return
            aliases = [a.strip() for a in self.txt_aliases.text().split(",") if a.strip()]
            if self.existing_entity:
                c = self.existing_entity
                c.name = name
                c.role = self.role_combo.currentText()
                c.first_scene = self.txt_first_scene.text().strip()
                c.actor_notes = self.txt_actor.text().strip()
                c.dialogue_voice = self.txt_voice.text().strip()
                c.character_arc = self.txt_arc.text().strip()
                c.wardrobe_notes = self.txt_wardrobe.text().strip()
                c.aliases = aliases
            else:
                c = ScreenplayCharacter(
                    name=name,
                    role=self.role_combo.currentText(),
                    first_scene=self.txt_first_scene.text().strip(),
                    actor_notes=self.txt_actor.text().strip(),
                    dialogue_voice=self.txt_voice.text().strip(),
                    character_arc=self.txt_arc.text().strip(),
                    wardrobe_notes=self.txt_wardrobe.text().strip(),
                    aliases=aliases
                )
                self.codex_manager.add_character(c)

        elif self.entity_type == "scene":
            heading = self.txt_heading.text().strip().upper()
            if not heading:
                heading = f"{self.combo_type.currentText()} {self.txt_loc.text().strip().upper()} - {self.combo_tod.currentText()}"
            if not heading.strip():
                QMessageBox.warning(self, "Validation", "Please specify a scene heading or location.")
                return
            if self.existing_entity:
                s = self.existing_entity
                s.heading = heading
                s.int_ext = self.combo_type.currentText()
                s.location_name = self.txt_loc.text().strip().upper() or "LOCATION"
                s.time_of_day = self.combo_tod.currentText()
                s.lighting_setup = self.txt_lighting.text().strip()
                s.setting_notes = self.txt_setting.toPlainText().strip()
                s.stage_directions = self.txt_camera.text().strip()
                s.props = self.txt_props.text().strip()
            else:
                s = ScreenplayScene(
                    heading=heading,
                    int_ext=self.combo_type.currentText(),
                    location_name=self.txt_loc.text().strip().upper() or "LOCATION",
                    time_of_day=self.combo_tod.currentText(),
                    lighting_setup=self.txt_lighting.text().strip(),
                    setting_notes=self.txt_setting.toPlainText().strip(),
                    stage_directions=self.txt_camera.text().strip(),
                    props=self.txt_props.text().strip()
                )
                self.codex_manager.add_scene(s)

        elif self.entity_type == "act":
            title = self.txt_act_title.text().strip()
            if not title:
                QMessageBox.warning(self, "Validation", "Please provide an act beat title.")
                return
            if self.existing_entity:
                a = self.existing_entity
                a.act_number = self.combo_act_num.currentText()
                a.title = title
                a.turning_point = self.txt_turning.text().strip()
                a.synopsis = self.txt_act_synopsis.toPlainText().strip()
            else:
                a = ScreenplayAct(
                    act_number=self.combo_act_num.currentText(),
                    title=title,
                    turning_point=self.txt_turning.text().strip(),
                    synopsis=self.txt_act_synopsis.toPlainText().strip()
                )
                self.codex_manager.add_act(a)

        self.accept()


# ==============================================================================
# CARD WIDGETS
# ==============================================================================

class ScreenplayCharacterCard(QFrame):
    """Visual dossier card for a screenplay character / cast member."""

    insertRequested = Signal(str)
    editRequested = Signal(str)
    deleteRequested = Signal(str)

    def __init__(self, character: ScreenplayCharacter, parent=None):
        super().__init__(parent)
        self.char_data = character
        self.setObjectName("ScreenplayCharCard")
        self._init_ui()

    def _init_ui(self) -> None:
        self.setStyleSheet("""
            QFrame#ScreenplayCharCard {
                background-color: #1a1b26;
                border: 1px solid #292e42;
                border-radius: 6px;
                padding: 4px;
            }
            QFrame#ScreenplayCharCard:hover {
                border-color: #414868;
                background-color: #1f2335;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(5)

        # Top Row: Name + Role Badge + Mention count
        top_row = QHBoxLayout()
        name_lbl = QLabel(self.char_data.name)
        name_lbl.setStyleSheet("color: #7aa2f7; font-weight: 700; font-size: 12px; letter-spacing: 0.5px;")
        top_row.addWidget(name_lbl, stretch=1)

        self.badge_mention = QLabel("0", self)
        self.badge_mention.setStyleSheet("""
            background-color: #24283b;
            color: #787c99;
            font-size: 9px;
            font-weight: 700;
            padding: 1px 5px;
            border-radius: 3px;
        """)
        top_row.addWidget(self.badge_mention)

        role_badge = QLabel(self.char_data.role)
        role_badge.setStyleSheet("""
            background-color: #2ac3de22;
            color: #2ac3de;
            font-size: 10px;
            font-weight: 600;
            padding: 2px 6px;
            border-radius: 4px;
            border: 1px solid #2ac3de44;
        """)
        top_row.addWidget(role_badge)
        layout.addLayout(top_row)

        # Details: Actor Notes, Voice, Arc
        if self.char_data.actor_notes:
            lbl = QLabel(f"<b>Casting:</b> {self.char_data.actor_notes}")
            lbl.setWordWrap(True)
            lbl.setStyleSheet("color: #9aa5ce; font-size: 10px;")
            layout.addWidget(lbl)

        if self.char_data.dialogue_voice:
            lbl_v = QLabel(f"<b>Voice:</b> {self.char_data.dialogue_voice}")
            lbl_v.setWordWrap(True)
            lbl_v.setStyleSheet("color: #bb9af7; font-size: 10px;")
            layout.addWidget(lbl_v)

        if self.char_data.wardrobe_notes:
            lbl_w = QLabel(f"<b>Wardrobe:</b> {self.char_data.wardrobe_notes}")
            lbl_w.setWordWrap(True)
            lbl_w.setStyleSheet("color: #565f89; font-size: 10px;")
            layout.addWidget(lbl_w)

        # Action Buttons
        btn_bar = QHBoxLayout()
        btn_bar.setSpacing(4)

        btn_insert = QPushButton("💬 Dialogue", self)
        btn_insert.setToolTip("Insert Character Name formatted for Dialogue")
        btn_insert.setStyleSheet("background-color: #24283b; color: #7aa2f7; font-size: 10px; padding: 3px 6px; border-radius: 3px;")
        btn_insert.clicked.connect(lambda: self.insertRequested.emit(f"\n{self.char_data.name}\n"))
        btn_bar.addWidget(btn_insert)

        btn_vo = QPushButton("(V.O.)", self)
        btn_vo.setToolTip("Insert Voiceover Header")
        btn_vo.setStyleSheet("background-color: #24283b; color: #bb9af7; font-size: 10px; padding: 3px 5px; border-radius: 3px;")
        btn_vo.clicked.connect(lambda: self.insertRequested.emit(f"\n{self.char_data.name} (V.O.)\n"))
        btn_bar.addWidget(btn_vo)

        btn_bar.addStretch()

        btn_edit = QToolButton(self)
        btn_edit.setIcon(VectorIconFactory.create_icon("gear", "#787c99", 14))
        btn_edit.setToolTip("Edit Cast Member")
        btn_edit.setFixedSize(20, 20)
        btn_edit.clicked.connect(lambda: self.editRequested.emit(self.char_data.id))
        btn_bar.addWidget(btn_edit)

        btn_del = QToolButton(self)
        btn_del.setIcon(VectorIconFactory.create_icon("cut", "#f7768e", 14))
        btn_del.setToolTip("Remove from Codex")
        btn_del.setFixedSize(20, 20)
        btn_del.clicked.connect(lambda: self.deleteRequested.emit(self.char_data.id))
        btn_bar.addWidget(btn_del)

        layout.addLayout(btn_bar)

    def set_mention_highlight(self, active: bool, count: int = 0) -> None:
        if active:
            self.setStyleSheet("""
                QFrame#ScreenplayCharCard {
                    background-color: #202b4d;
                    border: 1px solid #7aa2f7;
                    border-radius: 6px;
                }
            """)
            self.badge_mention.setText(f"{count} in script")
            self.badge_mention.setStyleSheet("background-color: #7aa2f7; color: #15161e; font-weight: 700; border-radius: 3px;")
        else:
            self.setStyleSheet("""
                QFrame#ScreenplayCharCard {
                    background-color: #1a1b26;
                    border: 1px solid #292e42;
                    border-radius: 6px;
                }
                QFrame#ScreenplayCharCard:hover {
                    border-color: #414868;
                }
            """)
            self.badge_mention.setText(f"{count}" if count > 0 else "")
            self.badge_mention.setStyleSheet("background-color: #24283b; color: #787c99; font-size: 9px; border-radius: 3px;")


class ScreenplaySceneCard(QFrame):
    """Visual card for a scene location, lighting setup, and environment."""

    insertRequested = Signal(str)
    editRequested = Signal(str)
    deleteRequested = Signal(str)

    def __init__(self, scene: ScreenplayScene, parent=None):
        super().__init__(parent)
        self.scene_data = scene
        self.setObjectName("ScreenplaySceneCard")
        self._init_ui()

    def _init_ui(self) -> None:
        self.setStyleSheet("""
            QFrame#ScreenplaySceneCard {
                background-color: #1a1b26;
                border: 1px solid #292e42;
                border-radius: 6px;
                padding: 4px;
            }
            QFrame#ScreenplaySceneCard:hover {
                border-color: #414868;
                background-color: #1f2335;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(5)

        # Header: Heading + TOD Badge
        top_row = QHBoxLayout()
        head_lbl = QLabel(self.scene_data.heading)
        head_lbl.setStyleSheet("color: #e0af68; font-weight: 700; font-size: 11px; letter-spacing: 0.5px;")
        head_lbl.setWordWrap(True)
        top_row.addWidget(head_lbl, stretch=1)

        tod_badge = QLabel(self.scene_data.time_of_day)
        tod_badge.setStyleSheet("""
            background-color: #e0af6822;
            color: #e0af68;
            font-size: 9px;
            font-weight: 700;
            padding: 2px 5px;
            border-radius: 3px;
        """)
        top_row.addWidget(tod_badge)
        layout.addLayout(top_row)

        # Lighting prompt
        if self.scene_data.lighting_setup:
            lbl_l = QLabel(f"💡 <i>{self.scene_data.lighting_setup}</i>")
            lbl_l.setWordWrap(True)
            lbl_l.setStyleSheet("color: #ff9e64; font-size: 10px;")
            layout.addWidget(lbl_l)

        # Setting notes
        if self.scene_data.setting_notes:
            lbl_s = QLabel(self.scene_data.setting_notes)
            lbl_s.setWordWrap(True)
            lbl_s.setStyleSheet("color: #9aa5ce; font-size: 10px;")
            layout.addWidget(lbl_s)

        # Props
        if self.scene_data.props:
            lbl_p = QLabel(self.scene_data.props)
            lbl_p.setWordWrap(True)
            lbl_p.setStyleSheet("color: #7dcfff; font-size: 9px;")
            layout.addWidget(lbl_p)

        # Buttons
        btn_bar = QHBoxLayout()
        btn_bar.setSpacing(4)

        btn_slug = QPushButton("🎬 Insert Heading", self)
        btn_slug.setStyleSheet("background-color: #24283b; color: #e0af68; font-size: 10px; padding: 3px 6px; border-radius: 3px;")
        btn_slug.clicked.connect(lambda: self.insertRequested.emit(f"\n{self.scene_data.heading}\n"))
        btn_bar.addWidget(btn_slug)

        if self.scene_data.lighting_setup:
            btn_light = QPushButton("💡 Light", self)
            btn_light.setStyleSheet("background-color: #24283b; color: #ff9e64; font-size: 10px; padding: 3px 5px; border-radius: 3px;")
            btn_light.clicked.connect(lambda: self.insertRequested.emit(f"{self.scene_data.lighting_setup}\n"))
            btn_bar.addWidget(btn_light)

        btn_bar.addStretch()

        btn_edit = QToolButton(self)
        btn_edit.setIcon(VectorIconFactory.create_icon("gear", "#787c99", 14))
        btn_edit.setToolTip("Edit Scene Profile")
        btn_edit.setFixedSize(20, 20)
        btn_edit.clicked.connect(lambda: self.editRequested.emit(self.scene_data.id))
        btn_bar.addWidget(btn_edit)

        btn_del = QToolButton(self)
        btn_del.setIcon(VectorIconFactory.create_icon("cut", "#f7768e", 14))
        btn_del.setToolTip("Remove Scene")
        btn_del.setFixedSize(20, 20)
        btn_del.clicked.connect(lambda: self.deleteRequested.emit(self.scene_data.id))
        btn_bar.addWidget(btn_del)

        layout.addLayout(btn_bar)


class ScreenplayActCard(QFrame):
    """Visual card for an Act outline beat and turning point."""

    insertRequested = Signal(str)
    editRequested = Signal(str)
    deleteRequested = Signal(str)

    def __init__(self, act: ScreenplayAct, parent=None):
        super().__init__(parent)
        self.act_data = act
        self.setObjectName("ScreenplayActCard")
        self._init_ui()

    def _init_ui(self) -> None:
        self.setStyleSheet("""
            QFrame#ScreenplayActCard {
                background-color: #1a1b26;
                border: 1px solid #292e42;
                border-radius: 6px;
                padding: 4px;
            }
            QFrame#ScreenplayActCard:hover {
                border-color: #414868;
                background-color: #1f2335;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(5)

        # Header: Act Number + Title
        top_row = QHBoxLayout()
        act_num = QLabel(self.act_data.act_number)
        act_num.setStyleSheet("color: #9ece6a; font-weight: 700; font-size: 11px;")
        top_row.addWidget(act_num)

        title_lbl = QLabel(self.act_data.title)
        title_lbl.setStyleSheet("color: #c0caf5; font-weight: 600; font-size: 11px;")
        top_row.addWidget(title_lbl, stretch=1)
        layout.addLayout(top_row)

        if self.act_data.turning_point:
            lbl_tp = QLabel(f"⚡ <b>Turning Point:</b> {self.act_data.turning_point}")
            lbl_tp.setWordWrap(True)
            lbl_tp.setStyleSheet("color: #f7768e; font-size: 10px;")
            layout.addWidget(lbl_tp)

        if self.act_data.synopsis:
            lbl_syn = QLabel(self.act_data.synopsis)
            lbl_syn.setWordWrap(True)
            lbl_syn.setStyleSheet("color: #9aa5ce; font-size: 10px;")
            layout.addWidget(lbl_syn)

        # Buttons
        btn_bar = QHBoxLayout()
        btn_act = QPushButton("📑 Insert Act Marker", self)
        btn_act.setStyleSheet("background-color: #24283b; color: #9ece6a; font-size: 10px; padding: 3px 6px; border-radius: 3px;")
        btn_act.clicked.connect(lambda: self.insertRequested.emit(f"\n\n{self.act_data.act_number}: {self.act_data.title.upper()}\n\n"))
        btn_bar.addWidget(btn_act)

        btn_bar.addStretch()

        btn_edit = QToolButton(self)
        btn_edit.setIcon(VectorIconFactory.create_icon("gear", "#787c99", 14))
        btn_edit.setToolTip("Edit Act Beat")
        btn_edit.setFixedSize(20, 20)
        btn_edit.clicked.connect(lambda: self.editRequested.emit(self.act_data.id))
        btn_bar.addWidget(btn_edit)

        btn_del = QToolButton(self)
        btn_del.setIcon(VectorIconFactory.create_icon("cut", "#f7768e", 14))
        btn_del.setToolTip("Remove Act Beat")
        btn_del.setFixedSize(20, 20)
        btn_del.clicked.connect(lambda: self.deleteRequested.emit(self.act_data.id))
        btn_bar.addWidget(btn_del)

        layout.addLayout(btn_bar)


# ==============================================================================
# MAIN DRAWER COMPONENT
# ==============================================================================

class ScreenplayCodexDrawer(QWidget):
    """Collapsible Right Drawer for Screenplay Worldbuilding, Cast, Scenes, and Live Mentions."""

    insertTextRequested = Signal(str)
    collapsedChanged = Signal(bool)
    entityUpdated = Signal()
    paletteSwitchRequested = Signal()

    EXPANDED_WIDTH = 320
    COLLAPSED_WIDTH = 32

    def __init__(self, codex_manager: ScreenplayCodexManager, parent=None):
        super().__init__(parent)
        self.codex_manager = codex_manager
        self.is_collapsed = False
        self._current_tab = "character"  # "character", "scene", "act"

        self._char_cards: Dict[str, ScreenplayCharacterCard] = {}
        self._scene_cards: Dict[str, ScreenplaySceneCard] = {}
        self._act_cards: Dict[str, ScreenplayActCard] = {}

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
        self.btn_collapse.setToolTip("Collapse Screenplay Codex")
        self.btn_collapse.clicked.connect(self.toggle_collapsed)
        header_bar.addWidget(self.btn_collapse)

        icon_lbl = QLabel(self.expanded_page)
        icon_lbl.setPixmap(VectorIconFactory.create_icon("codex", "#7aa2f7", 18).pixmap(18, 18))
        header_bar.addWidget(icon_lbl)

        title_lbl = QLabel("SCREENPLAY CODEX", self.expanded_page)
        title_lbl.setStyleSheet("color: #c0caf5; font-size: 11px; font-weight: 700; letter-spacing: 0.8px;")
        header_bar.addWidget(title_lbl)

        header_bar.addStretch()

        # Switch to Drag & Drop Terms / Phrases Palette
        self.btn_goto_palette = QPushButton("📋 Phrases", self.expanded_page)
        self.btn_goto_palette.setToolTip("Switch to Drag & Drop Terms / Phrases Palette")
        self.btn_goto_palette.setStyleSheet("""
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
        self.btn_goto_palette.clicked.connect(self.paletteSwitchRequested.emit)
        header_bar.addWidget(self.btn_goto_palette)

        exp_layout.addLayout(header_bar)

        # 2. Segmented Pill Switcher (Cast vs Scenes vs Acts)
        seg_layout = QHBoxLayout()
        seg_layout.setContentsMargins(0, 0, 0, 0)
        seg_layout.setSpacing(4)

        self.btn_tab_chars = QPushButton("Cast & Characters", self.expanded_page)
        self.btn_tab_chars.setCheckable(True)
        self.btn_tab_chars.setChecked(True)
        self.btn_tab_chars.clicked.connect(lambda: self._switch_tab("character"))

        self.btn_tab_scenes = QPushButton("Scenes & Locations", self.expanded_page)
        self.btn_tab_scenes.setCheckable(True)
        self.btn_tab_scenes.setChecked(False)
        self.btn_tab_scenes.clicked.connect(lambda: self._switch_tab("scene"))

        self.btn_tab_acts = QPushButton("Acts & Beats", self.expanded_page)
        self.btn_tab_acts.setCheckable(True)
        self.btn_tab_acts.setChecked(False)
        self.btn_tab_acts.clicked.connect(lambda: self._switch_tab("act"))

        self.tab_group = QButtonGroup(self)
        self.tab_group.addButton(self.btn_tab_chars)
        self.tab_group.addButton(self.btn_tab_scenes)
        self.tab_group.addButton(self.btn_tab_acts)

        pill_style = """
            QPushButton {
                background-color: #1f2335;
                color: #787c99;
                font-size: 10px;
                font-weight: 600;
                padding: 4px 6px;
                border: 1px solid #292e42;
                border-radius: 4px;
            }
            QPushButton:checked {
                background-color: #7aa2f7;
                color: #15161e;
                border-color: #7aa2f7;
            }
            QPushButton:hover:!checked {
                background-color: #24283b;
                color: #c0caf5;
            }
        """
        self.btn_tab_chars.setStyleSheet(pill_style)
        self.btn_tab_scenes.setStyleSheet(pill_style)
        self.btn_tab_acts.setStyleSheet(pill_style)

        seg_layout.addWidget(self.btn_tab_chars)
        seg_layout.addWidget(self.btn_tab_scenes)
        seg_layout.addWidget(self.btn_tab_acts)
        exp_layout.addLayout(seg_layout)

        # 3. Action Bar: Search Filter & "+ New" Button
        act_bar = QHBoxLayout()
        act_bar.setSpacing(6)

        self.search_filter = QLineEdit(self.expanded_page)
        self.search_filter.setPlaceholderText("Filter cast, scenes, beats...")
        self.search_filter.setStyleSheet("""
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
        self.search_filter.textChanged.connect(self._filter_cards)
        act_bar.addWidget(self.search_filter, stretch=1)

        self.btn_add = QPushButton("+ Add", self.expanded_page)
        self.btn_add.setStyleSheet("""
            QPushButton {
                background-color: #7aa2f7;
                color: #15161e;
                font-size: 10px;
                font-weight: 700;
                padding: 4px 10px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #89b4fa;
            }
        """)
        self.btn_add.clicked.connect(self._on_add_entity)
        act_bar.addWidget(self.btn_add)
        exp_layout.addLayout(act_bar)

        # 4. Scroll Area with Cards
        self.scroll_area = QScrollArea(self.expanded_page)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.cards_container = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(6)
        self.cards_layout.addStretch()

        self.scroll_area.setWidget(self.cards_container)
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
        self.btn_expand.setToolTip("Expand Screenplay Codex")
        self.btn_expand.clicked.connect(self.toggle_collapsed)
        col_layout.addWidget(self.btn_expand)

        self.btn_strip_icon = QToolButton(self.collapsed_page)
        self.btn_strip_icon.setIcon(VectorIconFactory.create_icon("codex", "#787c99", 18))
        self.btn_strip_icon.setIconSize(QSize(18, 18))
        self.btn_strip_icon.setFixedSize(24, 24)
        self.btn_strip_icon.setToolTip("Screenplay Codex")
        self.btn_strip_icon.clicked.connect(self.toggle_collapsed)
        col_layout.addWidget(self.btn_strip_icon)

        col_layout.addStretch()
        self.stack.addWidget(self.collapsed_page)
        self.stack.setCurrentWidget(self.expanded_page)

    @property
    def active_tab(self) -> str:
        return getattr(self, "_current_tab", "character")

    def _switch_tab(self, tab: str) -> None:
        self._current_tab = tab
        btn_labels = {
            "character": "+ Cast Member",
            "scene": "+ Scene Location",
            "act": "+ Act Beat"
        }
        self.btn_add.setText(btn_labels.get(tab, "+ Add"))
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
        """Rebuilds cards matching current active tab and filter."""
        # Clear existing cards
        for card in list(self._char_cards.values()) + list(self._scene_cards.values()) + list(self._act_cards.values()):
            self.cards_layout.removeWidget(card)
            card.deleteLater()
        self._char_cards.clear()
        self._scene_cards.clear()
        self._act_cards.clear()

        filter_text = self.search_filter.text().strip().lower()

        if self._current_tab == "character":
            for char in self.codex_manager.characters:
                if filter_text and filter_text not in char.name.lower() and not any(filter_text in a.lower() for a in char.aliases):
                    continue
                card = ScreenplayCharacterCard(char, self.cards_container)
                card.insertRequested.connect(self.insertTextRequested.emit)
                card.editRequested.connect(self._on_edit_entity)
                card.deleteRequested.connect(self._on_delete_entity)
                self._char_cards[char.id] = card
                self.cards_layout.insertWidget(self.cards_layout.count() - 1, card)

        elif self._current_tab == "scene":
            for scene in self.codex_manager.scenes:
                if filter_text and filter_text not in scene.heading.lower() and filter_text not in scene.location_name.lower():
                    continue
                card = ScreenplaySceneCard(scene, self.cards_container)
                card.insertRequested.connect(self.insertTextRequested.emit)
                card.editRequested.connect(self._on_edit_entity)
                card.deleteRequested.connect(self._on_delete_entity)
                self._scene_cards[scene.id] = card
                self.cards_layout.insertWidget(self.cards_layout.count() - 1, card)

        elif self._current_tab == "act":
            for act in self.codex_manager.acts:
                if filter_text and filter_text not in act.title.lower() and filter_text not in act.act_number.lower():
                    continue
                card = ScreenplayActCard(act, self.cards_container)
                card.insertRequested.connect(self.insertTextRequested.emit)
                card.editRequested.connect(self._on_edit_entity)
                card.deleteRequested.connect(self._on_delete_entity)
                self._act_cards[act.id] = card
                self.cards_layout.insertWidget(self.cards_layout.count() - 1, card)

    def _filter_cards(self) -> None:
        self.refresh()

    def _on_add_entity(self) -> None:
        dlg = ScreenplayEntityDialog(self.codex_manager, entity_type=self._current_tab, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.refresh()
            self.entityUpdated.emit()

    def _on_edit_entity(self, entity_id: str) -> None:
        existing = None
        if self._current_tab == "character":
            existing = next((c for c in self.codex_manager.characters if c.id == entity_id), None)
        elif self._current_tab == "scene":
            existing = next((s for s in self.codex_manager.scenes if s.id == entity_id), None)
        elif self._current_tab == "act":
            existing = next((a for a in self.codex_manager.acts if a.id == entity_id), None)

        if existing:
            dlg = ScreenplayEntityDialog(self.codex_manager, entity_type=self._current_tab, existing_entity=existing, parent=self)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                self.refresh()
                self.entityUpdated.emit()

    def _on_delete_entity(self, entity_id: str) -> None:
        if self._current_tab == "character":
            self.codex_manager.remove_character(entity_id)
        elif self._current_tab == "scene":
            self.codex_manager.remove_scene(entity_id)
        elif self._current_tab == "act":
            self.codex_manager.remove_act(entity_id)
        self.refresh()
        self.entityUpdated.emit()

    def highlight_mentions(self, text: str) -> None:
        """Live mention tracker: highlights cards whose names appear in the manuscript."""
        if not text:
            return
        t_lower = text.lower()

        for char_id, card in self._char_cards.items():
            name = card.char_data.name.lower()
            cnt = t_lower.count(name)
            for alias in card.char_data.aliases:
                if alias.strip():
                    cnt += t_lower.count(alias.lower())
            card.set_mention_highlight(cnt > 0, cnt)
