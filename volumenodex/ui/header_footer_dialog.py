"""Header and Footer customization dialog with per-page differentiation options."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QLineEdit, QCheckBox, QComboBox, QPushButton, QGroupBox, QFrame
)
from volumenodex.core.header_footer_model import HeaderFooterModel, PageHeaderFooterConfig


class HeaderFooterDialog(QDialog):
    """Dialog for customizing running headers and footers across the manuscript or per page."""

    def __init__(self, model: HeaderFooterModel, total_pages: int = 1, current_page: int = 1, parent=None):
        super().__init__(parent)
        self.model = model
        self.total_pages = max(1, total_pages)
        self.current_page = max(1, min(self.total_pages, current_page))
        self.setWindowTitle("Configure Running Headers & Footers")
        self.setFixedSize(540, 480)
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
            QLineEdit, QComboBox {
                background-color: #24283b;
                border: 1px solid #3b4261;
                border-radius: 4px;
                color: #ffffff;
                padding: 5px 8px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border-color: #7aa2f7;
            }
            QCheckBox {
                color: #c0caf5;
                font-size: 12px;
            }
            QPushButton {
                background-color: #24283b;
                color: #c0caf5;
                border: 1px solid #3b4261;
                border-radius: 5px;
                padding: 6px 14px;
                font-weight: 600;
                font-size: 11px;
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
        layout.setSpacing(12)

        # 1. Page Scope Selector & Unlink Toggle
        h_scope = QHBoxLayout()
        h_scope.addWidget(QLabel("Editing Target:"))

        self.combo_target = QComboBox()
        self.combo_target.addItem("Document Default (All Pages)", 0)
        for p in range(1, self.total_pages + 1):
            lbl = f"Page {p}" + (" (First Page / Title)" if p == 1 else "")
            if p == 1 and self.model.different_first_page:
                lbl += " [Different First Page]"
            elif p in self.model.page_overrides:
                lbl += " [Custom Unlinked]"
            self.combo_target.addItem(lbl, p)

        # Select current page by default
        idx = self.combo_target.findData(self.current_page)
        if idx >= 0:
            self.combo_target.setCurrentIndex(idx)

        self.combo_target.currentIndexChanged.connect(self._on_target_changed)
        h_scope.addWidget(self.combo_target)
        layout.addLayout(h_scope)

        # Differentiation Checkboxes
        h_diff = QHBoxLayout()
        self.chk_diff_first = QCheckBox("Different First Page (Title / Cover page unlinked)")
        self.chk_diff_first.setChecked(self.model.different_first_page)
        self.chk_diff_first.toggled.connect(self._on_diff_first_toggled)
        h_diff.addWidget(self.chk_diff_first)

        self.chk_unlink_page = QCheckBox("Make this page different (Unlink from previous)")
        self.chk_unlink_page.toggled.connect(self._on_unlink_toggled)
        h_diff.addWidget(self.chk_unlink_page)
        layout.addLayout(h_diff)

        self.chk_suppress = QCheckBox("Suppress Header & Footer on this page")
        self.chk_suppress.toggled.connect(self._on_suppress_toggled)
        layout.addWidget(self.chk_suppress)

        # 2. Running Top Header Group
        grp_hdr = QGroupBox("Running Top Header")
        grid_hdr = QGridLayout(grp_hdr)
        grid_hdr.setSpacing(8)

        grid_hdr.addWidget(QLabel("Left Header:"), 0, 0)
        self.txt_hdr_left = QLineEdit()
        self.txt_hdr_left.setPlaceholderText("{title} or Book Name")
        grid_hdr.addWidget(self.txt_hdr_left, 0, 1)

        grid_hdr.addWidget(QLabel("Center Header:"), 1, 0)
        self.txt_hdr_center = QLineEdit()
        self.txt_hdr_center.setPlaceholderText("Chapter / Section")
        grid_hdr.addWidget(self.txt_hdr_center, 1, 1)

        grid_hdr.addWidget(QLabel("Right Header:"), 2, 0)
        self.txt_hdr_right = QLineEdit()
        self.txt_hdr_right.setPlaceholderText("{author} or Date")
        grid_hdr.addWidget(self.txt_hdr_right, 2, 1)
        layout.addWidget(grp_hdr)

        # 3. Running Bottom Footer Group
        grp_ftr = QGroupBox("Running Bottom Footer")
        grid_ftr = QGridLayout(grp_ftr)
        grid_ftr.setSpacing(8)

        grid_ftr.addWidget(QLabel("Left Footer:"), 0, 0)
        self.txt_ftr_left = QLineEdit()
        grid_ftr.addWidget(self.txt_ftr_left, 0, 1)

        grid_ftr.addWidget(QLabel("Center Footer:"), 1, 0)
        self.txt_ftr_center = QLineEdit()
        self.txt_ftr_center.setPlaceholderText("— {page} —")
        grid_ftr.addWidget(self.txt_ftr_center, 1, 1)

        grid_ftr.addWidget(QLabel("Right Footer:"), 2, 0)
        self.txt_ftr_right = QLineEdit()
        grid_ftr.addWidget(self.txt_ftr_right, 2, 1)
        layout.addWidget(grp_ftr)

        # 4. Token Helper Chips
        h_tokens = QHBoxLayout()
        h_tokens.addWidget(QLabel("Insert Variable:"))
        tokens = [
            ("Page Number", "{page}"),
            ("Total Pages", "{total}"),
            ("Document Title", "{title}"),
            ("Author", "{author}"),
            ("Current Date", "{date}"),
        ]
        for name, token in tokens:
            btn = QPushButton(f"+ {name}")
            btn.setStyleSheet("padding: 3px 8px; font-size: 10px;")
            btn.clicked.connect(lambda _, t=token: self._insert_token(t))
            h_tokens.addWidget(btn)
        h_tokens.addStretch()
        layout.addLayout(h_tokens)

        layout.addStretch()

        # Action Buttons
        h_btn = QHBoxLayout()
        h_btn.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        h_btn.addWidget(btn_cancel)

        btn_save = QPushButton("Apply Headers & Footers")
        btn_save.setObjectName("primaryBtn")
        btn_save.clicked.connect(self._save_and_accept)
        h_btn.addWidget(btn_save)

        layout.addLayout(h_btn)

        # Load initial values
        self._load_target_values()

    def _insert_token(self, token: str) -> None:
        focused = self.focusWidget()
        if isinstance(focused, QLineEdit):
            focused.insert(token)
        else:
            self.txt_ftr_center.insert(token)

    def _on_target_changed(self) -> None:
        self._load_target_values()

    def _on_diff_first_toggled(self, checked: bool) -> None:
        self.model.different_first_page = checked
        if self.combo_target.currentData() == 1:
            self._load_target_values()

    def _on_unlink_toggled(self, checked: bool) -> None:
        target = self.combo_target.currentData()
        if target > 1:
            if checked:
                self.model.unlink_page(target)
            else:
                self.model.link_page_to_default(target)
            self._load_target_values()

    def _on_suppress_toggled(self, checked: bool) -> None:
        pass

    def _load_target_values(self) -> None:
        target = self.combo_target.currentData()
        if target == 0:
            # Default template
            self.chk_unlink_page.setEnabled(False)
            self.chk_unlink_page.setChecked(False)
            self.chk_suppress.setChecked(self.model.default_config.suppressed)
            cfg = self.model.default_config
        elif target == 1:
            self.chk_unlink_page.setEnabled(False)
            self.chk_unlink_page.setChecked(self.model.different_first_page)
            cfg = self.model.first_page_config if self.model.different_first_page else self.model.default_config
            self.chk_suppress.setChecked(cfg.suppressed)
        else:
            is_unlinked = target in self.model.page_overrides
            self.chk_unlink_page.setEnabled(True)
            self.chk_unlink_page.blockSignals(True)
            self.chk_unlink_page.setChecked(is_unlinked)
            self.chk_unlink_page.blockSignals(False)
            cfg = self.model.page_overrides.get(target, self.model.default_config)
            self.chk_suppress.setChecked(cfg.suppressed)

        self.txt_hdr_left.setText(cfg.header_left)
        self.txt_hdr_center.setText(cfg.header_center)
        self.txt_hdr_right.setText(cfg.header_right)
        self.txt_ftr_left.setText(cfg.footer_left)
        self.txt_ftr_center.setText(cfg.footer_center)
        self.txt_ftr_right.setText(cfg.footer_right)

    def _save_and_accept(self) -> None:
        target = self.combo_target.currentData()
        cfg = PageHeaderFooterConfig(
            header_left=self.txt_hdr_left.text(),
            header_center=self.txt_hdr_center.text(),
            header_right=self.txt_hdr_right.text(),
            footer_left=self.txt_ftr_left.text(),
            footer_center=self.txt_ftr_center.text(),
            footer_right=self.txt_ftr_right.text(),
            suppressed=self.chk_suppress.isChecked(),
            is_custom=(target > 0)
        )

        if target == 0:
            self.model.default_config = cfg
        elif target == 1:
            if self.model.different_first_page:
                self.model.first_page_config = cfg
            else:
                self.model.default_config = cfg
        else:
            if self.chk_unlink_page.isChecked():
                self.model.set_page_override(target, cfg)
            else:
                self.model.remove_page_override(target)

        self.accept()
