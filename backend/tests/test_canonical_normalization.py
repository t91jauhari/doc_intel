import pytest
from app.canonical_normalization import (
    clean_syntactic_text,
    strip_salutations,
    canonicalize_entity,
    compact_token_string,
    canonical_compare,
)


def test_clean_syntactic_text():
    assert clean_syntactic_text("Indah Laruna Prima .") == "indah laruna prima"
    assert clean_syntactic_text("  PT Tiga Utama.  ") == "pt tiga utama"
    assert clean_syntactic_text("langit . raharja") == "langit raharja"
    assert clean_syntactic_text('"Customer Name"') == "customer name"
    assert clean_syntactic_text(None) == ""


def test_strip_salutations():
    assert strip_salutations("ms poko") == "poko"
    assert strip_salutations("ms. poko") == "poko"
    assert strip_salutations("mr. john smith") == "john smith"
    assert strip_salutations("bpk. budi santoso") == "budi santoso"
    assert strip_salutations("ibu siti") == "siti"
    assert strip_salutations("poko") == "poko"


def test_canonicalize_entity():
    assert canonicalize_entity("orange software (hk) ltd.") == "orange software (hk) limited"
    assert canonicalize_entity("orange software (hk) ltd") == "orange software (hk) limited"
    assert canonicalize_entity("orange software (hk) limited") == "orange software (hk) limited"
    assert canonicalize_entity("p.t. bank central asia") == "pt bank central asia"
    assert canonicalize_entity("pt. maju jaya tbk.") == "pt maju jaya tbk"


def test_canonical_compare_exact_and_syntactic():
    matched, method, sim = canonical_compare("PT Tiga Utama", "pt tiga utama.")
    assert matched is True
    assert method == "syntactic_clean_match"
    assert sim == 1.0

    matched, method, sim = canonical_compare("indah laruna prima", "indah laruna prima .")
    assert matched is True
    assert method == "syntactic_clean_match"

    matched, method, sim = canonical_compare("langit raharja", "langit . raharja")
    assert matched is True
    assert method == "syntactic_clean_match"


def test_canonical_compare_entity_and_salutation():
    matched, method, sim = canonical_compare("orange software (hk) ltd.", "orange software (hk) limited")
    assert matched is True
    assert method in {"canonical_entity_match", "canonical_combined_match"}

    matched, method, sim = canonical_compare("ms. poko", "poko")
    assert matched is True
    assert method == "salutation_stripped_match"


def test_canonical_compare_compound_spacing():
    matched, method, sim = canonical_compare("sri pujianty", "sri puji anty")
    assert matched is True
    assert method == "compact_token_match"


def test_canonical_compare_negative_substantive_differences():
    matched, method, sim = canonical_compare("Test Custome", "Test Customer")
    assert matched is False
    assert method == "differ"
    assert sim > 0.90  # Minor similarity captured

    matched, method, sim = canonical_compare("Jl Melati 2", "Jl Melati 1")
    assert matched is False

    matched, method, sim = canonical_compare("John Doe", "Jane Smith")
    assert matched is False
