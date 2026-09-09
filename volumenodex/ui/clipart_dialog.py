"""Clip Art library dialog supporting user-provided graphics, vector SVG, and raster art."""

import os
from typing import Optional, List
from PySide6.QtCore import Qt, QSize, QUrl
from PySide6.QtGui import QIcon, QPixmap, QDesktopServices
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QFileDialog, QFrame, QMessageBox
)


class ClipArtDialog(QDialog):
    """Dialog allowing users to select clip art from their designated library or browse their computer."""

    SUPPORTED_EXTENSIONS = (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp", ".svg")

    def __init__(self, clipart_dir: str, parent=None):
        super().__init__(parent)
        self.clipart_dir = os.path.abspath(clipart_dir)
        os.makedirs(self.clipart_dir, exist_ok=True)
        self.selected_file: Optional[str] = None

        self.setWindowTitle("Insert Clip Art - Volumenodex Library")
        self.resize(680, 520)
        self.setStyleSheet("""
            QDialog {
                background-color: #1a1b26;
                color: #c0caf5;
            }
            QLabel {
                color: #c0caf5;
            }
            QListWidget {
                background-color: #1f2335;
                border: 1px solid #292e42;
                border-radius: 8px;
                padding: 8px;
                color: #c0caf5;
            }
            QListWidget::item {
                background-color: #24283b;
                border: 1px solid #292e42;
                border-radius: 6px;
                margin: 4px;
                padding: 6px;
            }
            QListWidget::item:hover {
                background-color: #2e344e;
                border: 1px solid #7aa2f7;
            }
            QListWidget::item:selected {
                background-color: #3b4261;
                border: 2px solid #7aa2f7;
                color: #ffffff;
            }
            QPushButton {
                background-color: #24283b;
                border: 1px solid #292e42;
                border-radius: 6px;
                padding: 6px 14px;
                color: #c0caf5;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #2e344e;
                border: 1px solid #7aa2f7;
                color: #7aa2f7;
            }
            QPushButton#primaryBtn {
                background-color: #7aa2f7;
                color: #1a1b26;
                font-weight: bold;
                border: none;
            }
            QPushButton#primaryBtn:hover {
                background-color: #89b4fa;
            }
        """)

        self._build_ui()
        self._load_library()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        # Header
        header = QLabel("Clip Art & Illustration Library")
        header.setStyleSheet("font-size: 16px; font-weight: bold; color: #7aa2f7;")
        layout.addWidget(header)

        # Subheader / directory note
        self.dir_label = QLabel(f"Library folder: {self.clipart_dir}")
        self.dir_label.setStyleSheet("color: #7982a9; font-size: 11px;")
        self.dir_label.setWordWrap(True)
        layout.addWidget(self.dir_label)

        # Content area: ListWidget for items or empty placeholder
        self.list_widget = QListWidget()
        self.list_widget.setViewMode(QListWidget.ViewMode.IconMode)
        self.list_widget.setIconSize(QSize(96, 96))
        self.list_widget.setGridSize(QSize(120, 130))
        self.list_widget.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.list_widget.setMovement(QListWidget.Movement.Static)
        self.list_widget.setSpacing(6)
        self.list_widget.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.list_widget.itemSelectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self.list_widget, stretch=1)

        # Empty library card banner (hidden by default)
        self.empty_card = QFrame()
        self.empty_card.setStyleSheet("""
            QFrame {
                background-color: #1f2335;
                border: 1px dashed #414868;
                border-radius: 8px;
                padding: 24px;
            }
        """)
        empty_layout = QVBoxLayout(self.empty_card)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.setSpacing(10)

        empty_icon = QLabel("🎨")
        empty_icon.setStyleSheet("font-size: 36px;")
        empty_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(empty_icon)

        empty_title = QLabel("Clip Art Library is Currently Empty")
        empty_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #c0caf5;")
        empty_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(empty_title)

        empty_desc = QLabel(
            "You can populate your library anytime by placing your image files\n"
            "(.png, .svg, .jpg, .webp, .gif) into your clip art folder,\n"
            "or click 'Choose Picture from PC' below to insert any file directly."
        )
        empty_desc.setStyleSheet("color: #a9b1d6; font-size: 12px; line-height: 1.4;")
        empty_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(empty_desc)

        layout.addWidget(self.empty_card)
        self.empty_card.hide()

        # Bottom toolbar
        bottom_bar = QHBoxLayout()
        bottom_bar.setSpacing(8)

        self.btn_open_folder = QPushButton("📂 Open Library Folder")
        self.btn_open_folder.setToolTip("Open the clip art folder in Windows File Explorer")
        self.btn_open_folder.clicked.connect(self._open_folder)
        bottom_bar.addWidget(self.btn_open_folder)

        self.btn_refresh = QPushButton("🔄 Refresh")
        self.btn_refresh.setToolTip("Refresh list from disk")
        self.btn_refresh.clicked.connect(self._load_library)
        bottom_bar.addWidget(self.btn_refresh)

        self.btn_browse = QPushButton("📁 Choose from PC...")
        self.btn_browse.setToolTip("Select any image from your computer to insert")
        self.btn_browse.clicked.connect(self._browse_custom_image)
        bottom_bar.addWidget(self.btn_browse)

        bottom_bar.addStretch()

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        bottom_bar.addWidget(self.btn_cancel)

        self.btn_insert = QPushButton("Insert Clip Art")
        self.btn_insert.setObjectName("primaryBtn")
        self.btn_insert.setEnabled(False)
        self.btn_insert.clicked.connect(self._on_insert_clicked)
        bottom_bar.addWidget(self.btn_insert)

        layout.addLayout(bottom_bar)

    def _load_library(self) -> None:
        self.list_widget.clear()
        if not os.path.isdir(self.clipart_dir):
            self.empty_card.show()
            self.list_widget.hide()
            return

        files = [
            f for f in sorted(os.listdir(self.clipart_dir))
            if os.path.splitext(f)[1].lower() in self.SUPPORTED_EXTENSIONS
        ]

        if not files:
            self.empty_card.show()
            self.list_widget.hide()
            self.btn_insert.setEnabled(False)
            return

        self.empty_card.hide()
        self.list_widget.show()

        for filename in files:
            full_path = os.path.join(self.clipart_dir, filename)
            pix = QPixmap(full_path)
            if not pix.isNull():
                scaled = pix.scaled(96, 96, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                item = QListWidgetItem(QIcon(scaled), os.path.splitext(filename)[0])
                item.setData(Qt.ItemDataRole.UserRole, full_path)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.list_widget.addItem(item)

    def _on_selection_changed(self) -> None:
        items = self.list_widget.selectedItems()
        self.btn_insert.setEnabled(len(items) > 0)

    def _on_item_double_clicked(self, item: QListWidgetItem) -> None:
        path = item.data(Qt.ItemDataRole.UserRole)
        if path and os.path.exists(path):
            self.selected_file = path
            self.accept()

    def _on_insert_clicked(self) -> None:
        items = self.list_widget.selectedItems()
        if items:
            path = items[0].data(Qt.ItemDataRole.UserRole)
            if path and os.path.exists(path):
                self.selected_file = path
                self.accept()

    def _open_folder(self) -> None:
        QDesktopServices.openUrl(QUrl.fromLocalFile(self.clipart_dir))

    def _browse_custom_image(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Choose Image File",
            "",
            "Image Files (*.png *.jpg *.jpeg *.bmp *.gif *.webp *.svg);;All Files (*)"
        )
        if file_path and os.path.exists(file_path):
            self.selected_file = file_path
            self.accept()
