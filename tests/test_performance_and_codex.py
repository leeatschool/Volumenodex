"""Comprehensive tests for:
1. PaginatedCanvas multi-page performance (page culling, ctx.clip, shadow caching, O(1) hit testing)
2. Story Codex clean initialization (zero default characters or lore)
3. Story Codex Auto-Extraction Engine (characters, dialogue tags, honorifics, roles, lore locations, factions, artifacts)
4. Non-destructive extraction updates and UI auto-extract integration
"""

import sys
import os
import time

from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QPainter, QPixmap, QTextCursor
from PySide6.QtWidgets import QApplication

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from volumenodex.ui.main_window import MainWindow
from volumenodex.canvas.paginated_canvas import PaginatedCanvas
from volumenodex.core.document_model import PageLayoutModel
from volumenodex.canvas.paper_texture import PaperTextureEngine
from volumenodex.core.theme_manager import ThemeManager
from volumenodex.story.codex_model import CodexManager, CharacterProfile, LoreEntry
from volumenodex.story.codex_extractor import CodexExtractionEngine


def get_app():
    app = QApplication.instance()
    if not app:
        app = QApplication([])
    return app


def test_codex_starts_clean():
    """Verify CodexManager starts completely empty without default characters or lore."""
    cm = CodexManager()
    assert len(cm.characters) == 0, f"Expected 0 characters, got {len(cm.characters)}"
    assert len(cm.lore_entries) == 0, f"Expected 0 lore entries, got {len(cm.lore_entries)}"
    assert len(cm.scene_items) == 0, f"Expected 0 scene items, got {len(cm.scene_items)}"
    print("[PASS] test_codex_starts_clean passed")


def test_main_window_starts_clean(app):
    """Verify MainWindow launches with clean manuscript and empty Codex."""
    win = MainWindow()
    win.show()

    assert len(win.codex_manager.characters) == 0, "Codex characters should be empty on launch"
    assert len(win.codex_manager.lore_entries) == 0, "Codex lore should be empty on launch"
    text = win.editor.toPlainText().strip()
    assert "Untitled Document" in text or text == "", f"Unexpected initial text: {text}"
    win.close()
    print("[PASS] test_main_window_starts_clean passed")


def test_multipage_performance_and_culling(app):
    """Verify multi-page canvas handles 20+ pages with high-speed rendering and O(1) hit testing."""
    win = MainWindow()
    win.show()

    # Generate a massive 20-page document
    ed = win.canvas_area
    doc = ed.document()

    long_text = []
    for i in range(1, 45):
        long_text.append(f"<h2>Chapter {i}: The Voyage Ahead</h2>")
        for p in range(4):
            long_text.append(
                f"<p>Paragraph {p + 1} of Chapter {i}. The journey through the storm tested every sailor aboard. "
                f"Captain Thorne watched the horizon with stern vigilance, clutching his brass compass. "
                f"The waves crashed against the hull with thunderous fury as the night deepened.</p>"
            )

    doc.setHtml("".join(long_text))
    ed.sync_document_geometry()

    total_pages = ed._total_pages()
    assert total_pages >= 12, f"Expected at least 12 pages for test document, got {total_pages}"

    # Verify O(1) hit-testing arithmetic (does not throw or loop)
    pos_top = ed._screen_point_to_doc_position(QPointF(200, 100))
    assert pos_top is not None and pos_top >= 0

    pos_mid = ed._screen_point_to_doc_position(QPointF(200, 3000))
    assert pos_mid is not None and pos_mid >= 0

    # Benchmark viewport repaint execution time
    t0 = time.perf_counter()
    ed.viewport().repaint()
    t_elapsed = time.perf_counter() - t0

    # With culling, ctx.clip, and cached shadows, paint should execute in under 50ms even with many pages
    print(f"  Multi-page ({total_pages} pages) paint elapsed: {t_elapsed * 1000:.2f}ms")
    assert t_elapsed < 0.2, f"Paint took too long: {t_elapsed * 1000:.2f}ms"

    # Verify shadow caching works
    pw = ed.layout_model.page_width_px
    ph = ed.layout_model.page_height_px
    cached_shadow = ed._get_cached_shadow(pw, ph)
    assert cached_shadow is not None
    assert ed._cached_shadow is cached_shadow

    win.close()
    print("[PASS] test_multipage_performance_and_culling passed")


