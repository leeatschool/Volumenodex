from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QSlider, QToolButton, QFrame
)
from volumenodex.core.document_model import DocumentStatistics
from volumenodex.pet.companion_figures import CompanionFigureRenderer


class VolumenodexStatusBar(QWidget):
    """Custom rich status bar with metrics and zoom controls."""

    zoomChanged = Signal(float)
    petClicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(28)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 2, 12, 2)
        layout.setSpacing(12)

        # Left: Document Metrics
        self.lbl_pages = QLabel("Page 1 of 1")
        layout.addWidget(self.lbl_pages)

        layout.addWidget(self._create_separator())

        self.lbl_words = QLabel("0 words")
        layout.addWidget(self.lbl_words)

        self.lbl_chars = QLabel("0 characters")
        layout.addWidget(self.lbl_chars)

        layout.addWidget(self._create_separator())

        self.lbl_reading_time = QLabel("0.0 min read")
        layout.addWidget(self.lbl_reading_time)

        layout.addStretch()

        # Center-Right: Scribe Companion / Writing Pet Chip
        self.btn_pet_chip = QToolButton()
        self.btn_pet_chip.setText("Corvus (Active)")
        self.btn_pet_chip.setIcon(CompanionFigureRenderer.render_icon("corvus", size=18))
        self.btn_pet_chip.setIconSize(QSize(18, 18))
        self.btn_pet_chip.setStyleSheet("""
            QToolButton {
                background-color: #1f2130;
                border: 1px solid #35384e;
                border-radius: 12px;
                padding: 2px 10px;
                color: #c0caf5;
                font-size: 11px;
                font-weight: 500;
            }
            QToolButton:hover {
                background-color: #272a3e;
                border: 1px solid #7aa2f7;
            }
        """)
        self.btn_pet_chip.clicked.connect(self.petClicked.emit)
        layout.addWidget(self.btn_pet_chip)

        layout.addWidget(self._create_separator())

        zoom_btn_style = """
            QToolButton {
                background-color: #1e202e;
                color: #c0caf5;
                border: 1px solid #2f334d;
                border-radius: 3px;
                font-size: 11px;
                font-weight: bold;
            }
            QToolButton:hover {
                background-color: #2a2d3e;
                color: #7aa2f7;
                border-color: #7aa2f7;
            }
            QToolButton:pressed {
                background-color: #7aa2f7;
                color: #101116;
            }
        """
        # Right: Zoom Controls
        self.btn_zoom_out = QToolButton()
        self.btn_zoom_out.setText("−")
        self.btn_zoom_out.setFixedSize(18, 18)
        self.btn_zoom_out.setStyleSheet(zoom_btn_style)
        self.btn_zoom_out.clicked.connect(self._zoom_step_down)
        layout.addWidget(self.btn_zoom_out)

        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setRange(50, 200)
        self.zoom_slider.setValue(100)
        self.zoom_slider.setFixedWidth(90)
        self.zoom_slider.valueChanged.connect(self._on_slider_value_changed)
        layout.addWidget(self.zoom_slider)

        self.btn_zoom_in = QToolButton()
        self.btn_zoom_in.setText("+")
        self.btn_zoom_in.setFixedSize(18, 18)
        self.btn_zoom_in.setStyleSheet(zoom_btn_style)
        self.btn_zoom_in.clicked.connect(self._zoom_step_up)
        layout.addWidget(self.btn_zoom_in)

        self.lbl_zoom = QLabel("100%")
        self.lbl_zoom.setFixedWidth(38)
        self.lbl_zoom.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.lbl_zoom)

    def _create_separator(self) -> QFrame:
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet("background-color: #2a2c3d; width: 1px; margin: 2px 4px;")
        return sep

    def update_statistics(self, stats: DocumentStatistics) -> None:
        self.lbl_pages.setText(f"Page {stats.page_count} of {stats.page_count}")
        self.lbl_words.setText(f"{stats.word_count:,} words")
        self.lbl_chars.setText(f"{stats.char_count:,} characters")
        self.lbl_reading_time.setText(f"{stats.reading_time_minutes} min read")

    def update_pet_status(self, pet_name: str, state_text: str, pet_id: str = "corvus") -> None:
        self.btn_pet_chip.setText(f"{pet_name} ({state_text})")
        self.btn_pet_chip.setIcon(CompanionFigureRenderer.render_icon(pet_id, size=18))

    def set_zoom_value(self, zoom: float) -> None:
        percent = int(round(zoom * 100))
        if self.zoom_slider.value() != percent:
            self.zoom_slider.blockSignals(True)
            self.zoom_slider.setValue(percent)
            self.zoom_slider.blockSignals(False)
        self.lbl_zoom.setText(f"{percent}%")

    def _on_slider_value_changed(self, val: int) -> None:
        self.lbl_zoom.setText(f"{val}%")
        self.zoomChanged.emit(val / 100.0)

    def _zoom_step_down(self) -> None:
        cur = self.zoom_slider.value()
        self.zoom_slider.setValue(max(50, cur - 10))

    def _zoom_step_up(self) -> None:
        cur = self.zoom_slider.value()
        self.zoom_slider.setValue(min(200, cur + 10))
