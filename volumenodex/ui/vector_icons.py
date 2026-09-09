"""High-fidelity vector icon renderer for the Modern Fluent Ribbon and UI chrome."""

from typing import Dict, Tuple
from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import (
    QIcon, QPixmap, QPainter, QColor, QPen, QBrush, QPainterPath, QFont
)


class VectorIconFactory:
    """Renders crisp, resolution-independent vector icons using QPainterPath."""

    @staticmethod
    def create_icon(icon_name: str, color: str = "#c0caf5", size: int = 20) -> QIcon:
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        pen = QPen(QColor(color), 1.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        s = float(size)

        if icon_name == "cut":
            # Scissor blades and finger loops
            # Top blade
            painter.drawLine(QPointF(s * 0.25, s * 0.35), QPointF(s * 0.8, s * 0.75))
            # Bottom blade
            painter.drawLine(QPointF(s * 0.25, s * 0.65), QPointF(s * 0.8, s * 0.25))
            # Rings
            painter.drawEllipse(QRectF(s * 0.12, s * 0.22, s * 0.25, s * 0.25))
            painter.drawEllipse(QRectF(s * 0.12, s * 0.53, s * 0.25, s * 0.25))

        elif icon_name == "copy":
            # Two overlapping rectangles
            painter.drawRoundedRect(QRectF(s * 0.15, s * 0.15, s * 0.5, s * 0.6), 2, 2)
            painter.drawRoundedRect(QRectF(s * 0.35, s * 0.3, s * 0.5, s * 0.6), 2, 2)

        elif icon_name == "paste":
            # Clipboard with paper sheet
            painter.drawRoundedRect(QRectF(s * 0.2, s * 0.22, s * 0.6, s * 0.7), 2, 2)
            # Clip at top
            painter.fillRect(QRectF(s * 0.35, s * 0.1, s * 0.3, s * 0.18), QColor(color))
            # Document lines
            painter.drawLine(QPointF(s * 0.32, s * 0.45), QPointF(s * 0.68, s * 0.45))
            painter.drawLine(QPointF(s * 0.32, s * 0.6), QPointF(s * 0.68, s * 0.6))
            painter.drawLine(QPointF(s * 0.32, s * 0.75), QPointF(s * 0.55, s * 0.75))

        elif icon_name in ("paste_plain", "paste_text"):
            # Clipboard with prominent 'T' for plain text
            painter.drawRoundedRect(QRectF(s * 0.2, s * 0.22, s * 0.6, s * 0.7), 2, 2)
            painter.fillRect(QRectF(s * 0.35, s * 0.1, s * 0.3, s * 0.18), QColor(color))
            font = QFont("Segoe UI", int(s * 0.38), QFont.Weight.Bold)
            painter.setFont(font)
            painter.drawText(QRectF(s * 0.2, s * 0.28, s * 0.6, s * 0.60), Qt.AlignmentFlag.AlignCenter, "T")

        elif icon_name == "bold":
            font = QFont("Segoe UI", int(s * 0.65), QFont.Weight.Bold)
            painter.setFont(font)
            painter.drawText(QRectF(0, 0, s, s), Qt.AlignmentFlag.AlignCenter, "B")

        elif icon_name == "italic":
            font = QFont("Georgia", int(s * 0.65), QFont.Weight.Normal)
            font.setItalic(True)
            painter.setFont(font)
            painter.drawText(QRectF(0, 0, s, s), Qt.AlignmentFlag.AlignCenter, "I")

        elif icon_name == "underline":
            font = QFont("Segoe UI", int(s * 0.6), QFont.Weight.Medium)
            painter.setFont(font)
            painter.drawText(QRectF(0, -2, s, s), Qt.AlignmentFlag.AlignCenter, "U")
            painter.drawLine(QPointF(s * 0.25, s * 0.85), QPointF(s * 0.75, s * 0.85))

        elif icon_name == "strike":
            font = QFont("Segoe UI", int(s * 0.6), QFont.Weight.Medium)
            painter.setFont(font)
            painter.drawText(QRectF(0, 0, s, s), Qt.AlignmentFlag.AlignCenter, "S")
            painter.drawLine(QPointF(s * 0.18, s * 0.5), QPointF(s * 0.82, s * 0.5))

        elif icon_name == "text_color":
            font = QFont("Segoe UI", int(s * 0.58), QFont.Weight.Bold)
            painter.setFont(font)
            painter.drawText(QRectF(0, -2, s, s), Qt.AlignmentFlag.AlignCenter, "A")
            # Color bar beneath
            painter.fillRect(QRectF(s * 0.2, s * 0.82, s * 0.6, s * 0.12), QColor("#7aa2f7"))

        elif icon_name == "highlight":
            # Highlighter marker tip
            path = QPainterPath()
            path.moveTo(s * 0.3, s * 0.7)
            path.lineTo(s * 0.7, s * 0.3)
            path.lineTo(s * 0.85, s * 0.45)
            path.lineTo(s * 0.45, s * 0.85)
            path.closeSubpath()
            painter.drawPath(path)
            painter.fillRect(QRectF(s * 0.15, s * 0.85, s * 0.7, s * 0.1), QColor("#e0af68"))

        elif icon_name == "align_left":
            painter.drawLine(QPointF(s * 0.15, s * 0.25), QPointF(s * 0.85, s * 0.25))
            painter.drawLine(QPointF(s * 0.15, s * 0.45), QPointF(s * 0.65, s * 0.45))
            painter.drawLine(QPointF(s * 0.15, s * 0.65), QPointF(s * 0.85, s * 0.65))
            painter.drawLine(QPointF(s * 0.15, s * 0.85), QPointF(s * 0.5, s * 0.85))

        elif icon_name == "align_center":
            painter.drawLine(QPointF(s * 0.15, s * 0.25), QPointF(s * 0.85, s * 0.25))
            painter.drawLine(QPointF(s * 0.25, s * 0.45), QPointF(s * 0.75, s * 0.45))
            painter.drawLine(QPointF(s * 0.15, s * 0.65), QPointF(s * 0.85, s * 0.65))
            painter.drawLine(QPointF(s * 0.3, s * 0.85), QPointF(s * 0.7, s * 0.85))

        elif icon_name == "align_right":
            painter.drawLine(QPointF(s * 0.15, s * 0.25), QPointF(s * 0.85, s * 0.25))
            painter.drawLine(QPointF(s * 0.35, s * 0.45), QPointF(s * 0.85, s * 0.45))
            painter.drawLine(QPointF(s * 0.15, s * 0.65), QPointF(s * 0.85, s * 0.65))
            painter.drawLine(QPointF(s * 0.5, s * 0.85), QPointF(s * 0.85, s * 0.85))

        elif icon_name == "align_justify":
            painter.drawLine(QPointF(s * 0.15, s * 0.25), QPointF(s * 0.85, s * 0.25))
            painter.drawLine(QPointF(s * 0.15, s * 0.45), QPointF(s * 0.85, s * 0.45))
            painter.drawLine(QPointF(s * 0.15, s * 0.65), QPointF(s * 0.85, s * 0.65))
            painter.drawLine(QPointF(s * 0.15, s * 0.85), QPointF(s * 0.85, s * 0.85))

        elif icon_name == "bullet_list":
            for y in [0.28, 0.52, 0.76]:
                painter.fillRect(QRectF(s * 0.15, s * y - 2, 4, 4), QColor(color))
                painter.drawLine(QPointF(s * 0.35, s * y), QPointF(s * 0.85, s * y))

        elif icon_name == "numbered_list":
            font = QFont("Segoe UI", int(s * 0.28), QFont.Weight.Bold)
            painter.setFont(font)
            for idx, y in enumerate([0.3, 0.55, 0.8]):
                painter.drawText(QRectF(s * 0.1, s * y - 8, 12, 12), Qt.AlignmentFlag.AlignCenter, str(idx + 1))
                painter.drawLine(QPointF(s * 0.38, s * y - 2), QPointF(s * 0.85, s * y - 2))

        elif icon_name == "page_break":
            # Sheet cut in half with scissors/dashed line
            painter.drawRoundedRect(QRectF(s * 0.2, s * 0.1, s * 0.6, s * 0.8), 2, 2)
            dash_pen = QPen(QColor("#7aa2f7"), 1.5, Qt.PenStyle.DashLine)
            painter.setPen(dash_pen)
            painter.drawLine(QPointF(s * 0.1, s * 0.5), QPointF(s * 0.9, s * 0.5))

        elif icon_name == "corkboard":
            # Corkboard grid with 2 pinned cards
            painter.drawRoundedRect(QRectF(s * 0.1, s * 0.1, s * 0.8, s * 0.8), 2, 2)
            painter.drawRoundedRect(QRectF(s * 0.2, s * 0.22, s * 0.25, s * 0.3), 1, 1)
            painter.drawRoundedRect(QRectF(s * 0.55, s * 0.35, s * 0.25, s * 0.3), 1, 1)

        elif icon_name == "raven":
            # Elegant Raven / Feather quill silhouette
            path = QPainterPath()
            path.moveTo(s * 0.8, s * 0.15)
            path.quadTo(s * 0.3, s * 0.3, s * 0.2, s * 0.85)
            path.quadTo(s * 0.5, s * 0.6, s * 0.8, s * 0.15)
            painter.setBrush(QBrush(QColor(color)))
            painter.drawPath(path)
            # Quill shaft
            painter.drawLine(QPointF(s * 0.8, s * 0.15), QPointF(s * 0.15, s * 0.9))

        elif icon_name == "zen":
            # Minimalist expand / focus frame
            painter.drawPolyline([
                QPointF(s * 0.15, s * 0.35), QPointF(s * 0.15, s * 0.15), QPointF(s * 0.35, s * 0.15)
            ])
            painter.drawPolyline([
                QPointF(s * 0.85, s * 0.35), QPointF(s * 0.85, s * 0.15), QPointF(s * 0.65, s * 0.15)
            ])
            painter.drawPolyline([
                QPointF(s * 0.15, s * 0.65), QPointF(s * 0.15, s * 0.85), QPointF(s * 0.35, s * 0.85)
            ])
            painter.drawPolyline([
                QPointF(s * 0.85, s * 0.65), QPointF(s * 0.85, s * 0.85), QPointF(s * 0.65, s * 0.85)
            ])

        elif icon_name == "stats":
            # Professional analytics bar graph
            painter.fillRect(QRectF(s * 0.2, s * 0.6, s * 0.12, s * 0.25), QColor(color))
            painter.fillRect(QRectF(s * 0.44, s * 0.35, s * 0.12, s * 0.5), QColor("#7aa2f7"))
            painter.fillRect(QRectF(s * 0.68, s * 0.2, s * 0.12, s * 0.65), QColor(color))
            painter.drawLine(QPointF(s * 0.12, s * 0.88), QPointF(s * 0.88, s * 0.88))

        elif icon_name in ("prompt", "lightbulb"):
            # Crisp vector lightbulb
            painter.drawEllipse(QRectF(s * 0.26, s * 0.14, s * 0.48, s * 0.46))
            painter.drawRoundedRect(QRectF(s * 0.36, s * 0.58, s * 0.28, s * 0.14), 2, 2)
            painter.drawLine(QPointF(s * 0.40, s * 0.76), QPointF(s * 0.60, s * 0.76))
            # Filament spark
            painter.drawLine(QPointF(s * 0.50, s * 0.30), QPointF(s * 0.50, s * 0.44))

        elif icon_name in ("timer", "clock"):
            # Crisp stopwatch / clock
            painter.drawEllipse(QRectF(s * 0.16, s * 0.18, s * 0.68, s * 0.68))
            painter.drawLine(QPointF(s * 0.42, s * 0.10), QPointF(s * 0.58, s * 0.10))
            painter.drawLine(QPointF(s * 0.50, s * 0.10), QPointF(s * 0.50, s * 0.18))
            # Clock hands
            painter.drawLine(QPointF(s * 0.50, s * 0.52), QPointF(s * 0.50, s * 0.34))
            painter.drawLine(QPointF(s * 0.50, s * 0.52), QPointF(s * 0.66, s * 0.52))

        elif icon_name in ("snooze", "moon"):
            # Crisp crescent moon
            path = QPainterPath()
            path.moveTo(s * 0.65, s * 0.16)
            path.cubicTo(s * 0.28, s * 0.22, s * 0.24, s * 0.78, s * 0.65, s * 0.84)
            path.cubicTo(s * 0.42, s * 0.70, s * 0.42, s * 0.30, s * 0.65, s * 0.16)
            path.closeSubpath()
            painter.setBrush(QBrush(QColor(color)))
            painter.drawPath(path)

        elif icon_name in ("settings", "gear"):
            # Crisp mechanical gear
            painter.drawEllipse(QRectF(s * 0.20, s * 0.20, s * 0.60, s * 0.60))
            painter.drawEllipse(QRectF(s * 0.38, s * 0.38, s * 0.24, s * 0.24))
            # 4 gear teeth pegs
            painter.drawLine(QPointF(s * 0.50, s * 0.10), QPointF(s * 0.50, s * 0.20))
            painter.drawLine(QPointF(s * 0.50, s * 0.80), QPointF(s * 0.50, s * 0.90))
            painter.drawLine(QPointF(s * 0.10, s * 0.50), QPointF(s * 0.20, s * 0.50))
            painter.drawLine(QPointF(s * 0.80, s * 0.50), QPointF(s * 0.90, s * 0.50))

        elif icon_name in ("close", "hide", "dismiss"):
            # Crisp dismissal cross
            painter.drawLine(QPointF(s * 0.25, s * 0.25), QPointF(s * 0.75, s * 0.75))
            painter.drawLine(QPointF(s * 0.75, s * 0.25), QPointF(s * 0.25, s * 0.75))

        elif icon_name in ("navigator", "outline"):
            # Hierarchical document outline tree
            painter.drawRect(QRectF(s * 0.15, s * 0.20, s * 0.18, s * 0.18))
            painter.drawLine(QPointF(s * 0.42, s * 0.29), QPointF(s * 0.85, s * 0.29))
            painter.drawRect(QRectF(s * 0.26, s * 0.45, s * 0.14, s * 0.14))
            painter.drawLine(QPointF(s * 0.48, s * 0.52), QPointF(s * 0.85, s * 0.52))
            painter.drawRect(QRectF(s * 0.26, s * 0.68, s * 0.14, s * 0.14))
            painter.drawLine(QPointF(s * 0.48, s * 0.75), QPointF(s * 0.85, s * 0.75))

        elif icon_name in ("codex", "character"):
            # Character portrait bust
            painter.drawEllipse(QRectF(s * 0.35, s * 0.18, s * 0.30, s * 0.30))
            painter.drawArc(QRectF(s * 0.20, s * 0.52, s * 0.60, s * 0.38), 0, 180 * 16)

        elif icon_name == "lore":
            # World Lore Globe
            painter.drawEllipse(QRectF(s * 0.18, s * 0.18, s * 0.64, s * 0.64))
            painter.drawLine(QPointF(s * 0.18, s * 0.50), QPointF(s * 0.82, s * 0.50))
            painter.drawArc(QRectF(s * 0.30, s * 0.18, s * 0.40, s * 0.64), 0, 360 * 16)

        elif icon_name in ("plus", "add"):
            painter.drawLine(QPointF(s * 0.50, s * 0.20), QPointF(s * 0.50, s * 0.80))
            painter.drawLine(QPointF(s * 0.20, s * 0.50), QPointF(s * 0.80, s * 0.50))

        elif icon_name == "search":
            painter.drawEllipse(QRectF(s * 0.18, s * 0.18, s * 0.44, s * 0.44))
            painter.drawLine(QPointF(s * 0.52, s * 0.52), QPointF(s * 0.82, s * 0.82))

        elif icon_name == "arrow_up":
            painter.drawPolyline([QPointF(s * 0.25, s * 0.62), QPointF(s * 0.50, s * 0.32), QPointF(s * 0.75, s * 0.62)])

        elif icon_name == "arrow_down":
            painter.drawPolyline([QPointF(s * 0.25, s * 0.38), QPointF(s * 0.50, s * 0.68), QPointF(s * 0.75, s * 0.38)])

        elif icon_name == "chevron_left":
            painter.drawPolyline([QPointF(s * 0.65, s * 0.25), QPointF(s * 0.35, s * 0.50), QPointF(s * 0.65, s * 0.75)])

        elif icon_name == "chevron_right":
            painter.drawPolyline([QPointF(s * 0.35, s * 0.25), QPointF(s * 0.65, s * 0.50), QPointF(s * 0.35, s * 0.75)])

        elif icon_name in ("citation", "quotes"):
            # Crisp quotation marks
            # Left quote
            painter.drawArc(QRectF(s * 0.20, s * 0.28, s * 0.24, s * 0.24), 0, 360 * 16)
            painter.drawLine(QPointF(s * 0.22, s * 0.46), QPointF(s * 0.16, s * 0.65))
            # Right quote
            painter.drawArc(QRectF(s * 0.55, s * 0.28, s * 0.24, s * 0.24), 0, 360 * 16)
            painter.drawLine(QPointF(s * 0.57, s * 0.46), QPointF(s * 0.51, s * 0.65))

        elif icon_name in ("book", "library"):
            # Open book pages
            # Left page
            p_left = QPainterPath()
            p_left.moveTo(s * 0.50, s * 0.30)
            p_left.quadTo(s * 0.32, s * 0.24, s * 0.15, s * 0.28)
            p_left.lineTo(s * 0.15, s * 0.75)
            p_left.quadTo(s * 0.32, s * 0.71, s * 0.50, s * 0.77)
            p_left.closeSubpath()
            painter.drawPath(p_left)
            # Right page
            p_right = QPainterPath()
            p_right.moveTo(s * 0.50, s * 0.30)
            p_right.quadTo(s * 0.68, s * 0.24, s * 0.85, s * 0.28)
            p_right.lineTo(s * 0.85, s * 0.75)
            p_right.quadTo(s * 0.68, s * 0.71, s * 0.50, s * 0.77)
            p_right.closeSubpath()
            painter.drawPath(p_right)

        elif icon_name in ("academic", "mortarboard", "scholar"):
            # Mortarboard cap
            cap = QPainterPath()
            cap.moveTo(s * 0.50, s * 0.22)
            cap.lineTo(s * 0.88, s * 0.38)
            cap.lineTo(s * 0.50, s * 0.54)
            cap.lineTo(s * 0.12, s * 0.38)
            cap.closeSubpath()
            painter.drawPath(cap)
            # Skull cap skull base
            painter.drawArc(QRectF(s * 0.28, s * 0.44, s * 0.44, s * 0.30), 180 * 16, 180 * 16)
            # Tassel
            painter.drawLine(QPointF(s * 0.82, s * 0.40), QPointF(s * 0.84, s * 0.68))

        elif icon_name in ("image", "picture", "photo"):
            # Clean photo frame with landscape mountain and sun
            painter.drawRoundedRect(QRectF(s * 0.15, s * 0.18, s * 0.70, s * 0.64), 2, 2)
            # Sun
            painter.drawEllipse(QRectF(s * 0.28, s * 0.28, s * 0.14, s * 0.14))
            # Mountains
            p_mtn = QPainterPath()
            p_mtn.moveTo(s * 0.15, s * 0.70)
            p_mtn.lineTo(s * 0.42, s * 0.44)
            p_mtn.lineTo(s * 0.62, s * 0.62)
            p_mtn.lineTo(s * 0.74, s * 0.50)
            p_mtn.lineTo(s * 0.85, s * 0.65)
            painter.drawPath(p_mtn)

        elif icon_name in ("clipart", "clip_art", "art"):
            # Painter palette with thumb hole and brush
            p_pal = QPainterPath()
            p_pal.addEllipse(QRectF(s * 0.15, s * 0.18, s * 0.70, s * 0.64))
            painter.drawPath(p_pal)
            # Thumb hole
            painter.drawEllipse(QRectF(s * 0.60, s * 0.52, s * 0.14, s * 0.14))
            # 3 paint spots
            painter.drawEllipse(QRectF(s * 0.28, s * 0.32, s * 0.08, s * 0.08))
            painter.drawEllipse(QRectF(s * 0.46, s * 0.26, s * 0.08, s * 0.08))
            painter.drawEllipse(QRectF(s * 0.32, s * 0.52, s * 0.08, s * 0.08))

        else:
            # Generic fallback document icon
            painter.drawRoundedRect(QRectF(s * 0.2, s * 0.15, s * 0.6, s * 0.7), 2, 2)
            painter.drawLine(QPointF(s * 0.35, s * 0.35), QPointF(s * 0.65, s * 0.35))
            painter.drawLine(QPointF(s * 0.35, s * 0.5), QPointF(s * 0.65, s * 0.5))

        painter.end()
        return QIcon(pixmap)
