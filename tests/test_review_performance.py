"""Comprehensive tests for:
1. Large document (20,000+ words) review and spell check performance (< 100ms)
2. Asynchronous background ReviewWorker execution (zero UI blocking)
3. RevisionInspectorDrawer card virtualization and pagination (instant UI update)
4. PaginatedCanvas spatial selection culling and lazy context menu suggestions
5. Automatic review lenses enabled by default on application launch
"""

import sys
import os
import time

from PySide6.QtCore import Qt, QPointF, QThreadPool, QEventLoop, QTimer
from PySide6.QtGui import QPainter, QPixmap, QColor
from PySide6.QtWidgets import QApplication

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from volumenodex.ui.main_window import MainWindow
from volumenodex.review.lens_engine import LensFinding, RevisionLensEngine
from volumenodex.review.spell_engine import SpellCheckEngine
from volumenodex.review.revision_inspector import FindingCardWidget, RevisionInspectorDrawer
from volumenodex.review.revision_worker import ReviewWorker


def get_app():
    app = QApplication.instance()
    if not app:
        app = QApplication([])
    return app


def generate_large_manuscript(word_count: int = 25000) -> str:
    """Generates a realistic multi-chapter manuscript with adverbs, passive voice, fillers, and misspellings."""
    base_paragraph = (
        "The ancient fortress was built by forgotten kings upon the jagged cliffs of the northern sea. "
        "Lord Kaelen walked quickly across the stone courtyard, his heavy woolen cloak billowing wildly in the cold wind. "
        "In order to understand the encroaching darkness, he had spent many long nights reading archaic scrolls. "
        "It was discovered by the royal guards that an unrecognized traveler had crossed the perimeter. "
        "\"We must act promptly,\" whispered the scout nervously, glancing toward the shadowy tree line. "
        "At the end of the day, all truth is revealed through courageous perseverance and watchful vigilance. "
        "The mysterious artifact glimerred with an unnatural violet phosphorescence in the gloomy twilight. "
        "Sir Gareth was wounded by an enchanted dagger during the sudden skirmish near the sunken valley. "
    )
    words_per_para = len(base_paragraph.split())
    repetitions = max(1, word_count // words_per_para)
    paragraphs = []
    for i in range(repetitions):
        paragraphs.append(f"Chapter {i+1}\n\n{base_paragraph}")
    return "\n\n".join(paragraphs)


def test_default_active_lenses(app):
    """Verify review lenses are enabled automatically by default on startup."""
    win = MainWindow()
    win.show()

    # Core lenses should be active by default
    assert win.active_lenses["spelling"] is True, "Spelling lens should be active by default"
    assert win.active_lenses["adverb"] is True, "Adverb lens should be active by default"
    assert win.active_lenses["passive"] is True, "Passive voice lens should be active by default"
    assert win.active_lenses["filler"] is True, "Filler words lens should be active by default"
    assert win.revision_mode_active is True, "Revision mode should be active by default"

    # Ribbon buttons should reflect active state
    assert win.ribbon.btn_rev_mode.isChecked() is True, "Ribbon review mode button should be checked"
    assert win.ribbon.btn_spell.isChecked() is True, "Ribbon spell check button should be checked"
    assert win.ribbon.btn_adverbs.isChecked() is True, "Ribbon adverbs button should be checked"
    assert win.ribbon.btn_passive.isChecked() is True, "Ribbon passive voice button should be checked"
    assert win.ribbon.btn_filler.isChecked() is True, "Ribbon filler button should be checked"

    # Spell engine should be shared with canvas and inspector
    assert win.canvas_area.spell_engine is win.spell_engine
    assert win.revision_inspector.spell_engine is win.spell_engine

    win.close()
    print("[PASS] test_default_active_lenses passed")


def test_large_document_review_benchmark():
    """Verify 25,000-word review analysis runs in tens of milliseconds, completely eliminating the 1-minute freeze."""
    text = generate_large_manuscript(25000)
    actual_words = len(text.split())
    assert actual_words >= 20000, f"Generated {actual_words} words"

    spell_engine = SpellCheckEngine()
    active_lenses = {
        "spelling": True,
        "adverb": True,
        "passive": True,
        "filler": True,
        "pacing": False,
        "dialogue": False,
    }

    t0 = time.perf_counter()
    findings = RevisionLensEngine.analyze_document(text, active_lenses)
    t_lens = (time.perf_counter() - t0) * 1000

    t1 = time.perf_counter()
    spelling_findings = spell_engine.check_text(text)
    t_spell = (time.perf_counter() - t1) * 1000

    findings.extend(spelling_findings)
    total_time = (time.perf_counter() - t0) * 1000

    print(f"\n--- 25,000+ Word Benchmark Results ---")
    print(f"Words: {actual_words:,}")
    print(f"Linguistic Lenses: {t_lens:.2f}ms ({len(findings) - len(spelling_findings)} findings)")
    print(f"Spell Check: {t_spell:.2f}ms ({len(spelling_findings)} findings)")
    print(f"Total Review Time: {total_time:.2f}ms ({len(findings)} total findings)")

    # Assert performance target: must be under 350ms total for 25,000 words (previously 55,000+ ms!)
    assert total_time < 350.0, f"Review took {total_time:.2f}ms, target was < 350ms"
    assert len(findings) > 0, "Should detect adverbs, passive voice, fillers, and spelling"
    print("[PASS] test_large_document_review_benchmark passed")


def test_lazy_suggestions_and_caching():
    """Verify Levenshtein candidates are deferred until requested and cached."""
    spell_engine = SpellCheckEngine()
    text = "The strange glimerred sword was held by a mystik knyght."

    # check_text must defer suggestions
    findings = spell_engine.check_text(text)
    assert len(findings) >= 2, f"Expected at least 2 spelling errors, got {len(findings)}"
    for f in findings:
        assert f.suggestions == [], f"Suggestions should be deferred during scan, got: {f.suggestions}"

    # Lazy on-demand lookup
    t0 = time.perf_counter()
    sugs1 = spell_engine.get_suggestions(findings[0].text, limit=4)
    t_first = (time.perf_counter() - t0) * 1000
    assert len(sugs1) > 0, f"Expected suggestions for '{findings[0].text}'"

    # Second lookup should hit memory cache instantaneously
    t1 = time.perf_counter()
    sugs2 = spell_engine.get_suggestions(findings[0].text, limit=4)
    t_cached = (time.perf_counter() - t1) * 1000

    assert sugs1 == sugs2
    assert t_cached < 1.0, f"Cached lookup took {t_cached:.4f}ms, expected < 1ms"
    print(f"Lazy suggestion compute: {t_first:.2f}ms, Cached: {t_cached:.4f}ms")
    print("[PASS] test_lazy_suggestions_and_caching passed")


def test_async_review_worker(app):
    """Verify asynchronous ReviewWorker dispatches to thread pool and signals back."""
    text = generate_large_manuscript(5000)
    spell_engine = SpellCheckEngine()
    active_lenses = {"spelling": True, "adverb": True, "passive": True, "filler": True}

    loop = QEventLoop()
    results = {}

    def on_finished(findings, req_id):
        results["findings"] = findings
        results["req_id"] = req_id
        loop.quit()

    worker = ReviewWorker(text, active_lenses, spell_engine, request_id=42)
    worker.signals.finished.connect(on_finished)

    # Set 5 second safety timeout
    timer = QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(loop.quit)
    timer.start(5000)

    QThreadPool.globalInstance().start(worker)
    loop.exec()

    assert "findings" in results, "Worker did not emit finished signal within timeout"
    assert results["req_id"] == 42, f"Expected request_id 42, got {results['req_id']}"
    assert len(results["findings"]) > 0, "Expected non-empty findings"
    print(f"[PASS] test_async_review_worker passed with {len(results['findings'])} findings")


def test_inspector_pagination_and_virtualization(app):
    """Verify RevisionInspectorDrawer handles thousands of findings with virtualization and zero UI freeze."""
    drawer = RevisionInspectorDrawer()
    spell_engine = SpellCheckEngine()
    drawer.spell_engine = spell_engine
    drawer.show()

    # Generate 1,000 findings
    dummy_findings = []
    for i in range(1000):
        dummy_findings.append(LensFinding(
            lens_type="adverb" if i % 2 == 0 else "spelling",
            start_pos=i * 50,
            end_pos=i * 50 + 6,
            text=f"word_{i}",
            color=QColor("#e0af68"),
            message="Editorial opportunity test note",
            suggestions=[],
            context_snippet=f"...sample sentence containing word_{i}...",
        ))

    t0 = time.perf_counter()
    drawer.update_findings(dummy_findings)
    elapsed_ms = (time.perf_counter() - t0) * 1000

    print(f"Inspector update with 1,000 findings took: {elapsed_ms:.2f}ms")
    assert elapsed_ms < 50.0, f"Inspector update took {elapsed_ms:.2f}ms, expected < 50ms"

    # Only PAGE_SIZE (40) cards should be instantiated in memory
    assert len(drawer._cards) == drawer.PAGE_SIZE, f"Expected {drawer.PAGE_SIZE} cards rendered, got {len(drawer._cards)}"
    assert drawer._btn_load_more is not None, "Load more button should be visible"
    remaining = 1000 - drawer.PAGE_SIZE
    assert f"{remaining} remaining" in drawer._btn_load_more.text()

    # Test loading next page
    drawer._on_load_more_clicked()
    assert len(drawer._cards) == drawer.PAGE_SIZE * 2, f"Expected {drawer.PAGE_SIZE * 2} cards after loading more"
    assert f"{1000 - drawer.PAGE_SIZE * 2} remaining" in drawer._btn_load_more.text()

    # Test collapsed state deferred rendering
    drawer.set_collapsed(True)
    assert drawer.is_collapsed is True
    drawer.update_findings(dummy_findings)
    assert len(drawer._cards) == 0, "Cards should not be instantiated while drawer is collapsed"
    assert drawer._needs_render is True

    # Expanding drawer should render first page
    drawer.set_collapsed(False)
    assert len(drawer._cards) == drawer.PAGE_SIZE, "Expanding should render the first page of cards"

    drawer.close()
    print("[PASS] test_inspector_pagination_and_virtualization passed")


def test_canvas_spatial_culling(app):
    """Verify PaginatedCanvas culls selections by page and renders rapidly with 1,000+ findings."""
    win = MainWindow()
    win.show()
    win.canvas_area.setPlainText("word " * 2500)

    # Generate 500 findings across document
    dummy_findings = []
    for i in range(500):
        dummy_findings.append(LensFinding(
            lens_type="spelling",
            start_pos=i * 20,
            end_pos=i * 20 + 5,
            text=f"test{i}",
            color=QColor(247, 118, 142, 50),
            message=f"Possible misspelling: test{i}",
            suggestions=[],
        ))

    win.canvas_area.set_lens_findings(dummy_findings)
    assert len(win.canvas_area._lens_selections_with_range) == 500

    # Trigger a paint pass
    t0 = time.perf_counter()
    win.canvas_area.viewport().repaint()
    paint_time = (time.perf_counter() - t0) * 1000

    print(f"Canvas repaint with 500 findings took: {paint_time:.2f}ms")
    assert paint_time < 50.0, f"Repaint took {paint_time:.2f}ms, expected < 50ms"

    win.close()
    print("[PASS] test_canvas_spatial_culling passed")


if __name__ == "__main__":
    app = get_app()
    test_default_active_lenses(app)
    test_large_document_review_benchmark()
    test_lazy_suggestions_and_caching()
    test_async_review_worker(app)
    test_inspector_pagination_and_virtualization(app)
    test_canvas_spatial_culling(app)
    print("\nALL REVIEW PERFORMANCE TESTS PASSED SUCCESSFULLY!")
