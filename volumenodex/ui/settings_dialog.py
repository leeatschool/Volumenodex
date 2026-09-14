"""Settings and Preferences Dialog for Volumenodex Studio.

Provides an intuitive Fluent interface to customize variable auto-save intervals,
default document modes, canvas visual cues, and studio behavior.
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox,
    QComboBox, QPushButton, QFrame, QGroupBox
)

from volumenodex.core.settings_manager import SettingsManager
from volumenodex.core.document_model import DocumentMode


class SettingsDialog(QDialog):
    """Preferences and settings configuration dialog."""

    def __init__(self, settings_manager: SettingsManager, parent=None):
        super().__init__(parent)
        self.settings_manager = settings_manager
        self.setWindowTitle("Studio Settings & Preferences — Volumenodex")
        self.setFixedWidth(520)
        self.setStyleSheet("""
            QDialog {
                background-color: #1a1b26;
                color: #c0caf5;
            }
            QLabel {
                color: #c0caf5;
            }
            QGroupBox {
                background-color: #1f2335;
                border: 1px solid #292e42;
                border-radius: 8px;
                margin-top: 18px;
                padding-top: 14px;
                padding-bottom: 12px;
                padding-left: 14px;
                padding-right: 14px;
                font-weight: 700;
                color: #7aa2f7;
                font-size: 12px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 6px;
                background-color: #1a1b26;
                color: #7aa2f7;
            }
            QComboBox {
                background-color: #16161e;
                color: #c0caf5;
                border: 1px solid #292e42;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 12px;
                min-width: 180px;
            }
            QComboBox:focus, QComboBox:hover {
                border-color: #7aa2f7;
            }
            QComboBox QAbstractItemView {
                background-color: #1f2335;
                color: #c0caf5;
                border: 1px solid #292e42;
                selection-background-color: #7aa2f7;
                selection-color: #1a1b26;
                outline: none;
            }
            QCheckBox {
                color: #c0caf5;
                font-size: 12px;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border-radius: 4px;
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
        lbl_header = QLabel("Studio Preferences", self)
        font_h = QFont("Segoe UI", 15, QFont.Weight.Bold)
        lbl_header.setFont(font_h)
        lbl_header.setStyleSheet("color: #7aa2f7;")
        layout.addWidget(lbl_header)

        lbl_sub = QLabel("Customize automatic saving, document defaults, and canvas behavior.", self)
        lbl_sub.setStyleSheet("color: #787c99; font-size: 11px;")
        layout.addWidget(lbl_sub)

        # 1. Automatic Saving Group
        grp_autosave = QGroupBox("AUTOMATIC SAVING (AUTO-SAVE)", self)
        v_autosave = QVBoxLayout(grp_autosave)
        v_autosave.setSpacing(10)

        self.chk_autosave_enable = QCheckBox("Enable background automatic saving", grp_autosave)
        self.chk_autosave_enable.setChecked(self.settings_manager.autosave_enabled)
        self.chk_autosave_enable.toggled.connect(self._on_autosave_toggle)
        v_autosave.addWidget(self.chk_autosave_enable)

        h_interval = QHBoxLayout()
        h_interval.setSpacing(12)
        lbl_interval = QLabel("Auto-Save Frequency:", grp_autosave)
        lbl_interval.setStyleSheet("color: #9aa5ce; font-size: 12px;")
        h_interval.addWidget(lbl_interval)

        self.combo_interval = QComboBox(grp_autosave)
        self.combo_interval.addItem("Every 1 Minute", 1)
        self.combo_interval.addItem("Every 2 Minutes (Default)", 2)
        self.combo_interval.addItem("Every 5 Minutes", 5)
        self.combo_interval.addItem("Every 10 Minutes", 10)
        self.combo_interval.addItem("Every 15 Minutes", 15)
        self.combo_interval.addItem("Every 30 Minutes", 30)

        idx = self.combo_interval.findData(self.settings_manager.autosave_interval_minutes)
        if idx >= 0:
            self.combo_interval.setCurrentIndex(idx)
        else:
            self.combo_interval.setCurrentIndex(1)

        h_interval.addWidget(self.combo_interval)
        h_interval.addStretch()
        v_autosave.addLayout(h_interval)

        lbl_desc = QLabel(
            "Active files are saved directly in-place without interrupting your work. "
            "Untitled manuscripts are safely preserved to an emergency recovery draft vault.",
            grp_autosave
        )
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet("color: #565f89; font-size: 10px; line-height: 1.3;")
        v_autosave.addWidget(lbl_desc)

        layout.addWidget(grp_autosave)

        # 2. General Studio Defaults Group
        grp_general = QGroupBox("DOCUMENT & CANVAS DEFAULTS", self)
        v_gen = QVBoxLayout(grp_general)
        v_gen.setSpacing(10)

        h_mode = QHBoxLayout()
        h_mode.setSpacing(12)
        lbl_mode = QLabel("Default Authoring Focus:", grp_general)
        lbl_mode.setStyleSheet("color: #9aa5ce; font-size: 12px;")
        h_mode.addWidget(lbl_mode)

        self.combo_default_mode = QComboBox(grp_general)
        self.combo_default_mode.addItem("Creative Fiction & Story Codex", DocumentMode.CREATIVE_FICTION.value)
        self.combo_default_mode.addItem("General Non-Fiction & Essays", DocumentMode.NON_FICTION.value)
        self.combo_default_mode.addItem("Academic & Scholarly Citations", DocumentMode.ACADEMIC.value)

        idx_mode = self.combo_default_mode.findData(self.settings_manager.default_document_mode)
        if idx_mode >= 0:
            self.combo_default_mode.setCurrentIndex(idx_mode)
        h_mode.addWidget(self.combo_default_mode)
        h_mode.addStretch()
        v_gen.addLayout(h_mode)

        self.chk_crop_marks = QCheckBox("Show publisher corner crop marks on paper sheets", grp_general)
        self.chk_crop_marks.setChecked(self.settings_manager.show_crop_marks)
        v_gen.addWidget(self.chk_crop_marks)

        layout.addWidget(grp_general)

        # Buttons
        layout.addSpacing(8)
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_cancel = QPushButton("Cancel", self)
        btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #24283b;
                color: #c0caf5;
                border: 1px solid #3b4261;
                border-radius: 6px;
                padding: 7px 18px;
                font-weight: 600;
            }
            QPushButton:hover { background-color: #2e344e; color: #ffffff; border-color: #7aa2f7; }
        """)
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

        btn_save = QPushButton("Save Preferences", self)
        btn_save.setDefault(True)
        btn_save.setStyleSheet("""
            QPushButton {
                background-color: #7aa2f7;
                color: #1a1b26;
                border: none;
                border-radius: 6px;
                padding: 7px 22px;
                font-weight: 700;
            }
            QPushButton:hover { background-color: #89b4fa; }
        """)
        btn_save.clicked.connect(self._on_save_clicked)
        btn_layout.addWidget(btn_save)

        layout.addLayout(btn_layout)

    def _on_autosave_toggle(self, checked: bool) -> None:
        self.combo_interval.setEnabled(checked)

    def _on_save_clicked(self) -> None:
        self.settings_manager.autosave_enabled = self.chk_autosave_enable.isChecked()
        self.settings_manager.autosave_interval_minutes = int(self.combo_interval.currentData())
        self.settings_manager.default_document_mode = str(self.combo_default_mode.currentData())
        self.settings_manager.show_crop_marks = self.chk_crop_marks.isChecked()
        self.settings_manager.save()
        self.accept()
