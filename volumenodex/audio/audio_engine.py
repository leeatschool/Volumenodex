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
        self.base_dir = self._resolve_base_dir(base_dir)
        self.sounds_dir = os.path.join(self.base_dir, "assets", "sounds")
        os.makedirs(self.sounds_dir, exist_ok=True)

        self.typewriter_preset = TypewriterSoundPreset.MANUAL
        self.ambient_preset = AmbientSoundPreset.OFF

        self._effects_volume = 0.5
        self._ambient_volume = 0.35

        # Preloaded low-latency sound effects for keystrokes & bell
        self._effects: Dict[str, QSoundEffect] = {}
        self._preload_effects()

        # Ambient background loop player
        self._ambient_player = QMediaPlayer(self)
        self._ambient_output = QAudioOutput(self)
        self._ambient_player.setAudioOutput(self._ambient_output)
        self._ambient_player.setLoops(QMediaPlayer.Infinite)
        self._ambient_output.setVolume(self._ambient_volume)

    @staticmethod
    def _resolve_base_dir(base_dir: Optional[str] = None) -> str:
        if base_dir and os.path.exists(os.path.join(base_dir, "assets", "sounds")):
            return base_dir
        cur = os.path.abspath(__file__)
        for _ in range(5):
            cur = os.path.dirname(cur)
            if os.path.exists(os.path.join(cur, "pyproject.toml")) and os.path.exists(os.path.join(cur, "assets", "sounds")):
                return cur
        # Fallback to repo root 3 levels up from volumenodex/audio/audio_engine.py
        return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    def _find_sound_file(self, base_name: str) -> Optional[str]:
        """Finds sound file matching base_name with .wav, .mp3, .ogg, or exact filename."""
        root, ext = os.path.splitext(base_name)
        extensions = [ext] if ext else [".wav", ".mp3", ".ogg", ".flac", ".m4a"]
        for test_ext in extensions:
            target = root + test_ext
            path = os.path.join(self.sounds_dir, target)
            if os.path.exists(path):
                return path
        return None

    def _preload_effects(self) -> None:
        """Preloads uncompressed .wav sound effects for zero-latency keystroke playback."""
        effect_names = [
            "manual_click1", "manual_click2", "manual_click3",
            "electric_click", "soft_mechanical", "bell"
        ]
        for name in effect_names:
            file_path = self._find_sound_file(name)
            if file_path and file_path.lower().endswith(".wav"):
                eff = QSoundEffect(self)
                eff.setSource(QUrl.fromLocalFile(file_path))
                eff.setVolume(self._effects_volume * (0.8 if name == "bell" else 1.0))
                self._effects[name] = eff

    def reload_sounds(self) -> None:
        """Re-scans sounds directory to load newly added audio files."""
        self._effects.clear()
        self._preload_effects()

    def set_typewriter_preset(self, preset: TypewriterSoundPreset) -> None:
        self.typewriter_preset = preset

    def set_ambient_preset(self, preset: AmbientSoundPreset) -> None:
        self.ambient_preset = preset
        if preset == AmbientSoundPreset.OFF:
            self._ambient_player.stop()
            return

        preset_names = {
            AmbientSoundPreset.RAIN: "rain",
            AmbientSoundPreset.LIBRARY: "library",
            AmbientSoundPreset.FIREPLACE: "fireplace",
            AmbientSoundPreset.COFFEE_SHOP: "coffee_shop",
            AmbientSoundPreset.CABIN: "cabin",
            AmbientSoundPreset.CAMPING: "camping",
            AmbientSoundPreset.BROWN_NOISE: "brown_noise",
        }

        name = preset_names.get(preset)
        if name:
            file_path = self._find_sound_file(name)
            if file_path:
                self._ambient_player.setSource(QUrl.fromLocalFile(file_path))
                self._ambient_player.play()
            else:
                self._ambient_player.stop()

    def play_keystroke(self, is_return: bool = False, is_space: bool = False) -> None:
        if self.typewriter_preset == TypewriterSoundPreset.OFF:
            return

        if is_return:
            if "bell" in self._effects:
                self._effects["bell"].play()
            return

        # Choose sound effect based on preset
        if self.typewriter_preset == TypewriterSoundPreset.MANUAL:
            sample_num = random.randint(1, 3)
            key = f"manual_click{sample_num}"
        elif self.typewriter_preset == TypewriterSoundPreset.ELECTRIC:
            key = "electric_click"
        else:  # Soft mechanical
            key = "soft_mechanical"

        if key in self._effects:
            self._effects[key].play()

    def set_ambient_volume(self, volume_percent: int) -> None:
        vol = max(0.0, min(1.0, volume_percent / 100.0))
        self._ambient_volume = vol
        self._ambient_output.setVolume(vol)

    def set_effects_volume(self, volume_percent: int) -> None:
        vol = max(0.0, min(1.0, volume_percent / 100.0))
        self._effects_volume = vol
        for name, eff in self._effects.items():
            eff.setVolume(vol * (0.8 if name == "bell" else 1.0))
