"""Unit and integration tests for Writers Reference knowledge base, search, and standalone builder tool."""

import os
import tempfile
import pytest
from PySide6.QtWidgets import QApplication

from volumenodex.reference.reference_model import ReferenceEntry, ReferenceCategory
from volumenodex.reference.reference_manager import ReferenceManager
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


def test_reference_manager_bundled_initial_state():
    rm = ReferenceManager()
    # Bundled knowledge contains the curated encyclopedic reference library
    assert rm.total_count >= 200
    assert rm.custom_count == 0
    categories = rm.get_categories()
    assert len(categories) >= 5


def test_reference_manager_empty_and_custom_entries():
    with tempfile.TemporaryDirectory() as tmpdir:
        empty_bundled = os.path.join(tmpdir, "empty_bundled.json")
        rm = ReferenceManager(user_storage_dir=tmpdir, bundled_path=empty_bundled)
        assert rm.total_count == 0

        custom_entry = ReferenceEntry(
            id="custom-magic-poison",
            title="Grave-Lotus Nectar",
            category=ReferenceCategory.POISONS_MEDICINE,
            tags=["lotus", "necromancy", "sleep", "poison"],
            summary="A mystical poison that induces death-like torpor.",
            quick_facts={"Duration": "24 Hours", "Taste": "Bitter Honey"},
            content="Extracted from black lotuses growing in burial grounds.",
            fiction_tips="Great for faking a character's death.",
            is_custom=True,
        )

        success = rm.add_or_update_entry(custom_entry)
        assert success is True
        assert rm.total_count == 1
        assert rm.custom_count == 1

        # Search
        results = rm.search("poison")
        assert len(results) == 1
        assert results[0].title == "Grave-Lotus Nectar"

        # Category filter
        results_cat = rm.search(category=ReferenceCategory.POISONS_MEDICINE)
        assert len(results_cat) == 1

        # Persistence across reloads
        rm2 = ReferenceManager(user_storage_dir=tmpdir, bundled_path=empty_bundled)
        assert rm2.total_count == 1
        loaded = rm2.get_entry("custom-magic-poison")
        assert loaded is not None
        assert loaded.title == "Grave-Lotus Nectar"

        # Deleting custom entry
        del_success = rm2.delete_entry("custom-magic-poison")
        assert del_success is True
        assert rm2.total_count == 0


def test_reference_manager_import_export():
    with tempfile.TemporaryDirectory() as tmpdir:
        empty_bundled = os.path.join(tmpdir, "empty_bundled.json")
        rm = ReferenceManager(user_storage_dir=tmpdir, bundled_path=empty_bundled)
        entry = ReferenceEntry(
            id="test-topic-1",
            title="Test Topic",
            category=ReferenceCategory.WEAPONS_WARFARE,
            summary="Summary here.",
            is_custom=True,
        )
        rm.add_or_update_entry(entry)

        export_file = os.path.join(tmpdir, "export.json")
        success = rm.export_to_json(export_file, include_bundled=True)
        assert success is True
        assert os.path.exists(export_file)

        # Import into separate manager
        with tempfile.TemporaryDirectory() as tmpdir2:
            rm2 = ReferenceManager(user_storage_dir=tmpdir2, bundled_path=empty_bundled)
            imported_count = rm2.import_from_json(export_file)
            assert imported_count == 1
            assert rm2.total_count == 1


def test_writers_reference_dialog_ui(app):
    with tempfile.TemporaryDirectory() as tmpdir:
        empty_bundled = os.path.join(tmpdir, "empty_bundled.json")
        rm = ReferenceManager(user_storage_dir=tmpdir, bundled_path=empty_bundled)
        # Empty state
        dlg = WritersReferenceDialog(manager=rm)
        assert dlg.lbl_logo.pixmap() is not None
        assert not dlg.lbl_logo.pixmap().isNull()
        assert dlg.list_results.count() == 0
        assert "Empty" in dlg.text_browser.toHtml()

        # Add an entry to test interactions
        entry = ReferenceEntry(
            id="sample-flintlock",
            title="Flintlock Firearms",
            category=ReferenceCategory.WEAPONS_WARFARE,
            tags=["flintlock", "blackpowder"],
            summary="Blackpowder mechanics.",
            quick_facts={"Range": "50 yards", "Reload": "20s"},
            content="Striking flint against steel.",
            fiction_tips="Rain ruins powder.",
            is_custom=True,
        )
        rm.add_or_update_entry(entry)
        dlg._refresh_results()
        assert dlg.list_results.count() == 1

        # Test search filter
        dlg.edit_search.setText("flintlock")
        assert dlg.list_results.count() == 1
        assert "Flintlock" in dlg.list_results.item(0).text()

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

    # Add a temporary entry to test insert
    entry = ReferenceEntry(
        id="test-entry",
        title="Test Entry Title",
        category="Test Category",
        summary="Test summary.",
        is_custom=True,
    )
    dlg.manager.add_or_update_entry(entry)
    dlg._refresh_results()

    init_text = win.canvas_area._cursor.document().toPlainText()
    dlg._insert_current_into_document()
    app.processEvents()
    after_text = win.canvas_area._cursor.document().toPlainText()
    assert len(after_text) > len(init_text)
    assert "WRITERS REFERENCE:" in after_text

    # Clean up test entry so user's database stays clean
    dlg.manager.delete_entry("test-entry")
    win.editor.document().setModified(False)
    dlg.close()
    win.close()
