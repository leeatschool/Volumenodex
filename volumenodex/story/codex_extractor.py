"""Intelligent Narrative Entity Extraction Engine for Volumenodex Story Codex.

Automatically analyzes story manuscripts to discover and extract:
- Named characters (dialogue attribution, honorifics, narrative actions)
- Roles (Protagonist, Supporting, Minor based on mention frequency)
- Appearance & trait snippets
- Aliases (honorific stripping, forename, surname)
- World lore (locations, factions, artifacts)

Operates non-destructively: preserves author-edited and manually created entities.
"""

import re
from typing import List, Dict, Set, Tuple, Optional, Any
from dataclasses import dataclass

from volumenodex.story.codex_model import CodexManager, CharacterProfile, LoreEntry


STOPWORDS = {
    "The", "A", "An", "This", "That", "These", "Those", "There", "Here",
    "It", "Its", "He", "She", "They", "We", "You", "I", "Me", "Him", "Her", "Us", "Them",
    "My", "Your", "His", "Their", "Our", "Mine", "Yours", "Hers", "Ours", "Theirs",
    "Then", "When", "While", "Where", "Why", "How", "What", "Who", "Which", "Whom", "Whose",
    "After", "Before", "Since", "Until", "Till", "During", "As", "At", "By", "For", "From",
    "In", "Into", "Of", "Off", "On", "Onto", "Through", "Throughout", "To", "Toward", "Towards",
    "With", "Within", "Without", "Above", "Below", "Under", "Over", "Between", "Among", "Around",
    "And", "But", "Or", "Nor", "So", "Yet", "Because", "Although", "Though", "Even", "While",
    "If", "Unless", "Whether", "Lest", "Provided",
    "Suddenly", "Finally", "Soon", "Meanwhile", "Perhaps", "However", "Instead", "Indeed",
    "Certainly", "Surely", "Actually", "Obviously", "Naturally", "Clearly", "Simply", "Just",
    "Every", "All", "Some", "Any", "None", "No", "Both", "Each", "Either", "Neither",
    "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten",
    "First", "Second", "Third", "Last", "Next", "Another", "Other",
    "Chapter", "Part", "Book", "Volume", "Section", "Prologue", "Epilogue", "Act", "Scene",
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday",
    "January", "February", "March", "April", "May", "June", "July", "August", "September",
    "October", "November", "December",
    "Morning", "Afternoon", "Evening", "Night", "Dawn", "Dusk", "Midnight", "Noon",
    "Yes", "No", "Please", "Thank", "Thanks", "Hello", "Goodbye", "Farewell",
    "Wait", "Look", "Listen", "See", "Come", "Go", "Stop", "Remember", "Tell", "Say", "Think",
    "Something", "Nothing", "Everything", "Anything",
    "Someone", "Nobody", "Everyone", "Anyone",
    "Somewhere", "Nowhere", "Everywhere", "Anywhere",
    "God", "Lord", "Sire", "Sir", "Lady", "Madam", "Madame", "Ma'am", "Mister"
}

HONORIFICS = (
    r"(?:Lord|Lady|Sir|Dame|Doctor|Dr\.|Professor|Prof\.|Captain|Capt\.|Commander|Cmdr\.|"
    r"Master|Mistress|Miss|Mrs\.|Mr\.|King|Queen|Prince|Princess|Baron|Baroness|Count|Countess|"
    r"Duke|Duchess|Archduke|Father|Brother|Sister|Bishop|Cardinal|Inspector|Detective|"
    r"General|Gen\.|Admiral|Adm\.|Major|Lieutenant|Lt\.|Sergeant|Sgt\.|Constable|Sheriff|"
    r"Chancellor|President|Governor|Emperor|Empress)"
)

SPEECH_VERBS = (
    r"(?:said|whispered|replied|asked|demanded|murmured|muttered|shouted|yelled|cried|"
    r"called|exclaimed|gasped|sighed|growled|snapped|breathed|inquired|stammered|stuttered|"
    r"hissed|laughed|echoed|chuckled|warned|urged|confessed|pleaded|answered|noted|"
    r"observed|insisted|commented|suggested|admitted|agreed|added)"
)

ACTION_VERBS = (
    r"(?:smiled|frowned|nodded|glanced|laughed|sighed|paused|hesitated|stepped|turned|"
    r"walked|knelt|stood|sat|stared|watched|listened|leaned|waited|spoke|strode|shivered)"
)

