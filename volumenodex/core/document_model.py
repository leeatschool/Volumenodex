"""Document model and physical page geometry specifications."""

from dataclasses import dataclass
from enum import Enum
from typing import Tuple


class PaperSizePreset(str, Enum):
    LETTER = "US Letter (8.5 × 11 in)"
    A4 = "A4 (210 × 297 mm)"
    LEGAL = "US Legal (8.5 × 14 in)"
    EXECUTIVE = "Executive (7.25 × 10.5 in)"
    BOOK_6X9 = "Trade Paperback (6 × 9 in)"


class Orientation(str, Enum):
    PORTRAIT = "Portrait"
    LANDSCAPE = "Landscape"


class DocumentMode(str, Enum):
    CREATIVE_FICTION = "creative_fiction"
    NON_FICTION = "non_fiction"
    ACADEMIC = "academic"


DOCUMENT_MODE_TITLES = {
    DocumentMode.CREATIVE_FICTION: "Creative Fiction & Narrative",
    DocumentMode.NON_FICTION: "General Non-Fiction & Essays",
    DocumentMode.ACADEMIC: "Academic & Research Paper",
}


# Dimensions in inches (Width, Height) in portrait
PAPER_DIMENSIONS_INCHES = {
    PaperSizePreset.LETTER: (8.5, 11.0),
    PaperSizePreset.A4: (8.267, 11.692),
    PaperSizePreset.LEGAL: (8.5, 14.0),
    PaperSizePreset.EXECUTIVE: (7.25, 10.5),
    PaperSizePreset.BOOK_6X9: (6.0, 9.0),
}

DPI_SCREEN = 96.0  # Standard Windows DPI base


@dataclass
class PageMargins:
    top: float = 1.0     # inches
    bottom: float = 1.0  # inches
    left: float = 1.0    # inches
    right: float = 1.0   # inches

    @classmethod
    def normal(cls) -> "PageMargins":
        return cls(1.0, 1.0, 1.0, 1.0)

    @classmethod
    def narrow(cls) -> "PageMargins":
        return cls(0.5, 0.5, 0.5, 0.5)

    @classmethod
    def wide(cls) -> "PageMargins":
        return cls(1.0, 1.0, 1.5, 1.5)

    @classmethod
    def manuscript(cls) -> "PageMargins":
        return cls(1.0, 1.0, 1.25, 1.25)


class PageLayoutModel:
    """Computes pixel dimensions, print coordinates, and layout for physical pages."""

    def __init__(
        self,
        paper_size: PaperSizePreset = PaperSizePreset.LETTER,
        orientation: Orientation = Orientation.PORTRAIT,
        margins: PageMargins = None,
        zoom: float = 1.0,
    ):
        self.paper_size = paper_size
        self.orientation = orientation
        self.margins = margins or PageMargins.normal()
        self._zoom = zoom

    @property
    def zoom(self) -> float:
        return self._zoom

    @zoom.setter
    def zoom(self, value: float) -> None:
        self._zoom = max(0.25, min(4.0, value))

    @property
    def raw_dimensions_inches(self) -> Tuple[float, float]:
        w, h = PAPER_DIMENSIONS_INCHES[self.paper_size]
        if self.orientation == Orientation.LANDSCAPE:
            return (h, w)
        return (w, h)

    @property
    def page_width_px_base(self) -> float:
        w_in, _ = self.raw_dimensions_inches
        return w_in * DPI_SCREEN

    @property
    def page_height_px_base(self) -> float:
        _, h_in = self.raw_dimensions_inches
        return h_in * DPI_SCREEN

    @property
    def page_width_px(self) -> int:
        return int(round(self.page_width_px_base * self._zoom))

    @property
    def page_height_px(self) -> int:
        return int(round(self.page_height_px_base * self._zoom))

    @property
    def margin_left_px(self) -> int:
        return int(round(self.margins.left * DPI_SCREEN * self._zoom))

    @property
    def margin_right_px(self) -> int:
        return int(round(self.margins.right * DPI_SCREEN * self._zoom))

    @property
    def margin_top_px(self) -> int:
        return int(round(self.margins.top * DPI_SCREEN * self._zoom))

    @property
    def margin_bottom_px(self) -> int:
        return int(round(self.margins.bottom * DPI_SCREEN * self._zoom))

    @property
    def printable_width_px(self) -> int:
        return max(100, self.page_width_px - self.margin_left_px - self.margin_right_px)

    @property
    def printable_height_px(self) -> int:
        return max(100, self.page_height_px - self.margin_top_px - self.margin_bottom_px)


@dataclass
class DocumentStatistics:
    word_count: int = 0
    char_count: int = 0
    char_no_spaces: int = 0
    paragraph_count: int = 0
    page_count: int = 1
    reading_time_minutes: float = 0.0

    @classmethod
    def compute(cls, text: str, page_count: int = 1) -> "DocumentStatistics":
        words = text.split()
        word_count = len(words)
        char_count = len(text)
        char_no_spaces = len(text.replace(" ", "").replace("\n", "").replace("\r", "").replace("\t", ""))
        paragraphs = [p for p in text.split("\n") if p.strip()]
        paragraph_count = len(paragraphs)
        reading_time = round(word_count / 225.0, 1)  # ~225 WPM average adult reading speed

        return cls(
            word_count=word_count,
            char_count=char_count,
            char_no_spaces=char_no_spaces,
            paragraph_count=paragraph_count,
            page_count=max(1, page_count),
            reading_time_minutes=reading_time,
        )
