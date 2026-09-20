"""Comprehensive test suite for Screenwriting mode, Screenplay Codex, and Drag & Drop Phrases Palette."""

import os
import pytest
from PySide6.QtGui import QTextCursor, QTextBlockFormat, QTextCharFormat, QFont
from PySide6.QtWidgets import QApplication

from volumenodex.core.document_model import DocumentMode, DOCUMENT_MODE_TITLES, PageMargins, PageLayoutModel
from volumenodex.canvas.paper_texture import PaperTextureEngine
from volumenodex.core.theme_manager import ThemeManager
from volumenodex.screenplay.screenplay_model import (
    ScreenplayCharacter,
    ScreenplayScene,
    ScreenplayAct,
    ScreenplayCodexManager,
    ScreenplayPhrase,
    ScreenplayPhraseLibrary,
)
from volumenodex.screenplay.screenplay_formatter import (
    ScreenplayElementType,
    ScreenplayFormatter,
)
from volumenodex.screenplay.screenplay_codex_drawer import ScreenplayCodexDrawer
from volumenodex.screenplay.screenplay_palette_drawer import ScreenplayPaletteDrawer
from volumenodex.canvas.paginated_canvas import PaginatedCanvas
from volumenodex.review.spell_engine import SpellCheckEngine
from volumenodex.pet.insight_engine import InsightEngine


# ==============================================================================
# 1. CORE DOCUMENT MODEL & PRESETS
# ==============================================================================

def test_screenwriting_document_mode_preset():
    """Verify DocumentMode.SCREENWRITING definition and margin presets."""
    assert DocumentMode.SCREENWRITING == "screenwriting"
    assert DocumentMode.SCREENWRITING.value == "screenwriting"
    assert DocumentMode.SCREENWRITING in DOCUMENT_MODE_TITLES
    assert "Screenplay" in DOCUMENT_MODE_TITLES[DocumentMode.SCREENWRITING]

    margins = PageMargins.screenplay()
    # Left margin 1.5 inches, top/right/bottom = 1.0 inch
    assert margins.left == 1.5
    assert margins.right == 1.0
    assert margins.top == 1.0
    assert margins.bottom == 1.0


# ==============================================================================
# 2. SCREENPLAY FORMATTER & ELEMENT CLASSIFIER
# ==============================================================================

def test_screenplay_element_classifier():
    """Verify classification of standard script lines into screenplay element types."""
    # Sluglines / Location Headings
    assert ScreenplayFormatter.classify_line("INT. COFFEE SHOP - DAY") == ScreenplayElementType.SLUGLINE
    assert ScreenplayFormatter.classify_line("EXT. CITY STREET - NIGHT") == ScreenplayElementType.SLUGLINE
    assert ScreenplayFormatter.classify_line("EXTERIOR: HOME - DUSK") == ScreenplayElementType.SLUGLINE
    assert ScreenplayFormatter.classify_line("INTERIOR: WAREHOUSE - CONTINUOUS") == ScreenplayElementType.SLUGLINE
    assert ScreenplayFormatter.classify_line("INT./EXT. CAR - MOVING - DAY") == ScreenplayElementType.SLUGLINE

    # Lighting Prompts / Direction
    assert ScreenplayFormatter.classify_line("LOW LIGHTING, LIT BY STREET LIGHTS ALONE") == ScreenplayElementType.LIGHTING_NOTE
    assert ScreenplayFormatter.classify_line("HARSH OVERHEAD FLUORESCENT LIGHTING") == ScreenplayElementType.LIGHTING_NOTE
    assert ScreenplayFormatter.classify_line("DIM AMBER TUNGSTEN GLOW") == ScreenplayElementType.LIGHTING_NOTE

    # Character Cues
    assert ScreenplayFormatter.classify_line("DETECTIVE MARCUS VANCE") == ScreenplayElementType.CHARACTER
    assert ScreenplayFormatter.classify_line("ELENA ROSTOVA (V.O.)") == ScreenplayElementType.CHARACTER
    assert ScreenplayFormatter.classify_line("POLICE CAPTAIN (O.S.)") == ScreenplayElementType.CHARACTER

    # Parentheticals
    assert ScreenplayFormatter.classify_line("(whispering in fear)") == ScreenplayElementType.PARENTHETICAL
    assert ScreenplayFormatter.classify_line("(beat)") == ScreenplayElementType.PARENTHETICAL

    # Transitions
    assert ScreenplayFormatter.classify_line("FADE IN:") == ScreenplayElementType.TRANSITION
    assert ScreenplayFormatter.classify_line("CUT TO:") == ScreenplayElementType.TRANSITION
    assert ScreenplayFormatter.classify_line("DISSOLVE TO:") == ScreenplayElementType.TRANSITION
    assert ScreenplayFormatter.classify_line("SMASH CUT TO:") == ScreenplayElementType.TRANSITION

    # Act & Scene Markers
    assert ScreenplayFormatter.classify_line("ACT I") == ScreenplayElementType.ACT_MARKER
    assert ScreenplayFormatter.classify_line("ACT II - THE CHASE") == ScreenplayElementType.ACT_MARKER
    assert ScreenplayFormatter.classify_line("SCENE 4") == ScreenplayElementType.SCENE_MARKER

    # Action / Description
    assert ScreenplayFormatter.classify_line("Marcus steps through the puddles, pulling his collar up.") == ScreenplayElementType.ACTION
    assert ScreenplayFormatter.classify_line("The rain drums steadily against the rusted metal roof.") == ScreenplayElementType.ACTION


