"""Real-time editorial insight engine, repetition detector, and break timer."""

import re
import random
from typing import Optional, Set
from PySide6.QtCore import QObject, Signal, QTimer
from volumenodex.core.document_model import DocumentMode
from volumenodex.pet.pet_model import PetProfile, PetMood, DEFAULT_PETS


IGNORED_WORDS: Set[str] = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "as", "is", "was", "were", "are", "be",
    "been", "being", "have", "has", "had", "do", "does", "did", "i", "you",
    "he", "she", "it", "we", "they", "my", "your", "his", "her", "its",
    "our", "their", "this", "that", "these", "those", "me", "him", "them",
    "us", "so", "if", "up", "out", "no", "not", "too", "into", "over"
}


class InsightEngine(QObject):
    """Monitors live manuscript typing to provide real-time editorial insights and break nudges."""

    messageReady = Signal(str, PetMood)  # text, mood
    moodChanged = Signal(PetMood)

    ACADEMIC_PROMPTS = [
        "Examine your hedging: is 'the evidence suggests' more appropriate than 'this definitively proves'?",
        "Check citation grounding: does this assertion require an empirical reference or attribution in the Citations drawer?",
        "Review your literature synthesis: are you contrasting conflicting scholarly perspectives or summarizing them in isolation?",
        "Clarify methodological scope: have you stated the boundary conditions and limitations of this finding?",
        "Strengthen topic sentences: does the first sentence of this paragraph directly advance the core research question?",
        "Eliminate colloquial crutches: replace informal expressions with precise scholarly terminology.",
        "Check acronym definitions: ensure specialized acronyms are spelled out in full upon first mention.",
    ]

    NONFICTION_PROMPTS = [
        "What counterargument or common misconception might a skeptical reader raise at this exact juncture?",
        "Anchor this abstract principle with a vivid real-world example, case study, or concrete statistic.",
        "Review your transitions: does the logical momentum carry naturally from the preceding paragraph?",
        "Check clarity: could this key point be understood immediately by an intelligent non-specialist?",
        "Highlight the stakes: why does this concept matter beyond purely theoretical interest?",
        "Trim throat-clearing phrasing: cut introductory filler and start directly with the compelling insight.",
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.active_pet: PetProfile = DEFAULT_PETS["corvus"]
        self.document_mode: DocumentMode = DocumentMode.CREATIVE_FICTION
        self._current_mood: PetMood = PetMood.IDLE

        self._last_word_count = 0
        self._achieved_milestones = set()
        self._last_warned_word = None
        self._last_warned_time = 0

        # Activity / Sleep timer (transitions to sleeping after 45s of silence)
        self._activity_timer = QTimer(self)
        self._activity_timer.setInterval(45000)
        self._activity_timer.timeout.connect(self._on_idle_timeout)

        # Break / Wellness Timer
        self._break_timer = QTimer(self)
        self._restart_break_timer()
        self._break_timer.timeout.connect(self._on_break_timer_fired)

    @property
    def current_mood(self) -> PetMood:
        return self._current_mood

    def set_pet(self, pet: PetProfile) -> None:
        self.active_pet = pet
        self._restart_break_timer()
        self._current_mood = PetMood.IDLE
        self.moodChanged.emit(PetMood.IDLE)
        self.messageReady.emit(
            f"Greetings, scribe. I am {pet.name}, {pet.species_title}.",
            PetMood.IDLE
        )

    def set_document_mode(self, mode: DocumentMode) -> None:
        self.document_mode = mode
        if mode == DocumentMode.ACADEMIC:
            self.messageReady.emit(
                "🎓 <b>Academic Research Mode Active.</b><br>I will assist with scholarly precision, hedging, and citation rigor.",
                PetMood.IDLE
            )
        elif mode == DocumentMode.NON_FICTION:
            self.messageReady.emit(
                "📝 <b>Non-Fiction Mode Active.</b><br>I will monitor argument structure, clarity, and expository flow.",
                PetMood.IDLE
            )
        else:
            self.messageReady.emit(
                "🪶 <b>Creative Fiction Mode Active.</b><br>Let us craft vivid prose, narrative tension, and unforgettable characters.",
                PetMood.IDLE
            )

    def set_break_timer_enabled(self, enabled: bool) -> None:
        self.active_pet.break_timer_enabled = enabled
        if enabled:
            self._restart_break_timer()
        else:
            self._break_timer.stop()

    def set_break_interval(self, minutes: int) -> None:
        self.active_pet.break_interval_minutes = max(1, minutes)
        self._restart_break_timer()

    def _restart_break_timer(self) -> None:
        if self.active_pet.break_timer_enabled:
            ms = self.active_pet.break_interval_minutes * 60 * 1000
            self._break_timer.start(ms)
        else:
            self._break_timer.stop()

    def on_text_changed(self, full_text: str, cursor_position: int) -> None:
        """Called on keystroke to evaluate repetition, activity, and milestones."""
        self._activity_timer.start()  # Reset idle timer
        if self._current_mood != PetMood.WRITING:
            self._current_mood = PetMood.WRITING
            self.moodChanged.emit(PetMood.WRITING)

        # 1. Milestone Check
        words = full_text.split()
        word_count = len(words)
        self._check_milestones(word_count)
        self._last_word_count = word_count

        # 2. Real-time Word Repetition & Tone in active sentence
        self._inspect_active_sentence(full_text, cursor_position)

    def _on_idle_timeout(self) -> None:
        self._current_mood = PetMood.SLEEPING
        self.moodChanged.emit(PetMood.SLEEPING)

    def _on_break_timer_fired(self) -> None:
        if not self.active_pet.break_timer_enabled:
            return
        self._current_mood = PetMood.NUDGING
        self.moodChanged.emit(PetMood.NUDGING)
        quote = random.choice(self.active_pet.break_quotes) if self.active_pet.break_quotes else "Time for a gentle stretch and a drink of water!"
        self.messageReady.emit(quote, PetMood.NUDGING)

    def _check_milestones(self, count: int) -> None:
        milestones = [100, 250, 500, 1000, 1500, 2000, 3000, 5000, 10000]
        for m in milestones:
            if count >= m and m not in self._achieved_milestones and (m <= count < m + 15):
                self._achieved_milestones.add(m)
                if self.document_mode == DocumentMode.ACADEMIC:
                    cheer = f"Outstanding academic output. Another {m:,} words of rigorous scholarship documented!"
                elif self.document_mode == DocumentMode.NON_FICTION:
                    cheer = f"Compelling clarity! Another {m:,} words of cogent exposition formulated."
                else:
                    cheer = random.choice(self.active_pet.milestone_quotes) if self.active_pet.milestone_quotes else f"Congratulations on reaching {m} words!"
                self.messageReady.emit(f"🎉 <b>{m:,} Words Reached!</b><br>{cheer}", PetMood.CELEBRATING)
                break

    def _inspect_active_sentence(self, full_text: str, cursor_pos: int) -> None:
        """Inspects sentence around cursor to detect duplicate words and tone cues."""
        if not full_text:
            return

        # Find sentence boundaries (. ! ?)
        start = max(0, cursor_pos - 150)
        end = min(len(full_text), cursor_pos + 50)
        snippet = full_text[start:end]

        # Extract last sentence before cursor
        sentences = re.split(r"[.!?\n]+", snippet)
        if not sentences:
            return

        current_sentence = sentences[-1].strip().lower()
        tokens = re.findall(r"\b[a-z]{4,}\b", current_sentence)

        # Academic absolute check
        if self.document_mode == DocumentMode.ACADEMIC:
            academic_absolutes = {"obviously", "clearly", "undoubtedly", "irrefutably", "indisputably"}
            for token in tokens:
                if token in academic_absolutes and token != self._last_warned_word:
                    self._last_warned_word = token
                    self.messageReady.emit(
                        f"🎓 <b>Scholarly Tip:</b> Absolute terms like <b>'{token}'</b> can attract peer-review skepticism. "
                        "Consider academic hedging (e.g. 'the findings indicate', 'substantially').",
                        PetMood.ALERT
                    )
                    return

        # Count frequencies of non-stop words
        counts = {}
        for token in tokens:
            if token not in IGNORED_WORDS:
                counts[token] = counts.get(token, 0) + 1

        for word, freq in counts.items():
            if freq >= 2 and word != self._last_warned_word:
                self._last_warned_word = word
                # Real-time insight requested by user:
                # "Hey, you've used 'because' twice in this sentence, maybe you want to pick a different word?"
                advice = (
                    f"Hey, you've used <b>'{word}'</b> twice in this sentence. "
                    "Maybe you'd like to pick a different word or rephrase?"
                )
                self.messageReady.emit(advice, PetMood.ALERT)
                break

    def trigger_creative_spark(self) -> None:
        """Gives an immediate creative or scholarly spark prompt based on active document mode."""
        if self.document_mode == DocumentMode.ACADEMIC:
            prompt = random.choice(self.ACADEMIC_PROMPTS)
            title = "Scholarly Guidance"
        elif self.document_mode == DocumentMode.NON_FICTION:
            prompt = random.choice(self.NONFICTION_PROMPTS)
            title = "Expository Guidance"
        else:
            if self.active_pet.prompt_ideas:
                prompt = random.choice(self.active_pet.prompt_ideas)
            else:
                prompt = "What hidden truth is someone in this scene desperately trying not to say aloud?"
            title = "Creative Spark"

        self.messageReady.emit(f"💡 <b>{title}:</b><br>{prompt}", PetMood.ALERT)

    def trigger_idle_quote(self) -> None:
        if self.active_pet.idle_quotes:
            quote = random.choice(self.active_pet.idle_quotes)
            self.messageReady.emit(quote, PetMood.IDLE)
