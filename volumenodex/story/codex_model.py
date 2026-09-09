"""Data models and manager for the Worldbuilding & Character Codex and Chapter Outliner."""

import uuid
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any


@dataclass
class CharacterProfile:
    id: str = field(default_factory=lambda: f"char_{uuid.uuid4().hex[:8]}")
    name: str = "New Character"
    role: str = "Supporting"  # Protagonist, Antagonist, Mentor, Supporting, Minor
    aliases: List[str] = field(default_factory=list)
    appearance: str = ""
    motivation: str = ""
    secrets: str = ""
    notes: str = ""
    icon_type: str = "person"  # corvus, quill, ink, scout, ignis, person, custom
    custom_image_path: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CharacterProfile":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class LoreEntry:
    id: str = field(default_factory=lambda: f"lore_{uuid.uuid4().hex[:8]}")
    title: str = "New Lore Entry"
    category: str = "Location"  # Location, Faction, Artifact, Magic/Tech, History, Custom
    aliases: List[str] = field(default_factory=list)
    description: str = ""
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LoreEntry":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class ChapterSceneItem:
    id: str = field(default_factory=lambda: f"scene_{uuid.uuid4().hex[:8]}")
    title: str = "Chapter"
    word_count: int = 0
    status: str = "Draft"  # Draft, In Progress, Needs Revision, Completed
    synopsis: str = ""
    block_number: int = 0
    heading_level: int = 1


class CodexManager:
    """Manages worldbuilding entities, characters, and live mention detection."""

    def __init__(self):
        self.characters: List[CharacterProfile] = []
        self.lore_entries: List[LoreEntry] = []
        self.scene_items: List[ChapterSceneItem] = []
        self._init_defaults()

    def _init_defaults(self) -> None:
        """Initial sample cast corresponding to the initial manuscript."""
        sean = CharacterProfile(
            id="char_sean",
            name="Master Sean",
            role="Protagonist",
            aliases=["Sean", "The Royal Cartographer", "The Mapmaker"],
            appearance="Brass spectacles, ink-stained cuffs, weathered tweed vest, sharp watchful eyes.",
            motivation="To complete the chart of the uncharted continent before the Royal Admiralty confiscates his secret ledgers.",
            secrets="Traced forbidden maritime coordinates in the margins of the King's official charts.",
            notes="Has transcribed official royal soundings for forty seasons.",
            icon_type="quill"
        )
        self.characters.append(sean)

        harbor = LoreEntry(
            id="lore_harbor",
            title="The Salt Fog Harbor",
            category="Location",
            aliases=["The Harbor", "Old Pier Fog"],
            description="A misty coastal haven where trading sloops dock under the shadow of the cathedral bell tower.",
            notes="Morning bells chime three times to guide ships through the shoal barrier."
        )
        self.lore_entries.append(harbor)

        compass = LoreEntry(
            id="lore_compass",
            title="The Cartographer's Compass",
            category="Artifact",
            aliases=["Ancient Compass", "The Brass Needle"],
            description="A hand-forged brass navigation tool with an azimuth bezel etched in archaic celestial script.",
            notes="Purported to point toward true uncharted land rather than magnetic north."
        )
        self.lore_entries.append(compass)

    def add_character(self, character: CharacterProfile) -> None:
        self.characters.append(character)

    def remove_character(self, char_id: str) -> None:
        self.characters = [c for c in self.characters if c.id != char_id]

    def add_lore(self, entry: LoreEntry) -> None:
        self.lore_entries.append(entry)

    def remove_lore(self, lore_id: str) -> None:
        self.lore_entries = [l for l in self.lore_entries if l.id != lore_id]

    def find_mention(self, text: str) -> Optional[Any]:
        """Finds if text contains any character or lore entity name/alias."""
        if not text:
            return None
        t_lower = text.lower()

        # Check characters
        for char in self.characters:
            if char.name.lower() in t_lower:
                return char
            for alias in char.aliases:
                if alias.strip() and alias.lower() in t_lower:
                    return char

        # Check lore
        for lore in self.lore_entries:
            if lore.title.lower() in t_lower:
                return lore
            for alias in lore.aliases:
                if alias.strip() and alias.lower() in t_lower:
                    return lore

        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "characters": [c.to_dict() for c in self.characters],
            "lore": [l.to_dict() for l in self.lore_entries]
        }

    def from_dict(self, data: Dict[str, Any]) -> None:
        if not data:
            return
        chars = data.get("characters", [])
        if chars:
            self.characters = [CharacterProfile.from_dict(c) for c in chars]

        lore = data.get("lore", [])
        if lore:
            self.lore_entries = [LoreEntry.from_dict(l) for l in lore]
