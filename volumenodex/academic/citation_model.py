"""Academic citation data models, multi-style formatters, and reference manager.

Supports APA 7th, MLA 9th, Chicago 17th (Author-Date), IEEE, and Harvard styles,
with instant in-text citation injection and complete bibliography generation.
"""

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import List, Dict, Optional, Any
import html
import uuid
import re


class CitationType(str, Enum):
    JOURNAL = "journal"
    BOOK = "book"
    CHAPTER = "chapter"
    CONFERENCE = "conference"
    WEBSITE = "website"
    REPORT = "report"
    OTHER = "other"


CITATION_TYPE_LABELS = {
    CitationType.JOURNAL: "Journal Article",
    CitationType.BOOK: "Book / Monograph",
    CitationType.CHAPTER: "Book Chapter",
    CitationType.CONFERENCE: "Conference Proceeding",
    CitationType.WEBSITE: "Webpage / Online Source",
    CitationType.REPORT: "Report / Working Paper",
    CitationType.OTHER: "Other Source",
}


@dataclass
class CitationEntry:
    """A scholarly reference entry with bibliographic metadata."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    entry_type: CitationType = CitationType.JOURNAL
    title: str = ""
    authors: List[str] = field(default_factory=list)  # Stored as ["Last, First" or "First Last"]
    year: str = ""
    source_title: str = ""  # Journal Name, Book Title, or Website Name
    volume: str = ""
    issue: str = ""
    pages: str = ""
    publisher: str = ""
    publisher_location: str = ""
    doi: str = ""
    url: str = ""
    access_date: str = ""
    notes: str = ""

    @property
    def primary_author(self) -> str:
        if not self.authors:
            return "Anonymous"
        return self.authors[0]

    @property
    def author_last_names(self) -> List[str]:
        lasts = []
        for a in self.authors:
            parts = a.split(",")
            if len(parts) >= 2:
                lasts.append(parts[0].strip())
            else:
                tokens = a.strip().split()
                lasts.append(tokens[-1] if tokens else a.strip())
        return lasts or ["Anonymous"]

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["entry_type"] = self.entry_type.value if isinstance(self.entry_type, CitationType) else self.entry_type
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CitationEntry":
        d = dict(data)
        if "entry_type" in d:
            try:
                d["entry_type"] = CitationType(d["entry_type"])
            except ValueError:
                d["entry_type"] = CitationType.JOURNAL
        valid_fields = {k: v for k, v in d.items() if k in cls.__dataclass_fields__}
        return cls(**valid_fields)


class CitationFormatter:
    """Generates strictly formatted in-text citations and bibliographies across styles."""

    SUPPORTED_STYLES = ["APA 7th", "MLA 9th", "Chicago 17th", "IEEE", "Harvard"]

    @classmethod
    def _parse_author_name(cls, raw: str) -> tuple[str, str]:
        """Returns (Last, First/Initials)."""
        raw = raw.strip()
        if not raw:
            return ("Anonymous", "")
        if "," in raw:
            parts = raw.split(",", 1)
            return (parts[0].strip(), parts[1].strip())
        tokens = raw.split()
        if len(tokens) == 1:
            return (tokens[0], "")
        return (tokens[-1], " ".join(tokens[:-1]))

    @classmethod
    def _initials(cls, first_name: str) -> str:
        if not first_name:
            return ""
        tokens = re.split(r"[\s.-]+", first_name.strip())
        return ". ".join([t[0].upper() for t in tokens if t]) + "."

    # -------------------------------------------------------------
    # In-Text Citations
    # -------------------------------------------------------------
    @classmethod
    def format_in_text(cls, entry: CitationEntry, style: str = "APA 7th", page: str = "", index: int = 1) -> str:
        lasts = entry.author_last_names
        n = len(lasts)
        year = entry.year or "n.d."

        if style == "IEEE":
            if page:
                return f"[{index}, p. {page}]"
            return f"[{index}]"

        if style == "MLA 9th":
            if n == 1:
                auth = lasts[0]
            elif n == 2:
                auth = f"{lasts[0]} and {lasts[1]}"
            else:
                auth = f"{lasts[0]} et al."
            return f"({auth} {page})" if page else f"({auth})"

        if style == "Chicago 17th":
            if n == 1:
                auth = lasts[0]
            elif n == 2:
                auth = f"{lasts[0]} and {lasts[1]}"
            else:
                auth = f"{lasts[0]} et al."
            loc = f", {page}" if page else ""
            return f"({auth} {year}{loc})"

        if style == "Harvard":
            if n == 1:
                auth = lasts[0]
            elif n == 2:
                auth = f"{lasts[0]} & {lasts[1]}"
            else:
                auth = f"{lasts[0]} et al."
            loc = f": {page}" if page else ""
            return f"({auth} {year}{loc})"

        # Default: APA 7th
        if n == 1:
            auth = lasts[0]
        elif n == 2:
            auth = f"{lasts[0]} & {lasts[1]}"
        else:
            auth = f"{lasts[0]} et al."
        loc = f", p. {page}" if page else ""
        return f"({auth}, {year}{loc})"

    # -------------------------------------------------------------
    # Bibliography Entries
    # -------------------------------------------------------------
    @classmethod
    def format_bibliography_entry(cls, entry: CitationEntry, style: str = "APA 7th", index: int = 1) -> str:
        authors_raw = entry.authors
        parsed_raw = [cls._parse_author_name(a) for a in authors_raw] if authors_raw else [("Anonymous", "")]
        parsed = [(html.escape(last), html.escape(first)) for last, first in parsed_raw]
        year = html.escape(entry.year or "n.d.")
        title = html.escape(entry.title.rstrip(".") if entry.title else "Untitled Work")
        source = html.escape(entry.source_title.rstrip(".") if entry.source_title else "")
        vol = html.escape(entry.volume.strip())
        issue = html.escape(entry.issue.strip())
        pages = html.escape(entry.pages.strip())
        publisher = html.escape(entry.publisher.strip())
        doi = entry.doi.strip()
        url = entry.url.strip()

        doi_or_url = ""
        if doi:
            doi_raw = f"https://doi.org/{doi}" if not doi.startswith("http") else doi
            doi_or_url = html.escape(doi_raw)
        elif url:
            doi_or_url = html.escape(url)

        if style == "APA 7th":
            # Authors: Last, F. M., & Last, F. M.
            auth_str_list = [f"{last}, {cls._initials(first)}" for last, first in parsed]
            if len(auth_str_list) == 1:
                auth_str = auth_str_list[0]
            elif len(auth_str_list) == 2:
                auth_str = f"{auth_str_list[0]} & {auth_str_list[1]}"
            else:
                auth_str = ", ".join(auth_str_list[:-1]) + f", & {auth_str_list[-1]}"

            if entry.entry_type == CitationType.JOURNAL:
                vi = f"<i>{source}</i>" if source else ""
                if vol:
                    vi += f", <i>{vol}</i>"
                    if issue:
                        vi += f"({issue})"
                if pages:
                    vi += f", {pages}"
                entry_str = f"{auth_str} ({year}). {title}. {vi}."
            elif entry.entry_type == CitationType.BOOK:
                entry_str = f"{auth_str} ({year}). <i>{title}</i>."
                if publisher:
                    entry_str += f" {publisher}."
            elif entry.entry_type == CitationType.CHAPTER:
                entry_str = f"{auth_str} ({year}). {title}."
                if source:
                    entry_str += f" In <i>{source}</i>"
                    if pages:
                        entry_str += f" (pp. {pages})"
                    entry_str += "."
                if publisher:
                    entry_str += f" {publisher}."
            else:
                entry_str = f"{auth_str} ({year}). <i>{title}</i>."
                if source:
                    entry_str += f" {source}."

            if doi_or_url:
                entry_str += f" {doi_or_url}"
            return entry_str

        elif style == "MLA 9th":
            # Authors: Last, First, and First Last.
            if len(parsed) == 1:
                auth_str = f"{parsed[0][0]}, {parsed[0][1]}".rstrip(", ")
            elif len(parsed) == 2:
                auth_str = f"{parsed[0][0]}, {parsed[0][1]}, and {parsed[1][1]} {parsed[1][0]}".rstrip(", ")
            else:
                auth_str = f"{parsed[0][0]}, {parsed[0][1]}, et al.".rstrip(", ")

            if entry.entry_type == CitationType.JOURNAL:
                entry_str = f'{auth_str}. "{title}." <i>{source}</i>'
                if vol:
                    entry_str += f", vol. {vol}"
                if issue:
                    entry_str += f", no. {issue}"
                entry_str += f", {year}"
                if pages:
                    entry_str += f", pp. {pages}"
                entry_str += "."
            elif entry.entry_type == CitationType.BOOK:
                entry_str = f"{auth_str}. <i>{title}</i>. "
                if publisher:
                    entry_str += f"{publisher}, "
                entry_str += f"{year}."
            else:
                entry_str = f'{auth_str}. "{title}." <i>{source}</i>, {year}.'

            if doi_or_url:
                entry_str += f" {doi_or_url}."
            return entry_str

        elif style == "Chicago 17th":
            # Authors: Last, First, and First Last. Year.
            if len(parsed) == 1:
                auth_str = f"{parsed[0][0]}, {parsed[0][1]}".rstrip(", ")
            elif len(parsed) == 2:
                auth_str = f"{parsed[0][0]}, {parsed[0][1]}, and {parsed[1][1]} {parsed[1][0]}".rstrip(", ")
            else:
                auth_str = f"{parsed[0][0]}, {parsed[0][1]}, et al.".rstrip(", ")

            if entry.entry_type == CitationType.JOURNAL:
                vi = f"<i>{source}</i>" if source else ""
                if vol:
                    vi += f" {vol}"
                if issue:
                    vi += f" ({issue})"
                if pages:
                    vi += f": {pages}"
                entry_str = f'{auth_str}. {year}. "{title}." {vi}.'
            elif entry.entry_type == CitationType.BOOK:
                loc = f"{entry.publisher_location}: " if entry.publisher_location else ""
                pub = f"{publisher}." if publisher else ""
                entry_str = f"{auth_str}. {year}. <i>{title}</i>. {loc}{pub}"
            else:
                entry_str = f'{auth_str}. {year}. "{title}." <i>{source}</i>.'

            if doi_or_url:
                entry_str += f" {doi_or_url}."
            return entry_str

        elif style == "IEEE":
            # Authors: [1] F. M. Last and F. M. Last, ...
            auth_str_list = [f"{cls._initials(first)} {last}".strip() for last, first in parsed]
            if len(auth_str_list) == 1:
                auth_str = auth_str_list[0]
            elif len(auth_str_list) == 2:
                auth_str = f"{auth_str_list[0]} and {auth_str_list[1]}"
            else:
                auth_str = f"{auth_str_list[0]} <i>et al.</i>"

            if entry.entry_type == CitationType.JOURNAL:
                vi = f"<i>{source}</i>" if source else ""
                if vol:
                    vi += f", vol. {vol}"
                if issue:
                    vi += f", no. {issue}"
                if pages:
                    vi += f", pp. {pages}"
                entry_str = f'[{index}] {auth_str}, "{title}," {vi}, {year}.'
            elif entry.entry_type == CitationType.BOOK:
                loc = f"{entry.publisher_location}: " if entry.publisher_location else ""
                pub = f"{publisher}, " if publisher else ""
                entry_str = f'[{index}] {auth_str}, <i>{title}</i>. {loc}{pub}{year}.'
            else:
                entry_str = f'[{index}] {auth_str}, "{title}," <i>{source}</i>, {year}.'

            if doi_or_url:
                entry_str += f" doi: {doi_or_url}."
            return entry_str

        else:  # Harvard
            auth_str_list = [f"{last}, {cls._initials(first)}" for last, first in parsed]
            if len(auth_str_list) == 1:
                auth_str = auth_str_list[0]
            elif len(auth_str_list) == 2:
                auth_str = f"{auth_str_list[0]} and {auth_str_list[1]}"
            else:
                auth_str = f"{auth_str_list[0]} et al."

            if entry.entry_type == CitationType.JOURNAL:
                vi = f"<i>{source}</i>" if source else ""
                if vol:
                    vi += f", {vol}"
                    if issue:
                        vi += f"({issue})"
                if pages:
                    vi += f", pp. {pages}"
                entry_str = f"{auth_str} ({year}) '{title}', {vi}."
            else:
                entry_str = f"{auth_str} ({year}) <i>{title}</i>. {publisher}."

            if doi_or_url:
                entry_str += f" Available at: {doi_or_url}."
            return entry_str

    @classmethod
    def generate_bibliography(cls, citations: List[CitationEntry], style: str = "APA 7th") -> str:
        """Generates formatted HTML for the complete references section."""
        if not citations:
            return "<p><i>No citations recorded in bibliography.</i></p>"

        # Sort: alphabetical by first author's last name (except IEEE which is indexed)
        if style != "IEEE":
            sorted_citations = sorted(citations, key=lambda c: (c.author_last_names[0].lower(), c.year, c.title.lower()))
        else:
            sorted_citations = list(citations)

        html_lines = []
        for idx, entry in enumerate(sorted_citations, start=1):
            formatted = cls.format_bibliography_entry(entry, style=style, index=idx)
            html_lines.append(f'<p style="margin-left: 28px; text-indent: -28px; margin-bottom: 8px;">{formatted}</p>')

        return "\n".join(html_lines)


class CitationManager:
    """Manages the author's scholarly sources, citations, and active bibliography."""

    def __init__(self):
        self.citations: List[CitationEntry] = []
        self.active_style: str = "APA 7th"

    def add_citation(self, entry: CitationEntry) -> None:
        self.citations.append(entry)

    def update_citation(self, entry: CitationEntry) -> None:
        for i, c in enumerate(self.citations):
            if c.id == entry.id:
                self.citations[i] = entry
                return
        self.add_citation(entry)

    def delete_citation(self, entry_id: str) -> None:
        self.citations = [c for c in self.citations if c.id != entry_id]

    def get_citation(self, entry_id: str) -> Optional[CitationEntry]:
        for c in self.citations:
            if c.id == entry_id:
                return c
        return None

    def search(self, query: str) -> List[CitationEntry]:
        if not query or not query.strip():
            return self.citations
        q = query.lower().strip()
        results = []
        for c in self.citations:
            if q in c.title.lower() or q in c.source_title.lower() or any(q in a.lower() for a in c.authors) or q in c.year:
                results.append(c)
        return results

    def to_dict(self) -> List[Dict[str, Any]]:
        return [c.to_dict() for c in self.citations]

    def from_dict(self, data: List[Dict[str, Any]]) -> None:
        self.citations = [CitationEntry.from_dict(d) for d in data if isinstance(d, dict)]
