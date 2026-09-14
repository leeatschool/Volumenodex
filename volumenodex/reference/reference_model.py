"""Data models for Writers Reference entries, categories, and relevance scoring."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
import re


class ReferenceCategory:
    """Standard categorized domains of human knowledge for fiction authors."""
    WEAPONS_WARFARE = "Weapons & Warfare"
    POISONS_MEDICINE = "Poisons & Medicine"
    HIERARCHY_NOBILITY = "Hierarchy & Nobility"
    HERALDRY_CHIVALRY = "Heraldry & Chivalry"
    NAUTICAL_SAILING = "Nautical & Sailing"
    AVIATION_FLIGHT = "Aviation & Flight"
    ASTRONOMY_SPACE = "Astronomy & Cosmos"
    EARTH_METALS_MACHINES = "Earth, Metals & Machines"
    WILDERNESS_SURVIVAL = "Wilderness & Survival"
    FORENSICS_CRIME = "Forensics & Crime"
    SLANG_CANT_DIALECT = "Slang, Cant & Dialect"
    MYTH_FOLKLORE = "Mythology & Folklore"
    STORY_DRAMATURGY = "Story & Dramaturgy"
    BODY_LANGUAGE = "Sensory & Body Language"
    CASTLES_ARCHITECTURE = "Castles & Architecture"
    ARCHAIC_UNITS_TIME = "Archaic Units & Time"
    CUSTOM_LORE = "Custom Author Lore"

    ALL_CATEGORIES = [
        WEAPONS_WARFARE,
        POISONS_MEDICINE,
        HIERARCHY_NOBILITY,
        HERALDRY_CHIVALRY,
        NAUTICAL_SAILING,
        AVIATION_FLIGHT,
        ASTRONOMY_SPACE,
        EARTH_METALS_MACHINES,
        WILDERNESS_SURVIVAL,
        FORENSICS_CRIME,
        SLANG_CANT_DIALECT,
        MYTH_FOLKLORE,
        STORY_DRAMATURGY,
        BODY_LANGUAGE,
        CASTLES_ARCHITECTURE,
        ARCHAIC_UNITS_TIME,
        CUSTOM_LORE,
    ]


@dataclass
class ReferenceEntry:
    """A single topic entry within the offline Writers Reference compendium."""
    id: str
    title: str
    category: str
    tags: List[str] = field(default_factory=list)
    summary: str = ""
    quick_facts: Dict[str, str] = field(default_factory=dict)
    content: str = ""
    fiction_tips: str = ""
    related_entries: List[str] = field(default_factory=list)
    is_custom: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Serializes the entry to a dictionary suitable for JSON."""
        return {
            "id": self.id,
            "title": self.title,
            "category": self.category,
            "tags": list(self.tags),
            "summary": self.summary,
            "quick_facts": dict(self.quick_facts),
            "content": self.content,
            "fiction_tips": self.fiction_tips,
            "related_entries": list(self.related_entries),
            "is_custom": self.is_custom,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ReferenceEntry":
        """Reconstitutes an entry from dictionary data."""
        return cls(
            id=data.get("id", ""),
            title=data.get("title", "Untitled Topic"),
            category=data.get("category", ReferenceCategory.CUSTOM_LORE),
            tags=list(data.get("tags", [])),
            summary=data.get("summary", ""),
            quick_facts=dict(data.get("quick_facts", {})),
            content=data.get("content", ""),
            fiction_tips=data.get("fiction_tips", ""),
            related_entries=list(data.get("related_entries", [])),
            is_custom=bool(data.get("is_custom", False)),
        )

    def matches_query(self, query: str) -> Tuple[bool, int]:
        """Calculates if this entry matches a search query, and calculates relevance score.

        Returns:
            Tuple of (matches: bool, score: int)
        """
        q = query.strip().lower()
        if not q:
            return True, 0

        score = 0
        words = [w for w in re.split(r"\s+", q) if w]

        title_lower = self.title.lower()
        summary_lower = self.summary.lower()
        category_lower = self.category.lower()
        content_lower = self.content.lower()
        tips_lower = self.fiction_tips.lower()
        tags_lower = [t.lower() for t in self.tags]

        # Exact phrase match in title
        if q in title_lower:
            score += 150
            if title_lower == q:
                score += 100

        # Exact phrase in tags
        for t in tags_lower:
            if q == t:
                score += 80
            elif q in t:
                score += 40

        # Exact phrase in summary or quick facts
        if q in summary_lower:
            score += 50
        for k, v in self.quick_facts.items():
            if q in k.lower() or q in v.lower():
                score += 35

        # Individual word matches
        all_words_found = True
        for w in words:
            word_found = False
            if w in title_lower:
                score += 40
                word_found = True
            if any(w in t for t in tags_lower):
                score += 25
                word_found = True
            if w in category_lower:
                score += 20
                word_found = True
            if any(w in k.lower() or w in v.lower() for k, v in self.quick_facts.items()):
                score += 15
                word_found = True
            if w in summary_lower:
                score += 10
                word_found = True
            if w in content_lower:
                score += 5
                word_found = True
            if w in tips_lower:
                score += 4
                word_found = True

            if not word_found:
                all_words_found = False

        if score > 0 and all_words_found:
            return True, score
        elif score >= 50:
            # High partial match
            return True, score

        return False, 0
