"""Reference Manager engine for offline knowledge lookup, indexing, search, and user entry persistence."""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

from volumenodex.reference.reference_model import ReferenceEntry, ReferenceCategory


class ReferenceManager:
    """Manages the bundled offline encyclopedia and user-created custom reference entries."""

    def __init__(self, user_storage_dir: Optional[str] = None):
        self._entries: Dict[str, ReferenceEntry] = {}
        self._bundled_path = os.path.join(os.path.dirname(__file__), "bundled_knowledge.json")

        if user_storage_dir:
            self._storage_dir = Path(user_storage_dir)
        else:
            self._storage_dir = Path.home() / ".volumenodex"
        
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        self._user_custom_path = self._storage_dir / "user_reference.json"

        self.reload()

    def reload(self) -> None:
        """Reloads bundled knowledge and user custom additions."""
        self._entries.clear()

        # 1. Load bundled entries
        if os.path.exists(self._bundled_path):
            try:
                with open(self._bundled_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for item in data:
                        entry = ReferenceEntry.from_dict(item)
                        entry.is_custom = False
                        self._entries[entry.id] = entry
            except Exception as e:
                print(f"Error loading bundled reference knowledge: {e}")

        # 2. Load user custom entries
        if self._user_custom_path.exists():
            try:
                with open(self._user_custom_path, "r", encoding="utf-8") as f:
                    user_data = json.load(f)
                    for item in user_data:
                        entry = ReferenceEntry.from_dict(item)
                        entry.is_custom = True
                        self._entries[entry.id] = entry
            except Exception as e:
                print(f"Error loading user custom reference entries: {e}")

    @property
    def total_count(self) -> int:
        """Returns the total number of loaded topics."""
        return len(self._entries)

    @property
    def custom_count(self) -> int:
        """Returns the number of user-created topics."""
        return sum(1 for e in self._entries.values() if e.is_custom)

    def get_entry(self, entry_id: str) -> Optional[ReferenceEntry]:
        """Fetches an entry by unique ID."""
        return self._entries.get(entry_id)

    def get_all_entries(self) -> List[ReferenceEntry]:
        """Returns all entries sorted alphabetically by title."""
        return sorted(self._entries.values(), key=lambda e: e.title.lower())

    def get_categories(self) -> List[str]:
        """Returns all distinct categories currently present in the database."""
        cats = set(e.category for e in self._entries.values() if e.category)
        # Ensure default categories come first in standard order
        ordered = []
        for std in ReferenceCategory.ALL_CATEGORIES:
            if std in cats:
                ordered.append(std)
                cats.remove(std)
        ordered.extend(sorted(cats))
        return ordered

    def get_tags(self) -> List[str]:
        """Returns all unique tags across all entries."""
        tags = set()
        for e in self._entries.values():
            tags.update(e.tags)
        return sorted(tags)

    def search(
        self,
        query: str = "",
        category: Optional[str] = None,
        tag: Optional[str] = None,
        only_custom: bool = False,
    ) -> List[ReferenceEntry]:
        """Searches and filters reference entries by keyword, category, and tag.

        Returns entries ranked by search relevance score, then alphabetically.
        """
        results: List[Tuple[ReferenceEntry, int]] = []
        q = query.strip()

        for entry in self._entries.values():
            if only_custom and not entry.is_custom:
                continue

            if category and category != "All Categories":
                if entry.category != category:
                    continue

            if tag and tag != "All Tags":
                if tag.lower() not in [t.lower() for t in entry.tags]:
                    continue

            if q:
                matches, score = entry.matches_query(q)
                if matches:
                    results.append((entry, score))
            else:
                # No query string, all matching filters are returned
                results.append((entry, 0))

        # Sort by score descending, then by title ascending
        results.sort(key=lambda item: (-item[1], item[0].title.lower()))
        return [item[0] for item in results]

    def add_or_update_entry(self, entry: ReferenceEntry) -> bool:
        """Adds or updates an entry and saves it to user storage."""
        if not entry.id:
            # Generate slug from title
            slug = "".join(c if c.isalnum() else "-" for c in entry.title.lower())
            slug = "-".join(filter(None, slug.split("-")))
            entry.id = slug or "custom-topic"

        entry.is_custom = True
        self._entries[entry.id] = entry
        return self._save_user_custom_entries()

    def delete_entry(self, entry_id: str) -> bool:
        """Deletes a user custom entry."""
        entry = self._entries.get(entry_id)
        if not entry or not entry.is_custom:
            return False

        del self._entries[entry_id]
        return self._save_user_custom_entries()

    def _save_user_custom_entries(self) -> bool:
        """Persists all custom entries to the user JSON storage file."""
        try:
            custom_entries = [e.to_dict() for e in self._entries.values() if e.is_custom]
            with open(self._user_custom_path, "w", encoding="utf-8") as f:
                json.dump(custom_entries, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error saving user custom entries: {e}")
            return False

    def export_to_json(self, file_path: str, include_bundled: bool = True) -> bool:
        """Exports entries to an external JSON package file."""
        try:
            entries_to_export = [
                e.to_dict()
                for e in self._entries.values()
                if (include_bundled or e.is_custom)
            ]
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(entries_to_export, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error exporting reference JSON to {file_path}: {e}")
            return False

    def import_from_json(self, file_path: str) -> int:
        """Imports reference entries from an external JSON file as user entries.

        Returns the number of entries imported.
        """
        if not os.path.exists(file_path):
            return 0

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if not isinstance(data, list):
                return 0

            count = 0
            for item in data:
                if isinstance(item, dict) and "title" in item:
                    entry = ReferenceEntry.from_dict(item)
                    entry.is_custom = True
                    self._entries[entry.id] = entry
                    count += 1

            if count > 0:
                self._save_user_custom_entries()
            return count
        except Exception as e:
            print(f"Error importing reference JSON from {file_path}: {e}")
            return 0
