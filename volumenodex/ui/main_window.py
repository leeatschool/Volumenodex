"""Main application window for Volumenodex Word Processing Studio."""

import os
from datetime import datetime
from typing import Optional
from PySide6.QtCore import Qt, QTime, QDate, QTimer, QThreadPool
from PySide6.QtGui import (
    QFont, QColor, QTextCursor, QTextBlockFormat, QTextCharFormat,
    QTextListFormat, QAction, QKeySequence, QIcon, QCloseEvent, QActionGroup
)
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFileDialog,
    QColorDialog, QMessageBox, QApplication, QStackedWidget, QInputDialog
)

from volumenodex.core.document_model import (
    PageLayoutModel, PaperSizePreset, Orientation, PageMargins, DocumentStatistics,
    DocumentMode, DOCUMENT_MODE_TITLES
)
from volumenodex.canvas.paper_texture import PaperTextureEngine, TextureType
from volumenodex.core.theme_manager import ThemeManager
from volumenodex.core.io_manager import IOManager
from volumenodex.ui.ribbon import RibbonBar
from volumenodex.ui.ruler import InteractiveRuler
from volumenodex.canvas.paginated_canvas import PaginatedCanvas
from volumenodex.ui.status_bar import VolumenodexStatusBar
from volumenodex.pet.pet_model import PetProfile, PetMood, DEFAULT_PETS
from volumenodex.pet.insight_engine import InsightEngine
from volumenodex.pet.pet_dock import FloatingPetDock
from volumenodex.pet.pet_dialog import PetSelectionDialog, BreakTimerDialog
from volumenodex.pet.companion_figures import CompanionFigureRenderer
from volumenodex.audio.audio_engine import AudioEngine, TypewriterSoundPreset, AmbientSoundPreset
from volumenodex.corkboard import CorkboardManager, CorkboardView, IndexCard
from volumenodex.story import CodexManager, ChapterNavigatorDrawer, CharacterCodexDrawer
from volumenodex.story.codex_extractor import CodexExtractionEngine
from volumenodex.review import RevisionLensEngine, RevisionInspectorDrawer, LensFinding, SpellCheckEngine
from volumenodex.review.revision_worker import ReviewWorker
from volumenodex.academic.citation_model import CitationManager, CitationEntry, CitationFormatter
from volumenodex.academic.citation_drawer import CitationGeneratorDrawer
from volumenodex.ui.new_document_dialog import NewDocumentDialog
from volumenodex.ui.clipart_dialog import ClipArtDialog
from volumenodex.core.settings_manager import SettingsManager
from volumenodex.ui.settings_dialog import SettingsDialog


