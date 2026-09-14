"""Settings and preferences manager for Volumenodex Studio.

Manages persistent configuration including variable autosave intervals,
default document modes, and studio preferences using QSettings.
"""

from typing import Dict, Any, List
from PySide6.QtCore import QObject, Signal, QSettings


class SettingsManager(QObject):
    """Manages application-wide persistent preferences and autosave options."""

    settingsChanged = Signal()

    AUTOSAVE_INTERVAL_OPTIONS: List[int] = [1, 2, 5, 10, 15, 30]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._settings = QSettings("Volumenodex", "Studio")
        self.autosave_enabled: bool = True
        self.autosave_interval_minutes: int = 2
        self.default_document_mode: str = "creative_fiction"
        self.show_crop_marks: bool = True
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

    def save(self) -> None:
        """Saves current configuration to persistent storage."""
        self._settings.setValue("autosave/enabled", self.autosave_enabled)
        self._settings.setValue("autosave/interval_minutes", self.autosave_interval_minutes)
        self._settings.setValue("general/default_mode", self.default_document_mode)
        self._settings.setValue("view/show_crop_marks", self.show_crop_marks)
        self._settings.sync()
        self.settingsChanged.emit()

    def set_autosave(self, enabled: bool, interval_minutes: int) -> None:
        """Updates autosave settings and triggers persistence."""
        self.autosave_enabled = enabled
        if interval_minutes in self.AUTOSAVE_INTERVAL_OPTIONS:
            self.autosave_interval_minutes = interval_minutes
        self.save()

    def get_autosave_label(self) -> str:
        """Returns a human-readable summary badge string for UI headers."""
        if not self.autosave_enabled:
            return "Auto-Save: Off"
        return f"Auto-Save: {self.autosave_interval_minutes}m"
