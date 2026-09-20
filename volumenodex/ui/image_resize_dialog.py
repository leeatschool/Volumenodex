"""Interactive Image Resize Dialog for Volumenodex Word Processing Studio."""

from typing import Optional, Tuple
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSpinBox, QCheckBox, QFrame, QGridLayout
)


class ImageResizeDialog(QDialog):
    """Dialog allowing users to resize an embedded image with aspect ratio preservation."""

    def __init__(
        self,
        current_width: int,
        current_height: int,
        page_width: int = 700,
        parent=None
    ):
        super().__init__(parent)
        self.orig_w = max(1, int(current_width))
        self.orig_h = max(1, int(current_height))
        self.page_w = max(100, int(page_width))
        self.aspect_ratio = self.orig_w / self.orig_h

        self.target_width = self.orig_w
        self.target_height = self.orig_h

        self.setWindowTitle("Resize Image — Volumenodex")
        self.setFixedWidth(420)
        self.setStyleSheet("""
            QDialog { background-color: #1a1b26; color: #c0caf5; }
            QLabel { color: #c0caf5; }
            QSpinBox {
                background-color: #1f2335; color: #ffffff; border: 1px solid #3b4261;
                border-radius: 4px; padding: 4px 8px; font-size: 13px; font-weight: bold;
            }
            QSpinBox:focus { border-color: #7aa2f7; }
            QCheckBox { color: #c0caf5; font-size: 12px; }
            QPushButton {
                background-color: #24283b; color: #c0caf5; border: 1px solid #3b4261;
                border-radius: 6px; padding: 5px 12px; font-weight: 600; font-size: 11px;
            }
            QPushButton:hover { background-color: #2e344e; border-color: #7aa2f7; color: #ffffff; }
            QPushButton#primaryBtn {
                background-color: #7aa2f7; color: #101116; font-weight: bold; border: none; font-size: 12px;
            }
            QPushButton#primaryBtn:hover { background-color: #89b4fa; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        # Header
        lbl_title = QLabel("Image Dimensions & Scaling")
        lbl_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #7aa2f7;")
        layout.addWidget(lbl_title)

        # Inputs Grid
        grid = QGridLayout()
        grid.setSpacing(10)

        grid.addWidget(QLabel("Width:"), 0, 0)
        self.spin_width = QSpinBox()
        self.spin_width.setRange(16, 4000)
        self.spin_width.setValue(self.orig_w)
        self.spin_width.setSuffix(" px")
        self.spin_width.valueChanged.connect(self._on_width_changed)
        grid.addWidget(self.spin_width, 0, 1)

        self.lbl_width_in = QLabel(f"({self.orig_w / 96.0:.2f} in)")
        self.lbl_width_in.setStyleSheet("color: #787c99; font-size: 11px;")
        grid.addWidget(self.lbl_width_in, 0, 2)

        grid.addWidget(QLabel("Height:"), 1, 0)
        self.spin_height = QSpinBox()
        self.spin_height.setRange(16, 4000)
        self.spin_height.setValue(self.orig_h)
        self.spin_height.setSuffix(" px")
        self.spin_height.valueChanged.connect(self._on_height_changed)
        grid.addWidget(self.spin_height, 1, 1)

        self.lbl_height_in = QLabel(f"({self.orig_h / 96.0:.2f} in)")
        self.lbl_height_in.setStyleSheet("color: #787c99; font-size: 11px;")
        grid.addWidget(self.lbl_height_in, 1, 2)

        layout.addLayout(grid)

        # Aspect ratio lock
        self.chk_lock_aspect = QCheckBox("Lock aspect ratio (constrain proportions)")
        self.chk_lock_aspect.setChecked(True)
        layout.addWidget(self.chk_lock_aspect)

        # Quick Presets
        lbl_presets = QLabel("Quick Scaling Presets:")
        lbl_presets.setStyleSheet("color: #7aa2f7; font-size: 11px; font-weight: 600; margin-top: 4px;")
        layout.addWidget(lbl_presets)

        h_presets1 = QHBoxLayout()
        btn_25 = QPushButton("25% Page")
        btn_25.clicked.connect(lambda: self._set_width(int(self.page_w * 0.25)))
        h_presets1.addWidget(btn_25)

        btn_50 = QPushButton("50% Page")
        btn_50.clicked.connect(lambda: self._set_width(int(self.page_w * 0.50)))
        h_presets1.addWidget(btn_50)

        btn_75 = QPushButton("75% Page")
        btn_75.clicked.connect(lambda: self._set_width(int(self.page_w * 0.75)))
        h_presets1.addWidget(btn_75)

        btn_100 = QPushButton("Full Page Width")
        btn_100.clicked.connect(lambda: self._set_width(self.page_w))
        h_presets1.addWidget(btn_100)
        layout.addLayout(h_presets1)

        h_presets2 = QHBoxLayout()
        btn_thumb = QPushButton("Thumbnail (150px)")
        btn_thumb.clicked.connect(lambda: self._set_width(150))
        h_presets2.addWidget(btn_thumb)

        btn_orig = QPushButton("Reset Original Size")
        btn_orig.clicked.connect(lambda: self._set_dimensions(self.orig_w, self.orig_h))
        h_presets2.addWidget(btn_orig)
        layout.addLayout(h_presets2)

        # Dialog Buttons
        layout.addSpacing(6)
        h_buttons = QHBoxLayout()
        h_buttons.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        h_buttons.addWidget(btn_cancel)

        btn_apply = QPushButton("Apply Size")
        btn_apply.setObjectName("primaryBtn")
        btn_apply.clicked.connect(self._on_apply)
        h_buttons.addWidget(btn_apply)
        layout.addLayout(h_buttons)

        self._updating = False

    def _set_width(self, w: int) -> None:
        self.spin_width.setValue(w)

    def _set_dimensions(self, w: int, h: int) -> None:
        self._updating = True
        self.spin_width.setValue(w)
        self.spin_height.setValue(h)
        self.lbl_width_in.setText(f"({w / 96.0:.2f} in)")
        self.lbl_height_in.setText(f"({h / 96.0:.2f} in)")
        self._updating = False

    def _on_width_changed(self, new_w: int) -> None:
        if self._updating:
            return
        self.lbl_width_in.setText(f"({new_w / 96.0:.2f} in)")
        if self.chk_lock_aspect.isChecked():
            self._updating = True
            new_h = max(1, int(round(new_w / self.aspect_ratio)))
            self.spin_height.setValue(new_h)
            self.lbl_height_in.setText(f"({new_h / 96.0:.2f} in)")
            self._updating = False

    def _on_height_changed(self, new_h: int) -> None:
        if self._updating:
            return
        self.lbl_height_in.setText(f"({new_h / 96.0:.2f} in)")
        if self.chk_lock_aspect.isChecked():
            self._updating = True
            new_w = max(1, int(round(new_h * self.aspect_ratio)))
            self.spin_width.setValue(new_w)
            self.lbl_width_in.setText(f"({new_w / 96.0:.2f} in)")
            self._updating = False

    def _on_apply(self) -> None:
        self.target_width = self.spin_width.value()
        self.target_height = self.spin_height.value()
        self.accept()

    def get_dimensions(self) -> Tuple[int, int]:
        return self.spin_width.value(), self.spin_height.value()
