"""Procedural paper grain and tactile texture generator for high print fidelity."""

import math
import random
from enum import Enum
from typing import Dict, Optional
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QImage, QPainter, QColor, QPen, QBrush, QPixmap


class TextureType(str, Enum):
    NONE = "None (Smooth Digital)"
    FINE_LINEN = "Fine Linen"
    LAID_COTTON = "Laid Cotton Fiber"
    VINTAGE_PARCHMENT = "Vintage Parchment"
    MINIMALIST_TOOTH = "Minimalist Matte Tooth"
    JAPANESE_WASHI = "Japanese Washi"


class PaperTextureEngine:
    """Generates and caches tileable procedural paper textures with alpha transparency."""

    def __init__(self):
        self._cache: Dict[TextureType, QPixmap] = {}
        self._current_type: TextureType = TextureType.FINE_LINEN
        self._opacity: float = 0.30  # Default subtle elegance

    @property
    def current_type(self) -> TextureType:
        return self._current_type

    @current_type.setter
    def current_type(self, texture_type: TextureType) -> None:
        self._current_type = texture_type

    @property
    def opacity(self) -> float:
        return self._opacity

    @opacity.setter
    def opacity(self, value: float) -> None:
        self._opacity = max(0.0, min(1.0, value))

    def get_texture_pixmap(self, texture_type: Optional[TextureType] = None) -> Optional[QPixmap]:
        t = texture_type or self._current_type
        if t == TextureType.NONE:
            return None

        if t in self._cache:
            return self._cache[t]

        pixmap = self._generate_texture(t)
        self._cache[t] = pixmap
        return pixmap

    def _generate_texture(self, texture_type: TextureType) -> QPixmap:
        width = 256
        height = 256
        image = QImage(width, height, QImage.Format.Format_ARGB32_Premultiplied)
        image.fill(QColor(0, 0, 0, 0))  # Fully transparent base

        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        rng = random.Random(42)  # Deterministic seed for seamless tiling

        if texture_type == TextureType.MINIMALIST_TOOTH:
            self._render_matte_tooth(painter, width, height, rng)
        elif texture_type == TextureType.FINE_LINEN:
            self._render_fine_linen(painter, width, height, rng)
        elif texture_type == TextureType.LAID_COTTON:
            self._render_laid_cotton(painter, width, height, rng)
        elif texture_type == TextureType.VINTAGE_PARCHMENT:
            self._render_parchment(painter, width, height, rng)
        elif texture_type == TextureType.JAPANESE_WASHI:
            self._render_washi(painter, width, height, rng)

        painter.end()
        return QPixmap.fromImage(image)

    def _render_matte_tooth(self, p: QPainter, w: int, h: int, rng: random.Random) -> None:
        # Microscopic paper tooth/grain
        for _ in range(2500):
            x = rng.randint(0, w - 1)
            y = rng.randint(0, h - 1)
            alpha = rng.randint(8, 25)
            # Alternate between subtle dark specks and subtle light highlights
            if rng.random() > 0.4:
                p.setPen(QColor(30, 25, 20, alpha))
            else:
                p.setPen(QColor(255, 255, 255, alpha))
            p.drawPoint(x, y)

    def _render_fine_linen(self, p: QPainter, w: int, h: int, rng: random.Random) -> None:
        # Subtle horizontal and vertical woven thread fibers
        # Horizontal threads
        for y in range(0, h, 3):
            alpha = rng.randint(10, 30)
            pen = QPen(QColor(40, 30, 20, alpha), 1)
            p.setPen(pen)
            p.drawLine(0, y, w, y)

        # Vertical threads
        for x in range(0, w, 3):
            alpha = rng.randint(10, 30)
            pen = QPen(QColor(255, 255, 255, int(alpha * 0.7)), 1)
            p.setPen(pen)
            p.drawLine(x, 0, x, h)

        # Micro fiber flecks
        for _ in range(800):
            x = rng.randint(0, w - 1)
            y = rng.randint(0, h - 1)
            p.setPen(QColor(50, 40, 30, rng.randint(15, 45)))
            p.drawPoint(x, y)

    def _render_laid_cotton(self, p: QPainter, w: int, h: int, rng: random.Random) -> None:
        # Classical watermarked laid paper with parallel chain lines
        for y in range(0, h, 6):
            alpha = rng.randint(12, 28)
            p.setPen(QPen(QColor(60, 45, 30, alpha), 1.2))
            p.drawLine(0, y, w, y)

        # Vertical chain lines spaced wider (every 32px)
        for x in range(0, w, 32):
            p.setPen(QPen(QColor(255, 255, 255, 35), 1.5))
            p.drawLine(x, 0, x, h)

        # Organic cotton pulp fibers
        for _ in range(150):
            x1 = rng.randint(0, w)
            y1 = rng.randint(0, h)
            angle = rng.uniform(0, math.pi * 2)
            length = rng.uniform(3, 10)
            x2 = x1 + math.cos(angle) * length
            y2 = y1 + math.sin(angle) * length
            p.setPen(QPen(QColor(50, 40, 30, rng.randint(20, 50)), 0.8))
            p.drawLine(QPointF(x1, y1), QPointF(x2, y2))

    def _render_parchment(self, p: QPainter, w: int, h: int, rng: random.Random) -> None:
        # Mottled organic depth and aged vellum grain
        # Soft mottled blotches
        for _ in range(60):
            cx = rng.randint(0, w)
            cy = rng.randint(0, h)
            rad = rng.randint(12, 45)
            alpha = rng.randint(8, 22)
            color = QColor(90, 60, 30, alpha) if rng.random() > 0.3 else QColor(255, 250, 230, alpha)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(color))
            p.drawEllipse(QPointF(cx, cy), rad, rad)

        # Fine surface crinkles
        for _ in range(120):
            x1 = rng.randint(0, w)
            y1 = rng.randint(0, h)
            x2 = x1 + rng.randint(-8, 8)
            y2 = y1 + rng.randint(-8, 8)
            p.setPen(QPen(QColor(80, 50, 20, rng.randint(15, 35)), 0.7))
            p.drawLine(x1, y1, x2, y2)

    def _render_washi(self, p: QPainter, w: int, h: int, rng: random.Random) -> None:
        # Long flowing kozo / mulberry fibers
        for _ in range(200):
            x1 = rng.randint(0, w)
            y1 = rng.randint(0, h)
            ctrl_x = x1 + rng.randint(-15, 15)
            ctrl_y = y1 + rng.randint(-15, 15)
            x2 = ctrl_x + rng.randint(-15, 15)
            y2 = ctrl_y + rng.randint(-15, 15)
            alpha = rng.randint(15, 55)
            p.setPen(QPen(QColor(70, 60, 50, alpha), rng.uniform(0.6, 1.4)))
            # Approximate curve with two line segments
            p.drawLine(QPointF(x1, y1), QPointF(ctrl_x, ctrl_y))
            p.drawLine(QPointF(ctrl_x, ctrl_y), QPointF(x2, y2))
