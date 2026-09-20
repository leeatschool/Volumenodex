"""Screenplay formatting engine: autoformatting, element detection, and typography rules."""

import re
from typing import Optional, Tuple
from PySide6.QtCore import Qt
from PySide6.QtGui import (
    QTextCursor, QTextBlockFormat, QTextCharFormat, QFont, QColor, QTextDocument
)


class ScreenplayElementType:
    HEADING = "heading"              # Scene Heading / Slugline (EXT. / INT.)
    SLUGLINE = "heading"             # Alias for HEADING
    ACTION = "action"                # Scene Description / Action
    CHARACTER = "character"          # Character Name
    PARENTHETICAL = "parenthetical"  # Character direction / (beat)
    DIALOGUE = "dialogue"            # Spoken dialogue
    TRANSITION = "transition"        # CUT TO:, FADE IN:, etc.
    LIGHTING = "lighting"            # Lighting / Technical Prompts
    LIGHTING_NOTE = "lighting"       # Alias for LIGHTING
    ACT_HEADER = "act_header"        # ACT I, COLD OPEN, etc.
    ACT_MARKER = "act_header"        # Alias for ACT_HEADER
    SCENE_MARKER = "act_header"      # Alias for SCENE_MARKER


# Element cycle for Tab key navigation
TAB_CYCLE = [
    ScreenplayElementType.ACTION,
    ScreenplayElementType.CHARACTER,
    ScreenplayElementType.PARENTHETICAL,
    ScreenplayElementType.DIALOGUE,
    ScreenplayElementType.TRANSITION,
    ScreenplayElementType.HEADING,
]


