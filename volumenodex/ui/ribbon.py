"""Modern Fluent Ribbon Bar with crisp vector icons, sleek typography, and refined groups."""

from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QFont, QFontDatabase, QColor, QIcon, QKeySequence
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QToolButton,
    QComboBox, QSpinBox, QSlider, QLabel, QFrame, QMenu,
    QPushButton
)
from volumenodex.core.document_model import PaperSizePreset, Orientation, PageMargins, DocumentMode
from volumenodex.canvas.paper_texture import TextureType
from volumenodex.audio.audio_engine import TypewriterSoundPreset, AmbientSoundPreset
from volumenodex.ui.vector_icons import VectorIconFactory


def create_ribbon_separator() -> QFrame:
    sep = QFrame()
    sep.setFrameShape(QFrame.Shape.VLine)
    sep.setFrameShadow(QFrame.Shadow.Plain)
    sep.setStyleSheet("background-color: #2a2c3d; width: 1px; margin: 6px 8px;")
    return sep


class ModernRibbonGroup(QWidget):
    """A sleekly styled group container inside a ribbon tab."""

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(6, 4, 6, 4)
        self.layout.setSpacing(4)

        self.content_widget = QWidget()
        self.content_layout = QHBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(4)
        self.layout.addWidget(self.content_widget)

        self.title_label = QLabel(title)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setStyleSheet("color: #6d7293; font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;")
        self.layout.addWidget(self.title_label)

    def add_widget(self, widget: QWidget) -> None:
        self.content_layout.addWidget(widget)

    def add_layout(self, layout) -> None:
        self.content_layout.addLayout(layout)