class MainWindow(QMainWindow):
    """The central studio window for Volumenodex."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Volumenodex — Untitled Document")
        self.resize(1280, 850)

        # Core Engines
        self.theme_manager = ThemeManager("Deep Midnight Studio", dark_paper=False)
        self.layout_model = PageLayoutModel()
        self.texture_engine = PaperTextureEngine()
        self.codex_manager = CodexManager()
        self.citation_manager = CitationManager()
        self.spell_engine = SpellCheckEngine()
        self.document_mode: DocumentMode = DocumentMode.CREATIVE_FICTION
        self.current_file_path: Optional[str] = None
        self.story_metadata: dict = {}
        self.custom_pets: dict = {}
        self.custom_styles: dict = {}

        # Proofreading & Revision Lenses State (Enabled automatically by default)
        self.active_lenses = {
            "spelling": True,
            "adverb": True,
            "passive": True,
            "pacing": False,
            "filler": True,
            "dialogue": False,
        }
        self.revision_mode_active = True
        self._revision_request_id = 0
        self._lens_debounce_timer = QTimer(self)
        self._lens_debounce_timer.setSingleShot(True)
        self._lens_debounce_timer.setInterval(300)
        self._lens_debounce_timer.timeout.connect(self._run_revision_analysis)

        # Performance Debounce Timers (Eliminates typing and multi-page lag)
        self._metrics_debounce_timer = QTimer(self)
        self._metrics_debounce_timer.setSingleShot(True)
        self._metrics_debounce_timer.setInterval(250)
        self._metrics_debounce_timer.timeout.connect(self._run_debounced_metrics)

        self._mention_debounce_timer = QTimer(self)
        self._mention_debounce_timer.setSingleShot(True)
        self._mention_debounce_timer.setInterval(150)
        self._mention_debounce_timer.timeout.connect(self._check_live_mentions)

        self._codex_extract_timer = QTimer(self)
        self._codex_extract_timer.setSingleShot(True)
        self._codex_extract_timer.setInterval(1500)
        self._codex_extract_timer.timeout.connect(self._run_codex_auto_extract)

        # Writing Pet / Scribe Companion Engine
        self.pet_engine = InsightEngine(self)

        # Sensory Audio Engine
        self.audio_engine = AudioEngine(parent=self)

        # Settings and Variable Auto-Save
        self.settings_manager = SettingsManager(self)
        self._autosave_timer = QTimer(self)
        self._autosave_timer.timeout.connect(self._on_autosave_timer)
        self.settings_manager.settingsChanged.connect(self._apply_autosave_settings)

        # Apply global theme stylesheet
        self.setStyleSheet(self.theme_manager.generate_qss())

        # Central Layout Assembly
        self._init_ui()
        self._init_menu_bar()
        self._connect_signals()
        self._apply_autosave_settings()

        # Initial Document Content & Metrics
        self._populate_initial_manuscript()
        self._update_metrics()
        self._reposition_pet_dock()
        self._schedule_revision_analysis()

    def _init_ui(self) -> None:
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # 1. Top Tabbed Ribbon
        self.ribbon = RibbonBar(self)
        root_layout.addWidget(self.ribbon)

        # 2. Main Workspace Stack (Canvas Mode vs Corkboard Mode)
        self.main_stack = QStackedWidget(self)
        root_layout.addWidget(self.main_stack, stretch=1)

        # Mode 0: Main Paginated Canvas Workspace (with flush Left & Right Story Drawers)
        self.canvas_workspace = QWidget()
        cw_layout = QHBoxLayout(self.canvas_workspace)
        cw_layout.setContentsMargins(0, 0, 0, 0)
        cw_layout.setSpacing(0)

        # Left Push Panel: Chapter & Scene Outline Navigator
        self.left_navigator = ChapterNavigatorDrawer(self.canvas_workspace)
        cw_layout.addWidget(self.left_navigator)

        # Center Column: Interactive Ruler + Paginated Canvas Area
        center_container = QWidget(self.canvas_workspace)
        center_layout = QVBoxLayout(center_container)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(0)

        self.ruler = InteractiveRuler(self.layout_model, center_container)
        center_layout.addWidget(self.ruler)

        self.canvas_area = PaginatedCanvas(
            self.layout_model, self.texture_engine, self.theme_manager, center_container
        )
        self.canvas_area.spell_engine = self.spell_engine
        center_layout.addWidget(self.canvas_area, stretch=1)
        cw_layout.addWidget(center_container, stretch=1)

        # Right Push Panel Stack: Worldbuilding Codex vs Revision Inspector vs Citation Generator
        self.right_stack = QStackedWidget(self.canvas_workspace)

        self.right_codex = CharacterCodexDrawer(self.codex_manager, self.right_stack)
        self.right_stack.addWidget(self.right_codex)

        self.revision_inspector = RevisionInspectorDrawer(self.right_stack)
        self.revision_inspector.spell_engine = self.spell_engine
        self.right_stack.addWidget(self.revision_inspector)

        self.citation_drawer = CitationGeneratorDrawer(self.citation_manager, self.right_stack)
        self.right_stack.addWidget(self.citation_drawer)

        self.right_stack.setCurrentWidget(self.right_codex)
        self.right_stack.setFixedWidth(self.right_codex.width())
        cw_layout.addWidget(self.right_stack)

        self.main_stack.addWidget(self.canvas_workspace)

        # Mode 1: Hybrid Corkboard & Index Card Studio
        self.corkboard_manager = CorkboardManager()
        self.corkboard_view = CorkboardView(self.corkboard_manager, self)
        self.main_stack.addWidget(self.corkboard_view)

        # 3. Floating Scribe Companion (Writing Pet)
        self.pet_dock = FloatingPetDock(self.pet_engine, self.canvas_area.viewport())
        self.pet_dock.show()

        # 4. Status Bar
        self.status_bar = VolumenodexStatusBar(self)
        root_layout.addWidget(self.status_bar)

        # Configure initial default active lens buttons on ribbon
        self.ribbon.btn_rev_mode.setChecked(True)
        self.ribbon.btn_spell.setChecked(True)
        self.ribbon.btn_adverbs.setChecked(True)
        self.ribbon.btn_passive.setChecked(True)
        self.ribbon.btn_filler.setChecked(True)

    def _init_menu_bar(self) -> None:
        menu_bar = self.menuBar()

        # File Menu
        file_menu = menu_bar.addMenu("&File")

        act_new = QAction("New Document", self)
        act_new.setShortcut(QKeySequence.StandardKey.New)
        act_new.triggered.connect(self.new_document)
        file_menu.addAction(act_new)

        act_open = QAction("Open (.docx)...", self)
        act_open.setShortcut(QKeySequence.StandardKey.Open)
        act_open.triggered.connect(self.open_document)
        file_menu.addAction(act_open)

        file_menu.addSeparator()

        act_save = QAction("Save", self)
        act_save.setShortcut(QKeySequence.StandardKey.Save)
        act_save.triggered.connect(self.save_document)
        file_menu.addAction(act_save)

        act_save_as = QAction("Save As...", self)
        act_save_as.setShortcut(QKeySequence.StandardKey.SaveAs)
        act_save_as.triggered.connect(self.save_document_as)
        file_menu.addAction(act_save_as)

        act_export_pdf = QAction("Export to PDF...", self)
        act_export_pdf.setShortcut(QKeySequence("Ctrl+Shift+E"))
        act_export_pdf.triggered.connect(self.export_pdf)
        file_menu.addAction(act_export_pdf)

        file_menu.addSeparator()

        act_exit = QAction("Exit", self)
        act_exit.setShortcut(QKeySequence.StandardKey.Quit)
        act_exit.triggered.connect(self.close)
        file_menu.addAction(act_exit)

        # Edit Menu
        edit_menu = menu_bar.addMenu("&Edit")
        act_undo = QAction("Undo", self)
        act_undo.setShortcut(QKeySequence.StandardKey.Undo)
        act_undo.triggered.connect(self.editor.undo)
        edit_menu.addAction(act_undo)

        act_redo = QAction("Redo", self)
        act_redo.setShortcut(QKeySequence.StandardKey.Redo)
        act_redo.triggered.connect(self.editor.redo)
        edit_menu.addAction(act_redo)

        edit_menu.addSeparator()

        act_cut = QAction("Cut", self)
        act_cut.setShortcut(QKeySequence.StandardKey.Cut)
        act_cut.triggered.connect(self.editor.cut)
        edit_menu.addAction(act_cut)

        act_copy = QAction("Copy", self)
        act_copy.setShortcut(QKeySequence.StandardKey.Copy)
        act_copy.triggered.connect(self.editor.copy)
        edit_menu.addAction(act_copy)

        act_paste = QAction("Paste", self)
        act_paste.setShortcut(QKeySequence.StandardKey.Paste)
        act_paste.triggered.connect(self.editor.paste)
        edit_menu.addAction(act_paste)

        act_paste_plain = QAction("Paste without Formatting", self)
        act_paste_plain.setShortcut(QKeySequence("Ctrl+Shift+V"))
        act_paste_plain.triggered.connect(self._paste_plain_text)
        edit_menu.addAction(act_paste_plain)

        edit_menu.addSeparator()

        act_find = QAction("Find...", self)
        act_find.setShortcut(QKeySequence.StandardKey.Find)
        act_find.triggered.connect(lambda: self.canvas_area.show_find(replace_mode=False))
        edit_menu.addAction(act_find)

        act_replace = QAction("Replace...", self)
        act_replace.setShortcut(QKeySequence.StandardKey.Replace)
        act_replace.triggered.connect(lambda: self.canvas_area.show_find(replace_mode=True))
        edit_menu.addAction(act_replace)

        act_find_next = QAction("Find Next", self)
        act_find_next.setShortcut(QKeySequence("F3"))
        act_find_next.triggered.connect(self._on_find_next_shortcut)
        edit_menu.addAction(act_find_next)

        act_find_prev = QAction("Find Previous", self)
        act_find_prev.setShortcut(QKeySequence("Shift+F3"))
        act_find_prev.triggered.connect(self._on_find_prev_shortcut)
        edit_menu.addAction(act_find_prev)

        edit_menu.addSeparator()

        act_select_all = QAction("Select All", self)
        act_select_all.setShortcut(QKeySequence.StandardKey.SelectAll)
        act_select_all.triggered.connect(self.editor.selectAll)
        edit_menu.addAction(act_select_all)

        # View Menu
        view_menu = menu_bar.addMenu("&View")
        act_zen = QAction("Zen / Distraction-Free Mode", self)
        act_zen.setShortcut(QKeySequence("F11"))
        act_zen.triggered.connect(self.toggle_zen_mode)
        view_menu.addAction(act_zen)

        view_menu.addSeparator()

        act_nav = QAction("Chapter Outline Navigator", self)
        act_nav.setShortcut(QKeySequence("Ctrl+Alt+N"))
        act_nav.triggered.connect(self.left_navigator.toggle_collapsed)
        view_menu.addAction(act_nav)

        act_codex = QAction("Story Codex", self)
        act_codex.setShortcut(QKeySequence("Ctrl+Alt+C"))
        act_codex.triggered.connect(self._toggle_codex_panel)
        view_menu.addAction(act_codex)

        act_insp = QAction("Revision Inspector", self)
        act_insp.setShortcut(QKeySequence("Ctrl+Alt+R"))
        act_insp.triggered.connect(self._toggle_inspector_panel)
        view_menu.addAction(act_insp)

        # Settings Menu
        settings_menu = menu_bar.addMenu("&Settings")

        # Variable Auto-Save Submenu
        self.menu_autosave = settings_menu.addMenu("Auto-&Save Frequency")
        self.act_autosave_enable = QAction("Enable Auto-Save", self)
        self.act_autosave_enable.setCheckable(True)
        self.act_autosave_enable.setChecked(self.settings_manager.autosave_enabled)
        self.act_autosave_enable.toggled.connect(self._on_menu_autosave_toggled)
        self.menu_autosave.addAction(self.act_autosave_enable)
        self.menu_autosave.addSeparator()

        self.autosave_action_group = QActionGroup(self)
        self.autosave_action_group.setExclusive(True)
        self._autosave_interval_actions = {}
        for minutes in [1, 2, 5, 10, 15, 30]:
            label = f"Every {minutes} Minute" if minutes == 1 else f"Every {minutes} Minutes"
            if minutes == 2:
                label += " (Default)"
            act = QAction(label, self)
            act.setCheckable(True)
            act.setData(minutes)
            if minutes == self.settings_manager.autosave_interval_minutes:
                act.setChecked(True)
            act.triggered.connect(lambda checked=False, m=minutes: self._on_menu_autosave_interval_triggered(m))
            self.autosave_action_group.addAction(act)
            self.menu_autosave.addAction(act)
            self._autosave_interval_actions[minutes] = act

        settings_menu.addSeparator()

        act_prefs = QAction("Studio Preferences...", self)
        act_prefs.setShortcut(QKeySequence("Ctrl+,"))
        act_prefs.triggered.connect(self._show_settings_dialog)
        settings_menu.addAction(act_prefs)

        # Help Menu
        help_menu = menu_bar.addMenu("&Help")
        act_about = QAction("About Volumenodex", self)
        act_about.triggered.connect(self._show_about_dialog)
        help_menu.addAction(act_about)

    def _connect_signals(self) -> None:
        ed = self.editor

        # Clipboard
        self.ribbon.btn_paste.clicked.connect(ed.paste)
        self.ribbon.btn_paste_plain.clicked.connect(self._paste_plain_text)
        self.ribbon.btn_cut.clicked.connect(ed.cut)
        self.ribbon.btn_copy.clicked.connect(ed.copy)
        self.ribbon.pasteRequested.connect(ed.paste)
        self.ribbon.pastePlainRequested.connect(self._paste_plain_text)
        self.ribbon.cutRequested.connect(ed.cut)
        self.ribbon.copyRequested.connect(ed.copy)

        # Search & Replace
        self.ribbon.findRequested.connect(lambda: self.canvas_area.show_find(replace_mode=False))
        self.ribbon.replaceRequested.connect(lambda: self.canvas_area.show_find(replace_mode=True))

        # Formatting
        self.ribbon.fontFamilyChanged.connect(ed.setFontFamily)
        self.ribbon.fontSizeChanged.connect(ed.setFontPointSize)
        self.ribbon.boldToggled.connect(self._toggle_bold)
        self.ribbon.italicToggled.connect(self._toggle_italic)
        self.ribbon.underlineToggled.connect(self._toggle_underline)
        self.ribbon.strikeToggled.connect(self._toggle_strike)
        self.ribbon.textColorRequested.connect(self._choose_text_color)
        self.ribbon.highlightColorRequested.connect(self._choose_highlight_color)

        # Paragraph Alignment & Spacing
        self.ribbon.alignLeftRequested.connect(lambda: ed.setAlignment(Qt.AlignmentFlag.AlignLeft))
        self.ribbon.alignCenterRequested.connect(lambda: ed.setAlignment(Qt.AlignmentFlag.AlignCenter))
        self.ribbon.alignRightRequested.connect(lambda: ed.setAlignment(Qt.AlignmentFlag.AlignRight))
        self.ribbon.alignJustifyRequested.connect(lambda: ed.setAlignment(Qt.AlignmentFlag.AlignJustify))
        self.ribbon.lineSpacingChanged.connect(self._set_line_spacing)
        self.ribbon.bulletListRequested.connect(self._toggle_bullet_list)
        self.ribbon.numberedListRequested.connect(self._toggle_numbered_list)
        self.ribbon.styleSelected.connect(self._apply_style)
        self.ribbon.saveCurrentStyleRequested.connect(self._on_save_current_style)
        self.ribbon.customStyleSelected.connect(self._on_custom_style_selected)

        # Insert actions
        self.ribbon.pageBreakRequested.connect(self._insert_page_break)
        self.ribbon.horizontalRuleRequested.connect(self._insert_horizontal_rule)
        self.ribbon.dateTimeRequested.connect(self._insert_date_time)
        self.ribbon.symbolRequested.connect(self._insert_symbol)
        self.ribbon.insertImageRequested.connect(self._on_insert_image)
        self.ribbon.insertClipArtRequested.connect(self._on_insert_clip_art)

        # Page Setup & Print Fidelity
        self.ribbon.paperSizeChanged.connect(self._on_paper_size_changed)
        self.ribbon.orientationChanged.connect(self._on_orientation_changed)
        self.ribbon.marginsChanged.connect(self._on_margins_preset_changed)
        self.ribbon.textureTypeChanged.connect(self._on_texture_type_changed)
        self.ribbon.textureOpacityChanged.connect(self._on_texture_opacity_changed)
        self.ribbon.darkPaperToggled.connect(self._on_dark_paper_toggled)
        self.ribbon.cropMarksToggled.connect(self._on_crop_marks_toggled)

        # Modes & Display
        self.ribbon.rulerToggled.connect(self.ruler.setVisible)
        self.ribbon.zoomChanged.connect(self._on_zoom_changed)
        self.status_bar.zoomChanged.connect(self._on_zoom_changed)
        self.ribbon.themeChanged.connect(self._on_theme_changed)
        self.ribbon.zenModeRequested.connect(self.toggle_zen_mode)
        self.ribbon.statisticsRequested.connect(self._show_statistics_dialog)

        # Ruler interaction
        self.ruler.marginsChanged.connect(self._on_ruler_margins_dragged)
        self.canvas_area.pageOffsetChanged.connect(self.ruler.set_page_offset)

        # Text changes & cursor updates (Zero-Latency Debounced Architecture)
        ed.textChanged.connect(self._on_canvas_text_changed)
        ed.cursorPositionChanged.connect(self._on_canvas_cursor_changed)

        # Writing Pet / Scribe Companion connections
        self.ribbon.btn_pet.clicked.connect(self._toggle_pet_dock)
        self.status_bar.petClicked.connect(self._open_pet_selection_dialog)
        self.pet_dock.settingsRequested.connect(self._open_pet_selection_dialog)
        self.pet_dock.breakSettingsRequested.connect(self._open_break_timer_dialog)
        self.pet_dock.dismissRequested.connect(self._on_pet_dock_dismissed)
        self.pet_engine.moodChanged.connect(self._on_pet_mood_changed)

        # Sensory Audio connections
        ed.keystrokeHappened.connect(self.audio_engine.play_keystroke)
        self.ribbon.typewriterSoundChanged.connect(self.audio_engine.set_typewriter_preset)
        self.ribbon.ambientSoundChanged.connect(self.audio_engine.set_ambient_preset)

        # Corkboard mode switching & synchronization
        self.ribbon.btn_corkboard.clicked.connect(self.toggle_corkboard_mode)
        self.corkboard_view.returnToManuscriptRequested.connect(self.show_manuscript_mode)
        self.corkboard_view.jumpToSectionRequested.connect(self._on_jump_to_scene_from_card)
        self.corkboard_view.reorderManuscriptRequested.connect(self._reorder_manuscript_from_cards)

        # Story Drawers
        self.ribbon.tab_widget.currentChanged.connect(self._on_ribbon_tab_changed)
        self.ribbon.navigatorToggled.connect(self.left_navigator.toggle_collapsed)
        self.ribbon.codexToggled.connect(self._toggle_codex_panel)
        self.left_navigator.collapsedChanged.connect(lambda c: self.ribbon.btn_navigator.setChecked(not c))
        self.right_codex.collapsedChanged.connect(self._on_codex_collapsed_changed)

        self.left_navigator.chapterSelected.connect(self.canvas_area.scroll_to_position)
        self.left_navigator.newChapterRequested.connect(self._on_add_chapter_requested)
        self.left_navigator.reorderChaptersRequested.connect(self._on_reorder_chapters_requested)

        self.right_codex.insertTextRequested.connect(self.canvas_area.insert_text_at_cursor)
        self.right_codex.autoExtractRequested.connect(self._run_codex_auto_extract_manual)

        # Proofreading Lenses, Spell Check & Revision Inspector
        self.ribbon.revisionModeToggled.connect(self._toggle_revision_mode)
        self.ribbon.spellCheckToggled.connect(lambda: self._toggle_lens("spelling"))
        self.ribbon.adverbsLensToggled.connect(lambda: self._toggle_lens("adverb"))
        self.ribbon.passiveVoiceLensToggled.connect(lambda: self._toggle_lens("passive"))
        self.ribbon.pacingLensToggled.connect(lambda: self._toggle_lens("pacing"))
        self.ribbon.fillerLensToggled.connect(lambda: self._toggle_lens("filler"))
        self.ribbon.dialogueLensToggled.connect(lambda: self._toggle_lens("dialogue"))
        self.ribbon.inspectorToggled.connect(self._toggle_inspector_panel)

        self.canvas_area.addToDictionaryRequested.connect(self._on_add_to_dictionary)
        self.canvas_area.ignoreWordRequested.connect(self._on_ignore_spelling_word)
        self.revision_inspector.addToDictionaryRequested.connect(self._on_add_to_dictionary)

        self.revision_inspector.jumpRequested.connect(self.canvas_area.highlight_range)
        self.revision_inspector.replaceRequested.connect(self._on_replace_requested)
        self.revision_inspector.collapsedChanged.connect(self._on_inspector_collapsed_changed)

        self.right_codex.entityUpdated.connect(self._on_codex_entities_changed)

        # Academic Citation Generator connections
        self.citation_drawer.insertInTextRequested.connect(self.canvas_area.insert_text_at_cursor)
        self.citation_drawer.insertBibliographyRequested.connect(self._on_insert_bibliography)
        self.citation_drawer.collapsedChanged.connect(self._on_citation_collapsed_changed)
        self.citation_drawer.citationUpdated.connect(self._on_citations_changed)

        # Ribbon Header Actions (Save & Settings)
        self.ribbon.saveRequested.connect(self.save_document)
        self.ribbon.settingsRequested.connect(self._show_settings_dialog)

        # Document Modification Tracking for Title and Save Prompts
        self.editor.document().modificationChanged.connect(self._on_modification_changed)

    def _on_ribbon_tab_changed(self, index: int) -> None:
        tab_name = self.ribbon.tab_widget.tabText(index)
        if tab_name == "Review":
            self.show_revision_inspector()
        elif tab_name in ("Story", "Research", "Structure"):
            if self.document_mode == DocumentMode.ACADEMIC:
                self.show_citation_drawer()
            else:
                self.show_codex_drawer()

    def show_codex_drawer(self) -> None:
        if self.document_mode == DocumentMode.ACADEMIC:
            self.show_citation_drawer()
            return
        self.right_stack.setCurrentWidget(self.right_codex)
        self.right_codex.set_collapsed(False)
        self.right_stack.setFixedWidth(self.right_codex.width())
        self.ribbon.btn_codex.setChecked(True)

    def show_citation_drawer(self) -> None:
        self.right_stack.setCurrentWidget(self.citation_drawer)
        self.citation_drawer.set_collapsed(False)
        self.right_stack.setFixedWidth(self.citation_drawer.width())
        self.ribbon.btn_codex.setChecked(True)

    def show_revision_inspector(self) -> None:
        self.right_stack.setCurrentWidget(self.revision_inspector)
        self.revision_inspector.set_collapsed(False)
        self.right_stack.setFixedWidth(self.revision_inspector.width())
        self.ribbon.btn_inspector.setChecked(True)

    def _toggle_codex_panel(self) -> None:
        if self.document_mode == DocumentMode.ACADEMIC:
            if self.right_stack.currentWidget() != self.citation_drawer:
                self.show_citation_drawer()
            else:
                self.citation_drawer.toggle_collapsed()
                self.right_stack.setFixedWidth(self.citation_drawer.width())
                self.ribbon.btn_codex.setChecked(not self.citation_drawer.is_collapsed)
        else:
            if self.right_stack.currentWidget() != self.right_codex:
                self.show_codex_drawer()
            else:
                self.right_codex.toggle_collapsed()
                self.right_stack.setFixedWidth(self.right_codex.width())
                self.ribbon.btn_codex.setChecked(not self.right_codex.is_collapsed)

    def _toggle_inspector_panel(self) -> None:
        if self.right_stack.currentWidget() != self.revision_inspector:
            self.show_revision_inspector()
        else:
            self.revision_inspector.toggle_collapsed()
            self.right_stack.setFixedWidth(self.revision_inspector.width())
            self.ribbon.btn_inspector.setChecked(not self.revision_inspector.is_collapsed)

    def _on_codex_collapsed_changed(self, is_collapsed: bool) -> None:
        if self.document_mode != DocumentMode.ACADEMIC:
            self.right_stack.setFixedWidth(self.right_codex.width())
            self.ribbon.btn_codex.setChecked(not is_collapsed)

    def _on_citation_collapsed_changed(self, is_collapsed: bool) -> None:
        if self.document_mode == DocumentMode.ACADEMIC:
            self.right_stack.setFixedWidth(self.citation_drawer.width())
            self.ribbon.btn_codex.setChecked(not is_collapsed)

    def _on_inspector_collapsed_changed(self, is_collapsed: bool) -> None:
        self.right_stack.setFixedWidth(self.revision_inspector.width())
        self.ribbon.btn_inspector.setChecked(not is_collapsed)

    def _on_citations_changed(self) -> None:
        if self.active_lenses.get("spelling", False):
            self._run_revision_analysis()

    def _on_insert_bibliography(self, html_bib: str) -> None:
        cursor = self.editor.textCursor()
        cursor.insertHtml(html_bib)
        self.canvas_area.sync_document_geometry()
        self.statusBar().showMessage("Formatted bibliography inserted into manuscript.", 3000)
        self._update_metrics()

    def set_document_mode(self, mode: DocumentMode) -> None:
        """Adapts UI components, right-drawer widgets, and companion tone to active mode."""
        self.document_mode = mode
        self.ribbon.set_document_mode(mode)
        self.pet_engine.set_document_mode(mode)

        if mode == DocumentMode.ACADEMIC:
            # Academic Mode: No Story Codex, replace with Citation Drawer
            self.right_stack.setCurrentWidget(self.citation_drawer)
            self.right_stack.setFixedWidth(self.citation_drawer.width())
            self.ribbon.btn_codex.setChecked(not self.citation_drawer.is_collapsed)
        else:
            # Fiction / Non-Fiction: Story Codex
            self.right_stack.setCurrentWidget(self.right_codex)
            self.right_stack.setFixedWidth(self.right_codex.width())
            self.ribbon.btn_codex.setChecked(not self.right_codex.is_collapsed)

    def _toggle_revision_mode(self) -> None:
        self.revision_mode_active = not self.revision_mode_active
        self.ribbon.btn_rev_mode.setChecked(self.revision_mode_active)
        for k in ["spelling", "adverb", "passive", "pacing", "filler"]:
            self.active_lenses[k] = self.revision_mode_active

        self.ribbon.btn_spell.setChecked(self.revision_mode_active)
        self.ribbon.btn_adverbs.setChecked(self.revision_mode_active)
        self.ribbon.btn_passive.setChecked(self.revision_mode_active)
        self.ribbon.btn_filler.setChecked(self.revision_mode_active)
        self.ribbon.btn_pacing.setChecked(self.revision_mode_active)

        if self.revision_mode_active:
            self.show_revision_inspector()
        self._run_revision_analysis()

    def _toggle_lens(self, lens_key: str) -> None:
        self.active_lenses[lens_key] = not self.active_lenses.get(lens_key, False)
        btn_map = {
            "spelling": self.ribbon.btn_spell,
            "adverb": self.ribbon.btn_adverbs,
            "passive": self.ribbon.btn_passive,
            "pacing": self.ribbon.btn_pacing,
            "filler": self.ribbon.btn_filler,
            "dialogue": self.ribbon.btn_dialogue,
        }
        if lens_key in btn_map:
            btn_map[lens_key].setChecked(self.active_lenses[lens_key])

        if self.active_lenses[lens_key]:
            self.show_revision_inspector()
            filt = lens_key if lens_key in ("spelling", "adverb", "passive", "filler", "pacing") else "all"
            self.revision_inspector.set_filter(filt)

        self._run_revision_analysis()

    def _schedule_revision_analysis(self) -> None:
        if any(self.active_lenses.values()):
            self._lens_debounce_timer.start(300)

    def _run_revision_analysis(self) -> None:
        text = self.editor.toPlainText()
        if not any(self.active_lenses.values()):
            self.canvas_area.clear_lens_findings()
            self.revision_inspector.update_findings([])
            return

        self._revision_request_id += 1
        req_id = self._revision_request_id
        worker = ReviewWorker(
            text=text,
            active_lenses=self.active_lenses,
            spell_engine=self.spell_engine,
            request_id=req_id,
        )
        worker.signals.finished.connect(self._on_revision_worker_finished)
        QThreadPool.globalInstance().start(worker)

    def _on_revision_worker_finished(self, findings: list, request_id: int) -> None:
        if request_id == self._revision_request_id:
            self.canvas_area.set_lens_findings(findings)
            self.revision_inspector.update_findings(findings)

    def _on_add_to_dictionary(self, word: str) -> None:
        self.spell_engine.add_to_user_dictionary(word)
        self.statusBar().showMessage(f"Added '{word}' to author dictionary.", 3000)
        self._run_revision_analysis()

    def _on_ignore_spelling_word(self, word: str) -> None:
        self.spell_engine.ignore_word_for_session(word)
        self.statusBar().showMessage(f"Ignored '{word}' for this session.", 3000)
        self._run_revision_analysis()

    def _on_codex_entities_changed(self) -> None:
        self.spell_engine.sync_story_codex_whitelist(self.codex_manager)
        if self.active_lenses.get("spelling", False):
            self._run_revision_analysis()

    def _on_replace_requested(self, start_pos: int, end_pos: int, new_text: str) -> None:
        self.canvas_area.replace_range(start_pos, end_pos, new_text)
        self._run_revision_analysis()
        self._update_metrics()

    def _on_add_chapter_requested(self) -> None:
        title, ok = QInputDialog.getText(
            self, "New Chapter", "Chapter Title:", text="New Chapter"
        )
        if ok and title.strip():
            self.canvas_area.insert_chapter(title.strip())
            self.left_navigator.scan_manuscript(self.canvas_area.document())
            self._update_metrics()

    def _on_reorder_chapters_requested(self, from_idx: int, to_idx: int) -> None:
        items = self.left_navigator.get_items()
        if 0 <= from_idx < len(items) and 0 <= to_idx < len(items):
            items[from_idx], items[to_idx] = items[to_idx], items[from_idx]
            self.left_navigator._rebuild_cards()

    def _on_canvas_text_changed(self) -> None:
        """Central debounced handler for manuscript typing to guarantee zero latency."""
        self._metrics_debounce_timer.start(250)
        self._schedule_revision_analysis()
        self.left_navigator.request_scan(self.canvas_area.document())
        if self.document_mode != DocumentMode.ACADEMIC:
            self._codex_extract_timer.start(1500)

    def _on_canvas_cursor_changed(self) -> None:
        """Central handler for cursor movements and selection changes."""
        self._update_ribbon_states()
        self._mention_debounce_timer.start(150)

    def _run_debounced_metrics(self) -> None:
        """Runs full document metric analysis and pet insight engine during typing pauses."""
        self._update_metrics()
        self._on_text_changed_for_pet()

    def _run_codex_auto_extract(self, manual: bool = False) -> None:
        """Scans the manuscript for new characters, lore, and mentions to auto-build Story Codex."""
        if self.document_mode == DocumentMode.ACADEMIC:
            return

        text = self.editor.toPlainText()
        res = CodexExtractionEngine.extract_into_manager(text, self.codex_manager)
        if res.new_characters > 0 or res.new_lore > 0:
            self.right_codex.refresh()
            self.spell_engine.sync_story_codex_whitelist(self.codex_manager)
            parts = []
            if res.new_characters > 0:
                parts.append(f"{res.new_characters} character{'s' if res.new_characters > 1 else ''}")
            if res.new_lore > 0:
                parts.append(f"{res.new_lore} lore entrit{'ies' if res.new_lore > 1 else 'y'}")
            summary = " and ".join(parts)
            self.statusBar().showMessage(f"✨ Story Codex updated: {summary} auto-discovered.", 4000)
        elif manual:
            self.statusBar().showMessage(
                f"Story Codex is up to date ({res.total_characters} characters, {res.total_lore} lore entries).", 3000
            )

    def _run_codex_auto_extract_manual(self) -> None:
        self._run_codex_auto_extract(manual=True)

    def _check_live_mentions(self) -> None:
        active_text = self.canvas_area.get_active_sentence_or_paragraph()
        self.right_codex.highlight_mention(active_text)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._reposition_pet_dock()

    def _reposition_pet_dock(self) -> None:
        if hasattr(self, "pet_dock") and self.pet_dock:
            self.pet_dock.reposition()

    def _on_pet_dock_dismissed(self) -> None:
        self.ribbon.btn_pet.setChecked(False)
        pet = self.pet_engine.active_pet
        self.status_bar.update_pet_status(pet.name, "Hidden", pet.id)

    def _toggle_pet_dock(self) -> None:
        vis = not self.pet_dock.isVisible()
        self.pet_dock.setVisible(vis)
        self.ribbon.btn_pet.setChecked(vis)
        pet = self.pet_engine.active_pet
        if vis:
            self._reposition_pet_dock()
            self.status_bar.update_pet_status(pet.name, "Active", pet.id)
        else:
            self.status_bar.update_pet_status(pet.name, "Hidden", pet.id)

    def _on_text_changed_for_pet(self) -> None:
        text = self.editor.toPlainText()
        cursor_pos = self.editor.textCursor().position()
        self.pet_engine.on_text_changed(text, cursor_pos)

    def _on_pet_mood_changed(self, mood: PetMood) -> None:
        pet = self.pet_engine.active_pet
        state_label = mood.value.capitalize()
        if not self.pet_dock.isVisible():
            state_label = "Hidden"
        elif self.pet_dock.is_snoozed:
            state_label = "Snoozed"
        self.status_bar.update_pet_status(pet.name, state_label, pet.id)

    def _open_pet_selection_dialog(self) -> None:
        dlg = PetSelectionDialog(self.pet_engine.active_pet, self.custom_pets, self)
        dlg.petSelected.connect(self._set_active_pet)
        dlg.hideCompanionRequested.connect(self.pet_dock.hide_companion)
        dlg.exec()

    def _set_active_pet(self, pet: PetProfile) -> None:
        if pet.id.startswith("custom_"):
            self.custom_pets[pet.id] = pet
        self.pet_engine.set_pet(pet)
        self.pet_dock.update_pet_profile(pet)
        self.pet_dock.show()
        self.ribbon.btn_pet.setChecked(True)
        self.ribbon.btn_pet.setText(f"{pet.name} the {pet.species_title.replace('The ', '')}")
        self.ribbon.btn_pet.setIcon(CompanionFigureRenderer.render_icon(pet.id, size=20, custom_image_path=pet.custom_image_path))
        self.status_bar.update_pet_status(pet.name, "Active", pet.id)
        self._reposition_pet_dock()

    def _open_break_timer_dialog(self) -> None:
        pet = self.pet_engine.active_pet
        dlg = BreakTimerDialog(pet.break_interval_minutes, pet.break_timer_enabled, self)
        if dlg.exec():
            self.pet_engine.set_break_interval(dlg.interval_minutes)
            self.pet_engine.set_break_timer_enabled(dlg.timer_enabled)

    # --- Corkboard & Storyboard Handlers ---
    def toggle_corkboard_mode(self) -> None:
        if self.main_stack.currentIndex() == 1:
            self.show_manuscript_mode()
        else:
            self.show_corkboard_mode()

    def show_corkboard_mode(self) -> None:
        self.sync_document_to_corkboard()
        self.corkboard_view.refresh_cards()
        self.main_stack.setCurrentIndex(1)
        self.ribbon.btn_corkboard.setChecked(True)
        self.pet_dock.hide()

    def show_manuscript_mode(self) -> None:
        self.main_stack.setCurrentIndex(0)
        self.ribbon.btn_corkboard.setChecked(False)
        self.pet_dock.show()
        self._reposition_pet_dock()

    def _on_jump_to_scene_from_card(self, card: IndexCard) -> None:
        self.show_manuscript_mode()
        found = self.editor.find(card.title)
        if not found:
            words = card.section_text.split()[:5]
            if words:
                self.editor.find(" ".join(words))

    def sync_document_to_corkboard(self) -> None:
        """Parses document headings to build or update linked scene index cards."""
        qdoc = self.editor.document()
        block = qdoc.firstBlock()

        sections = []
        current_title = "Prologue / Scene 1"
        current_lines = []

        while block.isValid():
            text = block.text().strip()
            fmt = block.blockFormat()
            user_prop = str(fmt.property(QTextBlockFormat.Property.UserProperty) or "")

            is_heading = (
                user_prop.startswith("h") or
                user_prop == "title" or
                text.lower().startswith("chapter") or
                text.lower().startswith("scene") or
                block.charFormat().font().pointSize() >= 15
            )

            if is_heading and text:
                if current_lines:
                    sections.append((current_title, "\n".join(current_lines)))
                    current_lines = []
                current_title = text
            else:
                if text:
                    current_lines.append(text)

            block = block.next()

        if current_lines or current_title:
            sections.append((current_title, "\n".join(current_lines)))

        # Update or create linked cards
        new_cards = []
        for idx, (title, body) in enumerate(sections):
            existing = None
            if idx < len(self.corkboard_manager.linked_cards):
                existing = self.corkboard_manager.linked_cards[idx]

            if existing:
                existing.title = title
                existing.section_text = body
                existing.word_count = len(body.split())
                new_cards.append(existing)
            else:
                synopsis = body[:120] + "..." if len(body) > 120 else body
                card = IndexCard(
                    title=title,
                    synopsis=synopsis or "Scene outline and notes...",
                    section_text=body,
                    word_count=len(body.split()) if body else 0,
                    is_linked=True
                )
                new_cards.append(card)

        self.corkboard_manager.linked_cards = new_cards

    def _reorder_manuscript_from_cards(self, cards: list) -> None:
        """Reconstructs the manuscript document matching the card sequence."""
        html_parts = []
        for card in cards:
            html_parts.append(f"<h2>{card.title}</h2>")
            paragraphs = card.section_text.split("\n")
            for p in paragraphs:
                if p.strip():
                    html_parts.append(f"<p>{p.strip()}</p>")
        self.editor.setHtml("".join(html_parts))
        self._update_metrics()

    @property
    def editor(self):
        return self.canvas_area

    # --- Formatting Helpers ---
    def _toggle_bold(self) -> None:
        self.canvas_area.toggle_bold()

    def _toggle_italic(self) -> None:
        self.canvas_area.toggle_italic()

    def _toggle_underline(self) -> None:
        self.canvas_area.toggle_underline()

    def _toggle_strike(self) -> None:
        self.canvas_area.toggle_strike()

    def _choose_text_color(self) -> None:
        col = QColorDialog.getColor(Qt.GlobalColor.black, self, "Select Text Color")
        if col.isValid():
            self.canvas_area.set_text_color(col)

    def _choose_highlight_color(self) -> None:
        col = QColorDialog.getColor(QColor(255, 245, 150), self, "Select Highlight Color")
        if col.isValid():
            self.canvas_area.set_highlight_color(col)

    def _set_line_spacing(self, spacing_mult: float) -> None:
        self.canvas_area.set_line_spacing(spacing_mult)

    def _toggle_bullet_list(self) -> None:
        self.canvas_area.create_bullet_list()

    def _toggle_numbered_list(self) -> None:
        self.canvas_area.create_numbered_list()

    def _paste_plain_text(self) -> None:
        """Pastes plain text without formatting matching surrounding format."""
        self.canvas_area.paste_plain()

    def _on_find_next_shortcut(self) -> None:
        """Navigates to the next search match or summons find bar if closed."""
        if hasattr(self.canvas_area, "find_replace_bar") and self.canvas_area.find_replace_bar.isVisible():
            self.canvas_area.find_replace_bar.find_next()
        else:
            self.canvas_area.show_find(replace_mode=False)

    def _on_find_prev_shortcut(self) -> None:
        """Navigates to the previous search match or summons find bar if closed."""
        if hasattr(self.canvas_area, "find_replace_bar") and self.canvas_area.find_replace_bar.isVisible():
            self.canvas_area.find_replace_bar.find_prev()
        else:
            self.canvas_area.show_find(replace_mode=False)

    def _apply_style(self, style_name: str) -> None:
        self.canvas_area.apply_style(style_name)

    def _on_save_current_style(self) -> None:
        """Prompts user to name the current formatting snapshot and saves it as a custom style."""
        style_name, ok = QInputDialog.getText(
            self, "Save Custom Style", "Enter a name for your custom style:"
        )
        if ok and style_name.strip():
            name = style_name.strip()
            snapshot = self.canvas_area.current_style_snapshot()
            self.custom_styles[name] = snapshot
            self.ribbon.add_custom_style_button(name)
            self.status_bar.set_message(f"Style '{name}' saved to styles palette.")

    def _on_custom_style_selected(self, style_name: str) -> None:
        """Applies a user-created style to the selection or current block."""
        if style_name in self.custom_styles:
            self.canvas_area.apply_custom_style(self.custom_styles[style_name])
            self.status_bar.set_message(f"Applied custom style '{style_name}'.")

    def _on_insert_image(self) -> None:
        """Opens a file dialog to insert any computer image into the manuscript."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Insert Picture",
            "",
            "Image Files (*.png *.jpg *.jpeg *.bmp *.gif *.webp *.svg);;All Files (*)"
        )
        if file_path:
            success = self.canvas_area.insert_image(file_path)
            if success:
                self.status_bar.set_message(f"Inserted image: {os.path.basename(file_path)}")
            else:
                QMessageBox.warning(self, "Image Error", "Unable to load the selected image file.")

    def _on_insert_clip_art(self) -> None:
        """Opens the Clip Art Library dialog to select or browse clip art."""
        clipart_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "assets", "clipart"))
        dlg = ClipArtDialog(clipart_dir, parent=self)
        if dlg.exec():
            if dlg.selected_file:
                success = self.canvas_area.insert_image(dlg.selected_file)
                if success:
                    self.status_bar.set_message(f"Inserted clip art: {os.path.basename(dlg.selected_file)}")
                else:
                    QMessageBox.warning(self, "Clip Art Error", "Unable to load the selected clip art.")

    def _insert_page_break(self) -> None:
        self.canvas_area.insert_page_break()

    def _insert_horizontal_rule(self) -> None:
        cursor = self.editor.textCursor()
        cursor.insertHtml("<hr style='border: 1px solid #3b3e56; margin: 16px 0;'>")
        cursor.insertBlock()
        self.canvas_area.viewport().update()

    def _insert_date_time(self) -> None:
        cursor = self.editor.textCursor()
        dt_str = datetime.now().strftime("%B %d, %Y - %I:%M %p")
        cursor.insertText(dt_str)
        self.canvas_area.viewport().update()

    def _insert_symbol(self) -> None:
        cursor = self.editor.textCursor()
        cursor.insertText("§ ")
        self.canvas_area.viewport().update()

    # --- Layout & Paper Handlers ---
    def _on_paper_size_changed(self, preset: PaperSizePreset) -> None:
        self.layout_model.paper_size = preset
        self.canvas_area.sync_document_geometry()
        self.ruler.update()

    def _on_orientation_changed(self, orient: Orientation) -> None:
        self.layout_model.orientation = orient
        self.canvas_area.sync_document_geometry()
        self.ruler.update()

    def _on_margins_preset_changed(self, margins: PageMargins) -> None:
        self.layout_model.margins = margins
        self.canvas_area.sync_document_geometry()
        self.ruler.update()

    def _on_ruler_margins_dragged(self, left_in: float, right_in: float) -> None:
        self.canvas_area.sync_document_geometry()

    def _on_texture_type_changed(self, texture_type: TextureType) -> None:
        self.texture_engine.current_type = texture_type
        self.canvas_area.viewport().update()

    def _on_texture_opacity_changed(self, opacity: float) -> None:
        self.texture_engine.opacity = opacity
        self.canvas_area.viewport().update()

    def _on_dark_paper_toggled(self, is_dark: bool) -> None:
        self.canvas_area.dark_paper = is_dark
        self.canvas_area.viewport().update()

    def _on_crop_marks_toggled(self, show: bool) -> None:
        self.canvas_area.show_crop_marks = show
        self.canvas_area.viewport().update()

    def _on_zoom_changed(self, zoom: float) -> None:
        self.layout_model.zoom = zoom
        self.status_bar.set_zoom_value(zoom)
        self.canvas_area.sync_document_geometry()
        self.ruler.update()

    def _on_theme_changed(self, theme_name: str) -> None:
        self.theme_manager.set_theme(theme_name)
        self.setStyleSheet(self.theme_manager.generate_qss())
        self.canvas_area.viewport().update()
        self.ruler.update()

    def toggle_zen_mode(self) -> None:
        if self.isFullScreen():
            self.showNormal()
            self.ribbon.show()
            self.ruler.show()
            self.menuBar().show()
            self.status_bar.show()
        else:
            self.showFullScreen()
            self.ribbon.hide()
            self.ruler.hide()
            self.menuBar().hide()

    def _update_metrics(self) -> None:
        text = self.editor.toPlainText()
        page_count = self.canvas_area.page_count
        stats = DocumentStatistics.compute(text, page_count)
        self.status_bar.update_statistics(stats)

    def _update_ribbon_states(self) -> None:
        ed = self.editor
        self.ribbon.btn_bold.setChecked(ed.fontWeight() >= 700)
        self.ribbon.btn_italic.setChecked(ed.fontItalic())
        self.ribbon.btn_underline.setChecked(ed.fontUnderline())

    # --- File IO Handlers ---
    def new_document(self) -> None:
        if not self._maybe_save_prompt():
            return

        confirmed, title, mode, use_template = NewDocumentDialog.prompt_new_document(self)
        if not confirmed:
            return

        self.editor.clear()
        self.current_file_path = None
        self.story_metadata = {"document_mode": mode.value, "title": title}
        self.codex_manager = CodexManager()
        self.right_codex.codex_manager = self.codex_manager
        self.right_codex.refresh()

        self.citation_manager = CitationManager()
        self.citation_drawer.citation_manager = self.citation_manager
        self.citation_drawer.refresh()

        self.set_document_mode(mode)

        if use_template:
            template_html = self._generate_mode_template(title, mode)
            self.editor.setHtml(template_html)
        else:
            self.editor.clear()

        self.editor.document().setModified(False)
        self.spell_engine.sync_story_codex_whitelist(self.codex_manager)
        self.left_navigator.scan_manuscript(self.canvas_area.document())
        self._update_window_title()
        self._update_metrics()
        self._schedule_revision_analysis()

    def _generate_mode_template(self, title: str, mode: DocumentMode) -> str:
        if mode == DocumentMode.ACADEMIC:
            return (
                "<p><b>Author Name</b><br>"
                "<i>Department / Academic Institution Affiliation</i><br>"
                "<i>scholar@institution.edu</i></p>"
                "<p><b>Abstract</b><br>"
                "<i>[This study investigates the fundamental principles of... We present a systematic framework evaluating empirical parameters. The results demonstrate significant improvements across key benchmarks.]</i></p>"
                "<p><b>1. Introduction & Problem Statement</b><br>"
                "The advancement of rigorous analytical methodologies has long formed the cornerstone of scholarly inquiry. "
                "Recent literature demonstrates the necessity of empirical validation and methodological clarity. "
                "In this paper, we address key open questions by systematically examining the underlying factors...</p>"
                "<p><b>2. Literature Review & Theoretical Framework</b><br>"
                "Prior investigations present contrasting paradigms regarding these dynamics. "
                "While foundational studies established initial correlations, subsequent scholarship identified critical boundary conditions that warrant closer scrutiny...</p>"
                "<p><b>3. Methodology & Research Design</b><br>"
                "Our experimental framework employs systematic observation under controlled parameters. "
                "Data collection protocols were calibrated to minimize confounding variables across distinct test conditions...</p>"
                "<p><b>4. Results & Discussion</b><br>"
                "The empirical data indicates significant consistency across trials. "
                "Comparative analysis reveals that theoretical predictions align with observed outcomes within standard confidence intervals...</p>"
                "<p><b>5. Conclusion & Future Directions</b><br>"
                "This study provides empirical grounding for understanding the operational parameters. "
                "Future research should explore longitudinal variations across broader cohorts.</p>"
                "<h2>References</h2>"
                "<p><i>[Use the Citations drawer on the right to manage references and click '📚 Bibliography' to insert them here.]</i></p>"
            )
        elif mode == DocumentMode.NON_FICTION:
            return (
                "<p><i>An In-Depth Investigation and Analysis</i></p>"
                "<p><b>Introduction: The Central Thesis</b><br>"
                "Every significant shift begins with an observation that is easily overlooked. "
                "When we trace the trajectory of recent developments, a clear and consequential pattern begins to emerge...</p>"
                "<p><b>I. The Background and Origins</b><br>"
                "To understand where the current landscape originated, one must return to the initial circumstances that set it in motion...</p>"
                "<p><b>II. Evidence, Case Studies, and Data</b><br>"
                "Consider a concrete example that illustrates this dynamic in practice. "
                "In examining the records, three factors immediately stand out as decisive drivers of change...</p>"
                "<p><b>III. Counterarguments and Dilemmas</b><br>"
                "Skeptics may reasonably contend that alternative explanations carry equal weight. "
                "Yet when scrutinized against the primary evidence, a very different conclusion emerges...</p>"
                "<p><b>IV. Synthesis and Outlook</b><br>"
                "What remains is to translate these insights into actionable understanding for the road ahead...</p>"
            )
        else:
            return (
                "<p><b>Chapter One: The Salt and the Stars</b></p>"
                "<p>The harbor bell chimed three times through the morning sea fog. "
                "Across the polished oak desk, the ancient parchment maps lay unfurled, their ink smelling of crushed oak gall and dried cedar. "
                "Master Sean adjusted his brass spectacles, observing the fine woven grain of the paper catching the dawn light.</p>"
                "<p>For forty seasons he had transcribed the royal charts, recording each shoal and sound with absolute fidelity. "
                "The kingdom demanded precision—margins measured to the millimeter, seals embossed in crimson wax, and ledgers bound in linen. "
                "Yet between the official decrees, in the quiet margins of his ledger, he traced the contours of an uncharted continent.</p>"
                "<blockquote>\"To write is to build a cathedral out of silence, stone by stone, word by word.\"</blockquote>"
                "<p>He dipped his quill into the dark inkwell. The paper drank the pigment cleanly, leaving crisp, elegant lines that would outlast empires.</p>"
            )

    def open_document(self) -> None:
        if not self._maybe_save_prompt():
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Document", "", "Word Document (*.docx);;All Files (*.*)"
        )
        if path:
            meta = IOManager.load_docx(path, self.editor.document())
            self.current_file_path = path
            self.story_metadata = meta or {}
            if meta:
                self.codex_manager.from_dict(meta)
                self.right_codex.refresh()
                if "citations" in meta and isinstance(meta["citations"], list):
                    self.citation_manager.from_dict(meta["citations"])
                    if "citation_style" in meta:
                        self.citation_manager.active_style = meta["citation_style"]
                    self.citation_drawer.refresh()
                if "document_mode" in meta:
                    try:
                        mode = DocumentMode(meta["document_mode"])
                        self.set_document_mode(mode)
                    except ValueError:
                        self.set_document_mode(DocumentMode.CREATIVE_FICTION)
                else:
                    self.set_document_mode(DocumentMode.CREATIVE_FICTION)
            self.spell_engine.sync_story_codex_whitelist(self.codex_manager)
            self.left_navigator.scan_manuscript(self.canvas_area.document())
            self._check_live_mentions()
            self.editor.document().setModified(False)
            self._update_window_title()
            self._update_metrics()
            self._schedule_revision_analysis()

    def save_document(self) -> bool:
        if not self.current_file_path:
            return self.save_document_as()
        else:
            meta = self.codex_manager.to_dict()
            meta["document_mode"] = self.document_mode.value
            meta["citations"] = self.citation_manager.to_dict()
            meta["citation_style"] = self.citation_manager.active_style
            if self.story_metadata:
                meta.update(self.story_metadata)
                meta["document_mode"] = self.document_mode.value
                meta["citations"] = self.citation_manager.to_dict()
                meta["citation_style"] = self.citation_manager.active_style
            success = IOManager.save_docx(
                self.current_file_path,
                self.editor.document(),
                self.layout_model,
                meta
            )
            if success:
                self.editor.document().setModified(False)
                self._update_window_title()
                self.statusBar().showMessage("Document, Story Codex, and Citations saved successfully.", 3000)
                self._cleanup_draft_recovery()
            return bool(success)

    def save_document_as(self) -> bool:
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Document As", "Untitled.docx", "Word Document (*.docx)"
        )
        if path:
            if not path.endswith(".docx"):
                path += ".docx"
            self.current_file_path = path
            success = self.save_document()
            self._update_window_title()
            return success
        return False

    def export_pdf(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Export to PDF", "Manuscript.pdf", "PDF Document (*.pdf)"
        )
        if path:
            if not path.endswith(".pdf"):
                path += ".pdf"
            success = IOManager.export_pdf(path, self.editor.document(), self.layout_model)
            if success:
                QMessageBox.information(self, "Export Complete", f"PDF exported successfully to:\n{path}")

    def _show_statistics_dialog(self) -> None:
        text = self.editor.toPlainText()
        page_count = self.canvas_area.page_count
        stats = DocumentStatistics.compute(text, page_count)

        msg = (
            f"<b>Document Statistics</b><br><br>"
            f"• <b>Words:</b> {stats.word_count:,}<br>"
            f"• <b>Characters (with spaces):</b> {stats.char_count:,}<br>"
            f"• <b>Characters (no spaces):</b> {stats.char_no_spaces:,}<br>"
            f"• <b>Paragraphs:</b> {stats.paragraph_count:,}<br>"
            f"• <b>Pages:</b> {stats.page_count}<br>"
            f"• <b>Estimated Reading Time:</b> {stats.reading_time_minutes} minutes"
        )
        QMessageBox.information(self, "Volumenodex Analytics", msg)

    def _show_about_dialog(self) -> None:
        QMessageBox.about(
            self,
            "About Volumenodex",
            "<h3>Volumenodex Studio</h3>"
            "<p>A standalone, high-fidelity Windows word processing program crafted for creative storytellers and document authors.</p>"
            "<p><b>Version:</b> 0.1.0 (Phase 1: Core Engine & Paginated Canvas)<br>"
            "<b>Features:</b> Procedural Paper Grain Textures, Print Fidelity, Classic Ribbon, Interactive Top Ruler, Native .docx IO & PDF Vector Export.</p>"
        )

    def _populate_initial_manuscript(self) -> None:
        self.editor.clear()
        self.editor.document().setModified(False)
        self.left_navigator.scan_manuscript(self.canvas_area.document())
        self.right_codex.refresh()
        self.spell_engine.sync_story_codex_whitelist(self.codex_manager)
        self._update_window_title()

    # --- Save on Close & Document State Tracking ---
    def _on_modification_changed(self, modified: bool) -> None:
        self._update_window_title()

    def _update_window_title(self) -> None:
        if self.current_file_path:
            name = os.path.basename(self.current_file_path)
        else:
            name = self.story_metadata.get("title") or "Untitled Document"
        star = " *" if self.editor.document().isModified() else ""
        self.setWindowTitle(f"Volumenodex — {name}{star}")

    def _maybe_save_prompt(self) -> bool:
        """Prompts the author to save unsaved modifications.
        Returns True if safe to proceed (saved or discarded), False if canceled."""
        if not self.editor.document().isModified():
            return True

        # Check for automated test override or bypass
        test_response = getattr(self, "_test_save_prompt_response", None)
        if test_response is not None:
            ret = test_response
        elif os.environ.get("PYTEST_CURRENT_TEST") or getattr(self, "_suppress_save_prompt", False):
            # Bypass modal dialog during automated unit test runs unless explicitly testing prompt
            return True
        else:
            doc_name = (
                os.path.basename(self.current_file_path)
                if self.current_file_path
                else (self.story_metadata.get("title") or "Untitled Document")
            )

            box = QMessageBox(self)
            box.setWindowTitle("Volumenodex")
            box.setText(f"Do you want to save changes to \"{doc_name}\"?")
            box.setInformativeText("Your changes will be lost if you close or switch documents without saving.")
            box.setStandardButtons(
                QMessageBox.StandardButton.Save
                | QMessageBox.StandardButton.Discard
                | QMessageBox.StandardButton.Cancel
            )
            box.setDefaultButton(QMessageBox.StandardButton.Save)
            ret = box.exec()

        if ret == QMessageBox.StandardButton.Save:
            return self.save_document()
        elif ret == QMessageBox.StandardButton.Discard:
            return True
        else:  # Cancel
            return False

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._maybe_save_prompt():
            event.accept()
        else:
            event.ignore()

    # --- Variable Auto-Save & Settings Handlers ---
    def _apply_autosave_settings(self) -> None:
        enabled = self.settings_manager.autosave_enabled
        interval_m = self.settings_manager.autosave_interval_minutes

        if hasattr(self, "act_autosave_enable"):
            self.act_autosave_enable.setChecked(enabled)
        if hasattr(self, "_autosave_interval_actions") and interval_m in self._autosave_interval_actions:
            self._autosave_interval_actions[interval_m].setChecked(True)

        badge_text = self.settings_manager.get_autosave_label()
        self.ribbon.update_autosave_badge(badge_text)

        if enabled and interval_m > 0:
            self._autosave_timer.start(interval_m * 60 * 1000)
        else:
            self._autosave_timer.stop()

    def _on_autosave_timer(self) -> None:
        if not self.editor.document().isModified():
            return

        now_str = datetime.now().strftime("%H:%M:%S")
        if self.current_file_path:
            success = self.save_document()
            if success:
                self.ribbon.update_autosave_badge(f"Auto-Saved ({now_str})")
                self.statusBar().showMessage(f"Auto-saved to {os.path.basename(self.current_file_path)} at {now_str}", 4000)
        else:
            self._save_draft_recovery(now_str)

    def _save_draft_recovery(self, now_str: str) -> None:
        try:
            draft_dir = os.path.expanduser("~/.volumenodex/autosave")
            os.makedirs(draft_dir, exist_ok=True)
            draft_path = os.path.join(draft_dir, "untitled_recovery.docx")
            meta = self.codex_manager.to_dict()
            meta["document_mode"] = self.document_mode.value
            meta["citations"] = self.citation_manager.to_dict()
            meta["citation_style"] = self.citation_manager.active_style
            if self.story_metadata:
                meta.update(self.story_metadata)
            IOManager.save_docx(draft_path, self.editor.document(), self.layout_model, meta)
            self.ribbon.update_autosave_badge(f"Draft Saved ({now_str})")
            self.statusBar().showMessage(f"Draft auto-saved to recovery vault at {now_str}", 4000)
        except Exception as e:
            print(f"Error during draft recovery save: {e}")

    def _cleanup_draft_recovery(self) -> None:
        try:
            draft_path = os.path.expanduser("~/.volumenodex/autosave/untitled_recovery.docx")
            if os.path.exists(draft_path):
                os.remove(draft_path)
            meta_path = os.path.expanduser("~/.volumenodex/autosave/untitled_recovery.story.json")
            if os.path.exists(meta_path):
                os.remove(meta_path)
        except Exception:
            pass

    def _show_settings_dialog(self) -> None:
        dlg = SettingsDialog(self.settings_manager, self)
        if dlg.exec():
            self._apply_autosave_settings()
            self.canvas_area.show_crop_marks = self.settings_manager.show_crop_marks
            self.ribbon.chk_crop_marks.setChecked(self.settings_manager.show_crop_marks)

    def _on_menu_autosave_toggled(self, checked: bool) -> None:
        self.settings_manager.autosave_enabled = checked
        self.settings_manager.save()

    def _on_menu_autosave_interval_triggered(self, minutes: int) -> None:
        self.settings_manager.autosave_enabled = True
        self.settings_manager.autosave_interval_minutes = minutes
        self.settings_manager.save()
