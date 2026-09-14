"""Text Normalizer and Smart Cleaner for Writers Reference.

Provides algorithms to:
1. Reflow line-broken PDF and OCR text into clean, natural paragraphs.
2. Normalize ALL-CAPS screaming text into proper Sentence Case.
3. Normalize headings into standard Title Case.
4. Clean typography, remove running page headers/footers, and repair split words.
5. Preserve technical acronyms (FAA, NASA, DNA, LD50, etc.) and Roman numerals.
"""

import re
import unicodedata
from typing import Set, List


# Technical, military, scientific, and governmental acronyms to preserve in uppercase
KNOWN_ACRONYMS: Set[str] = {
    # Organizations & Government
    "NASA", "FAA", "FBI", "NIJ", "CDC", "ATSDR", "DOJ", "DOD", "US", "USA", "UK", "USMC",
    "NATO", "UN", "WHO", "USGS", "NGA", "NOAA",
    # Aviation & Sailing
    "AOA", "VHF", "UHF", "GPS", "APN", "PHAK", "IFR", "VFR", "ILS", "VOR", "ATC", "AGL", "MSL",
    "KT", "KTS", "RPM", "PSI",
    # Medicine & Forensics
    "DNA", "RNA", "CPR", "PMI", "START", "CBRN", "EMS", "EMT", "ICU", "ER", "IV", "IM", "SC",
    "BP", "HR", "ECG", "EKG", "LD50", "LC50", "NOAEL", "TBI", "PPE", "BVM", "GCS",
    # Military Tactics
    "FM", "MCRP", "IED", "EOD", "FOB", "LZ", "SOP", "COA", "ROE", "ROE", "CAS", "IDF",
    "TOW", "ATGM", "NVG", "NOD", "EPW", "CCP", "MEDEVAC", "CASEVAC", "OP", "LP", "PIR",
    # Narrative & General
    "POV", "VIP", "CEO", "CFO", "CTO", "TOC", "FAQ", "BC", "AD", "BCE", "CE",
    # Roman Numerals
    "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII", "XIII", "XIV", "XV"
}

# Minor words kept lowercase in titles (unless first or last word)
TITLE_MINOR_WORDS: Set[str] = {
    "a", "an", "the", "and", "but", "or", "nor", "for", "yet", "so",
    "as", "at", "by", "for", "in", "of", "on", "per", "to", "up", "via",
    "with", "from", "into", "onto", "over", "than", "vs", "versus"
}

# Proper nouns (days of week, months)
PROPER_NOUNS: Set[str] = {
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday",
    "January", "February", "March", "April", "May", "June", "July", "August",
    "September", "October", "November", "December"
}


