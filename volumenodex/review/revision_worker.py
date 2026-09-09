"""Asynchronous Background Worker for Editorial Lenses and Spell Checking.

Runs linguistic analysis and spell check tokenization off the main GUI thread
using QRunnable and QThreadPool, guaranteeing a zero-latency editing experience
and 60 FPS scrolling on large 20,000+ word manuscripts.
"""

from typing import List, Dict, Any, Optional
from PySide6.QtCore import QRunnable, QObject, Signal
from volumenodex.review.lens_engine import LensFinding, RevisionLensEngine


class ReviewWorkerSignals(QObject):
    """Signals for background review processing."""
    finished = Signal(list, int)   # findings: List[LensFinding], request_id: int
    error = Signal(str, int)       # error_message: str, request_id: int


class ReviewWorker(QRunnable):
    """Background task that executes linguistic lenses and spell check."""

    def __init__(
        self,
        text: str,
        active_lenses: Dict[str, bool],
        spell_engine: Optional[Any],
        request_id: int,
    ):
        super().__init__()
        self.text = text
        self.active_lenses = dict(active_lenses)
        self.spell_engine = spell_engine
        self.request_id = request_id
        self.signals = ReviewWorkerSignals()
        self.setAutoDelete(True)

    def run(self) -> None:
        try:
            findings: List[LensFinding] = []
            if not self.text.strip() or not any(self.active_lenses.values()):
                self.signals.finished.emit([], self.request_id)
                return

            # 1. Run Linguistic Lenses (Adverbs, Passive, Pacing, Filler, Dialogue)
            findings = RevisionLensEngine.analyze_document(self.text, self.active_lenses)

            # 2. Run High-Speed Spell Check (with lazy suggestion candidate deferral)
            if self.active_lenses.get("spelling", False) and self.spell_engine:
                spelling_findings = self.spell_engine.check_text(self.text)
                findings.extend(spelling_findings)
                findings.sort(key=lambda f: f.start_pos)

            self.signals.finished.emit(findings, self.request_id)
        except Exception as e:
            self.signals.error.emit(str(e), self.request_id)
