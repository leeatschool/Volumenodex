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
    QFileDialog, QScrollArea, QFrame, QSplitter
)

from volumenodex.reference.reference_model import ReferenceEntry, ReferenceCategory


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

        self.entrySaved.emit(res_dict)
        self.accept()


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

        h_head.addStretch()

        btn_new = QPushButton("➕ Add New Topic")
        btn_new.setObjectName("primaryBtn")
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

    args = parser.parse_args()
    target_path = Path(args.file)

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
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
