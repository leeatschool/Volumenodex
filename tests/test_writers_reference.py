"""Unit and integration tests for Writers Reference knowledge base, search, and builder tool."""

import os
import tempfile
import pytest
from PySide6.QtWidgets import QApplication

from volumenodex.reference.reference_model import ReferenceEntry, ReferenceCategory
from volumenodex.reference.reference_manager import ReferenceManager
from volumenodex.reference.builder_tool import ReferenceEntryEditorDialog, ReferenceBuilderWindow
from volumenodex.ui.writers_reference_dialog import WritersReferenceDialog
from volumenodex.ui.ribbon import RibbonBar
from volumenodex.ui.main_window import MainWindow


@pytest.fixture(scope="session")
def app():
    return QApplication.instance() or QApplication([])


def test_reference_entry_model():
    entry = ReferenceEntry(
        id="test-topic",
        title="Test Topic Title",
        category=ReferenceCategory.WEAPONS_WARFARE,
        tags=["swords", "combat", "steel"],
        summary="A test summary of weapons.",
        quick_facts={"Range": "Close", "Weight": "2 lbs"},
        content="Detailed combat mechanics here.",
        fiction_tips="Avoid slow swinging clichés.",
        is_custom=True,
    )
    d = entry.to_dict()
    assert d["id"] == "test-topic"
    assert d["title"] == "Test Topic Title"
    assert d["category"] == ReferenceCategory.WEAPONS_WARFARE
    assert "swords" in d["tags"]
    assert d["quick_facts"]["Range"] == "Close"
    assert d["is_custom"] is True

    reconstituted = ReferenceEntry.from_dict(d)
    assert reconstituted.id == entry.id
    assert reconstituted.title == entry.title
    assert reconstituted.quick_facts == entry.quick_facts

    # Test relevance scoring
    matches, score_exact = entry.matches_query("Test Topic")
    assert matches is True
    assert score_exact > 100

    matches_tag, score_tag = entry.matches_query("swords")
    assert matches_tag is True
    assert score_tag > 0

    matches_fact, score_fact = entry.matches_query("Range")
    assert matches_fact is True

    matches_none, score_none = entry.matches_query("spaceship")
    assert matches_none is False
    assert score_none == 0


def test_reference_manager_bundled():
    with tempfile.TemporaryDirectory() as tmpdir:
        rm = ReferenceManager(user_storage_dir=tmpdir)
        assert rm.total_count >= 20, f"Expected at least 20 bundled entries, got {rm.total_count}"

        # Test search
        results_poison = rm.search("poison")
        assert len(results_poison) >= 1
        titles = [e.title for e in results_poison]
        assert any("Arsenic" in t or "Cyanide" in t for t in titles)

        # Test category filtering
        results_nautical = rm.search(category=ReferenceCategory.NAUTICAL_SAILING)
        assert len(results_nautical) >= 2
        for e in results_nautical:
            assert e.category == ReferenceCategory.NAUTICAL_SAILING

        # Test categories and tags extraction
        cats = rm.get_categories()
        assert ReferenceCategory.POISONS_MEDICINE in cats
        assert ReferenceCategory.WEAPONS_WARFARE in cats

        tags = rm.get_tags()
        assert "poison" in tags or "arsenic" in tags


def test_reference_manager_custom_entries():
    with tempfile.TemporaryDirectory() as tmpdir:
        rm = ReferenceManager(user_storage_dir=tmpdir)
        initial_count = rm.total_count

        custom_entry = ReferenceEntry(
            id="custom-magic-poison",
            title="Grave-Lotus Nectar",
            category="Dark Fantasy Alchemy",
            tags=["lotus", "necromancy", "sleep"],
            summary="A mystical poison that induces death-like torpor.",
            quick_facts={"Duration": "24 Hours", "Taste": "Bitter Honey"},
            content="Extracted from black lotuses growing in burial grounds.",
            fiction_tips="Great for faking a character's death.",
            is_custom=True,
        )

        success = rm.add_or_update_entry(custom_entry)
        assert success is True
        assert rm.total_count == initial_count + 1
        assert rm.custom_count == 1

        # Test persistence across reloads
        rm2 = ReferenceManager(user_storage_dir=tmpdir)
        assert rm2.total_count == initial_count + 1
        loaded = rm2.get_entry("custom-magic-poison")
        assert loaded is not None
        assert loaded.title == "Grave-Lotus Nectar"
        assert loaded.is_custom is True

        # Test deleting custom entry
        del_success = rm2.delete_entry("custom-magic-poison")
        assert del_success is True
        assert rm2.total_count == initial_count
        assert rm2.get_entry("custom-magic-poison") is None


def test_reference_manager_import_export():
    with tempfile.TemporaryDirectory() as tmpdir:
        rm = ReferenceManager(user_storage_dir=tmpdir)
        export_file = os.path.join(tmpdir, "export.json")

        success = rm.export_to_json(export_file, include_bundled=True)
        assert success is True
        assert os.path.exists(export_file)

        # Import into a separate manager
        with tempfile.TemporaryDirectory() as tmpdir2:
            rm2 = ReferenceManager(user_storage_dir=tmpdir2)
            imported_count = rm2.import_from_json(export_file)
            assert imported_count >= 20


def test_writers_reference_dialog_ui(app):
    with tempfile.TemporaryDirectory() as tmpdir:
        rm = ReferenceManager(user_storage_dir=tmpdir)
        dlg = WritersReferenceDialog(manager=rm)
        assert dlg.list_results.count() == rm.total_count

        # Test search filter
        dlg.edit_search.setText("arsenic")
        assert dlg.list_results.count() >= 1
        assert "Arsenic" in dlg.list_results.item(0).text()

        # Test category chip filter
        dlg.edit_search.clear()
        dlg._on_category_chip_clicked(ReferenceCategory.NAUTICAL_SAILING)
        assert dlg.list_results.count() >= 2

        # Test copy facts feedback
        dlg._copy_facts_to_clipboard()
        assert "Copied" in dlg.btn_copy_facts.text()

        # Test insert into manuscript signal
        received_text = []
        dlg.insertIntoDocumentRequested.connect(lambda t: received_text.append(t))
        dlg._insert_current_into_document()
        assert len(received_text) == 1
        assert "WRITERS REFERENCE:" in received_text[0]
        assert "Inserted" in dlg.btn_insert.text()

        dlg.close()


def test_ribbon_integration(app):
    ribbon = RibbonBar()
    assert hasattr(ribbon, "btn_header_reference")
    assert hasattr(ribbon, "btn_writers_reference")

    signals_fired = []
    ribbon.writersReferenceRequested.connect(lambda: signals_fired.append(True))

    ribbon.btn_header_reference.click()
    assert len(signals_fired) == 1

    ribbon.btn_writers_reference.click()
    assert len(signals_fired) == 2


def test_main_window_writers_reference(app):
    win = MainWindow()
    win.show()
    app.processEvents()

    # Verify menu action exists
    actions = [a.text() for a in win.menuBar().actions()]
    assert any("&View" in a for a in actions)

    # Trigger opening writers reference
    win.open_writers_reference()
    dlg = win.writers_reference_dialog
    assert dlg is not None
    assert dlg.isVisible()

    # Test inserting text via dialog signal
    init_text = win.canvas_area._cursor.document().toPlainText()
    dlg._insert_current_into_document()
    app.processEvents()
    after_text = win.canvas_area._cursor.document().toPlainText()
    assert len(after_text) > len(init_text)
    assert "WRITERS REFERENCE:" in after_text

    win.editor.document().setModified(False)
    dlg.close()
    win.close()
