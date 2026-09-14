"""Theme management and styling for Volumenodex."""

from dataclasses import dataclass
from typing import Dict


@dataclass
class ThemeColors:
    name: str
    bg_app: str
    bg_surface: str
    bg_surface_hover: str
    bg_surface_active: str
    border: str
    border_subtle: str
    text_primary: str
    text_secondary: str
    text_muted: str
    accent_primary: str
    accent_secondary: str
    accent_hover: str
    accent_text: str
    page_bg_light: str
    page_text_light: str
    page_bg_dark: str
    page_text_dark: str
    ruler_bg: str
    ruler_text: str
    ruler_mark: str
    ribbon_tab_bg: str
    ribbon_tab_active: str


THEMES: Dict[str, ThemeColors] = {
    "Deep Midnight Studio": ThemeColors(
        name="Deep Midnight Studio",
        bg_app="#101116",
        bg_surface="#181922",
        bg_surface_hover="#232532",
        bg_surface_active="#2d3042",
        border="#2a2c3d",
        border_subtle="#1f212e",
        text_primary="#e1e4f2",
        text_secondary="#a2a7c4",
        text_muted="#666a87",
        accent_primary="#7aa2f7",
        accent_secondary="#bb9af7",
        accent_hover="#89b4fa",
        accent_text="#101116",
        page_bg_light="#fcfbf7",
        page_text_light="#18181b",
        page_bg_dark="#1c1d28",
        page_text_dark="#f1f3fa",
        ruler_bg="#161720",
        ruler_text="#8c91b0",
        ruler_mark="#3b3e56",
        ribbon_tab_bg="#14151d",
        ribbon_tab_active="#20222f",
    ),
    "Classic Warm Scholarly": ThemeColors(
        name="Classic Warm Scholarly",
        bg_app="#25211d",
        bg_surface="#322c27",
        bg_surface_hover="#413a34",
        bg_surface_active="#4f463e",
        border="#4a423a",
        border_subtle="#38312b",
        text_primary="#ece5dd",
        text_secondary="#bdaea1",
        text_muted="#85776b",
        accent_primary="#d4a373",
        accent_secondary="#e29578",
        accent_hover="#dfab7c",
        accent_text="#25211d",
        page_bg_light="#faf6ee",
        page_text_light="#2b231c",
        page_bg_dark="#27221d",
        page_text_dark="#ece5dd",
        ruler_bg="#2b2621",
        ruler_text="#a89a8c",
        ruler_mark="#574d43",
        ribbon_tab_bg="#221e1a",
        ribbon_tab_active="#3a332d",
    ),
    "Modern Fluent Light": ThemeColors(
        name="Modern Fluent Light",
        bg_app="#f4f4f6",
        bg_surface="#ffffff",
        bg_surface_hover="#f0f1f4",
        bg_surface_active="#e4e6eb",
        border="#d6d9e0",
        border_subtle="#e7e9ee",
        text_primary="#1c1e21",
        text_secondary="#525760",
        text_muted="#8d929b",
        accent_primary="#0067c0",
        accent_secondary="#625b71",
        accent_hover="#1976d2",
        accent_text="#ffffff",
        page_bg_light="#ffffff",
        page_text_light="#1a1a1a",
        page_bg_dark="#26282b",
        page_text_dark="#f0f2f5",
        ruler_bg="#ffffff",
        ruler_text="#5a606a",
        ruler_mark="#cbd0d8",
        ribbon_tab_bg="#eaecf0",
        ribbon_tab_active="#ffffff",
    ),
}


