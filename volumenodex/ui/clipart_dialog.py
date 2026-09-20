"""Clip Art library dialog supporting native .JXL graphics, full-text metadata search, and Wikimedia Commons autoexpansion."""

import os
import re
import sys
from typing import Optional, List, Dict, Any
from PySide6.QtCore import Qt, QSize, QUrl, QTimer, QThread
from PySide6.QtGui import QIcon, QPixmap, QDesktopServices, QColor
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QFileDialog, QFrame, QMessageBox,
    QLineEdit, QProgressBar
)

from volumenodex.core.image_utils import load_image, load_pixmap, IMAGE_FILE_FILTER, SUPPORTED_EXTENSIONS
from volumenodex.clipart.metadata_parser import ClipartMetadataCache
from volumenodex.clipart.autoexpansion import AutoexpansionWorker, check_storage_limit


class ClipArtDialog(QDialog):
    """Luxury Clip Art library browser with deep EXIF/XPKeywords search, JXL fidelity, and live Wikimedia Autoexpansion."""

    SUPPORTED_EXTENSIONS = (".jxl", ".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp", ".svg")

    def __init__(self, clipart_dir: str, settings_manager=None, parent=None):
        super().__init__(parent)
        self.clipart_dir = os.path.abspath(clipart_dir)
        os.makedirs(self.clipart_dir, exist_ok=True)
        self.settings_manager = settings_manager
        self.selected_file: Optional[str] = None
        self.selected_attribution: Optional[str] = None

        self._all_records: List[Dict[str, Any]] = []
        self._indexed_items: List[Dict[str, Any]] = []
        self._current_matches: List[Dict[str, Any]] = []
        self._displayed_count: int = 0
        self._batch_size: int = 120

        self._metadata_cache = ClipartMetadataCache()
        self._load_more_clicks: int = 0
        self._active_worker: Optional[AutoexpansionWorker] = None
        self._worker_thread: Optional[QThread] = None

        self.setWindowTitle("Insert Clip Art - Volumenodex Library")
        self.resize(860, 640)
        self.setMinimumSize(680, 500)
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
                padding: 8px 14px;
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
            QPushButton#loadMoreBtn {
                background-color: #2a2c42;
                color: #7aa2f7;
                border: 1px dashed #7aa2f7;
                border-radius: 6px;
                padding: 8px 18px;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton#loadMoreBtn:hover {
                background-color: rgba(122, 162, 247, 0.15);
                color: #ffffff;
            }
        """)

        self._build_ui()
        self._scan_library_files()

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
        self.search_input.setPlaceholderText("🔍 Search illustrations by title, tags, EXIF descriptions, or keywords...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self._on_search_text_changed)
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

        # Autoexpansion status & progress bar (hidden by default)
        self.frame_expansion = QFrame()
        self.frame_expansion.setStyleSheet("background-color: #1f2335; border-radius: 6px; padding: 4px;")
        h_exp = QHBoxLayout(self.frame_expansion)
        h_exp.setContentsMargins(8, 4, 8, 4)
        self.lbl_expansion_status = QLabel("Autoexpanding library from Wikimedia Commons...")
        self.lbl_expansion_status.setStyleSheet("color: #7aa2f7; font-size: 11px; font-weight: 500;")
        h_exp.addWidget(self.lbl_expansion_status)
        h_exp.addStretch()
        self.progress_expansion = QProgressBar()
        self.progress_expansion.setRange(0, 0)
        self.progress_expansion.setFixedSize(120, 14)
        h_exp.addWidget(self.progress_expansion)
        layout.addWidget(self.frame_expansion)
        self.frame_expansion.hide()

        # Content area: ListWidget for items
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

        # Empty library card banner
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
            "Place image files (.jxl, .png, .svg, .jpg, .webp, .gif) into your clip art folder,\n"
            "or search to automatically discover illustrations from Wikimedia Commons."
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

        self.lbl_no_results = QLabel("No local clip art matched your search.")
        self.lbl_no_results.setStyleSheet("font-size: 13px; font-weight: bold; color: #c0caf5;")
        self.lbl_no_results.setAlignment(Qt.AlignmentFlag.AlignCenter)
        no_res_layout.addWidget(self.lbl_no_results)

        btn_reset_filter = QPushButton("Reset Search Filter")
        btn_reset_filter.clicked.connect(self._clear_search)
        btn_reset_filter.setFixedWidth(160)
        no_res_layout.addWidget(btn_reset_filter, alignment=Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(self.no_results_card)
        self.no_results_card.hide()

        # "Load More" / Autoexpansion Bar under results
        self.load_more_bar = QHBoxLayout()
        self.btn_load_more = QPushButton("✨ Not what you're looking for? Load more!")
        self.btn_load_more.setObjectName("loadMoreBtn")
        self.btn_load_more.setToolTip("Query Wikimedia Commons for additional illustrations and add them to your library")
        self.btn_load_more.clicked.connect(self._on_load_more_clicked)
        self.load_more_bar.addStretch()
        self.load_more_bar.addWidget(self.btn_load_more)
        self.load_more_bar.addStretch()
        layout.addLayout(self.load_more_bar)
        self.btn_load_more.hide()

        # Bottom toolbar
        bottom_bar = QHBoxLayout()
        bottom_bar.setSpacing(8)

        self.btn_open_folder = QPushButton("📂 Open Library Folder")
        self.btn_open_folder.setToolTip("Open the clip art folder in Windows File Explorer")
        self.btn_open_folder.clicked.connect(self._open_folder)
        bottom_bar.addWidget(self.btn_open_folder)

        self.btn_refresh = QPushButton("🔄 Refresh")
        self.btn_refresh.setToolTip("Refresh list from disk")
        self.btn_refresh.clicked.connect(self._scan_library_files)
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

    def _scan_library_files(self) -> None:
        """Rapidly discovers files on disk without blocking or decoding bitmaps up-front."""
        self._all_records.clear()
        self.list_widget.clear()
        self._displayed_count = 0
        self.no_results_card.hide()
        self.btn_load_more.hide()

        if not os.path.isdir(self.clipart_dir):
            self.empty_card.show()
            self.list_widget.hide()
            self.lbl_stats.setText("0 illustrations")
            return

        discovered: List[Dict[str, Any]] = []
        for root, _, files in os.walk(self.clipart_dir):
            for f in sorted(files):
                ext = os.path.splitext(f)[1].lower()
                if ext in self.SUPPORTED_EXTENSIONS:
                    full_p = os.path.join(root, f)
                    raw_title, _ = os.path.splitext(f)
                    clean_title = raw_title.replace("_", " ").replace("-", " ").strip().title()
                    rel_dir = os.path.relpath(root, self.clipart_dir)
                    cat = "" if rel_dir == "." else rel_dir.replace("\\", " / ")

                    discovered.append({
                        "path": full_p,
                        "title": clean_title,
                        "raw": raw_title,
                        "category": cat,
                        "filename": f,
                        "ext": ext,
                    })

        self._all_records = discovered
        self._indexed_items = discovered
        total = len(discovered)
        if total == 0:
            self.empty_card.show()
            self.list_widget.hide()
            self.btn_insert.setEnabled(False)
            self.lbl_stats.setText("0 illustrations")
            return

        self.empty_card.hide()
        self.list_widget.show()
        self.lbl_stats.setText(f"{total:,} illustration{'s' if total != 1 else ''} in library")
        self._run_filter()

    _load_library = _scan_library_files

    def _on_search_text_changed(self, text: str) -> None:
        self._load_more_clicks = 0
        self._run_filter()

    def _run_filter(self) -> None:
        query = self.search_input.text().strip().lower()
        search_terms = query.split()

        self.list_widget.clear()
        self._displayed_count = 0

        if not query:
            self._current_matches = self._all_records
            self.btn_load_more.hide()
        else:
            matches = []
            for rec in self._all_records:
                title = rec["title"].lower()
                raw = rec["raw"].lower()
                cat = rec["category"].lower()

                # Check filename and title first (instant match)
                if all(t in title or t in raw or t in cat for t in search_terms):
                    matches.append(rec)
                    continue

                # Query cached metadata (EXIF description, tags, keywords, artist)
                meta = self._metadata_cache.get_metadata(rec["path"])
                if meta:
                    meta_text = (
                        f"{meta.get('keywords', '')} "
                        f"{meta.get('description', '')} "
                        f"{meta.get('artist', '')} "
                        f"{meta.get('comments', '')}"
                    ).lower()
                    if all(t in title or t in raw or t in cat or t in meta_text for t in search_terms):
                        matches.append(rec)

            self._current_matches = matches

        total_matches = len(self._current_matches)

        if total_matches == 0:
            self.list_widget.hide()
            self.lbl_no_results.setText(f"No clip art matches \"{self.search_input.text().strip()}\"")
            self.no_results_card.show()
            self.btn_insert.setEnabled(False)
        else:
            self.list_widget.show()
            self.no_results_card.hide()
            self._render_match_batch(self._batch_size)

        # Update stats text
        if query:
            self.lbl_stats.setText(f"Showing {min(self._displayed_count, total_matches)} of {total_matches} matches (from {len(self._all_records):,} in library)")
            self.btn_load_more.show()
        else:
            self.lbl_stats.setText(f"Showing {min(self._displayed_count, total_matches)} of {total_matches:,} illustrations")
            self.btn_load_more.hide()

        # Trigger Clipart Library Autoexpansion if results < 3 and query entered
        if query and total_matches < 3:
            self._trigger_autoexpansion(query, offset=0, max_images=5)

    def _render_match_batch(self, count: int) -> None:
        """Renders up to count items into the list widget with thumbnails."""
        start_idx = self._displayed_count
        end_idx = min(len(self._current_matches), start_idx + count)

        for i in range(start_idx, end_idx):
            rec = self._current_matches[i]
            full_path = rec["path"]
            clean_title = rec["title"]
            category = rec["category"]
            ext = rec.get("ext", os.path.splitext(full_path)[1])

            pix = load_pixmap(full_path)
            if pix and not pix.isNull():
                scaled = pix.scaled(96, 96, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                icon = QIcon(scaled)
            else:
                icon = QIcon()

            display_label = clean_title if len(clean_title) <= 22 else clean_title[:20] + "…"
            item = QListWidgetItem(icon, display_label)
            item.setData(Qt.ItemDataRole.UserRole, full_path)
            item.setData(Qt.ItemDataRole.UserRole + 1, clean_title)
            item.setData(Qt.ItemDataRole.UserRole + 2, category)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            try:
                size_kb = os.path.getsize(full_path) / 1024
            except OSError:
                size_kb = 0.0

            cat_str = f"Category: {category}\n" if category else ""
            dims = f"{pix.width()}×{pix.height()} px" if (pix and not pix.isNull()) else "Unknown"
            item.setToolTip(f"{clean_title}\n{cat_str}Resolution: {dims}\nFormat: {ext[1:].upper()}\nSize: {size_kb:.1f} KB")

            self.list_widget.addItem(item)

        self._displayed_count = end_idx
        self._on_selection_changed()

    def _trigger_autoexpansion(self, query: str, offset: int = 0, max_images: int = 5) -> None:
        """Starts a background worker to query Wikimedia Commons."""
        autoexp_enabled = False
        size_mode = "500px"
        limit_val = 2.0
        limit_unit = "GB"
        pd_cc0 = True
        cc_by = False
        cc_by_sa = False

        if self.settings_manager:
            autoexp_enabled = getattr(self.settings_manager, "clipart_autoexpansion_enabled", True)
            size_mode = getattr(self.settings_manager, "clipart_autoexpansion_size", "500px")
            limit_val = getattr(self.settings_manager, "clipart_size_limit_val", 2.0)
            limit_unit = getattr(self.settings_manager, "clipart_size_limit_unit", "GB")
            pd_cc0 = getattr(self.settings_manager, "clipart_license_pd_cc0", True)
            cc_by = getattr(self.settings_manager, "clipart_license_cc_by", False)
            cc_by_sa = getattr(self.settings_manager, "clipart_license_cc_by_sa", False)

        if not autoexp_enabled:
            return

        if self._worker_thread and self._worker_thread.isRunning():
            return

        self.frame_expansion.show()
        self.lbl_expansion_status.setText(f"Searching Wikimedia Commons for '{query}'...")

        self._worker_thread = QThread(self)
        self._active_worker = AutoexpansionWorker(
            query=query,
            destination_dir=self.clipart_dir,
            offset=offset,
            max_images=max_images,
            target_size_mode=size_mode,
            allow_pd_cc0=pd_cc0,
            allow_cc_by=cc_by,
            allow_cc_by_sa=cc_by_sa,
            limit_val=limit_val,
            limit_unit=limit_unit
        )
        self._active_worker.moveToThread(self._worker_thread)
        self._worker_thread.started.connect(self._active_worker.run)
        self._active_worker.imageDownloaded.connect(self._on_autoexpansion_image_downloaded)
        self._active_worker.downloadFinished.connect(self._on_autoexpansion_finished)
        self._active_worker.storageLimitExceeded.connect(self._on_storage_limit_exceeded)
        self._active_worker.statusMessage.connect(self.lbl_expansion_status.setText)
        self._worker_thread.start()

    def _on_load_more_clicked(self) -> None:
        """Pagination logic: ignores first 3 images on first click, then increments ignored images by 5 (3 + 5*n)."""
        query = self.search_input.text().strip()
        if not query:
            return

        self._load_more_clicks += 1
        # Click 1: offset = 3; Click 2: offset = 3 + 5*1 = 8; Click 3: offset = 3 + 5*2 = 13
        offset = 3 + 5 * (self._load_more_clicks - 1)
        self._trigger_autoexpansion(query, offset=offset, max_images=5)

    def _on_autoexpansion_image_downloaded(self, file_path: str, meta: dict) -> None:
        """Adds newly downloaded illustration to the list widget in real time."""
        clean_title = meta.get("title", os.path.splitext(os.path.basename(file_path))[0])
        pix = load_pixmap(file_path)
        icon = QIcon(pix.scaled(96, 96, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)) if (pix and not pix.isNull()) else QIcon()

        display_label = clean_title if len(clean_title) <= 22 else clean_title[:20] + "…"
        item = QListWidgetItem(icon, display_label)
        item.setData(Qt.ItemDataRole.UserRole, file_path)
        item.setData(Qt.ItemDataRole.UserRole + 1, clean_title)
        item.setData(Qt.ItemDataRole.UserRole + 2, "Wikimedia Commons")
        item.setData(Qt.ItemDataRole.UserRole + 4, meta.get("attribution", ""))
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

        size_kb = os.path.getsize(file_path) / 1024 if os.path.exists(file_path) else 0.0
        dims = f"{pix.width()}×{pix.height()} px" if (pix and not pix.isNull()) else "Unknown"
        lic_str = f"License: {meta.get('license', 'Free')}\n"
        attr_str = f"Attribution: {meta.get('attribution')}\n" if meta.get("attribution") else ""
        item.setToolTip(f"{clean_title}\n{lic_str}{attr_str}Resolution: {dims}\nFormat: JXL\nSize: {size_kb:.1f} KB")

        self.list_widget.show()
        self.no_results_card.hide()
        self.list_widget.insertItem(0, item)
        item.setSelected(True)

        # Record in in-memory list and metadata cache
        rec = {
            "path": file_path,
            "title": clean_title,
            "raw": clean_title,
            "category": "Wikimedia Commons",
            "filename": os.path.basename(file_path),
            "ext": ".jxl"
        }
        self._all_records.insert(0, rec)
        self._metadata_cache.get_metadata(file_path)
        self.lbl_stats.setText(f"{len(self._all_records):,} illustrations in library")

    def _on_autoexpansion_finished(self, count: int) -> None:
        if self._worker_thread:
            self._worker_thread.quit()
            self._worker_thread.wait()
            self._worker_thread = None
        self._active_worker = None
        self.frame_expansion.hide()
        self._metadata_cache.save()

    def _on_storage_limit_exceeded(self, cur_gb: float, limit_gb: float) -> None:
        """Rich warning dialog when Hard Drive space limit is exceeded, offering direct jump to settings."""
        msg = QMessageBox(self)
        msg.setWindowTitle("Storage Limit Exceeded — Clipart Library Autoexpansion")
        msg.setText(
            f"<p><b>Clipart Library Hard Drive Space Exceeded</b></p>"
            f"<p>Your Clipart Library has reached <b>{cur_gb:.2f} GB</b>, exceeding your configured "
            f"hard drive safety limit of <b>{limit_gb:.2f} GB</b>.</p>"
            f"<p>Autoexpansion downloads have been paused to protect your local disk space. "
            f"You can increase this limit anytime in Studio Settings.</p>"
        )
        msg.setIcon(QMessageBox.Icon.Warning)
        btn_settings = msg.addButton("Open Settings...", QMessageBox.ButtonRole.ActionRole)
        msg.addButton("Dismiss", QMessageBox.ButtonRole.RejectRole)
        msg.exec()

        if msg.clickedButton() == btn_settings and self.settings_manager:
            from volumenodex.ui.settings_dialog import SettingsDialog
            sdlg = SettingsDialog(self.settings_manager, parent=self)
            sdlg.highlight_autoexpansion_limit()
            sdlg.exec()

    def _clear_search(self) -> None:
        self.search_input.clear()
        self.search_input.setFocus()

    def _on_search_return_pressed(self) -> None:
        selected = self.list_widget.selectedItems()
        if selected and not selected[0].isHidden():
            self._on_insert_clicked()
            return
        if self.list_widget.count() > 0:
            item = self.list_widget.item(0)
            if item and not item.isHidden():
                item.setSelected(True)
                self._on_insert_clicked()

    def _on_selection_changed(self) -> None:
        items = self.list_widget.selectedItems()
        self.btn_insert.setEnabled(len(items) > 0 and not items[0].isHidden())

    def _on_item_double_clicked(self, item: QListWidgetItem) -> None:
        path = item.data(Qt.ItemDataRole.UserRole)
        if path and os.path.exists(path):
            self.selected_file = path
            self.selected_attribution = item.data(Qt.ItemDataRole.UserRole + 4) or None
            self.accept()

    def _on_insert_clicked(self) -> None:
        items = self.list_widget.selectedItems()
        if items and not items[0].isHidden():
            path = items[0].data(Qt.ItemDataRole.UserRole)
            if path and os.path.exists(path):
                self.selected_file = path
                self.selected_attribution = items[0].data(Qt.ItemDataRole.UserRole + 4) or None
                self.accept()

    def _open_folder(self) -> None:
        QDesktopServices.openUrl(QUrl.fromLocalFile(self.clipart_dir))

    def _browse_custom_image(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Choose Image File",
            "",
            IMAGE_FILE_FILTER
        )
        if file_path and os.path.exists(file_path):
            self.selected_file = file_path
            self.selected_attribution = None
            self.accept()

    def _stop_worker(self) -> None:
        if self._active_worker:
            self._active_worker.cancel()
        if self._worker_thread and self._worker_thread.isRunning():
            self._worker_thread.quit()
            if not self._worker_thread.wait(1000):
                self._worker_thread.terminate()
                self._worker_thread.wait(500)
        self._worker_thread = None
        self._active_worker = None

    def done(self, r: int) -> None:
        self._stop_worker()
        self._metadata_cache.save()
        super().done(r)

    def closeEvent(self, event):
        self._stop_worker()
        self._metadata_cache.save()
        super().closeEvent(event)
