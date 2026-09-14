"""Unit tests for the automated PDF-to-articles ingestion engine."""

import os
import tempfile
import json
import pytest
import pymupdf as fitz

from volumenodex.reference.reference_model import ReferenceCategory
from volumenodex.reference.pdf_ingestor import PDFArticleifier


def create_sample_pdf(filepath: str):
    """Creates a sample multi-chapter PDF with Table of Contents and domain text for testing."""
    doc = fitz.open()

    # Page 1: Title page
    p1 = doc.new_page()
    p1.insert_text((72, 100), "A FIELD GUIDE TO NAUTICAL RIGGING AND SAILS", fontsize=18)
    p1.insert_text((72, 130), "By Admiral John Sailor", fontsize=12)

    # Page 2: Chapter 1 - Standing and Running Rigging
    p2 = doc.new_page()
    p2.insert_text((72, 72), "CHAPTER 1: STANDING RIGGING AND SHROUDS", fontsize=14)
    ch1_text = (
        "The standing rigging consists of shrouds, stays, and backstays supporting the masts.\n\n"
        "Shrouds extend from the masthead down to the chainplates on the hull sides, providing lateral support.\n"
        "Ratlines are hitched horizontally across the shrouds to form rope ladders for the crew to ascend aloft.\n\n"
        "Stays support the spars against fore-and-aft pitch. Heavy Stockholm tar protects the hemp cordage from sea spray.\n"
        "Tensile Strength: 4500 lbs\n"
        "Standard Diameter: 2.5 inches\n"
        "Inspection Interval: 30 days\n"
    )
    p2.insert_textbox(fitz.Rect(72, 100, 500, 400), ch1_text, fontsize=10)

    # Page 3: Chapter 2 - Celestial Navigation with Sextants
    p3 = doc.new_page()
    p3.insert_text((72, 72), "CHAPTER 2: SEXTANTS AND CELESTIAL DEAD RECKONING", fontsize=14)
    ch2_text = (
        "Celestial navigation relies on measuring the altitude of celestial bodies above the visible sea horizon.\n\n"
        "The marine sextant employs an index arm and mirror to bring the reflected image of the sun or star into coincidence with the sea horizon.\n"
        "Dead reckoning plots the vessel's estimated position using course steered and speed through the water.\n"
        "Index Error: 2 arcminutes\n"
        "Accuracy Range: 1 nautical mile\n"
        "Sighting Window: Dawn and dusk twilight\n"
    )
    p3.insert_textbox(fitz.Rect(72, 100, 500, 400), ch2_text, fontsize=10)

    # Page 4: Chapter 3 - Tactical Combat and Overwatch
    p4 = doc.new_page()
    p4.insert_text((72, 72), "CHAPTER 3: INFANTRY SQUAD FIRE AND OVERWATCH", fontsize=14)
    ch3_text = (
        "In tactical combat, the rifle squad executes bounding overwatch to advance across open terrain under enemy fire.\n\n"
        "One team establishes a base of fire laying down suppressive fire while the maneuver team bounds forward.\n"
        "Suppression pins enemy riflemen, preventing accurate return fire while the assault element flanks.\n"
        "Effective Range: 500 meters\n"
        "Suppression Ratio: 3 to 1\n"
        "Ammunition Load: 210 rounds\n"
    )
    p4.insert_textbox(fitz.Rect(72, 100, 500, 400), ch3_text, fontsize=10)

    # Set Table of Contents (TOC)
    # [lvl, title, page (1-indexed)]
    toc = [
        [1, "Standing Rigging and Shrouds", 2],
        [1, "Sextants and Celestial Navigation", 3],
        [1, "Infantry Squad Fire and Overwatch", 4],
    ]
    doc.set_toc(toc)
    doc.save(filepath)
    doc.close()


def test_pdf_articleifier_inspection():
    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_path = os.path.join(tmpdir, "test_manual.pdf")
        create_sample_pdf(pdf_path)

        ingestor = PDFArticleifier(pdf_path)
        info = ingestor.inspect_structure()

        assert info["page_count"] == 4
        assert info["has_toc"] is True
        assert info["toc_entry_count"] == 3


def test_pdf_articleifier_auto_extraction():
    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_path = os.path.join(tmpdir, "test_manual.pdf")
        create_sample_pdf(pdf_path)

        ingestor = PDFArticleifier(pdf_path)
        entries = ingestor.process(mode="auto")

        assert len(entries) == 3

        # First entry: Nautical Rigging
        rigging = entries[0]
        assert "Rigging" in rigging.title
        assert rigging.category == ReferenceCategory.NAUTICAL_SAILING
        assert "shrouds" in rigging.tags or "rigging" in rigging.tags
        assert len(rigging.quick_facts) >= 2
        assert "Tensile Strength" in rigging.quick_facts or "Standard Diameter" in rigging.quick_facts
        assert len(rigging.summary) > 20
        assert len(rigging.fiction_tips) > 20

        # Second entry: Navigation
        nav = entries[1]
        assert "Navigation" in nav.title or "Sextants" in nav.title
        assert nav.category == ReferenceCategory.NAUTICAL_SAILING
        assert "sextant" in nav.tags or "navigation" in nav.tags

        # Third entry: Tactical squad
        tactics = entries[2]
        assert "Infantry" in tactics.title or "Tactical" in tactics.title or "Overwatch" in tactics.title
        assert tactics.category == ReferenceCategory.WEAPONS_WARFARE
        assert "squad" in tactics.tags or "infantry" in tactics.tags or "combat" in tactics.tags
        assert "Effective Range" in tactics.quick_facts or "Suppression Ratio" in tactics.quick_facts