LOCATION_NOUNS = (
    r"(?:Harbor|Port|River|Ocean|Sea|Bay|Strait|Lake|Gulf|Castle|Keep|Tower|Fortress|"
    r"Palace|Manor|Hall|Estate|Citadel|City|Town|Village|Hamlet|Forest|Woods|Grove|"
    r"Valley|Glen|Mountain|Mountains|Peak|Pass|Cliff|Isle|Island|Islands|Archipelago|"
    r"Canyon|Gorge|Bridge|Gate|Temple|Sanctuary|Cathedral|Chapel|Shrine|Library|"
    r"Archive|Archives|Academy|College|University|Station|Street|Avenue|Lane|Road|"
    r"Boulevard|Square|Market|Tavern|Inn|Pub)"
)

FACTION_NOUNS = (
    r"(?:Order|Guild|Syndicate|Council|Clan|House|Regiment|Legion|Alliance|Brotherhood|"
    r"Sisterhood|Cult|Cabal|Faction|Society|Circle|Empire|Admiralty|Inquisition|Court|"
    r"Federation|Coalition|Dynasty|Cartel)"
)

ARTIFACT_NOUNS = (
    r"(?:Sword|Blade|Dagger|Compass|Amulet|Ring|Tome|Grimoire|Codex|Chalice|Orb|Staff|"
    r"Wand|Crown|Circlet|Relic|Locket|Stone|Ledger|Map|Key|Scepter|Talisman|Mirror|"
    r"Scroll|Shield|Armor)"
)


@dataclass
class ExtractionResult:
    new_characters: int = 0
    new_lore: int = 0
    updated_entities: int = 0
    total_characters: int = 0
    total_lore: int = 0


