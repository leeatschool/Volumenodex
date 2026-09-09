"""Modern Fluent Paginated Document Canvas with discrete paper sheets and print fidelity."""

import os
import math
from typing import Optional, List, Any
from PySide6.QtCore import Qt, Signal, QRectF, QPointF, QPoint, QTimer, QSize, QSizeF, QUrl
from PySide6.QtGui import (
    QPainter, QColor, QPen, QBrush, QFont, QTextCursor, QTextDocument,
    QAbstractTextDocumentLayout, QTextCharFormat, QTextBlockFormat,
    QTextListFormat, QKeySequence, QLinearGradient, QRadialGradient,
    QPainterPath, QClipboard, QGuiApplication, QImage, QTextImageFormat
)
from PySide6.QtWidgets import (
    QAbstractScrollArea, QScrollBar, QApplication, QMenu
)

from volumenodex.core.document_model import PageLayoutModel, DPI_SCREEN, PageMargins
from volumenodex.canvas.paper_texture import PaperTextureEngine, TextureType
from volumenodex.core.theme_manager import ThemeManager


class PaginatedCanvas(QAbstractScrollArea):
    """Luxury discrete multi-page canvas with photorealistic paper sheets, drop shadows, and typography."""

    textChanged = Signal()
    cursorPositionChanged = Signal()
    keystrokeHappened = Signal(bool, bool)  # is_return, is_space
    pageOffsetChanged = Signal(int)
    addToDictionaryRequested = Signal(str)
    ignoreWordRequested = Signal(str)

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

        self.dark_paper = False
        self.show_margin_guides = True
        self.show_crop_marks = True

        # Document Engine
        self._doc = QTextDocument(self)
        self._doc.setUndoRedoEnabled(True)

        # Sublime default typography
        default_font = QFont("Georgia", 12)
        default_font.setStyleHint(QFont.StyleHint.Serif)
        self._doc.setDefaultFont(default_font)

        self._cursor = QTextCursor(self._doc)
        self._cursor_visible = True
        self._is_mouse_selecting = False
        self._lens_findings = []
        self._lens_selections = []

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
    def cursor(self) -> QTextCursor:
        return self._cursor

    def sync_document_geometry(self) -> None:
        """Configures the document page size to match the printable area."""
        pw_print = self.layout_model.printable_width_px
        ph_print = self.layout_model.printable_height_px
        self._doc.setPageSize(QSizeF(pw_print, ph_print))
        self._update_scroll_bars()
        self.viewport().update()

    def _on_doc_contents_changed(self) -> None:
        self._update_scroll_bars()
        self.textChanged.emit()
        self.viewport().update()

    def _toggle_cursor_blink(self) -> None:
        if self.hasFocus():
            self._cursor_visible = not self._cursor_visible
            self.viewport().update()

    def _reset_cursor_blink(self) -> None:
        self._cursor_visible = True
        self._blink_timer.start(500)
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

    def scrollContentsBy(self, dx: int, dy: int):
        super().scrollContentsBy(dx, dy)
        vw = self.viewport().width()
        pw = self.layout_model.page_width_px
        page_x = max(32, (vw - pw) // 2) - self.horizontalScrollBar().value()
        self.pageOffsetChanged.emit(int(page_x))
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

        for p in range(total_pages):
            page_rect = self._get_page_rect(p)
            # Adjust for scrolling
            screen_page_rect = QRectF(page_rect.x() - sx, page_rect.y() - sy, page_rect.width(), page_rect.height())

            # Skip pages outside viewport
            if screen_page_rect.bottom() < 0 or screen_page_rect.top() > vh:
                continue

            # 2. Photorealistic Multi-Layer Drop Shadow
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

            # 7. Running Page Footer
            self._draw_page_footer(painter, screen_page_rect, p + 1)

            # 8. Sliced Text Content & Selection
            print_rect = self._get_printable_rect(p)
            screen_print_rect = QRectF(print_rect.x() - sx, print_rect.y() - sy, print_rect.width(), print_rect.height())

            painter.save()
            painter.setClipRect(screen_print_rect)
            painter.translate(screen_print_rect.x(), screen_print_rect.y() - p * ph_print)

            # Draw document slice with cursor and selection
            ctx = QAbstractTextDocumentLayout.PaintContext()
            ctx.cursorPosition = self._cursor.position() if (self._cursor_visible and self.hasFocus()) else -1

            selections = []
            if hasattr(self, "_lens_selections") and self._lens_selections:
                selections.extend(self._lens_selections)

            if self._cursor.hasSelection():
                sel = QAbstractTextDocumentLayout.Selection()
                sel.cursor = self._cursor
                sel.format.setBackground(QColor(59, 130, 246, 90))
                selections.append(sel)

            ctx.selections = selections

            self._doc.documentLayout().draw(painter, ctx)
            painter.restore()

    def _draw_luxury_page_shadow(self, p: QPainter, rect: QRectF) -> None:
        """Renders realistic multi-stage ambient occlusion and directional paper drop shadow."""
        p.save()
        # Stage 1: Soft Ambient Halo (Blur 18px)
        for i in range(1, 6):
            alpha = int(22 / i)
            p.setPen(QPen(QColor(0, 0, 0, alpha), 3))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(rect.adjusted(-i * 2.5, -i * 1.5, i * 2.5, i * 3.5), 3, 3)

        # Stage 2: Crisp directional bottom shadow
        bottom_rect = QRectF(rect.x() + 4, rect.bottom() - 2, rect.width() - 8, 8)
        grad = QLinearGradient(bottom_rect.topLeft(), bottom_rect.bottomLeft())
        grad.setColorAt(0.0, QColor(0, 0, 0, 75))
        grad.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.fillRect(bottom_rect, grad)
        p.restore()

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

    def _draw_page_footer(self, p: QPainter, rect: QRectF, page_num: int) -> None:
        p.save()
        font = QFont("Georgia", 9)
        font.setStyleHint(QFont.StyleHint.Serif)
        p.setFont(font)
        footer_col = QColor(140, 145, 165, 140) if not self.dark_paper else QColor(160, 165, 185, 120)
        p.setPen(footer_col)

        footer_y = rect.bottom() - int(self.layout_model.margin_bottom_px * 0.45)
        p.drawText(QRectF(rect.x(), footer_y - 10, rect.width(), 20), Qt.AlignmentFlag.AlignCenter, f"— {page_num} —")
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
            pos = self._screen_point_to_doc_position(event.position())
            if pos is not None:
                self._cursor.setPosition(pos)
                self._cursor.select(QTextCursor.SelectionType.WordUnderCursor)
                self._reset_cursor_blink()
                self.cursorPositionChanged.emit()
                self.viewport().update()

    def _screen_point_to_doc_position(self, screen_pt: QPointF) -> Optional[int]:
        sx = self.horizontalScrollBar().value()
        sy = self.verticalScrollBar().value()
        click_x = screen_pt.x() + sx
        click_y = screen_pt.y() + sy

        total_pages = self._total_pages()
        ph_print = self.layout_model.printable_height_px
        pw_print = self.layout_model.printable_width_px

        target_page = 0
        for p in range(total_pages):
            page_rect = self._get_page_rect(p)
            if page_rect.top() <= click_y <= page_rect.bottom() + 36:
                target_page = p
                break
            if p == total_pages - 1:
                target_page = p

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

        # 4. Text Input
        elif event.text() and not is_ctrl:
            self._cursor.insertText(event.text())
            is_space = event.text() == " "
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
        fmt.setFontFamily(family)
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

    def create_numbered_list(self) -> None:
        self._cursor.createList(QTextListFormat.Style.ListDecimal)
        self.viewport().update()

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
            cf.setFontFamily(style_dict["font_family"])
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
        self.sync_document_geometry()

    def setHtml(self, html: str) -> None:
        self._doc.setHtml(html)
        self._cursor = QTextCursor(self._doc)
        self.sync_document_geometry()

    def clear(self) -> None:
        self._doc.clear()
        self._cursor = QTextCursor(self._doc)
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

    def paste_plain(self) -> None:
        """Pastes plain text without any formatting, matching surrounding text format."""
        mime = QApplication.clipboard().mimeData()
        if mime and mime.hasText():
            self._cursor.insertText(mime.text())
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
        for f in findings:
            sel = QAbstractTextDocumentLayout.Selection()
            c = QTextCursor(self._doc)
            c.setPosition(f.start_pos)
            c.setPosition(min(f.end_pos, self._doc.characterCount() - 1), QTextCursor.MoveMode.KeepAnchor)
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
        self.viewport().update()

    def contextMenuEvent(self, event):
        """Context menu with intelligent spelling suggestions and standard text editing."""
        pos = self._screen_point_to_doc_position(event.position())

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

        # Find if click is inside any spelling finding
        spelling_finding = None
        if pos is not None and hasattr(self, "_lens_findings") and self._lens_findings:
            for f in self._lens_findings:
                if getattr(f, "lens_type", "") == "spelling" and f.start_pos <= pos <= f.end_pos:
                    spelling_finding = f
                    break

        if spelling_finding:
            # Top candidate suggestions
            if spelling_finding.suggestions:
                for sug in spelling_finding.suggestions:
                    act = menu.addAction(f"✨ {sug}")
                    font = act.font()
                    font.setBold(True)
                    act.setFont(font)
                    act.triggered.connect(
                        lambda _, s=sug, sf=spelling_finding: self.replace_range(sf.start_pos, sf.end_pos, s)
                    )
            else:
                act_no_sug = menu.addAction("No spelling suggestions")
                act_no_sug.setEnabled(False)

            menu.addSeparator()
            act_add_dict = menu.addAction(f"➕ Add '{spelling_finding.text}' to Dictionary")
            act_add_dict.triggered.connect(
                lambda _, sf=spelling_finding: self.addToDictionaryRequested.emit(sf.text)
            )

            act_ignore = menu.addAction("👁 Ignore for Session")
            act_ignore.triggered.connect(
                lambda _, sf=spelling_finding: self.ignoreWordRequested.emit(sf.text)
            )

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
        self.viewport().update()

    def replace_range(self, start_pos: int, end_pos: int, replacement_text: str) -> None:
        """Replaces a specific text span in the manuscript with full undo support."""
        c = QTextCursor(self._doc)
        c.setPosition(start_pos)
        c.setPosition(min(end_pos, self._doc.characterCount() - 1), QTextCursor.MoveMode.KeepAnchor)
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

