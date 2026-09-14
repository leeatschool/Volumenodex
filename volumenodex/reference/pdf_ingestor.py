"""Automated PDF-to-Articles Ingestion and Extraction Engine.

Extracts structured chapters, sections, or lexicon entries from PDF documents using
local parsing and heuristic algorithms, then automatically categorizes, tags,
generates quick-facts, and incorporates them into Volumenodex's offline Writers Reference.
"""

import os
import re
import json
import math
import unicodedata
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Callable
from collections import Counter

try:
    import pymupdf as fitz
except ImportError:
    try:
        import fitz
    except ImportError:
        fitz = None

from volumenodex.reference.reference_model import ReferenceEntry, ReferenceCategory
from volumenodex.reference.text_normalizer import TextNormalizer


# Standard common English stopwords for tag extraction
STOPWORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", "aren't",
    "as", "at", "be", "because", "been", "before", "being", "below", "between", "both", "but", "by",
    "can", "can't", "cannot", "could", "couldn't", "did", "didn't", "do", "does", "doesn't", "doing",
    "don't", "down", "during", "each", "few", "for", "from", "further", "had", "hadn't", "has", "hasn't",
    "have", "haven't", "having", "he", "he'd", "he'll", "he's", "her", "here", "here's", "hers", "herself",
    "him", "himself", "his", "how", "how's", "i", "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is",
    "isn't", "it", "it's", "its", "itself", "let's", "me", "more", "most", "mustn't", "my", "myself",
    "no", "nor", "not", "of", "off", "on", "once", "only", "or", "other", "ought", "our", "ours",
    "ourselves", "out", "over", "own", "same", "shan't", "she", "she'd", "she'll", "she's", "should",
    "shouldn't", "so", "some", "such", "than", "that", "that's", "the", "their", "theirs", "them",
    "themselves", "then", "there", "there's", "these", "they", "they'd", "they'll", "they're", "they've",
    "this", "those", "through", "to", "too", "under", "until", "up", "very", "was", "wasn't", "we", "we'd",
    "we'll", "we're", "we've", "were", "weren't", "what", "what's", "when", "when's", "where", "where's",
    "which", "while", "who", "who's", "whom", "why", "why's", "with", "won't", "would", "wouldn't", "you",
    "you'd", "you'll", "you're", "you've", "your", "yours", "yourself", "yourselves",
    # Additional PDF / publication artifacts
    "page", "figure", "table", "section", "chapter", "edition", "published", "copyright", "index",
    "reference", "notes", "appendix", "author", "press", "university", "department", "isbn", "issn",
    "http", "https", "www", "com", "org", "gov", "et", "al", "ibid", "see", "also", "use", "used", "using"
}