def test_pdf_articleifier_headings_mode():
    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_path = os.path.join(tmpdir, "test_manual.pdf")
        create_sample_pdf(pdf_path)

        ingestor = PDFArticleifier(pdf_path)
        entries = ingestor.process(mode="headings")

        # Headings mode extracts the chapters based on 'CHAPTER X:' patterns
        assert len(entries) >= 2
        assert any(e.category == ReferenceCategory.NAUTICAL_SAILING for e in entries)
        assert any(e.category == ReferenceCategory.WEAPONS_WARFARE for e in entries)


def test_pdf_articleifier_category_heuristics():
    # Test classifier on diverse domain snippets
    med_snippet = "The medic administered atropine to counteract neurotoxic poisoning while applying a tourniquet for hemorrhage."
    assert PDFArticleifier.classify_category(med_snippet) == ReferenceCategory.POISONS_MEDICINE

    forensic_snippet = "Autopsy examination revealed fixed lividity (livor mortis) on the dorsal aspect, along with extensive petechial hemorrhage."
    assert PDFArticleifier.classify_category(forensic_snippet) == ReferenceCategory.FORENSICS_CRIME

    aviation_snippet = "The pilot checked the pitot-static tube and adjusted the elevator trim to avoid exceeding critical angle of attack."
    assert PDFArticleifier.classify_category(aviation_snippet) == ReferenceCategory.AVIATION_FLIGHT

    space_snippet = "Orbital mechanics dictate that celestial bodies near perihelion accelerate due to solar gravitational gradient."
    assert PDFArticleifier.classify_category(space_snippet) == ReferenceCategory.ASTRONOMY_SPACE

    heraldry_snippet = "The escutcheon displays a chevron argent on a field azure, adhering strictly to the ancient rule of tinctures."
    assert PDFArticleifier.classify_category(heraldry_snippet) == ReferenceCategory.HERALDRY_CHIVALRY


def test_incorporate_entries():
    from volumenodex.reference.pdf_ingestor import incorporate_entries

    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_path = os.path.join(tmpdir, "sample.pdf")
        create_sample_pdf(pdf_path)

        ingestor = PDFArticleifier(pdf_path)
        entries = ingestor.process(mode="auto")

        target_json = os.path.join(tmpdir, "custom_knowledge.json")
        added, updated, total = incorporate_entries(entries, target_json)

        assert added == 3
        assert updated == 0
        assert total == 3
        assert os.path.exists(target_json)

        # Re-incorporate should update rather than duplicate
        added2, updated2, total2 = incorporate_entries(entries, target_json, overwrite=True)
        assert added2 == 0
        assert updated2 == 3
        assert total2 == 3


def test_pdf_ingestion_dialog_ui(monkeypatch):
    from tools.reference_builder import PDFIngestionDialog, StandaloneReferenceBuilderApp
    from PySide6.QtWidgets import QApplication, QMessageBox
    app = QApplication.instance() or QApplication([])

    monkeypatch.setattr(QMessageBox, "information", lambda *args, **kwargs: QMessageBox.StandardButton.Ok)
    monkeypatch.setattr(QMessageBox, "warning", lambda *args, **kwargs: QMessageBox.StandardButton.Ok)
    monkeypatch.setattr(QMessageBox, "critical", lambda *args, **kwargs: QMessageBox.StandardButton.Ok)

    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_path = os.path.join(tmpdir, "sample.pdf")
        create_sample_pdf(pdf_path)

        target_json = os.path.join(tmpdir, "library.json")
        builder = StandaloneReferenceBuilderApp(target_json_path=target_json)

        # Dialog UI verification
        dlg = PDFIngestionDialog(target_json_path=target_json, parent=builder)
        assert dlg.isVisible() is False
        dlg.edit_pdf_path.setText(pdf_path)

        # Triggers inspection and banner update
        assert "Bookmarks" in dlg.lbl_doc_info.text() or "Pages: 4" in dlg.lbl_doc_info.text()

        # Run extraction through UI
        dlg._start_extraction()
        assert len(dlg._extracted_entries) == 3
        assert dlg.table_preview.rowCount() == 3

        # Test preview filtering
        dlg.edit_filter.setText("Rigging")
        assert dlg.table_preview.rowCount() == 1
        dlg.edit_filter.clear()
        assert dlg.table_preview.rowCount() == 3

        # Test commit
        dlg._commit_entries()
        assert os.path.exists(target_json)
        with open(target_json, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert len(data) == 3

        dlg.close()
        builder.close()
