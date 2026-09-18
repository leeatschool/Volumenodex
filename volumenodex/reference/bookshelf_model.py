"""Bookshelf management and metadata discovery for the Writers Reference Library."""

import os
import shutil
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

from volumenodex.reference.epub_reader import EpubParser, EpubBook


@dataclass
class BookCoverStyle:
    """Styling parameters for physically rendering a bound hardcover book on the shelf."""
    leather_top: str
    leather_bottom: str
    gilt_foil: str
    ribbon_color: str
    spine_ribs_count: int = 4


BOOK_COLOR_PALETTES = [
    BookCoverStyle(
        leather_top="#801e28",
        leather_bottom="#4a0f16",
        gilt_foil="#f5c767",
        ribbon_color="#d9383a",
    ),  # Antique Crimson
    BookCoverStyle(
        leather_top="#1d3866",
        leather_bottom="#0f203d",
        gilt_foil="#e8c263",
        ribbon_color="#3b82f6",
    ),  # Royal Midnight Navy
    BookCoverStyle(
        leather_top="#1d5444",
        leather_bottom="#0f3329",
        gilt_foil="#e0b852",
        ribbon_color="#22c55e",
    ),  # Victorian Forest Emerald
    BookCoverStyle(
        leather_top="#733f1c",
        leather_bottom="#42220d",
        gilt_foil="#f3cf7a",
        ribbon_color="#eab308",
    ),  # Cognac Amber Leather
    BookCoverStyle(
        leather_top="#522650",
        leather_bottom="#30142f",
        gilt_foil="#f0d182",
        ribbon_color="#a855f7",
    ),  # Imperial Plum Morocco
    BookCoverStyle(
        leather_top="#2a3f4d",
        leather_bottom="#16242e",
        gilt_foil="#e2bd66",
        ribbon_color="#06b6d4",
    ),  # Deep Slate Teal
]


class ReferenceBookshelfManager:
    """Manages discovery, persistence, and querying of reference volumes."""

    def __init__(self, user_books_dir: Optional[str] = None):
        if user_books_dir:
            self.user_books_dir = os.path.abspath(user_books_dir)
        else:
            self.user_books_dir = os.path.join(str(Path.home()), ".volumenodex", "books")

        os.makedirs(self.user_books_dir, exist_ok=True)
        self._cached_books: List[EpubBook] = []
        self._palette_map: Dict[str, BookCoverStyle] = {}
        self.reload_books()

    def reload_books(self) -> List[EpubBook]:
        """Discovers all reference books across bundled assets, user books, and standard paths."""
        discovered_paths = set()

        # 1. Bundled resources in package
        repo_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        bundled_dir = os.path.join(repo_dir, "resources", "books")
        if os.path.isdir(bundled_dir):
            for f in sorted(os.listdir(bundled_dir)):
                if f.lower().endswith(".epub"):
                    discovered_paths.add(os.path.join(bundled_dir, f))

        # 2. User library directory (~/.volumenodex/books)
        if os.path.isdir(self.user_books_dir):
            for f in sorted(os.listdir(self.user_books_dir)):
                if f.lower().endswith(".epub"):
                    discovered_paths.add(os.path.join(self.user_books_dir, f))

        # 3. Explicit initial user download locations as fallback
        explicit_candidates = [
            r"C:\Users\Aaron\Downloads\pg12342-images-3.epub",
            r"C:\Users\Aaron\Downloads\pg74575-images-3.epub",
            r"C:\Users\Aaron\Downloads\pg18362-images-3.epub",
            r"C:\Users\Aaron\Downloads\pg40825-images-3.epub",
            os.path.join(str(Path.home()), "Downloads", "pg12342-images-3.epub"),
            os.path.join(str(Path.home()), "Downloads", "pg74575-images-3.epub"),
            os.path.join(str(Path.home()), "Downloads", "pg18362-images-3.epub"),
            os.path.join(str(Path.home()), "Downloads", "pg40825-images-3.epub"),
        ]
        for p in explicit_candidates:
            if os.path.isfile(p):
                # Avoid duplicates by basename
                bname = os.path.basename(p)
                if not any(os.path.basename(existing) == bname for existing in discovered_paths):
                    discovered_paths.add(p)

        books: List[EpubBook] = []
        for path in sorted(discovered_paths):
            book = EpubParser.load_full_book(path)
            if book:
                # Clean up any unicode character glitch in titles
                book.title = book.title.replace("\ufffd", "æ")
                books.append(book)

        # Sort books deterministically
        self._cached_books = sorted(books, key=lambda b: b.title.lower())

        # Assign beautiful consistent cover palettes
        for idx, book in enumerate(self._cached_books):
            self._palette_map[book.file_path] = BOOK_COLOR_PALETTES[idx % len(BOOK_COLOR_PALETTES)]

        return self._cached_books

    @property
    def books(self) -> List[EpubBook]:
        return self._cached_books

    def get_style_for_book(self, book: EpubBook) -> BookCoverStyle:
        return self._palette_map.get(book.file_path, BOOK_COLOR_PALETTES[0])

    def add_book(self, source_path: str) -> Optional[EpubBook]:
        """Imports an external EPUB into the local reference bookshelf library."""
        if not os.path.isfile(source_path) or not source_path.lower().endswith(".epub"):
            return None

        filename = os.path.basename(source_path)
        dest_path = os.path.join(self.user_books_dir, filename)

        if not os.path.exists(dest_path) or os.path.abspath(source_path) != os.path.abspath(dest_path):
            shutil.copy2(source_path, dest_path)

        self.reload_books()
        return next((b for b in self._cached_books if os.path.basename(b.file_path) == filename), None)

    def filter_books(self, query: str) -> List[EpubBook]:
        """Filters books on the shelf by title or author."""
        q = query.strip().lower()
        if not q:
            return self._cached_books
        return [
            b for b in self._cached_books
            if q in b.title.lower() or q in b.author.lower() or q in b.description.lower()
        ]
