"""Interactive Visual Image Crop Dialog for Volumenodex Word Processing Studio."""

import os
from typing import Optional
from PySide6.QtCore import Qt, QRect, QRectF, QPoint, QSize, Signal
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QPixmap, QImage, QPainterPath
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QWidget, QFrame, QSizePolicy
)

from volumenodex.core.image_utils import load_image, crop_image, save_image


class CropPreviewWidget(QWidget):
    """Interactive preview canvas with draggable and resizable crop selection overlay."""

    cropChanged = Signal(QRect)

    def __init__(self, image: QImage, parent=None):
        super().__init__(parent)
        self.original_image = image
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(400, 300)
        self.setMouseTracking(True)

        self._aspect_ratio: Optional[float] = None  # None = freeform
        self._norm_crop = QRectF(0.1, 0.1, 0.8, 0.8)  # Normalized 0.0 - 1.0 coords
        self._dragging = False
        self._resizing_handle = -1  # 0: TL, 1: TR, 2: BR, 3: BL, -1: move inside
        self._drag_start_pos = QPoint()
        self._drag_start_crop = QRectF()

    def set_aspect_ratio(self, ratio: Optional[float]) -> None:
        self._aspect_ratio = ratio
        if ratio is not None and ratio > 0:
            # Adjust normalized crop to match aspect ratio
            img_w = self.original_image.width()
            img_h = self.original_image.height()
            if img_w > 0 and img_h > 0:
                cur_w = self._norm_crop.width() * img_w
                cur_h = cur_w / ratio
                if cur_h > img_h:
                    cur_h = img_h * 0.8
                    cur_w = cur_h * ratio
                self._norm_crop.setWidth(min(1.0, cur_w / img_w))
                self._norm_crop.setHeight(min(1.0, cur_h / img_h))
        self.update()
        self.cropChanged.emit(self.get_image_crop_rect())

    def reset_crop(self) -> None:
        self._norm_crop = QRectF(0.05, 0.05, 0.9, 0.9)
        self.update()
        self.cropChanged.emit(self.get_image_crop_rect())

    def _get_image_display_rect(self) -> QRectF:
        """Returns the QRectF where the image is drawn scaled inside this widget."""
        w = self.width()
        h = self.height()
        img_w = self.original_image.width()
        img_h = self.original_image.height()
        if img_w <= 0 or img_h <= 0 or w <= 0 or h <= 0:
            return QRectF()

        scale = min(w / img_w, h / img_h)
        disp_w = img_w * scale
        disp_h = img_h * scale
        disp_x = (w - disp_w) / 2
        disp_y = (h - disp_h) / 2
        return QRectF(disp_x, disp_y, disp_w, disp_h)

    def _crop_screen_rect(self) -> QRectF:
        disp = self._get_image_display_rect()
        return QRectF(
            disp.x() + self._norm_crop.x() * disp.width(),
            disp.y() + self._norm_crop.y() * disp.height(),
            self._norm_crop.width() * disp.width(),
            self._norm_crop.height() * disp.height()
        )

    def get_image_crop_rect(self) -> QRect:
        """Returns the crop rectangle in original image pixel coordinates."""
        img_w = self.original_image.width()
        img_h = self.original_image.height()
        x = int(round(self._norm_crop.x() * img_w))
        y = int(round(self._norm_crop.y() * img_h))
        w = int(round(self._norm_crop.width() * img_w))
        h = int(round(self._norm_crop.height() * img_h))
        # Ensure within bounds
        x = max(0, min(img_w - 1, x))
        y = max(0, min(img_h - 1, y))
        w = max(1, min(img_w - x, w))
        h = max(1, min(img_h - y, h))
        return QRect(x, y, w, h)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.fillRect(self.rect(), QColor("#13141c"))

        disp = self._get_image_display_rect()
        if disp.isEmpty():
            return

        # Draw source image
        painter.drawImage(disp, self.original_image)

        # Draw darkened overlay outside crop area
        crop_screen = self._crop_screen_rect()
        path = QPainterPath()
        path.addRect(disp)
        path.addRect(crop_screen)
        painter.fillPath(path, QColor(0, 0, 0, 160))

        # Draw crop rectangle outline
        painter.setPen(QPen(QColor("#7aa2f7"), 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(crop_screen)

        # Draw rule-of-thirds grid
        painter.setPen(QPen(QColor(255, 255, 255, 60), 1, Qt.PenStyle.DashLine))
        w3 = crop_screen.width() / 3
        h3 = crop_screen.height() / 3
        painter.drawLine(crop_screen.x() + w3, crop_screen.y(), crop_screen.x() + w3, crop_screen.bottom())
        painter.drawLine(crop_screen.x() + w3 * 2, crop_screen.y(), crop_screen.x() + w3 * 2, crop_screen.bottom())
        painter.drawLine(crop_screen.x(), crop_screen.y() + h3, crop_screen.right(), crop_screen.y() + h3)
        painter.drawLine(crop_screen.x(), crop_screen.y() + h3 * 2, crop_screen.right(), crop_screen.y() + h3 * 2)

        # Draw corner handles
        handle_size = 10
        painter.setBrush(QColor("#ffffff"))
        painter.setPen(QPen(QColor("#7aa2f7"), 2))
        for pt in [crop_screen.topLeft(), crop_screen.topRight(), crop_screen.bottomRight(), crop_screen.bottomLeft()]:
            painter.drawRect(QRectF(pt.x() - handle_size / 2, pt.y() - handle_size / 2, handle_size, handle_size))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            pt = event.position() if hasattr(event, "position") else event.pos()
            crop_screen = self._crop_screen_rect()
            handle_size = 14

            # Check corner handles
            corners = [
                crop_screen.topLeft(),
                crop_screen.topRight(),
                crop_screen.bottomRight(),
                crop_screen.bottomLeft()
            ]
            for idx, c in enumerate(corners):
                rect = QRectF(c.x() - handle_size, c.y() - handle_size, handle_size * 2, handle_size * 2)
                if rect.contains(pt):
                    self._dragging = True
                    self._resizing_handle = idx
                    self._drag_start_pos = pt
                    self._drag_start_crop = QRectF(self._norm_crop)
                    return

            if crop_screen.contains(pt):
                self._dragging = True
                self._resizing_handle = -1  # move
                self._drag_start_pos = pt
                self._drag_start_crop = QRectF(self._norm_crop)

    def mouseMoveEvent(self, event):
        pt = event.position() if hasattr(event, "position") else event.pos()
        disp = self._get_image_display_rect()
        if disp.isEmpty():
            return

        if self._dragging:
            dx = (pt.x() - self._drag_start_pos.x()) / disp.width()
            dy = (pt.y() - self._drag_start_pos.y()) / disp.height()

            if self._resizing_handle == -1:
                # Move
                new_x = max(0.0, min(1.0 - self._drag_start_crop.width(), self._drag_start_crop.x() + dx))
                new_y = max(0.0, min(1.0 - self._drag_start_crop.height(), self._drag_start_crop.y() + dy))
                self._norm_crop.moveLeft(new_x)
                self._norm_crop.moveTop(new_y)
            elif self._resizing_handle == 2:  # BR
                new_w = max(0.05, min(1.0 - self._drag_start_crop.x(), self._drag_start_crop.width() + dx))
                new_h = max(0.05, min(1.0 - self._drag_start_crop.y(), self._drag_start_crop.height() + dy))
                if self._aspect_ratio:
                    new_h = (new_w * disp.width()) / (self._aspect_ratio * disp.height())
                self._norm_crop.setWidth(new_w)
                self._norm_crop.setHeight(min(1.0 - self._drag_start_crop.y(), new_h))
            elif self._resizing_handle == 0:  # TL
                new_x = max(0.0, min(self._drag_start_crop.right() - 0.05, self._drag_start_crop.x() + dx))
                new_y = max(0.0, min(self._drag_start_crop.bottom() - 0.05, self._drag_start_crop.y() + dy))
                self._norm_crop.setLeft(new_x)
                self._norm_crop.setTop(new_y)

            self.update()
            self.cropChanged.emit(self.get_image_crop_rect())
        else:
            # Update cursor shape
            crop_screen = self._crop_screen_rect()
            if crop_screen.contains(pt):
                self.setCursor(Qt.CursorShape.SizeAllCursor)
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)

    def mouseReleaseEvent(self, event):
        self._dragging = False
        self._resizing_handle = -1


class ImageCropDialog(QDialog):
    """Modal dialog providing high-precision visual cropping for images."""

    def __init__(self, image: QImage, image_path: Optional[str] = None, parent=None):
        super().__init__(parent)
        self.image = image
        self.image_path = image_path
        self.cropped_image: Optional[QImage] = None

        self.setWindowTitle("Crop Image — Volumenodex")
        self.resize(720, 560)
        self.setStyleSheet("""
            QDialog { background-color: #1a1b26; color: #c0caf5; }
            QLabel { color: #c0caf5; }
            QComboBox {
                background-color: #1f2335; color: #c0caf5; border: 1px solid #3b4261;
                border-radius: 4px; padding: 4px 8px;
            }
            QPushButton {
                background-color: #24283b; color: #c0caf5; border: 1px solid #3b4261;
                border-radius: 6px; padding: 6px 14px; font-weight: 600;
            }
            QPushButton:hover { background-color: #2e344e; border-color: #7aa2f7; color: #ffffff; }
            QPushButton#primaryBtn {
                background-color: #7aa2f7; color: #101116; font-weight: bold; border: none;
            }
            QPushButton#primaryBtn:hover { background-color: #89b4fa; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        # Header controls
        h_top = QHBoxLayout()
        h_top.addWidget(QLabel("Aspect Ratio:"))

        self.combo_ratio = QComboBox()
        self.combo_ratio.addItem("Freeform (No Constraint)", None)
        self.combo_ratio.addItem("1:1 Square", 1.0)
        self.combo_ratio.addItem("4:3 Standard Photo", 4.0 / 3.0)
        self.combo_ratio.addItem("16:9 Widescreen", 16.0 / 9.0)
        self.combo_ratio.addItem("3:2 Classic 35mm", 3.0 / 2.0)
        self.combo_ratio.addItem("2:3 Portrait", 2.0 / 3.0)
        self.combo_ratio.currentIndexChanged.connect(self._on_ratio_changed)
        h_top.addWidget(self.combo_ratio)

        h_top.addStretch()

        self.lbl_dims = QLabel(f"Crop Size: {image.width()} × {image.height()} px")
        self.lbl_dims.setStyleSheet("color: #7aa2f7; font-weight: 600;")
        h_top.addWidget(self.lbl_dims)

        btn_reset = QPushButton("Reset Selection")
        btn_reset.clicked.connect(self._on_reset)
        h_top.addWidget(btn_reset)
        layout.addLayout(h_top)

        # Preview area
        self.preview = CropPreviewWidget(self.image, self)
        self.preview.cropChanged.connect(self._on_crop_changed)
        layout.addWidget(self.preview, stretch=1)

        # Bottom buttons
        h_bot = QHBoxLayout()
        h_bot.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        h_bot.addWidget(btn_cancel)

        btn_apply = QPushButton("Apply Crop")
        btn_apply.setObjectName("primaryBtn")
        btn_apply.clicked.connect(self._on_apply)
        h_bot.addWidget(btn_apply)
        layout.addLayout(h_bot)

    def _on_ratio_changed(self, index: int) -> None:
        val = self.combo_ratio.currentData()
        self.preview.set_aspect_ratio(val)

    def _on_reset(self) -> None:
        self.preview.reset_crop()

    def _on_crop_changed(self, rect: QRect) -> None:
        self.lbl_dims.setText(f"Crop Size: {rect.width()} × {rect.height()} px")

    def _on_apply(self) -> None:
        crop_rect = self.preview.get_image_crop_rect()
        self.cropped_image = crop_image(self.image, crop_rect)
        self.accept()

    def get_cropped_image(self) -> QImage:
        if self.cropped_image is not None:
            return self.cropped_image
        crop_rect = self.preview.get_image_crop_rect()
        return crop_image(self.image, crop_rect)