class RibbonBar(QWidget):
    """Modern Fluent tabbed ribbon bar with crisp vector graphics and authoring controls."""

    # Clipboard signals
    pasteRequested = Signal()
    pastePlainRequested = Signal()
    cutRequested = Signal()
    copyRequested = Signal()

    # Formatting signals
    fontFamilyChanged = Signal(str)
    fontSizeChanged = Signal(int)
    boldToggled = Signal()
    italicToggled = Signal()
    underlineToggled = Signal()
    strikeToggled = Signal()
    textColorRequested = Signal()
    highlightColorRequested = Signal()
    alignLeftRequested = Signal()
    alignCenterRequested = Signal()
    alignRightRequested = Signal()
    alignJustifyRequested = Signal()
    lineSpacingChanged = Signal(float)
    bulletListRequested = Signal()
    numberedListRequested = Signal()
    styleSelected = Signal(str)
    saveCurrentStyleRequested = Signal()
    customStyleSelected = Signal(str)

    # Search & Replace signals
    findRequested = Signal()
    replaceRequested = Signal()

    # Insert signals
    pageBreakRequested = Signal()
    horizontalRuleRequested = Signal()
    dateTimeRequested = Signal()
    symbolRequested = Signal()
    insertImageRequested = Signal()
    insertClipArtRequested = Signal()

    # Layout signals
    paperSizeChanged = Signal(PaperSizePreset)
    orientationChanged = Signal(Orientation)
    marginsChanged = Signal(PageMargins)
    textureTypeChanged = Signal(TextureType)
    textureOpacityChanged = Signal(float)
    darkPaperToggled = Signal(bool)
    cropMarksToggled = Signal(bool)

    # Story signals
    navigatorToggled = Signal()
    codexToggled = Signal()
    corkboardToggled = Signal()
    scratchpadToggled = Signal()
    writingPetToggled = Signal()

    # Proof & Review signals
    revisionModeToggled = Signal()
    spellCheckToggled = Signal()
    adverbsLensToggled = Signal()
    passiveVoiceLensToggled = Signal()
    pacingLensToggled = Signal()
    clicheLensToggled = Signal()
    fillerLensToggled = Signal()
    dialogueLensToggled = Signal()
    inspectorToggled = Signal()
    statisticsRequested = Signal()

    # View signals
    zenModeRequested = Signal()
    splitScreenRequested = Signal()
    rulerToggled = Signal(bool)
    zoomChanged = Signal(float)
    themeChanged = Signal(str)
    typewriterSoundChanged = Signal(TypewriterSoundPreset)
    ambientSoundChanged = Signal(AmbientSoundPreset)

    # Document & Studio Header signals
    saveRequested = Signal()
    settingsRequested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(126)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.tab_widget = QTabWidget()
        self.tab_widget.setDocumentMode(True)
        main_layout.addWidget(self.tab_widget)

        self._build_header_controls()

        self._build_home_tab()
        self._build_insert_tab()
        self._build_layout_tab()
        self._build_story_tab()
        self._build_review_tab()
        self._build_view_tab()

    def _build_header_controls(self) -> None:
        """Constructs Quick Access header controls in the top tab bar."""
        # Top-Left Header: Prominent Save button
        left_widget = QWidget()
        left_layout = QHBoxLayout(left_widget)
        left_layout.setContentsMargins(4, 2, 6, 2)
        left_layout.setSpacing(4)

        self.btn_header_save = QPushButton("Save")
        self.btn_header_save.setObjectName("headerSaveBtn")
        self.btn_header_save.setIcon(VectorIconFactory.create_icon("save", color="#c0caf5", size=16))
        self.btn_header_save.setIconSize(QSize(16, 16))
        self.btn_header_save.setToolTip("Save Document (Ctrl+S)")
        self.btn_header_save.setStyleSheet("""
            QPushButton#headerSaveBtn {
                background-color: #24283b;
                color: #c0caf5;
                border: 1px solid #3b4261;
                border-radius: 4px;
                padding: 3px 10px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton#headerSaveBtn:hover {
                background-color: #2e344e;
                border-color: #7aa2f7;
                color: #ffffff;
            }
            QPushButton#headerSaveBtn:pressed {
                background-color: #7aa2f7;
                color: #1a1b26;
            }
        """)
        self.btn_header_save.clicked.connect(self.saveRequested.emit)
        left_layout.addWidget(self.btn_header_save)
        self.tab_widget.setCornerWidget(left_widget, Qt.Corner.TopLeftCorner)

        # Top-Right Header: Auto-Save status badge and Settings button
        right_widget = QWidget()
        right_layout = QHBoxLayout(right_widget)
        right_layout.setContentsMargins(6, 2, 8, 2)
        right_layout.setSpacing(6)

        self.lbl_autosave_badge = QLabel("Auto-Save: 2m")
        self.lbl_autosave_badge.setToolTip("Current background automatic save interval (adjustable in Settings)")
        self.lbl_autosave_badge.setStyleSheet("""
            QLabel {
                color: #7aa2f7;
                background-color: rgba(122, 162, 247, 0.12);
                border: 1px solid rgba(122, 162, 247, 0.25);
                border-radius: 4px;
                padding: 2px 8px;
                font-size: 10px;
                font-weight: 600;
            }
        """)
        right_layout.addWidget(self.lbl_autosave_badge)

        self.btn_header_settings = QToolButton()
        self.btn_header_settings.setIcon(VectorIconFactory.create_icon("settings", color="#c0caf5", size=16))
        self.btn_header_settings.setIconSize(QSize(16, 16))
        self.btn_header_settings.setToolTip("Studio Settings & Preferences (Ctrl+,)")
        self.btn_header_settings.setStyleSheet("""
            QToolButton {
                background-color: transparent;
                border: 1px solid transparent;
                border-radius: 4px;
                padding: 3px;
                color: #c0caf5;
            }
            QToolButton:hover {
                background-color: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.15);
            }
        """)
        self.btn_header_settings.clicked.connect(self.settingsRequested.emit)
        right_layout.addWidget(self.btn_header_settings)
        self.tab_widget.setCornerWidget(right_widget, Qt.Corner.TopRightCorner)

    def update_autosave_badge(self, text: str) -> None:
        """Updates the header autosave status badge text."""
        if hasattr(self, "lbl_autosave_badge"):
            self.lbl_autosave_badge.setText(text)

    def _create_tool_button(self, icon_name: str, tooltip: str, text: str = "", checkable: bool = False, width: int = 30) -> QToolButton:
        btn = QToolButton()
        if icon_name:
            btn.setIcon(VectorIconFactory.create_icon(icon_name))
            btn.setIconSize(QSize(18, 18))
        if text:
            btn.setText(text)
            btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon if icon_name else Qt.ToolButtonStyle.ToolButtonTextOnly)
        else:
            btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        btn.setToolTip(tooltip)
        btn.setCheckable(checkable)
        btn.setMinimumWidth(width)
        btn.setStyleSheet("""
            QToolButton {
                background: transparent;
                border: 1px solid transparent;
                border-radius: 4px;
                padding: 4px;
                color: #c0caf5;
            }
            QToolButton:hover {
                background: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.12);
            }
            QToolButton:checked, QToolButton:pressed {
                background: rgba(122, 162, 247, 0.2);
                border: 1px solid #7aa2f7;
                color: #7aa2f7;
            }
        """)
        return btn

    def _build_home_tab(self) -> None:
        tab = QWidget()
        layout = QHBoxLayout(tab)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)

        # 1. Clipboard Group (Always showing dedicated Paste Plain button)
        clip_group = ModernRibbonGroup("Clipboard")
        v_clip = QVBoxLayout()
        v_clip.setSpacing(3)

        h_paste = QHBoxLayout()
        h_paste.setSpacing(3)
        self.btn_paste = self._create_tool_button("paste", "Paste (Ctrl+V)", text="Paste", width=74)
        self.btn_paste.clicked.connect(self.pasteRequested.emit)
        h_paste.addWidget(self.btn_paste)

        self.btn_paste_plain = self._create_tool_button(
            "paste_plain", "Paste without Formatting (Ctrl+Shift+V)", text="Paste Plain", width=98
        )
        self.btn_paste_plain.clicked.connect(self.pastePlainRequested.emit)
        h_paste.addWidget(self.btn_paste_plain)
        v_clip.addLayout(h_paste)

        h_sub = QHBoxLayout()
        h_sub.setSpacing(3)
        self.btn_cut = self._create_tool_button("cut", "Cut (Ctrl+X)", text="Cut", width=74)
        self.btn_cut.clicked.connect(self.cutRequested.emit)
        h_sub.addWidget(self.btn_cut)

        self.btn_copy = self._create_tool_button("copy", "Copy (Ctrl+C)", text="Copy", width=98)
        self.btn_copy.clicked.connect(self.copyRequested.emit)
        h_sub.addWidget(self.btn_copy)
        v_clip.addLayout(h_sub)

        clip_group.add_layout(v_clip)
        layout.addWidget(clip_group)
        layout.addWidget(create_ribbon_separator())

        # 2. Typography Group
        font_group = ModernRibbonGroup("Typography")
        v_font = QVBoxLayout()
        v_font.setSpacing(3)

        # Row 1: Font Combo + Size Combo (up to 200 pt, all system fonts)
        h_f1 = QHBoxLayout()
        h_f1.setSpacing(4)
        self.font_combo = QComboBox()
        self.font_combo.setEditable(True)
        self.font_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.font_combo.setFixedWidth(160)
        self.font_combo.setToolTip("Font Family (all installed & downloaded system fonts included)")

        curated_fonts = [
            "Georgia", "Palatino Linotype", "Cambria", "Times New Roman",
            "Garamond", "Constantia", "Baskerville", "Book Antiqua", "Century Schoolbook",
            "Segoe UI", "Calibri", "Aptos", "Cascadia Code", "Consolas", "Courier New", "Verdana", "Arial"
        ]
        system_fonts = QFontDatabase.families()
        seen_fonts = set()
        for f in curated_fonts:
            if f in system_fonts and f not in seen_fonts:
                self.font_combo.addItem(f)
                seen_fonts.add(f)
        for f in sorted(system_fonts):
            if f not in seen_fonts:
                self.font_combo.addItem(f)
                seen_fonts.add(f)

        self.font_combo.setCurrentText("Georgia")
        self.font_combo.currentTextChanged.connect(self.fontFamilyChanged.emit)
        h_f1.addWidget(self.font_combo)

        self.size_combo = QComboBox()
        self.size_combo.setEditable(True)
        self.size_combo.setFixedWidth(60)
        self.size_combo.setToolTip("Font Size in pt (up to 200 pt, editable)")
        font_sizes = [
            6, 7, 8, 9, 10, 11, 12, 14, 16, 18, 20, 22, 24, 26, 28, 32, 36, 42, 48,
            56, 64, 72, 84, 96, 110, 128, 144, 160, 180, 200
        ]
        for s in font_sizes:
            self.size_combo.addItem(str(s), s)
        self.size_combo.setCurrentText("12")

        def _on_font_size_changed(text: str):
            try:
                val = int(text.strip())
                if 1 <= val <= 500:
                    self.fontSizeChanged.emit(val)
            except ValueError:
                pass

        self.size_combo.currentTextChanged.connect(_on_font_size_changed)
        h_f1.addWidget(self.size_combo)
        v_font.addLayout(h_f1)

        # Row 2: B, I, U, S, Text Color, Highlight Color, Bullets, Numbers
        # (Bullet points and numbers moved under Typography per user requirement)
        h_f2 = QHBoxLayout()
        h_f2.setSpacing(2)
        self.btn_bold = self._create_tool_button("bold", "Bold (Ctrl+B)", checkable=True, width=28)
        self.btn_bold.clicked.connect(self.boldToggled.emit)
        h_f2.addWidget(self.btn_bold)

        self.btn_italic = self._create_tool_button("italic", "Italic (Ctrl+I)", checkable=True, width=28)
        self.btn_italic.clicked.connect(self.italicToggled.emit)
        h_f2.addWidget(self.btn_italic)

        self.btn_underline = self._create_tool_button("underline", "Underline (Ctrl+U)", checkable=True, width=28)
        self.btn_underline.clicked.connect(self.underlineToggled.emit)
        h_f2.addWidget(self.btn_underline)

        self.btn_strike = self._create_tool_button("strike", "Strikethrough", checkable=True, width=28)
        self.btn_strike.clicked.connect(self.strikeToggled.emit)
        h_f2.addWidget(self.btn_strike)

        self.btn_text_color = self._create_tool_button("text_color", "Text Color", width=28)
        self.btn_text_color.clicked.connect(self.textColorRequested.emit)
        h_f2.addWidget(self.btn_text_color)

        self.btn_highlight = self._create_tool_button("highlight", "Highlight Color", width=28)
        self.btn_highlight.clicked.connect(self.highlightColorRequested.emit)
        h_f2.addWidget(self.btn_highlight)

        self.btn_bullet = self._create_tool_button("bullet_list", "Bulleted List", width=28)
        self.btn_bullet.clicked.connect(self.bulletListRequested.emit)
        h_f2.addWidget(self.btn_bullet)

        self.btn_numbered = self._create_tool_button("numbered_list", "Numbered List", width=28)
        self.btn_numbered.clicked.connect(self.numberedListRequested.emit)
        h_f2.addWidget(self.btn_numbered)

        v_font.addLayout(h_f2)
        font_group.add_layout(v_font)
        layout.addWidget(font_group)
        layout.addWidget(create_ribbon_separator())

        # 3. Paragraph Group
        para_group = ModernRibbonGroup("Paragraph")
        v_para = QVBoxLayout()
        v_para.setSpacing(3)

        # Row 1: Alignment (Left, Center, Right, Justify)
        h_p1 = QHBoxLayout()
        h_p1.setSpacing(3)
        self.btn_align_left = self._create_tool_button("align_left", "Align Left (Ctrl+L)", width=28)
        self.btn_align_left.clicked.connect(self.alignLeftRequested.emit)
        h_p1.addWidget(self.btn_align_left)

        self.btn_align_center = self._create_tool_button("align_center", "Align Center (Ctrl+E)", width=28)
        self.btn_align_center.clicked.connect(self.alignCenterRequested.emit)
        h_p1.addWidget(self.btn_align_center)

        self.btn_align_right = self._create_tool_button("align_right", "Align Right (Ctrl+R)", width=28)
        self.btn_align_right.clicked.connect(self.alignRightRequested.emit)
        h_p1.addWidget(self.btn_align_right)

        self.btn_align_justify = self._create_tool_button("align_justify", "Justify (Ctrl+J)", width=28)
        self.btn_align_justify.clicked.connect(self.alignJustifyRequested.emit)
        h_p1.addWidget(self.btn_align_justify)
        v_para.addLayout(h_p1)

        # Row 2: Line Spacing
        h_p2 = QHBoxLayout()
        self.spacing_combo = QComboBox()
        self.spacing_combo.addItem("1.0 Spacing", 1.0)
        self.spacing_combo.addItem("1.15 Spacing", 1.15)
        self.spacing_combo.addItem("1.45 Book", 1.45)
        self.spacing_combo.addItem("2.0 Double", 2.0)
        self.spacing_combo.setCurrentText("1.45 Book")
        self.spacing_combo.currentIndexChanged.connect(lambda: self.lineSpacingChanged.emit(self.spacing_combo.currentData()))
        h_p2.addWidget(self.spacing_combo)
        v_para.addLayout(h_p2)

        para_group.add_layout(v_para)
        layout.addWidget(para_group)
        layout.addWidget(create_ribbon_separator())

        # 4. Styles Palette Group (Heading 1-5, Title, Blockquote, and Custom Save Style)
        styles_group = ModernRibbonGroup("Styles")
        v_styles = QVBoxLayout()
        v_styles.setSpacing(3)

        self.h_styles_row1 = QHBoxLayout()
        self.h_styles_row1.setSpacing(3)
        for style_name in ["Normal", "Title", "Heading 1", "Heading 2"]:
            btn = self._create_style_button(style_name)
            self.h_styles_row1.addWidget(btn)
        v_styles.addLayout(self.h_styles_row1)

        self.h_styles_row2 = QHBoxLayout()
        self.h_styles_row2.setSpacing(3)
        for style_name in ["Heading 3", "Heading 4", "Heading 5", "Blockquote"]:
            btn = self._create_style_button(style_name)
            self.h_styles_row2.addWidget(btn)

        self.btn_save_style = QPushButton("+ Save Style")
        self.btn_save_style.setToolTip("Save current selection formatting as a custom reusable style")
        self.btn_save_style.setStyleSheet("""
            QPushButton {
                background-color: #24283b;
                border: 1px dashed #7aa2f7;
                border-radius: 4px;
                padding: 4px 8px;
                color: #7aa2f7;
                font-size: 10px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #3b4261;
                border: 1px solid #7aa2f7;
                color: #ffffff;
            }
        """)
        self.btn_save_style.clicked.connect(self.saveCurrentStyleRequested.emit)
        self.h_styles_row2.addWidget(self.btn_save_style)
        v_styles.addLayout(self.h_styles_row2)

        styles_group.add_layout(v_styles)
        layout.addWidget(styles_group)
        layout.addWidget(create_ribbon_separator())

        # 5. Editing Group (Find, Replace)
        editing_group = ModernRibbonGroup("Editing")
        v_editing = QVBoxLayout()
        v_editing.setSpacing(3)

        self.btn_find = self._create_tool_button("search", "Find in document (Ctrl+F)", text="Find", width=80)
        self.btn_find.clicked.connect(self.findRequested.emit)
        v_editing.addWidget(self.btn_find)

        self.btn_replace = self._create_tool_button("replace", "Replace in document (Ctrl+H)", text="Replace", width=80)
        self.btn_replace.clicked.connect(self.replaceRequested.emit)
        v_editing.addWidget(self.btn_replace)

        editing_group.add_layout(v_editing)
        layout.addWidget(editing_group)

        layout.addStretch()
        self.tab_widget.addTab(tab, "Home")

    def _create_style_button(self, style_name: str) -> QPushButton:
        btn = QPushButton(style_name)
        btn.setStyleSheet("""
            QPushButton {
                background-color: #20222f;
                border: 1px solid #323549;
                border-radius: 4px;
                padding: 4px 8px;
                color: #c0caf5;
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: #2a2d3e;
                border: 1px solid #7aa2f7;
            }
        """)
        btn.clicked.connect(lambda _, s=style_name: self.styleSelected.emit(s))
        return btn

    def add_custom_style_button(self, name: str) -> None:
        """Adds a button for a user-created style to the ribbon palette."""
        btn = QPushButton(name)
        btn.setStyleSheet("""
            QPushButton {
                background-color: #22263d;
                border: 1px solid #bb9af7;
                border-radius: 4px;
                padding: 4px 8px;
                color: #bb9af7;
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: #3b4261;
                color: #ffffff;
            }
        """)
        btn.clicked.connect(lambda _, s=name: self.customStyleSelected.emit(s))
        idx = self.h_styles_row2.indexOf(self.btn_save_style)
        if idx >= 0:
            self.h_styles_row2.insertWidget(idx, btn)
        else:
            self.h_styles_row2.addWidget(btn)

    def _build_insert_tab(self) -> None:
        tab = QWidget()
        layout = QHBoxLayout(tab)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)

        # Pages Group
        page_group = ModernRibbonGroup("Pages")
        self.btn_page_break = self._create_tool_button("page_break", "Insert Page Break (Ctrl+Enter)", text="Page Break", width=105)
        self.btn_page_break.clicked.connect(self.pageBreakRequested.emit)
        page_group.add_widget(self.btn_page_break)
        layout.addWidget(page_group)
        layout.addWidget(create_ribbon_separator())

        # Illustrations Group (Pictures & User Clip Art Library)
        illus_group = ModernRibbonGroup("Illustrations")
        h_illus = QHBoxLayout()
        h_illus.setSpacing(4)
        self.btn_image = self._create_tool_button(
            "image", "Insert picture from computer file (PNG, JPG, WebP, GIF, SVG)", text="Picture", width=85
        )
        self.btn_image.clicked.connect(self.insertImageRequested.emit)
        h_illus.addWidget(self.btn_image)

        self.btn_clipart = self._create_tool_button(
            "clipart", "Insert clip art from designated library folder", text="Clip Art", width=85
        )
        self.btn_clipart.clicked.connect(self.insertClipArtRequested.emit)
        h_illus.addWidget(self.btn_clipart)
        illus_group.add_layout(h_illus)
        layout.addWidget(illus_group)
        layout.addWidget(create_ribbon_separator())

        # Elements Group
        elem_group = ModernRibbonGroup("Elements")
        h_el = QHBoxLayout()
        self.btn_divider = QPushButton("Horizontal Rule")
        self.btn_divider.setStyleSheet("background: #20222f; border: 1px solid #323549; border-radius: 4px; padding: 6px 12px;")
        self.btn_divider.clicked.connect(self.horizontalRuleRequested.emit)
        h_el.addWidget(self.btn_divider)

        self.btn_datetime = QPushButton("Date & Time")
        self.btn_datetime.setStyleSheet("background: #20222f; border: 1px solid #323549; border-radius: 4px; padding: 6px 12px;")
        self.btn_datetime.clicked.connect(self.dateTimeRequested.emit)
        h_el.addWidget(self.btn_datetime)

        elem_group.add_layout(h_el)
        layout.addWidget(elem_group)

        layout.addStretch()
        self.tab_widget.addTab(tab, "Insert")

    def _build_layout_tab(self) -> None:
        tab = QWidget()
        layout = QHBoxLayout(tab)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)

        setup_group = ModernRibbonGroup("Page Setup")
        v_setup = QVBoxLayout()
        v_setup.setSpacing(3)

        h_m = QHBoxLayout()
        h_m.addWidget(QLabel("Margins:"))
        self.margin_combo = QComboBox()
        self.margin_combo.addItem("Normal (1.0 in)", PageMargins.normal())
        self.margin_combo.addItem("Narrow (0.5 in)", PageMargins.narrow())
        self.margin_combo.addItem("Wide (1.5 in)", PageMargins.wide())
        self.margin_combo.addItem("Manuscript (1.25 in)", PageMargins.manuscript())
        self.margin_combo.currentIndexChanged.connect(lambda: self.marginsChanged.emit(self.margin_combo.currentData()))
        h_m.addWidget(self.margin_combo)
        v_setup.addLayout(h_m)

        h_so = QHBoxLayout()
        self.size_preset_combo = QComboBox()
        for preset in PaperSizePreset:
            self.size_preset_combo.addItem(preset.value, preset)
        self.size_preset_combo.currentIndexChanged.connect(lambda: self.paperSizeChanged.emit(self.size_preset_combo.currentData()))
        h_so.addWidget(self.size_preset_combo)

        self.orient_combo = QComboBox()
        for o in Orientation:
            self.orient_combo.addItem(o.value, o)
        self.orient_combo.currentIndexChanged.connect(lambda: self.orientationChanged.emit(self.orient_combo.currentData()))
        h_so.addWidget(self.orient_combo)
        v_setup.addLayout(h_so)

        setup_group.add_layout(v_setup)
        layout.addWidget(setup_group)
        layout.addWidget(create_ribbon_separator())

        # Paper Craft & Print Fidelity
        texture_group = ModernRibbonGroup("Paper Craft & Print Fidelity")
        v_tex = QVBoxLayout()
        v_tex.setSpacing(3)

        h_t1 = QHBoxLayout()
        h_t1.addWidget(QLabel("Paper Grain:"))
        self.texture_combo = QComboBox()
        for t in TextureType:
            self.texture_combo.addItem(t.value, t)
        self.texture_combo.setCurrentText(TextureType.FINE_LINEN.value)
        self.texture_combo.currentIndexChanged.connect(lambda: self.textureTypeChanged.emit(self.texture_combo.currentData()))
        h_t1.addWidget(self.texture_combo)

        self.chk_dark_paper = QPushButton("Dark Paper")
        self.chk_dark_paper.setCheckable(True)
        self.chk_dark_paper.toggled.connect(self.darkPaperToggled.emit)
        self.chk_dark_paper.setStyleSheet("""
            QPushButton {
                background: #20222f;
                border: 1px solid #323549;
                border-radius: 4px;
                padding: 4px 8px;
            }
            QPushButton:checked {
                background: rgba(122, 162, 247, 0.2);
                border: 1px solid #7aa2f7;
                color: #7aa2f7;
            }
        """)
        h_t1.addWidget(self.chk_dark_paper)
        v_tex.addLayout(h_t1)

        h_t2 = QHBoxLayout()
        h_t2.addWidget(QLabel("Grain Opacity:"))
        self.slider_opacity = QSlider(Qt.Orientation.Horizontal)
        self.slider_opacity.setRange(0, 100)
        self.slider_opacity.setValue(30)
        self.slider_opacity.setFixedWidth(110)
        self.lbl_opacity = QLabel("30%")
        self.slider_opacity.valueChanged.connect(self._on_opacity_slider_changed)
        h_t2.addWidget(self.slider_opacity)
        h_t2.addWidget(self.lbl_opacity)

        self.chk_crop_marks = QPushButton("Crop Marks")
        self.chk_crop_marks.setCheckable(True)
        self.chk_crop_marks.setChecked(True)
        self.chk_crop_marks.toggled.connect(self.cropMarksToggled.emit)
        self.chk_crop_marks.setStyleSheet("""
            QPushButton {
                background: #20222f;
                border: 1px solid #323549;
                border-radius: 4px;
                padding: 4px 8px;
            }
            QPushButton:checked {
                background: rgba(122, 162, 247, 0.2);
                border: 1px solid #7aa2f7;
                color: #7aa2f7;
            }
        """)
        h_t2.addWidget(self.chk_crop_marks)
        v_tex.addLayout(h_t2)

        texture_group.add_layout(v_tex)
        layout.addWidget(texture_group)

        layout.addStretch()
        self.tab_widget.addTab(tab, "Layout")

    def _on_opacity_slider_changed(self, val: int) -> None:
        self.lbl_opacity.setText(f"{val}%")
        self.textureOpacityChanged.emit(val / 100.0)

    def _build_story_tab(self) -> None:
        tab = QWidget()
        layout = QHBoxLayout(tab)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)

        self.drawers_group = ModernRibbonGroup("Story Drawers")
        self.btn_navigator = self._create_tool_button("navigator", "Toggle Chapter & Scene Navigator", text="Outline Navigator", checkable=True, width=145)
        self.btn_navigator.setChecked(True)
        self.btn_navigator.clicked.connect(self.navigatorToggled.emit)
        self.drawers_group.add_widget(self.btn_navigator)

        self.btn_codex = self._create_tool_button("codex", "Toggle Worldbuilding & Character Codex", text="Story Codex", checkable=True, width=135)
        self.btn_codex.setChecked(True)
        self.btn_codex.clicked.connect(self.codexToggled.emit)
        self.drawers_group.add_widget(self.btn_codex)
        layout.addWidget(self.drawers_group)
        layout.addWidget(create_ribbon_separator())

        self.cork_group = ModernRibbonGroup("Storyboarding")
        self.btn_corkboard = self._create_tool_button("corkboard", "Hybrid Corkboard & Index Cards", text="Corkboard Studio", width=140)
        self.cork_group.add_widget(self.btn_corkboard)
        layout.addWidget(self.cork_group)
        layout.addWidget(create_ribbon_separator())

        pet_group = ModernRibbonGroup("Scribe Companion")
        self.btn_pet = self._create_tool_button("raven", "Toggle Writing Pet", text="Corvus the Raven", checkable=True, width=150)
        self.btn_pet.setChecked(True)
        self.btn_pet.clicked.connect(self.writingPetToggled.emit)
        pet_group.add_widget(self.btn_pet)
        layout.addWidget(pet_group)

        layout.addStretch()
        self.story_tab_idx = self.tab_widget.count()
        self.tab_widget.addTab(tab, "Story")

    def set_document_mode(self, mode: DocumentMode) -> None:
        """Adapts the ribbon tabs and drawer button labels to the active document mode."""
        if mode == DocumentMode.ACADEMIC:
            self.tab_widget.setTabText(self.story_tab_idx, "Research")
            self.btn_codex.setText("Citations")
            self.btn_codex.setIcon(VectorIconFactory.create_icon("citation", "#7aa2f7", 18))
            self.btn_codex.setToolTip("Toggle Scholarly Citations & Bibliography Drawer")
            self.btn_navigator.setText("Paper Outline")
            self.drawers_group.title_label.setText("Scholarly Drawers")
            self.cork_group.title_label.setText("Notes & Cards")
        elif mode == DocumentMode.NON_FICTION:
            self.tab_widget.setTabText(self.story_tab_idx, "Structure")
            self.btn_codex.setText("Research Dossier")
            self.btn_codex.setIcon(VectorIconFactory.create_icon("navigator", "#7aa2f7", 18))
            self.btn_codex.setToolTip("Toggle Research & Topic Dossier Drawer")
            self.btn_navigator.setText("Section Outline")
            self.drawers_group.title_label.setText("Outline Drawers")
            self.cork_group.title_label.setText("Idea Board")
        else:
            self.tab_widget.setTabText(self.story_tab_idx, "Story")
            self.btn_codex.setText("Story Codex")
            self.btn_codex.setIcon(VectorIconFactory.create_icon("codex", "#7aa2f7", 18))
            self.btn_codex.setToolTip("Toggle Worldbuilding & Character Codex")
            self.btn_navigator.setText("Outline Navigator")
            self.drawers_group.title_label.setText("Story Drawers")
            self.cork_group.title_label.setText("Storyboarding")

    def _build_review_tab(self) -> None:
        tab = QWidget()
        layout = QHBoxLayout(tab)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)

        # Master Revision Mode
        rev_group = ModernRibbonGroup("Revision Suite")
        self.btn_rev_mode = self._create_tool_button("highlight", "Activate Full Revision Suite", text="Revision Mode", checkable=True, width=125)
        self.btn_rev_mode.clicked.connect(self.revisionModeToggled.emit)
        rev_group.add_widget(self.btn_rev_mode)
        layout.addWidget(rev_group)
        layout.addWidget(create_ribbon_separator())

        # Five Proofreading Lenses
        lenses_group = ModernRibbonGroup("Proofreading Lenses")
        h_lens = QHBoxLayout()
        h_lens.setSpacing(4)

        lens_btn_style = """
            QPushButton {
                background-color: #1f2335;
                color: #9aa5ce;
                border: 1px solid #292e42;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 10px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #24283b;
                color: #c0caf5;
            }
            QPushButton:checked {
                background-color: rgba(122, 162, 247, 0.22);
                color: #7aa2f7;
                border: 1px solid #7aa2f7;
            }
        """

        self.btn_spell = QPushButton("Spell Check")
        self.btn_spell.setCheckable(True)
        self.btn_spell.setStyleSheet(lens_btn_style)
        self.btn_spell.setToolTip("Underline misspelled words with candidate correction suggestions")
        self.btn_spell.clicked.connect(self.spellCheckToggled.emit)
        h_lens.addWidget(self.btn_spell)

        self.btn_adverbs = QPushButton("Adverbs")
        self.btn_adverbs.setCheckable(True)
        self.btn_adverbs.setStyleSheet(lens_btn_style)
        self.btn_adverbs.setToolTip("Highlight weak -ly adverbs and soft modifiers")
        self.btn_adverbs.clicked.connect(self.adverbsLensToggled.emit)
        h_lens.addWidget(self.btn_adverbs)

        self.btn_passive = QPushButton("Passive Voice")
        self.btn_passive.setCheckable(True)
        self.btn_passive.setStyleSheet(lens_btn_style)
        self.btn_passive.setToolTip("Flag 'was/were + participle' passive constructions")
        self.btn_passive.clicked.connect(self.passiveVoiceLensToggled.emit)
        h_lens.addWidget(self.btn_passive)

        self.btn_pacing = QPushButton("Pacing & Rhythm")
        self.btn_pacing.setCheckable(True)
        self.btn_pacing.setStyleSheet(lens_btn_style)
        self.btn_pacing.setToolTip("Sentence cadence heatmap (staccato vs fluid vs lyrical)")
        self.btn_pacing.clicked.connect(self.pacingLensToggled.emit)
        h_lens.addWidget(self.btn_pacing)

        self.btn_filler = QPushButton("Filler Words")
        self.btn_filler.setCheckable(True)
        self.btn_filler.setStyleSheet(lens_btn_style)
        self.btn_filler.setToolTip("Identify empty throat-clearing crutches")
        self.btn_filler.clicked.connect(self.fillerLensToggled.emit)
        h_lens.addWidget(self.btn_filler)

        self.btn_dialogue = QPushButton("Dialogue Flow")
        self.btn_dialogue.setCheckable(True)
        self.btn_dialogue.setStyleSheet(lens_btn_style)
        self.btn_dialogue.setToolTip("Isolate quoted dialogue speech from narrative")
        self.btn_dialogue.clicked.connect(self.dialogueLensToggled.emit)
        h_lens.addWidget(self.btn_dialogue)

        lenses_group.add_layout(h_lens)
        layout.addWidget(lenses_group)
        layout.addWidget(create_ribbon_separator())

        # Inspector Panel & Analytics
        insp_group = ModernRibbonGroup("Inspector & Analytics")
        h_insp = QHBoxLayout()
        h_insp.setSpacing(4)

        self.btn_inspector = self._create_tool_button("highlight", "Toggle Revision Inspector Sidebar", text="Revision Inspector", checkable=True, width=135)
        self.btn_inspector.setChecked(False)
        self.btn_inspector.clicked.connect(self.inspectorToggled.emit)
        h_insp.addWidget(self.btn_inspector)

        self.btn_stats = self._create_tool_button("stats", "Document Statistics & Readability", text="Statistics", width=95)
        self.btn_stats.clicked.connect(self.statisticsRequested.emit)
        h_insp.addWidget(self.btn_stats)

        insp_group.add_layout(h_insp)
        layout.addWidget(insp_group)
        layout.addWidget(create_ribbon_separator())

        # Find & Replace
        search_group = ModernRibbonGroup("Search")
        h_search = QHBoxLayout()
        h_search.setSpacing(4)
        btn_find_rev = self._create_tool_button("search", "Find in Document (Ctrl+F)", text="Find", width=80)
        btn_find_rev.clicked.connect(self.findRequested.emit)
        h_search.addWidget(btn_find_rev)

        btn_rep_rev = self._create_tool_button("replace", "Find & Replace (Ctrl+H)", text="Replace", width=85)
        btn_rep_rev.clicked.connect(self.replaceRequested.emit)
        h_search.addWidget(btn_rep_rev)

        search_group.add_layout(h_search)
        layout.addWidget(search_group)

        layout.addStretch()
        self.tab_widget.addTab(tab, "Review")

    def _build_view_tab(self) -> None:
        tab = QWidget()
        layout = QHBoxLayout(tab)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)

        modes_group = ModernRibbonGroup("Operating Modes")
        self.btn_zen = self._create_tool_button("zen", "Distraction-Free Zen Mode (F11)", text="Zen Focus", width=105)
        self.btn_zen.clicked.connect(self.zenModeRequested.emit)
        modes_group.add_widget(self.btn_zen)
        layout.addWidget(modes_group)
        layout.addWidget(create_ribbon_separator())

        disp_group = ModernRibbonGroup("Display")
        v_d = QVBoxLayout()
        v_d.setSpacing(3)

        self.chk_ruler = QPushButton("Ruler")
        self.chk_ruler.setCheckable(True)
        self.chk_ruler.setChecked(True)
        self.chk_ruler.toggled.connect(self.rulerToggled.emit)
        v_d.addWidget(self.chk_ruler)

        h_z = QHBoxLayout()
        h_z.addWidget(QLabel("Zoom:"))
        self.zoom_combo = QComboBox()
        for z in [50, 75, 100, 125, 150, 200]:
            self.zoom_combo.addItem(f"{z}%", z / 100.0)
        self.zoom_combo.setCurrentText("100%")
        self.zoom_combo.currentIndexChanged.connect(lambda: self.zoomChanged.emit(self.zoom_combo.currentData()))
        h_z.addWidget(self.zoom_combo)
        v_d.addLayout(h_z)

        disp_group.add_layout(v_d)
        layout.addWidget(disp_group)
        layout.addWidget(create_ribbon_separator())

        theme_group = ModernRibbonGroup("Theme")
        self.theme_combo = QComboBox()
        self.theme_combo.addItem("Deep Midnight Studio")
        self.theme_combo.addItem("Classic Warm Scholarly")
        self.theme_combo.addItem("Modern Fluent Light")
        self.theme_combo.currentTextChanged.connect(self.themeChanged.emit)
        theme_group.add_widget(self.theme_combo)
        layout.addWidget(theme_group)
        layout.addWidget(create_ribbon_separator())

        # Sensory Acoustics Group
        sound_group = ModernRibbonGroup("Sensory & Acoustics")
        v_s = QVBoxLayout()
        v_s.setSpacing(3)

        h_s1 = QHBoxLayout()
        h_s1.addWidget(QLabel("Typewriter:"))
        self.typewriter_combo = QComboBox()
        for tp in TypewriterSoundPreset:
            self.typewriter_combo.addItem(tp.value, tp)
        self.typewriter_combo.currentIndexChanged.connect(lambda: self.typewriterSoundChanged.emit(self.typewriter_combo.currentData()))
        h_s1.addWidget(self.typewriter_combo)
        v_s.addLayout(h_s1)

        h_s2 = QHBoxLayout()
        h_s2.addWidget(QLabel("Ambient:"))
        self.ambient_combo = QComboBox()
        for ap in AmbientSoundPreset:
            self.ambient_combo.addItem(ap.value, ap)
        self.ambient_combo.currentIndexChanged.connect(lambda: self.ambientSoundChanged.emit(self.ambient_combo.currentData()))
        h_s2.addWidget(self.ambient_combo)
        v_s.addLayout(h_s2)

        sound_group.add_layout(v_s)
        layout.addWidget(sound_group)

        layout.addStretch()
        self.tab_widget.addTab(tab, "View")