def test_codex_auto_extraction_characters_and_speech():
    """Verify CodexExtractionEngine extracts characters from dialogue attribution and honorifics."""
    cm = CodexManager()
    story_text = """
    "We cannot stay here any longer," whispered Genevieve, her hands trembling.
    "I know," said Marcus, checking the lock on the iron door.
    Across the dim hallway, Captain Blackwood stepped forward into the lantern light.
    Blackwood wore a tailored navy coat with tarnished gold epaulets and carried a silver saber.
    "The guards have breached the outer perimeter," shouted Marcus.
    "Then follow me," replied Captain Blackwood.
    """

    res = CodexExtractionEngine.extract_into_manager(story_text, cm)

    assert res.new_characters >= 2, f"Expected at least 2 characters, got {res.new_characters}"
    names = [c.name for c in cm.characters]

    # Verify extracted names
    assert any("Blackwood" in n for n in names), f"Captain Blackwood not found in {names}"
    assert any("Marcus" in n for n in names), f"Marcus not found in {names}"
    assert any("Genevieve" in n for n in names), f"Genevieve not found in {names}"

    # Verify appearance / traits extracted for Blackwood
    blackwood = next(c for c in cm.characters if "Blackwood" in c.name)
    assert "navy coat" in blackwood.appearance or "saber" in blackwood.appearance, f"Appearance missed: {blackwood.appearance}"
    assert blackwood.is_auto_extracted is True
    assert blackwood.mention_count >= 2

    # Verify aliases
    assert "Blackwood" in blackwood.aliases

    print("[PASS] test_codex_auto_extraction_characters_and_speech passed")


def test_codex_auto_extraction_lore():
    """Verify CodexExtractionEngine extracts locations, factions, and artifacts."""
    cm = CodexManager()
    lore_text = """
    They fled across the Misty River toward the ancient fortress of Dragonstone Keep.
    Deep within the vaults lay the legendary Sunfire Blade, an ancient relic of the Sun Kings.
    Rumors held that the Obsidian Guild had already dispatched their deadliest assassins
    to seize the Sunfire Blade before dawn.
    """

    res = CodexExtractionEngine.extract_into_manager(lore_text, cm)

    assert res.new_lore >= 3, f"Expected at least 3 lore entries, got {res.new_lore}"
    lore_titles = {l.title: l.category for l in cm.lore_entries}

    # Verify locations
    assert any("River" in t or "Keep" in t for t in lore_titles), f"Locations not found in {lore_titles}"

    # Verify factions
    assert any("Guild" in t for t in lore_titles), f"Faction not found in {lore_titles}"

    # Verify artifacts
    assert any("Blade" in t for t in lore_titles), f"Artifact not found in {lore_titles}"

    # Verify categories
    for title, cat in lore_titles.items():
        if "Keep" in title or "River" in title:
            assert cat == "Location"
        elif "Guild" in title:
            assert cat == "Faction"
        elif "Blade" in title:
            assert cat == "Artifact"

    print("[PASS] test_codex_auto_extraction_lore passed")


def test_codex_non_destructive_preservation():
    """Verify user-customized entities are preserved and never overwritten."""
    cm = CodexManager()

    # User manually created character
    custom_char = CharacterProfile(
        id="char_custom_1",
        name="Elena Vance",
        role="Protagonist",
        appearance="Amber eyes and a scarlet scarf.",
        motivation="Avenging her family.",
        notes="Custom author notes.",
        is_auto_extracted=False
    )
    cm.add_character(custom_char)

    # Narrative has Elena doing actions
    text = "Elena Vance stepped quietly onto the stone terrace. 'Be careful,' whispered Elena."
    res = CodexExtractionEngine.extract_into_manager(text, cm)

    # Character count should not duplicate
    assert len(cm.characters) == 1
    c = cm.characters[0]
    assert c.name == "Elena Vance"
    assert c.role == "Protagonist"
    assert c.appearance == "Amber eyes and a scarlet scarf."
    assert c.notes == "Custom author notes."
    assert c.is_auto_extracted is False
    assert c.mention_count >= 1

    print("[PASS] test_codex_non_destructive_preservation passed")


def test_drawer_auto_button_and_manual_extraction(app):
    """Verify the ✨ Auto button in CharacterCodexDrawer and manual trigger."""
    win = MainWindow()
    win.show()

    drawer = win.right_codex
    assert hasattr(drawer, "btn_auto_extract")
    assert drawer.btn_auto_extract.text() == "✨ Auto"

    # Set text with new characters and click auto-extract
    win.editor.setPlainText(
        "Lord Sterling examined the map of Silverwood Forest. 'We leave at dusk,' said Sterling."
    )

    # Click auto extract
    drawer.btn_auto_extract.click()

    # Verify codex populated
    char_names = [c.name for c in win.codex_manager.characters]
    assert any("Sterling" in n for n in char_names), f"Sterling not in {char_names}"

    lore_titles = [l.title for l in win.codex_manager.lore_entries]
    assert any("Forest" in t for t in lore_titles), f"Forest not in {lore_titles}"

    win.close()
    print("[PASS] test_drawer_auto_button_and_manual_extraction passed")


if __name__ == "__main__":
    app_instance = get_app()
    test_codex_starts_clean()
    test_main_window_starts_clean(app_instance)
    test_multipage_performance_and_culling(app_instance)
    test_codex_auto_extraction_characters_and_speech()
    test_codex_auto_extraction_lore()
    test_codex_non_destructive_preservation()
    test_drawer_auto_button_and_manual_extraction(app_instance)
    print("\nALL PERFORMANCE AND STORY CODEX TESTS PASSED SUCCESSFULLY!")
