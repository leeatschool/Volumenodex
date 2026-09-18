"""Graphical Reference Bookshelf and Built-In E-Reader for Volumenodex."""

import os
import re
from typing import Optional, List, Dict
from PySide6.QtCore import Qt, Signal, QSize, QRect, QRectF, QPointF, QTimer
from PySide6.QtGui import (
    QPainter, QColor, QPen, QBrush, QFont, QLinearGradient,
    QPainterPath, QIcon, QPixmap, QDesktopServices, QTextCursor
)
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QScrollArea, QFrame, QSplitter, QTextBrowser,
    QListWidget, QListWidgetItem, QFileDialog, QSizePolicy,
    QComboBox, QSlider, QMessageBox, QGraphicsDropShadowEffect
)

from volumenodex.reference.epub_reader import EpubBook, EpubChapter, EpubParser
from volumenodex.reference.bookshelf_model import (
    ReferenceBookshelfManager, BookCoverStyle, BOOK_COLOR_PALETTES
)


class BoundBookWidget(QWidget):
    """Custom graphical widget rendering an authentic leather-bound hardcover book."""

    clicked = Signal(object)  # EpubBook

    def __init__(self, book: EpubBook, style: BookCoverStyle, parent=None):
        super().__init__(parent)
        self.book = book
        self.cover_style = style
        self.is_hovered = False

        self.setFixedSize(148, 206)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # Full tooltip
        author_str = f"Author: {self.book.author}\n" if self.book.author else ""
        desc_str = f"\n{self.book.description[:240]}…" if self.book.description else ""
        self.setToolTip(
            f"📖 {self.book.title}\n{author_str}"
            f"Chapters: {len(self.book.chapters)} • Size: {self.book.file_size_mb:.2f} MB"
            f"{desc_str}\n\nClick to open in built-in E-Reader"
        )

    def enterEvent(self, event):
        self.is_hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.is_hovered = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.book)
        super().mousePressEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        w = self.width()
        h = self.height()

        # Lift effect when hovered
        y_offset = -6 if self.is_hovered else 0

        # 1. Book Drop Shadow
        shadow_rect = QRectF(6, 12 + y_offset, w - 10, h - 14)
        shadow_path = QPainterPath()
        shadow_path.addRoundedRect(shadow_rect, 6, 6)
        painter.fillPath(shadow_path, QColor(0, 0, 0, 95 if self.is_hovered else 65))

        # 2. Stacked Paper Page Block on the right edge
        paper_rect = QRectF(w - 18, 8 + y_offset, 14, h - 18)
        paper_grad = QLinearGradient(paper_rect.left(), 0, paper_rect.right(), 0)
        paper_grad.setColorAt(0.0, QColor("#e8e0cc"))
        paper_grad.setColorAt(0.5, QColor("#f4eedf"))
        paper_grad.setColorAt(1.0, QColor("#d0c4aa"))
        painter.fillRect(paper_rect, paper_grad)

        # Page edge grooves
        painter.setPen(QPen(QColor(160, 145, 120, 90), 1))
        for line_x in (w - 15, w - 12, w - 9, w - 6):
            painter.drawLine(int(line_x), int(8 + y_offset), int(line_x), int(h - 10 + y_offset))

        # 3. Main Hardcover Leather Surface
        book_rect = QRectF(4, 4 + y_offset, w - 16, h - 12)
        cover_grad = QLinearGradient(0, book_rect.top(), 0, book_rect.bottom())
        cover_grad.setColorAt(0.0, QColor(self.cover_style.leather_top))
        cover_grad.setColorAt(1.0, QColor(self.cover_style.leather_bottom))

        cover_path = QPainterPath()
        cover_path.addRoundedRect(book_rect, 5, 5)
        painter.fillPath(cover_path, cover_grad)

        # 4. Gilded Foil Outer & Inner Border
        gilt_color = QColor(self.cover_style.gilt_foil)
        if self.is_hovered:
            gilt_color = gilt_color.lighter(120)

        painter.setPen(QPen(gilt_color, 1.5))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        inner_border = book_rect.adjusted(6, 6, -6, -6)
        painter.drawRoundedRect(inner_border, 3, 3)

        painter.setPen(QPen(QColor(gilt_color.red(), gilt_color.green(), gilt_color.blue(), 110), 0.8))
        inner_sub_border = book_rect.adjusted(9, 9, -9, -9)
        painter.drawRoundedRect(inner_sub_border, 2, 2)

        # 5. Book Spine Ribs on Left
        spine_width = 14
        spine_rect = QRectF(book_rect.left(), book_rect.top(), spine_width, book_rect.height())
        spine_grad = QLinearGradient(spine_rect.left(), 0, spine_rect.right(), 0)
        spine_grad.setColorAt(0.0, QColor(255, 255, 255, 40))
        spine_grad.setColorAt(0.7, QColor(0, 0, 0, 0))
        spine_grad.setColorAt(1.0, QColor(0, 0, 0, 70))
        painter.fillRect(spine_rect, spine_grad)

        # Raised horizontal spine ribs
        rib_y_positions = [
            book_rect.top() + book_rect.height() * 0.20,
            book_rect.top() + book_rect.height() * 0.40,
            book_rect.top() + book_rect.height() * 0.60,
            book_rect.top() + book_rect.height() * 0.80,
        ]
        for ry in rib_y_positions:
            painter.setPen(QPen(QColor(255, 255, 255, 70), 1))
            painter.drawLine(int(book_rect.left()), int(ry), int(book_rect.left() + spine_width), int(ry))
            painter.setPen(QPen(QColor(0, 0, 0, 90), 1))
            painter.drawLine(int(book_rect.left()), int(ry + 1), int(book_rect.left() + spine_width), int(ry + 1))

        # 6. Satin Bookmark Ribbon Hanging at Bottom
        ribbon_x = book_rect.left() + book_rect.width() * 0.65
        ribbon_w = 10
        ribbon_h = 16
        ribbon_rect = QRectF(ribbon_x, book_rect.bottom() - 4, ribbon_w, ribbon_h)
        ribbon_color = QColor(self.cover_style.ribbon_color)
        painter.fillRect(ribbon_rect, ribbon_color)

        # Cutout notch at bottom of ribbon
        ribbon_notch = QPainterPath()
        ribbon_notch.moveTo(ribbon_rect.left(), ribbon_rect.bottom())
        ribbon_notch.lineTo(ribbon_rect.center().x(), ribbon_rect.bottom() - 4)
        ribbon_notch.lineTo(ribbon_rect.right(), ribbon_rect.bottom())
        painter.fillPath(ribbon_notch, QColor(0, 0, 0, 80))

        # 7. Gilded Foil Title Typography
        painter.setPen(QPen(gilt_color, 1))
        title_font = QFont("Georgia", 9, QFont.Weight.Bold)
        title_font.setStyleHint(QFont.StyleHint.Serif)
        painter.setFont(title_font)

        text_rect = QRectF(
            book_rect.left() + spine_width + 6,
            book_rect.top() + 18,
            book_rect.width() - spine_width - 16,
            96
        )

        display_title = self.book.title
        # If title is long, wrap gracefully
        painter.drawText(
            text_rect,
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap,
            display_title
        )

        # Decorative ornament dividing title and author
        painter.setPen(QPen(QColor(gilt_color.red(), gilt_color.green(), gilt_color.blue(), 140), 1))
        orn_y = book_rect.top() + 124
        cx = book_rect.left() + spine_width + (book_rect.width() - spine_width) / 2
        painter.drawLine(int(cx - 16), int(orn_y), int(cx + 16), int(orn_y))
        painter.drawText(QRectF(cx - 8, orn_y - 6, 16, 12), Qt.AlignmentFlag.AlignCenter, "♦")

        # 8. Author Name Typography
        author_font = QFont("Georgia", 8, QFont.Weight.Medium)
        author_font.setStyleHint(QFont.StyleHint.Serif)
        painter.setFont(author_font)
        painter.setPen(QPen(QColor(gilt_color.red(), gilt_color.green(), gilt_color.blue(), 190), 1))

        author_rect = QRectF(
            book_rect.left() + spine_width + 4,
            book_rect.top() + 138,
            book_rect.width() - spine_width - 12,
            38
        )
        display_author = self.book.author if len(self.book.author) <= 30 else self.book.author[:28] + "…"
        painter.drawText(
            author_rect,
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap,
            display_author
        )

        # 9. Hover Badge Overlay
        if self.is_hovered:
            badge_rect = QRectF(book_rect.left() + 8, book_rect.bottom() - 26, book_rect.width() - 16, 20)
            badge_path = QPainterPath()
            badge_path.addRoundedRect(badge_rect, 4, 4)
            painter.fillPath(badge_path, QColor(16, 17, 22, 220))
            painter.setPen(QPen(QColor("#7aa2f7"), 1))
            painter.drawRoundedRect(badge_rect, 4, 4)

            badge_font = QFont("Segoe UI", 8, QFont.Weight.Bold)
            painter.setFont(badge_font)
            painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, "Read Volume 📖")


