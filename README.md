# Volumenodex — Word Processing Studio

> **"Where the classical codex meets modern authorial precision."**  
> *A native standalone Windows word processing studio crafted for creative storytellers, non-fiction authors, and academic researchers.*

---

## ✨ Features at a Glance

### 1. Luxury Physical Print Fidelity
* **Discrete Multi-Sheet Paper Canvas**: True physical paper sheets with realistic ambient occlusion, directional drop shadows, and 36px desk gutters.
* **Procedural Paper Textures**: High-fidelity tactile paper grain overlays (*Fine Linen, Laid Cotton, Vintage Parchment, Japanese Washi, Minimalist Tooth*) with opacity and dark paper contrast sliders.
* **Prepress Publisher Crop Marks & Page Numbering**: Real-time page boundary slicing with running centered footers.
* **Interactive Top Ruler**: Millimeter and inch ruler synchronized with margins and canvas scrolling.

### 2. Modern Fluent Ribbon Bar & Precision Typography
* **Resolution-Independent Vector Icons**: Crisp QPainterPath vector geometry at any DPI scaling.
* **Complete System Font Integration**: Automatically enumerates all installed and downloaded Windows system fonts with curated book fonts prioritized and searchable text.
* **Extreme Font Scale**: Point size dropdown extends up to 200 pt with direct numeric input.
* **Dedicated Paste Plain**: Always-visible "Paste without Formatting" button (`Ctrl+Shift+V`) alongside standard paste.
* **Expanded Heading Hierarchy**: Native support for Title, Heading 1, 2, 3, 4, 5, and Blockquote.
* **Custom Style Creator (`+ Save Style`)**: Capture a formatting snapshot (font, size, slant, colors, alignment, spacing) and dynamically generate a new button on your ribbon palette.
* **Print Preview**: Interactive high-resolution print preview dialog (`QPrintPreviewDialog`) accessible via File menu, Ribbon quick access, and `Ctrl+Shift+P`.
* **Dynamic Autoscrolling**: Keep the active typing line comfortably in view at all times when Enter is struck or when text naturally wraps across lines.

### 3. Native JPEG XL (.JXL) & Advanced Image Suite
* **Native .JXL First-Class Support**: JPEG XL (`.jxl`) is the **primary and preferred** image format across all dialogs, insertions, and operations, providing unmatched fidelity and compression.
* **Visual Cropping Suite**: Interactive crop dialog (`ImageCropDialog`) featuring draggable handles, rule-of-thirds grid, aspect ratio locks, and presets (1:1, 4:3, 16:9, Freeform).
* **Precision Resizing Suite**: Modal resize dialog (`ImageResizeDialog`) with proportional aspect ratio lock, exact pixel/inch dimensions, and one-click page-width presets (25%, 50%, 75%, 100%).
* **Flexible Placement & Alignment**: Full support for in-line text flow and block alignment (Align Left, Center, Right).
* **Lossless Image Copy & Paste**: Full clipboard integration—copy or cut images directly from the manuscript and paste images from the system clipboard or local file paths without placeholder characters.

### 4. Baked-In Clipart Library & Wikimedia Autoexpansion
* **20,000+ Baked-in Illustrations**: Packaged with over 20,500 curated, compressed, public domain `.jxl` illustrations directly in the program library (`assets/clipart/`).
* **Deep Metadata Search**: High-performance local search scanning image titles, EXIF descriptions, artist data, comments, and Windows Explorer `XPKeywords` (tag 40094).
* **Wikimedia Commons Autoexpansion**: Automatically triggers when local search matches are sparse (< 3) or on demand via *"Not what you're looking for? Load more!"*, progressively expanding your local library.
* **License & Attribution Safeguards**: Filter illustrations by Public Domain/CC0, CC-BY, and CC-BY-SA, with automatic italicized attribution insertion for CC licenses.
* **Storage Protection Guard**: Configurable Hard Drive safety limits (in KB, MB, GB, TB) with warning alerts and direct links to Settings.

### 5. Specialized Authoring Modes
* **Creative Fiction**: Worldbuilding Codex, chapter navigator, creative pet companion tips, scene cards.
* **General Non-Fiction & Essays**: Expository outline, evidence and argument structure, clarity-focused writing companion.
* **Academic & Research**: Replaces Story Codex with a comprehensive **Citation Generator** (APA 7th, MLA 9th, Chicago 17th, IEEE, Harvard), one-click in-text citations, and bibliography generation.

### 6. Narrative Architecture & Story Codex
* **Chapter Outline Navigator**: Real-time manuscript outline scanner with word count metrics, status tracking, and one-click chapter jumping.
* **Character & Worldbuilding Codex**: Expandable dossiers for cast members and lore categories with **Live Mention Detection** (cards illuminate when typed in the manuscript).
* **Hybrid Corkboard Studio**: Tactile cork board with synchronized two-way scene cards that automatically rearrange manuscript text when reordered.

### 7. Proofreading Lenses & Spell Check
* **Non-Destructive Highlighter Washes**: Pastel highlighter washes and wavy red squiggles rendered via non-destructive paint contexts without polluting saved `.docx` files.
* **Spell Check & Author Dictionary**: Frequency-ranked candidate suggestions, right-click context menu, permanent user dictionary, and automatic Story Codex whitelisting.
* **Five Specialized Revision Lenses**: Adverb detector, Passive Voice hunter, Cliche lens, Filler word detector, and Pacing/rhythm visualizer.

### 8. Acoustic Atmosphere & Scribe Companion
* **Tactile Typing Acoustics**: Vintage mechanical typewriter, IBM Model M, modern laptop switch audio feedback.
* **Ambient Soundscapes**: Library rain, coffeehouse hearth, midnight wind, forest stream.
* **Corvus the Raven (Writing Pet)**: Non-intrusive desktop companion dock offering editorial insight, sprint tracking, and break reminders.

### 9. Offline Writer's Reference Compendium
* **Curated Reference Encyclopedia**: Over 260 encyclopedic articles across 12 disciplines (Aviation, Nautical, Survival, Poisons & Medicine, Warfare, Storytelling, and more) accessible directly inside the editor without an internet connection.
* **Instant In-Text Insertion**: One-click copying and direct insertion of reference points, technical nomenclature, and historical details directly into your manuscript.
* **Personal Custom Lore**: Seamlessly extend the offline encyclopedia with your own custom worldbuilding dossiers, notes, and quick-fact properties.

---

## 🚀 Quickstart

### Prerequisites
* Windows 10 or 11 (64-bit)
* Python 3.10, 3.11, 3.12, 3.13, or 3.14

### Installation

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
   *Alternatively, double-click `run_volumenodex.bat`.*

---

## 📦 Packaging & Building

### Standalone Windows Executable
To package Volumenodex as a standalone Windows executable with all clipart and dependencies bundled:
```bash
pyinstaller Volumenodex.spec
```

---

## 📄 License & Status

**Version**: `2.0.0`  
**Status**: Production Release  
Copyright © 2026. All rights reserved.
