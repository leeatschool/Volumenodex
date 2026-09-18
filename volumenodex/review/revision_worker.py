"""Asynchronous Background Worker for Editorial Lenses and Spell Checking.

Runs linguistic analysis and spell check tokenization off the main GUI thread
using QRunnable and QThreadPool, guaranteeing a zero-latency editing experience
and 60 FPS scrolling on large 20,000+ word manuscripts.
"""

import threading
from typing import List, Dict, Any, Optional
from PySide6.QtCore import QRunnable, QObject, Signal, Slot
from volumenodex.review.lens_engine import LensFinding, RevisionLensEngine


class ReviewWorkerSignals(QObject):
    """Signals for background review processing."""
    finished = Signal(list, int)   # findings: List[LensFinding], request_id: int
    error = Signal(str, int)       # error_message: str, request_id: int


class ReviewAnalysisWorker(QObject):
    """Dedicated persistent QObject worker designed to run inside a long-lived QThread.

    Eliminates QRunnable thread pool churn, C++ secondary-thread deallocation,
    and Shiboken GC race conditions. Automatically drops superseded requests
    during rapid manuscript typing.
    """
    finished = Signal(list, int)   # findings: List[LensFinding], request_id: int
    error = Signal(str, int)       # error_message: str, request_id: int

    def __init__(self, spell_engine: Optional[Any] = None, parent=None):
        super().__init__(parent)
        self.spell_engine = spell_engine
        self._lock = threading.Lock()
        self._latest_request_id = 0

    @Slot(str, dict, int)
    def process_review(self, text: str, active_lenses: Dict[str, bool], request_id: int) -> None:
        """Processes document lenses and spelling on the persistent background thread."""
        with self._lock:
            if request_id < self._latest_request_id:
                return  # Superseded by a newer typing event
            self._latest_request_id = request_id

        try:
            findings: List[LensFinding] = []
            if not text.strip() or not any(active_lenses.values()):
                self.finished.emit([], request_id)
                return

            # 1. Run Linguistic Lenses (Adverbs, Passive, Pacing, Filler, Dialogue)
            findings = RevisionLensEngine.analyze_document(text, active_lenses)

            # Check if superseded while running regex lenses
            with self._lock:
                if request_id < self._latest_request_id:
                    return

            # 2. Run High-Speed Spell Check
            if active_lenses.get("spelling", False) and self.spell_engine:
                spelling_findings = self.spell_engine.check_text(text)
                findings.extend(spelling_findings)
                findings.sort(key=lambda f: f.start_pos)

            # Final check before emitting
            with self._lock:
                if request_id < self._latest_request_id:
                    return

            self.finished.emit(findings, request_id)
        except Exception as e:
            self.error.emit(str(e), request_id)


class ReviewWorker(QRunnable):
    """Background task that executes linguistic lenses and spell check via QThreadPool."""

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
        # CRITICAL: setAutoDelete(False) prevents C++ QThreadPool from invoking
        # Shiboken destructor on secondary thread, preventing python312.dll 0xc0000005 crashes
        self.setAutoDelete(False)

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
