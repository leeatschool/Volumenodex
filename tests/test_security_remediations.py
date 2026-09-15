import os
import sys
import tempfile
import zipfile
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from PySide6.QtGui import QTextDocument

from volumenodex.pet.companion_figures import CompanionFigureRenderer
from volumenodex.core.io_manager import IOManager
from volumenodex.academic.citation_model import CitationEntry, CitationType, CitationFormatter
from volumenodex.corkboard.corkboard_model import IndexCard, CardStatus


def test_sec_01_avatar_unc_paths_rejected():
    """Validates that CompanionFigureRenderer._render_custom_image rejects UNC and network paths."""
    unc_paths = [
        r"\\192.168.1.50\share\avatar.png",
        r"\\evil-attacker.com\share\image.jpg",
        "//10.0.0.1/share/photo.png",
        "http://attacker.com/malicious.png",
        "https://attacker.com/malicious.png",
        "file:////attacker/share/image.png",
    ]
    for path in unc_paths:
        result = CompanionFigureRenderer._render_custom_image(path, size=48)
        assert result is None, f"UNC or network path should be rejected: {path}"


def test_sec_02_citation_html_escaping():
    """Validates that CitationFormatter escapes user input in bibliography output."""
    entry = CitationEntry(
        id="c1",
        entry_type=CitationType.JOURNAL,
        title='Research <script>alert("xss")</script> & Analysis',
        authors=['Hacker <img src="x" onerror="alert(1)">, Alice'],
        year="2026",
        source_title='Journal of <b>Exploits</b> & Safety',
        doi='10.1000/182<x>',
    )
    formatted = CitationFormatter.format_bibliography_entry(entry, style="APA 7th")
    assert "<script>" not in formatted
    assert "&lt;script&gt;" in formatted
    assert '<img src="x"' not in formatted
    assert "&lt;img" in formatted
    assert "<b>Exploits</b>" not in formatted  # User's source title <b> should be escaped
    assert "&lt;b&gt;Exploits&lt;/b&gt;" in formatted


def test_sec_06_citation_entry_from_dict_extra_fields():
    """Validates that CitationEntry.from_dict ignores unexpected/malformed fields without crashing."""
    malicious_dict = {
        "id": "test_id",
        "title": "A Safe Paper",
        "unexpected_field": "injected_value",
        "another_extra_key": 12345,
        "entry_type": "invalid_type_enum",
    }
    # Should safely construct without raising TypeError or ValueError
    entry = CitationEntry.from_dict(malicious_dict)
    assert entry.id == "test_id"
    assert entry.title == "A Safe Paper"
    assert entry.entry_type == CitationType.JOURNAL  # Defaulted safely


def test_sec_06_index_card_from_dict_invalid_data():
    """Validates that IndexCard.from_dict handles unknown status or non-integer word counts safely."""
    bad_dict = {
        "id": "card_01",
        "title": "Scene 1",
        "status": "NON_EXISTENT_STATUS",
        "word_count": "not_an_int",
    }
    card = IndexCard.from_dict(bad_dict)
    assert card.id == "card_01"
    assert card.status == CardStatus.DRAFT  # Fell back safely
    assert card.word_count == 0  # Fell back safely


def test_sec_08_io_manager_zip_slip_rejection():
    """Validates that IOManager.load_docx rejects archives with zip-slip path traversal."""
    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tf:
        bad_zip_path = tf.name

    try:
        with zipfile.ZipFile(bad_zip_path, "w") as zf:
            zf.writestr("../../evil.txt", "payload")
            zf.writestr("word/document.xml", "<w:document xmlns:w='http://schemas.openxmlformats.org/wordprocessingml/2006/main'><w:body/></w:document>")

        doc = QTextDocument()
        result = IOManager.load_docx(bad_zip_path, doc)
        assert result is None
    finally:
        if os.path.exists(bad_zip_path):
            os.remove(bad_zip_path)


def test_sec_08_io_manager_zip_bomb_rejection():
    """Validates that IOManager.load_docx rejects excessively large uncompressed archives."""
    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tf:
        bad_zip_path = tf.name

    try:
        with zipfile.ZipFile(bad_zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            # 110 MB of zeros compresses to a few kilobytes
            zf.writestr("huge_file.xml", b"\x00" * (110 * 1024 * 1024))
            zf.writestr("word/document.xml", "<w:document xmlns:w='http://schemas.openxmlformats.org/wordprocessingml/2006/main'><w:body/></w:document>")

        doc = QTextDocument()
        result = IOManager.load_docx(bad_zip_path, doc)
        assert result is None  # Rejection due to exceeding 100MB limit
    finally:
        if os.path.exists(bad_zip_path):
            os.remove(bad_zip_path)
