"""Data models for Footnotes, Head Notes, and Margin Notes."""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any


@dataclass
class Footnote:
    """Footnote anchored to a specific position in the manuscript."""
    id: int
    text: str
    marker: str = ""  # e.g., "1", "2"
    anchor_pos: int = 0
    page_num: int = 1

    @property
    def number(self) -> int:
        return self.id


@dataclass
class HeadNote:
    """Introductory section or chapter note (epigraph, setting, historical note)."""
    id: str
    section_title: str
    content: str
    attribution: str = ""


@dataclass
class MarginNote:
    """Non-destructive editorial sticky note anchored to text."""
    id: str
    anchor_pos: int
    length: int
    selected_text: str
    comment: str
    created_at: str = ""


@dataclass
class NoteManager:
    """Manages document annotations: footnotes, head notes, and margin notes."""
    footnotes: List[Footnote] = field(default_factory=list)
    headnotes: List[HeadNote] = field(default_factory=list)
    margin_notes: List[MarginNote] = field(default_factory=list)

    def add_footnote(self, text: str, anchor_pos: int = 0, page_num: int = 1) -> Footnote:
        fn_id = len(self.footnotes) + 1
        fn = Footnote(id=fn_id, text=text, marker=str(fn_id), anchor_pos=anchor_pos, page_num=page_num)
        self.footnotes.append(fn)
        return fn

    def remove_footnote(self, fn_id: int) -> None:
        self.footnotes = [fn for fn in self.footnotes if fn.id != fn_id]
        # Re-number markers
        for idx, fn in enumerate(self.footnotes, start=1):
            fn.id = idx
            fn.marker = str(idx)

    def get_footnotes_for_page(self, page_num: int) -> List[Footnote]:
        return [fn for fn in self.footnotes if fn.page_num == page_num]

    def add_headnote(self, section_title: str, content: str, attribution: str = "") -> HeadNote:
        hn_id = f"hn_{len(self.headnotes) + 1}"
        hn = HeadNote(id=hn_id, section_title=section_title, content=content, attribution=attribution)
        self.headnotes.append(hn)
        return hn

    def add_margin_note(self, anchor_pos: int, length: int, selected_text: str, comment: str) -> MarginNote:
        import datetime
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        mn_id = f"mn_{len(self.margin_notes) + 1}"
        mn = MarginNote(
            id=mn_id,
            anchor_pos=anchor_pos,
            length=length,
            selected_text=selected_text,
            comment=comment,
            created_at=now_str
        )
        self.margin_notes.append(mn)
        return mn

    def to_dict(self) -> Dict[str, Any]:
        return {
            "footnotes": [asdict(f) for f in self.footnotes],
            "headnotes": [asdict(h) for h in self.headnotes],
            "margin_notes": [asdict(m) for m in self.margin_notes],
        }

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "NoteManager":
        if not data:
            return cls()
        mgr = cls()
        for f in data.get("footnotes", []):
            try:
                mgr.footnotes.append(Footnote(**f))
            except Exception:
                pass
        for h in data.get("headnotes", []):
            try:
                mgr.headnotes.append(HeadNote(**h))
            except Exception:
                pass
        for m in data.get("margin_notes", []):
            try:
                mgr.margin_notes.append(MarginNote(**m))
            except Exception:
                pass
        return mgr
