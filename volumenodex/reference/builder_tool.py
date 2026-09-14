"""Writers Reference Builder Tool.

Provides both an interactive visual editor and a CLI tool to create, edit,
validate, import, export, and manage offline knowledge entries for fiction writers.
"""

import sys
import os
import argparse
from typing import Optional, Dict, Any, List

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont, QIcon
from PySide6.QtWidgets import (
    QApplication, QDialog, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QTextEdit, QComboBox, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QFileDialog, QScrollArea, QFrame, QSplitter
)

from volumenodex.reference.reference_model import ReferenceEntry, ReferenceCategory
from volumenodex.reference.reference_manager import ReferenceManager


class ReferenceEntryEditorDialog(QDialog):
    """Interactive GUI dialog to add or edit a reference entry."""

    entrySaved = Signal(ReferenceEntry)

    def __init__(self, entry: Optional[ReferenceEntry] = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Reference Entry" if entry else "Add New Reference Entry")
        self.resize(720, 680)
        self.setMinimumSize(540, 500)
        self._existing_entry = entry

        self.setStyleSheet("""
            QDialog {
                background-color: #181922;
                color: #e1e4f2;
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
            }
            QPushButton#primaryBtn:hover {
                background-color: #89b4fa;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        # Title & Category Row
        h_row1 = QHBoxLayout()
        h_row1.setSpacing(12)

        v_title = QVBoxLayout()
        v_title.setSpacing(4)
        v_title.addWidget(QLabel("Topic Title:"))
        self.edit_title = QLineEdit()
        self.edit_title.setPlaceholderText("e.g. Damascus Steel & Crucible Metallurgy")
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
        h_facts_header.addWidget(QLabel("Quick Facts Table:"))
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
        self.table_facts.setColumnWidth(0, 180)
        self.table_facts.setFixedHeight(120)
        v_facts.addWidget(self.table_facts)
        layout.addLayout(v_facts)

        # Detailed Content
        v_content = QVBoxLayout()
        v_content.setSpacing(4)
        v_content.addWidget(QLabel("Deep Historical / Scientific Mechanics:"))
        self.edit_content = QTextEdit()
        self.edit_content.setPlaceholderText("Explain how this actually works in the real world: timelines, chemistry, physics, tactics...")
        v_content.addWidget(self.edit_content)
        layout.addLayout(v_content, stretch=1)

        # Fiction Tips
        v_tips = QVBoxLayout()
        v_tips.setSpacing(4)
        v_tips.addWidget(QLabel("Fiction Writing Tips & Tropes to Avoid:"))
        self.edit_tips = QTextEdit()
        self.edit_tips.setPlaceholderText("Sensory details to describe, common movie clichés to avoid, narrative complications...")
        self.edit_tips.setFixedHeight(85)
        v_tips.addWidget(self.edit_tips)
        layout.addLayout(v_tips)

        # Buttons
        h_btns = QHBoxLayout()
        h_btns.addStretch()
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        h_btns.addWidget(btn_cancel)

        self.btn_save = QPushButton("Save Entry")
        self.btn_save.setObjectName("primaryBtn")
        self.btn_save.clicked.connect(self._save_entry)
        h_btns.addWidget(self.btn_save)
        layout.addLayout(h_btns)

        if entry:
            self._load_entry_data(entry)
        else:
            # Default empty quick facts
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

    def _load_entry_data(self, entry: ReferenceEntry) -> None:
        self.edit_title.setText(entry.title)
        self.combo_category.setCurrentText(entry.category)
        self.edit_tags.setText(", ".join(entry.tags))
        self.edit_summary.setText(entry.summary)
        self.edit_content.setPlainText(entry.content)
        self.edit_tips.setPlainText(entry.fiction_tips)

        self.table_facts.setRowCount(0)
        for k, v in entry.quick_facts.items():
            self._add_fact_row(k, v)

    def _save_entry(self) -> None:
        title = self.edit_title.text().strip()
        if not title:
            QMessageBox.warning(self, "Missing Title", "Please provide a title for the reference topic.")
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

        entry_id = self._existing_entry.id if self._existing_entry else ""
        entry = ReferenceEntry(
            id=entry_id,
            title=title,
            category=category,
            tags=tags,
            summary=summary,
            quick_facts=quick_facts,
            content=content,
            fiction_tips=tips,
            is_custom=True,
        )

        self.entrySaved.emit(entry)
        self.accept()


class ReferenceBuilderWindow(QWidget):
    """Standalone management studio for Writers Reference knowledge base."""

    def __init__(self, manager: Optional[ReferenceManager] = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Writers Reference Knowledge Builder & Manager")
        self.resize(1000, 650)
        self.manager = manager or ReferenceManager()

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
                padding: 6px 12px;
                color: #ffffff;
                font-size: 13px;
            }
            QPushButton {
                background-color: #181922;
                color: #e1e4f2;
                border: 1px solid #2a2c3d;
                border-radius: 5px;
                padding: 6px 14px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #232532;
                border-color: #7aa2f7;
            }
            QPushButton#primaryBtn {
                background-color: #7aa2f7;
                color: #101116;
                border-color: #7aa2f7;
            }
            QTableWidget {
                background-color: #181922;
                border: 1px solid #2a2c3d;
                gridline-color: #20222f;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header
        h_head = QHBoxLayout()
        title_lbl = QLabel("📚 Writers Reference — Knowledge Base Builder")
        title_lbl.setStyleSheet("font-size: 16px; font-weight: 700; color: #7aa2f7;")
        h_head.addWidget(title_lbl)
        h_head.addStretch()

        btn_new = QPushButton("➕ Add New Topic")
        btn_new.setObjectName("primaryBtn")
        btn_new.clicked.connect(self._create_new_entry)
        h_head.addWidget(btn_new)

        btn_import = QPushButton("📥 Import JSON...")
        btn_import.clicked.connect(self._import_json)
        h_head.addWidget(btn_import)

        btn_export = QPushButton("📤 Export JSON...")
        btn_export.clicked.connect(self._export_json)
        h_head.addWidget(btn_export)
        layout.addLayout(h_head)

        # Search Bar
        self.edit_search = QLineEdit()
        self.edit_search.setPlaceholderText("Search all reference topics (title, tags, symptoms, mechanics)...")
        self.edit_search.textChanged.connect(self._refresh_table)
        layout.addWidget(self.edit_search)

        # Table
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Title", "Category", "Tags", "Source"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setColumnWidth(0, 280)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.doubleClicked.connect(self._edit_selected_entry)
        layout.addWidget(self.table)

        # Footer Actions
        h_foot = QHBoxLayout()
        self.lbl_stats = QLabel()
        h_foot.addWidget(self.lbl_stats)
        h_foot.addStretch()

        btn_edit = QPushButton("✏️ Edit Selected")
        btn_edit.clicked.connect(self._edit_selected_entry)
        h_foot.addWidget(btn_edit)

        btn_del = QPushButton("🗑️ Delete Custom")
        btn_del.clicked.connect(self._delete_selected_entry)
        h_foot.addWidget(btn_del)
        layout.addLayout(h_foot)

        self._refresh_table()

    def _refresh_table(self) -> None:
        q = self.edit_search.text()
        entries = self.manager.search(q)
        self.table.setRowCount(0)

        for entry in entries:
            r = self.table.rowCount()
            self.table.insertRow(r)

            item_title = QTableWidgetItem(entry.title)
            item_title.setData(Qt.ItemDataRole.UserRole, entry.id)
            item_cat = QTableWidgetItem(entry.category)
            item_tags = QTableWidgetItem(", ".join(entry.tags))
            item_source = QTableWidgetItem("Custom" if entry.is_custom else "Bundled")

            if entry.is_custom:
                item_source.setForeground(QColor("#7aa2f7"))
            else:
                item_source.setForeground(QColor("#a2a7c4"))

            self.table.setItem(r, 0, item_title)
            self.table.setItem(r, 1, item_cat)
            self.table.setItem(r, 2, item_tags)
            self.table.setItem(r, 3, item_source)

        self.lbl_stats.setText(
            f"Showing {len(entries)} of {self.manager.total_count} topics ({self.manager.custom_count} custom)"
        )

    def _create_new_entry(self) -> None:
        dlg = ReferenceEntryEditorDialog(entry=None, parent=self)
        dlg.entrySaved.connect(self._on_entry_saved)
        dlg.exec()

    def _edit_selected_entry(self) -> None:
        curr = self.table.currentRow()
        if curr < 0:
            return
        entry_id = self.table.item(curr, 0).data(Qt.ItemDataRole.UserRole)
        entry = self.manager.get_entry(entry_id)
        if entry:
            dlg = ReferenceEntryEditorDialog(entry=entry, parent=self)
            dlg.entrySaved.connect(self._on_entry_saved)
            dlg.exec()

    def _delete_selected_entry(self) -> None:
        curr = self.table.currentRow()
        if curr < 0:
            return
        entry_id = self.table.item(curr, 0).data(Qt.ItemDataRole.UserRole)
        entry = self.manager.get_entry(entry_id)
        if not entry:
            return

        if not entry.is_custom:
            QMessageBox.information(
                self, "Cannot Delete Bundled Topic",
                "Bundled topics are part of the core offline encyclopedia and cannot be deleted. You can create custom entries or overrides instead."
            )
            return

        res = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to delete custom topic '{entry.title}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if res == QMessageBox.StandardButton.Yes:
            self.manager.delete_entry(entry_id)
            self._refresh_table()

    def _on_entry_saved(self, entry: ReferenceEntry) -> None:
        self.manager.add_or_update_entry(entry)
        self._refresh_table()

    def _import_json(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Import Reference JSON", "", "JSON Files (*.json)")
        if path:
            count = self.manager.import_from_json(path)
            QMessageBox.information(self, "Import Complete", f"Successfully imported {count} reference topics.")
            self._refresh_table()

    def _export_json(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Export Reference JSON", "writers_reference.json", "JSON Files (*.json)")
        if path:
            success = self.manager.export_to_json(path, include_bundled=True)
            if success:
                QMessageBox.information(self, "Export Complete", f"Knowledge base exported to:\n{path}")


def main_cli():
    """Command-line entry point for Writers Reference Tool."""
    parser = argparse.ArgumentParser(description="Writers Reference Knowledge Builder & CLI Tool")
    parser.add_argument("--gui", action="store_true", help="Launch the standalone Reference Builder GUI Studio")
    parser.add_argument("--list", action="store_true", help="List all available topics")
    parser.add_argument("--search", type=str, help="Search the knowledge base with a query")
    parser.add_argument("--export", type=str, help="Export reference topics to a JSON file")
    parser.add_argument("--import-file", type=str, help="Import reference topics from a JSON file")
    parser.add_argument("--add-topic", action="store_true", help="Interactively add a new topic via CLI prompts")

    args = parser.parse_args()
    mgr = ReferenceManager()

    if args.gui or (len(sys.argv) == 1):
        app = QApplication.instance() or QApplication(sys.argv)
        win = ReferenceBuilderWindow(manager=mgr)
        win.show()
        sys.exit(app.exec())

    if args.list:
        print(f"\n--- Writers Reference ({mgr.total_count} Topics, {mgr.custom_count} Custom) ---")
        for e in mgr.get_all_entries():
            src = "[Custom]" if e.is_custom else "[Bundled]"
            print(f" • {e.title:<45} | {e.category:<22} {src}")
        return

    if args.search:
        results = mgr.search(args.search)
        print(f"\n--- Search Results for '{args.search}' ({len(results)} matches) ---")
        for e in results:
            print(f"\n📌 {e.title} ({e.category})")
            print(f"   Summary: {e.summary}")
            if e.quick_facts:
                print("   Facts:")
                for k, v in e.quick_facts.items():
                    print(f"     - {k}: {v}")
        return

    if args.export:
        success = mgr.export_to_json(args.export)
        if success:
            print(f"Exported knowledge base to {args.export}")
        return

    if args.import_file:
        count = mgr.import_from_json(args.import_file)
        print(f"Imported {count} topics from {args.import_file}")
        return

    if args.add_topic:
        print("\n--- Add New Topic via CLI ---")
        title = input("Title: ").strip()
        if not title:
            print("Title cannot be empty.")
            return
        category = input(f"Category (Default '{ReferenceCategory.CUSTOM_LORE}'): ").strip() or ReferenceCategory.CUSTOM_LORE
        tags_str = input("Tags (comma separated): ").strip()
        tags = [t.strip() for t in tags_str.split(",") if t.strip()]
        summary = input("Summary: ").strip()
        content = input("Detailed Content: ").strip()
        tips = input("Fiction Tips: ").strip()

        entry = ReferenceEntry(
            id="",
            title=title,
            category=category,
            tags=tags,
            summary=summary,
            content=content,
            fiction_tips=tips,
            is_custom=True,
        )
        mgr.add_or_update_entry(entry)
        print(f"Topic '{title}' successfully added to user reference!")
        return


if __name__ == "__main__":
    main_cli()
