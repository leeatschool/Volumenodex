"""Sensory audio engine handling keystroke acoustics and looping ambient soundscapes."""

import os
import random
from enum import Enum
from typing import Dict, List, Optional, Tuple, Union
from PySide6.QtCore import QObject, QUrl, Signal, QFileSystemWatcher
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


EFFECT_EXTENSIONS = {".wav", ".wave", ".aiff", ".aif"}
AMBIENT_EXTENSIONS = {".wav", ".wave", ".mp3", ".ogg", ".flac", ".m4a", ".aac", ".wma"}


class AudioEngine(QObject):
    """Manages tactile keystroke acoustics and continuous ambient soundscapes."""

    availablePresetsChanged = Signal()

    def __init__(self, base_dir: Optional[str] = None, parent=None):
        super().__init__(parent)
        self.base_dir = self._resolve_base_dir(base_dir)
        self.sounds_dir = os.path.join(self.base_dir, "assets", "sounds")
        try:
            os.makedirs(self.sounds_dir, exist_ok=True)
        except OSError:
            pass

        self._effects_volume = 0.5
        self._ambient_volume = 0.35

        # Preloaded low-latency sound effects for keystrokes & bell
        self._effects: Dict[str, QSoundEffect] = {}
        self._preload_effects()

        # Initial active presets based on available files
        if self.has_typewriter_sound(TypewriterSoundPreset.MANUAL):
            self.typewriter_preset = TypewriterSoundPreset.MANUAL
        else:
            avail_tw = self.get_available_typewriter_presets()
            self.typewriter_preset = avail_tw[0][1] if avail_tw else TypewriterSoundPreset.OFF

        self.ambient_preset = AmbientSoundPreset.OFF

        # Ambient background loop player
        self._ambient_player = QMediaPlayer(self)
        self._ambient_output = QAudioOutput(self)
        self._ambient_player.setAudioOutput(self._ambient_output)
        self._ambient_player.setLoops(QMediaPlayer.Infinite)
        self._ambient_output.setVolume(self._ambient_volume)

        # File watcher for automatic updates when sounds directory changes
        self._watcher = QFileSystemWatcher(self)
        if os.path.exists(self.sounds_dir):
            self._watcher.addPath(self.sounds_dir)
        self._watcher.directoryChanged.connect(self._on_sounds_dir_changed)

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

    def _get_files_in_sounds_dir(self) -> List[str]:
        """Returns filenames in the sounds directory."""
        if not os.path.exists(self.sounds_dir):
            return []
        try:
            return [f for f in os.listdir(self.sounds_dir) if os.path.isfile(os.path.join(self.sounds_dir, f))]
        except Exception:
            return []

    def _find_sound_file(self, base_name: str) -> Optional[str]:
        """Finds sound file matching base_name case-insensitively with audio extensions."""
        files = self._get_files_in_sounds_dir()
        target_stem = os.path.splitext(base_name)[0].lower()

        # 1. Exact stem match
        for f in files:
            stem, ext = os.path.splitext(f)
            if ext.lower() in AMBIENT_EXTENSIONS and stem.lower() == target_stem:
                return os.path.join(self.sounds_dir, f)

        # 2. Prefix match (e.g. 'rain' matching 'Rain_Window.wav' or 'Rain.wav')
        for f in files:
            stem, ext = os.path.splitext(f)
            if ext.lower() in AMBIENT_EXTENSIONS and stem.lower().startswith(target_stem):
                return os.path.join(self.sounds_dir, f)

        return None

    def has_typewriter_sound(self, preset: Union[TypewriterSoundPreset, str]) -> bool:
        """Determines whether a typewriter variation has matching audio files in sounds."""
        if preset == TypewriterSoundPreset.OFF or preset == "Off (Silent)":
            return True

        files = self._get_files_in_sounds_dir()
        effect_files = [f for f in files if os.path.splitext(f)[1].lower() in EFFECT_EXTENSIONS]

        if preset == TypewriterSoundPreset.MANUAL:
            return any(
                f.lower().startswith("manual") or "manual_click" in f.lower() or f.lower().startswith("typewriter")
                for f in effect_files
            )
        elif preset == TypewriterSoundPreset.ELECTRIC:
            return any(
                f.lower().startswith("electric") or "electric_click" in f.lower()
                for f in effect_files
            )
        elif preset == TypewriterSoundPreset.SOFT_MECHANICAL:
            return any(
                f.lower().startswith("soft") or "mechanical" in f.lower()
                for f in effect_files
            )
        elif isinstance(preset, str) and preset.startswith("custom:"):
            fname = preset.split("custom:", 1)[1]
            return os.path.exists(os.path.join(self.sounds_dir, fname))

        return False

    def has_ambient_sound(self, preset: Union[AmbientSoundPreset, str]) -> bool:
        """Determines whether an ambient soundscape variation has a matching audio file in sounds."""
        if preset == AmbientSoundPreset.OFF or preset == "None (Quiet Room)":
            return True

        if isinstance(preset, str) and preset.startswith("custom:"):
            fname = preset.split("custom:", 1)[1]
            return os.path.exists(os.path.join(self.sounds_dir, fname))

        preset_stems = {
            AmbientSoundPreset.RAIN: ["rain"],
            AmbientSoundPreset.LIBRARY: ["library"],
            AmbientSoundPreset.FIREPLACE: ["fireplace", "fire"],
            AmbientSoundPreset.COFFEE_SHOP: ["coffee", "cafe"],
            AmbientSoundPreset.CABIN: ["cabin"],
            AmbientSoundPreset.CAMPING: ["camping", "camp"],
            AmbientSoundPreset.BROWN_NOISE: ["brown_noise", "brown", "whitenoise", "white_noise"],
        }
        stems = preset_stems.get(preset, [])
        for stem in stems:
            if self._find_sound_file(stem):
                return True
        return False

    def get_available_typewriter_presets(self) -> List[Tuple[str, Union[TypewriterSoundPreset, str]]]:
        """Returns a list of (display_label, preset) for only the variations that have sound files."""
        available: List[Tuple[str, Union[TypewriterSoundPreset, str]]] = [
            (TypewriterSoundPreset.OFF.value, TypewriterSoundPreset.OFF)
        ]

        # Check standard presets
        standard_presets = [
            (TypewriterSoundPreset.MANUAL.value, TypewriterSoundPreset.MANUAL),
            (TypewriterSoundPreset.ELECTRIC.value, TypewriterSoundPreset.ELECTRIC),
            (TypewriterSoundPreset.SOFT_MECHANICAL.value, TypewriterSoundPreset.SOFT_MECHANICAL),
        ]
        for label, preset in standard_presets:
            if self.has_typewriter_sound(preset):
                available.append((label, preset))

        # Check for any custom keystroke sound files
        files = self._get_files_in_sounds_dir()
        known_stems = {"bell", "manual", "electric", "soft", "rain", "library", "fire", "coffee", "cabin", "camp", "brown", "white"}
        for f in sorted(files):
            stem, ext = os.path.splitext(f)
            if ext.lower() in EFFECT_EXTENSIONS:
                lower_stem = stem.lower()
                if not any(lower_stem.startswith(k) for k in known_stems):
                    if "click" in lower_stem or "switch" in lower_stem or "type" in lower_stem:
                        label = stem.replace("_", " ").title()
                        available.append((f"{label} (Custom)", f"custom:{f}"))

        return available

    def get_available_ambient_presets(self) -> List[Tuple[str, Union[AmbientSoundPreset, str]]]:
        """Returns a list of (display_label, preset) for only ambient soundscapes that have sound files."""
        available: List[Tuple[str, Union[AmbientSoundPreset, str]]] = [
            (AmbientSoundPreset.OFF.value, AmbientSoundPreset.OFF)
        ]

        standard_presets = [
            (AmbientSoundPreset.RAIN.value, AmbientSoundPreset.RAIN),
            (AmbientSoundPreset.LIBRARY.value, AmbientSoundPreset.LIBRARY),
            (AmbientSoundPreset.FIREPLACE.value, AmbientSoundPreset.FIREPLACE),
            (AmbientSoundPreset.COFFEE_SHOP.value, AmbientSoundPreset.COFFEE_SHOP),
            (AmbientSoundPreset.CABIN.value, AmbientSoundPreset.CABIN),
            (AmbientSoundPreset.CAMPING.value, AmbientSoundPreset.CAMPING),
            (AmbientSoundPreset.BROWN_NOISE.value, AmbientSoundPreset.BROWN_NOISE),
        ]
        for label, preset in standard_presets:
            if self.has_ambient_sound(preset):
                available.append((label, preset))

        # Check for any extra ambient files in sounds directory
        files = self._get_files_in_sounds_dir()
        ignored_stems = {
            "bell", "manual", "electric", "soft", "click", "switch",
            "rain", "library", "fire", "coffee", "cafe", "cabin", "camp", "brown", "white"
        }
        for f in sorted(files):
            stem, ext = os.path.splitext(f)
            if ext.lower() in AMBIENT_EXTENSIONS:
                lower_stem = stem.lower()
                if not any(lower_stem.startswith(k) for k in ignored_stems):
                    label = stem.replace("_", " ").title()
                    available.append((f"{label} (Ambient)", f"custom:{f}"))

        return available

    def _preload_effects(self) -> None:
        """Preloads uncompressed .wav sound effects for zero-latency keystroke playback."""
        files = self._get_files_in_sounds_dir()
        for f in files:
            stem, ext = os.path.splitext(f)
            if ext.lower() in EFFECT_EXTENSIONS:
                file_path = os.path.join(self.sounds_dir, f)
                eff = QSoundEffect(self)
                eff.setSource(QUrl.fromLocalFile(file_path))
                volume_scale = 0.8 if "bell" in stem.lower() else 1.0
                eff.setVolume(self._effects_volume * volume_scale)
                self._effects[stem.lower()] = eff

    def reload_sounds(self) -> None:
        """Re-scans sounds directory to load newly added audio files and refresh presets."""
        self._effects.clear()
        self._preload_effects()

        # Validate current typewriter preset
        if not self.has_typewriter_sound(self.typewriter_preset):
            avail = self.get_available_typewriter_presets()
            self.typewriter_preset = avail[0][1] if avail else TypewriterSoundPreset.OFF

        # Validate current ambient preset
        if not self.has_ambient_sound(self.ambient_preset):
            self.set_ambient_preset(AmbientSoundPreset.OFF)

        self.availablePresetsChanged.emit()

    def _on_sounds_dir_changed(self, path: str) -> None:
        self.reload_sounds()

    def set_typewriter_preset(self, preset: Union[TypewriterSoundPreset, str]) -> None:
        self.typewriter_preset = preset

    def set_ambient_preset(self, preset: Union[AmbientSoundPreset, str]) -> None:
        self.ambient_preset = preset
        if preset in (AmbientSoundPreset.OFF, "None (Quiet Room)", "Off (Silent)", "Off", "off"):
            self._ambient_player.stop()
            return

        # Custom ambient audio file
        if isinstance(preset, str) and preset.startswith("custom:"):
            fname = preset.split("custom:", 1)[1]
            file_path = os.path.join(self.sounds_dir, fname)
            if os.path.exists(file_path):
                self._ambient_player.setSource(QUrl.fromLocalFile(file_path))
                self._ambient_player.play()
            else:
                self._ambient_player.stop()
            return

        preset_stems = {
            AmbientSoundPreset.RAIN: ["rain"],
            AmbientSoundPreset.LIBRARY: ["library"],
            AmbientSoundPreset.FIREPLACE: ["fireplace", "fire"],
            AmbientSoundPreset.COFFEE_SHOP: ["coffee", "cafe"],
            AmbientSoundPreset.CABIN: ["cabin"],
            AmbientSoundPreset.CAMPING: ["camping", "camp"],
            AmbientSoundPreset.BROWN_NOISE: ["brown_noise", "brown", "whitenoise", "white_noise"],
        }
        stems = preset_stems.get(preset, [str(preset)])
        file_path = None
        for stem in stems:
            file_path = self._find_sound_file(stem)
            if file_path:
                break

        if file_path:
            self._ambient_player.setSource(QUrl.fromLocalFile(file_path))
            self._ambient_player.play()
        else:
            self._ambient_player.stop()

    def play_keystroke(self, is_return: bool = False, is_space: bool = False) -> None:
        if self.typewriter_preset == TypewriterSoundPreset.OFF:
            return

        if is_return:
            bell_keys = [k for k in self._effects if "bell" in k]
            if bell_keys:
                self._effects[bell_keys[0]].play()
            return

        # Gather matching sound effects for current preset
        matching_keys = []
        if self.typewriter_preset == TypewriterSoundPreset.MANUAL:
            matching_keys = [k for k in self._effects if "manual" in k]
        elif self.typewriter_preset == TypewriterSoundPreset.ELECTRIC:
            matching_keys = [k for k in self._effects if "electric" in k]
        elif self.typewriter_preset == TypewriterSoundPreset.SOFT_MECHANICAL:
            matching_keys = [k for k in self._effects if "soft" in k or "mechanical" in k]
        elif isinstance(self.typewriter_preset, str) and self.typewriter_preset.startswith("custom:"):
            target = os.path.splitext(self.typewriter_preset.split("custom:", 1)[1])[0].lower()
            matching_keys = [k for k in self._effects if k == target]

        if matching_keys:
            key = random.choice(matching_keys)
            self._effects[key].play()

    def set_ambient_volume(self, volume_percent: int) -> None:
        vol = max(0.0, min(1.0, volume_percent / 100.0))
        self._ambient_volume = vol
        self._ambient_output.setVolume(vol)

    def set_effects_volume(self, volume_percent: int) -> None:
        vol = max(0.0, min(1.0, volume_percent / 100.0))
        self._effects_volume = vol
        for name, eff in self._effects.items():
            eff.setVolume(vol * (0.8 if "bell" in name else 1.0))
