"""Collapsible Right Drawer for Scholarly Citations & Bibliography Generation.

Provides an integrated academic reference manager beside the desk gutter in Academic Mode,
complete with on-the-fly multi-style formatting (APA, MLA, Chicago, IEEE, Harvard),
one-click in-text citation injection, and automated bibliography creation.
"""

from typing import Optional, List, Dict
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QFont, QColor, QIcon, QClipboard
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QToolButton, QScrollArea, QFrame, QLineEdit, QComboBox,
    QTextEdit, QDialog, QMessageBox, QApplication
)

from volumenodex.ui.vector_icons import VectorIconFactory
from volumenodex.academic.citation_model import (
    CitationEntry, CitationType, CitationManager, CitationFormatter, CITATION_TYPE_LABELS
)


class CitationEditDialog(QDialog):
    """Sleek modal dialog to add or edit an academic citation entry."""

    def __init__(self, citation_manager: CitationManager, existing_entry: Optional[CitationEntry] = None, parent=None):
        super().__init__(parent)
        self.citation_manager = citation_manager
        self.existing_entry = existing_entry

        self.setWindowTitle("Edit Citation" if existing_entry else "Add New Citation")
        self.setFixedWidth(460)
        self.setStyleSheet("""
            QDialog {
                background-color: #1a1b26;
                color: #c0caf5;
            }
            QLabel {
                color: #9aa5ce;
                font-size: 11px;
                font-weight: 600;
            }
            QLineEdit, QTextEdit, QComboBox {
                background-color: #16161e;
                color: #c0caf5;
                border: 1px solid #292e42;
                border-radius: 5px;
                padding: 5px 8px;
                font-size: 12px;
            }
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus {
                border-color: #7aa2f7;
            }
            QPushButton {
                border-radius: 5px;
                padding: 6px 14px;
                font-weight: 600;
                font-size: 12px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        # Type Selector
        layout.addWidget(QLabel("SOURCE TYPE"))
        self.combo_type = QComboBox()
        for ct in CitationType:
            self.combo_type.addItem(CITATION_TYPE_LABELS.get(ct, ct.value.capitalize()), ct)
        layout.addWidget(self.combo_type)

        # Title
        layout.addWidget(QLabel("WORK TITLE *"))
        self.txt_title = QLineEdit()
        self.txt_title.setPlaceholderText("e.g. Attention Is All You Need")
        layout.addWidget(self.txt_title)

        # Authors
        layout.addWidget(QLabel("AUTHORS (Comma or Semicolon Separated) *"))
        self.txt_authors = QLineEdit()
        self.txt_authors.setPlaceholderText("e.g. Vaswani, Ashish; Shazeer, Noam; Parmar, Niki")
        layout.addWidget(self.txt_authors)

        # Row: Year, Volume, Issue, Pages
        h_nums = QHBoxLayout()
        h_nums.setSpacing(8)

        v_yr = QVBoxLayout()
        v_yr.addWidget(QLabel("YEAR"))
        self.txt_year = QLineEdit()
        self.txt_year.setPlaceholderText("2023")
        v_yr.addWidget(self.txt_year)
        h_nums.addLayout(v_yr, 1)

        v_vol = QVBoxLayout()
        v_vol.addWidget(QLabel("VOLUME"))
        self.txt_vol = QLineEdit()
        self.txt_vol.setPlaceholderText("30")
        v_vol.addWidget(self.txt_vol)
        h_nums.addLayout(v_vol, 1)

        v_iss = QVBoxLayout()
        v_iss.addWidget(QLabel("ISSUE"))
        self.txt_iss = QLineEdit()
        self.txt_iss.setPlaceholderText("2")
        v_iss.addWidget(self.txt_iss)
        h_nums.addLayout(v_iss, 1)

        v_pg = QVBoxLayout()
        v_pg.addWidget(QLabel("PAGES"))
        self.txt_pages = QLineEdit()
        self.txt_pages.setPlaceholderText("112-128")
        v_pg.addWidget(self.txt_pages)
        h_nums.addLayout(v_pg, 1)

        layout.addLayout(h_nums)

        # Source / Journal / Publisher
        layout.addWidget(QLabel("JOURNAL / BOOK / WEBSITE NAME"))
        self.txt_source = QLineEdit()
        self.txt_source.setPlaceholderText("e.g. Journal of Machine Learning Research")
        layout.addWidget(self.txt_source)

        # Publisher & Location
        h_pub = QHBoxLayout()
        h_pub.setSpacing(8)
        v_p1 = QVBoxLayout()
        v_p1.addWidget(QLabel("PUBLISHER"))
        self.txt_publisher = QLineEdit()
        self.txt_publisher.setPlaceholderText("e.g. MIT Press")
        v_p1.addWidget(self.txt_publisher)
        h_pub.addLayout(v_p1, 2)

        v_p2 = QVBoxLayout()
        v_p2.addWidget(QLabel("LOCATION"))
        self.txt_location = QLineEdit()
        self.txt_location.setPlaceholderText("Cambridge, MA")
        v_p2.addWidget(self.txt_location)
        h_pub.addLayout(v_p2, 1)
        layout.addLayout(h_pub)

        # DOI / URL
        h_links = QHBoxLayout()
        h_links.setSpacing(8)
        v_doi = QVBoxLayout()
        v_doi.addWidget(QLabel("DOI"))
        self.txt_doi = QLineEdit()
        self.txt_doi.setPlaceholderText("10.1016/j...")
        v_doi.addWidget(self.txt_doi)
        h_links.addLayout(v_doi, 1)

        v_url = QVBoxLayout()
        v_url.addWidget(QLabel("URL"))
        self.txt_url = QLineEdit()
        self.txt_url.setPlaceholderText("https://...")
        v_url.addWidget(self.txt_url)
        h_links.addLayout(v_url, 2)
        layout.addLayout(h_links)

        # Pre-fill if editing
        if existing_entry:
            idx = self.combo_type.findData(existing_entry.entry_type)
            if idx >= 0:
                self.combo_type.setCurrentIndex(idx)
            self.txt_title.setText(existing_entry.title)
            self.txt_authors.setText("; ".join(existing_entry.authors))
            self.txt_year.setText(existing_entry.year)
            self.txt_vol.setText(existing_entry.volume)
            self.txt_iss.setText(existing_entry.issue)
            self.txt_pages.setText(existing_entry.pages)
            self.txt_source.setText(existing_entry.source_title)
            self.txt_publisher.setText(existing_entry.publisher)
            self.txt_location.setText(existing_entry.publisher_location)
            self.txt_doi.setText(existing_entry.doi)
            self.txt_url.setText(existing_entry.url)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setStyleSheet("background-color: #24283b; color: #9aa5ce; border: 1px solid #3b4261;")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

        btn_save = QPushButton("Save Citation")
        btn_save.setStyleSheet("background-color: #7aa2f7; color: #1a1b26;")
        btn_save.clicked.connect(self._on_save)
        btn_layout.addWidget(btn_save)

        layout.addLayout(btn_layout)

    def _on_save(self) -> None:
        title = self.txt_title.text().strip()
        if not title:
            QMessageBox.warning(self, "Missing Title", "Please specify the title of the work.")
            return

        raw_authors = self.txt_authors.text().strip()
        if ";" in raw_authors:
            authors = [a.strip() for a in raw_authors.split(";") if a.strip()]
        else:
            authors = [a.strip() for a in raw_authors.split(",") if a.strip()]
        if not authors:
            authors = ["Anonymous"]

        entry_type = self.combo_type.currentData()
        entry_id = self.existing_entry.id if self.existing_entry else ""

        entry = CitationEntry(
            id=entry_id or CitationEntry().id,
            entry_type=entry_type,
            title=title,
            authors=authors,
            year=self.txt_year.text().strip(),
            source_title=self.txt_source.text().strip(),
            volume=self.txt_vol.text().strip(),
            issue=self.txt_iss.text().strip(),
            pages=self.txt_pages.text().strip(),
            publisher=self.txt_publisher.text().strip(),
            publisher_location=self.txt_location.text().strip(),
            doi=self.txt_doi.text().strip(),
            url=self.txt_url.text().strip(),
        )

        if self.existing_entry:
            self.citation_manager.update_citation(entry)
        else:
            self.citation_manager.add_citation(entry)

        self.accept()


class CitationCardWidget(QFrame):
    """Card representing a single academic reference with quick action chips."""

    inTextRequested = Signal(str)      # Emits formatted in-text citation string
    copyRequested = Signal(str)        # Emits full reference string
    editRequested = Signal(str)        # Emits citation id
    deleteRequested = Signal(str)      # Emits citation id

    TYPE_COLORS = {
        CitationType.JOURNAL: "#7aa2f7",     # Soft cyan-blue
        CitationType.BOOK: "#bb9af7",        # Amethyst purple
        CitationType.CHAPTER: "#b4f9f8",     # Aqua
        CitationType.CONFERENCE: "#e0af68",  # Warm gold
        CitationType.WEBSITE: "#73daca",     # Emerald
        CitationType.REPORT: "#ff9e64",      # Coral
        CitationType.OTHER: "#9aa5ce",       # Slate
    }

    def __init__(self, citation: CitationEntry, active_style: str = "APA 7th", index: int = 1, parent=None):
        super().__init__(parent)
        self.citation = citation
        self.active_style = active_style
        self.index = index

        self.setObjectName("citationCard")
        self.setStyleSheet("""
            #citationCard {
                background-color: #1f2335;
                border: 1px solid #292e42;
                border-radius: 6px;
                padding: 6px;
            }
            #citationCard:hover {
                background-color: #24283b;
                border-color: #414868;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(5)

        # Top row: Type Badge + Author/Year + Edit/Delete
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(6)

        color = self.TYPE_COLORS.get(citation.entry_type, "#7aa2f7")
        badge = QLabel(citation.entry_type.value.upper() if hasattr(citation.entry_type, "value") else str(citation.entry_type).upper())
        badge.setStyleSheet(f"""
            color: {color};
            background-color: {color}18;
            border: 1px solid {color}44;
            border-radius: 3px;
            padding: 1px 4px;
            font-size: 8px;
            font-weight: 700;
        """)
        top_row.addWidget(badge)

        # Primary author & Year
        primary_lasts = citation.author_last_names
        auth_head = primary_lasts[0] if primary_lasts else "Anonymous"
        if len(primary_lasts) == 2:
            auth_head += f" & {primary_lasts[1]}"
        elif len(primary_lasts) > 2:
            auth_head += " et al."

        yr_head = f"({citation.year})" if citation.year else ""
        lbl_head = QLabel(f"<b>{auth_head}</b> {yr_head}")
        lbl_head.setStyleSheet("color: #c0caf5; font-size: 11px;")
        top_row.addWidget(lbl_head, stretch=1)

        # Edit button
        btn_edit = QToolButton()
        btn_edit.setIcon(VectorIconFactory.create_icon("settings", "#787c99", 12))
        btn_edit.setFixedSize(18, 18)
        btn_edit.setToolTip("Edit citation")
        btn_edit.setStyleSheet("background: transparent; border: none;")
        btn_edit.clicked.connect(lambda: self.editRequested.emit(self.citation.id))
        top_row.addWidget(btn_edit)

        # Delete button
        btn_del = QToolButton()
        btn_del.setIcon(VectorIconFactory.create_icon("close", "#787c99", 12))
        btn_del.setFixedSize(18, 18)
        btn_del.setToolTip("Delete citation")
        btn_del.setStyleSheet("background: transparent; border: none;")
        btn_del.clicked.connect(lambda: self.deleteRequested.emit(self.citation.id))
        top_row.addWidget(btn_del)

        layout.addLayout(top_row)

        # Title
        lbl_title = QLabel(citation.title)
        lbl_title.setWordWrap(True)
        lbl_title.setStyleSheet("color: #9aa5ce; font-size: 11px; font-style: italic;")
        layout.addWidget(lbl_title)

        # Source snippet if available
        if citation.source_title:
            src_text = citation.source_title
            if citation.volume:
                src_text += f" {citation.volume}"
                if citation.issue:
                    src_text += f"({citation.issue})"
            lbl_src = QLabel(src_text)
            lbl_src.setWordWrap(True)
            lbl_src.setStyleSheet("color: #565f89; font-size: 10px;")
            layout.addWidget(lbl_src)

        # Action Buttons: [ In-Text ] and [ Copy Ref ]
        bot_row = QHBoxLayout()
        bot_row.setContentsMargins(0, 4, 0, 0)
        bot_row.setSpacing(6)

        in_text_sample = CitationFormatter.format_in_text(citation, style=active_style, index=index)
        btn_in_text = QPushButton(f"Insert {in_text_sample}")
        btn_in_text.setToolTip(f"Insert in-text citation '{in_text_sample}' at document cursor")
        btn_in_text.setStyleSheet("""
            QPushButton {
                background-color: #1a1b26;
                color: #7aa2f7;
                border: 1px solid #3b4261;
                border-radius: 4px;
                padding: 3px 8px;
                font-size: 10px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #24283b;
                border-color: #7aa2f7;
            }
        """)
        btn_in_text.clicked.connect(lambda: self.inTextRequested.emit(in_text_sample))
        bot_row.addWidget(btn_in_text, stretch=1)

        btn_copy = QPushButton("Copy")
        btn_copy.setToolTip("Copy full reference to clipboard")
        btn_copy.setFixedWidth(46)
        btn_copy.setStyleSheet("""
            QPushButton {
                background-color: #1a1b26;
                color: #9aa5ce;
                border: 1px solid #3b4261;
                border-radius: 4px;
                padding: 3px 4px;
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: #24283b;
                color: #c0caf5;
            }
        """)
        full_ref = CitationFormatter.format_bibliography_entry(citation, style=active_style, index=index)
        btn_copy.clicked.connect(lambda: self.copyRequested.emit(full_ref))
        bot_row.addWidget(btn_copy)

        layout.addLayout(bot_row)