def test_screenplay_smart_routing():
    """Verify smart Enter flow and smart Tab element cycling."""
    # Smart Enter progression
    assert ScreenplayFormatter.next_element_after_enter(ScreenplayElementType.SLUGLINE) == ScreenplayElementType.ACTION
    assert ScreenplayFormatter.next_element_after_enter(ScreenplayElementType.CHARACTER) == ScreenplayElementType.DIALOGUE
    assert ScreenplayFormatter.next_element_after_enter(ScreenplayElementType.PARENTHETICAL) == ScreenplayElementType.DIALOGUE
    assert ScreenplayFormatter.next_element_after_enter(ScreenplayElementType.DIALOGUE) == ScreenplayElementType.ACTION
    assert ScreenplayFormatter.next_element_after_enter(ScreenplayElementType.TRANSITION) == ScreenplayElementType.SLUGLINE
    assert ScreenplayFormatter.next_element_after_enter(ScreenplayElementType.LIGHTING_NOTE) == ScreenplayElementType.ACTION

    # Smart Tab progression (Forward)
    assert ScreenplayFormatter.cycle_element(ScreenplayElementType.ACTION, reverse=False) == ScreenplayElementType.CHARACTER
    assert ScreenplayFormatter.cycle_element(ScreenplayElementType.CHARACTER, reverse=False) == ScreenplayElementType.PARENTHETICAL
    assert ScreenplayFormatter.cycle_element(ScreenplayElementType.PARENTHETICAL, reverse=False) == ScreenplayElementType.DIALOGUE
    assert ScreenplayFormatter.cycle_element(ScreenplayElementType.DIALOGUE, reverse=False) == ScreenplayElementType.TRANSITION
    assert ScreenplayFormatter.cycle_element(ScreenplayElementType.TRANSITION, reverse=False) == ScreenplayElementType.SLUGLINE
    assert ScreenplayFormatter.cycle_element(ScreenplayElementType.SLUGLINE, reverse=False) == ScreenplayElementType.ACTION

    # Smart Shift-Tab progression (Reverse)
    assert ScreenplayFormatter.cycle_element(ScreenplayElementType.CHARACTER, reverse=True) == ScreenplayElementType.ACTION
    assert ScreenplayFormatter.cycle_element(ScreenplayElementType.ACTION, reverse=True) == ScreenplayElementType.SLUGLINE


