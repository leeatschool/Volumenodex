# Volumenodex Sound Samples Directory

Place your custom audio files in this directory (`Volumenodex/assets/sounds/`).

### Typewriter Keystroke Samples (`.wav` recommended for zero latency)
Qt's low-latency `QSoundEffect` engine uses uncompressed `.wav` files (16-bit PCM, 44.1kHz or 48kHz, ~20ms–50ms):
- `manual_click1.wav` — Primary mechanical typewriter key strike
- `manual_click2.wav` — Subtle variation keystroke
- `manual_click3.wav` — Subtle variation keystroke
- `electric_click.wav` — Crisp electric typewriter sound
- `soft_mechanical.wav` — Muted soft mechanical switch click
- `bell.wav` — Classic carriage return bell chime (plays on Enter / Return)

*Note: Default synthesized mechanical clicks and bell chime are bundled so typewriter audio works immediately. Dropping your own `.wav` files into this directory overrides them with your custom recordings.*

### Ambient Soundscapes (`.mp3`, `.wav`, or `.ogg`)
Continuous looping background soundscapes played via `QMediaPlayer`:
- `rain.mp3` (or `.wav`) — Gentle rain on windowpane
- `library.mp3` (or `.wav`) — Quiet library atmosphere
- `fireplace.mp3` (or `.wav`) — Warm crackling fireside
- `coffee_shop.mp3` (or `.wav`) — Cozy cafe murmurs and coffee cups
- `cabin.mp3` (or `.wav`) — Cabin in the woods / gentle wind
- `camping.mp3` (or `.wav`) — Camping under the stars / crickets & night breeze
- `brown_noise.mp3` (or `.wav`) — Deep brown noise for intense focus (bundled default active)