class CitationGeneratorDrawer(QWidget):
    """Collapsible Right Push-Panel Drawer for Citations & Bibliography Management."""

    insertInTextRequested = Signal(str)
    insertBibliographyRequested = Signal(str)
    collapsedChanged = Signal(bool)
    citationUpdated = Signal()

    EXPANDED_WIDTH = 310
    COLLAPSED_WIDTH = 32

    def __init__(self, citation_manager: CitationManager, parent=None):
        super().__init__(parent)
        self.citation_manager = citation_manager
        self.is_collapsed = False
        self._cards: Dict[str, CitationCardWidget] = {}

        self._init_ui()
        self.setFixedWidth(self.EXPANDED_WIDTH)
        self.refresh()

    def _init_ui(self) -> None:
        self.setObjectName("citationDrawer")
        self.setStyleSheet("""
            #citationDrawer {
                background-color: #16161e;
                border-left: 1px solid #24283b;
            }
        """)

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Collapsed strip (left edge)
        self.collapsed_bar = QWidget(self)
        self.collapsed_bar.setFixedWidth(self.COLLAPSED_WIDTH)
        self.collapsed_bar.setStyleSheet("background-color: #13141c; border-left: 1px solid #1f2335;")
        cb_layout = QVBoxLayout(self.collapsed_bar)
        cb_layout.setContentsMargins(4, 10, 4, 10)
        cb_layout.setSpacing(10)

        self.btn_toggle_expand = QToolButton(self)
        self.btn_toggle_expand.setIcon(VectorIconFactory.create_icon("chevron_left", "#7aa2f7", 14))
        self.btn_toggle_expand.setFixedSize(24, 24)
        self.btn_toggle_expand.setToolTip("Expand Citations Drawer (Ctrl+Alt+C)")
        self.btn_toggle_expand.clicked.connect(self.toggle_collapsed)
        self.btn_toggle_expand.setStyleSheet("background: transparent; border: none;")
        cb_layout.addWidget(self.btn_toggle_expand, alignment=Qt.AlignmentFlag.AlignHCenter)

        lbl_strip_icon = QLabel(self)
        lbl_strip_icon.setPixmap(VectorIconFactory.create_icon("navigator", "#9aa5ce", 16).pixmap(16, 16))
        cb_layout.addWidget(lbl_strip_icon, alignment=Qt.AlignmentFlag.AlignHCenter)

        cb_layout.addStretch()
        main_layout.addWidget(self.collapsed_bar)
        self.collapsed_bar.hide()

        # 2. Expanded Container
        self.expanded_container = QWidget(self)
        ec_layout = QVBoxLayout(self.expanded_container)
        ec_layout.setContentsMargins(8, 8, 8, 8)
        ec_layout.setSpacing(8)

        # Header: Icon + Title + Collapse Button
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(6)

        icon_lbl = QLabel(self)
        icon_lbl.setPixmap(VectorIconFactory.create_icon("navigator", "#7aa2f7", 18).pixmap(18, 18))
        header.addWidget(icon_lbl)

        title_lbl = QLabel("Citations & Sources", self)
        font = QFont("Segoe UI", 11, QFont.Weight.Bold)
        title_lbl.setFont(font)
        title_lbl.setStyleSheet("color: #c0caf5;")
        header.addWidget(title_lbl, stretch=1)

        self.btn_collapse = QToolButton(self)
        self.btn_collapse.setIcon(VectorIconFactory.create_icon("chevron_right", "#9aa5ce", 14))
        self.btn_collapse.setFixedSize(24, 24)
        self.btn_collapse.setToolTip("Collapse Drawer")
        self.btn_collapse.clicked.connect(self.toggle_collapsed)
        self.btn_collapse.setStyleSheet("""
            QToolButton { background: transparent; border: 1px solid transparent; border-radius: 4px; }
            QToolButton:hover { background: #1f2335; border-color: #3b4261; }
        """)
        header.addWidget(self.btn_collapse)
        ec_layout.addLayout(header)

        # Style Selector Row: "Style: [ APA 7th ▼ ]"
        style_row = QHBoxLayout()
        style_row.setSpacing(6)
        lbl_style = QLabel("STYLE:", self)
        lbl_style.setStyleSheet("color: #787c99; font-size: 10px; font-weight: 700;")
        style_row.addWidget(lbl_style)

        self.combo_style = QComboBox(self)
        for s in CitationFormatter.SUPPORTED_STYLES:
            self.combo_style.addItem(s)
        self.combo_style.setCurrentText(self.citation_manager.active_style)
        self.combo_style.setStyleSheet("""
            QComboBox {
                background-color: #1f2335;
                color: #c0caf5;
                border: 1px solid #292e42;
                border-radius: 4px;
                padding: 3px 8px;
                font-size: 11px;
                font-weight: 600;
            }
            QComboBox:hover { border-color: #7aa2f7; }
        """)
        self.combo_style.currentTextChanged.connect(self._on_style_changed)
        style_row.addWidget(self.combo_style, stretch=1)
        ec_layout.addLayout(style_row)

        # Search Bar
        self.search_input = QLineEdit(self)
        self.search_input.setPlaceholderText("Search authors, titles, years...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: #1a1b26;
                color: #c0caf5;
                border: 1px solid #292e42;
                border-radius: 5px;
                padding: 5px 8px;
                font-size: 11px;
            }
            QLineEdit:focus { border-color: #7aa2f7; }
        """)
        self.search_input.textChanged.connect(self._on_search_text_changed)
        ec_layout.addWidget(self.search_input)

        # Action Buttons: "+ Add Citation" and "📚 Insert Bibliography"
        act_row = QHBoxLayout()
        act_row.setSpacing(6)

        btn_add = QPushButton("+ Add Citation", self)
        btn_add.setStyleSheet("""
            QPushButton {
                background-color: #24283b;
                color: #7aa2f7;
                border: 1px solid #3b4261;
                border-radius: 5px;
                padding: 5px 10px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #2e344e;
                border-color: #7aa2f7;
            }
        """)
        btn_add.clicked.connect(self._open_new_citation_dialog)
        act_row.addWidget(btn_add)

        btn_insert_bib = QPushButton("📚 Bibliography", self)
        btn_insert_bib.setToolTip("Insert fully formatted References / Bibliography into manuscript")
        btn_insert_bib.setStyleSheet("""
            QPushButton {
                background-color: rgba(122, 162, 247, 0.15);
                color: #7aa2f7;
                border: 1px solid #7aa2f7;
                border-radius: 5px;
                padding: 5px 10px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: rgba(122, 162, 247, 0.28);
            }
        """)
        btn_insert_bib.clicked.connect(self._insert_full_bibliography)
        act_row.addWidget(btn_insert_bib)

        ec_layout.addLayout(act_row)

        # Scroll Area for Citations
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.cards_container = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(0, 4, 0, 4)
        self.cards_layout.setSpacing(6)
        self.cards_layout.addStretch()

        self.scroll_area.setWidget(self.cards_container)
        ec_layout.addWidget(self.scroll_area, stretch=1)

        main_layout.addWidget(self.expanded_container)

    def _on_style_changed(self, new_style: str) -> None:
        self.citation_manager.active_style = new_style
        self.refresh()

    def _on_search_text_changed(self, text: str) -> None:
        self.refresh(search_query=text)

    def refresh(self, search_query: str = "") -> None:
        """Rebuilds citation cards list."""
        # Clear existing cards
        while self.cards_layout.count() > 1:
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self._cards.clear()
        citations = self.citation_manager.search(search_query) if search_query else self.citation_manager.citations
        active_style = self.citation_manager.active_style

        if not citations:
            empty_lbl = QLabel("No citations recorded yet.\nClick '+ Add Citation' to begin.", self)
            empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_lbl.setStyleSheet("color: #565f89; font-size: 11px; padding: 30px 10px;")
            self.cards_layout.insertWidget(0, empty_lbl)
            return

        for idx, cit in enumerate(citations, start=1):
            card = CitationCardWidget(cit, active_style=active_style, index=idx, parent=self)
            card.inTextRequested.connect(self.insertInTextRequested.emit)
            card.copyRequested.connect(self._copy_to_clipboard)
            card.editRequested.connect(self._edit_citation)
            card.deleteRequested.connect(self._delete_citation)
            self._cards[cit.id] = card
            self.cards_layout.insertWidget(self.cards_layout.count() - 1, card)

    def _copy_to_clipboard(self, text: str) -> None:
        # Strip simple HTML formatting tags for clean text copying
        plain = text.replace("<i>", "").replace("</i>", "").replace("<b>", "").replace("</b>", "")
        QApplication.clipboard().setText(plain)
        QMessageBox.information(self, "Citation Copied", f"Formatted reference copied to clipboard:\n\n{plain}")

    def _open_new_citation_dialog(self) -> None:
        dlg = CitationEditDialog(self.citation_manager, existing_entry=None, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.refresh()
            self.citationUpdated.emit()

    def _edit_citation(self, citation_id: str) -> None:
        cit = self.citation_manager.get_citation(citation_id)
        if cit:
            dlg = CitationEditDialog(self.citation_manager, existing_entry=cit, parent=self)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                self.refresh()
                self.citationUpdated.emit()

    def _delete_citation(self, citation_id: str) -> None:
        reply = QMessageBox.question(
            self, "Delete Citation",
            "Are you sure you want to remove this citation from the bibliography?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.citation_manager.delete_citation(citation_id)
            self.refresh()
            self.citationUpdated.emit()

    def _insert_full_bibliography(self) -> None:
        if not self.citation_manager.citations:
            QMessageBox.information(self, "No Citations", "Add at least one citation before generating the bibliography.")
            return

        html_bib = CitationFormatter.generate_bibliography(
            self.citation_manager.citations,
            style=self.citation_manager.active_style
        )
        full_html = f"<h2>References</h2>\n{html_bib}"
        self.insertBibliographyRequested.emit(full_html)

    def toggle_collapsed(self) -> None:
        self.set_collapsed(not self.is_collapsed)

    def set_collapsed(self, collapsed: bool) -> None:
        self.is_collapsed = collapsed
        if collapsed:
            self.expanded_container.hide()
            self.collapsed_bar.show()
            self.setFixedWidth(self.COLLAPSED_WIDTH)
            self.btn_toggle_expand.setIcon(VectorIconFactory.create_icon("chevron_left", "#7aa2f7", 14))
        else:
            self.collapsed_bar.hide()
            self.expanded_container.show()
            self.setFixedWidth(self.EXPANDED_WIDTH)
            self.btn_collapse.setIcon(VectorIconFactory.create_icon("chevron_right", "#9aa5ce", 14))
        self.collapsedChanged.emit(self.is_collapsed)
