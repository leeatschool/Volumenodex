"""Modern Fluent Paginated Document Canvas with discrete paper sheets and print fidelity."""

import os
import re
import math
from typing import Optional, List, Any, Tuple
from PySide6.QtCore import Qt, Signal, QRectF, QRect, QPointF, QPoint, QTimer, QSize, QSizeF, QUrl
from PySide6.QtGui import (
    QPainter, QColor, QPen, QBrush, QFont, QTextCursor, QTextDocument,
    QAbstractTextDocumentLayout, QTextCharFormat, QTextBlockFormat,
    QTextListFormat, QKeySequence, QLinearGradient, QRadialGradient,
    QPainterPath, QClipboard, QGuiApplication, QImage, QTextImageFormat, QPixmap, QIcon,
    QTextTableFormat, QTextTable, QTextLength, QPalette
)
from PySide6.QtWidgets import (
    QAbstractScrollArea, QScrollBar, QApplication, QMenu
)

from volumenodex.core.document_model import PageLayoutModel, DPI_SCREEN, PageMargins
from volumenodex.canvas.paper_texture import PaperTextureEngine, TextureType
from volumenodex.core.theme_manager import ThemeManager
from volumenodex.core.header_footer_model import HeaderFooterModel, PageHeaderFooterConfig
from volumenodex.core.note_model import NoteManager, Footnote
from volumenodex.review.lens_engine import LensFinding