class CodexExtractionEngine:
    """Intelligent entity extractor that dynamically populates the Story Codex."""

    @classmethod
    def extract_into_manager(cls, text: str, codex: CodexManager) -> ExtractionResult:
        """Analyzes text, extracts character and lore entities, and non-destructively populates codex."""
        res = ExtractionResult()
        if not text or len(text.strip()) < 15:
            res.total_characters = len(codex.characters)
            res.total_lore = len(codex.lore_entries)
            return res

        # 1. Strip basic HTML if present
        clean_text = re.sub(r"<[^>]+>", " ", text)
        clean_text = re.sub(r"\s+", " ", clean_text).strip()

        # 2. Candidate Extraction
        raw_characters, char_mentions = cls._extract_character_candidates(clean_text)
        raw_lore, lore_mentions = cls._extract_lore_candidates(clean_text)

        # 3. Non-Destructive Update for Characters
        cls._merge_characters(clean_text, raw_characters, char_mentions, codex, res)

        # 4. Non-Destructive Update for Lore
        cls._merge_lore(clean_text, raw_lore, lore_mentions, codex, res)

        res.total_characters = len(codex.characters)
        res.total_lore = len(codex.lore_entries)
        return res

    @classmethod
    def _extract_character_candidates(cls, text: str) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, int]]:
        """Identifies characters using honorifics, dialogue tags, and action attribution."""
        char_dict: Dict[str, Dict[str, Any]] = {}
        mentions: Dict[str, int] = {}

        def record(name: str, reason: str, honorific: Optional[str] = None):
            name = name.strip()
            # Clean punctuation and quotes from ends
            name = re.sub(r"^['\",.\s]+|['\",.\s]+$", "", name)
            if name.lower().startswith("the "):
                name = name[4:].strip()
            if not name or len(name) < 2:
                return

            words = name.split()
            # If single word, verify not in stopwords
            if len(words) == 1 and words[0] in STOPWORDS:
                return
            if all(w in STOPWORDS for w in words):
                return

            mentions[name] = mentions.get(name, 0) + 1
            if name not in char_dict:
                char_dict[name] = {
                    "name": name,
                    "reasons": {reason},
                    "honorific": honorific,
                }
            else:
                char_dict[name]["reasons"].add(reason)
                if honorific and not char_dict[name]["honorific"]:
                    char_dict[name]["honorific"] = honorific

        # Heuristic A: Honorific + Name (e.g. Master Sean, Inspector James, Lady Genevieve)
        hon_pattern = re.compile(rf"\b({HONORIFICS}\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b")
        for match in hon_pattern.finditer(text):
            full_match = match.group(1)
            parts = full_match.split(maxsplit=1)
            h_title = parts[0]
            record(full_match, "honorific", honorific=h_title)

        # Heuristic B: Dialogue Speech Attributions
        # 1) "... ," / "...?" said Name
        pat_speech_post = re.compile(
            rf'(?:[,.?!]\s*[\"\'“”]|[\"\'“”]\s*[,.?!]?)\s*{SPEECH_VERBS}\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b',
            re.IGNORECASE
        )
        for match in pat_speech_post.finditer(text):
            record(match.group(1), "speech_attribution")

        # 2) Name said, "..."
        pat_speech_pre = re.compile(
            rf'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+{SPEECH_VERBS}\s*,\s*[\"\'“”]',
            re.IGNORECASE
        )
        for match in pat_speech_pre.finditer(text):
            record(match.group(1), "speech_attribution")

        # 3) "..." Name said
        pat_speech_invert = re.compile(
            rf'(?:[,.?!]\s*[\"\'“”]|[\"\'“”]\s*[,.?!]?)\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+{SPEECH_VERBS}\b',
            re.IGNORECASE
        )
        for match in pat_speech_invert.finditer(text):
            record(match.group(1), "speech_attribution")

        # Heuristic C: Dialogue Action attribution (e.g. "..." Name smiled.)
        pat_action = re.compile(
            rf'(?:[,.?!]\s*[\"\'“”]|[\"\'“”]\s*[,.?!]?)\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+{ACTION_VERBS}\b',
            re.IGNORECASE
        )
        for match in pat_action.finditer(text):
            record(match.group(1), "action_attribution")

        # Heuristic D: Sentence beginning Name + Action verb (e.g. "Genevieve stepped toward...")
        pat_sent_action = re.compile(
            rf'(?:^|[.!?]\s+)([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+{ACTION_VERBS}\b'
        )
        for match in pat_sent_action.finditer(text):
            record(match.group(1), "sentence_action")

        return char_dict, mentions

    @classmethod
    def _extract_lore_candidates(cls, text: str) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, int]]:
        """Identifies locations, factions, and artifacts using domain nouns."""
        lore_dict: Dict[str, Dict[str, Any]] = {}
        mentions: Dict[str, int] = {}

        def record(title: str, category: str):
            title = title.strip()
            title = re.sub(r"^['\",.\s]+|['\",.\s]+$", "", title)
            if not title or len(title) < 3:
                return

            words = title.split()
            if all(w in STOPWORDS for w in words):
                return

            mentions[title] = mentions.get(title, 0) + 1
            if title not in lore_dict:
                lore_dict[title] = {
                    "title": title,
                    "category": category,
                }

        # 1. Locations
        loc_pat = re.compile(
            rf'\b((?:The\s+)?(?:[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+{LOCATION_NOUNS}))\b'
        )
        for m in loc_pat.finditer(text):
            record(m.group(1), "Location")

        # "Kingdom/Realm/Empire of X"
        loc_of_pat = re.compile(
            r'\b((?:Kingdom|Empire|Republic|Realm|Dominion|Duchy|Principality)\s+of\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b'
        )
        for m in loc_of_pat.finditer(text):
            record(m.group(1), "Location")

        # 2. Factions
        fac_pat = re.compile(
            rf'\b((?:The\s+)?(?:[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+{FACTION_NOUNS}))\b'
        )
        for m in fac_pat.finditer(text):
            record(m.group(1), "Faction")

        # 3. Artifacts
        art_pat = re.compile(
            rf'\b((?:The\s+)?(?:[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+{ARTIFACT_NOUNS}))\b'
        )
        for m in art_pat.finditer(text):
            record(m.group(1), "Artifact")

        return lore_dict, mentions

    @classmethod
    def _merge_characters(
        cls,
        text: str,
        candidates: Dict[str, Dict[str, Any]],
        mentions: Dict[str, int],
        codex: CodexManager,
        res: ExtractionResult
    ) -> None:
        """Smartly groups and merges candidate names into existing or new characters."""
        # Sort candidate names by length descending (longer, full names like 'Master Sean' first)
        sorted_names = sorted(candidates.keys(), key=lambda n: len(n), reverse=True)

        for name in sorted_names:
            info = candidates[name]
            count = mentions.get(name, 1)

            # Check if this name already belongs to an existing character (or alias)
            existing_char: Optional[CharacterProfile] = None
            for c in codex.characters:
                if c.name.lower() == name.lower() or any(a.lower() == name.lower() for a in c.aliases):
                    existing_char = c
                    break

            if existing_char:
                # Update mention count
                existing_char.mention_count = max(existing_char.mention_count, count)
                res.updated_entities += 1
                continue

            # Check if this candidate is a sub-name / alias of a longer character already in codex
            is_alias_of_existing = False
            for c in codex.characters:
                c_parts = [p.lower() for p in c.name.split()]
                if name.lower() in c_parts:
                    if name not in c.aliases:
                        c.aliases.append(name)
                    c.mention_count += count
                    is_alias_of_existing = True
                    res.updated_entities += 1
                    break

            if is_alias_of_existing:
                continue

            # Generate smart aliases
            aliases: List[str] = []
            name_parts = name.split()
            # If has honorific, add name without honorific as alias
            if info.get("honorific") and len(name_parts) > 1:
                without_hon = " ".join(name_parts[1:])
                aliases.append(without_hon)
                if len(name_parts) > 2:
                    aliases.append(name_parts[-1])  # Surname
            elif len(name_parts) >= 2:
                aliases.append(name_parts[0])   # First name
                aliases.append(name_parts[-1])  # Surname

            # Determine narrative role from mention frequency
            role = "Supporting"
            if count >= 3:
                role = "Protagonist"
            elif count == 1:
                role = "Minor"

            # Determine icon type from honorific or role
            icon = "person"
            hon_lower = (info.get("honorific") or "").lower()
            if any(k in hon_lower for k in ["captain", "admiral", "commander", "general", "major", "knight"]):
                icon = "scout"
            elif any(k in hon_lower for k in ["master", "professor", "doctor", "dr.", "scholar"]):
                icon = "quill"
            elif any(k in hon_lower for k in ["lord", "lady", "king", "queen", "duke", "baron", "count"]):
                icon = "ignis"

            # Search text for appearance / trait snippet
            appearance_snippet = cls._extract_trait_snippet(text, name, aliases)

            new_char = CharacterProfile(
                name=name,
                role=role,
                aliases=aliases,
                appearance=appearance_snippet,
                notes=f"Auto-discovered from narrative (mentioned {count}x).",
                icon_type=icon,
                is_auto_extracted=True,
                mention_count=count
            )
            codex.add_character(new_char)
            res.new_characters += 1

    @classmethod
    def _merge_lore(
        cls,
        text: str,
        candidates: Dict[str, Dict[str, Any]],
        mentions: Dict[str, int],
        codex: CodexManager,
        res: ExtractionResult
    ) -> None:
        """Merges discovered lore locations, factions, and artifacts into codex."""
        for title, info in candidates.items():
            count = mentions.get(title, 1)

            # Check if title or alias already exists in codex
            existing_lore: Optional[LoreEntry] = None
            for l in codex.lore_entries:
                if l.title.lower() == title.lower() or any(a.lower() == title.lower() for a in l.aliases):
                    existing_lore = l
                    break

            if existing_lore:
                existing_lore.mention_count = max(existing_lore.mention_count, count)
                res.updated_entities += 1
                continue

            # Generate smart aliases (e.g. without 'The ')
            aliases: List[str] = []
            if title.lower().startswith("the "):
                stripped = title[4:].strip()
                if stripped:
                    aliases.append(stripped)

            new_lore = LoreEntry(
                title=title,
                category=info["category"],
                aliases=aliases,
                description=f"Auto-extracted {info['category'].lower()} from manuscript.",
                notes=f"Discovered in text (mentioned {count}x).",
                is_auto_extracted=True,
                mention_count=count
            )
            codex.add_lore(new_lore)
            res.new_lore += 1

    @classmethod
    def _extract_trait_snippet(cls, text: str, name: str, aliases: List[str]) -> str:
        """Finds descriptive fragments like 'Name wore ...' or 'Name was ...'."""
        search_names = [name] + aliases
        for nm in search_names:
            pat = re.compile(
                rf'\b{re.escape(nm)}\s+(?:wore|was wearing|had|carried|clutched|held|bore)\s+([^.,;\n]{{5,80}})',
                re.IGNORECASE
            )
            m = pat.search(text)
            if m:
                snippet = m.group(1).strip()
                return f"{nm} had/wore {snippet}."
        return ""