class TextNormalizer:
    """Smart text normalization and paragraph reflow engine."""

    @classmethod
    def clean_and_normalize(cls, text: str, is_title: bool = False) -> str:
        """Runs the complete cleaning and normalization pipeline."""
        if not text:
            return ""

        if is_title:
            return cls.normalize_title_case(text)

        # 1. Clean typography and OCR artifacts
        cleaned = cls.clean_typography(text)

        # 2. Reflow line-broken paragraphs
        reflowed = cls.reflow_paragraphs(cleaned)

        # 3. Normalize capitalization into sentence case
        normalized = cls.normalize_sentence_case(reflowed)

        return normalized.strip()

    @classmethod
    def reflow_paragraphs(cls, raw_text: str) -> str:
        """Reflows line-broken PDF text into contiguous, natural paragraphs.

        Distinguishes between false line-breaks (mid-sentence column wrapping)
        and genuine structural breaks (blank lines, bullet points, headers).
        """
        if not raw_text:
            return ""

        # Normalize line endings
        text = raw_text.replace("\r\n", "\n").replace("\r", "\n")

        # Strip running page number lines (e.g. "\n 14 \n" or "\n Page 4 of 20 \n")
        text = re.sub(r'(?m)^\s*(?:Page\s+)?\d+(?:\s+of\s+\d+)?\s*$', '', text)

        # Fix hyphenated words broken across linebreaks: "recon- \n naissance" -> "reconnaissance"
        text = re.sub(r'(\b\w+)-\s*\n\s*(\w+\b)', r'\1\2', text)

        # Split into blocks separated by 2 or more newlines
        blocks = re.split(r'\n\s*\n+', text)
        reflowed_blocks: List[str] = []

        bullet_pattern = re.compile(r'^\s*(?:[•\-\*–—]|(?:\d+|[a-zA-Z])[\.\)])\s+(.+)$')

        for block in blocks:
            lines = [l.strip() for l in block.splitlines() if l.strip()]
            if not lines:
                continue

            # Check if block contains list or bullet items
            has_bullets = any(bullet_pattern.match(l) for l in lines)

            if has_bullets:
                cleaned_bullets = []
                for line in lines:
                    m = bullet_pattern.match(line)
                    if m:
                        content = m.group(1).strip()
                        cleaned_bullets.append(f"• {content}")
                    else:
                        if cleaned_bullets:
                            cleaned_bullets[-1] += " " + line
                        else:
                            cleaned_bullets.append(line)

                reflowed_blocks.append("\n".join(cleaned_bullets))
            else:
                # Regular paragraph: join lines with spaces where appropriate, preserving Key: Value lines
                kv_pattern = re.compile(r'^[A-Z][A-Za-z\s]{2,25}\s*:\s*.+$')
                para_words: List[str] = []
                for idx, line in enumerate(lines):
                    if para_words:
                        prev_line = lines[idx - 1]
                        if prev_line.endswith(":") or kv_pattern.match(line) or kv_pattern.match(prev_line):
                            para_words.append("\n" + line)
                        else:
                            para_words.append(" " + line)
                    else:
                        para_words.append(line)

                para_text = "".join(para_words)
                para_text = re.sub(r'[ \t]+', ' ', para_text)
                reflowed_blocks.append(para_text.strip())

        return "\n\n".join(reflowed_blocks)

    @classmethod
    def normalize_sentence_case(cls, text: str) -> str:
        """Converts screaming ALL-CAPS paragraphs into clean Sentence case while preserving acronyms."""
        if not text:
            return ""

        # Check if text is predominantly uppercase
        letters = [c for c in text if c.isalpha()]
        if not letters:
            return text

        uppercase_count = sum(1 for c in letters if c.isupper())
        upper_ratio = uppercase_count / len(letters)

        # Process paragraph by paragraph
        paragraphs = text.split("\n\n")
        converted_paras = []

        for p in paragraphs:
            p_letters = [c for c in p if c.isalpha()]
            if not p_letters:
                converted_paras.append(p)
                continue

            p_upper_ratio = sum(1 for c in p_letters if c.isupper()) / len(p_letters)

            # If this paragraph is screaming uppercase (> 50% uppercase letters)
            if p_upper_ratio > 0.50:
                p_converted = cls._convert_string_to_sentence_case(p)
            else:
                p_converted = p

            converted_paras.append(p_converted)

        return "\n\n".join(converted_paras)

    @classmethod
    def _convert_string_to_sentence_case(cls, s: str) -> str:
        """Helper to convert a screaming string into proper sentence case."""
        # First lower-case the string
        lowered = s.lower()

        # Capitalize the first letter of each sentence
        # Split by sentence terminators (. ! ? or newline)
        segments = re.split(r'([.!?]+\s+|\n+)', lowered)
        capitalized_segments = []

        for i, seg in enumerate(segments):
            if i % 2 == 0:  # Sentence text
                seg_l = seg.lstrip()
                if seg_l:
                    leading = seg[:len(seg) - len(seg_l)]
                    first_char = seg_l[0].upper()
                    rest = seg_l[1:]
                    capitalized_segments.append(leading + first_char + rest)
                else:
                    capitalized_segments.append(seg)
            else:
                capitalized_segments.append(seg)

        res = "".join(capitalized_segments)

        # Restore known acronyms (case-insensitive search, replace with exact casing)
        for acr in KNOWN_ACRONYMS:
            pattern = re.compile(rf'\b{re.escape(acr.lower())}\b', re.IGNORECASE)
            res = pattern.sub(acr, res)

        # Restore proper nouns (days, months)
        for pn in PROPER_NOUNS:
            pattern = re.compile(rf'\b{re.escape(pn.lower())}\b', re.IGNORECASE)
            res = pattern.sub(pn, res)

        # Restore standalone pronoun "I" and contractions (I'm, I've, I'll, I'd)
        res = re.sub(r'\bi\b', 'I', res)
        res = re.sub(r"\bi'(m|ve|ll|d)\b", r"I'\1", res)

        return res

    @classmethod
    def normalize_title_case(cls, title: str) -> str:
        """Converts titles into clean Title Case, handling ALL-CAPS and Roman numerals."""
        if not title:
            return ""

        clean_title = cls.clean_typography(title).strip()
        # Remove trailing periods or colons from titles
        clean_title = re.sub(r'[\.:]+$', '', clean_title)

        words = clean_title.split()
        if not words:
            return ""

        # Check if title is predominantly uppercase
        letters = [c for c in clean_title if c.isalpha()]
        is_shouting = (len(letters) > 0 and (sum(1 for c in letters if c.isupper()) / len(letters)) > 0.6)

        if not is_shouting:
            # If not shouting, preserve original casing with minimal cleanup
            return clean_title

        titled_words = []
        last_idx = len(words) - 1

        for idx, word in enumerate(words):
            # Check for punctuation attached to word (e.g. "CHAPTER 1:", "TITLE,")
            prefix = ""
            suffix = ""
            m_pre = re.match(r'^([^a-zA-Z0-9]+)(.*)$', word)
            if m_pre:
                prefix = m_pre.group(1)
                word = m_pre.group(2)

            m_suf = re.match(r'^(.*?)([^a-zA-Z0-9]+)$', word)
            if m_suf:
                word = m_suf.group(1)
                suffix = m_suf.group(2)

            w_upper = word.upper()
            w_lower = word.lower()

            prev_ended_punct = False
            if idx > 0:
                prev_raw = words[idx - 1]
                if prev_raw.endswith((":", "-", "—", "–", ";", ".", "?", "!")):
                    prev_ended_punct = True

            if w_upper in KNOWN_ACRONYMS:
                cased = w_upper
            elif not prev_ended_punct and idx > 0 and idx < last_idx and w_lower in TITLE_MINOR_WORDS:
                cased = w_lower
            else:
                cased = word.capitalize()

            titled_words.append(f"{prefix}{cased}{suffix}")

        return " ".join(titled_words)

    @classmethod
    def clean_typography(cls, text: str) -> str:
        """Cleans typographic quotes, em-dashes, stray symbols, and excessive spacing."""
        if not text:
            return ""

        # Normalize unicode NFKD
        t = unicodedata.normalize("NFKD", text)

        # Smart quotes to standard quotes
        t = t.replace("“", '"').replace("”", '"')
        t = t.replace("‘", "'").replace("’", "'").replace("`", "'")

        # Dashes
        t = t.replace("—", " — ").replace("–", " — ")

        # Remove control characters (except newline and tab)
        t = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', t)

        # Collapse repeated spaces
        t = re.sub(r'[ \t]{2,}', ' ', t)

        # Normalize spaces before punctuation
        t = re.sub(r'\s+([,;:\.\?!])', r'\1', t)

        return t.strip()
