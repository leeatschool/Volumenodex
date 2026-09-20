# Volumenodex — Word Processing Studio

> **"Where the classical codex meets modern authorial precision."**  
> *A native standalone word processing studio crafted for creative storytellers, non-fiction authors, and academic researchers.*

---

## ✨ Features at a Glance

### 1. Zero-Lag Launch Architecture & Visual Polish
* **Instant Branded Splash Screen**: Launches with a sleek dark slate splash screen (`QSplashScreen`) featuring application branding and real-time initialization status, providing immediate visual feedback upon launch with zero perceived delay.
* **Lazy Multi-Editor Construction**: Dual-screen split canvas is instantiated on demand, halving initial startup construction time and memory overhead.
* **Deferred Sensory Audio Engine**: Keeps Qt Multimedia / FFmpeg subsystems uninitialized until ambient soundscapes are selected, eliminating background startup latency.
* **Native Taskbar & Window Icon Reliability**: Synchronous native Win32 `WM_SETICON` binding with `LoadImageW` guarantees crisp 16x16 and multi-resolution taskbar rendering immediately upon launch without generic placeholder delays.

### 2. Luxury Physical Print Fidelity
* **Discrete Multi-Sheet Paper Canvas**: True physical paper sheets with realistic ambient occlusion, directional drop shadows, and 36px desk gutters.
* **Procedural Paper Textures**: High-fidelity tactile paper grain overlays (*Fine Linen, Laid Cotton, Vintage Parchment, Japanese Washi, Minimalist Tooth*) with opacity and dark paper contrast sliders.
* **Prepress Publisher Crop Marks & Page Numbering**: Real-time page boundary slicing with running centered footers.
* **Interactive Top Ruler**: Millimeter and inch ruler synchronized with margins and canvas scrolling.

### 3. Modern Fluent Ribbon Bar & Precision Typography
* **Resolution-Independent Vector Icons**: Crisp QPainterPath vector geometry at any DPI scaling.
* **Complete System Font Integration**: Automatically enumerates all installed and downloaded system fonts with curated book fonts prioritized and searchable text.
* **Extreme Font Scale**: Point size dropdown extends up to 200 pt with direct numeric input.
* **Dedicated Paste Plain**: Always-visible "Paste without Formatting" button (`Ctrl+Shift+V`) alongside standard paste.
* **Expanded Heading Hierarchy**: Native support for Title, Heading 1, 2, 3, 4, 5, and Blockquote.
* **Custom Style Creator (`+ Save Style`)**: Capture a formatting snapshot (font, size, slant, colors, alignment, spacing) and dynamically generate a new button on your ribbon palette.
* **Print Preview**: Interactive high-resolution print preview dialog (`QPrintPreviewDialog`) accessible via File menu, Ribbon quick access, and `Ctrl+Shift+P`.
* **Dynamic Autoscrolling**: Keep the active typing line comfortably in view at all times when Enter is struck or when text naturally wraps across lines.

### 4. Native JPEG XL (.JXL) & Advanced Image Suite
* **Native .JXL First-Class Support**: JPEG XL (`.jxl`) is the **primary and preferred** image format across all dialogs, insertions, and operations, providing unmatched fidelity and compression.
* **Visual Cropping Suite**: Interactive crop dialog (`ImageCropDialog`) featuring draggable handles, rule-of-thirds grid, aspect ratio locks, and presets (1:1, 4:3, 16:9, Freeform).
* **Precision Resizing Suite**: Modal resize dialog (`ImageResizeDialog`) with proportional aspect ratio lock, exact pixel/inch dimensions, and one-click page-width presets (25%, 50%, 75%, 100%).
* **Flexible Placement & Alignment**: Full support for in-line text flow and block alignment (Align Left, Center, Right).
* **Lossless Image Copy & Paste**: Full clipboard integration—copy or cut images directly from the manuscript and paste images from the system clipboard or local file paths without placeholder characters.

### 5. Baked-In Clipart Library & Zero-Decode Search Engine
* **20,500+ Baked-in Illustrations**: Packaged with over 20,580 curated, compressed, public domain `.jxl` illustrations directly in the program library (`assets/clipart/`).
* **Instant In-Memory Metadata Catalog**: Utilizes a pre-compiled JSON catalog (`clipart_index.json`) that loads 20,580+ entries into a lightning-fast lookup structure in ~60ms.
* **Zero-Decode on Initial Open**: The Clip Art interface opens instantly without decoding any images up-front. Users are greeted by an inviting search hub featuring quick-search chips (*Animals, Borders, Vintage, Nature, Ornaments, Frames, Music*) or a *"Browse All"* option.
* **On-Demand Image Decoding**: Thumbnails and photos are decoded solely for matching search queries, preventing UI freezes and keeping memory consumption lean.
* **Wikimedia Commons Autoexpansion**: Progressively expand your collection with live Wikimedia Commons downloads when local matches are sparse, complete with multi-license filtering and automated italicized author attributions.
* **Storage Protection Guard**: Configurable hard drive safety limits (KB, MB, GB, TB) with warning alerts and direct links to Settings.