def test_screenplay_geometry_specs():
    """Verify screenplay typography specs and margins for standard screenplay layout."""
    slug_spec = ScreenplayFormatter.ELEMENT_SPECS[ScreenplayElementType.SLUGLINE]
    assert slug_spec["left_margin"] == 0
    assert slug_spec["uppercase"] is True
    assert slug_spec["bold"] is True

    char_spec = ScreenplayFormatter.ELEMENT_SPECS[ScreenplayElementType.CHARACTER]
    assert char_spec["left_margin"] == 210.0
    assert char_spec["uppercase"] is True
    assert char_spec["bold"] is True

    dial_spec = ScreenplayFormatter.ELEMENT_SPECS[ScreenplayElementType.DIALOGUE]
    assert dial_spec["left_margin"] == 100.0
    assert dial_spec["right_margin"] == 120.0

    paren_spec = ScreenplayFormatter.ELEMENT_SPECS[ScreenplayElementType.PARENTHETICAL]
    assert paren_spec["left_margin"] == 150.0
    assert paren_spec["italic"] is True

    trans_spec = ScreenplayFormatter.ELEMENT_SPECS[ScreenplayElementType.TRANSITION]
    assert trans_spec["left_margin"] == 360.0


# ==============================================================================
# 3. SCREENPLAY CODEX (Cast, Scenes, Acts & Mentions)
# ==============================================================================

def test_screenplay_codex_manager_crud():
    """Verify ScreenplayCodexManager cast, scene, and act management and serialization."""
    manager = ScreenplayCodexManager()
    assert len(manager.characters) == 0
    assert len(manager.scenes) == 0
    assert len(manager.acts) == 0

    # Load defaults
    manager.init_sample_defaults()
    assert len(manager.characters) >= 2
    assert len(manager.scenes) >= 2
    assert len(manager.acts) >= 2

    marcus = manager.characters[0]
    assert "MARCUS" in marcus.name
    assert marcus.role == "Lead"

    elena = manager.characters[1]
    assert "ELENA" in elena.name
    assert elena.role == "Antagonist"

    # Add custom character
    new_char = ScreenplayCharacter(
        name="CHIEF O'MALLEY",
        role="Supporting",
        aliases=["Chief", "O'Malley"],
        dialogue_voice="Booming Irish-American brogue, cynical."
    )
    manager.add_character(new_char)
    assert len(manager.characters) == 3

    # Mention detection
    match = manager.find_mention("Chief O'Malley banged his fist on the desk.")
    assert match is not None
    assert match.name == "CHIEF O'MALLEY"

    scene_match = manager.find_mention("We need to meet at the Harbor Docks tonight.")
    assert scene_match is not None
    assert scene_match.location_name == "HARBOR DOCKS"

    no_match = manager.find_mention("Just a quiet stroll under the moon.")
    assert no_match is None

    # Remove entity
    manager.remove_character(new_char.id)
    assert len(manager.characters) == 2

    # Serialization Roundtrip
    data = manager.to_dict()
    assert "characters" in data
    assert "scenes" in data
    assert "acts" in data

    new_manager = ScreenplayCodexManager()
    new_manager.from_dict(data)
    assert len(new_manager.characters) == 2
    assert new_manager.characters[0].name == marcus.name
    assert len(new_manager.scenes) == len(manager.scenes)
    assert len(new_manager.acts) == len(manager.acts)


# ==============================================================================
# 4. CATEGORIZED TERMS / PHRASES PALETTE & PERSISTENCE
# ==============================================================================