class ThemeManager:
    """Manages application stylesheets and color themes."""

    def __init__(self, current_theme: str = "Deep Midnight Studio", dark_paper: bool = False):
        self._current_theme_name = current_theme
        self._dark_paper = dark_paper

    @property
    def current(self) -> ThemeColors:
        return THEMES.get(self._current_theme_name, THEMES["Deep Midnight Studio"])

    @property
    def dark_paper(self) -> bool:
        return self._dark_paper

    @dark_paper.setter
    def dark_paper(self, value: bool) -> None:
        self._dark_paper = value

    def set_theme(self, theme_name: str) -> None:
        if theme_name in THEMES:
            self._current_theme_name = theme_name

    def generate_qss(self) -> str:
        c = self.current
        return f"""
        QMainWindow, QDialog {{
            background-color: {c.bg_app};
            color: {c.text_primary};
        }}
        QWidget {{
            font-family: 'Segoe UI', 'SF Pro Text', -apple-system, sans-serif;
            font-size: 13px;
            color: {c.text_primary};
        }}
        /* Push Buttons (Standard across Studio, Dialogs & Message Boxes) */
        QPushButton {{
            background-color: {c.bg_surface};
            color: {c.text_primary};
            border: 1px solid {c.border};
            border-radius: 5px;
            padding: 5px 14px;
            font-weight: 600;
            font-size: 12px;
            outline: none;
        }}
        QPushButton:hover {{
            background-color: {c.bg_surface_hover};
            border: 1px solid {c.accent_primary};
            color: {c.text_primary};
        }}
        QPushButton:pressed, QPushButton:checked {{
            background-color: {c.bg_surface_active};
            border: 1px solid {c.accent_primary};
            color: {c.accent_primary};
        }}
        QPushButton:disabled {{
            background-color: {c.bg_surface};
            color: {c.text_muted};
            border: 1px solid {c.border_subtle};
        }}
        QPushButton:default, QPushButton#primaryBtn {{
            background-color: {c.accent_primary};
            color: {c.accent_text};
            border: 1px solid {c.accent_primary};
            font-weight: 700;
        }}
        QPushButton:default:hover, QPushButton#primaryBtn:hover {{
            background-color: {c.accent_hover};
            border: 1px solid {c.accent_hover};
            color: {c.accent_text};
        }}
        /* Dialog & Message Box Buttons */
        QMessageBox {{
            background-color: {c.bg_app};
            color: {c.text_primary};
        }}
        QMessageBox QLabel {{
            color: {c.text_primary};
            background-color: transparent;
            font-size: 13px;
        }}
        QMessageBox QPushButton {{
            min-width: 80px;
            min-height: 26px;
            padding: 6px 16px;
            border-radius: 5px;
            font-weight: 600;
            background-color: {c.bg_surface};
            color: {c.text_primary};
            border: 1px solid {c.border};
        }}
        QMessageBox QPushButton:hover {{
            background-color: {c.bg_surface_hover};
            border: 1px solid {c.accent_primary};
            color: {c.text_primary};
        }}
        QMessageBox QPushButton:default {{
            background-color: {c.accent_primary};
            color: {c.accent_text};
            border: 1px solid {c.accent_primary};
            font-weight: 700;
        }}
        QMessageBox QPushButton:default:hover {{
            background-color: {c.accent_hover};
            border: 1px solid {c.accent_hover};
            color: {c.accent_text};
        }}
        QDialogButtonBox QPushButton {{
            min-width: 80px;
            padding: 6px 16px;
        }}
        QMenuBar {{
            background-color: {c.bg_surface};
            color: {c.text_primary};
            border-bottom: 1px solid {c.border};
            padding: 2px 4px;
        }}
        QMenuBar::item {{
            background: transparent;
            padding: 4px 10px;
            border-radius: 4px;
        }}
        QMenuBar::item:selected {{
            background: {c.bg_surface_hover};
        }}
        QMenu {{
            background-color: {c.bg_surface};
            color: {c.text_primary};
            border: 1px solid {c.border};
            border-radius: 6px;
            padding: 4px;
        }}
        QMenu::item {{
            padding: 6px 24px 6px 12px;
            border-radius: 4px;
        }}
        QMenu::item:selected {{
            background-color: {c.accent_primary};
            color: #ffffff;
        }}
        QMenu::separator {{
            height: 1px;
            background: {c.border};
            margin: 4px 8px;
        }}
        QToolBar {{
            background-color: {c.bg_surface};
            border-bottom: 1px solid {c.border};
            spacing: 4px;
            padding: 4px;
        }}
        QToolButton {{
            background-color: transparent;
            border: 1px solid transparent;
            border-radius: 5px;
            padding: 5px 8px;
            color: {c.text_primary};
        }}
        QToolButton:hover {{
            background-color: {c.bg_surface_hover};
            border: 1px solid {c.border_subtle};
        }}
        QToolButton:pressed, QToolButton:checked {{
            background-color: {c.bg_surface_active};
            border: 1px solid {c.accent_primary};
            color: {c.accent_primary};
        }}
        QComboBox {{
            background-color: {c.bg_surface};
            border: 1px solid {c.border};
            border-radius: 5px;
            padding: 4px 10px;
            color: {c.text_primary};
            min-height: 22px;
        }}
        QComboBox:hover {{
            border: 1px solid {c.accent_primary};
        }}
        QComboBox::drop-down {{
            border: none;
            width: 20px;
        }}
        QComboBox QAbstractItemView {{
            background-color: {c.bg_surface};
            border: 1px solid {c.border};
            selection-background-color: {c.accent_primary};
            color: {c.text_primary};
            outline: none;
        }}
        QTabWidget::pane {{
            border: none;
            background: transparent;
        }}
        QTabBar::tab {{
            background: {c.ribbon_tab_bg};
            color: {c.text_secondary};
            padding: 6px 16px;
            border-top-left-radius: 6px;
            border-top-right-radius: 6px;
            border: 1px solid transparent;
            margin-right: 2px;
            font-weight: 500;
        }}
        QTabBar::tab:hover {{
            background: {c.bg_surface_hover};
            color: {c.text_primary};
        }}
        QTabBar::tab:selected {{
            background: {c.ribbon_tab_active};
            color: {c.accent_primary};
            border: 1px solid {c.border};
            border-bottom: 2px solid {c.accent_primary};
        }}
        QScrollBar:vertical {{
            background: {c.bg_app};
            width: 12px;
            margin: 0px;
            border-radius: 6px;
        }}
        QScrollBar::handle:vertical {{
            background: {c.border};
            min-height: 24px;
            border-radius: 6px;
            margin: 2px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {c.accent_primary};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
        QScrollBar:horizontal {{
            background: {c.bg_app};
            height: 12px;
            margin: 0px;
            border-radius: 6px;
        }}
        QScrollBar::handle:horizontal {{
            background: {c.border};
            min-width: 24px;
            border-radius: 6px;
            margin: 2px;
        }}
        QScrollBar::handle:horizontal:hover {{
            background: {c.accent_primary};
        }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            width: 0px;
        }}
        QStatusBar {{
            background-color: {c.bg_surface};
            color: {c.text_secondary};
            border-top: 1px solid {c.border};
            font-size: 12px;
        }}
        QToolTip {{
            background-color: {c.bg_surface};
            color: {c.text_primary};
            border: 1px solid {c.border};
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
        }}
        """