# Domain vocabulary for automated heuristic categorization
CATEGORY_KEYWORDS: Dict[str, Dict[str, float]] = {
    ReferenceCategory.WEAPONS_WARFARE: {
        "rifle": 2.5, "infantry": 3.0, "platoon": 3.0, "squad": 2.5, "battalion": 2.5, "combat": 2.0,
        "tactics": 2.0, "fire": 1.0, "suppression": 2.5, "bounding": 3.0, "patrol": 2.0, "ambush": 2.5,
        "weapon": 2.0, "sword": 2.5, "blade": 2.0, "bullet": 2.0, "caliber": 2.5, "armor": 2.0,
        "grenade": 2.0, "artillery": 2.5, "assault": 2.0, "defense": 1.5, "flanking": 2.5, "mortar": 2.5,
        "bayonet": 2.5, "soldier": 1.5, "battlefield": 2.0, "overwatch": 3.0, "recoil": 2.0, "ammunition": 2.0
    },
    ReferenceCategory.POISONS_MEDICINE: {
        "triage": 3.0, "medic": 2.5, "wound": 2.0, "dressing": 2.0, "hemorrhage": 3.0, "tourniquet": 3.0,
        "toxic": 2.5, "toxin": 3.0, "poison": 3.0, "antidote": 3.0, "dosage": 2.5, "symptom": 2.0,
        "lethal": 2.0, "ld50": 3.5, "airway": 2.5, "respiration": 2.0, "pulse": 2.0, "venom": 3.0,
        "arsenic": 3.0, "cyanide": 3.5, "atropine": 3.5, "casualty": 2.0, "bandage": 2.0, "trauma": 2.0,
        "pharmaceutical": 2.5, "exposure": 1.5, "inhalation": 2.0, "ingestion": 2.0, "carcinogen": 2.5
    },
    ReferenceCategory.FORENSICS_CRIME: {
        "autopsy": 3.5, "postmortem": 3.5, "rigor": 3.5, "livor": 3.5, "algor": 3.5, "mortis": 3.5,
        "coroner": 3.0, "homicide": 2.5, "fingerprint": 3.0, "custody": 2.5, "evidence": 2.0,
        "bloodstain": 3.0, "investigation": 1.5, "investigator": 2.0, "laceration": 2.0, "contusion": 2.0,
        "pathology": 2.5, "forensic": 3.0, "decomposition": 2.5, "cadaver": 3.0, "crime": 1.5
    },
    ReferenceCategory.NAUTICAL_SAILING: {
        "knot": 2.0, "mast": 3.0, "sail": 3.0, "rigging": 3.0, "shrouds": 3.0, "halyard": 3.0,
        "port": 1.5, "starboard": 3.0, "helm": 3.0, "rudder": 2.0, "anchor": 2.5, "keel": 2.5,
        "hull": 2.0, "bow": 1.5, "stern": 2.0, "leeway": 3.0, "compass": 1.5, "sextant": 3.5,
        "dead reckoning": 3.5, "tides": 2.0, "currents": 1.5, "vessel": 2.0, "ship": 1.5, "sloop": 3.0,
        "frigate": 3.0, "gale": 2.0, "beaufort": 3.0, "windward": 3.0, "leeward": 3.0, "spar": 2.5
    },
    ReferenceCategory.AVIATION_FLIGHT: {
        "aircraft": 3.0, "airplane": 3.0, "flight": 2.0, "wing": 2.0, "cockpit": 3.0, "pilot": 2.5,
        "altitude": 2.5, "airspeed": 3.0, "stall": 3.0, "pitch": 2.0, "roll": 2.0, "yaw": 2.5,
        "aileron": 3.5, "elevator": 2.0, "altimeter": 3.5, "gyroscope": 2.5, "pitot": 3.5, "airfoil": 3.0,
        "thrust": 2.5, "drag": 2.0, "lift": 2.0, "runway": 2.5, "avionics": 3.0, "aerodynamic": 3.0
    },
    ReferenceCategory.ASTRONOMY_SPACE: {
        "planet": 3.0, "orbit": 2.5, "orbital": 2.5, "gravity": 2.0, "atmosphere": 1.5, "solar": 2.0,
        "lunar": 2.5, "celestial": 2.5, "star": 2.0, "crater": 2.0, "astronomical": 2.5, "eclipse": 2.5,
        "jupiter": 3.5, "saturn": 3.5, "mars": 3.0, "mercury": 2.0, "venus": 3.0, "nebula": 3.0,
        "perihelion": 3.5, "aphelion": 3.5, "eccentricity": 2.5, "telescope": 2.5, "cosmos": 2.5
    },
    ReferenceCategory.EARTH_METALS_MACHINES: {
        "metal": 2.0, "iron": 2.0, "steel": 2.0, "bronze": 2.5, "alloy": 2.5, "forge": 3.0,
        "anvil": 3.5, "smith": 2.5, "smelting": 3.0, "mineral": 2.5, "quartz": 2.5, "ore": 2.5,
        "hardness": 2.0, "mohs": 3.5, "lathe": 3.0, "gear": 2.5, "steam": 2.0, "engine": 2.0,
        "waterwheel": 3.5, "turbine": 2.5, "copper": 2.0, "lead": 1.5, "tin": 2.0, "zinc": 2.0
    },
    ReferenceCategory.WILDERNESS_SURVIVAL: {
        "shelter": 2.5, "survival": 2.5, "foraging": 3.0, "tinder": 3.5, "kindling": 3.0, "flint": 2.5,
        "snare": 3.0, "trap": 2.0, "purification": 2.5, "hypothermia": 3.0, "edible": 2.5, "dehydration": 2.5,
        "bushcraft": 3.5, "lean-to": 3.5, "debris": 1.5, "bivouac": 3.0, "water procurement": 3.5
    },
    ReferenceCategory.HERALDRY_CHIVALRY: {
        "heraldry": 3.5, "shield": 2.0, "blazon": 3.5, "escutcheon": 3.5, "tincture": 3.5, "crest": 2.5,
        "charge": 2.0, "argent": 3.5, "or": 1.0, "gules": 3.5, "azure": 3.0, "sable": 3.0, "vert": 3.0,
        "chevron": 3.0, "cadency": 3.5, "fess": 3.5, "coat of arms": 3.5, "chivalry": 2.5, "knighthood": 2.5
    },
    ReferenceCategory.SLANG_CANT_DIALECT: {
        "cant": 3.0, "slang": 3.0, "vulgar": 2.5, "rogue": 2.5, "beggar": 2.0, "thief": 2.0,
        "underworld": 2.5, "flash": 2.0, "highwayman": 3.0, "footpad": 3.5, "prigger": 3.5,
        "jargon": 2.5, "dialect": 2.5, "shill": 2.5, "sharper": 3.0, "cloy": 3.5, "gallows": 2.0
    },
    ReferenceCategory.MYTH_FOLKLORE: {
        "myth": 3.0, "folklore": 3.5, "motif": 3.0, "legend": 2.5, "fairy": 2.5, "ogre": 3.0,
        "dragon": 3.0, "ghost": 2.0, "revenant": 3.5, "supernatural": 2.5, "tabu": 3.5, "transformation": 2.0,
        "shapeshifting": 3.0, "tale": 2.0, "enchanted": 2.5, "talisman": 3.0, "curse": 2.5, "god": 1.5
    },
    ReferenceCategory.STORY_DRAMATURGY: {
        "situation": 2.0, "dramatic": 2.5, "tragedy": 2.5, "protagonist": 3.0, "antagonist": 3.0,
        "nemesis": 2.5, "remorse": 2.5, "supplication": 3.0, "sacrifice": 2.5, "rivalry": 2.0,
        "abduction": 2.5, "disaster": 2.0, "plot": 2.5, "climax": 2.5, "thesaurus": 2.5, "volition": 3.0
    },
    ReferenceCategory.CASTLES_ARCHITECTURE: {
        "castle": 3.0, "keep": 3.0, "tower": 2.0, "masonry": 2.5, "portcullis": 3.5, "moat": 3.0,
        "battlement": 3.5, "gatehouse": 3.5, "fortress": 2.5, "citadel": 3.0, "drawbridge": 3.5,
        "buttress": 3.0, "curtain wall": 3.5, "machicolation": 3.5, "rampart": 3.0
    },
    ReferenceCategory.ARCHAIC_UNITS_TIME: {
        "league": 3.0, "cubit": 3.5, "fathom": 3.0, "stone": 1.5, "bushel": 3.0, "rod": 2.0,
        "perch": 2.5, "dram": 3.0, "grain": 2.0, "fortnight": 3.0, "score": 1.5, "candlemas": 3.5,
        "michaelmas": 3.5, "gregorian": 2.5, "julian": 2.5, "sundial": 2.5, "clepsydra": 3.5
    }
}


