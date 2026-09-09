"""High-fidelity paginated document canvas and editing surface."""

import math
from typing import Optional
from PySide6.QtCore import Qt, Signal, QRectF, QRect, QPoint, QSize
from PySide6.QtGui import (
    QPainter, QColor, QPen, QBrush, QFont, QTextCursor,
    QTextBlockFormat, QTextCharFormat, QTextListFormat, QPainterPath
)
from PySide6.QtWidgets import (
    QWidget, QScrollArea, QTextEdit, QVBoxLayout, QHBoxLayout,
    QGraphicsDropShadowEffect, QSizePolicy
)
from volumenodex.core.document_model import PageLayoutModel, DPI_SCREEN, PageMargins
from volumenodex.canvas.paper_texture import PaperTextureEngine, TextureType
from volumenodex.core.theme_manager import ThemeManager


class PaginatedTextEditor(QTextEdit):
    """The rich text editing surface styled and fitted to the printable page boundaries."""

    cursorChangedInfo = Signal()
    keystrokeHappened = Signal(bool, bool)  # is_return, is_space

    def keyPressEvent(self, event):
        super().keyPressEvent(event)
        is_return = event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter)
        is_space = event.key() == Qt.Key.Key_Space
        self.keystrokeHappened.emit(is_return, is_space)

    def __init__(self, layout_model: PageLayoutModel, parent=None):
        super().__init__(parent)
        self.layout_model = layout_model
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setFrameShape(QTextEdit.Shape.NoFrame)

        # Base typography
        default_font = QFont("Georgia", 12)
        default_font.setStyleHint(QFont.StyleHint.Serif)
        self.setFont(default_font)

        self.cursorPositionChanged.connect(self.cursorChangedInfo.emit)
        self.document().contentsChanged.connect(self.adjust_height_to_content)

        # Style sheet for clean transparent embedding
        self._apply_editor_style()

    def _apply_editor_style(self, dark_paper: bool = False) -> None:
        text_color = "#f0f2f8" if dark_paper else "#18181b"
        self.setStyleSheet(f"""
            QTextEdit {{
                background-color: transparent;
                color: {text_color};
                border: none;
                selection-background-color: #3b82f6;
                selection-color: #ffffff;
            }}
        """)

    def adjust_height_to_content(self) -> None:
        # Auto-expand to fit text without clipping
        doc_height = self.document().size().height()
        min_height = self.layout_model.printable_height_px
        target_height = max(int(doc_height) + 40, min_height)
        if self.height() != target_height:
            self.setFixedHeight(target_height)


