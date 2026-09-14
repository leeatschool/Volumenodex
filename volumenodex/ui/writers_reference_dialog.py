"""Writers Reference pop-up window: offline compendium of human knowledge for fiction authors."""

import os
import shutil
from pathlib import Path
from typing import Optional, List, Dict

from PySide6.QtCore import Qt, Signal, QSize, QRectF, QPointF
from PySide6.QtGui import (
    QColor, QFont, QIcon, QPixmap, QPainter, QBrush, QPen,
    QPainterPath, QKeySequence, QShortcut
)
from PySide6.QtWidgets import (
    QApplication, QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QListWidget, QListWidgetItem,
    QScrollArea, QFrame, QSplitter, QTextBrowser, QComboBox,
    QMessageBox, QFileDialog, QSizePolicy
)

from volumenodex.reference.reference_model import ReferenceEntry, ReferenceCategory
from volumenodex.reference.reference_manager import ReferenceManager
from volumenodex.ui.vector_icons import VectorIconFactory


class WritersReferenceDialog(QDialog):
    """The Writers Reference pop-up window featuring offline knowledge, live search, and custom entries."""

    insertIntoDocumentRequested = Signal(str)

    def __init__(self, manager: Optional[ReferenceManager] = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Writers Reference — Offline Compendium for Authors")
        self.resize(1080, 720)
        self.setMinimumSize(780, 520)

        self.manager = manager or ReferenceManager()
        self._custom_logo_path = self._discover_logo_path()
        if self._custom_logo_path and os.path.exists(self._custom_logo_path):
            self.setWindowIcon(QIcon(self._custom_logo_path))
        self._current_entry: Optional[ReferenceEntry] = None

        self._init_styles()
        self._init_ui()
        self._setup_shortcuts()
        self._refresh_results()

    def _discover_logo_path(self) -> Optional[str]:
        """Looks for the Writers Reference logo in standard locations."""
        candidates = [
            os.path.join(os.path.dirname(__file__), "..", "resources", "writers_reference_logo.png"),
            os.path.join(os.path.dirname(__file__), "..", "..", "assets", "writers_reference_logo.png"),
            os.path.join(os.path.dirname(__file__), "..", "..", "assets", "writref.png"),
            r"C:\Users\thele\Downloads\writref.png",
            os.path.join(str(Path.home()), "Downloads", "writref.png"),
            os.path.join(str(Path.home()), "Downloads", "writers_reference_logo.png"),
            os.path.join(os.path.dirname(__file__), "..", "resources", "writers_reference_logo.jpg"),
            os.path.join(os.path.dirname(__file__), "..", "resources", "writers_reference_logo.jpeg"),
            os.path.join(str(Path.home()), "Downloads", "writers_reference_logo.jpg"),
            os.path.join(str(Path.home()), "Pictures", "writers_reference_logo.png"),
        ]
        for c in candidates:
            if os.path.exists(c):
                return c
        return None

    def _init_styles(self) -> None:
        self.setStyleSheet("""
            QDialog {
                background-color: #101116;
                color: #e1e4f2;
                font-family: 'Segoe UI', 'SF Pro Text', sans-serif;
            }
            QLabel {
                color: #e1e4f2;
            }
            QLineEdit {
                background-color: #181922;
                color: #f1f3fa;
                border: 1px solid #2a2c3d;
                border-radius: 6px;
                padding: 8px 14px;
                font-size: 13px;
                selection-background-color: #7aa2f7;
            }
            QLineEdit:focus {
                border: 1px solid #7aa2f7;
                background-color: #1d1f2b;
            }
            QListWidget {
                background-color: #14151d;
                border: 1px solid #2a2c3d;
                border-radius: 6px;
                padding: 4px;
                outline: none;
                color: #e1e4f2;
                font-size: 13px;
            }
            QListWidget::item {
                border-bottom: 1px solid #1f212e;
                border-radius: 4px;
                padding: 8px 10px;
                margin-bottom: 2px;
                color: #e1e4f2;
            }
            QListWidget::item:hover {
                background-color: #1e202c;
                color: #ffffff;
            }
            QListWidget::item:selected {
                background-color: #24283b;
                border-left: 3px solid #7aa2f7;
                color: #ffffff;
            }
            QPushButton {
                background-color: #1c1e28;
                color: #e1e4f2;
                border: 1px solid #2a2c3d;
                border-radius: 5px;
                padding: 6px 14px;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #282b3a;
                border-color: #7aa2f7;
                color: #ffffff;
            }
            QPushButton#primaryBtn {
                background-color: #7aa2f7;
                color: #101116;
                border: 1px solid #7aa2f7;
                font-weight: 700;
            }
            QPushButton#primaryBtn:hover {
                background-color: #89b4fa;
                border-color: #89b4fa;
            }
            QPushButton#catPill {
                background-color: #161720;
                color: #a2a7c4;
                border: 1px solid #232532;
                border-radius: 12px;
                padding: 4px 12px;
                font-size: 11px;
                font-weight: 500;
            }
            QPushButton#catPill:hover {
                background-color: #232532;
                color: #e1e4f2;
                border-color: #3b4261;
            }
            QPushButton#catPill:checked {
                background-color: rgba(122, 162, 247, 0.18);
                color: #7aa2f7;
                border: 1px solid #7aa2f7;
                font-weight: 700;
            }
            QTextBrowser {
                background-color: #14151d;
                border: 1px solid #2a2c3d;
                border-radius: 6px;
                padding: 16px;
                color: #e1e4f2;
                font-size: 13px;
                line-height: 1.5;
            }
            QScrollBar:vertical {
                background: #101116;
                width: 10px;
                margin: 0px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background: #2a2c3d;
                min-height: 20px;
                border-radius: 5px;
                margin: 2px;
            }
            QScrollBar::handle:vertical:hover {
                background: #7aa2f7;
            }
            QScrollBar:horizontal {
                background: #101116;
                height: 6px;
                margin: 0px;
                border-radius: 3px;
            }
            QScrollBar::handle:horizontal {
                background: #2a2c3d;
                min-width: 20px;
                border-radius: 3px;
                margin: 1px;
            }
            QScrollBar::handle:horizontal:hover {
                background: #7aa2f7;
            }
        """)

    def _init_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(18, 14, 18, 14)
        root_layout.setSpacing(12)

        # 1. Top Header with Logo & Actions
        h_header = QHBoxLayout()
        h_header.setSpacing(14)

        # Logo display widget
        self.lbl_logo = QLabel()
        self._render_logo()
        self.lbl_logo.setToolTip("Writers Reference")
        h_header.addWidget(self.lbl_logo)

        # Title & Subtitle block
        v_title = QVBoxLayout()
        v_title.setSpacing(2)
        lbl_main_title = QLabel("WRITERS REFERENCE")
        lbl_main_title.setStyleSheet("font-size: 18px; font-weight: 800; letter-spacing: 1.5px; color: #7aa2f7;")
        v_title.addWidget(lbl_main_title)

        self.lbl_subtitle = QLabel(f"Condensed Offline Knowledge Compendium • {self.manager.total_count} Verified Topics")
        self.lbl_subtitle.setStyleSheet("font-size: 11px; color: #8c91b0; font-weight: 500;")
        v_title.addWidget(self.lbl_subtitle)
        h_header.addLayout(v_title)

        h_header.addStretch()

        root_layout.addLayout(h_header)

        # 2. Search Bar
        h_search = QHBoxLayout()
        h_search.setSpacing(8)
        self.edit_search = QLineEdit()
        self.edit_search.setPlaceholderText("🔍 Search human knowledge (e.g. arsenic, plate armor, longbow, peerage, rigor mortis, sailing, shock)...")
        self.edit_search.textChanged.connect(self._on_search_text_changed)
        h_search.addWidget(self.edit_search)

        btn_clear = QPushButton("✕ Clear")
        btn_clear.clicked.connect(self._clear_search)
        h_search.addWidget(btn_clear)
        root_layout.addLayout(h_search)

        # 3. Category Filter Chips (Scrollable row)
        cat_scroll = QScrollArea()
        cat_scroll.setWidgetResizable(True)
        cat_scroll.setFrameShape(QFrame.Shape.NoFrame)
        cat_scroll.setFixedHeight(36)
        cat_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        cat_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        cat_scroll.setStyleSheet("""
            QScrollArea, QScrollArea > QWidget {
                background: transparent;
                border: none;
            }
            QScrollBar:horizontal {
                background: transparent;
                height: 4px;
            }
            QScrollBar::handle:horizontal {
                background: #2a2c3d;
                border-radius: 2px;
            }
            QScrollBar::handle:horizontal:hover {
                background: #7aa2f7;
            }
        """)

        cat_container = QWidget()
        self.cat_layout = QHBoxLayout(cat_container)
        self.cat_layout.setContentsMargins(0, 0, 0, 0)
        self.cat_layout.setSpacing(6)

        self.cat_buttons: Dict[str, QPushButton] = {}
        all_cats = ["All Categories"] + self.manager.get_categories() + ["My Custom Lore"]

        for cat in all_cats:
            btn = QPushButton(cat.replace("&", "&&"))
            btn.setObjectName("catPill")
            btn.setCheckable(True)
            if cat == "All Categories":
                btn.setChecked(True)
            btn.clicked.connect(lambda checked, c=cat: self._on_category_chip_clicked(c))
            self.cat_layout.addWidget(btn)
            self.cat_buttons[cat] = btn

        self.cat_layout.addStretch()
        cat_scroll.setWidget(cat_container)
        root_layout.addWidget(cat_scroll)

        # 4. Main Two-Pane Splitter: Results List + Detail Viewer
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #20222f;
                width: 4px;
            }
        """)

        # Left Column: Search Results List & Match Header
        left_container = QWidget()
        v_left = QVBoxLayout(left_container)
        v_left.setContentsMargins(0, 0, 0, 0)
        v_left.setSpacing(6)

        self.lbl_match_count = QLabel("Results")
        self.lbl_match_count.setStyleSheet("font-size: 11px; font-weight: 600; color: #8c91b0; text-transform: uppercase;")
        v_left.addWidget(self.lbl_match_count)

        self.list_results = QListWidget()
        self.list_results.currentItemChanged.connect(self._on_item_selected)
        v_left.addWidget(self.list_results)
        splitter.addWidget(left_container)

        # Right Column: Topic Detail Viewer
        right_container = QWidget()
        v_right = QVBoxLayout(right_container)
        v_right.setContentsMargins(0, 0, 0, 0)
        v_right.setSpacing(8)

        # Action Bar above reader
        h_actions = QHBoxLayout()
        h_actions.setSpacing(8)

        self.btn_insert = QPushButton("📝 Insert into Manuscript")
        self.btn_insert.setObjectName("primaryBtn")
        self.btn_insert.setToolTip("Insert quick facts and summary directly into your open manuscript")
        self.btn_insert.clicked.connect(self._insert_current_into_document)
        h_actions.addWidget(self.btn_insert)

        self.btn_copy_facts = QPushButton("📋 Copy Facts")
        self.btn_copy_facts.setToolTip("Copy quick reference summary and table to clipboard")
        self.btn_copy_facts.clicked.connect(self._copy_facts_to_clipboard)
        h_actions.addWidget(self.btn_copy_facts)

        h_actions.addStretch()
        v_right.addLayout(h_actions)

        # Reader Browser
        self.text_browser = QTextBrowser()
        self.text_browser.setOpenExternalLinks(False)
        self.text_browser.anchorClicked.connect(self._on_anchor_clicked)
        v_right.addWidget(self.text_browser)
        splitter.addWidget(right_container)

        splitter.setSizes([340, 700])
        root_layout.addWidget(splitter, stretch=1)

    def _render_logo(self) -> None:
        """Renders the Writers Reference logo emblem."""
        target_size = 64
        if self._custom_logo_path and os.path.exists(self._custom_logo_path):
            src = QPixmap(self._custom_logo_path)
            if not src.isNull():
                rounded = QPixmap(target_size, target_size)
                rounded.fill(Qt.GlobalColor.transparent)

                painter = QPainter(rounded)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
                painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

                path = QPainterPath()
                path.addRoundedRect(QRectF(0.5, 0.5, target_size - 1, target_size - 1), 10, 10)
                painter.setClipPath(path)

                scaled_src = src.scaled(
                    target_size, target_size,
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation
                )
                painter.drawPixmap(0, 0, scaled_src)

                # Elegant subtle border matching theme
                painter.setClipping(False)
                painter.setPen(QPen(QColor(122, 162, 247, 130), 1.5))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRoundedRect(QRectF(0.5, 0.5, target_size - 1, target_size - 1), 10, 10)
                painter.end()

                self.lbl_logo.setPixmap(rounded)
                return

        # Vector Emblem Fallback: An open leather tome with a golden quill
        pix = QPixmap(44, 44)
        pix.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        # Outer glowing circle / seal
        painter.setBrush(QBrush(QColor("#1f2335")))
        painter.setPen(QPen(QColor("#7aa2f7"), 1.5))
        painter.drawEllipse(2, 2, 40, 40)

        # Inner book shape
        book_path = QPainterPath()
        book_path.moveTo(8, 28)
        book_path.cubicTo(14, 30, 20, 27, 22, 29)
        book_path.cubicTo(24, 27, 30, 30, 36, 28)
        book_path.lineTo(36, 15)
        book_path.cubicTo(30, 17, 24, 14, 22, 16)
        book_path.cubicTo(20, 14, 14, 17, 8, 15)
        book_path.closeSubpath()

        painter.setBrush(QBrush(QColor("#24283b")))
        painter.setPen(QPen(QColor("#c0caf5"), 1.2))
        painter.drawPath(book_path)

        # Spine center line
        painter.drawLine(22, 16, 22, 29)

        # Golden Quill feather
        quill = QPainterPath()
        quill.moveTo(32, 8)
        quill.cubicTo(26, 12, 22, 19, 18, 25)
        quill.lineTo(19, 25)
        quill.cubicTo(24, 18, 28, 13, 33, 9)
        quill.closeSubpath()

        painter.setBrush(QBrush(QColor("#e0af68")))
        painter.setPen(QPen(QColor("#e0af68"), 1))
        painter.drawPath(quill)

        painter.end()
        self.lbl_logo.setPixmap(pix)

    def set_custom_logo(self, path: str) -> bool:
        """Sets and copies a user-provided logo image for the Writers Reference."""
        if not os.path.exists(path):
            return False

        try:
            target_dir = os.path.join(os.path.dirname(__file__), "..", "resources")
            os.makedirs(target_dir, exist_ok=True)
            target_path = os.path.join(target_dir, "writers_reference_logo.png")
            shutil.copyfile(path, target_path)
            self._custom_logo_path = target_path
            self._render_logo()
            return True
        except Exception as e:
            print(f"Error copying logo file: {e}")
            return False

    def _choose_custom_logo(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Writers Reference Logo", "", "Images (*.png *.jpg *.jpeg *.svg *.bmp)"
        )
        if path:
            if self.set_custom_logo(path):
                QMessageBox.information(self, "Logo Updated", "Writers Reference logo successfully updated!")
            else:
                QMessageBox.warning(self, "Error", "Could not load the selected image file.")

    def _setup_shortcuts(self) -> None:
        QShortcut(QKeySequence("Ctrl+F"), self, self.edit_search.setFocus)
        QShortcut(QKeySequence("Escape"), self, self.close)

    def _clear_search(self) -> None:
        self.edit_search.clear()
        self.edit_search.setFocus()

    def _on_search_text_changed(self, text: str) -> None:
        self._refresh_results()

    def _on_category_chip_clicked(self, category: str) -> None:
        for cat, btn in self.cat_buttons.items():
            btn.setChecked(cat == category)
        self._refresh_results()

    def _get_active_category(self) -> Optional[str]:
        for cat, btn in self.cat_buttons.items():
            if btn.isChecked():
                return cat
        return "All Categories"

    def _refresh_results(self) -> None:
        query = self.edit_search.text()
        active_cat = self._get_active_category()

        only_custom = False
        cat_filter = active_cat
        if active_cat == "All Categories":
            cat_filter = None
        elif active_cat == "My Custom Lore":
            cat_filter = None
            only_custom = True

        entries = self.manager.search(query=query, category=cat_filter, only_custom=only_custom)

        self.list_results.clear()
        for entry in entries:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, entry.id)

            # Custom styled item text
            src_tag = " ★ Custom" if entry.is_custom else ""
            item.setText(f"{entry.title}\n{entry.category}{src_tag}")
            self.list_results.addItem(item)

        self.lbl_match_count.setText(f"Found {len(entries)} Topics")
        self.lbl_subtitle.setText(f"Condensed Offline Knowledge Compendium • {self.manager.total_count} Verified Topics")

        if self.list_results.count() > 0:
            self.list_results.setCurrentRow(0)
        else:
            self._render_empty_state()

    def _on_item_selected(self, current: Optional[QListWidgetItem], previous=None) -> None:
        if not current:
            self._current_entry = None
            return
        entry_id = current.data(Qt.ItemDataRole.UserRole)
        entry = self.manager.get_entry(entry_id)
        if entry:
            self._current_entry = entry
            self._render_entry_detail(entry)

    def _render_empty_state(self) -> None:
        self._current_entry = None
        if self.manager.total_count == 0:
            html = """
            <div style="text-align: center; padding-top: 80px; color: #8c91b0;">
                <h2 style="color: #7aa2f7; font-size: 20px;">Writers Reference is Empty</h2>
                <p style="font-size: 13.5px; line-height: 1.6; max-width: 520px; margin: 12px auto 0 auto;">
                    No reference topics are currently bundled. To add knowledge topics, run the standalone <b>Reference Builder Tool</b> (<code>tools/reference_builder.py</code>) to curate topics for your offline library.
                </p>
            </div>
            """
        else:
            html = """
            <div style="text-align: center; padding-top: 80px; color: #8c91b0;">
                <h2 style="color: #7aa2f7; font-size: 20px;">No Matching Topics Found</h2>
                <p style="font-size: 13px;">Try searching with broader terms or clearing active filters.</p>
            </div>
            """
        self.text_browser.setHtml(html)

    def _render_entry_detail(self, entry: ReferenceEntry) -> None:

        badge_bg = "#232532" if not entry.is_custom else "#1e293b"
        badge_text = "#7aa2f7" if not entry.is_custom else "#38bdf8"
        source_label = "Verified Core Knowledge" if not entry.is_custom else "Personal Custom Lore"

        tags_html = "".join(
            f"<span style='background-color: #1e202c; color: #a2a7c4; padding: 2px 8px; border-radius: 10px; font-size: 11px; margin-right: 4px;'>#{t}</span>"
            for t in entry.tags
        )

        facts_table_html = ""
        if entry.quick_facts:
            rows_html = ""
            for k, v in entry.quick_facts.items():
                rows_html += f"""
                <tr>
                    <td style="padding: 6px 10px; font-weight: 600; color: #7aa2f7; border-bottom: 1px solid #1f212e; width: 32%;">{k}</td>
                    <td style="padding: 6px 10px; color: #f1f3fa; border-bottom: 1px solid #1f212e;">{v}</td>
                </tr>
                """
            facts_table_html = f"""
            <div style="margin: 16px 0; background-color: #161720; border: 1px solid #26293b; border-radius: 6px; overflow: hidden;">
                <div style="background-color: #1c1e2b; padding: 6px 12px; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; color: #7aa2f7;">
                    ⚡ Quick Facts & Realistic Properties
                </div>
                <table style="width: 100%; border-collapse: collapse; font-size: 12.5px;">
                    {rows_html}
                </table>
            </div>
            """

        fiction_tips_html = ""
        if entry.fiction_tips:
            fiction_tips_html = f"""
            <div style="margin: 16px 0; background-color: #171d2b; border-left: 4px solid #bb9af7; padding: 12px 16px; border-radius: 4px;">
                <div style="font-size: 12px; font-weight: 700; color: #bb9af7; text-transform: uppercase; margin-bottom: 4px;">
                    💡 Fiction Writer's Reality Guide & Tropes to Avoid
                </div>
                <div style="color: #e1e4f2; font-size: 13px; line-height: 1.5;">
                    {entry.fiction_tips}
                </div>
            </div>
            """

        related_html = ""
        if entry.related_entries:
            links = []
            for rel_id in entry.related_entries:
                rel_entry = self.manager.get_entry(rel_id)
                if rel_entry:
                    links.append(f"<a href='topic:{rel_id}' style='color: #7aa2f7; text-decoration: none; font-weight: 600;'>{rel_entry.title}</a>")
            if links:
                related_html = f"""
                <div style="margin-top: 20px; padding-top: 12px; border-top: 1px solid #1f212e; font-size: 12px; color: #8c91b0;">
                    <b>Related Reference Topics:</b> {" • ".join(links)}
                </div>
                """

        # Format main paragraphs
        paragraphs = entry.content.split("\n\n")
        body_html = "".join(f"<p style='margin-bottom: 12px; line-height: 1.6;'>{p.replace(chr(10), '<br>')}</p>" for p in paragraphs if p.strip())

        html = f"""
        <div style="font-family: 'Segoe UI', sans-serif; color: #e1e4f2;">
            <div style="display: flex; justify-content: space-between; align-items: baseline;">
                <span style="background-color: {badge_bg}; color: {badge_text}; font-size: 11px; font-weight: 700; padding: 3px 10px; border-radius: 4px; text-transform: uppercase;">
                    {entry.category} • {source_label}
                </span>
            </div>
            <h1 style="font-size: 22px; font-weight: 800; color: #ffffff; margin: 10px 0 6px 0;">{entry.title}</h1>
            <div style="margin-bottom: 12px;">{tags_html}</div>

            <div style="font-size: 14px; font-weight: 500; color: #c0caf5; margin-bottom: 16px; border-left: 3px solid #7aa2f7; padding-left: 10px; line-height: 1.5;">
                {entry.summary}
            </div>

            {facts_table_html}

            <div style="font-size: 13.5px; color: #d0d4eb; margin-top: 16px;">
                {body_html}
            </div>

            {fiction_tips_html}

            {related_html}
        </div>
        """
        self.text_browser.setHtml(html)

    def _on_anchor_clicked(self, url) -> None:
        scheme = url.scheme()
        topic_id = url.path()
        if scheme == "topic" or topic_id:
            target_id = topic_id or url.toString().replace("topic:", "")
            target_entry = self.manager.get_entry(target_id)
            if target_entry:
                # Select it in the list
                for i in range(self.list_results.count()):
                    item = self.list_results.item(i)
                    if item.data(Qt.ItemDataRole.UserRole) == target_id:
                        self.list_results.setCurrentItem(item)
                        return
                # If not in filtered list, clear search and select
                self.edit_search.clear()
                for i in range(self.list_results.count()):
                    item = self.list_results.item(i)
                    if item.data(Qt.ItemDataRole.UserRole) == target_id:
                        self.list_results.setCurrentItem(item)
                        return

    def _insert_current_into_document(self) -> None:
        if not self._current_entry:
            return
        e = self._current_entry

        lines = [
            f"=== WRITERS REFERENCE: {e.title} ({e.category}) ===",
            f"Summary: {e.summary}",
        ]
        if e.quick_facts:
            lines.append("Quick Facts:")
            for k, v in e.quick_facts.items():
                lines.append(f"  • {k}: {v}")
        if e.fiction_tips:
            lines.append(f"Fiction Tip: {e.fiction_tips}")
        lines.append("")

        text_to_insert = "\n".join(lines)
        self.insertIntoDocumentRequested.emit(text_to_insert)

        orig_text = self.btn_insert.text()
        self.btn_insert.setText("✓ Inserted into Manuscript!")
        from PySide6.QtCore import QTimer
        QTimer.singleShot(1800, lambda: self.btn_insert.setText(orig_text))

    def _copy_facts_to_clipboard(self) -> None:
        if not self._current_entry:
            return
        e = self._current_entry

        lines = [f"{e.title} ({e.category})", f"Summary: {e.summary}"]
        if e.quick_facts:
            lines.append("Quick Facts:")
            for k, v in e.quick_facts.items():
                lines.append(f"  - {k}: {v}")
        if e.fiction_tips:
            lines.append(f"Writing Tip: {e.fiction_tips}")

        from PySide6.QtGui import QClipboard
        clipboard = QApplication.clipboard()
        clipboard.setText("\n".join(lines))

        orig_text = self.btn_copy_facts.text()
        self.btn_copy_facts.setText("✓ Copied to Clipboard!")
        from PySide6.QtCore import QTimer
        QTimer.singleShot(1800, lambda: self.btn_copy_facts.setText(orig_text))
