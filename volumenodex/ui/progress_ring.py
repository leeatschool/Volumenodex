"""Daily Word Count Goal Circular Progress Ring Widget."""

import math
from PySide6.QtCore import Qt, Signal, QRectF, QSize
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont
from PySide6.QtWidgets import QWidget, QInputDialog


class DailyGoalProgressRing(QWidget):
    """Circular progress meter showing daily words typed towards author's goal."""

    goalAdjusted = Signal(int)

    def __init__(self, current_words: int = 0, goal_words: int = 1000, parent=None):
        super().__init__(parent)
        self._current_words = max(0, current_words)
        self._goal_words = max(1, goal_words)
        self.setFixedSize(140, 26)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._update_tooltip()

    def set_progress(self, current: int, goal: int = None) -> None:
        self._current_words = max(0, current)
        if goal is not None and goal > 0:
            self._goal_words = goal
        self._update_tooltip()
        self.update()

    @property
    def current_words(self) -> int:
        return self._current_words

    @property
    def goal_words(self) -> int:
        return self._goal_words

    def _update_tooltip(self) -> None:
        pct = int(min(100.0, (self._current_words / self._goal_words) * 100.0))
        self.setToolTip(
            f"Daily Writing Target: {self._current_words:,} / {self._goal_words:,} words ({pct}%)\n"
            "Click to adjust your daily word count goal."
        )

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            new_goal, ok = QInputDialog.getInt(
                self,
                "Daily Word Goal",
                "Set your daily word count target:",
                value=self._goal_words,
                minValue=50,
                maxValue=50000,
                step=250,
            )
            if ok and new_goal > 0:
                self._goal_words = new_goal
                self._update_tooltip()
                self.goalAdjusted.emit(new_goal)
                self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        h = self.height()
        ring_size = 18
        ring_x = 4
        ring_y = (h - ring_size) // 2

        # 1. Track circle (background)
        track_pen = QPen(QColor(60, 65, 95, 120), 2.5)
        painter.setPen(track_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        rect_ring = QRectF(ring_x, ring_y, ring_size, ring_size)
        painter.drawEllipse(rect_ring)

        # 2. Progress Arc
        pct = min(1.0, self._current_words / float(self._goal_words))
        arc_span = int(-pct * 360 * 16)  # Negative for clockwise

        if pct >= 1.0:
            arc_color = QColor("#9ece6a")  # Vibrant emerald completion
        elif pct >= 0.5:
            arc_color = QColor("#7aa2f7")  # Radiant sky blue
        else:
            arc_color = QColor("#bb9af7")  # Soft lavender

        arc_pen = QPen(arc_color, 2.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(arc_pen)
        # 12 o'clock start is 90 * 16
        painter.drawArc(rect_ring, 90 * 16, arc_span)

        # 3. Label text: "350/1k w (35%)"
        font = QFont("Segoe UI", 9)
        font.setWeight(QFont.Weight.DemiBold)
        painter.setFont(font)
        painter.setPen(QColor("#c0caf5"))

        pct_int = int(pct * 100)
        if self._goal_words >= 1000:
            goal_k = f"{self._goal_words / 1000:.1f}k".replace(".0k", "k")
        else:
            goal_k = str(self._goal_words)

        label_text = f"{self._current_words:,}/{goal_k} ({pct_int}%)"
        text_rect = QRectF(ring_x + ring_size + 6, 0, self.width() - (ring_x + ring_size + 8), h)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, label_text)
