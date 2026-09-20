"""Spell Check Engine with custom user dictionary and Story Codex whitelisting.

Integrates fast, frequency-ranked English spelling analysis, personalized author
dictionaries, right-click correction suggestions, and automatic whitelisting
for all narrative characters and lore terms created in the Codex.
"""

import os
import json
import re
import threading
from typing import List, Set, Dict, Optional, Tuple
from PySide6.QtGui import QColor

from volumenodex.review.lens_engine import LensFinding

try:
    from spellchecker import SpellChecker
    PYSPELLCHECKER_AVAILABLE = True
except ImportError:
    PYSPELLCHECKER_AVAILABLE = False


class SpellCheckEngine:
    """Manages spell check verification, suggestions, and custom author dictionaries."""

    DEFAULT_DICT_PATH = os.path.join(os.path.expanduser("~"), ".volumenodex", "user_dictionary.json")

    COLOR_SPELLING = QColor(247, 118, 142, 50)  # Soft red wash

    def __init__(self, dict_path: Optional[str] = None):
        self.dict_path = dict_path or self.DEFAULT_DICT_PATH
        self._lock = threading.RLock()
        self.user_words: Set[str] = set()
        self.session_ignored: Set[str] = set()
        self.story_whitelist: Set[str] = set()
        self._suggestion_cache: Dict[str, List[str]] = {}

        # Lazy spellchecker backend to guarantee sub-second startup
        self._spell: Optional[SpellChecker] = None
        self._load_user_dictionary()

    @property
    def spell(self) -> Optional[SpellChecker]:
        """Lazily instantiates the underlying SpellChecker dictionary on demand."""
        if self._spell is None and PYSPELLCHECKER_AVAILABLE:
            with self._lock:
                if self._spell is None:
                    try:
                        loaded = SpellChecker(language="en")
                        if self.user_words:
                            loaded.word_frequency.load_words(list(self.user_words))
                        self._spell = loaded
                    except Exception as e:
                        print(f"Notice: Could not load spellchecker dictionary: {e}")
                        self._spell = None
        return self._spell

    @spell.setter
    def spell(self, val: Optional[SpellChecker]) -> None:
        with self._lock:
            self._spell = val

    def _load_user_dictionary(self) -> None:
        """Loads custom author words from persistence."""
        try:
            if os.path.exists(self.dict_path):
                with open(self.dict_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        self.user_words = {w.lower().strip() for w in data if w.strip()}
                        if self._spell is not None:
                            self._spell.word_frequency.load_words(list(self.user_words))
        except Exception as e:
            print(f"Notice: Could not load user dictionary: {e}")

    def _save_user_dictionary(self) -> None:
        """Persists custom author words."""
        try:
            os.makedirs(os.path.dirname(self.dict_path), exist_ok=True)
            with open(self.dict_path, "w", encoding="utf-8") as f:
                json.dump(sorted(list(self.user_words)), f, indent=2)
        except Exception as e:
            print(f"Notice: Could not save user dictionary: {e}")

    def add_to_user_dictionary(self, word: str) -> None:
        """Permanently whitelists a word for this user."""
        w_clean = word.lower().strip()
        if not w_clean:
            return
        with self._lock:
            if w_clean not in self.user_words:
                self.user_words.add(w_clean)
                self._suggestion_cache.pop(w_clean, None)
                if self.spell:
                    self.spell.word_frequency.load_words([w_clean])
                self._save_user_dictionary()

    def remove_from_user_dictionary(self, word: str) -> None:
        w_clean = word.lower().strip()
        with self._lock:
            if w_clean in self.user_words:
                self.user_words.remove(w_clean)
                self._suggestion_cache.pop(w_clean, None)
                self._save_user_dictionary()

    def ignore_word_for_session(self, word: str) -> None:
        """Temporarily ignores a word for the current editing session."""
        w_clean = word.lower().strip()
        if w_clean:
            with self._lock:
                self.session_ignored.add(w_clean)
                self._suggestion_cache.pop(w_clean, None)

    def sync_story_codex_whitelist(self, codex_manager) -> None:
        """Whitelists all character names, aliases, and worldbuilding lore terms."""
        if not codex_manager:
            return

        new_whitelist: Set[str] = set()

        # Add characters and aliases
        for char in codex_manager.characters:
            for token in re.findall(r"\b[a-zA-Z]+\b", char.name):
                new_whitelist.add(token.lower())
            for alias in char.aliases:
                for token in re.findall(r"\b[a-zA-Z]+\b", alias):
                    new_whitelist.add(token.lower())

        # Add lore titles and aliases
        for lore in codex_manager.lore_entries:
            for token in re.findall(r"\b[a-zA-Z]+\b", lore.title):
                new_whitelist.add(token.lower())
            for alias in lore.aliases:
                for token in re.findall(r"\b[a-zA-Z]+\b", alias):
                    new_whitelist.add(token.lower())

        with self._lock:
            self.story_whitelist = new_whitelist
            if self.spell and new_whitelist:
                self.spell.word_frequency.load_words(list(new_whitelist))

    def get_suggestions(self, word: str, limit: int = 5) -> List[str]:
        """Generates top candidate replacements for a misspelled word with caching."""
        if not self.spell or not word:
            return []
        w_lower = word.lower().strip()
        with self._lock:
            if w_lower in self._suggestion_cache:
                candidates = self._suggestion_cache[w_lower]
            else:
                try:
                    candidates = list(self.spell.candidates(w_lower) or [])
                except Exception:
                    candidates = []
                self._suggestion_cache[w_lower] = candidates

        # Preserve original capitalization if input was capitalized
        if word.istitle():
            res = [c.capitalize() for c in candidates]
        elif word.isupper():
            res = [c.upper() for c in candidates]
        else:
            res = list(candidates)
        return res[:limit]

    def has_cached_suggestions(self, word: str) -> bool:
        """Returns True if suggestion candidates have already been calculated and cached."""
        if not word:
            return False
        w_lower = word.lower().strip()
        with self._lock:
            return w_lower in self._suggestion_cache

    def is_correct(self, word: str) -> bool:
        """Returns True if the word is spelled correctly or whitelisted."""
        if not word or len(word) <= 1:
            return True
        w_lower = word.lower().strip()
        with self._lock:
            if w_lower in self.user_words or w_lower in self.session_ignored or w_lower in self.story_whitelist:
                return True
            if not self.spell:
                return True
            return w_lower not in self.spell.unknown([w_lower])

    def check_word(self, word: str) -> bool:
        """Returns True if the word is spelled correctly or whitelisted."""
        return self.is_correct(word)

    def check_text(self, text: str) -> List[LensFinding]:
        """Scans text and returns structured findings for any spelling errors.
        
        Runs in milliseconds by batch-checking unknown tokens and deferring Levenshtein
        candidate computations until on-demand inspection or right-click.
        """
        if not text or not self.spell:
            return []

        with self._lock:
            combined_whitelist = self.user_words | self.session_ignored | self.story_whitelist

        findings: List[LensFinding] = []

        # Tokenize words with their exact character offsets
        pattern = re.compile(r"\b[a-zA-Z]+(?:'[a-zA-Z]+)?\b")

        words_to_check: List[Tuple[str, int, int]] = []
        unique_tokens: Set[str] = set()

        for match in pattern.finditer(text):
            raw_word = match.group(0)
            # Skip single letter words like 'a', 'I'
            if len(raw_word) <= 1:
                continue

            w_lower = raw_word.lower()

            # Check whitelists
            if w_lower in combined_whitelist:
                continue

            words_to_check.append((raw_word, match.start(), match.end()))
            unique_tokens.add(w_lower)

        if not unique_tokens:
            return []

        # High-speed batch lookup of unknown words in frequency dictionary
        with self._lock:
            misspelled_set = self.spell.unknown(list(unique_tokens))

        if not misspelled_set:
            return []

        for raw_word, start, end in words_to_check:
            w_lower = raw_word.lower()
            if w_lower in misspelled_set:
                # Note: suggestions are lazily resolved on demand when right-clicked or inspected
                s = max(0, start - 30)
                e = min(len(text), end + 30)
                prefix = "..." if s > 0 else ""
                suffix = "..." if e < len(text) else ""
                snippet = f"{prefix}{text[s:start]}[{raw_word}]{text[end:e]}{suffix}".replace("\n", " ")

                findings.append(LensFinding(
                    lens_type="spelling",
                    start_pos=start,
                    end_pos=end,
                    text=raw_word,
                    color=self.COLOR_SPELLING,
                    message=f"Possible misspelling: '{raw_word}'",
                    suggestions=[],  # Lazily resolved
                    context_snippet=snippet,
                ))

        return findings
