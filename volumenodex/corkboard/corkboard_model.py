"""Corkboard data model, scene index cards, and two-way manuscript synchronizer."""

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any


class CardStatus(str, Enum):
    IDEA = "Idea"
    DRAFT = "In Progress"
    REVISE = "Needs Revision"
    FINAL = "Completed"


STATUS_COLORS = {
    CardStatus.IDEA: "#7aa2f7",      # Blue
    CardStatus.DRAFT: "#e0af68",     # Amber
    CardStatus.REVISE: "#bb9af7",    # Lavender/Purple
    CardStatus.FINAL: "#9ece6a",     # Emerald Green
}

CARD_COLOR_PRESETS = [
    ("#fff9db", "#2b2616"),  # Classic Warm Ivory / Canary
    ("#e8f5e9", "#1b3320"),  # Mint Green
    ("#e1f5fe", "#123043"),  # Ice Blue
    ("#f3e5f5", "#351c38"),  # Lavender
    ("#ffebee", "#3d191d"),  # Pale Rose
    ("#282a36", "#f8f8f2"),  # Midnight Slate
]


@dataclass
class IndexCard:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    title: str = "Untitled Scene"
    synopsis: str = ""
    status: CardStatus = CardStatus.DRAFT
    bg_color: str = "#fff9db"
    text_color: str = "#2b2616"
    word_count: int = 0
    is_linked: bool = True  # True if bound to a document heading/section
    section_text: str = ""  # Full text body of the linked scene in manuscript

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "synopsis": self.synopsis,
            "status": self.status.value,
            "bg_color": self.bg_color,
            "text_color": self.text_color,
            "word_count": self.word_count,
            "is_linked": self.is_linked,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "IndexCard":
        return cls(
            id=data.get("id", str(uuid.uuid4())[:8]),
            title=data.get("title", "Untitled"),
            synopsis=data.get("synopsis", ""),
            status=CardStatus(data.get("status", CardStatus.DRAFT.value)),
            bg_color=data.get("bg_color", "#fff9db"),
            text_color=data.get("text_color", "#2b2616"),
            word_count=data.get("word_count", 0),
            is_linked=data.get("is_linked", True),
        )


class CorkboardManager:
    """Manages scene index cards and coordinates two-way synchronization with document text."""

    def __init__(self):
        self.linked_cards: List[IndexCard] = []
        self.scratch_cards: List[IndexCard] = []

    def add_linked_card(self, title: str, synopsis: str = "", text: str = "") -> IndexCard:
        card = IndexCard(
            title=title,
            synopsis=synopsis,
            is_linked=True,
            section_text=text,
            word_count=len(text.split()) if text else 0,
        )
        self.linked_cards.append(card)
        return card

    def add_scratch_card(self, title: str = "New Idea", synopsis: str = "") -> IndexCard:
        card = IndexCard(
            title=title,
            synopsis=synopsis,
            is_linked=False,
            bg_color="#ffebee",  # Pale rose
            text_color="#3d191d",
            status=CardStatus.IDEA,
        )
        self.scratch_cards.append(card)
        return card

    def move_card(self, from_idx: int, to_idx: int) -> bool:
        if 0 <= from_idx < len(self.linked_cards) and 0 <= to_idx < len(self.linked_cards):
            card = self.linked_cards.pop(from_idx)
            self.linked_cards.insert(to_idx, card)
            return True
        return False

    def to_metadata(self) -> Dict[str, Any]:
        return {
            "linked_cards": [c.to_dict() for c in self.linked_cards],
            "scratch_cards": [c.to_dict() for c in self.scratch_cards],
        }

    def load_metadata(self, data: Dict[str, Any]) -> None:
        self.linked_cards = [IndexCard.from_dict(d) for d in data.get("linked_cards", [])]
        self.scratch_cards = [IndexCard.from_dict(d) for d in data.get("scratch_cards", [])]
