"""Test normalize_package_no handles all known e-GP formats (W-010)."""

from app.core.helpers import normalize_package_no


def test_none_and_empty():
    assert normalize_package_no(None) == ""
    assert normalize_package_no("") == ""


def test_whitespace_stripped():
    assert normalize_package_no("  ABC-123  ") == "ABC-123"
    assert normalize_package_no("\tABC-123\n") == "ABC-123"


def test_uppercased():
    assert normalize_package_no("abc-123") == "ABC-123"
    assert normalize_package_no("abc/def2") == "ABC/DEF2"


def test_backslash_replaced():
    assert normalize_package_no("ABC\\123") == "ABC/123"


def test_special_chars_removed():
    assert normalize_package_no("ABC#123$%^") == "ABC123"
    assert normalize_package_no("A_B-1C!D") == "AB-1CD"


def test_pure_numeric_rejected():
    assert normalize_package_no("1127087") == ""
    assert normalize_package_no("123456") == ""
    assert normalize_package_no("9999999") == ""


def test_short_numeric_rejected():
    assert normalize_package_no("12345") == ""
    assert normalize_package_no("99999") == ""


def test_no_digit_rejected():
    assert normalize_package_no("ABCDEF") == ""
    assert normalize_package_no("ABC/DEF") == ""


def test_no_alpha_no_separator_rejected():
    assert normalize_package_no("12345") == ""
    assert normalize_package_no("00000") == ""


def test_over_120_chars_rejected():
    assert normalize_package_no("A" + "1" * 120) == ""


def test_known_egp_formats():
    assert normalize_package_no("ABC-123/DEF") == "ABC-123/DEF"
    assert normalize_package_no("04.09.01.01") == "04.09.01.01"
    assert normalize_package_no("40-200-00") == "40-200-00"
    assert normalize_package_no("26.50.1") == "26.50.1"
    assert normalize_package_no("02-1-2") == "02-1-2"


def test_mixed_format():
    assert normalize_package_no("  ab/12-3  ") == "AB/12-3"
    assert normalize_package_no("x.123.456") == "X.123.456"
    assert normalize_package_no("PWD-23/45") == "PWD-23/45"


def test_punctuation_preserved():
    assert normalize_package_no("ABC-123.45") == "ABC-123.45"
    assert normalize_package_no("A/B/C-1.2") == "A/B/C-1.2"
    assert normalize_package_no("B.1.1.1") == "B.1.1.1"


def test_zero_length_after_cleanup():
    assert normalize_package_no("!!!") == ""
    assert normalize_package_no("   ") == ""
