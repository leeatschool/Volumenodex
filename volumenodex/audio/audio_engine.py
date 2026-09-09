"""Sensory audio engine handling keystroke acoustics and looping ambient soundscapes."""

import os
import random
from enum import Enum
from typing import Dict, Optional
from PySide6.QtCore import QObject, QUrl
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput, QSoundEffect


class TypewriterSoundPreset(str, Enum):
    OFF = "Off (Silent)"
    MANUAL = "Classic Manual Typewriter"
    ELECTRIC = "Electric Typewriter"
    SOFT_MECHANICAL = "Soft Mechanical Switches"


class AmbientSoundPreset(str, Enum):
    OFF = "None (Quiet Room)"
    RAIN = "Rain on Window"
    LIBRARY = "Quiet Library"
    FIREPLACE = "Crackling Fireplace"
    COFFEE_SHOP = "Cozy Coffee Shop"
    CABIN = "Cabin in the Woods"
    CAMPING = "Camping Under Stars"
    BROWN_NOISE = "Deep Brown Noise"


class AudioEngine(QObject):
    """Manages tactile keystroke acoustics and continuous ambient soundscapes."""

    def __init__(self, base_dir: Optional[str] = None, parent=None):
        super().__init__(parent)
        self.base_dir = base_dir or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.sounds_dir = os.path.join(self.base_dir, "assets", "sounds")
        os.makedirs(self.sounds_dir, exist_ok=True)

        self.typewriter_preset = TypewriterSoundPreset.MANUAL
        self.ambient_preset = AmbientSoundPreset.OFF

        # Keystroke low-latency sound player
        self._key_effect = QSoundEffect(self)
        self._key_effect.setVolume(0.5)

        # Bell effect for Enter / Margins
        self._bell_effect = QSoundEffect(self)
        self._bell_effect.setVolume(0.4)

        # Ambient background loop player
        self._ambient_player = QMediaPlayer(self)
        self._ambient_output = QAudioOutput(self)
        self._ambient_player.setAudioOutput(self._ambient_output)
        self._ambient_player.setLoops(QMediaPlayer.Infinite)
        self._ambient_output.setVolume(0.35)

    def set_typewriter_preset(self, preset: TypewriterSoundPreset) -> None:
        self.typewriter_preset = preset

    def set_ambient_preset(self, preset: AmbientSoundPreset) -> None:
        self.ambient_preset = preset
        if preset == AmbientSoundPreset.OFF:
            self._ambient_player.stop()
            return

        # Map preset to file name
        preset_files = {
            AmbientSoundPreset.RAIN: "rain.mp3",
            AmbientSoundPreset.LIBRARY: "library.mp3",
            AmbientSoundPreset.FIREPLACE: "fireplace.mp3",
            AmbientSoundPreset.COFFEE_SHOP: "coffee_shop.mp3",
            AmbientSoundPreset.CABIN: "cabin.mp3",
            AmbientSoundPreset.CAMPING: "camping.mp3",
            AmbientSoundPreset.BROWN_NOISE: "brown_noise.mp3",
        }

        filename = preset_files.get(preset)
        if filename:
            file_path = os.path.join(self.sounds_dir, filename)
            if os.path.exists(file_path):
                self._ambient_player.setSource(QUrl.fromLocalFile(file_path))
                self._ambient_player.play()
            else:
                self._ambient_player.stop()

    def play_keystroke(self, is_return: bool = False, is_space: bool = False) -> None:
        if self.typewriter_preset == TypewriterSoundPreset.OFF:
            return

        if is_return:
            bell_path = os.path.join(self.sounds_dir, "bell.mp3")
            if os.path.exists(bell_path):
                self._bell_effect.setSource(QUrl.fromLocalFile(bell_path))
                self._bell_effect.play()
                return

        # Choose sound file based on preset
        if self.typewriter_preset == TypewriterSoundPreset.MANUAL:
            sample_num = random.randint(1, 3)
            sample_name = f"manual_click{sample_num}.mp3"
        elif self.typewriter_preset == TypewriterSoundPreset.ELECTRIC:
            sample_name = "electric_click.mp3"
        else:  # Soft mechanical
            sample_name = "soft_mechanical.mp3"

        sample_path = os.path.join(self.sounds_dir, sample_name)
        if os.path.exists(sample_path):
            self._key_effect.setSource(QUrl.fromLocalFile(sample_path))
            self._key_effect.play()

    def set_ambient_volume(self, volume_percent: int) -> None:
        vol = max(0.0, min(1.0, volume_percent / 100.0))
        self._ambient_output.setVolume(vol)

    def set_effects_volume(self, volume_percent: int) -> None:
        vol = max(0.0, min(1.0, volume_percent / 100.0))
        self._key_effect.setVolume(vol)
        self._bell_effect.setVolume(vol * 0.8)