def test_screenplay_phrase_library(tmp_path):
    """Verify preloaded screenplay terms, categorizations, and custom note persistence."""
    custom_file = str(tmp_path / "test_phrases.json")
    library = ScreenplayPhraseLibrary(custom_file_path=custom_file)

    # Check categories
    categories = library.get_all_categories()
    assert "Headings" in categories
    assert "Light Direction" in categories
    assert "Setting Notes" in categories
    assert "Stage Directions" in categories
    assert "Prop Directions" in categories
    assert "Act & Scene Markers" in categories

    # Check preloaded items
    headings = library.get_phrases_by_category("Headings")
    assert len(headings) >= 6
    ext_home = next((p for p in headings if "EXTERIOR: HOME" in p.text or "EXT. HOME" in p.text), None)
    assert ext_home is not None

    lighting = library.get_phrases_by_category("Light Direction")
    assert len(lighting) >= 5
    street_lights = next((p for p in lighting if "STREET LIGHTS ALONE" in p.text), None)
    assert street_lights is not None

    # Add custom note
    custom_phrase = ScreenplayPhrase(
        category="Custom Notes",
        subcategory="Directorial",
        title="WHISPER MIC INTRO",
        text="[DIRECTOR NOTE: Actor delivers line with extreme proximity effect on lavalier mic.]\n",
        description="High-intimacy audio cue for interrogation scenes.",
        is_custom=True
    )
    library.add_custom_phrase(custom_phrase)

    # Verify custom phrase appears in library
    custom_items = library.get_phrases_by_category("Custom Notes")
    assert len(custom_items) == 1
    assert custom_items[0].title == "WHISPER MIC INTRO"

    # Reload from file and verify persistence
    reloaded_lib = ScreenplayPhraseLibrary(custom_file_path=custom_file)
    reloaded_custom = reloaded_lib.get_phrases_by_category("Custom Notes")
    assert len(reloaded_custom) == 1
    assert reloaded_custom[0].title == "WHISPER MIC INTRO"
    assert "proximity effect" in reloaded_custom[0].text

    # Remove custom phrase
    reloaded_lib.remove_custom_phrase(custom_phrase.id)
    assert len(reloaded_lib.get_phrases_by_category("Custom Notes")) == 0


# ==============================================================================
# 5. CANVAS SCREENWRITING INTEGRATION & TYPOGRAPHY
# ==============================================================================

def test_paginated_canvas_screenwriting(app):
    """Verify PaginatedCanvas behavior under DocumentMode.SCREENWRITING."""
    layout = PageLayoutModel()
    texture = PaperTextureEngine()
    theme = ThemeManager()
    canvas = PaginatedCanvas(layout, texture, theme)
    canvas.resize(800, 1000)
    canvas.set_document_mode(DocumentMode.SCREENWRITING)
    assert canvas.document_mode == DocumentMode.SCREENWRITING

    # Insert snippet via insert_screenplay_snippet
    canvas.insert_screenplay_snippet("EXT. ROOFTOP - MIDNIGHT\n")
    plain = canvas.toPlainText()
    assert "EXT. ROOFTOP - MIDNIGHT" in plain

    # Test applying element formatting
    cursor = QTextCursor(canvas.document())
    cursor.movePosition(QTextCursor.MoveOperation.Start)
    canvas.apply_screenplay_element(ScreenplayElementType.SLUGLINE, cursor)

    fmt = cursor.blockFormat()
    assert fmt.leftMargin() == 0.0

    # Insert dialogue block
    canvas.insert_screenplay_snippet("The wind howls across the gravel.\nMARCUS\nWe only get one shot at this.\n")
    
    # Run autoformat_screenplay
    adjusted_count = canvas.autoformat_screenplay()
    assert adjusted_count >= 1

    canvas.close()


# ==============================================================================
# 6. SPELL CHECK ENGINE SCREENPLAY WHITELIST
# ==============================================================================

def test_spell_engine_screenplay_whitelist():
    """Verify ScreenplayCodexManager cast and scene locations are whitelisted in spellcheck."""
    spell_engine = SpellCheckEngine()
    codex_manager = ScreenplayCodexManager()
    codex_manager.init_sample_defaults()

    spell_engine.sync_story_codex_whitelist(None, codex_manager)

    # Marcus Vance and Elena Rostova and Harbor Docks should be whitelisted
    assert "marcus" in spell_engine.story_whitelist
    assert "vance" in spell_engine.story_whitelist
    assert "elena" in spell_engine.story_whitelist
    assert "rostova" in spell_engine.story_whitelist
    assert "harbor" in spell_engine.story_whitelist
    assert "docks" in spell_engine.story_whitelist


# ==============================================================================
# 7. SCREENPLAY DRAWERS INITIALIZATION
# ==============================================================================