class PDFArticleifier:
    """Engine that reads a PDF file and automatically segments it into structured ReferenceEntry objects."""

    def __init__(self, pdf_path: str):
        self.pdf_path = Path(pdf_path)
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        if fitz is None:
            raise ImportError("PyMuPDF (fitz) is required for PDFArticleifier.")

    def inspect_structure(self) -> Dict[str, Any]:
        """Analyzes PDF metadata, page count, and determines whether TOC or text heuristic is optimal."""
        doc = fitz.open(str(self.pdf_path))
        page_count = len(doc)
        toc = doc.get_toc()
        metadata = doc.metadata or {}
        doc.close()

        has_toc = bool(toc and len(toc) >= 3)
        return {
            "page_count": page_count,
            "has_toc": has_toc,
            "toc_entry_count": len(toc),
            "title": metadata.get("title") or self.pdf_path.stem.replace("_", " ").title(),
            "author": metadata.get("author") or "Unknown Author",
        }

    def process(
        self,
        mode: str = "auto",
        target_category: Optional[str] = None,
        min_words_per_article: int = 40,
        max_words_per_article: int = 2500,
        reflow_paragraphs: bool = True,
        normalize_case: bool = True,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> List[ReferenceEntry]:
        """Main pipeline to parse the PDF, split into articles, auto-tag, auto-classify, and build entries.

        Modes:
            - 'auto': Use TOC if available, otherwise heuristic headings
            - 'toc': Strictly use Table of Contents / bookmark hierarchy
            - 'headings': Use font size / heading detection across pages
            - 'lexicon': Treat as dictionary / glossary with alphabetical or bold headword terms
        """
        doc = fitz.open(str(self.pdf_path))
        total_pages = len(doc)
        toc = doc.get_toc()

        if mode == "auto":
            if toc and len(toc) >= 3:
                chosen_mode = "toc"
            else:
                chosen_mode = "headings"
        else:
            chosen_mode = mode

        raw_sections = []
        if chosen_mode == "toc":
            raw_sections = self._extract_by_toc(doc, toc, progress_callback)
        elif chosen_mode == "lexicon":
            raw_sections = self._extract_lexicon_entries(doc, progress_callback)
        else:
            raw_sections = self._extract_by_headings(doc, progress_callback)

        doc.close()

        # If sections are empty (e.g. malformed TOC), fallback to headings
        if not raw_sections and chosen_mode != "headings":
            doc = fitz.open(str(self.pdf_path))
            raw_sections = self._extract_by_headings(doc, progress_callback)
            doc.close()

        # Refine, chunk long sections, clean text, and assemble ReferenceEntry items
        articles: List[ReferenceEntry] = []
        doc_stem = re.sub(r'[^a-zA-Z0-9]+', '-', self.pdf_path.stem.lower()).strip('-')

        total_sections = len(raw_sections)
        for idx, sec in enumerate(raw_sections):
            if progress_callback:
                progress_callback(idx + 1, total_sections, f"Structuring article: {sec['title'][:35]}...")

            title = sec["title"].strip()
            text = sec["text"].strip()

            # Filter out non-content sections (TOC, Index, Copyright)
            if self._is_boilerplate(title, text):
                continue

            words = text.split()
            if len(words) < min_words_per_article:
                continue

            # If section is too massive (> max_words), split into cohesive subsections
            chunks = self._chunk_text(title, text, max_words_per_article)

            for chunk_idx, (chunk_title, chunk_text) in enumerate(chunks):
                # 1. Normalize Title Casing
                if normalize_case:
                    chunk_title = TextNormalizer.normalize_title_case(chunk_title)

                # 2. Reflow line-broken paragraphs and clean typography
                if reflow_paragraphs:
                    chunk_text = TextNormalizer.clean_typography(chunk_text)
                    chunk_text = TextNormalizer.reflow_paragraphs(chunk_text)

                # 3. Normalize Sentence Case for screaming all-caps text
                if normalize_case:
                    chunk_text = TextNormalizer.normalize_sentence_case(chunk_text)

                # Classify category
                category = target_category
                if not category or category == "Auto-Detect Category":
                    category = self.classify_category(chunk_title + " " + chunk_text)

                # Extract tags
                tags = self.extract_tags(chunk_title, chunk_text)

                # Extract quick facts
                quick_facts = self.extract_quick_facts(chunk_text)

                # Generate summary
                summary = self.generate_summary(chunk_text)

                # Generate fiction author craft tips
                fiction_tips = self.generate_fiction_tips(chunk_title, category, chunk_text)

                # Generate unique slug ID
                slug_base = re.sub(r'[^a-zA-Z0-9]+', '-', chunk_title.lower()).strip('-')
                suffix = f"-{chunk_idx + 1}" if len(chunks) > 1 else ""
                entry_id = f"{doc_stem}-{slug_base}{suffix}"[:60].rstrip('-')

                entry = ReferenceEntry(
                    id=entry_id,
                    title=chunk_title,
                    category=category,
                    tags=tags,
                    summary=summary,
                    quick_facts=quick_facts,
                    content=chunk_text,
                    fiction_tips=fiction_tips,
                    is_custom=True
                )
                articles.append(entry)

        return articles

    def _extract_by_toc(
        self,
        doc: Any,
        toc: List[List[Any]],
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> List[Dict[str, str]]:
        """Segments the document according to bookmarks/TOC page ranges."""
        sections = []
        total_pages = len(doc)
        total_items = len(toc)

        for i, item in enumerate(toc):
            lvl, title, start_page = item
            if progress_callback:
                progress_callback(i + 1, total_items, f"Parsing TOC: {title[:30]}")

            # 1-indexed to 0-indexed
            start_p = max(0, start_page - 1)
            end_p = total_pages

            # Look ahead to find end page of this section
            for next_item in toc[i + 1:]:
                next_page = max(0, next_item[2] - 1)
                if next_page > start_p:
                    end_p = next_page
                    break

            end_p = max(start_p + 1, end_p)

            if start_p >= total_pages:
                continue

            # Extract pages in range
            pages_text = []
            for p in range(start_p, min(end_p, total_pages)):
                page = doc[p]
                pages_text.append(page.get_text("text"))

            combined_text = "\n\n".join(pages_text)
            clean_text = self._clean_extracted_text(combined_text)

            sections.append({
                "title": title.strip(),
                "text": clean_text,
                "start_page": start_p + 1,
                "end_page": min(end_p, total_pages)
            })

        return sections

    def _extract_by_headings(
        self,
        doc: Any,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> List[Dict[str, str]]:
        """Segments the document by detecting visual headings, font styles, and chapter headers."""
        sections = []
        current_title = "Introduction & Overview"
        current_paras = []
        total_pages = len(doc)

        heading_regex = re.compile(
            r'^(?:CHAPTER\s+[0-9IVXLCDM]+|SECTION\s+[A-Z0-9]+|PART\s+[0-9IVXLCDM]+|PROCEDURE\s+[A-Z0-9\.]+|[0-9]{1,2}\.[0-9]{1,2}(?:\.[0-9]+)?)\s*[:\-\.]?\s*(.+)$',
            re.IGNORECASE
        )

        for p_idx in range(total_pages):
            if progress_callback:
                progress_callback(p_idx + 1, total_pages, f"Scanning page {p_idx + 1}/{total_pages}")

            page = doc[p_idx]
            blocks = page.get_text("blocks")

            for b in blocks:
                # b: (x0, y0, x1, y1, text, block_no, block_type)
                if b[6] != 0:  # Skip image blocks
                    continue
                block_text = b[4].strip()
                if not block_text:
                    continue

                lines = [l.strip() for l in block_text.splitlines() if l.strip()]
                if not lines:
                    continue

                first_line = lines[0]

                # Check if block is a heading
                is_heading = False
                detected_title = ""

                m = heading_regex.match(first_line)
                if m:
                    is_heading = True
                    detected_title = first_line
                elif len(lines) == 1 and len(first_line) < 80 and (first_line.isupper() or first_line.istitle()) and not first_line.endswith("."):
                    is_heading = True
                    detected_title = first_line

                if is_heading:
                    # Save previous section if it has enough content
                    prev_text = "\n\n".join(current_paras).strip()
                    if len(prev_text.split()) >= 40:
                        sections.append({
                            "title": current_title,
                            "text": self._clean_extracted_text(prev_text)
                        })
                    current_title = detected_title
                    current_paras = lines[1:] if len(lines) > 1 else []
                else:
                    current_paras.append(block_text)

        # Append last section
        last_text = "\n\n".join(current_paras).strip()
        if len(last_text.split()) >= 40:
            sections.append({
                "title": current_title,
                "text": self._clean_extracted_text(last_text)
            })

        return sections

    def _extract_lexicon_entries(
        self,
        doc: Any,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> List[Dict[str, str]]:
        """Segments dictionary, glossary, or lexicon style documents into headwords and definitions."""
        sections = []
        total_pages = len(doc)

        # Common dictionary pattern: TERM. or TERM — or TERM, or ALL_CAPS TERM followed by text
        entry_pattern = re.compile(r'^([A-Z][A-Za-z\s\-\']{1,45})(?:\.|\s*[\—\–\-]\s*|\s*,\s*)(.+)$')

        current_headword = None
        current_def = []

        for p_idx in range(total_pages):
            if progress_callback:
                progress_callback(p_idx + 1, total_pages, f"Extracting lexicon: page {p_idx + 1}")

            page = doc[p_idx]
            text = page.get_text("text")

            for line in text.splitlines():
                l = line.strip()
                if not l:
                    continue

                m = entry_pattern.match(l)
                if m and len(m.group(1).split()) <= 4:
                    if current_headword and current_def:
                        def_text = " ".join(current_def).strip()
                        if len(def_text.split()) >= 8:
                            sections.append({
                                "title": current_headword,
                                "text": def_text
                            })
                    current_headword = m.group(1).strip().title()
                    current_def = [m.group(2).strip()]
                else:
                    if current_headword:
                        current_def.append(l)

        if current_headword and current_def:
            sections.append({
                "title": current_headword,
                "text": " ".join(current_def).strip()
            })

        return sections

    @staticmethod
    def _clean_extracted_text(raw_text: str) -> str:
        """Cleans PDF extraction artifacts, line-breaks inside sentences, and extraneous whitespace."""
        text = unicodedata.normalize("NFKD", raw_text)
        # Fix hyphenated words broken across linebreaks (e.g. 'recon- \n naissance' -> 'reconnaissance')
        text = re.sub(r'(\w+)-\s*\n\s*(\w+)', r'\1\2', text)
        # Collapse multiple newlines
        text = re.sub(r'\n{3,}', '\n\n', text)
        # Clean page numbers on standalone lines
        text = re.sub(r'\n\s*\d{1,4}\s*\n', '\n', text)
        return text.strip()

    @staticmethod
    def _is_boilerplate(title: str, text: str) -> bool:
        """Determines whether a section is publication boilerplate rather than author knowledge."""
        t_low = title.lower()
        boilerplate_titles = {
            "table of contents", "contents", "index", "foreword", "preface",
            "acknowledgments", "acknowledgements", "title page", "copyright",
            "dedication", "bibliography", "about the author", "errata"
        }
        if any(b in t_low for b in boilerplate_titles):
            return True
        if len(text.split()) < 35:
            return True
        return False

    @staticmethod
    def _chunk_text(title: str, text: str, max_words: int) -> List[Tuple[str, str]]:
        """Breaks overly long sections into cohesive subsections."""
        words = text.split()
        if len(words) <= max_words:
            return [(title, text)]

        paragraphs = text.split("\n\n")
        chunks = []
        curr_paras = []
        curr_word_count = 0
        part_num = 1

        for p in paragraphs:
            p_words = len(p.split())
            if curr_word_count + p_words > max_words and curr_paras:
                sub_title = f"{title} (Part {part_num})"
                chunks.append((sub_title, "\n\n".join(curr_paras).strip()))
                part_num += 1
                curr_paras = [p]
                curr_word_count = p_words
            else:
                curr_paras.append(p)
                curr_word_count += p_words

        if curr_paras:
            sub_title = f"{title} (Part {part_num})" if part_num > 1 else title
            chunks.append((sub_title, "\n\n".join(curr_paras).strip()))

        return chunks

    @classmethod
    def classify_category(cls, text: str) -> str:
        """Heuristically calculates scores across all categories using keyword frequency."""
        lowered = text.lower()
        tokens = re.findall(r'\b[a-z]{3,}\b', lowered)
        counts = Counter(tokens)

        best_category = ReferenceCategory.WEAPONS_WARFARE
        best_score = -1.0

        for cat, kw_dict in CATEGORY_KEYWORDS.items():
            score = 0.0
            for term, weight in kw_dict.items():
                if " " in term:
                    # Multi-word phrase
                    if term in lowered:
                        score += weight * 3.0
                else:
                    if term in counts:
                        score += counts[term] * weight

            if score > best_score:
                best_score = score
                best_category = cat

        return best_category

    @staticmethod
    def extract_tags(title: str, text: str, max_tags: int = 6) -> List[str]:
        """Extracts high-value domain keywords for tagging and fast indexing."""
        tags = set()

        # Add significant words from title
        title_tokens = re.findall(r'\b[a-zA-Z]{3,}\b', title.lower())
        for token in title_tokens:
            if token not in STOPWORDS and len(token) > 2:
                tags.add(token)

        # Extract top frequency domain terms from text
        text_tokens = re.findall(r'\b[a-zA-Z]{4,}\b', text.lower())
        meaningful = [t for t in text_tokens if t not in STOPWORDS]
        counts = Counter(meaningful)

        for word, _ in counts.most_common(12):
            if len(tags) >= max_tags:
                break
            if word not in tags:
                tags.add(word)

        return sorted(list(tags))

    @staticmethod
    def extract_quick_facts(text: str) -> Dict[str, str]:
        """Finds structured quantitative facts, definitions, and key-value metrics."""
        facts: Dict[str, str] = {}
        lines = [l.strip() for l in text.splitlines() if l.strip()]

        # Pattern 1: Explicit key-value lines or segments (e.g. "Range: 500m" or "Duration: 2 hours")
        kv_pattern = re.compile(r'(?:^|\n|[\.;]\s+)([A-Z][A-Za-z\s]{2,20})\s*:\s*([^\n;]{3,70})')
        for m in kv_pattern.finditer(text):
            k = m.group(1).strip().title()
            v = m.group(2).strip()
            if k not in facts and not k.startswith(("Http", "Figure", "Table")):
                facts[k] = v
            if len(facts) >= 5:
                break

        # Pattern 2: Numbers with units (distances, speeds, weights, temperatures)
        if len(facts) < 4:
            unit_pattern = re.compile(r'(\b\d+(?:\.\d+)?\s*(?:knots|mph|km/h|feet|ft|meters|m|yards|lbs|kg|psi|bars|hours|minutes|seconds|volts|cal|mm)\b)', re.IGNORECASE)
            matches = unit_pattern.findall(text)
            if matches:
                facts["Typical Metric / Measure"] = ", ".join(list(dict.fromkeys(matches))[:3])

        # Pattern 3: Key concept or standard rule
        if len(facts) < 3:
            first_sentence = re.split(r'(?<=[.!?])\s+', text)[0]
            if len(first_sentence) < 110:
                facts["Key Concept"] = first_sentence

        if not facts:
            facts["Status"] = "Standard Field Reference"

        return facts

    @staticmethod
    def generate_summary(text: str) -> str:
        """Synthesizes a 1-2 sentence core overview from the extracted text."""
        sentences = re.split(r'(?<=[.!?])\s+', text)
        clean_sentences = []
        for s in sentences:
            clean = s.strip()
            if len(clean) > 25 and not clean.startswith(("Fig", "Table", "See", "http")):
                clean_sentences.append(clean)
            if len(clean_sentences) >= 2:
                break

        if clean_sentences:
            return " ".join(clean_sentences)
        return text[:180].strip() + "..."

    @staticmethod
    def generate_fiction_tips(title: str, category: str, text: str) -> str:
        """Generates specific advice for fiction writers utilizing this reference topic."""
        category_prompts = {
            ReferenceCategory.WEAPONS_WARFARE: "In combat fiction, highlight muzzle blast, deafening acoustic concussion, and realistic reload or exhaustion limits.",
            ReferenceCategory.POISONS_MEDICINE: "Describe somatic symptoms: cold clammy perspiration, dilated pupils, rapid thready pulse, or bitter metallic taste.",
            ReferenceCategory.FORENSICS_CRIME: "Contrast procedural rigor with physical scene messiness; emphasize olfactory details like copper blood and chemical fixatives.",
            ReferenceCategory.NAUTICAL_SAILING: "Incorporate authentic shipboard commands and physics; emphasize the groaning of timber, spray over gunwales, and wind leeway.",
            ReferenceCategory.AVIATION_FLIGHT: "Convey the visceral sensations of G-force, instrument scan discipline, control stick resistance, and horizon cues.",
            ReferenceCategory.ASTRONOMY_SPACE: "Account for atmospheric pressure, lethal radiation, communications lag, and orbital gravity dynamics.",
            ReferenceCategory.EARTH_METALS_MACHINES: "Sensory cues: radiant heat from the hearth, hammer ringing on anvil face, and distinctive smells of slag and quenching oil.",
            ReferenceCategory.WILDERNESS_SURVIVAL: "Survival tension stems from caloric deficit, fine motor skill loss in cold fingers, and smoky expedient fires.",
            ReferenceCategory.HERALDRY_CHIVALRY: "Use heraldic blazons to telegraph lineage, legitimacy, bastardy cadency, or political alliances on shields and banners.",
            ReferenceCategory.SLANG_CANT_DIALECT: "Sprinkle thieves' cant naturally in dialogue to delineate social caste, illicit trade, and outsider suspicion.",
            ReferenceCategory.MYTH_FOLKLORE: "Folkloric logic operates on strict symbolic rules and reciprocal taboos rather than rational modern logic.",
            ReferenceCategory.STORY_DRAMATURGY: "Ensure the antagonist's motivation mirrors the protagonist's core flaw to heighten moral and emotional resonance.",
            ReferenceCategory.CASTLES_ARCHITECTURE: "Portray stone fortification as a system of lethal kill zones, spiraling stairs favoring right-handed defenders, and narrow arrow slits."
        }
        base_tip = category_prompts.get(category, "Ground the scene with realistic sensory cues and technical verisimilitude.")
        return f"{base_tip} Use {title.lower()} to anchor the scene with authenticity without pausing narrative pacing."


def incorporate_entries(
    entries: List[ReferenceEntry],
    target_json_path: str | Path,
    overwrite: bool = True
) -> Tuple[int, int, int]:
    """Merges a list of ReferenceEntry objects into a target JSON knowledge base.

    Returns:
        Tuple of (added_count, updated_count, total_count)
    """
    target_path = Path(target_json_path)
    existing_entries: Dict[str, dict] = {}

    if target_path.exists():
        try:
            with open(target_path, "r", encoding="utf-8") as f:
                raw_list = json.load(f)
                if isinstance(raw_list, list):
                    for item in raw_list:
                        if isinstance(item, dict) and "id" in item:
                            existing_entries[item["id"]] = item
        except Exception as e:
            print(f"Warning: Could not parse existing target JSON ({e}). Initializing fresh.")

    added_count = 0
    updated_count = 0

    for entry in entries:
        e_dict = entry.to_dict()
        eid = entry.id

        if eid in existing_entries:
            if overwrite:
                existing_entries[eid] = e_dict
                updated_count += 1
        else:
            existing_entries[eid] = e_dict
            added_count += 1

    # Write out cleanly sorted by title
    target_path.parent.mkdir(parents=True, exist_ok=True)
    all_sorted = sorted(existing_entries.values(), key=lambda d: d.get("title", "").lower())

    with open(target_path, "w", encoding="utf-8") as f:
        json.dump(all_sorted, f, indent=2, ensure_ascii=False)

    return added_count, updated_count, len(all_sorted)


def main():
    """Command-line interface to auto-ingest a PDF into Writers Reference."""
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Automated PDF-to-Articles Ingestion Tool for Writers Reference")
    parser.add_argument("pdf", help="Path to PDF file to process")
    parser.add_argument("--mode", choices=["auto", "toc", "headings", "lexicon"], default="auto",
                        help="Parsing strategy (default: auto)")
    parser.add_argument("--category", choices=ReferenceCategory.ALL_CATEGORIES, default=None,
                        help="Override category classification")
    parser.add_argument("--target", default=None,
                        help="Target JSON file path (default: bundled_knowledge.json)")
    parser.add_argument("--min-words", type=int, default=40, help="Minimum word threshold per article")
    parser.add_argument("--dry-run", action="store_true", help="Parse and display articles without saving")

    args = parser.parse_args()

    default_target = Path(__file__).resolve().parent / "bundled_knowledge.json"
    target_path = Path(args.target) if args.target else default_target

    print(f"[*] Opening PDF: {args.pdf}")
    ingestor = PDFArticleifier(args.pdf)
    info = ingestor.inspect_structure()
    print(f"    Pages: {info['page_count']} | TOC entries: {info['toc_entry_count']} | Has TOC: {info['has_toc']}")

    def on_progress(curr, total, msg):
        pct = int((curr / max(1, total)) * 100)
        print(f"[{pct:3d}%] ({curr}/{total}) {msg}")

    print(f"[*] Extracting and structuring articles using mode '{args.mode}'...")
    entries = ingestor.process(
        mode=args.mode,
        target_category=args.category,
        min_words_per_article=args.min_words,
        progress_callback=on_progress
    )

    print(f"\n[+] Extracted {len(entries)} articles successfully!\n")
    for idx, e in enumerate(entries[:5], 1):
        print(f"  {idx}. [{e.category}] {e.title}")
        print(f"     Tags: {', '.join(e.tags[:5])}")
        print(f"     Quick Facts: {len(e.quick_facts)} keys")
        print(f"     Summary: {e.summary[:90]}...")
        print()

    if len(entries) > 5:
        print(f"  ... and {len(entries) - 5} more articles.\n")

    if args.dry_run:
        print("[*] Dry run requested. No changes written to disk.")
        return

    added, updated, total = incorporate_entries(entries, target_path)
    print(f"[✓] Knowledge base updated: {target_path}")
    print(f"    Added: {added} new topics | Updated: {updated} topics | Total in Library: {total}")


if __name__ == "__main__":
    main()
