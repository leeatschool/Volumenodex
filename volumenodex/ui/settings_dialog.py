"""Settings and Preferences Dialog for Volumenodex Studio.

Provides an intuitive Fluent interface to customize variable auto-save intervals,
default document modes, canvas visual cues, and studio behavior.
"""

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QFont, QDesktopServices
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox,
    QComboBox, QPushButton, QFrame, QGroupBox, QScrollArea, QWidget,
    QLineEdit, QFileDialog, QDoubleSpinBox, QSpinBox
)

from volumenodex.core.settings_manager import SettingsManager
from volumenodex.core.document_model import DocumentMode


class SettingsDialog(QDialog):
    """Preferences and settings configuration dialog."""

    def __init__(self, settings_manager: SettingsManager, parent=None):
        super().__init__(parent)
        self.settings_manager = settings_manager
        self.setWindowTitle("Studio Settings & Preferences — Volumenodex")
        self.resize(560, 600)
        self.setMinimumSize(480, 360)
        self.setStyleSheet("""
            QDialog {
                background-color: #1a1b26;
                color: #c0caf5;
            }
            QLabel {
                color: #c0caf5;
            }
            QScrollArea {
                background-color: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background-color: #16161e;
                width: 10px;
                margin: 0px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background-color: #3b4261;
                min-height: 24px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #7aa2f7;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QLineEdit {
                background-color: #16161e;
                color: #c0caf5;
                border: 1px solid #292e42;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border-color: #7aa2f7;
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

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Scrollable Settings Container
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        container.setStyleSheet("background-color: #1a1b26;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 20, 24, 20)
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

        self.chk_auto_open_recent = QCheckBox("Automatically open the most recent document on startup", grp_general)
        self.chk_auto_open_recent.setChecked(self.settings_manager.auto_open_recent)
        v_gen.addWidget(self.chk_auto_open_recent)

        layout.addWidget(grp_general)

        # 3. Writing Goals & Analytics
        grp_goals = QGroupBox("WRITING TARGETS & RECENT FILES", self)
        v_goals = QVBoxLayout(grp_goals)
        v_goals.setSpacing(10)

        h_goal = QHBoxLayout()
        h_goal.addWidget(QLabel("Daily Word Count Target:"))
        from PySide6.QtWidgets import QSpinBox
        self.spin_daily_goal = QSpinBox()
        self.spin_daily_goal.setRange(50, 50000)
        self.spin_daily_goal.setSingleStep(250)
        self.spin_daily_goal.setValue(self.settings_manager.daily_word_goal)
        self.spin_daily_goal.setSuffix(" words")
        self.spin_daily_goal.setStyleSheet("""
            QSpinBox {
                background-color: #24283b;
                border: 1px solid #3b4261;
                border-radius: 4px;
                color: #ffffff;
                padding: 4px 8px;
            }
        """)
        h_goal.addWidget(self.spin_daily_goal)
        h_goal.addStretch()
        v_goals.addLayout(h_goal)

        h_recent = QHBoxLayout()
        lbl_rec_count = QLabel(f"Recent Documents Tracked: {len(self.settings_manager.recent_files)}")
        lbl_rec_count.setStyleSheet("color: #787c99; font-size: 11px;")
        h_recent.addWidget(lbl_rec_count)
        h_recent.addStretch()

        btn_clear_rec = QPushButton("Clear Recent History")
        btn_clear_rec.setStyleSheet("""
            QPushButton {
                background-color: #24283b;
                color: #f7768e;
                border: 1px solid #3b4261;
                border-radius: 4px;
                padding: 4px 10px;
                font-size: 10px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: rgba(247, 118, 142, 0.15);
                border-color: #f7768e;
            }
        """)
        btn_clear_rec.clicked.connect(lambda: (self.settings_manager.clear_recent_files(), lbl_rec_count.setText("Recent Documents Tracked: 0")))
        h_recent.addWidget(btn_clear_rec)
        v_goals.addLayout(h_recent)

        layout.addWidget(grp_goals)

        # 4. Clipart Library Autoexpansion (Wikimedia Commons)
        from PySide6.QtWidgets import QDoubleSpinBox
        self.grp_autoexpansion = QGroupBox("CLIPART LIBRARY AUTOEXPANSION (WIKIMEDIA COMMONS)", self)
        v_clipart = QVBoxLayout(self.grp_autoexpansion)
        v_clipart.setSpacing(10)

        self.chk_autoexpansion_enable = QCheckBox(
            "Enable Clipart Autoexpansion (query Wikimedia Commons when < 3 local results)",
            self.grp_autoexpansion
        )
        self.chk_autoexpansion_enable.setChecked(self.settings_manager.clipart_autoexpansion_enabled)
        v_clipart.addWidget(self.chk_autoexpansion_enable)

        h_size = QHBoxLayout()
        h_size.setSpacing(12)
        lbl_size = QLabel("Download Image Size:", self.grp_autoexpansion)
        lbl_size.setStyleSheet("color: #9aa5ce; font-size: 12px;")
        h_size.addWidget(lbl_size)

        self.combo_autoexpansion_size = QComboBox(self.grp_autoexpansion)
        self.combo_autoexpansion_size.addItem("500px Standard (Fast & Compact, Default)", "500px")
        self.combo_autoexpansion_size.addItem("1000px High-Resolution", "1000px")
        self.combo_autoexpansion_size.addItem("Full Original Size", "full")
        idx_sz = self.combo_autoexpansion_size.findData(self.settings_manager.clipart_autoexpansion_size)
        if idx_sz >= 0:
            self.combo_autoexpansion_size.setCurrentIndex(idx_sz)
        h_size.addWidget(self.combo_autoexpansion_size)
        h_size.addStretch()
        v_clipart.addLayout(h_size)

        # Storage size limit
        h_limit = QHBoxLayout()
        h_limit.setSpacing(10)
        lbl_limit = QLabel("Library Hard Drive Limit:", self.grp_autoexpansion)
        lbl_limit.setStyleSheet("color: #9aa5ce; font-size: 12px;")
        h_limit.addWidget(lbl_limit)

        self.spin_limit_val = QDoubleSpinBox(self.grp_autoexpansion)
        self.spin_limit_val.setRange(0.1, 9999.0)
        self.spin_limit_val.setSingleStep(0.5)
        self.spin_limit_val.setValue(self.settings_manager.clipart_size_limit_val)
        self.spin_limit_val.setStyleSheet("""
            QDoubleSpinBox {
                background-color: #24283b;
                border: 1px solid #3b4261;
                border-radius: 4px;
                color: #ffffff;
                padding: 4px 8px;
            }
        """)
        h_limit.addWidget(self.spin_limit_val)

        self.combo_limit_unit = QComboBox(self.grp_autoexpansion)
        self.combo_limit_unit.addItem("MB", "MB")
        self.combo_limit_unit.addItem("GB", "GB")
        self.combo_limit_unit.addItem("TB", "TB")
        self.combo_limit_unit.addItem("KB", "KB")
        idx_u = self.combo_limit_unit.findData(self.settings_manager.clipart_size_limit_unit)
        if idx_u >= 0:
            self.combo_limit_unit.setCurrentIndex(idx_u)
        h_limit.addWidget(self.combo_limit_unit)
        h_limit.addStretch()
        v_clipart.addLayout(h_limit)

        # License options
        lbl_lic = QLabel("Allowed License Types:", self.grp_autoexpansion)
        lbl_lic.setStyleSheet("color: #9aa5ce; font-size: 11px; font-weight: 600;")
        v_clipart.addWidget(lbl_lic)

        self.chk_pd_cc0 = QCheckBox("Public Domain & CC0 (No attribution needed, default)", self.grp_autoexpansion)
        self.chk_pd_cc0.setChecked(self.settings_manager.clipart_license_pd_cc0)
        v_clipart.addWidget(self.chk_pd_cc0)

        self.chk_cc_by = QCheckBox("Creative Commons BY (Attribution saved in metadata & inserted below photo)", self.grp_autoexpansion)
        self.chk_cc_by.setChecked(self.settings_manager.clipart_license_cc_by)
        v_clipart.addWidget(self.chk_cc_by)

        self.chk_cc_by_sa = QCheckBox("Creative Commons BY-SA (Attribution saved & inserted below photo)", self.grp_autoexpansion)
        self.chk_cc_by_sa.setChecked(self.settings_manager.clipart_license_cc_by_sa)
        v_clipart.addWidget(self.chk_cc_by_sa)

        # Clipart Library Folder row
        lbl_dir = QLabel("Clipart Library Folder:", self.grp_autoexpansion)
        lbl_dir.setStyleSheet("color: #9aa5ce; font-size: 12px;")
        v_clipart.addWidget(lbl_dir)

        h_dir_input = QHBoxLayout()
        h_dir_input.setSpacing(6)
        self.txt_clipart_dir = QLineEdit(self.grp_autoexpansion)
        self.txt_clipart_dir.setText(self.settings_manager.clipart_library_dir or "")
        self.txt_clipart_dir.setPlaceholderText("Default bundled library folder (assets/clipart)")
        h_dir_input.addWidget(self.txt_clipart_dir, stretch=1)

        btn_browse_dir = QPushButton("📁 Browse...", self.grp_autoexpansion)
        btn_browse_dir.setStyleSheet("""
            QPushButton {
                background-color: #24283b;
                color: #c0caf5;
                border: 1px solid #3b4261;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover { background-color: #2e344e; color: #ffffff; border-color: #7aa2f7; }
        """)
        btn_browse_dir.clicked.connect(self._on_browse_clipart_dir)
        h_dir_input.addWidget(btn_browse_dir)

        btn_open_curr_dir = QPushButton("📂 Open", self.grp_autoexpansion)
        btn_open_curr_dir.setToolTip("Open this clipart folder in Windows File Explorer")
        btn_open_curr_dir.setStyleSheet("""
            QPushButton {
                background-color: #24283b;
                color: #c0caf5;
                border: 1px solid #3b4261;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 11px;
            }
            QPushButton:hover { background-color: #2e344e; color: #ffffff; border-color: #7aa2f7; }
        """)
        btn_open_curr_dir.clicked.connect(self._on_open_clipart_dir)
        h_dir_input.addWidget(btn_open_curr_dir)

        btn_reset_dir = QPushButton("↺", self.grp_autoexpansion)
        btn_reset_dir.setToolTip("Reset to default library folder")
        btn_reset_dir.setStyleSheet("""
            QPushButton {
                background-color: #24283b;
                color: #c0caf5;
                border: 1px solid #3b4261;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 12px;
            }
            QPushButton:hover { background-color: #2e344e; color: #ffffff; border-color: #7aa2f7; }
        """)
        btn_reset_dir.clicked.connect(lambda: self.txt_clipart_dir.setText(""))
        h_dir_input.addWidget(btn_reset_dir)

        v_clipart.addLayout(h_dir_input)

        lbl_dir_note = QLabel(
            "Downloaded Wikimedia illustrations and custom graphics are permanently saved to this folder for future use.",
            self.grp_autoexpansion
        )
        lbl_dir_note.setWordWrap(True)
        lbl_dir_note.setStyleSheet("color: #565f89; font-size: 10px; line-height: 1.3;")
        v_clipart.addWidget(lbl_dir_note)

        layout.addWidget(self.grp_autoexpansion)

        # Set scroll container widget and add to root layout
        self.scroll_area.setWidget(container)
        root_layout.addWidget(self.scroll_area, stretch=1)

        # Sticky Footer Buttons bar (always visible at bottom)
        bottom_bar = QFrame(self)
        bottom_bar.setStyleSheet("""
            QFrame {
                background-color: #16161e;
                border-top: 1px solid #292e42;
            }
        """)
        btn_layout = QHBoxLayout(bottom_bar)
        btn_layout.setContentsMargins(24, 12, 24, 12)
        btn_layout.setSpacing(10)
        btn_layout.addStretch()

        btn_cancel = QPushButton("Cancel", bottom_bar)
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

        btn_save = QPushButton("Save Preferences", bottom_bar)
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

        root_layout.addWidget(bottom_bar)

    def _on_browse_clipart_dir(self) -> None:
        """Opens directory picker to choose custom clipart library folder."""
        import os
        start_dir = self.txt_clipart_dir.text().strip() or os.path.expanduser("~/Pictures")
        chosen = QFileDialog.getExistingDirectory(self, "Select Clipart Library Folder", start_dir)
        if chosen:
            self.txt_clipart_dir.setText(os.path.normpath(chosen))

    def _on_open_clipart_dir(self) -> None:
        """Opens the currently configured clipart folder in Windows File Explorer."""
        import os
        d = self.txt_clipart_dir.text().strip()
        if not d or not os.path.exists(d):
            d = os.path.expanduser("~/Pictures")
        QDesktopServices.openUrl(QUrl.fromLocalFile(d))

    def highlight_autoexpansion_limit(self) -> None:
        """Visually highlights the autoexpansion storage limit controls and scrolls to them."""
        self.grp_autoexpansion.setStyleSheet("""
            QGroupBox {
                background-color: #1f2335;
                border: 2px solid #f7768e;
                border-radius: 8px;
                margin-top: 18px;
                padding: 14px;
                font-weight: 700;
                color: #f7768e;
            }
        """)
        self.spin_limit_val.setStyleSheet("""
            QDoubleSpinBox {
                background-color: #24283b;
                border: 2px solid #f7768e;
                border-radius: 4px;
                color: #ffffff;
                padding: 4px 8px;
            }
        """)
        self.scroll_area.ensureWidgetVisible(self.grp_autoexpansion)
        self.spin_limit_val.setFocus()

    def _on_autosave_toggle(self, checked: bool) -> None:
        self.combo_interval.setEnabled(checked)

    def _on_save_clicked(self) -> None:
        self.settings_manager.autosave_enabled = self.chk_autosave_enable.isChecked()
        self.settings_manager.autosave_interval_minutes = int(self.combo_interval.currentData())
        self.settings_manager.default_document_mode = str(self.combo_default_mode.currentData())
        self.settings_manager.show_crop_marks = self.chk_crop_marks.isChecked()
        self.settings_manager.auto_open_recent = self.chk_auto_open_recent.isChecked()
        self.settings_manager.daily_word_goal = self.spin_daily_goal.value()

        # Clipart Library & Autoexpansion settings
        self.settings_manager.clipart_library_dir = self.txt_clipart_dir.text().strip()
        self.settings_manager.clipart_autoexpansion_enabled = self.chk_autoexpansion_enable.isChecked()
        self.settings_manager.clipart_autoexpansion_size = str(self.combo_autoexpansion_size.currentData())
        self.settings_manager.clipart_size_limit_val = self.spin_limit_val.value()
        self.settings_manager.clipart_size_limit_unit = str(self.combo_limit_unit.currentData())
        self.settings_manager.clipart_license_pd_cc0 = self.chk_pd_cc0.isChecked()
        self.settings_manager.clipart_license_cc_by = self.chk_cc_by.isChecked()
        self.settings_manager.clipart_license_cc_by_sa = self.chk_cc_by_sa.isChecked()

        self.settings_manager.save()
        self.accept()
