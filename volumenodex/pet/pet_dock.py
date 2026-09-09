"""Floating studio dock widget for the Writing Pet with auto-fading speech bubble and mood animations."""

from typing import Optional
from PySide6.QtCore import Qt, Signal, QTimer, QSize, QRectF
from PySide6.QtGui import QColor, QFont, QPainter, QBrush, QPen
from PySide6.QtWidgets import (
    QWidget, QFrame, QVBoxLayout, QHBoxLayout, QLabel, QToolButton,
    QGraphicsDropShadowEffect
)

from volumenodex.pet.pet_model import PetProfile, PetMood
from volumenodex.pet.insight_engine import InsightEngine
from volumenodex.pet.companion_figures import CompanionFigureRenderer
from volumenodex.ui.vector_icons import VectorIconFactory


class PetSpeechBubble(QFrame):
    """An elegant speech bubble that appears over the companion and auto-fades after 8 seconds."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(290)
        self.setObjectName("petSpeechBubble")
        self.setStyleSheet("""
            #petSpeechBubble {
                background-color: #1a1c2b;
                border: 1px solid #3b3e58;
                border-radius: 10px;
            }
            #petSpeechBubble QLabel {
                background: transparent;
                border: none;
            }
        """)

        # Drop shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(16)
        shadow.setColor(QColor(0, 0, 0, 160))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        # Header with dismiss
        h_top = QHBoxLayout()
        self.lbl_title = QLabel("Corvus whispers:")
        self.lbl_title.setStyleSheet("color: #7aa2f7; font-size: 11px; font-weight: bold; border: none;")
        h_top.addWidget(self.lbl_title)
        h_top.addStretch()

        self.btn_close = QToolButton()
        self.btn_close.setIcon(VectorIconFactory.create_icon("close", "#717897", 10))
        self.btn_close.setFixedSize(16, 16)
        self.btn_close.setStyleSheet("""
            QToolButton {
                background: transparent;
                border: none;
                border-radius: 3px;
            }
            QToolButton:hover {
                background: rgba(255, 255, 255, 0.1);
            }
        """)
        self.btn_close.clicked.connect(self.hide_bubble)
        h_top.addWidget(self.btn_close)
        layout.addLayout(h_top)

        # Content Text
        self.lbl_message = QLabel()
        self.lbl_message.setWordWrap(True)
        self.lbl_message.setStyleSheet("color: #e1e4f2; font-size: 12px; line-height: 1.35; border: none;")
        layout.addWidget(self.lbl_message)

        # Auto-fade timer (8 seconds)
        self._fade_timer = QTimer(self)
        self._fade_timer.setInterval(8000)
        self._fade_timer.setSingleShot(True)
        self._fade_timer.timeout.connect(self.hide_bubble)

    def show_message(self, pet_name: str, message: str, mood: PetMood) -> None:
        mood_titles = {
            PetMood.ALERT: f"{pet_name} noticed:",
            PetMood.CELEBRATING: f"{pet_name} celebrates!",
            PetMood.NUDGING: f"{pet_name} reminds you:",
            PetMood.WRITING: f"{pet_name}:",
            PetMood.IDLE: f"{pet_name} ponders:",
            PetMood.SLEEPING: f"{pet_name} (dozing):",
        }
        self.lbl_title.setText(mood_titles.get(mood, f"{pet_name}:"))
        self.lbl_message.setText(message)
        self.show()
        self.raise_()
        self._fade_timer.start(8000)

        dock = self.parentWidget()
        if hasattr(dock, "reposition"):
            dock.reposition()
            QTimer.singleShot(0, dock.reposition)

    def hide_bubble(self) -> None:
        self._fade_timer.stop()
        self.hide()
        dock = self.parentWidget()
        if hasattr(dock, "reposition"):
            dock.reposition()
            QTimer.singleShot(0, dock.reposition)


class FloatingPetDock(QWidget):
    """Floating Studio Companion docked in the bottom-right corner with avatar and control palette."""

    settingsRequested = Signal()
    breakSettingsRequested = Signal()
    dismissRequested = Signal()

    def __init__(self, engine: InsightEngine, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.is_snoozed = False

        self.setFixedWidth(330)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        if parent:
            parent.installEventFilter(self)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(6)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignRight)

        # Speech Bubble
        self.bubble = PetSpeechBubble(self)
        self.bubble.hide()
        main_layout.addWidget(self.bubble)

        # Companion Card Container
        self.card = QFrame(self)
        self.card.setObjectName("companionCard")
        self.card.setStyleSheet("""
            #companionCard {
                background-color: #171822;
                border: 1px solid #2e3146;
                border-radius: 14px;
            }
            #companionCard QLabel {
                border: none;
                background: transparent;
            }
        """)

        # Subtle card shadow
        card_shadow = QGraphicsDropShadowEffect(self.card)
        card_shadow.setBlurRadius(20)
        card_shadow.setColor(QColor(0, 0, 0, 170))
        card_shadow.setOffset(0, 4)
        self.card.setGraphicsEffect(card_shadow)

        card_layout = QHBoxLayout(self.card)
        card_layout.setContentsMargins(8, 6, 8, 6)
        card_layout.setSpacing(8)

        # Avatar / Figure Button (Illustrated Vector Portrait)
        self.btn_avatar = QToolButton()
        self.btn_avatar.setFixedSize(42, 42)
        self.btn_avatar.setIconSize(QSize(38, 38))
        self.btn_avatar.setStyleSheet("""
            QToolButton {
                background-color: #1f2130;
                border: 1px solid #3b3e58;
                border-radius: 21px;
                padding: 0px;
            }
            QToolButton:hover {
                background-color: #272a3e;
                border: 1px solid #7aa2f7;
            }
        """)
        self.btn_avatar.clicked.connect(self._on_avatar_clicked)
        card_layout.addWidget(self.btn_avatar)

        # Companion Info Labels
        v_info = QVBoxLayout()
        v_info.setSpacing(1)

        self.lbl_name = QLabel(self.engine.active_pet.name)
        self.lbl_name.setStyleSheet("font-weight: bold; font-size: 12px; color: #c0caf5; border: none;")
        v_info.addWidget(self.lbl_name)

        self.lbl_species = QLabel(self.engine.active_pet.species_title)
        self.lbl_species.setStyleSheet("font-size: 10px; color: #787c99; border: none;")
        v_info.addWidget(self.lbl_species)
        card_layout.addLayout(v_info)

        card_layout.addStretch()

        # Action Button Stylesheet
        action_btn_qss = """
            QToolButton {
                background: transparent;
                border: 1px solid transparent;
                border-radius: 4px;
                padding: 2px;
            }
            QToolButton:hover {
                background: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.12);
            }
            QToolButton:pressed {
                background: rgba(122, 162, 247, 0.2);
            }
        """

        # 1. Creative Spark / Story Prompt
        self.btn_prompt = QToolButton()
        self.btn_prompt.setIcon(VectorIconFactory.create_icon("prompt", "#e0af68", 16))
        self.btn_prompt.setIconSize(QSize(16, 16))
        self.btn_prompt.setToolTip("Creative Spark / Story Twist (Click for inspiration)")
        self.btn_prompt.setFixedSize(26, 26)
        self.btn_prompt.setStyleSheet(action_btn_qss)
        self.btn_prompt.clicked.connect(self.engine.trigger_creative_spark)
        card_layout.addWidget(self.btn_prompt)

        # 2. Break Timer Dialog
        self.btn_timer = QToolButton()
        self.btn_timer.setIcon(VectorIconFactory.create_icon("timer", "#c0caf5", 16))
        self.btn_timer.setIconSize(QSize(16, 16))
        self.btn_timer.setToolTip("Configure Break / Pomodoro Timer")
        self.btn_timer.setFixedSize(26, 26)
        self.btn_timer.setStyleSheet(action_btn_qss)
        self.btn_timer.clicked.connect(self.breakSettingsRequested.emit)
        card_layout.addWidget(self.btn_timer)

        # 3. Snooze / Wake
        self.btn_snooze = QToolButton()
        self.btn_snooze.setIcon(VectorIconFactory.create_icon("snooze", "#7aa2f7", 16))
        self.btn_snooze.setIconSize(QSize(16, 16))
        self.btn_snooze.setToolTip("Snooze Companion")
        self.btn_snooze.setFixedSize(26, 26)
        self.btn_snooze.setStyleSheet(action_btn_qss)
        self.btn_snooze.clicked.connect(self.toggle_snooze)
        card_layout.addWidget(self.btn_snooze)

        # 4. Settings / Pet Selection Dialog
        self.btn_settings = QToolButton()
        self.btn_settings.setIcon(VectorIconFactory.create_icon("settings", "#c0caf5", 16))
        self.btn_settings.setIconSize(QSize(16, 16))
        self.btn_settings.setToolTip("Select or Create Writing Pet")
        self.btn_settings.setFixedSize(26, 26)
        self.btn_settings.setStyleSheet(action_btn_qss)
        self.btn_settings.clicked.connect(self.settingsRequested.emit)
        card_layout.addWidget(self.btn_settings)

        # 5. Explicit Dismiss / Hide Companion Button
        self.btn_hide = QToolButton()
        self.btn_hide.setIcon(VectorIconFactory.create_icon("close", "#717897", 12))
        self.btn_hide.setIconSize(QSize(12, 12))
        self.btn_hide.setToolTip("Hide Companion (Can be re-enabled from Story ribbon or Status bar)")
        self.btn_hide.setFixedSize(22, 22)
        self.btn_hide.setStyleSheet("""
            QToolButton {
                background: transparent;
                border: 1px solid transparent;
                border-radius: 4px;
            }
            QToolButton:hover {
                background: rgba(247, 118, 142, 0.15);
                border: 1px solid rgba(247, 118, 142, 0.3);
            }
        """)
        self.btn_hide.clicked.connect(self.hide_companion)
        card_layout.addWidget(self.btn_hide)

        main_layout.addWidget(self.card)

        # Initial Avatar Figure Render
        self._refresh_avatar_figure()

        # Wire engine signals
        self.engine.messageReady.connect(self._on_message_ready)
        self.engine.moodChanged.connect(self._on_mood_changed)

    def _refresh_avatar_figure(self) -> None:
        pet = self.engine.active_pet
        mood = PetMood.SLEEPING if self.is_snoozed else self.engine.current_mood
        icon = CompanionFigureRenderer.render_icon(
            pet.id,
            size=38,
            mood=mood,
            custom_image_path=pet.custom_image_path
        )
        self.btn_avatar.setIcon(icon)

    def _on_avatar_clicked(self) -> None:
        if self.bubble.isVisible():
            self.bubble.hide_bubble()
        else:
            self.engine.trigger_idle_quote()

    def _on_message_ready(self, message: str, mood: PetMood) -> None:
        if self.is_snoozed:
            return
        self.bubble.show_message(self.engine.active_pet.name, message, mood)

    def _on_mood_changed(self, mood: PetMood) -> None:
        self._refresh_avatar_figure()
        if mood == PetMood.SLEEPING:
            self.btn_avatar.setToolTip(f"{self.engine.active_pet.name} is resting quietly.")
        elif mood == PetMood.WRITING:
            self.btn_avatar.setToolTip(f"{self.engine.active_pet.name} is reading as you write.")
        else:
            self.btn_avatar.setToolTip(f"{self.engine.active_pet.name} — {self.engine.active_pet.species_title}")

    def update_pet_profile(self, pet: PetProfile) -> None:
        self.lbl_name.setText(pet.name)
        self.lbl_species.setText(pet.species_title)
        self._refresh_avatar_figure()
        self.reposition()

    def toggle_snooze(self) -> None:
        self.is_snoozed = not self.is_snoozed
        if self.is_snoozed:
            self.bubble.hide_bubble()
            self.btn_snooze.setIcon(VectorIconFactory.create_icon("snooze", "#f7768e", 16))
            self.btn_snooze.setToolTip("Companion is asleep. Click to wake.")
            self.lbl_species.setText("Snoozed — Resting")
        else:
            self.btn_snooze.setIcon(VectorIconFactory.create_icon("snooze", "#7aa2f7", 16))
            self.btn_snooze.setToolTip("Snooze Companion")
            self.lbl_species.setText(self.engine.active_pet.species_title)
            self.bubble.show_message(self.engine.active_pet.name, "I am awake and at your service once more.", PetMood.IDLE)
        self._refresh_avatar_figure()
        self.reposition()

    def hide_companion(self) -> None:
        """Hides the companion dock completely and signals the window."""
        self.bubble.hide_bubble()
        self.hide()
        self.dismissRequested.emit()

    def reposition(self) -> None:
        """Positions the dock anchored at the bottom-right so the speech bubble blossoms upwards."""
        parent = self.parentWidget()
        if not parent:
            return
        self.adjustSize()
        pw = parent.width()
        ph = parent.height()
        w = self.width()
        h = self.height()

        new_x = max(10, pw - w - 24)
        new_y = max(10, ph - h - 16)
        self.move(new_x, new_y)
        self.raise_()

    def eventFilter(self, watched, event):
        if watched == self.parentWidget():
            from PySide6.QtCore import QEvent
            if event.type() in (QEvent.Type.Resize, QEvent.Type.Show):
                self.reposition()
                QTimer.singleShot(0, self.reposition)
        return super().eventFilter(watched, event)

    def showEvent(self, event):
        super().showEvent(event)
        self.reposition()
        QTimer.singleShot(0, self.reposition)

