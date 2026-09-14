"""Unit tests for the TextNormalizer smart paragraph reflow and sentence case normalization."""

import pytest
from volumenodex.reference.text_normalizer import TextNormalizer


def test_normalize_title_case():
    raw_title = "CHAPTER 1: THE INFANTRY SQUAD AND ITS MOVEMENTS IN BATTLE"
    cased = TextNormalizer.normalize_title_case(raw_title)
    assert cased == "Chapter 1: The Infantry Squad and Its Movements in Battle"

    # Preserves known acronyms
    aviation_title = "FAA AND NASA REGULATIONS ON AIRCRAFT STALLS AND AOA DYNAMICS"
    cased_av = TextNormalizer.normalize_title_case(aviation_title)
    assert "FAA" in cased_av
    assert "NASA" in cased_av
    assert "AOA" in cased_av
    assert "on" in cased_av
    assert "and" in cased_av

    # Preserves already well-cased titles
    good_title = "Postmortem Changes: Algor, Livor, and Rigor Mortis"
    assert TextNormalizer.normalize_title_case(good_title) == good_title


def test_normalize_sentence_case():
    shouting = (
        "THE STANDING RIGGING CONSISTS OF SHROUDS AND STAYS. "
        "ACCORDING TO NASA AND THE FAA, THE AOA MUST BE CAREFULLY MONITORED. "
        "I AM CONVINCED OF THIS! DO YOU AGREE? YES, I'VE CHECKED ON MONDAY."
    )
    result = TextNormalizer.normalize_sentence_case(shouting)

    # First letters capitalized
    assert result.startswith("The standing rigging consists of shrouds and stays.")
    # Acronyms preserved
    assert "NASA" in result
    assert "FAA" in result
    assert "AOA" in result
    # Pronoun I and contractions preserved
    assert "I am convinced" in result
    assert "I've checked" in result
    # Proper nouns preserved
    assert "Monday" in result


def test_reflow_paragraphs_and_hyphens():
    broken_text = (
        "The standing rigging consists of\n"
        "shrouds, stays, and backstays\n"
        "supporting the masts against\n"
        "wind and spray.\n\n"
        "During close recon-\n"
        "naissance operations, the squad\n"
        "advances cautiously."
    )
    reflowed = TextNormalizer.reflow_paragraphs(broken_text)

    # Two paragraphs separated by double newline
    paras = reflowed.split("\n\n")
    assert len(paras) == 2

    # First paragraph joined into single line
    assert paras[0] == "The standing rigging consists of shrouds, stays, and backstays supporting the masts against wind and spray."

    # Hyphen repaired into 'reconnaissance'
    assert "reconnaissance" in paras[1]
    assert "recon-" not in paras[1]


def test_reflow_bullet_lists():
    list_text = (
        "- First tactical procedure\n"
        "- Second procedure that wraps\n"
        "  onto another line\n"
        "- Third procedure"
    )
    reflowed = TextNormalizer.reflow_paragraphs(list_text)
    lines = reflowed.splitlines()

    assert len(lines) == 3
    assert lines[0] == "• First tactical procedure"
    assert "Second procedure that wraps onto another line" in lines[1]
    assert lines[2] == "• Third procedure"


def test_clean_typography():
    messy = '“This is a test,” said the officer — ‘with quotes’ and    extra   spaces.'
    cleaned = TextNormalizer.clean_typography(messy)

    assert cleaned == '"This is a test," said the officer — \'with quotes\' and extra spaces.'