class PaginatedCanvas(QAbstractScrollArea):
    """Luxury discrete multi-page canvas with photorealistic paper sheets, drop shadows, and typography."""

    textChanged = Signal()
    cursorPositionChanged = Signal()
    keystrokeHappened = Signal(bool, bool)  # is_return, is_space
    pageOffsetChanged = Signal(int)
    addToDictionaryRequested = Signal(str)
    ignoreWordRequested = Signal(str)
    zoomRequested = Signal(float)
    headerFooterEditRequested = Signal(int)

    def __init__(
        self,
        layout_model: PageLayoutModel,
        texture_engine: PaperTextureEngine,
        theme_manager: ThemeManager,
        parent=None,
    ):
        super().__init__(parent)
        self.layout_model = layout_model
        self.texture_engine = texture_engine
        self.theme_manager = theme_manager

        self._dark_paper = False
        self.show_margin_guides = True
        self.show_crop_marks = True
        self.typewriter_scrolling = False
        self.header_footer_model = HeaderFooterModel()
        self.note_manager = NoteManager()
        self.story_title = ""
        self.story_author = ""

        # Document Engine
        self._doc = QTextDocument(self)
        self._doc.setUndoRedoEnabled(True)
        self._doc.setDefaultStyleSheet("body { color: #000000; }")

        # Sublime default typography
        default_font = QFont("Georgia", 12)
        default_font.setStyleHint(QFont.StyleHint.Serif)
        self._doc.setDefaultFont(default_font)

        self._cursor = QTextCursor(self._doc)
        self._apply_default_text_format()
        self._cursor_visible = True
        self._is_mouse_selecting = False
        self._lens_findings = []
        self._lens_selections = []
        self._lens_selections_with_range = []
        self.spell_engine = None

        # Search and Replace matches state
        self._search_matches = []
        self._current_search_match_index = -1
        self._search_selections_with_range = []

        # Drop shadow caching
        self._cached_shadow: Optional[QPixmap] = None
        self._cached_shadow_size: Optional[tuple] = None

        # Floating Find & Replace HUD
        from volumenodex.ui.find_replace_bar import FindReplaceBar
        self.find_replace_bar = FindReplaceBar(self, self.viewport())
        self.find_replace_bar.hide()

        # Blinking Cursor Timer (500ms)
        self._blink_timer = QTimer(self)
        self._blink_timer.setInterval(500)
        self._blink_timer.timeout.connect(self._toggle_cursor_blink)
        self._blink_timer.start()

        # Connect document changes to canvas updates
        self._doc.contentsChanged.connect(self._on_doc_contents_changed)

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.viewport().setCursor(Qt.CursorShape.IBeamCursor)
        self.sync_document_geometry()

    def document(self) -> QTextDocument:
        return self._doc

    @property
    def dark_paper(self) -> bool:
        return getattr(self, "_dark_paper", False)

    @dark_paper.setter
    def dark_paper(self, value: bool) -> None:
        self._dark_paper = bool(value)
        css_color = "#ffffff" if self._dark_paper else "#000000"
        self._doc.setDefaultStyleSheet(f"body {{ color: {css_color}; }}")
        self._apply_default_text_format()
        self.viewport().update()

    def _apply_default_text_format(self) -> None:
        default_color = QColor("#ffffff" if self.dark_paper else "#000000")
        fmt = self._cursor.charFormat()
        fmt.setForeground(default_color)
        self._cursor.setCharFormat(fmt)

    def set_document(self, doc: QTextDocument) -> None:
        """Shares or binds an existing QTextDocument to this canvas."""
        try:
            self._doc.contentsChanged.disconnect(self._on_doc_contents_changed)
        except Exception:
            pass
        self._doc = doc
        css_color = "#ffffff" if self.dark_paper else "#000000"
        self._doc.setDefaultStyleSheet(f"body {{ color: {css_color}; }}")
        self._cursor = QTextCursor(self._doc)
        self._apply_default_text_format()
        self._doc.contentsChanged.connect(self._on_doc_contents_changed)
        self.sync_document_geometry()
        self._update_scroll_bars()
        self.viewport().update()

    @property
    def cursor(self) -> QTextCursor:
        return self._cursor

    def sync_document_geometry(self) -> None:
        """Configures the document page size to match the printable area."""
        self._cached_shadow = None
        self._cached_shadow_size = None
        pw_print = self.layout_model.printable_width_px
        ph_print = self.layout_model.printable_height_px
        self._doc.setPageSize(QSizeF(pw_print, ph_print))
        self._update_scroll_bars()
        self.viewport().update()

    def _on_doc_contents_changed(self) -> None:
        self._update_scroll_bars()
        self.textChanged.emit()
        self.viewport().update()

    def _cursor_page_index(self) -> int:
        block = self._doc.findBlock(self._cursor.position())
        if not block.isValid():
            return 0
        doc_y = self._doc.documentLayout().blockBoundingRect(block).top()
        ph_print = self.layout_model.printable_height_px
        return max(0, int(doc_y // ph_print)) if ph_print > 0 else 0

    def _toggle_cursor_blink(self) -> None:
        if self.hasFocus():
            self._cursor_visible = not self._cursor_visible
            p_idx = self._cursor_page_index()
            page_rect = self._get_page_rect(p_idx)
            sx = self.horizontalScrollBar().value()
            sy = self.verticalScrollBar().value()
            dirty_rect = QRect(
                int(page_rect.x() - sx - 4),
                int(page_rect.y() - sy - 4),
                int(page_rect.width() + 8),
                int(page_rect.height() + 8)
            )
            self.viewport().update(dirty_rect)

    def _reset_cursor_blink(self) -> None:
        self._cursor_visible = True
        self._blink_timer.start(500)
        if getattr(self, "typewriter_scrolling", False):
            self._apply_typewriter_scrolling()
        self.viewport().update()

    def _get_page_rect(self, page_index: int) -> QRectF:
        vw = self.viewport().width()
        pw = self.layout_model.page_width_px
        ph = self.layout_model.page_height_px
        px = max(32, (vw - pw) // 2)
        gutter = 36
        top_padding = 36
        py = top_padding + page_index * (ph + gutter)
        return QRectF(px, py, pw, ph)

    def _get_printable_rect(self, page_index: int) -> QRectF:
        page_rect = self._get_page_rect(page_index)
        mx = self.layout_model.margin_left_px
        my = self.layout_model.margin_top_px
        pw_print = self.layout_model.printable_width_px
        ph_print = self.layout_model.printable_height_px
        return QRectF(page_rect.x() + mx, page_rect.y() + my, pw_print, ph_print)

    def _total_pages(self) -> int:
        return max(1, self._doc.pageCount())

    def _update_scroll_bars(self) -> None:
        total_p = self._total_pages()
        ph = self.layout_model.page_height_px
        gutter = 36
        total_h = 36 + total_p * (ph + gutter) + 48

        self.verticalScrollBar().setRange(0, max(0, total_h - self.viewport().height()))
        self.verticalScrollBar().setPageStep(self.viewport().height())

        pw = self.layout_model.page_width_px
        total_w = pw + 80
        self.horizontalScrollBar().setRange(0, max(0, total_w - self.viewport().width()))
        self.horizontalScrollBar().setPageStep(self.viewport().width())

        # Notify ruler of current horizontal offset
        vw = self.viewport().width()
        page_x = max(32, (vw - pw) // 2) - self.horizontalScrollBar().value()
        self.pageOffsetChanged.emit(int(page_x))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.sync_document_geometry()
        if hasattr(self, "find_replace_bar") and self.find_replace_bar:
            self._reposition_find_bar()

    def scrollContentsBy(self, dx: int, dy: int):
        super().scrollContentsBy(dx, dy)
        vw = self.viewport().width()
        pw = self.layout_model.page_width_px
        page_x = max(32, (vw - pw) // 2) - self.horizontalScrollBar().value()
        self.pageOffsetChanged.emit(int(page_x))
        if hasattr(self, "find_replace_bar") and self.find_replace_bar:
            self._reposition_find_bar()
        self.viewport().update()

    # --- Painting Engine: Photorealistic Sheets, Grain, and Typography ---
    def paintEvent(self, event):
        painter = QPainter(self.viewport())
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        vw = self.viewport().width()
        vh = self.viewport().height()
        sx = self.horizontalScrollBar().value()
        sy = self.verticalScrollBar().value()

        # 1. Velvety Studio Desk Background
        desk_color = QColor(self.theme_manager.current.bg_app)
        painter.fillRect(0, 0, vw, vh, desk_color)

        total_pages = self._total_pages()
        ph_print = self.layout_model.printable_height_px
        pw_print = self.layout_model.printable_width_px

        texture_pixmap = self.texture_engine.get_texture_pixmap()

        top_padding = 36
        gutter = 36
        ph = self.layout_model.page_height_px
        page_stride = ph + gutter

        # Direct O(1) page range calculation: only iterate over visible pages
        start_page = max(0, int((sy - top_padding - ph) // page_stride))
        end_page = min(total_pages, int((sy + vh - top_padding) // page_stride) + 2)

        for p in range(start_page, end_page):
            page_rect = self._get_page_rect(p)
            # Adjust for scrolling
            screen_page_rect = QRectF(page_rect.x() - sx, page_rect.y() - sy, page_rect.width(), page_rect.height())

            # Skip pages outside viewport
            if screen_page_rect.bottom() < 0 or screen_page_rect.top() > vh:
                continue

            # 2. Photorealistic Multi-Layer Drop Shadow (Hardware-Accelerated Blit)
            self._draw_luxury_page_shadow(painter, screen_page_rect)

            # 3. Physical Paper Surface Fill
            paper_bg = QColor(self.theme_manager.current.page_bg_dark if self.dark_paper else self.theme_manager.current.page_bg_light)
            painter.fillRect(screen_page_rect, paper_bg)

            # 4. Subtle 1px Paper Rim Highlight
            rim_color = QColor(255, 255, 255, 18) if self.dark_paper else QColor(0, 0, 0, 22)
            painter.setPen(QPen(rim_color, 1))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(screen_page_rect)

            # 5. Procedural Paper Grain Overlay
            if texture_pixmap and self.texture_engine.opacity > 0.001:
                painter.save()
                painter.setOpacity(self.texture_engine.opacity)
                painter.drawTiledPixmap(screen_page_rect, texture_pixmap)
                painter.restore()

            # 6. Prepress Corner Crop Marks
            if self.show_crop_marks:
                self._draw_crop_marks(painter, screen_page_rect)

            # 7. Running Page Header & Footer
            self._draw_page_header(painter, screen_page_rect, p + 1, total_pages)
            self._draw_page_footer(painter, screen_page_rect, p + 1, total_pages)
            self._draw_page_footnotes(painter, screen_page_rect, p + 1)

            # 8. Sliced Text Content & Selection
            print_rect = self._get_printable_rect(p)
            screen_print_rect = QRectF(print_rect.x() - sx, print_rect.y() - sy, print_rect.width(), print_rect.height())

            painter.save()
            painter.setClipRect(screen_print_rect)
            painter.translate(screen_print_rect.x(), screen_print_rect.y() - p * ph_print)

            # Draw document slice with cursor and selection
            ctx = QAbstractTextDocumentLayout.PaintContext()
            default_text_color = QColor("#ffffff" if self.dark_paper else "#000000")
            ctx.palette.setColor(QPalette.ColorRole.Text, default_text_color)
            ctx.cursorPosition = self._cursor.position() if (self._cursor_visible and self.hasFocus()) else -1
            # CRITICAL OPTIMIZATION: Tell Qt to cull all blocks outside this page slice in document coordinates!
            ctx.clip = QRectF(0, p * ph_print, pw_print, ph_print)

            # Spatial selection culling: only pass selections that intersect page p
            page_selections = []
            doc_layout = self._doc.documentLayout()
            p_top_y = p * ph_print
            p_bot_y = (p + 1) * ph_print
            p_start_pos = max(0, doc_layout.hitTest(QPointF(0, p_top_y), Qt.HitTestAccuracy.FuzzyHit))
            p_end_pos = doc_layout.hitTest(QPointF(pw_print, p_bot_y), Qt.HitTestAccuracy.FuzzyHit)
            if p_end_pos < p_start_pos:
                p_end_pos = self._doc.characterCount()

            if hasattr(self, "_lens_selections_with_range") and self._lens_selections_with_range:
                for f_start, f_end, sel in self._lens_selections_with_range:
                    if not (f_end < p_start_pos or f_start > p_end_pos):
                        page_selections.append(sel)
            elif hasattr(self, "_lens_selections") and self._lens_selections:
                page_selections.extend(self._lens_selections)

            if hasattr(self, "_search_selections_with_range") and self._search_selections_with_range:
                for s_start, s_end, sel in self._search_selections_with_range:
                    if not (s_end < p_start_pos or s_start > p_end_pos):
                        page_selections.append(sel)

            if self._cursor.hasSelection():
                c_start = self._cursor.selectionStart()
                c_end = self._cursor.selectionEnd()
                if not (c_end < p_start_pos or c_start > p_end_pos):
                    sel = QAbstractTextDocumentLayout.Selection()
                    sel.cursor = self._cursor
                    sel.format.setBackground(QColor(59, 130, 246, 90))
                    page_selections.append(sel)

            ctx.selections = page_selections

            self._doc.documentLayout().draw(painter, ctx)
            painter.restore()

    def _get_cached_shadow(self, pw: int, ph: int) -> QPixmap:
        """Pre-renders luxury ambient occlusion and drop shadow into a cached QPixmap."""
        if (
            self._cached_shadow is not None
            and self._cached_shadow_size == (pw, ph)
        ):
            return self._cached_shadow

        pad = 24
        pad_bot = 32
        pix_w = pw + pad * 2
        pix_h = ph + pad + pad_bot
        pixmap = QPixmap(pix_w, pix_h)
        pixmap.fill(Qt.GlobalColor.transparent)

        p = QPainter(pixmap)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        base_rect = QRectF(pad, pad, pw, ph)

        # Stage 1: Soft Ambient Halo
        for i in range(1, 6):
            alpha = int(22 / i)
            p.setPen(QPen(QColor(0, 0, 0, alpha), 3))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(base_rect.adjusted(-i * 2.5, -i * 1.5, i * 2.5, i * 3.5), 3, 3)

        # Stage 2: Crisp directional bottom shadow
        bottom_rect = QRectF(base_rect.x() + 4, base_rect.bottom() - 2, base_rect.width() - 8, 8)
        grad = QLinearGradient(bottom_rect.topLeft(), bottom_rect.bottomLeft())
        grad.setColorAt(0.0, QColor(0, 0, 0, 75))
        grad.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.fillRect(bottom_rect, grad)
        p.end()

        self._cached_shadow = pixmap
        self._cached_shadow_size = (pw, ph)
        return pixmap

    def _draw_luxury_page_shadow(self, p: QPainter, rect: QRectF) -> None:
        """Renders realistic multi-stage paper drop shadow via high-speed cached pixmap blit."""
        pw = int(rect.width())
        ph = int(rect.height())
        shadow_pixmap = self._get_cached_shadow(pw, ph)
        pad = 24
        p.drawPixmap(int(rect.x() - pad), int(rect.y() - pad), shadow_pixmap)

    def _draw_crop_marks(self, p: QPainter, rect: QRectF) -> None:
        """Draws subtle 6px publisher corner crop marks at margin boundaries."""
        mx = self.layout_model.margin_left_px
        my = self.layout_model.margin_top_px
        p_pen = QPen(QColor(130, 140, 170, 45), 1)
        p.setPen(p_pen)

        # Top-Left Margin Corner
        p.drawLine(rect.x() + mx - 6, rect.y() + my, rect.x() + mx, rect.y() + my)
        p.drawLine(rect.x() + mx, rect.y() + my - 6, rect.x() + mx, rect.y() + my)

        # Top-Right Margin Corner
        p.drawLine(rect.right() - mx, rect.y() + my, rect.right() - mx + 6, rect.y() + my)
        p.drawLine(rect.right() - mx, rect.y() + my - 6, rect.right() - mx, rect.y() + my)

        # Bottom-Left Margin Corner
        p.drawLine(rect.x() + mx - 6, rect.bottom() - my, rect.x() + mx, rect.bottom() - my)
        p.drawLine(rect.x() + mx, rect.bottom() - my, rect.x() + mx, rect.bottom() - my + 6)

        # Bottom-Right Margin Corner
        p.drawLine(rect.right() - mx, rect.bottom() - my, rect.right() - mx + 6, rect.bottom() - my)
        p.drawLine(rect.right() - mx, rect.bottom() - my, rect.right() - mx, rect.bottom() - my + 6)

    def _draw_page_header(self, p: QPainter, rect: QRectF, page_num: int, total_pages: int) -> None:
        cfg = self.header_footer_model.get_config_for_page(page_num)
        if cfg.suppressed:
            return
        if not (cfg.header_left or cfg.header_center or cfg.header_right):
            return

        p.save()
        font = QFont("Georgia", 8)
        font.setStyleHint(QFont.StyleHint.Serif)
        p.setFont(font)
        col = QColor(140, 145, 165, 140) if not self.dark_paper else QColor(160, 165, 185, 120)
        p.setPen(col)

        mx = self.layout_model.margin_left_px
        header_y = rect.top() + int(self.layout_model.margin_top_px * 0.45)
        hdr_rect = QRectF(rect.x() + mx, header_y - 10, rect.width() - (2 * mx), 20)

        left_text = self.header_footer_model.expand_tokens(cfg.header_left, page_num, total_pages, self.story_title, self.story_author)
        center_text = self.header_footer_model.expand_tokens(cfg.header_center, page_num, total_pages, self.story_title, self.story_author)
        right_text = self.header_footer_model.expand_tokens(cfg.header_right, page_num, total_pages, self.story_title, self.story_author)

        if left_text:
            p.drawText(hdr_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, left_text)
        if center_text:
            p.drawText(hdr_rect, Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter, center_text)
        if right_text:
            p.drawText(hdr_rect, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, right_text)

        p.restore()

    def _draw_page_footer(self, p: QPainter, rect: QRectF, page_num: int, total_pages: int = 1) -> None:
        cfg = self.header_footer_model.get_config_for_page(page_num)
        if cfg.suppressed:
            return

        p.save()
        font = QFont("Georgia", 9)
        font.setStyleHint(QFont.StyleHint.Serif)
        p.setFont(font)
        footer_col = QColor(140, 145, 165, 140) if not self.dark_paper else QColor(160, 165, 185, 120)
        p.setPen(footer_col)

        mx = self.layout_model.margin_left_px
        footer_y = rect.bottom() - int(self.layout_model.margin_bottom_px * 0.45)
        ftr_rect = QRectF(rect.x() + mx, footer_y - 10, rect.width() - (2 * mx), 20)

        left_text = self.header_footer_model.expand_tokens(cfg.footer_left, page_num, total_pages, self.story_title, self.story_author)
        center_text = self.header_footer_model.expand_tokens(cfg.footer_center, page_num, total_pages, self.story_title, self.story_author)
        right_text = self.header_footer_model.expand_tokens(cfg.footer_right, page_num, total_pages, self.story_title, self.story_author)

        if left_text:
            p.drawText(ftr_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, left_text)
        if center_text:
            p.drawText(ftr_rect, Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter, center_text)
        if right_text:
            p.drawText(ftr_rect, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, right_text)

        p.restore()

    def _draw_page_footnotes(self, p: QPainter, rect: QRectF, page_num: int) -> None:
        if not hasattr(self, "note_manager") or not self.note_manager:
            return
        notes = self.note_manager.get_footnotes_for_page(page_num)
        if not notes:
            return

        p.save()
        mx = self.layout_model.margin_left_px
        my = self.layout_model.margin_bottom_px
        pw_print = self.layout_model.printable_width_px

        start_y = rect.bottom() - my + 6
        p.setPen(QPen(QColor(130, 140, 170, 80), 1))
        p.drawLine(int(rect.x() + mx), int(start_y), int(rect.x() + mx + 60), int(start_y))

        fn_font = QFont("Georgia", 8)
        p.setFont(fn_font)
        fn_color = QColor(120, 125, 145) if not self.dark_paper else QColor(170, 175, 195)
        p.setPen(fn_color)

        cur_y = start_y + 4
        for fn in notes[:3]:
            fn_text = f"{fn.marker}. {fn.text}"
            p.drawText(QRectF(rect.x() + mx, cur_y, pw_print, 14), Qt.AlignmentFlag.AlignLeft, fn_text)
            cur_y += 14

        p.restore()

    # --- Mouse Interaction & Hit-Testing Across Discrete Sheets ---
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            pos = self._screen_point_to_doc_position(event.position())
            if pos is not None:
                move_mode = QTextCursor.MoveMode.KeepAnchor if (event.modifiers() & Qt.KeyboardModifier.ShiftModifier) else QTextCursor.MoveMode.MoveAnchor
                self._cursor.setPosition(pos, move_mode)
                self._is_mouse_selecting = True
                self._reset_cursor_blink()
                self.cursorPositionChanged.emit()
                self.viewport().update()

    def mouseMoveEvent(self, event):
        if self._is_mouse_selecting:
            pos = self._screen_point_to_doc_position(event.position())
            if pos is not None:
                self._cursor.setPosition(pos, QTextCursor.MoveMode.KeepAnchor)
                self.cursorPositionChanged.emit()
                self.viewport().update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_mouse_selecting = False

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            pt = event.position() if hasattr(event, "position") else event.pos()
            # Check if double-clicked in header or footer margin
            sx = self.horizontalScrollBar().value()
            sy = self.verticalScrollBar().value()
            click_y = pt.y() + sy
            top_padding = 36
            gutter = 36
            ph = self.layout_model.page_height_px
            page_stride = ph + gutter
            target_page = max(0, min(self._total_pages() - 1, int((click_y - top_padding) // page_stride)))
            print_rect = self._get_printable_rect(target_page)
            page_rect = self._get_page_rect(target_page)

            if page_rect.contains(pt.x() + sx, click_y):
                if click_y < print_rect.top() or click_y > print_rect.bottom():
                    self.headerFooterEditRequested.emit(target_page + 1)
                    return

            pos = self._screen_point_to_doc_position(pt)
            if pos is not None:
                self._cursor.setPosition(pos)
                self._cursor.select(QTextCursor.SelectionType.WordUnderCursor)
                self._reset_cursor_blink()
                self.cursorPositionChanged.emit()
                self.viewport().update()

    def wheelEvent(self, event):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            step = 0.05 if delta > 0 else -0.05
            new_zoom = max(0.25, min(3.0, round(self.layout_model.zoom + step, 2)))
            if new_zoom != self.layout_model.zoom:
                self.zoomRequested.emit(new_zoom)
            event.accept()
        else:
            super().wheelEvent(event)

    def _screen_point_to_doc_position(self, screen_pt: QPointF) -> Optional[int]:
        sx = self.horizontalScrollBar().value()
        sy = self.verticalScrollBar().value()
        click_x = screen_pt.x() + sx
        click_y = screen_pt.y() + sy

        total_pages = self._total_pages()
        ph_print = self.layout_model.printable_height_px
        pw_print = self.layout_model.printable_width_px

        top_padding = 36
        gutter = 36
        ph = self.layout_model.page_height_px
        page_stride = ph + gutter
        target_page = max(0, min(total_pages - 1, int((click_y - top_padding) // page_stride)))

        print_rect = self._get_printable_rect(target_page)
        doc_x = max(0.0, min(float(pw_print), click_x - print_rect.x()))
        doc_y = target_page * ph_print + max(0.0, min(float(ph_print), click_y - print_rect.y()))

        pos = self._doc.documentLayout().hitTest(QPointF(doc_x, doc_y), Qt.HitTestAccuracy.FuzzyHit)
        return pos if pos >= 0 else 0

    # --- Keyboard Input, Navigation, and Shortcuts ---
    def keyPressEvent(self, event):
        key = event.key()
        modifiers = event.modifiers()
        is_ctrl = bool(modifiers & Qt.KeyboardModifier.ControlModifier)
        is_shift = bool(modifiers & Qt.KeyboardModifier.ShiftModifier)
        move_mode = QTextCursor.MoveMode.KeepAnchor if is_shift else QTextCursor.MoveMode.MoveAnchor

        # 1. Navigation
        if key == Qt.Key.Key_Left:
            op = QTextCursor.MoveOperation.PreviousWord if is_ctrl else QTextCursor.MoveOperation.Left
            self._cursor.movePosition(op, move_mode)
        elif key == Qt.Key.Key_Right:
            op = QTextCursor.MoveOperation.NextWord if is_ctrl else QTextCursor.MoveOperation.Right
            self._cursor.movePosition(op, move_mode)
        elif key == Qt.Key.Key_Up:
            self._cursor.movePosition(QTextCursor.MoveOperation.Up, move_mode)
        elif key == Qt.Key.Key_Down:
            self._cursor.movePosition(QTextCursor.MoveOperation.Down, move_mode)
        elif key == Qt.Key.Key_Home:
            op = QTextCursor.MoveOperation.Start if is_ctrl else QTextCursor.MoveOperation.StartOfLine
            self._cursor.movePosition(op, move_mode)
        elif key == Qt.Key.Key_End:
            op = QTextCursor.MoveOperation.End if is_ctrl else QTextCursor.MoveOperation.EndOfLine
            self._cursor.movePosition(op, move_mode)

        # 2. Editing & Deletion
        elif key == Qt.Key.Key_Backspace:
            if not self._cursor.hasSelection() and self._cursor.block().textList() is not None:
                block = self._cursor.block()
                if not block.text().strip():
                    lst = block.textList()
                    lst.remove(block)
                    bf = QTextBlockFormat()
                    self._cursor.setBlockFormat(bf)
                    self.keystrokeHappened.emit(False, False)
                    self._reset_cursor_blink()
                    self.cursorPositionChanged.emit()
                    self.viewport().update()
                    return
            if self._cursor.hasSelection():
                self._cursor.removeSelectedText()
            else:
                self._cursor.deletePreviousChar()
            self.keystrokeHappened.emit(False, False)
        elif key == Qt.Key.Key_Delete:
            if self._cursor.hasSelection():
                self._cursor.removeSelectedText()
            else:
                self._cursor.deleteChar()
            self.keystrokeHappened.emit(False, False)
        elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if not is_ctrl and self._cursor.block().textList() is not None:
                block = self._cursor.block()
                if not block.text().strip():
                    lst = block.textList()
                    lst.remove(block)
                    bf = QTextBlockFormat()
                    self._cursor.setBlockFormat(bf)
                    self.keystrokeHappened.emit(True, False)
                    self._reset_cursor_blink()
                    self.cursorPositionChanged.emit()
                    self.viewport().update()
                    return
            if is_ctrl:
                # Page Break
                bf = QTextBlockFormat()
                bf.setPageBreakPolicy(QTextBlockFormat.PageBreakFlag.PageBreak_AlwaysBefore)
                self._cursor.insertBlock(bf)
            else:
                self._cursor.insertBlock()
            self.keystrokeHappened.emit(True, False)

        # 3. Standard Shortcuts (Ctrl+Z, Ctrl+Y, Ctrl+C, Ctrl+V, Ctrl+X, Ctrl+A, Ctrl+B, Ctrl+I, Ctrl+U)
        elif is_ctrl and key == Qt.Key.Key_Z:
            if is_shift:
                self._doc.redo()
            else:
                self._doc.undo()
        elif is_ctrl and key == Qt.Key.Key_Y:
            self._doc.redo()
        elif is_ctrl and key == Qt.Key.Key_A:
            self._cursor.select(QTextCursor.SelectionType.Document)
        elif is_ctrl and key == Qt.Key.Key_C:
            if self._cursor.hasSelection():
                QApplication.clipboard().setText(self._cursor.selectedText())
        elif is_ctrl and key == Qt.Key.Key_X:
            if self._cursor.hasSelection():
                QApplication.clipboard().setText(self._cursor.selectedText())
                self._cursor.removeSelectedText()
        elif is_ctrl and key == Qt.Key.Key_V:
            clip_text = QApplication.clipboard().text()
            if clip_text:
                self._cursor.insertText(clip_text)
        elif is_ctrl and key == Qt.Key.Key_B:
            fmt = QTextCharFormat()
            fmt.setFontWeight(QFont.Weight.Normal if self._cursor.charFormat().fontWeight() >= 700 else QFont.Weight.Bold)
            self._cursor.mergeCharFormat(fmt)
        elif is_ctrl and key == Qt.Key.Key_I:
            fmt = QTextCharFormat()
            fmt.setFontItalic(not self._cursor.charFormat().fontItalic())
            self._cursor.mergeCharFormat(fmt)
        elif is_ctrl and key == Qt.Key.Key_U:
            fmt = QTextCharFormat()
            fmt.setFontUnderline(not self._cursor.charFormat().fontUnderline())
            self._cursor.mergeCharFormat(fmt)
        elif is_ctrl and key == Qt.Key.Key_F:
            self.show_find(replace_mode=False)
        elif is_ctrl and key == Qt.Key.Key_H:
            self.show_find(replace_mode=True)
        elif key == Qt.Key.Key_F3:
            if hasattr(self, "find_replace_bar") and self.find_replace_bar.isVisible():
                if is_shift:
                    self.find_replace_bar.find_prev()
                else:
                    self.find_replace_bar.find_next()
            else:
                self.show_find(replace_mode=False)

        # Tab / Backtab Indentation & Table Navigation
        elif key in (Qt.Key.Key_Tab, Qt.Key.Key_Backtab):
            if is_shift or key == Qt.Key.Key_Backtab:
                self.decrease_indent()
            else:
                table = self._cursor.currentTable()
                if table:
                    self._cursor.movePosition(QTextCursor.MoveOperation.NextCell)
                elif self._cursor.hasSelection() or self._cursor.atBlockStart():
                    self.increase_indent()
                else:
                    self._cursor.insertText("    ")
            self.keystrokeHappened.emit(False, False)

        # 4. Text Input
        elif event.text() and not is_ctrl:
            typed_char = event.text()
            if typed_char == " " and self._cursor.block().textList() is not None and not self._cursor.block().text():
                self._reset_cursor_blink()
                self.viewport().update()
                return

            # Ensure default text color matches paper mode (black on light paper, white on dark paper)
            cf = self._cursor.charFormat()
            target_color = QColor("#ffffff" if self.dark_paper else "#000000")
            old_default = QColor("#000000" if self.dark_paper else "#ffffff")
            if (
                cf.foreground().style() == Qt.BrushStyle.NoBrush
                or not cf.foreground().color().isValid()
                or cf.foreground().color() == old_default
            ):
                cf.setForeground(target_color)
                self._cursor.setCharFormat(cf)

            self._cursor.insertText(typed_char)
            is_space = typed_char == " "

            # Auto-numbered list check: triggered after entering a number followed by a period at start of line
            if (typed_char == "." or is_space) and self._cursor.block().textList() is None:
                self._check_auto_numbered_list()

            self.keystrokeHappened.emit(False, is_space)
        else:
            super().keyPressEvent(event)
            return

        self._reset_cursor_blink()
        self.cursorPositionChanged.emit()
        self.viewport().update()

    def wheelEvent(self, event):
        # Ctrl + Wheel = Smooth Zoom
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            cur_zoom = self.layout_model.zoom
            new_zoom = max(0.5, min(2.0, cur_zoom + (0.1 if delta > 0 else -0.1)))
            self.layout_model.zoom = new_zoom
            self.sync_document_geometry()
            event.accept()
        else:
            super().wheelEvent(event)

    # --- Rich Formatting Helpers for Ribbon ---
    def set_font_family(self, family: str) -> None:
        fmt = QTextCharFormat()
        fmt.setFontFamilies([family])
        self._cursor.mergeCharFormat(fmt)
        self.viewport().update()

    def set_font_size(self, pt_size: int) -> None:
        fmt = QTextCharFormat()
        fmt.setFontPointSize(pt_size)
        self._cursor.mergeCharFormat(fmt)
        self.viewport().update()

    def toggle_bold(self) -> None:
        fmt = QTextCharFormat()
        is_bold = self._cursor.charFormat().fontWeight() >= 700
        fmt.setFontWeight(QFont.Weight.Normal if is_bold else QFont.Weight.Bold)
        self._cursor.mergeCharFormat(fmt)
        self.viewport().update()

    def toggle_italic(self) -> None:
        fmt = QTextCharFormat()
        fmt.setFontItalic(not self._cursor.charFormat().fontItalic())
        self._cursor.mergeCharFormat(fmt)
        self.viewport().update()

    def toggle_underline(self) -> None:
        fmt = QTextCharFormat()
        fmt.setFontUnderline(not self._cursor.charFormat().fontUnderline())
        self._cursor.mergeCharFormat(fmt)
        self.viewport().update()

    def toggle_strike(self) -> None:
        fmt = QTextCharFormat()
        fmt.setFontStrikeOut(not self._cursor.charFormat().fontStrikeOut())
        self._cursor.mergeCharFormat(fmt)
        self.viewport().update()

    def set_text_color(self, color: QColor) -> None:
        fmt = QTextCharFormat()
        fmt.setForeground(color)
        self._cursor.mergeCharFormat(fmt)
        self.viewport().update()

    def set_highlight_color(self, color: QColor) -> None:
        fmt = QTextCharFormat()
        fmt.setBackground(color)
        self._cursor.mergeCharFormat(fmt)
        self.viewport().update()

    def clear_highlight(self) -> None:
        """Removes background highlight color from current selection or cursor position."""
        fmt = QTextCharFormat()
        fmt.setBackground(QBrush(Qt.BrushStyle.NoBrush))
        self._cursor.mergeCharFormat(fmt)
        self.viewport().update()

    def set_alignment(self, align: Qt.AlignmentFlag) -> None:
        bf = self._cursor.blockFormat()
        bf.setAlignment(align)
        self._cursor.setBlockFormat(bf)
        self.viewport().update()

    def set_line_spacing(self, spacing_mult: float) -> None:
        bf = self._cursor.blockFormat()
        bf.setLineHeight(int(spacing_mult * 100), QTextBlockFormat.LineHeightTypes.ProportionalHeight.value)
        self._cursor.setBlockFormat(bf)
        self.viewport().update()

    def create_bullet_list(self) -> None:
        self._cursor.createList(QTextListFormat.Style.ListDisc)
        self.viewport().update()

    def create_numbered_list(self, start: int = 1) -> None:
        fmt = QTextListFormat()
        fmt.setStyle(QTextListFormat.Style.ListDecimal)
        fmt.setStart(start)
        self._cursor.createList(fmt)
        self.viewport().update()

    def _check_auto_numbered_list(self) -> None:
        """Detects 'N.' at the start of a line and auto-triggers a numbered list starting at N."""
        block = self._cursor.block()
        if block.textList() is not None:
            return

        text = block.text()
        m = re.match(r"^(\s*)(\d+)\.(\s*)$", text)
        if m:
            indent = len(m.group(1))
            start_num = int(m.group(2))

            self._cursor.beginEditBlock()
            self._cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
            self._cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock, QTextCursor.MoveMode.KeepAnchor)
            self._cursor.removeSelectedText()

            fmt = QTextListFormat()
            fmt.setStyle(QTextListFormat.Style.ListDecimal)
            fmt.setStart(start_num)
            if indent > 0:
                fmt.setIndent(indent)
            self._cursor.createList(fmt)
            self._cursor.endEditBlock()

    # --- Script Formatting (Superscript, Subscript, Super-superscript, Sub-subscript) ---
    def set_script_alignment(self, script_type: str) -> None:
        """Sets vertical script alignment: 'super', 'sub', 'super_super', 'sub_sub', or 'normal'."""
        fmt = QTextCharFormat()
        current_fmt = self._cursor.charFormat()
        base_size = current_fmt.fontPointSize() if current_fmt.fontPointSize() > 0 else 12.0

        if script_type == "super":
            fmt.setVerticalAlignment(QTextCharFormat.VerticalAlignment.AlignSuperScript)
            fmt.setFontPointSize(max(6.5, round(base_size * 0.78, 1)))
        elif script_type == "sub":
            fmt.setVerticalAlignment(QTextCharFormat.VerticalAlignment.AlignSubScript)
            fmt.setFontPointSize(max(6.5, round(base_size * 0.78, 1)))
        elif script_type == "super_super":
            fmt.setVerticalAlignment(QTextCharFormat.VerticalAlignment.AlignSuperScript)
            fmt.setFontPointSize(max(5.0, round(base_size * 0.55, 1)))
        elif script_type == "sub_sub":
            fmt.setVerticalAlignment(QTextCharFormat.VerticalAlignment.AlignSubScript)
            fmt.setFontPointSize(max(5.0, round(base_size * 0.55, 1)))
        else:
            fmt.setVerticalAlignment(QTextCharFormat.VerticalAlignment.AlignNormal)
            curr_align = current_fmt.verticalAlignment()
            if curr_align in (QTextCharFormat.VerticalAlignment.AlignSuperScript, QTextCharFormat.VerticalAlignment.AlignSubScript):
                fmt.setFontPointSize(round(base_size / 0.78, 1))

        self._cursor.mergeCharFormat(fmt)
        self.viewport().update()

    # --- Robust Indentation Controls ---
    def increase_indent(self) -> None:
        """Increases block left indentation level."""
        bf = self._cursor.blockFormat()
        bf.setIndent(bf.indent() + 1)
        self._cursor.setBlockFormat(bf)
        self.viewport().update()

    def decrease_indent(self) -> None:
        """Decreases block left indentation level."""
        bf = self._cursor.blockFormat()
        if bf.indent() > 0:
            bf.setIndent(bf.indent() - 1)
            self._cursor.setBlockFormat(bf)
            self.viewport().update()

    def set_first_line_indent(self, indent_pt: float) -> None:
        """Sets or toggles first-line paragraph indent (e.g., 36.0 pt = 0.5 in)."""
        bf = self._cursor.blockFormat()
        new_indent = 0.0 if bf.textIndent() > 1.0 else indent_pt
        bf.setTextIndent(new_indent)
        self._cursor.setBlockFormat(bf)
        self.viewport().update()

    # --- Table Builder & Manipulation ---
    def insert_table(
        self,
        rows: int,
        cols: int,
        has_header: bool = True,
        border_width: int = 1,
        padding: int = 6,
        cell_padding: Optional[int] = None,
    ) -> Optional[QTextTable]:
        """Inserts a structured QTextTable at the current cursor."""
        if cell_padding is not None:
            padding = cell_padding
        tf = QTextTableFormat()
        tf.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        tf.setCellPadding(padding)
        tf.setCellSpacing(0)
        tf.setBorder(border_width)
        tf.setBorderStyle(
            QTextTableFormat.BorderStyle.BorderStyle_Solid if border_width > 0
            else QTextTableFormat.BorderStyle.BorderStyle_None
        )
        tf.setBorderBrush(QBrush(QColor(100, 110, 140, 120)))

        table = self._cursor.insertTable(rows, cols, tf)
        if has_header and table:
            header_col = QColor(122, 162, 247, 30) if not self.dark_paper else QColor(36, 40, 59, 200)
            for col in range(cols):
                cell = table.cellAt(0, col)
                cf = cell.format()
                cf.setBackground(header_col)
                cell.setFormat(cf)

        self.sync_document_geometry()
        self.viewport().update()
        return table

    def table_insert_row_above(self) -> None:
        table = self._cursor.currentTable()
        if table:
            cell = table.cellAt(self._cursor)
            if cell.isValid():
                table.insertRows(cell.row(), 1)
                self.sync_document_geometry()
                self.viewport().update()

    def table_insert_row_below(self) -> None:
        table = self._cursor.currentTable()
        if table:
            cell = table.cellAt(self._cursor)
            if cell.isValid():
                table.insertRows(cell.row() + 1, 1)
                self.sync_document_geometry()
                self.viewport().update()

    def table_insert_col_left(self) -> None:
        table = self._cursor.currentTable()
        if table:
            cell = table.cellAt(self._cursor)
            if cell.isValid():
                table.insertColumns(cell.column(), 1)
                self.sync_document_geometry()
                self.viewport().update()

    def table_insert_col_right(self) -> None:
        table = self._cursor.currentTable()
        if table:
            cell = table.cellAt(self._cursor)
            if cell.isValid():
                table.insertColumns(cell.column() + 1, 1)
                self.sync_document_geometry()
                self.viewport().update()

    def table_remove_row(self) -> None:
        table = self._cursor.currentTable()
        if table:
            cell = table.cellAt(self._cursor)
            if cell.isValid() and table.rows() > 1:
                table.removeRows(cell.row(), 1)
                self.sync_document_geometry()
                self.viewport().update()

    def table_remove_col(self) -> None:
        table = self._cursor.currentTable()
        if table:
            cell = table.cellAt(self._cursor)
            if cell.isValid() and table.columns() > 1:
                table.removeColumns(cell.column(), 1)
                self.sync_document_geometry()
                self.viewport().update()

    def table_remove_table(self) -> None:
        table = self._cursor.currentTable()
        if table:
            cur = table.firstCursorPosition()
            cur.movePosition(QTextCursor.MoveOperation.PreviousCharacter)
            table_len = table.lastCursorPosition().position() - cur.position()
            cur.movePosition(QTextCursor.MoveOperation.NextCharacter, QTextCursor.MoveMode.KeepAnchor, table_len + 1)
            cur.removeSelectedText()
            self.sync_document_geometry()
            self.viewport().update()

    # --- Footnotes & Head Notes ---
    def insert_footnote(self, text: str) -> None:
        """Inserts an in-text superscript marker linked to footnote text."""
        p_idx = self._cursor_page_index()
        anchor = self._cursor.position()
        fn = self.note_manager.add_footnote(text=text, anchor_pos=anchor, page_num=p_idx + 1)

        # Insert superscript marker [1] in text
        fmt = QTextCharFormat()
        fmt.setVerticalAlignment(QTextCharFormat.VerticalAlignment.AlignSuperScript)
        fmt.setFontPointSize(8.0)
        fmt.setForeground(QColor("#7aa2f7"))
        self._cursor.insertText(f"[{fn.marker}]", fmt)
        self.viewport().update()

    def insert_headnote(self, section_title: str, content: str) -> None:
        """Inserts a styled head note banner above current section."""
        self.note_manager.add_headnote(section_title, content)
        bf = QTextBlockFormat()
        bf.setTopMargin(10)
        bf.setBottomMargin(10)
        bf.setBackground(QColor(122, 162, 247, 18))
        self._cursor.insertBlock(bf)

        cf = QTextCharFormat()
        cf.setFontItalic(True)
        cf.setFontPointSize(10.5)
        cf.setForeground(QColor(160, 165, 190) if self.dark_paper else QColor(70, 75, 95))
        self._cursor.insertText(f"§ {section_title} — {content}", cf)
        self._cursor.insertBlock()
        self.viewport().update()

    # --- Typewriter Scrolling ---
    def _apply_typewriter_scrolling(self) -> None:
        """Keeps the active typing line centered vertically in the canvas viewport."""
        if not self.typewriter_scrolling or not self.hasFocus():
            return
        p_idx = self._cursor_page_index()
        print_rect = self._get_printable_rect(p_idx)
        cursor_rect = self._doc.documentLayout().cursorBounds(self._cursor)
        ph_print = self.layout_model.printable_height_px
        doc_cursor_y = cursor_rect.top() - (p_idx * ph_print)
        cursor_screen_y = print_rect.top() + doc_cursor_y
        vh = self.viewport().height()
        target_val = int(cursor_screen_y - (vh / 2))
        self.verticalScrollBar().setValue(max(0, target_val))

    def apply_style(self, style_name: str) -> None:
        bf = self._cursor.blockFormat()
        cf = QTextCharFormat()

        if style_name == "Title":
            cf.setFontPointSize(26)
            cf.setFontWeight(QFont.Weight.Bold)
            bf.setTopMargin(14)
            bf.setBottomMargin(8)
            bf.setProperty(QTextBlockFormat.Property.UserProperty, "title")
        elif style_name == "Heading 1":
            cf.setFontPointSize(18)
            cf.setFontWeight(QFont.Weight.Bold)
            bf.setTopMargin(12)
            bf.setBottomMargin(6)
            bf.setProperty(QTextBlockFormat.Property.UserProperty, "h1")
        elif style_name == "Heading 2":
            cf.setFontPointSize(14)
            cf.setFontWeight(QFont.Weight.Bold)
            bf.setTopMargin(8)
            bf.setBottomMargin(4)
            bf.setProperty(QTextBlockFormat.Property.UserProperty, "h2")
        elif style_name == "Heading 3":
            cf.setFontPointSize(13)
            cf.setFontWeight(QFont.Weight.Bold)
            bf.setTopMargin(6)
            bf.setBottomMargin(3)
            bf.setProperty(QTextBlockFormat.Property.UserProperty, "h3")
        elif style_name == "Heading 4":
            cf.setFontPointSize(12)
            cf.setFontWeight(QFont.Weight.Bold)
            bf.setTopMargin(4)
            bf.setBottomMargin(2)
            bf.setProperty(QTextBlockFormat.Property.UserProperty, "h4")
        elif style_name == "Heading 5":
            cf.setFontPointSize(11)
            cf.setFontWeight(QFont.Weight.Bold)
            cf.setFontItalic(True)
            bf.setTopMargin(4)
            bf.setBottomMargin(2)
            bf.setProperty(QTextBlockFormat.Property.UserProperty, "h5")
        elif style_name == "Blockquote":
            cf.setFontPointSize(11)
            cf.setFontItalic(True)
            bf.setLeftMargin(28)
            bf.setRightMargin(28)
            bf.setTopMargin(8)
            bf.setBottomMargin(8)
        else:  # Normal
            cf.setFontPointSize(12)
            cf.setFontWeight(QFont.Weight.Normal)
            cf.setFontItalic(False)
            bf.setLeftMargin(0)
            bf.setRightMargin(0)
            bf.setTopMargin(2)
            bf.setBottomMargin(6)

        self._cursor.setBlockFormat(bf)
        self._cursor.setBlockCharFormat(cf)
        self._cursor.mergeCharFormat(cf)
        if not self._cursor.hasSelection():
            c = QTextCursor(self._cursor)
            c.select(QTextCursor.SelectionType.BlockUnderCursor)
            c.mergeCharFormat(cf)
        self.sync_document_geometry()
        self.viewport().update()

    def apply_custom_style(self, style_dict: dict) -> None:
        """Applies a custom user-defined style dictionary to current cursor or selection."""
        cf = QTextCharFormat()
        if "font_family" in style_dict and style_dict["font_family"]:
            cf.setFontFamilies([style_dict["font_family"]])
        if "font_size" in style_dict and style_dict["font_size"]:
            cf.setFontPointSize(style_dict["font_size"])
        if "bold" in style_dict:
            cf.setFontWeight(QFont.Weight.Bold if style_dict["bold"] else QFont.Weight.Normal)
        if "italic" in style_dict:
            cf.setFontItalic(style_dict["italic"])
        if "underline" in style_dict:
            cf.setFontUnderline(style_dict["underline"])
        if "strike" in style_dict:
            cf.setFontStrikeOut(style_dict["strike"])
        if "color" in style_dict and style_dict["color"]:
            cf.setForeground(QColor(style_dict["color"]))
        if "bg_color" in style_dict and style_dict["bg_color"]:
            cf.setBackground(QColor(style_dict["bg_color"]))

        bf = QTextBlockFormat()
        if "align" in style_dict and style_dict["align"] is not None:
            bf.setAlignment(style_dict["align"])
        if "line_height" in style_dict and style_dict["line_height"]:
            bf.setLineHeight(style_dict["line_height"], QTextBlockFormat.LineHeightTypes.ProportionalHeight.value)
        if "top_margin" in style_dict:
            bf.setTopMargin(style_dict["top_margin"])
        if "bottom_margin" in style_dict:
            bf.setBottomMargin(style_dict["bottom_margin"])

        self._cursor.setBlockFormat(bf)
        self._cursor.setBlockCharFormat(cf)
        self._cursor.mergeCharFormat(cf)
        if not self._cursor.hasSelection():
            c = QTextCursor(self._cursor)
            c.select(QTextCursor.SelectionType.BlockUnderCursor)
            c.mergeCharFormat(cf)
        self.sync_document_geometry()
        self.viewport().update()

    def insert_image(self, file_path: str, width: Optional[int] = None) -> bool:
        """Inserts an image into the document with auto-scaling to the printable page width."""
        if not os.path.exists(file_path):
            return False
        img = QImage(file_path)
        if img.isNull():
            return False

        pw_print = self.layout_model.printable_width_px
        max_w = int(pw_print - 40)
        actual_w = img.width()
        actual_h = img.height()

        if width:
            target_w = min(width, max_w)
        elif actual_w > max_w:
            target_w = max_w
        else:
            target_w = actual_w

        aspect = actual_h / max(1, actual_w)
        target_h = int(target_w * aspect)

        img_fmt = QTextImageFormat()
        img_fmt.setName(file_path)
        img_fmt.setWidth(target_w)
        img_fmt.setHeight(target_h)

        self._doc.addResource(QTextDocument.ResourceType.ImageResource, QUrl.fromLocalFile(file_path), img)
        self._cursor.insertImage(img_fmt)
        self.sync_document_geometry()
        self.viewport().update()
        return True

    def insert_page_break(self) -> None:
        bf = QTextBlockFormat()
        bf.setPageBreakPolicy(QTextBlockFormat.PageBreakFlag.PageBreak_AlwaysBefore)
        self._cursor.insertBlock(bf)
        self.viewport().update()

    # --- Editor Compatibility API ---
    def toPlainText(self) -> str:
        return self._doc.toPlainText()

    def setPlainText(self, text: str) -> None:
        self._doc.setPlainText(text)
        self._cursor = QTextCursor(self._doc)
        self._apply_default_text_format()
        self.sync_document_geometry()

    def setHtml(self, html: str) -> None:
        self._doc.setHtml(html)
        self._cursor = QTextCursor(self._doc)
        self.sync_document_geometry()

    def clear(self) -> None:
        self._doc.clear()
        css_color = "#ffffff" if self.dark_paper else "#000000"
        self._doc.setDefaultStyleSheet(f"body {{ color: {css_color}; }}")
        self._cursor = QTextCursor(self._doc)
        self._apply_default_text_format()
        self.sync_document_geometry()

    def textCursor(self) -> QTextCursor:
        return self._cursor

    def setTextCursor(self, cursor: QTextCursor) -> None:
        self._cursor = cursor
        self.viewport().update()

    def find(self, text: str) -> bool:
        cursor = self._doc.find(text, self._cursor)
        if not cursor.isNull():
            self._cursor = cursor
            self._reset_cursor_blink()
            self.viewport().update()
            return True
        return False

    def undo(self) -> None:
        self._doc.undo()
        self.viewport().update()

    def redo(self) -> None:
        self._doc.redo()
        self.viewport().update()

    def cut(self) -> None:
        if self._cursor.hasSelection():
            QApplication.clipboard().setText(self._cursor.selectedText())
            self._cursor.removeSelectedText()
            self.viewport().update()

    def copy(self) -> None:
        if self._cursor.hasSelection():
            QApplication.clipboard().setText(self._cursor.selectedText())

    def paste(self) -> None:
        mime = QApplication.clipboard().mimeData()
        if mime:
            if mime.hasHtml():
                self._cursor.insertHtml(mime.html())
            elif mime.hasText():
                self._cursor.insertText(mime.text())
            self.sync_document_geometry()
            self.viewport().update()

    def paste_plain(self, text: Optional[str] = None) -> None:
        """Pastes plain text without any formatting, matching surrounding text format."""
        if text is None:
            clipboard = QApplication.clipboard()
            try:
                text = clipboard.text()
            except Exception:
                text = ""
            if not text:
                try:
                    mime = clipboard.mimeData()
                    if mime and mime.hasText():
                        text = mime.text()
                except Exception:
                    pass
        if text:
            self._cursor.insertText(text)
            self.sync_document_geometry()
            self.viewport().update()

    def selectAll(self) -> None:
        self._cursor.select(QTextCursor.SelectionType.Document)
        self.viewport().update()

    def fontWeight(self) -> int:
        return self._cursor.charFormat().fontWeight()

    def fontItalic(self) -> bool:
        return self._cursor.charFormat().fontItalic()

    def fontUnderline(self) -> bool:
        return self._cursor.charFormat().fontUnderline()

    def currentCharFormat(self) -> QTextCharFormat:
        return self._cursor.charFormat()

    def currentBlockFormat(self) -> QTextBlockFormat:
        return self._cursor.blockFormat()

    def current_style_snapshot(self) -> dict:
        """Captures a full snapshot of current formatting to save as a custom style."""
        cf = self._cursor.charFormat()
        bf = self._cursor.blockFormat()
        fam = cf.font().family() if hasattr(cf, "font") else "Georgia"
        pt = int(cf.fontPointSize()) if cf.fontPointSize() > 0 else (int(cf.font().pointSize()) if hasattr(cf, "font") and cf.font().pointSize() > 0 else 12)
        return {
            "font_family": fam or "Georgia",
            "font_size": pt if pt > 0 else 12,
            "bold": cf.fontWeight() >= 700 or (hasattr(cf, "font") and cf.font().bold()),
            "italic": cf.fontItalic() or (hasattr(cf, "font") and cf.font().italic()),
            "underline": cf.fontUnderline() or (hasattr(cf, "font") and cf.font().underline()),
            "strike": cf.fontStrikeOut() or (hasattr(cf, "font") and cf.font().strikeOut()),
            "color": cf.foreground().color().name() if cf.foreground().color().isValid() else "#c0caf5",
            "bg_color": cf.background().color().name() if cf.background().color().isValid() else None,
            "align": bf.alignment(),
            "line_height": bf.lineHeight(),
            "top_margin": bf.topMargin(),
            "bottom_margin": bf.bottomMargin(),
        }

    def scroll_to_position(self, pos: int) -> None:
        """Positions cursor at the specified document index and scrolls the page into view."""
        self._cursor.setPosition(min(max(0, pos), max(0, self._doc.characterCount() - 1)))
        self.cursorPositionChanged.emit()
        self._reset_cursor_blink()

        block = self._doc.findBlock(self._cursor.position())
        if not block.isValid():
            return

        doc_y = self._doc.documentLayout().blockBoundingRect(block).top()
        ph_print = self.layout_model.printable_height_px
        target_page = int(doc_y // ph_print) if ph_print > 0 else 0
        offset_y = doc_y - (target_page * ph_print)
        page_rect = self._get_page_rect(target_page)
        my = self.layout_model.margin_top_px

        screen_y = page_rect.y() + my + offset_y
        self.verticalScrollBar().setValue(max(0, int(screen_y - 80)))
        self.viewport().update()

    def insert_chapter(self, title: str = "New Chapter") -> None:
        """Inserts a page break and heading for a new chapter in the manuscript."""
        bf = QTextBlockFormat()
        bf.setPageBreakPolicy(QTextBlockFormat.PageBreakFlag.PageBreak_AlwaysBefore)
        bf.setProperty(QTextBlockFormat.Property.UserProperty, "h1")
        bf.setTopMargin(18)
        bf.setBottomMargin(8)

        cf = QTextCharFormat()
        cf.setFontPointSize(18)
        cf.setFontWeight(QFont.Weight.Bold)

        self._cursor.insertBlock(bf, cf)
        self._cursor.insertText(title)

        bf_body = QTextBlockFormat()
        bf_body.setTopMargin(4)
        bf_body.setBottomMargin(6)
        cf_body = QTextCharFormat()
        cf_body.setFontPointSize(12)
        cf_body.setFontWeight(QFont.Weight.Normal)
        self._cursor.insertBlock(bf_body, cf_body)
        self.viewport().update()

    def insert_text_at_cursor(self, text: str) -> None:
        """Inserts text at current cursor location."""
        self._cursor.insertText(text)
        self._reset_cursor_blink()
        self.cursorPositionChanged.emit()
        self.viewport().update()

    def get_active_sentence_or_paragraph(self) -> str:
        """Returns the text of the block/paragraph where the cursor currently resides."""
        block = self._cursor.block()
        if block.isValid():
            return block.text()
        return ""

    def set_lens_findings(self, findings: List[Any]) -> None:
        """Configures non-destructive highlighter washes and spellcheck squiggles."""
        self._lens_findings = findings
        self._lens_selections = []
        self._lens_selections_with_range = []
        doc_len = self._doc.characterCount()
        for f in findings:
            sel = QAbstractTextDocumentLayout.Selection()
            c = QTextCursor(self._doc)
            c.setPosition(f.start_pos)
            c.setPosition(min(f.end_pos, doc_len - 1), QTextCursor.MoveMode.KeepAnchor)
            sel.cursor = c
            fmt = QTextCharFormat()
            if getattr(f, "lens_type", "") == "spelling":
                fmt.setUnderlineStyle(QTextCharFormat.UnderlineStyle.SpellCheckUnderline)
                fmt.setUnderlineColor(QColor("#f7768e"))
                fmt.setBackground(f.color)
            else:
                fmt.setBackground(f.color)
            sel.format = fmt
            self._lens_selections.append(sel)
            self._lens_selections_with_range.append((f.start_pos, f.end_pos, sel))
        self.viewport().update()

    def _create_color_icon(self, color_hex: str, size: int = 14) -> QIcon:
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QBrush(QColor(color_hex)))
        painter.setPen(QPen(QColor(120, 120, 140, 160), 1))
        painter.drawRoundedRect(0, 0, size - 1, size - 1, 3, 3)
        painter.end()
        return QIcon(pixmap)

    def contextMenuEvent(self, event):
        """Context menu with intelligent review fixes, spelling suggestions, color options, and editing."""
        if hasattr(event, "pos"):
            screen_pt = event.pos()
        elif hasattr(event, "position"):
            screen_pt = event.position()
        else:
            screen_pt = event.globalPos()

        pos = self._screen_point_to_doc_position(screen_pt)
        if pos is not None:
            self._cursor.setPosition(pos)
            self.cursorPositionChanged.emit()

        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #1f2335;
                color: #c0caf5;
                border: 1px solid #292e42;
                border-radius: 6px;
                padding: 4px;
            }
            QMenu::item {
                padding: 5px 20px 5px 12px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #2e344e;
                color: #7aa2f7;
            }
            QMenu::separator {
                height: 1px;
                background-color: #292e42;
                margin: 4px 8px;
            }
        """)

        # 1. Table Context Actions if clicked inside a table
        table = self._cursor.currentTable()
        if table:
            tbl_menu = menu.addMenu("📊 Table Options")
            act_r_above = tbl_menu.addAction("➕ Insert Row Above")
            act_r_above.triggered.connect(self.table_insert_row_above)
            act_r_below = tbl_menu.addAction("➕ Insert Row Below")
            act_r_below.triggered.connect(self.table_insert_row_below)

            tbl_menu.addSeparator()
            act_c_left = tbl_menu.addAction("➕ Insert Column Left")
            act_c_left.triggered.connect(self.table_insert_col_left)
            act_c_right = tbl_menu.addAction("➕ Insert Column Right")
            act_c_right.triggered.connect(self.table_insert_col_right)

            tbl_menu.addSeparator()
            act_del_r = tbl_menu.addAction("🗑️ Delete Row")
            act_del_r.triggered.connect(self.table_remove_row)
            act_del_c = tbl_menu.addAction("🗑️ Delete Column")
            act_del_c.triggered.connect(self.table_remove_col)
            act_del_t = tbl_menu.addAction("🗑️ Delete Entire Table")
            act_del_t.triggered.connect(self.table_remove_table)
            menu.addSeparator()

        # 2. Find review findings encompassing click position
        matched_findings = []
        if pos is not None and hasattr(self, "_lens_findings") and self._lens_findings:
            for f in self._lens_findings:
                if f.start_pos <= pos <= f.end_pos or (pos > 0 and f.start_pos <= pos - 1 <= f.end_pos):
                    matched_findings.append(f)

        # On-the-fly live spelling check if cursor is on an unrecognized word
        if not matched_findings and getattr(self, "spell_engine", None) and pos is not None:
            c_word = QTextCursor(self._doc)
            c_word.setPosition(pos)
            c_word.select(QTextCursor.SelectionType.WordUnderCursor)
            word = c_word.selectedText().strip()
            if word and len(word) > 1 and word.isalpha() and not self.spell_engine.check_word(word):
                sugs = self.spell_engine.get_suggestions(word, limit=4)
                w_start = c_word.selectionStart()
                w_end = c_word.selectionEnd()
                f_live = LensFinding(
                    lens_type="spelling",
                    start_pos=w_start,
                    end_pos=w_end,
                    text=word,
                    message=f"Possible spelling mistake: '{word}'",
                    color=QColor(247, 118, 142, 60),
                    suggestions=sugs,
                )
                matched_findings.append(f_live)

        if matched_findings:
            for f in matched_findings:
                lens_type = getattr(f, "lens_type", "")
                if lens_type == "spelling":
                    if not f.suggestions and getattr(self, "spell_engine", None):
                        f.suggestions = self.spell_engine.get_suggestions(f.text, limit=4)

                    if f.suggestions:
                        for sug in f.suggestions:
                            act = menu.addAction(f"✨ {sug}")
                            font = act.font()
                            font.setBold(True)
                            act.setFont(font)
                            act.triggered.connect(
                                lambda _, s=sug, ff=f: self.replace_range(ff.start_pos, ff.end_pos, s)
                            )
                    else:
                        act_no_sug = menu.addAction("No spelling suggestions")
                        act_no_sug.setEnabled(False)

                    menu.addSeparator()
                    act_add_dict = menu.addAction(f"➕ Add '{f.text}' to Dictionary")
                    act_add_dict.triggered.connect(
                        lambda _, ff=f: self.addToDictionaryRequested.emit(ff.text)
                    )

                    act_ignore = menu.addAction("👁 Ignore for Session")
                    act_ignore.triggered.connect(
                        lambda _, ff=f: self.ignoreWordRequested.emit(ff.text)
                    )
                    menu.addSeparator()
                else:
                    # Adverbs, filler phrases, passive voice, etc.
                    lens_titles = {
                        "adverb": "Weak Adverb",
                        "filler": "Wordy Crutch",
                        "passive": "Passive Voice",
                        "dialogue": "Dialogue Voice",
                        "pacing": "Pacing & Cadence",
                    }
                    title = lens_titles.get(lens_type, lens_type.capitalize())
                    hdr = menu.addAction(f"💡 {title}: '{f.text}'")
                    hdr.setEnabled(False)

                    if f.suggestions:
                        for sug in f.suggestions:
                            if sug == "(remove)":
                                act = menu.addAction(f"🗑️ Remove '{f.text}'")
                                act.triggered.connect(
                                    lambda _, ff=f: self.replace_range(ff.start_pos, ff.end_pos, "")
                                )
                            elif sug in ("Rephrase in active voice", "(make subject the actor)", "Read aloud to check cadence"):
                                act_info = menu.addAction(f"💡 {sug}")
                                act_info.setEnabled(False)
                            else:
                                act = menu.addAction(f"✨ Swap with '{sug}'")
                                font = act.font()
                                font.setBold(True)
                                act.setFont(font)
                                act.triggered.connect(
                                    lambda _, s=sug, ff=f: self.replace_range(ff.start_pos, ff.end_pos, s)
                                )
                    elif f.message:
                        act_msg = menu.addAction(f"💡 {f.message[:60]}...")
                        act_msg.setEnabled(False)

                    menu.addSeparator()

        # Quick Highlighting and Font Color for Selection
        if self._cursor.hasSelection():
            hl_menu = menu.addMenu("🎨 Highlight Selection")
            palette_hl = [
                ("Yellow", "#fef08a"),
                ("Mint Green", "#bbf7d0"),
                ("Sky Blue", "#bae6fd"),
                ("Pink", "#fbcfe8"),
                ("Amber", "#fed7aa"),
                ("Lavender", "#e9d5ff"),
            ]
            for name, col_hex in palette_hl:
                act_hl = hl_menu.addAction(self._create_color_icon(col_hex), name)
                act_hl.triggered.connect(lambda _, c=col_hex: self.set_highlight_color(QColor(c)))

            hl_menu.addSeparator()
            act_clear_hl = hl_menu.addAction("🚫 Clear Highlight")
            act_clear_hl.triggered.connect(self.clear_highlight)

            color_menu = menu.addMenu("🔤 Font Color")
            palette_fc = [
                ("Default (Dark)", "#18181b"),
                ("Royal Blue", "#2563eb"),
                ("Crimson Red", "#dc2626"),
                ("Emerald Green", "#15803d"),
                ("Amber Brown", "#b45309"),
                ("Deep Purple", "#7e22ce"),
                ("Slate Gray", "#64748b"),
            ]
            for name, col_hex in palette_fc:
                act_fc = color_menu.addAction(self._create_color_icon(col_hex), name)
                act_fc.triggered.connect(lambda _, c=col_hex: self.set_text_color(QColor(c)))

            menu.addSeparator()

        # Standard context menu actions
        act_undo = menu.addAction("Undo")
        act_undo.setEnabled(self._doc.isUndoAvailable())
        act_undo.triggered.connect(self._doc.undo)

        act_redo = menu.addAction("Redo")
        act_redo.setEnabled(self._doc.isRedoAvailable())
        act_redo.triggered.connect(self._doc.redo)

        menu.addSeparator()

        act_cut = menu.addAction("Cut")
        act_cut.setEnabled(self._cursor.hasSelection())
        act_cut.triggered.connect(self.cut)

        act_copy = menu.addAction("Copy")
        act_copy.setEnabled(self._cursor.hasSelection())
        act_copy.triggered.connect(self.copy)

        act_paste = menu.addAction("Paste")
        act_paste.triggered.connect(self.paste)

        act_paste_plain = menu.addAction("Paste without Formatting")
        act_paste_plain.triggered.connect(self.paste_plain)

        menu.addSeparator()

        act_sel_all = menu.addAction("Select All")
        act_sel_all.triggered.connect(self.selectAll)

        menu.exec(event.globalPos())

    def clear_lens_findings(self) -> None:
        """Clears all revision highlights returning canvas to pristine paper."""
        self._lens_findings = []
        self._lens_selections = []
        self._lens_selections_with_range = []
        self.viewport().update()

    def replace_range(self, start_pos: int, end_pos: int, replacement_text: str) -> None:
        """Replaces a specific text span in the manuscript with full undo support and whitespace cleanup."""
        c = QTextCursor(self._doc)
        c.setPosition(start_pos)
        actual_end = min(end_pos, self._doc.characterCount() - 1)
        if replacement_text == "":
            c_check = QTextCursor(self._doc)
            c_check.setPosition(actual_end)
            c_check.setPosition(min(actual_end + 1, self._doc.characterCount() - 1), QTextCursor.MoveMode.KeepAnchor)
            if c_check.selectedText() == " ":
                actual_end = min(actual_end + 1, self._doc.characterCount() - 1)
            elif start_pos > 0:
                c_prev = QTextCursor(self._doc)
                c_prev.setPosition(start_pos - 1)
                c_prev.setPosition(start_pos, QTextCursor.MoveMode.KeepAnchor)
                if c_prev.selectedText() == " ":
                    start_pos -= 1
                    c.setPosition(start_pos)

        c.setPosition(actual_end, QTextCursor.MoveMode.KeepAnchor)
        c.insertText(replacement_text)
        self._cursor.setPosition(c.position())
        self.cursorPositionChanged.emit()
        self.viewport().update()

    def highlight_range(self, start_pos: int, end_pos: int) -> None:
        """Selects a range and scrolls it smoothly into view."""
        self._cursor.setPosition(start_pos)
        self._cursor.setPosition(min(end_pos, self._doc.characterCount() - 1), QTextCursor.MoveMode.KeepAnchor)
        self.scroll_to_position(start_pos)
        self.viewport().update()

    def set_search_matches(self, matches: List[Tuple[int, int]], current_index: int = -1) -> None:
        """Highlights all search matches across the paginated sheets with active match accent."""
        self._search_matches = matches
        self._current_search_match_index = current_index
        self._search_selections_with_range = []
        doc_len = self._doc.characterCount()

        for idx, (start_pos, end_pos) in enumerate(matches):
            sel = QAbstractTextDocumentLayout.Selection()
            c = QTextCursor(self._doc)
            c.setPosition(start_pos)
            c.setPosition(min(end_pos, doc_len - 1), QTextCursor.MoveMode.KeepAnchor)
            sel.cursor = c
            fmt = QTextCharFormat()

            if idx == current_index:
                # Active match: vibrant golden orange with high contrast
                fmt.setBackground(QColor("#ff9e3b"))
                fmt.setForeground(QColor("#16161e"))
                fmt.setFontWeight(QFont.Weight.Bold)
            else:
                # Background matches: luminous soft golden yellow highlight
                fmt.setBackground(QColor(255, 215, 0, 80))
            sel.format = fmt
            self._search_selections_with_range.append((start_pos, end_pos, sel))

        self.viewport().update()

    def clear_search_matches(self) -> None:
        """Clears all search match highlights from the manuscript."""
        self._search_matches = []
        self._current_search_match_index = -1
        self._search_selections_with_range = []
        self.viewport().update()

    def scroll_to_match(self, match_index: int) -> None:
        """Centers the viewport on the selected search match and updates active highlight."""
        if 0 <= match_index < len(self._search_matches):
            start_pos, end_pos = self._search_matches[match_index]
            self.scroll_to_position(start_pos)
            self.set_search_matches(self._search_matches, match_index)

    def show_find(self, replace_mode: bool = False) -> None:
        """Summons the Find & Replace floating HUD with pre-filled selection if present."""
        prefill = ""
        if self._cursor.hasSelection():
            selected = self._cursor.selectedText().strip()
            if selected and "\u2029" not in selected and "\n" not in selected and len(selected) <= 100:
                prefill = selected
        self.find_replace_bar.show_find(replace_mode=replace_mode, prefill=prefill)
        self._reposition_find_bar()

    def _reposition_find_bar(self) -> None:
        """Ensures the floating find bar stays cleanly docked in the upper-right corner."""
        if not hasattr(self, "find_replace_bar") or not self.find_replace_bar:
            return
        vw = self.viewport().width()
        bw = self.find_replace_bar.width()
        bh = self.find_replace_bar.sizeHint().height()
        x = max(16, vw - bw - 24)
        y = 16
        self.find_replace_bar.setGeometry(x, y, bw, bh)

    # Aliases for QTextEdit / Studio compatibility
    setFontFamily = set_font_family
    setFontPointSize = set_font_size
    setTextColor = set_text_color
    setTextBackgroundColor = set_highlight_color
    setAlignment = set_alignment
    sync_canvas_layout = sync_document_geometry

    @property
    def page_count(self) -> int:
        return self._total_pages()

