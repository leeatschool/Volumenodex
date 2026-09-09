"""Interactive top ruler with draggable margin sliders and unit markers."""

from PySide6.QtCore import Qt, Signal, QRectF, QPointF
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QPolygonF, QFont
from PySide6.QtWidgets import QWidget
from volumenodex.core.document_model import PageLayoutModel, DPI_SCREEN


class InteractiveRuler(QWidget):
    """Horizontal ruler that mirrors page width, printable area, and draggable margin handles."""

    marginsChanged = Signal(float, float)  # left_in, right_in

    HANDLE_NONE = 0
    HANDLE_LEFT_MARGIN = 1
    HANDLE_RIGHT_MARGIN = 2
    HANDLE_FIRST_INDENT = 3

    def __init__(self, layout_model: PageLayoutModel, parent=None):
        super().__init__(parent)
        self.layout_model = layout_model
        self.setFixedHeight(28)
        self.setMouseTracking(True)

        self._page_x_offset = 0  # Horizontal pixel offset where the physical page starts
        self._dragging_handle = self.HANDLE_NONE
        self._hover_handle = self.HANDLE_NONE
        self._first_line_indent_in = 0.0  # relative to left margin

    def set_page_offset(self, offset_x: int) -> None:
        if self._page_x_offset != offset_x:
            self._page_x_offset = offset_x
            self.update()

    def set_first_line_indent(self, indent_in: float) -> None:
        self._first_line_indent_in = indent_in
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        w = self.width()
        h = self.height()
        zoom = self.layout_model.zoom
        dpi = DPI_SCREEN * zoom

        # Background - outer ruler
        painter.fillRect(0, 0, w, h, QColor("#14151e"))

        page_w = self.layout_model.page_width_px
        page_x = self._page_x_offset
        left_m_px = self.layout_model.margin_left_px
        right_m_px = self.layout_model.margin_right_px

        # Non-printable page left margin
        painter.fillRect(page_x, 0, left_m_px, h, QColor("#1e202c"))
        # Printable area (subtly lighter to show active text column)
        printable_w = max(0, page_w - left_m_px - right_m_px)
        painter.fillRect(page_x + left_m_px, 0, printable_w, h, QColor("#282a3a"))
        # Non-printable page right margin
        painter.fillRect(page_x + page_w - right_m_px, 0, right_m_px, h, QColor("#1e202c"))

        # Outer ruler bottom border
        painter.setPen(QPen(QColor("#34374c"), 1))
        painter.drawLine(0, h - 1, w, h - 1)

        # Draw tick marks across the page width
        # 0 inch mark is at the LEFT MARGIN
        zero_x = page_x + left_m_px

        # We'll draw ticks every 1/8 inch
        total_inches = self.layout_model.raw_dimensions_inches[0]
        left_margin_inches = self.layout_model.margins.left
        right_margin_inches = self.layout_model.margins.right

        font = QFont("Segoe UI", 8)
        painter.setFont(font)

        tick_count = int(total_inches * 8)
        for i in range(tick_count + 1):
            cur_inch = (i / 8.0) - left_margin_inches
            tx = zero_x + cur_inch * dpi

            if tx < page_x or tx > page_x + page_w:
                continue

            # Decide tick height
            if i % 8 == 0:
                # Full inch
                tick_h = 10
                painter.setPen(QPen(QColor("#8e94b8"), 1))
                painter.drawLine(int(tx), h - 1 - tick_h, int(tx), h - 1)

                # Number label
                num_val = int(round(cur_inch))
                if num_val != 0:
                    painter.drawText(int(tx) - 8, 12, f"{abs(num_val)}")
            elif i % 4 == 0:
                # 1/2 inch
                tick_h = 6
                painter.setPen(QPen(QColor("#5c6180"), 1))
                painter.drawLine(int(tx), h - 1 - tick_h, int(tx), h - 1)
            elif i % 2 == 0:
                # 1/4 inch
                tick_h = 4
                painter.setPen(QPen(QColor("#454964"), 1))
                painter.drawLine(int(tx), h - 1 - tick_h, int(tx), h - 1)
            else:
                # 1/8 inch
                tick_h = 2
                painter.setPen(QPen(QColor("#393c52"), 1))
                painter.drawLine(int(tx), h - 1 - tick_h, int(tx), h - 1)

        # Draw Margin Sliders
        # Left Margin Marker (at zero_x)
        self._draw_left_marker(painter, zero_x, h)

        # Right Margin Marker (at page_x + page_w - right_m_px)
        right_marker_x = page_x + page_w - right_m_px
        self._draw_right_marker(painter, right_marker_x, h)

        # First line indent marker (at zero_x + indent)
        indent_x = zero_x + (self._first_line_indent_in * dpi)
        self._draw_indent_marker(painter, indent_x, h)

    def _draw_left_marker(self, p: QPainter, x: float, h: int) -> None:
        p.setPen(QPen(QColor("#7aa2f7"), 1.2))
        p.setBrush(QBrush(QColor("#7aa2f7") if self._hover_handle == self.HANDLE_LEFT_MARGIN else QColor("#496bb5")))

        # Bottom upward-pointing triangle & base
        poly = QPolygonF([
            QPointF(x, h - 8),
            QPointF(x - 5, h - 1),
            QPointF(x + 5, h - 1),
        ])
        p.drawPolygon(poly)

    def _draw_right_marker(self, p: QPainter, x: float, h: int) -> None:
        p.setPen(QPen(QColor("#7aa2f7"), 1.2))
        p.setBrush(QBrush(QColor("#7aa2f7") if self._hover_handle == self.HANDLE_RIGHT_MARGIN else QColor("#496bb5")))

        poly = QPolygonF([
            QPointF(x, h - 8),
            QPointF(x - 5, h - 1),
            QPointF(x + 5, h - 1),
        ])
        p.drawPolygon(poly)

    def _draw_indent_marker(self, p: QPainter, x: float, h: int) -> None:
        p.setPen(QPen(QColor("#bb9af7"), 1.2))
        p.setBrush(QBrush(QColor("#bb9af7") if self._hover_handle == self.HANDLE_FIRST_INDENT else QColor("#7f68a8")))

        # Top downward-pointing triangle
        poly = QPolygonF([
            QPointF(x - 5, 1),
            QPointF(x + 5, 1),
            QPointF(x, 8),
        ])
        p.drawPolygon(poly)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            x = event.position().x()
            handle = self._hit_test(x)
            if handle != self.HANDLE_NONE:
                self._dragging_handle = handle
                self.update()

    def mouseMoveEvent(self, event):
        x = event.position().x()
        if self._dragging_handle != self.HANDLE_NONE:
            self._handle_drag(x)
            self.update()
        else:
            old_hover = self._hover_handle
            self._hover_handle = self._hit_test(x)
            if old_hover != self._hover_handle:
                self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging_handle = self.HANDLE_NONE
            self.update()

    def _hit_test(self, mouse_x: float) -> int:
        dpi = DPI_SCREEN * self.layout_model.zoom
        page_x = self._page_x_offset
        left_m_px = self.layout_model.margin_left_px
        right_m_px = self.layout_model.margin_right_px
        page_w = self.layout_model.page_width_px

        zero_x = page_x + left_m_px
        right_x = page_x + page_w - right_m_px
        indent_x = zero_x + (self._first_line_indent_in * dpi)

        if abs(mouse_x - indent_x) <= 6:
            return self.HANDLE_FIRST_INDENT
        if abs(mouse_x - zero_x) <= 6:
            return self.HANDLE_LEFT_MARGIN
        if abs(mouse_x - right_x) <= 6:
            return self.HANDLE_RIGHT_MARGIN
        return self.HANDLE_NONE

    def _handle_drag(self, mouse_x: float) -> None:
        dpi = DPI_SCREEN * self.layout_model.zoom
        page_x = self._page_x_offset
        total_w_in = self.layout_model.raw_dimensions_inches[0]

        if self._dragging_handle == self.HANDLE_LEFT_MARGIN:
            new_left_in = max(0.25, min(total_w_in - self.layout_model.margins.right - 1.0, (mouse_x - page_x) / dpi))
            # Snap to 1/8 inch
            new_left_in = round(new_left_in * 8) / 8
            self.layout_model.margins.left = new_left_in
            self.marginsChanged.emit(self.layout_model.margins.left, self.layout_model.margins.right)
        elif self._dragging_handle == self.HANDLE_RIGHT_MARGIN:
            new_right_in = max(0.25, min(total_w_in - self.layout_model.margins.left - 1.0, (page_x + self.layout_model.page_width_px - mouse_x) / dpi))
            new_right_in = round(new_right_in * 8) / 8
            self.layout_model.margins.right = new_right_in
            self.marginsChanged.emit(self.layout_model.margins.left, self.layout_model.margins.right)
        elif self._dragging_handle == self.HANDLE_FIRST_INDENT:
            zero_x = page_x + self.layout_model.margin_left_px
            new_indent = (mouse_x - zero_x) / dpi
            # Snap to 1/8 inch
            self._first_line_indent_in = round(new_indent * 8) / 8
