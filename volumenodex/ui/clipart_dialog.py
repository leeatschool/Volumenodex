"""Clip Art library dialog supporting user-provided graphics, vector SVG, and raster art with full-text search."""

import os
from typing import Optional, List, Dict, Any
from PySide6.QtCore import Qt, QSize, QUrl, QEvent
from PySide6.QtGui import QIcon, QPixmap, QDesktopServices, QKeyEvent
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QFileDialog, QFrame, QMessageBox,
    QLineEdit
)


class ClipArtDialog(QDialog):
    """Dialog allowing users to search, filter, and select clip art from their designated library or browse their computer."""

    SUPPORTED_EXTENSIONS = (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp", ".svg")

    def __init__(self, clipart_dir: str, parent=None):
        super().__init__(parent)
        self.clipart_dir = os.path.abspath(clipart_dir)
        os.makedirs(self.clipart_dir, exist_ok=True)
        self.selected_file: Optional[str] = None
        self._indexed_items: List[Dict[str, Any]] = []

        self.setWindowTitle("Insert Clip Art - Volumenodex Library")
        self.resize(760, 560)
        self.setMinimumSize(600, 440)
        self.setStyleSheet("""
            QDialog {
                background-color: #1a1b26;
                color: #c0caf5;
            }
            QLabel {
                color: #c0caf5;
            }
            QLineEdit {
                background-color: #1f2335;
                color: #c0caf5;
                border: 1px solid #292e42;
                border-radius: 6px;
                padding: 7px 12px;
                font-size: 13px;
                selection-background-color: #7aa2f7;
            }
            QLineEdit:focus {
                border: 1px solid #7aa2f7;
                background-color: #24283b;
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
                border: 1px solid #3b4261;
                border-radius: 6px;
                padding: 6px 14px;
                color: #c0caf5;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #2e344e;
                border: 1px solid #7aa2f7;
                color: #ffffff;
            }
            QPushButton:disabled {
                background-color: #1a1b26;
                color: #565f89;
                border: 1px solid #292e42;
            }
            QPushButton#primaryBtn {
                background-color: #7aa2f7;
                color: #101116;
                font-weight: bold;
                border: 1px solid #7aa2f7;
            }
            QPushButton#primaryBtn:hover {
                background-color: #89b4fa;
                border-color: #89b4fa;
            }
            QPushButton#primaryBtn:disabled {
                background-color: #24283b;
                color: #565f89;
                border: 1px solid #292e42;
            }
        """)

        self._build_ui()
        self._load_library()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        # Header bar
        h_top = QHBoxLayout()
        header = QLabel("Clip Art & Illustration Library")
        header.setStyleSheet("font-size: 16px; font-weight: bold; color: #7aa2f7;")
        h_top.addWidget(header)

        h_top.addStretch()

        self.lbl_stats = QLabel("")
        self.lbl_stats.setStyleSheet("color: #8c91b0; font-size: 11px; font-weight: 500;")
        h_top.addWidget(self.lbl_stats)
        layout.addLayout(h_top)

        # Search Bar Row
        h_search = QHBoxLayout()
        h_search.setSpacing(8)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Search clip art by title, category, or keyword...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self._filter_library)
        self.search_input.returnPressed.connect(self._on_search_return_pressed)
        h_search.addWidget(self.search_input, stretch=1)

        self.btn_clear_search = QPushButton("✕ Clear")
        self.btn_clear_search.clicked.connect(self._clear_search)
        h_search.addWidget(self.btn_clear_search)

        layout.addLayout(h_search)

        # Subheader / directory note
        self.dir_label = QLabel(f"Library folder: {self.clipart_dir}")
        self.dir_label.setStyleSheet("color: #7982a9; font-size: 11px;")
        self.dir_label.setWordWrap(True)
        layout.addWidget(self.dir_label)

        # Content area: ListWidget for items or empty placeholder
        self.list_widget = QListWidget()
        self.list_widget.setViewMode(QListWidget.ViewMode.IconMode)
        self.list_widget.setIconSize(QSize(96, 96))
        self.list_widget.setGridSize(QSize(126, 136))
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

        self.empty_title = QLabel("Clip Art Library is Currently Empty")
        self.empty_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #c0caf5;")
        self.empty_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(self.empty_title)

        self.empty_desc = QLabel(
            "You can populate your library anytime by placing image files\n"
            "(.png, .svg, .jpg, .webp, .gif) into your clip art folder,\n"
            "or click 'Choose Picture from PC' below to insert any file directly."
        )
        self.empty_desc.setStyleSheet("color: #a9b1d6; font-size: 12px; line-height: 1.4;")
        self.empty_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(self.empty_desc)

        layout.addWidget(self.empty_card)
        self.empty_card.hide()

        # No search results indicator
        self.no_results_card = QFrame()
        self.no_results_card.setStyleSheet("""
            QFrame {
                background-color: #1f2335;
                border: 1px dashed #414868;
                border-radius: 8px;
                padding: 20px;
            }
        """)
        no_res_layout = QVBoxLayout(self.no_results_card)
        no_res_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        no_res_layout.setSpacing(8)

        no_res_icon = QLabel("🔍")
        no_res_icon.setStyleSheet("font-size: 30px;")
        no_res_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        no_res_layout.addWidget(no_res_icon)

        self.lbl_no_results = QLabel("No clip art matched your search.")
        self.lbl_no_results.setStyleSheet("font-size: 13px; font-weight: bold; color: #c0caf5;")
        self.lbl_no_results.setAlignment(Qt.AlignmentFlag.AlignCenter)
        no_res_layout.addWidget(self.lbl_no_results)

        btn_reset_filter = QPushButton("Reset Search Filter")
        btn_reset_filter.clicked.connect(self._clear_search)
        btn_reset_filter.setFixedWidth(160)
        no_res_layout.addWidget(btn_reset_filter, alignment=Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(self.no_results_card)
        self.no_results_card.hide()

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
        self._indexed_items.clear()
        self.no_results_card.hide()

        if not os.path.isdir(self.clipart_dir):
            self.empty_card.show()
            self.list_widget.hide()
            self.lbl_stats.setText("0 illustrations")
            return

        # Multi-directory recursive scanning: supports category subfolders for large libraries
        discovered_files: List[str] = []
        for root, _, files in os.walk(self.clipart_dir):
            for f in sorted(files):
                if os.path.splitext(f)[1].lower() in self.SUPPORTED_EXTENSIONS:
                    discovered_files.append(os.path.join(root, f))

        if not discovered_files:
            self.empty_card.show()
            self.list_widget.hide()
            self.btn_insert.setEnabled(False)
            self.lbl_stats.setText("0 illustrations")
            return

        self.empty_card.hide()
        self.list_widget.show()

        for full_path in discovered_files:
            filename = os.path.basename(full_path)
            raw_title, ext = os.path.splitext(filename)
            clean_title = raw_title.replace("_", " ").replace("-", " ").strip().title()

            # Category from subfolder
            rel_dir = os.path.relpath(os.path.dirname(full_path), self.clipart_dir)
            category = "" if rel_dir == "." else rel_dir.replace("\\", " / ")

            # Load thumbnail
            pix = QPixmap(full_path)
            if not pix.isNull():
                scaled = pix.scaled(
                    96, 96,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                display_label = clean_title if len(clean_title) <= 22 else clean_title[:20] + "…"
                item = QListWidgetItem(QIcon(scaled), display_label)
                item.setData(Qt.ItemDataRole.UserRole, full_path)
                item.setData(Qt.ItemDataRole.UserRole + 1, clean_title)
                item.setData(Qt.ItemDataRole.UserRole + 2, category)
                item.setData(Qt.ItemDataRole.UserRole + 3, raw_title)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                # Tooltip with metadata
                size_kb = os.path.getsize(full_path) / 1024
                dims = f"{pix.width()}×{pix.height()} px"
                cat_str = f"Category: {category}\n" if category else ""
                item.setToolTip(f"{clean_title}\n{cat_str}Resolution: {dims}\nFormat: {ext[1:].upper()}\nSize: {size_kb:.1f} KB")

                self.list_widget.addItem(item)
                self._indexed_items.append({
                    "item": item,
                    "title": clean_title,
                    "raw": raw_title,
                    "category": category,
                    "path": full_path,
                })

        total = len(self._indexed_items)
        self.lbl_stats.setText(f"{total} illustration{'s' if total != 1 else ''} in library")
        self._filter_library(self.search_input.text())

    def _filter_library(self, query: str) -> None:
        query_cleaned = query.strip().lower()
        if not self._indexed_items:
            return

        visible_count = 0
        search_terms = query_cleaned.split()

        for entry in self._indexed_items:
            item = entry["item"]
            title = entry["title"].lower()
            raw = entry["raw"].lower()
            cat = entry["category"].lower()

            if not query_cleaned:
                item.setHidden(False)
                visible_count += 1
            else:
                # Match all search tokens against title, filename, or category
                matches = all(
                    term in title or term in raw or term in cat
                    for term in search_terms
                )
                item.setHidden(not matches)
                if matches:
                    visible_count += 1

        total = len(self._indexed_items)
        if query_cleaned:
            self.lbl_stats.setText(f"Showing {visible_count} of {total} items")
            if visible_count == 0:
                self.list_widget.hide()
                self.lbl_no_results.setText(f"No clip art matches \"{query.strip()}\"")
                self.no_results_card.show()
                self.btn_insert.setEnabled(False)
            else:
                self.list_widget.show()
                self.no_results_card.hide()
                self._on_selection_changed()
        else:
            self.lbl_stats.setText(f"{total} illustration{'s' if total != 1 else ''} in library")
            self.list_widget.show()
            self.no_results_card.hide()
            self._on_selection_changed()

    def _clear_search(self) -> None:
        self.search_input.clear()
        self.search_input.setFocus()

    def _on_search_return_pressed(self) -> None:
        """When Enter is pressed in search, pick the first visible or selected item."""
        selected = self.list_widget.selectedItems()
        if selected and not selected[0].isHidden():
            self._on_insert_clicked()
            return

        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if not item.isHidden():
                item.setSelected(True)
                self._on_insert_clicked()
                return

    def _on_selection_changed(self) -> None:
        items = self.list_widget.selectedItems()
        self.btn_insert.setEnabled(len(items) > 0 and not items[0].isHidden())

    def _on_item_double_clicked(self, item: QListWidgetItem) -> None:
        path = item.data(Qt.ItemDataRole.UserRole)
        if path and os.path.exists(path):
            self.selected_file = path
            self.accept()

    def _on_insert_clicked(self) -> None:
        items = self.list_widget.selectedItems()
        if items and not items[0].isHidden():
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