def test_screenplay_drawers_ui(app):
    """Verify initialization and controls of ScreenplayCodexDrawer and ScreenplayPaletteDrawer."""
    codex_mgr = ScreenplayCodexManager()
    codex_mgr.init_sample_defaults()
    codex_drawer = ScreenplayCodexDrawer(codex_mgr)
    assert len(codex_drawer.tab_group.buttons()) == 3  # Cast, Scenes, Acts
    assert codex_drawer.active_tab == "character"
    codex_drawer._switch_tab("scene")
    assert codex_drawer.active_tab == "scene"
    codex_drawer._switch_tab("act")
    assert codex_drawer.active_tab == "act"

    phrase_lib = ScreenplayPhraseLibrary()
    palette_drawer = ScreenplayPaletteDrawer(phrase_lib)
    assert palette_drawer.combo_filter_cat is not None
    assert palette_drawer.search_bar is not None
    assert palette_drawer.btn_add_custom is not None

    # Test category filtering
    idx = palette_drawer.combo_filter_cat.findText("Headings")
    if idx >= 0:
        palette_drawer.combo_filter_cat.setCurrentIndex(idx)
    assert palette_drawer.container_layout.count() > 0

    codex_drawer.close()
    palette_drawer.close()


# ==============================================================================
# 8. PET & INSIGHT ENGINE SCREENPLAY PROMPTS
# ==============================================================================

def test_insight_engine_screenplay_mode():
    """Verify pet insight engine adapts prompts when in Screenwriting mode."""
    engine = InsightEngine()
    engine.set_document_mode(DocumentMode.SCREENWRITING)
    assert engine.document_mode == DocumentMode.SCREENWRITING

    received_messages = []
    engine.messageReady.connect(lambda msg, mood: received_messages.append((msg, mood)))

    engine.trigger_creative_spark()
    assert len(received_messages) == 1
    msg, mood = received_messages[0]
    assert "Screenplay Spark" in msg
    assert any(p in msg for p in InsightEngine.SCREENPLAY_PROMPTS)


# ==============================================================================
# 9. MAIN WINDOW SCREENPLAY INTEGRATION & IO PERSISTENCE
# ==============================================================================

def test_main_window_screenwriting_mode(app):
    """Verify MainWindow UI, drawers, and template generation for Screenwriting mode."""
    from volumenodex.ui.main_window import MainWindow

    win = MainWindow()
    win.set_document_mode(DocumentMode.SCREENWRITING)

    assert win.document_mode == DocumentMode.SCREENWRITING
    assert win.canvas_area.document_mode == DocumentMode.SCREENWRITING
    assert win.right_stack.currentWidget() == win.screenplay_codex

    # Switch to Palette drawer
    win.show_screenplay_palette()
    assert win.right_stack.currentWidget() == win.screenplay_palette

    # Switch back to Codex drawer
    win.show_screenplay_codex()
    assert win.right_stack.currentWidget() == win.screenplay_codex

    # Verify template generation
    tmpl = win._generate_mode_template("Test Script", DocumentMode.SCREENWRITING)
    assert "FADE IN:" in tmpl
    assert "EXT. HARBOR DOCKS - NIGHT" in tmpl
    assert "MARCUS" in tmpl

    win.close()


def test_screenplay_document_save_load(app, tmp_path):
    """Verify saving a screenplay document with Screenplay Codex and reloading it."""
    from volumenodex.ui.main_window import MainWindow

    win = MainWindow()
    win.set_document_mode(DocumentMode.SCREENWRITING)

    # Add custom character
    new_char = ScreenplayCharacter(
        name="DETECTIVE STONE",
        role="Supporting",
        aliases=["Stone"],
        notes="Undercover narcotics liaison"
    )
    win.screenplay_codex_manager.add_character(new_char)

    # Insert script snippet
    win.canvas_area.insert_screenplay_snippet("EXT. ROOFTOP - NIGHT\nDETECTIVE STONE\nKeep your radio on.\n")

    # Save document
    save_path = str(tmp_path / "test_screenplay.docx")
    win.current_file_path = save_path
    saved = win.save_document()
    assert saved is True
    assert os.path.exists(save_path)

    # Reload into a new window
    win2 = MainWindow()
    loaded = win2._load_file(save_path)
    assert loaded is True
    assert win2.document_mode == DocumentMode.SCREENWRITING

    # Verify Screenplay Codex was restored
    stone = next((c for c in win2.screenplay_codex_manager.characters if c.name == "DETECTIVE STONE"), None)
    assert stone is not None
    assert stone.notes == "Undercover narcotics liaison"

    win.close()
    win2.close()