class DocumentPageContainer(QWidget):
    """The physical paper sheet widget rendering realistic paper texture, drop shadows, margins, and headers/footers."""

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

        self.show_margin_guides = True
        self.dark_paper = False

        # Embedded editor
        self.editor = PaginatedTextEditor(layout_model, self)

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.update_geometry()

    def update_geometry(self) -> None:
        pw = self.layout_model.page_width_px
        ph = self.layout_model.page_height_px
        self.setFixedSize(pw, max(ph, self.editor.height() + self.layout_model.margin_top_px + self.layout_model.margin_bottom_px))

        # Position editor inside printable area
        mx = self.layout_model.margin_left_px
        my = self.layout_model.margin_top_px
        pw_print = self.layout_model.printable_width_px
        ph_print = self.height() - self.layout_model.margin_top_px - self.layout_model.margin_bottom_px

        self.editor.setGeometry(mx, my, pw_print, ph_print)
        self.editor._apply_editor_style(self.dark_paper)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        pw = self.width()
        ph = self.height()

        # 1. Physical Paper Sheet Background
        paper_bg = QColor(self.theme_manager.current.page_bg_dark if self.dark_paper else self.theme_manager.current.page_bg_light)
        painter.fillRect(0, 0, pw, ph, paper_bg)

        # 2. Procedural Paper Grain Texture Overlay (Print Fidelity Feature)
        texture_pixmap = self.texture_engine.get_texture_pixmap()
        if texture_pixmap and self.texture_engine.opacity > 0.001:
            painter.save()
            painter.setOpacity(self.texture_engine.opacity)
            painter.drawTiledPixmap(0, 0, pw, ph, texture_pixmap)
            painter.restore()

        # 3. Subtle Margin Boundary Guidelines (Toggleable)
        if self.show_margin_guides:
            mx = self.layout_model.margin_left_px
            my = self.layout_model.margin_top_px
            mw = self.layout_model.printable_width_px
            mh = ph - my - self.layout_model.margin_bottom_px

            guide_pen = QPen(QColor(140, 150, 180, 50), 1, Qt.PenStyle.DashLine)
            painter.setPen(guide_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(mx, my, mw, mh)

        # 4. Page Break Dividers for Multi-Page flow
        single_page_h = self.layout_model.page_height_px
        page_count = max(1, math.ceil(ph / single_page_h))

        for p in range(1, page_count):
            split_y = p * single_page_h
            # Draw page break gutter
            gutter_h = 24
            painter.fillRect(0, split_y - gutter_h // 2, pw, gutter_h, QColor(self.theme_manager.current.bg_app))

            # Drop shadow under the upper page edge
            painter.setPen(QPen(QColor(0, 0, 0, 80), 1))
            painter.drawLine(0, split_y - gutter_h // 2, pw, split_y - gutter_h // 2)

            # Drop shadow on top of the lower page edge
            painter.setPen(QPen(QColor(0, 0, 0, 80), 1))
            painter.drawLine(0, split_y + gutter_h // 2, pw, split_y + gutter_h // 2)

        # 5. Header & Footer (Page Numbering)
        font = QFont("Georgia", 9)
        painter.setFont(font)
        footer_pen = QColor(130, 135, 155, 140) if not self.dark_paper else QColor(170, 175, 195, 120)
        painter.setPen(footer_pen)

        for p in range(page_count):
            page_bottom = (p + 1) * single_page_h
            footer_y = page_bottom - int(self.layout_model.margin_bottom_px * 0.45)
            if footer_y < ph:
                page_num_str = f"— {p + 1} —"
                painter.drawText(QRectF(0, footer_y - 12, pw, 20), Qt.AlignmentFlag.AlignCenter, page_num_str)


class DocumentCanvasArea(QScrollArea):
    """Viewport hosting the centered document pages, drop shadows, and responsive layout."""

    pageOffsetChanged = Signal(int)

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

        self.setWidgetResizable(False)
        self.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        self.setStyleSheet(f"background-color: {self.theme_manager.current.bg_app}; border: none;")

        # Host container widget
        self.host_widget = QWidget()
        self.host_layout = QVBoxLayout(self.host_widget)
        self.host_layout.setContentsMargins(40, 32, 40, 48)
        self.host_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)

        # Physical Page Container
        self.page_container = DocumentPageContainer(layout_model, texture_engine, theme_manager, self.host_widget)

        # Realistic Physical Page Drop Shadow
        shadow = QGraphicsDropShadowEffect(self.page_container)
        shadow.setBlurRadius(28)
        shadow.setColor(QColor(0, 0, 0, 130))
        shadow.setOffset(0, 8)
        self.page_container.setGraphicsEffect(shadow)

        self.host_layout.addWidget(self.page_container)
        self.setWidget(self.host_widget)

        # Connect editor resize to container and host update
        self.page_container.editor.document().contentsChanged.connect(self.sync_canvas_layout)
        self.horizontalScrollBar().valueChanged.connect(self._notify_page_offset)

    @property
    def editor(self) -> PaginatedTextEditor:
        return self.page_container.editor

    def sync_canvas_layout(self) -> None:
        self.page_container.update_geometry()
        # Adjust host widget size to wrap page container
        hw = max(self.viewport().width(), self.page_container.width() + 80)
        hh = self.page_container.height() + 80
        self.host_widget.resize(hw, hh)
        self._notify_page_offset()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.sync_canvas_layout()

    def _notify_page_offset(self) -> None:
        # Calculate screen X coordinate where the page container begins
        page_pos_in_viewport = self.page_container.mapTo(self.viewport(), QPoint(0, 0))
        self.pageOffsetChanged.emit(page_pos_in_viewport.x())
