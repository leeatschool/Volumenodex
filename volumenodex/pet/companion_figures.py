"""High-resolution vector illustrated companion figures for the Scribe Companion system.

Renders crisp, resolution-independent portraits for each companion without relying
on unicode emojis that can fail or elide on various Windows font configurations.
"""

from typing import Optional
from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import (
    QPixmap, QPainter, QColor, QPen, QBrush, QPainterPath,
    QLinearGradient, QRadialGradient, QIcon
)
from volumenodex.pet.pet_model import PetMood


class CompanionFigureRenderer:
    """Renders high-fidelity vector portraits for Scribe Companions."""

    @classmethod
    def render_figure(
        cls,
        pet_id: str,
        size: int = 48,
        mood: PetMood = PetMood.IDLE,
        custom_image_path: Optional[str] = None
    ) -> QPixmap:
        """Renders an illustrated circular portrait of the companion."""
        # Handle custom image if provided
        if custom_image_path:
            pix = cls._render_custom_image(custom_image_path, size)
            if pix is not None:
                return pix

        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        s = float(size)

        pet_key = (pet_id or "").lower()
        if "corvus" in pet_key:
            cls._draw_corvus(painter, s, mood)
        elif "quill" in pet_key:
            cls._draw_quill(painter, s, mood)
        elif "ink" in pet_key:
            cls._draw_ink(painter, s, mood)
        elif "scout" in pet_key:
            cls._draw_scout(painter, s, mood)
        elif "ignis" in pet_key:
            cls._draw_ignis(painter, s, mood)
        else:
            cls._draw_quill_scroll(painter, s, mood)

        painter.end()
        return pixmap

    @classmethod
    def render_icon(
        cls,
        pet_id: str,
        size: int = 48,
        mood: PetMood = PetMood.IDLE,
        custom_image_path: Optional[str] = None
    ) -> QIcon:
        """Returns a QIcon wrapping the rendered portrait."""
        return QIcon(cls.render_figure(pet_id, size, mood, custom_image_path))

    @classmethod
    def _render_custom_image(cls, path: str, size: int) -> Optional[QPixmap]:
        src = QPixmap(path)
        if src.isNull():
            return None
        target = QPixmap(size, size)
        target.fill(Qt.GlobalColor.transparent)
        p = QPainter(target)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        clip_path = QPainterPath()
        clip_path.addEllipse(QRectF(1, 1, size - 2, size - 2))
        p.setClipPath(clip_path)

        scaled = src.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
        ox = (scaled.width() - size) // 2
        oy = (scaled.height() - size) // 2
        p.drawPixmap(0, 0, scaled, ox, oy, size, size)

        p.setClipping(False)
        p.setPen(QPen(QColor(122, 162, 247, 180), 1.5))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QRectF(1, 1, size - 2, size - 2))
        p.end()
        return target

    # --- 1. Corvus the Literary Raven ---
    @classmethod
    def _draw_corvus(cls, p: QPainter, s: float, mood: PetMood) -> None:
        # Disc Background
        bg_grad = QRadialGradient(s * 0.4, s * 0.35, s * 0.55)
        bg_grad.setColorAt(0.0, QColor("#1e2238"))
        bg_grad.setColorAt(1.0, QColor("#0e1018"))
        p.setPen(QPen(QColor("#7aa2f7"), 1.5))
        p.setBrush(bg_grad)
        p.drawEllipse(QRectF(1, 1, s - 2, s - 2))

        # Raven Body / Wing (Rich Obsidian with Indigo Highlights)
        body = QPainterPath()
        body.moveTo(s * 0.35, s * 0.88)
        body.cubicTo(s * 0.18, s * 0.70, s * 0.22, s * 0.42, s * 0.38, s * 0.30)
        body.cubicTo(s * 0.45, s * 0.24, s * 0.56, s * 0.22, s * 0.65, s * 0.26)
        body.cubicTo(s * 0.75, s * 0.32, s * 0.72, s * 0.48, s * 0.78, s * 0.65)
        body.cubicTo(s * 0.82, s * 0.75, s * 0.70, s * 0.88, s * 0.55, s * 0.88)
        body.closeSubpath()

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#181a28"))
        p.drawPath(body)

        # Layered Primary Wing Feathers
        wing = QPainterPath()
        wing.moveTo(s * 0.42, s * 0.45)
        wing.quadTo(s * 0.72, s * 0.48, s * 0.76, s * 0.78)
        wing.quadTo(s * 0.55, s * 0.82, s * 0.42, s * 0.62)
        wing.closeSubpath()
        p.setBrush(QColor("#24283b"))
        p.drawPath(wing)

        # Wing Feather Highlights
        p.setPen(QPen(QColor("#7aa2f7"), 1.0, Qt.PenStyle.SolidLine))
        p.drawLine(QPointF(s * 0.48, s * 0.52), QPointF(s * 0.68, s * 0.72))
        p.drawLine(QPointF(s * 0.54, s * 0.55), QPointF(s * 0.70, s * 0.75))

        # Beak (Sharp curved gothic bill)
        p.setPen(Qt.PenStyle.NoPen)
        beak = QPainterPath()
        beak.moveTo(s * 0.62, s * 0.32)
        beak.lineTo(s * 0.88, s * 0.38)
        beak.quadTo(s * 0.76, s * 0.46, s * 0.60, s * 0.42)
        beak.closeSubpath()
        beak_grad = QLinearGradient(s * 0.6, s * 0.35, s * 0.88, s * 0.4)
        beak_grad.setColorAt(0.0, QColor("#414868"))
        beak_grad.setColorAt(1.0, QColor("#24283b"))
        p.setBrush(beak_grad)
        p.drawPath(beak)

        # Throat Feathers / Hackles
        p.setPen(QPen(QColor("#3b4261"), 1.0))
        p.drawLine(QPointF(s * 0.38, s * 0.42), QPointF(s * 0.34, s * 0.52))
        p.drawLine(QPointF(s * 0.36, s * 0.50), QPointF(s * 0.30, s * 0.60))

        # Eye
        if mood == PetMood.SLEEPING:
            p.setPen(QPen(QColor("#c0caf5"), 1.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawArc(QRectF(s * 0.46, s * 0.30, s * 0.12, s * 0.10), 0, 180 * 16)
        else:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor("#0f1017"))
            p.drawEllipse(QRectF(s * 0.48, s * 0.31, s * 0.10, s * 0.10))
            p.setBrush(QColor("#c0caf5"))
            p.drawEllipse(QRectF(s * 0.49, s * 0.32, s * 0.08, s * 0.08))
            p.setBrush(QColor("#1a1b26"))
            p.drawEllipse(QRectF(s * 0.51, s * 0.34, s * 0.04, s * 0.04))
            p.setBrush(QColor("#ffffff"))
            p.drawEllipse(QRectF(s * 0.53, s * 0.33, s * 0.02, s * 0.02))

    # --- 2. Quill the Scholarly Owl ---
    @classmethod
    def _draw_quill(cls, p: QPainter, s: float, mood: PetMood) -> None:
        # Warm Parchment / Mahogany Disc
        bg_grad = QRadialGradient(s * 0.5, s * 0.45, s * 0.55)
        bg_grad.setColorAt(0.0, QColor("#33241c"))
        bg_grad.setColorAt(1.0, QColor("#19120e"))
        p.setPen(QPen(QColor("#e0af68"), 1.5))
        p.setBrush(bg_grad)
        p.drawEllipse(QRectF(1, 1, s - 2, s - 2))

        # Owl Body / Shoulders
        body = QPainterPath()
        body.moveTo(s * 0.22, s * 0.88)
        body.quadTo(s * 0.24, s * 0.50, s * 0.32, s * 0.38)
        body.lineTo(s * 0.68, s * 0.38)
        body.quadTo(s * 0.76, s * 0.50, s * 0.78, s * 0.88)
        body.closeSubpath()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#54392a"))
        p.drawPath(body)

        # Horned Ear Tufts
        ears = QPainterPath()
        ears.moveTo(s * 0.28, s * 0.40)
        ears.lineTo(s * 0.22, s * 0.20)
        ears.lineTo(s * 0.38, s * 0.32)
        ears.moveTo(s * 0.62, s * 0.32)
        ears.lineTo(s * 0.78, s * 0.20)
        ears.lineTo(s * 0.72, s * 0.40)
        p.setBrush(QColor("#402b1f"))
        p.drawPath(ears)

        # Facial Disc (Heart-shaped warm cream mask)
        mask = QPainterPath()
        mask.addEllipse(QRectF(s * 0.24, s * 0.30, s * 0.27, s * 0.28))
        mask.addEllipse(QRectF(s * 0.49, s * 0.30, s * 0.27, s * 0.28))
        p.setBrush(QColor("#d4a373"))
        p.drawPath(mask)

        # Chest Feathers (Warm Cream Bib)
        p.setBrush(QColor("#f2e9e4"))
        chest = QPainterPath()
        chest.moveTo(s * 0.35, s * 0.62)
        chest.quadTo(s * 0.50, s * 0.82, s * 0.65, s * 0.62)
        chest.quadTo(s * 0.50, s * 0.54, s * 0.35, s * 0.62)
        p.drawPath(chest)

        # Chevron Feathers on Chest
        p.setPen(QPen(QColor("#8c6245"), 1.0))
        p.drawPolyline([QPointF(s * 0.44, s * 0.66), QPointF(s * 0.50, s * 0.70), QPointF(s * 0.56, s * 0.66)])
        p.drawPolyline([QPointF(s * 0.46, s * 0.73), QPointF(s * 0.50, s * 0.76), QPointF(s * 0.54, s * 0.73)])

        # Small Hooked Beak
        p.setPen(Qt.PenStyle.NoPen)
        beak = QPainterPath()
        beak.moveTo(s * 0.46, s * 0.44)
        beak.lineTo(s * 0.54, s * 0.44)
        beak.lineTo(s * 0.50, s * 0.56)
        beak.closeSubpath()
        p.setBrush(QColor("#e0af68"))
        p.drawPath(beak)

        # Huge Scholarly Golden Eyes
        if mood == PetMood.SLEEPING:
            p.setPen(QPen(QColor("#e0af68"), 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawArc(QRectF(s * 0.28, s * 0.36, s * 0.16, s * 0.12), 0, 180 * 16)
            p.drawArc(QRectF(s * 0.56, s * 0.36, s * 0.16, s * 0.12), 0, 180 * 16)
        else:
            # Left eye
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor("#241c16"))
            p.drawEllipse(QRectF(s * 0.27, s * 0.33, s * 0.19, s * 0.19))
            p.setBrush(QColor("#f6c177"))
            p.drawEllipse(QRectF(s * 0.29, s * 0.35, s * 0.15, s * 0.15))
            p.setBrush(QColor("#181411"))
            p.drawEllipse(QRectF(s * 0.32, s * 0.38, s * 0.09, s * 0.09))
            p.setBrush(QColor("#ffffff"))
            p.drawEllipse(QRectF(s * 0.36, s * 0.37, s * 0.035, s * 0.035))

            # Right eye
            p.setBrush(QColor("#241c16"))
            p.drawEllipse(QRectF(s * 0.54, s * 0.33, s * 0.19, s * 0.19))
            p.setBrush(QColor("#f6c177"))
            p.drawEllipse(QRectF(s * 0.56, s * 0.35, s * 0.15, s * 0.15))
            p.setBrush(QColor("#181411"))
            p.drawEllipse(QRectF(s * 0.59, s * 0.38, s * 0.09, s * 0.09))
            p.setBrush(QColor("#ffffff"))
            p.drawEllipse(QRectF(s * 0.63, s * 0.37, s * 0.035, s * 0.035))

    # --- 3. Ink the Cozy Cat ---
    @classmethod
    def _draw_ink(cls, p: QPainter, s: float, mood: PetMood) -> None:
        bg_grad = QRadialGradient(s * 0.5, s * 0.45, s * 0.55)
        bg_grad.setColorAt(0.0, QColor("#1e2b2c"))
        bg_grad.setColorAt(1.0, QColor("#0d1416"))
        p.setPen(QPen(QColor("#73daca"), 1.5))
        p.setBrush(bg_grad)
        p.drawEllipse(QRectF(1, 1, s - 2, s - 2))

        # Cat Head Silhouette (Charcoal / Tuxedo)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#1a1c24"))

        # Ears
        ears = QPainterPath()
        ears.moveTo(s * 0.24, s * 0.42)
        ears.lineTo(s * 0.18, s * 0.18)
        ears.lineTo(s * 0.40, s * 0.32)
        ears.moveTo(s * 0.60, s * 0.32)
        ears.lineTo(s * 0.82, s * 0.18)
        ears.lineTo(s * 0.76, s * 0.42)
        p.drawPath(ears)

        # Inner Ear Pink Glow
        p.setBrush(QColor("#f7768e"))
        p.setOpacity(0.65)
        inner_ears = QPainterPath()
        inner_ears.moveTo(s * 0.25, s * 0.38)
        inner_ears.lineTo(s * 0.22, s * 0.24)
        inner_ears.lineTo(s * 0.35, s * 0.34)
        inner_ears.moveTo(s * 0.65, s * 0.34)
        inner_ears.lineTo(s * 0.78, s * 0.24)
        inner_ears.lineTo(s * 0.75, s * 0.38)
        p.drawPath(inner_ears)
        p.setOpacity(1.0)

        # Head & Cheeks
        head = QPainterPath()
        head.addEllipse(QRectF(s * 0.22, s * 0.28, s * 0.56, s * 0.50))
        p.setBrush(QColor("#1a1c24"))
        p.drawPath(head)

        # White Chest / Bib
        p.setBrush(QColor("#e5e9f0"))
        bib = QPainterPath()
        bib.moveTo(s * 0.40, s * 0.72)
        bib.lineTo(s * 0.50, s * 0.88)
        bib.lineTo(s * 0.60, s * 0.72)
        bib.closeSubpath()
        p.drawPath(bib)

        # Nose (Cute little pink triangle)
        p.setBrush(QColor("#f7768e"))
        nose = QPainterPath()
        nose.moveTo(s * 0.47, s * 0.54)
        nose.lineTo(s * 0.53, s * 0.54)
        nose.lineTo(s * 0.50, s * 0.58)
        nose.closeSubpath()
        p.drawPath(nose)

        # Whiskers
        p.setPen(QPen(QColor(255, 255, 255, 110), 0.8))
        p.drawLine(QPointF(s * 0.44, s * 0.58), QPointF(s * 0.16, s * 0.54))
        p.drawLine(QPointF(s * 0.44, s * 0.61), QPointF(s * 0.18, s * 0.65))
        p.drawLine(QPointF(s * 0.56, s * 0.58), QPointF(s * 0.84, s * 0.54))
        p.drawLine(QPointF(s * 0.56, s * 0.61), QPointF(s * 0.82, s * 0.65))

        # Almond Emerald Eyes
        if mood == PetMood.SLEEPING:
            p.setPen(QPen(QColor("#73daca"), 1.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawArc(QRectF(s * 0.28, s * 0.42, s * 0.14, s * 0.08), 0, 180 * 16)
            p.drawArc(QRectF(s * 0.58, s * 0.42, s * 0.14, s * 0.08), 0, 180 * 16)
        else:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor("#73daca"))
            p.drawEllipse(QRectF(s * 0.28, s * 0.39, s * 0.15, s * 0.12))
            p.drawEllipse(QRectF(s * 0.57, s * 0.39, s * 0.15, s * 0.12))

            p.setBrush(QColor("#111318"))
            p.drawEllipse(QRectF(s * 0.34, s * 0.40, s * 0.04, s * 0.10))
            p.drawEllipse(QRectF(s * 0.62, s * 0.40, s * 0.04, s * 0.10))

            p.setBrush(QColor("#ffffff"))
            p.drawEllipse(QRectF(s * 0.37, s * 0.41, s * 0.03, s * 0.03))
            p.drawEllipse(QRectF(s * 0.65, s * 0.41, s * 0.03, s * 0.03))

    # --- 4. Scout the Loyal Hound ---
    @classmethod
    def _draw_scout(cls, p: QPainter, s: float, mood: PetMood) -> None:
        bg_grad = QRadialGradient(s * 0.5, s * 0.45, s * 0.55)
        bg_grad.setColorAt(0.0, QColor("#382717"))
        bg_grad.setColorAt(1.0, QColor("#1a110a"))
        p.setPen(QPen(QColor("#ff9e64"), 1.5))
        p.setBrush(bg_grad)
        p.drawEllipse(QRectF(1, 1, s - 2, s - 2))

        # Floppy Ears
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#85542f"))
        ears = QPainterPath()
        ears.moveTo(s * 0.26, s * 0.32)
        ears.cubicTo(s * 0.10, s * 0.45, s * 0.14, s * 0.72, s * 0.28, s * 0.68)
        ears.moveTo(s * 0.74, s * 0.32)
        ears.cubicTo(s * 0.90, s * 0.45, s * 0.86, s * 0.72, s * 0.72, s * 0.68)
        p.drawPath(ears)

        # Head
        head = QPainterPath()
        head.addEllipse(QRectF(s * 0.24, s * 0.24, s * 0.52, s * 0.52))
        p.setBrush(QColor("#d19a66"))
        p.drawPath(head)

        # Muzzle
        snout = QPainterPath()
        snout.addEllipse(QRectF(s * 0.35, s * 0.46, s * 0.30, s * 0.28))
        p.setBrush(QColor("#edd7be"))
        p.drawPath(snout)

        # Black Button Nose
        p.setBrush(QColor("#242220"))
        nose = QPainterPath()
        nose.moveTo(s * 0.44, s * 0.50)
        nose.lineTo(s * 0.56, s * 0.50)
        nose.quadTo(s * 0.50, s * 0.60, s * 0.44, s * 0.50)
        p.drawPath(nose)

        p.setBrush(QColor("#ffffff"))
        p.drawEllipse(QRectF(s * 0.46, s * 0.51, s * 0.03, s * 0.02))

        # Smile Line
        p.setPen(QPen(QColor("#593a20"), 1.2))
        p.drawLine(QPointF(s * 0.50, s * 0.58), QPointF(s * 0.50, s * 0.64))
        p.drawArc(QRectF(s * 0.44, s * 0.60, s * 0.12, s * 0.08), 180 * 16, 180 * 16)

        # Loyal Warm Eyes
        if mood == PetMood.SLEEPING:
            p.setPen(QPen(QColor("#85542f"), 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawArc(QRectF(s * 0.31, s * 0.36, s * 0.12, s * 0.08), 0, 180 * 16)
            p.drawArc(QRectF(s * 0.57, s * 0.36, s * 0.12, s * 0.08), 0, 180 * 16)
        else:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor("#2a180f"))
            p.drawEllipse(QRectF(s * 0.31, s * 0.34, s * 0.13, s * 0.13))
            p.drawEllipse(QRectF(s * 0.56, s * 0.34, s * 0.13, s * 0.13))
            p.setBrush(QColor("#ffffff"))
            p.drawEllipse(QRectF(s * 0.34, s * 0.35, s * 0.045, s * 0.045))
            p.drawEllipse(QRectF(s * 0.59, s * 0.35, s * 0.045, s * 0.045))

    # --- 5. Ignis the Miniature Dragon ---
    @classmethod
    def _draw_ignis(cls, p: QPainter, s: float, mood: PetMood) -> None:
        bg_grad = QRadialGradient(s * 0.5, s * 0.45, s * 0.55)
        bg_grad.setColorAt(0.0, QColor("#3d1c28"))
        bg_grad.setColorAt(1.0, QColor("#180a10"))
        p.setPen(QPen(QColor("#f7768e"), 1.5))
        p.setBrush(bg_grad)
        p.drawEllipse(QRectF(1, 1, s - 2, s - 2))

        # Golden Horns
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#e0af68"))
        horns = QPainterPath()
        horns.moveTo(s * 0.34, s * 0.32)
        horns.quadTo(s * 0.22, s * 0.14, s * 0.14, s * 0.18)
        horns.quadTo(s * 0.24, s * 0.26, s * 0.38, s * 0.38)
        horns.moveTo(s * 0.60, s * 0.32)
        horns.quadTo(s * 0.76, s * 0.14, s * 0.86, s * 0.18)
        horns.quadTo(s * 0.74, s * 0.26, s * 0.58, s * 0.38)
        p.drawPath(horns)

        # Dragon Head
        head = QPainterPath()
        head.moveTo(s * 0.36, s * 0.82)
        head.cubicTo(s * 0.20, s * 0.70, s * 0.26, s * 0.38, s * 0.44, s * 0.30)
        head.lineTo(s * 0.68, s * 0.30)
        head.cubicTo(s * 0.84, s * 0.46, s * 0.80, s * 0.74, s * 0.62, s * 0.82)
        head.closeSubpath()
        p.setBrush(QColor("#bb9af7"))
        p.drawPath(head)

        # Underbelly Plate
        belly = QPainterPath()
        belly.moveTo(s * 0.40, s * 0.64)
        belly.quadTo(s * 0.50, s * 0.84, s * 0.60, s * 0.64)
        belly.closeSubpath()
        p.setBrush(QColor("#ff9e64"))
        p.drawPath(belly)

        # Nostrils
        p.setBrush(QColor("#24141e"))
        p.drawEllipse(QRectF(s * 0.44, s * 0.58, s * 0.03, s * 0.03))
        p.drawEllipse(QRectF(s * 0.53, s * 0.58, s * 0.03, s * 0.03))

        # Flame Spark
        flame = QPainterPath()
        flame.moveTo(s * 0.50, s * 0.48)
        flame.quadTo(s * 0.55, s * 0.38, s * 0.48, s * 0.32)
        flame.quadTo(s * 0.42, s * 0.40, s * 0.50, s * 0.48)
        p.setBrush(QColor("#ff7a93"))
        p.drawPath(flame)

        # Fiery Eye
        if mood == PetMood.SLEEPING:
            p.setPen(QPen(QColor("#ff9e64"), 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawArc(QRectF(s * 0.34, s * 0.38, s * 0.12, s * 0.08), 0, 180 * 16)
            p.drawArc(QRectF(s * 0.54, s * 0.38, s * 0.12, s * 0.08), 0, 180 * 16)
        else:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor("#ff9e64"))
            p.drawEllipse(QRectF(s * 0.32, s * 0.36, s * 0.14, s * 0.14))
            p.drawEllipse(QRectF(s * 0.54, s * 0.36, s * 0.14, s * 0.14))
            p.setBrush(QColor("#180a10"))
            p.drawEllipse(QRectF(s * 0.37, s * 0.37, s * 0.035, s * 0.12))
            p.drawEllipse(QRectF(s * 0.59, s * 0.37, s * 0.035, s * 0.12))

    # --- 6. Fallback Quill & Scroll Crest ---
    @classmethod
    def _draw_quill_scroll(cls, p: QPainter, s: float, mood: PetMood) -> None:
        bg_grad = QRadialGradient(s * 0.5, s * 0.45, s * 0.55)
        bg_grad.setColorAt(0.0, QColor("#1e2238"))
        bg_grad.setColorAt(1.0, QColor("#0e1018"))
        p.setPen(QPen(QColor("#7aa2f7"), 1.5))
        p.setBrush(bg_grad)
        p.drawEllipse(QRectF(1, 1, s - 2, s - 2))

        # Scroll
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#e0af68"))
        p.drawRoundedRect(QRectF(s * 0.25, s * 0.35, s * 0.50, s * 0.38), 3, 3)

        # Quill
        quill = QPainterPath()
        quill.moveTo(s * 0.72, s * 0.18)
        quill.quadTo(s * 0.55, s * 0.38, s * 0.38, s * 0.72)
        quill.quadTo(s * 0.48, s * 0.52, s * 0.72, s * 0.18)
        p.setBrush(QColor("#7aa2f7"))
        p.drawPath(quill)

        p.setPen(QPen(QColor("#ffffff"), 1.0))
        p.drawLine(QPointF(s * 0.72, s * 0.18), QPointF(s * 0.36, s * 0.74))
