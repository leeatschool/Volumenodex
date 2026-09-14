"""Standalone Writers Reference Builder Tool.

A dedicated tool to create, curate, edit, import, and export knowledge topics
directly into Volumenodex's offline bundled reference compendium.
"""

import sys
import os
import json
import argparse
from pathlib import Path
from typing import Optional, Dict, Any, List

# Ensure repository root is in sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from PySide6.QtCore import Qt, Signal, QRectF
from PySide6.QtGui import QColor, QFont, QIcon, QPixmap, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QApplication, QDialog, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QTextEdit, QComboBox, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QFileDialog, QScrollArea, QFrame, QSplitter, QProgressBar,
    QSpinBox, QRadioButton, QButtonGroup, QCheckBox
)

from volumenodex.reference.reference_model import ReferenceEntry, ReferenceCategory
from volumenodex.reference.pdf_ingestor import PDFArticleifier, incorporate_entries
from volumenodex.reference.text_normalizer import TextNormalizer


DEFAULT_BUNDLED_PATH = REPO_ROOT / "volumenodex" / "reference" / "bundled_knowledge.json"


class ReferenceEntryEditorDialog(QDialog):
    """Interactive GUI dialog to add or edit a reference entry."""

    entrySaved = Signal(dict)

    def __init__(self, entry_dict: Optional[dict] = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Reference Topic" if entry_dict else "Add New Reference Topic")
        self.resize(760, 700)
        self.setMinimumSize(560, 520)
        self._existing_dict = entry_dict
        if parent and hasattr(parent, "logo_path") and parent.logo_path:
            self.setWindowIcon(QIcon(parent.logo_path))

        self.setStyleSheet("""
            QDialog {
                background-color: #181922;
                color: #e1e4f2;
                font-family: 'Segoe UI', sans-serif;
            }
            QLabel {
                color: #a2a7c4;
                font-weight: 600;
                font-size: 11px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            QLineEdit, QComboBox, QTextEdit {
                background-color: #101116;
                color: #f1f3fa;
                border: 1px solid #2a2c3d;
                border-radius: 5px;
                padding: 6px 10px;
                font-size: 13px;
                selection-background-color: #7aa2f7;
            }
            QLineEdit:focus, QComboBox:focus, QTextEdit:focus {
                border-color: #7aa2f7;
            }
            QTableWidget {
                background-color: #101116;
                color: #f1f3fa;
                border: 1px solid #2a2c3d;
                border-radius: 5px;
                gridline-color: #2a2c3d;
                font-size: 12px;
            }
            QHeaderView::section {
                background-color: #181922;
                color: #7aa2f7;
                padding: 4px;
                font-weight: 600;
                border: 1px solid #2a2c3d;
            }
            QPushButton {
                background-color: #232532;
                color: #e1e4f2;
                border: 1px solid #2a2c3d;
                border-radius: 5px;
                padding: 6px 14px;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #2d3042;
                border-color: #7aa2f7;
            }
            QPushButton#primaryBtn {
                background-color: #7aa2f7;
                color: #101116;
                border-color: #7aa2f7;
                font-weight: 700;
            }
            QPushButton#primaryBtn:hover {
                background-color: #89b4fa;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(12)

        # Title & Category Row
        h_row1 = QHBoxLayout()
        h_row1.setSpacing(12)

        v_title = QVBoxLayout()
        v_title.setSpacing(4)
        v_title.addWidget(QLabel("Topic Title:"))
        self.edit_title = QLineEdit()
        self.edit_title.setPlaceholderText("e.g. Damascus Steel Metallurgy & Trade")
        v_title.addWidget(self.edit_title)
        h_row1.addLayout(v_title, stretch=2)

        v_cat = QVBoxLayout()
        v_cat.setSpacing(4)
        v_cat.addWidget(QLabel("Category:"))
        self.combo_category = QComboBox()
        self.combo_category.setEditable(True)
        for cat in ReferenceCategory.ALL_CATEGORIES:
            self.combo_category.addItem(cat)
        v_cat.addWidget(self.combo_category)
        h_row1.addLayout(v_cat, stretch=1)
        layout.addLayout(h_row1)

        # Tags
        v_tags = QVBoxLayout()
        v_tags.setSpacing(4)
        v_tags.addWidget(QLabel("Tags (comma separated):"))
        self.edit_tags = QLineEdit()
        self.edit_tags.setPlaceholderText("e.g. blades, metallurgy, medieval, trade, forging")
        v_tags.addWidget(self.edit_tags)
        layout.addLayout(v_tags)

        # Summary
        v_summary = QVBoxLayout()
        v_summary.setSpacing(4)
        v_summary.addWidget(QLabel("Core Summary (1-2 sentences):"))
        self.edit_summary = QLineEdit()
        self.edit_summary.setPlaceholderText("Brief, crisp overview for immediate reference while writing...")
        v_summary.addWidget(self.edit_summary)
        layout.addLayout(v_summary)

        # Quick Facts Table
        v_facts = QVBoxLayout()
        v_facts.setSpacing(4)
        h_facts_header = QHBoxLayout()
        h_facts_header.addWidget(QLabel("Quick Facts Key-Value Table:"))
        h_facts_header.addStretch()
        btn_add_fact = QPushButton("+ Add Fact Row")
        btn_add_fact.clicked.connect(self._add_fact_row)
        h_facts_header.addWidget(btn_add_fact)
        btn_del_fact = QPushButton("Remove Fact")
        btn_del_fact.clicked.connect(self._remove_fact_row)
        h_facts_header.addWidget(btn_del_fact)
        v_facts.addLayout(h_facts_header)

        self.table_facts = QTableWidget(0, 2)
        self.table_facts.setHorizontalHeaderLabels(["Key / Property", "Value / Details"])
        self.table_facts.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.table_facts.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table_facts.setColumnWidth(0, 190)
        self.table_facts.setFixedHeight(125)
        v_facts.addWidget(self.table_facts)
        layout.addLayout(v_facts)

        # Detailed Content
        v_content = QVBoxLayout()
        v_content.setSpacing(4)
        v_content.addWidget(QLabel("Deep Historical / Technical Breakdown:"))
        self.edit_content = QTextEdit()
        self.edit_content.setPlaceholderText("Explain how this actually works: physics, timeline, mechanics, real-world behavior...")
        v_content.addWidget(self.edit_content)
        layout.addLayout(v_content, stretch=1)

        # Fiction Tips
        v_tips = QVBoxLayout()
        v_tips.setSpacing(4)
        v_tips.addWidget(QLabel("Fiction Writing Tips & Tropes to Avoid:"))
        self.edit_tips = QTextEdit()
        self.edit_tips.setPlaceholderText("Sensory details to describe, realistic complications, common movie clichés to avoid...")
        self.edit_tips.setFixedHeight(85)
        v_tips.addWidget(self.edit_tips)
        layout.addLayout(v_tips)

        # Buttons
        h_btns = QHBoxLayout()

        btn_clean = QPushButton("✨ Clean & Reflow Text")
        btn_clean.setToolTip("Reflow line breaks into clean paragraphs and normalize ALL-CAPS into sentence case")
        btn_clean.clicked.connect(self._clean_and_reflow_text)
        h_btns.addWidget(btn_clean)

        h_btns.addStretch()
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        h_btns.addWidget(btn_cancel)

        self.btn_save = QPushButton("Save Topic")
        self.btn_save.setObjectName("primaryBtn")
        self.btn_save.clicked.connect(self._save_entry)
        h_btns.addWidget(self.btn_save)
        layout.addLayout(h_btns)

        if entry_dict:
            self._load_data(entry_dict)
        else:
            self._add_fact_row("Key Factor", "")
            self._add_fact_row("Timeline / Range", "")

    def _add_fact_row(self, key: str = "", val: str = "") -> None:
        r = self.table_facts.rowCount()
        self.table_facts.insertRow(r)
        item_k = QTableWidgetItem(key)
        item_v = QTableWidgetItem(val)
        self.table_facts.setItem(r, 0, item_k)
        self.table_facts.setItem(r, 1, item_v)

    def _remove_fact_row(self) -> None:
        curr = self.table_facts.currentRow()
        if curr >= 0:
            self.table_facts.removeRow(curr)
        elif self.table_facts.rowCount() > 0:
            self.table_facts.removeRow(self.table_facts.rowCount() - 1)

    def _load_data(self, d: dict) -> None:
        self.edit_title.setText(d.get("title", ""))
        self.combo_category.setCurrentText(d.get("category", ReferenceCategory.CUSTOM_LORE))
        self.edit_tags.setText(", ".join(d.get("tags", [])))
        self.edit_summary.setText(d.get("summary", ""))
        self.edit_content.setPlainText(d.get("content", ""))
        self.edit_tips.setPlainText(d.get("fiction_tips", ""))

        self.table_facts.setRowCount(0)
        for k, v in d.get("quick_facts", {}).items():
            self._add_fact_row(k, v)

    def _clean_and_reflow_text(self) -> None:
        """Cleans broken line-breaks into paragraphs, repairs typography, and normalizes case."""
        raw_title = self.edit_title.text()
        if raw_title:
            self.edit_title.setText(TextNormalizer.normalize_title_case(raw_title))

        raw_summary = self.edit_summary.text()
        if raw_summary:
            self.edit_summary.setText(TextNormalizer.clean_and_normalize(raw_summary))

        raw_content = self.edit_content.toPlainText()
        if raw_content:
            self.edit_content.setPlainText(TextNormalizer.clean_and_normalize(raw_content))

        raw_tips = self.edit_tips.toPlainText()
        if raw_tips:
            self.edit_tips.setPlainText(TextNormalizer.clean_and_normalize(raw_tips))

    def _save_entry(self) -> None:
        title = self.edit_title.text().strip()
        if not title:
            QMessageBox.warning(self, "Missing Title", "Please enter a title for the reference topic.")
            return

        category = self.combo_category.currentText().strip() or ReferenceCategory.CUSTOM_LORE
        tags = [t.strip() for t in self.edit_tags.text().split(",") if t.strip()]
        summary = self.edit_summary.text().strip()
        content = self.edit_content.toPlainText().strip()
        tips = self.edit_tips.toPlainText().strip()

        quick_facts = {}
        for r in range(self.table_facts.rowCount()):
            k_item = self.table_facts.item(r, 0)
            v_item = self.table_facts.item(r, 1)
            k = k_item.text().strip() if k_item else ""
            v = v_item.text().strip() if v_item else ""
            if k or v:
                quick_facts[k] = v

        entry_id = ""
        if self._existing_dict and self._existing_dict.get("id"):
            entry_id = self._existing_dict["id"]
        else:
            slug = "".join(c if c.isalnum() else "-" for c in title.lower())
            entry_id = "-".join(filter(None, slug.split("-"))) or "topic"

        res_dict = {
            "id": entry_id,
            "title": title,
            "category": category,
            "tags": tags,
            "summary": summary,
            "quick_facts": quick_facts,
            "content": content,
            "fiction_tips": tips,
            "related_entries": self._existing_dict.get("related_entries", []) if self._existing_dict else [],
            "is_custom": False,
        }

class PDFIngestionDialog(QDialog):
    """Interactive GUI dialog to auto-ingest a PDF document into structured reference entries."""

    entriesIngested = Signal(list)  # Emits list of incorporated dicts

    def __init__(self, target_json_path: Optional[Path] = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Auto-Ingest PDF into Writers Reference")
        self.resize(980, 720)
        self.setMinimumSize(740, 560)
        self.target_path = Path(target_json_path) if target_json_path else DEFAULT_BUNDLED_PATH
        self._extracted_entries: List[ReferenceEntry] = []
        self._filtered_indices: List[int] = []

        if parent and hasattr(parent, "logo_path") and parent.logo_path:
            self.setWindowIcon(QIcon(parent.logo_path))

        self._init_styles()
        self._init_ui()

    def _init_styles(self) -> None:
        self.setStyleSheet("""
            QDialog {
                background-color: #12131a;
                color: #e1e4f2;
                font-family: 'Segoe UI', sans-serif;
            }
            QLabel {
                color: #a2a7c4;
                font-weight: 600;
                font-size: 11px;
            }
            QLineEdit, QComboBox, QSpinBox {
                background-color: #1a1b24;
                color: #ffffff;
                border: 1px solid #2d2f40;
                border-radius: 5px;
                padding: 6px 10px;
                font-size: 12px;
            }
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
                border-color: #7aa2f7;
            }
            QTableWidget {
                background-color: #161720;
                border: 1px solid #2a2c3d;
                border-radius: 6px;
                gridline-color: #1f212e;
                font-size: 12px;
                color: #e1e4f2;
            }
            QHeaderView::section {
                background-color: #1a1b26;
                color: #7aa2f7;
                padding: 5px;
                font-weight: 700;
                border: 1px solid #262838;
            }
            QPushButton {
                background-color: #1f212d;
                color: #e1e4f2;
                border: 1px solid #2d2f40;
                border-radius: 5px;
                padding: 6px 14px;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #2b2d3d;
                border-color: #7aa2f7;
                color: #ffffff;
            }
            QPushButton#primaryBtn {
                background-color: #7aa2f7;
                color: #101116;
                border: 1px solid #7aa2f7;
                font-weight: 700;
            }
            QPushButton#primaryBtn:hover {
                background-color: #89b4fa;
            }
            QProgressBar {
                border: 1px solid #2d2f40;
                border-radius: 4px;
                text-align: center;
                background-color: #161720;
                color: #ffffff;
                font-size: 11px;
                font-weight: bold;
                height: 18px;
            }
            QProgressBar::chunk {
                background-color: #7aa2f7;
                border-radius: 3px;
            }
            QRadioButton {
                color: #e1e4f2;
                font-size: 12px;
                font-weight: 500;
            }
        """)

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        # Header Title
        h_title = QHBoxLayout()
        v_meta = QVBoxLayout()
        v_meta.setSpacing(2)
        lbl_head = QLabel("AUTOMATED PDF ARTICLEIFIER")
        lbl_head.setStyleSheet("font-size: 16px; font-weight: 800; letter-spacing: 1px; color: #7aa2f7;")
        v_meta.addWidget(lbl_head)
        lbl_sub = QLabel("Convert PDF manuals, treatises, and books into structured offline knowledge articles with local heuristic NLP.")
        lbl_sub.setStyleSheet("font-size: 11px; color: #8c91b0;")
        v_meta.addWidget(lbl_sub)
        h_title.addLayout(v_meta)
        h_title.addStretch()
        layout.addLayout(h_title)

        # PDF File Picker Row
        h_file = QHBoxLayout()
        h_file.setSpacing(8)
        lbl_f = QLabel("PDF File:")
        lbl_f.setStyleSheet("min-width: 60px;")
        h_file.addWidget(lbl_f)

        self.edit_pdf_path = QLineEdit()
        self.edit_pdf_path.setPlaceholderText("Select a PDF document to articleafy...")
        self.edit_pdf_path.textChanged.connect(self._on_pdf_path_changed)
        h_file.addWidget(self.edit_pdf_path, stretch=1)

        btn_browse = QPushButton("📁 Browse PDF...")
        btn_browse.clicked.connect(self._browse_pdf)
        h_file.addWidget(btn_browse)
        layout.addLayout(h_file)

        # Document Info Banner
        self.lbl_doc_info = QLabel("No PDF selected.")
        self.lbl_doc_info.setStyleSheet("background-color: #181924; border: 1px dashed #2d2f40; border-radius: 5px; padding: 6px 12px; font-size: 11px; color: #7aa2f7;")
        layout.addWidget(self.lbl_doc_info)

        # Extraction Settings Bar
        h_settings = QHBoxLayout()
        h_settings.setSpacing(10)

        # Mode
        h_settings.addWidget(QLabel("Mode:"))
        self.combo_mode = QComboBox()
        self.combo_mode.addItem("Auto-Detect Structure (Recommended)", "auto")
        self.combo_mode.addItem("Table of Contents / Bookmarks", "toc")
        self.combo_mode.addItem("Visual Headings & Chapters", "headings")
        self.combo_mode.addItem("Lexicon / Glossary Entries", "lexicon")
        h_settings.addWidget(self.combo_mode)

        # Category
        h_settings.addWidget(QLabel("Category:"))
        self.combo_category = QComboBox()
        self.combo_category.addItem("Auto-Classify (AI Heuristics)", None)
        for cat in ReferenceCategory.ALL_CATEGORIES:
            self.combo_category.addItem(cat, cat)
        h_settings.addWidget(self.combo_category)

        # Min words
        h_settings.addWidget(QLabel("Min Words:"))
        self.spin_min_words = QSpinBox()
        self.spin_min_words.setRange(15, 1000)
        self.spin_min_words.setValue(40)
        h_settings.addWidget(self.spin_min_words)

        h_settings.addStretch()

        self.btn_extract = QPushButton("🚀 Parse & Extract Articles")
        self.btn_extract.setObjectName("primaryBtn")
        self.btn_extract.clicked.connect(self._start_extraction)
        h_settings.addWidget(self.btn_extract)
        layout.addLayout(h_settings)

        # Smart Normalization Controls
        h_norm = QHBoxLayout()
        h_norm.setSpacing(16)

        self.chk_reflow = QCheckBox("Reflow line breaks into clean paragraphs")
        self.chk_reflow.setChecked(True)
        self.chk_reflow.setToolTip("Joins hard-wrapped OCR and column line-breaks into contiguous paragraphs, repairing split hyphens.")
        h_norm.addWidget(self.chk_reflow)

        self.chk_sentence_case = QCheckBox("Normalize ALL-CAPS into Sentence / Title Case")
        self.chk_sentence_case.setChecked(True)
        self.chk_sentence_case.setToolTip("Converts screaming uppercase text into natural Sentence case while preserving acronyms like FAA, NASA, DNA, and Roman numerals.")
        h_norm.addWidget(self.chk_sentence_case)

        h_norm.addStretch()
        layout.addLayout(h_norm)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Status Label
        self.lbl_status = QLabel("Ready to process.")
        self.lbl_status.setStyleSheet("font-size: 11px; color: #8c91b0;")
        layout.addWidget(self.lbl_status)

        # Preview Section Header
        h_prev_head = QHBoxLayout()
        h_prev_head.addWidget(QLabel("EXTRACTED ARTICLES PREVIEW (Double-click to edit prior to import):"))
        h_prev_head.addStretch()

        self.edit_filter = QLineEdit()
        self.edit_filter.setPlaceholderText("🔍 Filter preview...")
        self.edit_filter.setMaximumWidth(220)
        self.edit_filter.textChanged.connect(self._render_preview_table)
        h_prev_head.addWidget(self.edit_filter)
        layout.addLayout(h_prev_head)

        # Extracted Articles Preview Table
        self.table_preview = QTableWidget(0, 5)
        self.table_preview.setHorizontalHeaderLabels(["Title", "Category", "Tags", "Facts", "Words"])
        self.table_preview.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.table_preview.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table_preview.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table_preview.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table_preview.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table_preview.setColumnWidth(0, 320)
        self.table_preview.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table_preview.doubleClicked.connect(self._edit_preview_entry)
        layout.addWidget(self.table_preview, stretch=1)

        # Destination & Incorporation Row
        h_actions = QHBoxLayout()
        h_actions.setSpacing(12)

        self.lbl_preview_count = QLabel("0 Articles Extracted")
        self.lbl_preview_count.setStyleSheet("font-weight: 700; color: #7aa2f7;")
        h_actions.addWidget(self.lbl_preview_count)

        btn_edit_row = QPushButton("✏️ Edit Selected")
        btn_edit_row.clicked.connect(self._edit_preview_entry)
        h_actions.addWidget(btn_edit_row)

        btn_remove = QPushButton("🗑️ Discard Selected")
        btn_remove.clicked.connect(self._remove_preview_entry)
        h_actions.addWidget(btn_remove)

        h_actions.addStretch()

        self.radio_current = QRadioButton(f"Incorporate into {self.target_path.name}")
        self.radio_current.setChecked(True)
        h_actions.addWidget(self.radio_current)

        self.radio_export = QRadioButton("Export to new JSON...")
        h_actions.addWidget(self.radio_export)

        self.btn_commit = QPushButton("📥 Import All into Knowledge Base")
        self.btn_commit.setObjectName("primaryBtn")
        self.btn_commit.setEnabled(False)
        self.btn_commit.clicked.connect(self._commit_entries)
        h_actions.addWidget(self.btn_commit)

        layout.addLayout(h_actions)

    def _browse_pdf(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select PDF Document", "", "PDF Documents (*.pdf)"
        )
        if path:
            self.edit_pdf_path.setText(path)

    def _on_pdf_path_changed(self, text: str) -> None:
        pdf_path = text.strip()
        if not pdf_path or not os.path.exists(pdf_path):
            self.lbl_doc_info.setText("Selected file does not exist.")
            return

        try:
            ingestor = PDFArticleifier(pdf_path)
            info = ingestor.inspect_structure()
            toc_text = f"Found {info['toc_entry_count']} Bookmarks (TOC Mode Recommended)" if info["has_toc"] else "No Bookmarks found (Visual Headings Recommended)"
            self.lbl_doc_info.setText(
                f"📄 {info['title']} | Pages: {info['page_count']} | {toc_text}"
            )
            # Auto-adjust combo box
            if info["has_toc"]:
                self.combo_mode.setCurrentIndex(0)
            else:
                self.combo_mode.setCurrentIndex(2)
        except Exception as e:
            self.lbl_doc_info.setText(f"Error inspecting PDF: {e}")

    def _start_extraction(self) -> None:
        pdf_path = self.edit_pdf_path.text().strip()
        if not pdf_path or not os.path.exists(pdf_path):
            QMessageBox.warning(self, "Invalid Path", "Please select a valid PDF file first.")
            return

        self.btn_extract.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.lbl_status.setText("Beginning local PDF analysis...")

        mode = self.combo_mode.currentData()
        category = self.combo_category.currentData()
        min_words = self.spin_min_words.value()

        def progress_cb(curr, total, msg):
            pct = int((curr / max(1, total)) * 100)
            self.progress_bar.setValue(pct)
            self.lbl_status.setText(f"[{pct}%] {msg}")
            QApplication.processEvents()

        try:
            ingestor = PDFArticleifier(pdf_path)
            entries = ingestor.process(
                mode=mode,
                target_category=category,
                min_words_per_article=min_words,
                reflow_paragraphs=self.chk_reflow.isChecked(),
                normalize_case=self.chk_sentence_case.isChecked(),
                progress_callback=progress_cb
            )
            self._extracted_entries = entries
            self.progress_bar.setValue(100)
            self.lbl_status.setText(f"✓ Extraction complete! Processed {len(entries)} structured articles.")
            self.btn_commit.setEnabled(len(entries) > 0)
            self._render_preview_table()
        except Exception as e:
            QMessageBox.critical(self, "Extraction Error", f"Failed to extract articles from PDF:\n{e}")
            self.lbl_status.setText(f"Error: {e}")
        finally:
            self.btn_extract.setEnabled(True)

    def _render_preview_table(self) -> None:
        q = self.edit_filter.text().strip().lower()
        self.table_preview.setRowCount(0)
        self._filtered_indices = []

        for idx, entry in enumerate(self._extracted_entries):
            title = entry.title
            cat = entry.category
            tags = ", ".join(entry.tags)
            facts_count = f"{len(entry.quick_facts)} facts"
            word_count = f"{len(entry.content.split())} w"

            if q and (q not in title.lower() and q not in cat.lower() and q not in tags.lower()):
                continue

            r = self.table_preview.rowCount()
            self.table_preview.insertRow(r)
            self._filtered_indices.append(idx)

            item_title = QTableWidgetItem(title)
            item_title.setData(Qt.ItemDataRole.UserRole, idx)
            item_cat = QTableWidgetItem(cat)
            item_tags = QTableWidgetItem(tags)
            item_facts = QTableWidgetItem(facts_count)
            item_words = QTableWidgetItem(word_count)

            self.table_preview.setItem(r, 0, item_title)
            self.table_preview.setItem(r, 1, item_cat)
            self.table_preview.setItem(r, 2, item_tags)
            self.table_preview.setItem(r, 3, item_facts)
            self.table_preview.setItem(r, 4, item_words)

        self.lbl_preview_count.setText(f"Extracted: {len(self._extracted_entries)} Articles ({len(self._filtered_indices)} shown)")

    def _edit_preview_entry(self) -> None:
        curr = self.table_preview.currentRow()
        if curr < 0 or curr >= len(self._filtered_indices):
            return
        real_idx = self._filtered_indices[curr]
        entry = self._extracted_entries[real_idx]

        dlg = ReferenceEntryEditorDialog(entry_dict=entry.to_dict(), parent=self)
        dlg.entrySaved.connect(lambda updated_dict, i=real_idx: self._on_preview_entry_saved(i, updated_dict))
        dlg.exec()

    def _on_preview_entry_saved(self, idx: int, updated_dict: dict) -> None:
        if 0 <= idx < len(self._extracted_entries):
            self._extracted_entries[idx] = ReferenceEntry.from_dict(updated_dict)
            self._render_preview_table()

    def _remove_preview_entry(self) -> None:
        curr = self.table_preview.currentRow()
        if curr < 0 or curr >= len(self._filtered_indices):
            return
        real_idx = self._filtered_indices[curr]
        removed_title = self._extracted_entries[real_idx].title
        self._extracted_entries.pop(real_idx)
        self._render_preview_table()
        self.lbl_status.setText(f"Removed '{removed_title}' from batch.")

    def _commit_entries(self) -> None:
        if not self._extracted_entries:
            return

        target_file = self.target_path
        if self.radio_export.isChecked():
            path, _ = QFileDialog.getSaveFileName(
                self, "Export Extracted Articles", "extracted_reference_topics.json", "JSON Files (*.json)"
            )
            if not path:
                return
            target_file = Path(path)

        try:
            added, updated, total = incorporate_entries(self._extracted_entries, target_file, overwrite=True)
            QMessageBox.information(
                self, "Articles Incorporated",
                f"Successfully incorporated {len(self._extracted_entries)} articles!\n\n"
                f"• Added: {added} new topics\n"
                f"• Updated: {updated} existing topics\n"
                f"• Total topics in {target_file.name}: {total}"
            )
            raw_dicts = [e.to_dict() for e in self._extracted_entries]
            self.entriesIngested.emit(raw_dicts)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Incorporation Error", f"Failed to incorporate articles:\n{e}")


class StandaloneReferenceBuilderApp(QWidget):
    """Standalone manager window to curate the bundled offline reference library."""

    def __init__(self, target_json_path: Optional[str] = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Writers Reference — Knowledge Base Builder & Manager")
        self.resize(1020, 680)

        self.target_path = Path(target_json_path) if target_json_path else DEFAULT_BUNDLED_PATH
        self.topics: List[dict] = []
        self.logo_path = self._discover_logo_path()
        if self.logo_path:
            self.setWindowIcon(QIcon(self.logo_path))

        self._init_styles()
        self._init_ui()
        self._load_topics()

    def _discover_logo_path(self) -> Optional[str]:
        candidates = [
            REPO_ROOT / "volumenodex" / "resources" / "writers_reference_logo.png",
            REPO_ROOT / "assets" / "writers_reference_logo.png",
            REPO_ROOT / "assets" / "writref.png",
            Path(r"C:\Users\thele\Downloads\writref.png"),
            Path.home() / "Downloads" / "writref.png",
        ]
        for c in candidates:
            if c.exists():
                return str(c)
        return None

    def _init_styles(self) -> None:
        self.setStyleSheet("""
            QWidget {
                background-color: #101116;
                color: #e1e4f2;
                font-family: 'Segoe UI', sans-serif;
            }
            QLineEdit {
                background-color: #181922;
                border: 1px solid #2a2c3d;
                border-radius: 5px;
                padding: 7px 12px;
                color: #ffffff;
                font-size: 13px;
            }
            QLineEdit:focus {
                border-color: #7aa2f7;
            }
            QPushButton {
                background-color: #181922;
                color: #e1e4f2;
                border: 1px solid #2a2c3d;
                border-radius: 5px;
                padding: 6px 14px;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #232532;
                border-color: #7aa2f7;
                color: #ffffff;
            }
            QPushButton#primaryBtn {
                background-color: #7aa2f7;
                color: #101116;
                border: 1px solid #7aa2f7;
                font-weight: 700;
            }
            QPushButton#primaryBtn:hover {
                background-color: #89b4fa;
            }
            QTableWidget {
                background-color: #14151d;
                border: 1px solid #2a2c3d;
                border-radius: 6px;
                gridline-color: #1f212e;
                font-size: 13px;
            }
            QHeaderView::section {
                background-color: #181922;
                color: #7aa2f7;
                padding: 6px;
                font-weight: 700;
                border: 1px solid #2a2c3d;
            }
        """)

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        # Header Bar
        h_head = QHBoxLayout()
        h_head.setSpacing(12)

        if self.logo_path and os.path.exists(self.logo_path):
            lbl_logo = QLabel()
            src = QPixmap(self.logo_path)
            if not src.isNull():
                target_size = 48
                rounded = QPixmap(target_size, target_size)
                rounded.fill(Qt.GlobalColor.transparent)
                p = QPainter(rounded)
                p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
                p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
                clip = QPainterPath()
                clip.addRoundedRect(QRectF(0.5, 0.5, target_size - 1, target_size - 1), 8, 8)
                p.setClipPath(clip)
                p.drawPixmap(0, 0, src.scaled(target_size, target_size, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation))
                p.setClipping(False)
                p.setPen(QPen(QColor(122, 162, 247, 130), 1.2))
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawRoundedRect(QRectF(0.5, 0.5, target_size - 1, target_size - 1), 8, 8)
                p.end()
                lbl_logo.setPixmap(rounded)
                h_head.addWidget(lbl_logo)

        v_title = QVBoxLayout()
        v_title.setSpacing(2)

        title_lbl = QLabel("WRITERS REFERENCE BUILDER")
        title_lbl.setStyleSheet("font-size: 17px; font-weight: 800; letter-spacing: 1px; color: #7aa2f7;")
        v_title.addWidget(title_lbl)

        self.lbl_target = QLabel(f"Target Library: {self.target_path.name} (Bundled Offline Knowledge)")
        self.lbl_target.setStyleSheet("font-size: 11px; color: #8c91b0;")
        v_title.addWidget(self.lbl_target)
        h_head.addLayout(v_title)

        btn_pdf = QPushButton("⚡ Auto-Ingest PDF...")
        btn_pdf.setObjectName("primaryBtn")
        btn_pdf.setToolTip("Automatically parse, split, tag, and incorporate PDF books and manuals")
        btn_pdf.clicked.connect(self._open_pdf_ingestor)
        h_head.addWidget(btn_pdf)

        btn_new = QPushButton("➕ Add New Topic")
        btn_new.clicked.connect(self._add_topic)
        h_head.addWidget(btn_new)

        btn_import = QPushButton("📥 Import JSON...")
        btn_import.clicked.connect(self._import_json)
        h_head.addWidget(btn_import)

        btn_export = QPushButton("📤 Export JSON...")
        btn_export.clicked.connect(self._export_json)
        h_head.addWidget(btn_export)
        layout.addLayout(h_head)

        # Search / Filter Bar
        self.edit_search = QLineEdit()
        self.edit_search.setPlaceholderText("🔍 Filter loaded topics by title, tag, or category...")
        self.edit_search.textChanged.connect(self._render_table)
        layout.addWidget(self.edit_search)

        # Table of Topics
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Title", "Category", "Tags"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(0, 320)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.doubleClicked.connect(self._edit_topic)
        layout.addWidget(self.table)

        # Bottom Actions Bar
        h_foot = QHBoxLayout()
        self.lbl_count = QLabel("0 Topics")
        self.lbl_count.setStyleSheet("font-weight: 600; color: #8c91b0;")
        h_foot.addWidget(self.lbl_count)

        h_foot.addStretch()

        btn_edit = QPushButton("✏️ Edit Selected")
        btn_edit.clicked.connect(self._edit_topic)
        h_foot.addWidget(btn_edit)

        btn_del = QPushButton("🗑️ Delete Selected")
        btn_del.clicked.connect(self._delete_topic)
        h_foot.addWidget(btn_del)
        layout.addLayout(h_foot)

    def _load_topics(self) -> None:
        if self.target_path.exists():
            try:
                with open(self.target_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        self.topics = data
                    else:
                        self.topics = []
            except Exception as e:
                QMessageBox.warning(self, "Load Error", f"Could not read {self.target_path}:\n{e}")
                self.topics = []
        else:
            self.topics = []

        self._render_table()

    def _save_topics(self) -> bool:
        try:
            self.target_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.target_path, "w", encoding="utf-8") as f:
                json.dump(self.topics, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save to {self.target_path}:\n{e}")
            return False

    def _render_table(self) -> None:
        q = self.edit_search.text().strip().lower()
        self.table.setRowCount(0)

        displayed = 0
        for idx, t in enumerate(self.topics):
            title = t.get("title", "")
            cat = t.get("category", "")
            tags = ", ".join(t.get("tags", []))

            if q and (q not in title.lower() and q not in cat.lower() and q not in tags.lower()):
                continue

            r = self.table.rowCount()
            self.table.insertRow(r)

            item_title = QTableWidgetItem(title)
            item_title.setData(Qt.ItemDataRole.UserRole, idx)
            item_cat = QTableWidgetItem(cat)
            item_tags = QTableWidgetItem(tags)

            self.table.setItem(r, 0, item_title)
            self.table.setItem(r, 1, item_cat)
            self.table.setItem(r, 2, item_tags)
            displayed += 1

        self.lbl_count.setText(f"Showing {displayed} of {len(self.topics)} Topics")

    def _add_topic(self) -> None:
        dlg = ReferenceEntryEditorDialog(entry_dict=None, parent=self)
        dlg.entrySaved.connect(self._on_topic_added)
        dlg.exec()

    def _on_topic_added(self, topic_dict: dict) -> None:
        self.topics.append(topic_dict)
        if self._save_topics():
            self._render_table()
            self.lbl_count.setText(f"✓ Saved '{topic_dict.get('title')}'! Total: {len(self.topics)} Topics")

    def _open_pdf_ingestor(self, initial_pdf_path: Optional[str] = None) -> None:
        dlg = PDFIngestionDialog(target_json_path=self.target_path, parent=self)
        if initial_pdf_path and os.path.exists(initial_pdf_path):
            dlg.edit_pdf_path.setText(str(initial_pdf_path))
        dlg.entriesIngested.connect(self._on_pdf_entries_ingested)
        dlg.exec()

    def _on_pdf_entries_ingested(self, new_entries: list) -> None:
        self._load_topics()
        self.lbl_count.setText(f"✓ Successfully incorporated {len(new_entries)} articles from PDF! Total: {len(self.topics)} Topics")

    def _edit_topic(self) -> None:
        curr = self.table.currentRow()
        if curr < 0:
            return
        idx = self.table.item(curr, 0).data(Qt.ItemDataRole.UserRole)
        if 0 <= idx < len(self.topics):
            dlg = ReferenceEntryEditorDialog(entry_dict=self.topics[idx], parent=self)
            dlg.entrySaved.connect(lambda d, i=idx: self._on_topic_edited(i, d))
            dlg.exec()

    def _on_topic_edited(self, idx: int, topic_dict: dict) -> None:
        if 0 <= idx < len(self.topics):
            self.topics[idx] = topic_dict
            if self._save_topics():
                self._render_table()

    def _delete_topic(self) -> None:
        curr = self.table.currentRow()
        if curr < 0:
            return
        idx = self.table.item(curr, 0).data(Qt.ItemDataRole.UserRole)
        if 0 <= idx < len(self.topics):
            title = self.topics[idx].get("title", "Topic")
            res = QMessageBox.question(
                self, "Confirm Delete",
                f"Are you sure you want to delete '{title}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if res == QMessageBox.StandardButton.Yes:
                self.topics.pop(idx)
                if self._save_topics():
                    self._render_table()

    def _import_json(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Import Reference Topics", "", "JSON Files (*.json)")
        if path:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    added = 0
                    for item in data:
                        if isinstance(item, dict) and "title" in item:
                            self.topics.append(item)
                            added += 1
                    if added > 0 and self._save_topics():
                        self._render_table()
                        QMessageBox.information(self, "Import Complete", f"Successfully imported {added} topics.")
                else:
                    QMessageBox.warning(self, "Invalid File", "JSON file must contain a list of topic objects.")
            except Exception as e:
                QMessageBox.critical(self, "Import Error", f"Failed to import file:\n{e}")

    def _export_json(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Export Reference Topics", "writers_reference_export.json", "JSON Files (*.json)")
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(self.topics, f, indent=2, ensure_ascii=False)
                QMessageBox.information(self, "Export Complete", f"Knowledge base exported successfully to:\n{path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to export file:\n{e}")


def main():
    """Command-line launcher for the Standalone Writers Reference Builder."""
    parser = argparse.ArgumentParser(description="Standalone Writers Reference Knowledge Builder")
    parser.add_argument("--file", type=str, default=str(DEFAULT_BUNDLED_PATH), help="Target reference JSON file")
    parser.add_argument("--list", action="store_true", help="List all topics currently in the database")
    parser.add_argument("--add", action="store_true", help="Interactively add a topic via CLI prompts")
    parser.add_argument("--import-file", type=str, help="Import topics from a JSON file into the reference")
    parser.add_argument("--ingest-pdf", type=str, help="Auto-ingest a PDF file directly into the reference library")
    parser.add_argument("--pdf-mode", choices=["auto", "toc", "headings", "lexicon"], default="auto", help="PDF parsing strategy (default: auto)")
    parser.add_argument("--pdf-category", choices=ReferenceCategory.ALL_CATEGORIES, default=None, help="Override category classification")
    parser.add_argument("--min-words", type=int, default=40, help="Minimum word count per article")
    parser.add_argument("pdf_file", nargs="?", default=None, help="Optional PDF file to open in the visual Ingestion Dialog")

    args = parser.parse_args()
    target_path = Path(args.file)

    if args.ingest_pdf:
        pdf_path = Path(args.ingest_pdf)
        if not pdf_path.exists():
            print(f"Error: PDF file {pdf_path} not found.")
            return
        print(f"[*] Analyzing and ingesting PDF: {pdf_path}")
        ingestor = PDFArticleifier(str(pdf_path))
        info = ingestor.inspect_structure()
        print(f"    Document: {info['title']} | Pages: {info['page_count']} | Bookmarks: {info['toc_entry_count']}")
        entries = ingestor.process(
            mode=args.pdf_mode,
            target_category=args.pdf_category,
            min_words_per_article=args.min_words,
            reflow_paragraphs=True,
            normalize_case=True,
        )
        print(f"[+] Extracted {len(entries)} structured articles.")
        added, updated, total = incorporate_entries(entries, target_path, overwrite=True)
        print(f"[✓] Successfully incorporated into {target_path}: {added} added, {updated} updated (Total: {total}).")
        return

    if args.list:
        if target_path.exists():
            with open(target_path, "r", encoding="utf-8") as f:
                topics = json.load(f)
            print(f"\n--- Writers Reference ({len(topics)} Topics in {target_path}) ---")
            for t in topics:
                print(f" • {t.get('title'):<45} | {t.get('category', ''):<20}")
        else:
            print(f"Reference file {target_path} is currently empty.")
        return

    if args.import_file:
        imp_path = Path(args.import_file)
        if not imp_path.exists():
            print(f"File {imp_path} does not exist.")
            return
        with open(imp_path, "r", encoding="utf-8") as f:
            new_topics = json.load(f)
        current = []
        if target_path.exists():
            with open(target_path, "r", encoding="utf-8") as f:
                current = json.load(f)
        current.extend(new_topics)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(current, f, indent=2, ensure_ascii=False)
        print(f"Successfully imported {len(new_topics)} topics into {target_path}")
        return

    if args.add:
        print("\n--- Add Topic to Writers Reference ---")
        title = input("Title: ").strip()
        if not title:
            print("Title cannot be empty.")
            return
        cat = input(f"Category (Default: '{ReferenceCategory.CUSTOM_LORE}'): ").strip() or ReferenceCategory.CUSTOM_LORE
        tags = [t.strip() for t in input("Tags (comma separated): ").split(",") if t.strip()]
        summary = input("Core Summary: ").strip()
        content = input("Technical/Historical Breakdown: ").strip()
        tips = input("Fiction Writing Tips: ").strip()

        slug = "".join(c if c.isalnum() else "-" for c in title.lower())
        entry_id = "-".join(filter(None, slug.split("-"))) or "topic"

        topic_obj = {
            "id": entry_id,
            "title": title,
            "category": cat,
            "tags": tags,
            "summary": summary,
            "quick_facts": {},
            "content": content,
            "fiction_tips": tips,
            "related_entries": [],
            "is_custom": False,
        }

        current = []
        if target_path.exists():
            with open(target_path, "r", encoding="utf-8") as f:
                current = json.load(f)
        current.append(topic_obj)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(current, f, indent=2, ensure_ascii=False)
        print(f"Topic '{title}' successfully saved to {target_path}!")
        return

    # Default: launch the visual GUI Studio
    app = QApplication.instance() or QApplication(sys.argv)
    win = StandaloneReferenceBuilderApp(target_json_path=str(target_path))
    win.show()
    if args.pdf_file and os.path.exists(args.pdf_file):
        win._open_pdf_ingestor(initial_pdf_path=args.pdf_file)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