class ReferenceBookshelfView(QWidget):
    """The polished mahogany bookshelf interface displaying physical bound volumes."""

    bookSelected = Signal(object)  # EpubBook

    def __init__(self, manager: ReferenceBookshelfManager, parent=None):
        super().__init__(parent)
        self.manager = manager
        self._book_widgets: List[BoundBookWidget] = []

        self._init_ui()
        self.refresh_shelf()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)

        # Toolbar Row
        h_toolbar = QHBoxLayout()
        h_toolbar.setSpacing(10)

        self.edit_search = QLineEdit()
        self.edit_search.setPlaceholderText("🔍 Filter shelf volumes by title or author...")
        self.edit_search.setClearButtonEnabled(True)
        self.edit_search.textChanged.connect(self._filter_books)
        h_toolbar.addWidget(self.edit_search, stretch=1)

        self.btn_add_book = QPushButton("➕ Add Book (EPUB)...")
        self.btn_add_book.setToolTip("Import an EPUB volume to your personal reference library")
        self.btn_add_book.clicked.connect(self._on_add_book_clicked)
        h_toolbar.addWidget(self.btn_add_book)

        self.btn_open_folder = QPushButton("📂 Library Folder")
        self.btn_open_folder.setToolTip("Open local reference books folder in Windows Explorer")
        self.btn_open_folder.clicked.connect(self._open_library_folder)
        h_toolbar.addWidget(self.btn_open_folder)

        self.btn_refresh = QPushButton("🔄 Refresh")
        self.btn_refresh.setToolTip("Rescan books on disk")
        self.btn_refresh.clicked.connect(self.refresh_shelf)
        h_toolbar.addWidget(self.btn_refresh)

        layout.addLayout(h_toolbar)

        # Stats bar
        self.lbl_shelf_stats = QLabel("Loading reference volumes…")
        self.lbl_shelf_stats.setStyleSheet("color: #7aa2f7; font-size: 11px; font-weight: 600;")
        layout.addWidget(self.lbl_shelf_stats)

        # Bookshelf scrollable stage
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setStyleSheet("""
            QScrollArea, QScrollArea > QWidget {
                background-color: #12131a;
                border: none;
            }
        """)

        self.shelf_container = QWidget()
        self.shelf_layout = QVBoxLayout(self.shelf_container)
        self.shelf_layout.setContentsMargins(14, 16, 14, 24)
        self.shelf_layout.setSpacing(24)

        self.scroll_area.setWidget(self.shelf_container)
        layout.addWidget(self.scroll_area, stretch=1)

    def refresh_shelf(self) -> None:
        self.manager.reload_books()
        self._filter_books(self.edit_search.text())

    def _filter_books(self, query: str = "") -> None:
        # Clear existing shelf rows
        while self.shelf_layout.count():
            item = self.shelf_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        books = self.manager.filter_books(query)
        self._book_widgets.clear()

        total_books = len(self.manager.books)
        total_mb = sum(b.file_size_mb for b in self.manager.books)
        if query.strip():
            self.lbl_shelf_stats.setText(f"Showing {len(books)} of {total_books} reference volumes on shelf")
        else:
            self.lbl_shelf_stats.setText(f"{total_books} Reference Volumes on Shelf • {total_mb:.1f} MB Total Knowledge")

        if not books:
            empty_banner = QFrame()
            empty_banner.setStyleSheet("""
                QFrame {
                    background-color: #181a24;
                    border: 1px dashed #30354a;
                    border-radius: 8px;
                    padding: 30px;
                }
            """)
            ev_layout = QVBoxLayout(empty_banner)
            ev_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            ev_layout.setSpacing(10)

            icon_lbl = QLabel("📚")
            icon_lbl.setStyleSheet("font-size: 36px;")
            icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            ev_layout.addWidget(icon_lbl)

            msg_lbl = QLabel(f"No books matched '{query}'" if query else "No reference books found on shelf")
            msg_lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #c0caf5;")
            msg_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            ev_layout.addWidget(msg_lbl)

            self.shelf_layout.addWidget(empty_banner)
            self.shelf_layout.addStretch()
            return

        # Arrange books on shelves (up to 4 or 5 books per shelf row)
        ROW_CAPACITY = 4
        for r_start in range(0, len(books), ROW_CAPACITY):
            row_books = books[r_start:r_start + ROW_CAPACITY]

            shelf_row_widget = QWidget()
            shelf_row_layout = QVBoxLayout(shelf_row_widget)
            shelf_row_layout.setContentsMargins(0, 0, 0, 0)
            shelf_row_layout.setSpacing(0)

            # Books row container
            books_row = QWidget()
            h_books = QHBoxLayout(books_row)
            h_books.setContentsMargins(12, 0, 12, 0)
            h_books.setSpacing(24)

            for b in row_books:
                style = self.manager.get_style_for_book(b)
                book_widget = BoundBookWidget(b, style)
                book_widget.clicked.connect(self.bookSelected.emit)
                h_books.addWidget(book_widget)
                self._book_widgets.append(book_widget)

            h_books.addStretch()
            shelf_row_layout.addWidget(books_row)

            # Physical Wooden Shelf Plank
            plank = QFrame()
            plank.setFixedHeight(16)
            plank.setStyleSheet("""
                QFrame {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #4a2816,
                        stop:0.18 #361c0e,
                        stop:0.85 #241309,
                        stop:1 #140a04);
                    border-top: 2px solid #a66a38;
                    border-bottom: 2px solid #0a0502;
                    border-radius: 2px;
                }
            """)
            shelf_row_layout.addWidget(plank)

            self.shelf_layout.addWidget(shelf_row_widget)

        self.shelf_layout.addStretch()

    def _on_add_book_clicked(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Reference Book (EPUB)",
            "",
            "EPUB eBooks (*.epub);;All Files (*)"
        )
        if file_path and os.path.isfile(file_path):
            added = self.manager.add_book(file_path)
            if added:
                self.refresh_shelf()
                QMessageBox.information(
                    self,
                    "Book Imported",
                    f"Successfully added '{added.title}' to your reference bookshelf!"
                )
            else:
                QMessageBox.warning(
                    self,
                    "Import Failed",
                    "Could not parse the selected EPUB file. Please verify the file is a valid EPUB archive."
                )

    def _open_library_folder(self) -> None:
        QDesktopServices.openUrl(f"file:///{self.manager.user_books_dir.replace(os.sep, '/')}")


