"""Modern Fluent Floating Image Options HUD for Volumenodex.

Provides an instant, luxury floating toolbar anchored right to any clicked
or selected image on the paginated canvas, offering direct access to:
- Resize Image (with pixel dimension feedback)
- Crop Image
- Placement & Alignment (In-line, Left, Center, Right)
- Copy, Cut, Delete, and Save Image As (.JXL, .PNG).
"""

from typing import Optional
from PySide6.QtCore import Qt, Signal, QPoint
from PySide6.QtGui import QColor, QFont, QTextCursor, QTextImageFormat
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QPushButton, QToolButton, QLabel,
    QMenu, QGraphicsDropShadowEffect
)


class ImageOptionsBar(QFrame):
    """Floating HUD toolbar anchored to images for instant resizing, cropping, and alignment."""

    resizeRequested = Signal()
    cropRequested = Signal()
    alignmentRequested = Signal(object)  # Optional[Qt.AlignmentFlag]
    copyRequested = Signal()
    cutRequested = Signal()
    saveRequested = Signal()
    deleteRequested = Signal()
    closed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("imageOptionsBar")
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self._img_width: int = 0
        self._img_height: int = 0

        self._init_ui()
        self._apply_styling()

    def _init_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)

        # Title / Dimension badge
        self.lbl_info = QLabel("🖼️ Image")
        self.lbl_info.setStyleSheet("color: #7aa2f7; font-weight: 700; font-size: 11px; padding: 0 4px;")
        layout.addWidget(self.lbl_info)

        # Separator
        layout.addWidget(self._create_separator())

        # Resize Button
        self.btn_resize = QPushButton("📐 Resize...")
        self.btn_resize.setToolTip("Resize image dimensions and scale (Ctrl+Click)")
        self.btn_resize.clicked.connect(self.resizeRequested.emit)
        layout.addWidget(self.btn_resize)

        # Crop Button
        self.btn_crop = QPushButton("✂️ Crop...")
        self.btn_crop.setToolTip("Crop image with interactive preview")
        self.btn_crop.clicked.connect(self.cropRequested.emit)
        layout.addWidget(self.btn_crop)

        # Alignment Dropdown Button
        self.btn_align = QToolButton()
        self.btn_align.setText("📍 Placement ▾")
        self.btn_align.setToolTip("Change placement and text flow (In-line or Block Alignment)")
        self.btn_align.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        
        align_menu = QMenu(self.btn_align)
        align_menu.setStyleSheet(self._menu_stylesheet())

        act_inline = align_menu.addAction("In-line with Text")
        act_inline.triggered.connect(lambda: self.alignmentRequested.emit(None))

        act_left = align_menu.addAction("Block: Align Left")
        act_left.triggered.connect(lambda: self.alignmentRequested.emit(Qt.AlignmentFlag.AlignLeft))

        act_center = align_menu.addAction("Block: Align Center")
        act_center.triggered.connect(lambda: self.alignmentRequested.emit(Qt.AlignmentFlag.AlignHCenter))

        act_right = align_menu.addAction("Block: Align Right")
        act_right.triggered.connect(lambda: self.alignmentRequested.emit(Qt.AlignmentFlag.AlignRight))

        self.btn_align.setMenu(align_menu)
        layout.addWidget(self.btn_align)

        # Separator
        layout.addWidget(self._create_separator())

        # Copy Button
        self.btn_copy = QPushButton("📋 Copy")
        self.btn_copy.setToolTip("Copy image to clipboard")
        self.btn_copy.clicked.connect(self.copyRequested.emit)
        layout.addWidget(self.btn_copy)

        # Cut Button
        self.btn_cut = QPushButton("✂️ Cut")
        self.btn_cut.setToolTip("Cut image to clipboard")
        self.btn_cut.clicked.connect(self.cutRequested.emit)
        layout.addWidget(self.btn_cut)

        # Save Button
        self.btn_save = QPushButton("💾 Save As...")
        self.btn_save.setToolTip("Save image to disk (.jxl, .png, etc.)")
        self.btn_save.clicked.connect(self.saveRequested.emit)
        layout.addWidget(self.btn_save)

        # Delete Button
        self.btn_del = QPushButton("🗑️")
        self.btn_del.setToolTip("Delete image from document")
        self.btn_del.clicked.connect(self.deleteRequested.emit)
        layout.addWidget(self.btn_del)

        # Close HUD Button
        self.btn_close = QToolButton()
        self.btn_close.setText("✕")
        self.btn_close.setToolTip("Close image toolbar")
        self.btn_close.clicked.connect(self._on_close)
        layout.addWidget(self.btn_close)

    def _create_separator(self) -> QFrame:
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet("background-color: #3b4261; width: 1px; margin: 2px 2px;")
        return sep

    def _apply_styling(self) -> None:
        self.setStyleSheet("""
            #imageOptionsBar {
                background-color: #1f2335;
                border: 1px solid #414868;
                border-radius: 8px;
            }
            QPushButton, QToolButton {
                background-color: #24283b;
                color: #c0caf5;
                border: 1px solid #3b4261;
                border-radius: 4px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover, QToolButton:hover {
                background-color: #2e344e;
                border-color: #7aa2f7;
                color: #ffffff;
            }
            QPushButton:pressed, QToolButton:pressed {
                background-color: #7aa2f7;
                color: #101116;
            }
            QToolButton::menu-indicator {
                image: none;
            }
        """)

        # Ambient drop shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(18)
        shadow.setColor(QColor(0, 0, 0, 160))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)

    def _menu_stylesheet(self) -> str:
        return """
            QMenu {
                background-color: #1f2335;
                color: #c0caf5;
                border: 1px solid #3b4261;
                border-radius: 6px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 20px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #2e344e;
                color: #ffffff;
            }
            QMenu::separator {
                height: 1px;
                background-color: #292e42;
                margin: 4px 6px;
            }
        """

    def update_target(self, img_cursor: QTextCursor, img_fmt: QTextImageFormat) -> None:
        """Updates the badge with the current image dimensions."""
        w = int(round(img_fmt.width()))
        h = int(round(img_fmt.height()))
        self._img_width = w
        self._img_height = h
        self.lbl_info.setText(f"🖼️ Image ({w} × {h})")
        self.adjustSize()

    def _on_close(self) -> None:
        self.hide()
        self.closed.emit()
