"""Dialog for selecting preset writing pets or crafting a custom companion with vector figure previews."""

from typing import Dict, Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QIcon, QPixmap
from PySide6.QtWidgets import (
    QDialog, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLabel, QLineEdit, QSpinBox, QCheckBox,
    QPushButton, QRadioButton, QButtonGroup, QFileDialog, QGroupBox,
    QComboBox
)

from volumenodex.pet.pet_model import PetProfile, PetMood, DEFAULT_PETS
from volumenodex.pet.companion_figures import CompanionFigureRenderer


class PetSelectionDialog(QDialog):
    """Allows selecting a preset writing companion or creating a custom writing pet."""

    petSelected = Signal(PetProfile)
    hideCompanionRequested = Signal()

    def __init__(self, current_pet: PetProfile, custom_pets: Dict[str, PetProfile] = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Scribe Companion — Choose or Create Writing Pet")
        self.resize(600, 520)
        self.current_pet = current_pet
        self.custom_pets = custom_pets or {}
        self._custom_image_path: Optional[str] = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        self.tabs = QTabWidget(self)
        layout.addWidget(self.tabs)

        self._build_roster_tab()
        self._build_creator_tab()

        # Bottom Dialog Actions
        h_actions = QHBoxLayout()

        self.btn_hide = QPushButton("Hide / Disable Companion")
        self.btn_hide.setToolTip("Disables the floating companion widget completely.")
        self.btn_hide.setStyleSheet("""
            QPushButton {
                background-color: #202230;
                color: #f7768e;
                border: 1px solid #3c4058;
                padding: 6px 14px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: rgba(247, 118, 142, 0.15);
                border: 1px solid #f7768e;
            }
        """)
        self.btn_hide.clicked.connect(self._on_hide_companion)
        h_actions.addWidget(self.btn_hide)

        h_actions.addStretch()

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #24283b;
                color: #c0caf5;
                border: 1px solid #3b4261;
                border-radius: 6px;
                padding: 6px 16px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #2e344e;
                color: #ffffff;
                border-color: #7aa2f7;
            }
        """)
        self.btn_cancel.clicked.connect(self.reject)
        h_actions.addWidget(self.btn_cancel)

        self.btn_apply = QPushButton("Set Active Companion")
        self.btn_apply.setStyleSheet("""
            QPushButton {
                background-color: #7aa2f7;
                color: #1a1b26;
                font-weight: bold;
                padding: 6px 16px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #89b4fa;
            }
        """)
        self.btn_apply.clicked.connect(self._on_apply)
        h_actions.addWidget(self.btn_apply)

        layout.addLayout(h_actions)

    def _build_roster_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        lbl_desc = QLabel("Select your active writing companion. Each figure embodies a unique personality and editorial insight style.")
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet("color: #787c99; font-size: 11px;")
        layout.addWidget(lbl_desc)

        grid = QGridLayout()
        grid.setSpacing(10)
        grid.setContentsMargins(0, 0, 0, 0)

        self.roster_group = QButtonGroup(self)
        current_id = getattr(self.current_pet, 'id', None)

        all_pets = list(DEFAULT_PETS.values()) + list(self.custom_pets.values())

        for idx, pet in enumerate(all_pets):
            box = QGroupBox()
            box.setStyleSheet("""
                QGroupBox {
                    background-color: #191a26;
                    border: 1px solid #2f334d;
                    border-radius: 10px;
                    padding: 8px;
                }
                QGroupBox:hover {
                    border: 1px solid #7aa2f7;
                }
            """)
            box_layout = QHBoxLayout(box)
            box_layout.setContentsMargins(8, 6, 8, 6)
            box_layout.setSpacing(8)

            radio = QRadioButton()
            radio.setChecked(pet.id == current_id)
            self.roster_group.addButton(radio, idx)
            box_layout.addWidget(radio)

            # High-Resolution Illustrated Vector Figure
            lbl_figure = QLabel()
            pix = CompanionFigureRenderer.render_figure(
                pet.id,
                size=46,
                mood=PetMood.IDLE,
                custom_image_path=pet.custom_image_path
            )
            lbl_figure.setPixmap(pix)
            lbl_figure.setFixedSize(46, 46)
            lbl_figure.setStyleSheet("background: transparent; border: none;")
            box_layout.addWidget(lbl_figure)

            v = QVBoxLayout()
            v.setSpacing(2)
            lbl_title = QLabel(f"<b>{pet.name}</b> — {pet.species_title}")
            lbl_title.setStyleSheet("color: #e1e4f2; font-size: 12px; border: none; background: transparent;")
            v.addWidget(lbl_title)

            lbl_tone = QLabel(f"<i>{pet.personality_tone}</i>")
            lbl_tone.setStyleSheet("color: #787c99; font-size: 11px; border: none; background: transparent;")
            v.addWidget(lbl_tone)
            box_layout.addLayout(v)
            box_layout.addStretch()

            row = idx // 2
            col = idx % 2
            grid.addWidget(box, row, col)

        layout.addLayout(grid)
        layout.addStretch()
        self.tabs.addTab(tab, "Preset Roster")

    def _build_creator_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(12)

        lbl = QLabel("Craft a bespoke writing companion with custom personality and timers:")
        lbl.setStyleSheet("color: #a2a7c4; font-size: 12px;")
        layout.addWidget(lbl)

        grid = QGridLayout()
        grid.setSpacing(10)

        # Name
        grid.addWidget(QLabel("Companion Name:"), 0, 0)
        self.txt_name = QLineEdit()
        self.txt_name.setPlaceholderText("e.g. Barnaby, Ghost, Lady Catherine")
        grid.addWidget(self.txt_name, 0, 1)

        # Species / Title
        grid.addWidget(QLabel("Title / Species:"), 1, 0)
        self.txt_species = QLineEdit()
        self.txt_species.setPlaceholderText("e.g. The Cybernetic Cat, The Spectral Poet")
        grid.addWidget(self.txt_species, 1, 1)

        # Figure Avatar Type
        grid.addWidget(QLabel("Figure Appearance:"), 2, 0)
        h_fig = QHBoxLayout()
        self.combo_figure_base = QComboBox()
        self.combo_figure_base.addItem("Corvus (The Raven)", "corvus")
        self.combo_figure_base.addItem("Quill (The Owl)", "quill")
        self.combo_figure_base.addItem("Ink (The Cat)", "ink")
        self.combo_figure_base.addItem("Scout (The Hound)", "scout")
        self.combo_figure_base.addItem("Ignis (The Dragon)", "ignis")
        self.combo_figure_base.addItem("Ancient Quill & Scroll", "custom")
        self.combo_figure_base.currentIndexChanged.connect(self._update_creator_preview)
        h_fig.addWidget(self.combo_figure_base)

        self.btn_browse_img = QPushButton("Browse Photo / PNG...")
        self.btn_browse_img.setStyleSheet("""
            QPushButton {
                background-color: #24283b;
                color: #c0caf5;
                border: 1px solid #3b4261;
                border-radius: 5px;
                padding: 5px 12px;
                font-weight: 600;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #2e344e;
                color: #ffffff;
                border-color: #7aa2f7;
            }
        """)
        self.btn_browse_img.clicked.connect(self._browse_custom_image)
        h_fig.addWidget(self.btn_browse_img)

        self.lbl_creator_preview = QLabel()
        self.lbl_creator_preview.setFixedSize(48, 48)
        self.lbl_creator_preview.setStyleSheet("border: 1px solid #3b3e58; border-radius: 24px;")
        h_fig.addWidget(self.lbl_creator_preview)
        grid.addLayout(h_fig, 2, 1)

        # Personality Tone
        grid.addWidget(QLabel("Personality Tone:"), 3, 0)
        self.txt_tone = QLineEdit()
        self.txt_tone.setPlaceholderText("e.g. Snarky Editor, Gentle Encourager, Victorian Scholar")
        grid.addWidget(self.txt_tone, 3, 1)

        # Break Timer Interval
        grid.addWidget(QLabel("Break Timer (minutes):"), 4, 0)
        h_timer = QHBoxLayout()
        self.spin_break = QSpinBox()
        self.spin_break.setRange(5, 180)
        self.spin_break.setValue(25)
        h_timer.addWidget(self.spin_break)

        self.chk_break_enable = QCheckBox("Enable Break Reminders")
        self.chk_break_enable.setChecked(True)
        h_timer.addWidget(self.chk_break_enable)
        h_timer.addStretch()
        grid.addLayout(h_timer, 4, 1)

        layout.addLayout(grid)
        layout.addStretch()

        self._update_creator_preview()
        self.tabs.addTab(tab, "Create Your Own Pet")

    def _browse_custom_image(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Pet Image", "", "Images (*.png *.jpg *.jpeg *.bmp *.webp)"
        )
        if path:
            self._custom_image_path = path
            self._update_creator_preview()

    def _update_creator_preview(self) -> None:
        base_id = self.combo_figure_base.currentData()
        pix = CompanionFigureRenderer.render_figure(
            base_id,
            size=48,
            mood=PetMood.IDLE,
            custom_image_path=self._custom_image_path
        )
        self.lbl_creator_preview.setPixmap(pix)

    def _on_hide_companion(self) -> None:
        self.hideCompanionRequested.emit()
        self.accept()

    def _on_apply(self) -> None:
        if self.tabs.currentIndex() == 0:
            # Preset Roster selection
            sel_id = self.roster_group.checkedId()
            all_pets = list(DEFAULT_PETS.values()) + list(self.custom_pets.values())
            if 0 <= sel_id < len(all_pets):
                chosen_pet = all_pets[sel_id]
                self.petSelected.emit(chosen_pet)
                self.accept()
        else:
            # Custom pet creation
            name = self.txt_name.text().strip() or "Custom Companion"
            species = self.txt_species.text().strip() or "Scribe Familiar"
            base_id = self.combo_figure_base.currentData()
            tone = self.txt_tone.text().strip() or "Faithful Assistant"
            interval = self.spin_break.value()
            enabled = self.chk_break_enable.isChecked()

            new_pet = PetProfile(
                id=f"custom_{name.lower().replace(' ', '_')}_{base_id}",
                name=name,
                species_title=species,
                avatar_icon="🪶",
                personality_tone=tone,
                custom_image_path=self._custom_image_path,
                break_interval_minutes=interval,
                break_timer_enabled=enabled,
                idle_quotes=[
                    f"At your side, wordsmith. Let's make this chapter count.",
                    f"Writing is the art of giving shadow form. Continue onward.",
                ],
                milestone_quotes=[
                    f"Astounding! Another word milestone achieved!",
                ],
                break_quotes=[
                    f"Time to take a well-deserved break! Rest your eyes and hydrate.",
                ],
                prompt_ideas=[
                    "What truth does the character refuse to admit to themselves?",
                ]
            )
            self.petSelected.emit(new_pet)
            self.accept()


class BreakTimerDialog(QDialog):
    """Dedicated settings dialog for configuring or toggling the Pomodoro / Break Timer."""

    def __init__(self, interval_min: int, enabled: bool, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Customize Break Timer")
        self.setFixedSize(360, 200)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        self.chk_enabled = QCheckBox("Enable Gentle Break Reminders")
        self.chk_enabled.setChecked(enabled)
        layout.addWidget(self.chk_enabled)

        h_spin = QHBoxLayout()
        h_spin.addWidget(QLabel("Remind me every:"))
        self.spin_minutes = QSpinBox()
        self.spin_minutes.setRange(5, 120)
        self.spin_minutes.setValue(interval_min)
        self.spin_minutes.setSuffix(" minutes")
        h_spin.addWidget(self.spin_minutes)
        layout.addLayout(h_spin)

        lbl_desc = QLabel(
            "Your companion will gently remind you to rest your eyes, "
            "stretch your shoulders, and drink water when this timer fires."
        )
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet("color: #787c99; font-size: 11px;")
        layout.addWidget(lbl_desc)

        layout.addStretch()

        h_btn = QHBoxLayout()
        h_btn.addStretch()
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #24283b;
                color: #c0caf5;
                border: 1px solid #3b4261;
                border-radius: 4px;
                padding: 5px 14px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #2e344e;
                color: #ffffff;
                border-color: #7aa2f7;
            }
        """)
        btn_cancel.clicked.connect(self.reject)
        h_btn.addWidget(btn_cancel)

        btn_save = QPushButton("Save Timer")
        btn_save.setStyleSheet("background-color: #7aa2f7; color: #1a1b26; font-weight: bold; border-radius: 4px; padding: 5px 12px;")
        btn_save.clicked.connect(self.accept)
        h_btn.addWidget(btn_save)
        layout.addLayout(h_btn)

    @property
    def timer_enabled(self) -> bool:
        return self.chk_enabled.isChecked()

    @property
    def interval_minutes(self) -> int:
        return self.spin_minutes.value()