class ScreenplayFormatter:
    """Provides screenplay autoformatting, element detection, and geometry styling."""

    FONT_FAMILY = "Courier Prime"
    FALLBACK_FONTS = ["Courier Prime", "Courier New", "Courier", "monospace"]
    FONT_SIZE = 12

    # Heading prefixes
    SLUGLINE_PREFIXES = (
        "int.", "ext.", "int/ext", "ext/int", "i/e.", "i/e",
        "interior:", "exterior:", "est.", "insert -", "pov -"
    )

    # Transition suffixes and phrases
    TRANSITIONS = {
        "cut to:", "fade in:", "fade out.", "fade out:", "smash cut to:",
        "dissolve to:", "match cut to:", "jump cut to:", "time cut:",
        "back to:", "flash cut to:"
    }

    # Lighting / Technical prefixes
    LIGHTING_PREFIXES = (
        "lighting:", "light direction:", "low lighting", "pitch black",
        "harsh moonlight", "neon sign", "deep shadows", "blinding midday sun",
        "golden hour", "soft diffused", "dull overcast", "sterile fluorescent",
        "harsh fluorescent", "harsh overhead", "dim amber",
        "pale blue monitor", "emergency klaxon", "silhouette", "chiaroscuro",
        "[prop:", "prop:"
    )

    ELEMENT_SPECS = {
        ScreenplayElementType.HEADING: {"left_margin": 0.0, "right_margin": 0.0, "uppercase": True, "bold": True},
        ScreenplayElementType.ACTION: {"left_margin": 0.0, "right_margin": 0.0, "uppercase": False, "bold": False},
        ScreenplayElementType.CHARACTER: {"left_margin": 210.0, "right_margin": 0.0, "uppercase": True, "bold": True},
        ScreenplayElementType.PARENTHETICAL: {"left_margin": 150.0, "right_margin": 150.0, "italic": True},
        ScreenplayElementType.DIALOGUE: {"left_margin": 100.0, "right_margin": 120.0, "uppercase": False},
        ScreenplayElementType.TRANSITION: {"left_margin": 360.0, "right_margin": 0.0, "uppercase": True, "bold": True},
        ScreenplayElementType.LIGHTING: {"left_margin": 30.0, "right_margin": 30.0, "italic": True},
        ScreenplayElementType.ACT_HEADER: {"left_margin": 0.0, "right_margin": 0.0, "bold": True, "centered": True},
    }

    @classmethod
    def next_element_after_enter(cls, current_element: str, block_text: str = "") -> str:
        return cls.get_next_element_on_enter(current_element, block_text)

    @classmethod
    def cycle_element(cls, current_element: str, reverse: bool = False) -> str:
        return cls.get_next_element_on_tab(current_element, backwards=reverse)

    @classmethod
    def get_screenplay_font(cls) -> QFont:
        font = QFont()
        font.setFamilies(cls.FALLBACK_FONTS)
        font.setPointSize(cls.FONT_SIZE)
        font.setStyleHint(QFont.StyleHint.Monospace)
        return font

    @classmethod
    def classify_line(cls, text: str, prev_element: Optional[str] = None) -> str:
        """Determines the screenplay element type based on text structure and script context."""
        cleaned = text.strip()
        if not cleaned:
            return ScreenplayElementType.ACTION

        t_lower = cleaned.lower()

        # 1. Act & Scene Headers
        if re.match(r"^(act\s+[ivx0-9]+|scene\s+[0-9]+|cold\s+open|tag\s*/\s*epilogue|prologue)", t_lower):
            return ScreenplayElementType.ACT_HEADER

        # 2. Scene Headings / Sluglines
        for prefix in cls.SLUGLINE_PREFIXES:
            if t_lower.startswith(prefix):
                return ScreenplayElementType.HEADING

        # 3. Transitions
        if t_lower in cls.TRANSITIONS or (t_lower.endswith(" to:") and len(cleaned) < 30):
            return ScreenplayElementType.TRANSITION

        # 4. Parentheticals
        if cleaned.startswith("(") and cleaned.endswith(")"):
            return ScreenplayElementType.PARENTHETICAL

        # 5. Lighting / Direction Prompts
        for lp in cls.LIGHTING_PREFIXES:
            if t_lower.startswith(lp):
                return ScreenplayElementType.LIGHTING

        # 6. Character Name: All uppercase, relatively short (< 35 chars), no ending period
        # Example: "JOHN", "SARAH CONNER", "DETECTIVE VANCE (V.O.)", "VOICE (O.S.)"
        is_all_caps = cleaned.isupper() and any(c.isalpha() for c in cleaned)
        has_char_modifier = "(v.o.)" in t_lower or "(o.s.)" in t_lower or "(cont'd)" in t_lower
        if (is_all_caps or has_char_modifier) and len(cleaned) <= 38 and not cleaned.endswith("."):
            # If previous was character or parenthetical, and this has no dialogue between, treat as action or character
            return ScreenplayElementType.CHARACTER

        # 7. Dialogue: If following a Character or Parenthetical
        if prev_element in (ScreenplayElementType.CHARACTER, ScreenplayElementType.PARENTHETICAL):
            return ScreenplayElementType.DIALOGUE

        # Default fallback is Action (Scene Description)
        return ScreenplayElementType.ACTION

    @classmethod
    def apply_element_format(cls, cursor: QTextCursor, element_type: str, dark_paper: bool = False) -> None:
        """Applies screenplay margin geometry, alignment, and typography to a text block."""
        bf = QTextBlockFormat()
        cf = QTextCharFormat()

        cf.setFontFamilies(cls.FALLBACK_FONTS)
        cf.setFontPointSize(cls.FONT_SIZE)
        cf.setForeground(QColor("#ffffff" if dark_paper else "#000000"))

        if element_type == ScreenplayElementType.HEADING:
            # Scene Heading (Slugline): Left aligned, bold, uppercase
            bf.setLeftMargin(0)
            bf.setRightMargin(0)
            bf.setTopMargin(14)
            bf.setBottomMargin(4)
            cf.setFontWeight(QFont.Weight.Bold)
            bf.setProperty(QTextBlockFormat.Property.UserProperty, "screenplay_heading")

        elif element_type == ScreenplayElementType.ACTION:
            # Action (Scene Description): Full width, regular weight
            bf.setLeftMargin(0)
            bf.setRightMargin(0)
            bf.setTopMargin(4)
            bf.setBottomMargin(4)
            cf.setFontWeight(QFont.Weight.Normal)
            bf.setProperty(QTextBlockFormat.Property.UserProperty, "screenplay_action")

        elif element_type == ScreenplayElementType.CHARACTER:
            # Character: Indented ~2.2 inches (~210px), bold or regular all-caps
            bf.setLeftMargin(210)
            bf.setRightMargin(0)
            bf.setTopMargin(10)
            bf.setBottomMargin(1)
            cf.setFontWeight(QFont.Weight.Bold)
            bf.setProperty(QTextBlockFormat.Property.UserProperty, "screenplay_character")

        elif element_type == ScreenplayElementType.PARENTHETICAL:
            # Parenthetical: Indented ~1.6 inches (~150px), right margin ~150px
            bf.setLeftMargin(150)
            bf.setRightMargin(150)
            bf.setTopMargin(0)
            bf.setBottomMargin(0)
            cf.setFontItalic(True)
            bf.setProperty(QTextBlockFormat.Property.UserProperty, "screenplay_parenthetical")

        elif element_type == ScreenplayElementType.DIALOGUE:
            # Dialogue: Indented ~1.0 inch (~100px), right margin ~120px
            bf.setLeftMargin(100)
            bf.setRightMargin(120)
            bf.setTopMargin(0)
            bf.setBottomMargin(6)
            cf.setFontWeight(QFont.Weight.Normal)
            bf.setProperty(QTextBlockFormat.Property.UserProperty, "screenplay_dialogue")

        elif element_type == ScreenplayElementType.TRANSITION:
            # Transition: Right aligned or heavily indented
            bf.setLeftMargin(360)
            bf.setRightMargin(0)
            bf.setTopMargin(10)
            bf.setBottomMargin(10)
            cf.setFontWeight(QFont.Weight.Bold)
            bf.setProperty(QTextBlockFormat.Property.UserProperty, "screenplay_transition")

        elif element_type == ScreenplayElementType.LIGHTING:
            # Lighting & Atmosphere / Prop prompt: Slightly indented, distinct styling
            bf.setLeftMargin(30)
            bf.setRightMargin(30)
            bf.setTopMargin(4)
            bf.setBottomMargin(4)
            cf.setFontItalic(True)
            bf.setProperty(QTextBlockFormat.Property.UserProperty, "screenplay_lighting")

        elif element_type == ScreenplayElementType.ACT_HEADER:
            # Act Header: Centered, Bold
            bf.setAlignment(Qt.AlignmentFlag.AlignCenter)
            bf.setTopMargin(18)
            bf.setBottomMargin(8)
            cf.setFontWeight(QFont.Weight.Bold)
            bf.setProperty(QTextBlockFormat.Property.UserProperty, "screenplay_act")

        cursor.setBlockFormat(bf)
        cursor.setBlockCharFormat(cf)
        cursor.mergeCharFormat(cf)

    @classmethod
    def get_element_type_of_block(cls, block) -> str:
        """Retrieves stored element property from block or detects it."""
        prop = block.blockFormat().property(QTextBlockFormat.Property.UserProperty)
        if prop and str(prop).startswith("screenplay_"):
            return str(prop).replace("screenplay_", "")
        return cls.classify_line(block.text())

    @classmethod
    def get_next_element_on_enter(cls, current_element: str, block_text: str) -> str:
        """Modernized RawScripts smart Enter key routing."""
        cleaned = block_text.strip()

        if current_element == ScreenplayElementType.HEADING:
            # After Heading -> Action
            return ScreenplayElementType.ACTION

        elif current_element == ScreenplayElementType.CHARACTER:
            # After Character -> Dialogue (or parenthetical if user typed '(')
            if cleaned.endswith("("):
                return ScreenplayElementType.PARENTHETICAL
            return ScreenplayElementType.DIALOGUE

        elif current_element == ScreenplayElementType.PARENTHETICAL:
            # After Parenthetical -> Dialogue
            return ScreenplayElementType.DIALOGUE

        elif current_element == ScreenplayElementType.DIALOGUE:
            # If user hit Enter on empty dialogue block -> Action
            if not cleaned:
                return ScreenplayElementType.ACTION
            # Otherwise next is Action (double enter returns to action)
            return ScreenplayElementType.ACTION

        elif current_element == ScreenplayElementType.TRANSITION:
            # After Transition -> Scene Heading
            return ScreenplayElementType.HEADING

        elif current_element == ScreenplayElementType.LIGHTING:
            # After Lighting -> Action
            return ScreenplayElementType.ACTION

        elif current_element == ScreenplayElementType.ACT_HEADER:
            # After Act Header -> Heading
            return ScreenplayElementType.HEADING

        # Default after Action is Action
        return ScreenplayElementType.ACTION

    @classmethod
    def get_next_element_on_tab(cls, current_element: str, backwards: bool = False) -> str:
        """Cycles through screenplay elements using Tab or Shift+Tab."""
        try:
            idx = TAB_CYCLE.index(current_element)
        except ValueError:
            idx = 0

        delta = -1 if backwards else 1
        next_idx = (idx + delta) % len(TAB_CYCLE)
        return TAB_CYCLE[next_idx]

    @classmethod
    def autoformat_document(cls, doc: QTextDocument, dark_paper: bool = False) -> int:
        """Scans the entire document, classifies each block, and applies standard script geometry."""
        block = doc.begin()
        formatted_count = 0
        prev_element = None

        cursor = QTextCursor(doc)
        cursor.beginEditBlock()
        try:
            while block.isValid():
                text = block.text()
                element_type = cls.classify_line(text, prev_element)

                # Uppercase formatting for sluglines, characters, and transitions
                if element_type in (ScreenplayElementType.HEADING, ScreenplayElementType.CHARACTER, ScreenplayElementType.TRANSITION):
                    if text != text.upper():
                        c_block = QTextCursor(block)
                        c_block.select(QTextCursor.SelectionType.BlockUnderCursor)
                        c_block.insertText(text.upper())

                cursor.setPosition(block.position())
                cls.apply_element_format(cursor, element_type, dark_paper=dark_paper)

                prev_element = element_type
                formatted_count += 1
                block = block.next()
        finally:
            cursor.endEditBlock()

        return formatted_count
