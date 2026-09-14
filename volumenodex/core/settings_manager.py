"""Settings and preferences manager for Volumenodex Studio.

Manages persistent configuration including variable autosave intervals,
recent file history, startup behavior, daily writing goals,
default document modes, and studio preferences using QSettings.
"""

import os
from datetime import datetime
from typing import Dict, Any, List, Optional
from PySide6.QtCore import QObject, Signal, QSettings


class SettingsManager(QObject):
    """Manages application-wide persistent preferences and autosave options."""

    settingsChanged = Signal()
    recentFilesChanged = Signal()

    AUTOSAVE_INTERVAL_OPTIONS: List[int] = [1, 2, 5, 10, 15, 30]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._settings = QSettings("Volumenodex", "Studio")
        self.autosave_enabled: bool = True
        self.autosave_interval_minutes: int = 2
        self.default_document_mode: str = "creative_fiction"
        self.show_crop_marks: bool = True
        self.auto_open_recent: bool = False
        self.recent_files: List[str] = []
        self.daily_word_goal: int = 1000
        self.daily_words_date: str = ""
        self.daily_words_count: int = 0
        self.load()

    def load(self) -> None:
        """Loads configuration from persistent system storage."""
        val_enabled = self._settings.value("autosave/enabled", True)
        if isinstance(val_enabled, str):
            self.autosave_enabled = val_enabled.lower() in ("true", "1")
        else:
            self.autosave_enabled = bool(val_enabled)

        val_interval = self._settings.value("autosave/interval_minutes", 2)
        try:
            self.autosave_interval_minutes = int(val_interval)
            if self.autosave_interval_minutes not in self.AUTOSAVE_INTERVAL_OPTIONS:
                if self.autosave_interval_minutes <= 1:
                    self.autosave_interval_minutes = 1
                elif self.autosave_interval_minutes <= 3:
                    self.autosave_interval_minutes = 2
                elif self.autosave_interval_minutes <= 7:
                    self.autosave_interval_minutes = 5
                elif self.autosave_interval_minutes <= 12:
                    self.autosave_interval_minutes = 10
                else:
                    self.autosave_interval_minutes = 15
        except (ValueError, TypeError):
            self.autosave_interval_minutes = 2

        self.default_document_mode = str(self._settings.value("general/default_mode", "creative_fiction"))

        val_crop = self._settings.value("view/show_crop_marks", True)
        if isinstance(val_crop, str):
            self.show_crop_marks = val_crop.lower() in ("true", "1")
        else:
            self.show_crop_marks = bool(val_crop)

        val_auto_open = self._settings.value("general/auto_open_recent", False)
        if isinstance(val_auto_open, str):
            self.auto_open_recent = val_auto_open.lower() in ("true", "1")
        else:
            self.auto_open_recent = bool(val_auto_open)

        # Recent files list
        raw_recent = self._settings.value("general/recent_files", [])
        if isinstance(raw_recent, list):
            self.recent_files = [str(p) for p in raw_recent if os.path.exists(str(p))]
        elif isinstance(raw_recent, str) and raw_recent:
            self.recent_files = [raw_recent] if os.path.exists(raw_recent) else []
        else:
            self.recent_files = []

        # Daily word count goal & tracking
        val_goal = self._settings.value("writing/daily_word_goal", 1000)
        try:
            self.daily_word_goal = max(50, int(val_goal))
        except (ValueError, TypeError):
            self.daily_word_goal = 1000

        today_str = datetime.now().strftime("%Y-%m-%d")
        stored_date = str(self._settings.value("writing/daily_words_date", today_str))
        if stored_date == today_str:
            val_words = self._settings.value("writing/daily_words_count", 0)
            try:
                self.daily_words_count = max(0, int(val_words))
            except (ValueError, TypeError):
                self.daily_words_count = 0
            self.daily_words_date = today_str
        else:
            self.daily_words_date = today_str
            self.daily_words_count = 0

    def save(self) -> None:
        """Saves current configuration to persistent storage."""
        self._settings.setValue("autosave/enabled", self.autosave_enabled)
        self._settings.setValue("autosave/interval_minutes", self.autosave_interval_minutes)
        self._settings.setValue("general/default_mode", self.default_document_mode)
        self._settings.setValue("general/auto_open_recent", self.auto_open_recent)
        self._settings.setValue("general/recent_files", self.recent_files[:10])
        self._settings.setValue("view/show_crop_marks", self.show_crop_marks)
        self._settings.setValue("writing/daily_word_goal", self.daily_word_goal)
        self._settings.setValue("writing/daily_words_date", self.daily_words_date)
        self._settings.setValue("writing/daily_words_count", self.daily_words_count)
        self._settings.sync()
        self.settingsChanged.emit()

    def set_autosave(self, enabled: bool, interval_minutes: int) -> None:
        """Updates autosave settings and triggers persistence."""
        self.autosave_enabled = enabled
        if interval_minutes in self.AUTOSAVE_INTERVAL_OPTIONS:
            self.autosave_interval_minutes = interval_minutes
        self.save()

    def add_recent_file(self, file_path: str) -> None:
        """Adds a file to the recent history, deduplicating and placing at front."""
        if not file_path or not os.path.exists(file_path):
            return
        abs_path = os.path.abspath(file_path)
        if abs_path in self.recent_files:
            self.recent_files.remove(abs_path)
        self.recent_files.insert(0, abs_path)
        self.recent_files = self.recent_files[:10]
        self._settings.setValue("general/recent_files", self.recent_files)
        self._settings.sync()
        self.recentFilesChanged.emit()

    def clear_recent_files(self) -> None:
        """Clears the recent files history."""
        self.recent_files.clear()
        self._settings.setValue("general/recent_files", [])
        self._settings.sync()
        self.recentFilesChanged.emit()

    def get_most_recent_file(self) -> Optional[str]:
        """Returns the path of the most recently accessed document if valid."""
        for path in self.recent_files:
            if os.path.exists(path):
                return path
        return None

    def record_words_written(self, delta: int) -> int:
        """Adds typed words to today's tally and persists."""
        today_str = datetime.now().strftime("%Y-%m-%d")
        if self.daily_words_date != today_str:
            self.daily_words_date = today_str
            self.daily_words_count = 0
        if delta > 0:
            self.daily_words_count += delta
            self._settings.setValue("writing/daily_words_date", self.daily_words_date)
            self._settings.setValue("writing/daily_words_count", self.daily_words_count)
            self._settings.sync()
        return self.daily_words_count

    def get_autosave_label(self) -> str:
        """Returns a human-readable summary badge string for UI headers."""
        if not self.autosave_enabled:
            return "Auto-Save: Off"
        return f"Auto-Save: {self.autosave_interval_minutes}m"
