"""Linguistic analysis engine for Revision and Proofreading Lenses.

Implements five specialized editorial lenses:
1. Adverbs Lens (flags weak -ly modifiers with active verb alternatives)
2. Passive Voice Lens (detects 'was/were + past participle' passive constructions)
3. Pacing & Rhythm Heatmap (cadence analysis visualizing sentence tempo)
4. Filler & Crutch Phrases (wordiness and throat-clearing locutions)
5. Dialogue vs. Narrative Contrast (isolates spoken speech from surrounding prose)
"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Set
from PySide6.QtGui import QColor


@dataclass
class LensFinding:
    """A single flagged issue or insight detected by an editorial lens."""
    lens_type: str              # "adverb", "passive", "pacing", "filler", "dialogue"
    start_pos: int              # Absolute document character start
    end_pos: int                # Absolute document character end
    text: str                   # The exact matched string
    color: QColor               # Highlighter tint
    message: str                # Editorial guidance
    suggestions: List[str] = field(default_factory=list) # Alternative punchy replacements
    context_snippet: str = ""   # Surrounding sentence for inspector card preview
    sentence_length: int = 0    # Words count (for pacing lens)
    pacing_tier: str = ""       # "staccato", "brisk", "moderate", "lyrical"


class RevisionLensEngine:
    """High-speed manuscript analyzer producing non-destructive revision findings."""

    # Non-adverb -ly false positives
    LY_FALSE_POSITIVES: Set[str] = {
        "family", "lovely", "friendly", "early", "silly", "lonely", "ugly", "daily",
        "orderly", "holy", "jelly", "belly", "ally", "rally", "bully", "apply",
        "supply", "reply", "comply", "rely", "fly", "multiply", "butterfly", "lily",
        "monopoly", "anomaly", "homily", "italy", "folly", "gully", "chilly", "dolly",
        "holly", "woolly", "oily", "wily", "gravelly", "steely", "grisly", "bubbly",
        "sickly", "prickly", "elderly", "scholarly", "kingly", "queenly", "heavenly",
        "ghostly", "beastly", "fiddly", "wrinkly", "crumbly", "rabbly"
    }

    # Soft / empty modifiers
    SOFT_MODIFIERS: Set[str] = {
        "very", "really", "quite", "somewhat", "extremely", "absolutely", "totally",
        "fairly", "rather", "just", "mostly", "barely", "scarcely", "hardly", "virtually",
        "literally", "definitely", "completely", "truly"
    }

    # High-impact verb replacements for common adverbs
    ADVERB_REPLACEMENTS: Dict[str, List[str]] = {
        "quietly": ["whispered", "murmured", "tiptoed", "crept", "slipped"],
        "quickly": ["bolted", "dashed", "sprinted", "hurried", "darted"],
        "loudly": ["bellowed", "thundered", "roared", "clamored", "barked"],
        "slowly": ["inched", "drifted", "crawled", "lingered", "lagged"],
        "softly": ["breathed", "murmured", "whispered", "brushed", "muttered"],
        "angrily": ["snapped", "fumed", "seethed", "raged", "glowered"],
        "happily": ["beamed", "grinned", "rejoiced", "cheered"],
        "sadly": ["mourned", "grieved", "sighed", "lamented"],
        "suddenly": ["abruptly", "without warning", "(remove)"],
        "calmly": ["steadied", "composed", "soothed"],
        "carefully": ["measured", "studied", "scrutinized", "weighed"],
        "nervously": ["fidgeted", "trembled", "hesitated"],
        "anxiously": ["dreaded", "paced", "fretted"],
        "eagerly": ["yearned", "hungered", "craved"],
        "patiently": ["awaited", "endured", "bided"],
        "rudely": ["insulted", "scoffed", "sneered"],
        "politely": ["deferred", "bowed", "nodded"],
        "bravely": ["dared", "faced", "stood firm"],
        "very": ["(remove)", "exceptionally", "profoundly"],
        "really": ["(remove)", "genuinely", "truly"],
        "quite": ["(remove)", "rather"],
        "almost": ["nearly", "verged on"],
        "completely": ["(remove)", "entirely", "fully"],
        "actually": ["(remove)"],
        "basically": ["(remove)"],
        "simply": ["(remove)"],
    }

    # Filler and crutch phrases with direct punchy alternatives
    FILLER_PHRASES: Dict[str, List[str]] = {
        "in order to": ["to"],
        "due to the fact that": ["because", "since"],
        "at the end of the day": ["ultimately", "(remove)"],
        "all of a sudden": ["suddenly", "without warning", "(remove)"],
        "needless to say": ["(remove)"],
        "for the purpose of": ["to", "for"],
        "in the process of": ["(remove)"],
        "a number of": ["several", "many"],
        "as a matter of fact": ["in fact", "(remove)"],
        "it goes without saying": ["(remove)"],
        "at this point in time": ["now", "currently"],
        "by means of": ["by", "using"],
        "in light of the fact that": ["because", "considering"],
        "there is no doubt that": ["doubtless", "certainly"],
        "for all intents and purposes": ["effectively", "(remove)"],
        "in spite of the fact that": ["although", "even though"],
        "has the ability to": ["can"],
        "is able to": ["can"],
        "take into consideration": ["consider"],
        "make an assumption": ["assume"],
        "give consideration to": ["consider"],
        "came to the conclusion": ["concluded", "decided"],
        "started to": ["(use direct verb)"],
        "began to": ["(use direct verb)"],
    }

    # Passive auxiliary + participle pattern
    PASSIVE_REGEX = re.compile(
        r"\b(is|are|was|were|been|being|be)\s+([a-zA-Z]+ed|transcribed|confiscated|"
        r"embossed|measured|written|seen|taken|given|done|known|found|chosen|spoken|"
        r"broken|felt|heard|drawn|blown|struck|lost|built|held|kept|made|paid|said|"
        r"sent|told|met|left|led|set)\b",
        re.IGNORECASE
    )

    # Pre-compiled high-speed targeted regexes (replaces slow multi-pass matching)
    _SOFT_RE_STR = "|".join(re.escape(m) for m in sorted(SOFT_MODIFIERS, key=len, reverse=True))
    ADVERB_REGEX = re.compile(rf"\b([a-zA-Z]+ly|{_SOFT_RE_STR})\b", re.IGNORECASE)

    _FILLER_RE_STR = "|".join(re.escape(p) for p in sorted(FILLER_PHRASES.keys(), key=len, reverse=True))
    FILLER_REGEX = re.compile(rf"\b({_FILLER_RE_STR})\b", re.IGNORECASE)

    DIALOGUE_REGEX = re.compile(r'(".*?"|“.*?”|‘.*?’)', re.DOTALL)
    SENTENCE_REGEX = re.compile(r'([^.!?]+[.!?]+|\S[^.!?]*$)', re.MULTILINE)

    # Pastel Highlighter Wash Palettes
    COLOR_ADVERB = QColor(224, 175, 104, 75)      # Soft amber glow
    COLOR_PASSIVE = QColor(247, 118, 142, 75)     # Soft rose glow
    COLOR_FILLER = QColor(187, 154, 247, 75)      # Amethyst lavender glow
    COLOR_DIALOGUE = QColor(125, 207, 255, 65)    # Luminous cyan glow

    # Pacing Tier Colors
    COLOR_PACE_STACCATO = QColor(125, 207, 255, 60)  # Punchy Cyan (< 6 words)
    COLOR_PACE_BRISK = QColor(158, 206, 106, 50)     # Spring Green (6 - 14 words)
    COLOR_PACE_MODERATE = QColor(122, 162, 247, 45)  # Fluent Blue (15 - 25 words)
    COLOR_PACE_LYRICAL = QColor(224, 175, 104, 60)   # Amber Gold (> 25 words)

    @classmethod
    def analyze_document(
        cls,
        text: str,
        enabled_lenses: Optional[Dict[str, bool]] = None
    ) -> List[LensFinding]:
        """Runs linguistic analysis across text for all enabled lenses."""
        if not text:
            return []

        if enabled_lenses is None:
            enabled_lenses = {
                "adverb": True,
                "passive": True,
                "pacing": False,
                "filler": True,
                "dialogue": False,
            }

        findings: List[LensFinding] = []

        if enabled_lenses.get("adverb"):
            findings.extend(cls._find_adverbs(text))

        if enabled_lenses.get("passive"):
            findings.extend(cls._find_passive_voice(text))

        if enabled_lenses.get("filler"):
            findings.extend(cls._find_filler_phrases(text))

        if enabled_lenses.get("dialogue"):
            findings.extend(cls._find_dialogue(text))

        if enabled_lenses.get("pacing"):
            findings.extend(cls._analyze_pacing(text))

        # Sort findings by start position
        findings.sort(key=lambda f: f.start_pos)
        return findings

    @classmethod
    def _find_adverbs(cls, text: str) -> List[LensFinding]:
        """Flags -ly adverbs and weak soft modifiers using fast targeted matching."""
        findings = []
        for match in cls.ADVERB_REGEX.finditer(text):
            word = match.group(1)
            w_lower = word.lower()

            is_adverb = False
            if w_lower.endswith("ly") and w_lower not in cls.LY_FALSE_POSITIVES:
                is_adverb = True
            elif w_lower in cls.SOFT_MODIFIERS:
                is_adverb = True

            if is_adverb:
                suggestions = cls.ADVERB_REPLACEMENTS.get(w_lower, ["(remove)", "rephrase with a punchy verb"])
                snippet = cls._extract_snippet(text, match.start(), match.end())
                msg = f"Weak adverb or modifier '{word}'. Strong verbs create more vivid prose."
                findings.append(LensFinding(
                    lens_type="adverb",
                    start_pos=match.start(),
                    end_pos=match.end(),
                    text=word,
                    color=cls.COLOR_ADVERB,
                    message=msg,
                    suggestions=suggestions,
                    context_snippet=snippet,
                ))

        return findings

    @classmethod
    def _find_passive_voice(cls, text: str) -> List[LensFinding]:
        """Detects passive constructions."""
        findings = []
        for match in cls.PASSIVE_REGEX.finditer(text):
            phrase = match.group(0)
            snippet = cls._extract_snippet(text, match.start(), match.end())
            findings.append(LensFinding(
                lens_type="passive",
                start_pos=match.start(),
                end_pos=match.end(),
                text=phrase,
                color=cls.COLOR_PASSIVE,
                message=f"Passive voice: '{phrase}'. Active voice places the actor first.",
                suggestions=["Rephrase in active voice", "(make subject the actor)"],
                context_snippet=snippet,
            ))
        return findings

    @classmethod
    def _find_filler_phrases(cls, text: str) -> List[LensFinding]:
        """Identifies wordy throat-clearing crutches in a single unified regex pass."""
        findings = []
        for match in cls.FILLER_REGEX.finditer(text):
            matched_text = match.group(0)
            suggestions = cls.FILLER_PHRASES.get(matched_text.lower(), ["(remove)"])
            snippet = cls._extract_snippet(text, match.start(), match.end())
            findings.append(LensFinding(
                lens_type="filler",
                start_pos=match.start(),
                end_pos=match.end(),
                text=matched_text,
                color=cls.COLOR_FILLER,
                message=f"Wordy crutch phrase '{matched_text}'. Tighten for stronger impact.",
                suggestions=suggestions,
                context_snippet=snippet,
            ))
        return findings

    @classmethod
    def _find_dialogue(cls, text: str) -> List[LensFinding]:
        """Isolates dialogue speech inside quotation marks."""
        findings = []
        for match in cls.DIALOGUE_REGEX.finditer(text):
            quoted = match.group(0)
            snippet = quoted[:60] + ("..." if len(quoted) > 60 else "")
            findings.append(LensFinding(
                lens_type="dialogue",
                start_pos=match.start(),
                end_pos=match.end(),
                text=quoted,
                color=cls.COLOR_DIALOGUE,
                message="Spoken dialogue: audit voice naturalness, rhythm, and character subtext.",
                suggestions=["Read aloud to check cadence"],
                context_snippet=snippet,
            ))
        return findings

    @classmethod
    def _analyze_pacing(cls, text: str) -> List[LensFinding]:
        """Evaluates sentence cadence and rhythm variations."""
        findings = []
        for match in cls.SENTENCE_REGEX.finditer(text):
            s_text = match.group(0).strip()
            if not s_text:
                continue

            words = s_text.split()
            w_count = len(words)

            if w_count <= 5:
                tier = "staccato"
                color = cls.COLOR_PACE_STACCATO
                msg = f"Staccato tempo ({w_count} words). High impact, punchy pacing."
            elif 6 <= w_count <= 14:
                tier = "brisk"
                color = cls.COLOR_PACE_BRISK
                msg = f"Brisk cadence ({w_count} words). Swift narrative progression."
            elif 15 <= w_count <= 25:
                tier = "moderate"
                color = cls.COLOR_PACE_MODERATE
                msg = f"Fluid narrative ({w_count} words). Balanced descriptive tempo."
            else:
                tier = "lyrical"
                color = cls.COLOR_PACE_LYRICAL
                msg = f"Lyrical / complex sentence ({w_count} words). Ensure clarity."

            findings.append(LensFinding(
                lens_type="pacing",
                start_pos=match.start(),
                end_pos=match.end(),
                text=s_text,
                color=color,
                message=msg,
                sentence_length=w_count,
                pacing_tier=tier,
                context_snippet=s_text[:75] + ("..." if len(s_text) > 75 else ""),
            ))

        return findings

    @staticmethod
    def _extract_snippet(text: str, start: int, end: int, window: int = 35) -> str:
        """Extracts text around a finding with an ellipsis prefix/suffix."""
        s = max(0, start - window)
        e = min(len(text), end + window)
        prefix = "..." if s > 0 else ""
        suffix = "..." if e < len(text) else ""
        return f"{prefix}{text[s:start]}[{text[start:end]}]{text[end:e]}{suffix}".replace("\n", " ")