### 6. Specialized Authoring Modes
* **Creative Fiction**: Worldbuilding Codex, chapter navigator, creative pet companion tips, scene cards.
* **General Non-Fiction & Essays**: Expository outline, evidence and argument structure, clarity-focused writing companion.
* **Academic & Research**: Replaces Story Codex with a comprehensive **Citation Generator** (APA 7th, MLA 9th, Chicago 17th, IEEE, Harvard), one-click in-text citations, and bibliography generation.

### 7. Narrative Architecture & Story Codex
* **Chapter Outline Navigator**: Real-time manuscript outline scanner with word count metrics, status tracking, and one-click chapter jumping.
* **Character & Worldbuilding Codex**: Expandable dossiers for cast members and lore categories with **Live Mention Detection** (cards illuminate when typed in the manuscript).
* **Hybrid Corkboard Studio**: Tactile cork board with synchronized two-way scene cards that automatically rearrange manuscript text when reordered.

### 8. Proofreading Lenses & Spell Check
* **Non-Destructive Highlighter Washes**: Pastel highlighter washes and wavy red squiggles rendered via non-destructive paint contexts without polluting saved `.docx` files.
* **Spell Check & Author Dictionary**: Frequency-ranked candidate suggestions, right-click context menu, permanent user dictionary, and automatic Story Codex whitelisting.
* **Five Specialized Revision Lenses**: Adverb detector, Passive Voice hunter, Cliche lens, Filler word detector, and Pacing/rhythm visualizer.

### 9. Acoustic Atmosphere & Scribe Companion
* **Tactile Typing Acoustics**: Vintage mechanical typewriter, IBM Model M, modern laptop switch audio feedback.
* **Ambient Soundscapes**: Library rain, coffeehouse hearth, midnight wind, forest stream.
* **Corvus the Raven (Writing Pet)**: Non-intrusive desktop companion dock offering editorial insight, sprint tracking, and break reminders.

### 10. Offline Writer's Reference Compendium
* **Curated Reference Encyclopedia**: Over 260 encyclopedic articles across 12 disciplines (Aviation, Nautical, Survival, Poisons & Medicine, Warfare, Storytelling, and more) accessible directly inside the editor without an internet connection.
* **Instant In-Text Insertion**: One-click copying and direct insertion of reference points, technical nomenclature, and historical details directly into your manuscript.
* **Personal Custom Lore**: Seamlessly extend the offline encyclopedia with your own custom worldbuilding dossiers, notes, and quick-fact properties.

---

## 🚀 Cross-Platform Downloads & Installation

Pre-compiled standalone binary packages for each operating system are available on the [Releases Page](https://github.com/leeatschool/Volumenodex/releases):

| Platform | Package | Description |
| :--- | :--- | :--- |
| **Windows x64** | `Volumenodex-v2.0.0-Windows-x64.zip` | Standalone portable zip containing `Volumenodex.exe` and full clipart library |
| **macOS** | `Volumenodex-v2.0.0-macOS.dmg` / `.zip` | Drag-and-drop macOS universal application bundle (`Volumenodex.app`) |
| **Linux x86_64** | `Volumenodex-v2.0.0-Linux-x86_64.tar.gz` | Portable distribution with `run.sh` script and desktop entry integration |

---

## 💻 Developer Quickstart

### Prerequisites
* Python 3.10, 3.11, 3.12, 3.13, or 3.14
* PySide6, Pillow, pillow-jxl-plugin, python-docx, pyspellchecker

### Running from Source

1. **Clone the repository**:
   ```bash
   git clone https://github.com/leeatschool/Volumenodex.git
   cd Volumenodex
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Launch the Studio**:
   ```bash
   python main.py
   ```
   *On Windows, you can also double-click `run_volumenodex.bat`.*

### Running the Test Suite
Volumenodex includes an extensive automated test suite covering all authoring features, performance benchmarks, and security safeguards:
```bash
pytest tests/ -v
```

---

## 📦 Building Standalone Distributions

### Building Windows Standalone
```bash
pyinstaller Volumenodex.spec
```

### Cross-Platform CI/CD Pipeline
Volumenodex utilizes a GitHub Actions automated workflow (`.github/workflows/build-release.yml`) that automatically builds, tests, packages, and attaches Linux and macOS release artifacts whenever a release tag (`v*`) is pushed.

---

## 📄 License & Status

**Version**: `2.0.0`  
**Status**: Production Release  
Copyright © 2026. All rights reserved.
