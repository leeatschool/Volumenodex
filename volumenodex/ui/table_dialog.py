"""Table builder and properties dialog for inserting structured tables into the manuscript."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QSpinBox, QCheckBox, QComboBox, QPushButton, QFrame, QGroupBox
)


class TableInsertDialog(QDialog):
    """Modern dialog to configure and insert customizable tables."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Insert Table")
        self.setFixedSize(380, 360)
        self.setStyleSheet("""
            QDialog {
                background-color: #1a1b26;
                color: #c0caf5;
            }
            QLabel {
                color: #c0caf5;
                font-size: 12px;
            }
            QGroupBox {
                border: 1px solid #292e42;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 10px;
                font-weight: 600;
                color: #7aa2f7;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
            }
            QSpinBox, QComboBox {
                background-color: #24283b;
                border: 1px solid #3b4261;
                border-radius: 4px;
                color: #ffffff;
                padding: 4px 8px;
                min-height: 24px;
            }
            QCheckBox {
                color: #c0caf5;
            }
            QPushButton {
                background-color: #24283b;
                color: #c0caf5;
                border: 1px solid #3b4261;
                border-radius: 5px;
                padding: 6px 16px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #2e344e;
                color: #ffffff;
                border-color: #7aa2f7;
            }
            QPushButton#primaryBtn {
                background-color: #7aa2f7;
                color: #101116;
                border: 1px solid #7aa2f7;
                font-weight: bold;
            }
            QPushButton#primaryBtn:hover {
                background-color: #89b4fa;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        # 1. Grid Dimensions
        grp_dim = QGroupBox("Grid Dimensions")
        grid_dim = QGridLayout(grp_dim)
        grid_dim.setSpacing(10)

        grid_dim.addWidget(QLabel("Number of Columns:"), 0, 0)
        self.spin_cols = QSpinBox()
        self.spin_cols.setRange(1, 20)
        self.spin_cols.setValue(3)
        grid_dim.addWidget(self.spin_cols, 0, 1)

        grid_dim.addWidget(QLabel("Number of Rows:"), 1, 0)
        self.spin_rows = QSpinBox()
        self.spin_rows.setRange(1, 50)
        self.spin_rows.setValue(3)
        grid_dim.addWidget(self.spin_rows, 1, 1)
        layout.addWidget(grp_dim)

        # 2. Table Formatting & Header
        grp_style = QGroupBox("Styling & Structure")
        grid_style = QGridLayout(grp_style)
        grid_style.setSpacing(10)

        self.chk_header = QCheckBox("Include Styled Header Row")
        self.chk_header.setChecked(True)
        grid_style.addWidget(self.chk_header, 0, 0, 1, 2)

        grid_style.addWidget(QLabel("Border Style:"), 1, 0)
        self.combo_border = QComboBox()
        self.combo_border.addItem("Subtle Gray Border", 1)
        self.combo_border.addItem("Medium Border", 2)
        self.combo_border.addItem("No Border (Borderless Grid)", 0)
        grid_style.addWidget(self.combo_border, 1, 1)

        grid_style.addWidget(QLabel("Cell Padding:"), 2, 0)
        self.spin_padding = QSpinBox()
        self.spin_padding.setRange(2, 20)
        self.spin_padding.setValue(6)
        self.spin_padding.setSuffix(" px")
        grid_style.addWidget(self.spin_padding, 2, 1)
        layout.addWidget(grp_style)

        layout.addStretch()

        # Action Buttons
        h_btn = QHBoxLayout()
        h_btn.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        h_btn.addWidget(btn_cancel)

        btn_insert = QPushButton("Insert Table")
        btn_insert.setObjectName("primaryBtn")
        btn_insert.clicked.connect(self.accept)
        h_btn.addWidget(btn_insert)

        layout.addLayout(h_btn)

    @property
    def rows(self) -> int:
        return self.spin_rows.value()

    @property
    def cols(self) -> int:
        return self.spin_cols.value()

    @property
    def has_header_row(self) -> bool:
        return self.chk_header.isChecked()

    @property
    def border_width(self) -> int:
        return self.combo_border.currentData()

    @property
    def cell_padding(self) -> int:
        return self.spin_padding.value()


TableDialog = TableInsertDialog