class BuiltInEpubReaderView(QWidget):
    """The dedicated full-text reading surface rendering EPUB chapters with inline figures."""

    backToShelfRequested = Signal()
    insertIntoDocumentRequested = Signal(str)

    THEMES = {
        "parchment": {
            "name": "Warm Parchment",
            "bg": "#faf4e8",
            "text": "#292119",
            "link": "#8f4414",
            "panel_bg": "#f0e6d2",
            "border": "#dcd0b8",
        },
        "night": {
            "name": "Velvet Night",
            "bg": "#14161f",
            "text": "#e2e5f2",
            "link": "#7aa2f7",
            "panel_bg": "#1c1e2b",
            "border": "#282c3f",
        },
        "classic": {
            "name": "Crisp White",
            "bg": "#ffffff",
            "text": "#111111",
            "link": "#0055aa",
            "panel_bg": "#f5f5f7",
            "border": "#e0e0e5",
        },
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_book: Optional[EpubBook] = None
        self.current_chapter_index = 0
        self.current_theme = "parchment"
        self.font_family = "Georgia"
        self.font_size_pt = 14

        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 1. Top Navigation & Appearance Header
        self.header_bar = QFrame()
        self.header_bar.setStyleSheet("""
            QFrame {
                background-color: #161822;
                border-bottom: 1px solid #282c3f;
                padding: 6px 12px;
            }
        """)
        h_nav = QHBoxLayout(self.header_bar)
        h_nav.setContentsMargins(8, 4, 8, 4)
        h_nav.setSpacing(10)

        self.btn_back = QPushButton("⬅️ Bookshelf")
        self.btn_back.setStyleSheet("padding: 5px 12px; font-weight: bold; background-color: #24283b; color: #7aa2f7; border: 1px solid #3b4261; border-radius: 5px;")
        self.btn_back.clicked.connect(self.backToShelfRequested.emit)
        h_nav.addWidget(self.btn_back)

        # Book Title & Author Heading
        self.lbl_book_title = QLabel("Book Title")
        self.lbl_book_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #f1f3fa;")
        h_nav.addWidget(self.lbl_book_title)

        h_nav.addStretch()

        # In-Book Full-Text Search Bar
        self.edit_search = QLineEdit()
        self.edit_search.setPlaceholderText("🔍 Find in book...")
        self.edit_search.setFixedWidth(180)
        self.edit_search.returnPressed.connect(self._find_next_in_browser)
        h_nav.addWidget(self.edit_search)

        self.btn_find_prev = QPushButton("▲")
        self.btn_find_prev.setToolTip("Previous match")
        self.btn_find_prev.setFixedWidth(28)
        self.btn_find_prev.clicked.connect(self._find_prev_in_browser)
        h_nav.addWidget(self.btn_find_prev)

        self.btn_find_next = QPushButton("▼")
        self.btn_find_next.setToolTip("Next match")
        self.btn_find_next.setFixedWidth(28)
        self.btn_find_next.clicked.connect(self._find_next_in_browser)
        h_nav.addWidget(self.btn_find_next)

        # Reading Theme Switcher
        self.combo_theme = QComboBox()
        self.combo_theme.addItem("📜 Parchment", "parchment")
        self.combo_theme.addItem("🌙 Night Velvet", "night")
        self.combo_theme.addItem("📄 Crisp White", "classic")
        self.combo_theme.currentIndexChanged.connect(self._on_theme_changed)
        h_nav.addWidget(self.combo_theme)

        # Font Family
        self.combo_font = QComboBox()
        for fam in ("Georgia", "Garamond", "Palatino Linotype", "Segoe UI", "Courier New"):
            self.combo_font.addItem(fam)
        self.combo_font.currentIndexChanged.connect(self._on_font_changed)
        h_nav.addWidget(self.combo_font)

        # Text Zoom A- / A+
        self.btn_zoom_out = QPushButton("A-")
        self.btn_zoom_out.setFixedWidth(30)
        self.btn_zoom_out.clicked.connect(self._zoom_out)
        h_nav.addWidget(self.btn_zoom_out)

        self.btn_zoom_in = QPushButton("A+")
        self.btn_zoom_in.setFixedWidth(30)
        self.btn_zoom_in.clicked.connect(self._zoom_in)
        h_nav.addWidget(self.btn_zoom_in)

        # Insert Excerpt into Manuscript
        self.btn_insert_excerpt = QPushButton("📋 Insert Excerpt into Manuscript")
        self.btn_insert_excerpt.setStyleSheet("background-color: #7aa2f7; color: #101116; font-weight: bold; border-radius: 5px; padding: 5px 14px;")
        self.btn_insert_excerpt.setToolTip("Copy selected passage or current chapter excerpt into your open manuscript")
        self.btn_insert_excerpt.clicked.connect(self._on_insert_excerpt_clicked)
        h_nav.addWidget(self.btn_insert_excerpt)

        layout.addWidget(self.header_bar)

        # 2. Main Two-Pane Splitter: Table of Contents Drawer + Reading Browser
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #282c3f;
                width: 4px;
            }
        """)

        # Left TOC Pane
        toc_container = QWidget()
        toc_container.setMinimumWidth(210)
        toc_layout = QVBoxLayout(toc_container)
        toc_layout.setContentsMargins(8, 8, 8, 8)
        toc_layout.setSpacing(6)

        lbl_toc = QLabel("TABLE OF CONTENTS")
        lbl_toc.setStyleSheet("font-size: 11px; font-weight: 800; color: #7aa2f7; letter-spacing: 1px;")
        toc_layout.addWidget(lbl_toc)

        self.list_toc = QListWidget()
        self.list_toc.setStyleSheet("""
            QListWidget {
                background-color: #181a24;
                border: 1px solid #282c3f;
                border-radius: 6px;
                color: #c0caf5;
                font-size: 12px;
                outline: none;
            }
            QListWidget::item {
                padding: 6px 10px;
                border-radius: 4px;
                margin-bottom: 2px;
            }
            QListWidget::item:hover {
                background-color: #24283b;
                color: #ffffff;
            }
            QListWidget::item:selected {
                background-color: #2e344e;
                border-left: 3px solid #7aa2f7;
                color: #ffffff;
                font-weight: 600;
            }
        """)
        self.list_toc.currentRowChanged.connect(self._on_toc_row_changed)
        toc_layout.addWidget(self.list_toc)

        self.splitter.addWidget(toc_container)

        # Right Reading Browser
        self.browser = QTextBrowser()
        self.browser.setOpenExternalLinks(True)
        self.splitter.addWidget(self.browser)
        self.splitter.setSizes([260, 820])

        layout.addWidget(self.splitter, stretch=1)

        # 3. Bottom Chapter Navigation Bar
        self.footer_bar = QFrame()
        self.footer_bar.setStyleSheet("""
            QFrame {
                background-color: #161822;
                border-top: 1px solid #282c3f;
                padding: 4px 14px;
            }
        """)
        h_footer = QHBoxLayout(self.footer_bar)
        h_footer.setContentsMargins(12, 4, 12, 4)
        h_footer.setSpacing(12)

        self.btn_prev_chapter = QPushButton("⬅️ Previous Chapter")
        self.btn_prev_chapter.clicked.connect(self._prev_chapter)
        h_footer.addWidget(self.btn_prev_chapter)

        self.lbl_progress = QLabel("Chapter 1 of 1")
        self.lbl_progress.setStyleSheet("color: #a2a7c4; font-size: 12px; font-weight: 500;")
        h_footer.addWidget(self.lbl_progress, alignment=Qt.AlignmentFlag.AlignCenter)

        h_footer.addStretch()

        self.btn_next_chapter = QPushButton("Next Chapter ➡️")
        self.btn_next_chapter.clicked.connect(self._next_chapter)
        h_footer.addWidget(self.btn_next_chapter)

        layout.addWidget(self.footer_bar)

    def load_book(self, book: EpubBook, start_chapter: int = 0) -> None:
        """Loads and displays the full EPUB book in the e-reader."""
        self.current_book = book
        self.lbl_book_title.setText(f"{book.title} — {book.author}")

        # Inject all images from archive into the browser document
        EpubParser.inject_images_into_document(book, self.browser.document())

        # Populate Table of Contents
        self.list_toc.blockSignals(True)
        self.list_toc.clear()
        for idx, ch in enumerate(book.chapters):
            item = QListWidgetItem(ch.title)
            item.setToolTip(f"Go to: {ch.title}")
            self.list_toc.addItem(item)
        self.list_toc.blockSignals(False)

        # Load starting chapter
        target_ch = max(0, min(start_chapter, len(book.chapters) - 1)) if book.chapters else 0
        self.set_chapter(target_ch)

    def set_chapter(self, index: int) -> None:
        if not self.current_book or not self.current_book.chapters:
            return

        idx = max(0, min(index, len(self.current_book.chapters) - 1))
        self.current_chapter_index = idx
        chapter = self.current_book.chapters[idx]

        # Update TOC selection
        self.list_toc.blockSignals(True)
        self.list_toc.setCurrentRow(idx)
        self.list_toc.blockSignals(False)

        # Update Footer
        total = len(self.current_book.chapters)
        self.lbl_progress.setText(f"Section {idx + 1} of {total} • {chapter.title}")
        self.btn_prev_chapter.setEnabled(idx > 0)
        self.btn_next_chapter.setEnabled(idx < total - 1)

        # Render HTML
        raw_html = EpubParser.get_chapter_html(self.current_book, chapter)
        self._apply_reader_style(raw_html)

        # Scroll to top
        self.browser.verticalScrollBar().setValue(0)

    def _apply_reader_style(self, content_html: str) -> None:
        t = self.THEMES.get(self.current_theme, self.THEMES["parchment"])
        bg = t["bg"]
        text_col = t["text"]
        link_col = t["link"]

        styled_page = f"""
        <html>
        <head>
        <style>
            body {{
                background-color: {bg};
                color: {text_col};
                font-family: '{self.font_family}', Georgia, serif;
                font-size: {self.font_size_pt}pt;
                line-height: 1.65;
                margin: 28px 48px;
            }}
            a {{
                color: {link_col};
                text-decoration: none;
            }}
            a:hover {{
                text-decoration: underline;
            }}
            h1, h2, h3, h4, h5, h6 {{
                color: {text_col};
                font-family: 'Segoe UI', 'Helvetica Neue', sans-serif;
                margin-top: 1.2em;
                margin-bottom: 0.4em;
            }}
            p {{
                margin-bottom: 0.9em;
                text-indent: 1.4em;
            }}
            p.no-indent, h1 + p, h2 + p, h3 + p {{
                text-indent: 0;
            }}
            blockquote {{
                margin: 1.2em 2.2em;
                font-style: italic;
                opacity: 0.9;
            }}
            img {{
                max-width: 90%;
                height: auto;
                margin: 16px auto;
                display: block;
                border-radius: 4px;
            }}
            hr {{
                border: none;
                border-top: 1px solid {t['border']};
                margin: 24px 0;
            }}
        </style>
        </head>
        <body>
            {content_html}
        </body>
        </html>
        """
        self.browser.setStyleSheet(f"""
            QTextBrowser {{
                background-color: {bg};
                color: {text_col};
                border: none;
                selection-background-color: #3b82f6;
                selection-color: #ffffff;
            }}
        """)
        self.browser.setHtml(styled_page)

    def _on_theme_changed(self) -> None:
        self.current_theme = self.combo_theme.currentData()
        if self.current_book and self.current_book.chapters:
            ch = self.current_book.chapters[self.current_chapter_index]
            html = EpubParser.get_chapter_html(self.current_book, ch)
            self._apply_reader_style(html)

    def _on_font_changed(self) -> None:
        self.font_family = self.combo_font.currentText()
        if self.current_book and self.current_book.chapters:
            ch = self.current_book.chapters[self.current_chapter_index]
            html = EpubParser.get_chapter_html(self.current_book, ch)
            self._apply_reader_style(html)

    def _zoom_in(self) -> None:
        self.font_size_pt = min(28, self.font_size_pt + 1)
        if self.current_book and self.current_book.chapters:
            ch = self.current_book.chapters[self.current_chapter_index]
            html = EpubParser.get_chapter_html(self.current_book, ch)
            self._apply_reader_style(html)

    def _zoom_out(self) -> None:
        self.font_size_pt = max(9, self.font_size_pt - 1)
        if self.current_book and self.current_book.chapters:
            ch = self.current_book.chapters[self.current_chapter_index]
            html = EpubParser.get_chapter_html(self.current_book, ch)
            self._apply_reader_style(html)

    def _on_toc_row_changed(self, row: int) -> None:
        if row >= 0:
            self.set_chapter(row)

    def _prev_chapter(self) -> None:
        if self.current_chapter_index > 0:
            self.set_chapter(self.current_chapter_index - 1)

    def _next_chapter(self) -> None:
        if self.current_book and self.current_chapter_index < len(self.current_book.chapters) - 1:
            self.set_chapter(self.current_chapter_index + 1)

    def _find_next_in_browser(self) -> None:
        q = self.edit_search.text().strip()
        if q:
            found = self.browser.find(q)
            if not found:
                # Wrap search to beginning
                self.browser.moveCursor(QTextCursor.MoveOperation.Start)
                self.browser.find(q)

    def _find_prev_in_browser(self) -> None:
        q = self.edit_search.text().strip()
        if q:
            self.browser.find(q, QTextDocument.FindFlag.FindBackward)

    def _on_insert_excerpt_clicked(self) -> None:
        """Copies highlighted text or whole chapter summary into the active manuscript."""
        selected_text = self.browser.textCursor().selectedText()
        if not selected_text.strip():
            # If no text selected, take first 400 chars of visible section
            plain = self.browser.toPlainText()
            selected_text = plain[:400].strip() + ("…" if len(plain) > 400 else "")

        if selected_text.strip():
            # Format with attribution
            book_title = self.current_book.title if self.current_book else "Reference Book"
            author = f" ({self.current_book.author})" if self.current_book and self.current_book.author else ""
            formatted_quote = f"\n\n> \"{selected_text.strip()}\"\n> — *{book_title}*{author}\n\n"
            self.insertIntoDocumentRequested.emit(formatted_quote)
            self.btn_insert_excerpt.setText("✓ Excerpt Inserted!")
            QTimer.singleShot(2500, lambda: self.btn_insert_excerpt.setText("📋 Insert Excerpt into Manuscript"))
